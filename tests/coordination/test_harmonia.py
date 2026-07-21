from dataclasses import FrozenInstanceError

import pytest

from olympus_v3.coordination import (
    AdmissionProposal,
    AdmissionSnapshot,
    AnycastAssignment,
    ContractLimits,
    ContractState,
    EvidenceGate,
    ExecutionContract,
    GateState,
    HarmoniaCoordinator,
    HarmoniaProjection,
    HarmoniaTask,
    ParticipantCard,
    PresenceProjection,
    PresenceState,
    Principal,
    SideEffectPolicy,
    TaskState,
)

PROJECT = "project-a"
OWNER = Principal(PROJECT, "hermes", "owner")
WORKER_A = Principal(PROJECT, "hefesto-a", "worker")
WORKER_B = Principal(PROJECT, "hefesto-b", "worker")
REVIEWER = Principal(PROJECT, "athena", "reviewer")


def contract(**changes) -> ExecutionContract:
    values = {
        "contract_id": "contract-a",
        "project_id": PROJECT,
        "generation": 1,
        "owner": OWNER,
        "participants": (OWNER, WORKER_A, WORKER_B, REVIEWER),
        "objective": "implement deterministic coordination",
        "expected_outcome": "verified coordination",
        "included_scopes": ("src/",),
        "excluded_scopes": ("secrets/",),
        "role_permissions": {"worker": ("implement",), "reviewer": ("review",)},
        "evidence_gates": (EvidenceGate("spec", True, GateState.PASSED),),
        "side_effect_policy": SideEffectPolicy((), 0, True),
        "limits": ContractLimits(3, 600, 2, 100, 10, 10),
        "escalation_conditions": ("ambiguity", "stall"),
        "completion_authority": OWNER,
        "amendment_authority": OWNER,
        "status": ContractState.ACTIVE,
    }
    values.update(changes)
    return ExecutionContract(**values)


def proposal(task_id="task-a", **changes) -> AdmissionProposal:
    values = {
        "task_id": task_id,
        "objective": "implement logical coordination",
        "objective_source": "implement deterministic coordination",
        "scopes": ("src/olympus_v3/coordination/harmonia.py",),
        "dependencies": (),
        "role": "worker",
        "permission": "implement",
        "evidence": ("spec",),
        "model_cost": 10,
        "tool_cost": 5,
        "time_cost_seconds": 30,
        "retries": 1,
        "effect_class": "none",
        "fan_out": 1,
        "payload_bytes": 128,
        "lease_resources": (),
        "ambiguities": (),
    }
    values.update(changes)
    return AdmissionProposal(**values)


def card(principal: Principal, role: str) -> ParticipantCard:
    return ParticipantCard(principal, role, "model-a", ("coordination",))


def presence(principal: Principal, state=PresenceState.IDLE, *, stale=False) -> PresenceProjection:
    return PresenceProjection(
        principal.owner_id,
        PROJECT,
        state,
        90,
        200,
        "event-a",
        1,
        "advisory only",
        stale,
    )


def test_harmonia_is_default_off_and_exposes_no_lifecycle_operations():
    coordinator = HarmoniaCoordinator()
    plan = coordinator.plan(
        contract(),
        (proposal(),),
        AdmissionSnapshot(),
        (card(WORKER_A, "worker"),),
        (presence(WORKER_A),),
        now=100,
    )

    assert plan.assignments == ()
    assert plan.projection.tasks[0].state is TaskState.BLOCKED
    assert plan.projection.tasks[0].reasons == ("coordination_disabled",)
    for forbidden in ("spawn", "close", "cancel", "amend", "approve", "dispatch"):
        assert not hasattr(coordinator, forbidden)


def test_selects_idle_role_anycast_target_deterministically():
    coordinator = HarmoniaCoordinator(enabled=True)
    cards = (card(WORKER_B, "worker"), card(WORKER_A, "worker"))
    presences = (presence(WORKER_B), presence(WORKER_A))

    forward = coordinator.plan(contract(), (proposal(),), AdmissionSnapshot(), cards, presences, now=100)
    reverse = coordinator.plan(
        contract(), (proposal(),), AdmissionSnapshot(), tuple(reversed(cards)), tuple(reversed(presences)), now=100
    )

    assert forward == reverse
    assert forward.assignments == (AnycastAssignment("task-a", WORKER_A),)
    assert forward.projection.tasks[0].state is TaskState.READY
    assert forward.projection.tasks[0].assignee == WORKER_A


def test_dependencies_are_admitted_but_not_ready_until_completed():
    item = proposal("task-b", dependencies=("task-a",))
    coordinator = HarmoniaCoordinator(enabled=True)
    cards = (card(WORKER_A, "worker"),)
    presences = (presence(WORKER_A),)

    waiting = coordinator.plan(
        contract(), (item,), AdmissionSnapshot(active_task_ids=("task-a",)), cards, presences, now=100
    )
    ready = coordinator.plan(
        contract(), (item,), AdmissionSnapshot(completed_task_ids=("task-a",)), cards, presences, now=100
    )

    assert waiting.assignments == ()
    assert waiting.projection.tasks[0].state is TaskState.ADMITTED
    assert ready.assignments == (AnycastAssignment("task-b", WORKER_A),)
    assert ready.projection.tasks[0].state is TaskState.READY


def test_offline_stale_or_busy_presence_cannot_be_used_as_authority():
    coordinator = HarmoniaCoordinator(enabled=True)
    plan = coordinator.plan(
        contract(),
        (proposal(),),
        AdmissionSnapshot(),
        (card(WORKER_A, "worker"), card(WORKER_B, "worker")),
        (presence(WORKER_A, PresenceState.WORKING), presence(WORKER_B, stale=True)),
        now=100,
    )

    assert plan.assignments == ()
    assert plan.escalations[0].reason == "no_eligible_target"
    assert plan.projection.tasks[0].state is TaskState.BLOCKED


def test_admission_ambiguity_is_escalated_without_assignment():
    plan = HarmoniaCoordinator(enabled=True).plan(
        contract(),
        (proposal(ambiguities=("product decision required",)),),
        AdmissionSnapshot(),
        (card(WORKER_A, "worker"),),
        (presence(WORKER_A),),
        now=100,
    )

    assert plan.assignments == ()
    assert plan.escalations[0].reason == "ambiguity"
    assert plan.projection.tasks[0].state is TaskState.BLOCKED


def test_running_stalls_and_unresolved_review_gates_are_monitored_not_closed():
    running = HarmoniaTask(proposal("task-running"), TaskState.RUNNING, WORKER_A, 10, ())
    review = HarmoniaTask(proposal("task-review"), TaskState.REVIEW, REVIEWER, 95, ())
    previous = HarmoniaProjection(3, (running, review))
    pending_contract = contract(evidence_gates=(EvidenceGate("spec", True),))

    plan = HarmoniaCoordinator(enabled=True, stall_after_seconds=60).plan(
        pending_contract,
        (proposal("task-new", evidence=()),),
        AdmissionSnapshot(),
        (card(WORKER_A, "worker"),),
        (presence(WORKER_A),),
        previous=previous,
        now=100,
    )

    reasons = {(item.task_id, item.reason) for item in plan.escalations}
    assert ("task-running", "stall") in reasons
    assert ("task-review", "gate_pending") in reasons
    assert plan.projection.revision == 4
    assert {task.task_id for task in plan.projection.tasks} == {"task-running", "task-review", "task-new"}


def test_harmonia_cannot_assign_contract_owner_to_review_its_own_work():
    plan = HarmoniaCoordinator(enabled=True).plan(
        contract(),
        (proposal(role="reviewer", permission="review"),),
        AdmissionSnapshot(),
        (card(OWNER, "reviewer"),),
        (presence(OWNER),),
        now=100,
    )

    assert plan.assignments == ()
    assert plan.escalations[0].reason == "no_eligible_target"


def test_projection_is_immutable_and_rejects_duplicate_or_replayed_tasks():
    item = HarmoniaTask(proposal(), TaskState.ADMITTED, None, 100, ())
    projection = HarmoniaProjection(1, (item,))

    with pytest.raises(FrozenInstanceError):
        item.state = TaskState.READY
    with pytest.raises(FrozenInstanceError):
        projection.revision = 2
    with pytest.raises(ValueError):
        HarmoniaProjection(1, (item, item))
    with pytest.raises(ValueError):
        HarmoniaCoordinator(enabled=True).plan(
            contract(),
            (proposal(),),
            AdmissionSnapshot(),
            (),
            (),
            previous=projection,
            now=100,
        )
