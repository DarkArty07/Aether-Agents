"""Claude Code adapter for Implementer work attempts.

Implements the official Claude Code CLI attempt lifecycle, readiness gate,
process management, outcome classification, receipts, and stateless Hermes fallback
per specs/external-implementer-harness/plan.md §3.6–§3.12 and tasks.md Decision 14a.
"""

from __future__ import annotations

import ctypes
import datetime
import json
import logging
import os
import re
import select
import shutil
import signal
import sqlite3
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any

from aether_agents.claude_context import (
    build_appended_context,
    build_first_user_message,
    build_skills_plugin,
    parse_pinned_skills,
)
from aether_agents.paths import state_root

logger = logging.getLogger("aether_agents.claude_adapter")

FORBIDDEN_FLAGS = frozenset(
    {
        "--bare",
        "--strict-mcp-config",
        "--setting-sources",
        "CLAUDE_CONFIG_DIR",
        "--model",
        "-w",
        "--worktree",
        "--continue",
        "--resume",
    }
)

RECEIPT_SCHEMA = "aether.harness-receipt.v1"
COMMENT_PREFIX = "aether-executor:"
MAX_STREAM_TAIL_BYTES = 256 * 1024  # 256 KiB ceiling per plan §3.12
HEARTBEAT_INTERVAL_SECONDS = 30.0
READINESS_TIMEOUT_SECONDS = 15.0

AUTH_BILLING_ERROR_CATEGORIES = frozenset(
    {
        "authentication_failed",
        "billing_error",
        "rate_limit",
        "account_on_hold",
    }
)


def _now_iso_utc() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def get_claude_version(claude_bin: str = "claude") -> str:
    """Retrieve installed Claude Code version string."""
    try:
        proc = subprocess.run(
            [claude_bin, "--version"],
            capture_output=True,
            text=True,
            timeout=5.0,
            check=False,
        )
        out = (proc.stdout or proc.stderr).strip()
        match = re.search(r"\b(\d+\.\d+\.\d+)\b", out)
        if match:
            return match.group(1)
        return out.split()[0] if out else "unknown"
    except Exception:
        return "unknown"


def check_single_writer(workspace: Path | str, self_pid: int) -> bool:
    """Return True if no process other than self_pid has its cwd inside workspace."""
    workspace_path = Path(workspace).resolve()
    proc_root = Path("/proc")
    if not proc_root.is_dir():
        return True

    for entry in proc_root.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            pid = int(entry.name)
            if pid == self_pid:
                continue
            cwd_link = (entry / "cwd").resolve(strict=False)
            if cwd_link == workspace_path or cwd_link.is_relative_to(workspace_path):
                logger.warning("Surviving writer found: pid %d in %s", pid, cwd_link)
                return False
        except (OSError, PermissionError, ValueError):
            continue
    return True


def check_task_state_read_only(
    db_path: Path | str, task_id: str, run_id: int | str
) -> dict[str, Any]:
    """Inspect the task state and transition events on the board read-only."""
    resolved_db = Path(db_path).resolve()
    try:
        conn = sqlite3.connect(f"file:{resolved_db}?mode=ro", uri=True)
    except sqlite3.OperationalError:
        conn = sqlite3.connect(str(resolved_db))

    cursor = conn.cursor()
    try:
        row = cursor.execute(
            "SELECT id, status, current_run_id, claim_lock FROM tasks WHERE id = ?",
            (task_id,),
        ).fetchone()
        if not row:
            return {"exists": False}

        task_data = {
            "exists": True,
            "id": row[0],
            "status": row[1],
            "current_run_id": str(row[2]) if row[2] is not None else None,
            "claim_lock": row[3],
        }

        # Check latest event produced by this run (try task_events, fallback to events)
        ev_row = None
        for table_name in ("task_events", "events"):
            try:
                ev_row = cursor.execute(
                    f"SELECT kind, payload FROM {table_name} WHERE task_id = ? AND run_id = ? "
                    "ORDER BY id DESC LIMIT 1",
                    (task_id, str(run_id)),
                ).fetchone()
                break
            except sqlite3.OperationalError:
                continue

        if ev_row:
            task_data["latest_run_event"] = ev_row[0]
        else:
            task_data["latest_run_event"] = None

        return task_data
    finally:
        conn.close()


def post_kanban_comment(task_id: str, board: str | None, body: str) -> None:
    """Post an executor comment using the native kanban tool under attempt identity."""
    try:
        import model_tools  # noqa: F401
        from tools import kanban_tools

        args: dict[str, Any] = {"task_id": task_id, "body": body}
        if board:
            args["board"] = board
        kanban_tools._handle_comment(args)
    except Exception as exc:
        logger.warning("Failed to post kanban comment: %s", exc)


def write_receipt(
    *,
    board: str,
    task_id: str,
    run_id: str | int,
    session_id: str,
    harness_version: str,
    start_utc: str,
    end_utc: str,
    readiness_summary: dict[str, Any],
    outcome: str,
    cause: str | None,
    fallback: bool,
    exit_status: int | None,
    stream_tail: bytes | None = None,
) -> Path:
    """Write aether.harness-receipt.v1 under the Aether-managed state root."""
    root = state_root()
    receipt_dir = root / "external_harness" / board / task_id / f"run_{run_id}"
    receipt_dir.mkdir(parents=True, exist_ok=True)

    receipt_data = {
        "schema": RECEIPT_SCHEMA,
        "harness": "claude-code",
        "harness_version": harness_version,
        "session_id": session_id,
        "board": board,
        "task": task_id,
        "run": str(run_id),
        "start_utc": start_utc,
        "end_utc": end_utc,
        "readiness_summary": readiness_summary,
        "outcome": outcome,
        "cause": cause,
        "fallback": fallback,
        "exit_status": exit_status,
    }

    receipt_file = receipt_dir / "receipt.json"
    receipt_file.write_text(json.dumps(receipt_data, indent=2), encoding="utf-8")

    if (fallback or exit_status not in (0, 143)) and stream_tail:
        tail_file = receipt_dir / "stream_tail.log"
        tail_file.write_bytes(stream_tail[-MAX_STREAM_TAIL_BYTES:])

    return receipt_file


def resolve_hermes_passthrough(env: dict[str, str]) -> tuple[str, list[str]]:
    """Resolve the pre-change Hermes entry point per plan §3.5 without reading HERMES_BIN."""
    path_env = env.get("PATH")
    shim = shutil.which("hermes", path=path_env)
    if shim:
        return shim, [shim]
    return sys.executable, [sys.executable, "-m", "hermes_cli.main"]


def _preexec_kill_group() -> None:
    """Run in child process to set up new process group and parent-death signal."""
    os.setsid()
    PR_SET_PDEATHSIG = 1
    try:
        libc = ctypes.CDLL("libc.so.6")
        libc.prctl(PR_SET_PDEATHSIG, signal.SIGTERM)
    except Exception:
        pass


def run_attempt(argv: list[str], env: dict[str, str]) -> int:
    """Execute an Implementer work attempt using Claude Code per plan §3.6–§3.12.

    Shared Decision 14a entry point called by the launcher:
    - `argv`: full dispatcher argument vector (argv[0] included).
    - `env`: dispatcher-built environment mapping.
    Returns:
    - 0 on native transition
    - 76 on clean exit without transition
    - 143 on propagated SIGTERM
    Does not return on fallback: replaces process with Hermes pass-through via execv.
    """
    start_utc = _now_iso_utc()
    task_id = env["HERMES_KANBAN_TASK"]
    run_id = env["HERMES_KANBAN_RUN_ID"]
    claim_lock = env["HERMES_KANBAN_CLAIM_LOCK"]
    db_path = env["HERMES_KANBAN_DB"]
    board = env["HERMES_KANBAN_BOARD"]
    workspace = env["HERMES_KANBAN_WORKSPACE"]
    self_pid = os.getpid()

    claude_bin = env.get("AETHER_CLAUDE_BIN") or os.environ.get("AETHER_CLAUDE_BIN") or "claude"
    claude_ver = get_claude_version(claude_bin)
    session_id = str(uuid.uuid4())

    pinned_skills = parse_pinned_skills(argv)

    # Prepare attempt scratch directory for transient files
    attempt_dir = Path(tempfile.mkdtemp(prefix=f"aether_claude_{task_id}_{run_id}_")).resolve()
    nonce_file = attempt_dir / f"nonce_{session_id}.txt"
    mcp_config_file = attempt_dir / "mcp.json"
    settings_file = attempt_dir / "settings.json"
    context_file = attempt_dir / "context.md"
    plugin_dir = attempt_dir / "plugin"
    hook_log_file = attempt_dir / "hook.log"

    # Setup isolated implementer hooks location for policy role evaluation
    policy_source = (
        Path(__file__).resolve().parents[2] / "policy" / "hooks" / "aether_pre_tool_policy.py"
    )
    isolated_policy_dir = attempt_dir / "profiles" / "implementer" / "hooks"
    isolated_policy_dir.mkdir(parents=True, exist_ok=True)
    isolated_policy = isolated_policy_dir / "aether_pre_tool_policy.py"
    if policy_source.is_file():
        shutil.copy2(policy_source, isolated_policy)
        isolated_policy.chmod(0o755)

    # Generate context file and skills plugin
    context_content = build_appended_context(
        task_id=task_id,
        workspace=workspace,
        pinned_skills=pinned_skills,
        hermes_home=env.get("HERMES_HOME"),
    )
    context_file.write_text(context_content, encoding="utf-8")
    build_skills_plugin(plugin_dir)

    # Generate MCP configuration pointing to aether-worker
    worker_env = dict(env)
    worker_env.pop("HERMES_BIN", None)
    mcp_config = {
        "mcpServers": {
            "aether-worker": {
                "command": sys.executable,
                "args": ["-m", "aether_agents.worker_mcp_server"],
                "env": worker_env,
            }
        }
    }
    mcp_config_file.write_text(json.dumps(mcp_config, indent=2), encoding="utf-8")

    # Generate Settings configuration with SessionStart nonce hook and PreToolUse hook
    nonce_cmd = (
        f'{sys.executable} -c "import pathlib; '
        f'pathlib.Path({repr(str(nonce_file))}).write_text({repr(session_id)})"'
    )
    hook_cmd = f"{sys.executable} -m aether_agents.pd71_claude_hook"
    settings_data = {
        "hooks": {
            "SessionStart": [
                {
                    "matcher": "*",
                    "hooks": [
                        {
                            "type": "command",
                            "command": nonce_cmd,
                        }
                    ],
                }
            ],
            "PreToolUse": [
                {
                    "matcher": "*",
                    "hooks": [
                        {
                            "type": "command",
                            "command": hook_cmd,
                        }
                    ],
                }
            ],
        }
    }
    settings_file.write_text(json.dumps(settings_data, indent=2), encoding="utf-8")

    # Build Claude command line exactly per plan §3.6
    cmd = [
        claude_bin,
        "-p",
        "--input-format",
        "stream-json",
        "--output-format",
        "stream-json",
        "--verbose",
        "--permission-mode",
        "bypassPermissions",
        "--permission-prompts",
        "none",
        "--session-id",
        session_id,
        "--append-system-prompt-file",
        str(context_file),
        "--mcp-config",
        str(mcp_config_file),
        "--settings",
        str(settings_file),
        "--plugin-dir",
        str(plugin_dir),
    ]

    # Verify no forbidden flag was included
    for flag in FORBIDDEN_FLAGS:
        if flag in cmd:
            raise ValueError(f"Forbidden flag {flag} present in Claude Code invocation")

    # Prepare child environment
    claude_env = dict(env)
    claude_env.pop("HERMES_BIN", None)
    claude_env.pop("CLAUDE_CONFIG_DIR", None)
    claude_env["AETHER_PRE_TOOL_POLICY_PATH"] = str(isolated_policy)
    claude_env["AETHER_HOOK_LOG_PATH"] = str(hook_log_file)

    first_user_message = build_first_user_message(db_path, task_id)

    # Spawn Claude process in a new process group
    try:
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=workspace,
            env=claude_env,
            preexec_fn=_preexec_kill_group,
        )
    except Exception as exc:
        logger.error("Failed to spawn Claude process: %s", exc)
        return _execute_fallback(
            cause="spawn_failed",
            session_id=session_id,
            claude_ver=claude_ver,
            board=board,
            task_id=task_id,
            run_id=run_id,
            claim_lock=claim_lock,
            db_path=db_path,
            workspace=workspace,
            argv=argv,
            env=env,
            start_utc=start_utc,
            readiness_summary={"spawn": False, "error": str(exc)},
            attempt_dir=attempt_dir,
            self_pid=self_pid,
            stream_tail=b"",
        )

    child_pid = proc.pid
    sigterm_received = False

    def _forward_signal(signum: int, frame: Any) -> None:
        nonlocal sigterm_received
        if signum == signal.SIGTERM:
            sigterm_received = True
        try:
            os.killpg(child_pid, signum)
        except OSError:
            pass

    old_sigterm = signal.signal(signal.SIGTERM, _forward_signal)
    old_sigint = signal.signal(signal.SIGINT, _forward_signal)

    readiness_ok = False
    readiness_summary: dict[str, Any] = {
        "permission_mode": None,
        "mcp_connected": False,
        "hook_active": False,
    }
    stream_tail = bytearray()
    structured_fallback_cause: str | None = None
    last_heartbeat = 0.0

    assert proc.stdout is not None
    readiness_deadline = time.time() + READINESS_TIMEOUT_SECONDS
    line_bytes = b""

    try:
        # Phase 1: Readiness gating
        while time.time() < readiness_deadline:
            # Check SessionStart nonce
            if not readiness_summary["hook_active"] and nonce_file.is_file():
                try:
                    if nonce_file.read_text(encoding="utf-8").strip() == session_id:
                        readiness_summary["hook_active"] = True
                except OSError:
                    pass

            r, _, _ = select.select([proc.stdout], [], [], 0.1)
            if proc.stdout in r:
                line_bytes = proc.stdout.readline()
                if line_bytes:
                    stream_tail.extend(line_bytes)
                    if len(stream_tail) > MAX_STREAM_TAIL_BYTES:
                        del stream_tail[: len(stream_tail) - MAX_STREAM_TAIL_BYTES]

                    line_str = line_bytes.decode("utf-8", errors="replace").strip()
                    if line_str:
                        try:
                            event = json.loads(line_str)
                            ev_type = event.get("type")
                            ev_subtype = event.get("subtype")
                            if ev_type == "system" and ev_subtype == "init":
                                perm_mode = event.get("permissionMode")
                                readiness_summary["permission_mode"] = perm_mode
                                # Check MCP servers and tools
                                mcp_servers = (
                                    event.get("mcp_servers") or event.get("mcpServers") or []
                                )
                                tools_list = event.get("tools") or []
                                server_ok = False
                                if isinstance(mcp_servers, list):
                                    for s in mcp_servers:
                                        if isinstance(s, dict) and s.get("name") == "aether-worker":
                                            if s.get("status") in (None, "connected", "ready"):
                                                server_ok = True
                                        elif isinstance(s, str) and s == "aether-worker":
                                            server_ok = True
                                if any(
                                    isinstance(t, str) and t.startswith("mcp__aether-worker__")
                                    for t in tools_list
                                ):
                                    server_ok = True

                                readiness_summary["mcp_connected"] = server_ok
                            elif ev_type == "system" and ev_subtype == "api_retry":
                                error_cat = event.get("error_category") or event.get("category")
                                if error_cat in AUTH_BILLING_ERROR_CATEGORIES:
                                    structured_fallback_cause = f"api_retry_{error_cat}"
                            elif ev_type == "result" and event.get("status") == "error":
                                structured_fallback_cause = "error_result"
                        except Exception:
                            pass
                elif proc.poll() is not None:
                    # EOF reached
                    pass
            elif proc.poll() is not None:
                # Process exited and no more output
                pass

            if (
                readiness_summary["hook_active"]
                and readiness_summary["permission_mode"] == "bypassPermissions"
                and readiness_summary["mcp_connected"]
            ):
                readiness_ok = True
                break

            if proc.poll() is not None and not (proc.stdout in r and line_bytes):
                # Process exited without completing readiness
                break

        if not readiness_ok:
            logger.warning("Readiness gate failed: %s", readiness_summary)
            _cleanup_process_group(proc, child_pid)
            return _execute_fallback(
                cause="readiness_failed",
                session_id=session_id,
                claude_ver=claude_ver,
                board=board,
                task_id=task_id,
                run_id=run_id,
                claim_lock=claim_lock,
                db_path=db_path,
                workspace=workspace,
                argv=argv,
                env=env,
                start_utc=start_utc,
                readiness_summary=readiness_summary,
                attempt_dir=attempt_dir,
                self_pid=self_pid,
                stream_tail=bytes(stream_tail),
            )

        # Readiness confirmed: write the work prompt to Claude's stdin
        work_payload = (
            json.dumps(
                {
                    "type": "user",
                    "message": {
                        "role": "user",
                        "content": first_user_message,
                    },
                }
            )
            + "\n"
        )
        if proc.stdin:
            proc.stdin.write(work_payload.encode("utf-8"))
            proc.stdin.flush()

        # Phase 2: Stream monitoring loop
        while proc.poll() is None:
            r, _, _ = select.select([proc.stdout], [], [], 0.5)
            if proc.stdout in r:
                line_bytes = proc.stdout.readline()
                if not line_bytes:
                    break
                stream_tail.extend(line_bytes)
                if len(stream_tail) > MAX_STREAM_TAIL_BYTES:
                    del stream_tail[: len(stream_tail) - MAX_STREAM_TAIL_BYTES]

                # Heartbeat on real stream events, rate-limited
                now = time.monotonic()
                if now - last_heartbeat >= HEARTBEAT_INTERVAL_SECONDS:
                    _trigger_heartbeat()
                    last_heartbeat = now

                line_str = line_bytes.decode("utf-8", errors="replace").strip()
                if line_str:
                    try:
                        event = json.loads(line_str)
                        ev_type = event.get("type")
                        ev_subtype = event.get("subtype")
                        # Check structured api_retry errors (auth/quota)
                        if ev_type == "system" and ev_subtype == "api_retry":
                            error_cat = event.get("error_category") or event.get("category")
                            if error_cat in AUTH_BILLING_ERROR_CATEGORIES:
                                structured_fallback_cause = f"api_retry_{error_cat}"
                        elif ev_type == "result" and event.get("status") == "error":
                            err_msg = str(event.get("error") or "")
                            if any(cat in err_msg for cat in AUTH_BILLING_ERROR_CATEGORIES):
                                structured_fallback_cause = "quota_or_billing_error"
                            else:
                                structured_fallback_cause = "error_result"
                    except Exception:
                        pass

        proc.wait()
    finally:
        signal.signal(signal.SIGTERM, old_sigterm)
        signal.signal(signal.SIGINT, old_sigint)
        _cleanup_process_group(proc, child_pid)

    end_utc = _now_iso_utc()
    exit_code = proc.returncode

    # Inspect board state read-only for classification
    board_state = check_task_state_read_only(db_path, task_id, run_id)
    latest_event = board_state.get("latest_run_event")
    task_status = board_state.get("status")

    # 1. Native transition check
    if latest_event in ("review_requested", "completed", "blocked") or task_status in (
        "review",
        "done",
        "blocked",
    ):
        outcome = str(latest_event or task_status or "transition")
        write_receipt(
            board=board,
            task_id=task_id,
            run_id=run_id,
            session_id=session_id,
            harness_version=claude_ver,
            start_utc=start_utc,
            end_utc=end_utc,
            readiness_summary=readiness_summary,
            outcome=outcome,
            cause=None,
            fallback=False,
            exit_status=0,
        )
        post_kanban_comment(
            task_id=task_id,
            board=board,
            body=f"{COMMENT_PREFIX} claude-code {claude_ver} session={session_id} outcome={outcome}",
        )
        _cleanup_transient_dir(attempt_dir)
        return 0

    # 2. SIGTERM received (timeout/cancel)
    if sigterm_received:
        write_receipt(
            board=board,
            task_id=task_id,
            run_id=run_id,
            session_id=session_id,
            harness_version=claude_ver,
            start_utc=start_utc,
            end_utc=end_utc,
            readiness_summary=readiness_summary,
            outcome="sigterm",
            cause="sigterm_received",
            fallback=False,
            exit_status=143,
        )
        _cleanup_transient_dir(attempt_dir)
        return 143

    # 3. Task cancelled, claim lost/changed, or already terminal
    if not board_state.get("exists") or task_status in ("cancelled", "archived"):
        write_receipt(
            board=board,
            task_id=task_id,
            run_id=run_id,
            session_id=session_id,
            harness_version=claude_ver,
            start_utc=start_utc,
            end_utc=end_utc,
            readiness_summary=readiness_summary,
            outcome="task_terminal",
            cause="task_cancelled_or_terminal",
            fallback=False,
            exit_status=exit_code,
        )
        _cleanup_transient_dir(attempt_dir)
        return exit_code if exit_code != 0 else 1

    if board_state.get("claim_lock") != claim_lock:
        write_receipt(
            board=board,
            task_id=task_id,
            run_id=run_id,
            session_id=session_id,
            harness_version=claude_ver,
            start_utc=start_utc,
            end_utc=end_utc,
            readiness_summary=readiness_summary,
            outcome="claim_lost",
            cause="claim_lock_changed",
            fallback=False,
            exit_status=exit_code,
        )
        _cleanup_transient_dir(attempt_dir)
        return exit_code if exit_code != 0 else 1

    # 4. Fallback triggers: structured error, crash, non-zero exit
    if structured_fallback_cause is not None:
        return _execute_fallback(
            cause=structured_fallback_cause,
            session_id=session_id,
            claude_ver=claude_ver,
            board=board,
            task_id=task_id,
            run_id=run_id,
            claim_lock=claim_lock,
            db_path=db_path,
            workspace=workspace,
            argv=argv,
            env=env,
            start_utc=start_utc,
            readiness_summary=readiness_summary,
            attempt_dir=attempt_dir,
            self_pid=self_pid,
            stream_tail=bytes(stream_tail),
        )

    if exit_code != 0:
        return _execute_fallback(
            cause=f"non_zero_exit_{exit_code}",
            session_id=session_id,
            claude_ver=claude_ver,
            board=board,
            task_id=task_id,
            run_id=run_id,
            claim_lock=claim_lock,
            db_path=db_path,
            workspace=workspace,
            argv=argv,
            env=env,
            start_utc=start_utc,
            readiness_summary=readiness_summary,
            attempt_dir=attempt_dir,
            self_pid=self_pid,
            stream_tail=bytes(stream_tail),
        )

    # 5. Clean exit without transition -> exit 76 per plan §3.11 table
    write_receipt(
        board=board,
        task_id=task_id,
        run_id=run_id,
        session_id=session_id,
        harness_version=claude_ver,
        start_utc=start_utc,
        end_utc=end_utc,
        readiness_summary=readiness_summary,
        outcome="clean_no_transition",
        cause=None,
        fallback=False,
        exit_status=76,
    )
    post_kanban_comment(
        task_id=task_id,
        board=board,
        body=f"{COMMENT_PREFIX} claude-code {claude_ver} session={session_id} outcome=clean_no_transition",
    )
    _cleanup_transient_dir(attempt_dir)
    return 76


def _cleanup_process_group(proc: subprocess.Popen[bytes], child_pid: int) -> None:
    """Terminate remaining group members (TERM, then KILL) and wait until empty."""
    try:
        os.killpg(child_pid, signal.SIGTERM)
    except OSError:
        pass
    time.sleep(0.3)
    try:
        os.killpg(child_pid, signal.SIGKILL)
    except OSError:
        pass
    # Bounded wait for process group emptiness
    start = time.time()
    while time.time() - start < 2.0:
        try:
            os.killpg(child_pid, 0)
            time.sleep(0.1)
        except OSError:
            break


def _cleanup_transient_dir(attempt_dir: Path) -> None:
    """Remove transient inputs (context file, MCP config, settings, nonce, plugin dir)."""
    try:
        shutil.rmtree(attempt_dir, ignore_errors=True)
    except Exception:
        pass


def _trigger_heartbeat() -> None:
    try:
        from tools.kanban_tools import heartbeat_current_worker_from_env

        heartbeat_current_worker_from_env()
    except Exception:
        pass


def _execute_fallback(
    *,
    cause: str,
    session_id: str,
    claude_ver: str,
    board: str,
    task_id: str,
    run_id: str | int,
    claim_lock: str,
    db_path: str,
    workspace: str,
    argv: list[str],
    env: dict[str, str],
    start_utc: str,
    readiness_summary: dict[str, Any],
    attempt_dir: Path,
    self_pid: int,
    stream_tail: bytes,
) -> int:
    """Execute stateless fallback by execv per plan §3.11."""
    end_utc = _now_iso_utc()

    # Single-writer check: confirm no process other than self has working directory in workspace
    if not check_single_writer(workspace, self_pid):
        logger.error("Single-writer check failed before fallback; exiting without fallback")
        write_receipt(
            board=board,
            task_id=task_id,
            run_id=run_id,
            session_id=session_id,
            harness_version=claude_ver,
            start_utc=start_utc,
            end_utc=end_utc,
            readiness_summary=readiness_summary,
            outcome="fallback_rejected_surviving_writer",
            cause=cause,
            fallback=False,
            exit_status=1,
            stream_tail=stream_tail,
        )
        _cleanup_transient_dir(attempt_dir)
        return 1

    # Confirm claim and task still belong to this attempt
    board_state = check_task_state_read_only(db_path, task_id, run_id)
    if not board_state.get("exists") or board_state.get("claim_lock") != claim_lock:
        logger.error("Claim lost or task missing before fallback; exiting without fallback")
        write_receipt(
            board=board,
            task_id=task_id,
            run_id=run_id,
            session_id=session_id,
            harness_version=claude_ver,
            start_utc=start_utc,
            end_utc=end_utc,
            readiness_summary=readiness_summary,
            outcome="claim_lost",
            cause="claim_lock_changed",
            fallback=False,
            exit_status=1,
            stream_tail=stream_tail,
        )
        _cleanup_transient_dir(attempt_dir)
        return 1

    # Write fallback receipt and comment
    write_receipt(
        board=board,
        task_id=task_id,
        run_id=run_id,
        session_id=session_id,
        harness_version=claude_ver,
        start_utc=start_utc,
        end_utc=end_utc,
        readiness_summary=readiness_summary,
        outcome="fallback",
        cause=cause,
        fallback=True,
        exit_status=None,
        stream_tail=stream_tail,
    )
    post_kanban_comment(
        task_id=task_id,
        board=board,
        body=f"{COMMENT_PREFIX} claude-code {claude_ver} session={session_id} outcome=fallback cause={cause}",
    )

    _cleanup_transient_dir(attempt_dir)

    # Resolve Hermes pass-through invocation
    target_exec, pass_through_base = resolve_hermes_passthrough(env)
    target_argv = [*pass_through_base, *argv[1:]]

    passthrough_env = dict(env)
    passthrough_env.pop("HERMES_BIN", None)

    # Replace current process via execv
    os.execv(target_exec, target_argv)
