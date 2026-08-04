"""Focused regression coverage for Aether-native project continuity."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from aether_agents.continuity import AetherDBSync, hooks, resolve_aether_db, resolve_aether_dir


@pytest.fixture
def project(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    root.mkdir()
    return root


@pytest.fixture
def database(project: Path) -> AetherDBSync:
    db = AetherDBSync(project / ".aether" / "aether.db")
    db.ensure_tables()
    return db


def test_schema_and_private_permissions_are_preserved(database: AetherDBSync) -> None:
    with sqlite3.connect(database.db_path) as connection:
        tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
    assert {"hot_state", "sessions", "file_changes", "decisions", "issues"} <= tables



def test_hot_state_round_trip(database: AetherDBSync, project: Path) -> None:
    database.update_hot_state(
        project_root=str(project.resolve()),
        current_phase="cleanup",
        current_task="remove Olympus",
        last_request="continue",
    )
    state = database.get_hot_state()
    assert state is not None
    assert state["project_root"] == str(project.resolve())
    assert state["current_phase"] == "cleanup"
    assert state["current_task"] == "remove Olympus"


def test_session_round_trip_and_terminal_update(database: AetherDBSync) -> None:
    database.insert_session("session-1", "hefesto", model="model", platform="cli")
    database.update_session(
        "session-1",
        status="completed",
        result_summary="done",
        files_modified="a.py",
        duration_seconds=7,
    )
    sessions = database.get_recent_sessions(limit=1)
    assert len(sessions) == 1
    assert sessions[0]["session_id"] == "session-1"
    assert sessions[0]["status"] == "completed"
    assert sessions[0]["result_summary"] == "done"


def test_file_change_queries_are_project_scoped(database: AetherDBSync) -> None:
    database.insert_session("session-1", "hefesto")
    database.insert_file_change("session-1", "hefesto", "src/a.py", "write")
    database.insert_file_change("session-1", "hefesto", "src/b.py", "patch")
    assert database.get_session_files("session-1") == ["src/a.py", "src/b.py"]
    assert set(database.get_recent_files()) == {"src/a.py", "src/b.py"}


def test_decision_is_persisted_without_payload_tables(database: AetherDBSync) -> None:
    decision_id = database.insert_decision(
        "Remove legacy runtime",
        "Delete it before adapter design",
        rationale="Product-owner direction",
    )
    with sqlite3.connect(database.db_path) as connection:
        row = connection.execute(
            "SELECT title, decision, rationale FROM decisions WHERE id = ?",
            (decision_id,),
        ).fetchone()
    assert row == (
        "Remove legacy runtime",
        "Delete it before adapter design",
        "Product-owner direction",
    )


def test_issue_count_and_resolution(database: AetherDBSync) -> None:
    database.insert_session("session-1", "hefesto")
    issue_id = database.insert_issue("blocked", error_type="bug", session_id="session-1")
    assert database.get_open_issue_count() == 1
    database.resolve_issue(issue_id, "fixed")
    assert database.get_open_issue_count() == 0


def test_two_project_databases_do_not_share_rows(tmp_path: Path) -> None:
    first = AetherDBSync(tmp_path / "one" / ".aether" / "aether.db")
    second = AetherDBSync(tmp_path / "two" / ".aether" / "aether.db")
    first.ensure_tables()
    second.ensure_tables()
    first.insert_session("only-first", "hefesto")
    assert [row["session_id"] for row in first.get_recent_sessions()] == ["only-first"]
    assert second.get_recent_sessions() == []


def test_resolvers_preserve_project_local_paths(project: Path) -> None:
    assert resolve_aether_dir(str(project)) == project.resolve() / ".aether"
    assert resolve_aether_db(str(project)) == project.resolve() / ".aether" / "aether.db"


def test_hooks_use_explicit_session_and_result_summary(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AETHER_HOME", str(project))
    db = Mock()
    db.get_hot_state.return_value = {"total_sessions": 0}
    with (
        patch.object(hooks, "_get_aether_db", return_value=db),
        patch.object(hooks, "_detect_agent_name", return_value="hefesto"),
    ):
        hooks.on_session_start("native-session", model="model", platform="cli")
        hooks.on_session_end(
            "native-session",
            completed=True,
            interrupted=False,
            model="model",
            platform="cli",
            result_summary="bounded result",
        )
    db.insert_session.assert_called_once_with(
        session_id="native-session",
        agent="hefesto",
        model="model",
        platform="cli",
    )
    assert any(
        call.kwargs.get("session_id") == "native-session"
        and call.kwargs.get("result_summary") == "bounded result"
        for call in db.update_session.call_args_list
    )


def test_hooks_ignore_legacy_pid_session_files(project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    legacy_home = tmp_path / "hermes"
    legacy_home.mkdir()
    (legacy_home / f".olympus_session.{os.getpid()}").write_text("legacy-session", encoding="utf-8")
    monkeypatch.setenv("HERMES_HOME", str(legacy_home))
    monkeypatch.setenv("AETHER_HOME", str(project))
    assert hooks._session_binding("native-session") == "native-session"
    assert hooks._session_binding("") is None
