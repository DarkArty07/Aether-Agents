"""Unit and integration tests for exact inventory and atomic rc3 source restoration.

Authority: Objective Contract oc_f190ae9e878151e6@v2 (SHA-256
9bd2828f6f13e086db394d3bb26afb289a23cb5f78293738594fb399c8567188),
in-scope items 1-2, AC-1, AC-2, and unit RS-RESTORE.
"""

from __future__ import annotations

import hashlib
import importlib.util
import os
import shutil
import stat
import sys
from pathlib import Path
from typing import Any

import pytest

from aether_agents.lifecycle import (
    DIR_MODE,
    IntegrityError,
    LifecycleManager,
    ReleaseStore,
    _materialize_git_archive,
    _tree_sha256,
)
from aether_agents.paths import data_root

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


def get_live_rc3_path() -> Path:
    candidates = sorted((data_root() / "releases").glob("1.0.0rc3-*"))
    if not candidates or not candidates[0].is_dir():
        pytest.skip("live rc3 release directory not available")
    return candidates[0]


@pytest.fixture(scope="module")
def clean_reference_tree(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Materialize one reference clean fork archive for the test module."""
    dest = tmp_path_factory.mktemp("clean_ref") / "hermes-source"
    repo_root = Path(__file__).resolve().parent.parent
    _materialize_git_archive(repo_root, EXPECTED_FORK_COMMIT, dest)
    digest = _tree_sha256(dest)
    assert digest == EXPECTED_FORK_TREE_SHA256
    return dest


def test_classify_hermes_source_expected_hash_equality(
    clean_reference_tree: Path, tmp_path: Path
) -> None:
    """Refuse when an expected file in hermes-source has altered bytes."""
    target = tmp_path / "hermes-source"
    shutil.copytree(clean_reference_tree, target)

    # Corrupt one expected file
    corrupt_file = target / "README.md"
    corrupt_file.write_text("corrupted content", encoding="utf-8")

    inventory = classify_hermes_source(target, clean_reference_tree)
    assert inventory.changed_count == 1
    assert "README.md" in inventory.changed_files
    assert not inventory.is_restorable

    with pytest.raises(RestorationError, match="changed expected files"):
        assert_restorable_inventory(inventory)


def test_classify_hermes_source_missing_file_refusal(
    clean_reference_tree: Path, tmp_path: Path
) -> None:
    """Refuse when an expected file in hermes-source is missing."""
    target = tmp_path / "hermes-source"
    shutil.copytree(clean_reference_tree, target)

    # Delete one expected file
    deleted_file = target / "LICENSE"
    deleted_file.unlink()

    inventory = classify_hermes_source(target, clean_reference_tree)
    assert inventory.missing_count == 1
    assert "LICENSE" in inventory.missing_files
    assert not inventory.is_restorable

    with pytest.raises(RestorationError, match="missing 1 expected files"):
        assert_restorable_inventory(inventory)


def test_classify_hermes_source_extra_prefix_refusal(
    clean_reference_tree: Path, tmp_path: Path
) -> None:
    """Refuse when extras exist outside the closed allowlist."""
    target = tmp_path / "hermes-source"
    shutil.copytree(clean_reference_tree, target)

    # Add disallowed extras
    disallowed_file = target / "unexpected_root.py"
    disallowed_file.write_text("print('disallowed')", encoding="utf-8")

    sub_disallowed = target / "hermes_cli" / "extra_file.txt"
    sub_disallowed.write_text("extra", encoding="utf-8")

    inventory = classify_hermes_source(target, clean_reference_tree)
    assert len(inventory.disallowed_extras) == 2
    assert "unexpected_root.py" in inventory.disallowed_extras
    assert "hermes_cli/extra_file.txt" in inventory.disallowed_extras
    assert not inventory.is_restorable

    with pytest.raises(RestorationError, match="outside closed allowlist"):
        assert_restorable_inventory(inventory)


def test_classify_hermes_source_allowlisted_symlink_and_regular_extras(
    clean_reference_tree: Path, tmp_path: Path
) -> None:
    """Accept regular files and symlinks confined to the three allowlisted prefixes."""
    target = tmp_path / "hermes-source"
    shutil.copytree(clean_reference_tree, target)

    # Add allowlisted extras
    nm_file = target / "node_modules" / "pkg" / "index.js"
    nm_file.parent.mkdir(parents=True)
    nm_file.write_text("module.exports = {};", encoding="utf-8")

    nm_symlink = target / "node_modules" / ".bin" / "pkg"
    nm_symlink.parent.mkdir(parents=True)
    nm_symlink.symlink_to("../pkg/index.js")

    tui_nm_file = target / "ui-tui" / "node_modules" / "ink" / "package.json"
    tui_nm_file.parent.mkdir(parents=True)
    tui_nm_file.write_text('{"name": "ink"}', encoding="utf-8")

    entry_js = target / "ui-tui" / "dist" / "entry.js"
    entry_js.parent.mkdir(parents=True)
    entry_js.write_text("console.log('tui');", encoding="utf-8")

    inventory = classify_hermes_source(target, clean_reference_tree)
    assert inventory.missing_count == 0
    assert inventory.changed_count == 0
    assert inventory.extras_count == 4
    assert inventory.extras_breakdown["node_modules"] == 2
    assert inventory.extras_breakdown["ui_tui_node_modules"] == 1
    assert inventory.extras_breakdown["ui_tui_dist_entry_js"] == 1
    assert inventory.extras_breakdown["symlinks"] == 1
    assert inventory.disallowed_extras == []
    assert inventory.is_restorable

    # Assert no refusal
    assert_restorable_inventory(inventory)


def test_classify_live_rc3_source_matches_exact_inventory(
    clean_reference_tree: Path,
) -> None:
    """Prove AC-1 against the actual read-only live rc3 hermes-source."""
    live_rc3 = get_live_rc3_path()
    assert live_rc3.is_dir(), f"live rc3 path not found: {live_rc3}"
    live_source = live_rc3 / "hermes-source"
    assert live_source.is_dir(), f"live hermes-source not found: {live_source}"

    inventory = classify_hermes_source(live_source, clean_reference_tree)

    assert inventory.clean_digest == EXPECTED_FORK_TREE_SHA256
    assert inventory.expected_files_count == 9377
    assert inventory.missing_count == 0
    assert inventory.changed_count == 0
    assert inventory.extras_count == 8881
    assert inventory.extras_breakdown["node_modules"] == 8650
    assert inventory.extras_breakdown["ui_tui_node_modules"] == 230
    assert inventory.extras_breakdown["ui_tui_dist_entry_js"] == 1
    assert inventory.extras_breakdown["symlinks"] == 16
    assert inventory.disallowed_extras == []
    assert inventory.missing_files == []
    assert inventory.changed_files == []
    assert inventory.is_restorable


def test_restore_refuse_cross_device(clean_reference_tree: Path, tmp_path: Path) -> None:
    """Refuse cross-device operation before any swap rename."""
    release_dir = tmp_path / "releases" / "1.0.0rc3-test"
    release_dir.mkdir(parents=True)
    target = release_dir / "hermes-source"
    shutil.copytree(clean_reference_tree, target)

    quarantine = tmp_path / "other_device" / "quarantine"
    quarantine.parent.mkdir(parents=True)

    real_os_stat = os.stat

    def fake_stat(path: Any, *args: Any, **kwargs: Any) -> os.stat_result:
        res = real_os_stat(path, *args, **kwargs)
        if Path(path).resolve() == quarantine.parent.resolve():
            # Return modified st_dev to simulate different filesystem
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

    repo_root = Path(__file__).resolve().parent.parent
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(os, "stat", fake_stat)
        with pytest.raises(RestorationError, match="cross-device operation refused"):
            restore_exact_hermes_source(
                release_dir,
                repo_root,
                quarantine_path=quarantine,
            )

    # Ensure zero mutation
    assert target.is_dir()
    assert not quarantine.exists()


def test_restore_rollback_on_injected_pre_swap_refusal(
    clean_reference_tree: Path, tmp_path: Path
) -> None:
    """Roll back with zero mutation when pre-swap refusal occurs."""
    release_dir = tmp_path / "releases" / "1.0.0rc3-test"
    release_dir.mkdir(parents=True)
    target = release_dir / "hermes-source"
    shutil.copytree(clean_reference_tree, target)

    # Add an allowed extra
    extra = target / "node_modules" / "pkg.txt"
    extra.parent.mkdir(parents=True)
    extra.write_text("extra", encoding="utf-8")

    initial_mtime = os.stat(extra).st_mtime_ns
    repo_root = Path(__file__).resolve().parent.parent

    with pytest.raises(RestorationError, match="injected pre-swap refusal"):
        restore_exact_hermes_source(
            release_dir,
            repo_root,
            inject_pre_swap_refusal=True,
        )

    # Target source is completely preserved
    assert target.is_dir()
    assert extra.is_file()
    assert os.stat(extra).st_mtime_ns == initial_mtime

    # No staging or quarantine directories remain
    sibling_names = [p.name for p in release_dir.iterdir()]
    assert sibling_names == ["hermes-source"]


def test_restore_rollback_on_injected_swap_failure(
    clean_reference_tree: Path, tmp_path: Path
) -> None:
    """Restore contaminated tree from quarantine when swap rename fails."""
    release_dir = tmp_path / "releases" / "1.0.0rc3-test"
    release_dir.mkdir(parents=True)
    target = release_dir / "hermes-source"
    shutil.copytree(clean_reference_tree, target)

    extra = target / "node_modules" / "pkg.txt"
    extra.parent.mkdir(parents=True)
    extra.write_text("extra", encoding="utf-8")

    quarantine = release_dir.parent / "quarantine-test"
    repo_root = Path(__file__).resolve().parent.parent

    with pytest.raises(OSError, match="injected swap rename failure"):
        restore_exact_hermes_source(
            release_dir,
            repo_root,
            quarantine_path=quarantine,
            inject_swap_failure=True,
        )

    # Original tree was restored to hermes-source
    assert target.is_dir()
    assert extra.is_file()
    assert not quarantine.exists()

    # No ambiguous pair
    assert [p.name for p in release_dir.iterdir()] == ["hermes-source"]


def test_restore_rollback_on_injected_post_swap_failure(
    clean_reference_tree: Path, tmp_path: Path
) -> None:
    """Restore contaminated tree from quarantine when post-swap validation fails."""
    release_dir = tmp_path / "releases" / "1.0.0rc3-test"
    release_dir.mkdir(parents=True)
    target = release_dir / "hermes-source"
    shutil.copytree(clean_reference_tree, target)

    extra = target / "node_modules" / "pkg.txt"
    extra.parent.mkdir(parents=True)
    extra.write_text("extra", encoding="utf-8")

    quarantine = release_dir.parent / "quarantine-test"
    repo_root = Path(__file__).resolve().parent.parent

    with pytest.raises(RestorationError, match="injected post-swap validation failure"):
        restore_exact_hermes_source(
            release_dir,
            repo_root,
            quarantine_path=quarantine,
            inject_post_swap_failure=True,
        )

    # Original contaminated tree was restored to hermes-source
    assert target.is_dir()
    assert extra.is_file()
    assert not quarantine.exists()

    # Exactly one hermes-source, no staging leftovers
    assert [p.name for p in release_dir.iterdir()] == ["hermes-source"]


def test_restore_disposable_contaminated_rc3_release(tmp_path: Path) -> None:
    """Full end-to-end restoration: proof of AC-2 against disposable rc3 release."""
    live_rc3 = get_live_rc3_path()
    assert live_rc3.is_dir(), f"live rc3 path not found: {live_rc3}"

    data_root = tmp_path / "data"
    state_root = tmp_path / "state"
    data_root.mkdir()
    state_root.mkdir()

    store = ReleaseStore(data_root, state_root=state_root)
    release_dir = store.releases / live_rc3.name
    release_dir.mkdir(parents=True)

    # Copy release files excluding hermes-source (preserving symlinks)
    shutil.copytree(
        live_rc3,
        release_dir,
        symlinks=True,
        dirs_exist_ok=True,
        ignore=lambda d, f: ["hermes-source"] if Path(d).resolve() == live_rc3.resolve() else [],
    )

    # Copy a contaminated hermes-source: copy uv.lock, README, LICENSE, etc., plus node_modules with symlink
    # and ui-tui/dist/entry.js
    target_source = release_dir / "hermes-source"

    # Materialize clean tree first to make it a realistic contaminated tree
    repo_root = Path(__file__).resolve().parent.parent
    _materialize_git_archive(repo_root, EXPECTED_FORK_COMMIT, target_source)

    # Add realistic contamination
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

    # Before restoration: validate_release must refuse due to contamination
    manager = LifecycleManager(
        store=store,
        python_executable=release_dir / "manager" / "bin" / "python",
    )
    with pytest.raises(IntegrityError):
        manager.validate_release(release_dir.name)

    quarantine_path = release_dir.parent / f"{release_dir.name}-quarantine"
    result = restore_exact_hermes_source(
        release_dir,
        repo_root,
        quarantine_path=quarantine_path,
        manager=manager,
    )

    # 1. Result properties
    assert result.status == "restored"
    assert result.clean_digest == EXPECTED_FORK_TREE_SHA256
    assert result.quarantine_path == str(quarantine_path)
    assert result.inventory["extras_count"] == 3
    assert result.inventory["extras_breakdown"]["symlinks"] == 1

    # 2. hermes-source digest matches exact fork digest
    assert _tree_sha256(target_source) == EXPECTED_FORK_TREE_SHA256

    # 3. Clean tree is hardened (DIR_MODE 0o700)
    st = os.stat(target_source)
    assert stat.S_IMODE(st.st_mode) == DIR_MODE

    # 4. Quarantine is durable outside release and contains original contaminated files
    assert quarantine_path.is_dir()
    assert (quarantine_path / "node_modules" / ".bin" / "pkg").is_symlink()
    assert (quarantine_path / "ui-tui" / "dist" / "entry.js").is_file()

    # 5. validate_release succeeds on the restored release
    rec = manager.validate_release(release_dir.name)
    assert rec.version == "1.0.0rc3"

    # 6. Metadata files are byte-identical (unchanged)
    post_hashes = {
        name: hashlib.sha256((release_dir / name).read_bytes()).hexdigest()
        for name in metadata_files
    }
    assert post_hashes == pre_hashes

    # 7. No mutation outside target_source / quarantine
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
