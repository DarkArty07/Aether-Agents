from dataclasses import FrozenInstanceError

import pytest

from olympus_v3.coordination import (
    ContractAmendment,
    ContractLimits,
    ContractState,
    EvidenceGate,
    ExecutionContract,
    GateState,
    Principal,
    SideEffectPolicy,
    TaskState,
    ValidationError,
    Waiver,
    amend_contract,
    assert_current_generation,
    is_role_permitted,
    transition_contract_state,
    transition_task_state,
)

PROJECT = "project-a"
OWNER = Principal(PROJECT, "hermes", "owner")
REVIEWER = Principal(PROJECT, "hermes", "reviewer")
WORKER = Principal(PROJECT, "hermes", "worker")
LIMITS = ContractLimits(2, 60, 3, 1000, 10, 5)
POLICY = SideEffectPolicy(("filesystem",), 2, True)
GATE = EvidenceGate("qa", True)


def make_contract(**changes):
    values = {
        "contract_id": "contract-a",
        "project_id": PROJECT,
        "generation": 0,
        "owner": OWNER,
        "participants": (OWNER, REVIEWER, WORKER),
        "objective": "build the feature",
        "expected_outcome": "verified feature",
        "included_scopes": ("src/",),
        "excluded_scopes": ("secrets/",),
        "role_permissions": {"reviewer": ("review",), "worker": ("implement",)},
        "evidence_gates": (GATE,),
        "side_effect_policy": POLICY,
        "limits": LIMITS,
        "escalation_conditions": ("ambiguity",),
        "completion_authority": OWNER,
        "amendment_authority": OWNER,
    }
    values.update(changes)
    return ExecutionContract(**values)


def test_execution_contract_is_frozen_and_round_trips_strictly():
    contract = make_contract()
    assert contract.to_dict() == ExecutionContract.from_dict(contract.to_dict()).to_dict()
    with pytest.raises((FrozenInstanceError, TypeError, AttributeError)):
        contract.generation = 1
    with pytest.raises(ValidationError):
        ExecutionContract.from_dict({**contract.to_dict(), "unknown": True})


def test_contract_rejects_identity_scope_limit_and_mutability_violations():
    with pytest.raises(ValidationError):
        make_contract(owner=Principal("other", "hermes", "owner"))
    with pytest.raises(ValidationError):
        make_contract(participants=(OWNER, OWNER))
    with pytest.raises(ValidationError):
        make_contract(participants=(REVIEWER, WORKER))
    with pytest.raises(ValidationError):
        make_contract(included_scopes=("src/",), excluded_scopes=("src/file.py",))
    with pytest.raises(ValidationError):
        make_contract(limits=ContractLimits(-1, 1, 1, 1, 1, 1))
    with pytest.raises(ValidationError):
        make_contract(limits=ContractLimits(1, 1, 1, 1, 0, 1))
    with pytest.raises(ValidationError):
        make_contract(objective=[])
    with pytest.raises(ValidationError):
        make_contract(role_permissions={"worker": ["implement"]})


def test_gate_completion_requires_passed_or_validly_waived_gates():
    contract = make_contract(status=ContractState.ACTIVE)
    assert transition_task_state(TaskState.REVIEW, TaskState.CLOSURE_PROPOSED, contract=contract, actor=OWNER, generation=0, contract_generation=0, revocation_epoch=0, current_revocation_epoch=0, gates=(EvidenceGate("qa", True, GateState.PASSED),)) == TaskState.CLOSURE_PROPOSED
    with pytest.raises(ValidationError):
        transition_task_state(TaskState.REVIEW, TaskState.CLOSURE_PROPOSED, contract=contract, actor=OWNER, generation=0, contract_generation=0, revocation_epoch=0, current_revocation_epoch=0, gates=(GATE,))
    waiver = Waiver("risk accepted", OWNER, "qa")
    assert EvidenceGate("qa", True, GateState.WAIVED, waiver).to_dict()["waiver"]["reason"] == "risk accepted"
    with pytest.raises(ValidationError):
        Waiver("", OWNER, "qa")


def test_amendment_is_atomic_new_generation_and_original_is_unchanged():
    original = make_contract(status=ContractState.ACTIVE)
    before = original.to_dict()
    amendment = amend_contract(original, rationale="scope clarified", issuer=OWNER, affected_identities=("task-1", "capability-x"))
    assert isinstance(amendment, ContractAmendment)
    assert amendment.prior_generation == 0
    assert amendment.new_contract.generation == 1
    assert amendment.revocation_epoch == 1
    assert amendment.affected_identities == ("task-1", "capability-x")
    assert original.to_dict() == before
    with pytest.raises(ValidationError):
        amend_contract(original, rationale="", issuer=OWNER, affected_identities=())


def test_legal_transitions_cover_lifecycle_interruptions_and_reject_illegal_or_stale():
    assert transition_contract_state(ContractState.PROPOSED, ContractState.ADMITTED, generation=0, contract_generation=0, revocation_epoch=0, current_revocation_epoch=0) == ContractState.ADMITTED
    assert transition_task_state(TaskState.BLOCKED, TaskState.READY, generation=0, contract_generation=0, revocation_epoch=0, current_revocation_epoch=0) == TaskState.READY
    assert transition_task_state(TaskState.REVIEW, TaskState.RETAINED, generation=0, contract_generation=0, revocation_epoch=0, current_revocation_epoch=0) == TaskState.RETAINED
    assert transition_task_state(TaskState.REVIEW, TaskState.RUNNING, generation=0, contract_generation=0, revocation_epoch=0, current_revocation_epoch=0) == TaskState.RUNNING
    with pytest.raises(ValidationError):
        transition_task_state(TaskState.COMPLETED, TaskState.RUNNING, generation=0, contract_generation=0, revocation_epoch=0, current_revocation_epoch=0)
    with pytest.raises(ValidationError):
        transition_task_state("unknown", TaskState.READY, generation=0, contract_generation=0, revocation_epoch=0, current_revocation_epoch=0)
    with pytest.raises(ValidationError):
        assert_current_generation(0, 1, 0, 0)
    with pytest.raises(ValidationError):
        assert_current_generation(0, 0, 0, 1)


def test_json_safe_contract_serialization_excludes_secrets():
    wire = make_contract().to_dict()
    assert not {"secret", "password", "credential", "token"} & set(wire)
    assert isinstance(wire["participants"], list)
    assert ExecutionContract.from_dict(wire) == make_contract()


def test_limits_require_executable_capacity_and_reserves_within_budget():
    with pytest.raises(ValidationError):
        ContractLimits(0, 60, 3, 100, 10, 5)
    with pytest.raises(ValidationError):
        ContractLimits(1, 0, 3, 100, 10, 5)
    with pytest.raises(ValidationError):
        ContractLimits(1, 60, 3, 10, 7, 4)


def test_closure_uses_the_complete_contract_gate_set_and_authorized_waivers():
    contract = make_contract(status=ContractState.ACTIVE)
    versions = {
        "generation": 0,
        "contract_generation": 0,
        "revocation_epoch": 0,
        "current_revocation_epoch": 0,
    }
    with pytest.raises(ValidationError):
        transition_task_state(
            TaskState.REVIEW,
            TaskState.CLOSURE_PROPOSED,
            contract=contract, actor=OWNER,
            gates=(),
            **versions,
        )
    passed = (EvidenceGate("qa", True, GateState.PASSED),)
    assert transition_task_state(
        TaskState.REVIEW,
        TaskState.CLOSURE_PROPOSED,
        contract=contract, actor=OWNER,
        gates=passed,
        **versions,
    ) is TaskState.CLOSURE_PROPOSED
    valid_waiver = (EvidenceGate("qa", True, GateState.WAIVED, Waiver("accepted", OWNER, "qa")),)
    assert transition_task_state(
        TaskState.REVIEW,
        TaskState.CLOSURE_PROPOSED,
        contract=contract, actor=OWNER,
        gates=valid_waiver,
        **versions,
    ) is TaskState.CLOSURE_PROPOSED

    outsider = Principal("other-project", "hermes", "outsider")
    forged_waivers = (
        EvidenceGate("qa", True, GateState.WAIVED, Waiver("accepted", outsider, "qa")),
        EvidenceGate("qa", True, GateState.WAIVED, Waiver("accepted", REVIEWER, "qa")),
    )
    for forged in forged_waivers:
        with pytest.raises(ValidationError):
            transition_task_state(
                TaskState.REVIEW,
                TaskState.CLOSURE_PROPOSED,
                contract=contract, actor=OWNER,
                gates=(forged,),
                **versions,
            )


def test_amendment_cannot_replace_contract_identity_or_system_fields():
    contract = make_contract(status=ContractState.ACTIVE)
    for changes in (
        {"contract_id": "different-contract"},
        {"project_id": "different-project"},
        {"generation": 99},
        {"revocation_epoch": 99},
        {"status": ContractState.REVOKED},
        {"unknown": "field"},
    ):
        with pytest.raises(ValidationError):
            amend_contract(
                contract,
                rationale="requested change",
                issuer=OWNER,
                affected_identities=("task-1",),
                **changes,
            )

    other = make_contract(
        contract_id="different-contract",
        generation=1,
        revocation_epoch=1,
        status=ContractState.AMENDED,
    )
    with pytest.raises(ValidationError):
        ContractAmendment(contract, other, 0, 1, "invalid replacement", OWNER, ("task-1",))


def test_transition_normalizes_valid_wire_states_and_rejects_boolean_versions():
    versions = {
        "generation": 0,
        "contract_generation": 0,
        "revocation_epoch": 0,
        "current_revocation_epoch": 0,
    }
    result = transition_task_state("blocked", "ready", **versions)
    assert result is TaskState.READY
    with pytest.raises(ValidationError):
        assert_current_generation(False, 0, 0, 0)


def test_non_active_contracts_cannot_authorize_semantic_closure():
    passed = (EvidenceGate("qa", True, GateState.PASSED),)
    versions = {
        "generation": 0,
        "contract_generation": 0,
        "revocation_epoch": 0,
        "current_revocation_epoch": 0,
    }
    for status in (
        ContractState.PROPOSED,
        ContractState.ADMITTED,
        ContractState.AMENDED,
        ContractState.REVOKED,
    ):
        contract = make_contract(status=status)
        with pytest.raises(ValidationError):
            transition_task_state(
                TaskState.REVIEW,
                TaskState.CLOSURE_PROPOSED,
                contract=contract,
                actor=OWNER,
                gates=passed,
                **versions,
            )


def test_designated_amendment_authority_is_required():
    contract = make_contract(status=ContractState.ACTIVE)
    with pytest.raises(ValidationError):
        amend_contract(
            contract,
            rationale="unauthorized change",
            issuer=REVIEWER,
            affected_identities=("task-1",),
            objective="broader objective",
        )

    delegated = make_contract(status=ContractState.ACTIVE, amendment_authority=REVIEWER)
    amendment = amend_contract(
        delegated,
        rationale="delegated change",
        issuer=REVIEWER,
        affected_identities=("task-1",),
        objective="approved objective",
    )
    assert amendment.issuer == REVIEWER


def test_owner_proposes_and_completion_authority_accepts_and_closes():
    contract = make_contract(status=ContractState.ACTIVE, completion_authority=REVIEWER)
    gates = (EvidenceGate("qa", True, GateState.PASSED),)
    versions = {
        "generation": 0,
        "contract_generation": 0,
        "revocation_epoch": 0,
        "current_revocation_epoch": 0,
    }
    with pytest.raises(ValidationError):
        transition_task_state(
            TaskState.REVIEW,
            TaskState.CLOSURE_PROPOSED,
            contract=contract,
            actor=REVIEWER,
            gates=gates,
            **versions,
        )
    assert transition_task_state(
        TaskState.REVIEW,
        TaskState.CLOSURE_PROPOSED,
        contract=contract,
        actor=OWNER,
        gates=gates,
        **versions,
    ) is TaskState.CLOSURE_PROPOSED

    with pytest.raises(ValidationError):
        transition_task_state(
            TaskState.CLOSURE_PROPOSED,
            TaskState.ACCEPTED,
            contract=contract,
            actor=OWNER,
            gates=gates,
            **versions,
        )
    assert transition_task_state(
        TaskState.CLOSURE_PROPOSED,
        TaskState.ACCEPTED,
        contract=contract,
        actor=REVIEWER,
        gates=gates,
        **versions,
    ) is TaskState.ACCEPTED

    with pytest.raises(ValidationError):
        transition_task_state(
            TaskState.ACCEPTED,
            TaskState.COMPLETED,
            contract=contract,
            actor=OWNER,
            gates=gates,
            **versions,
        )
    assert transition_task_state(
        TaskState.ACCEPTED,
        TaskState.COMPLETED,
        contract=contract,
        actor=REVIEWER,
        gates=gates,
        **versions,
    ) is TaskState.COMPLETED


def test_role_permissions_are_participant_bound_and_default_deny():
    with pytest.raises(ValidationError):
        make_contract(role_permissions={"ghost": ("admin",)})

    contract = make_contract()
    assert is_role_permitted(contract, WORKER, "implement") is True
    assert is_role_permitted(contract, REVIEWER, "implement") is False
    outsider = Principal(PROJECT, "hermes", "outsider")
    assert is_role_permitted(contract, outsider, "implement") is False
