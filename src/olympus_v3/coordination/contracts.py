"""Immutable execution contracts and semantic lifecycle transitions."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Mapping

from .protocol import Principal, ValidationError

_ID = re.compile(r"^[a-z0-9][a-z0-9._:-]{0,127}$")
_SECRET_WORDS = ("secret", "password", "credential", "token", "private_key")


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValidationError(f"invalid {label}")
    return value


def _id(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"invalid {label}")
    normalized = value.strip().lower()
    if normalized != value or not _ID.fullmatch(normalized):
        raise ValidationError(f"invalid {label}")
    return normalized


def _nonnegative(value: Any, label: str) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValidationError(f"invalid {label}")
    return value


def _strings(values: Any, label: str, *, allow_empty: bool = False) -> tuple[str, ...]:
    if not isinstance(values, tuple) or (not allow_empty and not values) or len(set(values)) != len(values):
        raise ValidationError(f"invalid {label}")
    return tuple(_text(value, label) for value in values)


def _immutable_permissions(value: Any) -> MappingProxyType:
    if not isinstance(value, Mapping):
        raise ValidationError("invalid role permissions")
    result: dict[str, tuple[str, ...]] = {}
    for role, permissions in value.items():
        if not isinstance(role, str) or any(word in role.lower() for word in _SECRET_WORDS):
            raise ValidationError("invalid role permissions")
        if not isinstance(permissions, tuple):
            raise ValidationError("invalid role permissions")
        result[_text(role, "role")] = _strings(permissions, "permission")
    return MappingProxyType(dict(sorted(result.items())))


class ContractState(StrEnum):
    PROPOSED = "proposed"
    ADMITTED = "admitted"
    ACTIVE = "active"
    AMENDED = "amended"
    REVOKED = "revoked"


class TaskState(StrEnum):
    PROPOSED = "proposed"
    ADMITTED = "admitted"
    READY = "ready"
    DISPATCHED = "dispatched"
    RUNNING = "running"
    REVIEW = "review"
    CLOSURE_PROPOSED = "closure_proposed"
    ACCEPTED = "accepted"
    COMPLETED = "completed"
    PARTIALLY_COMPLETED = "partially_completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETAINED = "retained"
    BLOCKED = "blocked"


class GateState(StrEnum):
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    WAIVED = "waived"


@dataclass(frozen=True, slots=True)
class ContractLimits:
    concurrency: int
    time_seconds: int
    retries: int
    model_budget: int
    qa_reserve: int
    recovery_reserve: int

    def __post_init__(self) -> None:
        for value, label in zip((self.concurrency, self.time_seconds, self.retries, self.model_budget, self.qa_reserve, self.recovery_reserve), ("concurrency", "time", "retries", "model budget", "qa reserve", "recovery reserve")):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValidationError(f"invalid {label}")
        if self.qa_reserve == 0 or self.recovery_reserve == 0:
            raise ValidationError("qa and recovery reserves are required")
        if self.concurrency == 0 or self.time_seconds == 0:
            raise ValidationError("contract requires executable capacity")
        if self.qa_reserve + self.recovery_reserve > self.model_budget:
            raise ValidationError("reserves exceed model budget")

    def to_dict(self) -> dict[str, int]:
        return {"concurrency": self.concurrency, "time_seconds": self.time_seconds, "retries": self.retries, "model_budget": self.model_budget, "qa_reserve": self.qa_reserve, "recovery_reserve": self.recovery_reserve}

    @classmethod
    def from_dict(cls, value: Any) -> ContractLimits:
        _fields(value, {"concurrency", "time_seconds", "retries", "model_budget", "qa_reserve", "recovery_reserve"}, "limits")
        return cls(**value)


@dataclass(frozen=True, slots=True)
class SideEffectPolicy:
    allowed_effects: tuple[str, ...]
    max_external_actions: int
    reversible: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "allowed_effects", _strings(self.allowed_effects, "allowed effects", allow_empty=True))
        if isinstance(self.max_external_actions, bool) or not isinstance(self.max_external_actions, int) or self.max_external_actions < 0 or not isinstance(self.reversible, bool):
            raise ValidationError("invalid side-effect policy")

    def to_dict(self) -> dict[str, Any]:
        return {"allowed_effects": list(self.allowed_effects), "max_external_actions": self.max_external_actions, "reversible": self.reversible}

    @classmethod
    def from_dict(cls, value: Any) -> SideEffectPolicy:
        _fields(value, {"allowed_effects", "max_external_actions", "reversible"}, "side-effect policy")
        if not isinstance(value["allowed_effects"], list):
            raise ValidationError("invalid allowed effects")
        return cls(tuple(value["allowed_effects"]), value["max_external_actions"], value["reversible"])


@dataclass(frozen=True, slots=True)
class Waiver:
    reason: str
    issuer: Principal
    gate: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "reason", _text(self.reason, "waiver reason"))
        object.__setattr__(self, "gate", _text(self.gate, "waiver gate"))
        if not isinstance(self.issuer, Principal):
            raise ValidationError("invalid waiver issuer")

    def to_dict(self) -> dict[str, Any]:
        return {"reason": self.reason, "issuer": self.issuer.to_dict(), "gate": self.gate}

    @classmethod
    def from_dict(cls, value: Any) -> Waiver:
        _fields(value, {"reason", "issuer", "gate"}, "waiver")
        return cls(value["reason"], Principal.from_dict(value["issuer"]), value["gate"])


@dataclass(frozen=True, slots=True)
class EvidenceGate:
    name: str
    required: bool
    state: GateState = GateState.PENDING
    waiver: Waiver | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _id(self.name, "gate name"))
        if not isinstance(self.required, bool) or not isinstance(self.state, GateState):
            raise ValidationError("invalid evidence gate")
        if self.state is GateState.WAIVED and self.waiver is None:
            raise ValidationError("waived gate requires typed waiver")
        if self.state is not GateState.WAIVED and self.waiver is not None:
            raise ValidationError("waiver only applies to waived gate")
        if self.waiver is not None and self.waiver.gate != self.name:
            raise ValidationError("waiver gate mismatch")

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "required": self.required, "state": self.state.value, "waiver": self.waiver.to_dict() if self.waiver else None}

    @classmethod
    def from_dict(cls, value: Any) -> EvidenceGate:
        _fields(value, {"name", "required", "state", "waiver"}, "evidence gate")
        try:
            state = GateState(value["state"])
        except (TypeError, ValueError) as exc:
            raise ValidationError("invalid gate state") from exc
        return cls(value["name"], value["required"], state, Waiver.from_dict(value["waiver"]) if value["waiver"] is not None else None)


@dataclass(frozen=True, slots=True)
class ExecutionContract:
    contract_id: str
    project_id: str
    generation: int
    owner: Principal
    participants: tuple[Principal, ...]
    objective: str
    expected_outcome: str
    included_scopes: tuple[str, ...]
    excluded_scopes: tuple[str, ...]
    role_permissions: Mapping[str, tuple[str, ...]]
    evidence_gates: tuple[EvidenceGate, ...]
    side_effect_policy: SideEffectPolicy
    limits: ContractLimits
    escalation_conditions: tuple[str, ...]
    completion_authority: Principal
    amendment_authority: Principal
    revocation_epoch: int = 0
    status: ContractState = ContractState.PROPOSED

    def __post_init__(self) -> None:
        object.__setattr__(self, "contract_id", _id(self.contract_id, "contract id"))
        object.__setattr__(self, "project_id", _id(self.project_id, "project"))
        if not isinstance(self.generation, int) or isinstance(self.generation, bool) or self.generation < 0:
            raise ValidationError("invalid generation")
        if not isinstance(self.revocation_epoch, int) or isinstance(self.revocation_epoch, bool) or self.revocation_epoch < 0:
            raise ValidationError("invalid revocation epoch")
        if not isinstance(self.owner, Principal) or self.owner.project_id != self.project_id:
            raise ValidationError("owner project mismatch")

        if not isinstance(self.participants, tuple) or not self.participants or len(set(self.participants)) != len(self.participants) or any(not isinstance(item, Principal) or item.project_id != self.project_id for item in self.participants):
            raise ValidationError("invalid participants")
        if self.participants.count(self.owner) != 1:
            raise ValidationError("owner must be authorized exactly once")
        object.__setattr__(self, "objective", _text(self.objective, "objective"))
        object.__setattr__(self, "expected_outcome", _text(self.expected_outcome, "expected outcome"))
        included = _strings(self.included_scopes, "included scopes")
        excluded = _strings(self.excluded_scopes, "excluded scopes", allow_empty=True)
        if any(a == b or a.startswith(b) or b.startswith(a) for a in included for b in excluded):
            raise ValidationError("scope include/exclude overlap")
        object.__setattr__(self, "included_scopes", included)
        object.__setattr__(self, "excluded_scopes", excluded)
        object.__setattr__(self, "role_permissions", _immutable_permissions(self.role_permissions))
        if not isinstance(self.evidence_gates, tuple) or len({gate.name for gate in self.evidence_gates}) != len(self.evidence_gates) or any(not isinstance(gate, EvidenceGate) for gate in self.evidence_gates):
            raise ValidationError("invalid evidence gates")
        if not isinstance(self.side_effect_policy, SideEffectPolicy) or not isinstance(self.limits, ContractLimits):
            raise ValidationError("invalid contract controls")
        object.__setattr__(self, "escalation_conditions", _strings(self.escalation_conditions, "escalation conditions"))
        if not isinstance(self.completion_authority, Principal) or self.completion_authority not in self.participants:
            raise ValidationError("invalid completion authority")
        if not isinstance(self.amendment_authority, Principal) or self.amendment_authority not in self.participants:
            raise ValidationError("invalid amendment authority")
        participant_roles = {participant.actor_id for participant in self.participants}
        if set(self.role_permissions) - participant_roles:
            raise ValidationError("role permissions are not participant-bound")
        if not isinstance(self.status, ContractState):
            raise ValidationError("invalid contract state")

    def to_dict(self) -> dict[str, Any]:
        return {"contract_id": self.contract_id, "project_id": self.project_id, "generation": self.generation, "owner": self.owner.to_dict(), "participants": [p.to_dict() for p in self.participants], "objective": self.objective, "expected_outcome": self.expected_outcome, "included_scopes": list(self.included_scopes), "excluded_scopes": list(self.excluded_scopes), "role_permissions": {k: list(v) for k, v in self.role_permissions.items()}, "evidence_gates": [g.to_dict() for g in self.evidence_gates], "side_effect_policy": self.side_effect_policy.to_dict(), "limits": self.limits.to_dict(), "escalation_conditions": list(self.escalation_conditions), "completion_authority": self.completion_authority.to_dict(), "amendment_authority": self.amendment_authority.to_dict(), "revocation_epoch": self.revocation_epoch, "status": self.status.value}

    @classmethod
    def from_dict(cls, value: Any) -> ExecutionContract:
        fields = {"contract_id", "project_id", "generation", "owner", "participants", "objective", "expected_outcome", "included_scopes", "excluded_scopes", "role_permissions", "evidence_gates", "side_effect_policy", "limits", "escalation_conditions", "completion_authority", "amendment_authority", "revocation_epoch", "status"}
        _fields(value, fields, "execution contract")
        if any(not isinstance(value[key], list) for key in ("participants", "included_scopes", "excluded_scopes", "evidence_gates", "escalation_conditions")):
            raise ValidationError("invalid contract collections")
        perms = value["role_permissions"]
        if not isinstance(perms, dict) or any(not isinstance(v, list) for v in perms.values()):
            raise ValidationError("invalid role permissions")
        try:
            status = ContractState(value["status"])
        except (TypeError, ValueError) as exc:
            raise ValidationError("invalid contract state") from exc
        return cls(value["contract_id"], value["project_id"], value["generation"], Principal.from_dict(value["owner"]), tuple(Principal.from_dict(p) for p in value["participants"]), value["objective"], value["expected_outcome"], tuple(value["included_scopes"]), tuple(value["excluded_scopes"]), {k: tuple(v) for k, v in perms.items()}, tuple(EvidenceGate.from_dict(g) for g in value["evidence_gates"]), SideEffectPolicy.from_dict(value["side_effect_policy"]), ContractLimits.from_dict(value["limits"]), tuple(value["escalation_conditions"]), Principal.from_dict(value["completion_authority"]), Principal.from_dict(value["amendment_authority"]), value["revocation_epoch"], status)


@dataclass(frozen=True, slots=True)
class ContractAmendment:
    prior_contract: ExecutionContract
    new_contract: ExecutionContract
    prior_generation: int
    revocation_epoch: int
    rationale: str
    issuer: Principal
    affected_identities: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.prior_contract, ExecutionContract) or not isinstance(self.new_contract, ExecutionContract):
            raise ValidationError("invalid amendment contracts")
        if self.prior_contract.status is not ContractState.ACTIVE or self.new_contract.status is not ContractState.AMENDED:
            raise ValidationError("invalid amendment contract states")
        if (
            self.new_contract.contract_id != self.prior_contract.contract_id
            or self.new_contract.project_id != self.prior_contract.project_id
        ):
            raise ValidationError("amendment cannot replace contract identity")
        if self.prior_generation != self.prior_contract.generation or self.new_contract.generation != self.prior_generation + 1:
            raise ValidationError("invalid amendment generation")
        if self.revocation_epoch != self.new_contract.revocation_epoch or self.revocation_epoch != self.prior_contract.revocation_epoch + 1:
            raise ValidationError("invalid amendment revocation epoch")
        if not isinstance(self.issuer, Principal) or self.issuer not in self.prior_contract.participants:
            raise ValidationError("invalid amendment issuer")
        if self.issuer != self.prior_contract.amendment_authority:
            raise ValidationError("issuer is not the amendment authority")
        object.__setattr__(self, "rationale", _text(self.rationale, "amendment rationale"))
        object.__setattr__(self, "affected_identities", _strings(self.affected_identities, "affected identities"))


def amend_contract(contract: ExecutionContract, *, rationale: str, issuer: Principal, affected_identities: tuple[str, ...], **changes: Any) -> ContractAmendment:
    if not isinstance(contract, ExecutionContract) or not isinstance(issuer, Principal):
        raise ValidationError("invalid amendment issuer")
    if issuer != contract.amendment_authority:
        raise ValidationError("issuer is not the amendment authority")
    if contract.status is not ContractState.ACTIVE:
        raise ValidationError("only an active contract can be amended")
    protected = {"contract_id", "project_id", "generation", "revocation_epoch", "status"}
    known = set(contract.__dataclass_fields__)
    if set(changes) & protected or set(changes) - known:
        raise ValidationError("invalid amendment fields")
    if not isinstance(affected_identities, tuple) or not affected_identities or len(set(affected_identities)) != len(affected_identities) or any(not _id(item, "affected identity") for item in affected_identities):
        raise ValidationError("invalid affected identities")
    rationale = _text(rationale, "amendment rationale")
    values = {field: getattr(contract, field) for field in contract.__dataclass_fields__}
    values.update(changes)
    values["generation"] = contract.generation + 1
    values["revocation_epoch"] = contract.revocation_epoch + 1
    values["status"] = ContractState.AMENDED
    new_contract = ExecutionContract(**values)
    return ContractAmendment(contract, new_contract, contract.generation, new_contract.revocation_epoch, rationale, issuer, affected_identities)


def assert_current_generation(generation: int, revocation_epoch: int, contract_generation: int, current_revocation_epoch: int) -> None:
    values = (generation, revocation_epoch, contract_generation, current_revocation_epoch)
    if any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in values):
        raise ValidationError("invalid generation or revocation epoch")
    if generation != contract_generation or revocation_epoch != current_revocation_epoch:
        raise ValidationError("stale contract generation or revocation epoch")


def _transition(current: Any, target: Any, enum_type: type[StrEnum], legal: Mapping[Any, set[Any]], *, generation: int, contract_generation: int, revocation_epoch: int, current_revocation_epoch: int) -> Any:
    try:
        current = enum_type(current)
        target = enum_type(target)
    except (TypeError, ValueError) as exc:
        raise ValidationError("unknown lifecycle state") from exc
    assert_current_generation(generation, revocation_epoch, contract_generation, current_revocation_epoch)
    if target not in legal.get(current, set()):
        raise ValidationError("illegal lifecycle transition")
    return target


def transition_contract_state(current: ContractState, target: ContractState, **versions: int) -> ContractState:
    legal = {ContractState.PROPOSED: {ContractState.ADMITTED}, ContractState.ADMITTED: {ContractState.ACTIVE, ContractState.REVOKED}, ContractState.ACTIVE: {ContractState.AMENDED, ContractState.REVOKED}, ContractState.AMENDED: {ContractState.ACTIVE, ContractState.REVOKED}}
    return _transition(current, target, ContractState, legal, **versions)


def transition_task_state(current: TaskState | str, target: TaskState | str, *, contract: ExecutionContract | None = None, actor: Principal | None = None, gates: tuple[EvidenceGate, ...] = (), **versions: int) -> TaskState:
    legal = {TaskState.PROPOSED: {TaskState.ADMITTED, TaskState.BLOCKED}, TaskState.ADMITTED: {TaskState.READY, TaskState.BLOCKED}, TaskState.READY: {TaskState.DISPATCHED, TaskState.BLOCKED}, TaskState.DISPATCHED: {TaskState.RUNNING, TaskState.BLOCKED}, TaskState.RUNNING: {TaskState.REVIEW, TaskState.BLOCKED, TaskState.CANCELLED}, TaskState.REVIEW: {TaskState.CLOSURE_PROPOSED, TaskState.RUNNING, TaskState.RETAINED, TaskState.BLOCKED, TaskState.CANCELLED}, TaskState.CLOSURE_PROPOSED: {TaskState.ACCEPTED, TaskState.REVIEW, TaskState.RETAINED}, TaskState.ACCEPTED: {TaskState.COMPLETED, TaskState.PARTIALLY_COMPLETED, TaskState.FAILED, TaskState.CANCELLED}, TaskState.RETAINED: {TaskState.READY, TaskState.BLOCKED}, TaskState.BLOCKED: {TaskState.READY, TaskState.RETAINED}}
    result = _transition(current, target, TaskState, legal, **versions)
    authority_targets = {TaskState.CLOSURE_PROPOSED, TaskState.ACCEPTED, TaskState.COMPLETED, TaskState.PARTIALLY_COMPLETED, TaskState.FAILED, TaskState.CANCELLED}
    gated_targets = {TaskState.CLOSURE_PROPOSED, TaskState.ACCEPTED, TaskState.COMPLETED, TaskState.PARTIALLY_COMPLETED}
    if result in authority_targets:
        if not isinstance(contract, ExecutionContract):
            raise ValidationError("contract is required for semantic closure")
        if contract.status is not ContractState.ACTIVE:
            raise ValidationError("only an active contract can authorize semantic transitions")
        if not isinstance(actor, Principal):
            raise ValidationError("semantic transition actor is required")
        if result is TaskState.CLOSURE_PROPOSED and actor != contract.owner:
            raise ValidationError("only the accountable owner can propose closure")
        if result in {TaskState.ACCEPTED, TaskState.COMPLETED, TaskState.PARTIALLY_COMPLETED, TaskState.FAILED} and actor != contract.completion_authority:
            raise ValidationError("only the completion authority can accept or close")
        if result is TaskState.CANCELLED and actor not in {contract.owner, contract.completion_authority}:
            raise ValidationError("unauthorized cancellation")
        if (
            versions.get("contract_generation") != contract.generation
            or versions.get("current_revocation_epoch") != contract.revocation_epoch
        ):
            raise ValidationError("contract authority does not match transition")
    if result in gated_targets:
        if not isinstance(contract, ExecutionContract):
            raise ValidationError("contract is required for semantic closure")
        if not isinstance(gates, tuple) or any(not isinstance(gate, EvidenceGate) for gate in gates):
            raise ValidationError("required evidence gates are unresolved")
        definitions = {gate.name: gate for gate in contract.evidence_gates}
        results = {gate.name: gate for gate in gates}
        if len(results) != len(gates) or set(results) - set(definitions):
            raise ValidationError("invalid evidence gate results")
        for name, definition in definitions.items():
            result_gate = results.get(name)
            if not definition.required:
                continue
            if result_gate is None or result_gate.required is not True:
                raise ValidationError("required evidence gates are unresolved")
            if result_gate.state not in {GateState.PASSED, GateState.WAIVED}:
                raise ValidationError("required evidence gates are unresolved")
            if result_gate.waiver is not None and result_gate.waiver.issuer != contract.completion_authority:
                raise ValidationError("unauthorized gate waiver")
    return result


def is_role_permitted(contract: ExecutionContract, principal: Principal, permission: str) -> bool:
    """Return explicit role permission; malformed, unknown, and unbound inputs deny."""
    if not isinstance(contract, ExecutionContract) or not isinstance(principal, Principal) or not isinstance(permission, str):
        return False
    if principal not in contract.participants:
        return False
    return permission in contract.role_permissions.get(principal.actor_id, ())


def _fields(value: Any, expected: set[str], label: str) -> None:
    if not isinstance(value, dict) or set(value) != expected:
        raise ValidationError(f"invalid {label} fields")


__all__ = ["ContractAmendment", "ContractLimits", "ContractState", "EvidenceGate", "ExecutionContract", "GateState", "SideEffectPolicy", "TaskState", "ValidationError", "Waiver", "amend_contract", "assert_current_generation", "is_role_permitted", "transition_contract_state", "transition_task_state"]
