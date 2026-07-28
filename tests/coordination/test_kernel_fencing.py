"""R11a RED adversarial contract for lease/fence-bound dispatch."""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest
from test_kernel_dispatcher import FakeRuntimeAdapter, async_test, dispatch_row

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


def dispatcher_api():
    try:
        module = importlib.import_module("olympus_v3.coordination.kernel_dispatcher")
    except ModuleNotFoundError as exc:
        pytest.fail(f"R11 RED: missing public fencing API: {exc.name}", pytrace=False)
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
        pytest.fail(f"R11 RED: missing fencing API: {', '.join(missing)}", pytrace=False)
    return module


def contract():
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
def kernel(tmp_path: Path):
    now = [100]
    scope = StoreScope("install-a", PROJECT)
    auth = HMACWriterAuthenticator({("owner", "key-owner"): b"owner-key"})
    ledger = SQLiteLedger(
        tmp_path / "fencing.sqlite",
        scope,
        writer_authenticator=auth,
        integrity_signer=HMACIntegritySigner(b"integrity-key"),
        clock=lambda: now[0],
    )
    lease = ledger.acquire_lease("ledger-owner", "owner", ttl=10).lease
    assert lease is not None
    context = WriterContext(scope, "owner", "key-owner", "ledger-owner", lease.epoch, lease.expires_at)
    assert ledger.create_contract(contract()) in (Result.APPLIED, Result.DUPLICATE)
    service = KernelRunService(ledger, writer=KernelWriter(context, auth))
    service.create_run(run_id="run-a", contract_id="contract-a", mode="kernel")
    service.create_task("run-a", task_id="task-a")
    service.admit_task("run-a", "task-a")
    service.mark_task_ready("run-a", "task-a")
    service.dispatch_task("run-a", "task-a")
    attempt = service.start_attempt("run-a", "task-a")
    yield ledger, service, attempt, now
    ledger.close()


def dispatcher(kernel, adapter=None):
    module = dispatcher_api()
    ledger, service, _, _ = kernel
    return module.KernelDispatcher(ledger=ledger, runtime=service, runtime_adapter=adapter or FakeRuntimeAdapter())


def stage(d, attempt):
    return d.stage_ready(
        "run-a",
        "task-a",
        attempt=attempt.attempt,
        project_root="/workspace/project",
        plan_revision=7,
        snapshot_digest="sha256:snapshot",
    )


def test_observe_is_async_and_accepted_is_technical_only(kernel):
    ledger, service, attempt, _ = kernel
    d = dispatcher(kernel)
    stage(d, attempt)
    async_test(d.dispatch_once())
    observation = async_test(d.observe_once("run-a", "task-a", attempt=attempt.attempt))
    assert observation.status == "accepted"
    assert any(e["kind"] == "observation.accepted" for e in ledger.events())
    assert service.task("run-a", "task-a").state.value == "running"


def test_expired_attempt_is_orphaned_and_cancellation_is_intent_only(kernel):
    ledger, service, attempt, now = kernel
    d = dispatcher(kernel)
    stage(d, attempt)
    now[0] = 111  # strictly beyond original lease before any replacement/cleanup
    d.reconcile_expired("run-a", "task-a", attempt=attempt.attempt)
    assert service.attempts("run-a", "task-a")[-1].state.value == "orphaned"
    assert any(e["kind"] == "cancel.intent" for e in ledger.events())
    assert any(e["kind"] == "attempt.orphaned" for e in ledger.events())


def test_replacement_lease_requires_clock_advance_beyond_original(kernel):
    ledger, _, attempt, now = kernel
    d = dispatcher(kernel)
    envelope = stage(d, attempt)
    now[0] = envelope.authority.lease_until + 1
    replacement = ledger.acquire_lease(envelope.authority.lease_resource, "replacement", ttl=10).lease
    assert replacement is not None and replacement.epoch > envelope.authority.lease_epoch


def test_stale_fence_rejects_result_without_runtime_effect(kernel):
    ledger, service, attempt, now = kernel
    adapter = FakeRuntimeAdapter()
    d = dispatcher(kernel, adapter)
    envelope = stage(d, attempt)
    now[0] = envelope.authority.lease_until + 1
    assert ledger.acquire_lease(envelope.authority.lease_resource, "replacement", ttl=10).lease
    before = len(adapter.opens), len(ledger.events()), service.task("run-a", "task-a")
    with pytest.raises(dispatcher_api().StaleFence):
        d.accept_result(envelope.authority, {"status": "accepted"})
    assert (len(adapter.opens), len(ledger.events()), service.task("run-a", "task-a")) == before


def test_superseded_attempt_rejects_late_result_with_stale_fence(kernel):
    d = dispatcher(kernel)
    first = stage(d, kernel[2])
    d.supersede_attempt("run-a", "task-a", attempt=kernel[2].attempt, replacement_attempt=kernel[2].attempt + 1)
    with pytest.raises(dispatcher_api().StaleFence):
        d.accept_result(first.authority, {"status": "accepted"})


def test_supersession_is_operational_not_semantic_completion(kernel):
    ledger, service, attempt, _ = kernel
    d = dispatcher(kernel)
    stage(d, attempt)
    d.supersede_attempt("run-a", "task-a", attempt=attempt.attempt, replacement_attempt=attempt.attempt + 1)
    assert any(e["kind"] == "attempt.superseded" for e in ledger.events())
    assert service.task("run-a", "task-a").state.value == "running"


def test_cancel_does_not_clear_unknown_without_typed_evidence(kernel):
    ledger, _, attempt, _ = kernel
    d = dispatcher(kernel, FakeRuntimeAdapter("accepted_response_lost"))
    envelope = stage(d, attempt)
    async_test(d.dispatch_once())
    d.cancel("run-a", "task-a", attempt=attempt.attempt)
    assert dispatch_row(ledger)["status"] == "UNKNOWN" and dispatch_row(ledger)["reconciliation_required"] == 1
    with pytest.raises(dispatcher_api().ReconciliationRequired):
        d.reconcile_unknown("run-a", "task-a", attempt=attempt.attempt, evidence=None)
    evidence = dispatcher_api().ReconciliationEvidence(
        authority=envelope.authority, observation="external-status-unknown"
    )
    d.reconcile_unknown("run-a", "task-a", attempt=attempt.attempt, evidence=evidence)
    assert dispatch_row(ledger)["reconciliation_required"] == 0


def test_current_fence_observation_never_asserts_task_completion(kernel):
    ledger, service, attempt, _ = kernel
    d = dispatcher(kernel)
    envelope = stage(d, attempt)
    result = d.accept_result(envelope.authority, {"status": "accepted"})
    assert result is not None and service.task("run-a", "task-a").state.value == "running"
    assert not any(e["kind"] == "task.completed" for e in ledger.events())
    accepted = [e for e in ledger.events() if e["kind"] == "observation.accepted"]
    assert len(accepted) == 1
    assert d.accept_result(envelope.authority, {"status": "accepted"}) == result
    assert len([e for e in ledger.events() if e["kind"] == "observation.accepted"]) == 1


def test_invalid_authority_rejected_before_dispatch_effect(kernel):
    adapter = FakeRuntimeAdapter()
    module = dispatcher_api()
    d = dispatcher(kernel, adapter)
    for args in (
        ("missing-run", "task-a", 1),
        ("run-a", "missing-task", 1),
        ("run-a", "task-a", 99),
        ("run-b", "task-a", 1),
    ):
        with pytest.raises(module.DispatchRejected):
            d.stage_ready(
                args[0],
                args[1],
                attempt=args[2],
                project_root="/workspace/project",
                plan_revision=7,
                snapshot_digest="sha256:snapshot",
            )
    assert adapter.opens == []


def test_each_stale_fence_operation_fails_before_adapter_effect(kernel):
    ledger, _, attempt, now = kernel
    adapter = FakeRuntimeAdapter()
    d = dispatcher(kernel, adapter)
    envelope = stage(d, attempt)
    now[0] = envelope.authority.lease_until + 1
    ledger.acquire_lease(envelope.authority.lease_resource, "replacement", ttl=10)
    sync_operations = (
        lambda: d.claim_with(envelope.authority),
        lambda: d.acknowledge(envelope.authority),
        lambda: d.cancel_with(envelope.authority),
    )
    for operation in sync_operations:
        with pytest.raises(dispatcher_api().StaleFence):
            operation()
    async_operations = (lambda: d.dispatch_with(envelope.authority), lambda: d.observe_with(envelope.authority))
    for operation in async_operations:
        with pytest.raises(dispatcher_api().StaleFence):
            async_test(operation())
    assert adapter.opens == []


def test_fencing_has_no_process_local_replay_authority():
    module = dispatcher_api()
    assert not any(name in dir(module) for name in ("replay_cache", "in_memory_outbox", "session_registry"))


def test_reconcile_expired_rejects_live_attempt_fence(kernel):
    ledger, _, attempt, _ = kernel
    d = dispatcher(kernel)
    stage(d, attempt)
    before = len(ledger.events())
    with pytest.raises(dispatcher_api().StaleFence):
        d.reconcile_expired("run-a", "task-a", attempt=attempt.attempt)
    assert len(ledger.events()) == before


@pytest.mark.parametrize("replacement", (0, 1))
def test_supersession_requires_strictly_monotonic_attempt(kernel, replacement):
    ledger, _, attempt, _ = kernel
    d = dispatcher(kernel)
    stage(d, attempt)
    before = len(ledger.events())
    with pytest.raises(dispatcher_api().DispatchRejected):
        d.supersede_attempt(
            "run-a",
            "task-a",
            attempt=attempt.attempt,
            replacement_attempt=replacement,
        )
    assert len(ledger.events()) == before
