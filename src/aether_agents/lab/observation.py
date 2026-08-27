"""Deterministic observation qualification lane for the formal laboratory."""

from __future__ import annotations

import json
import os
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
        f'project_id = "{project_id}"\n', encoding="utf-8"
    )
    state = root / "state"
    paths = ObservationPaths.for_project(project_id, root=state / "aether")
    ProjectRegistry(root=state / "aether" / "projects").register(project_id, project, "lab")
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


def _invoke_registered_tool(project: Path, trace_id: str, paths: ObservationPaths) -> dict[str, Any]:
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
    compact = {key: value for key, value in record.items() if key not in {"trace_seeded", "project_registered"}}
    validate_evidence(compact)
    evidence = run_root / "evidence"
    evidence.mkdir(parents=True, exist_ok=True)
    (evidence / "observation.json").write_text(
        json.dumps(compact, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return compact


def live_observation(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
    """Live observation remains owner/provider-authorized and is not run in I1."""
    return {
        "schema_version": "aether.lab.evidence.v1",
        "kind": "observation",
        "status": "CAPABILITY_WALL",
        "mode": "live-persistent",
        "suite": "observation",
        "reason": "live_observation_requires_explicit_runtime_authority",
    }
