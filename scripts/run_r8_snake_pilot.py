#!/usr/bin/env python3
"""Run, resume, or inspect the fixed R8 Snake pilot through Olympus."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import stat
from pathlib import Path

from olympus_v3.acp_manager import ACPManager
from olympus_v3.config_loader import load_config
from olympus_v3.coordination import OlympusRuntimeAdapter
from olympus_v3.coordination.pilot import PilotCoordinator
from olympus_v3.coordination.pilot_compiler import compile_snake_manifest
from olympus_v3.coordination.pilot_model import (
    CANONICAL_CONTROL_ROOT,
    CANONICAL_PILOT_ROOT,
    PilotError,
    validate_pilot_root,
)
from olympus_v3.coordination.pilot_store import PilotStore
from olympus_v3.db import OlympusDB


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("action", choices=("start", "resume", "inspect"))
    value.add_argument("--root", default=str(CANONICAL_PILOT_ROOT))
    value.add_argument("--max-steps", type=int, default=10_000)
    return value


def _admit_root(
    action: str,
    root: Path,
    *,
    expected_root: Path = CANONICAL_PILOT_ROOT,
    control_root: Path = CANONICAL_CONTROL_ROOT,
) -> tuple[Path, Path, Path]:
    root = validate_pilot_root(root, expected_root=expected_root)
    control = Path(control_root)
    if not control.is_absolute() or control != control.resolve(strict=False) or control == root:
        raise PilotError("invalid pilot control root")
    marker = control / "marker.json"
    expected = {"pilot_id": "snake-r8", "root": str(root)}
    if action == "start":
        if root.exists() and any(root.iterdir()):
            raise PilotError("pilot root must be empty on first admission")
        if control.exists():
            raise PilotError("pilot control root already exists; use resume")
        root.mkdir(parents=True, exist_ok=True)
        control.mkdir(parents=True, mode=0o700)
        if control.is_symlink() or marker.is_symlink():
            raise PilotError("pilot control symlink rejected")
        fd = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        try:
            os.write(fd, json.dumps(expected, sort_keys=True).encode())
        finally:
            os.close(fd)
    else:
        if not root.is_dir() or not control.is_dir() or control.is_symlink() or marker.is_symlink():
            raise PilotError("valid existing pilot required")
        if stat.S_IMODE(control.stat(follow_symlinks=False).st_mode) != 0o700:
            raise PilotError("insecure pilot control permissions")
        if stat.S_IMODE(marker.stat(follow_symlinks=False).st_mode) != 0o600:
            raise PilotError("insecure pilot marker permissions")
        if json.loads(marker.read_text()) != expected:
            raise PilotError("pilot marker mismatch")
    store_path = control / "pilot.db"
    for candidate in (store_path, Path(f"{store_path}-wal"), Path(f"{store_path}-shm")):
        if candidate.is_symlink():
            raise PilotError("pilot store symlink rejected")
        if candidate.exists() and stat.S_IMODE(candidate.stat(follow_symlinks=False).st_mode) & 0o077:
            raise PilotError("insecure pilot store permissions")
    return root, control, store_path


async def run(args: argparse.Namespace) -> int:
    root, _control, store_path = _admit_root(args.action, Path(args.root))
    manifest = compile_snake_manifest(root=root)
    if args.action == "inspect" and not store_path.is_file():
        raise PilotError("pilot store required")
    store = PilotStore(store_path, control_root=_control)
    try:
        if args.action == "inspect":
            store.verify_manifest(manifest)
            print(json.dumps(store.snapshot(), sort_keys=True, indent=2))
            return 0
        config = load_config()
        database = OlympusDB(config.db_path)
        await database.connect()
        try:
            manager = ACPManager(config.profiles_dir, database)
            adapter = OlympusRuntimeAdapter(manager, project_id=manifest.project_id, enabled=True)
            coordinator = PilotCoordinator(adapter, store, manifest)
            complete = await coordinator.run(max_steps=args.max_steps)
            print(json.dumps({"complete": complete, **store.snapshot()}, sort_keys=True, indent=2))
            return 0 if complete else 2
        finally:
            await database.close()
    finally:
        store.close()


def main() -> int:
    try:
        return asyncio.run(run(parser().parse_args()))
    except (PilotError, ValueError, RuntimeError) as exc:
        print(json.dumps({"error": str(exc)}, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
