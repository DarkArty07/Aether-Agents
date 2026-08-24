"""Exact project-context resolution for every observation event.

Normative decision: OBS-D-022, enforced by OBS-FR-077.

Every event must carry one stable canonical project UUID, but several profiles and
projects share one runtime. The accepted rule is therefore blunt: it is safer to lose
coverage visibly than to contaminate another project's history. ``cwd``, profile name,
timestamps, repository name, and an unverified environment value are hints — they never
establish project identity.

Precedence, highest first:

1. exact Aether project/board mapping for a bound task or run;
2. verified session-to-Hermes-Project mapping;
3. a manager-supplied launch binding, verified against BOTH the local Aether project
   registry and the portable ``.aether/project.toml`` marker.

Agreement resolves one canonical lower-case UUID. Disagreement, or no verified source,
suppresses project-journal output entirely and increments bounded content-free
observer-health counters. No unresolved message, task, or session identifier is ever
persisted in global health state.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final

from aether_agents.paths import (
    ObservationPaths,
    UnsafeObservationPath,
    atomic_private_write,
    ensure_private_dir,
    read_private_bytes,
    state_root,
)

__all__ = [
    "HealthCounters",
    "ObservationContextResolver",
    "ProjectCandidate",
    "ProjectRegistry",
    "Resolution",
    "read_project_marker",
]

_UUID_RE: Final = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")

#: Ordered by authority. The resolver never reorders them at runtime.
SOURCE_PRECEDENCE: Final = ("task_binding", "run_binding", "session_binding", "launch_binding")

#: Sources that are hints only and can never establish identity on their own.
UNVERIFIABLE_SOURCES: Final = ("cwd", "profile", "timestamp", "repository_name", "environment")


def canonical_project_id(value: Any) -> str | None:
    """Normalize to a canonical lower-case project UUID, or reject it."""
    if not isinstance(value, str):
        return None
    candidate = value.strip().lower()
    return candidate if _UUID_RE.fullmatch(candidate) else None


def read_project_marker(project_path: Path | str) -> dict[str, Any] | None:
    """Read the portable ``.aether/project.toml`` identity marker.

    Conforms to ``specs/001-aether-v1-productization/contracts/project.schema.json``.
    Returns ``None`` when the marker is absent, unreadable, or not schema-shaped.
    """
    marker = Path(project_path) / ".aether" / "project.toml"
    try:
        import tomllib

        data = tomllib.loads(marker.read_text(encoding="utf-8"))
    except (OSError, ValueError, ImportError):
        return None
    if not isinstance(data, dict):
        return None
    if canonical_project_id(data.get("project_id")) is None:
        return None
    return data


@dataclass(frozen=True, slots=True)
class ProjectCandidate:
    """One proposed project identity and the source that proposed it."""

    project_id: str
    source: str
    verified: bool = False

    @property
    def authoritative(self) -> bool:
        return self.verified and self.source in SOURCE_PRECEDENCE


@dataclass(frozen=True, slots=True)
class Resolution:
    """Outcome of one context resolution."""

    project_id: str | None
    source: str | None
    status: str  # "resolved" | "unresolved" | "conflict"
    reason_code: str | None = None

    @property
    def resolved(self) -> bool:
        return self.status == "resolved" and self.project_id is not None


class ProjectRegistry:
    """The local Aether project registry, owned by the A1 manager.

    Its contents are never copied into an observation event: it is consulted only to
    answer "is this UUID a project this installation actually knows?".
    """

    def __init__(self, root: Path | str | None = None) -> None:
        self._root = state_root(root)

    @property
    def path(self) -> Path:
        return self._root / "projects" / "registry.json"

    def _load(self) -> dict[str, Any]:
        try:
            data = json.loads(read_private_bytes(self.path).decode("utf-8"))
        except (OSError, UnicodeError, ValueError):
            return {}
        return data.get("projects", {}) if isinstance(data, dict) else {}

    def knows(self, project_id: str) -> bool:
        canonical = canonical_project_id(project_id)
        return canonical is not None and canonical in self._load()

    def project_path(self, project_id: str) -> Path | None:
        entry = self._load().get(canonical_project_id(project_id) or "")
        if not isinstance(entry, dict):
            return None
        raw = entry.get("path")
        return Path(raw) if isinstance(raw, str) and raw else None

    def verify_with_marker(self, project_id: str) -> bool:
        """A launch binding is trusted only when registry and portable marker agree."""
        canonical = canonical_project_id(project_id)
        if canonical is None or not self.knows(canonical):
            return False
        location = self.project_path(canonical)
        if location is None:
            return False
        marker = read_project_marker(location)
        return marker is not None and canonical_project_id(marker.get("project_id")) == canonical

    def register(self, project_id: str, project_path: Path | str, name: str = "") -> bool:
        """Record a project. Used by ``aether init``/``setup`` and by tests."""
        canonical = canonical_project_id(project_id)
        if canonical is None:
            return False
        projects = self._load()
        projects[canonical] = {"path": str(Path(project_path).resolve()), "name": name}
        ensure_private_dir(self.path.parent)
        atomic_private_write(
            self.path,
            json.dumps(
                {"schema_version": 1, "projects": projects},
                indent=2,
                sort_keys=True,
            ).encode("utf-8"),
        )
        return True


class HealthCounters:
    """Bounded, content-free counters that live outside every project directory.

    They record *how often* a class of problem happened, never *which* message, task, or
    session it happened to. ``aether doctor`` surfaces them.
    """

    def __init__(self, root: Path | str | None = None) -> None:
        self._root = state_root(root)

    @property
    def path(self) -> Path:
        return self._root / "observations" / "health" / "counters.json"

    def read(self) -> dict[str, int]:
        try:
            data = json.loads(read_private_bytes(self.path).decode("utf-8"))
        except (OSError, UnicodeError, ValueError):
            return {}
        if not isinstance(data, dict):
            return {}
        return {k: int(v) for k, v in data.items() if isinstance(v, int)}

    def increment(self, reason_code: str, amount: int = 1) -> None:
        """Increment one counter. Never raises: health accounting cannot break capture."""
        if not re.fullmatch(r"[A-Z0-9_]{2,64}", reason_code):
            reason_code = "UNCLASSIFIED"
        try:
            counters = self.read()
            counters[reason_code] = counters.get(reason_code, 0) + amount
            ensure_private_dir(self.path.parent)
            atomic_private_write(
                self.path,
                json.dumps(counters, indent=2, sort_keys=True).encode("utf-8"),
            )
        except (OSError, UnsafeObservationPath):
            pass


@dataclass
class ObservationContextResolver:
    """Resolve one canonical project UUID from verified sources only."""

    registry: ProjectRegistry = field(default_factory=ProjectRegistry)
    health: HealthCounters = field(default_factory=HealthCounters)

    def resolve(
        self,
        *,
        task_binding: str | None = None,
        run_binding: str | None = None,
        session_binding: str | None = None,
        launch_binding: str | None = None,
    ) -> Resolution:
        """Resolve context from the four verifiable sources, in precedence order.

        ``task_binding``/``run_binding`` are exact Aether board mappings; ``session_binding``
        is a verified session-to-Hermes-Project mapping; ``launch_binding`` is the
        manager-supplied binding, which is accepted only after registry *and* portable
        marker both confirm it.
        """
        candidates: list[ProjectCandidate] = []
        for source, raw in (
            ("task_binding", task_binding),
            ("run_binding", run_binding),
            ("session_binding", session_binding),
            ("launch_binding", launch_binding),
        ):
            canonical = canonical_project_id(raw)
            if canonical is None:
                continue
            verified = (
                self.registry.verify_with_marker(canonical)
                if source == "launch_binding"
                else self.registry.knows(canonical)
            )
            candidates.append(ProjectCandidate(canonical, source, verified))

        authoritative = [c for c in candidates if c.authoritative]
        if not authoritative:
            reason = "PROJECT_UNVERIFIED" if candidates else "PROJECT_UNRESOLVED"
            self.health.increment(reason)
            return Resolution(None, None, "unresolved", reason)

        distinct = {c.project_id for c in authoritative}
        if len(distinct) > 1:
            # Sources disagree. Emitting nothing is the accepted outcome: a wrong project
            # is unrecoverable, a missing interval is only a visible coverage gap.
            self.health.increment("PROJECT_CONFLICT")
            return Resolution(None, None, "conflict", "PROJECT_CONFLICT")

        winner = min(authoritative, key=lambda c: SOURCE_PRECEDENCE.index(c.source))
        return Resolution(winner.project_id, winner.source, "resolved")

    def paths_for(self, resolution: Resolution, *, root: Path | str | None = None):
        """Observation paths for a resolved project, or ``None`` when unresolved."""
        if not resolution.resolved:
            return None
        assert resolution.project_id is not None
        return ObservationPaths.for_project(resolution.project_id, root=root)
