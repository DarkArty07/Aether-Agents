"""Worker launcher for Aether Kanban tasks with external harness routing.

Routes an attempt to Claude Code when all eligibility conditions in plan section 3.5
hold; otherwise executes an exact pass-through to Hermes.
"""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import sys
from pathlib import Path
from typing import Any, NoReturn

REQUIRED_ENV_VARS: tuple[str, ...] = (
    "HERMES_KANBAN_TASK",
    "HERMES_KANBAN_RUN_ID",
    "HERMES_KANBAN_CLAIM_LOCK",
    "HERMES_KANBAN_DB",
    "HERMES_KANBAN_BOARD",
    "HERMES_KANBAN_WORKSPACE",
    "HERMES_PROFILE",
)


def _has_resume(argv: list[str]) -> bool:
    for arg in argv:
        if arg == "--resume" or arg.startswith("--resume="):
            return True
    return False


def _has_model_or_effort_pins(argv: list[str]) -> bool:
    for arg in argv:
        if arg in ("-m", "--model", "--provider", "--reasoning"):
            return True
        if arg.startswith(("-m=", "--model=", "--provider=", "--reasoning=")):
            return True
    return False


def _check_safe_board_metadata(db_path: Path, board_slug: str) -> dict[str, Any] | None:
    try:
        import hermes_cli.kanban_db as kdb  # type: ignore[import-not-found,import-untyped]
    except Exception:
        return None

    try:
        home = kdb.kanban_home()
        boards = kdb.boards_root()
        directory = kdb.board_dir(board_slug)
        expected = boards / board_slug
        if directory != expected:
            return None
        if db_path.resolve() != (directory / "kanban.db").resolve():
            return None

        for path in (home, home / "kanban", boards, directory):
            if path.is_symlink():
                return None
            if path.exists() and not path.is_dir():
                return None

        metadata_path = directory / "board.json"
        for path in (metadata_path, db_path):
            if path.is_symlink():
                return None
            if not path.is_file():
                return None

        metadata_raw = metadata_path.read_text(encoding="utf-8")
        metadata = json.loads(metadata_raw)
        if not isinstance(metadata, dict):
            return None
        return metadata
    except Exception:
        return None


def _check_claimed_event_not_review(db_path: Path, task_id: str, run_id_str: str) -> bool:
    try:
        run_id = int(run_id_str)
    except (ValueError, TypeError):
        return False

    conn = None
    try:
        conn = sqlite3.connect(f"file:{db_path.resolve()}?mode=ro", uri=True)
        cur = conn.execute(
            "SELECT payload FROM task_events WHERE task_id = ? AND run_id = ? AND kind = 'claimed' ORDER BY id DESC LIMIT 1",
            (task_id, run_id),
        )
        row = cur.fetchone()
        if row is None:
            cur = conn.execute(
                "SELECT payload FROM task_events WHERE task_id = ? AND kind = 'claimed' ORDER BY id DESC LIMIT 1",
                (task_id,),
            )
            row = cur.fetchone()
        if row is None:
            return False

        payload_raw = row[0]
        payload = json.loads(payload_raw) if payload_raw else {}
        if not isinstance(payload, dict):
            return False
        if payload.get("source_status") == "review":
            return False
        return True
    except Exception:
        return False
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


def is_eligible_for_claude_code(
    argv: list[str],
    env: dict[str, str] | None = None,
) -> bool:
    """Return True if the attempt satisfies all plan section 3.5 conditions."""
    if env is None:
        env = dict(os.environ)

    try:
        # 1. Environment variables and workspace directory
        for var in REQUIRED_ENV_VARS:
            val = env.get(var)
            if not val or not val.strip():
                return False

        workspace = Path(env["HERMES_KANBAN_WORKSPACE"])
        if not workspace.is_dir():
            return False

        # 2. Profile must be implementer
        if env.get("HERMES_PROFILE") != "implementer":
            return False

        # 4. Goal mode is not 1
        if env.get("HERMES_KANBAN_GOAL_MODE", "").strip() == "1":
            return False

        # 5a. Review affinity unset and no --resume in argv
        if bool(env.get("HERMES_KANBAN_REVIEW_AFFINITY", "").strip()):
            return False
        if _has_resume(argv):
            return False

        # 6. No model, provider, or reasoning pins in argv
        if _has_model_or_effort_pins(argv):
            return False

        # 7. claude executable resolves on PATH
        if not shutil.which("claude", path=env.get("PATH")):
            return False

        # 3. board.json checks (canonical paths, no symlinks, Aether identity, harness)
        db_path = Path(env["HERMES_KANBAN_DB"])
        board_slug = env["HERMES_KANBAN_BOARD"]
        metadata = _check_safe_board_metadata(db_path, board_slug)
        if metadata is None:
            return False

        if metadata.get("archived"):
            return False

        contract_id = metadata.get("aether_contract_id")
        project_id = metadata.get("aether_project_id")
        version = metadata.get("aether_contract_version")
        if not (
            isinstance(contract_id, str)
            and contract_id
            and isinstance(project_id, str)
            and project_id
            and isinstance(version, int)
            and version > 0
        ):
            return False

        if metadata.get("aether_implementer_harness") != "claude-code":
            return False

        # 5b. Database event check: latest claimed event has no source_status "review"
        task_id = env["HERMES_KANBAN_TASK"]
        run_id = env["HERMES_KANBAN_RUN_ID"]
        if not _check_claimed_event_not_review(db_path, task_id, run_id):
            return False

        return True
    except Exception:
        return False


def pass_through_to_hermes(
    argv_tail: list[str],
    env: dict[str, str] | None = None,
) -> NoReturn:
    """Replace current process with the Hermes entry the dispatcher would have resolved."""
    if env is None:
        env = dict(os.environ)

    hermes_path = shutil.which("hermes", path=env.get("PATH"))
    if sys.platform == "win32" and hermes_path and hermes_path.lower().endswith((".cmd", ".bat")):
        hermes_path = None

    if hermes_path:
        target = hermes_path
        cmd = [hermes_path, *argv_tail]
        try:
            os.environ.clear()
            os.environ.update(env)
            os.execv(target, cmd)
        except OSError:
            pass

    target = sys.executable
    cmd = [sys.executable, "-m", "hermes_cli.main", *argv_tail]
    os.environ.clear()
    os.environ.update(env)
    os.execv(target, cmd)
    sys.exit(1)


def main(
    argv: list[str] | None = None,
    env: dict[str, str] | None = None,
) -> int:
    """Entry point for the aether-kanban-worker console script."""
    if argv is None:
        argv = list(sys.argv)
    if env is None:
        env = dict(os.environ)

    if argv and argv[0].startswith("-"):
        full_argv = ["aether-kanban-worker", *argv]
        argv_tail = list(argv)
    elif argv:
        full_argv = list(argv)
        argv_tail = list(argv[1:])
    else:
        full_argv = ["aether-kanban-worker"]
        argv_tail = []

    try:
        eligible = is_eligible_for_claude_code(full_argv, env)
    except Exception:
        eligible = False

    if eligible:
        from aether_agents.claude_code_adapter import (  # type: ignore[import-not-found,import-untyped]
            run_attempt,
        )

        return run_attempt(full_argv, env)

    pass_through_to_hermes(argv_tail, env)


if __name__ == "__main__":
    sys.exit(main())
