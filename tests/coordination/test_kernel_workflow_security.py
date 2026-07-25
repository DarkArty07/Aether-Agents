"""Adversarial tests for the authenticated kernel workflow boundary."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from olympus_v3.coordination import ContractState, Result, amend_contract
from olympus_v3.coordination.kernel_runtime import KernelRunService
from tests.coordination.test_kernel_workflow import OWNER, active_contract, open_runtime


def _signed(ledger, context, auth, aggregate, kind, payload, expected=0):
    draft = ledger.draft(
        aggregate,
        kind,
        payload,
        writer=context,
        expected_version=expected,
        contract_generation=0,
        revocation_epoch=0,
    )
    return auth.sign(draft, context)


@pytest.mark.parametrize(
    ("generation", "revocation_epoch", "status"),
    ((1, 1, ContractState.ACTIVE), (7, 4, ContractState.ACTIVE), (0, 0, ContractState.AMENDED)),
)
def test_contract_bootstrap_rejects_forged_or_non_genesis_authority(
    tmp_path: Path, generation: int, revocation_epoch: int, status: ContractState
):
    ledger, _, _, _ = open_runtime(
        tmp_path / f"bootstrap-{generation}-{revocation_epoch}-{status}.sqlite", provision=False
    )
    forged = replace(
        active_contract(),
        generation=generation,
        revocation_epoch=revocation_epoch,
        status=status,
    )
    assert ledger.create_contract(forged) is Result.INVALID_INPUT
    assert ledger.conn.execute("SELECT COUNT(*) FROM contract_versions").fetchone()[0] == 0
    assert ledger.conn.execute("SELECT COUNT(*) FROM contract_heads").fetchone()[0] == 0


def test_contract_bootstrap_is_initialization_only(tmp_path: Path):
    ledger, _, _, _ = open_runtime(tmp_path / "single-bootstrap.sqlite", provision=False)
    assert ledger.create_contract(active_contract()) is Result.APPLIED
    assert ledger.create_contract(replace(active_contract(), contract_id="contract-b")) is Result.CAS_CONFLICT
    assert ledger.conn.execute("SELECT COUNT(*) FROM contract_versions").fetchone()[0] == 1


def test_generic_ledger_rejects_workflow_events_under_proposed_contract(tmp_path: Path):
    ledger, _, context, auth = open_runtime(tmp_path / "proposed-bypass.sqlite", provision=False)
    assert ledger.create_contract(replace(active_contract(), status=ContractState.PROPOSED)) is Result.APPLIED
    draft = _signed(
        ledger,
        context,
        auth,
        "run:run-a",
        "run.created",
        {"run_id": "run-a", "contract_id": "contract-a", "mode": "kernel"},
    )
    assert ledger.append(draft, context, message_id="proposed-bypass").status is Result.STALE_AUTHORITY
    assert ledger.conn.execute("SELECT COUNT(*) FROM events WHERE kind='run.created'").fetchone()[0] == 0


@pytest.mark.parametrize(
    "authority",
    ({}, {"contract_generation": 0}, {"revocation_epoch": 0}),
)
def test_generic_workflow_append_requires_complete_current_authority(tmp_path: Path, authority):
    ledger, _, context, auth = open_runtime(tmp_path / ("authority-" + str(len(authority)) + ".sqlite"))
    draft = ledger.draft(
        "run:run-a",
        "run.created",
        {"run_id": "run-a", "contract_id": "contract-a", "mode": "kernel"},
        writer=context,
        **authority,
    )
    signed = auth.sign(draft, context)
    before = {table: ledger.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in ("events", "projections", "inbox", "outbox")}
    assert ledger.append(signed, context, message_id="missing-authority").status in (Result.INVALID_INPUT, Result.STALE_AUTHORITY)
    after = {table: ledger.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in before}
    assert after == before


def test_receive_rejects_workflow_event_without_authority_metadata(tmp_path: Path):
    ledger, _, context, auth = open_runtime(tmp_path / "receive-missing-authority.sqlite")
    draft = ledger.draft(
        "run:run-a",
        "run.created",
        {"run_id": "run-a", "contract_id": "contract-a", "mode": "kernel"},
        writer=context,
    )
    signed = auth.sign(draft, context)
    assert ledger.receive("receive-missing-authority", signed, context).status is Result.INVALID_INPUT
    assert ledger.conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 0


def test_generic_append_rejects_contract_advance_without_mutation(tmp_path: Path):
    ledger, _, context, auth = open_runtime(tmp_path / "generic-amendment.sqlite")
    draft = ledger.draft(
        "contract",
        "contract.advance",
        {"contract_id": "contract-a", "forged": True},
        writer=context,
        contract_generation=0,
        revocation_epoch=0,
    )
    signed = auth.sign(draft, context)
    before = {table: ledger.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in ("events", "projections", "contract_versions", "contract_heads", "inbox", "outbox")}
    assert ledger.append(signed, context, message_id="forged-amendment").status is Result.INVALID_INPUT
    after = {table: ledger.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in before}
    assert after == before


@pytest.mark.parametrize("completion_id", ("missing-event", "unrelated-event"))
def test_complete_outbox_rejects_unbound_completion_evidence(tmp_path: Path, completion_id: str):
    ledger, service, _, _ = open_runtime(tmp_path / (completion_id + ".sqlite"))
    service.create_run(run_id="run-a", contract_id="contract-a", mode="kernel")
    lease = ledger.acquire_lease("outbox", "transport-a", ttl=10_000_000_000).lease
    assert lease is not None
    claimed = ledger.claim_outbox("transport-a", lease=lease)
    message_id = claimed[0]["message_id"]
    assert ledger.mark_outbox_sent(message_id, "transport-a", lease=lease) is Result.TRANSPORT_ACKNOWLEDGED
    assert ledger.outbox()[0]["semantic_completion_event_id"] is None
    assert ledger.complete_outbox(message_id, completion_id) is Result.INVALID_INPUT
    assert ledger.outbox()[0]["semantic_completion_event_id"] is None


def test_current_authority_cannot_forge_completed_task_creation(tmp_path: Path):
    ledger, service, context, auth = open_runtime(tmp_path / "forge.sqlite")
    service.create_run(run_id="run-a", contract_id="contract-a", mode="kernel")
    draft = _signed(
        ledger,
        context,
        auth,
        "task:run-a:task-a",
        "task.created",
        {
            "run_id": "run-a",
            "task_id": "task-a",
            "prerequisites": [],
            "contract_id": "contract-a",
            "state": "completed",
        },
    )
    result = ledger.append(draft, context, message_id="forged-task")
    assert result.status is Result.INVALID_INPUT
    assert ledger.conn.execute("SELECT COUNT(*) FROM events WHERE kind='task.created'").fetchone()[0] == 0


def test_out_of_order_and_identity_mismatch_are_atomic(tmp_path: Path):
    ledger, service, context, auth = open_runtime(tmp_path / "order.sqlite")
    draft = _signed(
        ledger,
        context,
        auth,
        "task:run-a:task-a",
        "task.created",
        {"run_id": "run-a", "task_id": "task-a", "prerequisites": [], "contract_id": "contract-a"},
    )
    assert ledger.append(draft, context, message_id="orphan-task").status is Result.INVALID_INPUT
    assert ledger.events() == []
    service.create_run(run_id="run-a", contract_id="contract-a", mode="kernel")
    bad = _signed(
        ledger,
        context,
        auth,
        "task:run-a:other",
        "task.created",
        {"run_id": "run-a", "task_id": "task-a", "prerequisites": [], "contract_id": "contract-a"},
    )
    assert ledger.append(bad, context, message_id="identity-mismatch").status is Result.INVALID_INPUT


def test_replay_and_projection_share_fail_closed_semantics_after_restart(tmp_path: Path):
    path = tmp_path / "restart.sqlite"
    ledger, service, _, _ = open_runtime(path)
    service.create_run(run_id="run-a", contract_id="contract-a", mode="kernel")
    service.create_task("run-a", task_id="task-a")
    service.admit_task("run-a", "task-a")
    service.mark_task_ready("run-a", "task-a")
    service.dispatch_task("run-a", "task-a")
    service.start_attempt("run-a", "task-a")
    service.bind_logical_session("run-a", "task-a", logical_session="session-a")
    assert ledger.verify_projections()
    rebuilt = KernelRunService.rebuild(ledger)
    assert rebuilt.task("run-a", "task-a") == service.task("run-a", "task-a")
    assert rebuilt.attempts("run-a", "task-a") == service.attempts("run-a", "task-a")
    assert rebuilt.sessions("run-a", "task-a") == service.sessions("run-a", "task-a")


def test_poison_event_has_independent_internal_proof_and_rebuilds(tmp_path: Path):
    ledger, service, _, _ = open_runtime(tmp_path / "poison.sqlite")
    service.create_run(run_id="run-a", contract_id="contract-a", mode="kernel")
    lease = ledger.acquire_lease("outbox", "transport-a", ttl=10_000_000_000)
    assert lease.lease is not None
    claimed = ledger.claim_outbox("transport-a", lease=lease.lease)
    assert claimed
    result = ledger.mark_outbox_retry("" + claimed[0]["message_id"], "transport-a", lease=lease.lease, max_attempts=1)
    assert result is Result.POISON_TERMINATED
    poison = next(row for row in ledger.events() if row["kind"] == "outbox.poison")
    assert (poison["writer_id"], poison["key_id"], poison["resource"]) == (
        "ledger-internal",
        ledger.integrity_signer.key_id,
        "ledger-integrity",
    )
    assert poison["writer_proof"] != ""
    assert KernelRunService.rebuild(ledger).run("run-a").run_id == "run-a"
    assert ledger.verify_projections()


def test_historical_events_remain_valid_after_authenticated_contract_amendment(tmp_path: Path):
    ledger, service, context, auth = open_runtime(tmp_path / "amendment.sqlite", writer_id=OWNER.actor_id)
    service.create_run(run_id="run-a", contract_id="contract-a", mode="kernel")
    service.create_task("run-a", task_id="task-a")
    contract = ledger.read_contract("contract-a")
    assert contract is not None
    amendment = amend_contract(
        contract,
        rationale="advance authority without rewriting history",
        issuer=OWNER,
        affected_identities=("task-a",),
    )
    proof = auth.sign(ledger._amendment_draft(amendment, context), context)
    assert (
        ledger.advance_contract(
            amendment,
            context,
            expected_generation=0,
            expected_revocation_epoch=0,
            proof=proof,
        )
        is Result.APPLIED
    )
    assert KernelRunService.rebuild(ledger).task("run-a", "task-a").state == "proposed"
    generations = {
        row[0]
        for row in ledger.conn.execute(
            "SELECT contract_generation FROM events WHERE kind IN ('run.created','task.created')"
        )
    }
    assert generations == {0}


def test_primary_append_failure_rolls_back_workflow_tables(tmp_path: Path):
    ledger, service, _, _ = open_runtime(tmp_path / "atomic.sqlite")
    service.create_run(run_id="run-a", contract_id="contract-a", mode="kernel")
    before = {
        table: ledger.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for table in ("events", "projections", "inbox", "outbox")
    }
    ledger.fault = lambda stage: (_ for _ in ()).throw(RuntimeError(stage)) if stage == "after_event_insert" else None
    with pytest.raises(RuntimeError):
        service.create_task("run-a", task_id="task-a")
    after = {table: ledger.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in before}
    assert after == before
    ledger.fault = None
    assert service.create_task("run-a", task_id="task-a").task_id == "task-a"
