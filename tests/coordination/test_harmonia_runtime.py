from __future__ import annotations

import asyncio
import base64
from pathlib import Path

import pytest

from olympus_v3.coordination import harmonia_runtime
from olympus_v3.coordination.harmonia_runtime import (
    CoordinationKeyProviderUnavailable,
    EnvironmentCoordinationKeyProvider,
    ProjectRuntimeRegistry,
    StaticCoordinationKeyProvider,
)


class PublicOnlyManager:
    def __init__(self):
        self.calls = []

    @property
    def agents(self):
        raise AssertionError("registry must not inspect manager.agents")

    @property
    def sessions(self):
        raise AssertionError("registry must not inspect manager.sessions")

    async def spawn_agent(self, *args, **kwargs):
        self.calls.append(("spawn_agent", args, kwargs))

    async def send_message(self, *args, **kwargs):
        self.calls.append(("send_message", args, kwargs))

    async def poll(self, *args, **kwargs):
        self.calls.append(("poll", args, kwargs))

    async def close(self, *args, **kwargs):
        self.calls.append(("close", args, kwargs))


class CountingProvider(StaticCoordinationKeyProvider):
    def __init__(self):
        super().__init__(b"w" * 32, b"i" * 32)
        self.calls = 0

    def load(self):
        self.calls += 1
        return super().load()


def test_registry_construction_is_default_off_and_creates_no_runtime_or_store(tmp_path):
    provider = CountingProvider()
    manager = PublicOnlyManager()

    registry = ProjectRuntimeRegistry(tmp_path / "aether-home", manager, provider)

    assert registry.context_count == 0
    assert provider.calls == 0
    assert manager.calls == []
    assert not (tmp_path / "aether-home").exists()


def test_first_eligible_acquisition_creates_exactly_one_project_context(tmp_path):
    home = tmp_path / "aether-home"
    project = tmp_path / "project"
    project.mkdir()
    provider = CountingProvider()
    manager = PublicOnlyManager()
    registry = ProjectRuntimeRegistry(home, manager, provider)

    first = asyncio.run(registry.get_or_create(project))
    second = asyncio.run(registry.get_or_create(project / "."))

    assert first is second
    assert registry.context_count == 1
    assert provider.calls == 1
    assert first.identity.store_path.exists()
    assert first.ledger.scope.installation_id == first.identity.installation_id
    assert first.ledger.scope.project_id == first.identity.project_id
    assert first.adapter.manager is manager
    assert manager.calls == []
    asyncio.run(registry.close())


def test_concurrent_same_project_acquisition_returns_one_context(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    provider = CountingProvider()
    registry = ProjectRuntimeRegistry(tmp_path / "home", PublicOnlyManager(), provider)

    async def acquire_many():
        return await asyncio.gather(*(registry.get_or_create(project) for _ in range(20)))

    contexts = asyncio.run(acquire_many())

    assert len({id(context) for context in contexts}) == 1
    assert provider.calls == 1
    assert registry.context_count == 1
    asyncio.run(registry.close())


def test_different_projects_receive_isolated_scopes_and_ledgers(tmp_path):
    root_a = tmp_path / "a"
    root_b = tmp_path / "b"
    root_a.mkdir()
    root_b.mkdir()
    registry = ProjectRuntimeRegistry(
        tmp_path / "home", PublicOnlyManager(), StaticCoordinationKeyProvider(b"w" * 32, b"i" * 32)
    )

    async def acquire_both():
        return await asyncio.gather(registry.get_or_create(root_a), registry.get_or_create(root_b))

    context_a, context_b = asyncio.run(acquire_both())

    assert context_a is not context_b
    assert context_a.ledger.scope != context_b.ledger.scope
    assert context_a.identity.store_path != context_b.identity.store_path
    assert registry.context_count == 2
    asyncio.run(registry.close())


@pytest.mark.parametrize(
    "environment",
    [
        {},
        {"AETHER_COORDINATION_WRITER_KEY_B64": "not-base64", "AETHER_COORDINATION_INTEGRITY_KEY_B64": "also-bad"},
        {
            "AETHER_COORDINATION_WRITER_KEY_B64": base64.b64encode(b"short").decode(),
            "AETHER_COORDINATION_INTEGRITY_KEY_B64": base64.b64encode(b"short").decode(),
        },
    ],
)
def test_missing_malformed_or_short_keys_fail_before_database_creation(tmp_path, environment):
    project = tmp_path / "project"
    project.mkdir()
    home = tmp_path / "home"
    registry = ProjectRuntimeRegistry(home, PublicOnlyManager(), EnvironmentCoordinationKeyProvider(environment))

    with pytest.raises(CoordinationKeyProviderUnavailable, match="coordination keys unavailable"):
        asyncio.run(registry.get_or_create(project))

    assert registry.context_count == 0
    assert not home.exists()


def test_key_material_is_not_represented_or_persisted_in_ledger_payloads(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    writer_key = b"writer-secret-material-1234567890X"
    integrity_key = b"integrity-secret-material-1234567Y"
    registry = ProjectRuntimeRegistry(
        tmp_path / "home",
        PublicOnlyManager(),
        StaticCoordinationKeyProvider(writer_key, integrity_key),
    )

    context = asyncio.run(registry.get_or_create(project))
    keys = context.keys
    context.ledger.conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    database_bytes = context.identity.store_path.read_bytes()

    assert writer_key not in database_bytes
    assert integrity_key not in database_bytes
    assert base64.b64encode(writer_key) not in database_bytes
    assert base64.b64encode(integrity_key) not in database_bytes
    assert "writer-secret" not in repr(keys)
    assert "integrity-secret" not in repr(keys)
    asyncio.run(registry.close())


def test_registry_close_is_bounded_idempotent_and_closes_every_ledger(tmp_path):
    roots = [tmp_path / "a", tmp_path / "b"]
    for root in roots:
        root.mkdir()
    registry = ProjectRuntimeRegistry(
        tmp_path / "home", PublicOnlyManager(), StaticCoordinationKeyProvider(b"w" * 32, b"i" * 32)
    )

    async def exercise():
        contexts = await asyncio.gather(*(registry.get_or_create(root) for root in roots))
        await asyncio.wait_for(registry.close(timeout_seconds=0.5), timeout=1)
        await asyncio.wait_for(registry.close(timeout_seconds=0.5), timeout=1)
        return contexts

    contexts = asyncio.run(exercise())

    assert registry.context_count == 0
    assert all(context.closed for context in contexts)
    assert all(context.ledger._closed for context in contexts)


def test_context_build_failure_closes_partial_ledger(tmp_path, monkeypatch):
    project = tmp_path / "project"
    project.mkdir()
    closed = []
    real_ledger = harmonia_runtime.SQLiteLedger

    class TrackingLedger(real_ledger):
        def close(self):
            closed.append(self.path)
            super().close()

    class BuildFailure(RuntimeError):
        pass

    def fail_runtime(*args, **kwargs):
        raise BuildFailure("runtime construction failed")

    monkeypatch.setattr(harmonia_runtime, "SQLiteLedger", TrackingLedger)
    monkeypatch.setattr(harmonia_runtime, "KernelRunService", fail_runtime)
    registry = ProjectRuntimeRegistry(
        tmp_path / "home", PublicOnlyManager(), StaticCoordinationKeyProvider(b"w" * 32, b"i" * 32)
    )

    with pytest.raises(BuildFailure, match="runtime construction failed"):
        asyncio.run(registry.get_or_create(project))

    assert len(closed) == 1
    assert registry.context_count == 0
