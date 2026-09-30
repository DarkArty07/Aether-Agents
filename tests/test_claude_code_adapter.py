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
    # Self process has cwd somewhere else or in tmp_path
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


def test_adapter_scenario_native_transition(
    test_board: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    # Stub Claude that performs a native transition via kanban_request_review
    task_id = test_board["task_id"]
    db_file = test_board["db"]

    script = f"""
import sys, json, os, sqlite3

# Read lines from stdin or stream
print(json.dumps({{'type': 'system', 'subtype': 'init', 'permissionMode': 'bypassPermissions', 'tools': ['mcp__aether-worker__kanban_request_review']}}), flush=True)

# Read work prompt sent by adapter
sys.stdin.readline()

# Simulate transition in db
conn = sqlite3.connect({repr(str(db_file))})
conn.execute("UPDATE tasks SET status = 'review', current_run_id = 1 WHERE id = '{task_id}'")
conn.execute("INSERT INTO task_events (task_id, run_id, kind, created_at) VALUES ('{task_id}', 1, 'review_requested', 100)")
conn.commit()
conn.close()

sys.exit(0)
"""
    stub = _create_stub_claude(tmp_path, script)
    monkeypatch.setenv("AETHER_CLAUDE_BIN", str(stub))

    argv = ["aether-kanban-worker", "chat", "-q", "prompt"]
    code = run_attempt(argv, test_board["env"])
    assert code == 0

    # Receipt exists with outcome review_requested
    receipt_dir = state_root() / "external_harness" / "default" / task_id / "run_1"
    receipt = json.loads((receipt_dir / "receipt.json").read_text(encoding="utf-8"))
    assert receipt["outcome"] in ("review_requested", "review")
    assert receipt["fallback"] is False


def test_adapter_scenario_clean_no_transition_exits_76(
    test_board: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    # Stub Claude exits 0 without transitioning the task
    script = """
import sys, json
print(json.dumps({'type': 'system', 'subtype': 'init', 'permissionMode': 'bypassPermissions', 'tools': ['mcp__aether-worker__kanban_show']}), flush=True)
sys.stdin.readline()
sys.exit(0)
"""
    stub = _create_stub_claude(tmp_path, script)
    monkeypatch.setenv("AETHER_CLAUDE_BIN", str(stub))

    argv = ["aether-kanban-worker", "chat", "-q", "prompt"]
    code = run_attempt(argv, test_board["env"])
    assert code == 76

    task_id = test_board["task_id"]
    receipt_dir = state_root() / "external_harness" / "default" / task_id / "run_1"
    receipt = json.loads((receipt_dir / "receipt.json").read_text(encoding="utf-8"))
    assert receipt["outcome"] == "clean_no_transition"
    assert receipt["exit_status"] == 76


def test_adapter_scenario_readiness_failure_falls_back(
    test_board: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    # Stub Claude emits permissionMode manual (bypass off)
    script = """
import sys, json
print(json.dumps({'type': 'system', 'subtype': 'init', 'permissionMode': 'manual', 'tools': []}), flush=True)
sys.exit(0)
"""
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
    target_exec, target_args = execv_calls[0]
    assert "chat" in target_args

    # Check fallback receipt
    task_id = test_board["task_id"]
    receipt_dir = state_root() / "external_harness" / "default" / task_id / "run_1"
    receipt = json.loads((receipt_dir / "receipt.json").read_text(encoding="utf-8"))
    assert receipt["fallback"] is True
    assert receipt["cause"] == "readiness_failed"


def test_adapter_scenario_api_retry_auth_falls_back(
    test_board: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    # Stub Claude emits readiness ok, reads prompt, then api_retry with authentication_failed
    script = """
import sys, json
print(json.dumps({'type': 'system', 'subtype': 'init', 'permissionMode': 'bypassPermissions', 'tools': ['mcp__aether-worker__kanban_show']}), flush=True)
sys.stdin.readline()
print(json.dumps({'type': 'system', 'subtype': 'api_retry', 'error_category': 'authentication_failed'}), flush=True)
sys.exit(1)
"""
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
    # Stub Claude emits readiness ok, reads prompt, then exits 1
    script = """
import sys, json
print(json.dumps({'type': 'system', 'subtype': 'init', 'permissionMode': 'bypassPermissions', 'tools': ['mcp__aether-worker__kanban_show']}), flush=True)
sys.stdin.readline()
sys.exit(1)
"""
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
    # Stub exits 1, but single writer check fails
    script = """
import sys, json
print(json.dumps({'type': 'system', 'subtype': 'init', 'permissionMode': 'bypassPermissions', 'tools': ['mcp__aether-worker__kanban_show']}), flush=True)
sys.stdin.readline()
sys.exit(1)
"""
    stub = _create_stub_claude(tmp_path, script)
    monkeypatch.setenv("AETHER_CLAUDE_BIN", str(stub))

    monkeypatch.setattr(
        "aether_agents.claude_code_adapter.check_single_writer", lambda ws, pid: False
    )

    argv = ["aether-kanban-worker", "chat", "-q", "prompt"]
    code = run_attempt(argv, test_board["env"])
    # Must NOT fall back, exits 1
    assert code == 1

    task_id = test_board["task_id"]
    receipt_dir = state_root() / "external_harness" / "default" / task_id / "run_1"
    receipt = json.loads((receipt_dir / "receipt.json").read_text(encoding="utf-8"))
    assert receipt["outcome"] == "fallback_rejected_surviving_writer"
    assert receipt["fallback"] is False


def test_adapter_scenario_claim_lost_never_falls_back(
    test_board: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    # Claim lock changed on board during execution
    conn = sqlite3.connect(str(test_board["db"]))
    conn.execute(
        "UPDATE tasks SET claim_lock = 'different_lock' WHERE id = ?", (test_board["task_id"],)
    )
    conn.commit()
    conn.close()

    script = """
import sys, json
print(json.dumps({'type': 'system', 'subtype': 'init', 'permissionMode': 'bypassPermissions', 'tools': ['mcp__aether-worker__kanban_show']}), flush=True)
sys.stdin.readline()
sys.exit(1)
"""
    stub = _create_stub_claude(tmp_path, script)
    monkeypatch.setenv("AETHER_CLAUDE_BIN", str(stub))

    argv = ["aether-kanban-worker", "chat", "-q", "prompt"]
    code = run_attempt(argv, test_board["env"])
    # Claim lost -> exits without fallback
    assert code != 0
    task_id = test_board["task_id"]
    receipt_dir = state_root() / "external_harness" / "default" / task_id / "run_1"
    receipt = json.loads((receipt_dir / "receipt.json").read_text(encoding="utf-8"))
    assert receipt["outcome"] == "claim_lost"
    assert receipt["fallback"] is False
