"""Focused tests for Claude Code adapter, readiness gate, lifecycle, and fallback."""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any

import pytest

from aether_agents.claude_code_adapter import (
    check_single_writer,
    get_required_worker_tools,
    resolve_hermes_passthrough,
    run_attempt,
    write_receipt,
)
from aether_agents.claude_context import (
    build_appended_context,
    build_first_user_message,
    build_skills_plugin,
    parse_pinned_skills,
)
from aether_agents.paths import state_root


@pytest.fixture
def test_board(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    from hermes_cli import kanban_db

    db_file = tmp_path / "kanban.db"
    conn = kanban_db.connect(db_path=db_file)
    task_id = kanban_db.create_task(conn, title="Test Task", assignee="implementer")

    conn.execute(
        "UPDATE tasks SET status = 'running', current_run_id = 1, claim_lock = 'lock_test' WHERE id = ?",
        (task_id,),
    )
    conn.commit()
    conn.close()

    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)

    env = {
        "HERMES_KANBAN_DB": str(db_file),
        "HERMES_KANBAN_TASK": task_id,
        "HERMES_KANBAN_RUN_ID": "1",
        "HERMES_KANBAN_CLAIM_LOCK": "lock_test",
        "HERMES_PROFILE": "implementer",
        "HERMES_KANBAN_BOARD": "default",
        "HERMES_KANBAN_WORKSPACE": str(workspace),
        "PATH": os.environ.get("PATH", ""),
        "XDG_STATE_HOME": str(tmp_path / "state"),
        "AETHER_READINESS_TIMEOUT": "2.0",
    }
    for k, v in env.items():
        monkeypatch.setenv(k, v)

    return {"db": db_file, "task_id": task_id, "workspace": workspace, "env": env}


def test_parse_pinned_skills():
    argv = ["aether-kanban-worker", "chat", "-q", "prompt", "--skills", "alpha,beta", "-s", "gamma"]
    skills = parse_pinned_skills(argv)
    assert skills == ["alpha", "beta", "gamma"]


def test_build_context_contains_required_sections(test_board: dict[str, Any]):
    context = build_appended_context(
        task_id=test_board["task_id"],
        workspace=test_board["workspace"],
        pinned_skills=["alpha"],
    )
    assert test_board["task_id"] in context
    assert "Tool Equivalence Table" in context
    assert "Role SOUL: Implementer" in context
    assert "Canonical Procedure: Implementation and Unit Evidence" in context
    assert "Kanban task execution protocol" in context
    assert "`terminal`" in context and "`Bash`" in context


def test_build_skills_plugin(tmp_path: Path):
    plugin_dir = tmp_path / "test_plugin"
    build_skills_plugin(plugin_dir)

    manifest = plugin_dir / ".claude-plugin" / "plugin.json"
    assert manifest.is_file()
    data = json.loads(manifest.read_text(encoding="utf-8"))
    assert data["name"] == "aether-implementer-skills"

    skills_dir = plugin_dir / "skills"
    assert (skills_dir / "implementation-evidence" / "SKILL.md").is_file()
    assert (skills_dir / "git-github-closeout" / "SKILL.md").is_file()


def test_build_first_user_message(test_board: dict[str, Any]):
    msg = build_first_user_message(test_board["db"], test_board["task_id"])
    assert msg.startswith(f"Work Aether Kanban task {test_board['task_id']}.")
    assert "Test Task" in msg


def test_check_single_writer_self_only(tmp_path: Path):
    assert check_single_writer(tmp_path, os.getpid())


def test_resolve_hermes_passthrough():
    target, args = resolve_hermes_passthrough({"PATH": "/dummy"})
    assert target == sys.executable
    assert args == [sys.executable, "-m", "hermes_cli.main"]


def test_write_receipt_fields(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    receipt_file = write_receipt(
        board="default",
        task_id="t_123",
        run_id=1,
        session_id="sess_abc",
        harness_version="2.1.285",
        start_utc="2026-09-30T10:00:00Z",
        end_utc="2026-09-30T10:05:00Z",
        readiness_summary={
            "permission_mode": "bypassPermissions",
            "mcp_connected": True,
            "hook_active": True,
            "mcp_status": "connected",
            "mcp_tools": ["kanban_show"],
        },
        outcome="completed",
        cause=None,
        fallback=False,
        exit_status=0,
    )
    assert receipt_file.is_file()
    data = json.loads(receipt_file.read_text(encoding="utf-8"))
    assert data["schema"] == "aether.harness-receipt.v1"
    assert data["harness"] == "claude-code"
    assert data["harness_version"] == "2.1.285"
    assert data["session_id"] == "sess_abc"
    assert data["outcome"] == "completed"
    assert data["fallback"] is False
    assert data["exit_status"] == 0
    assert data["readiness_summary"]["mcp_status"] == "connected"


def test_get_required_worker_tools_derives_and_fails_closed(monkeypatch: pytest.MonkeyPatch):
    import aether_agents.worker_mcp_server as server

    monkeypatch.setattr(
        server,
        "discover_worker_tool_definitions",
        lambda: [
            {"function": {"name": "kanban_show"}},
            {"function": {"name": "kanban_complete"}},
            {"not": "a tool"},
        ],
    )
    assert get_required_worker_tools({}) == {"kanban_show", "kanban_complete"}

    def _unavailable() -> list[dict[str, Any]]:
        raise RuntimeError("discovery unavailable")

    monkeypatch.setattr(server, "discover_worker_tool_definitions", _unavailable)
    assert get_required_worker_tools({}) == set()

    monkeypatch.setattr(server, "discover_worker_tool_definitions", lambda: [])
    assert get_required_worker_tools({}) == set()


def _create_stub_claude(tmp_path: Path, script_body: str, run_hooks: bool = True) -> Path:
    stub = tmp_path / f"stub_claude_{time.time_ns()}.py"
    hook_runner = (
        """
import sys, json, os

if "--settings" in sys.argv:
    idx = sys.argv.index("--settings")
    if idx + 1 < len(sys.argv):
        try:
            with open(sys.argv[idx + 1], "r", encoding="utf-8") as f:
                s_data = json.load(f)
            for grp in s_data.get("hooks", {}).get("SessionStart", []):
                for hk in grp.get("hooks", []):
                    os.system(hk["command"])
        except Exception:
            pass
"""
        if run_hooks
        else ""
    )
    stub.write_text(f"#!{sys.executable}\n{hook_runner}\n{script_body}", encoding="utf-8")
    stub.chmod(0o755)
    return stub


def _make_handshake_body(
    *,
    permission_mode: str = "bypassPermissions",
    mcp_status: str = "connected",
    tools: list[str] | None = None,
    mcp_req_id_mismatch: bool = False,
    mcp_req_id_missing: bool = False,
    other_servers: list[dict[str, Any]] | None = None,
    post_handshake: str = "",
) -> str:
    if tools is None:
        tools = sorted(get_required_worker_tools({}))

    servers: list[dict[str, Any]] = [
        {
            "name": "aether-worker",
            "status": mcp_status,
            "tools": [{"name": t} for t in tools],
        }
    ]
    if other_servers:
        servers.extend(other_servers)

    servers_json = json.dumps(servers)

    return f"""
import sys, json

# 1. Read initialize request
init_line = sys.stdin.readline()
init_req = json.loads(init_line) if init_line.strip() else {{}}
init_id = init_req.get("request_id")

# Respond to initialize
init_resp = json.dumps({{
    "type": "control_response",
    "response": {{
        "subtype": "success",
        "request_id": init_id,
        "response": {{"current_permission_mode": "{permission_mode}"}}
    }}
}})
print(init_resp, flush=True)

# 2. Read mcp_status request
mcp_line = sys.stdin.readline()
mcp_req = json.loads(mcp_line) if mcp_line.strip() else {{}}
mcp_id = mcp_req.get("request_id")
if {mcp_req_id_mismatch}:
    mcp_id = "mismatched_req_id_999"

mcp_resp = {{
    "type": "control_response",
    "response": {{
        "subtype": "success",
        "response": {{
            "mcpServers": {servers_json}
        }}
    }}
}}
if not {mcp_req_id_missing} and mcp_id is not None:
    mcp_resp["response"]["request_id"] = mcp_id

mcp_resp_str = json.dumps(mcp_resp)
print(mcp_resp_str, flush=True)

# Corroborating system/init
print(json.dumps({{"type": "system", "subtype": "init", "permissionMode": "{permission_mode}"}}), flush=True)

{post_handshake}
"""


def test_adapter_scenario_native_transition(
    test_board: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    task_id = test_board["task_id"]
    db_file = str(test_board["db"])

    execv_called = []
    monkeypatch.setattr(
        os, "execv", lambda target, args: execv_called.append((target, args)) or sys.exit(99)
    )

    post = f"""
# Read work prompt written after readiness succeeds
sys.stdin.readline()

# Simulate transition in db
import sqlite3
conn = sqlite3.connect({repr(db_file)})
conn.execute("UPDATE tasks SET status = 'review', current_run_id = 1 WHERE id = '{task_id}'")
conn.execute("INSERT INTO task_events (task_id, run_id, kind, created_at) VALUES ('{task_id}', 1, 'review_requested', 100)")
conn.commit()
conn.close()

sys.exit(0)
"""
    script = _make_handshake_body(post_handshake=post)
    stub = _create_stub_claude(tmp_path, script)
    monkeypatch.setenv("AETHER_CLAUDE_BIN", str(stub))

    argv = ["aether-kanban-worker", "chat", "-q", "prompt"]
    code = run_attempt(argv, test_board["env"])
    assert execv_called == []
    assert code == 0

    receipt_dir = state_root() / "external_harness" / "default" / task_id / "run_1"
    receipt = json.loads((receipt_dir / "receipt.json").read_text(encoding="utf-8"))
    assert receipt["outcome"] in ("review_requested", "review")
    assert receipt["fallback"] is False
    assert receipt["readiness_summary"]["mcp_connected"] is True
    assert receipt["readiness_summary"]["hook_active"] is True
    assert receipt["readiness_summary"]["permission_mode"] == "bypassPermissions"


def test_adapter_scenario_clean_no_transition_exits_76(
    test_board: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    execv_calls: list[tuple[str, list[str]]] = []
    monkeypatch.setattr(
        os, "execv", lambda target, args: execv_calls.append((target, args)) or sys.exit(99)
    )

    post = """
sys.stdin.readline()
sys.exit(0)
"""
    script = _make_handshake_body(post_handshake=post)
    stub = _create_stub_claude(tmp_path, script)
    monkeypatch.setenv("AETHER_CLAUDE_BIN", str(stub))

    argv = ["aether-kanban-worker", "chat", "-q", "prompt"]
    code = run_attempt(argv, test_board["env"])
    assert execv_calls == []
    assert code == 76

    task_id = test_board["task_id"]
    receipt_dir = state_root() / "external_harness" / "default" / task_id / "run_1"
    receipt = json.loads((receipt_dir / "receipt.json").read_text(encoding="utf-8"))
    assert receipt["outcome"] == "clean_no_transition"
    assert receipt["exit_status"] == 76


def test_adapter_scenario_api_retry_auth_falls_back(
    test_board: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    post = """
sys.stdin.readline()
print(json.dumps({'type': 'system', 'subtype': 'api_retry', 'error_category': 'authentication_failed'}), flush=True)
sys.exit(1)
"""
    script = _make_handshake_body(post_handshake=post)
    stub = _create_stub_claude(tmp_path, script)
    monkeypatch.setenv("AETHER_CLAUDE_BIN", str(stub))

    execv_calls: list[tuple[str, list[str]]] = []

    def mock_execv(target: str, args: list[str]) -> None:
        execv_calls.append((target, args))
        raise SystemExit(99)

    monkeypatch.setattr(os, "execv", mock_execv)

    argv = ["aether-kanban-worker", "chat", "-q", "prompt"]
    with pytest.raises(SystemExit) as exc:
        run_attempt(argv, test_board["env"])
    assert exc.value.code == 99

    assert len(execv_calls) == 1
    task_id = test_board["task_id"]
    receipt_dir = state_root() / "external_harness" / "default" / task_id / "run_1"
    receipt = json.loads((receipt_dir / "receipt.json").read_text(encoding="utf-8"))
    assert receipt["fallback"] is True
    assert "api_retry" in str(receipt["cause"]) or "authentication_failed" in str(receipt["cause"])


def test_adapter_scenario_crash_falls_back(
    test_board: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    post = """
sys.stdin.readline()
sys.exit(1)
"""
    script = _make_handshake_body(post_handshake=post)
    stub = _create_stub_claude(tmp_path, script)
    monkeypatch.setenv("AETHER_CLAUDE_BIN", str(stub))

    execv_calls: list[tuple[str, list[str]]] = []

    def mock_execv(target: str, args: list[str]) -> None:
        execv_calls.append((target, args))
        raise SystemExit(99)

    monkeypatch.setattr(os, "execv", mock_execv)

    argv = ["aether-kanban-worker", "chat", "-q", "prompt"]
    with pytest.raises(SystemExit) as exc:
        run_attempt(argv, test_board["env"])
    assert exc.value.code == 99

    assert len(execv_calls) == 1
    task_id = test_board["task_id"]
    receipt_dir = state_root() / "external_harness" / "default" / task_id / "run_1"
    receipt = json.loads((receipt_dir / "receipt.json").read_text(encoding="utf-8"))
    assert receipt["fallback"] is True
    assert "non_zero_exit" in str(receipt["cause"])


def test_adapter_scenario_surviving_writer_prevents_fallback(
    test_board: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    post = """
sys.stdin.readline()
sys.exit(1)
"""
    script = _make_handshake_body(post_handshake=post)
    stub = _create_stub_claude(tmp_path, script)
    monkeypatch.setenv("AETHER_CLAUDE_BIN", str(stub))

    monkeypatch.setattr(
        "aether_agents.claude_code_adapter.check_single_writer", lambda ws, pid: False
    )

    argv = ["aether-kanban-worker", "chat", "-q", "prompt"]
    code = run_attempt(argv, test_board["env"])
    assert code == 1

    task_id = test_board["task_id"]
    receipt_dir = state_root() / "external_harness" / "default" / task_id / "run_1"
    receipt = json.loads((receipt_dir / "receipt.json").read_text(encoding="utf-8"))
    assert receipt["outcome"] == "fallback_rejected_surviving_writer"
    assert receipt["fallback"] is False


def test_adapter_scenario_claim_lost_never_falls_back(
    test_board: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    conn = sqlite3.connect(str(test_board["db"]))
    conn.execute(
        "UPDATE tasks SET claim_lock = 'different_lock' WHERE id = ?", (test_board["task_id"],)
    )
    conn.commit()
    conn.close()

    post = """
sys.stdin.readline()
sys.exit(1)
"""
    script = _make_handshake_body(post_handshake=post)
    stub = _create_stub_claude(tmp_path, script)
    monkeypatch.setenv("AETHER_CLAUDE_BIN", str(stub))

    argv = ["aether-kanban-worker", "chat", "-q", "prompt"]
    code = run_attempt(argv, test_board["env"])
    assert code != 0
    task_id = test_board["task_id"]
    receipt_dir = state_root() / "external_harness" / "default" / task_id / "run_1"
    receipt = json.loads((receipt_dir / "receipt.json").read_text(encoding="utf-8"))
    assert receipt["outcome"] == "claim_lost"
    assert receipt["fallback"] is False


def test_adapter_scenario_readiness_failure_missing_request_id(
    test_board: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    script = _make_handshake_body(mcp_req_id_missing=True, post_handshake="sys.exit(0)")
    stub = _create_stub_claude(tmp_path, script)
    monkeypatch.setenv("AETHER_CLAUDE_BIN", str(stub))

    execv_calls: list[tuple[str, list[str]]] = []
    monkeypatch.setattr(
        os, "execv", lambda target, args: execv_calls.append((target, args)) or sys.exit(99)
    )

    argv = ["aether-kanban-worker", "chat", "-q", "prompt"]
    with pytest.raises(SystemExit) as exc:
        run_attempt(argv, test_board["env"])
    assert exc.value.code == 99

    assert len(execv_calls) == 1
    task_id = test_board["task_id"]
    receipt_dir = state_root() / "external_harness" / "default" / task_id / "run_1"
    receipt = json.loads((receipt_dir / "receipt.json").read_text(encoding="utf-8"))
    assert receipt["fallback"] is True
    assert receipt["cause"] == "readiness_failed"


def test_adapter_scenario_readiness_failure_mismatched_request_id(
    test_board: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    script = _make_handshake_body(mcp_req_id_mismatch=True, post_handshake="sys.exit(0)")
    stub = _create_stub_claude(tmp_path, script)
    monkeypatch.setenv("AETHER_CLAUDE_BIN", str(stub))

    execv_calls: list[tuple[str, list[str]]] = []
    monkeypatch.setattr(
        os, "execv", lambda target, args: execv_calls.append((target, args)) or sys.exit(99)
    )

    argv = ["aether-kanban-worker", "chat", "-q", "prompt"]
    with pytest.raises(SystemExit) as exc:
        run_attempt(argv, test_board["env"])
    assert exc.value.code == 99

    assert len(execv_calls) == 1
    task_id = test_board["task_id"]
    receipt_dir = state_root() / "external_harness" / "default" / task_id / "run_1"
    receipt = json.loads((receipt_dir / "receipt.json").read_text(encoding="utf-8"))
    assert receipt["fallback"] is True
    assert receipt["cause"] == "readiness_failed"


def test_adapter_scenario_readiness_failure_status_pending(
    test_board: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    script = _make_handshake_body(mcp_status="pending", post_handshake="sys.exit(0)")
    stub = _create_stub_claude(tmp_path, script)
    monkeypatch.setenv("AETHER_CLAUDE_BIN", str(stub))

    execv_calls: list[tuple[str, list[str]]] = []
    monkeypatch.setattr(
        os, "execv", lambda target, args: execv_calls.append((target, args)) or sys.exit(99)
    )

    argv = ["aether-kanban-worker", "chat", "-q", "prompt"]
    with pytest.raises(SystemExit) as exc:
        run_attempt(argv, test_board["env"])
    assert exc.value.code == 99

    assert len(execv_calls) == 1
    task_id = test_board["task_id"]
    receipt_dir = state_root() / "external_harness" / "default" / task_id / "run_1"
    receipt = json.loads((receipt_dir / "receipt.json").read_text(encoding="utf-8"))
    assert receipt["fallback"] is True
    assert receipt["cause"] == "readiness_failed"


def test_adapter_scenario_readiness_failure_status_ready(
    test_board: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    script = _make_handshake_body(mcp_status="ready", post_handshake="sys.exit(0)")
    stub = _create_stub_claude(tmp_path, script)
    monkeypatch.setenv("AETHER_CLAUDE_BIN", str(stub))

    execv_calls: list[tuple[str, list[str]]] = []
    monkeypatch.setattr(
        os, "execv", lambda target, args: execv_calls.append((target, args)) or sys.exit(99)
    )

    argv = ["aether-kanban-worker", "chat", "-q", "prompt"]
    with pytest.raises(SystemExit) as exc:
        run_attempt(argv, test_board["env"])
    assert exc.value.code == 99

    assert len(execv_calls) == 1
    task_id = test_board["task_id"]
    receipt_dir = state_root() / "external_harness" / "default" / task_id / "run_1"
    receipt = json.loads((receipt_dir / "receipt.json").read_text(encoding="utf-8"))
    assert receipt["fallback"] is True
    assert receipt["cause"] == "readiness_failed"


def test_adapter_scenario_readiness_failure_incomplete_tools(
    test_board: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    # Only 1 tool provided; missing remaining required tools
    script = _make_handshake_body(tools=["kanban_show"], post_handshake="sys.exit(0)")
    stub = _create_stub_claude(tmp_path, script)
    monkeypatch.setenv("AETHER_CLAUDE_BIN", str(stub))

    execv_calls: list[tuple[str, list[str]]] = []
    monkeypatch.setattr(
        os, "execv", lambda target, args: execv_calls.append((target, args)) or sys.exit(99)
    )

    argv = ["aether-kanban-worker", "chat", "-q", "prompt"]
    with pytest.raises(SystemExit) as exc:
        run_attempt(argv, test_board["env"])
    assert exc.value.code == 99

    assert len(execv_calls) == 1
    task_id = test_board["task_id"]
    receipt_dir = state_root() / "external_harness" / "default" / task_id / "run_1"
    receipt = json.loads((receipt_dir / "receipt.json").read_text(encoding="utf-8"))
    assert receipt["fallback"] is True
    assert receipt["cause"] == "readiness_failed"


def test_adapter_scenario_readiness_failure_missing_nonce(
    test_board: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    # run_hooks=False prevents SessionStart hook from writing nonce
    script = _make_handshake_body(post_handshake="sys.exit(0)")
    stub = _create_stub_claude(tmp_path, script, run_hooks=False)
    monkeypatch.setenv("AETHER_CLAUDE_BIN", str(stub))

    execv_calls: list[tuple[str, list[str]]] = []
    monkeypatch.setattr(
        os, "execv", lambda target, args: execv_calls.append((target, args)) or sys.exit(99)
    )

    argv = ["aether-kanban-worker", "chat", "-q", "prompt"]
    with pytest.raises(SystemExit) as exc:
        run_attempt(argv, test_board["env"])
    assert exc.value.code == 99

    assert len(execv_calls) == 1
    task_id = test_board["task_id"]
    receipt_dir = state_root() / "external_harness" / "default" / task_id / "run_1"
    receipt = json.loads((receipt_dir / "receipt.json").read_text(encoding="utf-8"))
    assert receipt["fallback"] is True
    assert receipt["cause"] == "readiness_failed"


def test_adapter_scenario_readiness_failure_permission_mode_manual(
    test_board: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    script = _make_handshake_body(permission_mode="manual", post_handshake="sys.exit(0)")
    stub = _create_stub_claude(tmp_path, script)
    monkeypatch.setenv("AETHER_CLAUDE_BIN", str(stub))

    execv_calls: list[tuple[str, list[str]]] = []
    monkeypatch.setattr(
        os, "execv", lambda target, args: execv_calls.append((target, args)) or sys.exit(99)
    )

    argv = ["aether-kanban-worker", "chat", "-q", "prompt"]
    with pytest.raises(SystemExit) as exc:
        run_attempt(argv, test_board["env"])
    assert exc.value.code == 99

    assert len(execv_calls) == 1
    task_id = test_board["task_id"]
    receipt_dir = state_root() / "external_harness" / "default" / task_id / "run_1"
    receipt = json.loads((receipt_dir / "receipt.json").read_text(encoding="utf-8"))
    assert receipt["fallback"] is True
    assert receipt["cause"] == "readiness_failed"


def test_adapter_system_init_cannot_supply_permission_mode(
    test_board: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    script = """
import sys, json
init_line = sys.stdin.readline()
init_req = json.loads(init_line) if init_line.strip() else {}
print(json.dumps({
    "type": "control_response",
    "response": {"subtype": "error", "request_id": init_req.get("request_id"), "response": {}},
}), flush=True)
print(json.dumps({
    "type": "system", "subtype": "init", "permissionMode": "bypassPermissions",
}), flush=True)
sys.exit(0)
"""
    stub = _create_stub_claude(tmp_path, script)
    monkeypatch.setenv("AETHER_CLAUDE_BIN", str(stub))

    execv_calls: list[tuple[str, list[str]]] = []
    monkeypatch.setattr(
        os, "execv", lambda target, args: execv_calls.append((target, args)) or sys.exit(99)
    )

    argv = ["aether-kanban-worker", "chat", "-q", "prompt"]
    with pytest.raises(SystemExit) as exc:
        run_attempt(argv, test_board["env"])
    assert exc.value.code == 99
    assert len(execv_calls) == 1

    task_id = test_board["task_id"]
    receipt_dir = state_root() / "external_harness" / "default" / task_id / "run_1"
    receipt = json.loads((receipt_dir / "receipt.json").read_text(encoding="utf-8"))
    assert receipt["fallback"] is True
    assert receipt["cause"] == "readiness_failed"
    assert receipt["readiness_summary"]["permission_mode"] is None


def test_adapter_scenario_readiness_exact_closed_set_success_and_failure(
    test_board: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    closed_set = ["kanban_show", "kanban_comment", "kanban_heartbeat"]
    import aether_agents.worker_mcp_server as server

    monkeypatch.setattr(
        server,
        "discover_worker_tool_definitions",
        lambda: [{"function": {"name": name}} for name in closed_set],
    )

    execv_calls: list[tuple[str, list[str]]] = []
    monkeypatch.setattr(
        os, "execv", lambda target, args: execv_calls.append((target, args)) or sys.exit(99)
    )

    # 1. Matching exact closed set -> succeeds
    post = """
sys.stdin.readline()
sys.exit(0)
"""
    script_ok = _make_handshake_body(tools=closed_set, post_handshake=post)
    stub_ok = _create_stub_claude(tmp_path, script_ok)
    monkeypatch.setenv("AETHER_CLAUDE_BIN", str(stub_ok))

    argv = ["aether-kanban-worker", "chat", "-q", "prompt"]
    code = run_attempt(argv, test_board["env"])
    assert execv_calls == []
    assert code == 76

    # 2. Incomplete closed set (missing kanban_heartbeat) -> fails and falls back
    script_incomplete = _make_handshake_body(
        tools=["kanban_show", "kanban_comment"], post_handshake="sys.exit(0)"
    )
    stub_inc = _create_stub_claude(tmp_path, script_incomplete)
    monkeypatch.setenv("AETHER_CLAUDE_BIN", str(stub_inc))

    with pytest.raises(SystemExit) as exc:
        run_attempt(argv, test_board["env"])
    assert exc.value.code == 99
    assert len(execv_calls) == 1


def test_adapter_control_responses_filtered_from_stream_tail(
    test_board: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    other_servers = [
        {
            "name": "other-service",
            "status": "connected",
            "headers": {"Authorization": "Bearer super_secret_token_12345"},
            "env": {"API_KEY": "private_secret_key_abc"},
        }
    ]
    post = """
sys.stdin.readline()
sys.exit(1)
"""
    script = _make_handshake_body(other_servers=other_servers, post_handshake=post)
    stub = _create_stub_claude(tmp_path, script)
    monkeypatch.setenv("AETHER_CLAUDE_BIN", str(stub))

    execv_calls: list[tuple[str, list[str]]] = []
    monkeypatch.setattr(
        os, "execv", lambda target, args: execv_calls.append((target, args)) or sys.exit(99)
    )

    argv = ["aether-kanban-worker", "chat", "-q", "prompt"]
    with pytest.raises(SystemExit) as exc:
        run_attempt(argv, test_board["env"])
    assert exc.value.code == 99

    task_id = test_board["task_id"]
    receipt_dir = state_root() / "external_harness" / "default" / task_id / "run_1"

    # Verify stream tail does not contain private secrets or control responses
    tail_file = receipt_dir / "stream_tail.log"
    if tail_file.is_file():
        tail_text = tail_file.read_text(encoding="utf-8", errors="replace")
        assert "super_secret_token_12345" not in tail_text
        assert "private_secret_key_abc" not in tail_text
        assert "control_response" not in tail_text

    # Verify receipt does not contain private secrets from other servers
    receipt = json.loads((receipt_dir / "receipt.json").read_text(encoding="utf-8"))
    receipt_text = json.dumps(receipt)
    assert "super_secret_token_12345" not in receipt_text
    assert "private_secret_key_abc" not in receipt_text
