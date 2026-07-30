from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from olympus_v3.config_loader import CoordinationConfig
from olympus_v3.coordination.harmonia_runtime import (
    ProjectRuntimeRegistry,
    StaticCoordinationKeyProvider,
)
from olympus_v3.coordination.harmonia_service import HarmoniaService
from olympus_v3.coordination.principal import Principal


class Manager:
    def __init__(self, *, send_error: Exception | None = None, close_error: Exception | None = None):
        self.send_error = send_error
        self.close_error = close_error
        self.spawned: list[str] = []
        self.sent: list[str] = []
        self.closed: list[str] = []
        self.polled: list[str] = []
        self.before_close = None

    async def spawn_agent(self, *, agent_name, session_id, project_root):
        self.spawned.append(session_id)
        return session_id

    async def send_message(self, session_id, prompt):
        self.sent.append(session_id)
        if self.send_error:
            raise self.send_error

    async def poll(self, session_id):
        self.polled.append(session_id)
        return {"status": "working"}

    async def close(self, session_id, *, terminal_status):
        if self.before_close:
            self.before_close()
        self.closed.append(session_id)
        if self.close_error:
            raise self.close_error


def run(awaitable):
    return asyncio.run(awaitable)


def test_principal_accepts_sha256_project_identity_starting_with_digit():
    assert Principal("0" * 64, "harmonia", "hermes").project_id == "0" * 64


def payload(root: Path, **overrides):
    value = {
        "action": "start",
        "project_root": str(root),
        "request_id": "service-one",
        "contract": {
            "worker": "hefesto",
            "objective": "Implement exactly one bounded change",
            "expected_outcome": "Focused tests pass",
            "included_scopes": ["src/olympus_v3/coordination"],
            "excluded_scopes": ["home/config.yaml"],
            "worker_permissions": ["read", "write"],
            "time_seconds": 600,
            "model_budget": 100,
            "qa_reserve": 1,
            "recovery_reserve": 1,
            "escalation_conditions": ["ambiguity"],
        },
        "plan_revision": 1,
        "snapshot_digest": "sha256:" + "a" * 64,
    }
    value.update(overrides)
    return value


def enabled_config(root: Path, *, cap: int = 1, allowlisted: bool = True):
    return CoordinationConfig(
        enabled=True,
        mode="legacy",
        allowed_modes=("legacy", "kernel-single-task"),
        project_allowlist=(str(root.resolve()),) if allowlisted else (),
        max_active_runs=cap,
    )


def service(tmp_path: Path, root: Path, manager: Manager, *, config=None):
    registry = ProjectRuntimeRegistry(
        tmp_path / "aether-home",
        manager,
        StaticCoordinationKeyProvider(b"w" * 32, b"i" * 32),
    )
    instance = HarmoniaService(
        aether_home=tmp_path / "aether-home",
        config=config or enabled_config(root),
        registry=registry,
        discovered_workers={"hefesto"},
    )
    return instance, registry


@pytest.mark.parametrize(
    ("config_factory", "code"),
    [
        (lambda root: CoordinationConfig(), "feature_disabled"),
        (lambda root: enabled_config(root, allowlisted=False), "project_not_allowed"),
        (lambda root: enabled_config(root, cap=0), "admission_limit"),
    ],
)
def test_start_admission_fails_before_runtime_or_store(tmp_path, config_factory, code):
    root = tmp_path / "project"
    root.mkdir()
    manager = Manager()
    instance, registry = service(tmp_path, root, manager, config=config_factory(root))

    result = run(instance.handle(payload(root)))

    assert result["error"]["code"] == code
    assert registry.context_count == 0
    assert not (tmp_path / "aether-home" / ".olympus").exists()
    assert manager.spawned == []


def test_start_success_and_exact_replay_produce_one_effect_and_one_durable_identity(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    manager = Manager()
    instance, registry = service(tmp_path, root, manager)

    first = run(instance.handle(payload(root)))
    second = run(instance.handle(payload(root)))

    assert first == second
    assert first["ok"] is True
    assert first["state"] == "session_bound"
    assert first["runtime_authority"] == "kernel"
    assert first["durable"] is True
    assert first["attempt"] == 1
    assert len(manager.spawned) == 1
    context = run(registry.get_or_create(root))
    counts = {
        kind: sum(event["kind"] == kind for event in context.ledger.events())
        for kind in ("run.created", "task.created", "attempt.started", "dispatch.staged", "session.bound")
    }
    assert counts == {kind: 1 for kind in counts}


def test_conflicting_replay_and_second_request_return_distinct_stable_errors(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    instance, _ = service(tmp_path, root, Manager())
    assert run(instance.handle(payload(root)))["ok"] is True

    changed = payload(root)
    changed["contract"] = {**changed["contract"], "objective": "Different objective"}
    conflict = run(instance.handle(changed))
    second = run(instance.handle(payload(root, request_id="service-two")))

    assert conflict["error"]["code"] == "idempotency_conflict"
    assert second["error"]["code"] == "admission_limit"


def test_status_is_cold_read_only_and_does_not_add_an_acp_poll(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    manager = Manager()
    instance, registry = service(tmp_path, root, manager)
    started = run(instance.handle(payload(root)))
    contexts_before = registry.context_count
    polls_before = list(manager.polled)

    status = run(
        instance.handle({"action": "status", "project_root": str(root), "run_id": started["run_id"]})
    )

    assert status == {**started, "action": "status"}
    assert registry.context_count == contexts_before
    assert manager.polled == polls_before


def test_status_missing_store_creates_nothing(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    instance, registry = service(tmp_path, root, Manager())

    result = run(
        instance.handle(
            {"action": "status", "project_root": str(root), "run_id": "run-" + "b" * 32}
        )
    )

    assert result["error"]["code"] == "not_found"
    assert registry.context_count == 0
    assert not (tmp_path / "aether-home" / ".olympus").exists()


def test_ambiguous_send_projects_reconciliation_required_without_poll(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    manager = Manager(send_error=TimeoutError("response lost"))
    instance, _ = service(tmp_path, root, manager)

    result = run(instance.handle(payload(root)))

    assert result["state"] == "reconciliation_required"
    assert result["uncertainty"] == "external_effect_unknown"
    assert manager.polled == []


def test_stop_persists_intent_before_close_and_repeated_stop_does_not_close_again(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    manager = Manager()
    instance, registry = service(tmp_path, root, manager)
    started = run(instance.handle(payload(root)))
    context = run(registry.get_or_create(root))

    def assert_intent():
        assert any(event["kind"] == "cancel.intent" for event in context.ledger.events())

    manager.before_close = assert_intent
    stop_request = {
        "action": "stop",
        "project_root": str(root),
        "run_id": started["run_id"],
        "reason": "operator request",
    }
    first = run(instance.handle(stop_request))
    second = run(instance.handle(stop_request))

    assert first["state"] == second["state"] == "cancel_requested"
    assert first["uncertainty"] == second["uncertainty"] == "cleanup_unverified"
    assert len(manager.closed) == 1
    assert sum(event["kind"] == "cancel.intent" for event in context.ledger.events()) == 1


def test_stop_close_timeout_preserves_committed_intent_and_honest_uncertainty(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    manager = Manager(close_error=TimeoutError("close response lost"))
    instance, registry = service(tmp_path, root, manager)
    started = run(instance.handle(payload(root)))

    result = run(
        instance.handle({"action": "stop", "project_root": str(root), "run_id": started["run_id"]})
    )

    assert result["state"] == "cancel_requested"
    assert result["uncertainty"] == "cancel_delivery_unknown"
    context = run(registry.get_or_create(root))
    assert any(event["kind"] == "cancel.intent" for event in context.ledger.events())


def test_public_states_never_claim_completion_or_closure(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    instance, _ = service(tmp_path, root, Manager())
    started = run(instance.handle(payload(root)))
    stopped = run(
        instance.handle({"action": "stop", "project_root": str(root), "run_id": started["run_id"]})
    )

    forbidden = {"stopped", "closed", "completed", "failed", "cancelled"}
    assert started["state"] not in forbidden
    assert stopped["state"] not in forbidden
