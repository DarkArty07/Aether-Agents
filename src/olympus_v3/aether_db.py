"""Aether continuity database — SQLite persistence for .aether project context.

Manages hot_state, sessions, file_changes, decisions, and issues.
Uses WAL mode for concurrent access between the MCP server (async)
and Daimon plugin hooks (sync).

Database path:
    - Default: $AETHER_HOME/.aether/aether.db (canonical, shared)
    - Fallback: .aether_home file in HERMES_HOME parent → {path}/.aether/aether.db
    - Last resort: cwd/.aether/aether.db

All async methods use aiosqlite. The sync methods (for plugin hooks)
use the stdlib sqlite3 module.
"""

from __future__ import annotations

import logging
import os
import sqlite3
import time
from pathlib import Path
from typing import Any

import aiosqlite

logger = logging.getLogger("olympus_v3.aether_db")

# ---------------------------------------------------------------------------
# Schema DDL
# ---------------------------------------------------------------------------

SCHEMA_HOT_STATE = """
CREATE TABLE IF NOT EXISTS hot_state (
    id INTEGER PRIMARY KEY DEFAULT 1,
    project_name TEXT, project_root TEXT, description TEXT,
    current_phase TEXT DEFAULT 'idea', current_task TEXT,
    last_session_id TEXT, last_agent TEXT,
    last_request TEXT, last_result TEXT, last_error TEXT,
    recent_files TEXT, pending_items TEXT, blockers TEXT,
    total_sessions INTEGER DEFAULT 0, updated_at REAL NOT NULL
)
"""

SCHEMA_SESSIONS = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY, agent TEXT NOT NULL,
    started_at REAL NOT NULL, completed_at REAL, status TEXT DEFAULT 'active',
    request TEXT, result_summary TEXT, files_modified TEXT, errors TEXT,
    model TEXT, platform TEXT, duration_seconds INTEGER
)
"""
CREATE_INDEX_SESSIONS_AGENT = """
CREATE INDEX IF NOT EXISTS idx_sessions_agent ON sessions(agent)
"""
CREATE_INDEX_SESSIONS_STATUS = """
CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status)
"""

SCHEMA_FILE_CHANGES = """
CREATE TABLE IF NOT EXISTS file_changes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT REFERENCES sessions(session_id),
    agent TEXT NOT NULL, file_path TEXT NOT NULL,
    action TEXT NOT NULL, timestamp REAL NOT NULL
)
"""
CREATE_INDEX_FILE_CHANGES_PATH = """
CREATE INDEX IF NOT EXISTS idx_file_changes_path ON file_changes(file_path)
"""
CREATE_INDEX_FILE_CHANGES_SESSION = """
CREATE INDEX IF NOT EXISTS idx_file_changes_session ON file_changes(session_id)
"""

SCHEMA_DECISIONS = """
CREATE TABLE IF NOT EXISTS decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL,
    decision TEXT NOT NULL, rationale TEXT, alternatives TEXT,
    made_by TEXT NOT NULL, status TEXT DEFAULT 'active',
    created_at REAL NOT NULL, superseded_at REAL,
    superseded_by INTEGER REFERENCES decisions(id)
)
"""

SCHEMA_ISSUES = """
CREATE TABLE IF NOT EXISTS issues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT REFERENCES sessions(session_id),
    description TEXT NOT NULL, error_type TEXT,
    resolution TEXT, resolved_by TEXT,
    status TEXT DEFAULT 'open', created_at REAL NOT NULL, resolved_at REAL
)
"""
CREATE_INDEX_ISSUES_STATUS = """
CREATE INDEX IF NOT EXISTS idx_issues_status ON issues(status)
"""

SEED_HOT_STATE = """
INSERT OR IGNORE INTO hot_state (id, project_name, project_root, updated_at)
VALUES (1, '', '', 0)
"""

_SCHEMA_STMTS = (
    SCHEMA_HOT_STATE,
    SCHEMA_SESSIONS,
    CREATE_INDEX_SESSIONS_AGENT,
    CREATE_INDEX_SESSIONS_STATUS,
    SCHEMA_FILE_CHANGES,
    CREATE_INDEX_FILE_CHANGES_PATH,
    CREATE_INDEX_FILE_CHANGES_SESSION,
    SCHEMA_DECISIONS,
    SCHEMA_ISSUES,
    CREATE_INDEX_ISSUES_STATUS,
    SEED_HOT_STATE,
)


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------

def get_aether_db_path() -> Path:
    """Resolve aether database path from env vars or defaults.

    Priority:
        1. AETHER_HOME env var → {AETHER_HOME}/.aether/aether.db
        2. Check for .aether_home file in the Daimon profile directory (HERMES_HOME) → read path
           from that file → {path}/.aether/aether.db
        3. Fallback: cwd/.aether/aether.db
    """
    # Priority 1: AETHER_HOME env var
    aether_home = os.environ.get("AETHER_HOME")
    if aether_home:
        return Path(aether_home) / ".aether" / "aether.db"

    # Priority 2: .aether_home file in the Daimon profile directory
    hermes_home = os.environ.get("HERMES_HOME")
    if hermes_home:
        aether_home_file = Path(hermes_home) / ".aether_home"
        try:
            file_path = aether_home_file.read_text().strip()
            if file_path:
                return Path(file_path) / ".aether" / "aether.db"
        except FileNotFoundError:
            pass
        except Exception as e:
            logger.debug("Could not read .aether_home file %s: %s", aether_home_file, e)

    # Priority 3: cwd fallback
    return Path.cwd() / ".aether" / "aether.db"


def resolve_aether_db(project_root: str) -> Path:
    """Resolve aether database path from project_root.

    Used by MCP tools (aether_status, aether_update, aether_curate) to
    ensure each project reads/writes its own database. Unlike
    get_aether_db_path() which uses AETHER_HOME, this function always
    resolves relative to the given project_root.

    Args:
        project_root: Absolute path to the project root directory.

    Returns:
        Path to {project_root}/.aether/aether.db

    Auto-creates the .aether/ directory if it doesn't exist.
    """
    db_path = Path(project_root) / ".aether" / "aether.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    logger.info("resolve_aether_db: %s", db_path)
    return db_path


def resolve_aether_dir(project_root: str) -> Path:
    """Resolve the .aether/ directory path from project_root.

    Convenience function that returns just the .aether/ directory
    without the database filename.

    Args:
        project_root: Absolute path to the project root directory.

    Returns:
        Path to {project_root}/.aether/

    Auto-creates the directory if it doesn't exist.
    """
    aether_dir = Path(project_root) / ".aether"
    aether_dir.mkdir(parents=True, exist_ok=True)
    return aether_dir


# ---------------------------------------------------------------------------
# Async database (for MCP server)
# ---------------------------------------------------------------------------

class AetherDB:
    """Async SQLite database for .aether continuity data.

    Used by the MCP server which runs in an asyncio event loop.
    Plugin hooks use AetherDBSync instead.
    """

    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or get_aether_db_path()
        self._db: aiosqlite.Connection | None = None

    async def _ensure_dir(self) -> None:
        """Create parent directory if it doesn't exist."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    async def connect(self) -> None:
        """Open connection, enable WAL, create tables."""
        await self._ensure_dir()
        self._db = await aiosqlite.connect(str(self.db_path))
        self._db.row_factory = aiosqlite.Row
        await self._db.execute("PRAGMA journal_mode=WAL")
        await self._db.execute("PRAGMA foreign_keys=ON")
        for stmt in _SCHEMA_STMTS:
            await self._db.execute(stmt)
        await self._db.commit()
        logger.info("AetherDB connected: %s", self.db_path)

    async def close(self) -> None:
        """Close the database connection."""
        if self._db:
            await self._db.close()
            self._db = None

    async def _execute(self, sql: str, params: tuple = ()) -> aiosqlite.Cursor:
        """Execute a SQL statement, auto-connecting if needed."""
        if self._db is None:
            await self.connect()
        assert self._db is not None
        return await self._db.execute(sql, params)

    # -------------------------------------------------------------------
    # Hot state
    # -------------------------------------------------------------------

    async def get_hot_state(self) -> dict[str, Any] | None:
        """Get the single hot_state row as a dict, or None if empty."""
        cursor = await self._execute("SELECT * FROM hot_state WHERE id = 1")
        row = await cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    async def update_hot_state(self, **kwargs: Any) -> None:
        """Update hot_state fields.

        Auto-sets updated_at=time.time() unless an explicit updated_at
        value is provided (e.g. to sync with a file mtime after curation).
        """
        if "updated_at" not in kwargs:
            kwargs["updated_at"] = time.time()
        set_clause = ", ".join(f"{k} = ?" for k in kwargs)
        values = list(kwargs.values())
        await self._execute(
            f"UPDATE hot_state SET {set_clause} WHERE id = 1",
            tuple(values),
        )
        await self._db.commit()

    # -------------------------------------------------------------------
    # Sessions
    # -------------------------------------------------------------------

    async def insert_session(
        self,
        session_id: str,
        agent: str,
        model: str | None = None,
        platform: str | None = None,
    ) -> str:
        """Create a new session row. Returns session_id."""
        now = time.time()
        await self._execute(
            "INSERT INTO sessions (session_id, agent, started_at, status, model, platform) "
            "VALUES (?, ?, ?, 'active', ?, ?)",
            (session_id, agent, now, model, platform),
        )
        await self._db.commit()
        logger.debug("Session created: %s (agent=%s)", session_id, agent)
        return session_id

    async def update_session(
        self,
        session_id: str,
        status: str | None = None,
        result_summary: str | None = None,
        files_modified: str | None = None,
        errors: str | None = None,
        duration_seconds: int | None = None,
    ) -> None:
        """Update session fields. For terminal statuses, also sets completed_at."""
        updates: list[str] = []
        values: list[Any] = []

        if status is not None:
            updates.append("status = ?")
            values.append(status)
            if status in ("completed", "error", "cancelled"):
                updates.append("completed_at = ?")
                values.append(time.time())

        if result_summary is not None:
            updates.append("result_summary = ?")
            values.append(result_summary)

        if files_modified is not None:
            updates.append("files_modified = ?")
            values.append(files_modified)

        if errors is not None:
            updates.append("errors = ?")
            values.append(errors)

        if duration_seconds is not None:
            updates.append("duration_seconds = ?")
            values.append(duration_seconds)

        if not updates:
            return

        values.append(session_id)
        await self._execute(
            f"UPDATE sessions SET {', '.join(updates)} WHERE session_id = ?",
            tuple(values),
        )
        await self._db.commit()

    async def get_recent_sessions(self, limit: int = 3) -> list[dict[str, Any]]:
        """Get most recent sessions ordered by started_at descending."""
        cursor = await self._execute(
            "SELECT * FROM sessions ORDER BY started_at DESC LIMIT ?",
            (limit,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    # -------------------------------------------------------------------
    # File changes
    # -------------------------------------------------------------------

    async def insert_file_change(
        self,
        session_id: str,
        agent: str,
        file_path: str,
        action: str,
    ) -> int:
        """Insert a file change record. Returns row id."""
        now = time.time()
        cursor = await self._execute(
            "INSERT INTO file_changes (session_id, agent, file_path, action, timestamp) "
            "VALUES (?, ?, ?, ?, ?)",
            (session_id, agent, file_path, action, now),
        )
        await self._db.commit()
        return cursor.lastrowid

    async def get_session_files(self, session_id: str) -> list[str]:
        """Get distinct file paths modified in a session."""
        cursor = await self._execute(
            "SELECT DISTINCT file_path FROM file_changes WHERE session_id = ? ORDER BY timestamp",
            (session_id,),
        )
        rows = await cursor.fetchall()
        return [row[0] for row in rows]

    async def get_recent_files(self, limit: int = 10) -> list[str]:
        """Get most recently changed file paths across all sessions."""
        cursor = await self._execute(
            "SELECT DISTINCT file_path FROM file_changes ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        )
        rows = await cursor.fetchall()
        return [row[0] for row in rows]

    # -------------------------------------------------------------------
    # Decisions
    # -------------------------------------------------------------------

    async def insert_decision(
        self,
        title: str,
        decision: str,
        rationale: str | None = None,
        alternatives: str | None = None,
        made_by: str = "hermes",
    ) -> int:
        """Insert a decision record. Returns row id."""
        now = time.time()
        cursor = await self._execute(
            "INSERT INTO decisions (title, decision, rationale, alternatives, made_by, status, created_at) "
            "VALUES (?, ?, ?, ?, ?, 'active', ?)",
            (title, decision, rationale, alternatives, made_by, now),
        )
        await self._db.commit()
        return cursor.lastrowid

    # -------------------------------------------------------------------
    # Issues
    # -------------------------------------------------------------------

    async def insert_issue(
        self,
        description: str,
        error_type: str | None = None,
        session_id: str | None = None,
    ) -> int:
        """Insert an issue record. Returns row id."""
        now = time.time()
        cursor = await self._execute(
            "INSERT INTO issues (session_id, description, error_type, status, created_at) "
            "VALUES (?, ?, ?, 'open', ?)",
            (session_id, description, error_type, now),
        )
        await self._db.commit()
        return cursor.lastrowid

    async def resolve_issue(
        self,
        issue_id: int,
        resolution: str,
        resolved_by: str = "hermes",
    ) -> None:
        """Mark an issue as resolved."""
        now = time.time()
        await self._execute(
            "UPDATE issues SET status = 'resolved', resolution = ?, "
            "resolved_by = ?, resolved_at = ? WHERE id = ?",
            (resolution, resolved_by, now, issue_id),
        )
        await self._db.commit()


# ---------------------------------------------------------------------------
# Sync database (for plugin hooks)
# ---------------------------------------------------------------------------

class AetherDBSync:
    """Synchronous SQLite database for .aether continuity plugin hooks.

    Plugin hooks run inside the hermes-agent process and are called
    synchronously. This class uses the stdlib sqlite3 module.
    """

    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or get_aether_db_path()

    def _connect(self) -> sqlite3.Connection:
        """Open a connection with WAL mode."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def ensure_tables(self) -> None:
        """Create tables if they don't exist. Called once at plugin init."""
        conn = self._connect()
        try:
            for stmt in _SCHEMA_STMTS:
                conn.execute(stmt)
            conn.commit()
        finally:
            conn.close()

    # -------------------------------------------------------------------
    # Hot state (sync)
    # -------------------------------------------------------------------

    def get_hot_state(self) -> dict[str, Any] | None:
        """Get the single hot_state row as a dict, or None if empty."""
        conn = self._connect()
        try:
            cursor = conn.execute("SELECT * FROM hot_state WHERE id = 1")
            row = cursor.fetchone()
            if row is None:
                return None
            return dict(row)
        finally:
            conn.close()

    def update_hot_state(self, **kwargs: Any) -> None:
        """Update hot_state fields.

        Auto-sets updated_at=time.time() unless an explicit updated_at
        value is provided (e.g. to sync with a file mtime after curation).
        """
        if "updated_at" not in kwargs:
            kwargs["updated_at"] = time.time()
        set_clause = ", ".join(f"{k} = ?" for k in kwargs)
        values = list(kwargs.values())
        conn = self._connect()
        try:
            conn.execute(
                f"UPDATE hot_state SET {set_clause} WHERE id = 1",
                tuple(values),
            )
            conn.commit()
        finally:
            conn.close()

    # -------------------------------------------------------------------
    # Sessions (sync)
    # -------------------------------------------------------------------

    def insert_session(
        self,
        session_id: str,
        agent: str,
        model: str | None = None,
        platform: str | None = None,
    ) -> str:
        """Create a new session row synchronously. Returns session_id."""
        conn = self._connect()
        try:
            now = time.time()
            conn.execute(
                "INSERT INTO sessions (session_id, agent, started_at, status, model, platform) "
                "VALUES (?, ?, ?, 'active', ?, ?)",
                (session_id, agent, now, model, platform),
            )
            conn.commit()
            return session_id
        finally:
            conn.close()

    def update_session(
        self,
        session_id: str,
        status: str | None = None,
        result_summary: str | None = None,
        files_modified: str | None = None,
        errors: str | None = None,
        duration_seconds: int | None = None,
    ) -> None:
        """Update session fields synchronously."""
        updates: list[str] = []
        values: list[Any] = []

        if status is not None:
            updates.append("status = ?")
            values.append(status)
            if status in ("completed", "error", "cancelled"):
                updates.append("completed_at = ?")
                values.append(time.time())

        if result_summary is not None:
            updates.append("result_summary = ?")
            values.append(result_summary)

        if files_modified is not None:
            updates.append("files_modified = ?")
            values.append(files_modified)

        if errors is not None:
            updates.append("errors = ?")
            values.append(errors)

        if duration_seconds is not None:
            updates.append("duration_seconds = ?")
            values.append(duration_seconds)

        if not updates:
            return

        values.append(session_id)
        conn = self._connect()
        try:
            conn.execute(
                f"UPDATE sessions SET {', '.join(updates)} WHERE session_id = ?",
                tuple(values),
            )
            conn.commit()
        finally:
            conn.close()

    def get_recent_sessions(self, limit: int = 3) -> list[dict[str, Any]]:
        """Get most recent sessions ordered by started_at descending."""
        conn = self._connect()
        try:
            cursor = conn.execute(
                "SELECT * FROM sessions ORDER BY started_at DESC LIMIT ?",
                (limit,),
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    # -------------------------------------------------------------------
    # File changes (sync)
    # -------------------------------------------------------------------

    def insert_file_change(
        self,
        session_id: str,
        agent: str,
        file_path: str,
        action: str,
    ) -> int:
        """Insert a file change record synchronously. Returns row id."""
        conn = self._connect()
        try:
            now = time.time()
            cursor = conn.execute(
                "INSERT INTO file_changes (session_id, agent, file_path, action, timestamp) "
                "VALUES (?, ?, ?, ?, ?)",
                (session_id, agent, file_path, action, now),
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def get_session_files(self, session_id: str) -> list[str]:
        """Get distinct file paths modified in a session."""
        conn = self._connect()
        try:
            cursor = conn.execute(
                "SELECT DISTINCT file_path FROM file_changes WHERE session_id = ? ORDER BY timestamp",
                (session_id,),
            )
            rows = cursor.fetchall()
            return [row[0] for row in rows]
        finally:
            conn.close()

    def get_recent_files(self, limit: int = 10) -> list[str]:
        """Get most recently changed file paths across all sessions."""
        conn = self._connect()
        try:
            cursor = conn.execute(
                "SELECT DISTINCT file_path FROM file_changes ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            )
            rows = cursor.fetchall()
            return [row[0] for row in rows]
        finally:
            conn.close()

    # -------------------------------------------------------------------
    # Decisions (sync)
    # -------------------------------------------------------------------

    def insert_decision(
        self,
        title: str,
        decision: str,
        rationale: str | None = None,
        alternatives: str | None = None,
        made_by: str = "hermes",
    ) -> int:
        """Insert a decision record synchronously. Returns row id."""
        conn = self._connect()
        try:
            now = time.time()
            cursor = conn.execute(
                "INSERT INTO decisions (title, decision, rationale, alternatives, made_by, status, created_at) "
                "VALUES (?, ?, ?, ?, ?, 'active', ?)",
                (title, decision, rationale, alternatives, made_by, now),
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    # -------------------------------------------------------------------
    # Issues (sync)
    # -------------------------------------------------------------------

    def insert_issue(
        self,
        description: str,
        error_type: str | None = None,
        session_id: str | None = None,
    ) -> int:
        """Insert an issue record synchronously. Returns row id."""
        conn = self._connect()
        try:
            now = time.time()
            cursor = conn.execute(
                "INSERT INTO issues (session_id, description, error_type, status, created_at) "
                "VALUES (?, ?, ?, 'open', ?)",
                (session_id, description, error_type, now),
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def resolve_issue(
        self,
        issue_id: int,
        resolution: str,
        resolved_by: str = "hermes",
    ) -> None:
        """Mark an issue as resolved synchronously."""
        conn = self._connect()
        try:
            now = time.time()
            conn.execute(
                "UPDATE issues SET status = 'resolved', resolution = ?, "
                "resolved_by = ?, resolved_at = ? WHERE id = ?",
                (resolution, resolved_by, now, issue_id),
            )
            conn.commit()
        finally:
            conn.close()

    def get_open_issue_count(self) -> int:
        """Count open issues."""
        conn = self._connect()
        try:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM issues WHERE status = 'open'"
            )
            return cursor.fetchone()[0]
        finally:
            conn.close()
