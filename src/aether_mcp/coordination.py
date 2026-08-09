"""M4/M5 bounded worker dispatch, messaging, retry and episode sealing."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, NoReturn, Protocol

from .content_store import ProtectedContentStore
from .lifecycle import LifecycleService, RunBinding
from .protocol import ProtocolError, canonical_request_digest, validate_request
from .trace_store import TraceStore

_UUID_NAMESPACE = uuid.UUID("3d5ad7fe-0e75-45c8-8d88-00bdf4a465ee")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,511}$")
_TERMINAL_STATES = {"TECHNICAL_COMPLETE", "FAILED", "CANCELLED", "FENCED"}
_ACTIVE_STATES = {"ACTIVE"}


class CoordinationError(RuntimeError):
    """Stable, secret-safe coordination failure."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _fail(code: str, message: str) -> NoReturn:
    raise CoordinationError(code, message)


def _uuid(value: Any, *, code: str = "INVALID_INPUT") -> str:
    try:
        parsed = uuid.UUID(value)
    except (ValueError, TypeError, AttributeError):
        _fail(code, "Coordination identity is invalid")
    if str(parsed) != value:
        _fail(code, "Coordination identity is not canonical")
    return value


def _token(value: Any) -> str:
    if not isinstance(value, str) or _TOKEN.fullmatch(value) is None:
        _fail("PROVIDER_RESPONSE_INVALID", "Provider identity is invalid")
    return value


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()
    ).hexdigest()


def _dispatch_id(operation_id: str) -> str:
    return str(uuid.uuid5(_UUID_NAMESPACE, f"dispatch:{operation_id}"))


def _message_id(operation_id: str) -> str:
    return str(uuid.uuid5(_UUID_NAMESPACE, f"message:{operation_id}"))


def _episode_id(run_id: str) -> str:
    return str(uuid.uuid5(_UUID_NAMESPACE, f"episode:{run_id}"))


@dataclass(frozen=True)
class ProviderDispatchResult:
    outcome: str
    provider_request_id: str | None
    provider_dispatch_id: str | None
    worker_id: str | None
    terminal_id: str | None
    worktree_id: str | None
    response_digest: str | None


@dataclass(frozen=True)
class ProviderMessageResult:
    outcome: str
    provider_message_id: str | None
    response_digest: str | None


class WorkerProvider(Protocol):
    binding_digest: str

    def dispatch_fixture(self, **kwargs: Any) -> ProviderDispatchResult: ...

    def retry_fixture(self, **kwargs: Any) -> ProviderDispatchResult: ...

    def send_worker_message(self, **kwargs: Any) -> ProviderMessageResult: ...

    def stop_worker(self, **kwargs: Any) -> Any: ...

    def cleanup_worker(self, **kwargs: Any) -> Any: ...

    def close(self, **kwargs: Any) -> Any: ...


@dataclass(frozen=True)
class Attempt:
    dispatch_id: str
    operation_id: str
    project_id: str
    run_id: str
    task_id: str
    task_key: str
    provider_task_id: str
    provider_dispatch_id: str
    worker_id: str
    terminal_id: str
    worktree_id: str
    generation: int
    state: str
    prior_dispatch_id: str | None
    authority_epoch: int
    artifact_path: str | None
    artifact_digest: str | None
    artifact_content_ref: str | None
    evidence_digest: str | None


class WorkerStore:
    """Aether-owned immutable Dispatch correlation and semantic attempt facts."""

    def __init__(self, root: Path) -> None:
        if root.is_symlink():
            _fail("TRACE_INTEGRITY_FAILURE", "Worker store root cannot be a symlink")
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(root, 0o700)
        self.root = root.resolve(strict=True)
        self.path = self.root / "coordination.sqlite3"
        if self.path.exists() and self.path.is_symlink():
            _fail("TRACE_INTEGRITY_FAILURE", "Worker store cannot be a symlink")
        self._migrate()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=5, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=5000")
        return connection

    def _migrate(self) -> None:
        try:
            with self._connect() as connection:
                version = int(connection.execute("PRAGMA user_version").fetchone()[0])
                if version == 0:
                    connection.executescript(
                        """
                        BEGIN EXCLUSIVE;
                        PRAGMA journal_mode=WAL;
                        CREATE TABLE attempts (
                            dispatch_id TEXT PRIMARY KEY,
                            operation_id TEXT NOT NULL UNIQUE,
                            project_id TEXT NOT NULL,
                            run_id TEXT NOT NULL,
                            task_id TEXT NOT NULL,
                            task_key TEXT NOT NULL,
                            provider_task_id TEXT NOT NULL,
                            provider_dispatch_id TEXT NOT NULL UNIQUE,
                            worker_id TEXT NOT NULL,
                            terminal_id TEXT NOT NULL,
                            worktree_id TEXT NOT NULL,
                            generation INTEGER NOT NULL,
                            state TEXT NOT NULL,
                            prior_dispatch_id TEXT,
                            authority_epoch INTEGER NOT NULL,
                            artifact_path TEXT,
                            artifact_digest TEXT,
                            artifact_content_ref TEXT,
                            evidence_digest TEXT,
                            UNIQUE(run_id, task_id, generation)
                        );
                        CREATE INDEX attempts_run_idx ON attempts(run_id, task_id, generation);
                        CREATE TABLE messages (
                            message_id TEXT PRIMARY KEY,
                            operation_id TEXT NOT NULL UNIQUE,
                            run_id TEXT NOT NULL,
                            sender_id TEXT NOT NULL,
                            recipient_id TEXT NOT NULL,
                            kind TEXT NOT NULL,
                            thread_id TEXT,
                            reply_to TEXT,
                            payload_digest TEXT NOT NULL,
                            safe_summary TEXT NOT NULL,
                            content_ref TEXT,
                            provider_message_id TEXT NOT NULL,
                            response_digest TEXT NOT NULL
                        );
                        CREATE INDEX messages_run_idx ON messages(run_id, message_id);
                        CREATE TABLE episodes (
                            episode_id TEXT PRIMARY KEY,
                            run_id TEXT NOT NULL UNIQUE,
                            manifest_digest TEXT NOT NULL,
                            envelope_json TEXT NOT NULL
                        );
                        PRAGMA user_version=1;
                        COMMIT;
                        """
                    )
                elif version != 1:
                    _fail("TRACE_SCHEMA_UNSUPPORTED", "Worker store schema is unsupported")
            os.chmod(self.path, 0o600)
        except CoordinationError:
            raise
        except sqlite3.Error:
            _fail("TRACE_INTEGRITY_FAILURE", "Worker store could not be initialized")

    @staticmethod
    def _attempt(row: sqlite3.Row) -> Attempt:
        return Attempt(**{key: row[key] for key in row.keys()})

    def bind_attempt(
        self,
        *,
        dispatch_id: str,
        operation_id: str,
        project_id: str,
        run_id: str,
        task_id: str,
        task_key: str,
        provider_task_id: str,
        provider: ProviderDispatchResult,
        generation: int,
        prior_dispatch_id: str | None,
    ) -> Attempt:
        _uuid(dispatch_id)
        _uuid(operation_id)
        _uuid(run_id)
        _uuid(task_id)
        if generation < 1 or provider.outcome != "APPLIED":
            _fail("PROVIDER_RESPONSE_INVALID", "Dispatch binding is invalid")
        identities = (
            provider.provider_dispatch_id,
            provider.worker_id,
            provider.terminal_id,
            provider.worktree_id,
        )
        if any(value is None for value in identities):
            _fail("PROVIDER_RESPONSE_INVALID", "Dispatch provider identities are incomplete")
        provider_dispatch_id, worker_id, terminal_id, worktree_id = (_token(value) for value in identities)
        provider_task_id = _token(provider_task_id)
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                existing = connection.execute("SELECT * FROM attempts WHERE operation_id=?", (operation_id,)).fetchone()
                if existing is not None:
                    attempt = self._attempt(existing)
                    expected = (
                        dispatch_id,
                        project_id,
                        run_id,
                        task_id,
                        task_key,
                        provider_task_id,
                        provider_dispatch_id,
                        generation,
                        prior_dispatch_id,
                    )
                    observed = (
                        attempt.dispatch_id,
                        attempt.project_id,
                        attempt.run_id,
                        attempt.task_id,
                        attempt.task_key,
                        attempt.provider_task_id,
                        attempt.provider_dispatch_id,
                        attempt.generation,
                        attempt.prior_dispatch_id,
                    )
                    if expected != observed:
                        _fail("IDEMPOTENCY_CONFLICT", "Dispatch replay conflicts with its durable binding")
                    connection.execute("COMMIT")
                    return attempt
                connection.execute(
                    """INSERT INTO attempts(
                           dispatch_id,operation_id,project_id,run_id,task_id,task_key,provider_task_id,provider_dispatch_id,
                           worker_id,terminal_id,worktree_id,generation,state,prior_dispatch_id,authority_epoch
                       ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        dispatch_id,
                        operation_id,
                        project_id,
                        run_id,
                        task_id,
                        task_key,
                        provider_task_id,
                        provider_dispatch_id,
                        worker_id,
                        terminal_id,
                        worktree_id,
                        generation,
                        "ACTIVE",
                        prior_dispatch_id,
                        generation,
                    ),
                )
                row = connection.execute("SELECT * FROM attempts WHERE dispatch_id=?", (dispatch_id,)).fetchone()
                connection.execute("COMMIT")
                return self._attempt(row)
        except CoordinationError:
            raise
        except sqlite3.IntegrityError:
            _fail("IDEMPOTENCY_CONFLICT", "Dispatch identity is already bound")
        except sqlite3.Error:
            _fail("TRACE_INTEGRITY_FAILURE", "Dispatch binding could not be persisted")

    def attempt(self, dispatch_id: str) -> Attempt:
        _uuid(dispatch_id)
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM attempts WHERE dispatch_id=?", (dispatch_id,)).fetchone()
        if row is None:
            _fail("PRINCIPAL_UNAUTHORIZED", "Dispatch is not admitted")
        return self._attempt(row)

    def attempt_by_operation(self, operation_id: str) -> Attempt | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM attempts WHERE operation_id=?", (operation_id,)).fetchone()
        return self._attempt(row) if row is not None else None

    def attempts_for_run(self, run_id: str) -> tuple[Attempt, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM attempts WHERE run_id=? ORDER BY task_id,generation", (run_id,)
            ).fetchall()
        return tuple(self._attempt(row) for row in rows)

    def active_for_task(self, run_id: str, task_id: str) -> Attempt | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM attempts WHERE run_id=? AND task_id=? AND state='ACTIVE' ORDER BY generation DESC LIMIT 1",
                (run_id, task_id),
            ).fetchone()
        return self._attempt(row) if row is not None else None

    def fence(self, dispatch_id: str, *, reason: str) -> Attempt:
        if not isinstance(reason, str) or not reason:
            _fail("INVALID_INPUT", "Fence reason is required")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute("SELECT * FROM attempts WHERE dispatch_id=?", (dispatch_id,)).fetchone()
            if row is None:
                _fail("PRINCIPAL_UNAUTHORIZED", "Dispatch is not admitted")
            if row["state"] != "FENCED":
                connection.execute(
                    "UPDATE attempts SET state='FENCED',authority_epoch=authority_epoch+1 WHERE dispatch_id=?",
                    (dispatch_id,),
                )
            row = connection.execute("SELECT * FROM attempts WHERE dispatch_id=?", (dispatch_id,)).fetchone()
            connection.execute("COMMIT")
        return self._attempt(row)

    def mark_terminal(
        self,
        dispatch_id: str,
        *,
        state: str,
        evidence_digest: str,
        artifact_path: str | None = None,
        artifact_digest: str | None = None,
        artifact_content_ref: str | None = None,
    ) -> Attempt:
        if state not in {"TECHNICAL_COMPLETE", "FAILED", "CANCELLED"} or _HEX64.fullmatch(evidence_digest) is None:
            _fail("EVIDENCE_REQUIRED", "Terminal attempt evidence is invalid")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute("SELECT * FROM attempts WHERE dispatch_id=?", (dispatch_id,)).fetchone()
            if row is None:
                _fail("PRINCIPAL_UNAUTHORIZED", "Dispatch is not admitted")
            if row["state"] == "FENCED":
                _fail("STALE_ATTEMPT", "Fenced attempt cannot mutate semantic state")
            connection.execute(
                """UPDATE attempts SET state=?,artifact_path=?,artifact_digest=?,artifact_content_ref=?,evidence_digest=?
                   WHERE dispatch_id=?""",
                (state, artifact_path, artifact_digest, artifact_content_ref, evidence_digest, dispatch_id),
            )
            row = connection.execute("SELECT * FROM attempts WHERE dispatch_id=?", (dispatch_id,)).fetchone()
            connection.execute("COMMIT")
        return self._attempt(row)

    def record_message(
        self,
        *,
        message_id: str,
        operation_id: str,
        run_id: str,
        sender_id: str,
        recipient_id: str,
        kind: str,
        thread_id: str | None,
        reply_to: str | None,
        payload_digest: str,
        safe_summary: str,
        content_ref: str | None,
        provider: ProviderMessageResult,
    ) -> dict[str, Any]:
        if provider.outcome != "APPLIED" or provider.provider_message_id is None or provider.response_digest is None:
            _fail("PROVIDER_RESPONSE_INVALID", "Message provider receipt is incomplete")
        values = (_token(provider.provider_message_id), provider.response_digest)
        if _HEX64.fullmatch(values[1]) is None:
            _fail("PROVIDER_RESPONSE_INVALID", "Message response digest is invalid")
        try:
            with self._connect() as connection:
                connection.execute(
                    """INSERT INTO messages(
                           message_id,operation_id,run_id,sender_id,recipient_id,kind,thread_id,reply_to,
                           payload_digest,safe_summary,content_ref,provider_message_id,response_digest
                       ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        message_id,
                        operation_id,
                        run_id,
                        sender_id,
                        recipient_id,
                        kind,
                        thread_id,
                        reply_to,
                        payload_digest,
                        safe_summary,
                        content_ref,
                        values[0],
                        values[1],
                    ),
                )
        except sqlite3.IntegrityError:
            with self._connect() as connection:
                row = connection.execute("SELECT * FROM messages WHERE operation_id=?", (operation_id,)).fetchone()
            if row is None or row["message_id"] != message_id or row["payload_digest"] != payload_digest:
                _fail("IDEMPOTENCY_CONFLICT", "Message replay conflicts with its durable receipt")
            return dict(row)
        except sqlite3.Error:
            _fail("TRACE_INTEGRITY_FAILURE", "Message receipt could not be persisted")
        return self.message(message_id)

    def message(self, message_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM messages WHERE message_id=?", (message_id,)).fetchone()
        if row is None:
            _fail("MESSAGE_CORRELATION_INVALID", "Message correlation is unavailable")
        return dict(row)

    def message_by_operation(self, operation_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM messages WHERE operation_id=?", (operation_id,)).fetchone()
        return dict(row) if row is not None else None

    def messages_for_run(self, run_id: str) -> tuple[dict[str, Any], ...]:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM messages WHERE run_id=? ORDER BY rowid", (run_id,)).fetchall()
        return tuple(dict(row) for row in rows)

    def seal_episode(self, *, episode_id: str, run_id: str, manifest_digest: str, envelope: dict[str, Any]) -> dict[str, Any]:
        encoded = json.dumps(envelope, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        try:
            with self._connect() as connection:
                connection.execute(
                    "INSERT INTO episodes(episode_id,run_id,manifest_digest,envelope_json) VALUES(?,?,?,?)",
                    (episode_id, run_id, manifest_digest, encoded),
                )
        except sqlite3.IntegrityError:
            existing = self.episode(episode_id)
            if existing != envelope:
                _fail("IDEMPOTENCY_CONFLICT", "Sealed episode is immutable")
            return existing
        return envelope

    def episode(self, episode_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute("SELECT envelope_json FROM episodes WHERE episode_id=?", (episode_id,)).fetchone()
        if row is None:
            _fail("TRACE_INTEGRITY_FAILURE", "Episode is unavailable")
        value = json.loads(row["envelope_json"])
        if not isinstance(value, dict):
            _fail("TRACE_INTEGRITY_FAILURE", "Episode envelope is invalid")
        return value


class WorkerService:
    """Hermes-facing internal M4/M5 coordination service; not MCP-registered."""

    def __init__(
        self,
        *,
        lifecycle: LifecycleService,
        store: WorkerStore,
        provider: WorkerProvider,
        content_store: ProtectedContentStore | None,
    ) -> None:
        self.lifecycle = lifecycle
        self.store = store
        self.provider = provider
        self.content_store = content_store
        self.trace: TraceStore = lifecycle.foundation.trace

    def _run_manifest(self, project_id: str, run_id: str) -> tuple[RunBinding, Any]:
        binding = self.lifecycle.store.run(run_id, project_id=project_id)
        pending = self.lifecycle.store.pending_by_run(run_id)
        manifest = self.lifecycle.store.manifest(
            digest=pending.manifest_digest,
            manifest_ref=pending.manifest_ref,
            project_id=project_id,
        )
        return binding, manifest

    @staticmethod
    def _operation(args: dict[str, Any]) -> dict[str, Any]:
        operation = args["operation"]
        if not isinstance(operation, dict):
            _fail("INVALID_INPUT", "Operation is invalid")
        return operation

    @staticmethod
    def _task(binding: RunBinding, task_key: str) -> Any:
        for task in binding.tasks:
            if task.task_key == task_key:
                return task
        _fail("TASK_NOT_READY", "Task is not bound to this Run")

    @staticmethod
    def _task_spec(manifest: Any, task_key: str) -> dict[str, Any]:
        for task in manifest.canonical["tasks"]:
            if task["task_key"] == task_key:
                return task
        _fail("MANIFEST_INVALID", "Task contract is unavailable")

    @staticmethod
    def _attempt_public(attempt: Attempt) -> dict[str, Any]:
        return {
            "dispatch_id": attempt.dispatch_id,
            "task_id": attempt.task_id,
            "task_key": attempt.task_key,
            "generation": attempt.generation,
            "state": attempt.state,
            "provider_dispatch_id": attempt.provider_dispatch_id,
        }

    def _admit_provider_placement(self, *, project_id: str, worktree_id: str | None) -> None:
        if worktree_id is None or not worktree_id.startswith("path:"):
            return
        current = self.lifecycle.foundation.project_inspect({"project_id": project_id})
        admitted = self.lifecycle.foundation.admissions.admit(
            context=self.lifecycle.foundation.context,
            project_root=Path(worktree_id[5:]),
            safe_alias=current.safe_alias,
            capture_policy=current.capture_policy,
            consent_authority_ref=current.consent_authority_ref,
        )
        if admitted.project_id != project_id:
            _fail("PROJECT_IDENTITY_MISMATCH", "Worker placement resolved to another project")

    def _remove_provider_placement(self, *, project_id: str, worktree_id: str) -> None:
        if not worktree_id.startswith("path:"):
            return
        self.lifecycle.foundation.admissions.remove_placement(
            context=self.lifecycle.foundation.context,
            project_id=project_id,
            project_root=Path(worktree_id[5:]),
        )

    def _prepare(
        self,
        *,
        operation: dict[str, Any],
        capability: str,
        request_digest: str,
    ) -> tuple[bool, dict[str, Any]]:
        try:
            return self.trace.prepare_intent(
                operation_id=operation["operation_id"],
                project_id=operation["project_id"],
                capability=capability,
                request_digest=request_digest,
            )
        except Exception as exc:
            code = getattr(exc, "code", "TRACE_INTEGRITY_FAILURE")
            _fail(code, "Coordination intent could not be persisted")

    def _append_success(
        self,
        *,
        operation: dict[str, Any],
        capability: str,
        request_digest: str,
        response_digest: str,
        provider_request_id: str | None,
        resources: tuple[str, ...],
    ) -> None:
        self.trace.append_event(
            operation_id=operation["operation_id"],
            project_id=operation["project_id"],
            capability=capability,
            phase="RECEIPT",
            outcome="SUCCEEDED",
            request_digest=request_digest,
            response_digest=response_digest,
            provider_request_id=provider_request_id,
            resource_ids=resources,
        )

    def swarm_dispatch(self, arguments: dict[str, Any]) -> dict[str, Any]:
        try:
            args = validate_request("swarm_dispatch", arguments)
        except ProtocolError as exc:
            _fail(exc.code, "Dispatch request is invalid")
        operation = self._operation(args)
        if operation["expected_effect"] != "LOCAL_REVERSIBLE":
            _fail("EFFECT_NOT_AUTHORIZED", "Dispatch requires local reversible authority")
        binding, manifest = self._run_manifest(operation["project_id"], args["run_id"])
        if operation["contract_id"] != manifest.canonical["contract"]["contract_id"]:
            _fail("CONTRACT_STALE", "Dispatch contract differs from the Run")
        request_digest = canonical_request_digest("swarm_dispatch", args)
        if self.trace.records_for(operation["operation_id"]):
            prepared, _latest = self._prepare(
                operation=operation, capability="swarm_dispatch", request_digest=request_digest
            )
            if prepared:
                _fail("TRACE_INTEGRITY_FAILURE", "Existing Dispatch unexpectedly prepared as new")
            attempts = [
                attempt
                for attempt in self.store.attempts_for_run(binding.run_id)
                if attempt.operation_id == operation["operation_id"]
            ]
            if not attempts:
                _fail("EFFECT_UNKNOWN", "Dispatch replay has no durable provider correlation")
            return {
                "outcome": "DISPATCHED",
                "replayed": True,
                "dispatches": [self._attempt_public(item) for item in attempts],
            }
        task_keys = tuple(args["task_keys"])
        status = self.lifecycle.swarm_status(
            {
                "project_id": operation["project_id"],
                "run_id": args["run_id"],
                "cursor": None,
                "wait_ms": 0,
                "detail": "tasks",
            }
        )
        status_by_key = {task["task_key"]: task["status"] for task in status["tasks"]}
        selected: list[tuple[Any, dict[str, Any]]] = []
        for task_key in task_keys:
            task = self._task(binding, task_key)
            spec = self._task_spec(manifest, task_key)
            if spec["archetype"] != "fixture" or status_by_key.get(task_key) != "ready":
                _fail("TASK_NOT_READY", "Only a ready deterministic fixture Task may dispatch")
            if self.store.active_for_task(binding.run_id, task.task_id) is not None:
                _fail("TASK_NOT_READY", "Task already has an active attempt")
            selected.append((task, spec))
        scopes: list[str] = []
        for active in self.store.attempts_for_run(binding.run_id):
            if active.state != "ACTIVE":
                continue
            active_spec = self._task_spec(manifest, active.task_key)
            scopes.extend(active_spec["write_scope"])
        for _task, spec in selected:
            for scope in spec["write_scope"]:
                if any(scope == prior or scope.startswith(prior + "/") or prior.startswith(scope + "/") for prior in scopes):
                    _fail("WRITE_SCOPE_CONFLICT", "Selected Tasks have conflicting write authority")
                scopes.append(scope)
        prepared, _latest = self._prepare(operation=operation, capability="swarm_dispatch", request_digest=request_digest)
        if not prepared:
            attempts = [attempt for attempt in self.store.attempts_for_run(binding.run_id) if attempt.operation_id == operation["operation_id"]]
            if not attempts:
                _fail("EFFECT_UNKNOWN", "Dispatch replay has no durable provider correlation")
            return {"outcome": "DISPATCHED", "replayed": True, "dispatches": [self._attempt_public(item) for item in attempts]}
        created: list[Attempt] = []
        response_digests: list[str] = []
        provider_requests: list[str] = []
        for index, (task, spec) in enumerate(selected):
            logical_id = _dispatch_id(operation["operation_id"] if len(selected) == 1 else f"{operation['operation_id']}:{index}")
            result = self.provider.dispatch_fixture(
                provider_run_id=binding.provider_run_id,
                provider_task_id=task.provider_task_id,
                logical_dispatch_id=logical_id,
                task_spec=spec,
                attempt_generation=1,
            )
            if result.outcome != "APPLIED" or result.response_digest is None or _HEX64.fullmatch(result.response_digest) is None:
                self.trace.append_event(
                    operation_id=operation["operation_id"],
                    project_id=operation["project_id"],
                    capability="swarm_dispatch",
                    phase="RECEIPT",
                    outcome="UNKNOWN",
                    request_digest=request_digest,
                    error_code="DELIVERY_UNKNOWN",
                )
                return {"outcome": "UNKNOWN", "replayed": False, "dispatches": [self._attempt_public(item) for item in created]}
            self._admit_provider_placement(
                project_id=operation["project_id"], worktree_id=result.worktree_id
            )
            attempt = self.store.bind_attempt(
                dispatch_id=logical_id,
                operation_id=operation["operation_id"] if len(selected) == 1 else str(uuid.uuid5(_UUID_NAMESPACE, f"{operation['operation_id']}:{index}")),
                project_id=operation["project_id"],
                run_id=binding.run_id,
                task_id=task.task_id,
                task_key=task.task_key,
                provider_task_id=task.provider_task_id,
                provider=result,
                generation=1,
                prior_dispatch_id=None,
            )
            created.append(attempt)
            response_digests.append(result.response_digest)
            if result.provider_request_id:
                provider_requests.append(result.provider_request_id)
        response_digest = _digest(response_digests)
        self._append_success(
            operation=operation,
            capability="swarm_dispatch",
            request_digest=request_digest,
            response_digest=response_digest,
            provider_request_id=provider_requests[0] if len(provider_requests) == 1 else None,
            resources=tuple(item.provider_dispatch_id for item in created),
        )
        return {"outcome": "DISPATCHED", "replayed": False, "dispatches": [self._attempt_public(item) for item in created]}

    def _participant(self, run_id: str, identity: str) -> Attempt | None:
        if identity == "coordinator":
            return None
        try:
            parsed = uuid.UUID(identity)
        except (ValueError, TypeError, AttributeError):
            _fail("PRINCIPAL_UNAUTHORIZED", "Participant is not an admitted Dispatch")
        if str(parsed) != identity:
            _fail("PRINCIPAL_UNAUTHORIZED", "Participant is not an admitted Dispatch")
        attempt = self.store.attempt(identity)
        if attempt.run_id != run_id:
            _fail("PRINCIPAL_UNAUTHORIZED", "Participant belongs to another Run")
        if attempt.state == "FENCED":
            _fail("STALE_ATTEMPT", "Fenced participant lost message authority")
        return attempt

    @staticmethod
    def _payload(value: str) -> dict[str, Any]:
        try:
            payload = json.loads(value)
        except json.JSONDecodeError:
            _fail("MESSAGE_CORRELATION_INVALID", "Worker message payload must be structured JSON")
        if not isinstance(payload, dict):
            _fail("MESSAGE_CORRELATION_INVALID", "Worker message payload must be an object")
        return payload

    def _artifact(
        self,
        *,
        project_id: str,
        manifest: Any,
        attempt: Attempt,
        payload: dict[str, Any],
    ) -> tuple[str, str, str | None, str]:
        artifact_path = payload.get("artifact_path")
        artifact_digest = payload.get("artifact_digest")
        evidence_digest = payload.get("evidence_digest")
        if (
            not isinstance(artifact_path, str)
            or not isinstance(artifact_digest, str)
            or _HEX64.fullmatch(artifact_digest) is None
            or not isinstance(evidence_digest, str)
            or _HEX64.fullmatch(evidence_digest) is None
        ):
            _fail("EVIDENCE_REQUIRED", "Completion requires artifact and evidence digests")
        spec = self._task_spec(manifest, attempt.task_key)
        if not any(
            artifact_path == scope or artifact_path.startswith(scope.rstrip("/") + "/")
            for scope in spec["write_scope"]
        ):
            _fail("WRITE_SCOPE_VIOLATION", "Artifact is outside the admitted write scope")
        project = self.lifecycle.foundation.project_inspect({"project_id": project_id})
        placement_ref = payload.get("worktree_id")
        if placement_ref is None:
            root = project.project_root
        else:
            if (
                not isinstance(placement_ref, str)
                or placement_ref != attempt.worktree_id
                or not placement_ref.startswith("path:")
            ):
                _fail("WRITE_SCOPE_VIOLATION", "Artifact placement does not match its Dispatch")
            matches = [
                placement.project_root
                for placement in project.placements
                if str(placement.project_root) == placement_ref[5:]
            ]
            if len(matches) != 1:
                _fail("PROJECT_IDENTITY_MISMATCH", "Worker placement is not currently admitted")
            root = matches[0]
        target = root / artifact_path
        try:
            resolved = target.resolve(strict=True)
        except OSError:
            _fail("EVIDENCE_REQUIRED", "Artifact is unavailable")
        if target.is_symlink() or not resolved.is_relative_to(root) or not resolved.is_file():
            _fail("WRITE_SCOPE_VIOLATION", "Artifact path is unsafe")
        body = resolved.read_bytes()
        if hashlib.sha256(body).hexdigest() != artifact_digest:
            _fail("EVIDENCE_REQUIRED", "Artifact digest does not match current bytes")
        content_ref: str | None = None
        if project.capture_policy == "FULL_EPISODE":
            if self.content_store is None:
                _fail("CAPTURE_DISABLED", "Full episode capture store is unavailable")
            content_ref = self.content_store.put(
                project_id=project_id,
                content_type="artifact_excerpt",
                payload=body,
                capture_policy="FULL_EPISODE",
            ).content_ref
        return artifact_path, artifact_digest, content_ref, evidence_digest

    def swarm_message(self, arguments: dict[str, Any]) -> dict[str, Any]:
        try:
            args = validate_request("swarm_message", arguments)
        except ProtocolError as exc:
            _fail(exc.code, "Message request is invalid")
        operation = self._operation(args)
        binding, manifest = self._run_manifest(operation["project_id"], args["run_id"])
        if operation["contract_id"] != manifest.canonical["contract"]["contract_id"]:
            _fail("CONTRACT_STALE", "Message contract differs from the Run")
        sender = self._participant(binding.run_id, args["sender_id"])
        recipient = self._participant(binding.run_id, args["recipient_id"])
        kind = args["kind"]
        payload = self._payload(args["payload"])
        provider_reply_to: str | None = None
        if kind == "technical_question":
            if (
                sender is None
                or (recipient is not None and recipient.dispatch_id == sender.dispatch_id)
                or not args["decision_required"]
                or args["blocking_effect"] is None
            ):
                _fail("MESSAGE_CORRELATION_INVALID", "Technical question direction or gate is invalid")
        elif kind == "reply":
            if sender is not None or recipient is None:
                _fail("MESSAGE_CORRELATION_INVALID", "Reply direction is invalid")
            reply_to = payload.get("reply_to")
            thread_id = payload.get("thread_id")
            if not isinstance(reply_to, str) or not isinstance(thread_id, str):
                _fail("MESSAGE_CORRELATION_INVALID", "Reply correlation is incomplete")
            question = self.store.message(reply_to)
            if question["kind"] != "technical_question" or question["thread_id"] != thread_id or question["sender_id"] != recipient.dispatch_id:
                _fail("MESSAGE_CORRELATION_INVALID", "Reply does not match its question")
            provider_reply_to = question["provider_message_id"]
        elif kind == "dependency_handoff":
            if sender is None or recipient is None or sender.dispatch_id == recipient.dispatch_id:
                _fail("MESSAGE_CORRELATION_INVALID", "Dependency handoff requires two distinct admitted Dispatches")
            artifact_digest = payload.get("artifact_digest")
            evidence_digest = payload.get("evidence_digest")
            if (
                sender.state != "TECHNICAL_COMPLETE"
                or sender.artifact_digest is None
                or sender.evidence_digest is None
                or artifact_digest != sender.artifact_digest
                or evidence_digest != sender.evidence_digest
            ):
                _fail("EVIDENCE_REQUIRED", "Dependency handoff lacks immutable predecessor evidence")
            reply_to = payload.get("reply_to")
            if reply_to is None:
                _fail("MESSAGE_CORRELATION_INVALID", "Dependency handoff requires a peer question correlation")
            question = self.store.message(reply_to)
            if (
                question["kind"] != "technical_question"
                or question["sender_id"] != recipient.dispatch_id
                or question["recipient_id"] != sender.dispatch_id
            ):
                _fail("MESSAGE_CORRELATION_INVALID", "Handoff does not answer the peer's question")
            provider_reply_to = question["provider_message_id"]
        elif sender is None and recipient is None:
            _fail("PRINCIPAL_UNAUTHORIZED", "Coordinator cannot message itself through worker routing")
        if kind in {"progress", "artifact_reference", "completion_reference", "finding", "blocker"} and sender is None:
            _fail("PRINCIPAL_UNAUTHORIZED", "Worker-originated message has no worker sender")
        if kind in {"steering", "reply"} and recipient is None:
            _fail("PRINCIPAL_UNAUTHORIZED", "Coordinator guidance has no worker recipient")
        thread_id = payload.get("thread_id") if isinstance(payload.get("thread_id"), str) else None
        reply_to = payload.get("reply_to") if isinstance(payload.get("reply_to"), str) else None
        request_digest = canonical_request_digest("swarm_message", args)
        prepared, _latest = self._prepare(operation=operation, capability="swarm_message", request_digest=request_digest)
        message_id = _message_id(operation["operation_id"])
        if not prepared:
            existing = self.store.message_by_operation(operation["operation_id"])
            if existing is None:
                _fail("EFFECT_UNKNOWN", "Message replay has no durable provider receipt")
            outcome = "TECHNICALLY_COMPLETED" if kind == "completion_reference" else "SENT"
            return {"outcome": outcome, "message_id": existing["message_id"], "replayed": True}
        project = self.lifecycle.foundation.project_inspect({"project_id": operation["project_id"]})
        content_ref: str | None = None
        if project.capture_policy == "FULL_EPISODE":
            if self.content_store is None:
                _fail("CAPTURE_DISABLED", "Full episode capture store is unavailable")
            content_ref = self.content_store.put(
                project_id=operation["project_id"],
                content_type="worker_message",
                payload=args["payload"].encode(),
                capture_policy="FULL_EPISODE",
            ).content_ref
        outcome = payload.get("outcome") if kind == "completion_reference" else None
        if outcome is not None and outcome not in {"SUCCEEDED", "FAILED"}:
            _fail("INVALID_INPUT", "Worker completion outcome is invalid")
        provider_attempt = sender or recipient
        if provider_attempt is None:
            _fail("PRINCIPAL_UNAUTHORIZED", "Worker routing lacks a Dispatch")
        artifact_result: tuple[str, str, str | None, str] | None = None
        if kind == "completion_reference":
            artifact_result = self._artifact(
                project_id=operation["project_id"], manifest=manifest, attempt=provider_attempt, payload=payload
            )
        provider_result = self.provider.send_worker_message(
            provider_run_id=binding.provider_run_id,
            provider_task_id=provider_attempt.provider_task_id,
            provider_dispatch_id=provider_attempt.provider_dispatch_id,
            terminal_id=provider_attempt.terminal_id,
            from_coordinator=sender is None,
            kind=kind,
            payload=payload,
            outcome=outcome,
            provider_reply_to=provider_reply_to,
        )
        if provider_result.outcome != "APPLIED" or provider_result.response_digest is None:
            self.trace.append_event(
                operation_id=operation["operation_id"],
                project_id=operation["project_id"],
                capability="swarm_message",
                phase="RECEIPT",
                outcome="UNKNOWN",
                request_digest=request_digest,
                error_code="DELIVERY_UNKNOWN",
            )
            return {"outcome": "UNKNOWN", "message_id": message_id, "replayed": False}
        self.store.record_message(
            message_id=message_id,
            operation_id=operation["operation_id"],
            run_id=binding.run_id,
            sender_id=args["sender_id"],
            recipient_id=args["recipient_id"],
            kind=kind,
            thread_id=thread_id,
            reply_to=reply_to,
            payload_digest=hashlib.sha256(args["payload"].encode()).hexdigest(),
            safe_summary=args["safe_summary"],
            content_ref=content_ref,
            provider=provider_result,
        )
        public_outcome = "SENT"
        if kind == "completion_reference":
            if artifact_result is None:
                _fail("EVIDENCE_REQUIRED", "Completion artifact validation was not preserved")
            artifact_path, artifact_digest, artifact_content_ref, evidence_digest = artifact_result
            terminal_state = "TECHNICAL_COMPLETE" if outcome == "SUCCEEDED" else "FAILED"
            self.store.mark_terminal(
                provider_attempt.dispatch_id,
                state=terminal_state,
                evidence_digest=evidence_digest,
                artifact_path=artifact_path,
                artifact_digest=artifact_digest,
                artifact_content_ref=artifact_content_ref,
            )
            public_outcome = "TECHNICALLY_COMPLETED"
        self._append_success(
            operation=operation,
            capability="swarm_message",
            request_digest=request_digest,
            response_digest=provider_result.response_digest,
            provider_request_id=provider_result.provider_message_id,
            resources=(provider_attempt.provider_dispatch_id,),
        )
        return {"outcome": public_outcome, "message_id": message_id, "replayed": False}

    def swarm_retry(self, arguments: dict[str, Any]) -> dict[str, Any]:
        try:
            args = validate_request("swarm_retry", arguments)
        except ProtocolError as exc:
            _fail(exc.code, "Retry request is invalid")
        operation = self._operation(args)
        binding, manifest = self._run_manifest(operation["project_id"], args["run_id"])
        prior = self.store.attempt(args["dispatch_id"])
        if prior.run_id != binding.run_id or prior.task_id != args["task_id"]:
            _fail("IDEMPOTENCY_CONFLICT", "Retry target does not match its Run and Task")
        expected_state = {"FAILED": "FAILED", "CANCELLED": "CANCELLED"}.get(args["prior_outcome"])
        if expected_state is None or prior.state != expected_state:
            _fail("RETRY_FORBIDDEN", "Retry requires matching terminal evidence")
        spec = self._task_spec(manifest, prior.task_key)
        attempts = [item for item in self.store.attempts_for_run(binding.run_id) if item.task_id == prior.task_id]
        if len(attempts) >= spec["attempt_budget"]:
            _fail("RETRY_BUDGET_EXHAUSTED", "Task attempt budget is exhausted")
        if args["contract_generation"] not in {None, manifest.canonical["contract"]["generation"]}:
            _fail("CONTRACT_STALE", "Retry contract generation is stale")
        request_digest = canonical_request_digest("swarm_retry", args)
        prepared, _latest = self._prepare(operation=operation, capability="swarm_retry", request_digest=request_digest)
        if not prepared:
            existing = self.store.attempt_by_operation(operation["operation_id"])
            if existing is None:
                _fail("EFFECT_UNKNOWN", "Retry replay has no durable Dispatch")
            return {**self._attempt_public(existing), "outcome": "DISPATCHED", "replayed": True}
        self.store.fence(prior.dispatch_id, reason=args["correction_summary"])
        logical_id = _dispatch_id(operation["operation_id"])
        result = self.provider.retry_fixture(
            provider_run_id=binding.provider_run_id,
            provider_task_id=self._task(binding, prior.task_key).provider_task_id,
            prior_provider_dispatch_id=prior.provider_dispatch_id,
            logical_dispatch_id=logical_id,
            task_spec=spec,
            attempt_generation=prior.generation + 1,
        )
        if result.outcome != "APPLIED" or result.response_digest is None:
            self.trace.append_event(
                operation_id=operation["operation_id"],
                project_id=operation["project_id"],
                capability="swarm_retry",
                phase="RECEIPT",
                outcome="UNKNOWN",
                request_digest=request_digest,
                error_code="DELIVERY_UNKNOWN",
            )
            return {"outcome": "UNKNOWN", "dispatch_id": logical_id, "replayed": False}
        self._admit_provider_placement(
            project_id=operation["project_id"], worktree_id=result.worktree_id
        )
        attempt = self.store.bind_attempt(
            dispatch_id=logical_id,
            operation_id=operation["operation_id"],
            project_id=operation["project_id"],
            run_id=binding.run_id,
            task_id=prior.task_id,
            task_key=prior.task_key,
            provider_task_id=prior.provider_task_id,
            provider=result,
            generation=prior.generation + 1,
            prior_dispatch_id=prior.dispatch_id,
        )
        self._append_success(
            operation=operation,
            capability="swarm_retry",
            request_digest=request_digest,
            response_digest=result.response_digest,
            provider_request_id=result.provider_request_id,
            resources=(attempt.provider_dispatch_id,),
        )
        return {**self._attempt_public(attempt), "outcome": "DISPATCHED", "replayed": False}

    def swarm_cancel(self, arguments: dict[str, Any]) -> dict[str, Any]:
        try:
            args = validate_request("swarm_cancel", arguments)
        except ProtocolError as exc:
            _fail(exc.code, "Cancel request is invalid")
        if args["target_type"] != "dispatch":
            return self.lifecycle.swarm_cancel(arguments)
        operation = self._operation(args)
        binding, _manifest = self._run_manifest(operation["project_id"], args["run_id"])
        attempt = self.store.attempt(args["target_id"])
        if attempt.run_id != binding.run_id:
            _fail("PRINCIPAL_UNAUTHORIZED", "Dispatch belongs to another Run")
        request_digest = canonical_request_digest("swarm_cancel", args)
        prepared, _latest = self._prepare(operation=operation, capability="swarm_cancel", request_digest=request_digest)
        if not prepared:
            return {"outcome": "CANCELLED", "replayed": True, "resource_ids": []}
        result = self.provider.stop_worker(
            provider_run_id=binding.provider_run_id,
            provider_dispatch_id=attempt.provider_dispatch_id,
            terminal_id=attempt.terminal_id,
            worktree_id=attempt.worktree_id,
        )
        if result.outcome != "APPLIED" or result.response_digest is None:
            self.trace.append_event(
                operation_id=operation["operation_id"],
                project_id=operation["project_id"],
                capability="swarm_cancel",
                phase="RECEIPT",
                outcome="UNKNOWN",
                request_digest=request_digest,
                error_code="DELIVERY_UNKNOWN",
            )
            return {"outcome": "UNKNOWN", "replayed": False, "resource_ids": []}
        self.store.fence(attempt.dispatch_id, reason="cancelled by admitted coordinator")
        self._append_success(
            operation=operation,
            capability="swarm_cancel",
            request_digest=request_digest,
            response_digest=result.response_digest,
            provider_request_id=result.provider_request_id,
            resources=(attempt.provider_dispatch_id,),
        )
        return {"outcome": "CANCELLED", "replayed": False, "resource_ids": list(result.resource_ids)}

    def integrate_artifacts(
        self,
        *,
        run_id: str,
        output_path: str,
        component_dispatch_ids: tuple[str, ...],
    ) -> dict[str, Any]:
        """Integrate verified worker JSON artifacts in coordinator-owned scope."""

        _uuid(run_id)
        if (
            not isinstance(output_path, str)
            or not output_path.startswith("integration/")
            or output_path.startswith("/")
            or ".." in Path(output_path).parts
            or len(component_dispatch_ids) < 2
            or len(set(component_dispatch_ids)) != len(component_dispatch_ids)
        ):
            _fail("INVALID_INPUT", "Coordinator integration request is invalid")
        attempts = tuple(self.store.attempt(value) for value in component_dispatch_ids)
        if any(attempt.run_id != run_id for attempt in attempts):
            _fail("PRINCIPAL_UNAUTHORIZED", "Integration component belongs to another Run")
        if any(
            attempt.state != "TECHNICAL_COMPLETE"
            or attempt.artifact_path is None
            or attempt.artifact_digest is None
            or attempt.evidence_digest is None
            for attempt in attempts
        ):
            _fail("EVIDENCE_REQUIRED", "Every integrated component requires successful immutable evidence")
        project_id = attempts[0].project_id
        _binding, manifest = self._run_manifest(project_id, run_id)
        for task in manifest.canonical["tasks"]:
            for scope in task["write_scope"]:
                if output_path == scope or output_path.startswith(scope.rstrip("/") + "/"):
                    _fail("WRITE_SCOPE_CONFLICT", "Coordinator integration overlaps worker write authority")
        project = self.lifecycle.foundation.project_inspect({"project_id": project_id})
        components: list[dict[str, Any]] = []
        for attempt in sorted(attempts, key=lambda value: value.task_key):
            artifact_path = attempt.artifact_path
            if artifact_path is None:
                _fail("EVIDENCE_REQUIRED", "Integration component lacks an artifact path")
            root = project.project_root
            if attempt.worktree_id.startswith("path:"):
                matches = [
                    placement.project_root
                    for placement in project.placements
                    if str(placement.project_root) == attempt.worktree_id[5:]
                ]
                if len(matches) != 1:
                    _fail("PROJECT_IDENTITY_MISMATCH", "Integration placement is unavailable")
                root = matches[0]
            target = root / artifact_path
            try:
                resolved = target.resolve(strict=True)
                body = resolved.read_bytes()
                decoded = json.loads(body)
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                _fail("EVIDENCE_REQUIRED", "Integration component is unavailable or malformed")
            if target.is_symlink() or not resolved.is_relative_to(root):
                _fail("WRITE_SCOPE_VIOLATION", "Integration component path is unsafe")
            if hashlib.sha256(body).hexdigest() != attempt.artifact_digest:
                _fail("EVIDENCE_REQUIRED", "Integration component changed after validation")
            components.append(
                {
                    "artifact_digest": attempt.artifact_digest,
                    "dispatch_id": attempt.dispatch_id,
                    "evidence_digest": attempt.evidence_digest,
                    "output": decoded,
                    "task_key": attempt.task_key,
                }
            )
        envelope = {
            "schema_version": "aether.integration/v1alpha1",
            "run_id": run_id,
            "components": components,
        }
        body = (json.dumps(envelope, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode()
        destination = project.project_root / output_path
        destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        if destination.is_symlink():
            _fail("WRITE_SCOPE_VIOLATION", "Integration destination is unsafe")
        temporary = destination.with_name(f".{destination.name}.{uuid.uuid4()}.tmp")
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(body)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, destination)
        finally:
            if temporary.exists():
                temporary.unlink()
        return {
            "artifact_path": output_path,
            "artifact_digest": hashlib.sha256(body).hexdigest(),
            "component_digests": sorted(attempt.artifact_digest for attempt in attempts if attempt.artifact_digest),
            "component_count": len(components),
        }

    def swarm_close(self, arguments: dict[str, Any]) -> dict[str, Any]:
        try:
            args = validate_request("swarm_close", arguments)
        except ProtocolError as exc:
            _fail(exc.code, "Close request is invalid")
        operation = self._operation(args)
        binding, _manifest = self._run_manifest(operation["project_id"], args["run_id"])
        attempts = self.store.attempts_for_run(binding.run_id)
        if any(attempt.state == "ACTIVE" for attempt in attempts):
            _fail("CLEANUP_INCOMPLETE", "Run still has an active worker attempt")
        status = self.lifecycle.swarm_status(
            {
                "project_id": operation["project_id"],
                "run_id": binding.run_id,
                "cursor": None,
                "wait_ms": 0,
                "detail": "resources",
            }
        )
        if any(task["status"] not in {"completed", "failed", "blocked"} for task in status["tasks"]):
            _fail("CLEANUP_INCOMPLETE", "Run still has a non-terminal provider Task")
        request_digest = canonical_request_digest("swarm_close", args)
        prepared, latest = self._prepare(operation=operation, capability="swarm_close", request_digest=request_digest)
        if not prepared:
            return {
                "outcome": "CLOSED" if latest["outcome"] == "SUCCEEDED" else "CLEANUP_FAILED",
                "replayed": True,
                "survivors": latest["resource_ids"],
            }
        digests: list[str] = []
        survivors: list[str] = []
        for attempt in attempts:
            self._remove_provider_placement(
                project_id=operation["project_id"], worktree_id=attempt.worktree_id
            )
            result = self.provider.cleanup_worker(
                provider_dispatch_id=attempt.provider_dispatch_id,
                terminal_id=attempt.terminal_id,
                worktree_id=attempt.worktree_id,
            )
            if result.response_digest:
                digests.append(result.response_digest)
            if result.outcome != "APPLIED" or not result.cleanup_complete or result.resource_ids:
                survivors.extend(result.resource_ids or (attempt.provider_dispatch_id, attempt.terminal_id, attempt.worktree_id))
        provider_close = self.provider.close(
            provider_run_id=binding.provider_run_id,
            effect_plan=tuple(args["effect_plan"]),
        )
        if provider_close.response_digest:
            digests.append(provider_close.response_digest)
        if provider_close.outcome != "APPLIED" or not provider_close.cleanup_complete or provider_close.resource_ids:
            survivors.extend(provider_close.resource_ids)
        resources = tuple(dict.fromkeys(survivors))
        succeeded = not resources
        self.trace.append_event(
            operation_id=operation["operation_id"],
            project_id=operation["project_id"],
            capability="swarm_close",
            phase="RECEIPT",
            outcome="SUCCEEDED" if succeeded else "FAILED",
            request_digest=request_digest,
            response_digest=_digest(digests),
            resource_ids=resources,
            error_code=None if succeeded else "CLEANUP_INCOMPLETE",
        )
        if succeeded:
            self.lifecycle.store.mark_closed(binding.run_id, project_id=operation["project_id"])
        return {
            "outcome": "CLOSED" if succeeded else "CLEANUP_FAILED",
            "replayed": False,
            "survivors": list(resources),
        }

    def seal_episode(self, *, run_id: str, final_state_digest: str, labels: tuple[str, ...]) -> dict[str, Any]:
        _uuid(run_id)
        if _HEX64.fullmatch(final_state_digest) is None or not labels:
            _fail("INVALID_INPUT", "Episode close evidence is invalid")
        attempts = self.store.attempts_for_run(run_id)
        if not attempts:
            _fail("EVIDENCE_REQUIRED", "Episode has no worker attempt")
        project_id = attempts[0].project_id
        binding, manifest = self._run_manifest(project_id, run_id)
        if binding.semantic_state != "CLOSED":
            _fail("RUN_NOT_CLOSED", "Episode can seal only after semantic close")
        if any(attempt.state == "ACTIVE" for attempt in attempts):
            _fail("RUN_NOT_CLOSED", "Episode has an active attempt")
        if any(attempt.state == "TECHNICAL_COMPLETE" and not attempt.artifact_content_ref for attempt in attempts):
            _fail("EVIDENCE_REQUIRED", "Completed attempt has no captured artifact")
        project = self.lifecycle.foundation.project_inspect({"project_id": project_id})
        if project.capture_policy != "FULL_EPISODE" or self.content_store is None:
            _fail("CAPTURE_DISABLED", "Complete episode capture is not admitted")
        messages = self.store.messages_for_run(run_id)
        content_refs = sorted(
            {
                value
                for value in [
                    *(message["content_ref"] for message in messages),
                    *(attempt.artifact_content_ref for attempt in attempts),
                ]
                if value
            }
        )
        episode_id = _episode_id(run_id)
        envelope = {
            "schema_version": "aether.learning-episode/v1alpha1",
            "episode_id": episode_id,
            "project_id": project_id,
            "aether_run_id": run_id,
            "contract_id": manifest.canonical["contract"]["contract_id"],
            "contract_generation": manifest.canonical["contract"]["generation"],
            "capture_policy": "FULL_EPISODE",
            "capture_policy_generation": 1,
            "purpose": list(manifest.canonical["learning"]["purpose"]),
            "consent_authority_ref": manifest.canonical["learning"]["consent_authority_ref"],
            "capture_complete": True,
            "capture_gaps": [],
            "final_state_digest": final_state_digest,
            "attempts": [self._attempt_public(attempt) for attempt in attempts],
            "messages": [
                {key: message[key] for key in ("message_id", "sender_id", "recipient_id", "kind", "content_ref")}
                for message in messages
            ],
            "content_refs": content_refs,
            "labels": list(labels),
        }
        envelope["episode_manifest_digest"] = _digest(envelope)
        return self.store.seal_episode(
            episode_id=episode_id,
            run_id=run_id,
            manifest_digest=envelope["episode_manifest_digest"],
            envelope=envelope,
        )


    def replay_episode(self, episode_id: str) -> dict[str, Any]:
        if self.content_store is None:
            _fail("CAPTURE_DISABLED", "Episode content store is unavailable")
        envelope = self.store.episode(episode_id)
        replayed: list[str] = []
        for content_ref in envelope["content_refs"]:
            replayed.append(
                self.content_store.get(project_id=envelope["project_id"], content_ref=content_ref).decode("utf-8")
            )
        return {"episode": envelope, "replayed_content": replayed}
