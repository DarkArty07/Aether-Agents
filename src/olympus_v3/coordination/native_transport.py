"""Ledger-backed native dispatch composed from existing fenced ledger APIs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .leases import Lease
from .ledger import (
    AppendResult,
    Result,
    SignedEventDraft,
    SQLiteLedger,
    WriterContext,
)
from .protocol import Envelope, ValidationError
from .transport import TransportStatus


@dataclass(frozen=True, slots=True)
class NativeTransportReceipt:
    message_id: str
    status: TransportStatus
    ledger_result: Result | None
    reason: str | None = None

    def __post_init__(self) -> None:
        if (
            not isinstance(self.message_id, str)
            or not isinstance(self.status, TransportStatus)
            or (self.ledger_result is not None and not isinstance(self.ledger_result, Result))
            or (self.reason is not None and not isinstance(self.reason, str))
        ):
            raise ValidationError("invalid native transport receipt")


@dataclass(frozen=True, slots=True)
class NativeDispatch:
    message_id: str
    envelope: Envelope
    attempt: int

    def __post_init__(self) -> None:
        if (
            not isinstance(self.message_id, str)
            or not isinstance(self.envelope, Envelope)
            or isinstance(self.attempt, bool)
            or not isinstance(self.attempt, int)
            or self.attempt < 1
        ):
            raise ValidationError("invalid native dispatch")


class LedgerNativeTransport:
    """Stage and consume native dispatch through ``SQLiteLedger`` public methods."""

    def __init__(
        self,
        ledger: SQLiteLedger,
        *,
        owner: str,
        lease: Lease,
        enabled: bool = False,
        max_attempts: int = 5,
        lease_ns: int = 30_000_000_000,
        backoff_ns: int = 1_000_000_000,
    ):
        if (
            not isinstance(ledger, SQLiteLedger)
            or not isinstance(owner, str)
            or not owner
            or not isinstance(lease, Lease)
            or not isinstance(enabled, bool)
            or isinstance(max_attempts, bool)
            or not isinstance(max_attempts, int)
            or max_attempts < 1
            or isinstance(lease_ns, bool)
            or not isinstance(lease_ns, int)
            or lease_ns < 1
            or isinstance(backoff_ns, bool)
            or not isinstance(backoff_ns, int)
            or backoff_ns < 1
        ):
            raise ValidationError("invalid ledger native transport")
        self.ledger = ledger
        self.owner = owner
        self.lease = lease
        self.enabled = enabled
        self.max_attempts = max_attempts
        self.lease_ns = lease_ns
        self.backoff_ns = backoff_ns

    @staticmethod
    def _receipt(
        message_id: str,
        status: TransportStatus,
        ledger_result: Result | None,
        reason: str | None = None,
    ) -> NativeTransportReceipt:
        return NativeTransportReceipt(message_id, status, ledger_result, reason)

    def stage(
        self,
        envelope: Envelope,
        draft: SignedEventDraft,
        writer: WriterContext,
    ) -> NativeTransportReceipt:
        if (
            not isinstance(envelope, Envelope)
            or not isinstance(draft, SignedEventDraft)
            or not isinstance(writer, WriterContext)
        ):
            raise ValidationError("invalid native stage request")
        if not self.enabled:
            return self._receipt(
                envelope.message_id,
                TransportStatus.REJECTED,
                None,
                "coordination_disabled",
            )
        expected_payload = {
            "contract_id": envelope.contract_id,
            "envelope": envelope.to_dict(),
        }
        if (
            draft.aggregate != envelope.message_id
            or dict(draft.payload) != expected_payload
            or draft.scope != writer.scope
            or draft.scope.project_id != envelope.project_id
        ):
            return self._receipt(
                envelope.message_id,
                TransportStatus.REJECTED,
                Result.INVALID_INPUT,
                "envelope_binding_mismatch",
            )
        result: AppendResult = self.ledger.append(draft, writer, message_id=envelope.message_id)
        if result.status is Result.APPLIED:
            return self._receipt(envelope.message_id, TransportStatus.QUEUED, result.status)
        if result.status is Result.DUPLICATE:
            return self._receipt(
                envelope.message_id,
                TransportStatus.REJECTED,
                result.status,
                "duplicate_message",
            )
        return self._receipt(
            envelope.message_id,
            TransportStatus.REJECTED,
            result.status,
            result.status.value.lower(),
        )

    def claim(self, *, now: int) -> tuple[NativeDispatch, ...]:
        if not self.enabled:
            return ()
        rows = self.ledger.claim_outbox(
            self.owner,
            lease=self.lease,
            now=now,
            lease_ns=self.lease_ns,
            max_attempts=self.max_attempts,
        )
        if not rows:
            return ()
        events = {event["event_id"]: event for event in self.ledger.events()}
        dispatches: list[NativeDispatch] = []
        for row in rows:
            try:
                event = events[row["event_id"]]
                payload: Any = json.loads(event["payload"])
                envelope = Envelope.from_dict(payload["envelope"])
                if (
                    envelope.message_id != row["message_id"]
                    or envelope.contract_id != row["contract_id"]
                    or (
                        row["contract_generation"] is not None
                        and envelope.generation != row["contract_generation"]
                    )
                ):
                    raise ValueError("outbox scope mismatch")
            except (KeyError, TypeError, ValueError, ValidationError, json.JSONDecodeError):
                self.ledger.mark_outbox_retry(
                    row["message_id"],
                    self.owner,
                    lease=self.lease,
                    now=now,
                    backoff_ns=self.backoff_ns,
                    error="invalid envelope payload",
                    max_attempts=self.max_attempts,
                )
                continue
            dispatches.append(NativeDispatch(row["message_id"], envelope, row["attempts"]))
        return tuple(dispatches)

    def ack(self, message_id: str) -> NativeTransportReceipt:
        result = self.ledger.mark_outbox_sent(message_id, self.owner, lease=self.lease)
        if result is Result.TRANSPORT_ACKNOWLEDGED:
            return self._receipt(message_id, TransportStatus.ACKED, result)
        return self._receipt(message_id, TransportStatus.REJECTED, result, result.value.lower())

    def nack(self, message_id: str, *, now: int, error: str) -> NativeTransportReceipt:
        result = self.ledger.mark_outbox_retry(
            message_id,
            self.owner,
            lease=self.lease,
            now=now,
            backoff_ns=self.backoff_ns,
            error=error,
            max_attempts=self.max_attempts,
        )
        if result is Result.RETRY_SCHEDULED:
            return self._receipt(message_id, TransportStatus.RETRY_WAIT, result, "transport_failure")
        if result is Result.POISON_TERMINATED:
            return self._receipt(message_id, TransportStatus.NACKED, result, "transport_failure")
        return self._receipt(message_id, TransportStatus.REJECTED, result, result.value.lower())


__all__ = [
    "LedgerNativeTransport",
    "NativeDispatch",
    "NativeTransportReceipt",
]
