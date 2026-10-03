"""PD-71 PreToolUse hook adapter for Claude Code.

Translates Claude PreToolUse hook payloads into the contract expected by
the unchanged Aether policy (policy/hooks/aether_pre_tool_policy.py) and
enforces fail-closed blocking per specs/external-implementer-harness/plan.md §3.10.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

BLOCK_EXIT = 2
HOOK_TIMEOUT_SECONDS = 5.0


def resolve_policy_path() -> Path | None:
    """Resolve the path to the unchanged aether_pre_tool_policy.py."""
    env_path = os.environ.get("AETHER_PRE_TOOL_POLICY_PATH", "").strip()
    if env_path:
        p = Path(env_path).resolve()
        if p.is_file():
            return p
        return None

    hermes_home = os.environ.get("HERMES_HOME", "").strip()
    if hermes_home:
        home = Path(hermes_home).resolve()
        candidates = [
            home / "hooks" / "aether_pre_tool_policy.py",
            home / "profiles" / "implementer" / "hooks" / "aether_pre_tool_policy.py",
        ]
        for c in candidates:
            if c.is_file():
                return c
        return None

    # Standard state root location for implementer profile
    state_candidates = [
        Path.home()
        / ".local"
        / "state"
        / "aether"
        / "hermes"
        / "profiles"
        / "implementer"
        / "hooks"
        / "aether_pre_tool_policy.py",
        Path.home()
        / ".hermes"
        / "profiles"
        / "implementer"
        / "hooks"
        / "aether_pre_tool_policy.py",
    ]
    for c in state_candidates:
        if c.is_file():
            return c

    return None


def translate_tool_payload(
    tool_name: str, tool_input: dict[str, Any]
) -> tuple[str, dict[str, Any]]:
    """Translate Claude's tool names and inputs into Aether's policy contract.

    - Bash -> terminal (command)
    - Write -> write_file (path, content)
    - Edit / MultiEdit / NotebookEdit -> patch (path, edit details)
    - mcp__aether-worker__<tool> -> <tool> with original arguments
    - Other tools keep their name and input
    """
    if tool_name == "Bash":
        return "terminal", {"command": tool_input.get("command", "")}

    if tool_name == "Write":
        path_val = tool_input.get("path") or tool_input.get("file_path") or ""
        content_val = tool_input.get("content", "")
        return "write_file", {"path": path_val, "content": content_val}

    if tool_name in ("Edit", "MultiEdit", "NotebookEdit"):
        path_val = (
            tool_input.get("path")
            or tool_input.get("file_path")
            or tool_input.get("notebook_path")
            or ""
        )
        translated_args = dict(tool_input)
        translated_args["path"] = path_val
        return "patch", translated_args

    prefix = "mcp__aether-worker__"
    if tool_name.startswith(prefix):
        stripped_name = tool_name[len(prefix) :]
        return stripped_name, dict(tool_input)

    return tool_name, dict(tool_input)


def log_hook_call(payload: dict[str, Any], translated_name: str, decision: str) -> None:
    """Record call details and permission_mode in the bounded attempt log."""
    log_path = os.environ.get("AETHER_HOOK_LOG_PATH", "").strip()
    if not log_path:
        return
    try:
        record = {
            "tool_name": payload.get("tool_name"),
            "translated_name": translated_name,
            "permission_mode": payload.get("permission_mode"),
            "decision": decision,
        }
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, separators=(",", ":")) + "\n")
    except Exception:
        pass


def evaluate_hook(raw_stdin: str) -> int:
    """Evaluate one PreToolUse hook invocation, returning the process exit code."""
    try:
        payload = json.loads(raw_stdin)
    except Exception as exc:
        print(f"aether-pd71-hook: invalid JSON on stdin: {exc}", file=sys.stderr)
        return BLOCK_EXIT

    if not isinstance(payload, dict):
        print("aether-pd71-hook: payload is not a JSON object", file=sys.stderr)
        return BLOCK_EXIT

    tool_name = payload.get("tool_name")
    if not isinstance(tool_name, str) or not tool_name.strip():
        print("aether-pd71-hook: missing or invalid tool_name", file=sys.stderr)
        return BLOCK_EXIT

    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        tool_input = {}

    translated_name, translated_input = translate_tool_payload(tool_name, tool_input)

    policy_path = resolve_policy_path()
    if policy_path is None:
        print("aether-pd71-hook: aether_pre_tool_policy.py not found", file=sys.stderr)
        log_hook_call(payload, translated_name, "block:missing_policy")
        return BLOCK_EXIT

    policy_payload = {
        "hook_event_name": "pre_tool_call",
        "tool_name": translated_name,
        "tool_input": translated_input,
    }

    try:
        proc = subprocess.run(
            [sys.executable, str(policy_path)],
            input=json.dumps(policy_payload),
            text=True,
            capture_output=True,
            timeout=HOOK_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired:
        print("aether-pd71-hook: policy evaluation timed out", file=sys.stderr)
        log_hook_call(payload, translated_name, "block:timeout")
        return BLOCK_EXIT
    except Exception as exc:
        print(f"aether-pd71-hook: error executing policy: {exc}", file=sys.stderr)
        log_hook_call(payload, translated_name, "block:exec_error")
        return BLOCK_EXIT

    if proc.returncode == 0:
        log_hook_call(payload, translated_name, "allow")
        return 0

    # Policy blocked the call
    reason = "policy block"
    try:
        out_json = json.loads(proc.stdout)
        if isinstance(out_json, dict) and "reason" in out_json:
            reason = str(out_json["reason"])
    except Exception:
        if proc.stderr:
            reason = proc.stderr.strip()

    print(f"aether-pd71-hook: {reason}", file=sys.stderr)
    log_hook_call(payload, translated_name, f"block:{reason}")
    return BLOCK_EXIT


def main() -> int:
    try:
        raw_input = sys.stdin.read()
    except Exception as exc:
        print(f"aether-pd71-hook: failed to read stdin: {exc}", file=sys.stderr)
        return BLOCK_EXIT

    return evaluate_hook(raw_input)


if __name__ == "__main__":
    raise SystemExit(main())
