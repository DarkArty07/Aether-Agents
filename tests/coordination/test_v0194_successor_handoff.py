from __future__ import annotations

import concurrent.futures
import inspect
import json
import threading
from dataclasses import replace
from pathlib import Path

import pytest
from test_harmonia_lease_lifecycle import (
    EffectBarrier,
    FakeClock,
    TerminalObservation,
    event_payloads,
    run,
    write_result_artifact,
)

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
from olympus_v3.coordination.closure import CompletionState
from olympus_v3.coordination.harmonia_runtime import ProjectRuntimeContext
from olympus_v3.coordination.harmonia_selection import (
    Candidate,
    KernelSelectionValidator,
    Prerequisite,
    SelectionAuthority,
    derive_projection,
    propose_selection,
)
from olympus_v3.coordination.kernel_dispatcher import DispatchRejected, KernelDispatcher
from olympus_v3.coordination.kernel_runtime import KernelRunService, KernelWriter
from olympus_v3.coordination.selection_commit import KernelSelectionCommitter

PROJECT = "project-a"
OWNER = Principal(PROJECT, "hermes", "owner")
WORKER_A = Principal(PROJECT, "hermes", "worker-a")
WORKER_B = Principal(PROJECT, "hermes", "worker-b")
WORKER_C = Principal(PROJECT, "hermes", "worker-c")


def two_successor_contract() -> ExecutionContract:
    return ExecutionContract(
        contract_id="contract-two-successors",
        project_id=PROJECT,
        generation=0,
        owner=OWNER,
        participants=(OWNER, WORKER_A, WORKER_B, WORKER_C),
        objective="two bounded successors",
        expected_outcome="verified successor dispatch",
        included_scopes=("src/",),
        excluded_scopes=("secrets/",),
        role_permissions={"worker-a": ("implement",), "worker-b": ("verify",), "worker-c": ("verify",)},
        evidence_gates=(EvidenceGate("qa", True),),
        side_effect_policy=SideEffectPolicy(("filesystem",), 2, True),
        limits=ContractLimits(2, 60, 3, 100, 1, 1),
        escalation_conditions=("ambiguity",),
        completion_authority=OWNER,
        amendment_authority=OWNER,
        status=ContractState.ACTIVE,
        task_worker_bindings={"task-a": WORKER_A, "task-b": WORKER_B, "task-c": WORKER_C},
    )


def fixed_contract() -> ExecutionContract:
    return ExecutionContract(
        contract_id="contract-fixed",
        project_id=PROJECT,
        generation=0,
        owner=OWNER,
        participants=(OWNER, WORKER_A, WORKER_B),
        objective="fixed A to B",
        expected_outcome="verified handoff",
        included_scopes=("src/",),
        excluded_scopes=("secrets/",),
        role_permissions={"worker-a": ("implement",), "worker-b": ("verify",)},
        evidence_gates=(EvidenceGate("qa", True),),
        side_effect_policy=SideEffectPolicy(("filesystem",), 2, True),
        limits=ContractLimits(2, 60, 3, 100, 1, 1),
        escalation_conditions=("ambiguity",),
        completion_authority=OWNER,
        amendment_authority=OWNER,
        status=ContractState.ACTIVE,
        task_worker_bindings={"task-a": WORKER_A, "task-b": WORKER_B},
    )


def commit_task_b_selection(ledger, dispatcher, *, epoch=1):
    authority = SelectionAuthority(
        "install-a", PROJECT, "run-fixed", "contract-fixed", 0, 0, epoch, 2, "sha256:selection-snapshot"
    )
    candidate = Candidate(
        "task-b", "worker-b", "sha256:binding-task-b",
        (Prerequisite("task-a", "receipt-a", "cleanup-a", TaskState.CLOSED),), TaskState.PROPOSED, True,
    )
    projection = derive_projection(
        authority, (candidate,), approved_task_ids=("task-b",), bindings={"task-b": "worker-b"}
    )
    proposal = propose_selection(projection)
    result = KernelSelectionCommitter(ledger, dispatcher._writer.context).commit(
        proposal, projection,
        KernelSelectionValidator(authority, (candidate,), approved_task_ids=("task-b",), bindings={"task-b": "worker-b"}),
    )
    assert result.status is Result.APPLIED
    return result


def commit_selection(ledger, dispatcher, *, run_id, contract_id, task_id, worker_id, epoch=1):
    authority = SelectionAuthority(
        "install-a", PROJECT, run_id, contract_id, 0, 0, epoch, 2, "sha256:selection-snapshot"
    )
    candidate = Candidate(
        task_id, worker_id, f"sha256:binding-{task_id}",
        (Prerequisite("task-a", "receipt-a", "cleanup-a", TaskState.CLOSED),), TaskState.PROPOSED, True,
    )
    projection = derive_projection(authority, (candidate,), approved_task_ids=(task_id,), bindings={task_id: worker_id})
    proposal = propose_selection(projection)
    result = KernelSelectionCommitter(ledger, dispatcher._writer.context).commit(
        proposal, projection,
        KernelSelectionValidator(authority, (candidate,), approved_task_ids=(task_id,), bindings={task_id: worker_id}),
    )
    assert result.status is Result.APPLIED
    return result


@pytest.fixture
def closed_source(tmp_path: Path):
    clock = FakeClock()
    scope = StoreScope("install-a", PROJECT)
    auth = HMACWriterAuthenticator({("owner", "key-owner"): b"owner-key"})
    ledger = SQLiteLedger(
        tmp_path / "successor.sqlite",
        scope,
        writer_authenticator=auth,
        integrity_signer=HMACIntegritySigner(b"integrity-key"),
        clock=clock,
        busy_timeout_ms=5_000,
    )
    lease = ledger.acquire_lease("ledger-owner", "owner", ttl=100_000_000_000).lease
    assert lease is not None
    context = WriterContext(scope, "owner", "key-owner", "ledger-owner", lease.epoch, lease.expires_at)
    assert ledger.create_contract(fixed_contract()) in (Result.APPLIED, Result.DUPLICATE)
    runtime = KernelRunService(ledger, writer=KernelWriter(context, auth))
    runtime.create_run(run_id="run-fixed", contract_id="contract-fixed", mode="kernel")
    runtime.create_task("run-fixed", task_id="task-a")
    runtime.create_task("run-fixed", task_id="task-b", prerequisites=("task-a",))
    runtime.admit_task("run-fixed", "task-a")
    runtime.mark_task_ready("run-fixed", "task-a")
    runtime.dispatch_task("run-fixed", "task-a")
    attempt = runtime.start_attempt("run-fixed", "task-a")
    effects = EffectBarrier()
    dispatcher = KernelDispatcher(ledger=ledger, runtime=runtime, runtime_adapter=effects, worker_id="owner")
    root = tmp_path / "project"
    root.mkdir()
    envelope = dispatcher.stage_ready(
        "run-fixed",
        "task-a",
        attempt=attempt.attempt,
        project_root=str(root),
        plan_revision=1,
        snapshot_digest="sha256:initial",
    )
    authority = envelope.authority
    run(dispatcher.dispatch_with(authority))
    binding = event_payloads(ledger, "session.bound")[0]
    dispatcher.record_terminal_with(
        authority,
        TerminalObservation("completed", authority.logical_session, binding["acp_session_id"], authority.message_id),
    )
    write_result_artifact(authority, binding["acp_session_id"])
    assert dispatcher.record_evidence_with(authority) is Result.APPLIED
    runtime.request_close(
        authority=authority,
        proposed_state=CompletionState.COMPLETED,
        command_id="close-fixed-a",
    )
    assert run(dispatcher.cleanup_once())["outcome"] == "completed"
    assert run(dispatcher.finalize_close())["state"] == TaskState.CLOSED.value
    assert runtime.task("run-fixed", "task-a").state is TaskState.CLOSED
    assert runtime.task("run-fixed", "task-b").state is TaskState.PROPOSED
    yield clock, ledger, runtime, dispatcher, effects, root, context
    if not ledger._closed:
        ledger.close()


@pytest.fixture
def two_successor_source(tmp_path: Path):
    clock = FakeClock()
    scope = StoreScope("install-a", PROJECT)
    auth = HMACWriterAuthenticator({("owner", "key-owner"): b"owner-key"})
    ledger = SQLiteLedger(
        tmp_path / "two-successors.sqlite", scope,
        writer_authenticator=auth, integrity_signer=HMACIntegritySigner(b"integrity-key"),
        clock=clock, busy_timeout_ms=5_000,
    )
    lease = ledger.acquire_lease("ledger-owner", "owner", ttl=100_000_000_000).lease
    assert lease is not None
    writer_context = WriterContext(scope, "owner", "key-owner", "ledger-owner", lease.epoch, lease.expires_at)
    assert ledger.create_contract(two_successor_contract()) in (Result.APPLIED, Result.DUPLICATE)
    runtime = KernelRunService(ledger, writer=KernelWriter(writer_context, auth))
    runtime.create_run(run_id="run-two-successors", contract_id="contract-two-successors", mode="kernel")
    runtime.create_task("run-two-successors", task_id="task-a")
    runtime.create_task("run-two-successors", task_id="task-b", prerequisites=("task-a",))
    runtime.create_task("run-two-successors", task_id="task-c", prerequisites=("task-a",))
    runtime.admit_task("run-two-successors", "task-a")
    runtime.mark_task_ready("run-two-successors", "task-a")
    runtime.dispatch_task("run-two-successors", "task-a")
    attempt = runtime.start_attempt("run-two-successors", "task-a")
    effects = EffectBarrier()
    dispatcher = KernelDispatcher(ledger=ledger, runtime=runtime, runtime_adapter=effects, worker_id="owner")
    root = tmp_path / "two-successor-project"
    root.mkdir()
    envelope = dispatcher.stage_ready(
        "run-two-successors", "task-a", attempt=attempt.attempt, project_root=str(root),
        plan_revision=1, snapshot_digest="sha256:initial",
    )
    authority = envelope.authority
    run(dispatcher.dispatch_with(authority))
    binding = event_payloads(ledger, "session.bound")[0]
    dispatcher.record_terminal_with(
        authority, TerminalObservation("completed", authority.logical_session, binding["acp_session_id"], authority.message_id)
    )
    write_result_artifact(authority, binding["acp_session_id"])
    assert dispatcher.record_evidence_with(authority) is Result.APPLIED
    runtime.request_close(authority=authority, proposed_state=CompletionState.COMPLETED, command_id="close-two-successor-a")
    assert run(dispatcher.cleanup_once())["outcome"] == "completed"
    assert run(dispatcher.finalize_close())["state"] == TaskState.CLOSED.value
    context = ProjectRuntimeContext(None, None, ledger, runtime, None, dispatcher)
    yield clock, ledger, runtime, dispatcher, effects, root, writer_context, context
    if not ledger._closed:
        ledger.close()


def test_public_stage_ready_has_no_handoff_or_message_identity_override():
    parameters = inspect.signature(KernelDispatcher.stage_ready).parameters
    assert "handoff" not in parameters
    assert "_message_id" not in parameters


def test_closed_source_stages_exact_bound_successor_with_bounded_handoff(closed_source):
    _, ledger, runtime, dispatcher, _, root, _ = closed_source

    envelope = dispatcher.stage_successor(
        "run-fixed", "task-a", "task-b", project_root=str(root), plan_revision=2
    )

    assert envelope.authority.agent_name == "worker-b"
    assert runtime.task("run-fixed", "task-b").state is TaskState.RUNNING
    assert len(runtime.attempts("run-fixed", "task-b")) == 1
    handoff = envelope.payload["handoff"]
    assert set(handoff) == {
        "source_run_id",
        "source_task_id",
        "source_attempt",
        "source_receipt_id",
        "source_artifact_generation",
        "snapshot_relative_path",
        "snapshot_digest",
        "canonical_size_bytes",
    }
    assert "result" not in json.dumps(envelope.payload)
    staged_b = [
        payload
        for payload in event_payloads(ledger, "dispatch.staged")
        if payload["task_id"] == "task-b"
    ]
    assert len(staged_b) == 1
    assert staged_b[0]["handoff"] == handoff


def test_successor_live_prompt_contains_verified_handoff_and_own_result_contract(closed_source):
    _, _, _, dispatcher, effects, root, _ = closed_source
    envelope = dispatcher.stage_successor(
        "run-fixed", "task-a", "task-b", project_root=str(root), plan_revision=2
    )

    run(dispatcher.dispatch_with(envelope.authority))

    request = [payload for kind, payload in effects.calls if kind == "dispatch"][-1]
    prompt = json.loads(request["prompt"])
    assert prompt["handoff"] == envelope.payload["handoff"]
    assert "result" not in json.dumps(prompt["handoff"])
    assert prompt["result_artifact"]["relative_path"] == ".aether/evidence/run-fixed/task-b/1/result.json"
    assert prompt["result_artifact"]["document"]["task_id"] == "task-b"
    assert prompt["result_artifact"]["document"]["acp_session_id"]


def test_tampered_snapshot_rejects_without_advancing_successor(closed_source):
    _, _, runtime, dispatcher, _, root, _ = closed_source
    receipt = next(
        payload
        for payload in event_payloads(dispatcher.ledger, "evidence.receipt.recorded")
        if payload["task_id"] == "task-a"
    )
    path = root / receipt["handoff"]["snapshot_relative_path"]
    path.chmod(0o644)
    path.write_bytes(b"tampered")

    with pytest.raises(DispatchRejected):
        dispatcher.stage_successor(
            "run-fixed", "task-a", "task-b", project_root=str(root), plan_revision=2
        )

    assert runtime.task("run-fixed", "task-b").state is TaskState.PROPOSED
    assert runtime.attempts("run-fixed", "task-b") == ()


def test_successor_restart_replays_one_staged_obligation(closed_source):
    _, ledger, _, dispatcher, effects, root, context = closed_source
    first = dispatcher.stage_successor(
        "run-fixed", "task-a", "task-b", project_root=str(root), plan_revision=2
    )
    restarted_runtime = KernelRunService(ledger, writer=KernelWriter(context, dispatcher._writer.authenticator))
    restarted = KernelDispatcher(
        ledger=ledger,
        runtime=restarted_runtime,
        runtime_adapter=effects,
        worker_id="owner",
    )

    replay = restarted.stage_successor(
        "run-fixed", "task-a", "task-b", project_root=str(root), plan_revision=2
    )

    assert replay.authority.message_id == first.authority.message_id
    assert len(
        [p for p in event_payloads(ledger, "dispatch.staged") if p["task_id"] == "task-b"]
    ) == 1
    assert len(restarted_runtime.attempts("run-fixed", "task-b")) == 1


def test_successor_recovers_crash_after_attempt_before_staged_event(closed_source, monkeypatch):
    _, ledger, runtime, dispatcher, _, root, _ = closed_source
    original = dispatcher._stage_ready

    def crash_before_stage(*args, **kwargs):
        raise RuntimeError("crash before successor stage")

    monkeypatch.setattr(dispatcher, "_stage_ready", crash_before_stage)
    with pytest.raises(RuntimeError, match="crash before successor stage"):
        dispatcher.stage_successor(
            "run-fixed", "task-a", "task-b", project_root=str(root), plan_revision=2
        )
    assert runtime.task("run-fixed", "task-b").state is TaskState.RUNNING
    assert not [
        payload
        for payload in event_payloads(ledger, "dispatch.staged")
        if payload["task_id"] == "task-b"
    ]

    monkeypatch.setattr(dispatcher, "_stage_ready", original)
    recovered = dispatcher.stage_successor(
        "run-fixed", "task-a", "task-b", project_root=str(root), plan_revision=2
    )

    assert recovered.authority.agent_name == "worker-b"
    assert len(runtime.attempts("run-fixed", "task-b")) == 1
    assert len(
        [p for p in event_payloads(ledger, "dispatch.staged") if p["task_id"] == "task-b"]
    ) == 1


def test_two_sqlite_successor_consumers_converge_to_one_dispatch(closed_source):
    clock, ledger, _, _, effects, root, context = closed_source
    commit_task_b_selection(ledger, KernelDispatcher(
        ledger=ledger,
        runtime=KernelRunService(ledger, writer=KernelWriter(context, HMACWriterAuthenticator({("owner", "key-owner"): b"owner-key"}))),
        runtime_adapter=effects,
        worker_id="owner",
    ))
    barrier = threading.Barrier(2)

    def stage_from_connection():
        auth = HMACWriterAuthenticator({("owner", "key-owner"): b"owner-key"})
        local = SQLiteLedger(
            ledger.path,
            ledger.scope,
            writer_authenticator=auth,
            integrity_signer=HMACIntegritySigner(b"integrity-key"),
            clock=clock,
            busy_timeout_ms=5_000,
        )
        try:
            runtime = KernelRunService(local, writer=KernelWriter(context, auth))
            dispatcher = KernelDispatcher(
                ledger=local,
                runtime=runtime,
                runtime_adapter=effects,
                worker_id="owner",
            )
            barrier.wait(timeout=5)
            return dispatcher.stage_successor(
                "run-fixed", "task-a", "task-b", project_root=str(root), plan_revision=2,
                selection_epoch=1, selection_proposal_id=next(
                    json.loads(event["payload"])["proposal_id"]
                    for event in local.events() if event["kind"] == "task.selection.committed"
                ), selection_worker_id="worker-b",
            ).authority.message_id
        finally:
            local.close()

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        message_ids = tuple(executor.map(lambda _: stage_from_connection(), range(2)))

    assert message_ids[0] == message_ids[1]
    rebuilt = KernelRunService.rebuild(ledger)
    assert rebuilt.task("run-fixed", "task-b").state is TaskState.RUNNING
    assert len(rebuilt.attempts("run-fixed", "task-b")) == 1
    assert len(
        [p for p in event_payloads(ledger, "dispatch.staged") if p["task_id"] == "task-b"]
    ) == 1
    staged_ids = {
        event["event_id"]
        for event in ledger.events()
        if event["kind"] == "dispatch.staged"
        and json.loads(event["payload"])["task_id"] == "task-b"
    }
    assert len([row for row in ledger.outbox() if row["event_id"] in staged_ids]) == 1


def test_committed_selection_reconciliation_prevents_legacy_successor_fallback(closed_source):
    _, ledger, runtime, dispatcher, effects, root, _ = closed_source
    context = ProjectRuntimeContext(None, None, ledger, runtime, None, dispatcher)
    commit_task_b_selection(ledger, dispatcher)
    run(context.resume_monitors())
    staged = [p for p in event_payloads(ledger, "dispatch.staged") if p["task_id"] == "task-b"]
    assert len(staged) == 1
    assert staged[0]["selection_epoch"] == 1
    assert len(runtime.attempts("run-fixed", "task-b")) == 1


def test_committed_selection_reconciliation_stages_only_committed_candidate(closed_source):
    _, ledger, runtime, dispatcher, _, _, _ = closed_source
    context = ProjectRuntimeContext(None, None, ledger, runtime, None, dispatcher)
    commit_task_b_selection(ledger, dispatcher)
    run(context._stage_committed_selections())
    assert runtime.task("run-fixed", "task-b").state is TaskState.RUNNING
    assert len(runtime.attempts("run-fixed", "task-b")) == 1
    assert len([p for p in event_payloads(ledger, "dispatch.staged") if p["task_id"] == "task-b"]) == 1


def test_uncommitted_proposal_cannot_stage_dispatch(closed_source):
    _, ledger, runtime, dispatcher, _, _, _ = closed_source
    context = ProjectRuntimeContext(None, None, ledger, runtime, None, dispatcher)
    run(context._stage_committed_selections())
    assert runtime.task("run-fixed", "task-b").state is TaskState.PROPOSED
    assert not [p for p in event_payloads(ledger, "dispatch.staged") if p["task_id"] == "task-b"]


def test_committed_selection_restart_reconciles_once_with_epoch_bound_identity(closed_source):
    _, ledger, runtime, dispatcher, effects, _, _ = closed_source
    context = ProjectRuntimeContext(None, None, ledger, runtime, None, dispatcher)
    commit_task_b_selection(ledger, dispatcher, epoch=1)
    run(context._stage_committed_selections())
    writer_context = dispatcher._writer.context
    restarted_runtime = KernelRunService(ledger, writer=KernelWriter(writer_context, dispatcher._writer.authenticator))
    restarted = ProjectRuntimeContext(None, None, ledger, restarted_runtime, None, KernelDispatcher(
        ledger=ledger, runtime=restarted_runtime, runtime_adapter=effects, worker_id="owner"
    ))
    run(restarted._stage_committed_selections())
    staged = [p for p in event_payloads(ledger, "dispatch.staged") if p["task_id"] == "task-b"]
    assert len(staged) == 1
    assert staged[0]["selection_epoch"] == 1
    assert len(restarted_runtime.attempts("run-fixed", "task-b")) == 1


def test_two_successors_committed_b_reconciles_twice_and_preserves_c(two_successor_source):
    _, ledger, runtime, dispatcher, effects, _, _, context = two_successor_source
    commit = commit_selection(
        ledger, dispatcher, run_id="run-two-successors", contract_id="contract-two-successors",
        task_id="task-b", worker_id="worker-b",
    )
    run(context.resume_monitors())
    run(context.resume_monitors())
    staged_b = [p for p in event_payloads(ledger, "dispatch.staged") if p["task_id"] == "task-b"]
    staged_c = [p for p in event_payloads(ledger, "dispatch.staged") if p["task_id"] == "task-c"]
    assert len(staged_b) == 1
    assert staged_b[0]["selection_epoch"] == commit.decision.selection_epoch
    assert staged_c == []
    assert len(runtime.attempts("run-two-successors", "task-b")) == 1
    assert runtime.task("run-two-successors", "task-c").state is TaskState.PROPOSED
    assert runtime.attempts("run-two-successors", "task-c") == ()
    staged_id = next(event["event_id"] for event in ledger.events()
                     if event["kind"] == "dispatch.staged" and json.loads(event["payload"])["task_id"] == "task-b")
    assert len([row for row in ledger.outbox() if row["event_id"] == staged_id]) == 1
    assert len([payload for kind, payload in effects.calls if kind == "dispatch" and payload["task_id"] == "task-b"]) == 1
    assert len([p for p in event_payloads(ledger, "session.bound") if p["task_id"] == "task-b"]) == 1


def test_invalid_committed_selection_cannot_fallback_to_either_successor(two_successor_source, monkeypatch):
    _, ledger, runtime, dispatcher, effects, _, _, context = two_successor_source
    committed = commit_selection(
        ledger, dispatcher, run_id="run-two-successors", contract_id="contract-two-successors",
        task_id="task-b", worker_id="worker-b",
    )
    invalid = replace(committed.decision, resolved_worker_id="worker-c")
    monkeypatch.setattr(
        "olympus_v3.coordination.harmonia_runtime.rebuild_selection_decisions",
        lambda _: {(invalid.run_id, invalid.selection_epoch): invalid},
    )
    run(context.resume_monitors())
    assert runtime.task("run-two-successors", "task-b").state is TaskState.PROPOSED
    assert runtime.task("run-two-successors", "task-c").state is TaskState.PROPOSED
    assert runtime.attempts("run-two-successors", "task-b") == ()
    assert runtime.attempts("run-two-successors", "task-c") == ()
    assert [p for p in event_payloads(ledger, "dispatch.staged") if p["task_id"] in {"task-b", "task-c"}] == []
    assert [payload for kind, payload in effects.calls if kind == "dispatch" and payload["task_id"] in {"task-b", "task-c"}] == []


def test_two_independent_contexts_reconcile_committed_b_once(two_successor_source):
    clock, ledger, runtime, dispatcher, effects, _, writer_context, _ = two_successor_source
    commit_selection(
        ledger, dispatcher, run_id="run-two-successors", contract_id="contract-two-successors",
        task_id="task-b", worker_id="worker-b",
    )
    barrier = threading.Barrier(2)

    def reconcile_from_connection():
        auth = HMACWriterAuthenticator({("owner", "key-owner"): b"owner-key"})
        local = SQLiteLedger(
            ledger.path, ledger.scope, writer_authenticator=auth,
            integrity_signer=HMACIntegritySigner(b"integrity-key"), clock=clock, busy_timeout_ms=5_000,
        )
        try:
            local_runtime = KernelRunService(local, writer=KernelWriter(writer_context, auth))
            local_dispatcher = KernelDispatcher(ledger=local, runtime=local_runtime, runtime_adapter=effects, worker_id="owner")
            local_context = ProjectRuntimeContext(None, None, local, local_runtime, None, local_dispatcher)
            barrier.wait(timeout=5)
            run(local_context._stage_committed_selections())
        finally:
            local.close()

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        tuple(executor.map(lambda _: reconcile_from_connection(), range(2)))

    staged_b = [p for p in event_payloads(ledger, "dispatch.staged") if p["task_id"] == "task-b"]
    assert len(staged_b) == 1
    rebuilt = KernelRunService.rebuild(ledger)
    assert len(rebuilt.attempts("run-two-successors", "task-b")) == 1
    assert runtime.task("run-two-successors", "task-c").state is TaskState.PROPOSED
    assert runtime.attempts("run-two-successors", "task-c") == ()
    staged_id = next(event["event_id"] for event in ledger.events()
                     if event["kind"] == "dispatch.staged" and json.loads(event["payload"])["task_id"] == "task-b")
    assert len([row for row in ledger.outbox() if row["event_id"] == staged_id]) == 1
    assert len([payload for kind, payload in effects.calls if kind == "dispatch" and payload["task_id"] == "task-b"]) == 1
    assert len([p for p in event_payloads(ledger, "session.bound") if p["task_id"] == "task-b"]) == 1
