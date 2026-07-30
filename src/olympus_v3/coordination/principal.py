"""Project-scoped coordination identity and shared validation error."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

_ID = re.compile(r"^[a-z0-9][a-z0-9._:-]{7,127}$")
_NAME = re.compile(r"^[a-z][a-z0-9._:/-]{0,127}$")


class ValidationError(ValueError):
    """Raised when a coordination value is malformed."""


def _name(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _NAME.fullmatch(value) or value != value.strip():
        raise ValidationError(f"invalid {label}")
    return value


def _id(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _ID.fullmatch(value) or value != value.strip():
        raise ValidationError(f"invalid {label}")
    return value


def _fields(value: Any, expected: set[str], label: str) -> None:
    if not isinstance(value, dict) or set(value) != expected:
        raise ValidationError(f"invalid {label} fields")


@dataclass(frozen=True, slots=True)
class Principal:
    project_id: str
    owner_id: str
    actor_id: str

    def __post_init__(self) -> None:
        project = _id(self.project_id, "project")
        owner = _name(self.owner_id, "owner")
        actor = _name(self.actor_id, "actor")
        if owner == actor:
            raise ValidationError("owner and actor must remain separate")
        object.__setattr__(self, "project_id", project)
        object.__setattr__(self, "owner_id", owner)
        object.__setattr__(self, "actor_id", actor)

    def to_dict(self) -> dict[str, str]:
        return {"project_id": self.project_id, "owner_id": self.owner_id, "actor_id": self.actor_id}

    @classmethod
    def from_dict(cls, value: Any) -> Principal:
        _fields(value, {"project_id", "owner_id", "actor_id"}, "principal")
        return cls(value["project_id"], value["owner_id"], value["actor_id"])


__all__ = ["Principal", "ValidationError"]
