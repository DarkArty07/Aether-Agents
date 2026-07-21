import asyncio
import inspect
import json
from functools import wraps

import pytest

from olympus_v3.coordination import (
    AdmissionDecision,
    AdmissionProposal,
    AdmissionStatus,
    AnycastAssignment,
    HarmoniaPlan,
    HarmoniaProjection,
    HarmoniaTask,
    OlympusRuntimeAdapter,
    Principal,
    RuntimeStatus,
    TaskState,
)

PROJECT = "project-a"
WORKER_A = Principal(PROJECT, "instance-a", "hefesto")
WORKER_B = Principal(PROJECT, "instance-b", "hefesto")


def async_test(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        return asyncio.run(function(*args, **kwargs))

    return wrapper


class FakeACPManager:
    def __init__(self, *, fail_send=False, cancel_send=False):
        self.calls = []
        self.fail_send = fail_send
        self.cancel_send = cancel_send

    async def spawn_agent(self, agent_name, session_id=None, project_root=None):
        self.calls.append(("spawn_agent", agent_name, session_id, project_root))
        return session_id

    async def send_message(self, session_id, message):
        self.calls.append(("send_message", session_id, message))
        if self.cancel_send:
            raise asyncio.CancelledError
        if self.fail_send:
            raise RuntimeError("send failed")
        return {"status": "sent", "session_id": session_id}

    async def poll(self, session_id):
        self.calls.append(("poll", session_id))
        return {"status": "completed", "last_turn": "technical output"}

    async def close(self, session_id, *, terminal_status=None):
        self.calls.append(("close", session_id, terminal_status))
        return {"status": terminal_status or "cancelled", "session_id": session_id}


class BlockingACPManager(FakeACPManager):
    def __init__(self):
        super().__init__()
        self.send_started = asyncio.Event()
        self.send_release = asyncio.Event()

    async def send_message(self, session_id, message):
        self.calls.append(("send_message", session_id, message))
        self.send_started.set()
        await self.send_release.wait()
        return {"status": "sent", "session_id": session_id}


def proposal(task_id="task-a", *, objective="objective-a"):
    return AdmissionProposal(
        task_id=task_id,
        objective=objective,
        objective_source="user",
        scopes=("src",),
        dependencies=(),
        role="hefesto",
        permission="implement",
        fan_out=1,
        payload_bytes=100,
        model_cost=1,
        tool_cost=1,
        time_cost_seconds=30,
        retries=1,
        effect_class="e1",
        lease_resources=(),
        evidence=("gate-a",),
    )


def plan(*, status=AdmissionStatus.ADMITTED, participants=(WORKER_A,)):
    item = proposal()
    decision = AdmissionDecision(
        item.task_id,
        status,
        () if status is AdmissionStatus.ADMITTED else ("denied",),
        item,
    )
    assignments = tuple(AnycastAssignment(item.task_id, participant) for participant in participants)
    task = HarmoniaTask(item, TaskState.READY, participants[0] if participants else None, 0, ())
    projection = HarmoniaProjection(1, (task,))
    return HarmoniaPlan((decision,), assignments, (), projection)


@async_test
async def test_runtime_adapter_is_default_off_and_calls_no_acp_operation():
    manager = FakeACPManager()
    adapter = OlympusRuntimeAdapter(manager, project_id=PROJECT)

    receipts = await adapter.dispatch(plan(), project_root="/tmp/project-a")

    assert receipts[0].status is RuntimeStatus.DISABLED
    assert manager.calls == []


@async_test
async def test_admitted_assignment_uses_only_public_spawn_and_send_operations():
    manager = FakeACPManager()
    adapter = OlympusRuntimeAdapter(manager, project_id=PROJECT, enabled=True)

    receipts = await adapter.dispatch(plan(), project_root="/tmp/project-a/../project-a")

    assert receipts[0].status is RuntimeStatus.SENT
    assert manager.calls[0][0:2] == ("spawn_agent", "hefesto")
    assert manager.calls[0][3] == "/tmp/project-a"
    prompt = json.loads(manager.calls[1][2])
    assert prompt["kind"] == "aether.admitted_work"
    assert prompt["task_id"] == "task-a"
    assert prompt["objective"] == "objective-a"
    assert prompt["permission"] == "implement"


@async_test
async def test_previous_projection_tasks_do_not_invalidate_new_admitted_assignment():
    manager = FakeACPManager()
    adapter = OlympusRuntimeAdapter(manager, project_id=PROJECT, enabled=True)
    current = plan()
    previous = proposal("task-previous")
    projection = HarmoniaProjection(
        2,
        current.projection.tasks
        + (HarmoniaTask(previous, TaskState.RUNNING, WORKER_B, 1, ()),),
    )
    incremental = HarmoniaPlan(current.admissions, current.assignments, (), projection)

    receipts = await adapter.dispatch(incremental, project_root="/tmp/project-a")

    assert receipts[0].status is RuntimeStatus.SENT
    assert [call[0] for call in manager.calls] == ["spawn_agent", "send_message"]


@async_test
async def test_replay_is_idempotent_and_does_not_open_a_second_session():
    manager = FakeACPManager()
    adapter = OlympusRuntimeAdapter(manager, project_id=PROJECT, enabled=True)
    first = await adapter.dispatch(plan(), project_root="/tmp/project-a")
    replay = await adapter.dispatch(plan(), project_root="/tmp/project-a")

    assert first[0].session_id == replay[0].session_id
    assert replay[0].status is RuntimeStatus.REPLAYED
    assert [call[0] for call in manager.calls] == ["spawn_agent", "send_message"]


@async_test
async def test_assignment_for_non_admitted_work_is_an_invalid_plan():
    manager = FakeACPManager()
    adapter = OlympusRuntimeAdapter(manager, project_id=PROJECT, enabled=True)

    denied = await adapter.dispatch(plan(status=AdmissionStatus.REJECTED), project_root="/tmp/project-a")

    assert denied[0].status is RuntimeStatus.REJECTED
    assert denied[0].reason == "invalid_plan"
    assert manager.calls == []


@async_test
async def test_send_failure_requests_manager_cleanup_without_owning_lifecycle():
    manager = FakeACPManager(fail_send=True)
    adapter = OlympusRuntimeAdapter(manager, project_id=PROJECT, enabled=True)

    receipt = (await adapter.dispatch(plan(), project_root="/tmp/project-a"))[0]

    assert receipt.status is RuntimeStatus.ERROR
    assert [call[0] for call in manager.calls] == ["spawn_agent", "send_message", "close"]
    assert manager.calls[-1][2] == "error"


def test_caller_cancellation_after_spawn_closes_session_before_propagating():
    manager = FakeACPManager(cancel_send=True)
    adapter = OlympusRuntimeAdapter(manager, project_id=PROJECT, enabled=True)

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(adapter.dispatch(plan(), project_root="/tmp/project-a"))

    assert [call[0] for call in manager.calls] == ["spawn_agent", "send_message", "close"]
    assert manager.calls[-1][2] == "error"


@async_test
async def test_multiple_assignments_for_one_anycast_task_fail_closed_before_acp():
    manager = FakeACPManager()
    adapter = OlympusRuntimeAdapter(manager, project_id=PROJECT, enabled=True)

    receipts = await adapter.dispatch(
        plan(participants=(WORKER_B, WORKER_A)),
        project_root="/tmp/project-a",
    )

    assert len(receipts) == 2
    assert all(item.status is RuntimeStatus.REJECTED for item in receipts)
    assert all(item.reason == "invalid_plan" for item in receipts)
    assert manager.calls == []


@async_test
async def test_substituted_projection_proposal_fails_closed_before_acp():
    manager = FakeACPManager()
    adapter = OlympusRuntimeAdapter(manager, project_id=PROJECT, enabled=True)
    admitted = plan()
    substituted = proposal(objective="substituted objective")
    projection = HarmoniaProjection(
        1,
        (HarmoniaTask(substituted, TaskState.READY, WORKER_A, 0, ()),),
    )
    tampered = HarmoniaPlan(admitted.admissions, admitted.assignments, (), projection)

    receipts = await adapter.dispatch(tampered, project_root="/tmp/project-a")

    assert receipts[0].status is RuntimeStatus.REJECTED
    assert receipts[0].reason == "invalid_plan"
    assert manager.calls == []


@async_test
async def test_unbound_admission_and_cross_project_principal_fail_closed():
    manager = FakeACPManager()
    adapter = OlympusRuntimeAdapter(manager, project_id=PROJECT, enabled=True)
    admitted = plan()
    unbound = HarmoniaPlan(
        (AdmissionDecision("task-a", AdmissionStatus.ADMITTED, ()),),
        admitted.assignments,
        (),
        admitted.projection,
    )
    other = Principal("project-b", "instance-a", "hefesto")
    cross_project = plan(participants=(other,))

    unbound_receipts = await adapter.dispatch(unbound, project_root="/tmp/project-a")
    cross_receipts = await adapter.dispatch(cross_project, project_root="/tmp/project-a")

    assert unbound_receipts[0].reason == "invalid_plan"
    assert cross_receipts[0].reason == "invalid_plan"
    assert manager.calls == []


@async_test
async def test_concurrent_duplicate_dispatch_reserves_before_first_await():
    manager = BlockingACPManager()
    adapter = OlympusRuntimeAdapter(manager, project_id=PROJECT, enabled=True)
    first = asyncio.create_task(adapter.dispatch(plan(), project_root="/tmp/project-a"))
    await manager.send_started.wait()

    duplicate = await adapter.dispatch(plan(), project_root="/tmp/project-a")
    manager.send_release.set()
    original = await first

    assert original[0].status is RuntimeStatus.SENT
    assert duplicate[0].status is RuntimeStatus.REPLAYED
    assert [call[0] for call in manager.calls] == ["spawn_agent", "send_message"]


@async_test
async def test_distinct_canonical_project_roots_have_distinct_replay_identity():
    manager = FakeACPManager()
    adapter = OlympusRuntimeAdapter(manager, project_id=PROJECT, enabled=True)

    first = await adapter.dispatch(plan(), project_root="/tmp/worktree-a")
    second = await adapter.dispatch(plan(), project_root="/tmp/worktree-b")

    assert first[0].status is RuntimeStatus.SENT
    assert second[0].status is RuntimeStatus.SENT
    assert first[0].session_id != second[0].session_id
    assert [call[0] for call in manager.calls] == [
        "spawn_agent",
        "send_message",
        "spawn_agent",
        "send_message",
    ]


@async_test
async def test_poll_is_technical_observation_never_semantic_completion():
    manager = FakeACPManager()
    adapter = OlympusRuntimeAdapter(manager, project_id=PROJECT, enabled=True)
    receipt = (await adapter.dispatch(plan(), project_root="/tmp/project-a"))[0]

    observation = await adapter.observe("task-a", WORKER_A, project_root="/tmp/project-a")

    assert observation.session_id == receipt.session_id
    assert observation.technical_status == "completed"
    assert observation.semantic_complete is False
    assert observation.progress["last_turn"] == "technical output"


def test_adapter_exposes_no_cancel_shutdown_or_process_ownership_surface():
    adapter = OlympusRuntimeAdapter(FakeACPManager(), project_id=PROJECT)
    source = inspect.getsource(type(adapter))

    assert not hasattr(adapter, "cancel")
    assert not hasattr(adapter, "shutdown_agent")
    assert ".agents" not in source
    assert ".sessions" not in source
    assert "_spawn" not in source
    assert "subprocess" not in source
