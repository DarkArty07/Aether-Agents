"""Behavioral RED regressions for GitHub #107 Harmonia lease lifecycle."""

from __future__ import annotations

import asyncio
import concurrent.futures
import hashlib
import json
import threading
from dataclasses import dataclass, replace
from pathlib import Path

import pytest

import olympus_v3.coordination.kernel_dispatcher as dispatcher_module
from aether_agents.evidence import (
    ARTIFACT_RELATIVE_PATH,
    build_evidence_receipt,
    verify_artifact,
)
from aether_agents.identity import Principal, ValidationError
from aether_agents.review.closure import CompletionState
from olympus_v3.acp_manager import ACPManager, AgentState, SessionInfo
from olympus_v3.coordination import (
    ContractLimits,
    ContractState,
    EvidenceGate,
    ExecutionContract,
    HMACIntegritySigner,
    HMACWriterAuthenticator,
    Result,
    SideEffectPolicy,
    SQLiteLedger,
    StoreScope,
    TaskState,
    WriterContext,
)
from olympus_v3.coordination.kernel_dispatcher import DispatchAuthority, KernelDispatcher
from olympus_v3.coordination.kernel_runtime import KernelRunService, KernelWriter
from olympus_v3.coordination.olympus_adapter import OlympusRuntimeAdapter
from olympus_v3.coordination.workflow import closure_proposal_hash

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

    async def cleanup_kernel(self, **request):
        self.calls.append(("cleanup_kernel", request))
        if self.cleanup_error:
            raise self.cleanup_error
        return {
            "status": request["terminal_status"],
            "acp_session_id": request["session_id"],
            "project_id": request["project_id"],
            "survivors": {"logical_manager_session": False, "acp_mapping": False, "prompt_task": False, "pid_session_mapping": False},
        }


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
        return {"status": terminal_status, "project_id": project_id, "acp_session_id": session_id, "survivors": {"logical_manager_session": False, "acp_mapping": False, "prompt_task": False, "pid_session_mapping": False}}


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
    project_root = tmp_path / "project"
    project_root.mkdir()
    envelope = dispatcher.stage_ready(
        "run-a",
        "task-a",
        attempt=attempt.attempt,
        project_root=str(project_root),
        plan_revision=7,
        snapshot_digest="sha256:snapshot",
    )
    yield clock, ledger, runtime, dispatcher, envelope, effects
    if not ledger._closed:
        ledger.close()


def event_payloads(ledger, kind: str) -> list[dict]:
    return [json.loads(row["payload"]) for row in ledger.events() if row["kind"] == kind]


def write_result_artifact(authority, acp_session_id: str, *, answer: str = "ok") -> Path:
    payload = {
        "schema": "AETHER_TASK_RESULT_V1",
        "installation_id": authority.installation_id,
        "project_id": authority.project_id,
        "run_id": authority.run_id,
        "task_id": authority.task_id,
        "attempt": authority.attempt,
        "contract_id": authority.contract_id,
        "contract_generation": authority.contract_generation,
        "revocation_epoch": authority.revocation_epoch,
        "message_id": authority.message_id,
        "logical_session": authority.logical_session,
        "acp_session_id": acp_session_id,
        "artifact_generation": 1,
        "result": {"answer": answer},
    }
    path = Path(authority.project_root) / ARTIFACT_RELATIVE_PATH.format(
        run_id=authority.run_id,
        task_id=authority.task_id,
        attempt=authority.attempt,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def stage_running_task(runtime, dispatcher, *, task_id: str, project_root: str, plan_revision: int):
    runtime.create_task("run-a", task_id=task_id)
    runtime.admit_task("run-a", task_id)
    runtime.mark_task_ready("run-a", task_id)
    runtime.dispatch_task("run-a", task_id)
    attempt = runtime.start_attempt("run-a", task_id)
    return dispatcher.stage_ready(
        "run-a",
        task_id,
        attempt=attempt.attempt,
        project_root=project_root,
        plan_revision=plan_revision,
        snapshot_digest=f"sha256:snapshot-{task_id}",
    )


def persist_task_receipt(ledger, dispatcher, envelope):
    authority = envelope.authority
    run(dispatcher.dispatch_with(authority))
    binding = next(
        payload
        for payload in event_payloads(ledger, "session.bound")
        if payload.get("message_id") == authority.message_id
    )
    terminal = TerminalObservation(
        "completed",
        authority.logical_session,
        binding["acp_session_id"],
        authority.message_id,
    )
    dispatcher.record_terminal_with(authority, terminal)
    write_result_artifact(authority, terminal.acp_session_id)
    return dispatcher.record_evidence_with(authority)


def authority_from(payload: dict) -> DispatchAuthority:
    names = (
        "installation_id",
        "project_id",
        "run_id",
        "task_id",
        "attempt",
        "contract_id",
        "contract_generation",
        "revocation_epoch",
        "agent_name",
        "plan_id",
        "plan_revision",
        "snapshot_digest",
        "project_root",
        "logical_session",
        "message_id",
        "lease_resource",
        "lease_owner",
        "lease_epoch",
        "lease_token",
        "lease_until",
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
        original.resource,
        original.owner,
        original.epoch,
        original.token,
    )
    assert current.expires_at > authority.lease_until
    assert renewed.lease.epoch == authority.lease_epoch
    assert clock() < current.expires_at


def test_successor_admission_is_cleanup_gated_by_source_closed_state(stack):
    _, _, runtime, dispatcher, _, _ = stack
    runtime.create_task("run-a", task_id="task-b", prerequisites=("task-a",))

    with pytest.raises(dispatcher_module.DispatchRejected, match="source task must be closed"):
        dispatcher.stage_successor(
            "run-a",
            "task-a",
            "task-b",
            project_root=str(Path("/workspace/project")),
            plan_revision=1,
        )


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


def test_evidence_receipt_records_once_and_changed_artifact_conflicts(stack):
    _, ledger, runtime, dispatcher, envelope, _ = stack
    authority = envelope.authority
    dependent = runtime.create_task("run-a", task_id="task-b", prerequisites=("task-a",))
    assert dependent.state is TaskState.BLOCKED
    run(dispatcher.dispatch_with(authority))
    binding = event_payloads(ledger, "session.bound")[0]
    terminal = TerminalObservation(
        "completed", authority.logical_session, binding["acp_session_id"], authority.message_id
    )
    dispatcher.record_terminal_with(authority, terminal)
    artifact_path = write_result_artifact(authority, terminal.acp_session_id)

    first = dispatcher.record_evidence_with(authority)
    replay = dispatcher.record_evidence_with(authority)

    assert first is Result.APPLIED
    assert replay is Result.DUPLICATE
    receipts = event_payloads(ledger, "evidence.receipt.recorded")
    assert len(receipts) == 1
    receipt = receipts[0]
    assert receipt["schema"] == "AETHER_EVIDENCE_RECEIPT_V1"
    assert receipt["contract_id"] == authority.contract_id
    assert receipt["terminal"] == {"technical_status": "completed"}
    assert receipt["artifact"]["digest"].startswith("sha256:")
    assert "result" not in receipt["artifact"]
    assert receipt["receipt_id"].startswith("receipt:")
    assert receipt["receipt_payload_digest"].startswith("sha256:")
    releases = event_payloads(ledger, "task.released")
    assert len(releases) == 1
    release = releases[0]
    assert release["contract_id"] == authority.contract_id
    assert release["run_id"] == "run-a"
    assert release["task_id"] == "task-b"
    assert release["satisfied_prerequisites"] == [{"task_id": "task-a", "receipt_id": receipt["receipt_id"]}]
    assert release["handoff"] == receipt["handoff"]
    assert runtime.task("run-a", "task-b").state is TaskState.PROPOSED
    projection = ledger.projection("task:run-a:task-b")
    assert projection is not None and projection["state"] == "proposed"
    assert runtime.task("run-a", "task-a").state is TaskState.RUNNING

    before = tuple((row["kind"], row["payload"]) for row in ledger.events())
    value = json.loads(artifact_path.read_text())
    value["result"]["answer"] = "changed"
    artifact_path.write_text(json.dumps(value))
    with pytest.raises(Exception, match="IDEMPOTENCY_CONFLICT"):
        dispatcher.record_evidence_with(authority)
    assert tuple((row["kind"], row["payload"]) for row in ledger.events()) == before


def test_receipt_and_release_rollback_as_one_transaction(stack):
    _, ledger, runtime, dispatcher, envelope, _ = stack
    authority = envelope.authority
    runtime.create_task("run-a", task_id="task-b", prerequisites=("task-a",))
    run(dispatcher.dispatch_with(authority))
    binding = event_payloads(ledger, "session.bound")[0]
    dispatcher.record_terminal_with(
        authority,
        TerminalObservation("completed", authority.logical_session, binding["acp_session_id"], authority.message_id),
    )
    write_result_artifact(authority, binding["acp_session_id"])
    before = {
        table: tuple(tuple(row) for row in ledger.conn.execute(f"SELECT * FROM {table} ORDER BY rowid"))
        for table in ("events", "projections", "inbox", "outbox")
    }

    def fail_between_receipt_and_release(stage):
        if stage == "batch_after_item_1":
            raise RuntimeError("injected batch crash")

    ledger.fault = fail_between_receipt_and_release
    with pytest.raises(RuntimeError, match="injected batch crash"):
        dispatcher.record_evidence_with(authority)
    ledger.fault = None

    assert len(event_payloads(ledger, "runtime.terminal.observed")) == 1
    assert not event_payloads(ledger, "evidence.receipt.recorded")
    assert not event_payloads(ledger, "task.released")
    after = {
        table: tuple(tuple(row) for row in ledger.conn.execute(f"SELECT * FROM {table} ORDER BY rowid"))
        for table in ("events", "projections", "inbox", "outbox")
    }
    assert after == before
    assert runtime.task("run-a", "task-b").state is TaskState.BLOCKED

    assert dispatcher.record_evidence_with(authority) is Result.APPLIED
    assert len(event_payloads(ledger, "evidence.receipt.recorded")) == 1
    assert len(event_payloads(ledger, "task.released")) == 1
    assert runtime.task("run-a", "task-b").state is TaskState.PROPOSED


def test_two_connections_racing_same_release_converge_to_one_batch(stack):
    clock, ledger, runtime, dispatcher, envelope, _ = stack
    authority = envelope.authority
    runtime.create_task("run-a", task_id="task-b", prerequisites=("task-a",))
    run(dispatcher.dispatch_with(authority))
    binding = event_payloads(ledger, "session.bound")[0]
    dispatcher.record_terminal_with(
        authority,
        TerminalObservation("completed", authority.logical_session, binding["acp_session_id"], authority.message_id),
    )
    write_result_artifact(authority, binding["acp_session_id"])
    db_path = Path(ledger.conn.execute("PRAGMA database_list").fetchone()[2])
    barrier = threading.Barrier(2)

    def record_from_independent_connection():
        auth = HMACWriterAuthenticator({("owner", "key-owner"): b"owner-key"})
        local = SQLiteLedger(
            db_path,
            ledger.scope,
            writer_authenticator=auth,
            integrity_signer=HMACIntegritySigner(b"integrity-key"),
            clock=clock,
        )
        try:
            lease = local.lease("ledger-owner")
            assert lease is not None
            context = WriterContext(
                local.scope,
                "owner",
                "key-owner",
                "ledger-owner",
                lease.epoch,
                lease.expires_at,
            )
            local_runtime = KernelRunService(local, writer=KernelWriter(context, auth))
            local_dispatcher = KernelDispatcher(
                ledger=local,
                runtime=local_runtime,
                runtime_adapter=EffectBarrier(),
                worker_id="owner",
            )
            barrier.wait(timeout=5)
            return local_dispatcher.record_evidence_with(authority)
        finally:
            local.close()

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        results = tuple(executor.map(lambda _: record_from_independent_connection(), range(2)))

    assert sorted(result.value for result in results) == ["APPLIED", "DUPLICATE"]
    assert len(event_payloads(ledger, "evidence.receipt.recorded")) == 1
    assert len(event_payloads(ledger, "task.released")) == 1
    assert runtime.task("run-a", "task-b").state is TaskState.PROPOSED


def test_one_receipt_releases_all_dependents_in_task_order(stack):
    _, ledger, runtime, dispatcher, envelope, _ = stack
    runtime.create_task("run-a", task_id="task-b", prerequisites=("task-a",))
    runtime.create_task("run-a", task_id="task-c", prerequisites=("task-a",))

    assert persist_task_receipt(ledger, dispatcher, envelope) is Result.APPLIED

    releases = event_payloads(ledger, "task.released")
    assert [payload["task_id"] for payload in releases] == ["task-b", "task-c"]
    receipt_id = event_payloads(ledger, "evidence.receipt.recorded")[0]["receipt_id"]
    assert all(
        payload["satisfied_prerequisites"] == [{"task_id": "task-a", "receipt_id": receipt_id}] for payload in releases
    )
    assert runtime.task("run-a", "task-b").state is TaskState.PROPOSED
    assert runtime.task("run-a", "task-c").state is TaskState.PROPOSED


def test_multiple_prerequisites_release_only_after_last_receipt(stack):
    _, ledger, runtime, dispatcher, envelope_a, _ = stack
    envelope_c = stage_running_task(
        runtime,
        dispatcher,
        task_id="task-c",
        project_root=envelope_a.authority.project_root,
        plan_revision=8,
    )
    runtime.create_task("run-a", task_id="task-b", prerequisites=("task-a", "task-c"))

    assert persist_task_receipt(ledger, dispatcher, envelope_a) is Result.APPLIED
    assert not event_payloads(ledger, "task.released")
    assert runtime.task("run-a", "task-b").state is TaskState.BLOCKED

    receipt_a = event_payloads(ledger, "evidence.receipt.recorded")[0]
    contract = ledger.read_contract("contract-a")
    assert contract is not None
    forged_payload = {
        "run_id": "run-a",
        "task_id": "task-b",
        "satisfied_prerequisites": [
            {"task_id": "task-a", "receipt_id": receipt_a["receipt_id"]},
            {"task_id": "task-c", "receipt_id": "receipt:" + "0" * 64},
        ],
        "contract_id": "contract-a",
    }
    forged = runtime.writer._author(
        ledger,
        "task:run-a:task-b",
        "task.released",
        forged_payload,
        ledger.aggregate_version("task:run-a:task-b"),
        contract_generation=contract.generation,
        revocation_epoch=contract.revocation_epoch,
    )
    assert ledger.append(forged, runtime.writer.context, message_id="forged-release").status is Result.INVALID_INPUT
    assert runtime.task("run-a", "task-b").state is TaskState.BLOCKED

    assert persist_task_receipt(ledger, dispatcher, envelope_c) is Result.APPLIED
    release = event_payloads(ledger, "task.released")[0]
    receipts = {
        payload["task_id"]: payload["receipt_id"] for payload in event_payloads(ledger, "evidence.receipt.recorded")
    }
    assert release["satisfied_prerequisites"] == [
        {"task_id": "task-a", "receipt_id": receipts["task-a"]},
        {"task_id": "task-c", "receipt_id": receipts["task-c"]},
    ]
    assert runtime.task("run-a", "task-b").state is TaskState.PROPOSED
    assert runtime.task("run-a", "task-a").state is TaskState.RUNNING
    assert runtime.task("run-a", "task-c").state is TaskState.RUNNING


def test_evidence_receipt_requires_durable_terminal_and_current_fence(stack):
    clock, ledger, _, dispatcher, envelope, _ = stack
    authority = envelope.authority
    run(dispatcher.dispatch_with(authority))
    binding = event_payloads(ledger, "session.bound")[0]
    write_result_artifact(authority, binding["acp_session_id"])

    with pytest.raises(Exception):
        dispatcher.record_evidence_with(authority)
    assert not event_payloads(ledger, "evidence.receipt.recorded")

    dispatcher.record_terminal_with(
        authority,
        TerminalObservation("completed", authority.logical_session, binding["acp_session_id"], authority.message_id),
    )
    clock.advance(authority.lease_until - clock() + 1)
    with pytest.raises(Exception):
        dispatcher.record_evidence_with(authority)
    assert not event_payloads(ledger, "evidence.receipt.recorded")


def test_ledger_rejects_well_formed_receipt_without_terminal_prerequisite(stack):
    _, ledger, _, dispatcher, envelope, _ = stack
    authority = envelope.authority
    run(dispatcher.dispatch_with(authority))
    binding = event_payloads(ledger, "session.bound")[0]
    write_result_artifact(authority, binding["acp_session_id"])
    identity = dispatcher._evidence_identity(authority, binding["acp_session_id"])
    receipt = build_evidence_receipt(
        identity,
        verify_artifact(Path(authority.project_root), identity),
        "completed",
    )

    with pytest.raises(Exception, match="INVALID_INPUT"):
        dispatcher._append(
            "evidence.receipt.recorded",
            "evidence:" + authority.message_id,
            receipt.event_payload(),
            message_id="evidence:" + authority.message_id,
        )
    assert not event_payloads(ledger, "evidence.receipt.recorded")


def test_ledger_rejects_standalone_receipt_that_would_strand_dependent(stack):
    _, ledger, runtime, dispatcher, envelope, _ = stack
    authority = envelope.authority
    runtime.create_task("run-a", task_id="task-b", prerequisites=("task-a",))
    run(dispatcher.dispatch_with(authority))
    binding = event_payloads(ledger, "session.bound")[0]
    dispatcher.record_terminal_with(
        authority,
        TerminalObservation("completed", authority.logical_session, binding["acp_session_id"], authority.message_id),
    )
    write_result_artifact(authority, binding["acp_session_id"])
    identity = dispatcher._evidence_identity(authority, binding["acp_session_id"])
    receipt = build_evidence_receipt(
        identity,
        verify_artifact(Path(authority.project_root), identity),
        "completed",
    )

    with pytest.raises(Exception, match="INVALID_INPUT"):
        dispatcher._append(
            "evidence.receipt.recorded",
            "evidence:" + authority.message_id,
            receipt.event_payload(),
            message_id="evidence:" + authority.message_id,
        )
    assert not event_payloads(ledger, "evidence.receipt.recorded")
    assert not event_payloads(ledger, "task.released")
    assert runtime.task("run-a", "task-b").state is TaskState.BLOCKED


def test_evidence_rechecks_fence_after_filesystem_verification(stack, monkeypatch):
    _, ledger, _, dispatcher, envelope, _ = stack
    authority = envelope.authority
    run(dispatcher.dispatch_with(authority))
    binding = event_payloads(ledger, "session.bound")[0]
    dispatcher.record_terminal_with(
        authority,
        TerminalObservation("completed", authority.logical_session, binding["acp_session_id"], authority.message_id),
    )
    write_result_artifact(authority, binding["acp_session_id"])
    real_verify = dispatcher_module.verify_artifact

    def replace_fence_after_verify(*args, **kwargs):
        verified = real_verify(*args, **kwargs)
        ledger.conn.execute(
            "UPDATE leases SET token=? WHERE resource=?",
            ("replaced-after-verification", authority.lease_resource),
        )
        ledger.conn.commit()
        return verified

    monkeypatch.setattr(dispatcher_module, "verify_artifact", replace_fence_after_verify)
    with pytest.raises(Exception):
        dispatcher.record_evidence_with(authority)
    assert not event_payloads(ledger, "evidence.receipt.recorded")


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
            authority,
            TerminalObservation("error", authority.logical_session + "-foreign", "acp-session-2", authority.message_id),
        )
    assert len(event_payloads(ledger, "runtime.terminal.observed")) == 1


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
        run(manager.cleanup_persisted("session-a", terminal_status="completed", project_id="foreign-project"))


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


def test_trusted_receipt_requests_one_durable_close_without_cleanup_effect(stack):
    _, ledger, runtime, dispatcher, envelope, effects = stack
    authority = envelope.authority
    assert persist_task_receipt(ledger, dispatcher, envelope) is Result.APPLIED
    calls_before = tuple(effects.calls)

    requested = runtime.request_close(
        authority=authority,
        proposed_state=CompletionState.COMPLETED,
        command_id="close-command-1",
    )

    assert requested.state is TaskState.CLEANUP_PENDING
    intents = event_payloads(ledger, "close.requested")
    assert len(intents) == 1
    receipt = event_payloads(ledger, "evidence.receipt.recorded")[0]
    assert intents[0] == {
        "installation_id": authority.installation_id,
        "project_id": authority.project_id,
        "run_id": authority.run_id,
        "task_id": authority.task_id,
        "attempt": authority.attempt,
        "contract_id": authority.contract_id,
        "contract_generation": authority.contract_generation,
        "revocation_epoch": authority.revocation_epoch,
        "message_id": authority.message_id,
        "logical_session": authority.logical_session,
        "lease_resource": authority.lease_resource,
        "lease_owner": authority.lease_owner,
        "lease_epoch": authority.lease_epoch,
        "lease_token": authority.lease_token,
        "lease_until": authority.lease_until,
        "acp_session_id": "acp-session-1",
        "evidence_receipt_id": receipt["receipt_id"],
        "fence": authority.lease_epoch,
        "closure_proposal_hash": intents[0]["closure_proposal_hash"],
        "cleanup_command_id": "cleanup:close-command-1",
        "command_id": "close-command-1",
        "proposed_state": "completed",
    }
    assert intents[0]["closure_proposal_hash"].startswith("sha256:")
    assert tuple(effects.calls) == calls_before
    assert not event_payloads(ledger, "task.closed")


def test_renewed_dispatch_lease_is_the_exact_fence_used_for_close(stack):
    _, ledger, runtime, dispatcher, envelope, _ = stack
    authority = envelope.authority
    assert persist_task_receipt(ledger, dispatcher, envelope) is Result.APPLIED
    renewed = dispatcher.renew_with(authority, ttl=500)
    assert renewed.lease is not None
    current = replace(authority, lease_until=renewed.lease.expires_at)

    runtime.request_close(
        authority=current,
        proposed_state=CompletionState.COMPLETED,
        command_id="close-after-renewal",
    )
    intent = event_payloads(ledger, "close.requested")[0]
    assert intent["lease_until"] == renewed.lease.expires_at
    assert run(dispatcher.cleanup_once(authority=current))["outcome"] == "completed"
    closed = run(dispatcher.finalize_close(authority=current))

    assert closed["state"] == TaskState.CLOSED.value
    receipt = event_payloads(ledger, "cleanup.receipt.recorded")[0]
    assert receipt["lease_released"] is True
    assert ledger.lease(authority.lease_resource) is None
    operation_leases = [
        row["resource"]
        for row in ledger.conn.execute("SELECT resource FROM leases").fetchall()
        if row["resource"].startswith(("cleanup-effect:", "close-finalize:"))
    ]
    assert operation_leases == []


def test_close_request_requires_matching_trusted_receipt_and_changes_nothing_on_rejection(stack):
    _, ledger, runtime, _, envelope, effects = stack
    authority = envelope.authority
    before = tuple((row["kind"], row["payload"]) for row in ledger.events())

    with pytest.raises(Exception, match="evidence"):
        runtime.request_close(
            authority=authority,
            proposed_state=CompletionState.COMPLETED,
            command_id="close-command-1",
        )

    assert tuple((row["kind"], row["payload"]) for row in ledger.events()) == before
    assert effects.calls == []
    assert runtime.task("run-a", "task-a").state is TaskState.RUNNING


def test_close_request_replays_exactly_and_conflicting_command_payload_fails_closed(stack):
    _, ledger, runtime, dispatcher, envelope, effects = stack
    authority = envelope.authority
    assert persist_task_receipt(ledger, dispatcher, envelope) is Result.APPLIED
    calls_before = tuple(effects.calls)

    first = runtime.request_close(
        authority=authority,
        proposed_state=CompletionState.COMPLETED,
        command_id="close-command-1",
    )
    replay = runtime.request_close(
        authority=authority,
        proposed_state=CompletionState.COMPLETED,
        command_id="close-command-1",
    )

    assert first == replay
    assert len(event_payloads(ledger, "close.requested")) == 1
    before = tuple((row["kind"], row["payload"]) for row in ledger.events())
    with pytest.raises(Exception, match="conflict"):
        runtime.request_close(
            authority=authority,
            proposed_state=CompletionState.FAILED,
            command_id="close-command-1",
        )
    assert tuple((row["kind"], row["payload"]) for row in ledger.events()) == before
    assert tuple(effects.calls) == calls_before

    rebuilt = KernelRunService.rebuild(ledger)
    assert rebuilt.task("run-a", "task-a").state is TaskState.CLEANUP_PENDING
    assert len(event_payloads(ledger, "close.requested")) == 1


def test_direct_completion_cannot_bypass_cleanup_pending_contract(stack):
    _, ledger, runtime, dispatcher, envelope, _ = stack
    assert persist_task_receipt(ledger, dispatcher, envelope) is Result.APPLIED

    with pytest.raises(Exception, match="completion gates"):
        runtime.complete_task("run-a", "task-a")

    assert not event_payloads(ledger, "close.requested")
    assert not event_payloads(ledger, "task.closed")
    assert runtime.task("run-a", "task-a").state is TaskState.RUNNING


@pytest.mark.parametrize("mutation", ["expired-fence", "forged-session", "unknown-run"])
def test_close_request_rejects_stale_or_cross_identity_authority_without_mutation(stack, mutation):
    clock, ledger, runtime, dispatcher, envelope, effects = stack
    authority = envelope.authority
    assert persist_task_receipt(ledger, dispatcher, envelope) is Result.APPLIED
    calls_before = tuple(effects.calls)
    before = tuple((row["kind"], row["payload"]) for row in ledger.events())
    if mutation == "expired-fence":
        clock.advance(authority.lease_until - clock() + 1)
    elif mutation == "forged-session":
        authority = replace(authority, logical_session="kernel:forged")
    else:
        authority = replace(authority, run_id="unknown-run")

    with pytest.raises(Exception):
        runtime.request_close(
            authority=authority,
            proposed_state=CompletionState.COMPLETED,
            command_id="close-command-1",
        )

    assert tuple((row["kind"], row["payload"]) for row in ledger.events()) == before
    assert tuple(effects.calls) == calls_before
    assert not event_payloads(ledger, "close.requested")


def test_ledger_rejects_close_intent_without_verifier_owned_receipt(stack):
    _, ledger, runtime, _, envelope, _ = stack
    authority = envelope.authority
    aggregate = f"task:{authority.run_id}:{authority.task_id}"
    payload = {
        "run_id": authority.run_id,
        "task_id": authority.task_id,
        "attempt": authority.attempt,
        "contract_generation": authority.contract_generation,
        "revocation_epoch": authority.revocation_epoch,
        "message_id": authority.message_id,
        "logical_session": authority.logical_session,
        "acp_session_id": "acp-session-1",
        "evidence_receipt_id": "receipt:" + "a" * 64,
        "cleanup_command_id": "cleanup:close-command-1",
        "command_id": "close-command-1",
        "proposed_state": "completed",
    }
    payload["closure_proposal_hash"] = closure_proposal_hash(payload)
    before = tuple((row["kind"], row["payload"]) for row in ledger.events())

    with pytest.raises(Exception, match="INVALID_INPUT"):
        runtime._append(
            aggregate,
            "close.requested",
            payload,
            runtime._version(aggregate),
            contract_id=authority.contract_id,
        )

    assert tuple((row["kind"], row["payload"]) for row in ledger.events()) == before
    assert runtime.task("run-a", "task-a").state is TaskState.RUNNING


def test_non_completion_authority_cannot_request_close(stack):
    _, ledger, runtime, dispatcher, envelope, effects = stack
    authority = envelope.authority
    assert persist_task_receipt(ledger, dispatcher, envelope) is Result.APPLIED
    current = runtime.writer.context
    other_auth = HMACWriterAuthenticator({("worker", "key-worker"): b"worker-key"})
    other_context = WriterContext(
        ledger.scope,
        "worker",
        "key-worker",
        current.resource,
        current.fence,
        current.expires_at,
    )
    unauthorized = KernelRunService(ledger, writer=KernelWriter(other_context, other_auth))
    before = tuple((row["kind"], row["payload"]) for row in ledger.events())
    calls_before = tuple(effects.calls)

    with pytest.raises(Exception, match="completion authority"):
        unauthorized.request_close(
            authority=authority,
            proposed_state=CompletionState.COMPLETED,
            command_id="close-command-1",
        )

    assert tuple((row["kind"], row["payload"]) for row in ledger.events()) == before
    assert tuple(effects.calls) == calls_before
    assert not event_payloads(ledger, "close.requested")


def test_same_close_command_converges_across_independent_sqlite_connections(stack):
    _, ledger, runtime, dispatcher, envelope, _ = stack
    authority = envelope.authority
    assert persist_task_receipt(ledger, dispatcher, envelope) is Result.APPLIED
    context = runtime.writer.context
    barrier = threading.Barrier(2)

    def request_from_independent_connection():
        auth = HMACWriterAuthenticator({("owner", "key-owner"): b"owner-key"})
        local = SQLiteLedger(
            ledger.path,
            ledger.scope,
            writer_authenticator=auth,
            integrity_signer=HMACIntegritySigner(b"integrity-key"),
            clock=ledger.clock,
            busy_timeout_ms=5_000,
        )
        try:
            service = KernelRunService(local, writer=KernelWriter(context, auth))
            barrier.wait(timeout=5)
            return service.request_close(
                authority=authority,
                proposed_state=CompletionState.COMPLETED,
                command_id="close-command-1",
            ).state
        finally:
            local.close()

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        states = tuple(executor.map(lambda _: request_from_independent_connection(), range(2)))

    assert states == (TaskState.CLEANUP_PENDING, TaskState.CLEANUP_PENDING)
    assert len(event_payloads(ledger, "close.requested")) == 1
    assert runtime.task("run-a", "task-a").state is TaskState.CLEANUP_PENDING


def _persist_close_intent(ledger, runtime, dispatcher, envelope, *, effects):
    assert persist_task_receipt(ledger, dispatcher, envelope) is Result.APPLIED
    runtime.request_close(
        authority=envelope.authority,
        proposed_state=CompletionState.COMPLETED,
        command_id="close-command-1",
    )
    effects.calls.clear()


def test_cleanup_coordinator_consumes_pending_obligation_once_and_never_closes(stack):
    _, ledger, runtime, dispatcher, envelope, effects = stack
    _persist_close_intent(ledger, runtime, dispatcher, envelope, effects=effects)

    first = run(dispatcher.cleanup_once())
    replay = run(dispatcher.cleanup_once())

    assert first["outcome"] == replay["outcome"] == "completed"
    assert len(event_payloads(ledger, "cleanup.requested")) == 1
    assert len(event_payloads(ledger, "cleanup.completed")) == 1
    assert [kind for kind, _ in effects.calls].count("cleanup_kernel") == 1
    assert runtime.task("run-a", "task-a").state is TaskState.CLEANUP_PENDING
    assert not event_payloads(ledger, "task.closed")


def test_cleanup_coordinator_persists_failed_or_unknown_typed_outcomes_without_retry(stack):
    _, ledger, runtime, dispatcher, envelope, effects = stack
    _persist_close_intent(ledger, runtime, dispatcher, envelope, effects=effects)
    effects.cleanup_error = ValidationError("cleanup rejected before effect")

    failed = run(dispatcher.cleanup_once())
    replay = run(dispatcher.cleanup_once())

    assert failed["outcome"] == replay["outcome"] == "failed"
    assert len(event_payloads(ledger, "cleanup.failed")) == 1
    assert [kind for kind, _ in effects.calls].count("cleanup_kernel") == 1
    assert runtime.task("run-a", "task-a").state is TaskState.CLEANUP_PENDING


def test_cleanup_timeout_is_ambiguous_and_never_classified_as_known_failure(stack):
    _, ledger, runtime, dispatcher, envelope, effects = stack
    _persist_close_intent(ledger, runtime, dispatcher, envelope, effects=effects)
    effects.cleanup_error = TimeoutError("cleanup response lost")

    result = run(dispatcher.cleanup_once())

    assert result["outcome"] == "unknown"
    assert len(event_payloads(ledger, "cleanup.unknown")) == 1
    assert not event_payloads(ledger, "cleanup.failed")
    assert not event_payloads(ledger, "cleanup.completed")


def test_cleanup_coordinator_rejects_mismatched_outcome_and_unknown_session_as_unknown(stack):
    _, ledger, runtime, dispatcher, envelope, effects = stack
    _persist_close_intent(ledger, runtime, dispatcher, envelope, effects=effects)
    effects.cleanup_kernel = None

    async def malformed(**request):
        effects.calls.append(("cleanup_kernel", request))
        return {"status": "completed", "acp_session_id": "foreign-session"}

    effects.cleanup_kernel = malformed
    malformed_result = run(dispatcher.cleanup_once())
    assert malformed_result["outcome"] == "unknown"
    assert len(event_payloads(ledger, "cleanup.unknown")) == 1

    # Replaying the typed unknown result must not invoke cleanup again.
    replay = run(dispatcher.cleanup_once())
    assert replay["outcome"] == "unknown"
    assert len([kind for kind, _ in effects.calls if kind == "cleanup_kernel"]) == 1

    # An unknown persisted session is also reconciliation-required, never success.
    assert runtime.task("run-a", "task-a").state is TaskState.CLEANUP_PENDING


def test_cleanup_coordinator_persists_unknown_for_unknown_persisted_session(stack):
    _, ledger, runtime, dispatcher, envelope, effects = stack
    _persist_close_intent(ledger, runtime, dispatcher, envelope, effects=effects)
    effects.cleanup_error = ValueError("unknown persisted session")

    result = run(dispatcher.cleanup_once())

    assert result["outcome"] == "unknown"
    assert len(event_payloads(ledger, "cleanup.unknown")) == 1
    assert not event_payloads(ledger, "cleanup.completed")
    assert runtime.task("run-a", "task-a").state is TaskState.CLEANUP_PENDING


def test_cleanup_coordinator_restarts_from_durable_requested_before_effect(stack):
    _, ledger, runtime, dispatcher, envelope, effects = stack
    _persist_close_intent(ledger, runtime, dispatcher, envelope, effects=effects)
    intent = event_payloads(ledger, "close.requested")[0]
    requested = {
        **{name: intent[name] for name in (
            "installation_id", "project_id", "run_id", "task_id", "attempt",
            "contract_id", "contract_generation", "revocation_epoch", "message_id",
            "logical_session", "acp_session_id", "evidence_receipt_id", "cleanup_command_id",
            "command_id", "proposed_state",
        )},
        "expected_terminal_status": "completed",
        "outcome": "requested",
    }
    dispatcher._append(
        "cleanup.requested",
        "dispatch:" + envelope.authority.message_id,
        requested,
        message_id="cleanup-requested:" + intent["cleanup_command_id"],
    )
    effects.calls.clear()
    restarted = KernelRunService(ledger, writer=runtime.writer)
    restarted_dispatcher = KernelDispatcher(
        ledger=ledger, runtime=restarted, runtime_adapter=effects, worker_id="owner"
    )

    result = run(restarted_dispatcher.cleanup_once())

    assert result["outcome"] == "completed"
    assert len(event_payloads(ledger, "cleanup.requested")) == 1
    assert len(event_payloads(ledger, "cleanup.completed")) == 1
    assert [kind for kind, _ in effects.calls].count("cleanup_kernel") == 1


def test_competing_cleanup_consumers_allow_only_one_external_effect(stack):
    _, ledger, runtime, dispatcher, envelope, effects = stack
    _persist_close_intent(ledger, runtime, dispatcher, envelope, effects=effects)

    class BlockingCleanup:
        def __init__(self):
            self.calls = []
            self.started = asyncio.Event()
            self.release = asyncio.Event()

        async def cleanup_kernel(self, **request):
            self.calls.append(request)
            self.started.set()
            await self.release.wait()
            return {"status": request["terminal_status"], "acp_session_id": request["session_id"], "project_id": request["project_id"], "survivors": {"logical_manager_session": False, "acp_mapping": False, "prompt_task": False, "pid_session_mapping": False}}

    adapter = BlockingCleanup()
    first_dispatcher = KernelDispatcher(
        ledger=ledger, runtime=runtime, runtime_adapter=adapter, worker_id="owner"
    )
    competing_dispatcher = KernelDispatcher(
        ledger=ledger, runtime=runtime, runtime_adapter=adapter, worker_id="owner"
    )

    async def scenario():
        first_task = asyncio.create_task(first_dispatcher.cleanup_once())
        await asyncio.wait_for(adapter.started.wait(), timeout=2)
        competing = await competing_dispatcher.cleanup_once()
        adapter.release.set()
        first = await first_task
        replay = await competing_dispatcher.cleanup_once()
        return first, competing, replay

    first, competing, replay = run(scenario())

    assert first["outcome"] == replay["outcome"] == "completed"
    assert competing is None
    assert len(adapter.calls) == 1
    assert len(event_payloads(ledger, "cleanup.requested")) == 1
    assert len(event_payloads(ledger, "cleanup.completed")) == 1


def test_release_lease_deletes_only_exact_live_owner_epoch_and_token(stack):
    clock, ledger, _, _, envelope, _ = stack
    lease = ledger.lease(envelope.authority.lease_resource)
    assert lease is not None
    released = ledger.release_lease(lease, envelope.authority.lease_owner)
    assert released.status.value == "ACQUIRED"
    assert ledger.lease(lease.resource) is None
    replacement = ledger.acquire_lease(lease.resource, "owner", ttl=100).lease
    assert replacement is not None
    stale = ledger.release_lease(lease, lease.owner)
    assert stale.status.value != "RELEASED"
    assert ledger.lease(lease.resource).token == replacement.token
    assert clock() < replacement.expires_at


def test_finalizer_requires_cleanup_proof_releases_dispatch_lease_and_projects_closed(stack):
    _, ledger, runtime, dispatcher, envelope, effects = stack
    _persist_close_intent(ledger, runtime, dispatcher, envelope, effects=effects)
    assert run(dispatcher.cleanup_once())["outcome"] == "completed"
    finalized = run(dispatcher.finalize_close())
    assert finalized["state"] == TaskState.CLOSED.value
    assert len(event_payloads(ledger, "cleanup.receipt.recorded")) == 1
    assert len(event_payloads(ledger, "task.closed")) == 1
    assert ledger.lease(envelope.authority.lease_resource) is None
    assert runtime.task("run-a", "task-a").state is TaskState.CLOSED
    assert run(dispatcher.finalize_close()) == finalized


@pytest.mark.parametrize(
    ("outcome", "expected_state", "expected_event"),
    [
        ("failed", TaskState.CLOSE_FAILED, "close.failed"),
        ("unknown", TaskState.RECONCILIATION_REQUIRED, "close.reconciliation_required"),
    ],
)
def test_failed_or_unknown_cleanup_never_projects_success(
    stack,
    outcome,
    expected_state,
    expected_event,
):
    _, ledger, runtime, dispatcher, envelope, effects = stack
    _persist_close_intent(ledger, runtime, dispatcher, envelope, effects=effects)
    effects.cleanup_error = ValidationError("cleanup rejected") if outcome == "failed" else TimeoutError("lost")
    assert run(dispatcher.cleanup_once())["outcome"] == outcome
    finalized = run(dispatcher.finalize_close())
    assert finalized["state"] == expected_state.value
    assert len(event_payloads(ledger, expected_event)) == 1
    assert not event_payloads(ledger, "task.closed")
    assert runtime.task("run-a", "task-a").state is expected_state


def test_acp_cleanup_returns_zero_survivor_proof_bound_to_exact_project_and_session(tmp_path):
    manager = ACPManager()
    session_id = "acp-session-1"
    root = tmp_path / "project"
    root.mkdir()
    project_id = hashlib.sha256(("olympus-project-v1\0" + str(root.resolve())).encode()).hexdigest()

    async def scenario():
        profile = tmp_path / "profile"
        profile.mkdir()
        agent = AgentState("hefesto", profile, pid=4242, status="idle")
        agent.acp_session_ids[session_id] = session_id
        done = asyncio.create_task(asyncio.sleep(0))
        await done
        agent.prompt_tasks[session_id] = done
        (profile / ".olympus_session.4242").write_text(session_id)
        manager.sessions[session_id] = SessionInfo(session_id, "hefesto", session_id, str(root))
        manager.agents[manager._agent_key("hefesto", str(root))] = agent
        return await manager.cleanup_persisted(
            session_id,
            terminal_status="completed",
            project_id=project_id,
        )

    proof = run(scenario())
    assert proof["status"] == "completed"
    assert proof["project_id"] == project_id
    assert proof["acp_session_id"] == session_id
    assert proof["survivors"] == {"logical_manager_session": False, "acp_mapping": False, "prompt_task": False, "pid_session_mapping": False}


def test_finalizer_recovers_receipt_written_before_task_closed(stack):
    _, ledger, runtime, dispatcher, envelope, effects = stack
    _persist_close_intent(ledger, runtime, dispatcher, envelope, effects=effects)
    assert run(dispatcher.cleanup_once())["outcome"] == "completed"
    original_append = dispatcher._append

    def crash_after_receipt(kind, *args, **kwargs):
        result = original_append(kind, *args, **kwargs)
        if kind == "cleanup.receipt.recorded":
            raise RuntimeError("crash after cleanup receipt")
        return result

    dispatcher._append = crash_after_receipt
    with pytest.raises(RuntimeError, match="crash after cleanup receipt"):
        run(dispatcher.finalize_close())
    dispatcher._append = original_append

    assert len(event_payloads(ledger, "cleanup.receipt.recorded")) == 1
    assert not event_payloads(ledger, "task.closed")
    recovered = run(dispatcher.finalize_close())
    assert recovered["state"] == TaskState.CLOSED.value
    assert len(event_payloads(ledger, "cleanup.receipt.recorded")) == 1
    assert len(event_payloads(ledger, "task.closed")) == 1
    assert runtime.task("run-a", "task-a").state is TaskState.CLOSED


def test_two_sqlite_finalizers_converge_without_split_terminal_state(stack):
    _, ledger, runtime, dispatcher, envelope, effects = stack
    _persist_close_intent(ledger, runtime, dispatcher, envelope, effects=effects)
    assert run(dispatcher.cleanup_once())["outcome"] == "completed"
    context = runtime.writer.context
    barrier = threading.Barrier(2)

    def finalize_from_connection():
        auth = HMACWriterAuthenticator({("owner", "key-owner"): b"owner-key"})
        local = SQLiteLedger(
            ledger.path,
            ledger.scope,
            writer_authenticator=auth,
            integrity_signer=HMACIntegritySigner(b"integrity-key"),
            clock=ledger.clock,
            busy_timeout_ms=5_000,
        )
        try:
            service = KernelRunService(local, writer=KernelWriter(context, auth))
            local_dispatcher = KernelDispatcher(
                ledger=local,
                runtime=service,
                runtime_adapter=effects,
                worker_id="owner",
            )
            barrier.wait(timeout=5)
            return run(local_dispatcher.finalize_close())
        finally:
            local.close()

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        results = tuple(executor.map(lambda _: finalize_from_connection(), range(2)))

    assert any(result and result["state"] == TaskState.CLOSED.value for result in results)
    assert len(event_payloads(ledger, "cleanup.receipt.recorded")) == 1
    assert len(event_payloads(ledger, "task.closed")) == 1
    assert not event_payloads(ledger, "close.failed")
    assert runtime.task("run-a", "task-a").state is TaskState.CLOSED
    assert run(dispatcher.finalize_close())["state"] == TaskState.CLOSED.value


def test_forged_cleanup_receipt_binding_is_rejected_without_terminal_success(stack):
    _, ledger, runtime, dispatcher, envelope, effects = stack
    _persist_close_intent(ledger, runtime, dispatcher, envelope, effects=effects)
    assert run(dispatcher.cleanup_once())["outcome"] == "completed"
    original_append = dispatcher._append

    def forge_receipt(kind, aggregate, payload, **kwargs):
        if kind == "cleanup.receipt.recorded":
            payload = {**payload, "acp_session_id": "foreign-session"}
        return original_append(kind, aggregate, payload, **kwargs)

    dispatcher._append = forge_receipt
    with pytest.raises(ValueError, match="INVALID_INPUT"):
        run(dispatcher.finalize_close())
    dispatcher._append = original_append

    assert not event_payloads(ledger, "cleanup.receipt.recorded")
    assert not event_payloads(ledger, "task.closed")
    assert runtime.task("run-a", "task-a").state is TaskState.CLEANUP_PENDING
    assert run(dispatcher.finalize_close())["state"] == TaskState.CLOSED.value


def test_newer_dispatch_lease_blocks_finalization_and_survives(stack):
    _, ledger, runtime, dispatcher, envelope, effects = stack
    _persist_close_intent(ledger, runtime, dispatcher, envelope, effects=effects)
    assert run(dispatcher.cleanup_once())["outcome"] == "completed"
    original = ledger.lease(envelope.authority.lease_resource)
    assert original is not None
    assert ledger.release_lease(original, original.owner).lease is None
    replacement = ledger.acquire_lease(original.resource, original.owner, ttl=1_000_000_000).lease
    assert replacement is not None and replacement.token != original.token

    with pytest.raises(dispatcher_module.StaleFence, match="newer dispatch lease"):
        run(dispatcher.finalize_close())

    assert ledger.lease(original.resource) == replacement
    assert not event_payloads(ledger, "cleanup.receipt.recorded")
    assert not event_payloads(ledger, "task.closed")
    assert runtime.task("run-a", "task-a").state is TaskState.CLEANUP_PENDING
