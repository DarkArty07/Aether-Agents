from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from scripts.run_harmonia_bounded_demo import bounded_payload

ROOT = Path(__file__).parents[2]
SCRIPT = ROOT / "scripts" / "run_harmonia_bounded_demo.py"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=ROOT, env=env, text=True, capture_output=True)


def test_bounded_demo_requires_explicit_isolated_opt_in():
    result = _run()
    assert result.returncode != 0
    assert "--confirm-isolated-demo" in result.stderr


def test_real_demo_requires_second_explicit_dispatch_opt_in():
    result = _run("--mode", "real-acp-manager", "--confirm-isolated-demo")
    assert result.returncode != 0
    assert "--confirm-real-acp-dispatch" in result.stderr


def test_real_payload_uses_kernel_materialized_response_evidence(tmp_path):
    payload = bounded_payload(
        tmp_path,
        "hefesto",
        "ictinus",
        "daedalus",
        response_delivery=True,
    )
    assert all(
        task["worker_permissions"] == ["read", "return_evidence"]
        for task in payload["contract"]["tasks"]
    )


def test_fake_demo_runs_full_bounded_lifecycle_and_reports_invariants():
    result = _run("--mode", "fake", "--confirm-isolated-demo")
    assert result.returncode == 0, result.stderr
    summary = json.loads(result.stdout)
    assert summary["committed"] is True
    assert summary["source_task_id"] == "task-a"
    assert summary["candidate_task_ids"] == ["task-c", "task-b"]
    assert summary["selected_task_id"] == "task-b"
    assert summary["selection_events"] == 1
    assert summary["selected_dispatches"] == 1
    assert summary["unselected_dispatches"] == 0
    assert summary["selected_attempts"] == 1
    assert summary["unselected_attempts"] == 0
    assert summary["cleanup_completed"] == 2
    assert summary["no_survivors"] is True
    assert summary["source_result"] == {"answer": "SOURCE_OK", "task_id": "task-a"}
    assert summary["selected_result"] == {
        "answer": "SELECTED_OK",
        "task_id": "task-b",
        "source_answer": "SOURCE_OK",
    }
    assert all(summary["invariants"].values())
