"""R7 deterministic isolated system simulation acceptance tests."""

import json

import pytest

from scripts.run_r7_shadow_benchmark import SCENARIOS, run_benchmark, run_scenario

EXPECTED = {
    "clean_single_task": "observed",
    "dependency_chain": "observed",
    "parallel_independent": "observed",
    "duplicate_dispatch": "mismatch",
    "runtime_unavailable_restored": "mismatch",
    "restart_rebuild_durable_registry": "observed",
    "budget_rejection": "mismatch",
    "reviewer_violation": "mismatch",
    "unknown_effect": "mismatch",
    "feature_disabled_rollback": "disabled",
}


def test_all_r7_scenarios_are_present_and_deterministic(tmp_path):
    assert tuple(SCENARIOS) == tuple(EXPECTED)
    first = {name: run_scenario(name, tmp_path / "one") for name in SCENARIOS}
    second = {name: run_scenario(name, tmp_path / "two") for name in SCENARIOS}
    assert {k: v["outcome"] for k, v in first.items()} == EXPECTED
    assert {k: v["outcome"] for k, v in second.items()} == EXPECTED
    for name in SCENARIOS:
        assert first[name]["semantic_complete"] is False
        assert first[name]["lifecycle_effect_calls"] == 0
        assert first[name]["outcome"] == second[name]["outcome"]


@pytest.mark.parametrize("name", SCENARIOS)
def test_each_scenario_exposes_machine_checkable_agreement_and_detection(name, tmp_path):
    result = run_scenario(name, tmp_path)
    required = {"assignment", "participant", "session", "status"}
    assert required <= set(result["agreement"])
    assert isinstance(result["mismatch_detected"], bool)
    assert result["manual_reconciliation_steps_avoided"] >= 0


def test_disabled_path_does_not_touch_observer_session_or_store(tmp_path):
    result = run_scenario("feature_disabled_rollback", tmp_path)
    assert result["observer_reads"] == 0
    assert result["session_derivations"] == 0
    assert result["store_writes"] == 0
    assert result["rollback"] is True


def test_benchmark_schema_repeats_all_scenarios_without_sensitive_payloads(tmp_path):
    report = run_benchmark(tmp_path / "results.json", repetitions=5)
    assert report["schema_version"] == "r7-shadow-benchmark-v2"
    assert report["repetitions"] == 5
    assert set(report["scenarios"]) == set(SCENARIOS)
    assert report["lifecycle_effect_calls"] == 0
    assert report["cost"] == "unknown"
    assert "prompt" not in json.dumps(report).lower()
    assert all(len(items) == 5 for items in report["scenario_runs"].values())
    assert report["injected_failure_runs"] == 25
    assert report["detected_failure_runs"] == 25
    assert report["mismatch_detection_recall"] == 1.0
    assert report["clean_false_positive_rate"] == 0.0


def test_scenarios_use_real_shadow_evidence_and_typed_mismatches(tmp_path):
    clean = run_scenario("clean_single_task", tmp_path / "clean")
    failure = run_scenario("unknown_effect", tmp_path / "failure")
    recovered = run_scenario("runtime_unavailable_restored", tmp_path / "recovered")

    assert clean["observer_reads"] == 2
    assert clean["agreement"] == {
        "assignment": True,
        "participant": True,
        "session": True,
        "status": True,
    }
    assert failure["mismatches"] == ["status_mismatch", "unknown_effect"]
    assert "runtime_unavailable" in recovered["mismatches"]
    assert recovered["agreement"]["status"] is True
    assert recovered["recovery_time_ms"] >= 0


def test_durable_scenario_writes_and_recovers_actual_shadow_binding(tmp_path):
    result = run_scenario("restart_rebuild_durable_registry", tmp_path)

    assert result["store_writes"] == 1
    assert result["storage_growth_bytes"] > 0
    assert result["agreement"]["session"] is True
    assert result["mismatch_detected"] is False
