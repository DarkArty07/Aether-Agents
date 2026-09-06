"""Small, local storage primitives for derived knowledge and role notes."""

from __future__ import annotations

import json
import os
import subprocess
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from aether_agents.paths import atomic_private_write, ensure_private_dir, read_private_bytes

GRAPHIFY_VERSION = "0.9.54"
ROLES = ("morfeo", "supervisor", "implementer")
MAX_RESULT_BYTES = 32768


class KnowledgeError(Exception):
    """A typed failure which must not stop ordinary file-based work."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def atomic_json(path: Path, data: Any) -> None:
    ensure_private_dir(path.parent)
    atomic_private_write(
        path, (json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
    )


def load_json(path: Path, *, limit: int = 2_000_000) -> Any:
    if path.is_symlink():
        raise KnowledgeError("UNSAFE_PATH", "A knowledge artifact is a symbolic link.")
    try:
        if path.stat().st_size > limit:
            raise KnowledgeError("INDEX_CORRUPT", "A knowledge artifact exceeds its size limit.")
        return json.loads(read_private_bytes(path))
    except FileNotFoundError:
        raise
    except (OSError, ValueError) as exc:
        raise KnowledgeError("INDEX_CORRUPT", "A knowledge artifact cannot be read.") from exc


@contextmanager
def stable_lock(path: Path, timeout: float = 10.0) -> Iterator[None]:
    """Keep the lock inode stable even across waiting processes and crashes."""
    if os.name != "posix":
        raise KnowledgeError("PLATFORM_UNSUPPORTED", "Knowledge writes require POSIX locking.")
    import fcntl

    ensure_private_dir(path.parent)
    flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags, 0o600)
    except OSError as exc:
        raise KnowledgeError("UNSAFE_PATH", "Cannot open the knowledge lock safely.") from exc
    acquired = False
    try:
        deadline = time.monotonic() + timeout
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise KnowledgeError("BUSY", "Another knowledge update is in progress.")
                time.sleep(0.025)
        yield
    finally:
        if acquired:
            fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
        # Never unlink: waiters may still hold descriptors for this inode.


def clean_environment(home: Path | None = None) -> dict[str, str]:
    """Do not inherit provider credentials, project config or Graphify overrides."""
    result = {
        "PATH": os.environ.get("PATH", os.defpath),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PYTHONIOENCODING": "utf-8",
        "GRAPHIFY_QUERY_LOG_DISABLE": "1",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_OPTIONAL_LOCKS": "0",
    }
    if home is not None:
        result.update(HOME=str(home), XDG_CONFIG_HOME=str(home / "config"))
    return result


def git(root: Path, *arguments: str, timeout: float = 20.0, data: bytes | None = None) -> bytes:
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), "-c", "core.hooksPath=" + os.devnull, *arguments],
            input=data,
            capture_output=True,
            timeout=timeout,
            env=clean_environment(),
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise KnowledgeError("SCOPE_UNAVAILABLE", "Cannot inspect the bound Git revision.") from exc
    if completed.returncode:
        raise KnowledgeError("SCOPE_UNAVAILABLE", "The bound Git repository is unavailable.")
    return completed.stdout


def bounded(text: str, budget_tokens: int = 2000) -> tuple[str, bool]:
    if type(budget_tokens) is not int or not 128 <= budget_tokens <= 8000:
        raise KnowledgeError("ARGUMENT_INVALID", "budget_tokens must be between 128 and 8000.")
    limit = min(MAX_RESULT_BYTES, budget_tokens * 4)
    raw = text.encode("utf-8")
    return raw[:limit].decode("utf-8", errors="ignore"), len(raw) > limit
