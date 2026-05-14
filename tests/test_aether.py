"""Tests for .aether continuity system — AetherDBSync and aether_hooks.

Uses tmp_path fixtures for test databases (never touches the real aether.db).
Hook tests mock the DB and file system operations to ensure isolation.
"""

from __future__ import annotations

import os
import sqlite3
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from olympus_v3.aether_db import AetherDBSync, get_aether_db_path
from olympus_v3.aether_hooks import hooks as hooks_module


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def db(tmp_path: Path) -> AetherDBSync:
    """Create an AetherDBSync with a temp database, tables initialized."""
    db_path = tmp_path / ".aether" / "aether.db"
    aether_db = AetherDBSync(db_path=db_path)
    aether_db.ensure_tables()
    return aether_db


@pytest.fixture()
def fresh_hooks(tmp_path: Path):
    """Reset module-level state in aether_hooks and patch _get_aether_db.

    Returns a dict with the mock db and the tmp_path for creating test files.
    """
    mock_db = MagicMock(spec=AetherDBSync)
    mock_db.get_hot_state.return_value = None

    # Reset module-level state
    hooks_module._aether_db = None  # type: ignore[attr-defined]
    hooks_module._turn_counter = 0
    hooks_module._session_id = None
    hooks_module._agent_name = None
    hooks_module._request = None

    # Patch _get_aether_db to return our mock
    with patch.object(hooks_module, "_get_aether_db", return_value=mock_db):
        yield {"db": mock_db, "tmp_path": tmp_path}

    # Cleanup module-level state
    hooks_module._aether_db = None  # type: ignore[attr-defined]
    hooks_module._turn_counter = 0
    hooks_module._session_id = None
    hooks_module._agent_name = None
    hooks_module._request = None


# ===========================================================================
# AetherDBSync tests
# ===========================================================================


class TestEnsureTables:
    """Test that ensure_tables creates all 5 tables + seed row."""

    def test_creates_all_tables(self, tmp_path: Path) -> None:
        db_path = tmp_path / ".aether" / "aether.db"
        db = AetherDBSync(db_path=db_path)
        db.ensure_tables()

        conn = sqlite3.connect(str(db_path))
        try:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
            tables = {row[0] for row in cursor.fetchall()}
        finally:
            conn.close()

        expected = {"hot_state", "sessions", "file_changes", "decisions", "issues"}
        assert expected.issubset(tables), f"Missing tables: {expected - tables}"

    def test_seeds_hot_state_row(self, db: AetherDBSync) -> None:
        """The seed statement ensures hot_state always has id=1."""
        state = db.get_hot_state()
        assert state is not None
        assert state["id"] == 1


class TestHotStateCRUD:
    """Test get/update operations on the single hot_state row."""

    def test_get_hot_state_initial(self, db: AetherDBSync) -> None:
        state = db.get_hot_state()
        assert state is not None
        assert state["project_name"] == ""  # seeded as empty string
        assert state["updated_at"] == 0

    def test_update_hot_state_sets_updated_at(self, db: AetherDBSync) -> None:
        before = time.time()
        db.update_hot_state(project_name="TestProject", current_phase="code")
        after = time.time()

        state = db.get_hot_state()
        assert state is not None
        assert state["project_name"] == "TestProject"
        assert state["current_phase"] == "code"
        assert before <= state["updated_at"] <= after

    def test_update_hot_state_explicit_updated_at(self, db: AetherDBSync) -> None:
        """When updated_at is explicitly provided, it should be used as-is."""
        db.update_hot_state(project_name="ExplicitTime", updated_at=1000.0)
        state = db.get_hot_state()
        assert state is not None
        assert state["updated_at"] == 1000.0

    def test_update_hot_state_multiple_fields(self, db: AetherDBSync) -> None:
        db.update_hot_state(
            project_name="Multi",
            current_task="Test task",
            blockers="None",
            total_sessions=5,
        )
        state = db.get_hot_state()
        assert state is not None
        assert state["project_name"] == "Multi"
        assert state["current_task"] == "Test task"
        assert state["blockers"] == "None"
        assert state["total_sessions"] == 5


class TestSessionsCRUD:
    """Test session insert, update, and get_recent_sessions."""

    def test_insert_session(self, db: AetherDBSync) -> None:
        sid = db.insert_session("sess-001", agent="hefesto", model="gpt-4", platform="openai")
        assert sid == "sess-001"

        sessions = db.get_recent_sessions(limit=10)
        assert len(sessions) == 1
        assert sessions[0]["session_id"] == "sess-001"
        assert sessions[0]["agent"] == "hefesto"
        assert sessions[0]["model"] == "gpt-4"
        assert sessions[0]["platform"] == "openai"
        assert sessions[0]["status"] == "active"

    def test_update_session_status_completed(self, db: AetherDBSync) -> None:
        db.insert_session("sess-002", agent="etalides")
        db.update_session("sess-002", status="completed", result_summary="All done")

        sessions = db.get_recent_sessions(limit=10)
        assert len(sessions) == 1
        s = sessions[0]
        assert s["status"] == "completed"
        assert s["result_summary"] == "All done"
        assert s["completed_at"] is not None  # completed_at set on terminal status

    def test_update_session_status_active_no_completed_at(self, db: AetherDBSync) -> None:
        db.insert_session("sess-003", agent="athena")
        db.update_session("sess-003", status="active")

        sessions = db.get_recent_sessions(limit=10)
        s = sessions[0]
        assert s["status"] == "active"
        assert s["completed_at"] is None

    def test_get_recent_sessions_ordered(self, db: AetherDBSync) -> None:
        db.insert_session("sess-old", agent="hefesto")
        time.sleep(0.05)  # ensure different started_at
        db.insert_session("sess-new", agent="etalides")

        sessions = db.get_recent_sessions(limit=10)
        assert sessions[0]["session_id"] == "sess-new"
        assert sessions[1]["session_id"] == "sess-old"

    def test_get_recent_sessions_limit(self, db: AetherDBSync) -> None:
        for i in range(5):
            db.insert_session(f"sess-{i:03d}", agent="hefesto")
            time.sleep(0.01)

        sessions = db.get_recent_sessions(limit=2)
        assert len(sessions) == 2

    def test_get_recent_sessions_with_model_platform(self, db: AetherDBSync) -> None:
        db.insert_session("sess-mp", agent="daedalus", model="claude-3", platform="anthropic")
        sessions = db.get_recent_sessions(limit=10)
        assert sessions[0]["model"] == "claude-3"
        assert sessions[0]["platform"] == "anthropic"


class TestFileChanges:
    """Test insert_file_change and get_session_files."""

    def test_insert_and_get_file_changes(self, db: AetherDBSync) -> None:
        db.insert_session("sess-f1", agent="hefesto")
        db.insert_file_change("sess-f1", "hefesto", "src/main.py", "write")
        db.insert_file_change("sess-f1", "hefesto", "src/utils.py", "write")
        db.insert_file_change("sess-f1", "hefesto", "src/main.py", "patch")

        files = db.get_session_files("sess-f1")
        assert "src/main.py" in files
        assert "src/utils.py" in files
        # DISTINCT — main.py appears once
        assert len(files) == 2

    def test_get_session_files_empty(self, db: AetherDBSync) -> None:
        db.insert_session("sess-empty", agent="hefesto")
        files = db.get_session_files("sess-empty")
        assert files == []

    def test_get_recent_files(self, db: AetherDBSync) -> None:
        db.insert_session("sess-r1", agent="hefesto")
        db.insert_file_change("sess-r1", "hefesto", "src/a.py", "write")
        db.insert_file_change("sess-r1", "hefesto", "src/b.py", "write")

        recent = db.get_recent_files(limit=10)
        assert "src/a.py" in recent
        assert "src/b.py" in recent


class TestDecisions:
    """Test insert_decision and retrieval."""

    def test_insert_decision(self, db: AetherDBSync) -> None:
        decision_id = db.insert_decision(
            title="Use SQLite",
            decision="Use SQLite for persistence",
            rationale="Lightweight, no server needed",
            alternatives="JSON files, PostgreSQL",
            made_by="hermes",
        )
        assert decision_id >= 1

    def test_decision_defaults_and_values(self, db: AetherDBSync) -> None:
        db.insert_decision(
            title="Framework choice",
            decision="Use FastAPI",
            made_by="daedalus",
        )
        # Verify via direct query
        conn = sqlite3.connect(str(db.db_path))
        conn.row_factory = sqlite3.Row
        try:
            row = conn.execute("SELECT * FROM decisions WHERE title = 'Framework choice'").fetchone()
            assert row is not None
            assert row["decision"] == "Use FastAPI"
            assert row["made_by"] == "daedalus"
            assert row["status"] == "active"
            assert row["rationale"] is None
            assert row["alternatives"] is None
        finally:
            conn.close()


class TestIssues:
    """Test insert_issue, resolve_issue, and get_open_issue_count."""

    def test_insert_and_resolve_issue(self, db: AetherDBSync) -> None:
        # Insert the referenced session first (FK constraint)
        db.insert_session("sess-001", agent="hefesto")
        issue_id = db.insert_issue(
            description="Bug in session handling",
            error_type="RuntimeError",
            session_id="sess-001",
        )
        assert issue_id >= 1

        # Open issue count should be 1
        assert db.get_open_issue_count() == 1

        # Resolve it
        db.resolve_issue(issue_id, resolution="Fixed in commit abc123", resolved_by="hefesto")

        # Open issue count should be 0
        assert db.get_open_issue_count() == 0

        # Verify via direct query
        conn = sqlite3.connect(str(db.db_path))
        conn.row_factory = sqlite3.Row
        try:
            row = conn.execute("SELECT * FROM issues WHERE id = ?", (issue_id,)).fetchone()
            assert row is not None
            assert row["status"] == "resolved"
            assert row["resolution"] == "Fixed in commit abc123"
            assert row["resolved_by"] == "hefesto"
            assert row["resolved_at"] is not None
        finally:
            conn.close()

    def test_get_open_issue_count_multiple(self, db: AetherDBSync) -> None:
        db.insert_issue(description="Issue 1")
        db.insert_issue(description="Issue 2")
        db.insert_issue(description="Issue 3")
        assert db.get_open_issue_count() == 3

        # Resolve one
        db.resolve_issue(1, resolution="Done")
        assert db.get_open_issue_count() == 2

    def test_issue_with_session_id(self, db: AetherDBSync) -> None:
        db.insert_session("sess-issue", agent="hefesto")
        issue_id = db.insert_issue(
            description="Test issue", session_id="sess-issue"
        )
        assert issue_id >= 1

        conn = sqlite3.connect(str(db.db_path))
        conn.row_factory = sqlite3.Row
        try:
            row = conn.execute("SELECT * FROM issues WHERE id = ?", (issue_id,)).fetchone()
            assert row["session_id"] == "sess-issue"
        finally:
            conn.close()


class TestGetAetherDBPath:
    """Test the 3-tier path resolution logic."""

    def test_priority1_aether_home_env(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """AETHER_HOME env var takes priority."""
        custom = tmp_path / "custom_aether_home"
        custom.mkdir()
        monkeypatch.setenv("AETHER_HOME", str(custom))
        # Ensure HERMES_HOME is also set, but AETHER_HOME should win
        monkeypatch.setenv("HERMES_HOME", str(tmp_path / "hermes_home"))

        result = get_aether_db_path()
        assert result == custom / ".aether" / "aether.db"

    def test_priority2_aether_home_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """When no AETHER_HOME, check .aether_home file in HERMES_HOME."""
        monkeypatch.delenv("AETHER_HOME", raising=False)

        hermes_home = tmp_path / "hermes_home"
        hermes_home.mkdir()
        aether_path = tmp_path / "shared_aether"
        aether_path.mkdir()

        # Write .aether_home file pointing to shared_aether
        (hermes_home / ".aether_home").write_text(str(aether_path))
        monkeypatch.setenv("HERMES_HOME", str(hermes_home))

        result = get_aether_db_path()
        assert result == aether_path / ".aether" / "aether.db"

    def test_priority2_aether_home_file_missing(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """When .aether_home file doesn't exist, fall through to cwd."""
        monkeypatch.delenv("AETHER_HOME", raising=False)

        hermes_home = tmp_path / "hermes_home_empty"
        hermes_home.mkdir()
        monkeypatch.setenv("HERMES_HOME", str(hermes_home))

        # .aether_home file doesn't exist — should fall through to cwd
        result = get_aether_db_path()
        assert result == Path.cwd() / ".aether" / "aether.db"

    def test_priority3_cwd_fallback(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """When no AETHER_HOME and no HERMES_HOME, use cwd fallback."""
        monkeypatch.delenv("AETHER_HOME", raising=False)
        monkeypatch.delenv("HERMES_HOME", raising=False)

        result = get_aether_db_path()
        assert result == Path.cwd() / ".aether" / "aether.db"

    def test_priority2_aether_home_file_empty(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """When .aether_home file exists but is empty, fall through to cwd."""
        monkeypatch.delenv("AETHER_HOME", raising=False)

        hermes_home = tmp_path / "hermes_home"
        hermes_home.mkdir()
        (hermes_home / ".aether_home").write_text("")  # empty
        monkeypatch.setenv("HERMES_HOME", str(hermes_home))

        result = get_aether_db_path()
        assert result == Path.cwd() / ".aether" / "aether.db"


# ===========================================================================
# aether_hooks tests
# ===========================================================================


class TestPreLlmCall:
    """Test on_pre_llm_call hook — context injection logic."""

    def test_first_turn_with_context(self, fresh_hooks: dict, tmp_path: Path) -> None:
        """Returns context dict when CONTEXT.md exists and has content."""
        db_path = tmp_path / ".aether" / "aether.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        # Create the db file so that db_path.exists() check passes
        db_path.touch()
        context_md = db_path.parent / "CONTEXT.md"
        context_md.write_text("# Project Context\nSome important context here.")

        with (
            patch.object(hooks_module, "get_aether_db_path", return_value=db_path),
        ):
            result = hooks_module.on_pre_llm_call(
                session_id="sess-1",
                user_message="hello",
                conversation_history=[],
                is_first_turn=True,
                model="gpt-4",
                platform="openai",
                sender_id="user-1",
            )

        assert result is not None
        assert isinstance(result, dict)
        assert "context" in result
        assert result["context"].startswith("[.aether Context]\n")
        assert "Some important context here." in result["context"]

    def test_first_turn_no_context(self, fresh_hooks: dict, tmp_path: Path) -> None:
        """Returns None when no CONTEXT.md exists."""
        db_path = tmp_path / ".aether" / "aether.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        # Don't create CONTEXT.md

        with (
            patch.object(hooks_module, "get_aether_db_path", return_value=db_path),
        ):
            result = hooks_module.on_pre_llm_call(
                session_id="sess-1",
                user_message="hello",
                conversation_history=[],
                is_first_turn=True,
                model="gpt-4",
                platform="openai",
                sender_id="user-1",
            )

        assert result is None

    def test_first_turn_empty_context(self, fresh_hooks: dict, tmp_path: Path) -> None:
        """Returns None when CONTEXT.md exists but is empty."""
        db_path = tmp_path / ".aether" / "aether.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        context_md = db_path.parent / "CONTEXT.md"
        context_md.write_text("   \n  \n  ")  # only whitespace

        with (
            patch.object(hooks_module, "get_aether_db_path", return_value=db_path),
        ):
            result = hooks_module.on_pre_llm_call(
                session_id="sess-1",
                user_message="hello",
                conversation_history=[],
                is_first_turn=True,
                model="gpt-4",
                platform="openai",
                sender_id="user-1",
            )

        assert result is None

    def test_not_first_turn(self, fresh_hooks: dict) -> None:
        """Returns None when is_first_turn=False, regardless of DB state."""
        result = hooks_module.on_pre_llm_call(
            session_id="sess-1",
            user_message="hello",
            conversation_history=[],
            is_first_turn=False,
            model="gpt-4",
            platform="openai",
            sender_id="user-1",
        )
        assert result is None

    def test_no_db(self, fresh_hooks: dict, tmp_path: Path) -> None:
        """Returns None when aether.db doesn't exist on disk."""
        db_path = tmp_path / "nonexistent" / ".aether" / "aether.db"
        # Don't create the file or parent dir

        with (
            patch.object(hooks_module, "get_aether_db_path", return_value=db_path),
        ):
            result = hooks_module.on_pre_llm_call(
                session_id="sess-1",
                user_message="hello",
                conversation_history=[],
                is_first_turn=True,
                model="gpt-4",
                platform="openai",
                sender_id="user-1",
            )

        assert result is None


class TestOnSessionStart:
    """Test on_session_start hook."""

    def test_inserts_session_row(self, fresh_hooks: dict) -> None:
        """Inserts a session row when session ID is available."""
        mock_db = fresh_hooks["db"]

        with (
            patch.object(hooks_module, "_get_session_id", return_value="olympus-sess-1"),
            patch.object(hooks_module, "_detect_agent_name", return_value="hefesto"),
        ):
            hooks_module.on_session_start(session_id="local-sess-1", model="gpt-4", platform="openai")

        mock_db.insert_session.assert_called_once()
        call_kwargs = mock_db.insert_session.call_args
        assert call_kwargs[1]["session_id"] == "olympus-sess-1"
        assert call_kwargs[1]["agent"] == "hefesto"
        assert call_kwargs[1]["model"] == "gpt-4"
        assert call_kwargs[1]["platform"] == "openai"

    def test_no_session_id_skips(self, fresh_hooks: dict) -> None:
        """Does nothing when session ID cannot be resolved."""
        mock_db = fresh_hooks["db"]

        with patch.object(hooks_module, "_get_session_id", return_value=None):
            hooks_module.on_session_start(session_id="local-sess-1")

        mock_db.insert_session.assert_not_called()


class TestOnPostToolCall:
    """Test on_post_tool_call hook for file change recording."""

    def test_records_write_file(self, fresh_hooks: dict) -> None:
        """Records a 'write' action for write_file tool."""
        mock_db = fresh_hooks["db"]

        with (
            patch.object(hooks_module, "_get_session_id", return_value="olympus-sess-1"),
            patch.object(hooks_module, "_detect_agent_name", return_value="hefesto"),
            patch.object(hooks_module, "_make_relative", side_effect=lambda x: x),
        ):
            hooks_module.on_post_tool_call(
                tool_name="write_file",
                args={"path": "/project/src/main.py", "content": "hello"},
                result="ok",
                task_id="t1",
                session_id="s1",
                tool_call_id="tc1",
                duration_ms=100,
            )

        mock_db.insert_file_change.assert_called_once()
        call_kwargs = mock_db.insert_file_change.call_args[1]
        assert call_kwargs["session_id"] == "olympus-sess-1"
        assert call_kwargs["agent"] == "hefesto"
        assert call_kwargs["file_path"] == "/project/src/main.py"
        assert call_kwargs["action"] == "write"

    def test_records_patch(self, fresh_hooks: dict) -> None:
        """Records a 'patch' action for patch tool."""
        mock_db = fresh_hooks["db"]

        with (
            patch.object(hooks_module, "_get_session_id", return_value="olympus-sess-2"),
            patch.object(hooks_module, "_detect_agent_name", return_value="hefesto"),
            patch.object(hooks_module, "_make_relative", side_effect=lambda x: x),
        ):
            hooks_module.on_post_tool_call(
                tool_name="patch",
                args={"path": "/project/src/utils.py", "old_string": "a", "new_string": "b"},
                result="patched",
                task_id="t2",
                session_id="s2",
                tool_call_id="tc2",
                duration_ms=50,
            )

        mock_db.insert_file_change.assert_called_once()
        call_kwargs = mock_db.insert_file_change.call_args[1]
        assert call_kwargs["action"] == "patch"
        assert call_kwargs["file_path"] == "/project/src/utils.py"

    def test_no_session_id_skips(self, fresh_hooks: dict) -> None:
        """Does nothing when session ID cannot be resolved."""
        mock_db = fresh_hooks["db"]

        with patch.object(hooks_module, "_get_session_id", return_value=None):
            hooks_module.on_post_tool_call(
                tool_name="write_file",
                args={"path": "/project/src/main.py"},
                result="ok",
                task_id="t1",
                session_id="s1",
                tool_call_id="tc1",
                duration_ms=100,
            )

        mock_db.insert_file_change.assert_not_called()


class TestOnSessionEnd:
    """Test on_session_end hook."""

    def test_updates_session_and_hot_state(self, fresh_hooks: dict) -> None:
        """Updates session status and hot_state on session end."""
        mock_db = fresh_hooks["db"]

        # Set up mock returns
        mock_db.get_hot_state.return_value = {"total_sessions": 5}

        with (
            patch.object(hooks_module, "_get_session_id", return_value="olympus-sess-end"),
            patch.object(hooks_module, "_detect_agent_name", return_value="hefesto"),
            patch("olympus_v3.aether_hooks.hooks.OlympusDBSync", create=True) as mock_olympus_cls,
        ):
            # Make the olympus db import fail so we skip result_summary
            mock_olympus_cls.side_effect = ImportError("No olympus db")
            hooks_module.on_session_end(
                session_id="local-sess-end",
                completed=True,
                interrupted=False,
                model="gpt-4",
                platform="openai",
            )

        # Verify update_session called with completed status
        mock_db.update_session.assert_called_once_with(
            session_id="olympus-sess-end",
            status="completed",
        )

        # Verify update_hot_state called
        mock_db.update_hot_state.assert_called_once()
        hot_state_kwargs = mock_db.update_hot_state.call_args[1]
        assert hot_state_kwargs["last_agent"] == "hefesto"
        assert hot_state_kwargs["last_session_id"] == "olympus-sess-end"
        assert hot_state_kwargs["total_sessions"] == 6  # 5 + 1

    def test_interrupted_session(self, fresh_hooks: dict) -> None:
        """Session marked as cancelled and last_error set when interrupted."""
        mock_db = fresh_hooks["db"]
        mock_db.get_hot_state.return_value = {"total_sessions": 1}

        with (
            patch.object(hooks_module, "_get_session_id", return_value="olympus-sess-int"),
            patch.object(hooks_module, "_detect_agent_name", return_value="etalides"),
            patch("olympus_v3.aether_hooks.hooks.OlympusDBSync", create=True) as mock_olympus_cls,
        ):
            mock_olympus_cls.side_effect = ImportError("No olympus db")
            hooks_module.on_session_end(
                session_id="local-sess-int",
                completed=False,
                interrupted=True,
                model="claude-3",
                platform="anthropic",
            )

        # Status should be cancelled
        call_args = mock_db.update_session.call_args
        assert call_args[1]["status"] == "cancelled"

        # last_error should be set
        hot_state_kwargs = mock_db.update_hot_state.call_args[1]
        assert hot_state_kwargs["last_error"] == "Session interrupted"