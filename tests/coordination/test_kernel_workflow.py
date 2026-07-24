"""RED contracts for the single semantic kernel workflow command boundary."""

from __future__ import annotations

import importlib
import inspect
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

PROJECT = "project-a"
OWNER = Principal(PROJECT, "hermes", "owner")
WORKER = Principal(PROJECT, "hermes", "worker")


def kernel_api():
    try:
        workflow = importlib.import_module("olympus_v3.coordination.workflow")
        runtime = importlib.import_module("olympus_v3.coordination.kernel_runtime")
    except ModuleNotFoundError as exc:
        pytest.fail(f"missing kernel workflow capability: {exc.name}", pytrace=False)
    return workflow, runtime


def active_contract(*, model_budget: int = 100) -> ExecutionContract:
    return ExecutionContract(
        contract_id="contract-a",
        project_id=PROJECT,
        generation=0,
        owner=OWNER,
        participants=(OWNER, WORKER),
        objective="build the feature",
        expected_outcome="verified feature",
        included_scopes=("src/",),
        excluded_scopes=("secrets/",),
        role_permissions={"worker": ("implement",)},
        evidence_gates=(EvidenceGate("qa", True),),
        side_effect_policy=SideEffectPolicy(("filesystem",), 2, True),
        limits=ContractLimits(2, 60, 3, model_budget, 1, 1),
        escalation_conditions=("ambiguity",),
        completion_authority=OWNER,
        amendment_authority=OWNER,
        status=ContractState.ACTIVE,
    )


def open_runtime(
    path: Path,
    *,
    model_budget: int = 100,
    writer_id: str = "writer-a",
    key_id: str = "key-a",
    provision: bool = True,
):
    scope = StoreScope("install-a", PROJECT)
    auth = HMACWriterAuthenticator({(writer_id, key_id): b"writer-key"})
    signer = HMACIntegritySigner(b"integrity-key", key_id="integrity-a")
    ledger = SQLiteLedger(
        path,
        scope,
        writer_authenticator=auth,
        integrity_signer=signer,
    )
    lease_result = ledger.acquire_lease("ledger-" + writer_id, writer_id, ttl=10_000_000_000)
    assert lease_result.lease is not None
    context = WriterContext(
        scope,
        writer_id,
        key_id,
        "ledger-" + writer_id,
        lease_result.lease.epoch,
        lease_result.lease.expires_at,
    )
    contract = active_contract(model_budget=model_budget)
    if provision:
        result = ledger.create_contract(contract)
        if result is Result.CAS_CONFLICT:
            assert ledger.read_contract("contract-a") == contract
        else:
            assert result in (Result.APPLIED, Result.DUPLICATE)
            assert ledger.read_contract("contract-a") == contract
    runtime = importlib.import_module("olympus_v3.coordination.kernel_runtime")
    writer = runtime.KernelWriter(context, auth)
    return ledger, runtime.KernelRunService(ledger, writer=writer), context, auth


def test_run_rebuild_restores_durable_workflow_from_typed_intent_events(tmp_path: Path):
    _, runtime = kernel_api()
    ledger, service, _, _ = open_runtime(tmp_path / "kernel.sqlite")
    original = service.create_run(run_id="run-a", contract_id="contract-a", mode="kernel")
    service.create_task("run-a", task_id="task-a", prerequisites=())
    service.admit_task("run-a", "task-a")
    service.mark_task_ready("run-a", "task-a")
    service.dispatch_task("run-a", "task-a")
    service.start_attempt("run-a", "task-a")
    service.bind_logical_session("run-a", "task-a", logical_session="logical-a")

    event_kinds = [row[0] for row in ledger.conn.execute("SELECT kind FROM events")]
    assert {
        "run.created",
        "task.created",
        "task.admitted",
        "task.ready",
        "task.dispatched",
        "attempt.started",
        "session.bound",
    } <= set(event_kinds)

    rebuilt = runtime.KernelRunService.rebuild(ledger)
    assert rebuilt.run("run-a") == original
    assert rebuilt.task("run-a", "task-a").state == "running"
    assert rebuilt.attempts("run-a", "task-a")[0].attempt == 1
    assert rebuilt.sessions("run-a", "task-a")[0].logical_session == "logical-a"



def test_task_progress_requires_durable_task_and_legal_transitions(tmp_path: Path):
    _, runtime = kernel_api()
    ledger, service, _, _ = open_runtime(tmp_path / "state.sqlite")
    service.create_run(run_id="run-a", contract_id="contract-a", mode="kernel")
    with pytest.raises((KeyError, ValueError, runtime.InvalidTransition)):
        service.complete_task("run-a", "task-a")
    service.create_task("run-a", task_id="task-a", prerequisites=())
    service.admit_task("run-a", "task-a")
    with pytest.raises((ValueError, runtime.InvalidTransition)):
        service.complete_task("run-a", "task-a")
    service.mark_task_ready("run-a", "task-a")
    service.dispatch_task("run-a", "task-a")
    service.start_attempt("run-a", "task-a")
    assert service.task("run-a", "task-a").state == "running"
    with pytest.raises((ValueError, runtime.InvalidTransition)):
        service.complete_task("run-a", "task-a")


def test_only_authenticated_kernel_writer_can_advance_semantic_task_state(tmp_path: Path):
    workflow, runtime = kernel_api()
    ledger, service, _, _ = open_runtime(tmp_path / "writer.sqlite")
    service.create_run(run_id="run-a", contract_id="contract-a", mode="kernel")
    service.create_task("run-a", task_id="task-a", prerequisites=())
    task = service.task("run-a", "task-a")
    with pytest.raises((AttributeError, TypeError, workflow.AuthorityError)):
        task.state = "completed"
    service.admit_task("run-a", "task-a")
    signature = inspect.signature(service.complete_task)
    assert "state" not in signature.parameters
    assert "outcome" not in signature.parameters


def test_runtime_mode_is_immutable_and_kernel_never_writes_pilot_store(tmp_path: Path):
    _, runtime = kernel_api()
    ledger, service, _, _ = open_runtime(tmp_path / "mode.sqlite")
    service.create_run(run_id="run-a", contract_id="contract-a", mode="kernel")
    with pytest.raises(runtime.RuntimeModeError):
        service.set_runtime_mode("run-a", "pilot")
    assert service.run("run-a").mode == "kernel"
