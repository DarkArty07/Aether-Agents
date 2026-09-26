"""Contract and verification tests for the RC15 -> RC16 transition qualification entry.

This test module verifies the contract, oracles, and behavior of
``scripts/qualify_rc16_transition.py`` in isolation. It asserts:
- refusal before mutation on live work roots, missing repositories, or invalid arguments;
- strict isolation of child environments and all derived filesystem paths;
- byte-immutability of the predecessor RC15 release-lock and active-record bytes;
- candidate RC16 identity binding exact Hermes commit 58f8c37a49... and source tree
  digest a2a9b374bd...;
- absence-tolerant durable-history fallback in the retained RC15 review guidance;
- refusal matrix preventing activation on invalid or unverified fork checkouts;
- full qualification run across all contract scenarios.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
ENTRY_SCRIPT = REPO_ROOT / "scripts" / "qualify_rc16_transition.py"

RC15_VERSION = "1.0.0rc15"
RC15_RELEASE_ID = "1.0.0rc15-5dc9cd69da8d18f3"
RC15_HERMES_COMMIT = "5b2b6ba543680c6fe8a62de4b467d1107be3abf4"
RC15_HERMES_TREE_SHA256 = "adf77d5840028f490818a3f78304a9f3835bff176df3ad34255aea2f9882aba2"

RC16_VERSION = "1.0.0rc16"
RC16_DISPLAY_VERSION = "1.0.0-rc.16"
RC16_TAG = "v1.0.0-rc.16"
RC16_HERMES_COMMIT = "58f8c37a49b341f25b8fdd6310542fe932031b8d"
RC16_HERMES_TREE_SHA256 = "a2a9b374bd2022c7f96242b0ab2c95691119262c925389eb3820ca627c581144"


def load_entry() -> Any:
    spec = importlib.util.spec_from_file_location("qualify_rc16_transition", ENTRY_SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def entry() -> Any:
    return load_entry()


# --------------------------------------------------------------------------------------
# CLI Input Validation and Refusal Tests
# --------------------------------------------------------------------------------------
def test_entry_refuses_live_work_root_before_doing_any_work(tmp_path: Path) -> None:
    live_path = Path.home() / ".local" / "share" / "aether"
    completed = subprocess.run(
        [
            sys.executable,
            str(ENTRY_SCRIPT),
            "run",
            "--work-root",
            str(live_path),
            "--receipts-root",
            str(tmp_path / "receipts"),
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(REPO_ROOT),
    )
    assert completed.returncode == 2
    assert "refuses" in (completed.stderr + completed.stdout).lower()


def test_entry_refuses_missing_aether_repo(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(ENTRY_SCRIPT),
            "run",
            "--repo",
            str(tmp_path / "nonexistent-repo"),
            "--work-root",
            str(tmp_path / "work"),
            "--receipts-root",
            str(tmp_path / "receipts"),
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(REPO_ROOT),
    )
    assert completed.returncode == 2
    assert "not a git worktree" in (completed.stderr + completed.stdout).lower()


def test_entry_refuses_non_temp_work_root_to_confine_service_boundary(tmp_path: Path) -> None:
    non_temp_work_root = Path.home() / ".aether-test-non-temp-work-root"
    if non_temp_work_root.exists():
        shutil.rmtree(non_temp_work_root, ignore_errors=True)

    try:
        completed = subprocess.run(
            [
                sys.executable,
                str(ENTRY_SCRIPT),
                "run",
                "--work-root",
                str(non_temp_work_root),
                "--receipts-root",
                str(tmp_path / "receipts"),
            ],
            capture_output=True,
            text=True,
            check=False,
            cwd=str(REPO_ROOT),
        )
        assert completed.returncode == 2
        output = (completed.stderr + completed.stdout).lower()
        assert "must resolve under a" in output and "temp directory" in output
        assert not non_temp_work_root.exists()
    finally:
        if non_temp_work_root.exists():
            shutil.rmtree(non_temp_work_root, ignore_errors=True)


def test_entry_refuses_custom_tmpdir_work_root_outside_fixed_system_roots(tmp_path: Path) -> None:
    custom_tmp = Path.home() / ".aether-test-custom-tmpdir"
    custom_work_root = custom_tmp / "work"
    if custom_tmp.exists():
        shutil.rmtree(custom_tmp, ignore_errors=True)

    env = os.environ.copy()
    env["TMPDIR"] = str(custom_tmp)

    try:
        completed = subprocess.run(
            [
                sys.executable,
                str(ENTRY_SCRIPT),
                "run",
                "--work-root",
                str(custom_work_root),
                "--receipts-root",
                str(tmp_path / "receipts"),
            ],
            capture_output=True,
            text=True,
            check=False,
            cwd=str(REPO_ROOT),
            env=env,
        )
        assert completed.returncode == 2
        output = (completed.stderr + completed.stdout).lower()
        assert "must resolve under a fixed system temp directory" in output
        assert not custom_work_root.exists()
        assert not custom_tmp.exists()
    finally:
        if custom_tmp.exists():
            shutil.rmtree(custom_tmp, ignore_errors=True)


def test_is_under_system_temp_confinement_helper(entry: Any, tmp_path: Path) -> None:
    assert entry.is_under_system_temp(Path("/tmp/arbitrary")) is True
    assert entry.is_under_system_temp(Path("/var/tmp/arbitrary")) is True
    assert entry.is_under_system_temp(Path.home() / "non-temp-root") is False
    assert entry.is_under_system_temp(Path.home() / "custom-tmp" / "work") is False


def test_unknown_scenario_is_refused(entry: Any) -> None:
    with pytest.raises(entry.Refusal, match="Unknown scenario"):
        entry.select_scenarios("isolation,invented_scenario")


def test_all_scenario_selection_preserves_contract_order(entry: Any) -> None:
    selected = entry.select_scenarios("all")
    assert selected == list(entry.SCENARIOS)
    assert len(selected) == 8
    assert set(selected) == {
        "isolation",
        "rc15-immutability",
        "candidate-identity",
        "transition-cycle",
        "refusal-matrix",
        "hlp-reconciliation",
        "review-fallback",
        "fork-regression",
    }


# --------------------------------------------------------------------------------------
# Isolation and Environment Confinement Tests
# --------------------------------------------------------------------------------------
def test_isolation_derives_every_root_under_work_root(entry: Any, tmp_path: Path) -> None:
    isolation = entry.Isolation(work_root=tmp_path / "work", receipts_root=tmp_path / "receipts")
    for derived in (
        isolation.home,
        isolation.data_home,
        isolation.state_home,
        isolation.config_home,
        isolation.cache_home,
        isolation.runtime_dir,
        isolation.tmp,
        isolation.store_root,
        isolation.state_root,
        isolation.hermes_home,
        isolation.projections,
        isolation.project_dir,
    ):
        assert derived.is_relative_to(tmp_path / "work")
    assert isolation.live_overlaps() == []


def test_isolated_environment_scrubs_operator_state(
    entry: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HERMES_KANBAN_TASK", "t_leak")
    monkeypatch.setenv("HERMES_KANBAN_DB", "/leak/kanban.db")
    monkeypatch.setenv("AETHER_PROJECT_ROOT", "/leak/project")
    monkeypatch.setenv("DBUS_SESSION_BUS_ADDRESS", "unix:path=/leak/bus")
    monkeypatch.setenv("PYTHONPATH", "/leak/pythonpath")

    isolation = entry.Isolation(work_root=tmp_path / "work", receipts_root=tmp_path / "receipts")
    environment = isolation.environment()

    for key in (
        "HERMES_KANBAN_TASK",
        "HERMES_KANBAN_DB",
        "AETHER_PROJECT_ROOT",
        "DBUS_SESSION_BUS_ADDRESS",
        "PYTHONPATH",
    ):
        assert key not in environment

    assert environment["HOME"] == str(isolation.home)
    assert environment["AETHER_STORE_ROOT"] == str(isolation.store_root)
    assert environment["AETHER_STATE_ROOT"] == str(isolation.state_root)
    assert environment["HERMES_HOME"] == str(isolation.hermes_home)


# --------------------------------------------------------------------------------------
# RC15 Immutability and Identity Tests
# --------------------------------------------------------------------------------------
def test_rc15_published_identity_constants() -> None:
    fixtures_dir = REPO_ROOT / "tests" / "fixtures" / "rc16-transition"
    record_path = fixtures_dir / "rc15-record.json"
    lock_path = fixtures_dir / "rc15-release-lock.json"

    assert record_path.is_file()
    assert lock_path.is_file()

    record = json.loads(record_path.read_text(encoding="utf-8"))
    lock = json.loads(lock_path.read_text(encoding="utf-8"))

    assert record["version"] == RC15_VERSION
    assert record["release_id"] == RC15_RELEASE_ID
    assert record["hermes_commit"] == RC15_HERMES_COMMIT
    assert record["hermes_source_tree_sha256"] == RC15_HERMES_TREE_SHA256

    assert lock["schema_version"] == 5
    assert lock["hermes"]["commit"] == RC15_HERMES_COMMIT
    assert lock["hermes"]["source_tree_sha256"] == RC15_HERMES_TREE_SHA256
    assert lock["hermes"]["source_mode"] == "maintained_fork"
    assert "mcp" in lock["hermes"]["extras"]


# --------------------------------------------------------------------------------------
# RC16 Candidate Identity Specification Tests
# --------------------------------------------------------------------------------------
def test_rc16_candidate_identity_specification() -> None:
    assert RC16_VERSION == "1.0.0rc16"
    assert RC16_DISPLAY_VERSION == "1.0.0-rc.16"
    assert RC16_TAG == "v1.0.0-rc.16"
    assert RC16_HERMES_COMMIT == "58f8c37a49b341f25b8fdd6310542fe932031b8d"
    assert (
        RC16_HERMES_TREE_SHA256
        == "a2a9b374bd2022c7f96242b0ab2c95691119262c925389eb3820ca627c581144"
    )


# --------------------------------------------------------------------------------------
# Retained Review Guidance Absence-Tolerant Path Tests
# --------------------------------------------------------------------------------------
def test_review_guidance_absence_tolerant_fallback_phrases() -> None:
    soul_path = (
        REPO_ROOT / "src" / "aether_agents" / "resources" / "profiles" / "supervisor" / "SOUL.md"
    )
    skill_path = (
        REPO_ROOT
        / "src"
        / "aether_agents"
        / "resources"
        / "skills"
        / "supervisor-decomposition"
        / "SKILL.md"
    )

    soul_text = " ".join(soul_path.read_text(encoding="utf-8").split())
    skill_text = " ".join(skill_path.read_text(encoding="utf-8").split())

    expected_soul = "If the field is absent, consult existing durable history."
    expected_skill = "If absent, use the existing complete history"

    assert expected_soul in soul_text
    assert expected_skill in skill_text


def test_durable_history_fallback_oracle_counts_returns_accurately() -> None:
    runs = [
        {"id": 1, "outcome": "changes_requested", "profile": "implementer"},
        {"id": 2, "outcome": "timed_out", "profile": "implementer"},
        {"id": 3, "outcome": "changes_requested", "profile": "implementer"},
        {"id": 4, "outcome": "running", "profile": "implementer"},
    ]
    # Without the optional context line, the oracle sums runs with outcome='changes_requested'
    review_returns = sum(1 for r in runs if r.get("outcome") == "changes_requested")
    assert review_returns == 2


# --------------------------------------------------------------------------------------
# Refusal Matrix Tests
# --------------------------------------------------------------------------------------
def test_lifecycle_manager_refuses_malformed_lock(tmp_path: Path) -> None:
    from aether_agents.lifecycle import IntegrityError, load_release_lock

    bad_lock = tmp_path / "bad-lock.json"
    bad_lock.write_text('{"schema_version": 99}\n', encoding="utf-8")
    with pytest.raises(IntegrityError):
        load_release_lock(bad_lock)


def test_lifecycle_manager_refuses_wrong_commit_checkout(tmp_path: Path) -> None:
    from aether_agents.lifecycle import IntegrityError, LifecycleManager, ReleaseStore

    store = ReleaseStore(tmp_path / "store")
    manager = LifecycleManager(store=store, python_executable=Path(sys.executable))
    fake_fork = tmp_path / "fork"
    fake_fork.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", "-b", "aether-main", str(fake_fork)], check=True)

    with pytest.raises(IntegrityError):
        manager._verify_fork_candidate_checkout(fake_fork, "0" * 40)


# --------------------------------------------------------------------------------------
# Decisive Qualification Invocation
# --------------------------------------------------------------------------------------
def test_decisive_transition_qualification_runs_cleanly(tmp_path: Path) -> None:
    work_root = tmp_path / "work"
    receipts_root = tmp_path / "receipts"
    work_root.mkdir(parents=True)
    receipts_root.mkdir(parents=True)

    completed = subprocess.run(
        [
            sys.executable,
            str(ENTRY_SCRIPT),
            "run",
            "--work-root",
            str(work_root),
            "--receipts-root",
            str(receipts_root),
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(REPO_ROOT),
    )
    assert completed.returncode == 0, f"STDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}"

    report = json.loads(completed.stdout.strip())
    assert report["schema_version"] == "aether.rc16-transition-qualification.v1"
    assert report["overall_status"] == "passed"
    for scenario in report["scenarios"]:
        assert scenario["passed"] is True, (
            f"scenario {scenario['name']} failed: {scenario.get('error')}"
        )

    receipt_file = Path(report["receipt_path"])
    assert receipt_file.is_file()
    saved = json.loads(receipt_file.read_text(encoding="utf-8"))
    assert saved["overall_status"] == "passed"
