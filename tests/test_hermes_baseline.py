"""Regressions for the canonical Hermes release-baseline resource."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).parents[1]
DRIFT_CHECKER = ROOT / "scripts" / "check_hermes_baseline_drift.py"
TEST_BOOTSTRAP = ROOT / "scripts" / "run_tests.py"


def test_loader_reads_the_authoritative_machine_readable_resource() -> None:
    from aether_agents.hermes_baseline import load_hermes_baseline

    baseline = load_hermes_baseline()

    assert baseline.repository == "https://github.com/NousResearch/hermes-agent.git"
    assert baseline.tag == "v2026.8.18"
    assert baseline.tag_object == "9f13bbbf8423427e159c78066356ca0e27ca6b74"
    assert baseline.commit == "e624e9fde561e1add9388384012b295fde669ade"
    assert baseline.distribution == "hermes-agent"
    assert baseline.version == "0.20.4"
    assert baseline.python_requires == ">=3.11,<3.14"
    assert (
        baseline.observer_entry_point
        == "aether-contract-observer=aether_agents.observation.capture.hermes_plugin"
    )


def test_lifecycle_compatibility_export_is_loaded_from_the_resource() -> None:
    import aether_agents.lifecycle as lifecycle
    from aether_agents.hermes_baseline import HermesBaseline, load_hermes_baseline

    assert lifecycle.HermesBaseline is HermesBaseline
    assert lifecycle.HERMES_BASELINE == load_hermes_baseline()


def test_drift_checker_validates_derived_and_historical_baseline_references() -> None:
    completed = subprocess.run(
        [sys.executable, str(DRIFT_CHECKER), "--root", str(ROOT), "--json"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result["baseline"]["tag"] == "v2026.8.18"
    assert result["baseline"]["commit"] == "e624e9fde561e1add9388384012b295fde669ade"
    assert "HERMES_LOCAL_PATCHES.md" in result["historical_snapshot_paths"]


def test_drift_checker_rejects_a_changed_derived_baseline_value(tmp_path: Path) -> None:
    from aether_agents.hermes_baseline import load_hermes_baseline_resource

    resource = load_hermes_baseline_resource()
    for document in resource.derived_documents:
        destination = tmp_path / document.path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((ROOT / document.path).read_bytes())
    for snapshot in resource.historical_snapshots:
        destination = tmp_path / snapshot.path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text("classified fixture\n", encoding="utf-8")
    roadmap = tmp_path / "ROADMAP.md"
    roadmap.write_text(
        roadmap.read_text(encoding="utf-8").replace(resource.baseline.commit, "0" * 40),
        encoding="utf-8",
    )

    completed = subprocess.run(
        [sys.executable, str(DRIFT_CHECKER), "--root", str(tmp_path)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    assert "derived document drift: ROADMAP.md is missing commit" in completed.stderr


def test_bootstrap_verifies_the_selected_checkout_and_injects_it_first(
    monkeypatch,
    tmp_path: Path,
) -> None:
    spec = importlib.util.spec_from_file_location("run_tests_bootstrap", TEST_BOOTSTRAP)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    checkout = tmp_path / "hermes"
    checkout.mkdir()
    verified: dict[str, object] = {}
    executed: dict[str, object] = {}

    def verify(candidate, **expected):
        verified["candidate"] = candidate
        verified.update(expected)
        return SimpleNamespace(path=checkout.resolve(), clean=True)

    def run(arguments, **kwargs):
        executed["arguments"] = arguments
        executed.update(kwargs)
        return subprocess.CompletedProcess(arguments, 0)

    monkeypatch.setattr(module, "verify_clean_checkout", verify)
    monkeypatch.setattr(module.subprocess, "run", run)

    completed = module.run_tests(checkout, ["-q"])

    assert completed.returncode == 0
    assert verified["candidate"] == checkout
    assert verified["expected_tag"] == module.HERMES_BASELINE.tag
    assert verified["expected_commit"] == module.HERMES_BASELINE.commit
    assert verified["expected_tag_object"] == module.HERMES_BASELINE.tag_object
    assert executed["arguments"] == [sys.executable, "-m", "pytest", "-q"]
    environment = executed["env"]
    assert isinstance(environment, dict)
    assert environment["PYTHONPATH"].split(os.pathsep)[0] == str(checkout.resolve())
