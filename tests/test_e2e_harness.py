"""Deterministic tests for the disposable Aether E2E harness.

These tests never invoke a real model or provider. Live execution remains behind the
explicit ``--allow-model-spend`` gate in scripts/e2e/run.py.
"""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
E2E = ROOT / "scripts" / "e2e"
SCENARIOS = E2E / "scenarios"
FIXTURES = ROOT / "tests" / "fixtures" / "e2e"
RUNNER = E2E / "run.py"

sys.path.insert(0, str(E2E))
import collect  # noqa: E402
import dispatch  # noqa: E402
import run as e2e_run  # noqa: E402
from synthetic_owner import ScenarioError, load_scenario, matching_reply  # noqa: E402


def test_all_16_scenarios_are_strict_and_have_existing_fixtures() -> None:
    paths = sorted(SCENARIOS.glob("e2e-*.json"))
    assert len(paths) == 16
    scenarios = [load_scenario(path) for path in paths]
    assert [scenario.id for scenario in scenarios] == [f"e2e-{i:02d}" for i in range(1, 17)]
    for scenario in scenarios:
        assert (FIXTURES / scenario.fixture).is_dir()
        assert scenario.acceptance_command
        assert scenario.live_requires_spend is True


def test_scenario_loader_rejects_invented_owner_reply_shape(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text(
        json.dumps(
            {
                "id": "e2e-01",
                "fixture": "direct-text",
                "owner_message": "Do it",
                "expected_route": "direct",
                "acceptance_command": ["python3", "verify.py"],
                "scripted_replies": [{"pattern": "x", "reply": "yes", "fallback": "guess"}],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ScenarioError):
        load_scenario(path)


def test_scripted_owner_returns_only_predeclared_reply() -> None:
    scenario = load_scenario(SCENARIOS / "e2e-05.json")
    assert matching_reply(scenario, "¿Qué formato prefieres: JSON o texto?") == "Usa JSON."
    assert matching_reply(scenario, "Necesito otra decisión sin relación") is None


def test_prepare_only_creates_real_git_project_marker_registry_and_evidence(tmp_path: Path) -> None:
    run_root = tmp_path / "run"
    completed = subprocess.run(
        [sys.executable, str(RUNNER), "e2e-01", "--prepare-only", "--run-root", str(run_root)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result["status"] == "PREPARED"
    assert result["baseline_acceptance_passed"] is False

    repo = run_root / "repo"
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    assert len(head) == 40
    marker = (repo / ".aether" / "project.toml").read_text(encoding="utf-8")
    project_id = result["aether_project_id"]
    assert f'project_id = "{project_id}"' in marker
    registry = json.loads(
        (run_root / "xdg-state" / "aether" / "projects" / "registry.json").read_text(
            encoding="utf-8"
        )
    )
    assert registry["projects"][project_id]["path"] == str(repo.resolve())
    assert (run_root / "evidence" / "commands.jsonl").is_file()
    assert (run_root / "evidence" / "git-before.txt").is_file()
    assert (run_root / "evidence" / "baseline-acceptance.stdout").is_file()


def _fake_profile_root(tmp_path: Path) -> Path:
    root = tmp_path / "profiles-source"
    for role in ("morfeo", "supervisor", "implementer"):
        profile = root / role
        profile.mkdir(parents=True, exist_ok=True)
        (profile / "config.yaml").write_text(
            "hooks:\n"
            "  pre_tool_call:\n"
            "    - matcher: .*\n"
            f"      command: /private/{role}/hooks/aether_pre_tool_policy.py\n"
            "      timeout: 5\n"
            "      fail_closed: true\n",
            encoding="utf-8",
        )
        (profile / "sessions").mkdir()
        (profile / "sessions" / "private.json").write_text("SECRET-RUNTIME-STATE", encoding="utf-8")
    return root


def test_profile_preparation_copies_only_config_tracked_soul_and_candidate_hook(
    tmp_path: Path,
) -> None:
    source = _fake_profile_root(tmp_path)
    run_root = tmp_path / "run"
    run_root.mkdir()
    commands = run_root / "evidence" / "commands.jsonl"
    hermes_root = e2e_run.prepare_profiles(source, run_root, commands)

    canonical_hook = (ROOT / "policy" / "hooks" / "aether_pre_tool_policy.py").read_bytes()
    for role in ("morfeo", "supervisor", "implementer"):
        target = hermes_root / "profiles" / role
        files = sorted(
            path.relative_to(target).as_posix() for path in target.rglob("*") if path.is_file()
        )
        assert files == ["SOUL.md", "config.yaml", "hooks/aether_pre_tool_policy.py"]
        assert (target / "hooks" / "aether_pre_tool_policy.py").read_bytes() == canonical_hook
        config = (target / "config.yaml").read_text(encoding="utf-8")
        assert "/private/" not in config
        assert str(target / "hooks" / "aether_pre_tool_policy.py") in config
        assert "SECRET-RUNTIME-STATE" not in "\n".join(
            path.read_text(encoding="utf-8", errors="ignore")
            for path in target.rglob("*")
            if path.is_file()
        )


def test_recovery_fault_injection_is_disposable_blocks_only_file_mutation_and_can_restore(
    tmp_path: Path,
) -> None:
    source = _fake_profile_root(tmp_path)
    run_root = tmp_path / "run-fault"
    run_root.mkdir()
    evidence = run_root / "evidence"
    evidence.mkdir()
    commands = evidence / "commands.jsonl"
    hermes_root = e2e_run.prepare_profiles(source, run_root, commands)
    scenario = load_scenario(SCENARIOS / "e2e-11.json")
    known_good = e2e_run._apply_fault_injection(scenario, hermes_root, evidence)
    assert known_good is not None and known_good.is_file()
    active = known_good.with_name("aether_pre_tool_policy.py")
    payload = {
        "hook_event_name": "pre_tool_call",
        "tool_name": "write_file",
        "tool_input": {"path": "greeting.txt", "content": "Hola\n"},
    }
    denied = subprocess.run(
        [sys.executable, str(active)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
    )
    assert denied.returncode == 2
    assert "INJECTED-FALSE-POSITIVE" in denied.stdout

    allowed = subprocess.run(
        [sys.executable, str(active)],
        input=json.dumps(
            {
                "hook_event_name": "pre_tool_call",
                "tool_name": "terminal",
                "tool_input": {"command": "git status --short"},
            }
        ),
        text=True,
        capture_output=True,
        check=False,
    )
    assert allowed.returncode == 0
    assert e2e_run._fault_recovered(known_good) is False
    active.write_bytes(known_good.read_bytes())
    active.chmod(0o755)
    assert e2e_run._fault_recovered(known_good) is True
    fault = json.loads((evidence / "fault-injection.json").read_text(encoding="utf-8"))
    assert fault["scope"] == "disposable morfeo profile only"


def test_live_mode_refuses_model_spend_before_invoking_hermes(tmp_path: Path) -> None:
    fake_hermes = tmp_path / "fake-hermes"
    invoked = tmp_path / "INVOKED"
    fake_hermes.write_text(
        f"#!/bin/sh\nprintf invoked > {invoked}\nexit 0\n",
        encoding="utf-8",
    )
    fake_hermes.chmod(0o755)
    profile_root = _fake_profile_root(tmp_path)
    completed = subprocess.run(
        [
            sys.executable,
            str(RUNNER),
            "e2e-01",
            "--live",
            "--run-root",
            str(tmp_path / "run-live"),
            "--hermes",
            str(fake_hermes),
            "--profile-root",
            str(profile_root),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 3
    assert "allow-model-spend" in completed.stderr
    assert not invoked.exists()


def test_hermes_env_pins_runtime_and_scrubs_ambient_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    exact = tmp_path / "candidate" / "hermes"
    exact.parent.mkdir()
    exact.write_text("#!/bin/sh\n", encoding="utf-8")
    monkeypatch.setenv("TERMINAL_CWD", "/private/tui-cwd")
    monkeypatch.setenv("HERMES_CWD", "/private/hermes-cwd")
    env = e2e_run._hermes_env(tmp_path / "run", tmp_path / "home", exact)
    assert env["HERMES_BIN"] == str(exact.resolve())
    assert "TERMINAL_CWD" not in env
    assert "HERMES_CWD" not in env


def test_dispatch_passes_are_spread_across_the_scenario_timeout(monkeypatch) -> None:
    sleeps: list[float] = []
    monotonic = iter((0.0, 0.0, 0.0, 0.0))
    monkeypatch.setattr(dispatch.time, "monotonic", lambda: next(monotonic))
    monkeypatch.setattr(dispatch.time, "sleep", sleeps.append)
    monkeypatch.setattr(
        dispatch,
        "run_command",
        lambda *args, **kwargs: collect.CommandResult((), 0, "{}", "", 0.0),
    )
    monkeypatch.setattr(
        dispatch,
        "board_list",
        lambda *args, **kwargs: [{"id": "t_x", "status": "running"}],
    )
    monkeypatch.setattr(dispatch, "snapshot_board", lambda *args, **kwargs: [])
    state = dispatch.dispatch_until_settled(
        Path("/hermes"),
        cwd=Path("/repo"),
        env={},
        commands_log=Path("/commands"),
        evidence_dir=Path("/evidence"),
        max_passes=2,
        timeout_seconds=30,
    )
    assert state.reason == "pass_budget_exhausted"
    assert sleeps == [15.0, 15.0]


def test_origin_morfeo_session_id_is_exact_and_fail_closed(tmp_path: Path) -> None:
    profile = tmp_path / "profiles" / "morfeo"
    profile.mkdir(parents=True)
    with sqlite3.connect(profile / "state.db") as conn:
        conn.execute(
            "CREATE TABLE sessions (id TEXT, source TEXT, archived INTEGER, last_activity_at REAL)"
        )
        conn.executemany(
            "INSERT INTO sessions VALUES (?, ?, ?, ?)",
            [
                ("session-origin", "tui", 0, 1.0),
                ("worker-session", "kanban", 0, 2.0),
            ],
        )
    assert e2e_run._origin_morfeo_session_id(tmp_path) == "session-origin"
    with sqlite3.connect(profile / "state.db") as conn:
        conn.execute("INSERT INTO sessions VALUES ('ambiguous', 'tui', 0, 3.0)")
    with pytest.raises(e2e_run.HarnessError, match="ambiguous"):
        e2e_run._origin_morfeo_session_id(tmp_path)


def test_invoke_morfeo_places_workspace_and_resume_before_chat(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[str] = []

    def record(argv, **kwargs):
        captured.extend(argv)
        return collect.CommandResult(tuple(argv), 0, "ok", "", 0.0)

    monkeypatch.setattr(e2e_run, "run_command", record)
    e2e_run._invoke_morfeo(
        tmp_path / "hermes",
        tmp_path / "home",
        tmp_path / "repo",
        {},
        tmp_path / "commands.jsonl",
        tmp_path / "evidence",
        "continue",
        resume_session_id="session-origin",
        usage_name="usage.json",
    )
    assert captured.index("--in") < captured.index("chat")
    assert captured.index("--resume") < captured.index("chat")
    assert captured[captured.index("--resume") + 1] == "session-origin"


def test_command_evidence_never_serializes_environment(tmp_path: Path) -> None:
    log = tmp_path / "commands.jsonl"
    env = dict(os.environ)
    env["AETHER_TEST_SUPER_SECRET"] = "never-write-this-value"
    result = collect.run_command(
        (sys.executable, "-c", "print('ok')"),
        cwd=tmp_path,
        env=env,
        log_path=log,
        timeout_seconds=10,
    )
    assert result.returncode == 0
    evidence = log.read_text(encoding="utf-8")
    assert "AETHER_TEST_SUPER_SECRET" not in evidence
    assert "never-write-this-value" not in evidence


@pytest.mark.skipif(not Path("/proc").is_dir(), reason="Linux process ownership probe")
def test_cleanup_stops_only_workers_bound_to_the_disposable_board(tmp_path: Path) -> None:
    run_root = tmp_path / "run"
    evidence = run_root / "evidence"
    evidence.mkdir(parents=True)
    board = (run_root / "kanban.db").resolve()
    owned_env = dict(os.environ, HERMES_KANBAN_DB=str(board))
    decoy_env = dict(os.environ, HERMES_KANBAN_DB=str(tmp_path / "other.db"))
    owned = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"], env=owned_env)
    decoy = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"], env=decoy_env)
    try:
        with sqlite3.connect(board) as conn:
            conn.execute("CREATE TABLE tasks (worker_pid INTEGER)")
            conn.executemany(
                "INSERT INTO tasks(worker_pid) VALUES (?)", [(owned.pid,), (decoy.pid,)]
            )
        report = e2e_run._cleanup_disposable_workers(run_root, grace_seconds=1.0)
        owned.wait(timeout=3)
        assert decoy.poll() is None
        assert owned.pid in report["terminated"]
        assert decoy.pid in report["skipped"]
        assert report["survivors"] == []
        assert (evidence / "worker-cleanup.json").is_file()
    finally:
        if decoy.poll() is None:
            decoy.terminate()
            decoy.wait(timeout=3)


def test_fixture_acceptance_is_real_and_changes_from_red_to_green(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    shutil.copytree(FIXTURES / "direct-text", repo)
    red = subprocess.run([sys.executable, "verify.py"], cwd=repo, capture_output=True, text=True)
    assert red.returncode != 0
    (repo / "greeting.txt").write_text("Hola\n", encoding="utf-8")
    green = subprocess.run([sys.executable, "verify.py"], cwd=repo, capture_output=True, text=True)
    assert green.returncode == 0
    assert "PASS" in green.stdout


def test_run_root_rejects_nonempty_destination(tmp_path: Path) -> None:
    occupied = tmp_path / "occupied"
    occupied.mkdir()
    (occupied / "sentinel").write_text("keep", encoding="utf-8")
    completed = subprocess.run(
        [sys.executable, str(RUNNER), "e2e-01", "--prepare-only", "--run-root", str(occupied)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 3
    assert (occupied / "sentinel").read_text(encoding="utf-8") == "keep"
