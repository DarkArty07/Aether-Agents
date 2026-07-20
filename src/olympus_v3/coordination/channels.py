"""Default-deny R4 channel metadata and independent access predicates.

Channel state and ACLs do not create capabilities. Publishing additionally requires a
grant from the canonical capability authorization boundary.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from .capabilities import AuthorizationResult
from .identity import IdentityCredential, IdentityRegistry, verify_identity_credential
from .protocol import ValidationError

MAX_CHANNEL_MEMBERS = 256
_MAX_INT = (1 << 63) - 1
_ID = re.compile(r"^[a-z0-9][a-z0-9._:-]{0,127}$")


def _id(value: Any, label: str) -> str:
    if not isinstance(value, str) or value != value.strip() or not _ID.fullmatch(value):
        raise ValidationError(f"invalid {label}")
    return value


def _integer(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= _MAX_INT:
        raise ValidationError(f"invalid {label}")
    return value


def _fields(value: Any, expected: set[str], label: str) -> None:
    if not isinstance(value, dict) or set(value) != expected:
        raise ValidationError(f"invalid {label} fields")


def _members(value: Any, label: str) -> frozenset[str]:
    if not isinstance(value, frozenset) or len(value) > MAX_CHANNEL_MEMBERS:
        raise ValidationError(f"invalid {label}")
    result = frozenset(_id(member, "channel identity") for member in value)
    if len(result) != len(value):
        raise ValidationError(f"invalid {label}")
    return result


class DeliveryClass(StrEnum):
    LIVE = "live"
    DURABLE = "durable"


@dataclass(frozen=True, slots=True)
class Channel:
    channel_id: str
    project_id: str
    contract_id: str
    generation: int
    revocation_epoch: int
    delivery_class: DeliveryClass
    active: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "channel_id", _id(self.channel_id, "channel id"))
        object.__setattr__(self, "project_id", _id(self.project_id, "project id"))
        object.__setattr__(self, "contract_id", _id(self.contract_id, "contract id"))
        object.__setattr__(self, "generation", _integer(self.generation, "generation"))
        object.__setattr__(self, "revocation_epoch", _integer(self.revocation_epoch, "revocation epoch"))
        if not isinstance(self.delivery_class, DeliveryClass) or not isinstance(self.active, bool):
            raise ValidationError("invalid channel metadata")

    @property
    def is_durable_evidence(self) -> bool:
        return self.delivery_class is DeliveryClass.DURABLE

    @property
    def proves_completion(self) -> bool:
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "channel_id": self.channel_id,
            "project_id": self.project_id,
            "contract_id": self.contract_id,
            "generation": self.generation,
            "revocation_epoch": self.revocation_epoch,
            "delivery_class": self.delivery_class.value,
            "active": self.active,
        }

    @classmethod
    def from_dict(cls, value: Any) -> Channel:
        fields = {
            "channel_id", "project_id", "contract_id", "generation", "revocation_epoch", "delivery_class", "active",
        }
        _fields(value, fields, "channel")
        try:
            delivery_class = DeliveryClass(value["delivery_class"])
        except (TypeError, ValueError) as exc:
            raise ValidationError("invalid delivery class") from exc
        return cls(
            value["channel_id"], value["project_id"], value["contract_id"], value["generation"],
            value["revocation_epoch"], delivery_class, value["active"],
        )


@dataclass(frozen=True, slots=True)
class ChannelACL:
    channel_id: str
    project_id: str
    contract_id: str
    generation: int
    revocation_epoch: int
    read: frozenset[str]
    publish: frozenset[str]

    def __post_init__(self) -> None:
        object.__setattr__(self, "channel_id", _id(self.channel_id, "channel id"))
        object.__setattr__(self, "project_id", _id(self.project_id, "project id"))
        object.__setattr__(self, "contract_id", _id(self.contract_id, "contract id"))
        object.__setattr__(self, "generation", _integer(self.generation, "generation"))
        object.__setattr__(self, "revocation_epoch", _integer(self.revocation_epoch, "revocation epoch"))
        object.__setattr__(self, "read", _members(self.read, "read ACL"))
        object.__setattr__(self, "publish", _members(self.publish, "publish ACL"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "channel_id": self.channel_id,
            "project_id": self.project_id,
            "contract_id": self.contract_id,
            "generation": self.generation,
            "revocation_epoch": self.revocation_epoch,
            "read": sorted(self.read),
            "publish": sorted(self.publish),
        }

    @classmethod
    def from_dict(cls, value: Any) -> ChannelACL:
        fields = {"channel_id", "project_id", "contract_id", "generation", "revocation_epoch", "read", "publish"}
        _fields(value, fields, "channel ACL")
        if not isinstance(value["read"], list) or not isinstance(value["publish"], list):
            raise ValidationError("invalid channel ACL collections")
        return cls(
            value["channel_id"], value["project_id"], value["contract_id"], value["generation"],
            value["revocation_epoch"], frozenset(value["read"]), frozenset(value["publish"]),
        )


def _acl_matches(channel: Channel, acl: ChannelACL) -> bool:
    return (
        acl.channel_id == channel.channel_id
        and acl.project_id == channel.project_id
        and acl.contract_id == channel.contract_id
        and acl.generation == channel.generation
        and acl.revocation_epoch == channel.revocation_epoch
    )


def can_activate(
    registry: IdentityRegistry,
    identity: IdentityCredential,
    channel: Channel,
    *,
    trusted_issuer: str,
    audience: str,
    now: int,
    current_generation: int,
    current_revocation_epoch: int,
) -> bool:
    """Verify identity and channel liveness/scope; never grant read or publish."""
    if (
        not isinstance(registry, IdentityRegistry)
        or not isinstance(identity, IdentityCredential)
        or not isinstance(channel, Channel)
    ):
        return False
    try:
        issuer = _id(trusted_issuer, "trusted issuer")
        expected_audience = _id(audience, "audience")
        current_time = _integer(now, "now")
        generation = _integer(current_generation, "current generation")
        epoch = _integer(current_revocation_epoch, "current revocation epoch")
    except ValidationError:
        return False
    return (
        identity.issuer == issuer
        and verify_identity_credential(registry, identity, audience=expected_audience, now=current_time)
        and channel.active
        and identity.binding.project_id == channel.project_id
        and channel.generation == generation
        and channel.revocation_epoch == epoch
    )


def can_read(
    registry: IdentityRegistry,
    identity: IdentityCredential,
    channel: Channel,
    acl: ChannelACL,
    *,
    trusted_issuer: str,
    audience: str,
    now: int,
    current_generation: int,
    current_revocation_epoch: int,
) -> bool:
    if not isinstance(acl, ChannelACL) or not _acl_matches(channel, acl):
        return False
    return can_activate(
        registry,
        identity,
        channel,
        trusted_issuer=trusted_issuer,
        audience=audience,
        now=now,
        current_generation=current_generation,
        current_revocation_epoch=current_revocation_epoch,
    ) and identity.identity_id in acl.read


def can_publish(
    registry: IdentityRegistry,
    identity: IdentityCredential,
    channel: Channel,
    acl: ChannelACL,
    authorization: AuthorizationResult,
    *,
    trusted_issuer: str,
    audience: str,
    now: int,
    current_generation: int,
    current_revocation_epoch: int,
) -> bool:
    if (
        not isinstance(acl, ChannelACL)
        or not _acl_matches(channel, acl)
        or not isinstance(authorization, AuthorizationResult)
        or not authorization.granted
    ):
        return False
    return can_activate(
        registry,
        identity,
        channel,
        trusted_issuer=trusted_issuer,
        audience=audience,
        now=now,
        current_generation=current_generation,
        current_revocation_epoch=current_revocation_epoch,
    ) and identity.identity_id in acl.publish


__all__ = [
    "Channel",
    "ChannelACL",
    "DeliveryClass",
    "MAX_CHANNEL_MEMBERS",
    "can_activate",
    "can_publish",
    "can_read",
]
