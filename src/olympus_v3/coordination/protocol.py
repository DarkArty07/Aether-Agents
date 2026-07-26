"""Pure, immutable coordination protocol values and wire validation."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Mapping

MAX_PAYLOAD_BYTES = 16_384
MAX_METADATA_BYTES = 8_192
MAX_NESTING_DEPTH = 8
MAX_PARTS = 32
MAX_REFERENCES = 32
MAX_REFERENCE_LENGTH = 256
MAX_METADATA_ITEMS = 32

_ID = re.compile(r"^[a-z0-9][a-z0-9._:-]{7,127}$")
_NAME = re.compile(r"^[a-z][a-z0-9._:/-]{0,127}$")


class ValidationError(ValueError):
    """Raised when a protocol value or wire representation is invalid."""


class MessageType(StrEnum):
    CONTEXT = "context"
    QUESTION = "question"
    RESULT = "result"
    REQUEST = "request"
    STATUS = "status"


class AuthorityClass(StrEnum):
    INFORMATIONAL = "informational"
    REQUEST = "request"
    RESULT = "result"
    AUTHORIZED_CONTROL = "authorized_control"


def _name(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _NAME.fullmatch(value) or value != value.strip():
        raise ValidationError(f"invalid {label}")
    return value


def _id(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _ID.fullmatch(value) or value != value.strip():
        raise ValidationError(f"invalid {label}")
    return value


def _freeze(value: Any, *, depth: int = 0) -> Any:
    if depth > MAX_NESTING_DEPTH:
        raise ValidationError("maximum nesting depth exceeded")
    if value is None or isinstance(value, (str, int, float, bool)):
        if isinstance(value, float) and (value != value or value in (float("inf"), float("-inf"))):
            raise ValidationError("invalid metadata")
        return value
    if isinstance(value, Mapping):
        if len(value) > MAX_METADATA_ITEMS or any(not isinstance(k, str) or len(k) > 128 for k in value):
            raise ValidationError("invalid metadata")
        return MappingProxyType({k: _freeze(v, depth=depth + 1) for k, v in sorted(value.items())})
    if isinstance(value, (tuple, list)):
        if len(value) > MAX_METADATA_ITEMS:
            raise ValidationError("invalid metadata")
        return tuple(_freeze(item, depth=depth + 1) for item in value)
    raise ValidationError("invalid metadata")


def _wire_json(value: Any, label: str = "payload", *, max_bytes: int = MAX_PAYLOAD_BYTES) -> str:
    try:
        encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValidationError(f"invalid {label}") from exc
    if len(encoded.encode("utf-8")) > max_bytes:
        raise ValidationError(f"{label} exceeds limit")
    return encoded


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


@dataclass(frozen=True, slots=True)
class ParticipantCard:
    principal: Principal
    role: str
    model: str
    skills: tuple[str, ...]
    metadata: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        if not isinstance(self.principal, Principal):
            raise ValidationError("invalid card principal")
        object.__setattr__(self, "role", _name(self.role, "role"))
        object.__setattr__(self, "model", _name(self.model, "model"))
        if not isinstance(self.skills, tuple) or not self.skills or len(self.skills) > MAX_METADATA_ITEMS:
            raise ValidationError("invalid skills")
        skills = tuple(_name(skill, "skill") for skill in self.skills)
        if len(set(skills)) != len(skills):
            raise ValidationError("duplicate skills")
        if not isinstance(self.metadata, Mapping):
            raise ValidationError("invalid metadata")
        if any(isinstance(value, (dict, list, set, bytearray)) for value in self.metadata.values()):
            raise ValidationError("mutable metadata is not allowed")
        object.__setattr__(self, "skills", skills)
        metadata = _freeze(dict(self.metadata))
        _wire_json(_thaw(metadata), "metadata", max_bytes=MAX_METADATA_BYTES)
        object.__setattr__(self, "metadata", metadata)

    def to_dict(self) -> dict[str, Any]:
        return {"principal": self.principal.to_dict(), "role": self.role, "model": self.model, "skills": list(self.skills), "metadata": _thaw(self.metadata)}

    @classmethod
    def from_dict(cls, value: Any) -> ParticipantCard:
        _fields(value, {"principal", "role", "model", "skills", "metadata"}, "participant card")
        if not isinstance(value["skills"], list):
            raise ValidationError("invalid skills")
        return cls(Principal.from_dict(value["principal"]), value["role"], value["model"], tuple(value["skills"]), value["metadata"])


@dataclass(frozen=True, slots=True)
class MessagePart:
    kind: str
    payload: Any

    def __post_init__(self) -> None:
        kind = _name(self.kind, "part kind")
        if kind not in {"text", "json"}:
            raise ValidationError("unsupported part kind")
        if kind == "text" and not isinstance(self.payload, str):
            raise ValidationError("malformed text payload")
        if kind == "json" and isinstance(self.payload, (bytes, bytearray)):
            raise ValidationError("malformed json payload")
        frozen = _freeze(self.payload)
        _wire_json(_thaw(frozen), "payload")
        object.__setattr__(self, "kind", kind)
        object.__setattr__(self, "payload", frozen)

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "payload": _thaw(self.payload)}

    @classmethod
    def from_dict(cls, value: Any) -> MessagePart:
        _fields(value, {"kind", "payload"}, "message part")
        return cls(value["kind"], value["payload"])


@dataclass(frozen=True, slots=True)
class ChannelRoute:
    channel: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "channel", _name(self.channel, "channel"))

    def to_dict(self) -> dict[str, str]:
        return {"kind": "channel", "channel": self.channel}


@dataclass(frozen=True, slots=True)
class ParticipantRoute:
    participant: Principal

    def __post_init__(self) -> None:
        if not isinstance(self.participant, Principal):
            raise ValidationError("invalid participant target")

    def to_dict(self) -> dict[str, Any]:
        return {"kind": "participant", "participant": self.participant.to_dict()}


@dataclass(frozen=True, slots=True)
class RoleRoute:
    role: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "role", _name(self.role, "role"))

    def to_dict(self) -> dict[str, str]:
        return {"kind": "role", "role": self.role}


Route = ChannelRoute | ParticipantRoute | RoleRoute


@dataclass(frozen=True, slots=True)
class Envelope:
    message_id: str
    timestamp: datetime
    sender: Principal
    sender_card: ParticipantCard
    message_type: MessageType
    authority: AuthorityClass
    project_id: str
    contract_id: str
    generation: int
    task_id: str | None
    correlation_id: str | None
    reply_to: str | None
    references: tuple[str, ...]
    parts: tuple[MessagePart, ...]
    route: Route

    def __post_init__(self) -> None:
        object.__setattr__(self, "message_id", _id(self.message_id, "message id"))
        if not isinstance(self.timestamp, datetime) or self.timestamp.tzinfo is None or self.timestamp.utcoffset() is None or self.timestamp.utcoffset() != UTC.utcoffset(self.timestamp):
            raise ValidationError("timestamp must be UTC")
        object.__setattr__(self, "timestamp", self.timestamp.astimezone(UTC))
        if not isinstance(self.sender, Principal) or not isinstance(self.sender_card, ParticipantCard):
            raise ValidationError("invalid sender identity")
        project = _name(self.project_id, "project")
        if project != self.sender.project_id or self.sender_card.principal != self.sender:
            raise ValidationError("sender identity does not match project/card")
        if not isinstance(self.message_type, MessageType) or not isinstance(self.authority, AuthorityClass):
            raise ValidationError("invalid message classification")
        object.__setattr__(self, "project_id", project)
        object.__setattr__(self, "contract_id", _id(self.contract_id, "contract id"))
        if not isinstance(self.generation, int) or isinstance(self.generation, bool) or self.generation < 0:
            raise ValidationError("invalid generation")
        for value, label in ((self.task_id, "task id"), (self.correlation_id, "correlation id"), (self.reply_to, "reply-to")):
            if value is not None:
                _id(value, label)
        if self.reply_to is not None and self.correlation_id is None:
            raise ValidationError("reply-to requires correlation")
        if not isinstance(self.references, tuple) or len(self.references) > MAX_REFERENCES or len(set(self.references)) != len(self.references):
            raise ValidationError("invalid references")
        for reference in self.references:
            _id(reference, "reference")
            if len(reference) > MAX_REFERENCE_LENGTH:
                raise ValidationError("reference exceeds limit")
        if not isinstance(self.parts, tuple) or not self.parts or len(self.parts) > MAX_PARTS or any(not isinstance(part, MessagePart) for part in self.parts):
            raise ValidationError("invalid parts")
        if not isinstance(self.route, (ChannelRoute, ParticipantRoute, RoleRoute)):
            raise ValidationError("exactly one route is required")
        if isinstance(self.route, ParticipantRoute) and self.route.participant.project_id != project:
            raise ValidationError("route project mismatch")

    def to_dict(self) -> dict[str, Any]:
        return {
            "message_id": self.message_id, "timestamp": self.timestamp.isoformat().replace("+00:00", "Z"),
            "sender": self.sender.to_dict(), "sender_card": self.sender_card.to_dict(),
            "message_type": self.message_type.value, "authority": self.authority.value, "project_id": self.project_id,
            "contract_id": self.contract_id, "generation": self.generation, "task_id": self.task_id,
            "correlation_id": self.correlation_id, "reply_to": self.reply_to, "references": list(self.references),
            "parts": [part.to_dict() for part in self.parts], "route": self.route.to_dict(),
        }

    @classmethod
    def from_dict(cls, value: Any) -> Envelope:
        fields = {"message_id", "timestamp", "sender", "sender_card", "message_type", "authority", "project_id", "contract_id", "generation", "task_id", "correlation_id", "reply_to", "references", "parts", "route"}
        _fields(value, fields, "envelope")
        if not isinstance(value["references"], list) or not isinstance(value["parts"], list):
            raise ValidationError("malformed envelope collections")
        try:
            timestamp = datetime.fromisoformat(value["timestamp"].replace("Z", "+00:00"))
            message_type = MessageType(value["message_type"])
            authority = AuthorityClass(value["authority"])
        except (AttributeError, TypeError, ValueError) as exc:
            raise ValidationError("malformed envelope metadata") from exc
        route = _route_from_dict(value["route"])
        return cls(value["message_id"], timestamp, Principal.from_dict(value["sender"]), ParticipantCard.from_dict(value["sender_card"]), message_type, authority, value["project_id"], value["contract_id"], value["generation"], value["task_id"], value["correlation_id"], value["reply_to"], tuple(value["references"]), tuple(MessagePart.from_dict(part) for part in value["parts"]), route)


def _fields(value: Any, expected: set[str], label: str) -> None:
    if not isinstance(value, dict) or set(value) != expected:
        raise ValidationError(f"invalid {label} fields")


def _route_from_dict(value: Any) -> Route:
    if not isinstance(value, dict):
        raise ValidationError("invalid route fields")
    kind = value.get("kind")
    if kind == "channel" and set(value) == {"kind", "channel"}:
        return ChannelRoute(value["channel"])
    if kind == "participant" and set(value) == {"kind", "participant"}:
        return ParticipantRoute(Principal.from_dict(value["participant"]))
    if kind == "role" and set(value) == {"kind", "role"}:
        return RoleRoute(value["role"])
    raise ValidationError("unsupported route")


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value
