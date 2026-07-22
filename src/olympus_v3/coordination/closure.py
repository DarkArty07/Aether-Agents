"""Two-stage semantic closure over authenticated review and effect artifacts."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import StrEnum
from typing import Iterable

from .effects import (
    MAX_COLLECTION,
    EffectClass,
    EffectLifecycle,
    EffectReceipt,
    _canon,
    _hash,
    _id,
    _int,
    _s,
    _verify_receipt,
)
from .protocol import ValidationError
from .review import GateEvaluation, GateResult, _verify_gate_evaluation


class CompletionAuthority(StrEnum):
    AUTOMATIC = "automatic"
    HERMES = "hermes"
    USER = "user"


class CompletionState(StrEnum):
    COMPLETED = "completed"
    PARTIALLY_COMPLETED = "partially_completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CleanupStep(StrEnum):
    STOP_ADMISSION = "stop admission"
    REVOKE_CAPABILITIES = "revoke capabilities"
    RECONCILE_EFFECTS_SESSIONS = "reconcile effects/sessions"
    RELEASE_LEASE = "release lease"
    PUBLISH_CONTINUITY = "publish continuity"
    IDLE_SHUTDOWN = "idle shutdown"


@dataclass(frozen=True, slots=True)
class ClosureEvidence:
    evidence_id: str
    reference: str
    artifact_hash: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence_id", _id(self.evidence_id, "closure evidence id"))
        object.__setattr__(self, "reference", _id(self.reference, "closure evidence reference"))
        object.__setattr__(self, "artifact_hash", _hash(self.artifact_hash, "closure evidence artifact hash"))


@dataclass(frozen=True, slots=True)
class ClosureProposal:
    project_id: str
    contract_id: str
    task_id: str
    owner: str
    generation: int
    proposed_state: CompletionState
    evidence: tuple[ClosureEvidence, ...]
    authority: CompletionAuthority
    accepted_outcome: str = ""
    unmet_criteria: tuple[str, ...] = ()
    residual_risks: tuple[str, ...] = ()
    authority_decision: str = ""
    is_final: bool = False

    def __post_init__(self) -> None:
        for attribute, name in (
            ("project_id", "project id"),
            ("contract_id", "contract id"),
            ("task_id", "task id"),
            ("owner", "closure owner"),
        ):
            object.__setattr__(self, attribute, _id(getattr(self, attribute), name))
        object.__setattr__(self, "generation", _int(self.generation, "closure generation"))
        if (
            not isinstance(self.proposed_state, CompletionState)
            or not isinstance(self.authority, CompletionAuthority)
            or self.is_final is not False
        ):
            raise ValidationError("owner proposal cannot be final")
        if (
            not isinstance(self.evidence, tuple)
            or len(self.evidence) > MAX_COLLECTION
            or any(not isinstance(item, ClosureEvidence) for item in self.evidence)
        ):
            raise ValidationError("invalid closure evidence")
        for attribute, name in (("unmet_criteria", "unmet criterion"), ("residual_risks", "residual risk")):
            values = getattr(self, attribute)
            if not isinstance(values, tuple) or len(values) > MAX_COLLECTION:
                raise ValidationError(f"invalid {name} list")
            clean = tuple(_s(item, name) for item in values)
            if len(set(clean)) != len(clean):
                raise ValidationError(f"duplicate {name}")
            object.__setattr__(self, attribute, clean)
        if self.accepted_outcome:
            object.__setattr__(self, "accepted_outcome", _s(self.accepted_outcome, "accepted outcome"))
        if self.authority_decision:
            object.__setattr__(self, "authority_decision", _id(self.authority_decision, "authority decision"))
        if not self.authority_decision:
            raise ValidationError("authority decision required")
        if self.proposed_state is CompletionState.PARTIALLY_COMPLETED and (
            not self.accepted_outcome or not self.unmet_criteria or not self.residual_risks
        ):
            raise ValidationError("partial closure details required")
        if self.proposed_state is not CompletionState.PARTIALLY_COMPLETED and (
            self.unmet_criteria or self.residual_risks
        ):
            raise ValidationError("partial closure details on non-partial state")

    def to_dict(self) -> dict[str, object]:
        return {
            "project_id": self.project_id,
            "contract_id": self.contract_id,
            "task_id": self.task_id,
            "owner": self.owner,
            "generation": self.generation,
            "proposed_state": self.proposed_state.value,
            "evidence": [[item.evidence_id, item.reference, item.artifact_hash] for item in self.evidence],
            "authority": self.authority.value,
            "accepted_outcome": self.accepted_outcome,
            "unmet_criteria": list(self.unmet_criteria),
            "residual_risks": list(self.residual_risks),
            "authority_decision": self.authority_decision,
            "is_final": False,
        }


@dataclass(frozen=True, slots=True)
class ClosureDecision:
    state: CompletionState
    authorized_by: CompletionAuthority
    proposal_hash: str
    cleanup_steps: tuple[CleanupStep, ...]
    is_final: bool = True

    def __post_init__(self) -> None:
        if (
            not isinstance(self.state, CompletionState)
            or not isinstance(self.authorized_by, CompletionAuthority)
            or not isinstance(self.cleanup_steps, tuple)
            or self.cleanup_steps != cleanup_plan()
            or self.is_final is not True
        ):
            raise ValidationError("invalid closure decision")
        object.__setattr__(self, "proposal_hash", _hash(self.proposal_hash, "proposal hash"))


def cleanup_plan() -> tuple[CleanupStep, ...]:
    return (
        CleanupStep.STOP_ADMISSION,
        CleanupStep.REVOKE_CAPABILITIES,
        CleanupStep.RECONCILE_EFFECTS_SESSIONS,
        CleanupStep.RELEASE_LEASE,
        CleanupStep.PUBLISH_CONTINUITY,
        CleanupStep.IDLE_SHUTDOWN,
    )


def _ids(values: Iterable[str], name: str) -> frozenset[str]:
    if isinstance(values, (str, bytes)):
        raise ValidationError(f"invalid {name}")
    result = tuple(_id(item, name) for item in values)
    if len(result) > MAX_COLLECTION or len(set(result)) != len(result):
        raise ValidationError(f"duplicate or excessive {name}")
    return frozenset(result)


def _require_bool(value: object, name: str) -> bool:
    if not isinstance(value, bool):
        raise ValidationError(f"invalid {name}")
    return value


def _validate_gate_results(
    proposal: ClosureProposal,
    required: frozenset[str],
    results: tuple[GateEvaluation, ...],
) -> None:
    if not isinstance(results, tuple) or any(not isinstance(item, GateEvaluation) for item in results):
        raise ValidationError("authenticated gate evaluations required")
    ids = [item.gate_id for item in results]
    if len(set(ids)) != len(ids):
        raise ValidationError("duplicate gate result")
    by_id = {item.gate_id: item for item in results}
    if not required.issubset(by_id):
        raise ValidationError("required gate missing")
    evidence_hashes = {item.artifact_hash for item in proposal.evidence}
    for evaluation in results:
        _verify_gate_evaluation(evaluation)
        if (
            evaluation.project_id != proposal.project_id
            or evaluation.contract_id != proposal.contract_id
            or evaluation.task_id != proposal.task_id
            or evaluation.generation != proposal.generation
            or evaluation.artifact_hash not in evidence_hashes
        ):
            raise ValidationError("gate evaluation binding mismatch")
        if evaluation.result not in (GateResult.PASSED, GateResult.WAIVED):
            raise ValidationError("required gate did not pass")


def _validate_effect_results(
    proposal: ClosureProposal,
    results: tuple[EffectReceipt, ...],
) -> None:
    if not isinstance(results, tuple) or any(not isinstance(item, EffectReceipt) for item in results):
        raise ValidationError("authenticated effect receipts required")
    ids = [item.effect_id for item in results]
    if len(set(ids)) != len(ids):
        raise ValidationError("duplicate effect result")
    for receipt in results:
        _verify_receipt(receipt)
        if (
            receipt.project_id != proposal.project_id
            or receipt.contract_id != proposal.contract_id
            or receipt.task_id != proposal.task_id
            or receipt.generation != proposal.generation
        ):
            raise ValidationError("effect receipt binding mismatch")
        if receipt.effect_class is EffectClass.E4 and receipt.state is EffectLifecycle.UNKNOWN:
            raise ValidationError("unknown E4 effect blocks closure")
        if receipt.state in {
            EffectLifecycle.PLANNED,
            EffectLifecycle.AUTHORIZED,
            EffectLifecycle.EXECUTING,
            EffectLifecycle.UNKNOWN,
        }:
            raise ValidationError("effect reconciliation incomplete")
        if receipt.effect_class in (EffectClass.E2, EffectClass.E3) and receipt.state is EffectLifecycle.FAILED:
            raise ValidationError("effect reconciliation required")
        if proposal.proposed_state is CompletionState.COMPLETED and receipt.state in {
            EffectLifecycle.FAILED,
            EffectLifecycle.RECONCILED_FAILED,
        }:
            raise ValidationError("failed effect blocks completed state")


def validate_closure(
    proposal: ClosureProposal,
    *,
    current_owner: str,
    current_generation: int,
    required_gates: Iterable[str],
    gate_results: tuple[GateEvaluation, ...],
    required_evidence: Iterable[str],
    effect_results: tuple[EffectReceipt, ...],
    decision_authority: CompletionAuthority,
    automatic_allowed: bool,
    technical_status: str,
    critical_evidence: bool,
    integrity: bool,
    secret_violation: bool,
) -> ClosureDecision:
    if not isinstance(proposal, ClosureProposal):
        raise ValidationError("invalid closure proposal")
    if proposal.owner != _id(current_owner, "current owner"):
        raise ValidationError("closure owner mismatch")
    if proposal.generation != _int(current_generation, "current generation"):
        raise ValidationError("stale closure generation")
    if not isinstance(decision_authority, CompletionAuthority):
        raise ValidationError("invalid completion authority")
    if proposal.authority is not decision_authority:
        raise ValidationError("completion authority mismatch")
    automatic_allowed = _require_bool(automatic_allowed, "automatic completion flag")
    critical_evidence = _require_bool(critical_evidence, "critical evidence flag")
    integrity = _require_bool(integrity, "integrity flag")
    secret_violation = _require_bool(secret_violation, "secret violation flag")
    technical_status = _id(technical_status, "technical status")

    if not integrity:
        raise ValidationError("integrity uncertainty blocks closure")
    if secret_violation:
        raise ValidationError("secret violation blocks closure")
    if not critical_evidence:
        raise ValidationError("critical evidence missing")

    evidence_ids = [item.evidence_id for item in proposal.evidence]
    if len(set(evidence_ids)) != len(evidence_ids):
        raise ValidationError("duplicate evidence")
    if not _ids(required_evidence, "required evidence id").issubset(evidence_ids):
        raise ValidationError("required evidence missing")

    _validate_gate_results(proposal, _ids(required_gates, "required gate id"), gate_results)
    _validate_effect_results(proposal, effect_results)

    if proposal.authority is CompletionAuthority.AUTOMATIC:
        if not automatic_allowed:
            raise ValidationError("automatic completion not enabled")
        if any(item.effect_class not in (EffectClass.E0, EffectClass.E1) for item in effect_results):
            raise ValidationError("automatic completion limited to low-risk effects")

    expected_statuses = {
        CompletionState.COMPLETED: {"completed"},
        CompletionState.PARTIALLY_COMPLETED: {"completed"},
        CompletionState.FAILED: {"failed", "error"},
        CompletionState.CANCELLED: {"cancelled"},
    }
    if technical_status not in expected_statuses[proposal.proposed_state]:
        raise ValidationError("technical status does not support semantic closure")

    proposal_hash = hashlib.sha256(_canon(proposal.to_dict())).hexdigest()
    return ClosureDecision(proposal.proposed_state, decision_authority, proposal_hash, cleanup_plan())


__all__ = [
    "CleanupStep",
    "ClosureDecision",
    "ClosureEvidence",
    "ClosureProposal",
    "CompletionAuthority",
    "CompletionState",
    "cleanup_plan",
    "validate_closure",
]
