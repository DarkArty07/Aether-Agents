from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from aether_agents import lab
from aether_agents.lab import matrix, persistent

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


def test_live_observation_invokes_supplied_runtime_once_after_spend_acknowledgement(
    tmp_path: Path,
) -> None:
    invoked = tmp_path / "hermes-invoked.json"
    fake_hermes = tmp_path / "hermes"
    fake_hermes.write_text(
        f'''#!/usr/bin/env python3
import json, os, sqlite3, sys
from pathlib import Path

open({str(invoked)!r}, "w", encoding="utf-8").write(
    json.dumps({{"argv": sys.argv[1:], "home": os.environ.get("HERMES_HOME")}})
)
usage = Path(sys.argv[sys.argv.index("--usage-file") + 1])
usage.write_text(json.dumps({{
    "model": "test-model",
    "provider": "test-provider",
    "api_calls": 1,
    "completed": True,
}}), encoding="utf-8")
database = Path(os.environ["HERMES_HOME"]) / "profiles" / "morfeo" / "state.db"
database.parent.mkdir(parents=True, exist_ok=True)
with sqlite3.connect(database) as connection:
    connection.execute("CREATE TABLE messages (role TEXT, content TEXT, tool_name TEXT, tool_calls TEXT)")
    for action, result in (
        ("status", {{"action": "status", "state": "ready", "summary_id": "sum_" + "a" * 64}}),
        ("changes", {{"action": "changes", "comparable": True}}),
        ("diagnose", {{"action": "diagnose", "verdict": "clear"}}),
    ):
        connection.execute(
            "INSERT INTO messages VALUES (?, ?, ?, ?)",
            ("tool", json.dumps(result), "aether_observe", None),
        )
print("aether_observe status changes diagnose completed")
''',
        encoding="utf-8",
    )
    fake_hermes.chmod(0o755)

    profile_root = tmp_path / "profiles"
    for role in ("morfeo", "supervisor", "implementer"):
        target = profile_root / role
        target.mkdir(parents=True)
        (target / "config.yaml").write_text(
            "hooks:\n"
            "  pre_tool_call:\n"
            "    - matcher: .*\n"
            "      command: /candidate/aether_pre_tool_policy.py\n",
            encoding="utf-8",
        )

    result = lab.live_observation(
        tmp_path / "observation-live",
        hermes=fake_hermes,
        profile_root=profile_root,
        allow_model_spend=True,
    )

    assert invoked.is_file(), "the caller-supplied Hermes executable was not invoked"
    payload = json.loads(invoked.read_text(encoding="utf-8"))
    assert "--in" in payload["argv"]
    assert "--oneshot" in payload["argv"]
    assert payload["argv"][payload["argv"].index("--toolsets") + 1] == "aether_observation"
    assert "chat" not in payload["argv"]
    assert "-q" not in payload["argv"]
    assert payload["home"]
    assert result["mode"] == "live-oneshot"
    assert result["rolling_reliability_counted"] is False
    assert result["registered_tool"] == "aether_observe"
    assert result["aether_observe_calls"] == 3
    assert result["model"] == "test-model"
    assert result["provider"] == "test-provider"
    assert result["api_calls"] == 1
    assert [(call["action"], call["success"], call["limit"]) for call in result["calls"]] == [
        ("status", True, 2048),
        ("changes", True, 2048),
        ("diagnose", True, 4096),
    ]
    assert result["provider_operationally_exercised"] is True
    assert result["forbidden_fallback_counts"] == {
        "terminal": 0,
        "file": 0,
        "raw_logs_events": 0,
    }
    assert result["cleanup"] == {"completed": True, "survivors": 0}
    assert result["private_runtime_retained"] is False
    assert not (tmp_path / "observation-live" / "hermes-home").exists()
    assert not (tmp_path / "observation-live" / "state").exists()
    assert not (tmp_path / "observation-live" / "project").exists()


def test_live_observation_rejects_missing_usage_and_forbidden_fallbacks(tmp_path: Path) -> None:
    fake_hermes = tmp_path / "hermes"
    fake_hermes.write_text(
        '''#!/usr/bin/env python3
import json, os, sqlite3, sys
from pathlib import Path

database = Path(os.environ["HERMES_HOME"]) / "profiles" / "morfeo" / "state.db"
database.parent.mkdir(parents=True, exist_ok=True)
with sqlite3.connect(database) as connection:
    connection.execute("CREATE TABLE messages (role TEXT, content TEXT, tool_name TEXT, tool_calls TEXT)")
    for name, result in (
        ("aether_observe", {"action": "status", "state": "ready", "summary_id": "sum_" + "a" * 64}),
        ("aether_observe", {"action": "changes", "comparable": True}),
        ("aether_observe", {"action": "diagnose", "verdict": "clear"}),
        ("terminal", {}),
        ("read_file", {}),
        ("raw_logs", {}),
    ):
        connection.execute(
            "INSERT INTO messages VALUES (?, ?, ?, ?)",
            ("tool", json.dumps(result), name, None),
        )
print("completed without a verifiable usage report")
''',
        encoding="utf-8",
    )
    fake_hermes.chmod(0o755)

    profile_root = tmp_path / "profiles"
    for role in ("morfeo", "supervisor", "implementer"):
        target = profile_root / role
        target.mkdir(parents=True)
        (target / "config.yaml").write_text(
            "hooks:\n"
            "  pre_tool_call:\n"
            "    - matcher: .*\n"
            "      command: /candidate/aether_pre_tool_policy.py\n",
            encoding="utf-8",
        )

    result = lab.live_observation(
        tmp_path / "observation-live",
        hermes=fake_hermes,
        profile_root=profile_root,
        allow_model_spend=True,
    )

    assert result["status"] == "FAIL"
    assert result["api_calls"] == 0
    assert result["provider_operationally_exercised"] is False
    assert result["aether_observe_calls"] == 3
    assert result["forbidden_fallback_counts"] == {
        "terminal": 1,
        "file": 1,
        "raw_logs_events": 1,
    }


def test_observation_records_do_not_contaminate_rolling_score_history() -> None:
    records = [
        {
            "mode": "live-oneshot",
            "status": "PASS",
            "expected_route": route,
            "guard_caused_manual_recovery": False,
            "observed_protected_edge_violation": False,
            "aether_self_modification": False,
        }
        for route in ("direct", "pipeline", "safety", "recovery") * 5
    ]
    observation = {
        "kind": "observation",
        "mode": "live-persistent",
        "status": "CAPABILITY_WALL",
        "rolling_reliability_counted": False,
    }

    gate = matrix.score_history(records + [observation])

    assert gate["live_run_count"] == 20
    assert gate["window_size"] == 20
    assert gate["window_passes"] == 20


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
    assert one_shot.qualified is False
    lab.validate_evidence(one_shot.to_evidence())

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
    assert absent.qualified is False
    lab.validate_evidence(absent.to_evidence())


def test_persistent_probe_serializes_valid_native_success_evidence() -> None:
    result = persistent.qualify_persistent_evidence(
        {
            "session_id": "sid_native",
            "wake_session_id": "sid_native",
            "continuation_source": "native",
            "native_board_event": True,
            "durable_report": True,
            "owner_messages": 1,
        }
    )

    assert result.status == "PASS"
    assert result.qualified is True
    evidence = result.to_evidence()
    assert evidence["status"] == "PASS"
    lab.validate_evidence(evidence)


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
    assert result.qualified is False
    lab.validate_evidence(result.to_evidence())
