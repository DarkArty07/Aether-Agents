"""Independent review state machine and authenticated typed waivers."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum
from threading import Lock
from typing import Iterable

from .effects import _canon, _hash, _id, _int, _key, _s, _utc
from .protocol import ValidationError

MAX_REVIEW_ATTEMPTS = 3
_GATE_EVALUATION_KEY = secrets.token_bytes(32)


class FindingKind(StrEnum):
    BLOCKING = "blocking"
    NON_BLOCKING = "non_blocking"
    ADVISORY = "advisory"
    OPERATIONAL = "operational"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class GateResult(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    WAIVED = "waived"


@dataclass(frozen=True, slots=True)
class GateEvaluation:
    gate_id: str
    project_id: str
    contract_id: str
    task_id: str
    generation: int
    artifact_hash: str
    attempt: int
    reviewer_principal: str
    reviewer_runtime: str
    reviewer_credential: str
    reviewer_role: str
    result: GateResult
    evidence_ids: tuple[str, ...]
    evidence_hashes: tuple[str, ...]
    finding_ids: tuple[str, ...]
    finding_hashes: tuple[str, ...]
    waiver_hash: str | None
    signature: str

    def __post_init__(self) -> None:
        for attribute, name in (
            ("gate_id", "gate evaluation id"),
            ("project_id", "gate project"),
            ("contract_id", "gate contract"),
            ("task_id", "gate task"),
            ("reviewer_principal", "gate reviewer"),
            ("reviewer_runtime", "gate runtime"),
            ("reviewer_credential", "gate credential"),
            ("reviewer_role", "gate role"),
        ):
            object.__setattr__(self, attribute, _id(getattr(self, attribute), name))
        object.__setattr__(self, "generation", _int(self.generation, "gate generation"))
        object.__setattr__(self, "attempt", _int(self.attempt, "gate attempt"))
        object.__setattr__(self, "artifact_hash", _hash(self.artifact_hash, "gate artifact"))
        object.__setattr__(self, "signature", _hash(self.signature, "gate signature"))
        if not isinstance(self.result, GateResult):
            raise ValidationError("invalid gate result")
        for attribute in ("evidence_ids", "finding_ids"):
            values = getattr(self, attribute)
            if not isinstance(values, tuple) or len(set(values)) != len(values):
                raise ValidationError("invalid gate evaluation collection")
            object.__setattr__(self, attribute, tuple(_id(item, attribute) for item in values))
        for attribute in ("evidence_hashes", "finding_hashes"):
            values = getattr(self, attribute)
            if not isinstance(values, tuple):
                raise ValidationError("invalid gate evaluation hash collection")
            object.__setattr__(self, attribute, tuple(_hash(item, attribute) for item in values))
        if len(self.evidence_ids) != len(self.evidence_hashes) or len(self.finding_ids) != len(self.finding_hashes):
            raise ValidationError("gate evaluation collection mismatch")
        if self.waiver_hash is not None:
            object.__setattr__(self, "waiver_hash", _hash(self.waiver_hash, "gate waiver hash"))

    def payload(self) -> list[object]:
        return [
            self.gate_id,
            self.project_id,
            self.contract_id,
            self.task_id,
            self.generation,
            self.artifact_hash,
            self.attempt,
            self.reviewer_principal,
            self.reviewer_runtime,
            self.reviewer_credential,
            self.reviewer_role,
            self.result.value,
            list(zip(self.evidence_ids, self.evidence_hashes, strict=True)),
            list(zip(self.finding_ids, self.finding_hashes, strict=True)),
            self.waiver_hash,
        ]


@dataclass(frozen=True, slots=True)
class ReviewerIdentity:
    principal_id: str
    runtime_instance: str
    workload_credential: str
    role: str

    def __post_init__(self) -> None:
        for attribute, name in (
            ("principal_id", "review principal"),
            ("runtime_instance", "review runtime"),
            ("workload_credential", "review workload credential"),
            ("role", "review role"),
        ):
            object.__setattr__(self, attribute, _id(getattr(self, attribute), name))


@dataclass(frozen=True, slots=True)
class ReviewGate:
    gate_id: str
    project_id: str
    contract_id: str
    task_id: str
    generation: int
    artifact_hash: str
    required_role: str
    attempts: int = 0

    def __post_init__(self) -> None:
        for attribute, name in (
            ("gate_id", "gate id"),
            ("project_id", "project id"),
            ("contract_id", "contract id"),
            ("task_id", "task id"),
            ("required_role", "required review role"),
        ):
            object.__setattr__(self, attribute, _id(getattr(self, attribute), name))
        object.__setattr__(self, "generation", _int(self.generation, "review generation"))
        object.__setattr__(self, "artifact_hash", _hash(self.artifact_hash, "review artifact hash"))
        attempts = _int(self.attempts, "review attempts")
        if attempts > MAX_REVIEW_ATTEMPTS:
            raise ValidationError("invalid review attempts")
        object.__setattr__(self, "attempts", attempts)


@dataclass(frozen=True, slots=True)
class ReviewEvidence:
    evidence_id: str
    gate_id: str
    generation: int
    artifact_hash: str
    reference: str
    evidence_hash: str

    def __post_init__(self) -> None:
        for attribute, name in (
            ("evidence_id", "evidence id"),
            ("gate_id", "gate id"),
            ("reference", "evidence reference"),
        ):
            object.__setattr__(self, attribute, _id(getattr(self, attribute), name))
        object.__setattr__(self, "generation", _int(self.generation, "evidence generation"))
        object.__setattr__(self, "artifact_hash", _hash(self.artifact_hash, "evidence artifact hash"))
        object.__setattr__(self, "evidence_hash", _hash(self.evidence_hash, "evidence hash"))


@dataclass(frozen=True, slots=True)
class ReviewFinding:
    finding_id: str
    gate_id: str
    criterion: str
    kind: FindingKind
    claim: str
    evidence_refs: tuple[str, ...]
    impact: str
    confidence: str
    attempt: int

    def __post_init__(self) -> None:
        for attribute, name in (
            ("finding_id", "finding id"),
            ("gate_id", "gate id"),
            ("criterion", "review criterion"),
            ("confidence", "finding confidence"),
        ):
            object.__setattr__(self, attribute, _id(getattr(self, attribute), name))
        if not isinstance(self.kind, FindingKind):
            raise ValidationError("invalid finding kind")
        object.__setattr__(self, "claim", _s(self.claim, "finding claim"))
        object.__setattr__(self, "impact", _s(self.impact, "finding impact"))
        if not isinstance(self.evidence_refs, tuple) or not self.evidence_refs:
            raise ValidationError("finding evidence required")
        references = tuple(_id(item, "finding evidence reference") for item in self.evidence_refs)
        if len(set(references)) != len(references):
            raise ValidationError("duplicate finding evidence")
        object.__setattr__(self, "evidence_refs", references)
        attempt = _int(self.attempt, "finding attempt")
        if not 1 <= attempt <= MAX_REVIEW_ATTEMPTS:
            raise ValidationError("invalid finding attempt")
        object.__setattr__(self, "attempt", attempt)

    @property
    def canonical_hash(self) -> str:
        return hashlib.sha256(
            _canon(
                [
                    self.finding_id,
                    self.gate_id,
                    self.criterion,
                    self.kind.value,
                    self.claim,
                    list(self.evidence_refs),
                    self.impact,
                    self.confidence,
                    self.attempt,
                ]
            )
        ).hexdigest()


@dataclass(frozen=True, slots=True)
class ReviewWaiver:
    finding_id: str
    gate_id: str
    contract_id: str
    artifact: str
    artifact_hash: str
    generation: int
    risk: str
    rationale: str
    accepting_authority: str
    nonce: str
    issued_at: datetime
    expires_at: datetime

    def __post_init__(self) -> None:
        for attribute, name in (
            ("finding_id", "finding id"),
            ("gate_id", "gate id"),
            ("contract_id", "contract id"),
            ("artifact", "artifact"),
            ("accepting_authority", "accepting authority"),
            ("nonce", "waiver nonce"),
        ):
            object.__setattr__(self, attribute, _id(getattr(self, attribute), name))
        object.__setattr__(self, "artifact_hash", _hash(self.artifact_hash, "waiver artifact hash"))
        object.__setattr__(self, "generation", _int(self.generation, "waiver generation"))
        object.__setattr__(self, "risk", _s(self.risk, "waiver risk"))
        object.__setattr__(self, "rationale", _s(self.rationale, "waiver rationale"))
        object.__setattr__(self, "issued_at", _utc(self.issued_at, "waiver issued at"))
        object.__setattr__(self, "expires_at", _utc(self.expires_at, "waiver expires at"))
        if self.expires_at <= self.issued_at:
            raise ValidationError("waiver expiry")

    def to_dict(self) -> dict[str, object]:
        return {
            "finding_id": self.finding_id,
            "gate_id": self.gate_id,
            "contract_id": self.contract_id,
            "artifact": self.artifact,
            "artifact_hash": self.artifact_hash,
            "generation": self.generation,
            "risk": self.risk,
            "rationale": self.rationale,
            "accepting_authority": self.accepting_authority,
            "nonce": self.nonce,
            "issued_at": self.issued_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
        }

    @property
    def canonical_hash(self) -> str:
        return hashlib.sha256(_canon(self.to_dict())).hexdigest()


@dataclass(frozen=True, slots=True)
class SignedWaiver:
    waiver: ReviewWaiver
    signature: str

    def __post_init__(self) -> None:
        if not isinstance(self.waiver, ReviewWaiver):
            raise ValidationError("invalid signed waiver")
        object.__setattr__(self, "signature", _hash(self.signature, "waiver signature"))


class WaiverReplayCache:
    """Atomic process-local waiver replay protection for default-off R6."""

    def __init__(self) -> None:
        self._used: set[tuple[str, str, str]] = set()
        self._lock = Lock()

    def consume(self, waiver: ReviewWaiver) -> None:
        if not isinstance(waiver, ReviewWaiver):
            raise ValidationError("invalid waiver replay input")
        key = (waiver.accepting_authority, waiver.gate_id, waiver.nonce)
        with self._lock:
            if key in self._used:
                raise ValidationError("waiver replay")
            self._used.add(key)


def sign_waiver(waiver: ReviewWaiver, key: bytes) -> SignedWaiver:
    if not isinstance(waiver, ReviewWaiver):
        raise ValidationError("invalid waiver")
    signature = hmac.new(_key(key), _canon(waiver.to_dict()), hashlib.sha256).hexdigest()
    return SignedWaiver(waiver, signature)


def validate_reviewer(
    owner: ReviewerIdentity,
    reviewer: ReviewerIdentity,
    *,
    authorized_roles: Iterable[str],
    authorized: bool = True,
    self_review: bool = False,
) -> bool:
    if (
        not isinstance(owner, ReviewerIdentity)
        or not isinstance(reviewer, ReviewerIdentity)
        or not isinstance(authorized, bool)
        or not isinstance(self_review, bool)
    ):
        raise ValidationError("invalid reviewer validation")
    roles = frozenset(_id(item, "authorized review role") for item in authorized_roles)
    if not authorized or self_review:
        raise ValidationError("reviewer unauthorized")
    if (
        owner.principal_id == reviewer.principal_id
        or owner.runtime_instance == reviewer.runtime_instance
        or owner.workload_credential == reviewer.workload_credential
    ):
        raise ValidationError("reviewer is not independent")
    if reviewer.role not in roles:
        raise ValidationError("reviewer role unauthorized")
    return True


def advance_attempt(gate: ReviewGate) -> ReviewGate:
    if not isinstance(gate, ReviewGate):
        raise ValidationError("invalid review gate")
    if gate.attempts >= MAX_REVIEW_ATTEMPTS:
        raise ValidationError("review attempts exhausted")
    return replace(gate, attempts=gate.attempts + 1)


def _issue_gate_evaluation(
    gate: ReviewGate,
    reviewer: ReviewerIdentity,
    result: GateResult,
    evidence: tuple[ReviewEvidence, ...],
    findings: tuple[ReviewFinding, ...],
    waiver_hash: str | None = None,
) -> GateEvaluation:
    unsigned = GateEvaluation(
        gate.gate_id,
        gate.project_id,
        gate.contract_id,
        gate.task_id,
        gate.generation,
        gate.artifact_hash,
        gate.attempts,
        reviewer.principal_id,
        reviewer.runtime_instance,
        reviewer.workload_credential,
        reviewer.role,
        result,
        tuple(item.evidence_id for item in evidence),
        tuple(item.evidence_hash for item in evidence),
        tuple(item.finding_id for item in findings),
        tuple(item.canonical_hash for item in findings),
        waiver_hash,
        "0" * 64,
    )
    signature = hmac.new(_GATE_EVALUATION_KEY, _canon(unsigned.payload()), hashlib.sha256).hexdigest()
    return replace(unsigned, signature=signature)


def _verify_gate_evaluation(value: GateEvaluation) -> None:
    if not isinstance(value, GateEvaluation):
        raise ValidationError("authenticated gate evaluation required")
    expected = hmac.new(_GATE_EVALUATION_KEY, _canon(value.payload()), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, value.signature):
        raise ValidationError("invalid gate evaluation signature")


def _verify_waiver(
    signed: SignedWaiver,
    gate: ReviewGate,
    finding_ids: set[str],
    *,
    key: bytes,
    now: datetime,
    replay_cache: WaiverReplayCache,
    authorities: Iterable[str],
) -> None:
    if not isinstance(signed, SignedWaiver):
        raise ValidationError("typed signed waiver required")
    waiver = signed.waiver
    expected = hmac.new(_key(key), _canon(waiver.to_dict()), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signed.signature):
        raise ValidationError("invalid waiver signature")
    now = _utc(now, "waiver verification time")
    if not waiver.issued_at <= now < waiver.expires_at:
        raise ValidationError("expired waiver")
    allowed = frozenset(_id(item, "waiver authority") for item in authorities)
    if waiver.accepting_authority not in allowed:
        raise ValidationError("unauthorized waiver authority")
    if (
        waiver.finding_id not in finding_ids
        or waiver.gate_id != gate.gate_id
        or waiver.contract_id != gate.contract_id
        or waiver.artifact_hash != gate.artifact_hash
        or waiver.generation != gate.generation
    ):
        raise ValidationError("waiver binding mismatch")
    if not isinstance(replay_cache, WaiverReplayCache):
        raise ValidationError("invalid waiver replay cache")
    replay_cache.consume(waiver)


def evaluate_gate(
    gate: ReviewGate,
    owner: ReviewerIdentity,
    reviewer: ReviewerIdentity,
    findings: tuple[ReviewFinding, ...],
    evidence: tuple[ReviewEvidence, ...],
    *,
    current_generation: int,
    current_artifact_hash: str,
    authorized_roles: Iterable[str],
    signed_waiver: SignedWaiver | None = None,
    waiver_key: bytes | None = None,
    waiver_now: datetime | None = None,
    waiver_replay_cache: WaiverReplayCache | None = None,
    waiver_authorities: Iterable[str] = (),
) -> GateEvaluation:
    if not isinstance(gate, ReviewGate) or gate.attempts < 1:
        raise ValidationError("review attempt not started")
    validate_reviewer(owner, reviewer, authorized_roles=authorized_roles)
    if gate.required_role != reviewer.role:
        raise ValidationError("reviewer role does not satisfy gate")
    if _int(current_generation, "current generation") != gate.generation:
        raise ValidationError("stale review generation")
    if _hash(current_artifact_hash, "current artifact hash") != gate.artifact_hash:
        raise ValidationError("stale review artifact")
    if not isinstance(evidence, tuple) or not evidence:
        raise ValidationError("review evidence required")
    if any(not isinstance(item, ReviewEvidence) for item in evidence):
        raise ValidationError("invalid review evidence")
    evidence_ids = [item.evidence_id for item in evidence]
    if len(set(evidence_ids)) != len(evidence_ids):
        raise ValidationError("duplicate review evidence")
    if any(
        item.gate_id != gate.gate_id or item.generation != gate.generation or item.artifact_hash != gate.artifact_hash
        for item in evidence
    ):
        raise ValidationError("review evidence binding mismatch")
    if not isinstance(findings, tuple) or any(not isinstance(item, ReviewFinding) for item in findings):
        raise ValidationError("invalid review findings")
    finding_ids = [item.finding_id for item in findings]
    if len(set(finding_ids)) != len(finding_ids):
        raise ValidationError("duplicate review finding")
    known_evidence = set(evidence_ids)
    if any(
        item.gate_id != gate.gate_id
        or item.attempt != gate.attempts
        or not set(item.evidence_refs).issubset(known_evidence)
        for item in findings
    ):
        raise ValidationError("review finding binding mismatch")

    blocking = {
        item.finding_id for item in findings if item.kind in (FindingKind.BLOCKING, FindingKind.INSUFFICIENT_EVIDENCE)
    }
    if signed_waiver is not None:
        if not blocking:
            raise ValidationError("waiver without blocking finding")
        if waiver_key is None or waiver_now is None or waiver_replay_cache is None:
            raise ValidationError("incomplete waiver verification")
        _verify_waiver(
            signed_waiver,
            gate,
            blocking,
            key=waiver_key,
            now=waiver_now,
            replay_cache=waiver_replay_cache,
            authorities=waiver_authorities,
        )
        return _issue_gate_evaluation(
            gate, reviewer, GateResult.WAIVED, evidence, findings, signed_waiver.waiver.canonical_hash
        )
    if blocking:
        return _issue_gate_evaluation(gate, reviewer, GateResult.FAILED, evidence, findings)
    return _issue_gate_evaluation(gate, reviewer, GateResult.PASSED, evidence, findings)


__all__ = [
    "FindingKind",
    "GateEvaluation",
    "GateResult",
    "MAX_REVIEW_ATTEMPTS",
    "ReviewEvidence",
    "ReviewFinding",
    "ReviewGate",
    "ReviewerIdentity",
    "ReviewWaiver",
    "SignedWaiver",
    "WaiverReplayCache",
    "advance_attempt",
    "evaluate_gate",
    "sign_waiver",
    "validate_reviewer",
]
