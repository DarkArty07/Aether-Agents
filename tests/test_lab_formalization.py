from __future__ import annotations

import importlib.util
import json
import os
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from aether_agents import lab
from aether_agents.lab import affinity, matrix, persistent, runner

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
    scenarios = [lab.load_scenario(f"e2e-{index:02d}") for index in range(1, 17)]
    assert [scenario.id for scenario in scenarios] == [f"e2e-{index:02d}" for index in range(1, 17)]
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
    run_root = tmp_path / "observation"
    result = lab.prepare_observation_only(run_root)
    assert result["status"] == "PREPARED"
    assert result["suite"] == "observation"
    assert result["registered_tool"] == "aether_observe"
    assert {item["action"] for item in result["calls"]} == {"status", "changes", "diagnose"}
    assert all(item["success"] for item in result["calls"])
    assert result["calls"][0]["bytes"] <= 2048
    assert result["calls"][1]["bytes"] <= 2048
    assert result["calls"][2]["bytes"] <= 4096
    lab.validate_evidence(result)
    registry = run_root / "state" / "aether" / "projects" / "registry.json"
    assert registry.is_file()
    assert list((run_root / "state").rglob("registry.json")) == [registry]


def test_live_observation_invokes_supplied_runtime_once_after_spend_acknowledgement(
    tmp_path: Path,
) -> None:
    invoked = tmp_path / "hermes-invoked.json"
    fake_hermes = tmp_path / "hermes"
    fake_hermes.write_text(
        f"""#!/usr/bin/env python3
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
""",
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
        """#!/usr/bin/env python3
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
""",
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
    assert len(report["runs"]) == 16
    assert report["parallel"] == 2
    assert report["isolation_verified"] is True
    assert report["rolling_reliability_gate"]["live_run_count"] == 0
    assert next(item for item in report["runs"] if item["scenario"] == "e2e-15")["parallel"] == 1
    assert len([path for path in matrix_root.iterdir() if path.is_dir()]) == 16


def test_e2e16_is_a_serial_persistent_affinity_scenario() -> None:
    scenario = lab.load_scenario("e2e-16")
    assert scenario.id == "e2e-16"
    assert scenario.expected_route == "pipeline"
    assert scenario.live_requires_spend is True
    assert scenario.required_paths == (".aether/objective-contracts",)


def test_affinity_qualification_requires_real_resume_and_all_negative_controls() -> None:
    result = affinity.qualify_affinity_evidence(
        {
            "flow_id": "aether.flow.v1:" + "a" * 64,
            "first_supervisor_session_id": "supervisor-session",
            "resumed_supervisor_session_id": "supervisor-session",
            "implementer_session_ids": ["implementer-session"],
            "other_flow_session_id": "other-flow-session",
            "other_project_session_id": "other-project-session",
            "other_profile_session_id": "other-profile-session",
            "first_process_exit": -15,
            "resumed_process_exit": 0,
            "resume_invoked": True,
            "workspace_pinned": True,
            "prior_tool_evidence_observed": True,
            "reconstructed_input_sent": False,
            "stale_generation_rejected": True,
            "implementer_fresh": True,
            "internal_milestone_route": "suppressed",
            "terminal_route": "terminal",
            "input_route": "input",
            "revision_route": "revision",
            "runtime_available": True,
            "flow_binding_ok": True,
            "project_binding_ok": True,
            "profile_binding_ok": True,
            "other_flow_rejected": True,
            "other_project_rejected": True,
            "other_role_rejected": True,
            "native_control_lifecycle_observed": True,
            "review_integration_observed": True,
            "reclaim_succeeded": True,
        }
    )
    assert result.status == "PASS"
    assert result.qualified is True
    evidence = result.to_evidence()
    assert evidence["rolling_reliability_counted"] is False
    assert evidence["affinity"]["session_reused"] is True
    assert evidence["affinity"]["reconstructed_input_sent"] is False
    lab.validate_evidence(evidence)


def test_affinity_qualification_rejects_claims_without_observed_other_sessions() -> None:
    result = affinity.qualify_affinity_evidence(
        {
            "flow_id": "aether.flow.v1:" + "d" * 64,
            "first_supervisor_session_id": "supervisor-session",
            "resumed_supervisor_session_id": "supervisor-session",
            "implementer_session_ids": ["implementer-session"],
            "first_process_exit": -15,
            "resumed_process_exit": 0,
            "resume_invoked": True,
            "workspace_pinned": True,
            "prior_tool_evidence_observed": True,
            "reconstructed_input_sent": False,
            "stale_generation_rejected": True,
            "implementer_fresh": True,
            "internal_milestone_route": "suppressed",
            "terminal_route": "terminal",
            "input_route": "input",
            "revision_route": "revision",
            "runtime_available": True,
            "flow_binding_ok": True,
            "project_binding_ok": True,
            "profile_binding_ok": True,
            "other_flow_rejected": True,
            "other_project_rejected": True,
            "other_role_rejected": True,
            "native_control_lifecycle_observed": True,
            "review_integration_observed": True,
            "reclaim_succeeded": True,
        }
    )

    assert result.status == "FAIL"
    assert result.qualified is False
    assert result.to_evidence()["affinity"]["controls_passed"] is False
    lab.validate_evidence(result.to_evidence())


def test_affinity_qualification_reports_capability_wall_without_runtime() -> None:
    result = affinity.qualify_affinity_evidence({"runtime_available": False})
    assert result.status == "CAPABILITY_WALL"
    assert result.reason == "runtime_prerequisite_unavailable"
    assert result.qualified is False
    lab.validate_evidence(result.to_evidence())


def test_affinity_qualification_rejects_manual_control_ids_without_native_lifecycle() -> None:
    result = affinity.qualify_affinity_evidence(
        {
            "runtime_available": True,
            "flow_id": "aether.flow.v1:" + "b" * 64,
            "first_supervisor_session_id": "supervisor-session",
            "resumed_supervisor_session_id": "supervisor-session",
            "implementer_session_ids": ["implementer-session"],
            "other_flow_session_id": "copied-flow-session",
            "other_project_session_id": "copied-project-session",
            "other_role_session_id": "copied-role-session",
            "first_process_exit": -15,
            "resumed_process_exit": 0,
            "resume_invoked": True,
            "workspace_pinned": True,
            "prior_tool_evidence_observed": True,
            "reconstructed_input_sent": False,
            "stale_generation_rejected": True,
            "implementer_fresh": True,
            "internal_milestone_route": "suppressed",
            "terminal_route": "terminal",
            "input_route": "input",
            "revision_route": "revision",
            "flow_binding_ok": True,
            "project_binding_ok": True,
            "profile_binding_ok": True,
            "other_flow_rejected": True,
            "other_project_rejected": True,
            "other_role_rejected": True,
            "native_control_lifecycle_observed": False,
            "review_integration_observed": True,
            "reclaim_succeeded": True,
        }
    )
    assert result.status == "FAIL"
    assert result.qualified is False
    assert result.to_evidence()["affinity"]["controls_passed"] is False


def test_affinity_qualification_never_passes_when_a_generation_fence_control_fails() -> None:
    result = affinity.qualify_affinity_evidence(
        {
            "runtime_available": True,
            "flow_id": "aether.flow.v1:" + "c" * 64,
            "first_supervisor_session_id": "supervisor-session",
            "resumed_supervisor_session_id": "supervisor-session",
            "implementer_session_ids": ["implementer-session"],
            "other_flow_session_id": "other-flow-session",
            "other_project_session_id": "other-project-session",
            "other_profile_session_id": "other-role-session",
            "first_process_exit": -15,
            "resumed_process_exit": 0,
            "resume_invoked": True,
            "workspace_pinned": True,
            "prior_tool_evidence_observed": True,
            "reconstructed_input_sent": False,
            "stale_generation_rejected": False,
            "implementer_fresh": True,
            "internal_milestone_route": "suppressed",
            "terminal_route": "terminal",
            "input_route": "input",
            "revision_route": "revision",
            "flow_binding_ok": True,
            "project_binding_ok": True,
            "profile_binding_ok": True,
            "other_flow_rejected": True,
            "other_project_rejected": True,
            "other_role_rejected": True,
            "native_control_lifecycle_observed": True,
            "review_integration_observed": True,
            "reclaim_succeeded": True,
        }
    )
    assert result.status == "FAIL"
    assert result.qualified is False
    assert result.to_evidence()["affinity"]["controls_passed"] is False
    lab.validate_evidence(result.to_evidence())


def test_affinity_sqlite_fixture_uses_real_process_boundaries(tmp_path: Path) -> None:
    receipt = affinity.run_sqlite_boundary_fixture(tmp_path / "fixture")
    assert receipt["process_count"] == 3
    assert len(set(receipt["process_ids"])) == 3
    assert receipt["same_session"] is True
    assert receipt["prior_tool_evidence_observed"] is True
    assert receipt["stale_generation_rejected"] is True


def test_native_affinity_observer_does_not_qualify_copied_control_rows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    board = tmp_path / "kanban.db"
    flow_id = "aether.flow.v1:" + "e" * 64
    workspace = str(tmp_path / "workspace")
    with sqlite3.connect(board) as connection:
        connection.executescript(
            """
            CREATE TABLE kanban_session_affinity (
                board TEXT, project_id TEXT, flow_id TEXT, assignee TEXT,
                session_id TEXT, generation INTEGER, lease_token TEXT,
                owner_task_id TEXT, owner_run_id INTEGER, owner_claim_lock TEXT,
                workspace_path TEXT, updated_at INTEGER,
                PRIMARY KEY (board, project_id, flow_id, assignee)
            );
            CREATE TABLE tasks (
                id TEXT PRIMARY KEY, assignee TEXT, status TEXT, project_id TEXT,
                session_affinity TEXT, workspace_path TEXT, current_run_id INTEGER
            );
            CREATE TABLE task_runs (
                id INTEGER PRIMARY KEY, task_id TEXT, outcome TEXT, metadata TEXT
            );
            CREATE TABLE task_events (
                id INTEGER PRIMARY KEY, task_id TEXT, kind TEXT, payload TEXT
            );
            CREATE TABLE kanban_notify_subs (
                task_id TEXT, platform TEXT, chat_id TEXT, thread_id TEXT,
                last_event_id INTEGER
            );
            INSERT INTO task_runs VALUES (
                1, 't_worker', 'completed',
                '{"affinity_controls": {"other_flow_session_id": "forged"}}'
            );
            """
        )
        connection.executemany(
            """INSERT INTO kanban_session_affinity
               (board, project_id, flow_id, assignee, session_id, generation,
                lease_token, owner_task_id, owner_run_id, owner_claim_lock,
                workspace_path, updated_at)
               VALUES (?, ?, ?, ?, ?, 1, 'copied-token', 't_worker', 1,
                       'copied-lock', ?, 0)""",
            (
                ("copied-board", "project-main", flow_id, "supervisor", "main-session", workspace),
                (
                    "copied-board",
                    "project-main",
                    flow_id + ":copied",
                    "supervisor",
                    "copied-flow",
                    workspace,
                ),
                (
                    "copied-board",
                    "project-main:copied",
                    flow_id,
                    "supervisor",
                    "copied-project",
                    workspace,
                ),
                ("copied-board", "project-main", flow_id, "implementer", "copied-role", workspace),
            ),
        )

    monkeypatch.delenv("HERMES_HOME", raising=False)
    controls = runner._observe_native_affinity_controls(
        board=board,
        supervisor_db=tmp_path / "missing-supervisor.db",
        implementer_db=tmp_path / "missing-implementer.db",
        flow_id=flow_id,
        project_id="project-main",
        first_session_id="main-session",
        resumed_session_id="main-session",
        first_generation=1,
        workspace_path=workspace,
    )

    assert controls["other_flow_session_id"] == "copied-flow"
    assert controls["other_project_session_id"] == "copied-project"
    assert controls["other_role_session_id"] == "copied-role"
    assert controls["native_control_lifecycle_observed"] is False
    assert controls["other_flow_rejected"] is False
    assert controls["other_project_rejected"] is False
    assert controls["other_role_rejected"] is False
    qualification = affinity.qualify_affinity_evidence(
        {
            "runtime_available": True,
            "flow_id": flow_id,
            "first_supervisor_session_id": "main-session",
            "resumed_supervisor_session_id": "main-session",
            "implementer_session_ids": ["implementer-session"],
            "first_process_exit": -15,
            "resumed_process_exit": 0,
            "resume_invoked": True,
            "workspace_pinned": True,
            "prior_tool_evidence_observed": True,
            "reconstructed_input_sent": False,
            "stale_generation_rejected": True,
            "implementer_fresh": True,
            "internal_milestone_route": "suppressed",
            "terminal_route": "flow_terminal",
            "input_route": "input",
            "revision_route": "revision",
            "flow_binding_ok": True,
            "project_binding_ok": True,
            "profile_binding_ok": True,
            "review_integration_observed": True,
            "reclaim_succeeded": True,
            **controls,
            "other_flow_rejected": True,
            "other_project_rejected": True,
            "other_role_rejected": True,
        }
    )
    assert qualification.status == "FAIL"


@pytest.mark.integration
def test_native_affinity_observer_controls_are_created_by_native_lifecycle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    hermes = shutil.which("hermes")
    if hermes is None or importlib.util.find_spec("hermes_cli") is None:
        pytest.skip("exact Hermes runtime is unavailable")
    import inspect

    from hermes_cli import kanban_db as native_kanban_db

    if "session_affinity" not in inspect.signature(native_kanban_db.create_task).parameters:
        pytest.skip("exact Hermes runtime lacks session affinity")
    native_python = Path(sys.executable)
    source_home = tmp_path / "source-home"
    board = tmp_path / "main.db"
    workspace = tmp_path / "workspace"
    source_home.mkdir()
    workspace.mkdir()
    bootstrap = r"""
import json
import sys
from pathlib import Path

from hermes_cli import kanban_db, projects_db
from hermes_state import SessionDB

source_home, board, workspace = map(Path, sys.argv[1:])
flow_id = "aether.flow.v1:" + "f" * 64
with projects_db.connect_closing(db_path=source_home / "projects.db") as projects:
    project_id = projects_db.create_project(
        projects,
        name="Native observer fixture",
        slug="native-observer-fixture",
        primary_path=str(workspace),
        allow_duplicate_path=True,
    )
kanban_db.init_db(db_path=board)
with kanban_db.connect(db_path=board) as connection:
    task_id = kanban_db.create_task(
        connection,
        title="native observer main fixture",
        assignee="supervisor",
        workspace_kind="dir",
        workspace_path=str(workspace),
        project_id=project_id,
        session_affinity={"flow_id": flow_id},
    )
    task = kanban_db.claim_task(connection, task_id, claimer="fixture")
    lease = kanban_db.reserve_session_affinity(connection, task, board="main")
    state = SessionDB(db_path=source_home / "main-state.db")
    state.create_session(
        "main-supervisor-session",
        "kanban",
        cwd=str(workspace),
        profile_name="supervisor",
        model="fixture",
    )
    state.append_message(
        "main-supervisor-session",
        "tool",
        content="native fixture evidence",
        tool_name="fixture_tool",
        observed=True,
    )
    kanban_db.register_session_affinity(
        connection, task, lease, session_id="main-supervisor-session"
    )
    terminal_id = kanban_db.create_task(
        connection,
        title="native observer terminal review/integration",
        assignee="supervisor",
        parents=(task_id,),
        workspace_kind="dir",
        workspace_path=str(workspace),
        project_id=project_id,
        session_affinity={"flow_id": flow_id, "terminal": True},
    )
    kanban_db.add_notify_sub(
        connection, task_id=task_id, platform="e2e16", chat_id="origin"
    )
    kanban_db._append_event(
        connection, terminal_id, "review_requested", {"control": "native"}
    )
    kanban_db.complete_task(connection, task_id, result="decomposed")
    terminal = kanban_db.claim_task(connection, terminal_id, claimer="fixture-terminal")
    terminal_lease = kanban_db.reserve_session_affinity(
        connection, terminal, workspace_path=str(workspace), board="main"
    )
    assert terminal_lease.session_id == "main-supervisor-session"
    kanban_db.register_session_affinity(
        connection, terminal, terminal_lease, session_id="main-supervisor-session"
    )
    kanban_db.complete_task(connection, terminal_id, result="integrated")
    state.close()
print(json.dumps({"flow_id": flow_id, "project_id": project_id, "task_id": task_id,
                  "terminal_id": terminal_id}))
"""
    env = os.environ.copy()
    env.update(
        {
            "HERMES_HOME": str(source_home),
            "HERMES_KANBAN_DB": str(board),
            "PYTHONDONTWRITEBYTECODE": "1",
        }
    )
    bootstrapped = subprocess.run(
        [str(native_python), "-c", bootstrap, str(source_home), str(board), str(workspace)],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert bootstrapped.returncode == 0, bootstrapped.stderr
    fixture = json.loads(bootstrapped.stdout)
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "hostile-outer-home"))
    controls = runner._observe_native_affinity_controls(
        board=board,
        supervisor_db=tmp_path / "missing-supervisor.db",
        implementer_db=tmp_path / "missing-implementer.db",
        flow_id=fixture["flow_id"],
        project_id=fixture["project_id"],
        first_session_id="main-supervisor-session",
        resumed_session_id="main-supervisor-session",
        first_generation=1,
        workspace_path=str(workspace),
        hermes_home=source_home,
        hermes=native_python,
        task_id=fixture["task_id"],
    )

    assert controls["native_control_lifecycle_observed"] is True
    assert controls["review_integration_observed"] is True
    assert controls["workspace_pinned"] is True
    assert controls["resume_observed"] is True
    assert controls["other_flow_session_id"] != "unavailable"
    assert controls["other_project_session_id"] != "unavailable"
    assert controls["other_role_session_id"] != "unavailable"
    assert (
        len(
            {
                controls["other_flow_session_id"],
                controls["other_project_session_id"],
                controls["other_role_session_id"],
            }
        )
        == 3
    )


def test_native_python_resolves_shell_launcher_interpreter(tmp_path: Path) -> None:
    interpreter = tmp_path / "native-python"
    interpreter.write_text("#!/bin/sh\n", encoding="utf-8")
    launcher = tmp_path / "hermes"
    launcher.write_text(
        f'#!/usr/bin/env bash\nexec "{interpreter}" "/tmp/hermes" "$@"\n',
        encoding="utf-8",
    )

    assert runner._native_python(launcher) == interpreter


def test_e2e16_affinity_evidence_survives_runner_compaction() -> None:
    result = affinity.qualify_affinity_evidence(
        {
            "flow_id": "aether.flow.v1:" + "b" * 64,
            "first_supervisor_session_id": "supervisor-session",
            "resumed_supervisor_session_id": "supervisor-session",
            "implementer_session_ids": ["implementer-session"],
            "other_flow_session_id": "other-flow-session",
            "other_project_session_id": "other-project-session",
            "other_profile_session_id": "other-role-session",
            "first_process_exit": -15,
            "resumed_process_exit": 0,
            "resume_invoked": True,
            "workspace_pinned": True,
            "prior_tool_evidence_observed": True,
            "reconstructed_input_sent": False,
            "stale_generation_rejected": True,
            "implementer_fresh": True,
            "internal_milestone_route": "suppressed",
            "terminal_route": "terminal",
            "input_route": "input",
            "revision_route": "revision",
            "runtime_available": True,
            "flow_binding_ok": True,
            "project_binding_ok": True,
            "profile_binding_ok": True,
            "other_flow_rejected": True,
            "other_project_rejected": True,
            "other_role_rejected": True,
            "native_control_lifecycle_observed": True,
            "review_integration_observed": True,
            "reclaim_succeeded": True,
        }
    )
    compact = runner._compact_run_record(result.to_evidence())
    assert compact["affinity"]["flow_id"].startswith("aether.flow.v1:")
    assert compact["rolling_reliability_counted"] is False
    lab.validate_evidence(compact)


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
    assert one_shot.to_evidence()["continuation_source"] == "harness"
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
