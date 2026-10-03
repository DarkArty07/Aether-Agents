"""Focused tests for PD-71 PreToolUse hook adapter."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aether_agents.pd71_claude_hook import (
    BLOCK_EXIT,
    evaluate_hook,
    translate_tool_payload,
)


@pytest.fixture
def isolated_policy(tmp_path: Path) -> Path:
    """Provide a real, unchanged aether_pre_tool_policy.py under an implementer profile directory."""
    repo_policy = (
        Path(__file__).resolve().parents[1] / "policy" / "hooks" / "aether_pre_tool_policy.py"
    )
    target_dir = tmp_path / "profiles" / "implementer" / "hooks"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_policy = target_dir / "aether_pre_tool_policy.py"
    target_policy.write_bytes(repo_policy.read_bytes())
    target_policy.chmod(0o755)
    return target_policy


def test_translate_bash():
    name, args = translate_tool_payload("Bash", {"command": "git status"})
    assert name == "terminal"
    assert args == {"command": "git status"}


def test_translate_write():
    name, args = translate_tool_payload("Write", {"file_path": "foo.txt", "content": "hello"})
    assert name == "write_file"
    assert args == {"path": "foo.txt", "content": "hello"}


def test_translate_edit_multiedit_notebookedit():
    name1, args1 = translate_tool_payload(
        "Edit", {"file_path": "a.py", "old_string": "x", "new_string": "y"}
    )
    assert name1 == "patch"
    assert args1["path"] == "a.py"
    assert args1["old_string"] == "x"

    name2, args2 = translate_tool_payload("MultiEdit", {"file_path": "b.py", "edits": []})
    assert name2 == "patch"
    assert args2["path"] == "b.py"

    name3, args3 = translate_tool_payload(
        "NotebookEdit", {"notebook_path": "c.ipynb", "new_source": "z"}
    )
    assert name3 == "patch"
    assert args3["path"] == "c.ipynb"


def test_translate_mcp_worker_tool():
    name, args = translate_tool_payload(
        "mcp__aether-worker__kanban_create",
        {"title": "test task", "body": "do something"},
    )
    assert name == "kanban_create"
    assert args == {"title": "test task", "body": "do something"}


def test_translate_other_tool():
    name, args = translate_tool_payload("CustomTool", {"x": 1, "y": 2})
    assert name == "CustomTool"
    assert args == {"x": 1, "y": 2}


def test_evaluate_hook_allowed_call(isolated_policy: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AETHER_PRE_TOOL_POLICY_PATH", str(isolated_policy))
    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": "git status"},
        "permission_mode": "bypassPermissions",
    }
    code = evaluate_hook(json.dumps(payload))
    assert code == 0


def test_evaluate_hook_blocked_destructive_command(
    isolated_policy: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
):
    monkeypatch.setenv("AETHER_PRE_TOOL_POLICY_PATH", str(isolated_policy))
    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": "rm -rf /"},
        "permission_mode": "bypassPermissions",
    }
    code = evaluate_hook(json.dumps(payload))
    assert code == BLOCK_EXIT
    err = capsys.readouterr().err
    assert "DESTRUCTIVE" in err


def test_evaluate_hook_blocked_credential_command(
    isolated_policy: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
):
    monkeypatch.setenv("AETHER_PRE_TOOL_POLICY_PATH", str(isolated_policy))
    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": "gh auth login"},
        "permission_mode": "bypassPermissions",
    }
    code = evaluate_hook(json.dumps(payload))
    assert code == BLOCK_EXIT
    err = capsys.readouterr().err
    assert "CREDENTIAL" in err


def test_evaluate_hook_blocked_secret_in_tool_args(
    isolated_policy: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
):
    monkeypatch.setenv("AETHER_PRE_TOOL_POLICY_PATH", str(isolated_policy))
    fake_token = "gh" + "p_" + ("x" * 30)
    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Write",
        "tool_input": {"file_path": "code.py", "content": f"token = '{fake_token}'"},
        "permission_mode": "bypassPermissions",
    }
    code = evaluate_hook(json.dumps(payload))
    assert code == BLOCK_EXIT
    err = capsys.readouterr().err
    assert "CREDENTIAL" in err


def test_evaluate_hook_truncation_sentinel_in_kanban_create(
    isolated_policy: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
):
    monkeypatch.setenv("AETHER_PRE_TOOL_POLICY_PATH", str(isolated_policy))
    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "mcp__aether-worker__kanban_create",
        "tool_input": {"title": "task title", "body": "task body ...[truncated]"},
        "permission_mode": "bypassPermissions",
    }
    code = evaluate_hook(json.dumps(payload))
    assert code == BLOCK_EXIT
    err = capsys.readouterr().err
    assert "TRUNCATION" in err


def test_evaluate_hook_malformed_input(capsys: pytest.CaptureFixture):
    assert evaluate_hook("not-json") == BLOCK_EXIT
    assert evaluate_hook(json.dumps(["not", "dict"])) == BLOCK_EXIT
    assert evaluate_hook(json.dumps({"tool_input": {}})) == BLOCK_EXIT  # missing tool_name


def test_evaluate_hook_missing_policy(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setenv("AETHER_PRE_TOOL_POLICY_PATH", str(tmp_path / "nonexistent.py"))
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": "ls"},
    }
    code = evaluate_hook(json.dumps(payload))
    assert code == BLOCK_EXIT


def test_evaluate_hook_timeout(
    isolated_policy: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    slow_policy = tmp_path / "slow_policy.py"
    slow_policy.write_text("import time; time.sleep(10)", encoding="utf-8")
    monkeypatch.setenv("AETHER_PRE_TOOL_POLICY_PATH", str(slow_policy))
    monkeypatch.setattr("aether_agents.pd71_claude_hook.HOOK_TIMEOUT_SECONDS", 0.2)

    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": "ls"},
    }
    code = evaluate_hook(json.dumps(payload))
    assert code == BLOCK_EXIT


def test_evaluate_hook_logs_permission_mode(
    isolated_policy: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    log_file = tmp_path / "hook.log"
    monkeypatch.setenv("AETHER_PRE_TOOL_POLICY_PATH", str(isolated_policy))
    monkeypatch.setenv("AETHER_HOOK_LOG_PATH", str(log_file))

    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": "echo test"},
        "permission_mode": "bypassPermissions",
    }
    evaluate_hook(json.dumps(payload))

    assert log_file.is_file()
    record = json.loads(log_file.read_text(encoding="utf-8").strip())
    assert record["permission_mode"] == "bypassPermissions"
    assert record["tool_name"] == "Bash"
    assert record["translated_name"] == "terminal"
    assert record["decision"] == "allow"
