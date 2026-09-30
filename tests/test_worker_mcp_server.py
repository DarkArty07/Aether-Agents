"""Focused tests for the aether-worker MCP server."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

from aether_agents.worker_mcp_server import (
    create_worker_mcp_server,
    discover_worker_tool_definitions,
    dispatch_worker_call,
    is_worker_tool,
)


@pytest.fixture
def disposable_board(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create a minimal Kanban database for tool dispatch tests using native connect."""
    from hermes_cli import kanban_db

    db_file = tmp_path / "kanban.db"
    conn = kanban_db.connect(db_path=db_file)
    task_self = kanban_db.create_task(conn, title="Self Task", assignee="implementer")
    task_foreign = kanban_db.create_task(conn, title="Foreign Task", assignee="implementer")

    # Set status to running and give task_self a claim lock
    conn.execute(
        "UPDATE tasks SET status = 'running', current_run_id = 1, claim_lock = 'lock_self' WHERE id = ?",
        (task_self,),
    )
    conn.execute(
        "UPDATE tasks SET status = 'running', current_run_id = 2, claim_lock = 'lock_foreign' WHERE id = ?",
        (task_foreign,),
    )
    conn.commit()
    conn.close()

    monkeypatch.setenv("HERMES_KANBAN_DB", str(db_file))
    monkeypatch.setenv("HERMES_KANBAN_TASK", task_self)
    monkeypatch.setenv("HERMES_KANBAN_RUN_ID", "1")
    monkeypatch.setenv("HERMES_KANBAN_CLAIM_LOCK", "lock_self")
    monkeypatch.setenv("HERMES_PROFILE", "implementer")
    monkeypatch.setenv("HERMES_KANBAN_BOARD", "default")
    monkeypatch.setenv("HERMES_KANBAN_WORKSPACE", str(tmp_path))

    return db_file


def test_is_worker_tool_membership():
    # Included tools
    assert is_worker_tool("kanban_show")
    assert is_worker_tool("kanban_complete")
    assert is_worker_tool("kanban_block")
    assert is_worker_tool("kanban_request_review")
    assert is_worker_tool("kanban_request_changes")
    assert is_worker_tool("kanban_comment")
    assert is_worker_tool("kanban_create")
    assert is_worker_tool("kanban_heartbeat")
    assert is_worker_tool("kanban_link")
    assert is_worker_tool("kanban_attach")
    assert is_worker_tool("kanban_attach_url")
    assert is_worker_tool("kanban_attachments")
    assert is_worker_tool("project_knowledge")
    assert is_worker_tool("work_memory")

    # Excluded tools per plan §3.9
    assert not is_worker_tool("terminal")
    assert not is_worker_tool("execute_code")
    assert not is_worker_tool("read_file")
    assert not is_worker_tool("write_file")
    assert not is_worker_tool("patch")
    assert not is_worker_tool("search_files")
    assert not is_worker_tool("web_search")
    assert not is_worker_tool("web_extract")
    assert not is_worker_tool("memory")
    assert not is_worker_tool("session_search")
    assert not is_worker_tool("skill_manage")
    assert not is_worker_tool("skill_view")
    assert not is_worker_tool("skills_list")
    assert not is_worker_tool("delegate_task")
    assert not is_worker_tool("todo")
    assert not is_worker_tool("clarify")
    assert not is_worker_tool("process")
    assert not is_worker_tool("vision_analyze")
    assert not is_worker_tool("objective_contract")
    assert not is_worker_tool("morfeo_bootstrap")


def test_discover_worker_tool_definitions(disposable_board: Path):
    tools = discover_worker_tool_definitions()
    names = {t["function"]["name"] for t in tools}

    # Must contain essential Kanban worker tools
    expected_kanban = {
        "kanban_show",
        "kanban_complete",
        "kanban_block",
        "kanban_request_review",
        "kanban_request_changes",
        "kanban_comment",
        "kanban_create",
        "kanban_heartbeat",
        "kanban_link",
        "kanban_attach",
        "kanban_attach_url",
        "kanban_attachments",
    }
    assert expected_kanban.issubset(names)

    # Must not contain any excluded tools
    for tool_name in names:
        assert is_worker_tool(tool_name)


def test_create_worker_mcp_server_instance(disposable_board: Path):
    server = create_worker_mcp_server()
    assert server.name == "aether-worker"
    tool_names = [t.name for t in server._tool_manager.list_tools()]
    assert "kanban_show" in tool_names
    assert "kanban_complete" in tool_names
    assert "terminal" not in tool_names
    assert "read_file" not in tool_names


def test_dispatch_worker_call_native_handler(disposable_board: Path):
    task_self = os.environ["HERMES_KANBAN_TASK"]
    # Calling kanban_show on self task
    result_str = dispatch_worker_call("kanban_show", {"task_id": task_self})
    data = json.loads(result_str)
    assert data["task"]["id"] == task_self
    assert data["task"]["title"] == "Self Task"


def test_dispatch_worker_call_foreign_task_rejected(disposable_board: Path):
    # Foreign task mutation should be rejected by _enforce_worker_task_ownership
    result_str = dispatch_worker_call(
        "kanban_complete", {"task_id": "t_foreign_task", "summary": "done"}
    )
    assert "refusing to mutate" in result_str or "scoped to task" in result_str


def test_argument_forwarding_drops_none(disposable_board: Path, monkeypatch: pytest.MonkeyPatch):
    task_self = os.environ["HERMES_KANBAN_TASK"]
    # Verify that only supplied (non-None) arguments are forwarded
    recorded_args: dict[str, Any] = {}

    def spy_dispatch(name: str, args: dict[str, Any]) -> str:
        recorded_args.update(args)
        return "ok"

    monkeypatch.setattr("aether_agents.worker_mcp_server.dispatch_worker_call", spy_dispatch)

    server = create_worker_mcp_server()
    show_tool = next(t for t in server._tool_manager.list_tools() if t.name == "kanban_show")

    # FastMCP calls tool handler with arguments
    show_tool.fn(task_id=task_self, board=None)
    assert "task_id" in recorded_args
    assert "board" not in recorded_args  # None was dropped!
