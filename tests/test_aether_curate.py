"""Regression tests for fail-closed aether_curate execution."""

import asyncio
from datetime import datetime
from pathlib import Path

import pytest

from olympus_v3 import server
from olympus_v3.acp_manager import ACPManager, SessionInfo


class _Cursor:
    async def fetchall(self):
        return []


class _AetherDB:
    def __init__(self, db_path):
        self.db_path = db_path

    async def connect(self):
        pass

    async def close(self):
        pass

    async def get_hot_state(self):
        return {"project_name": "Test", "current_phase": "CODE", "current_task": "Curate", "total_sessions": 3}

    async def get_recent_sessions(self, limit):
        return []

    async def get_recent_files(self, limit):
        return []

    async def _execute(self, query):
        return _Cursor()


class _Manager:
    def __init__(self, progress, write_context=None):
        self.progress = progress
        self.write_context = write_context
        self.closed = []
        self.sent = []

    async def spawn_agent(self, *, agent_name, project_root):
        assert agent_name == "ariadna"
        return "curate-session"

    async def send_message(self, session_id, prompt):
        self.sent.append((session_id, prompt))
        if self.write_context is not None:
            self.write_context()

    async def poll(self, session_id):
        return self.progress

    async def close(self, session_id, *, terminal_status=None):
        self.closed.append((session_id, terminal_status))


@pytest.fixture
def curate_environment(monkeypatch, tmp_path):
    aether_dir = tmp_path / ".aether"
    aether_dir.mkdir()
    monkeypatch.setattr(server, "resolve_aether_dir", lambda _: aether_dir)
    monkeypatch.setattr(server, "resolve_aether_db", lambda _: tmp_path / "aether.db")
    monkeypatch.setattr(server, "AetherDB", _AetherDB)
    monkeypatch.setattr(server, "CURATE_POLL_INTERVAL", 0)
    monkeypatch.setattr(server, "CURATE_TIMEOUT_SECONDS", 1)
    return aether_dir


def _valid_context():
    return "\n".join(
        [
            "# Test — Phase: CODE | Task: Curate",
            "",
            "## Estado actual",
            "Ready.",
            "",
            "## Archivos recientes",
            "- `src/example.py` — relevant file",
            "",
            "## Decisiones activas",
            "- **Safety**: fail closed.",
            "",
            "## Proximo paso",
            "1. Verify the context.",
            "",
            f"— Curated: {datetime.now().strftime('%Y-%m-%d')} | focus: recent | sessions: 3",
        ]
    )


def _run_curate(monkeypatch, manager):
    monkeypatch.setattr(server, "_manager", manager)
    return asyncio.run(server._handle_aether_curate({"project_root": "/project", "focus": "recent"}))


def test_aether_curate_returns_success_only_after_verified_fresh_write(curate_environment, monkeypatch):
    context_path = curate_environment / "CONTEXT.md"
    manager = _Manager(
        {"status": "completed", "last_turn": "CONTEXT.md written and verified."},
        write_context=lambda: context_path.write_text(_valid_context()),
    )

    response = _run_curate(monkeypatch, manager)

    assert response[0].text == f"Curated context written to {context_path}"
    assert manager.closed == [("curate-session", None)]


@pytest.mark.parametrize(
    "last_turn",
    [
        "CLARIFICATION NEEDED: missing project direction",
        "NOT WRITTEN: write_file denied by ACP",
        "UNVERIFIED: file write could not be confirmed",
    ],
)
def test_aether_curate_rejects_agent_reported_unverified_write(curate_environment, monkeypatch, last_turn):
    manager = _Manager({"status": "completed", "last_turn": last_turn})

    response = _run_curate(monkeypatch, manager)

    assert response[0].text.startswith("Error: Ariadna")
    assert manager.closed == [("curate-session", "error")]


def test_aether_curate_rejects_terminal_agent_failure(curate_environment, monkeypatch):
    manager = _Manager({"status": "error", "last_turn": "ACP prompt failed"})

    response = _run_curate(monkeypatch, manager)

    assert response[0].text.startswith("Error: Ariadna session ended with status 'error'")
    assert manager.closed == [("curate-session", "error")]


def test_aether_curate_rejects_timeout_and_closes_session(curate_environment, monkeypatch):
    monkeypatch.setattr(server, "CURATE_TIMEOUT_SECONDS", 0)
    manager = _Manager({"status": "active", "last_turn": "still working"})

    response = _run_curate(monkeypatch, manager)

    assert response[0].text.startswith("Error: Ariadna curation timed out")
    assert manager.closed == [("curate-session", "error")]


def test_aether_curate_rejects_stale_unchanged_context(curate_environment, monkeypatch):
    context_path = curate_environment / "CONTEXT.md"
    context_path.write_text(_valid_context())
    manager = _Manager({"status": "completed", "last_turn": "CONTEXT.md written and verified."})

    response = _run_curate(monkeypatch, manager)

    assert response[0].text.startswith("Error: CONTEXT.md was not freshly written")
    assert manager.closed == [("curate-session", "error")]


def test_aether_curate_rejects_explicit_cancelled_status(curate_environment, monkeypatch):
    manager = _Manager({"status": "cancelled", "reason": "operator cancelled"})

    response = _run_curate(monkeypatch, manager)

    assert response[0].text.startswith("Error: Ariadna session ended with status 'cancelled'")
    assert manager.closed == [("curate-session", "cancelled")]


@pytest.mark.parametrize(
    "progress",
    [
        {"status": "active", "clarification_needed": True, "response": "Please clarify scope"},
        {"status": "clarification_needed", "last_turn": "Please clarify scope"},
    ],
)
def test_aether_curate_rejects_clarification_immediately(curate_environment, monkeypatch, progress):
    manager = _Manager(progress)

    response = _run_curate(monkeypatch, manager)

    assert response[0].text.startswith("Error: Ariadna requires clarification")
    assert manager.closed == [("curate-session", "error")]


def test_aether_curate_accepts_same_content_rewritten_in_this_invocation(curate_environment, monkeypatch):
    context_path = curate_environment / "CONTEXT.md"
    context_path.write_text(_valid_context())
    manager = _Manager(
        {"status": "completed", "last_turn": "CONTEXT.md written and verified."},
        write_context=lambda: context_path.write_text(_valid_context()),
    )

    response = _run_curate(monkeypatch, manager)

    assert response[0].text == f"Curated context written to {context_path}"
    assert manager.closed == [("curate-session", None)]


def test_aether_curate_rejects_footer_with_trailing_content(curate_environment, monkeypatch):
    context_path = curate_environment / "CONTEXT.md"
    manager = _Manager(
        {"status": "completed", "last_turn": "CONTEXT.md written and verified."},
        write_context=lambda: context_path.write_text(_valid_context() + "\nUnexpected trailing content."),
    )

    response = _run_curate(monkeypatch, manager)

    assert response[0].text == "Error: CONTEXT.md is missing the expected curated footer."
    assert manager.closed == [("curate-session", "error")]


@pytest.mark.parametrize("field", ["response", "result", "error", "reason"])
def test_aether_curate_rejects_negative_markers_from_all_outcome_fields(curate_environment, monkeypatch, field):
    context_path = curate_environment / "CONTEXT.md"
    progress = {"status": "completed", field: "UNVERIFIED: file write could not be confirmed"}
    manager = _Manager(progress, write_context=lambda: context_path.write_text(_valid_context()))

    response = _run_curate(monkeypatch, manager)

    assert response[0].text.startswith("Error: Ariadna did not verify CONTEXT.md")
    assert manager.closed == [("curate-session", "error")]


class _StatusDB:
    def __init__(self):
        self.status_updates = []

    async def update_session_status(self, session_id, status):
        self.status_updates.append((session_id, status))


class _PersistingCurateManager(ACPManager):
    def __init__(self, tmp_path, *, poll_error=False):
        self.status_db = _StatusDB()
        super().__init__(profiles_dir=tmp_path, db=self.status_db)
        self.poll_error = poll_error

    async def spawn_agent(self, *, agent_name, project_root):
        self.sessions["curate-session"] = SessionInfo(
            session_id="curate-session", agent_name=agent_name, project_root=project_root
        )
        return "curate-session"

    async def send_message(self, session_id, prompt):
        pass

    async def poll(self, session_id):
        if self.poll_error:
            raise RuntimeError("database unavailable")
        return {"status": "active"}


@pytest.mark.parametrize("poll_error", [False, True], ids=["timeout", "poll-error"])
def test_aether_curate_failure_persists_error_with_real_close(
    curate_environment, monkeypatch, poll_error
):
    if not poll_error:
        monkeypatch.setattr(server, "CURATE_TIMEOUT_SECONDS", 0)
    manager = _PersistingCurateManager(Path(curate_environment).parent, poll_error=poll_error)

    response = _run_curate(monkeypatch, manager)

    assert response[0].text.startswith("Error")
    assert manager.status_db.status_updates == [("curate-session", "error")]
