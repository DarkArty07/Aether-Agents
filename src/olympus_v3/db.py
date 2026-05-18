"""Olympus v3 Database — SQLite persistence for Daimon session data.

Manages sessions, turns, tool_calls, and steering directives.
Uses WAL mode for concurrent access between the MCP server (async)
and Daimon plugin hooks (sync).

Database path:
    - Default: $AETHER_HOME/.olympus/olympus_v3.db (canonical, shared)
    - Fallback: $HERMES_HOME/.olympus/olympus_v3.db (per-profile, not ideal)
    - Override: OLYMPUS_DB_PATH env var

All async methods use aiosqlite. The sync methods (for plugin hooks)
use the stdlib sqlite3 module.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any

import aiosqlite

logger = logging.getLogger("olympus_v3.db")

# ---------------------------------------------------------------------------
# Schema DDL
# ---------------------------------------------------------------------------

SCHEMA_SESSIONS = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id  TEXT PRIMARY KEY,
    agent       TEXT NOT NULL,
    status      TEXT DEFAULT 'active',
    started_at  REAL NOT NULL,
    completed_at REAL,
    metadata    TEXT
)
"""

SCHEMA_TURNS = """
CREATE TABLE IF NOT EXISTS turns (
    turn_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(session_id),
    turn_num   INTEGER NOT NULL,
    role       TEXT NOT NULL,
    content    TEXT,
    reasoning  TEXT,
    timestamp  REAL NOT NULL,
    metadata   TEXT
)
"""

SCHEMA_TOOL_CALLS = """
CREATE TABLE IF NOT EXISTS tool_calls (
    call_id    TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(session_id),
    turn_id    INTEGER REFERENCES turns(turn_id),
    tool_name  TEXT NOT NULL,
    arguments  TEXT,
    result     TEXT,
    status     TEXT DEFAULT 'pending',
    timestamp  REAL NOT NULL
)
"""

SCHEMA_STEERING = """
CREATE TABLE IF NOT EXISTS steering (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(session_id),
    directive  TEXT NOT NULL,
    priority   INTEGER DEFAULT 0,
    consumed   INTEGER DEFAULT 0,
    timestamp  REAL NOT NULL
)
"""

INDEX_SESSION_TURN = """
CREATE INDEX IF NOT EXISTS idx_turns_session_turn
ON turns(session_id, turn_num)
"""

INDEX_TOOL_CALLS_SESSION = """
CREATE INDEX IF NOT EXISTS idx_tool_calls_session
ON tool_calls(session_id)
"""

INDEX_STEERING_CONSUMED = """
CREATE INDEX IF NOT EXISTS idx_steering_session_consumed
ON steering(session_id, consumed)
"""

_SCHEMA_STMTS = (
    SCHEMA_SESSIONS,
    SCHEMA_TURNS,
    SCHEMA_TOOL_CALLS,
    SCHEMA_STEERING,
    INDEX_SESSION_TURN,
    INDEX_TOOL_CALLS_SESSION,
    INDEX_STEERING_CONSUMED,
)


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------

def get_db_path() -> Path:
    """Resolve database path from env var or defaults.

    Priority: OLYMPUS_DB_PATH > AETHER_HOME/.olympus > HERMES_HOME/.olympus > ~/.hermes/.olympus

    The canonical location is AETHER_HOME/.olympus/olympus_v3.db because
    it is shared across all processes (MCP server + plugin hooks inside Daimons).
    HERMES_HOME points to a specific profile dir, so using it would create
    a separate DB per Daimon profile — incorrect for a shared observability DB.
    """
    env_path = os.environ.get("OLYMPUS_DB_PATH")
    if env_path:
        return Path(env_path)

    # AETHER_HOME is the canonical location (shared across all Daimon profiles)
    aether_home = os.environ.get("AETHER_HOME")
    if aether_home:
        return Path(aether_home) / ".olympus" / "olympus_v3.db"

    # Fallback: HERMES_HOME (per-profile, NOT ideal for shared DB)
    hermes_home = os.environ.get("HERMES_HOME")
    if hermes_home:
        return Path(hermes_home) / ".olympus" / "olympus_v3.db"

    return Path(os.path.expanduser("~/.hermes")) / ".olympus" / "olympus_v3.db"


# ---------------------------------------------------------------------------
# Async database (for MCP server)
# ---------------------------------------------------------------------------

class OlympusDB:
    """Async SQLite database for Olympus v3 session data.

    Used by the MCP server (server.py) which runs in an asyncio event loop.
    Plugin hooks use the sync functions below instead.
    """

    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or get_db_path()
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
        logger.info("OlympusDB connected: %s", self.db_path)

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
    # Sessions
    # -------------------------------------------------------------------

    async def insert_session(
        self,
        session_id: str | None = None,
        agent: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Create a new session. Returns session_id."""
        sid = session_id or str(uuid.uuid4())
        now = time.time()
        meta_json = json.dumps(metadata) if metadata else None
        await self._execute(
            "INSERT INTO sessions (session_id, agent, status, started_at, metadata) "
            "VALUES (?, ?, 'active', ?, ?)",
            (sid, agent, now, meta_json),
        )
        await self._db.commit()
        logger.debug("Session created: %s (agent=%s)", sid, agent)
        return sid

    async def update_session_status(
        self, session_id: str, status: str, metadata: dict[str, Any] | None = None
    ) -> None:
        """Update session status. For 'completed' or 'error', also set completed_at."""
        now = time.time()
        if status in ("completed", "error", "cancelled"):
            await self._execute(
                "UPDATE sessions SET status = ?, completed_at = ? WHERE session_id = ?",
                (status, now, session_id),
            )
        else:
            await self._execute(
                "UPDATE sessions SET status = ? WHERE session_id = ?",
                (status, session_id),
            )
        if metadata:
            await self._execute(
                "UPDATE sessions SET metadata = ? WHERE session_id = ?",
                (json.dumps(metadata), session_id),
            )
        await self._db.commit()

    async def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Get session row as dict."""
        cursor = await self._execute(
            "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    # -------------------------------------------------------------------
    # Turns
    # -------------------------------------------------------------------

    async def insert_turn(
        self,
        session_id: str,
        turn_num: int,
        role: str,
        content: str | None = None,
        reasoning: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """Insert a turn. Returns turn_id."""
        now = time.time()
        meta_json = json.dumps(metadata) if metadata else None
        cursor = await self._execute(
            "INSERT INTO turns (session_id, turn_num, role, content, reasoning, timestamp, metadata) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (session_id, turn_num, role, content, reasoning, now, meta_json),
        )
        await self._db.commit()
        return cursor.lastrowid

    async def get_latest_turn(self, session_id: str) -> dict[str, Any] | None:
        """Get the latest assistant turn for a session."""
        cursor = await self._execute(
            "SELECT * FROM turns WHERE session_id = ? AND role = 'assistant' "
            "ORDER BY turn_num DESC LIMIT 1",
            (session_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    async def get_turns(
        self, session_id: str, since_turn: int = 0
    ) -> list[dict[str, Any]]:
        """Get all turns for a session, optionally since a given turn number."""
        cursor = await self._execute(
            "SELECT * FROM turns WHERE session_id = ? AND turn_num > ? ORDER BY turn_num",
            (session_id, since_turn),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    # -------------------------------------------------------------------
    # Tool calls
    # -------------------------------------------------------------------

    async def insert_tool_call(
        self,
        call_id: str,
        session_id: str,
        tool_name: str,
        turn_id: int | None = None,
        arguments: str | None = None,
        result: str | None = None,
        status: str = "pending",
    ) -> None:
        """Insert a tool call record."""
        now = time.time()
        await self._execute(
            "INSERT INTO tool_calls (call_id, session_id, turn_id, tool_name, arguments, result, status, timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (call_id, session_id, turn_id, tool_name, arguments, result, status, now),
        )
        await self._db.commit()

    async def update_tool_call_result(
        self, call_id: str, result: str, status: str = "completed"
    ) -> None:
        """Update a tool call with its result."""
        await self._execute(
            "UPDATE tool_calls SET result = ?, status = ? WHERE call_id = ?",
            (result, status, call_id),
        )
        await self._db.commit()

    async def get_tool_calls(self, session_id: str) -> list[dict[str, Any]]:
        """Get all tool calls for a session."""
        cursor = await self._execute(
            "SELECT * FROM tool_calls WHERE session_id = ? ORDER BY timestamp",
            (session_id,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    # -------------------------------------------------------------------
    # Steering
    # -------------------------------------------------------------------

    async def insert_steering(
        self, session_id: str, directive: str, priority: int = 0
    ) -> int:
        """Insert a steering directive. Returns steering id."""
        now = time.time()
        cursor = await self._execute(
            "INSERT INTO steering (session_id, directive, priority, consumed, timestamp) "
            "VALUES (?, ?, ?, 0, ?)",
            (session_id, directive, priority, now),
        )
        await self._db.commit()
        return cursor.lastrowid

    async def consume_steering(self, session_id: str) -> list[str]:
        """Read and mark as consumed all pending steering directives for a session.

        Returns list of directive strings, ordered by priority (highest first).
        Marks them as consumed in a single transaction.
        """
        cursor = await self._execute(
            "SELECT id, directive FROM steering "
            "WHERE session_id = ? AND consumed = 0 "
            "ORDER BY priority DESC, timestamp ASC",
            (session_id,),
        )
        rows = await cursor.fetchall()
        if not rows:
            return []
        directives = [row[1] for row in rows]
        ids = [row[0] for row in rows]
        placeholders = ",".join("?" * len(ids))
        await self._execute(
            f"UPDATE steering SET consumed = 1 WHERE id IN ({placeholders})", ids
        )
        await self._db.commit()
        return directives

    # -------------------------------------------------------------------
    # Progress / Poll
    # -------------------------------------------------------------------

    async def cleanup_stale_sessions(self, timeout: int = 3600) -> int:
        """Mark sessions stuck in 'active' for longer than *timeout* seconds as 'error'.

        Returns the number of rows updated.
        """
        cutoff = time.time() - timeout
        cursor = await self._execute(
            "UPDATE sessions SET status = 'error', completed_at = ? "
            "WHERE status = 'active' AND started_at < ?",
            (time.time(), cutoff),
        )
        await self._db.commit()
        return cursor.rowcount

    # -------------------------------------------------------------------
    # Progress / Poll
    # -------------------------------------------------------------------

    async def get_session_progress(self, session_id: str) -> dict[str, Any]:
        """Get progress summary for poll responses.

        Returns dict with:
            - thoughts: number of assistant turns
            - messages: number of turns with content
            - tool_calls: number of tool calls
            - status: session status
            - last_turn: latest assistant turn content (or None)
            - last_reasoning: latest reasoning content (or None)
        """
        # Session status
        session = await self.get_session(session_id)
        status = session["status"] if session else "unknown"

        # Count turns
        # ⚡ Bolt: Combine multiple COUNT aggregate queries into a single query to reduce database roundtrips
        cursor = await self._execute(
            """
            SELECT
                COALESCE(SUM(CASE WHEN role = 'assistant' THEN 1 ELSE 0 END), 0),
                COALESCE(SUM(CASE WHEN content IS NOT NULL AND content != '' THEN 1 ELSE 0 END), 0)
            FROM turns WHERE session_id = ?
            """,
            (session_id,),
        )
        row = await cursor.fetchone()
        thoughts = row[0]
        messages = row[1]

        # Count tool calls
        cursor = await self._execute(
            "SELECT COUNT(*) FROM tool_calls WHERE session_id = ?", (session_id,)
        )
        tool_calls_count = (await cursor.fetchone())[0]

        # Latest turn
        latest = await self.get_latest_turn(session_id)

        return {
            "thoughts": thoughts,
            "messages": messages,
            "tool_calls": tool_calls_count,
            "status": status,
            "last_turn": latest["content"] if latest else None,
            "last_reasoning": latest["reasoning"] if latest else None,
        }


# ---------------------------------------------------------------------------
# Sync database (for plugin hooks)
# ---------------------------------------------------------------------------

class OlympusDBSync:
    """Synchronous SQLite database for Olympus v3 plugin hooks.

    Plugin hooks run inside the hermes-agent process and are called
    synchronously. This class uses the stdlib sqlite3 module.
    """

    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or get_db_path()

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
    # Turns (sync — called from post_llm_call hook)
    # -------------------------------------------------------------------

    def insert_turn(
        self,
        session_id: str,
        turn_num: int,
        role: str,
        content: str | None = None,
        reasoning: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """Insert a turn synchronously. Returns turn_id."""
        conn = self._connect()
        try:
            now = time.time()
            meta_json = json.dumps(metadata) if metadata else None
            cursor = conn.execute(
                "INSERT INTO turns (session_id, turn_num, role, content, reasoning, timestamp, metadata) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (session_id, turn_num, role, content, reasoning, now, meta_json),
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    # -------------------------------------------------------------------
    # Tool calls (sync — called from post_tool_call hook)
    # -------------------------------------------------------------------

    def insert_tool_call(
        self,
        call_id: str,
        session_id: str,
        tool_name: str,
        turn_id: int | None = None,
        arguments: str | None = None,
        result: str | None = None,
        status: str = "pending",
    ) -> None:
        """Insert a tool call record synchronously."""
        conn = self._connect()
        try:
            now = time.time()
            conn.execute(
                "INSERT INTO tool_calls (call_id, session_id, turn_id, tool_name, arguments, result, status, timestamp) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (call_id, session_id, turn_id, tool_name, arguments, result, status, now),
            )
            conn.commit()
        finally:
            conn.close()

    def update_tool_call_result(
        self, call_id: str, result: str, status: str = "completed"
    ) -> None:
        """Update a tool call with its result synchronously."""
        conn = self._connect()
        try:
            conn.execute(
                "UPDATE tool_calls SET result = ?, status = ? WHERE call_id = ?",
                (result, status, call_id),
            )
            conn.commit()
        finally:
            conn.close()

    # -------------------------------------------------------------------
    # Session status (sync — called from on_session_end hook)
    # -------------------------------------------------------------------

    def update_session_status(
        self, session_id: str, status: str
    ) -> None:
        """Update session status. Sets completed_at for terminal statuses."""
        conn = self._connect()
        try:
            now = time.time()
            if status in ("completed", "error", "cancelled"):
                conn.execute(
                    "UPDATE sessions SET status = ?, completed_at = ? WHERE session_id = ?",
                    (status, now, session_id),
                )
            else:
                conn.execute(
                    "UPDATE sessions SET status = ? WHERE session_id = ?",
                    (status, session_id),
                )
            conn.commit()
        finally:
            conn.close()

    # -------------------------------------------------------------------
    # Steering (sync — called from pre_llm_call hook)
    # -------------------------------------------------------------------

    def insert_steering(self, session_id: str, directive: str, priority: int = 0) -> int:
        """Insert a steering directive synchronously. Returns steering id."""
        conn = self._connect()
        try:
            now = time.time()
            cursor = conn.execute(
                "INSERT INTO steering (session_id, directive, priority, consumed, timestamp) "
                "VALUES (?, ?, ?, 0, ?)",
                (session_id, directive, priority, now),
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def consume_steering(self, session_id: str) -> list[str]:
        """Read pending directives and mark consumed. Returns directives ordered by priority."""
        conn = self._connect()
        try:
            cursor = conn.execute(
                "SELECT id, directive FROM steering "
                "WHERE session_id = ? AND consumed = 0 "
                "ORDER BY priority DESC, timestamp ASC",
                (session_id,),
            )
            rows = cursor.fetchall()
            if not rows:
                return []
            directives = [row[1] for row in rows]
            ids = [row[0] for row in rows]
            placeholders = ",".join("?" * len(ids))
            conn.execute(
                f"UPDATE steering SET consumed = 1 WHERE id IN ({placeholders})", ids
            )
            conn.commit()
            return directives
        finally:
            conn.close()

    def cleanup_stale_sessions_sync(self, timeout: int = 3600) -> int:
        """Mark sessions stuck in 'active' for longer than *timeout* seconds as 'error'.

        Returns the number of rows updated.
        """
        conn = self._connect()
        try:
            cutoff = time.time() - timeout
            cursor = conn.execute(
                "UPDATE sessions SET status = 'error', completed_at = ? "
                "WHERE status = 'active' AND started_at < ?",
                (time.time(), cutoff),
            )
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()

    # -------------------------------------------------------------------
    # Progress (sync — rarely used, mainly for debugging)
    # -------------------------------------------------------------------

    def get_session_progress(self, session_id: str) -> dict[str, Any]:
        """Get progress summary synchronously."""
        conn = self._connect()
        try:
            # Session status
            cursor = conn.execute(
                "SELECT status FROM sessions WHERE session_id = ?", (session_id,)
            )
            row = cursor.fetchone()
            status = row[0] if row else "unknown"

            # Count turns
            # ⚡ Bolt: Combine multiple COUNT aggregate queries into a single query to reduce database roundtrips
            cursor = conn.execute(
                """
                SELECT
                    COALESCE(SUM(CASE WHEN role = 'assistant' THEN 1 ELSE 0 END), 0),
                    COALESCE(SUM(CASE WHEN content IS NOT NULL AND content != '' THEN 1 ELSE 0 END), 0)
                FROM turns WHERE session_id = ?
                """,
                (session_id,),
            )
            row = cursor.fetchone()
            thoughts = row[0]
            messages = row[1]

            # Count tool calls
            cursor = conn.execute(
                "SELECT COUNT(*) FROM tool_calls WHERE session_id = ?", (session_id,)
            )
            tool_calls_count = cursor.fetchone()[0]

            # Latest turn
            cursor = conn.execute(
                "SELECT content, reasoning FROM turns WHERE session_id = ? AND role = 'assistant' "
                "ORDER BY turn_num DESC LIMIT 1",
                (session_id,),
            )
            latest = cursor.fetchone()

            return {
                "thoughts": thoughts,
                "messages": messages,
                "tool_calls": tool_calls_count,
                "status": status,
                "last_turn": latest[0] if latest else None,
                "last_reasoning": latest[1] if latest else None,
            }
        finally:
            conn.close()
