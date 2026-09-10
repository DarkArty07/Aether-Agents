#!/usr/bin/env python3
"""Reject operator-specific machine paths in tracked/public release artifacts."""

from __future__ import annotations

import argparse
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from aether_agents.objective_contracts.store import find_operator_path_violations  # noqa: E402


def _violations(label: str, payload: bytes) -> list[str]:
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError:
        return []
    kinds = find_operator_path_violations(text)
    return [f"{label}: {kind}" for kind in kinds]


def _tracked(root: Path) -> Iterable[tuple[str, bytes]]:
    completed = subprocess.run(
        ("git", "ls-files", "-z"),
        cwd=root,
        check=True,
        capture_output=True,
    )
    for raw in completed.stdout.split(b"\0"):
        if not raw:
            continue
        relative = raw.decode("utf-8", errors="strict")
        path = root / relative
        if path.is_file():
            yield relative, path.read_bytes()


def _archive(path: Path) -> Iterable[tuple[str, bytes]]:
    lower = path.name.lower()
    if lower.endswith((".whl", ".zip")):
        with zipfile.ZipFile(path) as archive:
            for info in archive.infolist():
                if not info.is_dir():
                    yield f"{path.name}!{info.filename}", archive.read(info)
        return
    if lower.endswith((".tar.gz", ".tgz", ".tar")):
        with tarfile.open(path, mode="r:*") as archive:
            for member in archive.getmembers():
                if member.isfile():
                    stream = archive.extractfile(member)
                    if stream is not None:
                        yield f"{path.name}!{member.name}", stream.read()
        return
    raise ValueError(f"unsupported artifact type: {path}")


def scan(root: Path, artifacts: Iterable[Path]) -> list[str]:
    failures: list[str] = []
    for label, payload in _tracked(root):
        failures.extend(_violations(label, payload))
    for artifact in artifacts:
        for label, payload in _archive(artifact):
            failures.extend(_violations(label, payload))
    return sorted(set(failures))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--artifact", type=Path, action="append", default=[])
    args = parser.parse_args(argv)
    root = args.root.resolve()
    failures = scan(root, [path.resolve() for path in args.artifact])
    if failures:
        print("public artifact path scan failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    print(f"public artifact path scan passed: tracked surface + {len(args.artifact)} artifact(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
