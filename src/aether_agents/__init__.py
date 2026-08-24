"""Aether Agents product package.

The distribution is installed twice from one immutable wheel: once in the isolated
``uv tool`` manager environment that owns the public ``aether`` command, and once with
``--no-deps`` inside the Aether-managed versioned Hermes runtime so that Hermes can
discover ``aether_agents.observation.capture.hermes_plugin`` through the public
``hermes_agent.plugins`` entry-point group (OBS-D-021, OBS-FR-071/073/076).

Import boundary (normative, ``specs/001-aether-v1-productization/plan.md`` §5):
manager modules never import Hermes, and the Hermes adapter never imports manager
command/transition/release/service/update/rollback/authentication modules.
"""

from __future__ import annotations

from pathlib import Path

__all__ = ["__version__", "product_version"]

_FALLBACK_VERSION = "0.0.0+unknown"


def _version_from_source_tree() -> str | None:
    """Read the repository ``VERSION`` file when running from a source checkout."""
    # src/aether_agents/__init__.py -> src/aether_agents -> src -> repository root
    candidate = Path(__file__).resolve().parents[2] / "VERSION"
    try:
        text = candidate.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return text or None


def product_version() -> str:
    """Return the single Aether product version shared by manager and observer."""
    try:
        from importlib.metadata import PackageNotFoundError, version
    except ImportError:  # pragma: no cover - importlib.metadata is stdlib on 3.11+
        return _version_from_source_tree() or _FALLBACK_VERSION
    try:
        return version("aether-agents")
    except PackageNotFoundError:
        return _version_from_source_tree() or _FALLBACK_VERSION


__version__ = product_version()
