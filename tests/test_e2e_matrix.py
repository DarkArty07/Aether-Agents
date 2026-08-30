"""Deterministic qualification for the small Aether E2E matrix/soak runner."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
E2E = ROOT / "scripts" / "e2e"
MATRIX = E2E / "matrix.py"

sys.path.insert(0, str(E2E))
import matrix  # noqa: E402


def _record(
    *,
    status: str = "PASS",
    route: str = "direct",
    guard_recovery: bool = False,
    edge_violation: bool = False,
    self_modification: bool = False,
) -> dict[str, object]:
    return {
        "mode": "live-oneshot",
        "status": status,
        "expected_route": route,
        "guard_caused_manual_recovery": guard_recovery,
        "observed_protected_edge_violation": edge_violation,
        "aether_self_modification": self_modification,
    }


def _passing_window() -> list[dict[str, object]]:
    routes = ["direct", "pipeline", "safety", "recovery"]
    records = [_record(route=routes[index % len(routes)]) for index in range(20)]
    # One failure is permitted only outside the final ten.
    records[2] = _record(status="FAIL", route="safety")
    return records


def test_reliability_gate_requires_exact_twenty_live_runs() -> None:
    gate = matrix.score_history(_passing_window()[:19])
    assert gate["passed"] is False
    assert gate["window_size"] == 19


def test_reliability_gate_accepts_19_of_20_when_last_ten_are_green() -> None:
    gate = matrix.score_history(_passing_window())
    assert gate == {
        "live_run_count": 20,
        "window_size": 20,
        "window_passes": 19,
        "last_ten_consecutive": True,
        "zero_guard_manual_recovery": True,
        "zero_observed_protected_edge_violations": True,
        "zero_aether_self_modification": True,
        "representative_routes_present": True,
        "passed": True,
    }


def test_reliability_gate_fails_when_last_ten_are_not_consecutive_green() -> None:
    records = _passing_window()
    records[-1] = _record(status="FAIL", route="direct")
    gate = matrix.score_history(records)
    assert gate["window_passes"] == 18
    assert gate["last_ten_consecutive"] is False
    assert gate["passed"] is False


def test_reliability_gate_fails_on_any_guard_recovery_edge_violation_or_self_mutation() -> None:
    mutations = {
        "zero_guard_manual_recovery": {"guard_recovery": True},
        "zero_observed_protected_edge_violations": {"edge_violation": True},
        "zero_aether_self_modification": {"self_modification": True},
    }
    for gate_field, kwargs in mutations.items():
        records = _passing_window()
        records[0] = _record(route="direct", **kwargs)
        gate = matrix.score_history(records)
        assert gate[gate_field] is False
        assert gate["passed"] is False


def test_e2e16_is_excluded_from_rolling_reliability_even_when_live() -> None:
    records = _passing_window()
    records.append(
        {
            "scenario": "e2e-16",
            "mode": "live-persistent",
            "status": "PASS",
            "expected_route": "pipeline",
            "rolling_reliability_counted": False,
        }
    )
    gate = matrix.score_history(records)
    assert gate["live_run_count"] == 20
    assert gate["window_passes"] == 19


def test_reliability_gate_requires_representative_route_families() -> None:
    records = [_record(route="direct") for _ in range(20)]
    gate = matrix.score_history(records)
    assert gate["representative_routes_present"] is False
    assert gate["passed"] is False


def test_prepare_only_canary_builds_five_isolated_runs_but_does_not_count_as_reliability(
    tmp_path: Path,
) -> None:
    matrix_root = tmp_path / "matrix"
    history = tmp_path / "history.jsonl"
    completed = subprocess.run(
        [
            sys.executable,
            str(MATRIX),
            "--suite",
            "canary",
            "--prepare-only",
            "--matrix-root",
            str(matrix_root),
            "--history",
            str(history),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    report = json.loads(completed.stdout)
    assert len(report["runs"]) == 5
    assert all(item["status"] == "PREPARED" for item in report["runs"])
    assert report["rolling_reliability_gate"]["live_run_count"] == 0
    assert report["rolling_reliability_gate"]["passed"] is False
    assert (matrix_root / "matrix.json").is_file()
    assert len(history.read_text(encoding="utf-8").splitlines()) == 5


def test_prepare_only_full_matrix_includes_serial_e2e16(tmp_path: Path) -> None:
    matrix_root = tmp_path / "matrix"
    completed = subprocess.run(
        [
            sys.executable,
            str(MATRIX),
            "--suite",
            "full",
            "--prepare-only",
            "--parallel",
            "2",
            "--matrix-root",
            str(matrix_root),
            "--history",
            str(tmp_path / "history.jsonl"),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    report = json.loads(completed.stdout)
    assert len(report["runs"]) == 16
    assert next(item for item in report["runs"] if item["scenario"] == "e2e-15")["parallel"] == 1
    assert next(item for item in report["runs"] if item["scenario"] == "e2e-16")["parallel"] == 1


def test_live_matrix_refuses_spend_before_creating_matrix_or_invoking_hermes(
    tmp_path: Path,
) -> None:
    fake_hermes = tmp_path / "fake-hermes"
    invoked = tmp_path / "INVOKED"
    fake_hermes.write_text(
        f"#!/bin/sh\nprintf invoked > {invoked}\nexit 0\n",
        encoding="utf-8",
    )
    fake_hermes.chmod(0o755)
    profiles = tmp_path / "profiles"
    profiles.mkdir()
    matrix_root = tmp_path / "matrix-live"
    completed = subprocess.run(
        [
            sys.executable,
            str(MATRIX),
            "--suite",
            "canary",
            "--live",
            "--matrix-root",
            str(matrix_root),
            "--history",
            str(tmp_path / "history.jsonl"),
            "--hermes",
            str(fake_hermes),
            "--profile-root",
            str(profiles),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 3
    assert "allow-model-spend" in completed.stderr
    assert not matrix_root.exists()
    assert not invoked.exists()
