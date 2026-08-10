"""M4/M5 deterministic worker fixture contracts."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/aether_mcp/deterministic_worker.py"


def _run(root: Path, mode: str, *extra: str, timeout: int = 5) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(FIXTURE),
            "--root",
            str(root),
            "--artifact",
            "result.json",
            "--worker",
            "fixture-1",
            "--mode",
            mode,
            "--timeout",
            "2",
            *extra,
        ],
        cwd=root,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def test_success_is_deterministic_and_writes_one_allowlisted_artifact(tmp_path: Path) -> None:
    first = _run(tmp_path, "success")
    assert first.returncode == 0
    payload = (tmp_path / "result.json").read_bytes()
    (tmp_path / "result.json").unlink()
    second = _run(tmp_path, "success")
    assert second.returncode == 0
    assert (tmp_path / "result.json").read_bytes() == payload
    events = [json.loads(line) for line in second.stdout.splitlines()]
    assert [event["kind"] for event in events] == ["progress", "artifact", "completed"]


def test_question_waits_for_correlated_answer(tmp_path: Path) -> None:
    command = [
        sys.executable,
        str(FIXTURE),
        "--root",
        str(tmp_path),
        "--artifact",
        "result.json",
        "--worker",
        "fixture-q",
        "--mode",
        "question",
        "--question-file",
        "question.json",
        "--answer-file",
        "answer.txt",
        "--timeout",
        "3",
    ]
    process = subprocess.Popen(command, cwd=tmp_path, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline and not (tmp_path / "question.json").exists():
        time.sleep(0.02)
    assert (tmp_path / "question.json").exists()
    (tmp_path / "answer.txt").write_text("approved\n", encoding="utf-8")
    stdout, stderr = process.communicate(timeout=3)
    assert process.returncode == 0, stderr
    assert json.loads((tmp_path / "result.json").read_text())["answer"] == "approved"
    assert any(json.loads(line)["kind"] == "question" for line in stdout.splitlines())


def test_failure_boundaries_and_cancellation_are_distinct(tmp_path: Path) -> None:
    before = _run(tmp_path, "fail-before")
    assert before.returncode == 21
    assert not (tmp_path / "result.json").exists()

    after = _run(tmp_path, "fail-after")
    assert after.returncode == 22
    assert (tmp_path / "result.json").is_file()
    (tmp_path / "result.json").unlink()

    (tmp_path / "cancel").touch()
    cancelled = _run(tmp_path, "success", "--cancel-file", "cancel")
    assert cancelled.returncode == 23
    assert not (tmp_path / "result.json").exists()


def test_barrier_proves_two_workers_overlap(tmp_path: Path) -> None:
    barrier = tmp_path / "barrier"
    barrier.mkdir()
    commands = []
    for worker in ("alpha", "beta"):
        worker_root = tmp_path / f"{worker}-root"
        worker_root.mkdir()
        commands.append(
            subprocess.Popen(
                [
                    sys.executable,
                    str(FIXTURE),
                    "--root",
                    str(worker_root),
                    "--artifact",
                    "result.json",
                    "--worker",
                    worker,
                    "--mode",
                    "barrier",
                    "--barrier-dir",
                    str(barrier),
                    "--shared-root",
                    str(tmp_path),
                    "--peers",
                    "2",
                    "--timeout",
                    "3",
                ],
                cwd=worker_root,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        )
    results = [process.communicate(timeout=5) for process in commands]
    assert [process.returncode for process in commands] == [0, 0], results
    assert json.loads((tmp_path / "alpha-root/result.json").read_text())["overlap"] == ["alpha", "beta"]
    assert json.loads((tmp_path / "beta-root/result.json").read_text())["overlap"] == ["alpha", "beta"]
