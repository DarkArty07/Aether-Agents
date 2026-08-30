"""Compatibility wrapper for :mod:`aether_agents.lab.runner`."""

import importlib as _importlib
import sys as _sys
from pathlib import Path as _Path

_SOURCE_ROOT = _Path(__file__).resolve().parents[2]
_SOURCE_SRC = _SOURCE_ROOT / "src"
if _SOURCE_SRC.is_dir() and str(_SOURCE_SRC) not in _sys.path:
    _sys.path.insert(0, str(_SOURCE_SRC))

_implementation = _importlib.import_module("aether_agents.lab.runner")
_sys.modules[__name__] = _implementation

if __name__ == "__main__":
    raise SystemExit(_implementation.main())
