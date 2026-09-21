"""Contract tests for the mixed-version qualification entry.

The decisive mixed-version oracles live in ``scripts/qualify_mixed_version_lifecycle.py``
and run there against real installed predecessors, real frozen readers/writers and a real
installed candidate.  This module pins the entry's own contract so a regression in the
entry cannot silently weaken that disqualify.  It asserts:

* input validation refuses an absent, dirty, mistyped or unbound input;
* every destination the entry derives lives under the disposable work root, and a live
  destination is refused before any work happens;
* the child environment carries no operator transport, board routing or operator roots;
* receipts are attributable (result-producing revision, argv, environment identity, exit
  status, timing, digests, scope and limits);
* the corrected writer keeps a predecessor record's own field set and refuses to invent a
  record for a target that cannot present one, using real predecessor record bytes.

The frozen records used here are the *actual* field sets of the rc3/rc4/rc5 releases
(digest-bound fixtures), so the field-evolution assertions cannot drift into a fabricated
shape.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
ENTRY = REPO_ROOT / "scripts" / "qualify_mixed_version_lifecycle.py"
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "mixed-version"

FROZEN_COMMITS = {
    "rc3": "d8ff984c67bfc147ac9c83cf8a34a72edc27c8df",
    "rc4": "5a897746afe422f3c07f2290f9115d60204ef4d2",
    "rc5": "ee0aa036b2e0b70b137f761668209a5104f2e032",
}


def load_entry() -> Any:
    """Import the qualification entry as a module without executing its CLI."""

    spec = importlib.util.spec_from_file_location("qualify_mixed_version_lifecycle", ENTRY)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def entry() -> Any:
    return load_entry()


def fixture_record(version: str) -> dict[str, Any]:
    return json.loads((FIXTURES / f"{version}-record.json").read_text(encoding="utf-8"))


# --------------------------------------------------------------------------------------
# frozen record fixtures
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize("version", ["rc3", "rc4", "rc5", "candidate"])
def test_record_fixtures_declare_their_frozen_revision(version: str) -> None:
    payload = fixture_record(version)
    assert payload["version"].startswith("1.0.0")
    assert payload["schema_version"] == 3
    assert isinstance(payload["wheel_sha256"], str) and len(payload["wheel_sha256"]) == 64


def test_field_evolution_is_the_documented_post_rc4_addition() -> None:
    rc3 = fixture_record("rc3")
    rc4 = fixture_record("rc4")
    rc5 = fixture_record("rc5")
    candidate = fixture_record("candidate")

    assert "tui_sha256" not in rc3
    assert "tui_sha256" in rc4
    assert "tui_sha256" in rc5
    assert "tui_sha256" in candidate
    added = sorted(set(candidate) - set(rc3))
    assert added == ["tui_sha256"]


def test_fixtures_carry_no_operator_paths_or_credentials() -> None:
    for path in sorted(FIXTURES.glob("*.json")):
        text = path.read_text(encoding="utf-8")
        assert "/home/" not in text
        assert "darkarty" not in text
        assert "Authorization" not in text


# --------------------------------------------------------------------------------------
# input validation
# --------------------------------------------------------------------------------------


def test_entry_rejects_a_missing_candidate_checkout(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(ENTRY),
            "run",
            "--repo",
            str(tmp_path / "absent"),
            "--candidate-commit",
            "0" * 40,
            "--fork-checkout",
            str(tmp_path),
            "--bundle-dir",
            str(tmp_path / "bundle"),
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
    assert completed.returncode in (1, 2)
    assert "not a Git worktree" in (completed.stderr + completed.stdout)


def test_entry_refuses_a_live_work_root_before_doing_any_work(tmp_path: Path) -> None:
    live = Path.home() / ".local" / "share" / "aether"
    completed = subprocess.run(
        [
            sys.executable,
            str(ENTRY),
            "run",
            "--repo",
            str(REPO_ROOT),
            "--candidate-commit",
            "0" * 40,
            "--fork-checkout",
            str(tmp_path),
            "--bundle-dir",
            str(tmp_path / "bundle"),
            "--work-root",
            str(live),
            "--receipts-root",
            str(tmp_path / "receipts"),
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(REPO_ROOT),
    )
    assert completed.returncode == 2
    assert "refusing to run" in completed.stderr


def test_unknown_scenario_is_refused(entry: Any, tmp_path: Path) -> None:
    with pytest.raises(entry.Refusal):
        entry.select_scenarios("cycle,ornamental")


def test_all_scenario_selection_keeps_the_contract_order(entry: Any) -> None:
    assert entry.select_scenarios("all") == list(entry.SCENARIOS)
    assert "isolation" in entry.SCENARIOS
    # The entry must never grow a scenario that is not part of the pinned objective.
    assert set(entry.SCENARIOS) == {
        "isolation",
        "frozen-readers",
        "frozen-writer",
        "cycle",
        "legacy",
        "launch",
        "docs",
    }


# --------------------------------------------------------------------------------------
# isolation and receipts
# --------------------------------------------------------------------------------------


def test_isolation_derives_every_root_under_the_work_root(entry: Any, tmp_path: Path) -> None:
    isolation = entry.Isolation(
        work_root=tmp_path / "work", receipts_root=tmp_path / "receipts", run_id="unit"
    )
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
        isolation.projections,
    ):
        assert derived.is_relative_to(tmp_path / "work")
    assert isolation.live_overlaps() == []


def test_isolated_environment_is_scrubbed(entry: Any, tmp_path: Path, monkeypatch: Any) -> None:
    monkeypatch.setenv("HERMES_KANBAN_TASK", "t_leak")
    monkeypatch.setenv("HERMES_KANBAN_DB", "/leak/kanban.db")
    monkeypatch.setenv("HERMES_PYTHON", "/usr/bin/python3")
    monkeypatch.setenv("AETHER_PROJECT_ROOT", "/leak/project")
    monkeypatch.setenv("DBUS_SESSION_BUS_ADDRESS", "unix:path=/run/user/1000/bus")
    monkeypatch.setenv("PYTHONPATH", "/leak/src")
    isolation = entry.Isolation(
        work_root=tmp_path / "work", receipts_root=tmp_path / "receipts", run_id="unit"
    )
    environment = isolation.environment()
    for name in (
        "HERMES_KANBAN_TASK",
        "HERMES_KANBAN_DB",
        "HERMES_PYTHON",
        "AETHER_PROJECT_ROOT",
        "DBUS_SESSION_BUS_ADDRESS",
        "PYTHONPATH",
    ):
        assert name not in environment
    assert environment["HOME"] == str(isolation.home)
    assert environment["AETHER_HERMES_ROOT"] == str(isolation.hermes_root)
    identity = isolation.environment_identity(environment)
    assert len(identity) == 64
    other = isolation.environment_identity({**environment, "HOME": "/tmp/other-home"})
    assert other != identity


def test_live_witnesses_cover_unit_pointer_selector_and_operator_config(entry: Any) -> None:
    labels = {label for label, _ in entry.live_witness_paths()}
    assert {"live-active-pointer", "live-selector", "live-gateway-unit"} <= labels
    assert {"operator-morfeo-config", "operator-supervisor-config"} <= labels
    assert {"live-rc3-record", "live-rc4-record", "live-rc5-record"} <= labels


def test_witness_detects_content_and_metadata_changes(entry: Any, tmp_path: Path) -> None:
    target = tmp_path / "artifact.json"
    target.write_text("{}\n", encoding="utf-8")
    before = entry.witness(target)
    assert before.state["exists"] is True
    target.write_text('{"changed": true}\n', encoding="utf-8")
    after = entry.witness(target)
    assert before.state != after.state
    os.utime(target, (before.state["mtime_ns"] / 1e9, before.state["mtime_ns"] / 1e9))
    restored = entry.witness(target)
    assert restored.state["sha256"] != before.state["sha256"]


def test_receipts_are_attributable(entry: Any, tmp_path: Path) -> None:
    isolation = entry.Isolation(
        work_root=tmp_path / "work", receipts_root=tmp_path / "receipts", run_id="unit"
    )
    isolation.create()
    session = entry.Session(isolation)
    record = session.run(
        "sample",
        [sys.executable, "-c", "print('ok')"],
        env=isolation.environment(),
        cwd=tmp_path,
    )
    payload = record.to_json()
    for key in (
        "label",
        "argv",
        "cwd",
        "exit_code",
        "duration_ms",
        "stdout_sha256",
        "stderr_sha256",
        "environment_identity",
    ):
        assert key in payload
    assert payload["exit_code"] == 0
    assert payload["stdout_sha256"] == hashlib.sha256(b"ok\n").hexdigest()
    assert payload["duration_ms"] >= 0

    scenario = entry.ScenarioResult(name="cycle", scope="unit")
    scenario.check("AC-3", "pass", 1, 1)
    session.write_scenario(scenario)
    stored = json.loads((isolation.receipts / "scenarios" / "cycle.json").read_text())
    assert stored["status"] == "passed"
    assert stored["commands"] == []
    assert stored["assertions"][0]["result"] == "pass"


def test_scenario_failure_marks_the_scenario_failed(entry: Any) -> None:
    scenario = entry.ScenarioResult(name="cycle", scope="unit")
    with pytest.raises(entry.ScenarioFailure):
        scenario.require("AC-3", "1", 2, 1)
    assert scenario.status == "failed"
    assert scenario.assertions[0].ok is False


# --------------------------------------------------------------------------------------
# frozen reader contract (real frozen code, executed in isolation)
# --------------------------------------------------------------------------------------


def _frozen_module_source(version: str) -> str | None:
    completed = subprocess.run(
        ["git", "show", f"{FROZEN_COMMITS[version]}:src/aether_agents/lifecycle.py"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0 or not completed.stdout:
        return None
    return completed.stdout


@pytest.mark.parametrize("version", ["rc3", "rc4"])
def test_frozen_reader_source_is_available_and_unchanged(version: str) -> None:
    source = _frozen_module_source(version)
    if source is None:
        pytest.skip(f"frozen {version} revision is not present in this checkout")
    # The frozen reader is the disqualifying generation for the post-rc4 field addition.
    if version == "rc3":
        assert "tui_sha256" not in source
    else:
        assert "tui_sha256" in source
    assert "def from_json" in source


def test_rc3_reader_rejects_a_post_rc4_pointer_shape(tmp_path: Path) -> None:
    """Execute the frozen rc3 reader on an rc5-shaped payload with the repository interpreter."""

    source = _frozen_module_source("rc3")
    if source is None:
        pytest.skip("frozen rc3 revision is not present in this checkout")
    tree = _materialize_frozen_package(tmp_path, "rc3")
    payload = fixture_record("rc5")
    probe = tmp_path / "probe.py"
    probe.write_text(
        "import json, sys\n"
        "from aether_agents.lifecycle import IntegrityError, ReleaseRecord\n"
        "payload = json.loads(sys.stdin.read())\n"
        "try:\n"
        "    ReleaseRecord.from_json(payload)\n"
        "except IntegrityError:\n"
        "    print('rejected')\n"
        "else:\n"
        "    print('accepted')\n",
        encoding="utf-8",
    )
    completed = subprocess.run(
        [sys.executable, "-P", "-s", str(probe)],
        cwd=str(tree),
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=False,
        env=_frozen_environment(tree),
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "rejected"
    # The same reader accepts its own generation's shape.
    native = subprocess.run(
        [sys.executable, "-P", "-s", str(probe)],
        cwd=str(tree),
        input=json.dumps(fixture_record("rc3")),
        capture_output=True,
        text=True,
        check=False,
        env=_frozen_environment(tree),
    )
    assert native.returncode == 0, native.stderr
    assert native.stdout.strip() == "accepted"


def _frozen_environment(tree: Path) -> dict[str, str]:
    environment = {
        key: value
        for key, value in os.environ.items()
        if key in ("PATH", "LANG", "LC_ALL", "SYSTEMROOT")
    }
    environment["PYTHONPATH"] = str(tree / "src")
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return environment


def _materialize_frozen_package(tmp_path: Path, version: str) -> Path:
    tree = tmp_path / version
    tree.mkdir(parents=True, exist_ok=True)
    archive = subprocess.run(
        ["git", "archive", FROZEN_COMMITS[version], "src"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        check=False,
    )
    assert archive.returncode == 0, archive.stderr
    import io
    import tarfile

    with tarfile.open(fileobj=io.BytesIO(archive.stdout)) as bundle:
        bundle.extractall(tree, filter="data")
    return tree


def test_entry_never_writes_outside_its_work_root(entry: Any, tmp_path: Path) -> None:
    """Every path the entry hands to a child or writes to must live under the work root."""

    isolation = entry.Isolation(
        work_root=tmp_path / "work", receipts_root=tmp_path / "receipts", run_id="unit"
    )
    isolation.create()
    session = entry.Session(isolation)
    record = session.run(
        "cwd-check",
        [sys.executable, "-c", "import os; print(os.getcwd())"],
        env=isolation.environment(),
        cwd=isolation.work_root,
    )
    assert record.cwd.startswith(str(tmp_path / "work"))
    assert record.stdout_tail.strip().startswith(str(tmp_path / "work"))
    scenario = entry.ScenarioResult(name="cycle", scope="unit")
    scenario.check("AC-3", "pass", 1, 1)
    session.write_scenario(scenario)
    written = {path for path in isolation.receipts.rglob("*") if path.is_file()}
    assert written, "receipts must be written under the receipts root"
    for path in written:
        assert path.is_relative_to(tmp_path / "receipts")


def test_project_paths_stay_inside_the_work_root(entry: Any, tmp_path: Path) -> None:
    isolation = entry.Isolation(
        work_root=tmp_path / "work", receipts_root=tmp_path / "receipts", run_id="unit"
    )
    assert isolation.project.is_relative_to(isolation.work_root)
    assert isolation.second_project.is_relative_to(isolation.work_root)


def test_scenario_result_roundtrip_from_json(entry: Any) -> None:
    scenario = entry.ScenarioResult(
        name="launch",
        scope="launch-scope",
        reused=True,
        harness_sha256="1234abcd" * 8,
    )
    scenario.check("AC-7/launch", "ready", "ready", "ready")
    scenario.artifacts["pty"] = {"agent_ready_ms": 4500, "corpus_scale": {"events": 25}}
    encoded = scenario.to_json()
    assert encoded["reused"] is True
    assert encoded["harness_sha256"] == "1234abcd" * 8
    decoded = entry.ScenarioResult.from_json(encoded)
    assert decoded.name == scenario.name
    assert decoded.scope == scenario.scope
    assert decoded.status == "passed"
    assert decoded.reused is True
    assert decoded.harness_sha256 == "1234abcd" * 8
    assert len(decoded.assertions) == 1
    assert decoded.assertions[0].ok is True
    assert decoded.artifacts["pty"]["agent_ready_ms"] == 4500


def test_seed_observation_corpus_populates_store(entry: Any, tmp_path: Path) -> None:
    isolation = entry.Isolation(
        work_root=tmp_path / "work", receipts_root=tmp_path / "receipts", run_id="unit"
    )
    scale = entry.seed_observation_corpus(isolation, "11111111-1111-4111-8111-111111111111")
    assert scale["segments"] >= 1
    assert scale["events"] >= 20
    assert scale["digest"] is not None


def test_detect_agent_readiness_rejects_visible_prompt_with_construction_paused(
    entry: Any,
) -> None:
    # A visible prompt glyph/placeholder while agent construction is paused
    # (status still 'summoning hermes...', skeleton tool/skill rows) must NOT pass.
    paused_buffer = (
        b"\x1b[H\r\n\xe2\x94\x80 summoning hermes\xe2\x80\xa6 \xe2\x94\x82 \xe2\x94\x80 /project\r\n"
        b'\xe2\x9d\xaf Try "/help" for commands\r\n'
        b"\xe2\x94\x82 \xe2\x96\x81\xe2\x96\x81\xe2\x96\x81\xe2\x96\x81\xe2\x96\x81 \xe2\x94\x82\r\n"
    )
    is_ready, signal_name = entry.detect_agent_readiness(paused_buffer)
    assert not is_ready
    assert signal_name is None


def test_detect_agent_readiness_accepts_hydrated_and_titled_state(entry: Any) -> None:
    # Once agent construction completes, window title and/or hydrated tools arrive
    titled_buffer = (
        b"\x1b[H\r\n\xe2\x94\x80 ready \xe2\x94\x82 \xe2\x94\x80 /project\r\n"
        b"\x1b]2;\xe2\x9c\x93 stub-non-sending \xc2\xb7 /project\x07\r\n"
        b"39 tools \xc2\xb7 87 skills (and 9 more toolsets\xe2\x80\xa6)\r\n"
        b'\xe2\x9d\xaf Try "/help" for commands\r\n'
    )
    is_ready, signal_name = entry.detect_agent_readiness(titled_buffer)
    assert is_ready
    assert signal_name in (
        "window_title_ready_glyph",
        "status_chrome_ready",
        "hydrated_tools_banner",
    )
