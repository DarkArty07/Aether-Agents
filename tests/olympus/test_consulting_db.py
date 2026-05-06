"""Tests for the consulting_db module."""

import asyncio
import os
import tempfile
from pathlib import Path

import pytest
import pytest_asyncio

from olympus.consulting_db import ConsultingDB, get_consulting_db


@pytest_asyncio.fixture
async def db(tmp_path):
    """Provide an initialized ConsultingDB instance with a temp path."""
    db_path = tmp_path / ".eter" / ".consulting" / "consulting.db"
    db_instance = ConsultingDB(db_path)
    await db_instance._ensure_db()
    yield db_instance
    await db_instance.close()


@pytest.mark.asyncio
async def test_ensure_db_creates_dir_and_tables(db, tmp_path):
    """Database file and directory should be auto-created."""
    db_path = tmp_path / ".eter" / ".consulting" / "consulting.db"
    assert db_path.exists()


@pytest.mark.asyncio
async def test_create_session(db):
    """Creating a session should return a valid session dict."""
    session = await db.create_session(
        plan="Build a login page",
        agents=["daedalus", "athena"],
        context="E-commerce project",
        project_root="/tmp/test-project",
    )
    assert session["id"]
    assert session["plan"] == "Build a login page"
    assert session["agents"] == ["daedalus", "athena"]
    assert session["context"] == "E-commerce project"
    assert session["status"] == "planning"
    assert session["plan_version"] == 1


@pytest.mark.asyncio
async def test_get_session(db):
    """Getting a session by ID should return the same data."""
    session = await db.create_session(
        plan="Refactor auth module",
        agents=["athena"],
        project_root="/tmp/test",
    )
    fetched = await db.get_session(session["id"])
    assert fetched is not None
    assert fetched["plan"] == "Refactor auth module"
    assert fetched["agents"] == ["athena"]


@pytest.mark.asyncio
async def test_get_session_not_found(db):
    """Getting a non-existent session should return None."""
    result = await db.get_session("nonexistent-id")
    assert result is None


@pytest.mark.asyncio
async def test_update_session(db):
    """Updating session fields should persist."""
    session = await db.create_session(
        plan="Original plan",
        agents=["daedalus"],
        project_root="/tmp/test",
    )
    updated = await db.update_session(session["id"], status="consulting", plan_version=2)
    assert updated is not None
    assert updated["status"] == "consulting"
    assert updated["plan_version"] == 2


@pytest.mark.asyncio
async def test_update_session_agents(db):
    """Updating agents list should be JSON-serialized correctly."""
    session = await db.create_session(
        plan="Test agents update",
        agents=["daedalus"],
        project_root="/tmp/test",
    )
    updated = await db.update_session(session["id"], agents=["daedalus", "athena"])
    assert updated is not None
    assert updated["agents"] == ["daedalus", "athena"]


@pytest.mark.asyncio
async def test_save_consultation(db):
    """Saving a consultation should store enrichments, contract, refusals."""
    session = await db.create_session(
        plan="Test consultation",
        agents=["daedalus"],
        project_root="/tmp/test",
    )
    consultation = await db.save_consultation(
        session_id=session["id"],
        agent="daedalus",
        role="designer",
        enrichments=[{"area": "UX", "insight": "Missing error states", "severity": "high"}],
        contract={"tasks": [{"task_id": "t1", "description": "Design error states"}]},
        refusals=[{"task_id": "t2", "reason": "Backend only"}],
        plan_suggestion="Add error states to login flow",
        raw_response='{"enrichments": []}',
    )
    assert consultation["status"] == "consulted"
    assert consultation["agent"] == "daedalus"
    assert consultation["role"] == "designer"


@pytest.mark.asyncio
async def test_get_consultation(db):
    """Getting a consultation should return stored data."""
    session = await db.create_session(
        plan="Test get consultation",
        agents=["athena"],
        project_root="/tmp/test",
    )
    await db.save_consultation(
        session_id=session["id"],
        agent="athena",
        role="auditor",
        enrichments=[{"area": "Security", "insight": "Missing CSRF token", "severity": "critical"}],
        contract={"tasks": []},
        refusals=[],
        plan_suggestion="Add CSRF protection",
    )
    result = await db.get_consultation(session["id"], "athena")
    assert result is not None
    assert result["agent"] == "athena"
    assert result["role"] == "auditor"
    assert result["status"] == "consulted"
    assert len(result["enrichments"]) == 1
    assert result["enrichments"][0]["area"] == "Security"


@pytest.mark.asyncio
async def test_update_consultation_status_sign(db):
    """Updating consultation status to 'signed' should set signed_at."""
    session = await db.create_session(
        plan="Test signing",
        agents=["daedalus"],
        project_root="/tmp/test",
    )
    await db.save_consultation(
        session_id=session["id"],
        agent="daedalus",
        role="designer",
    )
    result = await db.update_consultation_status(
        session_id=session["id"],
        agent="daedalus",
        status="signed",
        contract={"tasks": [{"task_id": "t1", "description": "Design login"}]},
    )
    assert result is not None
    assert result["status"] == "signed"
    assert result["signed_at"] is not None


@pytest.mark.asyncio
async def test_add_agent(db):
    """Adding an agent to a session should update agents_json and create pending consultation."""
    session = await db.create_session(
        plan="Test add agent",
        agents=["daedalus"],
        project_root="/tmp/test",
    )
    result = await db.add_agent(session["id"], "athena", "auditor", "Need security review")
    assert result is not None
    assert result["agent"] == "athena"
    assert result["role"] == "auditor"
    assert result["status"] == "pending"

    # Verify session updated
    updated_session = await db.get_session(session["id"])
    assert "athena" in updated_session["agents"]


@pytest.mark.asyncio
async def test_add_agent_duplicate(db):
    """Adding an existing agent should return an error."""
    session = await db.create_session(
        plan="Test duplicate agent",
        agents=["daedalus"],
        project_root="/tmp/test",
    )
    result = await db.add_agent(session["id"], "daedalus", "designer", "Already here")
    assert "error" in result


@pytest.mark.asyncio
async def test_create_task(db):
    """Creating a task should store all fields."""
    session = await db.create_session(
        plan="Test task creation",
        agents=["daedalus"],
        project_root="/tmp/test",
    )
    task = await db.create_task(
        session_id=session["id"],
        task_id="task_1",
        description="Design login page",
        assigned_agent="daedalus",
        acceptance_criteria=["Login form renders", "Error states visible"],
        complexity="medium",
        dependencies=["task_0"],
    )
    assert task["task_id"] == "task_1"
    assert task["description"] == "Design login page"
    assert task["assigned_agent"] == "daedalus"
    assert task["status"] == "pending"
    assert task["acceptance_criteria"] == ["Login form renders", "Error states visible"]
    assert task["complexity"] == "medium"
    assert task["dependencies"] == ["task_0"]


@pytest.mark.asyncio
async def test_update_task_status(db):
    """Updating task status should persist the change."""
    session = await db.create_session(
        plan="Test task update",
        agents=["daedalus"],
        project_root="/tmp/test",
    )
    task = await db.create_task(
        session_id=session["id"],
        task_id="task_1",
        description="Test",
        assigned_agent="daedalus",
    )
    updated = await db.update_task_status("task_1", "implementing")
    assert updated is not None
    assert updated["status"] == "implementing"


@pytest.mark.asyncio
async def test_update_task_status_with_increment(db):
    """Updating task status with increment_attempts should bump the counter."""
    session = await db.create_session(
        plan="Test task attempts",
        agents=["daedalus"],
        project_root="/tmp/test",
    )
    await db.create_task(
        session_id=session["id"],
        task_id="task_1",
        description="Test",
        assigned_agent="daedalus",
    )
    await db.update_task_status("task_1", "failed", increment_attempts=True)
    updated = await db.update_task_status("task_1", "implementing", increment_attempts=True)
    assert updated["attempts"] == 2


@pytest.mark.asyncio
async def test_get_session_status(db):
    """Session status should include session, consultations, and tasks."""
    session = await db.create_session(
        plan="Test full status",
        agents=["daedalus", "athena"],
        project_root="/tmp/test",
    )
    await db.save_consultation(
        session_id=session["id"],
        agent="daedalus",
        role="designer",
        enrichments=[{"area": "UX", "insight": "Missing states", "severity": "high"}],
    )
    await db.create_task(
        session_id=session["id"],
        task_id="task_1",
        description="Design login",
        assigned_agent="daedalus",
    )

    status = await db.get_session_status(session["id"])
    assert status is not None
    assert status["session"]["id"] == session["id"]
    assert len(status["consultations"]) >= 1
    assert len(status["tasks"]) >= 1


@pytest.mark.asyncio
async def test_complete_session(db):
    """Completing a session should set status to 'completed'."""
    session = await db.create_session(
        plan="Test completion",
        agents=["daedalus"],
        project_root="/tmp/test",
    )
    result = await db.complete_session(session["id"])
    assert result is not None
    assert result["status"] == "completed"

    # Verify in DB
    fetched = await db.get_session(session["id"])
    assert fetched["status"] == "completed"


@pytest.mark.asyncio
async def test_get_consulting_db_caches(tmp_path):
    """get_consulting_db should return cached instance for same project root."""
    # Clear the module cache
    import olympus.consulting_db as db_mod
    db_mod._db_instances.clear()

    pr = str(tmp_path / "project")
    db1 = await get_consulting_db(pr)
    db2 = await get_consulting_db(pr)
    assert db1 is db2  # Same instance

    # Clean up
    await db1.close()
    db_mod._db_instances.clear()