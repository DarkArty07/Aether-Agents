"""Tests for .aether continuity system — AetherDBSync and aether_hooks.

Uses tmp_path fixtures for test databases (never touches the real aether.db).
Hook tests mock the DB and file system operations to ensure isolation.
"""

from __future__ import annotations

import asyncio
import os
import sqlite3
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from acp.schema import PermissionOption

from olympus_v3.acp_manager import ACPManager, AgentState, OlympusACPClient, SessionInfo
from olympus_v3.aether_db import AetherDBSync, get_aether_db_path, resolve_aether_db, resolve_aether_dir
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


# ===========================================================================
# resolve_aether_db / resolve_aether_dir tests
# ===========================================================================


class TestResolveAetherDB:
    """Test resolve_aether_db() for project-root-based DB path resolution."""

    def test_returns_correct_path(self, tmp_path: Path) -> None:
        """resolve_aether_db returns {project_root}/.aether/aether.db."""
        project_root = str(tmp_path / "myproject")
        result = resolve_aether_db(project_root)
        assert result == Path(project_root) / ".aether" / "aether.db"

    def test_creates_aether_directory(self, tmp_path: Path) -> None:
        """resolve_aether_db auto-creates .aether/ if it doesn't exist."""
        project_root = str(tmp_path / "newproject" / "deep")
        result = resolve_aether_db(project_root)
        assert (Path(project_root) / ".aether").is_dir()

    def test_path_with_spaces(self, tmp_path: Path) -> None:
        """resolve_aether_db handles paths containing spaces."""
        project_root = str(tmp_path / "my project" / "with spaces")
        result = resolve_aether_db(project_root)
        assert result == Path(project_root) / ".aether" / "aether.db"
        assert (Path(project_root) / ".aether").is_dir()

    def test_path_with_special_chars(self, tmp_path: Path) -> None:
        """resolve_aether_db handles paths with special characters."""
        project_root = str(tmp_path / "proj-foo_bar")
        result = resolve_aether_db(project_root)
        assert result == Path(project_root) / ".aether" / "aether.db"

    def test_does_not_use_aether_home(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """resolve_aether_db ignores AETHER_HOME env var — always uses project_root."""
        monkeypatch.setenv("AETHER_HOME", "/completely/different/path")
        project_root = str(tmp_path / "project")
        result = resolve_aether_db(project_root)
        # Must resolve to project_root, NOT to AETHER_HOME
        assert str(result).startswith(project_root)
        assert "/completely/different/path" not in str(result)

    def test_different_projects_different_dbs(self, tmp_path: Path) -> None:
        """Different project_roots resolve to different DB paths."""
        project_a = str(tmp_path / "project-a")
        project_b = str(tmp_path / "project-b")
        path_a = resolve_aether_db(project_a)
        path_b = resolve_aether_db(project_b)
        assert path_a != path_b
        assert "project-a" in str(path_a)
        assert "project-b" in str(path_b)


class TestResolveAetherDir:
    """Test resolve_aether_dir() for project-root-based .aether/ directory."""

    def test_returns_correct_path(self, tmp_path: Path) -> None:
        project_root = str(tmp_path / "myproject")
        result = resolve_aether_dir(project_root)
        assert result == Path(project_root) / ".aether"

    def test_creates_directory(self, tmp_path: Path) -> None:
        project_root = str(tmp_path / "newproject" / "deep")
        result = resolve_aether_dir(project_root)
        assert result.is_dir()

    def test_db_path_inside_dir(self, tmp_path: Path) -> None:
        """DB path from resolve_aether_db is inside dir from resolve_aether_dir."""
        project_root = str(tmp_path / "myproject")
        db_path = resolve_aether_db(project_root)
        dir_path = resolve_aether_dir(project_root)
        assert db_path.parent == dir_path


# ===========================================================================
# Multi-project isolation tests
# ===========================================================================


class TestMultiProjectIsolation:
    """Test that different project_roots lead to completely isolated databases."""

    def test_different_projects_separate_data(self, tmp_path: Path) -> None:
        """Writes to project A do not appear in project B's DB."""
        project_a = tmp_path / "project-a"
        project_b = tmp_path / "project-b"

        db_a = AetherDBSync(db_path=resolve_aether_db(str(project_a)))
        db_a.ensure_tables()
        db_b = AetherDBSync(db_path=resolve_aether_db(str(project_b)))
        db_b.ensure_tables()

        # Write to project A
        db_a.update_hot_state(project_name="Project A", current_phase="code")
        db_a.insert_session("sess-a1", agent="hefesto")
        db_a.insert_decision(title="Use SQLite", decision="SQLite for A")

        # Write to project B
        db_b.update_hot_state(project_name="Project B", current_phase="idea")
        db_b.insert_session("sess-b1", agent="ariadna")

        # Verify isolation
        state_a = db_a.get_hot_state()
        state_b = db_b.get_hot_state()
        assert state_a["project_name"] == "Project A"
        assert state_b["project_name"] == "Project B"

        sessions_a = db_a.get_recent_sessions(limit=10)
        sessions_b = db_b.get_recent_sessions(limit=10)
        assert len(sessions_a) == 1
        assert len(sessions_b) == 1
        assert sessions_a[0]["session_id"] == "sess-a1"
        assert sessions_b[0]["session_id"] == "sess-b1"

    def test_db_reads_from_project_root_not_home(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """resolve_aether_db uses project_root even when AETHER_HOME points elsewhere."""
        # Set AETHER_HOME to a different location
        other_home = tmp_path / "other_home"
        other_home.mkdir()
        monkeypatch.setenv("AETHER_HOME", str(other_home))

        project_root = str(tmp_path / "myproject")
        db_path = resolve_aether_db(project_root)

        # Verify the path is under project_root, not AETHER_HOME
        assert str(db_path).startswith(project_root)
        assert str(other_home) not in str(db_path)

    def test_reads_write_to_correct_db(self, tmp_path: Path) -> None:
        """Data written via resolve_aether_db reads back correctly from the same project."""
        project_root = str(tmp_path / "myproject")
        db = AetherDBSync(db_path=resolve_aether_db(project_root))
        db.ensure_tables()

        db.update_hot_state(
            project_name="IsolationTest",
            current_phase="test",
            project_root=project_root,
        )
        db.insert_session("sess-iso1", agent="hefesto")
        db.insert_issue(description="Test issue", error_type="TestError")

        # Read back from same path
        state = db.get_hot_state()
        assert state["project_name"] == "IsolationTest"
        assert state["current_phase"] == "test"
        assert state["project_root"] == project_root

        sessions = db.get_recent_sessions(limit=10)
        assert len(sessions) == 1
        assert sessions[0]["session_id"] == "sess-iso1"

        assert db.get_open_issue_count() == 1


# ===========================================================================
# Hook project_root tests
# ===========================================================================


class TestHookProjectRoot:
    """Test that on_post_llm_call and on_session_end write project_root to hot_state."""

    def test_post_llm_call_writes_project_root(self, fresh_hooks: dict, monkeypatch: pytest.MonkeyPatch) -> None:
        """on_post_llm_call writes AETHER_HOME as project_root on first turn."""
        mock_db = fresh_hooks["db"]

        monkeypatch.setenv("AETHER_HOME", "/my/project/root")
        with patch.object(hooks_module, "_get_session_id", return_value=None):
            hooks_module.on_post_llm_call(
                session_id="sess-1",
                user_message="hello",
                assistant_response="hi",
                conversation_history=[],
                model="gpt-4",
                platform="openai",
            )

        # Verify project_root was included in update_hot_state call
        call_kwargs = mock_db.update_hot_state.call_args[1]
        assert "project_root" in call_kwargs
        assert call_kwargs["project_root"] == "/my/project/root"

    def test_post_llm_call_no_project_root_without_aether_home(self, fresh_hooks: dict, monkeypatch: pytest.MonkeyPatch) -> None:
        """on_post_llm_call does not set project_root if AETHER_HOME is not set."""
        mock_db = fresh_hooks["db"]

        monkeypatch.delenv("AETHER_HOME", raising=False)
        with patch.object(hooks_module, "_get_session_id", return_value=None):
            hooks_module.on_post_llm_call(
                session_id="sess-1",
                user_message="hello",
                assistant_response="hi",
                conversation_history=[],
                model="gpt-4",
                platform="openai",
            )

        call_kwargs = mock_db.update_hot_state.call_args[1]
        assert "project_root" not in call_kwargs

    def test_session_end_writes_project_root(self, fresh_hooks: dict, monkeypatch: pytest.MonkeyPatch) -> None:
        """on_session_end writes AETHER_HOME as project_root."""
        mock_db = fresh_hooks["db"]
        mock_db.get_hot_state.return_value = {"total_sessions": 1}

        monkeypatch.setenv("AETHER_HOME", "/my/project/root")
        with (
            patch.object(hooks_module, "_get_session_id", return_value="olympus-sess-end"),
            patch.object(hooks_module, "_detect_agent_name", return_value="hefesto"),
            patch("olympus_v3.aether_hooks.hooks.OlympusDBSync", create=True) as mock_olympus_cls,
        ):
            mock_olympus_cls.side_effect = ImportError("No olympus db")
            hooks_module.on_session_end(
                session_id="local-sess-end",
                completed=True,
                interrupted=False,
                model="gpt-4",
                platform="openai",
            )

        call_kwargs = mock_db.update_hot_state.call_args[1]
        assert "project_root" in call_kwargs
        assert call_kwargs["project_root"] == "/my/project/root"

    def test_session_end_no_project_root_without_aether_home(self, fresh_hooks: dict, monkeypatch: pytest.MonkeyPatch) -> None:
        """on_session_end does not set project_root if AETHER_HOME is not set."""
        mock_db = fresh_hooks["db"]
        mock_db.get_hot_state.return_value = {"total_sessions": 1}

        monkeypatch.delenv("AETHER_HOME", raising=False)
        with (
            patch.object(hooks_module, "_get_session_id", return_value="olympus-sess-end"),
            patch.object(hooks_module, "_detect_agent_name", return_value="hefesto"),
            patch("olympus_v3.aether_hooks.hooks.OlympusDBSync", create=True) as mock_olympus_cls,
        ):
            mock_olympus_cls.side_effect = ImportError("No olympus db")
            hooks_module.on_session_end(
                session_id="local-sess-end",
                completed=True,
                interrupted=False,
                model="gpt-4",
                platform="openai",
            )

        call_kwargs = mock_db.update_hot_state.call_args[1]
        assert "project_root" not in call_kwargs


# ===========================================================================
# PID-suffixed session/home file tests
# ===========================================================================


class TestPIDSessionFiles:
    """Test that hooks read PID-suffixed files correctly for concurrent Daimon isolation.

    When multiple Daimons share the same HERMES_HOME, PID-suffixed files
    (.olympus_session.{pid}, .aether_home.{pid}) take priority over their
    generic counterparts (.olympus_session, .aether_home).
    """

    def test_session_id_reads_pid_file_first(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """_get_session_id() reads .olympus_session.{pid} over generic .olympus_session."""
        pid = os.getpid()
        hermes_home = tmp_path / "hermes_home"
        hermes_home.mkdir()

        # Write PID-suffixed file (priority)
        pid_file = hermes_home / f".olympus_session.{pid}"
        pid_file.write_text("olympus-sess-pid-123")

        # Write generic file (should be ignored when PID file exists)
        generic_file = hermes_home / ".olympus_session"
        generic_file.write_text("olympus-sess-generic")

        monkeypatch.setenv("HERMES_HOME", str(hermes_home))
        monkeypatch.delenv("OLYMPUS_SESSION_ID", raising=False)

        # Reset module-level cached session ID
        hooks_module._session_id = None  # type: ignore[attr-defined]

        result = hooks_module._get_session_id()
        assert result == "olympus-sess-pid-123"

        # Cleanup module state
        hooks_module._session_id = None  # type: ignore[attr-defined]

    def test_session_id_falls_back_to_generic(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """_get_session_id() falls back to generic .olympus_session when no PID file exists."""
        hermes_home = tmp_path / "hermes_home"
        hermes_home.mkdir()

        # Write generic file only (no PID file)
        generic_file = hermes_home / ".olympus_session"
        generic_file.write_text("olympus-sess-generic")

        monkeypatch.setenv("HERMES_HOME", str(hermes_home))
        monkeypatch.delenv("OLYMPUS_SESSION_ID", raising=False)

        # Reset module-level cached session ID
        hooks_module._session_id = None  # type: ignore[attr-defined]

        result = hooks_module._get_session_id()
        assert result == "olympus-sess-generic"

        # Cleanup module state
        hooks_module._session_id = None  # type: ignore[attr-defined]

    def test_aether_db_reads_pid_home_first(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """_get_aether_db() reads .aether_home.{pid} and uses its path over standard resolution."""
        pid = os.getpid()
        hermes_home = tmp_path / "hermes_home"
        hermes_home.mkdir()

        project_path = tmp_path / "my_project"
        project_path.mkdir()

        # Write PID-suffixed .aether_home file pointing to project path
        pid_home_file = hermes_home / f".aether_home.{pid}"
        pid_home_file.write_text(str(project_path))

        monkeypatch.setenv("HERMES_HOME", str(hermes_home))
        monkeypatch.delenv("AETHER_HOME", raising=False)

        # Reset module-level cached DB
        hooks_module._aether_db = None  # type: ignore[attr-defined]

        db = hooks_module._get_aether_db()
        expected_db_path = project_path / ".aether" / "aether.db"
        assert db.db_path == expected_db_path

        # Cleanup module state
        hooks_module._aether_db = None  # type: ignore[attr-defined]

    def test_aether_db_falls_back_to_standard(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """_get_aether_db() falls back to standard get_aether_db_path() when no PID home file exists."""
        hermes_home = tmp_path / "hermes_home"
        hermes_home.mkdir()

        monkeypatch.setenv("HERMES_HOME", str(hermes_home))
        monkeypatch.delenv("AETHER_HOME", raising=False)

        # Reset module-level cached DB
        hooks_module._aether_db = None  # type: ignore[attr-defined]

        # No .aether_home.{pid} and no .aether_home file — should fall back to cwd
        db = hooks_module._get_aether_db()
        expected_path = Path.cwd() / ".aether" / "aether.db"
        assert db.db_path == expected_path

        # Cleanup module state
        hooks_module._aether_db = None  # type: ignore[attr-defined]


# ===========================================================================
# Keyed agent key tests
# ===========================================================================


class TestKeyedAgentKey:
    """Test ACPManager._agent_key() — the compound key for multi-project isolation."""

    def test_agent_key_with_project_root(self) -> None:
        """_agent_key with a project_root returns (name, project_root)."""
        key = ACPManager._agent_key("hefesto", "/project/A")
        assert key == ("hefesto", "/project/A")

    def test_agent_key_without_project_root(self) -> None:
        """_agent_key with None project_root returns (name, empty string)."""
        key = ACPManager._agent_key("hefesto", None)
        assert key == ("hefesto", "")

    def test_different_projects_different_keys(self) -> None:
        """Different project_roots produce different keys for the same agent."""
        key_a = ACPManager._agent_key("hefesto", "/project/A")
        key_b = ACPManager._agent_key("hefesto", "/project/B")
        assert key_a != key_b

    def test_same_project_same_key(self) -> None:
        """Same agent + project_root produces the same key (dict lookup works)."""
        key1 = ACPManager._agent_key("hefesto", "/project/A")
        key2 = ACPManager._agent_key("hefesto", "/project/A")
        assert key1 == key2

class _PromptDB:
    def __init__(self) -> None:
        self.status_updates: list[tuple[str, str]] = []

    async def update_session_status(self, session_id: str, status: str) -> None:
        self.status_updates.append((session_id, status))


class _PromptConnection:
    def __init__(self, stop_reason: object) -> None:
        self.stop_reason = stop_reason

    async def prompt(self, **kwargs):
        return SimpleNamespace(stop_reason=self.stop_reason)


async def _wait_for_prompt_completion() -> None:
    await asyncio.sleep(0)
    await asyncio.sleep(0)


@pytest.mark.parametrize(
    ("stop_reason", "expected_status"),
    [
        ("end_turn", "completed"),
        ("cancelled", "cancelled"),
        ("refusal", "error"),
        ("max_tokens", "error"),
        ("max_turn_requests", "error"),
        ("unknown_terminal_reason", "error"),
        (SimpleNamespace(value="end_turn"), "completed"),
        (SimpleNamespace(name="cancelled"), "cancelled"),
    ],
)
def test_send_message_maps_acp_stop_reason_to_persisted_terminal_status(
    tmp_path: Path, stop_reason: object, expected_status: str
) -> None:
    manager_db = _PromptDB()
    manager = ACPManager(profiles_dir=tmp_path, db=manager_db)
    session_id = "stop-reason-session"
    project_root = "/project"
    profile_path = tmp_path / "hefesto"
    profile_path.mkdir()
    connection = _PromptConnection(stop_reason)
    manager.sessions[session_id] = SessionInfo(
        session_id=session_id,
        agent_name="hefesto",
        acp_session_id="acp-session",
        project_root=project_root,
    )
    manager.agents[("hefesto", project_root)] = AgentState(
        name="hefesto", profile_path=profile_path, connection=connection, pid=12345
    )

    asyncio.run(manager.send_message(session_id, "test prompt"))
    asyncio.run(_wait_for_prompt_completion())

    assert manager.sessions[session_id].status == expected_status
    assert manager_db.status_updates == [(session_id, expected_status)]


def test_close_uses_explicit_error_override_and_preserves_terminal_failures(tmp_path: Path) -> None:
    manager_db = _PromptDB()
    manager = ACPManager(profiles_dir=tmp_path, db=manager_db)
    session_id = "close-session"
    project_root = "/project"
    profile_path = tmp_path / "hefesto"
    profile_path.mkdir()
    manager.sessions[session_id] = SessionInfo(
        session_id=session_id,
        agent_name="hefesto",
        acp_session_id="acp-session",
        project_root=project_root,
    )
    manager.agents[("hefesto", project_root)] = AgentState(
        name="hefesto", profile_path=profile_path, pid=12345
    )

    result = asyncio.run(manager.close(session_id, terminal_status="error"))

    assert result == {"status": "error", "session_id": session_id}
    assert manager_db.status_updates == [(session_id, "error")]

    manager.sessions[session_id] = SessionInfo(
        session_id=session_id,
        agent_name="hefesto",
        project_root=project_root,
        status="cancelled",
    )
    result = asyncio.run(manager.close(session_id, terminal_status="completed"))

    assert result == {"status": "cancelled", "session_id": session_id}
    assert manager_db.status_updates[-1] == (session_id, "cancelled")


def test_close_rejects_nonterminal_status_override(tmp_path: Path) -> None:
    manager = ACPManager(profiles_dir=tmp_path)
    manager.sessions["close-session"] = SessionInfo(
        session_id="close-session", agent_name="hefesto"
    )

    with pytest.raises(ValueError, match="terminal_status"):
        asyncio.run(manager.close("close-session", terminal_status="active"))


def test_close_defaults_to_completed_for_active_session(tmp_path: Path) -> None:
    manager_db = _PromptDB()
    manager = ACPManager(profiles_dir=tmp_path, db=manager_db)
    manager.sessions["close-session"] = SessionInfo(
        session_id="close-session", agent_name="hefesto"
    )

    result = asyncio.run(manager.close("close-session"))

    assert result == {"status": "completed", "session_id": "close-session"}
    assert manager_db.status_updates == [("close-session", "completed")]


# ===========================================================================
# ACP permission and process ownership regressions
# ===========================================================================


class _ShutdownConnection:
    def __init__(self) -> None:
        self.closed_sessions: list[str] = []
        self.close_calls = 0

    async def close_session(self, session_id: str) -> None:
        self.closed_sessions.append(session_id)

    async def close(self) -> None:
        self.close_calls += 1


class _ProcessContext:
    def __init__(self, exc: Exception | None = None) -> None:
        self.exit_calls = 0
        self.exc = exc
        self.connection: _ShutdownConnection | None = None

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        self.exit_calls += 1
        if self.exc is not None:
            raise self.exc
        if self.connection is not None:
            await self.connection.close()


class _ActualProcess:
    def __init__(self, pid: int = 4242) -> None:
        self.pid = pid
        self.terminate_calls = 0
        self.kill_calls = 0
        self.wait_calls = 0

    def terminate(self) -> None:
        self.terminate_calls += 1

    def kill(self) -> None:
        self.kill_calls += 1

    async def wait(self) -> None:
        self.wait_calls += 1


def _shutdown_manager(tmp_path: Path, context: _ProcessContext, process: _ActualProcess) -> ACPManager:
    profile_path = tmp_path / "hefesto"
    profile_path.mkdir()
    manager = ACPManager(profiles_dir=tmp_path)
    agent = AgentState(
        name="hefesto",
        profile_path=profile_path,
        connection=_ShutdownConnection(),
        process_context=context,
        process=process,
        pid=process.pid,
        status="idle",
    )
    context.connection = agent.connection
    manager.agents[("hefesto", "/project")] = agent
    return manager


def test_request_permission_prefers_offered_allow_always_option() -> None:
    response = asyncio.run(OlympusACPClient().request_permission(
        [
            PermissionOption(kind="allow_once", name="Allow once", optionId="once"),
            PermissionOption(kind="allow_always", name="Always allow", optionId="always"),
        ],
        session_id="session",
        tool_call=SimpleNamespace(title="write_file", tool_call_id="tool-1"),
    ))

    assert response.outcome.outcome == "selected"
    assert response.outcome.option_id == "always"


def test_request_permission_falls_back_to_offered_allow_once_option() -> None:
    response = asyncio.run(OlympusACPClient().request_permission(
        [PermissionOption(kind="allow_once", name="Allow once", optionId="once")],
        session_id="session",
    ))

    assert response.outcome.outcome == "selected"
    assert response.outcome.option_id == "once"


def test_request_permission_denies_when_no_allow_option_is_offered() -> None:
    response = asyncio.run(OlympusACPClient().request_permission(
        [PermissionOption(kind="reject_once", name="Reject", optionId="reject")],
        session_id="session",
    ))

    assert response.outcome.outcome == "cancelled"


def test_spawn_process_keeps_context_manager_and_subprocess_distinct(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import olympus_v3.acp_manager as acp_manager_module

    class _SpawnConnection:
        async def initialize(self, **kwargs):
            return SimpleNamespace(protocol_version="1")

    connection = _SpawnConnection()
    process = _ActualProcess()

    class _SpawnContext:
        async def __aenter__(self):
            return connection, process

    context = _SpawnContext()
    monkeypatch.setattr(acp_manager_module, "spawn_agent_process", lambda *args, **kwargs: context)
    profile_path = tmp_path / "hefesto"
    profile_path.mkdir()
    agent = AgentState(name="hefesto", profile_path=profile_path, status="spawning")

    asyncio.run(ACPManager(profiles_dir=tmp_path)._spawn_process(agent, project_root=str(tmp_path)))

    assert agent.connection is connection
    assert agent.process_context is context
    assert agent.process is process
    assert agent.pid == process.pid


def test_shutdown_exits_context_once_without_terminating_context_or_process(tmp_path: Path) -> None:
    context = _ProcessContext()
    process = _ActualProcess()
    manager = _shutdown_manager(tmp_path, context, process)
    agent = manager.agents[("hefesto", "/project")]
    connection = agent.connection
    manager.sessions["session"] = SessionInfo(
        session_id="session",
        agent_name="hefesto",
        acp_session_id="acp-session",
        project_root="/project",
    )
    agent.acp_session_ids["session"] = "acp-session"

    result = asyncio.run(manager.shutdown_agent("hefesto", project_root="/project"))

    assert result["status"] == "shutdown"
    assert connection.closed_sessions == ["acp-session"]
    assert connection.close_calls == 1
    assert context.exit_calls == 1
    assert process.terminate_calls == 0
    assert process.kill_calls == 0
    assert ("hefesto", "/project") not in manager.agents


def test_shutdown_context_owns_connection_close_once(tmp_path: Path) -> None:
    context = _ProcessContext()
    process = _ActualProcess()
    manager = _shutdown_manager(tmp_path, context, process)
    connection = manager.agents[("hefesto", "/project")].connection

    asyncio.run(manager.shutdown_agent("hefesto", project_root="/project"))

    assert context.exit_calls == 1
    assert connection.close_calls == 1


def test_shutdown_terminates_actual_process_when_context_exit_fails(tmp_path: Path) -> None:
    context = _ProcessContext(RuntimeError("context cleanup failed"))
    process = _ActualProcess()
    manager = _shutdown_manager(tmp_path, context, process)

    asyncio.run(manager.shutdown_agent("hefesto", project_root="/project"))

    assert context.exit_calls == 1
    assert process.terminate_calls == 1
    assert process.wait_calls == 1


def test_shutdown_context_timeout_escalates_to_kill(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import olympus_v3.acp_manager as acp_manager_module

    class _HangingContext(_ProcessContext):
        async def __aexit__(self, exc_type, exc, traceback) -> None:
            self.exit_calls += 1
            await asyncio.Event().wait()

    class _EscalatingProcess(_ActualProcess):
        async def wait(self) -> None:
            self.wait_calls += 1
            if self.wait_calls == 1:
                await asyncio.Event().wait()

    real_wait_for = asyncio.wait_for

    async def _short_wait_for(awaitable, timeout):
        return await real_wait_for(awaitable, timeout=0.001)

    monkeypatch.setattr(acp_manager_module.asyncio, "wait_for", _short_wait_for)
    context = _HangingContext()
    process = _EscalatingProcess()
    manager = _shutdown_manager(tmp_path, context, process)

    asyncio.run(manager.shutdown_agent("hefesto", project_root="/project"))

    assert context.exit_calls == 1
    assert process.terminate_calls == 1
    assert process.kill_calls == 1
    assert process.wait_calls == 2
