#!/usr/bin/env python3
"""HLP-310 canary: a delegated-child marker must not persist into the reusable snapshot.

Exercises the real `LocalEnvironment` reusable bash session: one child-like command
carries ``HERMES_DELEGATED_CHILD_CONTEXT=1`` in the process environment, then the
session snapshot is inspected and a later parent-like command is executed in the
same session. The module origin of every imported Hermes module is printed so a run
can never be attributed to the wrong tree.

Usage (no paths are hard-coded; pass the tree under test through PYTHONPATH):

    env PYTHONPATH=<tree-under-test> PYTHONDONTWRITEBYTECODE=1 \
        <interpreter-of-the-runtime> specs/001-aether-v1-productization/fixtures/hlp310_snapshot_canary.py

Expected: ``VERDICT: no-leak`` on a runtime that excludes
``HERMES_DELEGATED_CHILD_CONTEXT`` and ``HERMES_KANBAN_*`` from terminal session
snapshots (HLP-310, issue #404). ``VERDICT: LEAK`` reproduces the #404 defect.

Only disposable roots are used: ``HERMES_HOME`` and the working directory are
temporary directories, and no live board, service or state is touched.
"""

from __future__ import annotations

import importlib.util
import os
import tempfile
from pathlib import Path


def _origin(module_name: str) -> str:
    spec = importlib.util.find_spec(module_name)
    return spec.origin if spec is not None and spec.origin else "unresolved"


def main() -> int:
    os.environ["HERMES_HOME"] = tempfile.mkdtemp(prefix="canary-hermes-home-")
    os.environ.pop("HERMES_DELEGATED_CHILD_CONTEXT", None)
    os.environ.pop("HERMES_KANBAN_TASK", None)
    os.environ.pop("HERMES_KANBAN_BOARD", None)

    for module_name in (
        "tools.environments.local",
        "tools.environments.base",
        "agent.delegation_context",
    ):
        print(f"{module_name}_module: {_origin(module_name)}")

    from tools.environments.local import LocalEnvironment

    workdir = tempfile.mkdtemp(prefix="canary-cwd-")
    env = LocalEnvironment(cwd=workdir, timeout=30)
    env.init_session()
    try:
        os.environ["HERMES_DELEGATED_CHILD_CONTEXT"] = "1"
        child = env.execute('echo "child_marker=[$HERMES_DELEGATED_CHILD_CONTEXT]"')
        print("child_output:", child.get("output", "").strip())
        os.environ.pop("HERMES_DELEGATED_CHILD_CONTEXT", None)

        snapshot = Path(getattr(env, "_snapshot_path", ""))
        text = snapshot.read_text(encoding="utf-8") if snapshot.exists() else ""
        print("snapshot_exists:", snapshot.exists())
        print("snapshot_has_delegated_marker:", "HERMES_DELEGATED_CHILD_CONTEXT" in text)
        print("snapshot_has_kanban_prefix:", "HERMES_KANBAN_" in text)

        parent = env.execute('echo "parent_marker=[$HERMES_DELEGATED_CHILD_CONTEXT]"')
        parent_output = parent.get("output", "")
        print("parent_output:", parent_output.strip())

        leaked = (
            "parent_marker=[1]" in parent_output
            or "HERMES_DELEGATED_CHILD_CONTEXT" in text
        )
        print("VERDICT:", "LEAK" if leaked else "no-leak")
        return 1 if leaked else 0
    finally:
        env.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
