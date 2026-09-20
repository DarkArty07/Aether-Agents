#!/usr/bin/env python3
"""Compatibility shim for the packaged Aether Morfeo launcher."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure repository root is on sys.path when run directly from checkout
_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = _REPO_ROOT / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from aether_agents.launcher import (  # noqa: E402
    _RESERVED_ARGS,
    REQUIRED_TOOLSETS,
    ActivationError,
    _portable_project_id,
    inspect_activation,
    main,
)

__all__ = [
    "REQUIRED_TOOLSETS",
    "_RESERVED_ARGS",
    "ActivationError",
    "_portable_project_id",
    "inspect_activation",
    "main",
]

if __name__ == "__main__":
    if "AETHER_PROJECT_ROOT" not in os.environ and not any(
        arg == "--project" or arg.startswith("--project=") for arg in sys.argv[1:]
    ):
        os.environ["AETHER_PROJECT_ROOT"] = str(_REPO_ROOT)
    raise SystemExit(main())
