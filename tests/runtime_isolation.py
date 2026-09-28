"""Minimal disposable-environment support for tests retaining native boundaries."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Mapping

SCRUB_PREFIXES: tuple[str, ...] = ("HERMES_KANBAN_", "HERMES_SESSION_")
SCRUB_NAMES: frozenset[str] = frozenset(
    {
        "TERMINAL_CWD",
        "HERMES_CWD",
        "HERMES_DELEGATED_CHILD_CONTEXT",
        "HERMES_PROJECT_ID",
        "HERMES_TENANT",
        "AETHER_PROJECT_ID",
    }
)


class RuntimeIsolationError(RuntimeError):
    """A disposable test destination is unsafe or escapes its sandbox."""


def scrub_inherited_identity(environ: Mapping[str, str]) -> dict[str, str]:
    """Return a copy without inherited Kanban, session, project or cwd identity."""

    return {
        name: value
        for name, value in environ.items()
        if not name.startswith(SCRUB_PREFIXES) and name not in SCRUB_NAMES
    }


def preflight_disposable_destinations(run_root: Path, *destinations: Path) -> tuple[Path, ...]:
    """Resolve disposable destinations and reject symlinks or sandbox escapes."""
    resolved_root = run_root.expanduser().resolve()
    targets = destinations or (run_root / "kanban.db", run_root / "worktrees")
    resolved_targets: list[Path] = []
    for dest in targets:
        expanded = dest.expanduser()
        if expanded.is_symlink():
            raise RuntimeIsolationError(f"disposable destination cannot be a symlink: {dest}")
        resolved_dest = expanded.resolve()
        try:
            if not (resolved_dest == resolved_root or resolved_dest.is_relative_to(resolved_root)):
                raise RuntimeIsolationError(
                    f"disposable destination escapes sandbox: {dest} resolves to {resolved_dest} outside {resolved_root}"
                )
        except ValueError:
            raise RuntimeIsolationError(
                f"disposable destination escapes sandbox: {dest} resolves to {resolved_dest} outside {resolved_root}"
            )
        chk = expanded
        while chk != run_root and chk.resolve() != resolved_root and chk != chk.parent:
            if chk.is_symlink():
                raise RuntimeIsolationError(
                    f"disposable destination cannot contain a symlink: {dest}"
                )
            chk = chk.parent
        resolved_targets.append(resolved_dest)
    return tuple(resolved_targets)


def isolated_hermes_env(run_root: Path, hermes_root: Path, hermes: Path) -> dict[str, str]:
    """Build the disposable Hermes environment used by retained boundary tests."""
    preflight_disposable_destinations(run_root, run_root / "kanban.db", run_root / "worktrees")

    env = scrub_inherited_identity(os.environ)
    env.update(
        {
            "HERMES_HOME": str(hermes_root),
            "HERMES_BIN": str(hermes.resolve()),
            "HERMES_ACCEPT_HOOKS": "1",
            "HERMES_KANBAN_DB": str(run_root / "kanban.db"),
            "HERMES_KANBAN_WORKSPACES_ROOT": str(run_root / "worktrees"),
            "XDG_STATE_HOME": str(run_root / "xdg-state"),
            "XDG_DATA_HOME": str(run_root / "xdg-data"),
            "PYTHONDONTWRITEBYTECODE": "1",
        }
    )
    return env
