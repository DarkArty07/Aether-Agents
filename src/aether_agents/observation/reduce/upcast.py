"""Pure, deterministic upcasters across released event schema versions.

Normative decision: OBS-D-026, enforced by OBS-FR-081.

Indefinite retention plus rollback requires forward preservation even though old code
cannot understand future schemas. Three rules follow, and none of them ever touches a
retained byte:

* every reducer declares exactly which event versions it reads and which summary version
  and read-model schema it writes;
* a supported historical version is transformed by a pure function before reduction;
* an unknown NEWER version is preserved in place and indexed as quarantined coverage —
  never moved, rewritten, discarded, or guessed at. A later compatible release reingests it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Final

from aether_agents.observation.contracts import (
    EVENT_SCHEMA_VERSION,
    READ_MODEL_SCHEMA,
    REDUCER_VERSION,
    SUMMARY_SCHEMA_VERSION,
    SUPPORTED_EVENT_SCHEMA_VERSIONS,
)

__all__ = [
    "READ_SET",
    "UpcastResult",
    "declared_versions",
    "is_known_version",
    "upcast_event",
]

#: Exactly the event versions this release claims to read.
READ_SET: Final = tuple(SUPPORTED_EVENT_SCHEMA_VERSIONS)

#: version -> pure transform into the next version. ``v1`` is current, so it is identity.
_UPCASTERS: Final[dict[str, Callable[[dict[str, Any]], dict[str, Any]]]] = {}


@dataclass(frozen=True, slots=True)
class UpcastResult:
    """Outcome of preparing one stored event for the current reducer."""

    event: dict[str, Any] | None
    status: str  # "ok" | "unknown_schema" | "malformed"
    reason_code: str | None = None

    @property
    def ok(self) -> bool:
        return self.status == "ok"


def declared_versions() -> dict[str, Any]:
    """What this reducer reads and writes. Recorded in every summary's provenance."""
    return {
        "reads_event_schema_versions": list(READ_SET),
        "writes_summary_schema_version": SUMMARY_SCHEMA_VERSION,
        "read_model_schema": READ_MODEL_SCHEMA,
        "reducer_version": REDUCER_VERSION,
    }


def _version_ordinal(version: str) -> int | None:
    prefix = "aether.observation.event.v"
    if not version.startswith(prefix):
        return None
    tail = version[len(prefix) :]
    return int(tail) if tail.isdigit() else None


def is_known_version(version: Any) -> bool:
    return isinstance(version, str) and version in READ_SET


def upcast_event(event: Any) -> UpcastResult:
    """Bring one stored event to the current schema version, or refuse to touch it."""
    if not isinstance(event, dict):
        return UpcastResult(None, "malformed", "EVENT_NOT_OBJECT")
    version = event.get("schema_version")
    if not isinstance(version, str):
        return UpcastResult(None, "malformed", "SCHEMA_VERSION_MISSING")
    if version == EVENT_SCHEMA_VERSION:
        return UpcastResult(event, "ok")

    ordinal = _version_ordinal(version)
    current = _version_ordinal(EVENT_SCHEMA_VERSION)
    if ordinal is None or current is None:
        return UpcastResult(None, "unknown_schema", "SCHEMA_VERSION_UNRECOGNIZED")
    if ordinal > current:
        # Newer than this release understands. Preserve and quarantine; never guess.
        return UpcastResult(None, "unknown_schema", "SCHEMA_VERSION_NEWER")

    upgraded = dict(event)
    visited: set[str] = set()
    while True:
        version = upgraded.get("schema_version")
        if version == EVENT_SCHEMA_VERSION:
            return UpcastResult(upgraded, "ok")
        if not isinstance(version, str):
            return UpcastResult(None, "malformed", "UPCAST_SCHEMA_VERSION_INVALID")
        if version in visited:
            return UpcastResult(None, "malformed", "UPCAST_CYCLE")
        visited.add(version)
        transform = _UPCASTERS.get(version)
        if transform is None:
            return UpcastResult(None, "unknown_schema", "NO_UPCASTER")
        try:
            candidate = transform(upgraded)
        except Exception:  # pure, stable classification; never copy exception text
            return UpcastResult(None, "malformed", "UPCAST_FAILED")
        if not isinstance(candidate, dict):
            return UpcastResult(None, "malformed", "UPCAST_RESULT_NOT_OBJECT")
        upgraded = candidate
