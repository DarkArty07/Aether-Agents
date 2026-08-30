"""Regression coverage for E2E-15 persistent-wake qualification."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from aether_agents.lab import matrix, persistent, runner


def _record(*, route: str, status: str = "PASS") -> dict[str, object]:
    return {
        "mode": "live-oneshot",
        "status": status,
        "expected_route": route,
        "guard_caused_manual_recovery": False,
        "observed_protected_edge_violation": False,
        "aether_self_modification": False,
    }


def test_score_history_excludes_unqualified_e2e15_claiming_pass_and_count() -> None:
    routes = ["direct", "pipeline", "safety", "recovery"]
    history = [_record(route=routes[index % len(routes)]) for index in range(19)]
    history[2] = _record(route="safety", status="FAIL")
    history.append(
        {
            **_record(route="pipeline"),
            "scenario": "e2e-15",
            "persistent_autonomous_wake_qualified": False,
            "rolling_reliability_counted": True,
        }
    )

    gate = matrix.score_history(history)

    assert gate["live_run_count"] == 19
    assert gate["window_size"] == 19
    assert gate["passed"] is False


def test_score_history_excludes_stale_e2e15_missing_qualification_fields() -> None:
    routes = ["direct", "pipeline", "safety", "recovery"]
    history = [_record(route=routes[index % len(routes)]) for index in range(19)]
    history[2] = _record(route="safety", status="FAIL")
    history.append({**_record(route="pipeline"), "scenario": "e2e-15"})

    gate = matrix.score_history(history)

    assert gate["live_run_count"] == 19
    assert gate["window_size"] == 19
    assert gate["passed"] is False


@pytest.mark.parametrize(
    ("receipts", "reason"),
    [
        (
            {"continuation_source": "one-shot", "native_surface": "hermes"},
            "one_shot_continuation_non_qualifying",
        ),
        (
            {
                "continuation_source": "native",
                "native_board_event": False,
                "durable_report": False,
                "owner_messages": 1,
                "session_id": "session-1",
            },
            "native_same_session_wake_unobserved",
        ),
    ],
)
def test_e2e15_unqualified_receipts_are_capability_wall_and_non_counted(
    receipts: dict[str, object], reason: str
) -> None:
    record = runner._qualify_e2e15_record(
        {"scenario": "e2e-15", "status": "PASS", "rolling_reliability_counted": True},
        receipts,
    )

    assert record["status"] == "CAPABILITY_WALL"
    assert record["reason"] == reason
    assert record["persistent_autonomous_wake_qualified"] is False
    assert record["rolling_reliability_counted"] is False


def test_e2e15_accepts_only_already_qualified_native_persistent_receipt() -> None:
    record = runner._qualify_e2e15_record(
        {"scenario": "e2e-15", "status": "PASS"},
        {
            "continuation_source": "native",
            "native_board_event": True,
            "durable_report": True,
            "owner_messages": 1,
            "session_id": "session-1",
            "wake_session_id": "session-1",
        },
    )

    assert record["status"] == "PASS"
    assert record["persistent_autonomous_wake_qualified"] is True
    assert record["rolling_reliability_counted"] is True


def test_e2e15_rejects_an_explicitly_failed_same_session_wake() -> None:
    result = persistent.qualify_persistent_evidence(
        {
            "continuation_source": "native",
            "native_board_event": True,
            "native_same_session_wake": False,
            "durable_report": True,
            "owner_messages": 1,
            "session_id": "session-1",
            "wake_session_id": "session-1",
        }
    )

    assert result.status == "CAPABILITY_WALL"
    assert result.reason == "same_session_or_owner_message_requirement_failed"


def _persistent_fixture(tmp_path: Path, *, terminal_event: bool) -> tuple[Path, Path, Path]:
    script = tmp_path / "fake-native-hermes.py"
    script.write_text(
        """
import sqlite3
import sys
import time

session_db, board_db = sys.argv[1:]
sys.stdout.write("\\x1b[?2004h\\x1b]2;Hermes\\x07/help for commands")
sys.stdout.flush()
message = sys.stdin.readline().rstrip("\\r\\n")
with sqlite3.connect(session_db) as db:
    db.execute(
        "CREATE TABLE sessions (id TEXT, source TEXT, archived INTEGER, last_activity_at REAL)"
    )
    db.execute(
        "CREATE TABLE messages (session_id TEXT, role TEXT, content TEXT, timestamp REAL)"
    )
    db.execute("INSERT INTO sessions VALUES ('sid-native', 'tui', 0, 1.0)")
    db.execute(
        "INSERT INTO messages VALUES ('sid-native', 'user', ?, ?)",
        (message, time.time()),
    )
    db.commit()
with sqlite3.connect(board_db) as db:
    db.execute("CREATE TABLE kanban_session_affinity (session_id TEXT, owner_task_id TEXT)")
    db.execute("CREATE TABLE tasks (id TEXT, session_id TEXT)")
    db.execute(
        "CREATE TABLE task_events "
        "(id INTEGER PRIMARY KEY, task_id TEXT, kind TEXT, payload TEXT, created_at INTEGER)"
    )
    db.execute("INSERT INTO tasks VALUES ('task-native', 'sid-native')")
    db.execute("INSERT INTO kanban_session_affinity VALUES ('worker-session', 'task-native')")
    db.commit()

time.sleep(0.15)
if %s:
    with sqlite3.connect(board_db) as db:
        db.execute(
            "INSERT INTO task_events VALUES (1, 'task-native', 'flow_terminal', ?, ?)",
            ('{"flow_id":"flow-native"}', int(time.time())),
        )
        db.commit()
    time.sleep(0.15)
    with sqlite3.connect(session_db) as db:
        db.execute(
            "INSERT INTO messages VALUES ('sid-native', 'user', 'internal native wake', ?)",
            (time.time(),),
        )
        db.execute(
            "INSERT INTO messages VALUES ('sid-native', 'assistant', 'durable report', ?)",
            (time.time(),),
        )
        db.execute("UPDATE sessions SET last_activity_at = 2.0 WHERE id = 'sid-native'")
        db.commit()
time.sleep(2)
"""
        % ("True" if terminal_event else "False"),
        encoding="utf-8",
    )
    return script, tmp_path / "session.db", tmp_path / "kanban.db"


def test_run_persistent_session_proves_native_wake_from_both_databases(tmp_path: Path) -> None:
    script, session_db, kanban_db = _persistent_fixture(tmp_path, terminal_event=True)

    receipt = persistent.run_persistent_session(
        [sys.executable, str(script), str(session_db), str(kanban_db)],
        owner_message="one owner message",
        session_db=session_db,
        kanban_db=kanban_db,
        timeout_seconds=3,
        poll_seconds=0.02,
    )

    assert receipt["status"] == "PASS"
    assert receipt["mode"] == "live-persistent"
    assert receipt["continuation_source"] == "native"
    assert receipt["native_same_session_wake"] is True
    assert receipt["durable_report"] is True
    assert receipt["same_session"] is True
    assert receipt["owner_messages"] == 1


def test_run_persistent_session_does_not_turn_missing_native_event_into_pass(
    tmp_path: Path,
) -> None:
    script, session_db, kanban_db = _persistent_fixture(tmp_path, terminal_event=False)

    receipt = persistent.run_persistent_session(
        [sys.executable, str(script), str(session_db), str(kanban_db)],
        owner_message="one owner message",
        session_db=session_db,
        kanban_db=kanban_db,
        timeout_seconds=0.5,
        poll_seconds=0.02,
    )

    assert receipt["status"] == "CAPABILITY_WALL"
    assert receipt["reason"] == "native_same_session_wake_unobserved"
    assert receipt["native_same_session_wake"] is False
    assert receipt["durable_report"] is False
    assert receipt["owner_messages"] == 1


def test_e2e15_runner_uses_tui_without_one_shot_or_harness_continuation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    scenario = runner.load_scenario("e2e-15")
    repo = tmp_path / "repo"
    (repo / ".aether" / "objective-contracts").mkdir(parents=True)
    (repo / ".aether" / "objective-contracts" / "report.md").write_text("ok")
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    captured: dict[str, object] = {}

    def fake_persistent(argv, **kwargs):
        captured["argv"] = tuple(argv)
        captured["owner_message"] = kwargs["owner_message"]
        return {
            "status": "PASS",
            "native_same_session_wake": True,
            "durable_report": True,
            "owner_messages": 1,
            "same_session": True,
            "continuation_source": "native",
        }

    monkeypatch.setattr(runner, "run_persistent_session", fake_persistent)
    monkeypatch.setattr(runner, "board_list", lambda *args, **kwargs: [])
    monkeypatch.setattr(runner, "_run_acceptance", lambda *args, **kwargs: True)
    monkeypatch.setattr(runner, "_check_paths", lambda *args, **kwargs: ([], []))
    monkeypatch.setattr(runner, "_source_status", lambda *args, **kwargs: "unchanged")
    monkeypatch.setattr(runner, "_denial_codes", lambda *args, **kwargs: [])
    monkeypatch.setattr(runner, "_protected_edge_probe_violated", lambda *args: False)

    record = runner._live_persistent_lane(
        scenario,
        hermes=tmp_path / "hermes",
        hermes_root=tmp_path / "hermes-home",
        repo=repo,
        env={"HERMES_KANBAN_DB": str(tmp_path / "kanban.db")},
        commands=tmp_path / "commands.jsonl",
        evidence=evidence,
        aether_project_id="aether-project",
        hermes_project_id="hermes-project",
        baseline_acceptance=False,
        source_status_before="unchanged",
        known_good_hook=None,
    )

    argv = captured["argv"]
    assert isinstance(argv, tuple)
    assert "--tui" in argv
    assert "--in" in argv
    assert "chat" not in argv
    assert "-q" not in argv
    assert "-Q" not in argv
    assert captured["owner_message"] == scenario.owner_message
    assert record["status"] == "PASS"
    assert record["harness_continuations"] == 0
