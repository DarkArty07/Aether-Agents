#!/usr/bin/env python3
"""Install, verify, or restore Aether's canonical profile policy hook.

This tool only reads and writes the three hook targets beneath an explicitly
provided Hermes home. It never edits profile configuration or starts, stops, or
reloads any process.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import tempfile
from pathlib import Path
from typing import Any, NoReturn

ROOT = Path(__file__).resolve().parents[1]
CANONICAL_HOOK = ROOT / "policy" / "hooks" / "aether_pre_tool_policy.py"
HOOK_NAME = CANONICAL_HOOK.name
PROFILES = ("morfeo", "supervisor", "implementer")
MANIFEST_NAME = "manifest.json"
INSTALL_MODE = 0o755


class SyncError(RuntimeError):
    """A safe synchronization precondition failed."""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _emit(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def _fail(message: str, *, code: int = 2) -> NoReturn:
    _emit({"result": "error", "error": message})
    raise SystemExit(code)


def _resolved_home(home: Path) -> Path:
    return home.expanduser().resolve(strict=False)


def _target(home: Path, profile: str) -> Path:
    target = home / "profiles" / profile / "hooks" / HOOK_NAME
    resolved = target.resolve(strict=False)
    if not resolved.is_relative_to(home):
        raise SyncError(f"hook target escapes the selected home: {profile}")
    if target.is_symlink():
        raise SyncError(f"hook target must not be a symlink: {profile}")
    return target


def _atomic_write(path: Path, data: bytes, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=path.parent, prefix=f".{path.name}.", delete=False
        ) as stream:
            temporary = Path(stream.name)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.chmod(mode)
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _canonical() -> tuple[bytes, str]:
    if not CANONICAL_HOOK.is_file() or CANONICAL_HOOK.is_symlink():
        raise SyncError("canonical hook is missing or is not a regular file")
    data = CANONICAL_HOOK.read_bytes()
    return data, _sha256(data)


def _profile_report(home: Path, canonical_hash: str) -> list[dict[str, Any]]:
    profiles: list[dict[str, Any]] = []
    for profile in PROFILES:
        target = _target(home, profile)
        exists = target.is_file()
        installed_hash = _sha256(target.read_bytes()) if exists else None
        mode = stat.S_IMODE(target.stat().st_mode) if exists else None
        profiles.append(
            {
                "profile": profile,
                "path": target.relative_to(home).as_posix(),
                "exists": exists,
                "sha256": installed_hash,
                "mode": f"{mode:04o}" if mode is not None else None,
                "in_sync": installed_hash == canonical_hash and mode == INSTALL_MODE,
            }
        )
    return profiles


def check(home: Path) -> int:
    _, canonical_hash = _canonical()
    profiles = _profile_report(home, canonical_hash)
    in_sync = all(item["in_sync"] for item in profiles)
    _emit(
        {
            "result": "in_sync" if in_sync else "drift",
            "canonical_sha256": canonical_hash,
            "profiles": profiles,
        }
    )
    return 0 if in_sync else 1


def _backup_manifest(home: Path, backup_dir: Path, canonical_hash: str) -> dict[str, Any]:
    if backup_dir.exists():
        raise SyncError(f"backup directory already exists: {backup_dir}")
    backup_dir.mkdir(parents=True, mode=0o700)
    manifest: dict[str, Any] = {
        "version": 1,
        "canonical_sha256": canonical_hash,
        "profiles": {},
    }
    try:
        for profile in PROFILES:
            target = _target(home, profile)
            relative = Path("profiles") / profile / "hooks" / HOOK_NAME
            entry: dict[str, Any] = {
                "path": relative.as_posix(),
                "existed": target.is_file(),
                "installed_sha256": canonical_hash,
            }
            if target.exists() and not target.is_file():
                raise SyncError(f"hook target is not a regular file: {profile}")
            if target.is_file():
                data = target.read_bytes()
                entry["sha256"] = _sha256(data)
                entry["mode"] = stat.S_IMODE(target.stat().st_mode)
                backup = backup_dir / relative
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, backup)
            manifest["profiles"][profile] = entry
        (backup_dir / MANIFEST_NAME).write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    except Exception:
        shutil.rmtree(backup_dir, ignore_errors=True)
        raise
    return manifest


def _read_manifest(backup_dir: Path) -> dict[str, Any]:
    path = backup_dir / MANIFEST_NAME
    if not path.is_file() or path.is_symlink():
        raise SyncError(f"backup manifest is missing: {path}")
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SyncError(f"backup manifest is invalid: {exc}") from exc
    if manifest.get("version") != 1:
        raise SyncError("unsupported backup manifest version")
    profiles = manifest.get("profiles")
    if not isinstance(profiles, dict) or set(profiles) != set(PROFILES):
        raise SyncError("backup manifest has an invalid profile set")
    return manifest


def _validate_restore(home: Path, backup_dir: Path, manifest: dict[str, Any]) -> None:
    expected_canonical = manifest.get("canonical_sha256")
    if not isinstance(expected_canonical, str):
        raise SyncError("backup manifest lacks the installed canonical hash")
    for profile in PROFILES:
        entry = manifest["profiles"][profile]
        expected_path = (Path("profiles") / profile / "hooks" / HOOK_NAME).as_posix()
        if entry.get("path") != expected_path:
            raise SyncError(f"backup manifest path mismatch: {profile}")
        target = _target(home, profile)
        if (
            not target.is_file()
            or _sha256(target.read_bytes()) != expected_canonical
            or stat.S_IMODE(target.stat().st_mode) != INSTALL_MODE
        ):
            raise SyncError(
                f"installed hook content or mode drifted after backup; "
                f"refusing to overwrite: {profile}"
            )
        if entry.get("existed"):
            backup = backup_dir / expected_path
            if not backup.is_file() or backup.is_symlink():
                raise SyncError(f"backup hook is missing: {profile}")
            if _sha256(backup.read_bytes()) != entry.get("sha256"):
                raise SyncError(f"backup hook hash mismatch: {profile}")
            if not isinstance(entry.get("mode"), int):
                raise SyncError(f"backup hook mode is invalid: {profile}")


def _restore_entries(
    home: Path, backup_dir: Path, manifest: dict[str, Any], *, enforce_current: bool
) -> None:
    if enforce_current:
        _validate_restore(home, backup_dir, manifest)
    for profile in PROFILES:
        entry = manifest["profiles"][profile]
        target = _target(home, profile)
        if entry.get("existed"):
            backup = backup_dir / entry["path"]
            _atomic_write(target, backup.read_bytes(), int(entry["mode"]))
        else:
            target.unlink(missing_ok=True)


def install(home: Path, backup_dir: Path) -> int:
    canonical, canonical_hash = _canonical()
    manifest = _backup_manifest(home, backup_dir, canonical_hash)
    try:
        for profile in PROFILES:
            _atomic_write(_target(home, profile), canonical, INSTALL_MODE)
        profiles = _profile_report(home, canonical_hash)
        if not all(item["in_sync"] for item in profiles):
            raise SyncError("post-install parity verification failed")
    except Exception:
        _restore_entries(home, backup_dir, manifest, enforce_current=False)
        raise
    _emit(
        {
            "result": "installed",
            "canonical_sha256": canonical_hash,
            "backup_dir": str(backup_dir),
            "profiles": profiles,
        }
    )
    return 0


def restore(home: Path, backup_dir: Path) -> int:
    manifest = _read_manifest(backup_dir)
    _restore_entries(home, backup_dir, manifest, enforce_current=True)
    _emit(
        {
            "result": "restored",
            "backup_dir": str(backup_dir),
            "profiles": list(PROFILES),
        }
    )
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("check", "install", "restore"))
    parser.add_argument(
        "--home",
        required=True,
        type=Path,
        help="Hermes home containing profiles/<role>/hooks",
    )
    parser.add_argument(
        "--backup-dir",
        type=Path,
        help="new backup directory for install, or existing backup for restore",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    home = _resolved_home(args.home)
    try:
        if args.action == "check":
            return check(home)
        if args.backup_dir is None:
            raise SyncError(f"--backup-dir is required for {args.action}")
        backup_dir = args.backup_dir.expanduser().resolve(strict=False)
        if args.action == "install":
            return install(home, backup_dir)
        return restore(home, backup_dir)
    except SyncError as exc:
        _fail(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
