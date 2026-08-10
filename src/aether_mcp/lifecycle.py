"""Manifest-bound M3 lifecycle control without worker dispatch.

Aether owns immutable contract/correlation facts and semantic closure. Orca remains
the sole authority for mutable Run, Task, terminal and resource state.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, NoReturn, Protocol

from .foundation import M2Foundation
from .manifest import ValidatedManifest, validate_swarm_manifest
from .protocol import ProtocolError, canonical_request_digest, validate_request
from .trace_store import StoreError

_NAMESPACE = uuid.UUID("7f4aaf53-7b89-4e1f-b66d-8fb413c7e09e")
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,511}$")
_RUN_STATUSES = {"running", "terminal", "unknown"}
_TASK_STATUSES = {"pending", "ready", "dispatched", "completed", "failed", "cancelled", "blocked", "unknown"}
_TERMINAL_TASK_STATUSES = {"completed", "failed", "cancelled", "blocked"}


class LifecycleError(RuntimeError):
    """Stable lifecycle failure without provider prose."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _fail(code: str, message: str) -> NoReturn:
    raise LifecycleError(code, message)


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()
    except (TypeError, ValueError):
        _fail("TRACE_INTEGRITY_FAILURE", "Lifecycle value is not canonical JSON")


def _uuid(value: str, *, code: str = "PROVIDER_RESPONSE_INVALID") -> str:
    try:
        parsed = uuid.UUID(value)
    except (TypeError, ValueError, AttributeError):
        _fail(code, "Lifecycle identity is invalid")
    if str(parsed) != value:
        _fail(code, "Lifecycle identity is not canonical")
    return value


def _token(value: str | None, *, code: str = "PROVIDER_RESPONSE_INVALID") -> str | None:
    if value is not None and (not isinstance(value, str) or _TOKEN_RE.fullmatch(value) is None):
        _fail(code, "Provider identity is invalid")
    return value


def _digest(value: str | None, *, code: str = "PROVIDER_RESPONSE_INVALID") -> str | None:
    if value is not None and (not isinstance(value, str) or _DIGEST_RE.fullmatch(value) is None):
        _fail(code, "Provider digest is invalid")
    return value


def _logical_run_id(operation_id: str) -> str:
    return str(uuid.uuid5(_NAMESPACE, f"run:{operation_id}"))


def _logical_task_id(run_id: str, task_key: str) -> str:
    return str(uuid.uuid5(_NAMESPACE, f"task:{run_id}:{task_key}"))


@dataclass(frozen=True)
class ProviderTaskProjection:
    task_key: str
    provider_task_id: str
    status: str


@dataclass(frozen=True)
class ProviderRunProjection:
    provider_run_id: str
    status: str
    tasks: tuple[ProviderTaskProjection, ...]
    live_resource_ids: tuple[str, ...]
    coordinator_generation: int
    source: str


@dataclass(frozen=True)
class ProviderStartResult:
    outcome: str
    provider_request_id: str | None
    provider_run_id: str | None
    provider_tasks: tuple[tuple[str, str], ...]
    response_digest: str | None


@dataclass(frozen=True)
class ProviderEffectResult:
    outcome: str
    provider_request_id: str | None
    resource_ids: tuple[str, ...]
    response_digest: str | None
    cleanup_complete: bool


class LifecycleProvider(Protocol):
    binding_digest: str

    def start_no_dispatch(
        self,
        *,
        operation_id: str,
        logical_run_id: str,
        manifest: ValidatedManifest,
    ) -> ProviderStartResult: ...

    def inspect_run(self, *, provider_run_id: str) -> ProviderRunProjection: ...

    def reconcile_start(self, *, operation_id: str, logical_run_id: str) -> ProviderStartResult | None: ...

    def cancel(self, *, provider_run_id: str, target_type: str, provider_target_id: str) -> ProviderEffectResult: ...

    def close(self, *, provider_run_id: str, effect_plan: tuple[str, ...]) -> ProviderEffectResult: ...


@dataclass(frozen=True)
class TaskBinding:
    task_id: str
    task_key: str
    provider_task_id: str


@dataclass(frozen=True)
class RunBinding:
    run_id: str
    project_id: str
    operation_id: str
    manifest_digest: str
    provider_run_id: str
    coordinator_generation: int
    tasks: tuple[TaskBinding, ...]
    semantic_state: str


@dataclass(frozen=True)
class StartIntent:
    operation_id: str
    project_id: str
    logical_run_id: str
    manifest_digest: str
    manifest_ref: str
    request_digest: str


class LifecycleStore:
    """SQLite authority for immutable manifests and logical/provider correlations."""

    def __init__(self, root: Path) -> None:
        if root.is_symlink():
            _fail("TRACE_INTEGRITY_FAILURE", "Lifecycle root cannot be a symlink")
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(root, 0o700)
        self.root = root.resolve(strict=True)
        self.path = self.root / "lifecycle.sqlite3"
        self._migrate()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=0.5, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=500")
        return connection

    def _migrate(self) -> None:
        try:
            with self._connect() as connection:
                version = int(connection.execute("PRAGMA user_version").fetchone()[0])
                if version > 1:
                    _fail("TRACE_INTEGRITY_FAILURE", "Lifecycle schema is newer than this build")
                if version == 0:
                    connection.executescript(
                        """
                        BEGIN EXCLUSIVE;
                        CREATE TABLE manifests (
                            digest TEXT PRIMARY KEY,
                            project_id TEXT NOT NULL,
                            manifest_ref TEXT NOT NULL,
                            contract_id TEXT NOT NULL,
                            generation INTEGER NOT NULL,
                            canonical_json TEXT NOT NULL,
                            UNIQUE(project_id, manifest_ref)
                        );
                        CREATE TABLE start_intents (
                            operation_id TEXT PRIMARY KEY,
                            project_id TEXT NOT NULL,
                            logical_run_id TEXT NOT NULL UNIQUE,
                            manifest_digest TEXT NOT NULL REFERENCES manifests(digest),
                            manifest_ref TEXT NOT NULL,
                            request_digest TEXT NOT NULL
                        );
                        CREATE TABLE runs (
                            run_id TEXT PRIMARY KEY,
                            project_id TEXT NOT NULL,
                            operation_id TEXT NOT NULL UNIQUE REFERENCES start_intents(operation_id),
                            manifest_digest TEXT NOT NULL REFERENCES manifests(digest),
                            provider_run_id TEXT NOT NULL UNIQUE,
                            coordinator_generation INTEGER NOT NULL,
                            semantic_state TEXT NOT NULL
                        );
                        CREATE TABLE tasks (
                            task_id TEXT PRIMARY KEY,
                            run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE RESTRICT,
                            task_key TEXT NOT NULL,
                            provider_task_id TEXT NOT NULL UNIQUE,
                            UNIQUE(run_id, task_key)
                        );
                        CREATE INDEX runs_project_idx ON runs(project_id, run_id);
                        PRAGMA user_version=1;
                        COMMIT;
                        """
                    )
                connection.execute("PRAGMA journal_mode=WAL")
                connection.execute("PRAGMA synchronous=FULL")
            os.chmod(self.path, 0o600)
        except LifecycleError:
            raise
        except sqlite3.Error:
            _fail("TRACE_INTEGRITY_FAILURE", "Lifecycle store migration failed")

    def register_manifest(self, manifest: ValidatedManifest, *, manifest_ref: str) -> None:
        if not isinstance(manifest, ValidatedManifest):
            _fail("MANIFEST_INVALID", "Validated manifest is required")
        if not isinstance(manifest_ref, str) or not manifest_ref or len(manifest_ref.encode()) > 1024:
            _fail("MANIFEST_INVALID", "Manifest reference is invalid")
        canonical = _canonical(manifest.canonical).decode("ascii")
        contract = manifest.canonical["contract"]
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                by_digest = connection.execute("SELECT * FROM manifests WHERE digest=?", (manifest.digest,)).fetchone()
                by_ref = connection.execute(
                    "SELECT * FROM manifests WHERE project_id=? AND manifest_ref=?",
                    (manifest.project_id, manifest_ref),
                ).fetchone()
                for existing in (by_digest, by_ref):
                    if existing is not None and (
                        existing["digest"] != manifest.digest
                        or existing["project_id"] != manifest.project_id
                        or existing["manifest_ref"] != manifest_ref
                        or existing["canonical_json"] != canonical
                    ):
                        _fail("CONTRACT_STALE", "Manifest reference or digest was reused")
                if by_digest is None:
                    connection.execute(
                        "INSERT INTO manifests VALUES (?, ?, ?, ?, ?, ?)",
                        (
                            manifest.digest,
                            manifest.project_id,
                            manifest_ref,
                            contract["contract_id"],
                            contract["generation"],
                            canonical,
                        ),
                    )
                connection.execute("COMMIT")
        except LifecycleError:
            raise
        except sqlite3.Error:
            _fail("TRACE_INTEGRITY_FAILURE", "Manifest could not be registered")

    def manifest(self, *, digest: str, manifest_ref: str, project_id: str) -> ValidatedManifest:
        _uuid(project_id, code="MANIFEST_INVALID")
        try:
            with self._connect() as connection:
                row = connection.execute("SELECT * FROM manifests WHERE digest=?", (digest,)).fetchone()
        except sqlite3.Error:
            _fail("TRACE_INTEGRITY_FAILURE", "Manifest store cannot be read")
        if row is None or row["project_id"] != project_id or row["manifest_ref"] != manifest_ref:
            _fail("MANIFEST_INVALID", "Manifest digest and reference are not registered")
        try:
            canonical = json.loads(row["canonical_json"])
        except (TypeError, json.JSONDecodeError):
            _fail("TRACE_INTEGRITY_FAILURE", "Registered manifest is malformed")
        validated = validate_swarm_manifest(canonical)
        if validated.digest != digest:
            _fail("TRACE_INTEGRITY_FAILURE", "Registered manifest digest changed")
        return validated

    def prepare_start(self, intent: StartIntent) -> None:
        values = (
            intent.operation_id,
            intent.project_id,
            intent.logical_run_id,
            intent.manifest_digest,
            intent.manifest_ref,
            intent.request_digest,
        )
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                row = connection.execute("SELECT * FROM start_intents WHERE operation_id=?", (intent.operation_id,)).fetchone()
                if row is not None:
                    observed = tuple(row[key] for key in (
                        "operation_id", "project_id", "logical_run_id", "manifest_digest", "manifest_ref", "request_digest"
                    ))
                    if observed != values:
                        _fail("IDEMPOTENCY_CONFLICT", "Start operation was reused with different input")
                else:
                    connection.execute("INSERT INTO start_intents VALUES (?, ?, ?, ?, ?, ?)", values)
                connection.execute("COMMIT")
        except LifecycleError:
            raise
        except sqlite3.Error:
            _fail("TRACE_INTEGRITY_FAILURE", "Start intent could not be persisted")

    def start_intent(self, operation_id: str) -> StartIntent:
        _uuid(operation_id, code="RECONCILIATION_REQUIRED")
        try:
            with self._connect() as connection:
                row = connection.execute("SELECT * FROM start_intents WHERE operation_id=?", (operation_id,)).fetchone()
        except sqlite3.Error:
            _fail("TRACE_INTEGRITY_FAILURE", "Start intent cannot be read")
        if row is None:
            _fail("RECONCILIATION_REQUIRED", "Start operation is not known")
        return StartIntent(*(row[key] for key in (
            "operation_id", "project_id", "logical_run_id", "manifest_digest", "manifest_ref", "request_digest"
        )))

    def bind_start(self, intent: StartIntent, result: ProviderStartResult, manifest: ValidatedManifest) -> RunBinding:
        if result.provider_run_id is None:
            _fail("PROVIDER_RESPONSE_INVALID", "Provider Run identity is missing")
        _token(result.provider_run_id)
        expected = set(manifest.topological_order)
        received = {key for key, _provider_id in result.provider_tasks}
        if len(received) != len(result.provider_tasks) or received != expected:
            _fail("PROVIDER_RESPONSE_INVALID", "Provider Task correlation is incomplete")
        provider_tasks = dict(result.provider_tasks)
        for provider_id in provider_tasks.values():
            _token(provider_id)
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                existing = connection.execute("SELECT * FROM runs WHERE run_id=?", (intent.logical_run_id,)).fetchone()
                if existing is None:
                    connection.execute(
                        "INSERT INTO runs VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (
                            intent.logical_run_id,
                            intent.project_id,
                            intent.operation_id,
                            intent.manifest_digest,
                            result.provider_run_id,
                            1,
                            "OPEN",
                        ),
                    )
                    for key in manifest.topological_order:
                        connection.execute(
                            "INSERT INTO tasks VALUES (?, ?, ?, ?)",
                            (_logical_task_id(intent.logical_run_id, key), intent.logical_run_id, key, provider_tasks[key]),
                        )
                elif existing["provider_run_id"] != result.provider_run_id:
                    _fail("PROVIDER_RESPONSE_INVALID", "Provider Run correlation changed")
                connection.execute("COMMIT")
        except LifecycleError:
            raise
        except sqlite3.IntegrityError:
            _fail("PROVIDER_RESPONSE_INVALID", "Provider correlation collides with another Run")
        except sqlite3.Error:
            _fail("TRACE_INTEGRITY_FAILURE", "Provider correlation could not be persisted")
        return self.run(intent.logical_run_id, project_id=intent.project_id)

    def run(self, run_id: str, *, project_id: str) -> RunBinding:
        _uuid(run_id, code="PROJECT_NOT_ADMITTED")
        _uuid(project_id, code="PROJECT_NOT_ADMITTED")
        try:
            with self._connect() as connection:
                row = connection.execute("SELECT * FROM runs WHERE run_id=? AND project_id=?", (run_id, project_id)).fetchone()
                task_rows = connection.execute("SELECT * FROM tasks WHERE run_id=? ORDER BY rowid", (run_id,)).fetchall()
        except sqlite3.Error:
            _fail("TRACE_INTEGRITY_FAILURE", "Lifecycle binding cannot be read")
        if row is None:
            _fail("PROJECT_NOT_ADMITTED", "Run is not bound to this project")
        return RunBinding(
            run_id=row["run_id"],
            project_id=row["project_id"],
            operation_id=row["operation_id"],
            manifest_digest=row["manifest_digest"],
            provider_run_id=row["provider_run_id"],
            coordinator_generation=row["coordinator_generation"],
            tasks=tuple(TaskBinding(item["task_id"], item["task_key"], item["provider_task_id"]) for item in task_rows),
            semantic_state=row["semantic_state"],
        )

    def pending_by_run(self, run_id: str) -> StartIntent:
        _uuid(run_id, code="RECONCILIATION_REQUIRED")
        try:
            with self._connect() as connection:
                row = connection.execute("SELECT operation_id FROM start_intents WHERE logical_run_id=?", (run_id,)).fetchone()
        except sqlite3.Error:
            _fail("TRACE_INTEGRITY_FAILURE", "Pending lifecycle intent cannot be read")
        if row is None:
            _fail("RECONCILIATION_REQUIRED", "Run has no pending start intent")
        return self.start_intent(row["operation_id"])

    def mark_closed(self, run_id: str, *, project_id: str) -> None:
        self.run(run_id, project_id=project_id)
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute("UPDATE runs SET semantic_state='CLOSED' WHERE run_id=? AND project_id=?", (run_id, project_id))
                connection.execute("COMMIT")
        except sqlite3.Error:
            _fail("TRACE_INTEGRITY_FAILURE", "Semantic closure could not be persisted")


class LifecycleService:
    """M3 lifecycle service; worker dispatch is intentionally absent."""

    def __init__(self, *, foundation: M2Foundation, store: LifecycleStore, provider: LifecycleProvider) -> None:
        if not isinstance(foundation, M2Foundation) or not isinstance(store, LifecycleStore):
            raise TypeError("M2 foundation and lifecycle store are required")
        binding_digest = getattr(provider, "binding_digest", None)
        if not isinstance(binding_digest, str) or _DIGEST_RE.fullmatch(binding_digest) is None:
            _fail("PROVIDER_SCHEMA_DRIFT", "Provider binding digest is invalid")
        self.foundation = foundation
        self.store = store
        self.provider = provider

    @staticmethod
    def _operation(arguments: dict[str, Any]) -> dict[str, Any]:
        operation = arguments["operation"]
        if operation["expected_effect"] != "LOCAL_REVERSIBLE":
            _fail("EFFECT_NOT_AUTHORIZED", "Lifecycle mutation requires LOCAL_REVERSIBLE authority")
        return operation

    @staticmethod
    def _resources(result: ProviderStartResult) -> tuple[str, ...]:
        values = []
        if result.provider_run_id is not None:
            values.append(result.provider_run_id)
        values.extend(provider_id for _key, provider_id in result.provider_tasks)
        for value in values:
            _token(value)
        return tuple(values)

    def _response(self, intent: StartIntent, *, outcome: str, replayed: bool) -> dict[str, Any]:
        try:
            binding = self.store.run(intent.logical_run_id, project_id=intent.project_id)
        except LifecycleError as exc:
            if exc.code != "PROJECT_NOT_ADMITTED":
                raise
            binding = None
        return {
            "outcome": outcome,
            "replayed": replayed,
            "run_id": intent.logical_run_id,
            "tasks": [] if binding is None else [
                {"task_id": task.task_id, "task_key": task.task_key, "provider_task_id": task.provider_task_id}
                for task in binding.tasks
            ],
        }

    def swarm_start(self, raw: dict[str, Any]) -> dict[str, Any]:
        try:
            arguments = validate_request("swarm_start", raw)
        except ProtocolError as exc:
            _fail(exc.code, "Start request is invalid")
        operation = self._operation(arguments)
        project_id = operation["project_id"]
        self.foundation.project_inspect({"project_id": project_id})
        if arguments["dispatch_ready"] is not False:
            _fail("EFFECT_NOT_AUTHORIZED", "M3 cannot dispatch workers")
        if arguments["provider_binding_digest"] != self.provider.binding_digest:
            _fail("PROVIDER_SCHEMA_DRIFT", "Provider binding does not match the admitted build")
        manifest = self.store.manifest(
            digest=arguments["manifest_digest"],
            manifest_ref=arguments["manifest_ref"],
            project_id=project_id,
        )
        if manifest.canonical["contract"]["contract_id"] != operation["contract_id"]:
            _fail("CONTRACT_STALE", "Operation contract does not match the manifest")
        request_digest = canonical_request_digest("swarm_start", raw)
        operation_id = operation["operation_id"]
        intent = StartIntent(
            operation_id=operation_id,
            project_id=project_id,
            logical_run_id=_logical_run_id(operation_id),
            manifest_digest=manifest.digest,
            manifest_ref=arguments["manifest_ref"],
            request_digest=request_digest,
        )
        self.store.prepare_start(intent)
        try:
            prepared, latest = self.foundation.trace.prepare_intent(
                operation_id=operation_id,
                project_id=project_id,
                capability="swarm_start",
                request_digest=request_digest,
            )
        except StoreError as exc:
            _fail(exc.code, "Start intent could not be journaled")
        if not prepared:
            outcome = "SUCCEEDED" if latest["outcome"] == "SUCCEEDED" else "UNKNOWN"
            return self._response(intent, outcome=outcome, replayed=True)
        try:
            result = self.provider.start_no_dispatch(
                operation_id=operation_id,
                logical_run_id=intent.logical_run_id,
                manifest=manifest,
            )
            self._validate_start_result(result)
        except Exception as exc:
            if isinstance(exc, LifecycleError):
                raise
            self.foundation.trace.append_event(
                operation_id=operation_id,
                project_id=project_id,
                capability="swarm_start",
                phase="RECEIPT",
                outcome="UNKNOWN",
                request_digest=request_digest,
                error_code="DELIVERY_UNKNOWN",
            )
            return self._response(intent, outcome="UNKNOWN", replayed=False)
        if result.outcome != "APPLIED":
            self.foundation.trace.append_event(
                operation_id=operation_id,
                project_id=project_id,
                capability="swarm_start",
                phase="RECEIPT",
                outcome="UNKNOWN",
                request_digest=request_digest,
                response_digest=result.response_digest,
                provider_request_id=result.provider_request_id,
                resource_ids=self._resources(result),
                error_code="RECONCILIATION_REQUIRED",
            )
            return self._response(intent, outcome="UNKNOWN", replayed=False)
        try:
            self.store.bind_start(intent, result, manifest)
        except LifecycleError:
            self.foundation.trace.append_event(
                operation_id=operation_id,
                project_id=project_id,
                capability="swarm_start",
                phase="RECEIPT",
                outcome="UNKNOWN",
                request_digest=request_digest,
                response_digest=result.response_digest,
                provider_request_id=result.provider_request_id,
                resource_ids=self._resources(result),
                error_code="RECONCILIATION_REQUIRED",
            )
            return self._response(intent, outcome="UNKNOWN", replayed=False)
        self.foundation.trace.append_event(
            operation_id=operation_id,
            project_id=project_id,
            capability="swarm_start",
            phase="RECEIPT",
            outcome="SUCCEEDED",
            request_digest=request_digest,
            response_digest=result.response_digest,
            provider_request_id=result.provider_request_id,
            resource_ids=self._resources(result),
        )
        return self._response(intent, outcome="SUCCEEDED", replayed=False)

    @staticmethod
    def _validate_start_result(result: ProviderStartResult) -> None:
        if not isinstance(result, ProviderStartResult) or result.outcome not in {"APPLIED", "PARTIAL", "FAILED", "UNKNOWN"}:
            _fail("PROVIDER_RESPONSE_INVALID", "Provider start result is invalid")
        _token(result.provider_request_id)
        _token(result.provider_run_id)
        _digest(result.response_digest)
        if not isinstance(result.provider_tasks, tuple) or len(result.provider_tasks) > 64:
            _fail("PROVIDER_RESPONSE_INVALID", "Provider Task result is invalid")
        for item in result.provider_tasks:
            if not isinstance(item, tuple) or len(item) != 2:
                _fail("PROVIDER_RESPONSE_INVALID", "Provider Task result is invalid")
            _token(item[0])
            _token(item[1])

    def _projection(self, binding: RunBinding) -> ProviderRunProjection:
        projection = self.provider.inspect_run(provider_run_id=binding.provider_run_id)
        if not isinstance(projection, ProviderRunProjection):
            _fail("PROVIDER_RESPONSE_INVALID", "Provider status is not structured")
        if (
            projection.provider_run_id != binding.provider_run_id
            or projection.status not in _RUN_STATUSES
            or not isinstance(projection.coordinator_generation, int)
            or projection.coordinator_generation < binding.coordinator_generation
            or not isinstance(projection.source, str)
            or not projection.source
        ):
            _fail("PROVIDER_RESPONSE_INVALID", "Provider Run projection is invalid")
        expected = {task.task_key: task for task in binding.tasks}
        observed: dict[str, ProviderTaskProjection] = {}
        for task in projection.tasks:
            if not isinstance(task, ProviderTaskProjection) or task.status not in _TASK_STATUSES:
                _fail("PROVIDER_RESPONSE_INVALID", "Provider Task projection is invalid")
            if task.task_key in observed:
                _fail("PROVIDER_RESPONSE_INVALID", "Provider Task projection is duplicated")
            observed[task.task_key] = task
        if set(observed) != set(expected):
            _fail("PROVIDER_RESPONSE_INVALID", "Provider Task projection drifted")
        for key, task in observed.items():
            if task.provider_task_id != expected[key].provider_task_id:
                _fail("PROVIDER_RESPONSE_INVALID", "Provider Task identity drifted")
        for resource in projection.live_resource_ids:
            _token(resource)
        return projection

    def swarm_status(self, raw: dict[str, Any]) -> dict[str, Any]:
        try:
            arguments = validate_request("swarm_status", raw)
        except ProtocolError as exc:
            _fail(exc.code, "Status request is invalid")
        self.foundation.project_inspect({"project_id": arguments["project_id"]})
        binding = self.store.run(arguments["run_id"], project_id=arguments["project_id"])
        projection = self._projection(binding)
        by_key = {task.task_key: task for task in projection.tasks}
        return {
            "project_id": binding.project_id,
            "run_id": binding.run_id,
            "status": projection.status,
            "semantic_state": binding.semantic_state,
            "source": projection.source,
            "coordinator_generation": projection.coordinator_generation,
            "tasks": [
                {
                    "task_id": task.task_id,
                    "task_key": task.task_key,
                    "provider_task_id": task.provider_task_id,
                    "status": by_key[task.task_key].status,
                }
                for task in binding.tasks
            ],
            "live_resource_ids": list(projection.live_resource_ids),
            "next_cursor": None,
        }

    def swarm_reconcile(self, raw: dict[str, Any]) -> dict[str, Any]:
        try:
            arguments = validate_request("swarm_reconcile", raw)
        except ProtocolError as exc:
            _fail(exc.code, "Reconciliation request is invalid")
        operation = self._operation(arguments)
        self.foundation.project_inspect({"project_id": operation["project_id"]})
        if arguments["target_type"] != "operation" or arguments["mode"] not in {"observe", "fence"}:
            _fail("RECONCILIATION_REQUIRED", "M3 reconciles start operations only")
        intent = self.store.start_intent(arguments["target_id"])
        if intent.project_id != operation["project_id"] or intent.logical_run_id != arguments["run_id"]:
            _fail("PRINCIPAL_UNAUTHORIZED", "Reconciliation target is outside the admitted Run")
        records = self.foundation.trace.records_for(intent.operation_id)
        if records[-1]["outcome"] == "SUCCEEDED":
            return self._response(intent, outcome="SUCCEEDED", replayed=True)
        try:
            result = self.provider.reconcile_start(operation_id=intent.operation_id, logical_run_id=intent.logical_run_id)
            if result is None:
                created, record = self.foundation.trace.append_reconcile_once(
                    operation_id=intent.operation_id,
                    project_id=intent.project_id,
                    capability="swarm_start",
                    outcome="NOT_APPLIED" if arguments["mode"] == "fence" else "UNKNOWN",
                    request_digest=intent.request_digest,
                    error_code=None if arguments["mode"] == "fence" else "RECONCILIATION_REQUIRED",
                )
                return self._response(
                    intent,
                    outcome="NOT_APPLIED" if record["outcome"] == "NOT_APPLIED" else "UNKNOWN",
                    replayed=not created,
                )
            self._validate_start_result(result)
            if result.outcome != "APPLIED":
                raise ValueError("not exactly applied")
            manifest = self.store.manifest(
                digest=intent.manifest_digest,
                manifest_ref=intent.manifest_ref,
                project_id=intent.project_id,
            )
            self.store.bind_start(intent, result, manifest)
            created, record = self.foundation.trace.append_reconcile_once(
                operation_id=intent.operation_id,
                project_id=intent.project_id,
                capability="swarm_start",
                outcome="SUCCEEDED",
                request_digest=intent.request_digest,
                response_digest=result.response_digest,
                provider_request_id=result.provider_request_id,
                resource_ids=self._resources(result),
            )
            return self._response(intent, outcome="SUCCEEDED", replayed=not created)
        except (LifecycleError, StoreError):
            raise
        except Exception:
            created, _record = self.foundation.trace.append_reconcile_once(
                operation_id=intent.operation_id,
                project_id=intent.project_id,
                capability="swarm_start",
                outcome="UNKNOWN",
                request_digest=intent.request_digest,
                error_code="RECONCILIATION_REQUIRED",
            )
            return self._response(intent, outcome="UNKNOWN", replayed=not created)

    def _effect_replay(self, operation_id: str) -> dict[str, Any] | None:
        records = self.foundation.trace.records_for(operation_id)
        if not records:
            return None
        latest = records[-1]
        return {"outcome": latest["outcome"], "replayed": True, "resource_ids": latest["resource_ids"]}

    def swarm_cancel(self, raw: dict[str, Any]) -> dict[str, Any]:
        try:
            arguments = validate_request("swarm_cancel", raw)
        except ProtocolError as exc:
            _fail(exc.code, "Cancel request is invalid")
        operation = self._operation(arguments)
        project_id = operation["project_id"]
        self.foundation.project_inspect({"project_id": project_id})
        binding = self.store.run(arguments["run_id"], project_id=project_id)
        target_type = arguments["target_type"]
        if target_type == "run":
            if arguments["target_id"] != binding.run_id:
                _fail("PRINCIPAL_UNAUTHORIZED", "Cancel target is outside the Run")
            provider_target = binding.provider_run_id
        elif target_type == "task":
            matched = next((task for task in binding.tasks if task.task_id == arguments["target_id"]), None)
            if matched is None:
                _fail("PRINCIPAL_UNAUTHORIZED", "Cancel target is outside the Run")
            provider_target = matched.provider_task_id
        else:
            _fail("CAPABILITY_UNAVAILABLE", "M3 has no Dispatch cancellation")
        request_digest = canonical_request_digest("swarm_cancel", raw)
        prepared, latest = self.foundation.trace.prepare_intent(
            operation_id=operation["operation_id"],
            project_id=project_id,
            capability="swarm_cancel",
            request_digest=request_digest,
        )
        if not prepared:
            return {
                "outcome": "CANCELLED" if latest["outcome"] == "SUCCEEDED" else "UNKNOWN",
                "replayed": True,
                "resource_ids": latest["resource_ids"],
            }
        try:
            result = self.provider.cancel(
                provider_run_id=binding.provider_run_id,
                target_type=target_type,
                provider_target_id=provider_target,
            )
            self._validate_effect_result(result)
        except Exception:
            self.foundation.trace.append_event(
                operation_id=operation["operation_id"], project_id=project_id, capability="swarm_cancel",
                phase="RECEIPT", outcome="UNKNOWN", request_digest=request_digest, error_code="DELIVERY_UNKNOWN"
            )
            return {"outcome": "UNKNOWN", "replayed": False, "resource_ids": []}
        outcome = "SUCCEEDED" if result.outcome == "APPLIED" else "UNKNOWN"
        self.foundation.trace.append_event(
            operation_id=operation["operation_id"], project_id=project_id, capability="swarm_cancel",
            phase="RECEIPT", outcome=outcome, request_digest=request_digest,
            response_digest=result.response_digest, provider_request_id=result.provider_request_id,
            resource_ids=result.resource_ids, error_code=None if outcome == "SUCCEEDED" else "DELIVERY_UNKNOWN"
        )
        return {
            "outcome": "CANCELLED" if outcome == "SUCCEEDED" else "UNKNOWN",
            "replayed": False,
            "resource_ids": list(result.resource_ids),
        }

    @staticmethod
    def _validate_effect_result(result: ProviderEffectResult) -> None:
        if not isinstance(result, ProviderEffectResult) or result.outcome not in {"APPLIED", "FAILED", "UNKNOWN"}:
            _fail("PROVIDER_RESPONSE_INVALID", "Provider effect result is invalid")
        _token(result.provider_request_id)
        _digest(result.response_digest)
        if not isinstance(result.resource_ids, tuple) or len(result.resource_ids) > 64:
            _fail("PROVIDER_RESPONSE_INVALID", "Provider resource inventory is invalid")
        for resource in result.resource_ids:
            _token(resource)
        if not isinstance(result.cleanup_complete, bool):
            _fail("PROVIDER_RESPONSE_INVALID", "Provider cleanup result is invalid")

    def swarm_close(self, raw: dict[str, Any]) -> dict[str, Any]:
        try:
            arguments = validate_request("swarm_close", raw)
        except ProtocolError as exc:
            _fail(exc.code, "Close request is invalid")
        operation = self._operation(arguments)
        project_id = operation["project_id"]
        self.foundation.project_inspect({"project_id": project_id})
        binding = self.store.run(arguments["run_id"], project_id=project_id)
        projection = self._projection(binding)
        if any(task.status not in _TERMINAL_TASK_STATUSES for task in projection.tasks):
            _fail("CLEANUP_INCOMPLETE", "Run has non-terminal Tasks")
        request_digest = canonical_request_digest("swarm_close", raw)
        prepared, latest = self.foundation.trace.prepare_intent(
            operation_id=operation["operation_id"],
            project_id=project_id,
            capability="swarm_close",
            request_digest=request_digest,
        )
        if not prepared:
            return {
                "outcome": "CLOSED" if latest["outcome"] == "SUCCEEDED" else "CLEANUP_FAILED",
                "replayed": True,
                "survivors": latest["resource_ids"],
            }
        try:
            result = self.provider.close(
                provider_run_id=binding.provider_run_id,
                effect_plan=tuple(arguments["effect_plan"]),
            )
            self._validate_effect_result(result)
        except Exception:
            self.foundation.trace.append_event(
                operation_id=operation["operation_id"], project_id=project_id, capability="swarm_close",
                phase="RECEIPT", outcome="UNKNOWN", request_digest=request_digest, error_code="DELIVERY_UNKNOWN"
            )
            return {"outcome": "UNKNOWN", "replayed": False, "survivors": list(projection.live_resource_ids)}
        succeeded = result.outcome == "APPLIED" and result.cleanup_complete and not result.resource_ids
        self.foundation.trace.append_event(
            operation_id=operation["operation_id"], project_id=project_id, capability="swarm_close",
            phase="RECEIPT", outcome="SUCCEEDED" if succeeded else "FAILED", request_digest=request_digest,
            response_digest=result.response_digest, provider_request_id=result.provider_request_id,
            resource_ids=result.resource_ids, error_code=None if succeeded else "CLEANUP_INCOMPLETE"
        )
        if succeeded:
            self.store.mark_closed(binding.run_id, project_id=project_id)
        return {
            "outcome": "CLOSED" if succeeded else "CLEANUP_FAILED",
            "replayed": False,
            "survivors": list(result.resource_ids),
        }
