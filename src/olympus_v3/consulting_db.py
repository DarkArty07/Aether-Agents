"""Olympus Consulting DB — SQLite persistence for Daimon consultation sessions.

Manages sessions, agent consultations, and task contracts for the consult workflow.
Database is stored at <project_root>/.aether/.consulting/consulting.db and is
auto-created on first use.

All methods are async and use aiosqlite.  Error handling returns error dicts,
never raises.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiosqlite

logger = logging.getLogger("olympus.consulting_db")

# ---------------------------------------------------------------------------
# Schema DDL
# ---------------------------------------------------------------------------

SCHEMA_SESSIONS = """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    project_root TEXT NOT NULL,
    plan TEXT NOT NULL,
    plan_version INTEGER DEFAULT 1,
    status TEXT DEFAULT 'planning',
    agents_json TEXT NOT NULL,
    context TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
)
"""

SCHEMA_CONSULTATIONS = """
CREATE TABLE IF NOT EXISTS agent_consultations (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id),
    agent TEXT NOT NULL,
    role TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    enrichments_json TEXT,
    contract_json TEXT,
    refusals_json TEXT,
    plan_suggestion TEXT,
    raw_response TEXT,
    consulted_at TIMESTAMP,
    signed_at TIMESTAMP,
    created_at TIMESTAMP
)
"""

SCHEMA_TASKS = """
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id),
    task_id TEXT NOT NULL,
    description TEXT NOT NULL,
    assigned_agent TEXT,
    status TEXT DEFAULT 'pending',
    acceptance_criteria_json TEXT,
    complexity TEXT,
    dependencies_json TEXT,
    attempts INTEGER DEFAULT 0,
    created_at TIMESTAMP
)
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SCHEMA_STMTS = (SCHEMA_SESSIONS, SCHEMA_CONSULTATIONS, SCHEMA_TASKS)


def _now_iso() -> str:
    """UTC ISO-8601 timestamp."""
    return datetime.now(timezone.utc).isoformat()


def _err(msg: str, **extra: Any) -> dict[str, Any]:
    """Return a standardised error dict."""
    return {"error": msg, **extra}


# ---------------------------------------------------------------------------
# ConsultingDB
# ---------------------------------------------------------------------------


class ConsultingDB:
    """Async SQLite database for consulting sessions.

    Auto-creates the database and directory on first use.
    All public methods return result dicts on success or error dicts on failure;
    they never raise exceptions.
    """

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self._conn: aiosqlite.Connection | None = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _ensure_db(self) -> aiosqlite.Connection | None:
        """Ensure database, directory, and tables exist. Return connection or None on error."""
        try:
            if self._conn is not None:
                return self._conn

            self.db_path.parent.mkdir(parents=True, exist_ok=True)

            self._conn = await aiosqlite.connect(str(self.db_path))
            self._conn.row_factory = aiosqlite.Row

            for stmt in _SCHEMA_STMTS:
                await self._conn.execute(stmt)
            await self._conn.commit()

            logger.info("ConsultingDB initialised at %s", self.db_path)
            return self._conn
        except Exception as exc:
            logger.error("Failed to initialise ConsultingDB: %s", exc)
            # Reset so we can retry later
            if self._conn is not None:
                try:
                    await self._conn.close()
                except Exception:
                    pass
                self._conn = None
            return None

    async def _get_conn(self) -> aiosqlite.Connection | dict[str, Any]:
        """Ensure DB is ready; return connection or error dict."""
        conn = await self._ensure_db()
        if conn is None:
            return _err("Database unavailable")
        return conn

    async def close(self) -> None:
        """Close the database connection."""
        if self._conn is not None:
            try:
                await self._conn.close()
            except Exception:
                pass
            self._conn = None

    # ------------------------------------------------------------------
    # Session CRUD
    # ------------------------------------------------------------------

    async def create_session(
        self,
        plan: str,
        agents: list[str],
        context: str | None = None,
        project_root: str | None = None,
    ) -> dict[str, Any]:
        """Create a new consulting session. Returns session dict or error dict."""
        try:
            conn = await self._get_conn()
            if isinstance(conn, dict):
                return conn

            session_id = str(uuid.uuid4())
            now = _now_iso()

            await conn.execute(
                """
                INSERT INTO sessions
                    (id, project_root, plan, plan_version, status, agents_json, context,
                     created_at, updated_at)
                VALUES (?, ?, ?, 1, 'planning', ?, ?, ?, ?)
                """,
                (
                    session_id,
                    project_root or "",
                    plan,
                    json.dumps(agents),
                    context or "",
                    now,
                    now,
                ),
            )
            await conn.commit()

            return {
                "id": session_id,
                "project_root": project_root or "",
                "plan": plan,
                "plan_version": 1,
                "status": "planning",
                "agents": agents,
                "context": context or "",
                "created_at": now,
                "updated_at": now,
            }
        except Exception as exc:
            logger.error("create_session failed: %s", exc)
            return _err(f"create_session failed: {exc}")

    async def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Get a session by ID. Returns session dict, None if not found, or error dict."""
        try:
            conn = await self._get_conn()
            if isinstance(conn, dict):
                return conn

            cursor = await conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
            row = await cursor.fetchone()
            if row is None:
                return None

            return {
                "id": row["id"],
                "project_root": row["project_root"],
                "plan": row["plan"],
                "plan_version": row["plan_version"],
                "status": row["status"],
                "agents": json.loads(row["agents_json"]),
                "context": row["context"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
        except Exception as exc:
            logger.error("get_session failed: %s", exc)
            return _err(f"get_session failed: {exc}")

    async def update_session(self, session_id: str, **kwargs: Any) -> dict[str, Any] | None:
        """Update session fields. Returns updated session dict, None if not found, or error dict."""
        try:
            conn = await self._get_conn()
            if isinstance(conn, dict):
                return conn

            # Verify session exists
            session = await self.get_session(session_id)
            if session is None or isinstance(session, dict) and "error" in session:
                return session

            allowed_fields = {"plan", "plan_version", "status", "context", "agents_json"}
            set_parts: list[str] = []
            set_values: list[Any] = []

            for key, value in kwargs.items():
                db_key = key
                if key == "agents":
                    db_key = "agents_json"
                    value = json.dumps(value)
                if db_key in allowed_fields:
                    set_parts.append(f"{db_key} = ?")
                    set_values.append(value)

            if not set_parts:
                return session

            # Always update updated_at
            set_parts.append("updated_at = ?")
            set_values.append(_now_iso())

            set_values.append(session_id)

            await conn.execute(
                f"UPDATE sessions SET {', '.join(set_parts)} WHERE id = ?",
                set_values,
            )
            await conn.commit()

            return await self.get_session(session_id)
        except Exception as exc:
            logger.error("update_session failed: %s", exc)
            return _err(f"update_session failed: {exc}")

    # ------------------------------------------------------------------
    # Agent Consultations
    # ------------------------------------------------------------------

    async def save_consultation(
        self,
        session_id: str,
        agent: str,
        role: str,
        enrichments: list[dict] | None = None,
        contract: dict | None = None,
        refusals: list[dict] | None = None,
        plan_suggestion: str | None = None,
        raw_response: str | None = None,
    ) -> dict[str, Any]:
        """Save a consultation result from an agent. Sets status='consulted'. Returns consultation dict or error dict."""
        try:
            conn = await self._get_conn()
            if isinstance(conn, dict):
                return conn

            consultation_id = str(uuid.uuid4())
            now = _now_iso()

            enrichments_json = json.dumps(enrichments or [])
            contract_json = json.dumps(contract or {})
            refusals_json = json.dumps(refusals or [])

            await conn.execute(
                """
                INSERT INTO agent_consultations
                    (id, session_id, agent, role, status, enrichments_json, contract_json,
                     refusals_json, plan_suggestion, raw_response, consulted_at, created_at)
                VALUES (?, ?, ?, ?, 'consulted', ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    consultation_id,
                    session_id,
                    agent,
                    role,
                    enrichments_json,
                    contract_json,
                    refusals_json,
                    plan_suggestion or "",
                    raw_response or "",
                    now,
                    now,
                ),
            )
            await conn.commit()

            return {
                "id": consultation_id,
                "session_id": session_id,
                "agent": agent,
                "role": role,
                "status": "consulted",
                "enrichments": enrichments or [],
                "contract": contract or {},
                "refusals": refusals or [],
                "plan_suggestion": plan_suggestion or "",
                "consulted_at": now,
            }
        except Exception as exc:
            logger.error("save_consultation failed: %s", exc)
            return _err(f"save_consultation failed: {exc}")

    async def get_consultation(self, session_id: str, agent: str) -> dict[str, Any] | None:
        """Get a consultation by session_id and agent name. Returns consultation dict, None if not found, or error dict."""
        try:
            conn = await self._get_conn()
            if isinstance(conn, dict):
                return conn

            cursor = await conn.execute(
                "SELECT * FROM agent_consultations WHERE session_id = ? AND agent = ?",
                (session_id, agent),
            )
            row = await cursor.fetchone()
            if row is None:
                return None

            return {
                "id": row["id"],
                "session_id": row["session_id"],
                "agent": row["agent"],
                "role": row["role"],
                "status": row["status"],
                "enrichments": json.loads(row["enrichments_json"]) if row["enrichments_json"] else [],
                "contract": json.loads(row["contract_json"]) if row["contract_json"] else {},
                "refusals": json.loads(row["refusals_json"]) if row["refusals_json"] else [],
                "plan_suggestion": row["plan_suggestion"] or "",
                "raw_response": row["raw_response"] or "",
                "consulted_at": row["consulted_at"],
                "signed_at": row["signed_at"],
                "created_at": row["created_at"],
            }
        except Exception as exc:
            logger.error("get_consultation failed: %s", exc)
            return _err(f"get_consultation failed: {exc}")

    async def update_consultation_status(
        self,
        session_id: str,
        agent: str,
        status: str,
        contract: dict | None = None,
    ) -> dict[str, Any] | None:
        """Update a consultation's status (e.g., to 'signed' or 'refused').
        If contract is provided, updates contract_json as well.
        Returns updated consultation dict, None if not found, or error dict.
        """
        try:
            conn = await self._get_conn()
            if isinstance(conn, dict):
                return conn

            # Verify consultation exists
            consultation = await self.get_consultation(session_id, agent)
            if consultation is None or isinstance(consultation, dict) and "error" in consultation:
                return consultation

            set_parts: list[str] = ["status = ?"]
            set_values: list[Any] = [status]

            if contract is not None:
                set_parts.append("contract_json = ?")
                set_values.append(json.dumps(contract))

            if status == "signed":
                set_parts.append("signed_at = ?")
                set_values.append(_now_iso())

            set_values.extend([session_id, agent])

            await conn.execute(
                f"UPDATE agent_consultations SET {', '.join(set_parts)} WHERE session_id = ? AND agent = ?",
                set_values,
            )
            await conn.commit()

            return await self.get_consultation(session_id, agent)
        except Exception as exc:
            logger.error("update_consultation_status failed: %s", exc)
            return _err(f"update_consultation_status failed: {exc}")

    # ------------------------------------------------------------------
    # Agent management within sessions
    # ------------------------------------------------------------------

    async def add_agent(
        self, session_id: str, agent: str, role: str, reason: str | None = None
    ) -> dict[str, Any] | None:
        """Add an agent to an existing session's agents list and create a pending consultation.
        Returns result dict, None if session not found, or error dict.
        """
        try:
            conn = await self._get_conn()
            if isinstance(conn, dict):
                return conn

            session = await self.get_session(session_id)
            if session is None or isinstance(session, dict) and "error" in session:
                return session

            agents: list[str] = session["agents"]
            if agent in agents:
                return _err(f"Agent '{agent}' already in session")

            agents.append(agent)
            update_result = await self.update_session(session_id, agents=agents)
            if update_result is not None and isinstance(update_result, dict) and "error" in update_result:
                return update_result

            # Create pending consultation row
            consultation_id = str(uuid.uuid4())
            now = _now_iso()
            await conn.execute(
                """
                INSERT INTO agent_consultations
                    (id, session_id, agent, role, status, enrichments_json, contract_json,
                     refusals_json, plan_suggestion, created_at)
                VALUES (?, ?, ?, ?, 'pending', '[]', '{}', '[]', '', ?)
                """,
                (consultation_id, session_id, agent, role, now),
            )
            await conn.commit()

            return {
                "session_id": session_id,
                "agent": agent,
                "role": role,
                "reason": reason or "",
                "status": "pending",
            }
        except Exception as exc:
            logger.error("add_agent failed: %s", exc)
            return _err(f"add_agent failed: {exc}")

    # ------------------------------------------------------------------
    # Tasks
    # ------------------------------------------------------------------

    async def create_task(
        self,
        session_id: str,
        task_id: str,
        description: str,
        assigned_agent: str | None = None,
        acceptance_criteria: list[str] | None = None,
        complexity: str | None = None,
        dependencies: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create a task in a session. Returns task dict or error dict."""
        try:
            conn = await self._get_conn()
            if isinstance(conn, dict):
                return conn

            id_ = str(uuid.uuid4())
            now = _now_iso()

            await conn.execute(
                """
                INSERT INTO tasks
                    (id, session_id, task_id, description, assigned_agent, status,
                     acceptance_criteria_json, complexity, dependencies_json, attempts, created_at)
                VALUES (?, ?, ?, ?, ?, 'pending', ?, ?, ?, 0, ?)
                """,
                (
                    id_,
                    session_id,
                    task_id,
                    description,
                    assigned_agent,
                    json.dumps(acceptance_criteria or []),
                    complexity,
                    json.dumps(dependencies or []),
                    now,
                ),
            )
            await conn.commit()

            return {
                "id": id_,
                "session_id": session_id,
                "task_id": task_id,
                "description": description,
                "assigned_agent": assigned_agent,
                "status": "pending",
                "acceptance_criteria": acceptance_criteria or [],
                "complexity": complexity,
                "dependencies": dependencies or [],
                "attempts": 0,
                "created_at": now,
            }
        except Exception as exc:
            logger.error("create_task failed: %s", exc)
            return _err(f"create_task failed: {exc}")

    async def update_task_status(
        self,
        task_id: str,
        status: str,
        increment_attempts: bool = False,
    ) -> dict[str, Any] | None:
        """Update a task's status and optionally increment the attempts counter.
        Returns updated task dict, None if not found, or error dict.
        """
        try:
            conn = await self._get_conn()
            if isinstance(conn, dict):
                return conn

            cursor = await conn.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
            row = await cursor.fetchone()
            if row is None:
                return None

            if increment_attempts:
                await conn.execute(
                    "UPDATE tasks SET status = ?, attempts = attempts + 1 WHERE task_id = ?",
                    (status, task_id),
                )
            else:
                await conn.execute(
                    "UPDATE tasks SET status = ? WHERE task_id = ?",
                    (status, task_id),
                )
            await conn.commit()

            # Return updated task
            cursor = await conn.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
            row = await cursor.fetchone()
            return {
                "id": row["id"],
                "session_id": row["session_id"],
                "task_id": row["task_id"],
                "description": row["description"],
                "assigned_agent": row["assigned_agent"],
                "status": row["status"],
                "acceptance_criteria": json.loads(row["acceptance_criteria_json"]) if row["acceptance_criteria_json"] else [],
                "complexity": row["complexity"],
                "dependencies": json.loads(row["dependencies_json"]) if row["dependencies_json"] else [],
                "attempts": row["attempts"],
                "created_at": row["created_at"],
            }
        except Exception as exc:
            logger.error("update_task_status failed: %s", exc)
            return _err(f"update_task_status failed: {exc}")

    # ------------------------------------------------------------------
    # Session status overview
    # ------------------------------------------------------------------

    async def get_session_status(self, session_id: str) -> dict[str, Any] | None:
        """Return full session status including consultations and tasks.
        Returns composite dict, None if session not found, or error dict.
        """
        try:
            conn = await self._get_conn()
            if isinstance(conn, dict):
                return conn

            session = await self.get_session(session_id)
            if session is None or isinstance(session, dict) and "error" in session:
                return session

            # Get consultations
            cursor = await conn.execute(
                "SELECT * FROM agent_consultations WHERE session_id = ?",
                (session_id,),
            )
            consultation_rows = await cursor.fetchall()
            consultations: list[dict[str, Any]] = []
            for row in consultation_rows:
                consultations.append({
                    "id": row["id"],
                    "agent": row["agent"],
                    "role": row["role"],
                    "status": row["status"],
                    "enrichments": json.loads(row["enrichments_json"]) if row["enrichments_json"] else [],
                    "contract": json.loads(row["contract_json"]) if row["contract_json"] else {},
                    "refusals": json.loads(row["refusals_json"]) if row["refusals_json"] else [],
                    "plan_suggestion": row["plan_suggestion"] or "",
                    "raw_response": row["raw_response"] or "",
                    "consulted_at": row["consulted_at"],
                    "signed_at": row["signed_at"],
                })

            # Get tasks
            cursor = await conn.execute(
                "SELECT * FROM tasks WHERE session_id = ?",
                (session_id,),
            )
            task_rows = await cursor.fetchall()
            tasks: list[dict[str, Any]] = []
            for row in task_rows:
                tasks.append({
                    "id": row["id"],
                    "task_id": row["task_id"],
                    "description": row["description"],
                    "assigned_agent": row["assigned_agent"],
                    "status": row["status"],
                    "acceptance_criteria": json.loads(row["acceptance_criteria_json"]) if row["acceptance_criteria_json"] else [],
                    "complexity": row["complexity"],
                    "dependencies": json.loads(row["dependencies_json"]) if row["dependencies_json"] else [],
                    "attempts": row["attempts"],
                    "created_at": row["created_at"],
                })

            return {
                "session": session,
                "consultations": consultations,
                "tasks": tasks,
            }
        except Exception as exc:
            logger.error("get_session_status failed: %s", exc)
            return _err(f"get_session_status failed: {exc}")

    async def complete_session(self, session_id: str) -> dict[str, Any] | None:
        """Mark a session as completed. Returns result dict, None if not found, or error dict."""
        try:
            result = await self.update_session(session_id, status="completed")
            if result is None:
                return None
            if isinstance(result, dict) and "error" in result:
                return result
            return {"session_id": session_id, "status": "completed"}
        except Exception as exc:
            logger.error("complete_session failed: %s", exc)
            return _err(f"complete_session failed: {exc}")


# ------------------------------------------------------------------
# Module-level DB instance management
# ------------------------------------------------------------------

_db_instances: dict[str, ConsultingDB] = {}


async def get_consulting_db(project_root: str) -> ConsultingDB:
    """Get or create the ConsultingDB for a given project root.

    The database is stored at <project_root>/.aether/.consulting/consulting.db.
    """
    if project_root not in _db_instances:
        db_path = Path(project_root) / ".aether" / ".consulting" / "consulting.db"
        db = ConsultingDB(db_path)
        await db._ensure_db()
        _db_instances[project_root] = db
    return _db_instances[project_root]