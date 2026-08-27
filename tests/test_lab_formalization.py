from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from aether_agents import lab
from aether_agents.lab import persistent

FORBIDDEN_EVIDENCE_KEYS = {
    "environment",
    "credentials",
    "prompt",
    "response",
    "command",
    "stdout",
    "stderr",
    "files",
    "diff",
    "logs",
    "events",
    "raw",
}


def test_formal_lab_loads_the_full_compatibility_set_from_packaged_resources() -> None:
    scenarios = [lab.load_scenario(f"e2e-{index:02d}") for index in range(1, 16)]
    assert [scenario.id for scenario in scenarios] == [f"e2e-{index:02d}" for index in range(1, 16)]
    assert lab.schema_bytes("scenario")
    assert lab.schema_bytes("fixture-manifest")
    assert lab.schema_bytes("evidence")


def test_scenario_validation_rejects_unknown_fields_and_invalid_acceptance(tmp_path: Path) -> None:
    invalid = {
        "id": "e2e-01",
        "fixture": "direct-text",
        "owner_message": "Do it",
        "expected_route": "direct",
        "acceptance_command": [],
        "unknown": "must be rejected",
    }
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(invalid), encoding="utf-8")
    with pytest.raises(lab.ScenarioError):
        lab.load_scenario(path)


def test_fixture_and_evidence_validation_rejects_malformed_inputs() -> None:
    fixture = lab.fixture_manifest()
    fixture["fixtures"][0]["unknown"] = "not allowed"
    with pytest.raises(ValueError):
        lab.validate_fixture_manifest(fixture)

    with pytest.raises(ValueError):
        lab.validate_evidence(
            {
                "schema_version": "aether.lab.evidence.v1",
                "kind": "run",
                "status": "PASS",
                "mode": "prepare-only",
                "command": "must never be evidence",
            }
        )


def test_prepare_only_emits_schema_valid_compact_evidence(tmp_path: Path) -> None:
    scenario = lab.load_scenario("e2e-01")
    result = lab.prepare_only(scenario, tmp_path / "run")
    assert result["status"] == "PREPARED"
    evidence = json.loads((tmp_path / "run" / "evidence" / "run.json").read_text())
    lab.validate_evidence(evidence)
    serialized = json.dumps(evidence, sort_keys=True).lower()
    assert not FORBIDDEN_EVIDENCE_KEYS.intersection(evidence)
    assert all(key not in serialized for key in FORBIDDEN_EVIDENCE_KEYS)


def test_observation_prepare_only_calls_registered_tool_for_each_action(tmp_path: Path) -> None:
    result = lab.prepare_observation_only(tmp_path / "observation")
    assert result["status"] == "PREPARED"
    assert result["suite"] == "observation"
    assert result["registered_tool"] == "aether_observe"
    assert {item["action"] for item in result["calls"]} == {"status", "changes", "diagnose"}
    assert all(item["success"] for item in result["calls"])
    assert result["calls"][0]["bytes"] <= 2048
    assert result["calls"][1]["bytes"] <= 2048
    assert result["calls"][2]["bytes"] <= 4096
    lab.validate_evidence(result)


def test_full_prepare_matrix_bounds_parallelism_and_serializes_e2e15(tmp_path: Path) -> None:
    matrix_root = tmp_path / "matrix"
    history = tmp_path / "history.jsonl"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "aether_agents.lab.matrix",
            "--suite",
            "full",
            "--prepare-only",
            "--parallel",
            "2",
            "--matrix-root",
            str(matrix_root),
            "--history",
            str(history),
        ],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    report = json.loads(completed.stdout)
    assert len(report["runs"]) == 15
    assert report["parallel"] == 2
    assert report["isolation_verified"] is True
    assert report["rolling_reliability_gate"]["live_run_count"] == 0
    assert next(item for item in report["runs"] if item["scenario"] == "e2e-15")["parallel"] == 1
    assert len([path for path in matrix_root.iterdir() if path.is_dir()]) == 15


def test_persistent_probe_rejects_one_shot_and_reports_native_capability_wall() -> None:
    one_shot = persistent.qualify_persistent_evidence(
        {
            "session_id": "sid_native",
            "continuation_source": "harness",
            "native_board_event": True,
            "durable_report": True,
            "owner_messages": 1,
        }
    )
    assert one_shot.status == "CAPABILITY_WALL"
    assert one_shot.reason == "one_shot_continuation_non_qualifying"

    absent = persistent.qualify_persistent_evidence(
        {
            "session_id": "sid_native",
            "continuation_source": "native",
            "native_board_event": False,
            "durable_report": False,
            "owner_messages": 1,
        }
    )
    assert absent.status == "CAPABILITY_WALL"
    assert absent.reason == "native_same_session_wake_unobserved"


def test_persistent_probe_requires_same_session_and_single_owner_message() -> None:
    result = persistent.qualify_persistent_evidence(
        {
            "session_id": "sid_native",
            "wake_session_id": "sid_other",
            "continuation_source": "native",
            "native_board_event": True,
            "durable_report": True,
            "owner_messages": 2,
        }
    )
    assert result.status == "CAPABILITY_WALL"
    assert result.reason == "same_session_or_owner_message_requirement_failed"
