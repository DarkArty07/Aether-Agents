"""Durable observation identities and deduplication keys.

Normative decisions: OBS-D-024 (identity), OBS-D-029 (segment identity),
OBS-D-031 (producer epochs), OBS-FR-079.

PIDs are reusable and wall clocks collide, so no identity in this module is derived
from a process ID, a timestamp, a profile name, or a filesystem path.
"""

from __future__ import annotations

import re
import secrets
import threading
from dataclasses import dataclass
from typing import Any, Final

from aether_agents.observation.contracts import (
    canonical_digest,
    is_opaque_ref,
    sha256_hex,
)

__all__ = [
    "CORRELATION_TOKEN_PREFIX",
    "ProducerSequence",
    "attribution_id",
    "binding_ref",
    "correlation_token",
    "deterministic_event_id",
    "fingerprint_key_id",
    "native_identity",
    "new_event_id",
    "new_producer_epoch",
    "new_trace_id",
    "parse_correlation_token",
    "segment_id",
    "summary_id",
]

_TRACE_PREFIX: Final = "ctr_"
_PRODUCER_PREFIX: Final = "prd_"
_EVENT_PREFIX: Final = "evt_"
_SUMMARY_PREFIX: Final = "sum_"
_SEGMENT_PREFIX: Final = "seg_"
_KEY_PREFIX: Final = "fpk_"

#: OBS-D-014: the deterministic opaque token attached inside the existing kanban_create.
CORRELATION_TOKEN_PREFIX: Final = "aether.obs.v1:"

_TOKEN_RE: Final = re.compile(
    r"^aether\.obs\.v1:(?P<trace>ctr_[a-f0-9]{32}):(?P<unit>[A-Za-z0-9][A-Za-z0-9_.-]{0,127})$",
    re.ASCII,
)
_TRACE_RE: Final = re.compile(r"^ctr_[a-f0-9]{32}$", re.ASCII)
_PRODUCER_RE: Final = re.compile(r"^prd_[a-f0-9]{32}$", re.ASCII)


def _random_128() -> str:
    """32 lowercase hexadecimal characters from 128 cryptographically random bits."""
    return secrets.token_hex(16)


def new_trace_id() -> str:
    """Allocate a trace ID once, at authoritative materialization."""
    return _TRACE_PREFIX + _random_128()


def new_producer_epoch() -> str:
    """Allocate one process identity. Never a PID (OBS-D-031)."""
    return _PRODUCER_PREFIX + _random_128()


def new_event_id() -> str:
    """Allocate a random event ID once, before append, for an incomplete native tuple."""
    return _EVENT_PREFIX + _random_128()


def native_identity(**parts: Any) -> dict[str, Any] | None:
    """Build a complete stable native source tuple, or ``None`` when any part is missing.

    An incomplete tuple is never fuzzy-matched: the caller falls back to
    :func:`new_event_id` and the reducer deduplicates only on the event ID.
    """
    if not parts:
        return None
    for key, value in parts.items():
        if not is_opaque_ref(key):
            return None
        if isinstance(value, bool) or value is None:
            return None
        if isinstance(value, int):
            if value < 0:
                return None
            continue
        if not is_opaque_ref(value, max_len=256):
            return None
    return dict(parts)


def deterministic_event_id(identity: dict[str, Any]) -> str:
    """Derive an event ID from a complete native identity tuple.

    Deterministic IDs use the 64-hex form so a replayed hook and a later
    reconciliation of the same native fact collapse to one row.
    """
    if not identity or native_identity(**identity) is None:
        raise ValueError("deterministic_event_id requires a complete native identity")
    return _EVENT_PREFIX + canonical_digest({"aether.observation.event-id.v1": identity})


def summary_id(summary_without_id: dict[str, Any]) -> str:
    """``sum_`` plus SHA-256 of the canonical summary with ``summary_id`` omitted."""
    payload = {k: v for k, v in summary_without_id.items() if k != "summary_id"}
    return _SUMMARY_PREFIX + canonical_digest(payload)


def segment_id(uncompressed_sha256: str) -> str:
    """``seg_`` plus the uncompressed segment digest (OBS-D-029)."""
    if not re.fullmatch(r"[a-f0-9]{64}", uncompressed_sha256):
        raise ValueError("segment_id requires a lowercase SHA-256 hex digest")
    return _SEGMENT_PREFIX + uncompressed_sha256


def fingerprint_key_id(key_bytes: bytes) -> str:
    """``fpk_`` plus ``first_16_bytes_hex(SHA-256(key))`` (OBS-D-028)."""
    if len(key_bytes) != 32:
        raise ValueError("fingerprint keys are exactly 32 bytes")
    return _KEY_PREFIX + sha256_hex(key_bytes)[:32]


def binding_ref(trace_id: str, unit_ref: str) -> str:
    """Stable opaque binding reference for one work unit inside one trace."""
    if not isinstance(trace_id, str) or _TRACE_RE.fullmatch(trace_id) is None:
        raise ValueError("binding trace_id must use the typed trace grammar")
    if not is_opaque_ref(unit_ref):
        raise ValueError("binding unit_ref must be an opaque reference")
    digest = canonical_digest({"trace": trace_id, "unit": unit_ref})
    return "bnd_" + digest[:40]


def attribution_id(kind: str, *parts: Any) -> str:
    """Deterministic attribution identity: ``bnk_`` for bottlenecks, ``dfc_`` for defects."""
    prefix = {"bottleneck": "bnk_", "defect": "dfc_"}[kind]
    if native_identity(**{f"part_{index}": part for index, part in enumerate(parts)}) is None:
        raise ValueError("attribution identity parts must be typed opaque metadata")
    return prefix + canonical_digest({"kind": kind, "parts": list(parts)})[:40]


def correlation_token(trace_ref: str, unit_ref: str) -> str:
    """Build the opaque in-call token attached to the existing ``kanban_create``.

    It carries no title, body, workspace, or arbitrary idempotency value; only the
    validated prefix and the two opaque references ever reach the journal.
    """
    if (
        not isinstance(trace_ref, str)
        or _TRACE_RE.fullmatch(trace_ref) is None
        or not is_opaque_ref(unit_ref)
    ):
        raise ValueError("correlation token references must be bounded opaque strings")
    return f"{CORRELATION_TOKEN_PREFIX}{trace_ref}:{unit_ref}"


def parse_correlation_token(value: Any) -> tuple[str, str] | None:
    """Parse a strict Aether correlation token.

    An ordinary arbitrary idempotency key returns ``None`` and is discarded rather
    than journaled (OBS-FR-050).
    """
    if not isinstance(value, str):
        return None
    match = _TOKEN_RE.fullmatch(value.strip())
    if match is None:
        return None
    return match.group("trace"), match.group("unit")


@dataclass(slots=True)
class ProducerSequence:
    """Strictly increasing sequence inside one producer epoch.

    Sequences never cross epochs: a restarted process allocates a new epoch and starts
    again at zero, so ordering stays authoritative per process without a global clock.
    """

    epoch: str
    _next: int = 0
    _lock: threading.Lock | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.epoch, str) or _PRODUCER_RE.fullmatch(self.epoch) is None:
            raise ValueError("producer epoch must use the prd_<128-bit-hex> grammar")
        if isinstance(self._next, bool) or not isinstance(self._next, int) or self._next < 0:
            raise ValueError("producer sequence must be a non-negative integer")
        if self._lock is None:
            self._lock = threading.Lock()

    def allocate(self) -> int:
        assert self._lock is not None
        with self._lock:
            value = self._next
            self._next += 1
            return value

    def resume_after(self, last_seq: int) -> None:
        """Continue an epoch recovered from disk, never reissuing a used sequence."""
        if isinstance(last_seq, bool) or not isinstance(last_seq, int) or last_seq < 0:
            raise ValueError("last producer sequence must be a non-negative integer")
        assert self._lock is not None
        with self._lock:
            self._next = max(self._next, last_seq + 1)

    @property
    def next_seq(self) -> int:
        return self._next
