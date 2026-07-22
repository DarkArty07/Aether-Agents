"""Read-only, default-off comparison of Harmonia predictions with Olympus evidence."""

from __future__ import annotations

import hashlib
import hmac
import json
import math
import secrets
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from threading import Lock
from typing import Any, Mapping

from .harmonia import HarmoniaPlan
from .olympus_adapter import OlympusRuntimeAdapter, RuntimeObservation
from .protocol import Principal, ValidationError

MAX_SHADOW_ASSIGNMENTS = 128
MAX_SHADOW_MISMATCHES = 256
MAX_SHADOW_REASON_BYTES = 256
_EVIDENCE_KEY = secrets.token_bytes(32)
_REPORT_KEY = secrets.token_bytes(32)


class ShadowCondition(StrEnum):
    """Observed non-happy-path facts; shadow mode never causes them."""

    DUPLICATE_DELIVERY = "duplicate_delivery"
    RUNTIME_UNAVAILABLE = "runtime_unavailable"
    REVIEWER_VIOLATION = "reviewer_violation"
    BUDGET_EXHAUSTED = "budget_exhausted"
    STALE_LEASE = "stale_lease"
    REVOCATION_RACE = "revocation_race"
    LEDGER_TAMPERED = "ledger_tampered"
    PROJECTION_REBUILT = "projection_rebuilt"
    UNKNOWN_EFFECT = "unknown_effect"
    PARTIAL_EVIDENCE = "partial_evidence"


def _bounded_text(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or len(value.encode()) > MAX_SHADOW_REASON_BYTES
    ):
        raise ValidationError(f"invalid {label}")
    return value


def _canonical_root(value: str) -> str:
    if not isinstance(value, str) or not value.startswith("/"):
        raise ValidationError("invalid shadow project root")
    return str(Path(value).resolve())


def _signature(key: bytes, payload: tuple[object, ...]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()
    return hmac.new(key, encoded, hashlib.sha256).hexdigest()


@dataclass(frozen=True, slots=True)
class ShadowConfig:
    enabled: bool = False
    max_assignments: int = MAX_SHADOW_ASSIGNMENTS
    max_mismatches: int = MAX_SHADOW_MISMATCHES

    def __post_init__(self) -> None:
        if not isinstance(self.enabled, bool):
            raise ValidationError("invalid shadow enabled flag")
        if (
            isinstance(self.max_assignments, bool)
            or not isinstance(self.max_assignments, int)
            or not 1 <= self.max_assignments <= MAX_SHADOW_ASSIGNMENTS
        ):
            raise ValidationError("invalid shadow assignment bound")
        if (
            isinstance(self.max_mismatches, bool)
            or not isinstance(self.max_mismatches, int)
            or not 1 <= self.max_mismatches <= MAX_SHADOW_MISMATCHES
        ):
            raise ValidationError("invalid shadow mismatch bound")


@dataclass(frozen=True, slots=True)
class ShadowObservation:
    """Untrusted compatibility input; enabled comparisons require verified evidence."""

    task_id: str
    participant: Principal
    session_id: str
    technical_status: str
    project_id: str | None = None
    contract_id: str | None = None
    generation: int | None = None
    latency_ms: float | None = None
    conditions: tuple[ShadowCondition, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.participant, Principal):
            raise ValidationError("invalid shadow observation")
        for value, label in (
            (self.task_id, "task"),
            (self.session_id, "session"),
            (self.technical_status, "technical status"),
        ):
            _bounded_text(value, label)
        for value, label in ((self.project_id, "project"), (self.contract_id, "contract")):
            if value is not None:
                _bounded_text(value, label)
        if self.generation is not None and (
            isinstance(self.generation, bool) or not isinstance(self.generation, int) or self.generation < 0
        ):
            raise ValidationError("invalid shadow generation")
        if self.latency_ms is not None and (
            isinstance(self.latency_ms, bool)
            or not isinstance(self.latency_ms, (int, float))
            or not math.isfinite(self.latency_ms)
            or self.latency_ms < 0
        ):
            raise ValidationError("invalid shadow latency")
        if (
            not isinstance(self.conditions, tuple)
            or len(self.conditions) > 16
            or len(set(self.conditions)) != len(self.conditions)
            or any(not isinstance(item, ShadowCondition) for item in self.conditions)
        ):
            raise ValidationError("invalid shadow conditions")


@dataclass(frozen=True, slots=True)
class VerifiedShadowEvidence:
    """Process-authenticated facts read from Olympus' public persistence API."""

    task_id: str
    participant: Principal
    actual_session_id: str
    project_root: str
    project_id: str
    contract_id: str
    generation: int
    technical_status: str
    response_hash: str
    signature: str
    latency_ms: float | None = None
    conditions: tuple[ShadowCondition, ...] = ()

    def payload(self) -> tuple[object, ...]:
        return (
            self.task_id,
            self.participant.project_id,
            self.participant.owner_id,
            self.participant.actor_id,
            self.actual_session_id,
            self.project_root,
            self.project_id,
            self.contract_id,
            self.generation,
            self.technical_status,
            self.response_hash,
            self.latency_ms,
            tuple(item.value for item in self.conditions),
        )


async def observe_olympus_session(
    db: Any,
    *,
    session_id: str,
    task_id: str,
    participant: Principal,
    project_root: str,
    project_id: str,
    contract_id: str,
    generation: int,
    latency_ms: float | None = None,
    conditions: tuple[ShadowCondition, ...] = (),
) -> VerifiedShadowEvidence:
    """Read and authenticate one actual Olympus session without changing it."""
    if not callable(getattr(db, "get_session", None)) or not callable(getattr(db, "get_latest_turn", None)):
        raise ValidationError("invalid Olympus evidence source")
    observation = ShadowObservation(
        task_id,
        participant,
        session_id,
        "pending",
        project_id,
        contract_id,
        generation,
        latency_ms,
        conditions,
    )
    canonical_root = _canonical_root(project_root)
    row = await db.get_session(session_id)
    turn = await db.get_latest_turn(session_id)
    if not isinstance(row, Mapping) or not isinstance(turn, Mapping):
        raise ValidationError("missing Olympus session evidence")
    try:
        metadata = json.loads(row.get("metadata") or "{}")
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValidationError("invalid Olympus session metadata") from exc
    status = row.get("status")
    response = turn.get("content")
    expected_response = (
        f"AETHER_SHADOW_V1 task_id={task_id} participant={participant.actor_id} technical_status={status}"
    )
    if (
        row.get("session_id") != session_id
        or row.get("agent") != participant.actor_id
        or metadata.get("profile") != participant.actor_id
        or _canonical_root(metadata.get("project_root")) != canonical_root
        or not isinstance(status, str)
        or not isinstance(response, str)
        or response != expected_response
    ):
        raise ValidationError("unbound Olympus session evidence")
    response_hash = hashlib.sha256(response.encode()).hexdigest()
    unsigned = VerifiedShadowEvidence(
        observation.task_id,
        observation.participant,
        observation.session_id,
        canonical_root,
        project_id,
        contract_id,
        generation,
        status,
        response_hash,
        "",
        latency_ms,
        conditions,
    )
    return VerifiedShadowEvidence(
        task_id,
        participant,
        session_id,
        canonical_root,
        project_id,
        contract_id,
        generation,
        status,
        response_hash,
        _signature(_EVIDENCE_KEY, unsigned.payload()),
        latency_ms,
        conditions,
    )


def _verify_evidence(evidence: VerifiedShadowEvidence) -> bool:
    return isinstance(evidence, VerifiedShadowEvidence) and hmac.compare_digest(
        evidence.signature, _signature(_EVIDENCE_KEY, evidence.payload())
    )


@dataclass(frozen=True, slots=True)
class ShadowSessionCorrelation:
    task_id: str
    participant: Principal
    project_root: str
    predicted_session_id: str
    actual_session_id: str
    evidence_signature: str

    @classmethod
    def from_evidence(cls, plan: HarmoniaPlan, evidence: VerifiedShadowEvidence) -> ShadowSessionCorrelation:
        if not _verify_evidence(evidence):
            raise ValidationError("unverified shadow evidence")
        matches = [item for item in plan.assignments if item.task_id == evidence.task_id]
        if len(matches) != 1 or matches[0].participant != evidence.participant:
            raise ValidationError("unbound shadow correlation source")
        predicted = OlympusRuntimeAdapter._session_id(evidence.task_id, evidence.participant, evidence.project_root)
        return cls(
            evidence.task_id,
            evidence.participant,
            evidence.project_root,
            predicted,
            evidence.actual_session_id,
            evidence.signature,
        )


class ShadowCorrelationRegistry:
    """Bounded process-local detector; same-binding repeats are idempotent."""

    def __init__(self, *, max_entries: int = MAX_SHADOW_ASSIGNMENTS) -> None:
        if (
            isinstance(max_entries, bool)
            or not isinstance(max_entries, int)
            or not 1 <= max_entries <= MAX_SHADOW_ASSIGNMENTS
        ):
            raise ValidationError("invalid shadow registry bound")
        self._lock = Lock()
        self._max_entries = max_entries
        self._actual: dict[str, tuple[str, Principal]] = {}

    def consume(self, correlation: ShadowSessionCorrelation) -> bool:
        binding = (correlation.task_id, correlation.participant)
        with self._lock:
            previous = self._actual.get(correlation.actual_session_id)
            if previous is not None:
                return previous == binding
            if len(self._actual) >= self._max_entries:
                return False
            self._actual[correlation.actual_session_id] = binding
            return True


@dataclass(frozen=True, slots=True)
class ShadowReport:
    enabled: bool
    assignment_agreement: bool
    participant_agreement: bool
    session_agreement: bool
    status_agreement: bool
    mismatches: tuple[str, ...]
    correlation: ShadowSessionCorrelation | None
    latency_ms: float | None
    signature: str
    semantic_complete: bool = field(default=False, init=False)

    def payload(self) -> tuple[object, ...]:
        correlation = None
        if self.correlation is not None:
            correlation = (
                self.correlation.task_id,
                self.correlation.participant.project_id,
                self.correlation.participant.owner_id,
                self.correlation.participant.actor_id,
                self.correlation.project_root,
                self.correlation.predicted_session_id,
                self.correlation.actual_session_id,
                self.correlation.evidence_signature,
            )
        return (
            self.enabled,
            self.assignment_agreement,
            self.participant_agreement,
            self.session_agreement,
            self.status_agreement,
            self.mismatches,
            correlation,
            self.latency_ms,
            self.semantic_complete,
        )


def verify_shadow_report(report: ShadowReport) -> bool:
    return isinstance(report, ShadowReport) and hmac.compare_digest(
        report.signature, _signature(_REPORT_KEY, report.payload())
    )


def _report(
    enabled: bool,
    assignment: bool,
    participant: bool,
    session: bool,
    status: bool,
    mismatches: tuple[str, ...],
    correlation: ShadowSessionCorrelation | None,
    latency_ms: float | None,
) -> ShadowReport:
    unsigned = ShadowReport(
        enabled,
        assignment,
        participant,
        session,
        status,
        mismatches,
        correlation,
        latency_ms,
        "",
    )
    return ShadowReport(
        enabled,
        assignment,
        participant,
        session,
        status,
        mismatches,
        correlation,
        latency_ms,
        _signature(_REPORT_KEY, unsigned.payload()),
    )


def compare_shadow(
    plan: HarmoniaPlan,
    evidence: VerifiedShadowEvidence | RuntimeObservation | ShadowObservation,
    *,
    project_root: str,
    config: ShadowConfig | None = None,
    project_id: str | None = None,
    contract_id: str | None = None,
    generation: int | None = None,
    expected_status: str | None = None,
    correlation: ShadowSessionCorrelation | None = None,
    registry: ShadowCorrelationRegistry | None = None,
) -> ShadowReport:
    """Compare verified Olympus facts to a plan without runtime side effects."""
    config = ShadowConfig() if config is None else config
    if not isinstance(config, ShadowConfig) or not isinstance(plan, HarmoniaPlan):
        raise ValidationError("invalid shadow comparison")
    if not config.enabled:
        return _report(False, False, False, False, False, ("feature_disabled",), None, None)
    if not isinstance(evidence, VerifiedShadowEvidence) or not _verify_evidence(evidence):
        return _report(True, False, False, False, False, ("unverified_evidence",), None, None)
    canonical_root = _canonical_root(project_root)
    for value, label in (
        (project_id, "project"),
        (contract_id, "contract"),
        (expected_status, "expected status"),
    ):
        _bounded_text(value, label)
    if isinstance(generation, bool) or not isinstance(generation, int) or generation < 0:
        raise ValidationError("invalid generation")
    if not isinstance(correlation, ShadowSessionCorrelation) or not isinstance(registry, ShadowCorrelationRegistry):
        return _report(True, False, False, False, False, ("unverified_correlation",), None, evidence.latency_ms)
    assignments = plan.assignments
    if len(assignments) > config.max_assignments or len({item.task_id for item in assignments}) != len(assignments):
        raise ValidationError("shadow assignment bound or replay violation")
    matches = [item for item in assignments if item.task_id == evidence.task_id]
    assignment_ok = len(matches) == 1
    participant_ok = assignment_ok and matches[0].participant == evidence.participant
    expected_prediction = OlympusRuntimeAdapter._session_id(evidence.task_id, evidence.participant, canonical_root)
    context_ok = (
        evidence.project_root == canonical_root
        and evidence.project_id == project_id
        and evidence.contract_id == contract_id
        and evidence.generation == generation
    )
    correlation_ok = (
        correlation.task_id == evidence.task_id
        and correlation.participant == evidence.participant
        and correlation.project_root == canonical_root
        and correlation.predicted_session_id == expected_prediction
        and correlation.actual_session_id == evidence.actual_session_id
        and correlation.evidence_signature == evidence.signature
        and registry.consume(correlation)
    )
    status_ok = evidence.technical_status == expected_status and not evidence.conditions
    mismatches: list[str] = []
    if not assignment_ok:
        mismatches.append("task_mismatch")
    if not participant_ok:
        mismatches.append("participant_mismatch")
    if not context_ok:
        mismatches.append("context_mismatch")
    if not correlation_ok:
        mismatches.append("correlation_mismatch")
    if not status_ok:
        mismatches.append("status_mismatch")
    mismatches.extend(item.value for item in evidence.conditions)
    return _report(
        True,
        assignment_ok,
        participant_ok,
        assignment_ok and participant_ok and context_ok and correlation_ok,
        status_ok,
        tuple(mismatches[: config.max_mismatches]),
        correlation if correlation_ok else None,
        evidence.latency_ms,
    )


__all__ = [
    "MAX_SHADOW_ASSIGNMENTS",
    "MAX_SHADOW_MISMATCHES",
    "ShadowCondition",
    "ShadowConfig",
    "ShadowCorrelationRegistry",
    "ShadowObservation",
    "ShadowReport",
    "ShadowSessionCorrelation",
    "VerifiedShadowEvidence",
    "compare_shadow",
    "observe_olympus_session",
    "verify_shadow_report",
]
