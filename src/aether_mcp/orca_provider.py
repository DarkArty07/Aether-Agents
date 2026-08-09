"""Exact-build adapter for the admitted public Orca orchestration CLI."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable
from typing import Any, NoReturn

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


def _field(record: dict[str, Any], *names: str) -> Any:
    for name in names:
        if name in record:
            return record[name]
    return None


class PublicOrcaLifecycleProvider:
    """Provider adapter restricted to public structured commands and exact argv."""

    def __init__(
        self,
        *,
        transport: Callable[[tuple[str, ...]], dict[str, Any]],
        binding_digest: str,
        coordinator_handle: str,
    ) -> None:
        if not callable(transport):
            raise TypeError("Structured Orca transport is required")
        if not isinstance(binding_digest, str) or re.fullmatch(r"[0-9a-f]{64}", binding_digest) is None:
            _fail("PROVIDER_SCHEMA_DRIFT", "Orca binding digest is invalid")
        self.transport = transport
        self.binding_digest = binding_digest
        self.coordinator_handle = _token(coordinator_handle)

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
