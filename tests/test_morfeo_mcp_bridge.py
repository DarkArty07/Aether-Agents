"""Mode filter, bootstrap gate and per-client isolation."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from aether_agents.mcp.bridge import ToolBridge
from aether_agents.mcp.context import build_snapshot, section_record
from aether_agents.mcp.contracts import (
    HOST_DUPLICATE_TOOLS,
    MORFEO_CONTEXT_REQUIRED,
    MorfeoMcpError,
    visible_tool_names,
)
from aether_agents.mcp.session import SessionTable


def _definition(name: str) -> dict:
    return {"type": "function", "function": {"name": name, "parameters": {"type": "object"}}}


SURFACE = [
    "terminal",
    "process",
    "read_file",
    "write_file",
    "patch",
    "search_files",
    "execute_code",
    "memory",
    "kanban_create",
    "objective_contract",
    "mcp__context7__resolve",
]


def test_harness_hides_host_duplicates_and_external_mcp() -> None:
    visible = visible_tool_names(set(SURFACE), "harness")
    assert HOST_DUPLICATE_TOOLS.isdisjoint(visible)
    assert "memory" in visible
    assert "kanban_create" in visible
    assert "objective_contract" in visible
    assert "mcp__context7__resolve" not in visible


def test_chatbot_keeps_host_tools_and_drops_external_mcp() -> None:
    visible = visible_tool_names(set(SURFACE), "chatbot")
    assert HOST_DUPLICATE_TOOLS <= visible
    assert "mcp__context7__resolve" not in visible


def test_bootstrap_is_required_then_idempotent(tmp_path: Path) -> None:
    calls: list[str] = []

    def on_bootstrap(session):
        calls.append(session.client_key)
        session.task_id = "task-1"
        session.agent = object()
        return build_snapshot(
            sections={
                "soul": "soul",
                "user": "",
                "memory": "",
                "project_context": "",
                "skills": "",
            },
            role="morfeo",
            mode="harness",
            project_id="project",
            project_root=str(tmp_path),
            tool_names=["memory"],
        )

    bridge = ToolBridge(
        sessions=SessionTable(),
        definitions=[_definition(name) for name in ("memory", "terminal")],
        mode="harness",
        invoke=lambda agent, name, arguments, task_id, tool_call_id: f"{name}:{task_id}",
        on_bootstrap=on_bootstrap,
    )
    session = bridge.ensure("client-a", project_id="project", project_root=tmp_path)
    with pytest.raises(MorfeoMcpError, match=MORFEO_CONTEXT_REQUIRED):
        bridge.call(session, "memory", {})
    first = bridge.bootstrap(session)
    second = bridge.bootstrap(session)
    assert first["context_revision"] == second["context_revision"]
    assert calls == ["client-a"]
    assert bridge.call(session, "memory", {}) == "memory:task-1"
    with pytest.raises(MorfeoMcpError, match="not on this surface"):
        bridge.call(session, "terminal", {})


def test_clients_do_not_share_bootstrap_or_tasks(tmp_path: Path) -> None:
    def on_bootstrap(session):
        session.task_id = f"task-{session.client_key}"
        session.agent = object()
        return build_snapshot(
            sections={},
            role="morfeo",
            mode="chatbot",
            project_id="project",
            project_root=str(tmp_path),
            tool_names=["memory"],
        )

    bridge = ToolBridge(
        sessions=SessionTable(),
        definitions=[_definition("memory")],
        mode="chatbot",
        invoke=lambda agent, name, arguments, task_id, tool_call_id: task_id,
        on_bootstrap=on_bootstrap,
    )
    left = bridge.ensure("a", project_id="project", project_root=tmp_path)
    right = bridge.ensure("b", project_id="project", project_root=tmp_path)
    bridge.bootstrap(left)
    assert not right.bootstrapped
    bridge.bootstrap(right)
    assert left.task_id != right.task_id
    assert bridge.call(left, "memory", {}) == "task-a"
    assert bridge.call(right, "memory", {}) == "task-b"


def test_snapshot_redacts_secrets_and_logs_omit_text() -> None:
    record = section_record("memory", "note\napi_key=super-secret\n")
    assert "super-secret" not in record["text"]
    assert record["redacted_lines"] == 1
    snapshot = build_snapshot(
        sections={"memory": "api_key=super-secret"},
        role="morfeo",
        mode="harness",
        project_id="p",
        project_root="/tmp/project",
        tool_names=["memory"],
    )
    from aether_agents.mcp.context import log_records

    logged = log_records(snapshot)
    assert "text" not in logged[0]
    assert "super-secret" not in str(logged)


def test_bootstrap_preserves_packaged_soul_task_instructions() -> None:
    soul = (
        Path(__file__).resolve().parents[1] / "src/aether_agents/resources/profiles/morfeo/SOUL.md"
    ).read_text(encoding="utf-8")
    assert "task-coverage evidence" in soul
    assert "task-relevant Aether Canonical Skills" in soul

    snapshot = build_snapshot(
        sections={"soul": soul},
        role="morfeo",
        mode="chatbot",
        project_id="project",
        project_root="/tmp/project",
        tool_names=[],
    )
    delivered = snapshot["sections"]["soul"]
    assert "task-coverage evidence" in delivered["text"]
    assert "task-relevant Aether Canonical Skills" in delivered["text"]
    assert delivered["redacted_lines"] == 0


def test_mixed_bootstrap_redacts_only_synthetic_secrets_and_logs_metadata() -> None:
    mixed = "\n".join(
        [
            "task-coverage evidence",
            "api_key=" + "A" * 16,
            "task-relevant Aether Canonical Skills",
            "Bearer sk-" + "B" * 16,
            "authorization: Bearer " + "C" * 16,
            "123456:" + "D" * 24,
        ]
    )
    snapshot = build_snapshot(
        sections={"soul": mixed, "memory": "ordinary memory note"},
        role="morfeo",
        mode="chatbot",
        project_id="project",
        project_root="/tmp/project",
        tool_names=[],
    )
    soul = snapshot["sections"]["soul"]
    assert soul["text"].splitlines() == [
        "task-coverage evidence",
        "[redacted]",
        "task-relevant Aether Canonical Skills",
        "[redacted]",
        "[redacted]",
        "[redacted]",
    ]
    assert soul["redacted_lines"] == 4
    assert soul["bytes"] == len(soul["text"].encode("utf-8"))
    assert soul["sha256"] == hashlib.sha256(soul["text"].encode("utf-8")).hexdigest()
    assert snapshot["sections"]["memory"]["text"] == "ordinary memory note"
    assert snapshot["sections"]["memory"]["redacted_lines"] == 0
    for name in ("user", "project_context", "skills"):
        assert snapshot["sections"][name]["text"] == ""
        assert snapshot["sections"][name]["redacted_lines"] == 0
    from aether_agents.mcp.context import log_records

    logged = log_records(snapshot)
    assert all("text" not in record for record in logged)
    assert next(record for record in logged if record["section"] == "soul")["redacted_lines"] == 4
    assert "A" * 16 not in str(logged)
    assert "B" * 16 not in str(logged)
