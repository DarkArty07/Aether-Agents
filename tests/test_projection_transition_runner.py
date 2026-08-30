"""Isolated contract tests for the release-local projection transition runner."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest
from observation_helpers import PROJECT_ID, complete_trace

from aether_agents.observation.capture.journal import JournalWriter, list_segments
from aether_agents.observation.contracts import READ_MODEL_SCHEMA
from aether_agents.observation.storage import ReadModel
from aether_agents.paths import ObservationPaths, atomic_private_write

_EXPECTED_UNSET = object()


def _write_trace(state_root: Path) -> ObservationPaths:
    paths = ObservationPaths.for_project(PROJECT_ID, root=state_root)
    fixture = complete_trace()
    writer = JournalWriter(paths=paths, producer_epoch=fixture.epoch)
    writer.open()
    try:
        for event in fixture.events:
            assert writer.append(event).accepted
    finally:
        writer.close()
    return paths


def _journal_digests(paths: ObservationPaths) -> dict[str, str]:
    return {
        segment.path.relative_to(paths.journal).as_posix(): hashlib.sha256(
            segment.path.read_bytes()
        ).hexdigest()
        for segment in list_segments(paths)
    }


def _request(
    state_root: Path,
    operation: str,
    *,
    expected_pointers: dict[str, str | None] | None | object = _EXPECTED_UNSET,
) -> dict[str, object]:
    value: dict[str, object] = {
        "operation": operation,
        "state_root": str(state_root),
        "expected_schema": READ_MODEL_SCHEMA,
    }
    if expected_pointers is not _EXPECTED_UNSET:
        value["expected_pointers"] = expected_pointers
    return value


def test_prepare_reingests_own_schema_without_publishing_or_touching_foreign_state(
    tmp_path: Path,
) -> None:
    from aether_agents.observation.projection_transition import run_transition

    state_root = tmp_path / "state" / "aether"
    paths = _write_trace(state_root)
    before = _journal_digests(paths)

    future_name = "aether.observation.projection.v999.sqlite3"
    future_bytes = b"opaque-future-projection"
    future = paths.projections / future_name
    future.write_bytes(future_bytes)
    atomic_private_write(paths.projection_pointer, (future_name + "\n").encode("ascii"))

    foreign = state_root / "observations" / "projects" / "not-a-project-uuid"
    foreign.mkdir(mode=0o700)
    sentinel = foreign / "opaque.bin"
    sentinel.write_bytes(b"foreign-state")

    result = run_transition(_request(state_root, "prepare"))

    assert result == {
        "operation": "prepare",
        "target_schema": READ_MODEL_SCHEMA,
        "project_count": 1,
        "projects": [
            {
                "project_id": PROJECT_ID,
                "expected_pointer": future_name,
                "segments_seen": 1,
                "lines_seen": len(complete_trace().events),
                "events_inserted": len(complete_trace().events),
                "duplicate_events": 0,
                "quarantined_events": 0,
                "corrupt_segments": 0,
                "unclean_epochs": 0,
            }
        ],
    }
    assert paths.projection_pointer.read_text(encoding="ascii") == future_name + "\n"
    assert future.read_bytes() == future_bytes
    assert _journal_digests(paths) == before
    assert sentinel.read_bytes() == b"foreign-state"
    assert not (foreign / "projections").exists()
    with ReadModel.open(paths) as model:
        assert model.storage_report().event_count == len(complete_trace().events)


def test_select_uses_exact_per_project_cas_and_unselects_only_own_pointer(
    tmp_path: Path,
) -> None:
    from aether_agents.observation.projection_transition import run_transition

    state_root = tmp_path / "state" / "aether"
    paths = _write_trace(state_root)
    prepared = run_transition(_request(state_root, "prepare"))
    snapshot = {
        row["project_id"]: row["expected_pointer"]
        for row in prepared["projects"]  # type: ignore[index]
    }

    selected = run_transition(_request(state_root, "select", expected_pointers=snapshot))
    own_pointer = paths.projection_db(READ_MODEL_SCHEMA).name
    assert selected == {
        "operation": "select",
        "target_schema": READ_MODEL_SCHEMA,
        "project_count": 1,
        "selected_count": 1,
        "projects": [
            {
                "project_id": PROJECT_ID,
                "previous_pointer": None,
                "selected_pointer": own_pointer,
            }
        ],
    }
    assert paths.projection_pointer.read_text(encoding="ascii") == own_pointer + "\n"

    removed = run_transition(
        _request(
            state_root,
            "unselect",
            expected_pointers=snapshot,
        )
    )
    assert removed == {
        "operation": "unselect",
        "target_schema": READ_MODEL_SCHEMA,
        "project_count": 1,
        "unselected_count": 1,
        "projects": [
            {
                "project_id": PROJECT_ID,
                "previous_pointer": own_pointer,
                "selected_pointer": None,
            }
        ],
    }
    assert not paths.projection_pointer.exists()

    future_name = "aether.observation.projection.v999.sqlite3"
    atomic_private_write(paths.projection_pointer, (future_name + "\n").encode("ascii"))
    unchanged = run_transition(
        _request(
            state_root,
            "unselect",
            expected_pointers={PROJECT_ID: future_name},
        )
    )
    assert unchanged["unselected_count"] == 0
    assert paths.projection_pointer.read_text(encoding="ascii") == future_name + "\n"


def test_select_rejects_stale_snapshot_and_project_set_drift(tmp_path: Path) -> None:
    from aether_agents.observation.projection_transition import (
        ProjectionTransitionError,
        run_transition,
    )

    state_root = tmp_path / "state" / "aether"
    paths = _write_trace(state_root)
    prepared = run_transition(_request(state_root, "prepare"))
    expected = prepared["projects"][0]["expected_pointer"]  # type: ignore[index]
    competing = "aether.observation.projection.v998.sqlite3"
    atomic_private_write(paths.projection_pointer, (competing + "\n").encode("ascii"))

    with pytest.raises(ProjectionTransitionError):
        run_transition(
            _request(
                state_root,
                "select",
                expected_pointers={PROJECT_ID: expected},
            )
        )
    assert paths.projection_pointer.read_text(encoding="ascii") == competing + "\n"

    with pytest.raises(ProjectionTransitionError):
        run_transition(_request(state_root, "select", expected_pointers={}))


def test_select_revalidates_the_prepared_projection_inode_before_publish(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import aether_agents.observation.projection_transition as transition

    state_root = tmp_path / "state" / "aether"
    paths = _write_trace(state_root)
    prepared = transition.run_transition(_request(state_root, "prepare"))
    snapshot = {row["project_id"]: row["expected_pointer"] for row in prepared["projects"]}
    original_require = transition._require_own_projection

    def unlink_after_proof(candidate: ObservationPaths) -> object:
        identity = original_require(candidate)
        for projection_file in candidate.projection_files(READ_MODEL_SCHEMA):
            projection_file.unlink(missing_ok=True)
        return identity

    monkeypatch.setattr(transition, "_require_own_projection", unlink_after_proof)

    with pytest.raises(transition.ProjectionTransitionError):
        transition.run_transition(_request(state_root, "select", expected_pointers=snapshot))
    assert not paths.projection_pointer.exists()


def test_select_never_opens_or_mutates_a_replacement_sqlite_inode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import aether_agents.observation.projection_transition as transition

    state_root = tmp_path / "state" / "aether"
    paths = _write_trace(state_root)
    prepared = transition.run_transition(_request(state_root, "prepare"))
    snapshot = {row["project_id"]: row["expected_pointer"] for row in prepared["projects"]}
    replacement = tmp_path / "replacement.sqlite3"
    connection = sqlite3.connect(replacement)
    connection.execute("CREATE TABLE opaque_sentinel (value INTEGER)")
    connection.commit()
    connection.close()
    replacement_bytes = replacement.read_bytes()
    original_require = transition._require_own_projection

    def replace_after_proof(candidate: ObservationPaths) -> tuple[int, int]:
        identity = original_require(candidate)
        for sidecar in candidate.projection_files(READ_MODEL_SCHEMA)[1:]:
            sidecar.unlink(missing_ok=True)
        os.replace(replacement, candidate.projection_db(READ_MODEL_SCHEMA))
        return identity

    monkeypatch.setattr(transition, "_require_own_projection", replace_after_proof)

    with pytest.raises(transition.ProjectionTransitionError):
        transition.run_transition(_request(state_root, "select", expected_pointers=snapshot))
    assert paths.projection_db(READ_MODEL_SCHEMA).read_bytes() == replacement_bytes
    assert not paths.projection_pointer.exists()


def test_select_revalidates_projection_inode_inside_pointer_publish_boundary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import aether_agents.observation.projection_transition as transition

    state_root = tmp_path / "state" / "aether"
    paths = _write_trace(state_root)
    prepared = transition.run_transition(_request(state_root, "prepare"))
    snapshot = {row["project_id"]: row["expected_pointer"] for row in prepared["projects"]}
    original_publish = transition.publish_projection_pointer

    def unlink_at_publish_boundary(
        candidate: ObservationPaths,
        *,
        schema: str,
        expected_active: str | None,
        expected_projection_identity: tuple[int, int] | None,
    ) -> None:
        for projection_file in candidate.projection_files(READ_MODEL_SCHEMA):
            projection_file.unlink(missing_ok=True)
        original_publish(
            candidate,
            schema=schema,
            expected_active=expected_active,
            expected_projection_identity=expected_projection_identity,
        )

    monkeypatch.setattr(
        transition,
        "publish_projection_pointer",
        unlink_at_publish_boundary,
    )

    with pytest.raises(transition.ProjectionTransitionError):
        transition.run_transition(_request(state_root, "select", expected_pointers=snapshot))
    assert not paths.projection_pointer.exists()


def test_select_revalidates_projection_inode_after_pointer_fsync(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import aether_agents.observation.projection_transition as transition
    import aether_agents.observation.storage as storage

    state_root = tmp_path / "state" / "aether"
    paths = _write_trace(state_root)
    prepared = transition.run_transition(_request(state_root, "prepare"))
    snapshot = {row["project_id"]: row["expected_pointer"] for row in prepared["projects"]}
    original_write = storage.atomic_private_write

    def write_then_unlink_projection(path: Path, data: bytes) -> None:
        original_write(path, data)
        if path == paths.projection_pointer:
            for projection_file in paths.projection_files(READ_MODEL_SCHEMA):
                projection_file.unlink(missing_ok=True)

    monkeypatch.setattr(storage, "atomic_private_write", write_then_unlink_projection)

    with pytest.raises(transition.ProjectionTransitionError):
        transition.run_transition(_request(state_root, "select", expected_pointers=snapshot))
    assert paths.projection_pointer.read_text(encoding="ascii") == (
        paths.projection_db(READ_MODEL_SCHEMA).name + "\n"
    )


@pytest.mark.skipif(os.name != "posix", reason="parent swap sabotage is POSIX-specific")
def test_pointer_read_failure_is_never_degraded_to_absence_by_path_restat(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import aether_agents.observation.projection_transition as transition

    state_root = tmp_path / "state" / "aether"
    paths = ObservationPaths.for_project(PROJECT_ID, root=state_root).ensure()
    outside = tmp_path / "outside"
    outside.mkdir()
    original = paths.projections.with_name("projections-original")

    def swap_parent_then_fail(*_args: object, **_kwargs: object) -> bytes:
        paths.projections.rename(original)
        paths.projections.symlink_to(outside, target_is_directory=True)
        raise transition.ProjectionTransitionError()

    monkeypatch.setattr(
        transition,
        "_read_bounded_private_file",
        swap_parent_then_fail,
    )

    with pytest.raises(transition.ProjectionTransitionError):
        transition._read_pointer(paths)
    assert paths.projections.is_symlink()
    assert list(outside.iterdir()) == []


def test_select_detects_a_project_added_during_the_mutation_loop(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import aether_agents.observation.projection_transition as transition

    state_root = tmp_path / "state" / "aether"
    first = _write_trace(state_root)
    prepared = transition.run_transition(_request(state_root, "prepare"))
    snapshot = {row["project_id"]: row["expected_pointer"] for row in prepared["projects"]}
    added_id = "22222222-2222-4222-8222-222222222222"
    original_publish = transition.publish_projection_pointer

    def publish_then_add(
        candidate: ObservationPaths,
        *,
        schema: str,
        expected_active: str | None,
        expected_projection_identity: tuple[int, int] | None,
    ) -> None:
        original_publish(
            candidate,
            schema=schema,
            expected_active=expected_active,
            expected_projection_identity=expected_projection_identity,
        )
        ObservationPaths.for_project(added_id, root=state_root).ensure()

    monkeypatch.setattr(transition, "publish_projection_pointer", publish_then_add)

    with pytest.raises(transition.ProjectionTransitionError):
        transition.run_transition(_request(state_root, "select", expected_pointers=snapshot))
    assert first.projection_pointer.is_file()
    assert ObservationPaths.for_project(added_id, root=state_root).project.is_dir()


def test_unselect_compensates_a_mixed_initial_install_boundary(tmp_path: Path) -> None:
    from aether_agents.observation.projection_transition import run_transition

    state_root = tmp_path / "state" / "aether"
    first = _write_trace(state_root)
    second_id = "22222222-2222-4222-8222-222222222222"
    second = ObservationPaths.for_project(second_id, root=state_root).ensure()
    prepared = run_transition(_request(state_root, "prepare"))
    assert [row["project_id"] for row in prepared["projects"]] == [  # type: ignore[index]
        PROJECT_ID,
        second_id,
    ]

    with ReadModel.open(first) as model:
        model.publish_projection(expected_active=None)
    assert not second.projection_pointer.exists()

    result = run_transition(
        _request(
            state_root,
            "unselect",
            expected_pointers={PROJECT_ID: None, second_id: None},
        )
    )

    assert result["project_count"] == 2
    assert result["unselected_count"] == 1
    assert not first.projection_pointer.exists()
    assert not second.projection_pointer.exists()


def test_unselect_rejects_a_third_pointer_and_restores_an_unknown_original(
    tmp_path: Path,
) -> None:
    from aether_agents.observation.projection_transition import (
        ProjectionTransitionError,
        run_transition,
    )

    state_root = tmp_path / "state" / "aether"
    paths = _write_trace(state_root)
    run_transition(_request(state_root, "prepare"))
    own_pointer = paths.projection_db(READ_MODEL_SCHEMA).name
    original_pointer = "aether.observation.projection.v998.sqlite3"
    competing_pointer = "aether.observation.projection.v999.sqlite3"

    atomic_private_write(paths.projection_pointer, (competing_pointer + "\n").encode("ascii"))
    with pytest.raises(ProjectionTransitionError):
        run_transition(
            _request(
                state_root,
                "unselect",
                expected_pointers={PROJECT_ID: original_pointer},
            )
        )
    assert paths.projection_pointer.read_text(encoding="ascii") == competing_pointer + "\n"

    original_bytes = b"opaque-unknown-newer-projection"
    paths.projection_db("aether.observation.projection.v998").write_bytes(original_bytes)
    atomic_private_write(paths.projection_pointer, (own_pointer + "\n").encode("ascii"))
    restored = run_transition(
        _request(
            state_root,
            "unselect",
            expected_pointers={PROJECT_ID: original_pointer},
        )
    )
    assert restored["unselected_count"] == 1
    assert paths.projection_pointer.read_text(encoding="ascii") == original_pointer + "\n"
    assert paths.projection_db("aether.observation.projection.v998").read_bytes() == original_bytes


def test_unselect_removes_own_pointer_without_opening_a_missing_or_corrupt_db(
    tmp_path: Path,
) -> None:
    from aether_agents.observation.projection_transition import (
        ProjectionTransitionError,
        run_transition,
    )

    state_root = tmp_path / "state" / "aether"
    paths = _write_trace(state_root)
    prepared = run_transition(_request(state_root, "prepare"))
    snapshot = {
        row["project_id"]: row["expected_pointer"]
        for row in prepared["projects"]  # type: ignore[index]
    }
    run_transition(_request(state_root, "select", expected_pointers=snapshot))
    own_pointer = paths.projection_db(READ_MODEL_SCHEMA).name

    for projection_file in paths.projection_files(READ_MODEL_SCHEMA):
        projection_file.unlink(missing_ok=True)
    missing = run_transition(
        _request(
            state_root,
            "unselect",
            expected_pointers=None,
        )
    )
    assert missing["unselected_count"] == 1
    assert not paths.projection_pointer.exists()
    assert not paths.projection_db(READ_MODEL_SCHEMA).exists()

    corrupt_bytes = b"corrupt-own-projection-must-remain-opaque"
    paths.projection_db(READ_MODEL_SCHEMA).write_bytes(corrupt_bytes)
    paths.projection_db(READ_MODEL_SCHEMA).chmod(0o600)
    atomic_private_write(paths.projection_pointer, (own_pointer + "\n").encode("ascii"))
    corrupt = run_transition(
        _request(
            state_root,
            "unselect",
            expected_pointers=None,
        )
    )
    assert corrupt["unselected_count"] == 1
    assert not paths.projection_pointer.exists()
    assert paths.projection_db(READ_MODEL_SCHEMA).read_bytes() == corrupt_bytes

    foreign_pointer = "aether.observation.projection.v999.sqlite3"
    atomic_private_write(
        paths.projection_pointer,
        (foreign_pointer + "\n").encode("ascii"),
    )
    with pytest.raises(ProjectionTransitionError):
        run_transition(
            _request(
                state_root,
                "unselect",
                expected_pointers=None,
            )
        )
    assert paths.projection_pointer.read_text(encoding="ascii") == foreign_pointer + "\n"
    assert paths.projection_db(READ_MODEL_SCHEMA).read_bytes() == corrupt_bytes


@pytest.mark.skipif(os.name != "posix", reason="foreign-schema symlink is POSIX-specific")
def test_select_never_opens_the_schema_named_by_the_previous_pointer(
    tmp_path: Path,
) -> None:
    from aether_agents.observation.projection_transition import run_transition

    state_root = tmp_path / "state" / "aether"
    paths = _write_trace(state_root)
    run_transition(_request(state_root, "prepare"))
    outside = tmp_path / "opaque-future.sqlite3"
    outside_bytes = b"not-a-target-sqlite-database"
    outside.write_bytes(outside_bytes)
    future_name = "aether.observation.projection.v999.sqlite3"
    (paths.projections / future_name).symlink_to(outside)
    atomic_private_write(paths.projection_pointer, (future_name + "\n").encode("ascii"))

    selected = run_transition(
        _request(
            state_root,
            "select",
            expected_pointers={PROJECT_ID: future_name},
        )
    )

    assert selected["projects"][0]["previous_pointer"] == future_name  # type: ignore[index]
    assert outside.read_bytes() == outside_bytes
    assert (paths.projections / future_name).is_symlink()


@pytest.mark.skipif(os.name != "posix", reason="nofollow sabotage is POSIX-specific")
def test_prepare_never_follows_a_canonical_uuid_symlink(tmp_path: Path) -> None:
    from aether_agents.observation.projection_transition import (
        ProjectionTransitionError,
        run_transition,
    )

    state_root = tmp_path / "state" / "aether"
    projects = state_root / "observations" / "projects"
    projects.mkdir(parents=True, mode=0o700)
    outside = tmp_path / "outside"
    outside.mkdir()
    sentinel = outside / "sentinel"
    sentinel.write_bytes(b"unchanged")
    (projects / PROJECT_ID).symlink_to(outside, target_is_directory=True)

    with pytest.raises(ProjectionTransitionError):
        run_transition(_request(state_root, "prepare"))
    assert sentinel.read_bytes() == b"unchanged"
    assert not (outside / "projections").exists()


def test_cli_rejects_schema_mismatch_without_disclosing_input(tmp_path: Path) -> None:
    state_root = tmp_path / "private-marker" / "state"
    state_root.mkdir(parents=True)
    request = {
        "operation": "prepare",
        "state_root": str(state_root),
        "expected_schema": "aether.observation.projection.v999",
    }
    env = dict(os.environ)
    source = str(Path(__file__).resolve().parents[1] / "src")
    env["PYTHONPATH"] = source + os.pathsep + env.get("PYTHONPATH", "")

    completed = subprocess.run(
        [sys.executable, "-m", "aether_agents.observation.projection_transition"],
        input=json.dumps(request),
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )

    assert completed.returncode != 0
    assert completed.stdout == ""
    assert json.loads(completed.stderr) == {"error": "PROJECTION_TRANSITION_FAILED"}
    assert "private-marker" not in completed.stderr


def test_cli_rejects_duplicate_json_members(tmp_path: Path) -> None:
    state_root = tmp_path / "state"
    state_root.mkdir()
    raw = (
        '{"operation":"prepare","operation":"select","state_root":'
        + json.dumps(str(state_root))
        + ',"expected_schema":'
        + json.dumps(READ_MODEL_SCHEMA)
        + "}"
    )
    env = dict(os.environ)
    source = str(Path(__file__).resolve().parents[1] / "src")
    env["PYTHONPATH"] = source + os.pathsep + env.get("PYTHONPATH", "")

    completed = subprocess.run(
        [sys.executable, "-m", "aether_agents.observation.projection_transition"],
        input=raw,
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )

    assert completed.returncode != 0
    assert completed.stdout == ""
    assert json.loads(completed.stderr)["error"] == "PROJECTION_TRANSITION_FAILED"


@pytest.mark.skipif(os.name != "posix", reason="private request files are POSIX-specific")
def test_cli_accepts_only_private_nofollow_request_files(tmp_path: Path) -> None:
    state_root = tmp_path / "state"
    state_root.mkdir()
    request_path = tmp_path / "request.json"
    request_path.write_text(json.dumps(_request(state_root, "prepare")), encoding="utf-8")
    request_path.chmod(0o600)
    env = dict(os.environ)
    source = str(Path(__file__).resolve().parents[1] / "src")
    env["PYTHONPATH"] = source + os.pathsep + env.get("PYTHONPATH", "")

    accepted = subprocess.run(
        [
            sys.executable,
            "-m",
            "aether_agents.observation.projection_transition",
            "--request-file",
            str(request_path),
        ],
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )
    assert accepted.returncode == 0
    assert json.loads(accepted.stdout)["project_count"] == 0

    request_path.chmod(0o644)
    rejected = subprocess.run(
        [
            sys.executable,
            "-m",
            "aether_agents.observation.projection_transition",
            "--request-file",
            str(request_path),
        ],
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )
    assert rejected.returncode != 0
    assert str(request_path) not in rejected.stderr

    request_path.chmod(0o600)
    request_link = tmp_path / "request-link.json"
    request_link.symlink_to(request_path)
    linked = subprocess.run(
        [
            sys.executable,
            "-m",
            "aether_agents.observation.projection_transition",
            "--request-file",
            str(request_link),
        ],
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )
    assert linked.returncode != 0
    assert str(request_link) not in linked.stderr
