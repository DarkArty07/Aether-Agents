"""Default-off native transport planning with bounded delivery state.

The adapter validates and queues immutable envelopes, then emits dispatch intents.
It performs no network, process, session, database, or ACP lifecycle operation.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from .capabilities import AuthorizationResult
from .channels import Channel, ChannelACL, can_publish
from .identity import IdentityCredential, IdentityRegistry
from .protocol import (
    ChannelRoute,
    Envelope,
    MessageType,
    ParticipantCard,
    ParticipantRoute,
    Principal,
    RoleRoute,
    ValidationError,
)

_REASON = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_MAX_INT = (1 << 63) - 1


class TransportStatus(StrEnum):
    QUEUED = "queued"
    IN_FLIGHT = "in_flight"
    ACKED = "acked"
    RETRY_WAIT = "retry_wait"
    NACKED = "nacked"
    REJECTED = "rejected"


def _integer(value: Any, label: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= _MAX_INT:
        raise ValidationError(f"invalid {label}")
    return value


def _reason(value: Any, label: str = "transport reason") -> str:
    if not isinstance(value, str) or not _REASON.fullmatch(value):
        raise ValidationError(f"invalid {label}")
    return value


@dataclass(frozen=True, slots=True)
class ChannelPublishContext:
    registry: IdentityRegistry
    identity: IdentityCredential
    channel: Channel
    acl: ChannelACL
    trusted_issuer: str
    audience: str
    now: int
    current_generation: int
    current_revocation_epoch: int

    def __post_init__(self) -> None:
        if (
            not isinstance(self.registry, IdentityRegistry)
            or not isinstance(self.identity, IdentityCredential)
            or not isinstance(self.channel, Channel)
            or not isinstance(self.acl, ChannelACL)
            or not isinstance(self.trusted_issuer, str)
            or not isinstance(self.audience, str)
        ):
            raise ValidationError("invalid channel publish context")
        object.__setattr__(self, "now", _integer(self.now, "channel time"))
        object.__setattr__(self, "current_generation", _integer(self.current_generation, "channel generation"))
        object.__setattr__(
            self,
            "current_revocation_epoch",
            _integer(self.current_revocation_epoch, "channel revocation epoch"),
        )


@dataclass(frozen=True, slots=True)
class TransportReceipt:
    message_id: str
    status: TransportStatus
    attempt: int
    reason: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.message_id, str) or not self.message_id or not isinstance(self.status, TransportStatus):
            raise ValidationError("invalid transport receipt")
        object.__setattr__(self, "attempt", _integer(self.attempt, "transport attempt"))
        if self.reason is not None:
            object.__setattr__(self, "reason", _reason(self.reason))
        if self.status is TransportStatus.REJECTED and self.reason is None:
            raise ValidationError("rejected transport receipt requires reason")


@dataclass(frozen=True, slots=True)
class DispatchIntent:
    message_id: str
    envelope: Envelope
    participant: Principal | None
    channel_id: str | None
    attempt: int

    def __post_init__(self) -> None:
        if (
            not isinstance(self.message_id, str)
            or not isinstance(self.envelope, Envelope)
            or (self.participant is None) == (self.channel_id is None)
        ):
            raise ValidationError("invalid dispatch intent")
        object.__setattr__(self, "attempt", _integer(self.attempt, "dispatch attempt", minimum=1))


@dataclass(frozen=True, slots=True)
class _QueueItem:
    envelope: Envelope
    participant: Principal | None
    channel_id: str | None
    status: TransportStatus
    attempt: int
    available_at: int
    reason: str | None = None


class NativeTransportAdapter:
    """Validate, queue, and acknowledge transport intents without performing I/O."""

    def __init__(
        self,
        *,
        enabled: bool = False,
        max_pending: int = 128,
        max_attempts: int = 3,
        retry_delay_seconds: int = 5,
        max_payload_bytes: int = 16_384,
    ):
        if not isinstance(enabled, bool):
            raise ValidationError("invalid transport enabled flag")
        self.enabled = enabled
        self.max_pending = _integer(max_pending, "max pending", minimum=1)
        self.max_attempts = _integer(max_attempts, "max attempts", minimum=1)
        self.retry_delay_seconds = _integer(retry_delay_seconds, "retry delay", minimum=1)
        self.max_payload_bytes = _integer(max_payload_bytes, "transport payload limit", minimum=1)
        self._items: dict[str, _QueueItem] = {}

    @property
    def pending_count(self) -> int:
        return sum(
            item.status in {TransportStatus.QUEUED, TransportStatus.IN_FLIGHT, TransportStatus.RETRY_WAIT}
            for item in self._items.values()
        )

    @staticmethod
    def _rejected(envelope: Envelope, reason: str) -> TransportReceipt:
        return TransportReceipt(envelope.message_id, TransportStatus.REJECTED, 0, reason)

    def submit(
        self,
        envelope: Envelope,
        authorization: AuthorizationResult,
        *,
        current_generation: int,
        participants: tuple[Principal, ...] = (),
        cards: tuple[ParticipantCard, ...] = (),
        channel_context: ChannelPublishContext | None = None,
    ) -> TransportReceipt:
        if not isinstance(envelope, Envelope) or not isinstance(authorization, AuthorizationResult):
            raise ValidationError("invalid transport submission")
        generation = _integer(current_generation, "current generation")
        if not isinstance(participants, tuple) or any(not isinstance(item, Principal) for item in participants):
            raise ValidationError("invalid transport participants")
        if not isinstance(cards, tuple) or any(not isinstance(item, ParticipantCard) for item in cards):
            raise ValidationError("invalid transport cards")
        if not self.enabled:
            return self._rejected(envelope, "coordination_disabled")
        if envelope.message_id in self._items:
            return self._rejected(envelope, "duplicate_message")
        if not authorization.granted:
            return self._rejected(envelope, "capability_denied")
        if envelope.generation != generation:
            return self._rejected(envelope, "stale_generation")
        if envelope.message_type is MessageType.REQUEST and envelope.correlation_id is None:
            return self._rejected(envelope, "correlation_required")
        encoded = json.dumps(
            envelope.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
        if len(encoded) > self.max_payload_bytes:
            return self._rejected(envelope, "payload_limit_exceeded")
        if self.pending_count >= self.max_pending:
            return self._rejected(envelope, "backpressure")

        participant: Principal | None = None
        channel_id: str | None = None
        if isinstance(envelope.route, ParticipantRoute):
            if envelope.route.participant not in participants:
                return self._rejected(envelope, "unknown_participant")
            participant = envelope.route.participant
        elif isinstance(envelope.route, RoleRoute):
            eligible = sorted(
                {
                    card.principal
                    for card in cards
                    if card.role == envelope.route.role and card.principal in participants
                },
                key=lambda item: (item.owner_id, item.actor_id),
            )
            if not eligible:
                return self._rejected(envelope, "unknown_role")
            participant = eligible[0]
        elif isinstance(envelope.route, ChannelRoute):
            if channel_context is None or channel_context.channel.channel_id != envelope.route.channel:
                return self._rejected(envelope, "channel_publish_denied")
            if (
                channel_context.channel.project_id != envelope.project_id
                or channel_context.channel.contract_id != envelope.contract_id
                or channel_context.channel.generation != envelope.generation
            ):
                return self._rejected(envelope, "channel_scope_mismatch")
            if not can_publish(
                channel_context.registry,
                channel_context.identity,
                channel_context.channel,
                channel_context.acl,
                authorization,
                trusted_issuer=channel_context.trusted_issuer,
                audience=channel_context.audience,
                now=channel_context.now,
                current_generation=channel_context.current_generation,
                current_revocation_epoch=channel_context.current_revocation_epoch,
            ):
                return self._rejected(envelope, "channel_publish_denied")
            channel_id = envelope.route.channel
        else:
            return self._rejected(envelope, "unsupported_route")

        self._items[envelope.message_id] = _QueueItem(
            envelope, participant, channel_id, TransportStatus.QUEUED, 0, 0
        )
        return TransportReceipt(envelope.message_id, TransportStatus.QUEUED, 0)

    def next_batch(self, *, limit: int, now: int) -> tuple[DispatchIntent, ...]:
        limit = _integer(limit, "dispatch limit", minimum=1)
        now = _integer(now, "dispatch time")
        selected = [
            (message_id, item)
            for message_id, item in sorted(self._items.items())
            if item.status in {TransportStatus.QUEUED, TransportStatus.RETRY_WAIT}
            and item.available_at <= now
        ][:limit]
        intents: list[DispatchIntent] = []
        for message_id, item in selected:
            attempt = item.attempt + 1
            self._items[message_id] = _QueueItem(
                item.envelope,
                item.participant,
                item.channel_id,
                TransportStatus.IN_FLIGHT,
                attempt,
                now,
            )
            intents.append(DispatchIntent(message_id, item.envelope, item.participant, item.channel_id, attempt))
        return tuple(intents)

    def ack(self, message_id: str) -> TransportReceipt:
        item = self._items.get(message_id)
        if item is None or item.status is not TransportStatus.IN_FLIGHT:
            raise ValidationError("message is not in flight")
        self._items[message_id] = _QueueItem(
            item.envelope, item.participant, item.channel_id, TransportStatus.ACKED, item.attempt, 0
        )
        return TransportReceipt(message_id, TransportStatus.ACKED, item.attempt)

    def nack(self, message_id: str, *, now: int, reason: str) -> TransportReceipt:
        now = _integer(now, "nack time")
        reason = _reason(reason)
        item = self._items.get(message_id)
        if item is None or item.status is not TransportStatus.IN_FLIGHT:
            raise ValidationError("message is not in flight")
        if item.attempt >= self.max_attempts:
            status = TransportStatus.NACKED
            available_at = 0
        else:
            status = TransportStatus.RETRY_WAIT
            available_at = now + self.retry_delay_seconds * item.attempt
        self._items[message_id] = _QueueItem(
            item.envelope, item.participant, item.channel_id, status, item.attempt, available_at, reason
        )
        return TransportReceipt(message_id, status, item.attempt, reason)


__all__ = [
    "ChannelPublishContext",
    "DispatchIntent",
    "NativeTransportAdapter",
    "TransportReceipt",
    "TransportStatus",
]
