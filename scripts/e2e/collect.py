"""Small evidence helpers for Aether disposable E2E runs.

The harness records argv, timing, stdout/stderr, Git and board evidence. It never
serializes the environment passed to subprocesses because provider credentials may
be present there during an explicitly authorized live run.
"""

from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence


@dataclass(frozen=True, slots=True)
class CommandResult:
    argv: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str
    duration_seconds: float


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def append_jsonl(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")))
        handle.write("\n")


def run_command(
    argv: Sequence[str],
    *,
    cwd: Path,
    env: Mapping[str, str] | None,
    log_path: Path,
    timeout_seconds: int | float,
    stdin: str | None = None,
) -> CommandResult:
    """Run a finite subprocess and record content-safe evidence.

    Environment values are deliberately omitted from evidence. This is important
    during live runs where provider credentials may be inherited from the shell.
    """

    started = time.monotonic()
    try:
        completed = subprocess.run(
            [str(item) for item in argv],
            cwd=cwd,
            env=dict(env) if env is not None else None,
            input=stdin,
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
        timed_out = False
        stdout = completed.stdout
        stderr = completed.stderr
        returncode = completed.returncode
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        returncode = 124
    duration = time.monotonic() - started
    result = CommandResult(
        argv=tuple(str(item) for item in argv),
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
        duration_seconds=duration,
    )
    append_jsonl(
        log_path,
        {
            "argv": list(result.argv),
            "cwd": str(cwd),
            "duration_seconds": round(duration, 6),
            "returncode": returncode,
            "stderr": stderr,
            "stdout": stdout,
            "timed_out": timed_out,
        },
    )
    return result


def git_snapshot(repo: Path, *, env: Mapping[str, str] | None, log_path: Path) -> str:
    parts: list[str] = []
    for label, argv in (
        ("HEAD", ("git", "rev-parse", "HEAD")),
        ("STATUS", ("git", "status", "--short", "--branch")),
        ("LOG", ("git", "log", "--oneline", "--decorate", "-20")),
        ("WORKTREES", ("git", "worktree", "list", "--porcelain")),
    ):
        result = run_command(
            argv,
            cwd=repo,
            env=env,
            log_path=log_path,
            timeout_seconds=20,
        )
        parts.append(f"--- {label} rc={result.returncode} ---\n{result.stdout}{result.stderr}")
    return "\n".join(parts)


def git_diff(repo: Path, *, env: Mapping[str, str] | None, log_path: Path) -> str:
    result = run_command(
        ("git", "diff", "--binary", "HEAD"),
        cwd=repo,
        env=env,
        log_path=log_path,
        timeout_seconds=30,
    )
    return result.stdout + result.stderr


def json_from_stdout(result: CommandResult, *, expected: type = dict) -> Any:
    if result.returncode != 0:
        raise ValueError(f"command failed: {' '.join(result.argv)}")
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ValueError(f"command did not return JSON: {' '.join(result.argv)}") from exc
    if not isinstance(payload, expected):
        raise ValueError(f"unexpected JSON shape from: {' '.join(result.argv)}")
    return payload
