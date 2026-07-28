import asyncio
import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

from olympus_v3.coordination import (
    PilotCoordinator,
    PilotError,
    PilotStore,
    RuntimeObservation,
    RuntimeReceipt,
    RuntimeStatus,
    compile_snake_manifest,
)
from olympus_v3.coordination.pilot_evidence import encode_result, parse_and_verify_result


class FakeAdapter:
    def __init__(self, root: Path, store: PilotStore):
        self.root = root
        self.store = store
        self.dispatches = []
        self.outputs = {}

    async def dispatch_pilot_task(self, task, *, manifest, session_id, project_root, envelope):
        assert self.store.task(task.task_id)["state"] == "intent_recorded"
        assert project_root == str(self.root)
        self.dispatches.append((task.task_id, session_id, envelope))
        return RuntimeReceipt(task.task_id, envelope["participant"], session_id, RuntimeStatus.SENT)

    async def observe_pilot_task(self, task, *, session_id, project_root):
        output = self.outputs.get(task.task_id)
        status = "completed" if output else "active"
        return RuntimeObservation(
            task.task_id,
            self.dispatches[-1][2]["participant"],
            session_id,
            status,
            {"status": status, "last_turn": output or ""},
        )


def artifact(root: Path, relative: str, content: str = "ok") -> str:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def result(root, manifest, task_id, attempt=1, recommendation="accept"):
    task = manifest.task(task_id)
    hashes = {rel: artifact(root, rel, task_id) for rel in task.required_artifacts}
    return encode_result(
        pilot_id=manifest.pilot_id,
        task_id=task_id,
        attempt=attempt,
        session_id=PilotCoordinator.session_id(manifest, task_id, attempt),
        status="completed",
        changed_paths=list(hashes),
        artifact_hashes=hashes,
        verification=[{"command": "bounded-local-check", "exit_code": 0}],
        findings=[],
        recommendation=recommendation,
    )


def test_fixed_graph_runs_in_dependency_order_with_independent_closure(tmp_path):
    root = tmp_path.resolve()
    manifest = compile_snake_manifest(root=root)
    store = PilotStore(
        tmp_path.parent / f"{tmp_path.name}-control" / "pilot.db",
        control_root=tmp_path.parent / f"{tmp_path.name}-control",
    )
    adapter = FakeAdapter(root, store)
    coordinator = PilotCoordinator(adapter, store, manifest)
    try:
        for task_id in ("snake-spec", "snake-build", "snake-verify", "snake-review", "snake-closure"):
            asyncio.run(coordinator.step())
            adapter.outputs[task_id] = result(root, manifest, task_id)
            asyncio.run(coordinator.step())
        assert asyncio.run(coordinator.run(max_steps=1)) is True
        assert [item[0] for item in adapter.dispatches] == list(
            manifest.task(task_id).task_id
            for task_id in ("snake-spec", "snake-build", "snake-verify", "snake-review", "snake-closure")
        )
        assert len(store.accepted()) == 5
    finally:
        store.close()


def test_restart_observes_recorded_session_without_redispatch(tmp_path):
    root = tmp_path.resolve()
    manifest = compile_snake_manifest(root=root)
    store = PilotStore(
        tmp_path.parent / f"{tmp_path.name}-control" / "pilot.db",
        control_root=tmp_path.parent / f"{tmp_path.name}-control",
    )
    adapter = FakeAdapter(root, store)
    first = PilotCoordinator(adapter, store, manifest)
    asyncio.run(first.step())
    assert len(adapter.dispatches) == 1
    adapter.outputs["snake-spec"] = result(root, manifest, "snake-spec")
    resumed = PilotCoordinator(adapter, store, manifest)
    asyncio.run(resumed.step())
    assert len(adapter.dispatches) == 1
    assert store.accepted() == ("snake-spec",)
    store.close()


def test_read_only_snapshot_survives_coordinator_restart(tmp_path):
    root = tmp_path.resolve()
    manifest = compile_snake_manifest(root=root)
    control = tmp_path.parent / f"{tmp_path.name}-control" / "pilot.db"
    store = PilotStore(control, control_root=control.parent)
    store.install(manifest)
    for task_id in ("snake-spec", "snake-build", "snake-verify"):
        session = PilotCoordinator.session_id(manifest, task_id, 1)
        store.record_intent(task_id, session)
        store.mark_running(task_id, 1, session)
        payload = json.loads(result(root, manifest, task_id).splitlines()[1])
        store._accept_verified_evidence(task_id, 1, payload, verified=True)
    adapter = FakeAdapter(root, store)
    first = PilotCoordinator(adapter, store, manifest)
    asyncio.run(first.step())
    (root / "README.md").write_text("tampered while coordinator was down")
    adapter.outputs["snake-review"] = result(root, manifest, "snake-review")
    resumed = PilotCoordinator(adapter, store, manifest)
    with pytest.raises(PilotError, match="read-only"):
        asyncio.run(resumed.step())
    assert "snake-review" not in store.accepted()
    store.close()


def test_technical_completion_without_valid_envelope_blocks_dependency(tmp_path):
    root = tmp_path.resolve()
    manifest = compile_snake_manifest(root=root)
    store = PilotStore(
        tmp_path.parent / f"{tmp_path.name}-control" / "pilot.db",
        control_root=tmp_path.parent / f"{tmp_path.name}-control",
    )
    adapter = FakeAdapter(root, store)
    coordinator = PilotCoordinator(adapter, store, manifest)
    asyncio.run(coordinator.step())
    adapter.outputs["snake-spec"] = "completed"
    with pytest.raises(PilotError, match="result envelope"):
        asyncio.run(coordinator.step())
    assert store.accepted() == ()
    assert len(adapter.dispatches) == 1
    store.close()


def test_result_binding_hash_and_path_tampering_fail_closed(tmp_path):
    root = tmp_path.resolve()
    manifest = compile_snake_manifest(root=root)
    task = manifest.task("snake-spec")
    text = result(root, manifest, task.task_id)
    with pytest.raises(PilotError):
        parse_and_verify_result(
            text.replace('"attempt":1', '"attempt":2'),
            task=task,
            manifest=manifest,
            attempt=1,
            session_id=PilotCoordinator.session_id(manifest, task.task_id, 1),
        )
    data = json.loads(text.splitlines()[1])
    data["artifact_hashes"]["DESIGN.md"] = "0" * 64
    with pytest.raises(PilotError, match="hash"):
        parse_and_verify_result(
            encode_result(**data), task=task, manifest=manifest, attempt=1, session_id=data["session_id"]
        )


def test_manifest_mutation_and_self_review_are_rejected(tmp_path):
    manifest = compile_snake_manifest(root=tmp_path.resolve())
    with pytest.raises(PilotError):
        replace(manifest, generation=2)
    tasks = list(manifest.tasks)
    tasks[3] = replace(tasks[3], assignee="hefesto")
    with pytest.raises(PilotError, match="independent"):
        replace(manifest, tasks=tuple(tasks), manifest_hash="")


def test_retry_is_bounded_and_preserves_attempt_history(tmp_path):
    root = tmp_path.resolve()
    manifest = compile_snake_manifest(root=root)
    store = PilotStore(
        tmp_path.parent / f"{tmp_path.name}-control" / "pilot.db",
        control_root=tmp_path.parent / f"{tmp_path.name}-control",
    )
    store.install(manifest)
    task = manifest.task("snake-spec")
    sid1 = PilotCoordinator.session_id(manifest, task.task_id, 1)
    assert store.record_intent(task.task_id, sid1) == 1
    store.mark_running(task.task_id, 1, sid1)
    payload = json.loads(result(root, manifest, task.task_id, recommendation="correction_required").splitlines()[1])
    store._accept_verified_evidence(task.task_id, 1, payload, verified=True)
    sid2 = PilotCoordinator.session_id(manifest, task.task_id, 2)
    assert store.record_intent(task.task_id, sid2) == 2
    store.mark_running(task.task_id, 2, sid2)
    store._accept_verified_evidence(
        task.task_id,
        2,
        payload | {"attempt": 2, "session_id": sid2},
        verified=True,
    )
    with pytest.raises(PilotError, match="attempt budget"):
        store.record_intent(task.task_id, "third")
    store.close()
