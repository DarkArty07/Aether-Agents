"""R11a RED contract for the ledger-native kernel dispatcher."""
from __future__ import annotations

import asyncio
import importlib
import inspect
from dataclasses import dataclass
from pathlib import Path

import pytest

from olympus_v3.coordination import (
    ContractLimits, ContractState, EvidenceGate, ExecutionContract,
    HMACIntegritySigner, HMACWriterAuthenticator, Principal, Result,
    SideEffectPolicy, SQLiteLedger, StoreScope, WriterContext,
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
    required = ("KernelDispatcher", "DispatchAuthority", "DispatchRejected", "StaleFence", "ReconciliationRequired", "ReconciliationEvidence")
    missing = [name for name in required if not hasattr(module, name)]
    if missing:
        pytest.fail(f"R11 RED: missing dispatcher API: {', '.join(missing)}", pytrace=False)
    return module


def make_contract():
    return ExecutionContract(
        contract_id="contract-a", project_id=PROJECT, generation=0, owner=OWNER,
        participants=(OWNER, WORKER), objective="build", expected_outcome="verified",
        included_scopes=("src/",), excluded_scopes=("secrets/",), role_permissions={"worker": ("implement",)},
        evidence_gates=(EvidenceGate("qa", True),), side_effect_policy=SideEffectPolicy(("filesystem",), 2, True),
        limits=ContractLimits(2, 60, 3, 100, 1, 1), escalation_conditions=("ambiguity",),
        completion_authority=OWNER, amendment_authority=OWNER, status=ContractState.ACTIVE,
    )


@pytest.fixture
def kernel(tmp_path: Path):
    scope = StoreScope("install-a", PROJECT)
    auth = HMACWriterAuthenticator({("owner", "key-owner"): b"owner-key"})
    ledger = SQLiteLedger(tmp_path / "kernel.sqlite", scope, writer_authenticator=auth, integrity_signer=HMACIntegritySigner(b"integrity-key"))
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


def dispatcher(kernel, adapter=None):
    module = dispatcher_api()
    ledger, service, _, _ = kernel
    return module.KernelDispatcher(ledger=ledger, runtime=service, runtime_adapter=adapter or FakeRuntimeAdapter())


def stage(d, attempt=1):
    return d.stage_ready("run-a", "task-a", attempt=attempt, project_root="/workspace/project", plan_revision=7, snapshot_digest="sha256:snapshot")


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
    row = ledger.outbox()[0]
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
    assert authority.logical_session == f"kernel:{PROJECT}:run-a:task-a:{attempt.attempt}"
    assert ledger.outbox()[0]["contract_id"] == "contract-a"


def test_duplicate_stage_reuses_one_intent_and_one_binding(kernel):
    ledger, _, attempt, _ = kernel
    adapter = FakeRuntimeAdapter()
    d = dispatcher(kernel, adapter)
    first, second = stage(d, attempt.attempt), stage(d, attempt.attempt)
    assert first.message_id == second.message_id
    async_test(d.dispatch_once()); async_test(d.dispatch_once())
    assert len(ledger.outbox()) == 1 and len(adapter.opens) == 1
    assert len([e for e in ledger.events() if e["kind"] == "session.bound"]) == 1


def test_accepted_but_response_lost_is_durable_unknown(kernel):
    ledger, _, attempt, _ = kernel
    d = dispatcher(kernel, FakeRuntimeAdapter("accepted_response_lost"))
    stage(d, attempt.attempt); async_test(d.dispatch_once())
    row = ledger.outbox()[0]
    assert row["status"] == "UNKNOWN" and row["reconciliation_required"] == 1
    assert any(e["kind"] == "dispatch.unknown" for e in ledger.events())


def test_unknown_blocks_retry_with_public_reconciliation_exception(kernel):
    ledger, _, attempt, _ = kernel
    d = dispatcher(kernel, FakeRuntimeAdapter("accepted_response_lost"))
    stage(d, attempt.attempt); async_test(d.dispatch_once())
    with pytest.raises(dispatcher_api().ReconciliationRequired):
        async_test(d.dispatch_once())
    assert ledger.outbox()[0]["status"] == "UNKNOWN"


def test_pre_acceptance_failure_is_retryable_not_unknown(kernel):
    ledger, _, attempt, _ = kernel
    d = dispatcher(kernel, FakeRuntimeAdapter("pre_acceptance_failure"))
    stage(d, attempt.attempt); async_test(d.dispatch_once())
    row = ledger.outbox()[0]
    assert row["status"] in {"RETRY_WAIT", "PENDING"} and row["reconciliation_required"] == 0


def test_restart_uses_fresh_writable_facade_and_preserves_uncertainty(kernel):
    ledger, service, attempt, _ = kernel
    first = dispatcher(kernel, FakeRuntimeAdapter("accepted_response_lost"))
    stage(first, attempt.attempt); first.claim_once()
    restarted = KernelRunService(ledger, writer=service.writer)
    second = dispatcher((ledger, restarted, attempt, 0), FakeRuntimeAdapter("accepted_response_lost"))
    async_test(second.dispatch_once())
    assert ledger.outbox()[0]["status"] == "UNKNOWN"


def test_reconciliation_requires_typed_evidence_bound_to_authority(kernel):
    module = dispatcher_api()
    ledger, _, attempt, _ = kernel
    d = dispatcher(kernel, FakeRuntimeAdapter("accepted_response_lost"))
    envelope = stage(d, attempt.attempt); async_test(d.dispatch_once())
    with pytest.raises(module.ReconciliationRequired):
        d.reconcile_unknown("run-a", "task-a", attempt=attempt.attempt, evidence=None)
    evidence = module.ReconciliationEvidence(authority=envelope.authority, observation="no-effect")
    assert d.reconcile_unknown("run-a", "task-a", attempt=attempt.attempt, evidence=evidence)
    assert ledger.outbox()[0]["reconciliation_required"] == 0


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
