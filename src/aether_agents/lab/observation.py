"""Deterministic observation qualification lane for the formal laboratory."""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import uuid
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterator

from aether_agents import product_version
from aether_agents.observation.capture.journal import JournalWriter
from aether_agents.observation.capture.projectors import EventBuilder
from aether_agents.observation.context import ProjectRegistry
from aether_agents.observation.contracts import validate_event
from aether_agents.paths import ObservationPaths

from .validation import validate_evidence


class _ToolContext:
    profile_name = "morfeo"

    def __init__(self) -> None:
        self.handler: Any = None
        self.unload_callbacks: list[Any] = []

    def get_config(self, key: str, default: object = None) -> object:
        return True if key == "curated_tool" else default

    def register_tool(self, **kwargs: Any) -> None:
        self.handler = kwargs.get("handler")

    def register_hook(self, _name: str, _callback: Any) -> None:
        return None

    def on_unload(self, callback: Any) -> None:
        self.unload_callbacks.append(callback)


@contextmanager
def _environment(values: dict[str, str]) -> Iterator[None]:
    previous = {key: os.environ.get(key) for key in values}
    os.environ.update(values)
    try:
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _seed_trace(root: Path) -> tuple[Path, ObservationPaths, str, str]:
    project_id = str(uuid.uuid4())
    trace_id = "ctr_" + uuid.uuid4().hex
    project = root / "project"
    (project / ".aether").mkdir(parents=True, exist_ok=True)
    (project / ".aether" / "project.toml").write_text(
        "\n".join(
            (
                "schema_version = 1",
                f'project_id = "{project_id}"',
                'name = "Aether observation laboratory"',
                f'initialized_by = "{product_version()}"',
                'forge = "local"',
                'contract_root = "specs"',
                'default_branch = "main"',
                "",
            )
        ),
        encoding="utf-8",
    )
    state = root / "state"
    paths = ObservationPaths.for_project(project_id, root=state / "aether")
    ProjectRegistry(root=state / "aether").register(project_id, project, "lab")
    builder = EventBuilder(
        trace_id=trace_id,
        project_id=project_id,
        collector_version=product_version(),
        runtime_fingerprint="0" * 64,
        normalizer_ref="hermes.tool-category.v1",
    )
    events = [
        builder.contract(
            event_type="trace.opened",
            status="started",
            origin_message_id=1,
            actor_kind="owner",
            actor_id="owner",
            profile=None,
            source_kind="aether_checkpoint",
            timestamp_source="native",
        ),
        builder.contract(
            event_type="contract.executable",
            status="passed",
            semantic_delta="invariant",
            actor_kind="agent",
            actor_id="morfeo",
            profile="morfeo",
            role="verification",
            source_kind="aether_checkpoint",
        ),
        builder.contract(
            event_type="contract.completion_verified",
            status="verified",
            evidence_refs=("evidence-1",),
            semantic_delta="evidence",
            actor_kind="agent",
            actor_id="morfeo",
            profile="morfeo",
            role="verification",
            source_kind="aether_checkpoint",
        ),
        builder.contract(
            event_type="trace.closed",
            status="completed",
            actor_kind="agent",
            actor_id="morfeo",
            profile="morfeo",
            role="verification",
            source_kind="aether_checkpoint",
        ),
    ]
    writer = JournalWriter(paths=paths, producer_epoch="prd_" + uuid.uuid4().hex)
    writer.open()
    try:
        for event in events:
            validate_event(event)
            assert writer.append(event).accepted
    finally:
        writer.close()
    return project, paths, project_id, trace_id


def _invoke_registered_tool(
    project: Path, trace_id: str, paths: ObservationPaths
) -> dict[str, Any]:
    from aether_agents.observation.capture import hermes_plugin

    context = _ToolContext()
    hermes_plugin.register(context)
    if not callable(context.handler):
        raise RuntimeError("aether_observe was not registered")
    try:
        status_raw = context.handler({"action": "status", "project": str(project), "ref": trace_id})
        status = json.loads(status_raw)
        if not isinstance(status, dict) or status.get("state") != "ready":
            raise RuntimeError("registered status call did not return a ready result")
        current_summary_id = status.get("summary_id")
        if not isinstance(current_summary_id, str):
            raise RuntimeError("status call did not return a summary identity")
        changes_raw = context.handler(
            {
                "action": "changes",
                "project": str(project),
                "ref": trace_id,
                "since_summary_id": current_summary_id,
            }
        )
        diagnose_raw = context.handler(
            {"action": "diagnose", "project": str(project), "ref": trace_id}
        )
        outputs = {
            "status": json.loads(status_raw),
            "changes": json.loads(changes_raw),
            "diagnose": json.loads(diagnose_raw),
        }
        calls: list[dict[str, Any]] = []
        limits = {"status": 2048, "changes": 2048, "diagnose": 4096}
        for action in ("status", "changes", "diagnose"):
            value = outputs[action]
            encoded = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
            calls.append(
                {
                    "action": action,
                    "success": isinstance(value, dict) and value.get("action") == action,
                    "bytes": len(encoded.encode("utf-8")),
                    "limit": limits[action],
                }
            )
        record = {
            "schema_version": "aether.lab.evidence.v1",
            "kind": "observation",
            "status": "PREPARED" if all(call["success"] for call in calls) else "FAIL",
            "mode": "prepare-only",
            "suite": "observation",
            "registered_tool": "aether_observe",
            "calls": calls,
            "content_redacted": True,
            "rolling_reliability_counted": False,
        }
        validate_evidence(record)
        return record
    finally:
        for callback in reversed(context.unload_callbacks):
            callback()


def prepare_observation_only(run_root: Path) -> dict[str, Any]:
    """Seed a real local trace and exercise all three registered tool actions."""
    run_root = run_root.expanduser().resolve()
    if run_root.exists() and any(run_root.iterdir()):
        raise ValueError("observation run root must be absent or empty")
    run_root.mkdir(parents=True, exist_ok=True)
    project, paths, project_id, trace_id = _seed_trace(run_root)
    with _environment(
        {
            "XDG_STATE_HOME": str(run_root / "state"),
            "AETHER_PROJECT_ID": project_id,
            "HERMES_HOME": str(run_root / "hermes-home" / "profiles" / "morfeo"),
        }
    ):
        record = _invoke_registered_tool(project, trace_id, paths)
    record = deepcopy(record)
    record["trace_seeded"] = True
    record["project_registered"] = True
    # Keep only fields in the canonical schema in exported evidence.
    compact = {
        key: value
        for key, value in record.items()
        if key not in {"trace_seeded", "project_registered"}
    }
    validate_evidence(compact)
    evidence = run_root / "evidence"
    evidence.mkdir(parents=True, exist_ok=True)
    (evidence / "observation.json").write_text(
        json.dumps(compact, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return compact


_LIVE_ACTIONS = ("status", "changes", "diagnose")
_LIVE_LIMITS = {"status": 2048, "changes": 2048, "diagnose": 4096}
_LIVE_PROMPT = """Use the registered aether_observe tool for this qualification attempt.
Call exactly these actions once, in order: status, changes (using the returned
summary identity), and diagnose. Do not use terminal, file, patch, shell, raw
logs, or any other fallback tool. Return only a short completion confirmation.
"""


def _bounded_identifier(value: Any) -> str:
    """Keep model/provider labels useful without retaining arbitrary config text."""
    if not isinstance(value, str):
        return "unavailable"
    value = value.strip()
    if not value or len(value) > 128 or any(ord(char) < 32 for char in value):
        return "unavailable"
    return value


def _read_usage_summary(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    api_calls = payload.get("api_calls")
    if not isinstance(api_calls, int) or isinstance(api_calls, bool) or api_calls < 0:
        api_calls = 0
    failed = payload.get("failed") is True
    return {
        "model": _bounded_identifier(payload.get("model")),
        "provider": _bounded_identifier(payload.get("provider")),
        "api_calls": api_calls,
        "provider_operationally_exercised": api_calls > 0 and not failed,
    }


def _json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return decoded if isinstance(decoded, dict) else {}
    return {}


def _tool_call_name(value: Any) -> str | None:
    if not isinstance(value, dict):
        return None
    function = value.get("function")
    if isinstance(function, dict):
        value = function
    name = value.get("name")
    return name.strip() if isinstance(name, str) and name.strip() else None


def _tool_call_arguments(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    function = value.get("function")
    if isinstance(function, dict):
        value = function
    return _json_object(value.get("arguments") or value.get("args"))


def _session_tool_calls(hermes_root: Path) -> list[tuple[str, dict[str, Any], dict[str, Any]]]:
    """Read names and bounded JSON results from disposable Hermes transcripts.

    Hermes's public session store has stable ``messages`` columns for role,
    tool-call request, tool name, and tool result. Only tool names, action labels,
    and the parsed result object are retained by the caller; this function never
    returns prompts, responses, session IDs, or raw errors.
    """
    result_rows: list[tuple[str, dict[str, Any], dict[str, Any]]] = []
    requested_rows: list[tuple[str, dict[str, Any], dict[str, Any]]] = []
    for database in sorted((hermes_root / "profiles").glob("*/state.db")):
        try:
            with sqlite3.connect(database) as connection:
                rows = connection.execute(
                    "SELECT role, content, tool_name, tool_calls FROM messages"
                ).fetchall()
        except (OSError, sqlite3.Error):
            continue
        for role, content, tool_name, tool_calls in rows:
            if isinstance(tool_name, str) and tool_name.strip():
                result = _json_object(content)
                result_rows.append((tool_name.strip(), result, result))
            if role != "assistant":
                continue
            calls = tool_calls
            if isinstance(calls, str):
                try:
                    calls = json.loads(calls)
                except json.JSONDecodeError:
                    calls = []
            if not isinstance(calls, list):
                continue
            for call in calls:
                name = _tool_call_name(call)
                if name is not None:
                    requested_rows.append((name, _tool_call_arguments(call), {}))

    # Tool-result rows contain the actual bounded result and avoid counting each
    # successful call twice alongside its assistant request row. Preserve every
    # result row, including empty results from a failed/fallback tool, then add
    # only assistant requests that have no corresponding result row. This keeps
    # fallback detection complete without retaining transcript content.
    result_keys: dict[tuple[str, str | None], int] = {}
    for name, _action_args, result in result_rows:
        action = result.get("action") if isinstance(result, dict) else None
        key = (name, action if isinstance(action, str) else None)
        result_keys[key] = result_keys.get(key, 0) + 1
    merged = list(result_rows)
    for name, action_args, result in requested_rows:
        action = action_args.get("action") if isinstance(action_args, dict) else None
        key = (name, action if isinstance(action, str) else None)
        if result_keys.get(key, 0):
            result_keys[key] -= 1
            continue
        merged.append((name, action_args, result))
    return merged


def _live_call_evidence(
    calls: list[tuple[str, dict[str, Any], dict[str, Any]]],
) -> tuple[list[dict[str, Any]], int, dict[str, int]]:
    observed: dict[str, list[dict[str, Any]]] = {action: [] for action in _LIVE_ACTIONS}
    fallback = {"terminal": 0, "file": 0, "raw_logs_events": 0}
    for name, arguments, result in calls:
        lowered = name.casefold()
        if name == "aether_observe":
            action = result.get("action") or arguments.get("action")
            if action in observed:
                encoded = json.dumps(
                    result,
                    sort_keys=True,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
                observed[action].append(
                    {
                        "action": action,
                        "success": result.get("action") == action,
                        "bytes": len(encoded.encode("utf-8")),
                        "limit": _LIVE_LIMITS[action],
                    }
                )
            continue
        if lowered in {"terminal", "shell", "run_command"} or "terminal" in lowered:
            fallback["terminal"] += 1
        if lowered in {"read_file", "write_file", "patch", "file"} or "file" in lowered:
            fallback["file"] += 1
        if any(token in lowered for token in ("raw", "log", "event")):
            fallback["raw_logs_events"] += 1

    compact_calls: list[dict[str, Any]] = []
    for action in _LIVE_ACTIONS:
        entries = observed[action]
        compact_calls.append(
            entries[0]
            if entries
            else {
                "action": action,
                "success": False,
                "bytes": 0,
                "limit": _LIVE_LIMITS[action],
            }
        )
    return compact_calls, sum(len(entries) for entries in observed.values()), fallback


def _remove_disposable_runtime(run_root: Path, hermes_root: Path | None) -> int:
    targets = [
        hermes_root,
        run_root / "project",
        run_root / "state",
        run_root / "xdg-state",
        run_root / "xdg-data",
        run_root / "hook-backup",
        run_root / "worktrees",
        run_root / "kanban.db",
        run_root / ".usage.json",
        run_root / ".commands.jsonl",
    ]
    try:
        for target in targets:
            if target is None or not target.exists():
                continue
            if target.is_dir() and not target.is_symlink():
                shutil.rmtree(target)
            else:
                target.unlink()
    except OSError:
        return sum(target is not None and target.exists() for target in targets)
    return sum(target is not None and target.exists() for target in targets)


def live_observation(
    run_root: Path,
    *,
    hermes: Path,
    profile_root: Path,
    allow_model_spend: bool,
) -> dict[str, Any]:
    """Run one explicit, provider-backed Morfeo observation attempt.

    The caller must supply the exact Hermes executable, candidate profile root,
    and spend acknowledgement. The attempt uses disposable roots and exports
    only compact observation metadata; provider/session transcripts are removed.
    """
    if not allow_model_spend:
        raise ValueError("live observation requires --allow-model-spend")
    hermes = Path(hermes).expanduser().resolve()
    profile_root = Path(profile_root).expanduser().resolve()
    if not hermes.is_file() or not os.access(hermes, os.X_OK):
        raise ValueError("live observation Hermes executable is missing or not executable")
    if not profile_root.is_dir():
        raise ValueError("live observation profile root is missing")

    from .runner import (
        HarnessError,
        _hermes_env,
        _invoke_morfeo,
        _safe_run_root,
        _source_status,
        prepare_profiles,
    )

    run_root = _safe_run_root(Path(run_root))
    evidence_dir = run_root / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    command_log = run_root / ".commands.jsonl"
    usage_path = run_root / ".usage.json"
    hermes_root: Path | None = None
    project: Path | None = None
    paths: ObservationPaths | None = None
    project_id: str | None = None
    trace_id: str | None = None
    usage = {
        "model": "unavailable",
        "provider": "unavailable",
        "api_calls": 0,
        "provider_operationally_exercised": False,
    }
    calls: list[dict[str, Any]] = [
        {"action": action, "success": False, "bytes": 0, "limit": _LIVE_LIMITS[action]}
        for action in _LIVE_ACTIONS
    ]
    aether_observe_calls = 0
    fallback = {"terminal": 0, "file": 0, "raw_logs_events": 0}
    failure_reason = "live_observation_failed"
    invocation_completed = False
    source_before: str | None = None
    source_after: str | None = None
    try:
        project, paths, project_id, trace_id = _seed_trace(run_root)
        hermes_root = prepare_profiles(profile_root, run_root, command_log)
        env = _hermes_env(run_root, hermes_root, hermes)
        env.update(
            {
                "XDG_STATE_HOME": str(run_root / "state"),
                "XDG_DATA_HOME": str(run_root / "xdg-data"),
                "AETHER_PROJECT_ID": project_id,
                "AETHER_OBSERVATION_TRACE_ID": trace_id,
            }
        )
        source_before = _source_status(command_log, env)
        _invoke_morfeo(
            hermes,
            hermes_root,
            project,
            env,
            command_log,
            run_root,
            _LIVE_PROMPT,
            resume_session_id=None,
            usage_name=".usage.json",
            observation_route=True,
        )
        invocation_completed = True
        usage = _read_usage_summary(usage_path)
        live_calls = _session_tool_calls(hermes_root)
        calls, aether_observe_calls, fallback = _live_call_evidence(live_calls)
        source_after = _source_status(command_log, env)
        failure_reason = "live_observation_qualification_failed"
    except (HarnessError, OSError, RuntimeError):
        # Keep the exported failure class stable; subprocess output and exception
        # text are deliberately not carried into evidence.
        usage = _read_usage_summary(usage_path)
    finally:
        cleanup_survivors = _remove_disposable_runtime(run_root, hermes_root)
    cleanup_complete = cleanup_survivors == 0

    isolation_verified = all(
        target is not None and (target == run_root or run_root in target.parents)
        for target in (hermes_root, project, paths.root if paths is not None else None)
    )
    all_calls_succeeded = all(call["success"] for call in calls)
    source_changed = (
        source_before is not None and source_after is not None and source_before != source_after
    )
    status = (
        "PASS"
        if invocation_completed
        and usage["provider_operationally_exercised"]
        and aether_observe_calls >= len(_LIVE_ACTIONS)
        and all_calls_succeeded
        and not any(fallback.values())
        and isolation_verified
        and cleanup_complete
        and not source_changed
        else "FAIL"
    )
    record = {
        "schema_version": "aether.lab.evidence.v1",
        "kind": "observation",
        "status": status,
        "mode": "live-oneshot",
        "suite": "observation",
        "model": usage["model"],
        "provider": usage["provider"],
        "api_calls": usage["api_calls"],
        "provider_operationally_exercised": usage["provider_operationally_exercised"],
        "registered_tool": "aether_observe",
        "aether_observe_calls": aether_observe_calls,
        "calls": calls,
        "forbidden_fallback_counts": fallback,
        "isolation_verified": isolation_verified,
        "cleanup": {"completed": cleanup_complete, "survivors": cleanup_survivors},
        "private_runtime_retained": cleanup_survivors > 0,
        "aether_self_modification": source_changed,
        "content_redacted": True,
        "rolling_reliability_counted": False,
    }
    if status != "PASS":
        record["reason"] = failure_reason
    validate_evidence(record)
    (evidence_dir / "observation.json").write_text(
        json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return record
