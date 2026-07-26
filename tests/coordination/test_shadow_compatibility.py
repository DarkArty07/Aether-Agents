"""Compatibility matrix for Olympus MCP when coordination is absent or disabled."""

from __future__ import annotations

import asyncio
import builtins
import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from olympus_v3 import config_loader, server
from olympus_v3.config_loader import CoordinationConfig, OlympusV3Config, load_config

TOOLS = {"talk_to", "discover", "aether_status", "aether_update", "aether_curate", "harmonia"}
ACTIONS = ("open", "message", "poll", "close", "cancel", "delegate", "steer")


@dataclass
class FakeManager:
    calls: list[tuple]
    next_id: int = 0

    def __init__(self):
        self.calls = []
        self.next_id = 0
        self.roots: dict[str, str] = {}

    async def spawn_agent(self, agent_name, session_id=None, project_root=None):
        self.next_id += 1
        sid = session_id or f"{agent_name}-{self.next_id}"
        self.roots[sid] = project_root
        self.calls.append(("open", agent_name, sid, project_root))
        return sid

    async def send_message(self, session_id, prompt):
        self.calls.append(("message", session_id, prompt))
        return {"status": "sent", "session_id": session_id}

    async def poll(self, session_id):
        self.calls.append(("poll", session_id))
        return {"status": "completed", "last_turn": "response"}

    async def close(self, session_id, *, terminal_status=None):
        self.calls.append(("close", session_id, terminal_status))
        return {"status": terminal_status or "closed", "session_id": session_id}

    async def cancel(self, session_id):
        self.calls.append(("cancel", session_id))
        return {"status": "cancelled", "session_id": session_id}

    def discover(self):
        self.calls.append(("discover",))
        return [{"name": "hefesto"}]


class FakeOlympusDB:
    def __init__(self):
        self.steering: list[tuple[str, str, int]] = []

    async def get_session_progress(self, session_id):
        return {"status": "active", "thoughts": 1, "messages": 1, "tool_calls": 0, "last_turn": "ok"}

    async def get_session(self, session_id):
        return {"session_id": session_id}

    async def insert_steering(self, session_id, directive, priority):
        self.steering.append((session_id, directive, priority))
        return 7


class FakeCursor:
    def __init__(self, value):
        self.value = value

    async def fetchone(self):
        return (self.value,)

    async def fetchall(self):
        return []


class FakeAetherDB:
    instances: list["FakeAetherDB"] = []

    def __init__(self, db_path):
        self.db_path = db_path
        self.hot = {"project_name": "demo", "total_sessions": 2, "blockers": "[]"}
        self.closed = False
        self.__class__.instances.append(self)

    async def connect(self):
        return None

    async def close(self):
        self.closed = True

    async def get_hot_state(self):
        return self.hot

    async def get_recent_sessions(self, limit=5):
        return []

    async def get_recent_files(self, limit=10):
        return []

    async def _execute(self, query):
        return FakeCursor(0)

    async def update_hot_state(self, **values):
        self.hot.update(values)

    async def insert_decision(self, **kwargs):
        return 1

    async def insert_issue(self, **kwargs):
        return 2

    async def resolve_issue(self, **kwargs):
        return None


@pytest.fixture
def isolated_server(monkeypatch):
    manager = FakeManager()
    monkeypatch.setattr(server, "_manager", manager)
    monkeypatch.setattr(server, "_db", FakeOlympusDB())
    monkeypatch.setattr(server, "AetherDB", FakeAetherDB)
    monkeypatch.setattr(server, "resolve_aether_db", lambda root: Path(root) / ".aether" / "aether.db")
    monkeypatch.setattr(server, "resolve_aether_dir", lambda root: Path(root) / ".aether")
    monkeypatch.setattr(server.asyncio, "sleep", _no_sleep)
    return manager


async def _no_sleep(_seconds):
    return None


def _text(result):
    return result[0].text


@pytest.mark.parametrize("config_text", [None, "coordination:\n  enabled: false\n  mode: legacy\n"])
def test_absent_and_explicit_false_preserve_public_tool_registration(tmp_path, config_text):
    path = tmp_path / "olympus_v3.yaml"
    if config_text is not None:
        path.write_text(config_text)
    config = load_config(path if config_text is not None else tmp_path / "missing.yaml")
    registered = asyncio.run(server.list_tools())

    assert config.coordination == CoordinationConfig()
    assert {tool.name for tool in registered} == TOOLS


@pytest.mark.parametrize("action", ACTIONS)
def test_every_talk_to_action_is_registered_and_dispatchable(isolated_server, action, tmp_path):
    manager = isolated_server
    session = asyncio.run(
        server.call_tool("talk_to", {"action": "open", "agent": "hefesto", "project_root": str(tmp_path)})
    )
    sid = json.loads(_text(session))["session_id"]
    args = {
        "action": action,
        "agent": "hefesto",
        "session_id": sid,
        "prompt": "continue",
        "directive": "focus on tests",
        "project_root": str(tmp_path),
        "poll_interval": 0,
        "timeout": 1,
    }
    result = asyncio.run(server.call_tool("talk_to", args))

    assert result and _text(result)
    calls = {call[0] for call in manager.calls}
    if action == "delegate":
        assert {"open", "message", "poll"} <= calls
    elif action == "steer":
        assert json.loads(_text(result))["status"] == "steered"
        assert server._db.steering == [(sid, "focus on tests", 0)]
    else:
        assert action in calls


def test_all_non_curation_public_handlers_work_when_disabled(isolated_server, tmp_path):
    discovered = json.loads(_text(asyncio.run(server.call_tool("discover", {}))))
    status = json.loads(
        _text(
            asyncio.run(
                server.call_tool(
                    "aether_status",
                    {"project_root": str(tmp_path), "detail": "summary"},
                )
            )
        )
    )
    updated = _text(
        asyncio.run(
            server.call_tool(
                "aether_update",
                {
                    "project_root": str(tmp_path),
                    "action": "set_task",
                    "task": "compatibility",
                },
            )
        )
    )

    assert discovered == {"agents": [{"name": "hefesto"}], "count": 1}
    assert status["hot_state"]["project_name"] == "demo"
    assert status["sessions_count"] == 0
    assert updated == "Task updated to: compatibility"
    assert all(db.closed for db in FakeAetherDB.instances)


def test_sessions_are_reusable_steerable_and_isolated_by_project_root(isolated_server, tmp_path):
    manager = isolated_server
    root_a, root_b = tmp_path / "a", tmp_path / "b"
    first = json.loads(
        _text(
            asyncio.run(
                server.call_tool("talk_to", {"action": "open", "agent": "hefesto", "project_root": str(root_a)})
            )
        )
    )
    second = json.loads(
        _text(
            asyncio.run(
                server.call_tool("talk_to", {"action": "open", "agent": "hefesto", "project_root": str(root_b)})
            )
        )
    )

    assert first["session_id"] != second["session_id"]
    asyncio.run(
        server.call_tool("talk_to", {"action": "message", "session_id": first["session_id"], "prompt": "follow up"})
    )
    asyncio.run(server.call_tool("talk_to", {"action": "poll", "session_id": first["session_id"]}))
    steered = asyncio.run(
        server.call_tool("talk_to", {"action": "steer", "session_id": first["session_id"], "directive": "clarify"})
    )

    assert json.loads(_text(steered))["status"] == "steered"
    assert manager.roots[first["session_id"]] == str(root_a)
    assert manager.roots[second["session_id"]] == str(root_b)


def test_curation_public_path_and_logical_teardown_are_available_when_disabled(isolated_server, tmp_path):
    manager = isolated_server
    root = tmp_path / "project"
    aether = root / ".aether"
    aether.mkdir(parents=True)
    original_spawn = manager.spawn_agent

    async def spawn_and_write(*args, **kwargs):
        sid = await original_spawn(*args, **kwargs)
        content = "# Demo — Phase: CODE | Task: test\n\n## Estado actual\nOK\n\n## Archivos recientes\n- test\n\n## Decisiones activas\n- none\n\n## Proximo paso\n1. verify\n\n— Curated: 2026-07-22 | focus: recent | sessions: 2\n"
        (aether / "CONTEXT.md").write_text(content)
        return sid

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(manager, "spawn_agent", spawn_and_write)
    monkeypatch.setattr(
        server,
        "datetime",
        type("D", (), {"now": staticmethod(lambda: type("T", (), {"strftime": lambda self, _: "2026-07-22"})())}),
    )
    try:
        result = asyncio.run(server.call_tool("aether_curate", {"project_root": str(root)}))
    finally:
        monkeypatch.undo()

    assert "Curated context written" in _text(result)
    assert any(call[0] == "close" and call[2] is None for call in manager.calls)


def test_startup_composes_no_project_context_or_pilot_runtime(monkeypatch, tmp_path):
    imported = []
    original_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if "coordination.pilot" in name or "pilot_store" in name:
            imported.append(name)
            raise AssertionError("startup must not import Pilot runtime")
        return original_import(name, *args, **kwargs)

    class DB:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        async def connect(self):
            pass

        async def close(self):
            pass

    class Manager:
        def __init__(self, **kwargs):
            self.calls = []

        async def spawn_agent(self, **kwargs):
            self.calls.append(("spawn", kwargs))

        async def send_message(self, *args, **kwargs):
            self.calls.append(("send", args, kwargs))

        async def poll(self, *args, **kwargs):
            self.calls.append(("poll", args, kwargs))

        async def close(self, *args, **kwargs):
            self.calls.append(("close", args, kwargs))

    monkeypatch.setattr(server, "OlympusDB", DB)
    monkeypatch.setattr(server, "ACPManager", Manager)
    monkeypatch.setattr(server, "get_db_path", lambda: tmp_path / "db")
    monkeypatch.setattr(
        config_loader,
        "get_config",
        lambda: OlympusV3Config(profiles_dir=tmp_path),
    )
    monkeypatch.setattr(builtins, "__import__", guarded_import)

    asyncio.run(server.init_server())

    assert imported == []
    assert server._harmonia_registry.context_count == 0
    assert server._manager.calls == []
    asyncio.run(server.shutdown_server())
