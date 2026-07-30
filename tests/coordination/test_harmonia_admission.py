from __future__ import annotations

import json
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from olympus_v3.coordination.contracts import (
    ContractLimits,
    ContractState,
    ExecutionContract,
    SideEffectPolicy,
)
from olympus_v3.coordination.kernel_dispatcher import KernelDispatcher
from olympus_v3.coordination.kernel_runtime import (
    AdmissionLimitError,
    IdempotencyConflictError,
    KernelRunService,
    KernelWriter,
)
from olympus_v3.coordination.ledger import (
    HMACIntegritySigner,
    HMACWriterAuthenticator,
    Result,
    SQLiteLedger,
    StoreScope,
    WriterContext,
)
from olympus_v3.coordination.principal import Principal

PROJECT = "project-harmonia"
CONTRACT = "contract-" + "b" * 32
RUN = "run-" + "a" * 32
REQUEST_DIGEST = "sha256:" + "c" * 64


def _contract(status: ContractState = ContractState.ACTIVE):
    owner = Principal(PROJECT, "server", "hermes")
    worker = Principal(PROJECT, "server", "hefesto")
    return ExecutionContract(
        CONTRACT,
        PROJECT,
        0,
        owner,
        (owner, worker),
        "one task",
        "one result",
        ("src",),
        ("home",),
        {"hefesto": ("read", "write")},
        (),
        SideEffectPolicy((), 0, True),
        ContractLimits(1, 600, 0, 100, 1, 1),
        ("ambiguity",),
        owner,
        owner,
        0,
        status,
    )


def _open(path: Path, *, create_contract: bool = True, status: ContractState = ContractState.ACTIVE):
    scope = StoreScope("installation-harmonia", PROJECT)
    auth = HMACWriterAuthenticator({("hermes", "harmonia-writer-v1"): b"w" * 32})
    ledger = SQLiteLedger(
        path,
        scope,
        writer_authenticator=auth,
        integrity_signer=HMACIntegritySigner(b"i" * 32, "harmonia-integrity-v1"),
    )
    if create_contract:
        assert ledger.create_contract(_contract(status)) in (Result.APPLIED, Result.DUPLICATE)
    lease = ledger.acquire_lease("harmonia-ledger-owner", "hermes", ttl=3_600_000_000_000).lease
    assert lease is not None
    context = WriterContext(
        scope,
        "hermes",
        "harmonia-writer-v1",
        "harmonia-ledger-owner",
        lease.epoch,
        lease.expires_at,
    )
    return ledger, KernelRunService(ledger, writer=KernelWriter(context, auth))


def _ensure(service: KernelRunService, *, run_id: str = RUN, request_id: str = "request-1", digest: str = REQUEST_DIGEST):
    return service.ensure_run(
        run_id=run_id,
        contract_id=CONTRACT,
        mode="kernel",
        request_id=request_id,
        request_digest=digest,
    )


def _kinds(ledger):
    return [row["kind"] for row in ledger.events()]


def test_legacy_run_created_rebuild_remains_valid(tmp_path):
    ledger, service = _open(tmp_path / "legacy.sqlite")
    service.create_run(run_id="run-legacy", contract_id=CONTRACT, mode="kernel")

    rebuilt = KernelRunService(ledger, writer=service.writer)

    assert rebuilt.run("run-legacy").run_id == "run-legacy"
    assert rebuilt.run_request("run-legacy") is None
    payload = json.loads(next(row for row in ledger.events() if row["kind"] == "run.created")["payload"])
    assert set(payload) == {"run_id", "contract_id", "mode"}
    ledger.close()


def test_new_run_created_rebuild_retains_request_identity_and_kernel_authority(tmp_path):
    ledger, service = _open(tmp_path / "new.sqlite")

    record = _ensure(service)
    metadata = KernelRunService(ledger, writer=service.writer).run_request(RUN)

    assert record.mode == "kernel"
    assert metadata.request_id == "request-1"
    assert metadata.request_digest == REQUEST_DIGEST
    payload = json.loads(next(row for row in ledger.events() if row["kind"] == "run.created")["payload"])
    assert payload == {
        "contract_id": CONTRACT,
        "mode": "kernel",
        "request_digest": REQUEST_DIGEST,
        "request_id": "request-1",
        "run_id": RUN,
    }
    ledger.close()


def test_exact_replay_produces_one_run_task_attempt_and_dispatch_stage(tmp_path):
    ledger, service = _open(tmp_path / "replay.sqlite")
    _ensure(service)
    assert _ensure(service) == service.run(RUN)
    task_id = "task-" + "d" * 32
    service.create_task(RUN, task_id=task_id)
    service.admit_task(RUN, task_id)
    service.mark_task_ready(RUN, task_id)
    service.dispatch_task(RUN, task_id)
    attempt = service.start_attempt(RUN, task_id)
    dispatcher = KernelDispatcher(ledger=ledger, runtime=service, runtime_adapter=object(), worker_id="hermes")

    first = dispatcher.stage_ready(
        RUN,
        task_id,
        attempt=attempt.attempt,
        project_root=str(tmp_path),
        plan_revision=1,
        snapshot_digest="sha256:" + "e" * 64,
    )
    second = dispatcher.stage_ready(
        RUN,
        task_id,
        attempt=attempt.attempt,
        project_root=str(tmp_path),
        plan_revision=1,
        snapshot_digest="sha256:" + "e" * 64,
    )

    assert first == second
    assert _kinds(ledger).count("run.created") == 1
    assert _kinds(ledger).count("task.created") == 1
    assert _kinds(ledger).count("attempt.started") == 1
    assert _kinds(ledger).count("dispatch.staged") == 1
    ledger.close()


def test_same_request_id_with_different_digest_is_idempotency_conflict(tmp_path):
    ledger, service = _open(tmp_path / "conflict.sqlite")
    _ensure(service)

    with pytest.raises(IdempotencyConflictError, match="idempotency conflict"):
        _ensure(service, digest="sha256:" + "f" * 64)

    assert _kinds(ledger).count("run.created") == 1
    ledger.close()


def test_different_durable_run_hits_single_run_admission_limit(tmp_path):
    ledger, service = _open(tmp_path / "limit.sqlite")
    _ensure(service)

    with pytest.raises(AdmissionLimitError, match="admission limit"):
        _ensure(service, run_id="run-" + "f" * 32, request_id="request-2")

    assert _kinds(ledger).count("run.created") == 1
    ledger.close()


def test_crash_after_genesis_resumes_exact_request_without_prior_effect(tmp_path):
    path = tmp_path / "resume.sqlite"
    ledger, service = _open(path)
    assert ledger.events() == []
    ledger.close()

    reopened, resumed = _open(path, create_contract=False)
    _ensure(resumed)

    assert _kinds(reopened) == ["run.created"]
    assert resumed.run_request(RUN).request_id == "request-1"
    reopened.close()


def test_inactive_genesis_fails_closed_before_run_event(tmp_path):
    ledger, service = _open(tmp_path / "inactive.sqlite", status=ContractState.PROPOSED)

    with pytest.raises(ValueError, match="active execution contract required"):
        _ensure(service)

    assert ledger.events() == []
    ledger.close()


def test_concurrent_exact_requests_converge_on_one_cas_event(tmp_path):
    path = tmp_path / "concurrent.sqlite"
    genesis, _ = _open(path)
    genesis.close()
    barrier = threading.Barrier(2)

    def admit():
        ledger, service = _open(path, create_contract=False)
        try:
            barrier.wait(timeout=5)
            return _ensure(service)
        finally:
            ledger.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        records = list(pool.map(lambda _: admit(), range(2)))

    ledger, service = _open(path, create_contract=False)
    assert records[0] == records[1] == service.run(RUN)
    assert _kinds(ledger).count("run.created") == 1
    ledger.close()
