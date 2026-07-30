"""Pure v0.19.5 Gate B Increment 1 selection authority values."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping

from .contracts import TaskState
from .principal import ValidationError

POLICY_ID = "lowest-canonical-eligible-task-id"
POLICY_VERSION = "1"
PROPOSAL_VERSION = "1"
_FORBIDDEN = {"worker_id", "resolved_worker_id", "binding_digest", "contract_amendment",
              "evidence", "prerequisites", "acp_session_id", "retry", "graph", "dispatch",
              "model", "agent"}


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()

def _digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical(value)).hexdigest()

def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValidationError(f"invalid {label}")
    return value

def _int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValidationError(f"invalid {label}")
    return value

@dataclass(frozen=True, slots=True)
class SelectionAuthority:
    installation_id: str
    project_id: str
    run_id: str
    contract_id: str
    contract_generation: int
    revocation_epoch: int
    selection_epoch: int
    plan_revision: int
    snapshot_digest: str

    def __post_init__(self) -> None:
        for value, label in ((self.installation_id, "installation_id"), (self.project_id, "project_id"),
                             (self.run_id, "run_id"), (self.contract_id, "contract_id"),
                             (self.snapshot_digest, "snapshot_digest")):
            _text(value, label)
        for value, label in ((self.contract_generation, "contract_generation"), (self.revocation_epoch, "revocation_epoch"),
                             (self.selection_epoch, "selection_epoch"), (self.plan_revision, "plan_revision")):
            _int(value, label)

    def to_dict(self) -> dict[str, Any]:
        return {"installation_id": self.installation_id, "project_id": self.project_id, "run_id": self.run_id,
                "contract_id": self.contract_id, "contract_generation": self.contract_generation,
                "revocation_epoch": self.revocation_epoch, "selection_epoch": self.selection_epoch,
                "plan_revision": self.plan_revision, "snapshot_digest": self.snapshot_digest}

@dataclass(frozen=True, slots=True)
class Prerequisite:
    task_id: str
    receipt_id: str
    cleanup_id: str
    state: TaskState

    def __post_init__(self) -> None:
        _text(self.task_id, "prerequisite task_id")
        _text(self.receipt_id, "receipt_id")
        _text(self.cleanup_id, "cleanup_id")
        if self.state is not TaskState.CLOSED:
            raise ValidationError("prerequisite must be CLOSED")

    def to_dict(self) -> dict[str, str]:
        return {"task_id": self.task_id, "receipt_id": self.receipt_id, "cleanup_id": self.cleanup_id, "state": self.state.value}

@dataclass(frozen=True, slots=True)
class Candidate:
    task_id: str
    resolved_worker_id: str
    binding_digest: str
    prerequisites: tuple[Prerequisite, ...]
    current_task_state: TaskState
    released: bool

    def __post_init__(self) -> None:
        _text(self.task_id, "task_id")
        _text(self.resolved_worker_id, "resolved_worker_id")
        _text(self.binding_digest, "binding_digest")
        if not isinstance(self.prerequisites, tuple) or not self.prerequisites:
            raise ValidationError("candidate requires trusted prerequisites")
        if any(not isinstance(item, Prerequisite) for item in self.prerequisites):
            raise ValidationError("invalid prerequisite")
        if self.current_task_state is not TaskState.PROPOSED or not isinstance(self.released, bool) or not self.released:
            raise ValidationError("candidate is not eligible")

    def to_dict(self) -> dict[str, Any]:
        return {"task_id": self.task_id, "resolved_worker_id": self.resolved_worker_id, "binding_digest": self.binding_digest,
                "prerequisites": [item.to_dict() for item in self.prerequisites],
                "current_task_state": self.current_task_state.value, "released": self.released}

@dataclass(frozen=True, slots=True)
class EligibilityProjection:
    authority: SelectionAuthority
    candidates: tuple[Candidate, ...]
    digest: str

    def __post_init__(self) -> None:
        if tuple(sorted(self.candidates, key=lambda item: item.task_id)) != self.candidates:
            raise ValidationError("projection candidates are not canonical")
        if len({item.task_id for item in self.candidates}) != len(self.candidates):
            raise ValidationError("duplicate candidate")
        if self.digest != _projection_digest(self.authority, self.candidates):
            raise ValidationError("invalid projection digest")

def _projection_digest(authority: SelectionAuthority, candidates: tuple[Candidate, ...]) -> str:
    return _digest({"authority": authority.to_dict(), "candidates": [item.to_dict() for item in candidates]})

def derive_projection(authority: SelectionAuthority, candidates: tuple[Candidate, ...], *, approved_task_ids: tuple[str, ...], bindings: Mapping[str, str]) -> EligibilityProjection:
    if not isinstance(candidates, tuple) or len(set(approved_task_ids)) != len(approved_task_ids):
        raise ValidationError("invalid candidate set")
    approved = set(approved_task_ids)
    if set(bindings) != approved:
        raise ValidationError("bindings do not match approved candidate set")
    for item in candidates:
        if item.task_id not in approved:
            raise ValidationError("unknown candidate")
        if bindings[item.task_id] != item.resolved_worker_id:
            raise ValidationError("worker binding mismatch")
    ordered = tuple(sorted(candidates, key=lambda item: item.task_id))
    return EligibilityProjection(authority, ordered, _projection_digest(authority, ordered))

class SelectionEscalation(ValueError):
    """No deterministic selection exists; callers must escalate without fallback."""

@dataclass(frozen=True, slots=True)
class SelectionProposal:
    proposal_version: str
    proposal_id: str
    run_id: str
    selection_epoch: int
    contract_id: str
    contract_generation: int
    revocation_epoch: int
    plan_revision: int
    snapshot_digest: str
    eligibility_projection_digest: str
    selected_task_id: str
    policy_id: str
    policy_version: str

    def to_dict(self) -> dict[str, Any]:
        return {key: getattr(self, key) for key in ("proposal_version", "proposal_id", "run_id", "selection_epoch", "contract_id",
                "contract_generation", "revocation_epoch", "plan_revision", "snapshot_digest", "eligibility_projection_digest",
                "selected_task_id", "policy_id", "policy_version")}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SelectionProposal":
        if not isinstance(value, Mapping) or set(value) != set(cls.__dataclass_fields__):
            raise ValidationError("proposal fields are not exact")
        try:
            proposal = cls(**dict(value))
        except (TypeError, ValueError) as exc:
            raise ValidationError("invalid proposal") from exc
        if proposal.proposal_id != _proposal_id(proposal.to_dict()):
            raise ValidationError("proposal digest mismatch")
        return proposal

def _proposal_id(data: Mapping[str, Any]) -> str:
    return _digest({key: value for key, value in data.items() if key != "proposal_id"})

def propose_selection(projection: EligibilityProjection, **forbidden: Any) -> SelectionProposal:
    if forbidden or set(forbidden) & _FORBIDDEN:
        raise ValidationError("forbidden proposal field")
    if not projection.candidates:
        raise SelectionEscalation("no eligible candidate")
    selected = projection.candidates[0].task_id
    data = {"proposal_version": PROPOSAL_VERSION, "proposal_id": "", "run_id": projection.authority.run_id,
            "selection_epoch": projection.authority.selection_epoch, "contract_id": projection.authority.contract_id,
            "contract_generation": projection.authority.contract_generation, "revocation_epoch": projection.authority.revocation_epoch,
            "plan_revision": projection.authority.plan_revision, "snapshot_digest": projection.authority.snapshot_digest,
            "eligibility_projection_digest": projection.digest, "selected_task_id": selected, "policy_id": POLICY_ID, "policy_version": POLICY_VERSION}
    data["proposal_id"] = _proposal_id(data)
    return SelectionProposal(**data)

class KernelSelectionValidator:
    def __init__(self, authority: SelectionAuthority, candidates: tuple[Candidate, ...], *, approved_task_ids: tuple[str, ...], bindings: Mapping[str, str]) -> None:
        self._authority = authority
        self._candidates = candidates
        self._approved = approved_task_ids
        self._bindings = dict(bindings)

    def validated_projection(self, proposal: SelectionProposal) -> EligibilityProjection:
        if not isinstance(proposal, SelectionProposal):
            raise ValidationError("invalid proposal type")
        expected = derive_projection(
            self._authority,
            self._candidates,
            approved_task_ids=self._approved,
            bindings=self._bindings,
        )
        expected_proposal = propose_selection(expected)
        if proposal.to_dict() != expected_proposal.to_dict():
            raise ValidationError("proposal does not match current kernel projection or policy")
        return expected

    def validate(self, proposal: SelectionProposal) -> str:
        expected = self.validated_projection(proposal)
        return expected.candidates[0].task_id
