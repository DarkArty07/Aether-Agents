"""Advisory, expiring R4 presence projections.

Presence can support routing and stall detection, but never grants authority, proves
ownership, or establishes semantic completion.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from .protocol import ValidationError

MAX_PRESENCE_TTL = 300
MAX_ADVISORY_BYTES = 4_096
_MAX_INT = (1 << 63) - 1
_ID = re.compile(r"^[a-z0-9][a-z0-9._:-]{0,127}$")


def _id(value: Any, label: str) -> str:
    if not isinstance(value, str) or value != value.strip() or not _ID.fullmatch(value):
        raise ValidationError(f"invalid {label}")
    return value


def _integer(value: Any, label: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= _MAX_INT:
        raise ValidationError(f"invalid {label}")
    return value


def _advisory(value: Any) -> str:
    if not isinstance(value, str) or len(value.encode("utf-8")) > MAX_ADVISORY_BYTES:
        raise ValidationError("invalid presence advisory text")
    return value


def _fields(value: Any, expected: set[str], label: str) -> None:
    if not isinstance(value, dict) or set(value) != expected:
        raise ValidationError(f"invalid {label} fields")


class PresenceState(StrEnum):
    IDLE = "idle"
    WAITING = "waiting"
    WORKING = "working"
    OFFLINE = "offline"


@dataclass(frozen=True, slots=True)
class PresenceEvent:
    identity_id: str
    project_id: str
    state: PresenceState
    observed_at: int
    expires_at: int
    source_event_id: str
    sequence: int
    advisory_text: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "identity_id", _id(self.identity_id, "identity id"))
        object.__setattr__(self, "project_id", _id(self.project_id, "project id"))
        if not isinstance(self.state, PresenceState):
            raise ValidationError("invalid presence state")
        object.__setattr__(self, "observed_at", _integer(self.observed_at, "observed_at"))
        object.__setattr__(self, "expires_at", _integer(self.expires_at, "expires_at"))
        if self.expires_at <= self.observed_at or self.expires_at - self.observed_at > MAX_PRESENCE_TTL:
            raise ValidationError("invalid presence validity window")
        object.__setattr__(self, "source_event_id", _id(self.source_event_id, "source event id"))
        object.__setattr__(self, "sequence", _integer(self.sequence, "sequence", minimum=1))
        object.__setattr__(self, "advisory_text", _advisory(self.advisory_text))

    def to_dict(self) -> dict[str, Any]:
        return {
            "identity_id": self.identity_id,
            "project_id": self.project_id,
            "state": self.state.value,
            "observed_at": self.observed_at,
            "expires_at": self.expires_at,
            "source_event_id": self.source_event_id,
            "sequence": self.sequence,
            "advisory_text": self.advisory_text,
        }

    @classmethod
    def from_dict(cls, value: Any) -> PresenceEvent:
        fields = {
            "identity_id", "project_id", "state", "observed_at", "expires_at",
            "source_event_id", "sequence", "advisory_text",
        }
        _fields(value, fields, "presence event")
        try:
            state = PresenceState(value["state"])
        except (TypeError, ValueError) as exc:
            raise ValidationError("invalid presence state") from exc
        return cls(
            value["identity_id"], value["project_id"], state, value["observed_at"], value["expires_at"],
            value["source_event_id"], value["sequence"], value["advisory_text"],
        )


@dataclass(frozen=True, slots=True)
class PresenceProjection:
    identity_id: str
    project_id: str
    state: PresenceState
    observed_at: int
    expires_at: int
    source_event_id: str | None
    sequence: int
    advisory_text: str
    stale: bool
    authoritative: bool = False
    can_authorize: bool = False

    def __post_init__(self) -> None:
        if self.authoritative or self.can_authorize:
            raise ValidationError("presence is never authoritative")


class PresenceTracker:
    """Project-local last-write projection ordered only by trusted server sequence."""

    def __init__(self, *, project_id: str):
        self.project_id = _id(project_id, "project id")
        self._events: dict[str, PresenceEvent] = {}

    def apply(self, event: PresenceEvent) -> bool:
        if not isinstance(event, PresenceEvent) or event.project_id != self.project_id:
            raise ValidationError("presence project mismatch")
        current = self._events.get(event.identity_id)
        if current is not None and event.sequence <= current.sequence:
            return False
        self._events[event.identity_id] = event
        return True

    def get(self, identity_id: str, *, now: int) -> PresenceProjection:
        identity_id = _id(identity_id, "identity id")
        now = _integer(now, "now")
        event = self._events.get(identity_id)
        if event is None:
            return PresenceProjection(identity_id, self.project_id, PresenceState.OFFLINE, now, now, None, 0, "", True)
        stale = event.expires_at <= now
        return PresenceProjection(
            event.identity_id,
            event.project_id,
            PresenceState.OFFLINE if stale else event.state,
            event.observed_at,
            event.expires_at,
            event.source_event_id,
            event.sequence,
            event.advisory_text,
            stale,
        )


__all__ = [
    "MAX_ADVISORY_BYTES",
    "MAX_PRESENCE_TTL",
    "PresenceEvent",
    "PresenceProjection",
    "PresenceState",
    "PresenceTracker",
]
