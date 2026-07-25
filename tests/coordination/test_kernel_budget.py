"""RED contracts for ledger-authorized budget commands."""

from __future__ import annotations

import importlib
import inspect
from concurrent.futures import ThreadPoolExecutor
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
    amend_contract,
)
from olympus_v3.coordination.budget import OBLIGATIONS

PROJECT = "project-a"
OWNER = Principal(PROJECT, "hermes", "owner")
WORKER = Principal(PROJECT, "hermes", "worker")


def budget_api():
    try:
        budget = importlib.import_module("olympus_v3.coordination.budget")
        runtime = importlib.import_module("olympus_v3.coordination.kernel_runtime")
    except ModuleNotFoundError as exc:
        pytest.fail(f"missing kernel budget capability: {exc.name}", pytrace=False)
    return budget, runtime


def contract(*, model_budget: int = 100) -> ExecutionContract:
    return ExecutionContract(
        contract_id="contract-a", project_id=PROJECT, generation=0, owner=OWNER,
        participants=(OWNER, WORKER), objective="build the feature", expected_outcome="verified feature",
        included_scopes=("src/",), excluded_scopes=("secrets/",), role_permissions={"worker": ("implement",)},
        evidence_gates=(EvidenceGate("qa", True),), side_effect_policy=SideEffectPolicy(("filesystem",), 2, True),
        limits=ContractLimits(2, 60, 3, model_budget, 1, 1), escalation_conditions=("ambiguity",),
        completion_authority=OWNER, amendment_authority=OWNER, status=ContractState.ACTIVE,
    )


def open_runtime(path: Path, *, model_budget: int = 100, writer_id: str = "owner", key_id: str = "key-owner", provision: bool = True):
    scope = StoreScope("install-a", PROJECT)
    auth = HMACWriterAuthenticator({(writer_id, key_id): b"owner-key"})
    signer = HMACIntegritySigner(b"integrity-key", key_id="integrity-a")
    ledger = SQLiteLedger(path, scope, writer_authenticator=auth, integrity_signer=signer)
    lease = ledger.acquire_lease("ledger-" + writer_id, writer_id, ttl=10_000_000_000)
    assert lease.lease is not None
    context = WriterContext(scope, writer_id, key_id, "ledger-" + writer_id, lease.lease.epoch, lease.lease.expires_at)
    expected = contract(model_budget=model_budget)
    if provision:
        result = ledger.create_contract(expected)
        if result is Result.CAS_CONFLICT:
            assert ledger.read_contract("contract-a") == expected
        else:
            assert result in (Result.APPLIED, Result.DUPLICATE)
            assert ledger.read_contract("contract-a") == expected
    runtime = importlib.import_module("olympus_v3.coordination.kernel_runtime")
    return ledger, runtime.KernelRunService(ledger, writer=runtime.KernelWriter(context, auth)), context, auth


def test_budget_current_conservation_and_read_only_projection(tmp_path: Path):
    _, runtime = budget_api()
    ledger, service, _, _ = open_runtime(tmp_path / "budget.sqlite")
    service.create_run(run_id="run-a", contract_id="contract-a", mode="kernel")
    reservation = service.reserve_budget("run-a", amount=30, command_id="reserve-1")
    service.commit_budget("run-a", reservation_id=reservation.id, amount=10, command_id="commit-1")
    service.spend_budget("run-a", reservation_id=reservation.id, amount=7, command_id="spend-1")
    service.release_budget("run-a", reservation_id=reservation.id, amount=13, command_id="release-1")
    state = service.budget("run-a")
    assert state.authorized == 100
    assert state.available + state.reserved + state.committed + state.spent == state.authorized
    assert (state.available, state.reserved, state.committed, state.spent, state.released) == (83, 7, 3, 7, 13)
    with pytest.raises((AttributeError, TypeError)):
        state.authorized = 1


def test_correction_derives_obligations_and_rejects_insufficient_total_budget(tmp_path: Path):
    budget, runtime = budget_api()
    small_ledger, small, _, _ = open_runtime(tmp_path / "small.sqlite", model_budget=3)
    small.create_run(run_id="run-a", contract_id="contract-a", mode="kernel")
    small.create_task("run-a", task_id="task-a")
    with pytest.raises(budget.InsufficientObligations):
        small.reserve_correction("run-a", task_id="task-a", amount=20, command_id="correction-1")
    ledger, service, _, _ = open_runtime(tmp_path / "correction.sqlite")
    service.create_run(run_id="run-a", contract_id="contract-a", mode="kernel")
    service.create_task("run-a", task_id="task-a")
    reservation = service.reserve_correction("run-a", task_id="task-a", amount=20, command_id="correction-2")
    assert reservation.obligations == ("verification", "re_review", "recovery", "cleanup")


def test_retry_and_replan_require_fresh_admission(tmp_path: Path):
    budget, runtime = budget_api()
    ledger, service, _, _ = open_runtime(tmp_path / "admission.sqlite")
    service.create_run(run_id="run-a", contract_id="contract-a", mode="kernel")
    service.create_task("run-a", task_id="task-a")
    admission = service.admit_retry("run-a", task_id="task-a", amount=10, command_id="admit-1")
    service.commit_budget("run-a", reservation_id=admission.reservation_id, amount=4, command_id="commit-1")
    service.spend_budget("run-a", reservation_id=admission.reservation_id, amount=4, command_id="spend-1")
    with pytest.raises(budget.FreshAdmissionRequired):
        service.retry_task("run-a", task_id="task-a", admission_id=admission.id, command_id="retry-1")
    with pytest.raises(budget.FreshAdmissionRequired):
        service.replan_task("run-a", task_id="task-a", admission_id=admission.id, command_id="replan-1")
    fresh = service.admit_retry("run-a", task_id="task-a", amount=10, command_id="admit-2")
    assert service.retry_task(
        "run-a", task_id="task-a", admission_id=fresh.id, command_id="retry-2"
    ).status == "admitted"


def test_release_returns_unused_reservation_without_erasing_spend(tmp_path: Path):
    _, runtime = budget_api()
    ledger, service, _, _ = open_runtime(tmp_path / "release.sqlite")
    service.create_run(run_id="run-a", contract_id="contract-a", mode="kernel")
    reservation = service.reserve_budget("run-a", amount=20, command_id="reserve-1")
    service.commit_budget("run-a", reservation_id=reservation.id, amount=12, command_id="commit-1")
    service.spend_budget("run-a", reservation_id=reservation.id, amount=5, command_id="spend-1")
    service.release_budget("run-a", reservation_id=reservation.id, amount=8, command_id="release-1")
    state = service.budget("run-a")
    assert state.spent == 5 and state.released == 8 and state.available == 88


def test_contract_elevation_requires_authenticated_ledger_amendment(tmp_path: Path):
    _, runtime = budget_api()
    ledger, service, context, auth = open_runtime(tmp_path / "authority.sqlite")
    service.create_run(run_id="run-a", contract_id="contract-a", mode="kernel")
    increased = ContractLimits(2, 60, 3, 110, 1, 1)
    amendment = amend_contract(ledger.read_contract("contract-a"), rationale="increase approved capacity", issuer=OWNER, affected_identities=("budget",), limits=increased)
    forged = amend_contract(ledger.read_contract("contract-a"), rationale="forged capacity", issuer=OWNER, affected_identities=("other",), limits=increased)
    proof = auth.sign(ledger._amendment_draft(amendment, context), context)
    assert ledger.advance_contract(forged, context, expected_generation=0, expected_revocation_epoch=0, proof=proof) is Result.AUTHENTICATION_FAILED
    service.refresh_contract_authority("run-a")
    assert service.budget("run-a").authorized == 100
    assert ledger.advance_contract(amendment, context, expected_generation=0, expected_revocation_epoch=0, proof=proof) is Result.APPLIED
    service.refresh_contract_authority("run-a")
    assert service.budget("run-a").authorized == 110
    assert "raise_authorized" not in dir(service)


def test_budget_rebuild_is_read_only_and_restores_projection(tmp_path: Path):
    _, runtime = budget_api()
    ledger, service, _, _ = open_runtime(tmp_path / "rebuild.sqlite")
    service.create_run(run_id="run-a", contract_id="contract-a", mode="kernel")
    reservation = service.reserve_budget("run-a", amount=30, command_id="reserve-1")
    service.commit_budget("run-a", reservation_id=reservation.id, amount=10, command_id="commit-1")
    service.spend_budget("run-a", reservation_id=reservation.id, amount=7, command_id="spend-1")
    service.release_budget("run-a", reservation_id=reservation.id, amount=13, command_id="release-1")
    assert runtime.KernelRunService.rebuild(ledger).budget("run-a") == service.budget("run-a")


def test_illegal_budget_boundaries_and_repeated_identity_are_rejected(tmp_path: Path):
    budget, runtime = budget_api()
    ledger, service, _, _ = open_runtime(tmp_path / "boundaries.sqlite")
    service.create_run(run_id="run-a", contract_id="contract-a", mode="kernel")
    reservation = service.reserve_budget("run-a", amount=10, command_id="reserve-1")
    with pytest.raises(budget.BudgetTransitionError):
        service.commit_budget("run-a", reservation_id=reservation.id, amount=11, command_id="commit-bad")
    with pytest.raises(budget.BudgetTransitionError):
        service.spend_budget("run-a", reservation_id=reservation.id, amount=1, command_id="spend-bad")
    service.commit_budget("run-a", reservation_id=reservation.id, amount=5, command_id="commit-1")
    with pytest.raises(budget.BudgetTransitionError):
        service.release_budget("run-a", reservation_id=reservation.id, amount=6, command_id="release-bad")
    service.spend_budget("run-a", reservation_id=reservation.id, amount=5, command_id="spend-1")
    with pytest.raises((budget.BudgetTransitionError, budget.IdempotencyError)):
        service.spend_budget("run-a", reservation_id=reservation.id, amount=5, command_id="spend-1")


def test_command_boundary_does_not_accept_caller_projection_or_semantic_outcome(tmp_path: Path):
    _, runtime = budget_api()
    ledger, service, _, _ = open_runtime(tmp_path / "boundary.sqlite")
    service.create_run(run_id="run-a", contract_id="contract-a", mode="kernel")
    for method in (service.reserve_budget, service.commit_budget, service.spend_budget, service.release_budget):
        parameters = inspect.signature(method).parameters
        assert not {"state", "outcome", "balance", "authority"} & set(parameters)


def test_generic_budget_append_requires_current_authority_metadata(tmp_path: Path):
    ledger, service, context, auth = open_runtime(tmp_path / "raw-budget-authority.sqlite")
    service.create_run(run_id="run-a", contract_id="contract-a", mode="kernel")
    draft = ledger.draft(
        "budget:run-a",
        "budget.reserved",
        {
            "run_id": "run-a",
            "contract_id": "contract-a",
            "reservation_id": "reservation:run-a:raw",
            "amount": 10,
            "obligations": (),
            "command_id": "raw-reserve",
        },
        writer=context,
        expected_version=0,
    )
    signed = auth.sign(draft, context)
    assert ledger.append(signed, context, message_id="raw-budget-authority").status in (
        Result.INVALID_INPUT,
        Result.STALE_AUTHORITY,
    )
    assert ledger.conn.execute("SELECT COUNT(*) FROM events WHERE kind='budget.reserved'").fetchone()[0] == 0


def test_concurrent_independent_services_allow_only_one_reservation(tmp_path: Path):
    _, runtime = budget_api()
    path = tmp_path / "concurrent.sqlite"
    ledger, service, _, _ = open_runtime(path)
    service.create_run(run_id="run-a", contract_id="contract-a", mode="kernel")
    ledger.close()

    def reserve(writer_id: str):
        ledger, service, _, _ = open_runtime(path, writer_id=writer_id, key_id="key-" + writer_id, provision=False)
        try:
            return service.reserve_budget("run-a", amount=60, command_id="reserve-" + writer_id)
        except (budget_api()[0].BudgetOverdrawn, ValueError):
            return None
        finally:
            ledger.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(reserve, ("writer-1", "writer-2")))
    assert sum(result is not None for result in results) == 1
    ledger, service, _, _ = open_runtime(path, writer_id="reader", key_id="key-reader", provision=False)
    assert service.budget("run-a").reserved == 60


def _raw_budget_append(ledger, context, auth, *, payload, aggregate="budget:run-a", kind="budget.reserved", version=0):
    draft = ledger.draft(
        aggregate,
        kind,
        payload,
        writer=context,
        expected_version=version,
        contract_generation=0,
        revocation_epoch=0,
    )
    return ledger.append(auth.sign(draft, context), context, message_id="raw-" + str(payload.get("command_id")))


@pytest.mark.parametrize("amount", [1.5, True, 0, -1])
def test_generic_budget_append_rejects_non_positive_integer_amount_without_mutation(tmp_path: Path, amount):
    ledger, service, context, auth = open_runtime(tmp_path / ("amount-" + str(amount) + ".sqlite"))
    service.create_run(run_id="run-a", contract_id="contract-a", mode="kernel")
    before = len(ledger.events())
    result = _raw_budget_append(
        ledger,
        context,
        auth,
        payload={
            "run_id": "run-a", "contract_id": "contract-a", "reservation_id": "reservation:run-a:raw",
            "amount": amount, "obligations": [], "command_id": "raw-amount",
        },
    )
    assert result.status is Result.INVALID_INPUT
    assert len(ledger.events()) == before
    assert ledger.projection("run:run-a")["run_id"] == "run-a"


@pytest.mark.parametrize(
    "payload,aggregate",
    [
        ({"contract_id": "contract-a", "reservation_id": "reservation:run-a:x", "amount": 1, "obligations": [], "command_id": "x"}, "budget:run-a"),
        ({"run_id": "ghost", "contract_id": "contract-a", "reservation_id": "reservation:ghost:x", "amount": 1, "obligations": [], "command_id": "x"}, "budget:ghost"),
        ({"run_id": "run-a", "contract_id": "contract-b", "reservation_id": "reservation:run-a:x", "amount": 1, "obligations": [], "command_id": "x"}, "budget:run-a"),
        ({"run_id": "run-a", "contract_id": "contract-a", "reservation_id": "reservation:run-a:x", "amount": 1, "obligations": [], "command_id": "x"}, "run:run-a"),
        ({"run_id": "run-a", "contract_id": "contract-a", "reservation_id": None, "amount": 1, "obligations": [], "command_id": "x"}, "budget:run-a"),
        ({"run_id": "run-a", "contract_id": "contract-a", "reservation_id": "", "amount": 1, "obligations": [], "command_id": "x"}, "budget:run-a"),
    ],
)
def test_generic_budget_append_rejects_orphan_scope_and_missing_identity_without_mutation(tmp_path: Path, payload, aggregate):
    ledger, service, context, auth = open_runtime(tmp_path / ("scope-" + str(payload.get("run_id")) + ".sqlite"))
    service.create_run(run_id="run-a", contract_id="contract-a", mode="kernel")
    before = (len(ledger.events()), ledger.projection("run:run-a"), len(ledger.outbox()), ledger.contract())
    result = _raw_budget_append(ledger, context, auth, payload=payload, aggregate=aggregate)
    assert result.status in (Result.INVALID_INPUT, Result.STALE_AUTHORITY)
    assert (len(ledger.events()), ledger.projection("run:run-a"), len(ledger.outbox()), ledger.contract()) == before


def test_generic_budget_append_positive_control_and_cross_run_reference_fail_closed(tmp_path: Path):
    ledger, service, context, auth = open_runtime(tmp_path / "identity.sqlite")
    service.create_run(run_id="run-a", contract_id="contract-a", mode="kernel")
    accepted = _raw_budget_append(
        ledger, context, auth,
        payload={
            "run_id": "run-a", "contract_id": "contract-a", "reservation_id": "reservation:run-a:raw",
            "amount": 1, "obligations": [], "command_id": "raw-positive",
        },
    )
    assert accepted.status is Result.APPLIED
    before = len(ledger.events())
    rejected = _raw_budget_append(
        ledger, context, auth,
        kind="budget.committed", version=1,
        payload={
            "run_id": "run-a", "contract_id": "contract-a", "reservation_id": "reservation:run-b:foreign",
            "amount": 1, "command_id": "raw-cross-run",
        },
    )
    assert rejected.status is Result.INVALID_INPUT
    assert len(ledger.events()) == before


@pytest.mark.parametrize("receive", [False, True])
@pytest.mark.parametrize(
    "kind,payload",
    [
        (
            "budget.reserved",
            {
                "run_id": "run-a", "contract_id": "contract-a", "reservation_id": "correction:run-a:ghost:c1",
                "task_id": "ghost", "amount": 1, "obligations": ["verification", "re_review", "recovery", "cleanup"],
                "command_id": "c1",
            },
        ),
        (
            "budget.retry_admitted",
            {
                "run_id": "run-a", "contract_id": "contract-a", "reservation_id": "retry:run-a:ghost:a1",
                "admission_id": "admission:run-a:ghost:a1", "task_id": "ghost", "amount": 1,
                "command_id": "a1",
            },
        ),
    ],
)
def test_direct_append_and_receive_reject_ghost_task_without_mutation(tmp_path: Path, receive, kind, payload):
    ledger, service, context, auth = open_runtime(tmp_path / f"ghost-{receive}-{kind}.sqlite")
    service.create_run(run_id="run-a", contract_id="contract-a", mode="kernel")
    before = (
        len(ledger.events()),
        ledger.projection("run:run-a"),
        len(ledger.outbox()),
        ledger.conn.execute("SELECT COUNT(*) FROM inbox").fetchone()[0],
    )
    draft = ledger.draft(
        "budget:run-a", kind, payload, writer=context, expected_version=0, contract_generation=0, revocation_epoch=0
    )
    signed = auth.sign(draft, context)
    result = ledger.receive("ghost-receive" if receive else "ghost-append", signed, context) if receive else ledger.append(
        signed, context, message_id="ghost-append"
    )
    assert result.status is Result.INVALID_INPUT
    assert (
        len(ledger.events()),
        ledger.projection("run:run-a"),
        len(ledger.outbox()),
        ledger.conn.execute("SELECT COUNT(*) FROM inbox").fetchone()[0],
    ) == before


def test_direct_append_accepts_only_same_run_task_control_and_rejects_foreign_run(tmp_path: Path):
    ledger, service, context, auth = open_runtime(tmp_path / "task-binding.sqlite")
    service.create_run(run_id="run-a", contract_id="contract-a", mode="kernel")
    service.create_run(run_id="run-b", contract_id="contract-a", mode="kernel")
    service.create_task("run-b", task_id="task-a")

    foreign = {
        "run_id": "run-a", "contract_id": "contract-a", "reservation_id": "correction:run-a:task-a:foreign",
        "task_id": "task-a", "amount": 1, "obligations": list(OBLIGATIONS),
        "command_id": "foreign",
    }
    before = len(ledger.events())
    draft = ledger.draft("budget:run-a", "budget.reserved", foreign, writer=context, contract_generation=0, revocation_epoch=0)
    assert ledger.append(auth.sign(draft, context), context, message_id="foreign").status is Result.INVALID_INPUT
    assert len(ledger.events()) == before

    service.create_task("run-a", task_id="task-a")
    valid = {**foreign, "reservation_id": "correction:run-a:task-a:valid", "command_id": "valid"}
    draft = ledger.draft("budget:run-a", "budget.reserved", valid, writer=context, contract_generation=0, revocation_epoch=0)
    assert ledger.append(auth.sign(draft, context), context, message_id="valid").status is Result.APPLIED
