#!/usr/bin/env python3
"""Reviewed exact inventory and atomic restorer for Hermes release source.

Authority: Objective Contract oc_f190ae9e878151e6@v2 (SHA-256
9bd2828f6f13e086db394d3bb26afb289a23cb5f78293738594fb399c8567188),
in-scope items 1-2, AC-1, AC-2, and unit RS-RESTORE.

Outcomes:
1. Independently materializes git archive of maintained-fork
   commit aed6591a69f453a1867b73628603e7b53ba40ffc and proves
   _tree_sha256 == cc1ebf94ad167979951e7b956ef3a8c448e96fd3389c93cddf60f8f883bb5ce7.
2. Compares every expected path/type/hash against the target hermes-source:
   requires zero missing, zero changed, and extras confined strictly to
   node_modules/**, ui-tui/node_modules/**, or ui-tui/dist/entry.js. Any other
   delta refuses restoration with zero mutation.
3. Materializes and hardens a clean sibling on the same filesystem, atomically
   quarantines the contaminated tree outside the release (sibling of release_dir,
   never inside hermes-source, never deleted), and renames the clean tree into
   hermes-source.
4. On any injected failure (pre-swap refusal, swap rename, post-swap validation),
   rolls back to the original tree and leaves exactly one hermes-source (no
   ambiguous pair).
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import shutil
import stat
import sys
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from aether_agents.lifecycle import (
    IntegrityError,
    LifecycleManager,
    _fsync_directory,
    _harden_private_tree,
    _materialize_git_archive,
    _sha256,
    _tree_sha256,
)

EXPECTED_FORK_COMMIT = "aed6591a69f453a1867b73628603e7b53ba40ffc"
EXPECTED_FORK_TREE_SHA256 = "cc1ebf94ad167979951e7b956ef3a8c448e96fd3389c93cddf60f8f883bb5ce7"

ALLOWED_EXTRA_PREFIXES = ("node_modules/", "ui-tui/node_modules/")
ALLOWED_EXTRA_EXACT = ("ui-tui/dist/entry.js",)


class RestorationError(IntegrityError):
    """Refusal or failure during source inventory or atomic restoration."""


@dataclass(frozen=True)
class EntryClassification:
    relative_path: str
    is_symlink: bool
    is_regular: bool
    sha256: str | None


@dataclass(frozen=True)
class InventoryResult:
    clean_digest: str
    expected_files_count: int
    target_files_count: int
    missing_count: int
    changed_count: int
    extras_count: int
    extras_breakdown: dict[str, int]
    disallowed_extras: list[str]
    missing_files: list[str]
    changed_files: list[str]

    @property
    def is_restorable(self) -> bool:
        return (
            self.clean_digest == EXPECTED_FORK_TREE_SHA256
            and self.missing_count == 0
            and self.changed_count == 0
            and len(self.disallowed_extras) == 0
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RestorationResult:
    status: str
    release_dir: str
    target_source: str
    quarantine_path: str | None
    clean_digest: str
    inventory: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def scan_tree_entries(root: Path) -> dict[str, EntryClassification]:
    """Scan root tree entries excluding __pycache__, matching _tree_sha256 rules."""
    entries: dict[str, EntryClassification] = {}
    for directory, names, files in os.walk(root, followlinks=False):
        current = Path(directory)
        if current.is_symlink():
            raise RestorationError(f"source tree contains a symlink directory: {current}")
        names[:] = sorted(name for name in names if name != "__pycache__")
        for name in sorted(files):
            path = current / name
            st = os.lstat(path)
            is_symlink = stat.S_ISLNK(st.st_mode)
            is_reg = stat.S_ISREG(st.st_mode)
            if not (is_symlink or is_reg):
                raise RestorationError(
                    f"source tree contains non-regular, non-symlink entry: {path}"
                )
            relative = path.relative_to(root).as_posix()
            file_sha = _sha256(path) if is_reg else None
            entries[relative] = EntryClassification(
                relative_path=relative,
                is_symlink=is_symlink,
                is_regular=is_reg,
                sha256=file_sha,
            )
    return entries


def classify_hermes_source(target_source: Path, clean_tree: Path) -> InventoryResult:
    """Classify target hermes-source against clean materialized fork tree."""
    clean_digest = _tree_sha256(clean_tree)
    clean_entries = scan_tree_entries(clean_tree)
    target_entries = scan_tree_entries(target_source)

    clean_keys = set(clean_entries)
    target_keys = set(target_entries)

    missing = sorted(clean_keys - target_keys)
    changed: list[str] = []
    for rel in sorted(clean_keys & target_keys):
        c = clean_entries[rel]
        t = target_entries[rel]
        if t.is_symlink or not t.is_regular or t.sha256 != c.sha256:
            changed.append(rel)

    extras = sorted(target_keys - clean_keys)
    disallowed_extras: list[str] = []
    nm_count = 0
    tui_nm_count = 0
    entry_js_count = 0
    symlink_count = 0

    for rel in extras:
        entry = target_entries[rel]
        if entry.is_symlink:
            symlink_count += 1
        is_allowed = (
            rel.startswith(ALLOWED_EXTRA_PREFIXES[0])
            or rel.startswith(ALLOWED_EXTRA_PREFIXES[1])
            or rel in ALLOWED_EXTRA_EXACT
        )
        if not is_allowed:
            disallowed_extras.append(rel)
            continue
        if rel.startswith(ALLOWED_EXTRA_PREFIXES[0]):
            nm_count += 1
        elif rel.startswith(ALLOWED_EXTRA_PREFIXES[1]):
            tui_nm_count += 1
        elif rel in ALLOWED_EXTRA_EXACT:
            entry_js_count += 1

    extras_breakdown = {
        "node_modules": nm_count,
        "ui_tui_node_modules": tui_nm_count,
        "ui_tui_dist_entry_js": entry_js_count,
        "symlinks": symlink_count,
    }

    return InventoryResult(
        clean_digest=clean_digest,
        expected_files_count=len(clean_entries),
        target_files_count=len(target_entries),
        missing_count=len(missing),
        changed_count=len(changed),
        extras_count=len(extras),
        extras_breakdown=extras_breakdown,
        disallowed_extras=disallowed_extras,
        missing_files=missing,
        changed_files=changed,
    )


def assert_restorable_inventory(inventory: InventoryResult) -> None:
    """Assert inventory fulfills AC-1 exact contamination classification rules."""
    if inventory.clean_digest != EXPECTED_FORK_TREE_SHA256:
        raise RestorationError(
            f"clean archive digest mismatch: observed {inventory.clean_digest} != "
            f"expected {EXPECTED_FORK_TREE_SHA256}"
        )
    if inventory.missing_count > 0:
        sample = inventory.missing_files[:5]
        raise RestorationError(
            f"target source missing {inventory.missing_count} expected files (sample: {sample})"
        )
    if inventory.changed_count > 0:
        sample = inventory.changed_files[:5]
        raise RestorationError(
            f"target source has {inventory.changed_count} changed expected files (sample: {sample})"
        )
    if inventory.disallowed_extras:
        sample = inventory.disallowed_extras[:5]
        raise RestorationError(
            f"target source contains {len(inventory.disallowed_extras)} extras outside "
            f"closed allowlist (sample: {sample})"
        )


def restore_exact_hermes_source(
    release_dir: Path,
    fork_checkout: Path,
    *,
    fork_commit: str = EXPECTED_FORK_COMMIT,
    expected_digest: str = EXPECTED_FORK_TREE_SHA256,
    quarantine_path: Path | None = None,
    manager: LifecycleManager | None = None,
    dry_run: bool = False,
    inject_pre_swap_refusal: bool = False,
    inject_swap_failure: bool = False,
    inject_post_swap_failure: bool = False,
) -> RestorationResult:
    """Atomically restore release hermes-source to authenticated fork bytes.

    Quarantine is placed outside the release directory (sibling of release_dir),
    never inside hermes-source, and never deleted.
    Rollback occurs on any failure during pre-swap, swap rename, or post-swap validation.
    """
    release_dir = Path(release_dir).resolve()
    if not release_dir.is_dir() or release_dir.is_symlink():
        raise RestorationError(f"release directory must be a regular directory: {release_dir}")

    target_source = release_dir / "hermes-source"
    if not target_source.is_dir() or target_source.is_symlink():
        raise RestorationError(f"target hermes-source must be a regular directory: {target_source}")

    target_stat = os.stat(target_source)
    release_stat = os.stat(release_dir)
    if target_stat.st_dev != release_stat.st_dev:
        raise RestorationError(
            "cross-device operation refused: hermes-source and release directory must be on same filesystem"
        )

    if quarantine_path is None:
        timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d%H%M%S")
        quarantine_path = release_dir.parent / f"{release_dir.name}-quarantine-{timestamp}"
    else:
        quarantine_path = Path(quarantine_path).resolve()

    if quarantine_path.exists():
        raise RestorationError(f"quarantine path already exists: {quarantine_path}")

    quarantine_parent_stat = os.stat(quarantine_path.parent)
    if quarantine_parent_stat.st_dev != target_stat.st_dev:
        raise RestorationError(
            "cross-device operation refused: quarantine path must be on same filesystem as target source"
        )

    clean_staging = release_dir / f".hermes-source.clean.{uuid.uuid4().hex}"
    staging_created = False

    try:
        try:
            _materialize_git_archive(fork_checkout, fork_commit, clean_staging)
            staging_created = True
        except Exception as error:
            raise RestorationError(f"failed to materialize clean git archive: {error}") from error

        clean_digest = _tree_sha256(clean_staging)
        if clean_digest != expected_digest:
            raise RestorationError(
                f"clean archive digest mismatch: observed {clean_digest} != expected {expected_digest}"
            )

        _harden_private_tree(clean_staging)
        if _tree_sha256(clean_staging) != expected_digest:
            raise RestorationError("clean archive digest changed after hardening")

        inventory = classify_hermes_source(target_source, clean_staging)
        assert_restorable_inventory(inventory)

        if inject_pre_swap_refusal:
            raise RestorationError("injected pre-swap refusal")

        if dry_run:
            return RestorationResult(
                status="dry_run",
                release_dir=str(release_dir),
                target_source=str(target_source),
                quarantine_path=None,
                clean_digest=clean_digest,
                inventory=inventory.to_dict(),
            )

        swap_step = 0
        try:
            os.rename(target_source, quarantine_path)
            swap_step = 1

            if inject_swap_failure:
                raise OSError("injected swap rename failure")

            os.rename(clean_staging, target_source)
            swap_step = 2

            _fsync_directory(release_dir)
            _fsync_directory(quarantine_path.parent)

            post_digest = _tree_sha256(target_source)
            if post_digest != expected_digest:
                raise RestorationError(
                    f"post-swap target source digest mismatch: observed {post_digest} != expected {expected_digest}"
                )

            if inject_post_swap_failure:
                raise RestorationError("injected post-swap validation failure")

            if manager is not None:
                manager.validate_release(release_dir.name)

        except Exception as swap_error:
            if swap_step == 1:
                if quarantine_path.exists() and not target_source.exists():
                    os.rename(quarantine_path, target_source)
                    _fsync_directory(release_dir)
            elif swap_step == 2:
                temp_failed = release_dir / f".hermes-source.failed.{uuid.uuid4().hex}"
                if target_source.exists():
                    os.rename(target_source, temp_failed)
                if quarantine_path.exists() and not target_source.exists():
                    os.rename(quarantine_path, target_source)
                if temp_failed.exists():
                    shutil.rmtree(temp_failed, ignore_errors=True)
                _fsync_directory(release_dir)
            raise swap_error

        return RestorationResult(
            status="restored",
            release_dir=str(release_dir),
            target_source=str(target_source),
            quarantine_path=str(quarantine_path),
            clean_digest=post_digest,
            inventory=inventory.to_dict(),
        )

    finally:
        if staging_created and clean_staging.exists():
            shutil.rmtree(clean_staging, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Exact inventory and atomic restorer for Hermes release source."
    )
    parser.add_argument(
        "--release-dir",
        type=Path,
        help="Path to release directory (e.g. <data-root>/releases/<release-id>)",
    )
    parser.add_argument(
        "--fork-checkout",
        type=Path,
        default=Path("."),
        help="Path to Git repository checkout containing the fork commit",
    )
    parser.add_argument(
        "--fork-commit",
        default=EXPECTED_FORK_COMMIT,
        help="Exact fork commit SHA",
    )
    parser.add_argument(
        "--quarantine-path",
        type=Path,
        help="Optional destination path for quarantined contamination outside the release",
    )
    parser.add_argument(
        "--inventory-only",
        action="store_true",
        help="Perform read-only inventory classification against materialized fork commit",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Materialize and validate without performing rename or quarantine",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit result as JSON",
    )

    args = parser.parse_args()

    if args.release_dir is None:
        parser.error("--release-dir is required")

    release_dir = args.release_dir.resolve()
    target_source = release_dir / "hermes-source"

    if args.inventory_only:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            clean_tmp = Path(tmp) / "clean"
            _materialize_git_archive(args.fork_checkout, args.fork_commit, clean_tmp)
            inventory = classify_hermes_source(target_source, clean_tmp)
            if args.json:
                print(json.dumps(inventory.to_dict(), indent=2))
            else:
                print(f"Clean digest:         {inventory.clean_digest}")
                print(f"Expected files:       {inventory.expected_files_count}")
                print(f"Target files:         {inventory.target_files_count}")
                print(f"Missing files:        {inventory.missing_count}")
                print(f"Changed files:        {inventory.changed_count}")
                print(f"Extras total:         {inventory.extras_count}")
                print(f"Extras breakdown:     {inventory.extras_breakdown}")
                print(f"Disallowed extras:    {len(inventory.disallowed_extras)}")
                print(f"Restorable:           {inventory.is_restorable}")
            return 0 if inventory.is_restorable else 1

    try:
        res = restore_exact_hermes_source(
            release_dir,
            args.fork_checkout,
            fork_commit=args.fork_commit,
            quarantine_path=args.quarantine_path,
            dry_run=args.dry_run,
        )
        if args.json:
            print(json.dumps(res.to_dict(), indent=2))
        else:
            print(f"Status:          {res.status}")
            print(f"Clean digest:    {res.clean_digest}")
            print(f"Quarantine:      {res.quarantine_path}")
        return 0
    except RestorationError as error:
        if args.json:
            print(json.dumps({"status": "refused", "error": str(error)}, indent=2))
        else:
            print(f"Restoration refused: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
