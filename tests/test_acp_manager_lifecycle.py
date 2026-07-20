"""Regression tests for Olympus ACP process and connection lifecycle safety."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest

from olympus_v3 import acp_manager
from olympus_v3.acp_manager import ACPManager, AgentState, SessionInfo


class _TaskState:
    def __init__(self, *, done: bool = False, cancelled: bool = False):
        self._done = done
        self._cancelled = cancelled

    def done(self) -> bool:
        return self._done

    def cancelled(self) -> bool:
        return self._cancelled


class _Connection:
    def __init__(self, *, receive_done: bool = False, session_delay: float = 0):
        self._closed = False
        self._recv_task = _TaskState(done=receive_done)
        self.session_delay = session_delay
        self.new_session_calls = 0
        self.cancelled_sessions: list[str] = []
        self.closed_sessions: list[str] = []
        self.closed = False
        self.prompt_error: BaseException | None = None
        self.prompt_calls = 0
        self.prompt_started = asyncio.Event()
        self.prompt_release = asyncio.Event()

    async def initialize(self, **_kwargs):
        return SimpleNamespace(protocol_version=1)

    async def new_session(self, **_kwargs):
        self.new_session_calls += 1
        if self.session_delay:
            await asyncio.sleep(self.session_delay)
        return SimpleNamespace(session_id=f"acp-{self.new_session_calls}")

    async def prompt(self, **_kwargs):
        self.prompt_calls += 1
        self.prompt_started.set()
        if self.prompt_error is not None:
            self._recv_task = _TaskState(done=True)
            raise self.prompt_error
        await self.prompt_release.wait()
        return SimpleNamespace(stop_reason="end_turn")

    async def cancel(self, session_id: str):
        self.cancelled_sessions.append(session_id)

    async def close_session(self, session_id: str):
        self.closed_sessions.append(session_id)

    async def close(self):
        self._closed = True
        self.closed = True


class _Process:
    def __init__(self, pid: int = 1234, *, returncode=None):
        self.pid = pid
        self.returncode = returncode


class _DB:
    def __init__(self):
        self.inserted: list[tuple[str, str]] = []
        self.updated: list[tuple[str, str]] = []

    async def insert_session(self, *, session_id, agent, metadata):
        self.inserted.append((session_id, agent))

    async def update_session_status(self, session_id, status):
        self.updated.append((session_id, status))


class _FakeManager(ACPManager):
    def __init__(self, profiles_dir: Path, *, db=None, session_open_timeout: float = 1):
        super().__init__(
            profiles_dir=profiles_dir,
            db=db,
            session_open_timeout=session_open_timeout,
        )
        self.spawn_count = 0
        self.spawn_delay = 0.01
        self.connections: list[_Connection] = []
        self.next_connection: _Connection | None = None

    async def _spawn_process(self, agent, project_root=None):
        self.spawn_count += 1
        await asyncio.sleep(self.spawn_delay)
        connection = self.next_connection or _Connection()
        self.next_connection = None
        self.connections.append(connection)
        agent.connection = connection
        agent.process = _Process(pid=1200 + self.spawn_count)
        agent.pid = agent.process.pid
        agent.status = "idle"


def _profiles(tmp_path: Path) -> Path:
    profiles = tmp_path / "profiles"
    (profiles / "hefesto").mkdir(parents=True)
    return profiles


def test_concurrent_same_key_opens_spawn_one_process_and_track_two_sessions(tmp_path, monkeypatch):
    monkeypatch.setattr(acp_manager, "spawn_agent_process", object())

    async def scenario():
        manager = _FakeManager(_profiles(tmp_path))
        first, second = await asyncio.gather(
            manager.spawn_agent("hefesto", project_root="/project"),
            manager.spawn_agent("hefesto", project_root="/project"),
        )
        agent = manager.get_agent("hefesto", "/project")
        assert manager.spawn_count == 1
        assert agent is not None
        assert set(agent.acp_session_ids) == {first, second}
        assert len(manager.sessions) == 2

    asyncio.run(scenario())


def test_concurrent_different_projects_spawn_independent_processes(tmp_path, monkeypatch):
    monkeypatch.setattr(acp_manager, "spawn_agent_process", object())

    async def scenario():
        manager = _FakeManager(_profiles(tmp_path))
        await asyncio.gather(
            manager.spawn_agent("hefesto", project_root="/one"),
            manager.spawn_agent("hefesto", project_root="/two"),
        )
        assert manager.spawn_count == 2
        assert manager.get_agent("hefesto", "/one") is not manager.get_agent("hefesto", "/two")

    asyncio.run(scenario())


def test_dead_receive_loop_is_never_reused(tmp_path, monkeypatch):
    monkeypatch.setattr(acp_manager, "spawn_agent_process", object())

    async def scenario():
        manager = _FakeManager(_profiles(tmp_path))
        stale_connection = _Connection(receive_done=True)
        stale = AgentState(
            name="hefesto",
            profile_path=manager.profiles_dir / "hefesto",
            connection=stale_connection,
            process=_Process(),
            status="idle",
        )
        manager.agents[("hefesto", "/project")] = stale

        await manager.spawn_agent("hefesto", project_root="/project")

        replacement = manager.get_agent("hefesto", "/project")
        assert manager.spawn_count == 1
        assert replacement is not stale
        assert stale.status == "dead"
        assert stale_connection.closed is True

    asyncio.run(scenario())


def test_new_session_timeout_invalidates_partial_agent(tmp_path, monkeypatch):
    monkeypatch.setattr(acp_manager, "spawn_agent_process", object())

    async def scenario():
        manager = _FakeManager(_profiles(tmp_path), session_open_timeout=0.01)
        manager.spawn_delay = 0
        manager.next_connection = _Connection(session_delay=3600)

        with pytest.raises(TimeoutError, match="new_session timed out"):
            await manager.spawn_agent("hefesto", project_root="/project")

        assert manager.get_agent("hefesto", "/project") is None
        assert manager.sessions == {}
        assert manager.connections[0].closed is True

    asyncio.run(scenario())


def test_spawn_process_configures_bounded_acp_stream_limit(tmp_path, monkeypatch):
    captured: dict = {}
    connection = _Connection()
    process = _Process()

    @asynccontextmanager
    async def fake_spawn(_client, _command, *_args, **kwargs):
        captured.update(kwargs)
        yield connection, process

    monkeypatch.setattr(acp_manager, "spawn_agent_process", fake_spawn)

    async def scenario():
        manager = ACPManager(profiles_dir=_profiles(tmp_path), acp_stream_limit=2_000_000)
        agent = AgentState(name="hefesto", profile_path=manager.profiles_dir / "hefesto")
        await manager._spawn_process(agent, project_root=str(tmp_path))
        assert captured["transport_kwargs"] == {"limit": 2_000_000}
        await agent.process_context.__aexit__(None, None, None)

    asyncio.run(scenario())


def test_concurrent_same_session_send_reserves_exactly_one_prompt(tmp_path):
    async def scenario():
        manager = ACPManager(profiles_dir=_profiles(tmp_path), db=_DB())
        connection = _Connection()
        agent = AgentState(
            "hefesto",
            manager.profiles_dir / "hefesto",
            connection=connection,
            process=_Process(1234),
            pid=1234,
            status="busy",
        )
        session = SessionInfo("logical", "hefesto", "raw", str(tmp_path))
        key = manager._agent_key("hefesto", str(tmp_path))
        manager.agents[key] = agent
        manager.sessions["logical"] = session
        agent.acp_session_ids["logical"] = "raw"

        results = await asyncio.gather(
            manager.send_message("logical", "first"),
            manager.send_message("logical", "second"),
            return_exceptions=True,
        )
        assert len([result for result in results if isinstance(result, RuntimeError)]) == 1
        assert len([result for result in results if isinstance(result, dict)]) == 1
        assert len(agent.prompt_tasks) == 1
        await connection.prompt_started.wait()
        assert connection.prompt_calls == 1
        await manager.close("logical")
        assert connection.prompt_calls == 1

    asyncio.run(scenario())


def test_close_active_prompt_cancels_work_and_never_reports_success(tmp_path):
    async def scenario():
        db = _DB()
        manager = ACPManager(profiles_dir=_profiles(tmp_path), db=db)
        connection = _Connection()
        agent = AgentState(
            name="hefesto",
            profile_path=manager.profiles_dir / "hefesto",
            connection=connection,
            process=_Process(),
            status="busy",
        )
        session = SessionInfo(
            session_id="logical",
            agent_name="hefesto",
            acp_session_id="raw",
            project_root="/project",
        )
        manager.agents[("hefesto", "/project")] = agent
        manager.sessions["logical"] = session
        agent.acp_session_ids["logical"] = "raw"
        task = asyncio.create_task(connection.prompt())
        agent.prompt_tasks["logical"] = task
        await connection.prompt_started.wait()

        result = await manager.close("logical")

        assert result["status"] == "cancelled"
        assert connection.cancelled_sessions == ["raw"]
        assert task.cancelled()
        assert ("logical", "cancelled") in db.updated
        assert agent.status == "idle"

    asyncio.run(scenario())


def test_prompts_share_one_process_without_overlapping_session_mapping(tmp_path):
    async def scenario():
        db = _DB()
        manager = ACPManager(profiles_dir=_profiles(tmp_path), db=db)
        connection = _Connection()
        agent = AgentState(
            name="hefesto",
            profile_path=manager.profiles_dir / "hefesto",
            connection=connection,
            process=_Process(),
            pid=1234,
            status="busy",
        )
        manager.agents[("hefesto", "/project")] = agent
        for sid in ("one", "two"):
            manager.sessions[sid] = SessionInfo(sid, "hefesto", f"raw-{sid}", "/project")
            agent.acp_session_ids[sid] = f"raw-{sid}"

        await manager.send_message("one", "first")
        await manager.send_message("two", "second")
        await connection.prompt_started.wait()
        await asyncio.sleep(0)

        assert connection.prompt_calls == 1
        tasks = list(agent.prompt_tasks.values())
        connection.prompt_release.set()
        await asyncio.gather(*tasks)
        assert connection.prompt_calls == 2
        assert manager.sessions["one"].status == "completed"
        assert manager.sessions["two"].status == "completed"

    asyncio.run(scenario())


def test_same_session_rejects_overlapping_prompts_and_close_cancels_original(tmp_path):
    async def scenario():
        manager = ACPManager(profiles_dir=_profiles(tmp_path), db=_DB())
        connection = _Connection()
        agent = AgentState(
            name="hefesto",
            profile_path=manager.profiles_dir / "hefesto",
            connection=connection,
            process=_Process(),
            pid=1234,
            status="busy",
        )
        session = SessionInfo("logical", "hefesto", "raw", "/project")
        manager.agents[("hefesto", "/project")] = agent
        manager.sessions["logical"] = session
        agent.acp_session_ids["logical"] = "raw"

        await manager.send_message("logical", "first")
        await connection.prompt_started.wait()
        with pytest.raises(RuntimeError, match="already has an active prompt"):
            await manager.send_message("logical", "second")

        result = await manager.close("logical")
        assert result["status"] == "cancelled"
        assert connection.prompt_calls == 1
        assert connection.cancelled_sessions == ["raw"]

    asyncio.run(scenario())


def test_mapping_failure_cleans_partial_files_and_never_starts_prompt(tmp_path, monkeypatch):
    async def scenario():
        db = _DB()
        manager = ACPManager(profiles_dir=_profiles(tmp_path), db=db)
        connection = _Connection()
        agent = AgentState(
            name="hefesto",
            profile_path=manager.profiles_dir / "hefesto",
            connection=connection,
            process=_Process(),
            pid=1234,
            status="busy",
        )
        session = SessionInfo("logical", "hefesto", "raw", "/project")
        manager.agents[("hefesto", "/project")] = agent
        manager.sessions["logical"] = session
        agent.acp_session_ids["logical"] = "raw"
        writes = 0

        def fail_second_write(path, content):
            nonlocal writes
            writes += 1
            if writes == 2:
                raise OSError("disk full")
            path.write_text(content)

        monkeypatch.setattr(manager, "_atomic_write", fail_second_write)
        await manager.send_message("logical", "must not run")
        task = agent.prompt_tasks["logical"]
        await task

        assert connection.prompt_calls == 0
        assert manager.sessions["logical"].status == "error"
        assert ("logical", "error") in db.updated
        for suffix in (".olympus_session.1234", ".olympus_db_path.1234", ".aether_home.1234"):
            assert not (agent.profile_path / suffix).exists()

    asyncio.run(scenario())


def test_delegate_rejects_persistent_completed_status_without_response_evidence(tmp_path, monkeypatch):
    async def scenario():
        manager = ACPManager(profiles_dir=_profiles(tmp_path))
        calls = 0

        async def fake_spawn(**_kwargs):
            manager.sessions["logical"] = SessionInfo("logical", "hefesto")
            return "logical"

        async def fake_send(_session_id, _message):
            return {"status": "sent"}

        async def fake_poll(_session_id):
            nonlocal calls
            calls += 1
            return {"status": "completed", "last_turn": None}

        monkeypatch.setattr(manager, "spawn_agent", fake_spawn)
        monkeypatch.setattr(manager, "send_message", fake_send)
        monkeypatch.setattr(manager, "poll", fake_poll)

        result = await manager.delegate("hefesto", "test", poll_interval=0, timeout=1)

        assert calls == 2
        assert result["status"] == "error"
        assert result["reason"] == "completed_without_response_evidence"
        assert manager.sessions["logical"].status == "error"

    asyncio.run(scenario())


def test_delegate_allows_one_poll_for_completed_turn_to_persist(tmp_path, monkeypatch):
    async def scenario():
        manager = ACPManager(profiles_dir=_profiles(tmp_path))
        calls = 0

        async def fake_spawn(**_kwargs):
            manager.sessions["logical"] = SessionInfo("logical", "hefesto")
            return "logical"

        async def fake_send(_session_id, _message):
            return {"status": "sent"}

        async def fake_poll(_session_id):
            nonlocal calls
            calls += 1
            return {
                "status": "completed",
                "last_turn": None if calls == 1 else "verified response",
            }

        monkeypatch.setattr(manager, "spawn_agent", fake_spawn)
        monkeypatch.setattr(manager, "send_message", fake_send)
        monkeypatch.setattr(manager, "poll", fake_poll)

        result = await manager.delegate("hefesto", "test", poll_interval=0, timeout=1)

        assert calls == 2
        assert result["status"] == "completed"
        assert result["last_turn"] == "verified response"

    asyncio.run(scenario())


def test_prompt_transport_failure_marks_agent_dead_and_all_sessions_error(tmp_path):
    async def scenario():
        db = _DB()
        manager = ACPManager(profiles_dir=_profiles(tmp_path), db=db)
        connection = _Connection()
        connection.prompt_error = ConnectionError("reader died")
        agent = AgentState(
            name="hefesto",
            profile_path=manager.profiles_dir / "hefesto",
            connection=connection,
            process=_Process(),
            status="busy",
        )
        for sid in ("one", "two"):
            manager.sessions[sid] = SessionInfo(sid, "hefesto", f"raw-{sid}", "/project")
            agent.acp_session_ids[sid] = f"raw-{sid}"
        manager.agents[("hefesto", "/project")] = agent

        await manager.send_message("one", "test")
        for _ in range(20):
            if agent.status == "dead":
                break
            await asyncio.sleep(0)

        assert agent.status == "dead"
        assert manager.get_agent("hefesto", "/project") is None
        assert manager.sessions["one"].status == "error"
        assert manager.sessions["two"].status == "error"
        assert ("one", "error") in db.updated
        assert ("two", "error") in db.updated


def test_shutdown_waits_for_spawn_and_cannot_orphan_published_session(tmp_path, monkeypatch):
    monkeypatch.setattr(acp_manager, "spawn_agent_process", object())

    class BlockingManager(_FakeManager):
        def __init__(self, profiles_dir):
            super().__init__(profiles_dir)
            self.started = asyncio.Event()
            self.release = asyncio.Event()

        async def _spawn_process(self, agent, project_root=None):
            self.started.set()
            await self.release.wait()
            await super()._spawn_process(agent, project_root)

    async def scenario():
        manager = BlockingManager(_profiles(tmp_path))
        spawn_task = asyncio.create_task(manager.spawn_agent("hefesto", project_root=str(tmp_path)))
        await manager.started.wait()
        shutdown_task = asyncio.create_task(
            manager.shutdown_agent("hefesto", project_root=str(tmp_path))
        )
        manager.release.set()
        session_id = await spawn_task
        result = await shutdown_task
        assert result["status"] == "shutdown"
        assert session_id not in manager.sessions
        assert manager.agents == {}

    asyncio.run(scenario())


def test_duplicate_supplied_session_id_rejected_before_second_acp_session(tmp_path, monkeypatch):
    monkeypatch.setattr(acp_manager, "spawn_agent_process", object())

    async def scenario():
        manager = _FakeManager(_profiles(tmp_path))
        await manager.spawn_agent("hefesto", session_id="fixed", project_root=str(tmp_path))
        with pytest.raises(ValueError, match="Session already exists"):
            await manager.spawn_agent("hefesto", session_id="fixed", project_root=str(tmp_path))
        agent = manager.get_agent("hefesto", str(tmp_path))
        assert agent is not None
        assert agent.connection.new_session_calls == 1
        assert list(agent.acp_session_ids) == ["fixed"]

    asyncio.run(scenario())


def test_duplicate_session_id_is_reserved_across_project_locks(tmp_path, monkeypatch):
    monkeypatch.setattr(acp_manager, "spawn_agent_process", object())

    async def scenario():
        manager = _FakeManager(_profiles(tmp_path))
        results = await asyncio.gather(
            manager.spawn_agent("hefesto", session_id="fixed", project_root="/one"),
            manager.spawn_agent("hefesto", session_id="fixed", project_root="/two"),
            return_exceptions=True,
        )
        assert results.count("fixed") == 1
        errors = [result for result in results if isinstance(result, ValueError)]
        assert len(errors) == 1
        assert str(errors[0]) == "Session already exists: fixed"
        assert sum(connection.new_session_calls for connection in manager.connections) == 1
        assert list(manager.sessions) == ["fixed"]
        assert manager._reserved_session_ids == set()

    asyncio.run(scenario())


def test_equivalent_project_roots_and_default_root_share_one_agent(tmp_path, monkeypatch):
    monkeypatch.setattr(acp_manager, "spawn_agent_process", object())
    link = tmp_path / "link"
    link.symlink_to(tmp_path, target_is_directory=True)

    async def scenario():
        manager = _FakeManager(_profiles(tmp_path))
        first = await manager.spawn_agent("hefesto", project_root=str(tmp_path))
        second = await manager.spawn_agent("hefesto", project_root=str(link))
        assert first != second
        assert len(manager.agents) == 1
        assert manager.get_agent("hefesto", str(link)) is manager.get_agent("hefesto", str(tmp_path))

    asyncio.run(scenario())


def test_db_registration_failure_rolls_back_acp_and_unused_agent(tmp_path, monkeypatch):
    class FailingDB(_DB):
        async def insert_session(self, **_kwargs):
            raise RuntimeError("db unavailable")

    monkeypatch.setattr(acp_manager, "spawn_agent_process", object())

    async def scenario():
        manager = _FakeManager(_profiles(tmp_path), db=FailingDB())
        with pytest.raises(RuntimeError, match="db unavailable"):
            await manager.spawn_agent("hefesto", project_root=str(tmp_path))
        assert manager.sessions == {}
        assert manager.agents == {}
        assert manager.connections[0].closed is True

    asyncio.run(scenario())


def test_cancellation_during_registration_rollback_waits_for_cleanup(tmp_path, monkeypatch):
    class FailingDB(_DB):
        async def insert_session(self, **_kwargs):
            raise RuntimeError("db unavailable")

    class BlockingCloseConnection(_Connection):
        def __init__(self):
            super().__init__()
            self.close_started = asyncio.Event()
            self.close_release = asyncio.Event()

        async def close_session(self, session_id: str):
            self.close_started.set()
            await self.close_release.wait()
            await super().close_session(session_id)

    monkeypatch.setattr(acp_manager, "spawn_agent_process", object())

    async def scenario():
        manager = _FakeManager(_profiles(tmp_path), db=FailingDB())
        connection = BlockingCloseConnection()
        manager.next_connection = connection
        task = asyncio.create_task(manager.spawn_agent("hefesto", project_root=str(tmp_path)))
        await connection.close_started.wait()

        task.cancel()
        await asyncio.sleep(0)
        try:
            assert not task.done(), "caller cancellation must wait for rollback cleanup"
        finally:
            connection.close_release.set()

        with pytest.raises(asyncio.CancelledError):
            await task
        assert connection.closed_sessions == ["acp-1"]
        assert connection.closed is True
        assert manager.sessions == {}
        assert manager.agents == {}
        assert manager._reserved_session_ids == set()

    asyncio.run(scenario())


def test_registration_failure_on_reused_agent_preserves_existing_session(tmp_path, monkeypatch):
    class FailSecondInsertDB(_DB):
        async def insert_session(self, *, session_id, agent, metadata):
            if self.inserted:
                raise RuntimeError("db unavailable")
            await super().insert_session(session_id=session_id, agent=agent, metadata=metadata)

    monkeypatch.setattr(acp_manager, "spawn_agent_process", object())

    async def scenario():
        manager = _FakeManager(_profiles(tmp_path), db=FailSecondInsertDB())
        first = await manager.spawn_agent("hefesto", project_root=str(tmp_path))
        agent = manager.get_agent("hefesto", str(tmp_path))
        assert agent is not None

        with pytest.raises(RuntimeError, match="db unavailable"):
            await manager.spawn_agent("hefesto", project_root=str(tmp_path))

        assert manager.get_agent("hefesto", str(tmp_path)) is agent
        assert list(manager.sessions) == [first]
        assert list(agent.acp_session_ids) == [first]
        assert agent.connection.closed_sessions == ["acp-2"]
        assert agent.connection.closed is False

    asyncio.run(scenario())


def test_close_db_failure_still_releases_logical_and_pid_ownership(tmp_path):
    class FailingUpdateDB(_DB):
        async def update_session_status(self, session_id, status):
            raise RuntimeError("db update unavailable")

    async def scenario():
        manager = ACPManager(profiles_dir=_profiles(tmp_path), db=FailingUpdateDB())
        profile = manager.profiles_dir / "hefesto"
        connection = _Connection()
        agent = AgentState(
            "hefesto",
            profile,
            connection=connection,
            process=_Process(1234),
            pid=1234,
            status="busy",
        )
        session = SessionInfo("logical", "hefesto", "raw", str(tmp_path))
        key = manager._agent_key("hefesto", str(tmp_path))
        manager.agents[key] = agent
        manager.sessions["logical"] = session
        agent.acp_session_ids["logical"] = "raw"
        manager._write_session_mapping(agent, session, "logical")

        with pytest.raises(RuntimeError, match="db update unavailable"):
            await manager.close("logical")

        assert connection.closed_sessions == ["raw"]
        assert "logical" not in manager.sessions
        assert "logical" not in agent.acp_session_ids
        assert agent.status == "idle"
        assert not list(profile.glob(".*.1234"))
        with pytest.raises(ValueError, match="Unknown session"):
            await manager.close("logical")

    asyncio.run(scenario())
















def test_close_removes_pid_mapping_before_delayed_prompt_can_publish(tmp_path):
    async def scenario():
        manager = ACPManager(profiles_dir=_profiles(tmp_path), db=_DB())
        profile = manager.profiles_dir / "hefesto"
        connection = _Connection()
        agent = AgentState("hefesto", profile, connection=connection, process=_Process(1234), pid=1234, status="busy")
        session = SessionInfo("logical", "hefesto", "raw", str(tmp_path))
        key = manager._agent_key("hefesto", str(tmp_path))
        manager.agents[key] = agent
        manager.sessions["logical"] = session
        agent.acp_session_ids["logical"] = "raw"
        await manager.send_message("logical", "prompt")
        await manager.close("logical")
        assert not list(profile.glob(".*.1234"))
        assert connection.prompt_calls == 0

    asyncio.run(scenario())


def test_closing_other_session_preserves_active_pid_mapping(tmp_path):
    async def scenario():
        manager = ACPManager(profiles_dir=_profiles(tmp_path), db=_DB())
        profile = manager.profiles_dir / "hefesto"
        connection = _Connection()
        agent = AgentState(
            "hefesto",
            profile,
            connection=connection,
            process=_Process(1234),
            pid=1234,
            status="busy",
        )
        key = manager._agent_key("hefesto", str(tmp_path))
        manager.agents[key] = agent
        for sid in ("active", "other"):
            session = SessionInfo(sid, "hefesto", f"raw-{sid}", str(tmp_path))
            manager.sessions[sid] = session
            agent.acp_session_ids[sid] = f"raw-{sid}"
        manager._write_session_mapping(agent, manager.sessions["active"], "active")

        await manager.close("other")

        mapping = profile / ".olympus_session.1234"
        assert mapping.read_text() == "active"
        assert (profile / ".olympus_db_path.1234").exists()
        assert (profile / ".aether_home.1234").exists()
        await manager.close("active")
        assert not mapping.exists()

    asyncio.run(scenario())


@pytest.mark.parametrize("field", ["last_turn", "last_reasoning", "recent_tool_calls"])
def test_completion_evidence_accepts_each_valid_field(field):
    progress = {"last_turn": None, "last_reasoning": None, "recent_tool_calls": []}
    progress[field] = "answer" if field != "recent_tool_calls" else [{"tool_name": "write_file"}]
    assert ACPManager._has_completion_evidence(progress)


def test_disposal_releases_handles_and_preserves_cancellation(tmp_path):
    class Context:
        async def __aexit__(self, *_args):
            await asyncio.sleep(0)

    async def scenario():
        manager = ACPManager(profiles_dir=_profiles(tmp_path))
        agent = AgentState(
            "hefesto",
            manager.profiles_dir / "hefesto",
            connection=_Connection(),
            process_context=Context(),
            process=_Process(1234),
            pid=1234,
            status="idle",
        )
        task = asyncio.create_task(manager._dispose_agent_transport(agent))
        await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert agent.connection is None
        assert agent.process_context is None
        assert agent.process is None
        assert agent.pid is None

    asyncio.run(scenario())
