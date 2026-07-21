from dataclasses import FrozenInstanceError

import pytest

from olympus_v3.coordination import (
    AdmissionDecision,
    AdmissionEngine,
    AdmissionProposal,
    AdmissionSnapshot,
    AdmissionStatus,
    ContractLimits,
    ContractState,
    EvidenceGate,
    ExecutionContract,
    GateState,
    Principal,
    SideEffectPolicy,
)

PROJECT = "project-a"
OWNER = Principal(PROJECT, "hermes", "owner")
WORKER = Principal(PROJECT, "hermes", "worker")
REVIEWER = Principal(PROJECT, "hermes", "reviewer")


def make_contract(**changes) -> ExecutionContract:
    values = {
        "contract_id": "contract-a",
        "project_id": PROJECT,
        "generation": 1,
        "owner": OWNER,
        "participants": (OWNER, WORKER, REVIEWER),
        "objective": "implement deterministic coordination",
        "expected_outcome": "verified default-off coordination",
        "included_scopes": ("src/olympus_v3/coordination/",),
        "excluded_scopes": ("secrets/",),
        "role_permissions": {"worker": ("implement",), "reviewer": ("review",)},
        "evidence_gates": (EvidenceGate("spec", True, GateState.PASSED),),
        "side_effect_policy": SideEffectPolicy(("filesystem",), 2, True),
        "limits": ContractLimits(3, 600, 2, 100, 10, 10),
        "escalation_conditions": ("ambiguity",),
        "completion_authority": OWNER,
        "amendment_authority": OWNER,
        "status": ContractState.ACTIVE,
    }
    values.update(changes)
    return ExecutionContract(**values)


def proposal(task_id: str = "task-a", **changes) -> AdmissionProposal:
    values = {
        "task_id": task_id,
        "objective": "implement admission",
        "objective_source": "implement deterministic coordination",
        "scopes": ("src/olympus_v3/coordination/admission.py",),
        "dependencies": (),
        "role": "worker",
        "permission": "implement",
        "evidence": ("spec",),
        "model_cost": 20,
        "tool_cost": 5,
        "time_cost_seconds": 30,
        "retries": 1,
        "effect_class": "none",
        "fan_out": 1,
        "payload_bytes": 256,
        "lease_resources": ("admission",),
        "ambiguities": (),
    }
    values.update(changes)
    return AdmissionProposal(**values)


def decision_map(decisions: tuple[AdmissionDecision, ...]) -> dict[str, AdmissionDecision]:
    return {decision.task_id: decision for decision in decisions}


def test_engine_is_default_off_and_has_no_admission_side_effect():
    engine = AdmissionEngine()
    result = engine.evaluate(make_contract(), (proposal(),), AdmissionSnapshot())

    assert result == (
        AdmissionDecision("task-a", AdmissionStatus.REJECTED, ("coordination_disabled",)),
    )


def test_admits_valid_subtask_against_contract_limits_and_reserves():
    result = AdmissionEngine(enabled=True).evaluate(
        make_contract(),
        (proposal(),),
        AdmissionSnapshot(active_task_ids=("existing",), model_cost_used=5, tool_cost_used=5),
    )

    assert result == (AdmissionDecision("task-a", AdmissionStatus.ADMITTED, ()),)


def test_rejects_unknown_dependencies_and_every_member_of_a_cycle():
    requests = (
        proposal("task-a", dependencies=("task-b",)),
        proposal("task-b", dependencies=("task-a",)),
        proposal("task-c", dependencies=("missing",)),
    )
    decisions = decision_map(AdmissionEngine(enabled=True).evaluate(make_contract(), requests, AdmissionSnapshot()))

    assert decisions["task-a"].reasons == ("dependency_cycle",)
    assert decisions["task-b"].reasons == ("dependency_cycle",)
    assert decisions["task-c"].reasons == ("unknown_dependency",)


def test_rejects_objective_scope_and_exclusion_violations():
    requests = (
        proposal("task-objective", objective_source="different objective"),
        proposal("task-scope", scopes=("tests/outside.py",)),
        proposal("task-excluded", scopes=("secrets/key.txt",)),
    )
    decisions = decision_map(AdmissionEngine(enabled=True).evaluate(make_contract(), requests, AdmissionSnapshot()))

    assert decisions["task-objective"].reasons == ("objective_mismatch",)
    assert decisions["task-scope"].reasons == ("scope_outside_contract",)
    assert decisions["task-excluded"].reasons == ("scope_outside_contract", "scope_excluded")


def test_rejects_role_ceiling_and_unresolved_or_missing_evidence():
    pending = make_contract(evidence_gates=(EvidenceGate("spec", True),))
    decisions = decision_map(
        AdmissionEngine(enabled=True).evaluate(
            pending,
            (
                proposal("task-role", permission="review"),
                proposal("task-evidence", evidence=()),
            ),
            AdmissionSnapshot(),
        )
    )

    assert decisions["task-role"].reasons == ("role_ceiling_exceeded", "evidence_gate_unresolved")
    assert decisions["task-evidence"].reasons == ("evidence_gate_unresolved", "required_evidence_missing")


def test_rejects_retry_effect_fanout_payload_and_external_action_limits():
    requests = (
        proposal("task-retries", retries=3),
        proposal("task-effect", effect_class="network"),
        proposal("task-fanout", fan_out=4),
        proposal("task-payload", payload_bytes=16_385),
        proposal("task-effects-count", effect_class="filesystem", fan_out=3),
    )
    decisions = decision_map(AdmissionEngine(enabled=True).evaluate(make_contract(), requests, AdmissionSnapshot()))

    assert decisions["task-retries"].reasons == ("retry_limit_exceeded",)
    assert decisions["task-effect"].reasons == ("effect_not_allowed",)
    assert decisions["task-fanout"].reasons == ("fan_out_limit_exceeded",)
    assert decisions["task-payload"].reasons == ("payload_limit_exceeded",)
    assert decisions["task-effects-count"].reasons == ("external_action_limit_exceeded",)


def test_rejects_contended_active_lease_but_allows_same_task_owner():
    requests = (proposal("task-a"), proposal("task-b", lease_resources=("shared",)))
    snapshot = AdmissionSnapshot(active_leases={"admission": "task-a", "shared": "other-task"})
    decisions = decision_map(AdmissionEngine(enabled=True).evaluate(make_contract(), requests, snapshot))

    assert decisions["task-a"].status is AdmissionStatus.ADMITTED
    assert decisions["task-b"].reasons == ("lease_contended",)


def test_budget_and_concurrency_allocation_is_deterministic_and_preserves_reserves():
    contract = make_contract(limits=ContractLimits(2, 600, 2, 100, 10, 10))
    first = proposal("task-a", model_cost=35, tool_cost=5)
    second = proposal("task-b", model_cost=35, tool_cost=5)
    snapshot = AdmissionSnapshot(model_cost_used=5, tool_cost_used=5)
    engine = AdmissionEngine(enabled=True)

    forward = engine.evaluate(contract, (second, first), snapshot)
    reverse = engine.evaluate(contract, (first, second), snapshot)

    assert forward == reverse
    decisions = decision_map(forward)
    assert decisions["task-a"].status is AdmissionStatus.ADMITTED
    assert decisions["task-b"].reasons == ("protected_reserve_exceeded",)


def test_rejects_proposals_that_exceed_remaining_time_budget():
    contract = make_contract(limits=ContractLimits(3, 60, 2, 100, 10, 10))
    result = AdmissionEngine(enabled=True).evaluate(
        contract,
        (proposal(time_cost_seconds=31),),
        AdmissionSnapshot(time_seconds_used=30),
    )

    assert result == (
        AdmissionDecision("task-a", AdmissionStatus.REJECTED, ("time_budget_exceeded",)),
    )


def test_time_budget_allocation_accumulates_deterministically_across_batch():
    contract = make_contract(limits=ContractLimits(3, 60, 2, 100, 10, 10))
    engine = AdmissionEngine(enabled=True)
    first = proposal("task-a", time_cost_seconds=31)
    second = proposal("task-b", time_cost_seconds=30)

    forward = engine.evaluate(contract, (second, first), AdmissionSnapshot())
    reverse = engine.evaluate(contract, (first, second), AdmissionSnapshot())

    assert forward == reverse
    decisions = decision_map(forward)
    assert decisions["task-a"].status is AdmissionStatus.ADMITTED
    assert decisions["task-b"].reasons == ("time_budget_exceeded",)


def test_ambiguity_escalates_without_allocating_budget_or_concurrency():
    requests = (
        proposal("task-a", ambiguities=("product decision required",)),
        proposal("task-b", model_cost=60, tool_cost=20),
    )
    decisions = decision_map(AdmissionEngine(enabled=True).evaluate(make_contract(), requests, AdmissionSnapshot()))

    assert decisions["task-a"] == AdmissionDecision("task-a", AdmissionStatus.ESCALATED, ("ambiguity",))
    assert decisions["task-b"].status is AdmissionStatus.ADMITTED


def test_proposals_snapshots_and_decisions_are_deeply_immutable_and_validate_input():
    item = proposal()
    snapshot = AdmissionSnapshot(active_leases={"admission": "task-a"})
    decision = AdmissionDecision("task-a", AdmissionStatus.ADMITTED, ())

    with pytest.raises(FrozenInstanceError):
        item.retries = 2
    with pytest.raises(TypeError):
        snapshot.active_leases["other"] = "task-b"
    with pytest.raises(FrozenInstanceError):
        decision.status = AdmissionStatus.REJECTED
    with pytest.raises(ValueError):
        proposal(dependencies=("task-b", "task-b"))
    with pytest.raises(ValueError):
        AdmissionSnapshot(active_task_ids=("task-a", "task-a"))
