from __future__ import annotations

import asyncio
import copy
import json
from pathlib import Path

import pytest
from test_harmonia_lease_lifecycle import TerminalObservation, event_payloads, write_result_artifact

from olympus_v3.config_loader import CoordinationConfig
from olympus_v3.coordination import Result, TaskState
from olympus_v3.coordination.closure import CompletionState
from olympus_v3.coordination.harmonia_contract import InvalidHarmoniaRequest, parse_harmonia_request
from olympus_v3.coordination.harmonia_runtime import ProjectRuntimeRegistry, StaticCoordinationKeyProvider
from olympus_v3.coordination.harmonia_service import HarmoniaService


def fixed_payload(root: Path) -> dict:
    contract = {
        "objective": "fixed A to B",
        "expected_outcome": "closed",
        "included_scopes": ["src"],
        "excluded_scopes": [],
        "time_seconds": 10,
        "model_budget": 10,
        "qa_reserve": 1,
        "recovery_reserve": 1,
        "escalation_conditions": ["ambiguity"],
        "tasks": [
            {"task_id": "task-a", "worker": "hefesto", "worker_permissions": ["read"], "prerequisites": []},
            {"task_id": "task-b", "worker": "ictinus", "worker_permissions": ["verify"], "prerequisites": ["task-a"]},
        ],
    }
    return {
        "action": "start",
        "project_root": str(root),
        "request_id": "fixed-gate-b",
        "contract": contract,
        "plan_revision": 1,
        "snapshot_digest": "sha256:" + "a" * 64,
    }


def test_start_accepts_exactly_one_fixed_two_task_contract(tmp_path):
    root = tmp_path / "project"
    root.mkdir()

    request = parse_harmonia_request(fixed_payload(root))

    assert tuple(task.task_id for task in request.contract.tasks) == ("task-a", "task-b")


@pytest.mark.parametrize("mutation", [
    lambda payload: payload["contract"]["tasks"].append(payload["contract"]["tasks"][0]),
    lambda payload: payload["contract"]["tasks"][1].update(prerequisites=[]),
    lambda payload: payload["contract"]["tasks"][0].update(worker="ictinus"),
    lambda payload: payload["contract"]["tasks"][1].update(task_id="task-a"),
    lambda payload: payload["contract"]["tasks"][1].pop("worker_permissions"),
    lambda payload: payload["contract"]["tasks"][1].update(worker="harmonia"),
])
def test_fixed_contract_rejects_topology_mutations(tmp_path, mutation):
    root = tmp_path / "project"
    root.mkdir()
    payload = fixed_payload(root)
    mutation(payload)
    with pytest.raises(InvalidHarmoniaRequest):
        parse_harmonia_request(payload)


class Manager:
    def __init__(self):
        self.sessions = set()
        self.calls = []

    async def spawn_agent(self, *, agent_name, session_id, project_root):
        self.calls.append(("spawn", agent_name, session_id))
        self.sessions.add(session_id)
        return session_id

    async def send_message(self, session_id, prompt):
        self.calls.append(("send", session_id))

    async def poll(self, session_id):
        return {"status": "working"}

    async def close(self, session_id, *, terminal_status):
        self.calls.append(("close", session_id))

    async def cleanup_persisted(self, session_id, *, terminal_status, project_id):
        assert session_id in self.sessions
        return {
            "status": terminal_status,
            "project_id": project_id,
            "acp_session_id": session_id,
            "survivors": {
                "logical_manager_session": False,
                "acp_mapping": False,
                "prompt_task": False,
                "pid_session_mapping": False,
            },
        }


def test_fixed_start_persists_b_blocked_and_binds_a(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    config = CoordinationConfig(True, "legacy", ("legacy", "kernel-single-task"), (str(root),), 1)
    registry = ProjectRuntimeRegistry(tmp_path / "home", Manager(), StaticCoordinationKeyProvider(b"w" * 32, b"i" * 32))
    service = HarmoniaService(aether_home=tmp_path / "home", config=config, registry=registry, discovered_workers={"hefesto", "ictinus"})

    result = asyncio.run(service.handle(fixed_payload(root)))

    assert result["ok"] is True
    assert result["task_id"] == "task-a"
    assert {row["task_id"]: row["state"] for row in result["tasks"]} == {"task-a": "running", "task-b": "blocked"}
    assert result["bindings"] == {"task-a": "hefesto", "task-b": "ictinus"}


def test_fixed_start_replay_is_exact_and_changed_topology_conflicts(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    config = CoordinationConfig(True, "legacy", ("legacy", "kernel-single-task"), (str(root),), 1)
    manager = Manager()
    registry = ProjectRuntimeRegistry(
        tmp_path / "home", manager, StaticCoordinationKeyProvider(b"w" * 32, b"i" * 32)
    )
    service = HarmoniaService(
        aether_home=tmp_path / "home",
        config=config,
        registry=registry,
        discovered_workers={"hefesto", "ictinus"},
    )
    request = fixed_payload(root)

    async def scenario():
        first = await service.handle(request)
        replay = await service.handle(copy.deepcopy(request))
        changed = copy.deepcopy(request)
        changed["contract"]["tasks"][1]["worker_permissions"] = ["verify", "review"]
        conflict = await service.handle(changed)
        context = await registry.get_or_create(root)
        run_count = sum(event["kind"] == "run.created" for event in context.ledger.events())
        await registry.close()
        return first, replay, conflict, run_count

    first, replay, conflict, run_count = asyncio.run(scenario())
    assert first["run_id"] == replay["run_id"]
    assert conflict["ok"] is False
    assert run_count == 1


def test_unknown_fixed_worker_rejects_before_durable_run_creation(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    config = CoordinationConfig(True, "legacy", ("legacy", "kernel-single-task"), (str(root),), 1)
    registry = ProjectRuntimeRegistry(
        tmp_path / "home", Manager(), StaticCoordinationKeyProvider(b"w" * 32, b"i" * 32)
    )
    service = HarmoniaService(
        aether_home=tmp_path / "home",
        config=config,
        registry=registry,
        discovered_workers={"hefesto"},
    )

    result = asyncio.run(service.handle(fixed_payload(root)))

    assert result["ok"] is False
    assert not list((tmp_path / "home").rglob("*.sqlite"))


def test_fixed_public_path_closes_a_and_auto_stages_b_once(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    config = CoordinationConfig(True, "legacy", ("legacy", "kernel-single-task"), (str(root),), 1)
    manager = Manager()
    registry = ProjectRuntimeRegistry(
        tmp_path / "home", manager, StaticCoordinationKeyProvider(b"w" * 32, b"i" * 32)
    )
    service = HarmoniaService(
        aether_home=tmp_path / "home",
        config=config,
        registry=registry,
        discovered_workers={"hefesto", "ictinus"},
    )

    async def scenario():
        started = await service.handle(fixed_payload(root))
        context = await registry.get_or_create(root)
        source_stage = next(
            payload
            for payload in event_payloads(context.ledger, "dispatch.staged")
            if payload["task_id"] == "task-a"
        )
        authority = context.dispatcher._envelope(source_stage).authority
        binding = next(
            payload
            for payload in event_payloads(context.ledger, "session.bound")
            if payload["message_id"] == authority.message_id
        )
        context.dispatcher.record_terminal_with(
            authority,
            TerminalObservation(
                "completed",
                authority.logical_session,
                binding["acp_session_id"],
                authority.message_id,
            ),
        )
        write_result_artifact(authority, binding["acp_session_id"])
        assert context.dispatcher.record_evidence_with(authority) is Result.APPLIED
        assert context.runtime.task(started["run_id"], "task-b").state is TaskState.PROPOSED
        context.runtime.request_close(
            authority=authority,
            proposed_state=CompletionState.COMPLETED,
            command_id="close-fixed-public-a",
        )
        assert (await context.dispatcher.cleanup_once())["outcome"] == "completed"
        assert (await context.dispatcher.finalize_close())["state"] == TaskState.CLOSED.value
        successor_stages = [
            payload
            for payload in event_payloads(context.ledger, "dispatch.staged")
            if payload["task_id"] == "task-b"
        ]
        status = await service.handle(
            {"action": "status", "project_root": str(root), "run_id": started["run_id"]}
        )
        await context._stage_fixed_successors()
        replay_stages = [
            payload
            for payload in event_payloads(context.ledger, "dispatch.staged")
            if payload["task_id"] == "task-b"
        ]
        await registry.close()
        return status, successor_stages, replay_stages

    status, successor_stages, replay_stages = asyncio.run(scenario())
    assert len(successor_stages) == len(replay_stages) == 1
    assert successor_stages[0]["agent_name"] == "ictinus"
    assert successor_stages[0]["handoff"]["source_task_id"] == "task-a"
    assert {row["task_id"]: row["state"] for row in status["tasks"]} == {
        "task-a": "closed",
        "task-b": "running",
    }
    assert status["bindings"] == {"task-a": "hefesto", "task-b": "ictinus"}
    public = json.dumps(status)
    assert "lease_token" not in public
    assert '"result"' not in public
    assert [call[1] for call in manager.calls if call[0] == "spawn"] == ["hefesto"]


def test_fixed_successor_auto_stages_after_runtime_registry_restart(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    home = tmp_path / "home"
    keys = StaticCoordinationKeyProvider(b"w" * 32, b"i" * 32)
    config = CoordinationConfig(True, "legacy", ("legacy", "kernel-single-task"), (str(root),), 1)
    manager = Manager()
    registry = ProjectRuntimeRegistry(home, manager, keys)
    service = HarmoniaService(
        aether_home=home,
        config=config,
        registry=registry,
        discovered_workers={"hefesto", "ictinus"},
    )

    async def scenario():
        started = await service.handle(fixed_payload(root))
        context = await registry.get_or_create(root)
        source_stage = next(
            payload
            for payload in event_payloads(context.ledger, "dispatch.staged")
            if payload["task_id"] == "task-a"
        )
        authority = context.dispatcher._envelope(source_stage).authority
        binding = next(
            payload
            for payload in event_payloads(context.ledger, "session.bound")
            if payload["message_id"] == authority.message_id
        )
        context.dispatcher.record_terminal_with(
            authority,
            TerminalObservation(
                "completed",
                authority.logical_session,
                binding["acp_session_id"],
                authority.message_id,
            ),
        )
        write_result_artifact(authority, binding["acp_session_id"])
        assert context.dispatcher.record_evidence_with(authority) is Result.APPLIED
        context.runtime.request_close(
            authority=authority,
            proposed_state=CompletionState.COMPLETED,
            command_id="close-fixed-restart-a",
        )
        assert (await context.dispatcher.cleanup_once())["outcome"] == "completed"
        context.dispatcher._after_close = None
        assert (await context.dispatcher.finalize_close())["state"] == TaskState.CLOSED.value
        assert context.runtime.task(started["run_id"], "task-b").state is TaskState.PROPOSED
        assert not [
            payload
            for payload in event_payloads(context.ledger, "dispatch.staged")
            if payload["task_id"] == "task-b"
        ]
        assert await registry.close() == ()

        restarted_registry = ProjectRuntimeRegistry(home, manager, keys)
        restarted = await restarted_registry.get_or_create(root)
        stages = [
            payload
            for payload in event_payloads(restarted.ledger, "dispatch.staged")
            if payload["task_id"] == "task-b"
        ]
        state = restarted.runtime.task(started["run_id"], "task-b").state
        await restarted._stage_fixed_successors()
        replay_count = len(
            [
                payload
                for payload in event_payloads(restarted.ledger, "dispatch.staged")
                if payload["task_id"] == "task-b"
            ]
        )
        await restarted_registry.close()
        return stages, state, replay_count

    stages, state, replay_count = asyncio.run(scenario())
    assert len(stages) == replay_count == 1
    assert stages[0]["agent_name"] == "ictinus"
    assert state is TaskState.RUNNING
