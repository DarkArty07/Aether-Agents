"""Unit and integration tests for exact inventory and atomic rc3 source restoration.

Authority: Objective Contract oc_f190ae9e878151e6@v2 (SHA-256
9bd2828f6f13e086db394d3bb26afb289a23cb5f78293738594fb399c8567188),
in-scope items 1-2, AC-1, AC-2, and unit RS-RESTORE.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import stat
import sys
from pathlib import Path
from typing import Any

import pytest
from test_observation_lifecycle import (
    FIXTURE_HERMES_VERSION,
    _build_wheel,
    _clean_tagged_checkout,
    _write_release_lock,
)

from aether_agents.lifecycle import (
    DIR_MODE,
    HERMES_BASELINE,
    IntegrityError,
    LifecycleManager,
    ReleaseStore,
    _materialize_git_archive,
    _observer_locked_distributions_for_python,
    _tree_sha256,
)

FIXTURE_PATH = (
    Path(__file__).resolve().parent.parent
    / "specs"
    / "001-aether-v1-productization"
    / "fixtures"
    / "restore_exact_hermes_source.py"
)

spec = importlib.util.spec_from_file_location("restore_exact_hermes_source", FIXTURE_PATH)
assert spec is not None and spec.loader is not None
restore_module = importlib.util.module_from_spec(spec)
sys.modules["restore_exact_hermes_source"] = restore_module
spec.loader.exec_module(restore_module)

RestorationError = restore_module.RestorationError
classify_hermes_source = restore_module.classify_hermes_source
assert_restorable_inventory = restore_module.assert_restorable_inventory
restore_exact_hermes_source = restore_module.restore_exact_hermes_source
EXPECTED_FORK_COMMIT = restore_module.EXPECTED_FORK_COMMIT
EXPECTED_FORK_TREE_SHA256 = restore_module.EXPECTED_FORK_TREE_SHA256


@pytest.fixture(scope="module")
def synthetic_fork_fixture(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, str, str, Path]:
    """Materialize a clean, disposable git repository and reference archive for tests."""
    fixture_root = tmp_path_factory.mktemp("synthetic_fork")
    checkout, commit = _clean_tagged_checkout(fixture_root)
    clean_dest = fixture_root / "clean-reference" / "hermes-source"
    clean_dest.parent.mkdir(parents=True, exist_ok=True)
    _materialize_git_archive(checkout, commit, clean_dest)
    clean_digest = _tree_sha256(clean_dest)
    return checkout, commit, clean_digest, clean_dest


def test_classify_hermes_source_expected_hash_equality(
    synthetic_fork_fixture: tuple[Path, str, str, Path], tmp_path: Path
) -> None:
    """Refuse when an expected file in hermes-source has altered bytes."""
    _, _, clean_digest, clean_dest = synthetic_fork_fixture
    target = tmp_path / "hermes-source"
    shutil.copytree(clean_dest, target)

    corrupt_file = target / "pyproject.toml"
    corrupt_file.write_text("# corrupted content\n", encoding="utf-8")

    inventory = classify_hermes_source(target, clean_dest)
    assert inventory.changed_count == 1
    assert "pyproject.toml" in inventory.changed_files
    assert not inventory.is_restorable

    with pytest.raises(RestorationError, match="changed expected files"):
        assert_restorable_inventory(inventory, expected_digest=clean_digest)


def test_classify_hermes_source_missing_file_refusal(
    synthetic_fork_fixture: tuple[Path, str, str, Path], tmp_path: Path
) -> None:
    """Refuse when an expected file in hermes-source is missing."""
    _, _, clean_digest, clean_dest = synthetic_fork_fixture
    target = tmp_path / "hermes-source"
    shutil.copytree(clean_dest, target)

    deleted_file = target / "uv.lock"
    deleted_file.unlink()

    inventory = classify_hermes_source(target, clean_dest)
    assert inventory.missing_count == 1
    assert "uv.lock" in inventory.missing_files
    assert not inventory.is_restorable

    with pytest.raises(RestorationError, match="missing 1 expected files"):
        assert_restorable_inventory(inventory, expected_digest=clean_digest)


def test_classify_hermes_source_extra_file_prefix_refusal(
    synthetic_fork_fixture: tuple[Path, str, str, Path], tmp_path: Path
) -> None:
    """Refuse when extra files exist outside the closed allowlist."""
    _, _, clean_digest, clean_dest = synthetic_fork_fixture
    target = tmp_path / "hermes-source"
    shutil.copytree(clean_dest, target)

    disallowed_file = target / "unexpected_root.py"
    disallowed_file.write_text("print('disallowed')", encoding="utf-8")

    sub_disallowed = target / "hermes_cli" / "extra_file.txt"
    sub_disallowed.write_text("extra", encoding="utf-8")

    inventory = classify_hermes_source(target, clean_dest)
    assert len(inventory.disallowed_extras) == 2
    assert "unexpected_root.py" in inventory.disallowed_extras
    assert "hermes_cli/extra_file.txt" in inventory.disallowed_extras
    assert not inventory.is_restorable

    with pytest.raises(RestorationError, match="outside closed allowlist"):
        assert_restorable_inventory(inventory, expected_digest=clean_digest)


def test_classify_hermes_source_disallowed_symlink_dir_refusal(
    synthetic_fork_fixture: tuple[Path, str, str, Path], tmp_path: Path
) -> None:
    """Refuse when an extra symlink directory exists outside the closed allowlist."""
    _, _, clean_digest, clean_dest = synthetic_fork_fixture
    target = tmp_path / "hermes-source"
    shutil.copytree(clean_dest, target)

    # Symlink directory outside allowlist
    bad_symlink = target / "bad_symlink_dir"
    bad_symlink.symlink_to("hermes_cli", target_is_directory=True)

    inventory = classify_hermes_source(target, clean_dest)
    assert "bad_symlink_dir" in inventory.disallowed_extras
    assert not inventory.is_restorable

    with pytest.raises(RestorationError, match="outside closed allowlist"):
        assert_restorable_inventory(inventory, expected_digest=clean_digest)


def test_classify_hermes_source_disallowed_dir_extra_refusal(
    synthetic_fork_fixture: tuple[Path, str, str, Path], tmp_path: Path
) -> None:
    """Refuse when an extra regular directory exists outside the clean dirs and allowlist."""
    _, _, clean_digest, clean_dest = synthetic_fork_fixture
    target = tmp_path / "hermes-source"
    shutil.copytree(clean_dest, target)

    # Regular directory outside clean dirs and allowlist (empty or with files)
    bad_dir = target / "unexpected_empty_dir"
    bad_dir.mkdir()

    inventory = classify_hermes_source(target, clean_dest)
    assert "unexpected_empty_dir" in inventory.disallowed_extras
    assert not inventory.is_restorable

    with pytest.raises(RestorationError, match="outside closed allowlist"):
        assert_restorable_inventory(inventory, expected_digest=clean_digest)


def test_classify_hermes_source_allowlisted_symlink_and_regular_extras(
    synthetic_fork_fixture: tuple[Path, str, str, Path], tmp_path: Path
) -> None:
    """Accept regular files and symlinks (files and dirs) confined to the allowlist."""
    _, _, clean_digest, clean_dest = synthetic_fork_fixture
    target = tmp_path / "hermes-source"
    shutil.copytree(clean_dest, target)

    # 1. Allowlisted node_modules regular file
    nm_file = target / "node_modules" / "pkg" / "index.js"
    nm_file.parent.mkdir(parents=True)
    nm_file.write_text("module.exports = {};", encoding="utf-8")

    # 2. Allowlisted node_modules symlink file
    nm_symlink_file = target / "node_modules" / ".bin" / "pkg"
    nm_symlink_file.parent.mkdir(parents=True)
    nm_symlink_file.symlink_to("../pkg/index.js")

    # 3. Allowlisted node_modules symlink directory
    nm_symlink_dir = target / "node_modules" / "pkg-link"
    nm_symlink_dir.symlink_to("pkg", target_is_directory=True)

    # 4. Allowlisted ui-tui node_modules file
    tui_nm_file = target / "ui-tui" / "node_modules" / "ink" / "package.json"
    tui_nm_file.parent.mkdir(parents=True)
    tui_nm_file.write_text('{"name": "ink"}', encoding="utf-8")

    # 5. Allowlisted ui-tui dist entry.js
    entry_js = target / "ui-tui" / "dist" / "entry.js"
    entry_js.parent.mkdir(parents=True)
    entry_js.write_text("console.log('tui');", encoding="utf-8")

    inventory = classify_hermes_source(target, clean_dest)
    assert inventory.clean_digest == clean_digest
    assert inventory.missing_count == 0
    assert inventory.changed_count == 0
    assert inventory.extras_count == 5
    assert inventory.extras_breakdown["node_modules"] == 3
    assert inventory.extras_breakdown["ui_tui_node_modules"] == 1
    assert inventory.extras_breakdown["ui_tui_dist_entry_js"] == 1
    assert inventory.extras_breakdown["symlinks"] == 2  # 1 file symlink + 1 dir symlink
    assert inventory.disallowed_extras == []
    assert_restorable_inventory(inventory, expected_digest=clean_digest)


def test_restore_refuse_cross_device(
    synthetic_fork_fixture: tuple[Path, str, str, Path], tmp_path: Path
) -> None:
    """Refuse cross-device operation before any swap rename."""
    checkout, commit, clean_digest, clean_dest = synthetic_fork_fixture
    release_dir = tmp_path / "releases" / "1.0.0rc3-test"
    release_dir.mkdir(parents=True)
    target = release_dir / "hermes-source"
    shutil.copytree(clean_dest, target)

    quarantine = tmp_path / "other_device" / ".quarantine-test"
    quarantine.parent.mkdir(parents=True)

    real_os_stat = os.stat

    def fake_stat(path: Any, *args: Any, **kwargs: Any) -> os.stat_result:
        res = real_os_stat(path, *args, **kwargs)
        if Path(path).resolve() == quarantine.parent.resolve():
            return os.stat_result(
                (
                    res.st_mode,
                    res.st_ino,
                    res.st_dev + 1,
                    res.st_nlink,
                    res.st_uid,
                    res.st_gid,
                    res.st_size,
                    res.st_atime,
                    res.st_mtime,
                    res.st_ctime,
                )
            )
        return res

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(os, "stat", fake_stat)
        with pytest.raises(RestorationError, match="cross-device operation refused"):
            restore_exact_hermes_source(
                release_dir,
                checkout,
                fork_commit=commit,
                expected_digest=clean_digest,
                quarantine_path=quarantine,
            )

    assert target.is_dir()
    assert not quarantine.exists()


def test_restore_rollback_on_injected_pre_swap_refusal(
    synthetic_fork_fixture: tuple[Path, str, str, Path], tmp_path: Path
) -> None:
    """Roll back with zero mutation when pre-swap refusal occurs."""
    checkout, commit, clean_digest, clean_dest = synthetic_fork_fixture
    release_dir = tmp_path / "releases" / "1.0.0rc3-test"
    release_dir.mkdir(parents=True)
    target = release_dir / "hermes-source"
    shutil.copytree(clean_dest, target)

    extra = target / "node_modules" / "pkg.txt"
    extra.parent.mkdir(parents=True)
    extra.write_text("extra", encoding="utf-8")

    initial_mtime = os.stat(extra).st_mtime_ns

    with pytest.raises(RestorationError, match="injected pre-swap refusal"):
        restore_exact_hermes_source(
            release_dir,
            checkout,
            fork_commit=commit,
            expected_digest=clean_digest,
            inject_pre_swap_refusal=True,
        )

    assert target.is_dir()
    assert extra.is_file()
    assert os.stat(extra).st_mtime_ns == initial_mtime
    assert [p.name for p in release_dir.iterdir()] == ["hermes-source"]


def test_restore_rollback_on_injected_swap_failure(
    synthetic_fork_fixture: tuple[Path, str, str, Path], tmp_path: Path
) -> None:
    """Restore contaminated tree from quarantine when swap rename fails."""
    checkout, commit, clean_digest, clean_dest = synthetic_fork_fixture
    release_dir = tmp_path / "releases" / "1.0.0rc3-test"
    release_dir.mkdir(parents=True)
    target = release_dir / "hermes-source"
    shutil.copytree(clean_dest, target)

    extra = target / "node_modules" / "pkg.txt"
    extra.parent.mkdir(parents=True)
    extra.write_text("extra", encoding="utf-8")

    quarantine = release_dir.parent / ".quarantine-test"

    with pytest.raises(OSError, match="injected swap rename failure"):
        restore_exact_hermes_source(
            release_dir,
            checkout,
            fork_commit=commit,
            expected_digest=clean_digest,
            quarantine_path=quarantine,
            inject_swap_failure=True,
        )

    assert target.is_dir()
    assert extra.is_file()
    assert not quarantine.exists()
    assert [p.name for p in release_dir.iterdir()] == ["hermes-source"]


def test_restore_rollback_on_injected_post_swap_failure(
    synthetic_fork_fixture: tuple[Path, str, str, Path], tmp_path: Path
) -> None:
    """Restore contaminated tree from quarantine when post-swap validation fails."""
    checkout, commit, clean_digest, clean_dest = synthetic_fork_fixture
    release_dir = tmp_path / "releases" / "1.0.0rc3-test"
    release_dir.mkdir(parents=True)
    target = release_dir / "hermes-source"
    shutil.copytree(clean_dest, target)

    extra = target / "node_modules" / "pkg.txt"
    extra.parent.mkdir(parents=True)
    extra.write_text("extra", encoding="utf-8")

    quarantine = release_dir.parent / ".quarantine-test"

    with pytest.raises(RestorationError, match="injected post-swap validation failure"):
        restore_exact_hermes_source(
            release_dir,
            checkout,
            fork_commit=commit,
            expected_digest=clean_digest,
            quarantine_path=quarantine,
            inject_post_swap_failure=True,
        )

    assert target.is_dir()
    assert extra.is_file()
    assert not quarantine.exists()
    assert [p.name for p in release_dir.iterdir()] == ["hermes-source"]


def test_quarantine_durability_against_release_store_recover(tmp_path: Path) -> None:
    """Prove that default dot-prefixed quarantine is durable and never deleted by store.recover()."""
    store = ReleaseStore(tmp_path / "data", state_root=tmp_path / "state")
    release_dir = store.releases / "1.0.0rc3-8987f650c027ad09"
    release_dir.mkdir(parents=True)
    (release_dir / "record.json").write_text("{}", encoding="utf-8")
    (release_dir / "hermes-source").mkdir(parents=True, exist_ok=True)

    # Create a quarantine directory sibling
    quarantine = store.releases / ".quarantine-1.0.0rc3-8987f650c027ad09-20260920120000"
    quarantine.mkdir()
    (quarantine / "preserved_extra.txt").write_text("contaminated bytes", encoding="utf-8")

    # Run recover()
    res = store.recover()
    assert res["incomplete_releases_removed"] == 0

    # Quarantine remains untouched
    assert quarantine.is_dir()
    assert (quarantine / "preserved_extra.txt").read_text(encoding="utf-8") == "contaminated bytes"

    # Refuse quarantine matching _RELEASE_ID_RE in releases directory
    bad_quarantine = store.releases / "1.0.0rc3-quarantine-leak"
    with pytest.raises(RestorationError, match="matches release ID pattern"):
        restore_exact_hermes_source(
            release_dir,
            tmp_path,
            quarantine_path=bad_quarantine,
        )


def test_restore_disposable_release_validate_and_doctor_ready(tmp_path: Path) -> None:
    """Full end-to-end restoration: proof of AC-2, validate_release, and doctor readiness."""
    checkout, commit = _clean_tagged_checkout(tmp_path)
    wheel = _build_wheel(tmp_path / "build", "1.0.0")
    wheel_sha = hashlib.sha256(wheel.read_bytes()).hexdigest()

    data_root = tmp_path / "data"
    state_root = tmp_path / "state"
    store = ReleaseStore(data_root, state_root=state_root)
    manager = LifecycleManager(store=store, python_executable=Path(sys.executable))

    release_lock = _write_release_lock(
        tmp_path,
        "1.0.0",
        aether_wheel_sha256=wheel_sha,
        hermes_checkout=checkout,
        hermes_commit=commit,
        hermes_version=FIXTURE_HERMES_VERSION,
    )
    prepared = manager.prepare_release(
        wheel=wheel, hermes_checkout=checkout, release_lock=release_lock
    )
    record = store.register(prepared)
    manager.activate_existing(
        record.release_id, transition_kind="install", expected_active_release_id=None
    )

    release_dir = store.release_path(record.release_id)
    target_source = release_dir / "hermes-source"
    expected_digest = prepared.hermes_source_tree_sha256

    # Unit isolation for non-source host-dependent checks in doctor
    manifest = json.loads((release_dir / "release.json").read_text(encoding="utf-8"))
    manager._installed_aether_identity = lambda path: {
        "version": record.version,
        "fingerprint": record.installed_file_fingerprint,
        "observation_compatibility": record.observation_compatibility,
        "observation_schema_sha256": manifest["observation_schema_sha256"],
    }

    def mock_dist_version(python_path: Any, distribution: str) -> str | None:
        if distribution == HERMES_BASELINE.distribution:
            return FIXTURE_HERMES_VERSION
        return _observer_locked_distributions_for_python(python_path).get(distribution)

    manager._installed_distribution_version = mock_dist_version
    manager._observer_hook_probe = lambda *_a, **_k: (
        {"expected_callbacks": 22, "registered_callbacks": 22, "remaining_callbacks": 0},
        True,
    )
    manager.projection_status = lambda *_a, **_k: {"mismatches": []}

    # Verify initially clean release is doctor ready
    assert manager.doctor().ready is True

    # 1. Contaminate target hermes-source
    nm_file = target_source / "node_modules" / "pkg" / "index.js"
    nm_file.parent.mkdir(parents=True)
    nm_file.write_text("module.exports = {};", encoding="utf-8")

    nm_symlink = target_source / "node_modules" / ".bin" / "pkg"
    nm_symlink.parent.mkdir(parents=True)
    nm_symlink.symlink_to("../pkg/index.js")

    tui_entry = target_source / "ui-tui" / "dist" / "entry.js"
    tui_entry.parent.mkdir(parents=True)
    tui_entry.write_text("console.log('entry');", encoding="utf-8")

    # Snapshot metadata files before restoration
    metadata_files = ["record.json", "release.json", "release-lock.json", "profile-bundle.json"]
    pre_hashes = {
        name: hashlib.sha256((release_dir / name).read_bytes()).hexdigest()
        for name in metadata_files
    }

    # 2. Before restoration: validate_release refuses and doctor flags ACTIVE_RELEASE_REVALIDATION_FAILED
    with pytest.raises(
        IntegrityError,
        match="release source tree contains a non-regular file|Hermes source digest mismatch",
    ):
        manager.validate_release(record.release_id)

    doctor_before = manager.doctor()
    assert doctor_before.ready is False
    assert "ACTIVE_RELEASE_REVALIDATION_FAILED" in doctor_before.codes

    # 3. Restore
    result = restore_exact_hermes_source(
        release_dir,
        checkout,
        fork_commit=commit,
        expected_digest=expected_digest,
        manager=manager,
    )

    # 4. Result assertions
    assert result.status == "restored"
    assert result.clean_digest == expected_digest
    assert result.inventory["extras_count"] == 3
    assert result.inventory["extras_breakdown"]["symlinks"] == 1
    assert result.quarantine_path is not None
    quarantine_path = Path(result.quarantine_path)
    assert quarantine_path.name.startswith(".quarantine-")

    # 5. hermes-source digest matches exact expected digest
    assert _tree_sha256(target_source) == expected_digest

    # 6. Clean tree is hardened (DIR_MODE 0o700)
    st = os.stat(target_source)
    assert stat.S_IMODE(st.st_mode) == DIR_MODE

    # 7. Quarantine is durable outside release and contains original contaminated files
    assert quarantine_path.is_dir()
    assert (quarantine_path / "node_modules" / ".bin" / "pkg").is_symlink()
    assert (quarantine_path / "ui-tui" / "dist" / "entry.js").is_file()

    # 8. ReleaseStore.recover() leaves quarantine untouched
    recover_res = store.recover()
    assert recover_res["incomplete_releases_removed"] == 0
    assert quarantine_path.is_dir()

    # 9. validate_release succeeds on the restored release
    rec = manager.validate_release(record.release_id)
    assert rec.release_id == record.release_id

    # 10. Doctor ready: ACTIVE_RELEASE_REVALIDATION_FAILED is gone and doctor.ready is True
    doctor_after = manager.doctor()
    assert "ACTIVE_RELEASE_REVALIDATION_FAILED" not in doctor_after.codes
    assert doctor_after.ready is True

    # 11. Metadata files are byte-identical (unchanged)
    post_hashes = {
        name: hashlib.sha256((release_dir / name).read_bytes()).hexdigest()
        for name in metadata_files
    }
    assert post_hashes == pre_hashes

    # 12. No mutation outside target_source / quarantine
    allowed_children = set(metadata_files) | {
        "artifacts",
        "hermes-source",
        "manager",
        "profiles",
        "runtime",
        "venv",
    }
    observed_children = {p.name for p in release_dir.iterdir()}
    assert observed_children == allowed_children
