"""Adversarial regressions for product-owned path confinement.

Every substitution below happens after directory creation but before the first
file mutation.  A confined writer must therefore reject the renamed ancestor,
must not create bytes below the attacker's replacement, and must close every
descriptor acquired before rejection.
"""

from __future__ import annotations

import io
import os
import stat
import tarfile
from pathlib import Path

import pytest

import aether_agents.lifecycle as lifecycle_module
import aether_agents.observation.fingerprints as fingerprints_module
import aether_agents.observation.locking as locking_module
import aether_agents.observation.reduce.ingest as ingest_module
import aether_agents.paths as paths_module
from aether_agents.lifecycle import IntegrityError, ReleaseStore
from aether_agents.observation.fingerprints import FingerprintKeyring
from aether_agents.observation.locking import project_lock
from aether_agents.paths import ObservationPaths, UnsafeObservationPath, ensure_private_dir

PROJECT_ID = "11111111-1111-4111-8111-111111111111"


def _swap_directory(directory: Path, external: Path) -> Path:
    """Replace ``directory`` with an alias to attacker-controlled storage."""

    held = directory.with_name(directory.name + "-held")
    directory.rename(held)
    directory.symlink_to(external, target_is_directory=True)
    return held


def _descriptor_snapshot() -> set[int]:
    return {int(name) for name in os.listdir("/proc/self/fd") if name.isdigit()}


def _close_descriptors(descriptors: set[int]) -> None:
    for descriptor in descriptors:
        try:
            os.close(descriptor)
        except OSError:
            pass


@pytest.mark.skipif(os.name != "posix", reason="POSIX dirfd/no-follow confinement")
def test_summary_write_rejects_ancestor_substitution_without_external_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path / "state")
    external = tmp_path / "external-summaries"
    external.mkdir()
    real_ensure = ensure_private_dir
    swapped = False

    def ensure_then_swap(directory: Path) -> Path:
        nonlocal swapped
        result = real_ensure(directory)
        if Path(directory) == paths.summaries and not swapped:
            swapped = True
            _swap_directory(paths.summaries, external)
        return result

    monkeypatch.setattr(paths_module, "ensure_private_dir", ensure_then_swap)
    rejected = False
    try:
        ingest_module._write_summary(
            paths,
            {"summary_id": "sum_" + "a" * 64, "state": "bounded"},
        )
    except UnsafeObservationPath:
        rejected = True

    assert swapped
    assert (rejected, list(external.iterdir())) == (True, [])


@pytest.mark.skipif(os.name != "posix", reason="POSIX dirfd/no-follow confinement")
def test_fingerprint_key_creation_rejects_ancestor_substitution_before_secret_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path / "state")
    external = tmp_path / "external-keys"
    external.mkdir()
    real_ensure = ensure_private_dir
    key_directory_calls = 0
    swapped = False

    def ensure_then_swap(directory: Path) -> Path:
        nonlocal key_directory_calls, swapped
        result = real_ensure(directory)
        if Path(directory) == paths.keys:
            key_directory_calls += 1
            if key_directory_calls == 2:
                swapped = True
                _swap_directory(paths.keys, external)
        return result

    monkeypatch.setattr(fingerprints_module, "ensure_private_dir", ensure_then_swap)
    rejected = False
    try:
        FingerprintKeyring(paths).load_or_create()
    except UnsafeObservationPath:
        rejected = True

    assert swapped
    assert (rejected, list(external.iterdir())) == (True, [])


@pytest.mark.skipif(os.name != "posix", reason="POSIX dirfd/no-follow confinement")
def test_project_lock_rejects_ancestor_substitution_without_relocation_or_fd_leak(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path / "state")
    external = tmp_path / "external-locks"
    external.mkdir()
    real_ensure = ensure_private_dir
    swapped = False

    def ensure_then_swap(directory: Path) -> Path:
        nonlocal swapped
        result = real_ensure(directory)
        if Path(directory) == paths.locks and not swapped:
            swapped = True
            _swap_directory(paths.locks, external)
        return result

    monkeypatch.setattr(locking_module, "ensure_private_dir", ensure_then_swap)
    before = _descriptor_snapshot()
    rejected = False
    try:
        try:
            with project_lock(paths, "storage-transition"):
                pass
        except UnsafeObservationPath:
            rejected = True
        leaked = _descriptor_snapshot() - before
        assert swapped
        assert (rejected, list(external.iterdir()), leaked) == (True, [], set())
    finally:
        _close_descriptors(_descriptor_snapshot() - before)


@pytest.mark.skipif(os.name != "posix", reason="POSIX descriptor lifecycle")
def test_project_lock_closes_descriptor_when_post_open_validation_fails(
    tmp_path: Path,
) -> None:
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path / "state")
    ensure_private_dir(paths.locks)
    external = tmp_path / "external-lock"
    external.write_bytes(b"outside")
    os.link(external, paths.locks / "storage-transition.lock")
    before = _descriptor_snapshot()
    try:
        with pytest.raises(UnsafeObservationPath):
            with project_lock(paths, "storage-transition"):
                pass
        leaked = _descriptor_snapshot() - before
        assert leaked == set()
    finally:
        _close_descriptors(_descriptor_snapshot() - before)


@pytest.mark.skipif(os.name != "posix", reason="POSIX dirfd/no-follow confinement")
def test_lifecycle_atomic_json_rejects_nonleaf_ancestor_substitution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    owned = tmp_path / "owned"
    target = owned / "records" / "active.json"
    external = tmp_path / "external-state"
    (external / "records").mkdir(parents=True)
    real_ensure = ensure_private_dir
    swapped = False

    def ensure_then_swap(directory: Path) -> Path:
        nonlocal swapped
        result = real_ensure(directory)
        if Path(directory) == target.parent and not swapped:
            swapped = True
            _swap_directory(owned, external)
        return result

    monkeypatch.setattr(lifecycle_module, "ensure_private_dir", ensure_then_swap)
    rejected = False
    try:
        lifecycle_module._atomic_json(target, {"bounded": True})
    except UnsafeObservationPath:
        rejected = True

    assert swapped
    assert (rejected, list((external / "records").iterdir())) == (True, [])


@pytest.mark.skipif(os.name != "posix", reason="POSIX dirfd/no-follow confinement")
def test_lifecycle_atomic_bytes_rejects_nonleaf_ancestor_substitution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    owned = tmp_path / "owned"
    target = owned / "profiles" / "marker"
    external = tmp_path / "external-data"
    (external / "profiles").mkdir(parents=True)
    real_ensure = ensure_private_dir
    swapped = False

    def ensure_then_swap(directory: Path) -> Path:
        nonlocal swapped
        result = real_ensure(directory)
        if Path(directory) == target.parent and not swapped:
            swapped = True
            _swap_directory(owned, external)
        return result

    monkeypatch.setattr(lifecycle_module, "ensure_private_dir", ensure_then_swap)
    rejected = False
    try:
        lifecycle_module._atomic_bytes(target, b"bounded\n")
    except UnsafeObservationPath:
        rejected = True

    assert swapped
    assert (rejected, list((external / "profiles").iterdir())) == (True, [])


@pytest.mark.skipif(os.name != "posix", reason="POSIX dirfd/no-follow confinement")
def test_lifecycle_directory_fsync_rejects_substituted_ancestor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    owned = tmp_path / "owned"
    directory = owned / "release"
    directory.mkdir(parents=True)
    external = tmp_path / "external-release"
    (external / "release").mkdir(parents=True)
    held = _swap_directory(owned, external)
    fsynced: list[tuple[int, int]] = []

    def record_fsync(descriptor: int) -> None:
        status = os.fstat(descriptor)
        fsynced.append((status.st_dev, status.st_ino))

    monkeypatch.setattr(lifecycle_module.os, "fsync", record_fsync)
    with pytest.raises(UnsafeObservationPath):
        lifecycle_module._fsync_directory(directory)

    assert held.is_dir()
    assert fsynced == []


@pytest.mark.skipif(os.name != "posix", reason="POSIX dirfd/no-follow confinement")
def test_lifecycle_durable_candidate_write_rejects_substituted_ancestor(
    tmp_path: Path,
) -> None:
    owned = tmp_path / "owned"
    external = tmp_path / "external-candidate"
    (external / "artifacts").mkdir(parents=True)
    owned.symlink_to(external, target_is_directory=True)
    target = owned / "artifacts" / "candidate.whl"
    rejected = False
    try:
        lifecycle_module.LifecycleManager._write_durable(target, b"wheel-bytes")
    except UnsafeObservationPath:
        rejected = True

    assert (rejected, list((external / "artifacts").iterdir())) == (True, [])


@pytest.mark.skipif(os.name != "posix", reason="POSIX dirfd/no-follow confinement")
def test_lifecycle_profile_restore_never_unlinks_through_substituted_ancestor(
    tmp_path: Path,
) -> None:
    owned = tmp_path / "owned"
    external = tmp_path / "external-profile"
    target = owned / "profiles" / "morfeo" / "config.yaml"
    external_target = external / "profiles" / "morfeo" / "config.yaml"
    external_target.parent.mkdir(parents=True)
    external_target.write_bytes(b"user-owned\n")
    owned.symlink_to(external, target_is_directory=True)
    rejected = False
    try:
        lifecycle_module.LifecycleManager._restore_profile_product_state({target: None})
    except UnsafeObservationPath:
        rejected = True

    assert (rejected, external_target.read_bytes()) == (True, b"user-owned\n")


@pytest.mark.skipif(os.name != "posix", reason="POSIX dirfd/no-follow confinement")
def test_lifecycle_debris_cleanup_never_deletes_through_substituted_ancestor(
    tmp_path: Path,
) -> None:
    owned = tmp_path / "owned"
    external = tmp_path / "external-source"
    source = owned / "hermes-source"
    external_debris = external / "hermes-source" / "hermes_agent.egg-info"
    external_debris.mkdir(parents=True)
    metadata = external_debris / "PKG-INFO"
    metadata.write_bytes(b"user-owned\n")
    owned.symlink_to(external, target_is_directory=True)
    rejected = False
    try:
        lifecycle_module._remove_hermes_editable_build_debris(source)
    except UnsafeObservationPath:
        rejected = True

    assert (rejected, metadata.read_bytes()) == (True, b"user-owned\n")


@pytest.mark.skipif(os.name != "posix", reason="POSIX dirfd/no-follow confinement")
def test_lifecycle_archive_extraction_never_writes_through_substituted_ancestor(
    tmp_path: Path,
) -> None:
    archive = io.BytesIO()
    with tarfile.open(fileobj=archive, mode="w:") as bundle:
        member = tarfile.TarInfo("hermes/module.py")
        member.mode = 0o664
        data = b"bounded = True\n"
        member.size = len(data)
        bundle.addfile(member, io.BytesIO(data))
    owned = tmp_path / "owned"
    external = tmp_path / "external-extract"
    external.mkdir()
    owned.symlink_to(external, target_is_directory=True)
    destination = owned / "source"
    rejected = False
    try:
        lifecycle_module._extract_git_archive(archive.getvalue(), destination)
    except UnsafeObservationPath:
        rejected = True

    assert (rejected, list(external.iterdir())) == (True, [])


@pytest.mark.skipif(os.name != "posix", reason="POSIX dirfd/no-follow confinement")
def test_lifecycle_tree_hardening_never_chmods_through_substituted_ancestor(
    tmp_path: Path,
) -> None:
    owned = tmp_path / "owned"
    external = tmp_path / "external-release"
    release = external / "release"
    release.mkdir(parents=True)
    artifact = release / "artifact.whl"
    artifact.write_bytes(b"external")
    release.chmod(0o755)
    artifact.chmod(0o644)
    before = (stat.S_IMODE(release.stat().st_mode), stat.S_IMODE(artifact.stat().st_mode))
    owned.symlink_to(external, target_is_directory=True)
    store = ReleaseStore(tmp_path / "data" / "aether")
    rejected = False
    try:
        store._harden_tree(owned / "release")
    except UnsafeObservationPath:
        rejected = True

    after = (stat.S_IMODE(release.stat().st_mode), stat.S_IMODE(artifact.stat().st_mode))
    assert (rejected, after) == (True, before)


@pytest.mark.skipif(os.name != "posix", reason="POSIX dirfd/no-follow confinement")
def test_lifecycle_mutation_lock_rejects_ancestor_substitution_without_relocation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state_root = tmp_path / "owned" / "state" / "aether"
    store = ReleaseStore(tmp_path / "data" / "aether", state_root=state_root)
    lock_parent = store.mutation_lock_file.parent
    external = tmp_path / "external-lock-parent"
    external.mkdir()
    real_ensure = ensure_private_dir
    swapped = False

    def ensure_then_swap(directory: Path) -> Path:
        nonlocal swapped
        result = real_ensure(directory)
        if Path(directory) == lock_parent and not swapped:
            swapped = True
            _swap_directory(lock_parent, external)
        return result

    monkeypatch.setattr(lifecycle_module, "ensure_private_dir", ensure_then_swap)
    before = _descriptor_snapshot()
    rejected = False
    try:
        try:
            with store.mutation_lock():
                pass
        except IntegrityError:
            rejected = True
        leaked = _descriptor_snapshot() - before
        assert swapped
        assert (rejected, list(external.iterdir()), leaked) == (True, [], set())
    finally:
        _close_descriptors(_descriptor_snapshot() - before)
