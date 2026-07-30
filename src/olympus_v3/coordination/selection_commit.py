"""Kernel-owned durable selection commit for v0.19.5 Gate B Increment 2."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from .harmonia_selection import KernelSelectionValidator, SelectionProposal
from .ledger import AppendResult, Result, SignedEventDraft, SQLiteLedger, WriterContext
from .principal import ValidationError

EVENT_KIND = "task.selection.committed"

@dataclass(frozen=True, slots=True)
class SelectionDecision:
    run_id: str
    selection_epoch: int
    proposal_id: str
    proposal_digest: str
    eligibility_projection_digest: str
    selected_task_id: str
    resolved_worker_id: str
    binding_digest: str
    expected_version: int
    contract_id: str
    contract_generation: int
    revocation_epoch: int
    plan_revision: int
    snapshot_digest: str

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "SelectionDecision":
        return cls(**{field: payload[field] for field in cls.__dataclass_fields__})

@dataclass(frozen=True, slots=True)
class SelectionCommitResult:
    status: Result
    decision: SelectionDecision | None = None
    event: Any = None

def _digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return "sha256:" + hashlib.sha256(encoded).hexdigest()

def _proposal_digest(proposal: SelectionProposal) -> str:
    return _digest(proposal.to_dict())

def _aggregate(run_id: str) -> str:
    return f"selection:{run_id}"

def _decision_payload(proposal: SelectionProposal, projection, expected_version: int) -> dict[str, Any]:
    candidate = next(item for item in projection.candidates if item.task_id == proposal.selected_task_id)
    authority = projection.authority
    return {
        "run_id": proposal.run_id, "selection_epoch": proposal.selection_epoch,
        "proposal_id": proposal.proposal_id, "proposal_digest": _proposal_digest(proposal),
        "eligibility_projection_digest": proposal.eligibility_projection_digest,
        "selected_task_id": candidate.task_id, "resolved_worker_id": candidate.resolved_worker_id,
        "binding_digest": candidate.binding_digest, "expected_version": expected_version,
        "contract_id": authority.contract_id, "contract_generation": authority.contract_generation,
        "revocation_epoch": authority.revocation_epoch, "plan_revision": authority.plan_revision,
        "snapshot_digest": authority.snapshot_digest,
        "proposal_version": proposal.proposal_version, "policy_id": proposal.policy_id, "policy_version": proposal.policy_version,
    }

class KernelSelectionCommitter:
    def __init__(self, ledger: SQLiteLedger, writer: WriterContext) -> None:
        if writer.scope != ledger.scope:
            raise ValueError("writer scope mismatch")
        self.ledger = ledger
        self.writer = writer

    def _existing(self, proposal: SelectionProposal) -> tuple[SelectionDecision, Any] | None:
        aggregate = _aggregate(proposal.run_id)
        for event in self.ledger.events():
            if event["aggregate"] != aggregate:
                continue
            payload = json.loads(event["payload"])
            if payload.get("selection_epoch") == proposal.selection_epoch:
                return SelectionDecision.from_payload(payload), event
        return None

    def commit(self, proposal: SelectionProposal, projection, validator: KernelSelectionValidator) -> SelectionCommitResult:
        if isinstance(proposal.selection_epoch, bool) or not isinstance(proposal.selection_epoch, int) or proposal.selection_epoch <= 0:
            raise ValidationError("selection_epoch must be strictly positive")
        existing = self._existing(proposal)
        if existing is not None:
            decision, event = existing
            if decision.proposal_id != proposal.proposal_id:
                return SelectionCommitResult(Result.CAS_CONFLICT, decision, event)
            if decision.proposal_digest != _proposal_digest(proposal):
                return SelectionCommitResult(Result.IDEMPOTENCY_CONFLICT, decision, event)
            return SelectionCommitResult(Result.DUPLICATE, decision, event)

        trusted_projection = validator.validated_projection(proposal)
        if projection != trusted_projection:
            raise ValidationError("projection does not match current kernel state")
        expected_version = proposal.selection_epoch - 1
        payload = _decision_payload(proposal, trusted_projection, expected_version)
        draft = SignedEventDraft(
            self.ledger.scope, _aggregate(proposal.run_id), EVENT_KIND, payload,
            self.writer.writer_id, self.writer.key_id, self.writer.resource, self.writer.fence,
            expected_version=expected_version, contract_generation=proposal.contract_generation,
            revocation_epoch=proposal.revocation_epoch,
        )
        signer = self.ledger.writer_authenticator
        if not hasattr(signer, "sign"):
            raise ValueError("kernel writer authenticator cannot sign")
        signed = signer.sign(draft, self.writer)
        result: AppendResult = self.ledger.append(
            signed, self.writer, message_id=f"selection:{proposal.run_id}:{proposal.selection_epoch}:{proposal.proposal_id}"
        )
        if result.status is Result.APPLIED:
            return SelectionCommitResult(result.status, SelectionDecision.from_payload(payload), result.event)
        if result.status is Result.CAS_CONFLICT:
            existing = self._existing(proposal)
            if existing is not None:
                return SelectionCommitResult(Result.CAS_CONFLICT, existing[0], existing[1])
        return SelectionCommitResult(result.status)

def rebuild_selection_decisions(ledger: SQLiteLedger) -> dict[tuple[str, int], SelectionDecision]:
    ledger.verify_chain()
    ledger.verify_projections()
    decisions: dict[tuple[str, int], SelectionDecision] = {}
    for event in ledger.events():
        if event["kind"] != EVENT_KIND:
            continue
        payload = json.loads(event["payload"])
        draft = SignedEventDraft(
            ledger.scope, event["aggregate"], event["kind"], payload,
            event["writer_id"], event["key_id"], event["resource"], event["fence"],
            event["writer_proof"], event["version"] - 1,
            event["contract_generation"], event["revocation_epoch"],
        )
        context = WriterContext(ledger.scope, event["writer_id"], event["key_id"], event["resource"], event["fence"], 1)
        if not ledger.writer_authenticator.verify(draft, context):
            raise ValueError("selection writer authentication failed")
        decision = SelectionDecision.from_payload(payload)
        key = (decision.run_id, decision.selection_epoch)
        if key in decisions and decisions[key] != decision:
            raise ValueError("duplicate selection authority")
        decisions[key] = decision
    return decisions
