#!/usr/bin/env python3
"""Reject operator-specific machine paths in tracked/public release artifacts."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path
from typing import Iterable

# Build sensitive literals from components so the scanner does not flag itself.
_UNIX_HOME = re.compile(
    r"(?<![A-Za-z0-9_$}>])/(?:" + "home" + r"|" + "Users" + r")/[A-Za-z0-9._-]+/"
)
_WINDOWS_HOME = re.compile(r"(?i)(?<![A-Za-z0-9_$}>])[A-Z]:\\" + "Users" + r"\\[^\\\s]+\\")
_PRIVATE_DESKTOP = re.compile(
    r"(?i)(?<![A-Za-z0-9_<])(?:" + "Desktop" + r"|" + "Escritorio" + r")/(?:agentes|dev)/"
)


def _violations(label: str, payload: bytes) -> list[str]:
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError:
        return []
    kinds: list[str] = []
    if _UNIX_HOME.search(text):
        kinds.append("absolute-user-home")
    if _WINDOWS_HOME.search(text):
        kinds.append("windows-user-home")
    if _PRIVATE_DESKTOP.search(text):
        kinds.append("operator-desktop-layout")
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
