"""Lifecycle adoption and setup-preview parity for maintained-fork first install.

Covers GitHub issues #465 (pre-marker profile adoption) and #466 (setup preview
validates the lock's maintained-fork identity, not the retired public baseline).
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

import pytest
from test_observation_lifecycle import (
    FIXTURE_HERMES_VERSION,
    _build_wheel,
    _clean_tagged_checkout,
    _prepared_release,
    _source_tree_sha256,
    _write_release_lock,
)

import aether_agents.lifecycle as lifecycle
from aether_agents.lifecycle import (
    HERMES_BASELINE,
    IntegrityError,
    LifecycleManager,
    ReleaseStore,
)


def test_inspect_candidate_uses_maintained_fork_lock_identity_not_baseline(
    tmp_path: Path,
) -> None:
    """#466: preview must accept the same maintained-fork candidate prepare accepts."""

    checkout, commit = _clean_tagged_checkout(tmp_path)
    assert commit != HERMES_BASELINE.commit
    wheel = _build_wheel(tmp_path / "build", "1.0.0")
    release_lock = _write_release_lock(
        tmp_path,
        "1.0.0",
        aether_wheel_sha256=hashlib.sha256(wheel.read_bytes()).hexdigest(),
        hermes_checkout=checkout,
        hermes_commit=commit,
        hermes_version=FIXTURE_HERMES_VERSION,
        source_tree_sha256=_source_tree_sha256(checkout, commit),
    )
    manager = LifecycleManager(
        store=ReleaseStore(tmp_path / "data" / "aether", state_root=tmp_path / "state" / "aether"),
        python_executable=Path(sys.executable),
    )

    identity = manager.inspect_candidate(
        wheel=wheel,
        hermes_checkout=checkout,
        release_lock=release_lock,
    )

    assert identity["version"] == "1.0.0"
    assert identity["wheel_sha256"] == hashlib.sha256(wheel.read_bytes()).hexdigest()


def test_inspect_candidate_still_refuses_wrong_maintained_fork_commit(
    tmp_path: Path,
) -> None:
    checkout, commit = _clean_tagged_checkout(tmp_path)
    wheel = _build_wheel(tmp_path / "build", "1.0.0")
    wrong_commit = "b" * 40
    release_lock = _write_release_lock(
        tmp_path,
        "1.0.0",
        aether_wheel_sha256=hashlib.sha256(wheel.read_bytes()).hexdigest(),
        hermes_checkout=checkout,
        hermes_commit=wrong_commit,
        hermes_version=FIXTURE_HERMES_VERSION,
        source_tree_sha256="d" * 64,
    )
    manager = LifecycleManager(
        store=ReleaseStore(tmp_path / "data" / "aether", state_root=tmp_path / "state" / "aether"),
        python_executable=Path(sys.executable),
    )

    with pytest.raises(IntegrityError, match="commit mismatch"):
        manager.inspect_candidate(
            wheel=wheel,
            hermes_checkout=checkout,
            release_lock=release_lock,
        )


def _seed_premarker_profiles(store: ReleaseStore) -> dict[str, bytes]:
    """Seed realistic pre-lifecycle homes: operator config, package SOUL, mixed skills."""

    resources = Path(lifecycle.__file__).parent / "resources"
    operator_configs: dict[str, bytes] = {}
    for role in ("morfeo", "supervisor", "implementer"):
        home = store.profile_home(role)
        home.mkdir(parents=True, exist_ok=True)
        operator = (
            f"# operator provisioned {role}\nchannels:\n  telegram:\n    enabled: true\n"
        ).encode()
        (home / "config.yaml").write_bytes(operator)
        os.chmod(home / "config.yaml", 0o600)
        operator_configs[role] = operator
        soul = (resources / "profiles" / role / "SOUL.md").read_bytes()
        (home / "SOUL.md").write_bytes(soul)
        os.chmod(home / "SOUL.md", 0o600)
        skills_root = home / "skills"
        skills_root.mkdir(parents=True, exist_ok=True)
        for skill_name in lifecycle._CANONICAL_SKILLS:
            skill_dir = skills_root / skill_name
            skill_dir.mkdir(parents=True, exist_ok=True)
            package_bytes = (resources / "skills" / skill_name / "SKILL.md").read_bytes()
            if skill_name == "project-knowledge":
                payload = b"# older live revision that must be backed up\n"
            else:
                payload = package_bytes
            target = skill_dir / "SKILL.md"
            target.write_bytes(payload)
            os.chmod(target, 0o644 if skill_name == "work-memory" else 0o600)
        learned = skills_root / "private-local" / "SKILL.md"
        learned.parent.mkdir(parents=True, exist_ok=True)
        learned.write_bytes(b"learned local procedure\n")
    return operator_configs


def test_recover_leaves_premarker_profiles_untouched(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """#465: recover with no active must not treat pre-marker homes as debris."""

    store = ReleaseStore(tmp_path / "data" / "aether", state_root=tmp_path / "state" / "aether")
    operator_configs = _seed_premarker_profiles(store)
    manager = LifecycleManager(store=store, python_executable=Path(sys.executable))
    monkeypatch.setattr(manager, "_reconcile_projections_locked", lambda _result: None)

    manager.recover()

    assert store.active(required=False) is None
    for role, expected in operator_configs.items():
        home = store.profile_home(role)
        assert (home / "config.yaml").read_bytes() == expected
        assert not (home / "aether-observer.json").exists()
        assert (home / "skills" / "private-local" / "SKILL.md").read_bytes() == (
            b"learned local procedure\n"
        )


def test_first_install_adopts_premarker_profiles_preserving_operator_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """#465: first install adopts unmarked homes without discarding operator config."""

    store = ReleaseStore(tmp_path / "data" / "aether", state_root=tmp_path / "state" / "aether")
    operator_configs = _seed_premarker_profiles(store)
    record = store.register(_prepared_release(tmp_path / "r1", "1.0.0", b"wheel-one"))
    manager = LifecycleManager(store=store, python_executable=Path(sys.executable))
    monkeypatch.setattr(
        manager,
        "validate_release",
        lambda release_id: store._read_release(release_id),
    )
    monkeypatch.setattr(
        manager,
        "_prepare_release_projections_locked",
        lambda _record: {"desktop": None, "launcher": None, "service": None},
    )
    monkeypatch.setattr(manager, "_select_release_projections_locked", lambda *_a, **_k: None)
    monkeypatch.setattr(manager, "project_release", lambda *_a, **_k: None)
    monkeypatch.setattr(manager, "_reconcile_release_projections_locked", lambda *_a, **_k: None)

    selected = manager.activate_existing(
        record.release_id,
        transition_kind="install",
        expected_active_release_id=None,
    )

    assert selected.release_id == record.release_id
    resources = Path(lifecycle.__file__).parent / "resources"
    for role, expected_config in operator_configs.items():
        home = store.profile_home(role)
        assert (home / "config.yaml").read_bytes() == expected_config
        assert (home / "SOUL.md").read_bytes() == (
            resources / "profiles" / role / "SOUL.md"
        ).read_bytes()
        marker = json.loads((home / "aether-observer.json").read_text(encoding="utf-8"))
        assert marker["release_id"] == record.release_id
        assert marker["role"] == role
        for skill_name in lifecycle._CANONICAL_SKILLS:
            observed = (home / "skills" / skill_name / "SKILL.md").read_bytes()
            assert observed == (resources / "skills" / skill_name / "SKILL.md").read_bytes()
        assert (home / "skills" / "private-local" / "SKILL.md").read_bytes() == (
            b"learned local procedure\n"
        )
    receipt = next(
        (store.state_root / "migrations").glob("*-profile-adoption/receipt.json"),
        None,
    )
    assert receipt is not None
    payload = json.loads(receipt.read_text(encoding="utf-8"))
    assert payload["schema"] == "aether.profile-adoption.v1"
    assert any(
        item["path"].endswith("skills/project-knowledge/SKILL.md") for item in payload["backed_up"]
    )
    manager._validate_profile_homes(selected)
