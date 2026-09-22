"""Cross-version profile-bundle transfer through the exact installed target manager."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

import pytest
from test_observation_lifecycle import (
    _bind_disposable_project,
    _build_wheel,
    _clean_tagged_checkout,
    _prepared_release,
    _prepared_release_with_target_manager,
    _write_release_lock,
)

import aether_agents.lifecycle as lifecycle
from aether_agents.lifecycle import (
    HERMES_BASELINE,
    OBSERVATION_COMPATIBILITY,
    CheckoutEvidence,
    IntegrityError,
    LifecycleManager,
    ReleaseStore,
)


def test_staged_target_manager_prepares_its_changed_profile_resources(tmp_path: Path) -> None:
    """A not-yet-registered release must get profile bytes from its own wheel."""
    marker = "\nTarget-owned profile transfer regression.\n"
    version = "1.0.0"
    wheel = _build_wheel(tmp_path, version, soul_marker=marker)
    prepared = _prepared_release_with_target_manager(
        tmp_path, version, wheel, observation_compatibility=OBSERVATION_COMPATIBILITY
    )
    store = ReleaseStore(tmp_path / "data", state_root=tmp_path / "state")
    release_id = f"{version}-{prepared.wheel_sha256[:16]}"
    stage = store.release_path(release_id)
    stage.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(prepared.stage), str(stage))
    # Synthetic fixture pre-populates old resources; a real staged release does not.
    shutil.rmtree(stage / "profiles")
    manager = LifecycleManager(store=store, python_executable=Path(sys.executable))

    assert not (stage / "profile-bundle.json").exists()
    result = manager._run_target_lifecycle_subprocess(
        release_id, {"operation": "prepare_profile_bundle"}
    )
    manifest = stage / "profile-bundle.json"
    assert result["sha256"] == hashlib.sha256(manifest.read_bytes()).hexdigest()
    assert manager._wheel_profile_bundle_sha256(wheel) == result["sha256"]
    target_soul = stage / "profiles/morfeo/SOUL.md"
    assert target_soul.read_text(encoding="utf-8").endswith(marker)
    assert (
        target_soul.read_bytes()
        != (Path(lifecycle.__file__).parent / "resources/profiles/morfeo/SOUL.md").read_bytes()
    )
    manager._validate_profile_bundle(
        stage, {"profile_bundle_sha256": result["sha256"]}, verify_local_resources=False
    )
    with pytest.raises(IntegrityError, match="profile resource drift"):
        manager._validate_profile_bundle(stage, {"profile_bundle_sha256": result["sha256"]})

    release_manifest = stage / "release.json"
    release_data = json.loads(release_manifest.read_text(encoding="utf-8"))
    release_data["profile_bundle_sha256"] = result["sha256"]
    lifecycle._atomic_json(release_manifest, release_data)
    store.register(lifecycle.replace(prepared, stage=stage))
    manager._run_target_lifecycle_subprocess(
        release_id,
        {"operation": "validate_profile_bundle", "expected_sha256": result["sha256"]},
    )

    # A self-consistent staged manifest cannot approve altered bytes if the
    # authenticated target package itself still contains the original resource.
    target_soul.write_bytes(target_soul.read_bytes() + b"forged\n")
    details = json.loads(manifest.read_text(encoding="utf-8"))
    details["profiles"]["morfeo"]["resources"]["SOUL.md"]["sha256"] = hashlib.sha256(
        target_soul.read_bytes()
    ).hexdigest()
    manifest_data = (json.dumps(details, sort_keys=True, separators=(",", ":")) + "\n").encode()
    lifecycle._atomic_bytes(manifest, manifest_data)
    release_data["profile_bundle_sha256"] = hashlib.sha256(manifest_data).hexdigest()
    lifecycle._atomic_json(release_manifest, release_data)
    with pytest.raises(IntegrityError, match="target lifecycle operation failed"):
        manager._run_target_lifecycle_subprocess(
            release_id,
            {
                "operation": "validate_profile_bundle",
                "expected_sha256": release_data["profile_bundle_sha256"],
            },
        )


def test_changed_profiles_update_and_rollback_preserve_operator_state(tmp_path: Path) -> None:
    """Two distinct bundles can alternate without clobbering user-owned bytes."""
    store = ReleaseStore(tmp_path / "data", state_root=tmp_path / "state")
    manager = LifecycleManager(store=store, python_executable=Path(sys.executable))
    old = store.register(_prepared_release(tmp_path / "old", "1.0.0", b"old-wheel"))
    manager._materialize_profile_homes(old)
    store._commit_active(old, expected_active_release_id=None)

    home = store.profile_home("morfeo")
    original_soul = (home / "SOUL.md").read_bytes()
    config = home / "config.yaml"
    config.write_bytes(b"local operator setting\n")
    learned = home / "skills" / "learned-local" / "SKILL.md"
    learned.parent.mkdir(parents=True)
    learned.write_bytes(b"local skill\n")
    memory = home / "memories" / "local.md"
    memory.parent.mkdir()
    memory.write_bytes(b"local memory\n")

    marker = "\nDifferent release-owned SOUL.\n"
    version = "1.0.1"
    wheel = _build_wheel(tmp_path, version, soul_marker=marker)
    prepared = _prepared_release_with_target_manager(
        tmp_path, version, wheel, observation_compatibility=OBSERVATION_COMPATIBILITY
    )
    stage = store.release_path(prepared.release_id)
    shutil.move(str(prepared.stage), str(stage))
    shutil.rmtree(stage / "profiles")
    manager._run_target_lifecycle_subprocess(
        prepared.release_id, {"operation": "prepare_profile_bundle"}
    )
    incoming = store.register(lifecycle.replace(prepared, stage=stage))

    manager._materialize_profile_homes(incoming)
    store._commit_active(incoming, expected_active_release_id=old.release_id)
    manager._validate_profile_homes(incoming)
    assert (home / "SOUL.md").read_text(encoding="utf-8").endswith(marker)

    manager._materialize_profile_homes(old)
    store._commit_active(old, expected_active_release_id=incoming.release_id)
    manager._validate_profile_homes(old)
    assert (home / "SOUL.md").read_bytes() == original_soul
    assert config.read_bytes() == b"local operator setting\n"
    assert learned.read_bytes() == b"local skill\n"
    assert memory.read_bytes() == b"local memory\n"


@pytest.mark.integration
def test_prepared_release_uses_incoming_wheel_profile_resources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Real preparation and activation accept a wheel with a changed SOUL."""
    checkout, fixture_commit = _clean_tagged_checkout(tmp_path)
    monkeypatch.setattr(
        lifecycle,
        "verify_clean_checkout",
        lambda *_args, **_kwargs: CheckoutEvidence(
            path=checkout,
            tag=HERMES_BASELINE.tag,
            tag_object=HERMES_BASELINE.tag_object,
            commit=HERMES_BASELINE.commit,
            clean=True,
        ),
    )
    archive = lifecycle._materialize_git_archive
    monkeypatch.setattr(
        lifecycle,
        "_materialize_git_archive",
        lambda source, _commit, destination: archive(source, fixture_commit, destination),
    )
    marker = "\nIncoming wheel SOUL from full preparation.\n"
    wheel = _build_wheel(tmp_path, "1.0.0", soul_marker=marker)
    store = ReleaseStore(tmp_path / "data", state_root=tmp_path / "state")
    manager = LifecycleManager(
        store=store,
        python_executable=Path(sys.executable),
        project_root=_bind_disposable_project(store, tmp_path),
    )
    lock = _write_release_lock(
        tmp_path,
        "1.0.0",
        aether_wheel_sha256=hashlib.sha256(wheel.read_bytes()).hexdigest(),
        profile_bundle_sha256=manager._wheel_profile_bundle_sha256(wheel),
        hermes_checkout=checkout,
        hermes_commit=fixture_commit,
    )
    prepared = manager.prepare_release(wheel=wheel, hermes_checkout=checkout, release_lock=lock)
    record = store.register(prepared)
    assert manager.validate_release(record.release_id) == record
    manager.activate_existing(
        record.release_id, transition_kind="install", expected_active_release_id=None
    )
    home = store.profile_home("morfeo")
    assert (home / "SOUL.md").read_text(encoding="utf-8").endswith(marker)
    active = store.active()
    assert active is not None and active.release_id == record.release_id
    assert manager.validate_release(record.release_id) == record
    manager._validate_profile_homes(record)
