"""Finite Hermes Kanban driver for disposable Aether E2E runs.

No daemon is introduced. The harness uses Hermes's existing one-pass dispatcher and
polls its durable board until the scenario settles or reaches its explicit budget.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from .collect import CommandResult, json_from_stdout, run_command, write_json

SETTLED_STATUSES = {"done", "archived", "blocked"}
SUCCESS_STATUSES = {"done", "archived"}


@dataclass(frozen=True, slots=True)
class BoardState:
    tasks: tuple[dict[str, object], ...]
    passes: int
    settled: bool
    successful: bool
    reason: str


def hermes_argv(hermes: Path, profile: str, *args: str) -> tuple[str, ...]:
    # --profile is consumed by Hermes before normal argparse and therefore works
    # for every subcommand. Keeping one root HERMES_HOME lets the three profiles
    # share the same isolated board/worktree substrate while retaining profile config.
    return (str(hermes), "-p", profile, *args)


def kanban_json(
    hermes: Path,
    profile: str,
    args: tuple[str, ...],
    *,
    cwd: Path,
    env: Mapping[str, str],
    commands_log: Path,
    timeout_seconds: int = 30,
    expected: type = list,
):
    result = run_command(
        hermes_argv(hermes, profile, "kanban", *args),
        cwd=cwd,
        env=env,
        log_path=commands_log,
        timeout_seconds=timeout_seconds,
    )
    return json_from_stdout(result, expected=expected)


def board_list(
    hermes: Path,
    *,
    cwd: Path,
    env: Mapping[str, str],
    commands_log: Path,
) -> list[dict[str, object]]:
    payload = kanban_json(
        hermes,
        "morfeo",
        ("list", "--json"),
        cwd=cwd,
        env=env,
        commands_log=commands_log,
        expected=list,
    )
    if not all(isinstance(item, dict) for item in payload):
        raise ValueError("kanban list returned non-object task")
    return payload


def snapshot_board(
    hermes: Path,
    *,
    cwd: Path,
    env: Mapping[str, str],
    commands_log: Path,
    evidence_dir: Path,
) -> list[dict[str, object]]:
    tasks = board_list(hermes, cwd=cwd, env=env, commands_log=commands_log)
    status_counts: dict[str, int] = {}
    for task in tasks:
        status = str(task.get("status", "unknown"))
        status_counts[status] = status_counts.get(status, 0) + 1
    write_json(
        evidence_dir / "board-list.json",
        {"kind": "board_summary", "task_count": len(tasks), "status_counts": status_counts},
    )
    return tasks


def dispatch_until_settled(
    hermes: Path,
    *,
    cwd: Path,
    env: Mapping[str, str],
    commands_log: Path,
    evidence_dir: Path,
    max_passes: int,
    timeout_seconds: int,
    poll_seconds: float = 0.5,
) -> BoardState:
    started = time.monotonic()
    last_tasks: list[dict[str, object]] = []
    poll_seconds = max(poll_seconds, timeout_seconds / max(1, max_passes))

    for pass_number in range(1, max_passes + 1):
        if time.monotonic() - started >= timeout_seconds:
            return BoardState(tuple(last_tasks), pass_number - 1, False, False, "timeout")

        dispatch: CommandResult = run_command(
            hermes_argv(hermes, "morfeo", "kanban", "dispatch", "--json", "--max", "4"),
            cwd=cwd,
            env=env,
            log_path=commands_log,
            timeout_seconds=min(60, timeout_seconds),
        )
        if dispatch.returncode != 0:
            return BoardState(tuple(last_tasks), pass_number, False, False, "dispatch_failed")
        try:
            json.loads(dispatch.stdout or "{}")
        except json.JSONDecodeError:
            return BoardState(tuple(last_tasks), pass_number, False, False, "dispatch_non_json")

        last_tasks = board_list(hermes, cwd=cwd, env=env, commands_log=commands_log)
        if not last_tasks:
            return BoardState((), pass_number, True, True, "no_tasks")

        statuses = {
            str(task.get("status", "")).casefold() for task in last_tasks if isinstance(task, dict)
        }
        if statuses and statuses <= SETTLED_STATUSES:
            successful = statuses <= SUCCESS_STATUSES
            snapshot_board(
                hermes,
                cwd=cwd,
                env=env,
                commands_log=commands_log,
                evidence_dir=evidence_dir,
            )
            return BoardState(
                tuple(last_tasks),
                pass_number,
                True,
                successful,
                "terminal" if successful else "blocked",
            )

        time.sleep(poll_seconds)

    snapshot_board(
        hermes,
        cwd=cwd,
        env=env,
        commands_log=commands_log,
        evidence_dir=evidence_dir,
    )
    return BoardState(tuple(last_tasks), max_passes, False, False, "pass_budget_exhausted")
