from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from olympus_v3 import config_loader, server
from olympus_v3.config_loader import CoordinationConfig, OlympusV3Config


class FakeService:
    def __init__(self, response=None, error: Exception | None = None):
        self.response = response
        self.error = error
        self.calls = []

    async def handle(self, arguments):
        self.calls.append(dict(arguments))
        if self.error:
            raise self.error
        return self.response or {
            "action": arguments["action"],
            "ok": True,
            "runtime_authority": "kernel",
            "durable": True,
            "state": "admitted",
            "uncertainty": None,
            "error": None,
        }


class FakeRegistry:
    instances = []

    def __init__(self, aether_home, manager, key_provider):
        self.aether_home = Path(aether_home)
        self.manager = manager
        self.key_provider = key_provider
        self.context_count = 0
        self.close_calls = 0
        self.__class__.instances.append(self)

    async def close(self):
        self.close_calls += 1


class FakeDB:
    def __init__(self, db_path=None):
        self.db_path = db_path
        self.connect_calls = 0
        self.close_calls = 0

    async def connect(self):
        self.connect_calls += 1

    async def close(self):
        self.close_calls += 1


class FakeManager:
    def __init__(self, profiles_dir=None, db=None):
        self.profiles_dir = profiles_dir
        self.db = db
        self.calls = []


@pytest.fixture(autouse=True)
def reset_harmonia_globals(monkeypatch):
    monkeypatch.setattr(server, "_harmonia_service", None, raising=False)
    monkeypatch.setattr(server, "_harmonia_registry", None, raising=False)
    FakeRegistry.instances.clear()


def text(result):
    return json.loads(result[0].text)


@pytest.mark.parametrize("action", ["start", "status", "stop"])
def test_each_harmonia_action_reaches_one_service_branch(monkeypatch, action, tmp_path):
    fake = FakeService()
    monkeypatch.setattr(server, "_harmonia_service", fake, raising=False)

    result = asyncio.run(server.call_tool("harmonia", {"action": action, "project_root": str(tmp_path)}))

    assert text(result)["action"] == action
    assert fake.calls == [{"action": action, "project_root": str(tmp_path)}]


def test_harmonia_handler_sanitizes_unexpected_exceptions(monkeypatch, tmp_path):
    internal_detail = "sensitive-internal-detail"
    monkeypatch.setattr(
        server,
        "_harmonia_service",
        FakeService(error=RuntimeError(internal_detail)),
        raising=False,
    )

    result = text(
        asyncio.run(server.call_tool("harmonia", {"action": "start", "project_root": str(tmp_path)}))
    )

    assert result["error"]["code"] == "internal_failure"
    assert internal_detail not in json.dumps(result)


def test_disabled_start_response_has_no_legacy_or_manager_effect(monkeypatch, tmp_path):
    manager = FakeManager()
    fake = FakeService(
        response={
            "action": "start",
            "ok": False,
            "runtime_authority": "kernel",
            "durable": False,
            "state": None,
            "uncertainty": None,
            "error": {"code": "feature_disabled", "message": "Harmonia is disabled.", "retryable": False},
        }
    )
    monkeypatch.setattr(server, "_manager", manager)
    monkeypatch.setattr(server, "_harmonia_service", fake, raising=False)

    result = text(
        asyncio.run(server.call_tool("harmonia", {"action": "start", "project_root": str(tmp_path)}))
    )

    assert result["error"]["code"] == "feature_disabled"
    assert manager.calls == []


def test_init_composes_registry_without_creating_project_runtime(monkeypatch, tmp_path):
    profiles = tmp_path / "home" / "profiles"
    profiles.mkdir(parents=True)
    config = OlympusV3Config(
        profiles_dir=profiles,
        db_path=tmp_path / "olympus.db",
        coordination=CoordinationConfig(),
    )
    config.daimons = {"hefesto": object()}
    monkeypatch.setattr(config_loader, "get_config", lambda: config)
    monkeypatch.setattr(server, "OlympusDB", FakeDB)
    monkeypatch.setattr(server, "ACPManager", FakeManager)
    monkeypatch.setattr(server, "ProjectRuntimeRegistry", FakeRegistry, raising=False)
    monkeypatch.setattr(server, "EnvironmentCoordinationKeyProvider", object, raising=False)
    monkeypatch.setattr(server, "HarmoniaService", lambda **kwargs: FakeService(), raising=False)

    asyncio.run(server.init_server())

    assert len(FakeRegistry.instances) == 1
    assert FakeRegistry.instances[0].context_count == 0
    assert server._harmonia_service is not None


def test_shutdown_closes_registry_exactly_once(monkeypatch):
    registry = FakeRegistry("/tmp/home", FakeManager(), object())
    db = FakeDB()
    monkeypatch.setattr(server, "_harmonia_registry", registry, raising=False)
    monkeypatch.setattr(server, "_harmonia_service", FakeService(), raising=False)
    monkeypatch.setattr(server, "_db", db)

    asyncio.run(server.shutdown_server())
    asyncio.run(server.shutdown_server())

    assert registry.close_calls == 1
    assert db.close_calls == 1
    assert server._harmonia_registry is None
    assert server._harmonia_service is None
