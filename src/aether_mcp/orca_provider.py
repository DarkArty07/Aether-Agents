"""Exact-build adapter for the admitted public Orca orchestration CLI."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, NoReturn

from .coordination import ProviderDispatchResult, ProviderMessageResult
from .lifecycle import (
    LifecycleError,
    ProviderEffectResult,
    ProviderRunProjection,
    ProviderStartResult,
    ProviderTaskProjection,
)
from .manifest import ValidatedManifest

_MAX_RESPONSE_BYTES = 4 * 1024 * 1024
_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,511}$")
_TASK_MARKER_RE = re.compile(
    r"^aether-task:(?P<run>[0-9a-f-]{36}):(?P<key>[A-Za-z0-9][A-Za-z0-9._:/-]*):(?P<digest>[0-9a-f]{64})(?:\s|$)"
)
_TERMINAL_TASKS = {"completed", "failed", "blocked"}


def _fail(code: str, message: str) -> NoReturn:
    raise LifecycleError(code, message)


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()
    ).hexdigest()


def _token(value: Any) -> str:
    if not isinstance(value, str) or _TOKEN_RE.fullmatch(value) is None:
        _fail("PROVIDER_RESPONSE_INVALID", "Orca returned an invalid identity")
    return value


def _envelope(value: Any) -> tuple[str | None, dict[str, Any]]:
    try:
        encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()
    except (TypeError, ValueError):
        _fail("PROVIDER_RESPONSE_INVALID", "Orca response is not canonical JSON")
    if len(encoded) > _MAX_RESPONSE_BYTES or not isinstance(value, dict):
        _fail("PROVIDER_RESPONSE_INVALID", "Orca response exceeded its admitted shape")
    if set(value) - {"id", "ok", "result", "error", "_meta"}:
        _fail("PROVIDER_SCHEMA_DRIFT", "Orca returned unknown envelope fields")
    if value.get("ok") is not True or not isinstance(value.get("result"), dict):
        _fail("PROVIDER_RESPONSE_INVALID", "Orca operation did not succeed structurally")
    request_id = value.get("id")
    if request_id is not None:
        request_id = _token(request_id)
    return request_id, value["result"]


def _entity_id(value: Any, *, entity: str) -> str:
    preferred = (f"{entity}Id", "id")
    containers = {entity, f"{entity}s"}

    def walk(item: Any, parent: str | None = None) -> str | None:
        if isinstance(item, dict):
            for key in preferred:
                candidate = item.get(key)
                if isinstance(candidate, str) and (key != "id" or parent in containers):
                    return _token(candidate)
            for key in sorted(item):
                found = walk(item[key], key)
                if found is not None:
                    return found
        elif isinstance(item, list):
            for child in item:
                found = walk(child, parent)
                if found is not None:
                    return found
        return None

    found = walk(value)
    if found is None:
        _fail("PROVIDER_SCHEMA_DRIFT", f"Orca {entity} response omitted its identity")
    return found


def _objects_under(value: Any, key: str) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []

    def walk(item: Any) -> None:
        if isinstance(item, dict):
            child = item.get(key)
            if isinstance(child, list):
                for entry in child:
                    if not isinstance(entry, dict):
                        _fail("PROVIDER_RESPONSE_INVALID", f"Orca {key} collection is malformed")
                    found.append(entry)
                return
            for nested in item.values():
                walk(nested)
        elif isinstance(item, list):
            for nested in item:
                walk(nested)

    walk(value)
    return found


def _terminal_handles(value: Any) -> set[str]:
    handles: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            if key in {"agentTerminalHandle", "terminalHandle", "handle"} and isinstance(child, str):
                handles.add(_token(child))
            handles.update(_terminal_handles(child))
    elif isinstance(value, list):
        for child in value:
            handles.update(_terminal_handles(child))
    return handles


def _field(record: dict[str, Any], *names: str) -> Any:
    for name in names:
        if name in record:
            return record[name]
    return None


def _find_string(value: Any, names: tuple[str, ...]) -> str:
    if isinstance(value, dict):
        for name in names:
            candidate = value.get(name)
            if isinstance(candidate, str):
                return _token(candidate)
        for child in value.values():
            try:
                return _find_string(child, names)
            except LifecycleError:
                continue
    elif isinstance(value, list):
        for child in value:
            try:
                return _find_string(child, names)
            except LifecycleError:
                continue
    _fail("PROVIDER_SCHEMA_DRIFT", "Orca response omitted a required identity")


def _find_path(value: Any, names: tuple[str, ...]) -> str:
    if isinstance(value, dict):
        for name in names:
            candidate = value.get(name)
            if isinstance(candidate, str):
                path = Path(candidate)
                if path.is_absolute() and ".." not in path.parts and "\x00" not in candidate and len(candidate) <= 4096:
                    return candidate
                _fail("PROVIDER_RESPONSE_INVALID", "Orca worktree path is invalid")
        for child in value.values():
            try:
                return _find_path(child, names)
            except LifecycleError:
                continue
    elif isinstance(value, list):
        for child in value:
            try:
                return _find_path(child, names)
            except LifecycleError:
                continue
    _fail("PROVIDER_SCHEMA_DRIFT", "Orca response omitted a required worktree path")


@dataclass(frozen=True)
class FixtureRuntimeConfig:
    repo_selector: str
    base_ref: str
    command_builder: Callable[[str, str, dict[str, Any], int], str]


@dataclass(frozen=True)
class ModelRuntimeConfig:
    repo_selector: str
    base_ref: str
    agent: str
    expected_model: str
    timeout_ms: int


@dataclass(frozen=True)
class ModelWorkerObservation:
    source: str
    activity_observed: bool
    idle_hint: bool
    blocked_reason: str | None
    response_digest: str
    response_bytes: int


class PublicOrcaLifecycleProvider:
    """Provider adapter restricted to public structured commands and exact argv."""

    def __init__(
        self,
        *,
        transport: Callable[[tuple[str, ...]], dict[str, Any]],
        binding_digest: str,
        coordinator_handle: str,
        fixture_runtime: FixtureRuntimeConfig | None = None,
        model_runtime: ModelRuntimeConfig | None = None,
    ) -> None:
        if not callable(transport):
            raise TypeError("Structured Orca transport is required")
        if not isinstance(binding_digest, str) or re.fullmatch(r"[0-9a-f]{64}", binding_digest) is None:
            _fail("PROVIDER_SCHEMA_DRIFT", "Orca binding digest is invalid")
        self.transport = transport
        self.binding_digest = binding_digest
        self.coordinator_handle = _token(coordinator_handle)
        if fixture_runtime is not None:
            _token(fixture_runtime.repo_selector)
            _token(fixture_runtime.base_ref)
            if not callable(fixture_runtime.command_builder):
                _fail("PROVIDER_SCHEMA_DRIFT", "Fixture command builder is invalid")
        self.fixture_runtime = fixture_runtime
        if model_runtime is not None:
            _token(model_runtime.repo_selector)
            _token(model_runtime.base_ref)
            _token(model_runtime.expected_model)
            if model_runtime.agent != "codex" or not 1_000 <= model_runtime.timeout_ms <= 600_000:
                _fail("CAPABILITY_UNAVAILABLE", "Model worker runtime exceeds its admitted boundary")
        self.model_runtime = model_runtime

    def _call(self, argv: tuple[str, ...]) -> tuple[str | None, dict[str, Any], dict[str, Any]]:
        if not argv or argv[-1] != "--json" or any(not isinstance(item, str) or "\x00" in item for item in argv):
            _fail("PROVIDER_SCHEMA_DRIFT", "Orca argv is not a structured admitted call")
        raw = self.transport(argv)
        request_id, result = _envelope(raw)
        return request_id, result, raw

    @staticmethod
    def _run_marker(logical_run_id: str, operation_id: str) -> str:
        return f"aether-run:{logical_run_id}:{operation_id}"

    @staticmethod
    def _task_marker(logical_run_id: str, task_key: str, manifest_digest: str) -> str:
        return f"aether-task:{logical_run_id}:{task_key}:{manifest_digest}"

    def start_no_dispatch(
        self,
        *,
        operation_id: str,
        logical_run_id: str,
        manifest: ValidatedManifest,
    ) -> ProviderStartResult:
        envelopes: list[dict[str, Any]] = []
        provider_run_id: str | None = None
        provider_tasks: list[tuple[str, str]] = []
        provider_request_id: str | None = None
        try:
            provider_request_id, result, raw = self._call(
                (
                    "orchestration",
                    "run-create",
                    "--objective",
                    self._run_marker(logical_run_id, operation_id),
                    "--from",
                    self.coordinator_handle,
                    "--json",
                )
            )
            envelopes.append(raw)
            provider_run_id = _entity_id(result, entity="run")
            task_specs = {task["task_key"]: task for task in manifest.canonical["tasks"]}
            for task_key in manifest.topological_order:
                task = task_specs[task_key]
                dependency_ids = [dict(provider_tasks)[key] for key in task["dependencies"]]
                argv: list[str] = [
                    "orchestration",
                    "task-create",
                    "--spec",
                    f"{self._task_marker(logical_run_id, task_key, manifest.digest)} {task['deliverable']}",
                    "--task-title",
                    task_key,
                    "--run",
                    provider_run_id,
                    "--from",
                    self.coordinator_handle,
                ]
                if dependency_ids:
                    argv.extend(("--deps", json.dumps(dependency_ids, separators=(",", ":"))))
                argv.append("--json")
                _request, task_result, task_raw = self._call(tuple(argv))
                envelopes.append(task_raw)
                provider_tasks.append((task_key, _entity_id(task_result, entity="task")))
        except (TimeoutError, LifecycleError):
            if provider_run_id is None:
                raise
            return ProviderStartResult(
                outcome="PARTIAL",
                provider_request_id=provider_request_id,
                provider_run_id=provider_run_id,
                provider_tasks=tuple(provider_tasks),
                response_digest=_digest(envelopes),
            )
        return ProviderStartResult(
            outcome="APPLIED",
            provider_request_id=provider_request_id,
            provider_run_id=provider_run_id,
            provider_tasks=tuple(provider_tasks),
            response_digest=_digest(envelopes),
        )

    @staticmethod
    def _task_rows(result: dict[str, Any], *, logical_run_id: str | None = None) -> list[tuple[str, str, str]]:
        rows: list[tuple[str, str, str]] = []
        for record in _objects_under(result, "tasks"):
            spec = _field(record, "spec", "description")
            if not isinstance(spec, str):
                continue
            match = _TASK_MARKER_RE.match(spec)
            if match is None or (logical_run_id is not None and match.group("run") != logical_run_id):
                continue
            provider_task_id = _token(_field(record, "taskId", "id"))
            status = _field(record, "status")
            if not isinstance(status, str) or status not in {
                "pending", "ready", "dispatched", "completed", "failed", "blocked"
            }:
                _fail("PROVIDER_RESPONSE_INVALID", "Orca Task status is invalid")
            rows.append((match.group("key"), provider_task_id, status))
        return rows

    def inspect_run(self, *, provider_run_id: str) -> ProviderRunProjection:
        provider_run_id = _token(provider_run_id)
        _request, run_result, run_raw = self._call(
            ("orchestration", "run-show", "--id", provider_run_id, "--json")
        )
        if _entity_id(run_result, entity="run") != provider_run_id:
            _fail("PROVIDER_RESPONSE_INVALID", "Orca Run identity changed")
        _request, tasks_result, tasks_raw = self._call(
            ("orchestration", "task-list", "--run", provider_run_id, "--json")
        )
        rows = self._task_rows(tasks_result)
        statuses = [status for _key, _provider_id, status in rows]
        run_status = "terminal" if statuses and all(status in _TERMINAL_TASKS for status in statuses) else "running"
        return ProviderRunProjection(
            provider_run_id=provider_run_id,
            status=run_status,
            tasks=tuple(
                ProviderTaskProjection(task_key=key, provider_task_id=task_id, status=status)
                for key, task_id, status in rows
            ),
            live_resource_ids=(),
            coordinator_generation=1,
            source="orca-public-cli",
        )

    def reconcile_start(self, *, operation_id: str, logical_run_id: str) -> ProviderStartResult | None:
        _request, runs_result, runs_raw = self._call(
            ("orchestration", "run-list", "--limit", "100", "--json")
        )
        marker = self._run_marker(logical_run_id, operation_id)
        matches: list[str] = []
        for record in _objects_under(runs_result, "runs"):
            if _field(record, "objective") == marker:
                matches.append(_token(_field(record, "runId", "id")))
        if not matches:
            return None
        if len(matches) != 1:
            _fail("PROVIDER_RESPONSE_INVALID", "Orca returned duplicate Run correlations")
        provider_run_id = matches[0]
        _request, tasks_result, tasks_raw = self._call(
            ("orchestration", "task-list", "--run", provider_run_id, "--json")
        )
        rows = self._task_rows(tasks_result, logical_run_id=logical_run_id)
        return ProviderStartResult(
            outcome="APPLIED" if rows else "PARTIAL",
            provider_request_id=None,
            provider_run_id=provider_run_id,
            provider_tasks=tuple((key, task_id) for key, task_id, _status in rows),
            response_digest=_digest((runs_raw, tasks_raw)),
        )

    def cancel(self, *, provider_run_id: str, target_type: str, provider_target_id: str) -> ProviderEffectResult:
        provider_run_id = _token(provider_run_id)
        provider_target_id = _token(provider_target_id)
        if target_type not in {"run", "task"}:
            _fail("CAPABILITY_UNAVAILABLE", "Orca M3 cancellation target is unsupported")
        targets: list[str]
        if target_type == "task":
            targets = [provider_target_id]
        else:
            _request, tasks_result, _raw = self._call(
                ("orchestration", "task-list", "--run", provider_run_id, "--json")
            )
            targets = [task_id for _key, task_id, status in self._task_rows(tasks_result) if status not in _TERMINAL_TASKS]
        envelopes: list[dict[str, Any]] = []
        for task_id in targets:
            _request, _result, raw = self._call(
                (
                    "orchestration", "task-update", "--id", task_id, "--status", "failed",
                    "--run", provider_run_id, "--from", self.coordinator_handle, "--json",
                )
            )
            envelopes.append(raw)
        return ProviderEffectResult(
            outcome="APPLIED",
            provider_request_id=None,
            resource_ids=tuple(targets),
            response_digest=_digest(envelopes),
            cleanup_complete=True,
        )

    def _fixture_start(
        self,
        *,
        provider_run_id: str,
        provider_task_id: str,
        logical_dispatch_id: str,
        task_spec: dict[str, Any],
        attempt_generation: int,
        prior_provider_dispatch_id: str | None,
    ) -> ProviderDispatchResult:
        fixture = self.fixture_runtime
        if fixture is None or task_spec.get("placement") != "child_worktree" or attempt_generation < 1:
            _fail("CAPABILITY_UNAVAILABLE", "Deterministic fixture runtime is not admitted")
        provider_run_id = _token(provider_run_id)
        provider_task_id = _token(provider_task_id)
        logical_dispatch_id = _token(logical_dispatch_id)
        envelopes: list[dict[str, Any]] = []
        worktree_path: str | None = None
        terminal_id: str | None = None
        provider_dispatch_id: str | None = None
        worker_id: str | None = None
        provider_request_id: str | None = None
        try:
            _request, worktree_result, raw = self._call(
                (
                    "worktree",
                    "create",
                    "--name",
                    f"aether-fixture-{logical_dispatch_id[:8]}-g{attempt_generation}",
                    "--repo",
                    fixture.repo_selector,
                    "--base-branch",
                    fixture.base_ref,
                    "--no-parent",
                    "--setup",
                    "skip",
                    "--json",
                )
            )
            envelopes.append(raw)
            worktree_path = _find_path(worktree_result, ("worktreePath", "path"))
            _request, terminal_result, raw = self._call(
                (
                    "terminal",
                    "create",
                    "--worktree",
                    f"path:{worktree_path}",
                    "--title",
                    f"AETHER-FIXTURE-G{attempt_generation}",
                    "--command",
                    "bash",
                    "--json",
                )
            )
            envelopes.append(raw)
            terminal_id = _find_string(terminal_result, ("agentTerminalHandle", "terminalHandle", "handle"))
            if prior_provider_dispatch_id is not None:
                _request, _result, raw = self._call(
                    (
                        "orchestration",
                        "task-update",
                        "--id",
                        provider_task_id,
                        "--status",
                        "ready",
                        "--run",
                        provider_run_id,
                        "--from",
                        self.coordinator_handle,
                        "--json",
                    )
                )
                envelopes.append(raw)
            dispatch_argv: list[str] = [
                "orchestration",
                "dispatch",
                "--task",
                provider_task_id,
                "--to",
                terminal_id,
                "--run",
                provider_run_id,
                "--from",
                self.coordinator_handle,
            ]
            dispatch_argv.append("--json")
            provider_request_id, worker_result, raw = self._call(tuple(dispatch_argv))
            envelopes.append(raw)
            provider_dispatch_id = _entity_id(worker_result, entity="dispatch")
            worker_id = terminal_id
            command = fixture.command_builder(logical_dispatch_id, worktree_path, task_spec, attempt_generation)
            if not isinstance(command, str) or not command or len(command.encode()) > 16_384 or "\x00" in command:
                _fail("PROVIDER_SCHEMA_DRIFT", "Fixture command is invalid")
            _request, _send_result, raw = self._call(
                ("terminal", "send", "--terminal", terminal_id, "--text", command, "--enter", "--json")
            )
            envelopes.append(raw)
        except LifecycleError:
            if worktree_path is None:
                raise
            return ProviderDispatchResult(
                outcome="PARTIAL",
                provider_request_id=provider_request_id,
                provider_dispatch_id=provider_dispatch_id,
                worker_id=worker_id,
                terminal_id=terminal_id,
                worktree_id=f"path:{worktree_path}",
                response_digest=_digest(envelopes),
            )
        return ProviderDispatchResult(
            outcome="APPLIED",
            provider_request_id=provider_request_id,
            provider_dispatch_id=provider_dispatch_id,
            worker_id=worker_id,
            terminal_id=terminal_id,
            worktree_id=f"path:{worktree_path}",
            response_digest=_digest(envelopes),
        )

    def dispatch_fixture(self, **kwargs: Any) -> ProviderDispatchResult:
        return self._fixture_start(prior_provider_dispatch_id=None, **kwargs)

    def retry_fixture(self, **kwargs: Any) -> ProviderDispatchResult:
        prior = kwargs.pop("prior_provider_dispatch_id")
        return self._fixture_start(prior_provider_dispatch_id=prior, **kwargs)

    def dispatch_model(
        self,
        *,
        provider_run_id: str,
        provider_task_id: str,
        logical_dispatch_id: str,
        task_spec: dict[str, Any],
        attempt_generation: int,
    ) -> ProviderDispatchResult:
        runtime = self.model_runtime
        if (
            runtime is None
            or task_spec.get("placement") != "child_worktree"
            or task_spec.get("archetype") != "model"
            or attempt_generation != 1
        ):
            _fail("CAPABILITY_UNAVAILABLE", "Model worker runtime is not admitted")
        provider_run_id = _token(provider_run_id)
        provider_task_id = _token(provider_task_id)
        logical_dispatch_id = _token(logical_dispatch_id)
        request_id, result, raw = self._call(
            (
                "orchestration",
                "worker-start",
                "--task",
                provider_task_id,
                "--worktree",
                "new-top-level",
                "--agent",
                runtime.agent,
                "--name",
                f"aether-model-{logical_dispatch_id[:8]}",
                "--repo",
                runtime.repo_selector,
                "--base-branch",
                runtime.base_ref,
                "--display-name",
                f"AETHER-MODEL-{task_spec['task_key']}",
                "--comment",
                f"aether-model:{runtime.expected_model}:{logical_dispatch_id}",
                "--setup",
                "skip",
                "--timeout-ms",
                str(runtime.timeout_ms),
                "--run",
                provider_run_id,
                "--from",
                self.coordinator_handle,
                "--json",
            )
        )
        provider_dispatch_id = _entity_id(result, entity="dispatch")
        _show_request_id, show_result, show_raw = self._call(
            (
                "orchestration",
                "worker-show",
                "--dispatch",
                provider_dispatch_id,
                "--json",
            )
        )
        identities = {"start": result, "show": show_result}
        terminal_id = _find_string(
            identities,
            ("agentTerminalHandle", "terminalHandle", "terminalId", "terminal_id", "handle"),
        )
        try:
            worker_id = _find_string(identities, ("workerId", "worker_id", "agentId"))
        except LifecycleError:
            worker_id = terminal_id
        worktree_path = _find_path(identities, ("worktreePath", "worktree_path", "path"))
        return ProviderDispatchResult(
            outcome="APPLIED",
            provider_request_id=request_id,
            provider_dispatch_id=provider_dispatch_id,
            worker_id=worker_id,
            terminal_id=terminal_id,
            worktree_id=f"path:{worktree_path}",
            response_digest=_digest((raw, show_raw)),
        )

    def observe_model_worker(self, provider_dispatch_id: str) -> ModelWorkerObservation:
        provider_dispatch_id = _token(provider_dispatch_id)
        _request_id, result, raw = self._call(
            (
                "orchestration",
                "worker-read",
                "--dispatch",
                provider_dispatch_id,
                "--source",
                "auto",
                "--limit",
                "200",
                "--json",
            )
        )
        encoded = json.dumps(raw, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
        source = result.get("source", "terminal")
        if source not in {"terminal", "transcript"}:
            _fail("PROVIDER_SCHEMA_DRIFT", "Orca worker-read returned an unknown source")
        transcript = result.get("transcript")
        messages = transcript.get("messages") if isinstance(transcript, dict) else None
        if messages is not None and not isinstance(messages, list):
            _fail("PROVIDER_RESPONSE_INVALID", "Orca worker transcript is malformed")
        activity_observed = source == "transcript" and bool(messages)
        terminal = result.get("terminal")
        tail = terminal.get("tail") if isinstance(terminal, dict) else None
        if tail is not None and (not isinstance(tail, list) or any(not isinstance(line, str) for line in tail)):
            _fail("PROVIDER_RESPONSE_INVALID", "Orca worker terminal tail is malformed")
        terminal_text = "\n".join(tail or []).lower()
        blocked_reason = None
        for reason, patterns in (
            ("auth", ("authentication required", "log in", "sign in", "unauthorized")),
            ("model", ("unknown model", "invalid model", "model is not supported")),
            ("quota", ("usage limit", "rate limit", "quota exceeded")),
            ("hook", ("hooks need review",)),
            ("launch", ("command not found", "no such file or directory")),
            ("network", ("connection error", "network error")),
        ):
            if any(pattern in terminal_text for pattern in patterns):
                blocked_reason = reason
                break
        idle_hint = (
            source == "terminal"
            and "openai codex" in terminal_text
            and "model:" in terminal_text
            and "directory:" in terminal_text
            and blocked_reason is None
        )
        return ModelWorkerObservation(
            source=source,
            activity_observed=activity_observed,
            idle_hint=idle_hint,
            blocked_reason=blocked_reason,
            response_digest=hashlib.sha256(encoded).hexdigest(),
            response_bytes=len(encoded),
        )

    def submit_model_worker_enter(self, terminal_id: str) -> ProviderEffectResult:
        terminal_id = _token(terminal_id)
        request_id, result, raw = self._call(
            ("terminal", "send", "--terminal", terminal_id, "--enter", "--json")
        )
        send = result.get("send")
        if not isinstance(send, dict) or send.get("accepted") is not True:
            _fail("PROVIDER_EFFECT_FAILED", "Orca did not accept the model worker submit recovery")
        return ProviderEffectResult("APPLIED", request_id, (), _digest(raw), True)

    def send_worker_message(
        self,
        *,
        provider_run_id: str,
        provider_task_id: str,
        provider_dispatch_id: str,
        terminal_id: str,
        from_coordinator: bool,
        kind: str,
        payload: dict[str, Any],
        outcome: str | None,
        provider_reply_to: str | None = None,
    ) -> ProviderMessageResult:
        provider_run_id = _token(provider_run_id)
        provider_task_id = _token(provider_task_id)
        provider_dispatch_id = _token(provider_dispatch_id)
        terminal_id = _token(terminal_id)
        body = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        if kind == "completion_reference":
            if outcome not in {"SUCCEEDED", "FAILED"}:
                _fail("PROVIDER_RESPONSE_INVALID", "Worker completion outcome is invalid")
            request_id, _result, raw = self._call(
                (
                    "orchestration",
                    "task-update",
                    "--id",
                    provider_task_id,
                    "--status",
                    "completed" if outcome == "SUCCEEDED" else "failed",
                    "--run",
                    provider_run_id,
                    "--from",
                    self.coordinator_handle,
                    "--json",
                )
            )
            if request_id is None:
                _fail("PROVIDER_RESPONSE_INVALID", "Orca task update omitted its request identity")
            return ProviderMessageResult("APPLIED", request_id, _digest(raw))
        if kind == "reply" or (kind == "dependency_handoff" and provider_reply_to is not None):
            if provider_reply_to is None:
                _fail("MESSAGE_CORRELATION_INVALID", "Reply lacks the provider message identity")
            _request, result, raw = self._call(
                (
                    "orchestration",
                    "reply",
                    "--id",
                    _token(provider_reply_to),
                    "--body",
                    body,
                    "--run",
                    provider_run_id,
                    "--from",
                    self.coordinator_handle,
                    "--json",
                )
            )
            return ProviderMessageResult(
                "APPLIED",
                _find_string(result, ("messageId", "deliveryId", "id")),
                _digest(raw),
            )
        argv: list[str] = [
            "orchestration",
            "send",
            "--subject",
            f"Aether {kind}",
            "--run",
            provider_run_id,
            "--from",
            self.coordinator_handle if from_coordinator else terminal_id,
        ]
        if from_coordinator:
            argv.extend(("--to", f"dispatch:{provider_dispatch_id}"))
        message_type = {"technical_question": "question", "reply": "guidance"}.get(kind, kind)
        argv.extend(("--body", body, "--type", message_type))
        argv.append("--json")
        _request, result, raw = self._call(tuple(argv))
        return ProviderMessageResult(
            outcome="APPLIED",
            provider_message_id=_find_string(result, ("messageId", "deliveryId", "id")),
            response_digest=_digest(raw),
        )

    def stop_worker(self, *, provider_dispatch_id: str, **_kwargs: Any) -> ProviderEffectResult:
        provider_dispatch_id = _token(provider_dispatch_id)
        runtime_kind = _kwargs.get("runtime_kind", "fixture")
        if runtime_kind == "model":
            request_id, _result, raw = self._call(
                ("orchestration", "worker-stop", "--dispatch", provider_dispatch_id, "--json")
            )
            return ProviderEffectResult("APPLIED", request_id, (), _digest(raw), True)
        if runtime_kind != "fixture":
            _fail("CAPABILITY_UNAVAILABLE", "Worker runtime kind is unsupported")
        worktree_id = _token(_kwargs.get("worktree_id"))
        request_id, _result, raw = self._call(
            ("terminal", "stop", "--worktree", worktree_id, "--json")
        )
        return ProviderEffectResult("APPLIED", request_id, (), _digest(raw), True)

    def cleanup_worker(
        self,
        *,
        provider_dispatch_id: str,
        terminal_id: str,
        worktree_id: str,
        runtime_kind: str = "fixture",
    ) -> ProviderEffectResult:
        resources = (_token(provider_dispatch_id), _token(terminal_id), _token(worktree_id))
        envelopes: list[dict[str, Any]] = []
        request_id: str | None = None
        try:
            if runtime_kind == "model":
                request_id, _result, raw = self._call(
                    ("orchestration", "worker-stop", "--dispatch", resources[0], "--json")
                )
            elif runtime_kind == "fixture":
                request_id, _result, raw = self._call(
                    ("terminal", "stop", "--worktree", resources[2], "--json")
                )
            else:
                _fail("CAPABILITY_UNAVAILABLE", "Worker runtime kind is unsupported")
            envelopes.append(raw)
            _request, _result, raw = self._call(
                ("worktree", "rm", "--worktree", resources[2], "--force", "--json")
            )
            envelopes.append(raw)
        except LifecycleError:
            return ProviderEffectResult("FAILED", request_id, resources, _digest(envelopes), False)
        return ProviderEffectResult("APPLIED", request_id, (), _digest(envelopes), True)

    def close(self, *, provider_run_id: str, effect_plan: tuple[str, ...]) -> ProviderEffectResult:
        projection = self.inspect_run(provider_run_id=provider_run_id)
        survivors = projection.live_resource_ids
        terminal = all(task.status in _TERMINAL_TASKS for task in projection.tasks)
        return ProviderEffectResult(
            outcome="APPLIED" if terminal and not survivors else "FAILED",
            provider_request_id=None,
            resource_ids=survivors,
            response_digest=_digest(
                {
                    "effect_plan": effect_plan,
                    "provider_run_id": provider_run_id,
                    "source": projection.source,
                    "tasks": [(task.provider_task_id, task.status) for task in projection.tasks],
                }
            ),
            cleanup_complete=terminal and not survivors,
        )
