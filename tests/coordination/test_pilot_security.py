import asyncio
import hashlib
import sqlite3
from dataclasses import replace

import pytest

from olympus_v3.coordination import PilotCoordinator, PilotError, PilotStore, compile_snake_manifest
from olympus_v3.coordination.pilot_evidence import encode_result, parse_and_verify_result
from olympus_v3.coordination.pilot_model import resolve_inside, validate_pilot_root


def test_canonical_root_and_symlink_escape_are_rejected(tmp_path):
    root = tmp_path.resolve()
    assert validate_pilot_root(root, expected_root=root) == root
    with pytest.raises(PilotError, match="fixed pilot root"):
        validate_pilot_root(root, expected_root=root / "other")
    outside = tmp_path.parent / "outside"
    outside.mkdir(exist_ok=True)
    root.mkdir(exist_ok=True)
    (root / "escape").symlink_to(outside, target_is_directory=True)
    with pytest.raises(PilotError, match="escape"):
        resolve_inside(root, "escape/file.txt")


def test_store_manifest_schema_and_event_corruption_fail_closed(tmp_path):
    root = tmp_path.resolve()
    manifest = compile_snake_manifest(root=root)
    path = tmp_path.parent / f"{tmp_path.name}-control" / "pilot.db"
    store = PilotStore(path, control_root=path.parent)
    store.install(manifest)
    store.db.execute("UPDATE events SET payload='tampered' WHERE sequence=1")
    with pytest.raises(PilotError, match="event corruption"):
        store.verify_integrity()
    store.close()
    connection = sqlite3.connect(path)
    connection.execute("UPDATE meta SET value='99' WHERE key='schema_version'")
    connection.commit()
    connection.close()
    with pytest.raises(PilotError, match="schema mismatch"):
        PilotStore(path, control_root=path.parent)


def test_read_only_review_cannot_report_changes_and_blocking_finding_cannot_accept(tmp_path):
    root = tmp_path.resolve()
    manifest = compile_snake_manifest(root=root)
    task = manifest.task("snake-review")
    session_id = PilotCoordinator.session_id(manifest, task.task_id, 1)
    base = {
        "pilot_id": manifest.pilot_id,
        "task_id": task.task_id,
        "attempt": 1,
        "session_id": session_id,
        "status": "completed",
        "changed_paths": [],
        "artifact_hashes": {},
        "verification": [{"command": "read-only-review", "exit_code": 0}],
        "findings": [],
        "recommendation": "accept",
    }
    changed = base | {"changed_paths": ["README.md"], "artifact_hashes": {"README.md": "0" * 64}}
    with pytest.raises(PilotError, match="read-only"):
        parse_and_verify_result(
            encode_result(**changed), task=task, manifest=manifest, attempt=1, session_id=session_id
        )
    blocked = base | {"findings": [{"blocking": True}], "recommendation": "accept"}
    with pytest.raises(PilotError, match="blocking"):
        parse_and_verify_result(
            encode_result(**blocked), task=task, manifest=manifest, attempt=1, session_id=session_id
        )


def test_deadline_and_step_budget_are_bounded(tmp_path):
    class IdleAdapter:
        async def dispatch_pilot_task(self, *args, **kwargs):
            raise AssertionError("deadline must prevent dispatch")

    root = tmp_path.resolve()
    manifest = compile_snake_manifest(root=root)
    store = PilotStore(
        tmp_path.parent / f"{tmp_path.name}-control" / "pilot.db",
        control_root=tmp_path.parent / f"{tmp_path.name}-control",
    )
    coordinator = PilotCoordinator(IdleAdapter(), store, manifest, clock=lambda: 10)
    with pytest.raises(PilotError, match="run bound"):
        asyncio.run(coordinator.run(deadline_seconds=0))
    store.close()


def test_result_schema_rejects_extra_fields_and_oversized_or_wrong_session(tmp_path):
    root = tmp_path.resolve()
    manifest = compile_snake_manifest(root=root)
    task = manifest.task("snake-review")
    session = PilotCoordinator.session_id(manifest, task.task_id, 1)
    payload = {
        "pilot_id": manifest.pilot_id,
        "task_id": task.task_id,
        "attempt": 1,
        "session_id": session,
        "status": "completed",
        "changed_paths": [],
        "artifact_hashes": {},
        "verification": [],
        "findings": [],
        "recommendation": "accept",
    }
    with pytest.raises(PilotError, match="schema"):
        parse_and_verify_result(
            encode_result(**(payload | {"extra": 1})), task=task, manifest=manifest, attempt=1, session_id=session
        )
    with pytest.raises(PilotError, match="binding"):
        parse_and_verify_result(encode_result(**payload), task=task, manifest=manifest, attempt=1, session_id="other")


def test_manifest_hash_detects_task_mutation(tmp_path):
    manifest = compile_snake_manifest(root=tmp_path.resolve())
    tasks = list(manifest.tasks)
    tasks[1] = replace(tasks[1], objective="tampered")
    changed = replace(manifest, tasks=tuple(tasks), manifest_hash="")
    assert changed.manifest_hash != manifest.manifest_hash
    store = PilotStore(
        tmp_path.parent / f"{tmp_path.name}-control" / "pilot.db",
        control_root=tmp_path.parent / f"{tmp_path.name}-control",
    )
    store.install(manifest)
    with pytest.raises(PilotError, match="manifest mismatch"):
        store.verify_manifest(changed)
    store.close()


def test_failed_or_nonzero_result_cannot_semantically_accept(tmp_path):
    root = tmp_path.resolve()
    manifest = compile_snake_manifest(root=root)
    task = manifest.task("snake-review")
    session = PilotCoordinator.session_id(manifest, task.task_id, 1)
    base = {
        "pilot_id": manifest.pilot_id,
        "task_id": task.task_id,
        "attempt": 1,
        "session_id": session,
        "changed_paths": [],
        "artifact_hashes": {},
        "verification": [{"command": "review", "exit_code": 0}],
        "findings": [],
        "recommendation": "accept",
    }
    with pytest.raises(PilotError, match="semantic"):
        parse_and_verify_result(
            encode_result(**(base | {"status": "failed"})),
            task=task,
            manifest=manifest,
            attempt=1,
            session_id=session,
        )
    with pytest.raises(PilotError, match="verification"):
        parse_and_verify_result(
            encode_result(
                **(
                    base
                    | {
                        "status": "completed",
                        "verification": [{"command": "review", "exit_code": 1}],
                    }
                )
            ),
            task=task,
            manifest=manifest,
            attempt=1,
            session_id=session,
        )


def test_store_refuses_unverified_direct_promotion(tmp_path):
    root = tmp_path.resolve()
    manifest = compile_snake_manifest(root=root)
    store = PilotStore(
        tmp_path.parent / f"{tmp_path.name}-control" / "pilot.db",
        control_root=tmp_path.parent / f"{tmp_path.name}-control",
    )
    store.install(manifest)
    task = manifest.task("snake-spec")
    session = PilotCoordinator.session_id(manifest, task.task_id, 1)
    store.record_intent(task.task_id, session)
    store.mark_running(task.task_id, 1, session)
    with pytest.raises(PilotError, match="verified"):
        store._accept_verified_evidence(task.task_id, 1, {"recommendation": "accept"}, verified=False)
    assert store.accepted() == ()
    store.close()


def test_external_dispatch_timeout_is_bounded(tmp_path):
    class HangingAdapter:
        async def dispatch_pilot_task(self, *args, **kwargs):
            await asyncio.Event().wait()

    root = tmp_path.resolve()
    manifest = compile_snake_manifest(root=root)
    store = PilotStore(
        tmp_path.parent / f"{tmp_path.name}-control" / "pilot.db",
        control_root=tmp_path.parent / f"{tmp_path.name}-control",
    )
    coordinator = PilotCoordinator(HangingAdapter(), store, manifest, external_timeout_seconds=0.01)
    with pytest.raises(TimeoutError):
        asyncio.run(coordinator.step())
    assert store.task("snake-spec")["state"] == "blocked"
    store.close()


def test_store_rejects_product_root_placement(tmp_path):
    root = tmp_path.resolve()
    with pytest.raises(PilotError, match="outside control"):
        PilotStore(root / "pilot.db", control_root=root.parent / "control")


def test_unhashable_changed_path_normalizes_to_pilot_error(tmp_path):
    root = tmp_path.resolve()
    manifest = compile_snake_manifest(root=root)
    task = manifest.task("snake-spec")
    session = PilotCoordinator.session_id(manifest, task.task_id, 1)
    payload = {
        "pilot_id": manifest.pilot_id,
        "task_id": task.task_id,
        "attempt": 1,
        "session_id": session,
        "status": "completed",
        "changed_paths": [[]],
        "artifact_hashes": {},
        "verification": [{"command": "review", "exit_code": 0}],
        "findings": [],
        "recommendation": "accept",
    }
    with pytest.raises(PilotError, match="changed paths"):
        parse_and_verify_result(
            encode_result(**payload),
            task=task,
            manifest=manifest,
            attempt=1,
            session_id=session,
        )


def test_changed_path_must_be_inside_declared_task_scope(tmp_path):
    root = tmp_path.resolve()
    manifest = compile_snake_manifest(root=root)
    task = manifest.task("snake-spec")
    session = PilotCoordinator.session_id(manifest, task.task_id, 1)
    design = root / "DESIGN.md"
    design.write_text("valid required design")
    forbidden = root / "README.md"
    forbidden.write_text("outside snake-spec scope")

    payload = {
        "pilot_id": manifest.pilot_id,
        "task_id": task.task_id,
        "attempt": 1,
        "session_id": session,
        "status": "completed",
        "changed_paths": ["DESIGN.md", "README.md"],
        "artifact_hashes": {
            "DESIGN.md": hashlib.sha256(design.read_bytes()).hexdigest(),
            "README.md": hashlib.sha256(forbidden.read_bytes()).hexdigest(),
        },
        "verification": [{"command": "design-check", "exit_code": 0}],
        "findings": [],
        "recommendation": "accept",
    }
    with pytest.raises(PilotError, match="outside task scope"):
        parse_and_verify_result(
            encode_result(**payload),
            task=task,
            manifest=manifest,
            attempt=1,
            session_id=session,
        )
