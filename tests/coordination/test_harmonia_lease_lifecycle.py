"""Behavioral RED regressions for GitHub #107 Harmonia lease lifecycle."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from olympus_v3.acp_manager import ACPManager, SessionInfo
from olympus_v3.coordination import (
    ContractLimits,
    ContractState,
    EvidenceGate,
    ExecutionContract,
    HMACIntegritySigner,
    HMACWriterAuthenticator,
    Principal,
    Result,
    SideEffectPolicy,
    SQLiteLedger,
    StoreScope,
    TaskState,
    WriterContext,
)
from olympus_v3.coordination.harmonia_runtime import ProjectRuntimeContext
from olympus_v3.coordination.harmonia_service import HarmoniaService
from olympus_v3.coordination.kernel_dispatcher import DispatchAuthority, KernelDispatcher
from olympus_v3.coordination.kernel_runtime import KernelRunService, KernelWriter
from olympus_v3.coordination.olympus_adapter import OlympusRuntimeAdapter

PROJECT = "project-a"
OWNER = Principal(PROJECT, "hermes", "owner")
WORKER = Principal(PROJECT, "hermes", "worker")


class FakeClock:
    def __init__(self, value: int = 1_000_000):
        self.value = value

    def __call__(self) -> int:
        return self.value

    def advance(self, amount: int) -> None:
        self.value += amount


@dataclass
class TerminalObservation:
    status: str
    logical_session: str
    acp_session_id: str
    message_id: str


class EffectBarrier:
    def __init__(self, *, observation: dict | None = None, cleanup_error: Exception | None = None):
        self.calls: list[tuple[str, dict]] = []
        self.observation = observation or {"status": "working", "acp_session_id": "acp-session-1"}
        self.observations: list[dict] = []
        self.observation_hook = None
        self.cleanup_error = cleanup_error
        self.cleanup_started = asyncio.Event()
        self.cleanup_release = asyncio.Event()
        self.block_cleanup = False

    async def dispatch(self, **request):
        self.calls.append(("dispatch", request))
        return {"accepted": True, "acp_session_id": "acp-session-1"}

    async def observe(self, **request):
        self.calls.append(("observe", request))
        if self.observation_hook:
            self.observation_hook(len([kind for kind, _ in self.calls if kind == "observe"]))
        if self.observations:
            return self.observations.pop(0)
        return self.observation

    async def cancel(self, **request):
        self.calls.append(("cancel", request))
        return {"accepted": True}

    async def cleanup(self, **request):
        self.calls.append(("cleanup", request))
        self.cleanup_started.set()
        if self.block_cleanup:
            await self.cleanup_release.wait()
        if self.cleanup_error:
            raise self.cleanup_error
        return {"status": request.get("terminal_status", "completed")}


class PublicManager:
    def __init__(self, *, cleanup_error: Exception | None = None):
        self.calls: list[tuple[str, object]] = []
        self.cleanup_error = cleanup_error
        self.before_close = None
        self.sessions: set[str] = set()

    async def spawn_agent(self, *, agent_name, session_id, project_root):
        self.calls.append(("spawn", session_id))
        self.sessions.add(session_id)
        return session_id

    async def send_message(self, session_id, prompt):
        self.calls.append(("send", session_id))

    async def poll(self, session_id):
        self.calls.append(("poll", session_id))
        return {"status": "working"}

    async def close(self, session_id, *, terminal_status):
        if self.before_close:
            self.before_close()
        self.calls.append(("close", (session_id, terminal_status)))
        if self.cleanup_error:
            raise self.cleanup_error
        return {"status": terminal_status}

    async def cleanup_persisted(self, session_id, *, terminal_status, project_id):
        self.calls.append(("cleanup_persisted", (session_id, terminal_status, project_id)))
        if session_id not in self.sessions:
            raise ValueError("unknown persisted session")
        if self.cleanup_error:
            raise self.cleanup_error
        return {"status": terminal_status}


def run(awaitable):
    return asyncio.run(awaitable)


def make_contract() -> ExecutionContract:
    return ExecutionContract(
        contract_id="contract-a",
        project_id=PROJECT,
        generation=0,
        owner=OWNER,
        participants=(OWNER, WORKER),
        objective="build",
        expected_outcome="verified",
        included_scopes=("src/",),
        excluded_scopes=("secrets/",),
        role_permissions={"worker": ("implement",)},
        evidence_gates=(EvidenceGate("qa", True),),
        side_effect_policy=SideEffectPolicy(("filesystem",), 2, True),
        limits=ContractLimits(2, 60, 3, 100, 1, 1),
        escalation_conditions=("ambiguity",),
        completion_authority=OWNER,
        amendment_authority=OWNER,
        status=ContractState.ACTIVE,
    )


@pytest.fixture
def stack(tmp_path: Path):
    clock = FakeClock()
    scope = StoreScope("install-a", PROJECT)
    auth = HMACWriterAuthenticator({("owner", "key-owner"): b"owner-key"})
    ledger = SQLiteLedger(
        tmp_path / "kernel.sqlite",
        scope,
        writer_authenticator=auth,
        integrity_signer=HMACIntegritySigner(b"integrity-key"),
        clock=clock,
    )
    lease = ledger.acquire_lease("ledger-owner", "owner", ttl=100_000_000_000).lease
    assert lease is not None
    writer_context = WriterContext(scope, "owner", "key-owner", "ledger-owner", lease.epoch, lease.expires_at)
    assert ledger.create_contract(make_contract()) in (Result.APPLIED, Result.DUPLICATE)
    runtime = KernelRunService(ledger, writer=KernelWriter(writer_context, auth))
    runtime.create_run(run_id="run-a", contract_id="contract-a", mode="kernel")
    runtime.create_task("run-a", task_id="task-a")
    runtime.admit_task("run-a", "task-a")
    runtime.mark_task_ready("run-a", "task-a")
    runtime.dispatch_task("run-a", "task-a")
    attempt = runtime.start_attempt("run-a", "task-a")
    effects = EffectBarrier()
    dispatcher = KernelDispatcher(ledger=ledger, runtime=runtime, runtime_adapter=effects, worker_id="owner")
    envelope = dispatcher.stage_ready(
        "run-a", "task-a", attempt=attempt.attempt, project_root="/workspace/project", plan_revision=7, snapshot_digest="sha256:snapshot"
    )
    yield clock, ledger, runtime, dispatcher, envelope, effects
    if not ledger._closed:
        ledger.close()


def event_payloads(ledger, kind: str) -> list[dict]:
    return [json.loads(row["payload"]) for row in ledger.events() if row["kind"] == kind]


def authority_from(payload: dict) -> DispatchAuthority:
    names = (
        "installation_id", "project_id", "run_id", "task_id", "attempt", "contract_id",
        "contract_generation", "revocation_epoch", "agent_name", "plan_id", "plan_revision",
        "snapshot_digest", "project_root", "logical_session", "message_id", "lease_resource",
        "lease_owner", "lease_epoch", "lease_token", "lease_until",
    )
    return DispatchAuthority(*(payload[name] for name in names))


def test_renewal_extends_same_dispatch_row_without_epoch_or_token_change(stack):
    clock, ledger, _, dispatcher, envelope, _ = stack
    authority = envelope.authority
    original = ledger.lease(authority.lease_resource)
    renewed = dispatcher.renew_with(authority, ttl=500)
    current = ledger.lease(authority.lease_resource)

    assert renewed.lease is not None
    assert current is not None
    assert (current.resource, current.owner, current.epoch, current.token) == (
        original.resource, original.owner, original.epoch, original.token
    )
    assert current.expires_at > authority.lease_until
    assert renewed.lease.epoch == authority.lease_epoch
    assert clock() < current.expires_at


@pytest.mark.parametrize(
    "mutation",
    ["expired", "foreign-token", "replaced-epoch", "revoked-contract", "replaced-attempt"],
)
def test_renewal_rejects_stale_or_replaced_authority_without_reacquisition(stack, mutation):
    clock, ledger, _, dispatcher, envelope, _ = stack
    authority = envelope.authority
    epoch_before = ledger.lease(authority.lease_resource).epoch
    if mutation == "expired":
        clock.advance(authority.lease_until - clock() + 1)
    elif mutation == "foreign-token":
        ledger.conn.execute("UPDATE leases SET token=? WHERE resource=?", ("foreign", authority.lease_resource))
    elif mutation == "replaced-epoch":
        clock.advance(authority.lease_until - clock() + 1)
        ledger.acquire_lease(authority.lease_resource, "other", ttl=100)
    elif mutation == "revoked-contract":
        ledger.conn.execute(
            "UPDATE contract_heads SET revocation_epoch=revocation_epoch+1 WHERE contract_id=?",
            (authority.contract_id,),
        )
    else:
        dispatcher.supersede_attempt("run-a", "task-a", attempt=authority.attempt, replacement_attempt=2)

    with pytest.raises(Exception):
        dispatcher.renew_with(authority, ttl=500)

    current = ledger.lease(authority.lease_resource)
    if mutation == "replaced-epoch":
        assert current.epoch != epoch_before
    else:
        assert current.epoch == epoch_before


def test_terminal_observation_is_authenticated_as_one_event_and_not_semantic_completion(stack):
    _, ledger, runtime, dispatcher, envelope, _ = stack
    authority = envelope.authority
    run(dispatcher.dispatch_with(authority))
    binding = event_payloads(ledger, "session.bound")[0]
    observation = TerminalObservation(
        "completed", authority.logical_session, binding["acp_session_id"], authority.message_id
    )

    first = dispatcher.record_terminal_with(authority, observation)
    replay = dispatcher.record_terminal_with(authority, observation)

    assert first == replay
    assert len(event_payloads(ledger, "runtime.terminal.observed")) == 1
    payload = event_payloads(ledger, "runtime.terminal.observed")[0]
    assert payload["run_id"] == authority.run_id
    assert payload["task_id"] == authority.task_id
    assert payload["attempt"] == authority.attempt
    assert payload["contract_generation"] == authority.contract_generation
    assert payload["revocation_epoch"] == authority.revocation_epoch
    assert payload["message_id"] == authority.message_id
    assert payload["logical_session"] == authority.logical_session
    assert payload["acp_session_id"] == observation.acp_session_id
    assert runtime.task("run-a", "task-a").state is not TaskState.COMPLETED


def test_terminal_observation_rejects_mismatched_session_or_status(stack):
    _, ledger, _, dispatcher, envelope, _ = stack
    authority = envelope.authority
    run(dispatcher.dispatch_with(authority))
    binding = event_payloads(ledger, "session.bound")[0]
    dispatcher.record_terminal_with(
        authority,
        TerminalObservation("completed", authority.logical_session, binding["acp_session_id"], authority.message_id),
    )
    with pytest.raises(Exception):
        dispatcher.record_terminal_with(
            authority, TerminalObservation("error", authority.logical_session + "-foreign", "acp-session-2", authority.message_id)
        )
    assert len(event_payloads(ledger, "runtime.terminal.observed")) == 1


def test_monitor_renews_past_original_deadline_then_persists_terminal_before_removal(stack):
    clock, ledger, runtime, dispatcher, envelope, effects = stack
    authority = envelope.authority
    run(dispatcher.dispatch_with(authority))
    context = ProjectRuntimeContext(None, None, ledger, runtime, None, dispatcher)
    effects.observations = [
        {"status": "working", "acp_session_id": "acp-session-1"},
        {"status": "completed", "acp_session_id": "acp-session-1"},
    ]

    def move_clock(observation_number):
        clock.value = authority.lease_until - 1 if observation_number == 1 else authority.lease_until + 1

    effects.observation_hook = move_clock

    async def scenario():
        task = await context.start_monitor(authority, clock=clock, poll_interval=0)
        duplicate = await context.start_monitor(authority, clock=clock, poll_interval=0)
        assert duplicate is task
        for _ in range(50):
            if event_payloads(ledger, "runtime.terminal.observed"):
                break
            await asyncio.sleep(0)
        assert event_payloads(ledger, "runtime.terminal.observed")
        assert ledger.lease(authority.lease_resource).expires_at > authority.lease_until
        assert clock() > authority.lease_until
        assert authority.message_id not in context.monitor_tasks
        assert not event_payloads(ledger, "cancel.intent")
        assert task.done()

    run(scenario())


def test_monitor_shutdown_cancels_and_awaits_before_ledger_close(stack):
    _, ledger, runtime, dispatcher, envelope, effects = stack
    context = ProjectRuntimeContext(None, None, ledger, runtime, None, dispatcher)
    effects.observation = {"status": "working", "acp_session_id": "acp-session-1"}

    async def scenario():
        task = await context.start_monitor(envelope.authority, poll_interval=0)
        await asyncio.sleep(0)
        assert not task.done()
        await context.aclose()
        assert task.done()
        assert context.monitor_tasks == {}

    run(scenario())
    assert context.closed is True
    assert ledger._closed is True


def test_active_stop_is_intent_before_one_cancel_under_concurrent_replay(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    manager = PublicManager()
    service, registry = _service(tmp_path, root, manager)
    started = run(service.handle(_request(root)))
    context = run(registry.get_or_create(root))
    manager.before_close = lambda: assert_event_exists(context.ledger, "cancel.intent")
    stop = {"action": "stop", "project_root": str(root), "run_id": started["run_id"], "reason": "operator"}
    async def concurrent_stops():
        return await asyncio.gather(service.handle(stop), service.handle(stop))

    first, second = run(concurrent_stops())

    assert first["state"] == second["state"] == "cancel_requested"
    assert sum(event["kind"] == "cancel.intent" for event in context.ledger.events()) == 1
    assert [kind for kind, _ in manager.calls].count("close") == 1
    run(registry.close())


@pytest.mark.parametrize("cleanup_error", [None, TimeoutError("cleanup timeout")])
def test_terminal_cleanup_after_expired_dispatch_has_one_effect_and_no_cancel(tmp_path, cleanup_error):
    root = tmp_path / "project"
    root.mkdir()
    manager = PublicManager(cleanup_error=cleanup_error)
    service, registry = _service(tmp_path, root, manager)
    started = run(service.handle(_request(root)))
    context = run(registry.get_or_create(root))
    authority = authority_from(json.loads(next(e["payload"] for e in context.ledger.events() if e["kind"] == "dispatch.staged")))
    binding = json.loads(next(e["payload"] for e in context.ledger.events() if e["kind"] == "session.bound"))
    context.dispatcher.record_terminal_with(
        authority,
        TerminalObservation("completed", authority.logical_session, binding["acp_session_id"], authority.message_id),
    )
    context.ledger.clock = lambda: authority.lease_until + 1

    first = run(service.handle({"action": "stop", "project_root": str(root), "run_id": started["run_id"]}))
    replay = run(service.handle({"action": "stop", "project_root": str(root), "run_id": started["run_id"]}))

    expected = "unknown" if cleanup_error else "completed"
    assert first["cleanup_state"] == replay["cleanup_state"] == expected
    assert [kind for kind, _ in manager.calls].count("cleanup_persisted") == 1
    assert not any(event["kind"] == "cancel.intent" for event in context.ledger.events())
    run(registry.close())


@pytest.mark.parametrize("action", ["status", "stop"])
def test_expired_without_terminal_evidence_reconciles_without_adapter_effect(tmp_path, action):
    root = tmp_path / "project"
    root.mkdir()
    manager = PublicManager()
    service, registry = _service(tmp_path, root, manager)
    started = run(service.handle(_request(root)))
    context = run(registry.get_or_create(root))
    authority = authority_from(
        json.loads(next(e["payload"] for e in context.ledger.events() if e["kind"] == "dispatch.staged"))
    )
    lease_before = context.ledger.lease(authority.lease_resource)
    assert lease_before is not None
    epoch_before = lease_before.epoch
    context.ledger.conn.execute(
        "UPDATE leases SET expires_at=1 WHERE installation_id=? AND project_id=? AND resource=?",
        (context.ledger.scope.installation_id, context.ledger.scope.project_id, authority.lease_resource),
    )
    context.ledger.conn.commit()
    result = run(service.handle({"action": action, "project_root": str(root), "run_id": started["run_id"]}))

    assert result["state"] == "reconciliation_required"
    assert not any(kind == "close" for kind, _ in manager.calls)
    assert not any(kind == "cleanup_persisted" for kind, _ in manager.calls)
    assert not any(kind == "send" for kind, _ in manager.calls[2:])
    lease_after = context.ledger.lease(authority.lease_resource)
    assert lease_after is not None
    assert lease_after.epoch == epoch_before
    run(registry.close())


def test_restart_resumes_live_binding_once_without_spawn_or_send(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    manager = PublicManager()
    service, registry = _service(tmp_path, root, manager)

    async def scenario():
        started = await service.handle(_request(root))
        first_context = await registry.get_or_create(root)
        authority = authority_from(
            json.loads(
                next(e["payload"] for e in first_context.ledger.events() if e["kind"] == "dispatch.staged")
            )
        )
        await registry.close()
        restarted, registry2 = _service(tmp_path, root, manager)
        result = await restarted.handle(
            {"action": "status", "project_root": str(root), "run_id": started["run_id"]}
        )
        context2 = await registry2.get_or_create(root)
        await asyncio.sleep(0)
        assert result["state"] == "session_bound"
        assert tuple(context2.monitor_tasks) == (authority.message_id,)
        assert [kind for kind, _ in manager.calls].count("spawn") == 1
        assert [kind for kind, _ in manager.calls].count("send") == 1
        await registry2.close()

    run(scenario())


def test_restart_terminal_evidence_cleans_once_and_missing_evidence_stays_fail_closed(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    manager = PublicManager()
    service, registry = _service(tmp_path, root, manager)
    started = run(service.handle(_request(root)))
    context = run(registry.get_or_create(root))
    authority = authority_from(json.loads(next(e["payload"] for e in context.ledger.events() if e["kind"] == "dispatch.staged")))
    binding = json.loads(next(e["payload"] for e in context.ledger.events() if e["kind"] == "session.bound"))
    context.dispatcher.record_terminal_with(
        authority,
        TerminalObservation("completed", authority.logical_session, binding["acp_session_id"], authority.message_id),
    )
    run(registry.close())
    restarted, registry2 = _service(tmp_path, root, manager)
    result = run(restarted.handle({"action": "stop", "project_root": str(root), "run_id": started["run_id"]}))

    assert result["cleanup_state"] == "completed"
    assert [kind for kind, _ in manager.calls].count("cleanup_persisted") == 1
    run(registry2.close())


def test_adapter_cleanup_uses_public_manager_and_rejects_wrong_project_or_session():
    manager = PublicManager()
    adapter = OlympusRuntimeAdapter(manager, project_id=PROJECT, enabled=True)
    logical_session = "kernel:project-a:run-a:task-a:1"
    session_id = adapter._kernel_session_id(logical_session)
    manager.sessions.add(session_id)
    with pytest.raises(Exception):
        run(
            adapter.cleanup_kernel(
                project_id="project-b",
                logical_session=logical_session,
                session_id=session_id,
                terminal_status="completed",
            )
        )
    with pytest.raises(Exception):
        run(
            adapter.cleanup_kernel(
                project_id=PROJECT,
                logical_session=logical_session,
                session_id="foreign-session",
                terminal_status="completed",
            )
        )
    assert manager.calls == []


def test_public_manager_cleanup_rejects_a_foreign_project_binding(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    manager = ACPManager.__new__(ACPManager)
    manager.sessions = {
        "session-a": SessionInfo("session-a", "worker", project_root=str(root)),
    }

    with pytest.raises(ValueError, match="project binding mismatch"):
        run(
            manager.cleanup_persisted(
                "session-a", terminal_status="completed", project_id="foreign-project"
            )
        )


def test_default_off_status_error_preserves_stable_contract_and_has_no_effect(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    manager = PublicManager()
    registry = _registry(tmp_path, manager)
    service = HarmoniaService(aether_home=tmp_path / "home", config=__import__("olympus_v3.config_loader", fromlist=["CoordinationConfig"]).CoordinationConfig(), registry=registry, discovered_workers={"worker"})
    result = run(service.handle({"action": "status", "project_root": str(root), "run_id": "run-" + "b" * 32}))

    assert result["error"]["code"] == "not_found"
    assert result["state"] is None
    assert "technical_status" not in result
    assert manager.calls == []


def test_repeated_unchanged_observations_persist_only_status_transitions(stack):
    _, ledger, _, dispatcher, envelope, effects = stack
    authority = envelope.authority
    run(dispatcher.dispatch_with(authority))
    effects.observations = [
        {"status": "working", "acp_session_id": "acp-session-1"},
        {"status": "working", "acp_session_id": "acp-session-1"},
        {"status": "completed", "acp_session_id": "acp-session-1"},
    ]

    observations = [run(dispatcher.observe_with(authority)) for _ in range(3)]

    assert [item.status for item in observations] == ["working", "working", "completed"]
    assert [item["status"] for item in event_payloads(ledger, "observation.accepted")] == [
        "working",
        "completed",
    ]


def test_public_state_projects_terminal_then_cleaned_without_duplicate_cleanup(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    manager = PublicManager()
    service, registry = _service(tmp_path, root, manager)

    async def scenario():
        started = await service.handle(_request(root))
        context = await registry.get_or_create(root)
        staged = next(event for event in context.ledger.events() if event["kind"] == "dispatch.staged")
        authority = context.dispatcher._envelope(json.loads(staged["payload"])).authority
        binding = event_payloads(context.ledger, "session.bound")[0]
        context.dispatcher.record_terminal_with(
            authority,
            TerminalObservation(
                "completed",
                authority.logical_session,
                binding["acp_session_id"],
                authority.message_id,
            ),
        )

        terminal = await service.handle(
            {"action": "status", "project_root": str(root), "run_id": started["run_id"]}
        )
        stopped = await service.handle(
            {"action": "stop", "project_root": str(root), "run_id": started["run_id"]}
        )
        replay = await service.handle(
            {"action": "stop", "project_root": str(root), "run_id": started["run_id"]}
        )

        assert terminal["state"] == "terminal_observed"
        assert terminal["technical_status"] == "completed"
        assert stopped["state"] == "cleaned"
        assert replay["state"] == "cleaned"
        assert len(event_payloads(context.ledger, "cleanup.requested")) == 1
        assert len(event_payloads(context.ledger, "cleanup.completed")) == 1
        await registry.close()

    run(scenario())


def assert_event_exists(ledger, kind):
    assert any(event["kind"] == kind for event in ledger.events())


def _registry(tmp_path, manager):
    from olympus_v3.coordination.harmonia_runtime import ProjectRuntimeRegistry, StaticCoordinationKeyProvider

    return ProjectRuntimeRegistry(tmp_path / "home", manager, StaticCoordinationKeyProvider(b"w" * 32, b"i" * 32))


def _service(tmp_path, root, manager):
    from olympus_v3.config_loader import CoordinationConfig

    registry = _registry(tmp_path, manager)
    config = CoordinationConfig(enabled=True, mode="legacy", allowed_modes=("legacy", "kernel-single-task"), project_allowlist=(str(root.resolve()),), max_active_runs=1)
    return HarmoniaService(aether_home=tmp_path / "home", config=config, registry=registry, discovered_workers={"hefesto"}), registry


def _request(root):
    return {
        "action": "start",
        "project_root": str(root),
        "request_id": "service-one",
        "contract": {
            "worker": "hefesto", "objective": "build", "expected_outcome": "verified",
            "included_scopes": ["src"], "excluded_scopes": [], "worker_permissions": ["implement"],
            "time_seconds": 60, "model_budget": 10, "qa_reserve": 1, "recovery_reserve": 1,
            "escalation_conditions": ["ambiguity"],
        },
        "plan_revision": 1,
        "snapshot_digest": "sha256:" + "a" * 64,
    }
