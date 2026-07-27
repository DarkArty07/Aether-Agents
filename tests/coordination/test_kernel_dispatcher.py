"""R11a RED contract for the ledger-native kernel dispatcher."""

from __future__ import annotations

import asyncio
import importlib
import inspect
import json
from dataclasses import dataclass
from pathlib import Path

import pytest

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
    WriterContext,
)
from olympus_v3.coordination.kernel_runtime import KernelRunService, KernelWriter

PROJECT = "project-a"
OWNER = Principal(PROJECT, "hermes", "owner")
WORKER = Principal(PROJECT, "hermes", "worker")


@dataclass
class FakeRuntimeAdapter:
    """Only fake at the ACP effect boundary; it owns no durable lifecycle state."""

    outcome: str = "accepted"

    def __post_init__(self):
        self.opens: list[dict] = []
        self.observations: list[dict] = []
        self.cancellations: list[dict] = []

    async def dispatch(self, **request):
        self.opens.append(request)
        if self.outcome == "pre_acceptance_failure":
            raise ConnectionError("transport refused before acceptance")
        if self.outcome == "accepted_response_lost":
            raise TimeoutError("response lost after acceptance")
        return {"accepted": True, "acp_session_id": "acp-session-1"}

    async def observe(self, **request):
        self.observations.append(request)
        return {"status": "accepted", "acp_session_id": "acp-session-1"}

    async def cancel(self, **request):
        self.cancellations.append(request)
        return {"accepted": True}


def async_test(awaitable):
    return asyncio.run(awaitable)


def dispatcher_api():
    try:
        module = importlib.import_module("olympus_v3.coordination.kernel_dispatcher")
    except ModuleNotFoundError as exc:
        pytest.fail(f"R11 RED: missing public dispatcher module/API: {exc.name}", pytrace=False)
    required = (
        "KernelDispatcher",
        "DispatchAuthority",
        "DispatchRejected",
        "StaleFence",
        "ReconciliationRequired",
        "ReconciliationEvidence",
    )
    missing = [name for name in required if not hasattr(module, name)]
    if missing:
        pytest.fail(f"R11 RED: missing dispatcher API: {', '.join(missing)}", pytrace=False)
    return module


def make_contract(task_worker_bindings=None, *, worker_permissions=("implement",)):
    participants = (OWNER, WORKER)
    if task_worker_bindings:
        participants = (OWNER, WORKER, *task_worker_bindings.values())
    return ExecutionContract(
        contract_id="contract-a",
        project_id=PROJECT,
        generation=0,
        owner=OWNER,
        participants=participants,
        objective="build",
        expected_outcome="verified",
        included_scopes=("src/",),
        excluded_scopes=("secrets/",),
        role_permissions={
            "worker": worker_permissions,
            **({principal.actor_id: ("implement",) for principal in task_worker_bindings.values()} if task_worker_bindings else {}),
        },
        evidence_gates=(EvidenceGate("qa", True),),
        side_effect_policy=SideEffectPolicy(("filesystem",), 2, True),
        limits=ContractLimits(2, 60, 3, 100, 1, 1),
        escalation_conditions=("ambiguity",),
        completion_authority=OWNER,
        amendment_authority=OWNER,
        task_worker_bindings=task_worker_bindings,
        status=ContractState.ACTIVE,
    )


@pytest.fixture
def kernel(tmp_path: Path):
    scope = StoreScope("install-a", PROJECT)
    auth = HMACWriterAuthenticator({("owner", "key-owner"): b"owner-key"})
    ledger = SQLiteLedger(
        tmp_path / "kernel.sqlite",
        scope,
        writer_authenticator=auth,
        integrity_signer=HMACIntegritySigner(b"integrity-key"),
    )
    lease = ledger.acquire_lease("ledger-owner", "owner", ttl=10_000_000_000).lease
    assert lease is not None
    context = WriterContext(scope, "owner", "key-owner", "ledger-owner", lease.epoch, lease.expires_at)
    assert ledger.create_contract(make_contract()) in (Result.APPLIED, Result.DUPLICATE)
    service = KernelRunService(ledger, writer=KernelWriter(context, auth))
    service.create_run(run_id="run-a", contract_id="contract-a", mode="kernel")
    service.create_task("run-a", task_id="task-a")
    service.admit_task("run-a", "task-a")
    service.mark_task_ready("run-a", "task-a")
    service.dispatch_task("run-a", "task-a")
    attempt = service.start_attempt("run-a", "task-a")
    before = ledger.conn.execute("SELECT COUNT(*) FROM outbox").fetchone()[0]
    yield ledger, service, attempt, before
    ledger.close()


@pytest.fixture
def response_kernel(tmp_path: Path):
    scope = StoreScope("install-a", PROJECT)
    auth = HMACWriterAuthenticator({("owner", "key-owner"): b"owner-key"})
    ledger = SQLiteLedger(
        tmp_path / "response-kernel.sqlite",
        scope,
        writer_authenticator=auth,
        integrity_signer=HMACIntegritySigner(b"integrity-key"),
    )
    lease = ledger.acquire_lease("ledger-owner", "owner", ttl=10_000_000_000).lease
    assert lease is not None
    context = WriterContext(scope, "owner", "key-owner", "ledger-owner", lease.epoch, lease.expires_at)
    assert ledger.create_contract(
        make_contract(worker_permissions=("read", "verify", "return_evidence"))
    ) in (Result.APPLIED, Result.DUPLICATE)
    service = KernelRunService(ledger, writer=KernelWriter(context, auth))
    service.create_run(run_id="run-a", contract_id="contract-a", mode="kernel")
    service.create_task("run-a", task_id="task-a")
    service.admit_task("run-a", "task-a")
    service.mark_task_ready("run-a", "task-a")
    service.dispatch_task("run-a", "task-a")
    attempt = service.start_attempt("run-a", "task-a")
    project_root = tmp_path / "project"
    project_root.mkdir()
    yield ledger, service, attempt, project_root
    ledger.close()


def dispatcher(kernel, adapter=None, worker_id=None):
    module = dispatcher_api()
    ledger, service, _, _ = kernel
    return module.KernelDispatcher(
        ledger=ledger,
        runtime=service,
        runtime_adapter=adapter or FakeRuntimeAdapter(),
        worker_id=worker_id,
    )


@pytest.fixture
def fixed_kernel(tmp_path: Path):
    scope = StoreScope("install-a", PROJECT)
    auth = HMACWriterAuthenticator({("owner", "key-owner"): b"owner-key"})
    ledger = SQLiteLedger(tmp_path / "fixed-kernel.sqlite", scope, writer_authenticator=auth, integrity_signer=HMACIntegritySigner(b"integrity-key"))
    lease = ledger.acquire_lease("ledger-owner", "owner", ttl=10_000_000_000).lease
    assert lease is not None
    context = WriterContext(scope, "owner", "key-owner", "ledger-owner", lease.epoch, lease.expires_at)
    worker_a = Principal(PROJECT, "hermes", "worker-a")
    worker_b = Principal(PROJECT, "hermes", "worker-b")
    assert ledger.create_contract(make_contract({"task-a": worker_a, "task-b": worker_b})) in (Result.APPLIED, Result.DUPLICATE)
    service = KernelRunService(ledger, writer=KernelWriter(context, auth))
    service.create_run(run_id="run-fixed", contract_id="contract-a", mode="kernel")
    for task_id in ("task-a", "task-b"):
        service.create_task("run-fixed", task_id=task_id)
        service.admit_task("run-fixed", task_id)
        service.mark_task_ready("run-fixed", task_id)
        service.dispatch_task("run-fixed", task_id)
        service.start_attempt("run-fixed", task_id)
    yield ledger, service
    ledger.close()


def stage(d, attempt=1):
    return d.stage_ready(
        "run-a",
        "task-a",
        attempt=attempt,
        project_root="/workspace/project",
        plan_revision=7,
        snapshot_digest="sha256:snapshot",
    )


def test_fixed_contract_dispatches_each_task_to_its_exact_bound_principal(fixed_kernel):
    ledger, service = fixed_kernel
    d = dispatcher((ledger, service, None, 0))
    first = d.stage_ready("run-fixed", "task-a", attempt=1, project_root="/workspace/project", plan_revision=1, snapshot_digest="sha256:a")
    second = d.stage_ready("run-fixed", "task-b", attempt=1, project_root="/workspace/project", plan_revision=1, snapshot_digest="sha256:b")

    assert first.authority.agent_name == "worker-a"
    assert second.authority.agent_name == "worker-b"
    with pytest.raises(TypeError, match="worker_id"):
        d.stage_ready("run-fixed", "task-a", attempt=1, project_root="/workspace/project", plan_revision=1, snapshot_digest="sha256:c", worker_id="worker-b")


def test_fixed_contract_rejects_dispatch_for_unbound_task(fixed_kernel):
    ledger, service = fixed_kernel
    service.create_task("run-fixed", task_id="task-c")
    service.admit_task("run-fixed", "task-c")
    service.mark_task_ready("run-fixed", "task-c")
    service.dispatch_task("run-fixed", "task-c")
    service.start_attempt("run-fixed", "task-c")

    with pytest.raises(dispatcher_api().DispatchRejected, match="binding required"):
        dispatcher((ledger, service, None, 0)).stage_ready(
            "run-fixed",
            "task-c",
            attempt=1,
            project_root="/workspace/project",
            plan_revision=1,
            snapshot_digest="sha256:c",
        )


def dispatch_row(ledger):
    staged = {event["event_id"] for event in ledger.events() if event["kind"] == "dispatch.staged"}
    return next(row for row in ledger.outbox() if row["event_id"] in staged)


def test_complete_outbox_is_ledger_method_and_fail_closed(kernel):
    ledger, _, _, _ = kernel
    assert ledger.complete_outbox("missing-message", "completion") is Result.INVALID_INPUT
    module = dispatcher_api()
    assert not hasattr(module, "complete_outbox")


def test_staging_is_durable_before_effect(kernel):
    ledger, _, attempt, before = kernel
    adapter = FakeRuntimeAdapter()
    d = dispatcher(kernel, adapter)
    stage(d, attempt.attempt)
    assert ledger.conn.execute("SELECT COUNT(*) FROM outbox").fetchone()[0] == before + 1
    assert any(e["kind"] == "dispatch.staged" for e in ledger.events())
    assert adapter.opens == []


def test_dispatch_is_async_and_binds_session(kernel):
    ledger, _, attempt, _ = kernel
    adapter = FakeRuntimeAdapter()
    d = dispatcher(kernel, adapter)
    envelope = stage(d, attempt.attempt)
    async_test(d.dispatch_once())
    assert adapter.opens
    assert ledger.conn.execute("SELECT COUNT(*) FROM events WHERE kind='session.bound'").fetchone()[0] == 1
    assert envelope.authority.attempt == attempt.attempt


def test_ack_is_sync_and_does_not_complete_task(kernel):
    ledger, service, attempt, _ = kernel
    d = dispatcher(kernel)
    stage(d, attempt.attempt)
    async_test(d.dispatch_once())
    d.ack_once()
    row = dispatch_row(ledger)
    assert row["semantic_completion_event_id"] is None
    assert service.task("run-a", "task-a").state.value == "running"


def test_authority_binds_explicit_plan_inputs_and_immutable_fields(kernel):
    ledger, _, attempt, _ = kernel
    d = dispatcher(kernel)
    envelope = stage(d, attempt.attempt)
    authority = envelope.authority
    assert (authority.run_id, authority.task_id, authority.attempt) == ("run-a", "task-a", attempt.attempt)
    assert authority.plan_revision == 7 and authority.snapshot_digest == "sha256:snapshot"
    assert authority.plan_id
    assert authority.contract_id == "contract-a" and authority.contract_generation == 0
    assert authority.project_root == "/workspace/project"
    assert authority.logical_session.startswith("kernel:")
    assert len(authority.logical_session) == 71
    assert dispatch_row(ledger)["contract_id"] == "contract-a"


def test_duplicate_stage_reuses_one_intent_and_one_binding(kernel):
    ledger, _, attempt, _ = kernel
    adapter = FakeRuntimeAdapter()
    d = dispatcher(kernel, adapter)
    first, second = stage(d, attempt.attempt), stage(d, attempt.attempt)
    assert first.message_id == second.message_id
    async_test(d.dispatch_once())
    async_test(d.dispatch_once())
    assert len([e for e in ledger.events() if e["kind"] == "dispatch.staged"]) == 1
    assert len(adapter.opens) == 1
    assert len([e for e in ledger.events() if e["kind"] == "session.bound"]) == 1


def test_accepted_but_response_lost_is_durable_unknown(kernel):
    ledger, _, attempt, _ = kernel
    d = dispatcher(kernel, FakeRuntimeAdapter("accepted_response_lost"))
    stage(d, attempt.attempt)
    async_test(d.dispatch_once())
    row = dispatch_row(ledger)
    assert row["status"] == "UNKNOWN" and row["reconciliation_required"] == 1
    assert any(e["kind"] == "dispatch.unknown" for e in ledger.events())


def test_unknown_blocks_retry_with_public_reconciliation_exception(kernel):
    ledger, _, attempt, _ = kernel
    d = dispatcher(kernel, FakeRuntimeAdapter("accepted_response_lost"))
    stage(d, attempt.attempt)
    async_test(d.dispatch_once())
    with pytest.raises(dispatcher_api().ReconciliationRequired):
        async_test(d.dispatch_once())
    assert dispatch_row(ledger)["status"] == "UNKNOWN"


def test_pre_acceptance_failure_is_retryable_not_unknown(kernel):
    ledger, _, attempt, _ = kernel
    d = dispatcher(kernel, FakeRuntimeAdapter("pre_acceptance_failure"))
    stage(d, attempt.attempt)
    async_test(d.dispatch_once())
    row = dispatch_row(ledger)
    assert row["status"] in {"RETRY_WAIT", "PENDING"} and row["reconciliation_required"] == 0


def test_restart_uses_fresh_writable_facade_and_preserves_uncertainty(kernel):
    ledger, service, attempt, _ = kernel
    first = dispatcher(kernel, FakeRuntimeAdapter("accepted_response_lost"))
    stage(first, attempt.attempt)
    first.claim_once()
    restarted = KernelRunService(ledger, writer=service.writer)
    second = dispatcher((ledger, restarted, attempt, 0), FakeRuntimeAdapter("accepted_response_lost"))
    async_test(second.dispatch_once())
    assert dispatch_row(ledger)["status"] == "UNKNOWN"


def test_reconciliation_requires_typed_evidence_bound_to_authority(kernel):
    module = dispatcher_api()
    ledger, _, attempt, _ = kernel
    d = dispatcher(kernel, FakeRuntimeAdapter("accepted_response_lost"))
    envelope = stage(d, attempt.attempt)
    async_test(d.dispatch_once())
    with pytest.raises(module.ReconciliationRequired):
        d.reconcile_unknown("run-a", "task-a", attempt=attempt.attempt, evidence=None)
    evidence = module.ReconciliationEvidence(authority=envelope.authority, observation="no-effect")
    assert d.reconcile_unknown("run-a", "task-a", attempt=attempt.attempt, evidence=evidence)
    assert dispatch_row(ledger)["reconciliation_required"] == 0


def test_public_surface_has_runtime_adapter_not_acp_manager(kernel):
    module = dispatcher_api()
    signature = inspect.signature(module.KernelDispatcher)
    assert {"ledger", "runtime", "runtime_adapter"} <= set(signature.parameters)
    package = importlib.import_module("olympus_v3.coordination")
    assert package.KernelDispatcher is module.KernelDispatcher
    assert package.DispatchAuthority is module.DispatchAuthority


def test_static_scope_excludes_legacy_export_and_scans_only_kernel_paths():
    dispatcher_api()
    root = Path(__file__).parents[2] / "src/olympus_v3/coordination"
    paths = (root / "kernel_dispatcher.py", root / "kernel_runtime.py")
    assert all("pilotstore" not in path.read_text().lower() for path in paths if path.exists())


def test_dispatcher_does_not_bypass_ledger_public_api():
    module = dispatcher_api()
    source = inspect.getsource(module.KernelDispatcher)
    assert ".conn" not in source


def test_attempt_fence_is_not_the_shared_transport_lease(kernel):
    ledger, _, attempt, _ = kernel
    envelope = stage(dispatcher(kernel), attempt.attempt)
    authority = envelope.authority
    assert authority.lease_resource == f"dispatch:run-a:task-a:{attempt.attempt}"
    assert authority.lease_resource != "outbox"
    assert ledger.check_lease(authority.as_lease(), authority.lease_owner).lease is not None


def test_kernel_outbox_does_not_hide_existing_durable_rows(kernel):
    ledger, _, attempt, before = kernel
    envelope = stage(dispatcher(kernel), attempt.attempt)
    assert len(ledger.outbox()) == before + 1
    assert ledger.outbox_message(envelope.message_id)["event_id"]


def test_effect_accepted_then_binding_write_failure_becomes_unknown(kernel):
    ledger, _, attempt, _ = kernel
    d = dispatcher(kernel, FakeRuntimeAdapter())
    envelope = stage(d, attempt.attempt)
    failures = [0]

    def fail_once(point):
        if point == "after_event_insert" and failures[0] == 0:
            failures[0] += 1
            raise RuntimeError("binding persistence failed after ACP acceptance")

    ledger.fault = fail_once
    async_test(d.dispatch_once())
    ledger.fault = None
    assert ledger.outbox_message(envelope.message_id)["status"] == "UNKNOWN"
    assert any(e["kind"] == "dispatch.unknown" for e in ledger.events())


def test_unknown_dispatch_does_not_block_independent_ready_task(kernel):
    ledger, service, attempt_a, _ = kernel
    adapter = FakeRuntimeAdapter("accepted_response_lost")
    d = dispatcher(kernel, adapter)
    envelope_a = stage(d, attempt_a.attempt)
    async_test(d.dispatch_once())
    assert ledger.outbox_message(envelope_a.message_id)["status"] == "UNKNOWN"

    service.create_task("run-a", task_id="task-b")
    service.admit_task("run-a", "task-b")
    service.mark_task_ready("run-a", "task-b")
    service.dispatch_task("run-a", "task-b")
    attempt_b = service.start_attempt("run-a", "task-b")
    envelope_b = d.stage_ready(
        "run-a",
        "task-b",
        attempt=attempt_b.attempt,
        project_root="/workspace/project",
        plan_revision=7,
        snapshot_digest="sha256:snapshot-b",
    )
    adapter.outcome = "accepted"
    async_test(d.dispatch_once())
    assert ledger.outbox_message(envelope_b.message_id)["status"] in {"LEASED", "SENT"}
    assert any(
        binding.logical_session == envelope_b.authority.logical_session
        for binding in service.sessions("run-a", "task-b")
    )


def test_future_retry_wait_does_not_block_independent_ready_task(kernel):
    ledger, service, attempt_a, _ = kernel
    adapter = FakeRuntimeAdapter("pre_acceptance_failure")
    d = dispatcher(kernel, adapter)
    envelope_a = stage(d, attempt_a.attempt)
    async_test(d.dispatch_once())
    assert ledger.outbox_message(envelope_a.message_id)["status"] == "RETRY_WAIT"

    service.create_task("run-a", task_id="task-b")
    service.admit_task("run-a", "task-b")
    service.mark_task_ready("run-a", "task-b")
    service.dispatch_task("run-a", "task-b")
    attempt_b = service.start_attempt("run-a", "task-b")
    envelope_b = d.stage_ready(
        "run-a",
        "task-b",
        attempt=attempt_b.attempt,
        project_root="/workspace/project",
        plan_revision=7,
        snapshot_digest="sha256:snapshot-b",
    )
    adapter.outcome = "accepted"

    async_test(d.dispatch_once())

    assert ledger.outbox_message(envelope_a.message_id)["status"] == "RETRY_WAIT"
    assert ledger.outbox_message(envelope_b.message_id)["status"] in {"LEASED", "SENT"}
    assert any(
        binding.logical_session == envelope_b.authority.logical_session
        for binding in service.sessions("run-a", "task-b")
    )
    assert len(adapter.opens) == 2


def test_kernel_prompt_is_canonical_contractual_and_contains_no_capabilities(kernel):
    adapter = FakeRuntimeAdapter()
    d = dispatcher(kernel, adapter)
    envelope = stage(d, kernel[2].attempt)

    async_test(d.dispatch_once())

    request = adapter.opens[0]
    prompt = json.loads(request["prompt"])
    assert set(prompt) == {
        "acceptance_evidence",
        "authority",
        "contract",
        "instructions",
        "kind",
        "result_artifact",
        "task",
    }
    assert prompt["kind"] == "aether.harmonia.task.v1"
    assert prompt["authority"] == {
        "attempt": envelope.authority.attempt,
        "contract_generation": 0,
        "contract_id": "contract-a",
        "message_id": envelope.authority.message_id,
        "plan_id": envelope.authority.plan_id,
        "plan_revision": 7,
        "project_id": PROJECT,
        "run_id": "run-a",
        "snapshot_digest": "sha256:snapshot",
        "task_id": "task-a",
    }
    assert prompt["contract"] == {
        "escalation_conditions": ["ambiguity"],
        "excluded_scopes": ["secrets/"],
        "expected_outcome": "verified",
        "included_scopes": ["src/"],
        "limits": {
            "max_parallel_tasks": 2,
            "max_retries": 3,
            "max_runtime_seconds": 60,
            "model_budget": 100,
            "network_budget": 1,
            "tool_budget": 1,
        },
        "objective": "build",
        "role_permissions": ["implement"],
        "side_effect_policy": {
            "allowed_effects": ["filesystem"],
            "approval_threshold": 2,
            "rollback_required": True,
        },
        "worker_id": "worker",
    }
    assert prompt["task"] == {
        "attempt": 1,
        "project_root": envelope.authority.project_root,
        "task_id": "task-a",
    }
    artifact = prompt["result_artifact"]
    assert artifact["delivery"] == "worker_file"
    assert artifact["relative_path"] == ".aether/evidence/run-a/task-a/1/result.json"
    assert artifact["write_before_completion"] is True
    assert artifact["document"]["schema"] == "AETHER_TASK_RESULT_V1"
    assert artifact["document"]["run_id"] == "run-a"
    assert artifact["document"]["task_id"] == "task-a"
    assert artifact["document"]["artifact_generation"] == 1
    assert artifact["document"]["acp_session_id"]
    assert artifact["document"]["result"] == {"answer": "REPLACE_WITH_TASK_RESULT"}
    assert prompt["acceptance_evidence"] == [{"name": "qa", "required": True, "state": "pending"}]
    assert prompt["instructions"] == [
        "Do not delegate.",
        "Do not widen scope.",
        "Do not modify the contract.",
        "Do not claim completion without evidence.",
        "Before reporting completion, atomically write result_artifact.document to result_artifact.relative_path and replace only its result value with the bounded task output.",
        "Report blockers and stop when authority is insufficient.",
    ]
    assert request["prompt_digest"].startswith("sha256:")
    assert len(request["prompt_digest"]) == 71
    serialized = request["prompt"]
    assert envelope.authority.lease_token not in serialized
    assert "owner-key" not in serialized
    assert "integrity-key" not in serialized


def test_read_only_worker_returns_json_and_kernel_materializes_evidence(response_kernel):
    ledger, service, attempt, project_root = response_kernel
    adapter = FakeRuntimeAdapter()
    d = dispatcher((ledger, service, attempt, 0), adapter)
    envelope = d.stage_ready(
        "run-a",
        "task-a",
        attempt=attempt.attempt,
        project_root=str(project_root),
        plan_revision=7,
        snapshot_digest="sha256:snapshot",
    )

    async_test(d.dispatch_once())
    prompt = json.loads(adapter.opens[0]["prompt"])
    assert prompt["result_artifact"]["delivery"] == "acp_response"
    assert prompt["result_artifact"]["write_before_completion"] is False
    assert "do not use markdown" in prompt["instructions"][4]

    observation = type(
        "TerminalObservation",
        (),
        {
            "status": "completed",
            "logical_session": envelope.authority.logical_session,
            "acp_session_id": "acp-session-1",
            "message_id": envelope.authority.message_id,
        },
    )()
    d.record_terminal_with(envelope.authority, observation)
    with pytest.raises(dispatcher_api().DispatchRejected, match="invalid structured ACP result"):
        d.materialize_response_result_with(
            envelope.authority,
            {"progress": {"last_turn": '{"answer":"ok","answer":"conflict"}'}},
        )

    d.materialize_response_result_with(
        envelope.authority,
        {"progress": {"last_turn": '{"answer":"B_VERIFIED","source_sha256":"sha256:source"}'}},
    )
    result_path = project_root / ".aether/evidence/run-a/task-a/1/result.json"
    document = json.loads(result_path.read_text())
    assert document["acp_session_id"] == "acp-session-1"
    assert document["result"] == {"answer": "B_VERIFIED", "source_sha256": "sha256:source"}
    assert d.record_evidence_with(envelope.authority) is Result.APPLIED


def test_real_adapter_rejects_tampered_prompt_before_any_acp_operation(kernel):
    from olympus_v3.coordination.olympus_adapter import OlympusRuntimeAdapter
    from olympus_v3.coordination.protocol import ValidationError

    class Manager:
        def __init__(self):
            self.calls = []

        async def spawn_agent(self, **kwargs):
            self.calls.append(("spawn", kwargs))
            return kwargs["session_id"]

        async def send_message(self, *args):
            self.calls.append(("send", args))

        async def poll(self, session_id):
            return {"status": "working", "session_id": session_id}

        async def close(self, *args, **kwargs):
            self.calls.append(("close", args, kwargs))

    manager = Manager()
    real = OlympusRuntimeAdapter(manager, project_id=PROJECT, enabled=True)

    class TamperingAdapter:
        async def dispatch_kernel(self, *, authority, request):
            tampered = dict(request)
            prompt = json.loads(tampered["prompt"])
            prompt["authority"]["plan_revision"] += 1
            tampered["prompt"] = json.dumps(prompt, sort_keys=True, separators=(",", ":"))
            return await real.dispatch_kernel(authority=authority, request=tampered)

    d = dispatcher(kernel, TamperingAdapter())
    stage(d, kernel[2].attempt)

    with pytest.raises(ValidationError, match="invalid kernel dispatch authority"):
        async_test(d.dispatch_once())

    assert manager.calls == []


def test_olympus_adapter_exposes_authoritative_kernel_seam():
    from olympus_v3.coordination.olympus_adapter import OlympusRuntimeAdapter

    assert inspect.iscoroutinefunction(OlympusRuntimeAdapter.dispatch_kernel)
    assert inspect.iscoroutinefunction(OlympusRuntimeAdapter.observe_kernel)
    assert inspect.iscoroutinefunction(OlympusRuntimeAdapter.cancel_kernel)


def test_real_olympus_adapter_owns_dispatch_observe_and_cancel_effects(kernel):
    from olympus_v3.coordination.olympus_adapter import OlympusRuntimeAdapter

    class PublicManager:
        def __init__(self):
            self.spawned = []
            self.sent = []
            self.closed = []

        async def spawn_agent(self, *, agent_name, session_id, project_root):
            self.spawned.append((agent_name, session_id, project_root))
            return session_id

        async def send_message(self, session_id, prompt):
            self.sent.append((session_id, prompt))

        async def poll(self, session_id):
            return {"status": "working", "session_id": session_id}

        async def close(self, session_id, *, terminal_status):
            self.closed.append((session_id, terminal_status))

    manager = PublicManager()
    adapter = OlympusRuntimeAdapter(manager, project_id=PROJECT, enabled=True)
    d = dispatcher(kernel, adapter)
    envelope = stage(d, kernel[2].attempt)
    response = async_test(d.dispatch_once())
    assert response["accepted"] is True
    assert manager.spawned[0][0] == "worker"
    assert manager.sent and "aether.harmonia.task.v1" in manager.sent[0][1]
    observation = async_test(d.observe_once("run-a", "task-a", attempt=kernel[2].attempt))
    assert observation.status == "working"
    d.cancel("run-a", "task-a", attempt=kernel[2].attempt)
    async_test(d.deliver_cancel_once("run-a", "task-a", attempt=kernel[2].attempt))
    assert manager.closed[0][1] == "cancelled"
    assert any(event["kind"] == "cancel.intent" for event in kernel[0].events())
    assert envelope.authority.logical_session


@pytest.mark.parametrize(
    ("kind", "aggregate", "payload", "message_id"),
    (
        ("dispatch.staged", "dispatch:forged", {"run_id": "run-a"}, "forged-stage"),
        (
            "dispatch.unknown",
            "dispatch:forged",
            {
                "run_id": "run-a",
                "task_id": "task-a",
                "attempt": 1,
                "contract_id": "contract-a",
                "message_id": "forged-stage",
                "reason": "forged",
            },
            None,
        ),
        (
            "session.bound",
            "task:run-a:task-a",
            {
                "run_id": "run-a",
                "task_id": "task-a",
                "logical_session": "forged",
                "contract_id": "contract-a",
                "unexpected": True,
            },
            None,
        ),
    ),
)
def test_generic_append_cannot_forge_r11_authority_events(kernel, kind, aggregate, payload, message_id):
    ledger, service, _, _ = kernel
    context = service.writer.context
    draft = ledger.draft(
        aggregate,
        kind,
        payload,
        writer=context,
        expected_version=ledger.aggregate_version(aggregate),
        contract_generation=0,
        revocation_epoch=0,
    )
    signed = service.writer.authenticator.sign(draft, context)
    assert ledger.append(signed, context, message_id=message_id).status is Result.INVALID_INPUT


def test_unknown_transition_rolls_back_as_one_durable_unit(kernel):
    ledger, _, attempt, _ = kernel
    d = dispatcher(kernel, FakeRuntimeAdapter("accepted_response_lost"), worker_id="worker-a")
    envelope = stage(d, attempt.attempt)
    failures = [0]

    def fail_once(point):
        if point == "after_unknown_event" and failures[0] == 0:
            failures[0] += 1
            raise RuntimeError("crash after unknown event")

    ledger.fault = fail_once
    with pytest.raises(RuntimeError, match="crash after unknown event"):
        async_test(d.dispatch_once())
    ledger.fault = None
    row = ledger.outbox_message(envelope.message_id)
    events = [e for e in ledger.events() if e["kind"] == "dispatch.unknown"]
    assert (row["status"], row["reconciliation_required"], bool(events)) != ("UNKNOWN", 1, False)


def test_post_acceptance_unknown_write_fault_never_replays_the_effect(kernel):
    ledger, _, attempt, _ = kernel
    adapter = FakeRuntimeAdapter("accepted_response_lost")
    d = dispatcher(kernel, adapter, worker_id="worker-a")
    envelope = stage(d, attempt.attempt)
    failures = [0]

    def fail_once(point):
        if point == "after_unknown_event" and failures[0] == 0:
            failures[0] += 1
            raise RuntimeError("crash after accepted effect before UNKNOWN commit")

    ledger.fault = fail_once
    with pytest.raises(RuntimeError, match="UNKNOWN commit"):
        async_test(d.dispatch_once())
    ledger.fault = None

    # The first runtime call may already have been accepted.  Recovery must
    # conservatively materialize UNKNOWN without attempting a second effect.
    async_test(d.dispatch_once())
    row = ledger.outbox_message(envelope.message_id)
    assert len(adapter.opens) == 1
    assert row["status"] == "UNKNOWN" and row["reconciliation_required"] == 1
    assert any(
        event["kind"] == "dispatch.unknown"
        and json.loads(event["payload"])["message_id"] == envelope.message_id
        for event in ledger.events()
    )


def test_dispatcher_worker_identity_is_not_shared_and_expiry_allows_new_epoch(kernel):
    ledger, _, attempt, now = kernel
    first = dispatcher(kernel, worker_id="worker-a")
    second = dispatcher(kernel, worker_id="worker-b")
    original = stage(first, attempt.attempt)
    assert original.authority.lease_owner == "worker-a"
    with pytest.raises(dispatcher_api().StaleFence):
        second.claim_with(original.authority)
    ledger.clock = lambda: original.authority.lease_until + 1
    replacement = ledger.acquire_lease(original.authority.lease_resource, "worker-b", ttl=10).lease
    assert replacement is not None
    assert replacement.owner == "worker-b"
    assert replacement.epoch > original.authority.lease_epoch


def test_second_sqlite_worker_fences_stale_owner_after_takeover(kernel, tmp_path):
    ledger, service, attempt, _ = kernel
    first = dispatcher(kernel, worker_id="worker-a")
    original = stage(first, attempt.attempt)
    other = SQLiteLedger(
        tmp_path / "kernel.sqlite",
        ledger.scope,
        writer_authenticator=ledger.writer_authenticator,
        integrity_signer=ledger.integrity_signer,
    )
    try:
        second_runtime = KernelRunService(other, writer=service.writer)
        second = dispatcher((other, second_runtime, attempt, 0), worker_id="worker-b")
        with pytest.raises(dispatcher_api().StaleFence):
            second.claim_with(original.authority)

        advanced = original.authority.lease_until + 1
        ledger.clock = lambda: advanced
        other.clock = lambda: advanced
        replacement = other.acquire_lease(original.authority.lease_resource, "worker-b", ttl=10).lease
        assert replacement is not None and replacement.epoch > original.authority.lease_epoch
        with pytest.raises(dispatcher_api().StaleFence):
            first.acknowledge(original.authority)
    finally:
        other.close()


def test_unknown_recovery_survives_fresh_ledger_and_dispatcher(kernel, tmp_path):
    ledger, service, attempt, _ = kernel
    first = dispatcher(kernel, FakeRuntimeAdapter("accepted_response_lost"), worker_id="worker-a")
    envelope = stage(first, attempt.attempt)
    async_test(first.dispatch_once())
    reopened = SQLiteLedger(
        tmp_path / "kernel.sqlite",
        ledger.scope,
        writer_authenticator=ledger.writer_authenticator,
        integrity_signer=ledger.integrity_signer,
    )
    restarted = KernelRunService(reopened, writer=service.writer)
    second = dispatcher((reopened, restarted, attempt, 0), worker_id="worker-a")
    with pytest.raises(dispatcher_api().ReconciliationRequired):
        async_test(second.dispatch_once())
    row = reopened.outbox_message(envelope.message_id)
    assert row["status"] == "UNKNOWN" and row["reconciliation_required"] == 1
    assert any(
        json.loads(event["payload"]).get("message_id") == envelope.message_id
        for event in reopened.events()
        if event["kind"] == "dispatch.unknown"
    )
    reopened.close()
