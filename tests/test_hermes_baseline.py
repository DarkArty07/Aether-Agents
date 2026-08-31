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
POLICY_WORKFLOW = ROOT / ".github" / "workflows" / "policy.yml"


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
    monkeypatch.setenv("PYTHONPATH", "/ambient/pythonpath")
    monkeypatch.setenv("HERMES_DELEGATED_CHILD_CONTEXT", "delegated-child")

    completed = module.run_tests(checkout, ["-q"])

    assert completed.returncode == 0
    assert verified["candidate"] == checkout
    assert verified["expected_tag"] == module.HERMES_BASELINE.tag
    assert verified["expected_commit"] == module.HERMES_BASELINE.commit
    assert verified["expected_tag_object"] == module.HERMES_BASELINE.tag_object
    assert executed["arguments"] == [sys.executable, "-m", "pytest", "-q"]
    environment = executed["env"]
    assert isinstance(environment, dict)
    assert environment["PYTHONPATH"].split(os.pathsep) == [
        str(checkout.resolve()),
        "/ambient/pythonpath",
    ]
    assert environment["AETHER_EXACT_HERMES_CHECKOUT"] == str(checkout.resolve())
    assert "HERMES_DELEGATED_CHILD_CONTEXT" not in environment


def test_main_without_checkout_bootstraps_the_default_and_forwards_pytest_arguments(
    monkeypatch,
    tmp_path: Path,
) -> None:
    spec = importlib.util.spec_from_file_location("run_tests_default_bootstrap", TEST_BOOTSTRAP)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    cache_home = tmp_path / "cache"
    expected_target = cache_home / "aether-agents" / "hermes" / module.HERMES_BASELINE.tag
    resolved_checkout = tmp_path / "resolved-hermes"
    bootstrapped: list[Path] = []
    executed: dict[str, object] = {}

    def checkout_exact(target: Path) -> dict[str, str]:
        bootstrapped.append(target)
        return {"path": str(resolved_checkout)}

    def run_tests(
        checkout: Path, pytest_arguments: list[str]
    ) -> subprocess.CompletedProcess[bytes]:
        executed["checkout"] = checkout
        executed["pytest_arguments"] = pytest_arguments
        return subprocess.CompletedProcess([], 0)

    monkeypatch.delenv("AETHER_EXACT_HERMES_CHECKOUT", raising=False)
    monkeypatch.setenv("XDG_CACHE_HOME", str(cache_home))
    monkeypatch.setattr(module, "checkout_exact", checkout_exact, raising=False)
    monkeypatch.setattr(module, "run_tests", run_tests)

    assert module.main(["--", "-q", "tests/test_hermes_baseline.py"]) == 0
    assert bootstrapped == [expected_target]
    assert executed == {
        "checkout": resolved_checkout,
        "pytest_arguments": ["-q", "tests/test_hermes_baseline.py"],
    }


def test_main_without_checkout_prefers_the_configured_exact_checkout(
    monkeypatch,
    tmp_path: Path,
) -> None:
    spec = importlib.util.spec_from_file_location("run_tests_configured_bootstrap", TEST_BOOTSTRAP)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    configured_checkout = tmp_path / "configured-hermes"
    executed: dict[str, object] = {}

    def checkout_exact(_target: Path) -> dict[str, str]:
        raise AssertionError("configured checkout must not trigger a network bootstrap")

    def run_tests(
        checkout: Path, pytest_arguments: list[str]
    ) -> subprocess.CompletedProcess[bytes]:
        executed["checkout"] = checkout
        executed["pytest_arguments"] = pytest_arguments
        return subprocess.CompletedProcess([], 0)

    monkeypatch.setenv("AETHER_EXACT_HERMES_CHECKOUT", str(configured_checkout))
    monkeypatch.setattr(module, "checkout_exact", checkout_exact)
    monkeypatch.setattr(module, "run_tests", run_tests)

    assert module.main(["--", "-q"]) == 0
    assert executed == {"checkout": configured_checkout, "pytest_arguments": ["-q"]}


def test_main_preserves_an_explicit_checkout_for_ci_or_debugging(
    monkeypatch,
    tmp_path: Path,
) -> None:
    spec = importlib.util.spec_from_file_location("run_tests_explicit_checkout", TEST_BOOTSTRAP)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    explicit_checkout = tmp_path / "explicit-hermes"
    executed: dict[str, object] = {}

    def run_tests(
        checkout: Path, pytest_arguments: list[str]
    ) -> subprocess.CompletedProcess[bytes]:
        executed["checkout"] = checkout
        executed["pytest_arguments"] = pytest_arguments
        return subprocess.CompletedProcess([], 0)

    monkeypatch.setenv("AETHER_EXACT_HERMES_CHECKOUT", str(tmp_path / "configured-hermes"))
    monkeypatch.setattr(module, "run_tests", run_tests)

    assert module.main(["--checkout", str(explicit_checkout), "--", "-q"]) == 0
    assert executed == {"checkout": explicit_checkout, "pytest_arguments": ["-q"]}


def test_main_fails_closed_when_default_checkout_bootstrap_errors(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    spec = importlib.util.spec_from_file_location("run_tests_bootstrap_error", TEST_BOOTSTRAP)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    def checkout_exact(_target: Path) -> dict[str, str]:
        raise RuntimeError("public Hermes checkout failed")

    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    monkeypatch.delenv("AETHER_EXACT_HERMES_CHECKOUT", raising=False)
    monkeypatch.setattr(module, "checkout_exact", checkout_exact)

    assert module.main([]) == 1
    assert (
        "exact Hermes test bootstrap failed: public Hermes checkout failed"
        in capsys.readouterr().err
    )


def test_main_fails_closed_on_an_invalid_cached_checkout(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    spec = importlib.util.spec_from_file_location("run_tests_cached_mismatch", TEST_BOOTSTRAP)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    cache_home = tmp_path / "cache"
    cached_checkout = cache_home / "aether-agents" / "hermes" / module.HERMES_BASELINE.tag
    cached_checkout.mkdir(parents=True)

    def checkout_exact(_target: Path) -> dict[str, str]:
        raise AssertionError("an existing cache entry must not be rewritten after a mismatch")

    def verify_clean_checkout(_checkout: Path, **_expected: str) -> None:
        raise module.IntegrityError("Hermes checkout commit mismatch")

    monkeypatch.setenv("XDG_CACHE_HOME", str(cache_home))
    monkeypatch.delenv("AETHER_EXACT_HERMES_CHECKOUT", raising=False)
    monkeypatch.setattr(module, "checkout_exact", checkout_exact)
    monkeypatch.setattr(module, "verify_clean_checkout", verify_clean_checkout)

    assert module.main([]) == 1
    assert (
        "exact Hermes test bootstrap failed: Hermes checkout commit mismatch"
        in capsys.readouterr().err
    )


def test_ci_exercises_the_no_argument_bootstrap_against_the_checkout_it_created() -> None:
    workflow = POLICY_WORKFLOW.read_text(encoding="utf-8")
    bootstrap_step = workflow.split("      - name: Run exact-Hermes test bootstrap\n", 1)[1].split(
        "      - name:", 1
    )[0]

    assert 'AETHER_EXACT_HERMES_CHECKOUT: "${RUNNER_TEMP}/hermes-exact"' in bootstrap_step
    assert (
        "uv run --frozen python scripts/run_tests.py\n          -- tests/test_hermes_baseline.py -q"
        in bootstrap_step
    )
    assert "--checkout" not in bootstrap_step
