import asyncio
import json
from dataclasses import replace

import pytest

from olympus_v3.coordination import OlympusRuntimeAdapter, RuntimeStatus, compile_snake_manifest
from olympus_v3.coordination.pilot import PilotCoordinator


class Manager:
    def __init__(self):
        self.calls = []

    async def spawn_agent(self, agent_name, session_id=None, project_root=None):
        self.calls.append(("spawn", agent_name, session_id, project_root))
        return session_id

    async def send_message(self, session_id, message):
        self.calls.append(("send", session_id, message))

    async def poll(self, session_id):
        self.calls.append(("poll", session_id))
        return {"status": "active"}

    async def close(self, session_id, terminal_status=None):
        self.calls.append(("close", session_id, terminal_status))


def envelope(manifest, task, session_id):
    coordinator = PilotCoordinator.__new__(PilotCoordinator)
    coordinator.manifest = manifest
    return coordinator._envelope(task, 1, session_id)


def test_pilot_adapter_remains_default_off():
    manager = Manager()
    adapter = OlympusRuntimeAdapter(manager, project_id="snake-r8")
    manifest = compile_snake_manifest(root=__import__("pathlib").Path("/tmp/snake-r8"))
    task = manifest.task("snake-spec")
    sid = PilotCoordinator.session_id(manifest, task.task_id, 1)
    receipt = asyncio.run(
        adapter.dispatch_pilot_task(
            task, manifest=manifest, session_id=sid, project_root=manifest.root, envelope=envelope(manifest, task, sid)
        )
    )
    assert receipt.status is RuntimeStatus.DISABLED
    assert manager.calls == []


def test_pilot_adapter_dispatches_exact_bound_prompt_and_replays():
    manager = Manager()
    adapter = OlympusRuntimeAdapter(manager, project_id="snake-r8", enabled=True)
    manifest = compile_snake_manifest(root=__import__("pathlib").Path("/tmp/snake-r8"))
    task = manifest.task("snake-spec")
    sid = PilotCoordinator.session_id(manifest, task.task_id, 1)
    bound = envelope(manifest, task, sid)
    first = asyncio.run(
        adapter.dispatch_pilot_task(task, manifest=manifest, session_id=sid, project_root=manifest.root, envelope=bound)
    )
    replay = asyncio.run(
        adapter.dispatch_pilot_task(task, manifest=manifest, session_id=sid, project_root=manifest.root, envelope=bound)
    )
    assert first.status is RuntimeStatus.SENT
    assert replay.status is RuntimeStatus.REPLAYED
    assert [call[0] for call in manager.calls] == ["spawn", "send"]
    prompt = json.loads(manager.calls[1][2])
    assert prompt["kind"] == "aether.snake.task.v1"
    assert prompt["manifest_hash"] == manifest.manifest_hash
    assert prompt["participant"]["actor_id"] == "daedalus"


def test_pilot_adapter_rejects_tampered_envelope_before_acp():
    manager = Manager()
    adapter = OlympusRuntimeAdapter(manager, project_id="snake-r8", enabled=True)
    manifest = compile_snake_manifest(root=__import__("pathlib").Path("/tmp/snake-r8"))
    task = manifest.task("snake-spec")
    sid = PilotCoordinator.session_id(manifest, task.task_id, 1)
    bound = envelope(manifest, task, sid) | {"manifest_hash": "0" * 64}
    receipt = asyncio.run(
        adapter.dispatch_pilot_task(task, manifest=manifest, session_id=sid, project_root=manifest.root, envelope=bound)
    )
    assert receipt.status is RuntimeStatus.REJECTED
    assert manager.calls == []


def test_pilot_observation_can_recover_after_adapter_restart():
    manager = Manager()
    manifest = compile_snake_manifest(root=__import__("pathlib").Path("/tmp/snake-r8"))
    task = manifest.task("snake-spec")
    sid = PilotCoordinator.session_id(manifest, task.task_id, 1)
    adapter = OlympusRuntimeAdapter(manager, project_id="snake-r8", enabled=True)
    observation = asyncio.run(adapter.observe_pilot_task(task, session_id=sid, project_root=manifest.root))
    assert observation.session_id == sid
    assert observation.semantic_complete is False
    assert manager.calls == [("poll", sid)]


def test_pilot_adapter_rejects_forged_task_against_authoritative_manifest():
    manager = Manager()
    adapter = OlympusRuntimeAdapter(manager, project_id="snake-r8", enabled=True)
    manifest = compile_snake_manifest(root=__import__("pathlib").Path("/tmp/snake-r8"))
    original = manifest.task("snake-spec")
    forged = replace(original, objective="attacker objective")
    sid = PilotCoordinator.session_id(manifest, original.task_id, 1)
    receipt = asyncio.run(
        adapter.dispatch_pilot_task(
            forged,
            manifest=manifest,
            session_id=sid,
            project_root=manifest.root,
            envelope=envelope(manifest, forged, sid),
        )
    )
    assert receipt.status is RuntimeStatus.REJECTED
    assert manager.calls == []


def test_pilot_adapter_closes_actual_session_on_identity_mismatch():
    class MismatchManager(Manager):
        async def spawn_agent(self, agent_name, session_id=None, project_root=None):
            self.calls.append(("spawn", agent_name, session_id, project_root))
            return "actual-session"

    manager = MismatchManager()
    adapter = OlympusRuntimeAdapter(manager, project_id="snake-r8", enabled=True)
    manifest = compile_snake_manifest(root=__import__("pathlib").Path("/tmp/snake-r8"))
    task = manifest.task("snake-spec")
    sid = PilotCoordinator.session_id(manifest, task.task_id, 1)
    receipt = asyncio.run(
        adapter.dispatch_pilot_task(
            task,
            manifest=manifest,
            session_id=sid,
            project_root=manifest.root,
            envelope=envelope(manifest, task, sid),
        )
    )
    assert receipt.status is RuntimeStatus.ERROR
    assert ("close", "actual-session", "error") in manager.calls


def test_failed_session_cleanup_propagates_cancellation_instead_of_hanging():
    class HangingCloseManager(Manager):
        async def close(self, session_id, terminal_status=None):
            await asyncio.Event().wait()

    manager = HangingCloseManager()
    adapter = OlympusRuntimeAdapter(manager, project_id="snake-r8", enabled=True)
    with pytest.raises(TimeoutError):
        asyncio.run(asyncio.wait_for(adapter._close_failed_session("session"), timeout=0.01))
