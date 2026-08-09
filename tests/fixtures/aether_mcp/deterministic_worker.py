#!/usr/bin/env python3
"""Deterministic no-model worker fixture for M4/M5 qualification."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any


def emit(kind: str, **fields: Any) -> None:
    print(json.dumps({"kind": kind, **fields}, sort_keys=True, separators=(",", ":")), flush=True)


def bounded(root: Path, candidate: Path) -> Path:
    resolved_root = root.resolve(strict=True)
    target = candidate if candidate.is_absolute() else resolved_root / candidate
    parent = target.parent.resolve(strict=True)
    resolved = parent / target.name
    if not resolved.is_relative_to(resolved_root) or target.is_symlink():
        raise ValueError("artifact escapes the admitted root")
    return resolved


def atomic_json(path: Path, value: dict[str, Any]) -> str:
    payload = (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode()
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()
    return hashlib.sha256(payload).hexdigest()


def wait_for(path: Path, *, cancel: Path | None, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if cancel is not None and cancel.exists():
            emit("cancelled")
            raise SystemExit(23)
        if path.exists():
            return True
        time.sleep(0.02)
    emit("timeout", awaited=path.name)
    return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--worker", required=True)
    parser.add_argument("--mode", choices=("success", "question", "fail-before", "fail-after", "barrier"), required=True)
    parser.add_argument("--question-file", type=Path)
    parser.add_argument("--answer-file", type=Path)
    parser.add_argument("--cancel-file", type=Path)
    parser.add_argument("--release-file", type=Path)
    parser.add_argument("--barrier-dir", type=Path)
    parser.add_argument("--shared-root", type=Path)
    parser.add_argument("--peers", type=int, default=1)
    parser.add_argument("--timeout", type=float, default=10.0)
    args = parser.parse_args()

    root = args.root.resolve(strict=True)
    artifact = bounded(root, args.artifact)
    cancel = bounded(root, args.cancel_file) if args.cancel_file else None
    emit("progress", phase="started", worker=args.worker)
    if cancel is not None and cancel.exists():
        emit("cancelled")
        return 23
    if args.mode == "fail-before":
        emit("failed", phase="before_artifact")
        return 21

    answer: str | None = None
    if args.mode == "question":
        if args.question_file is None or args.answer_file is None:
            raise ValueError("question mode requires question and answer files")
        question = bounded(root, args.question_file)
        answer_path = bounded(root, args.answer_file)
        atomic_json(question, {"question": "approved-value?", "worker": args.worker})
        emit("question", thread_id=f"thread-{args.worker}")
        if not wait_for(answer_path, cancel=cancel, timeout=args.timeout):
            return 24
        answer = answer_path.read_text(encoding="utf-8").strip()

    overlap: list[str] = []
    if args.mode == "barrier":
        if args.barrier_dir is None or args.peers < 2:
            raise ValueError("barrier mode requires a barrier directory and peers")
        barrier_root = args.shared_root.resolve(strict=True) if args.shared_root is not None else root
        barrier = bounded(barrier_root, args.barrier_dir / "placeholder").parent
        ready = barrier / f"{args.worker}.ready"
        atomic_json(ready, {"worker": args.worker})
        deadline = time.monotonic() + args.timeout
        while time.monotonic() < deadline:
            overlap = sorted(path.stem for path in barrier.glob("*.ready"))
            if len(overlap) >= args.peers:
                break
            if cancel is not None and cancel.exists():
                emit("cancelled")
                return 23
            time.sleep(0.02)
        if len(overlap) < args.peers:
            emit("timeout", awaited="barrier")
            return 24
        atomic_json(barrier / f"{args.worker}.overlap", {"peers": overlap, "worker": args.worker})
        emit("barrier_released", peers=overlap)

    artifact_digest = atomic_json(
        artifact,
        {
            "answer": answer,
            "mode": args.mode,
            "overlap": overlap,
            "result": "deterministic-fixture-output",
            "worker": args.worker,
        },
    )
    emit("artifact", path=artifact.name, sha256=artifact_digest)
    if args.mode == "fail-after":
        emit("failed", phase="after_artifact")
        return 22
    if args.release_file is not None:
        release = bounded(root, args.release_file)
        if not wait_for(release, cancel=cancel, timeout=args.timeout):
            return 24
    emit("completed", evidence_sha256=artifact_digest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
