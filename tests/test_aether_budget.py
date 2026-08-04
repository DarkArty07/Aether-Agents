"""Substrate-neutral budget behavior retained by Aether after kernel retirement."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from aether_agents.contracts.budget import (
    OBLIGATIONS,
    BudgetOverdrawn,
    BudgetTransitionError,
    FreshAdmissionRequired,
    IdempotencyError,
    reduce_budget,
    validate_budget_history,
)

RUNS = {"run-a": "contract-a"}
TASKS = {("run-a", "task-a"): object()}


def event(kind: str, command_id: str, amount: int, **payload):
    return {
        "aggregate": "budget:run-a",
        "kind": kind,
        "payload": {
            "run_id": "run-a",
            "contract_id": "contract-a",
            "command_id": command_id,
            "amount": amount,
            **payload,
        },
    }


def reservation(command_id: str = "reserve-1", amount: int = 30, **payload):
    payload.setdefault("reservation_id", "reservation:run-a:one")
    payload.setdefault("obligations", [])
    return event("budget.reserved", command_id, amount, **payload)


def test_budget_conservation_and_immutable_projection():
    events = [
        reservation(),
        event("budget.committed", "commit-1", 10, reservation_id="reservation:run-a:one"),
        event("budget.spent", "spend-1", 7, reservation_id="reservation:run-a:one"),
        event("budget.released", "release-1", 13, reservation_id="reservation:run-a:one"),
    ]

    state, reservations, admissions = reduce_budget(events, 100)

    assert state.available + state.reserved + state.committed + state.spent == state.authorized
    assert (state.available, state.reserved, state.committed, state.spent, state.released) == (83, 7, 3, 7, 13)
    assert reservations["reservation:run-a:one"]["spent"] == 7
    assert admissions == {}
    with pytest.raises((FrozenInstanceError, AttributeError)):
        setattr(state, "authorized", 1)


def test_release_returns_unused_reservation_without_erasing_spend():
    state, _, _ = reduce_budget(
        [
            reservation(amount=20),
            event("budget.committed", "commit-1", 12, reservation_id="reservation:run-a:one"),
            event("budget.spent", "spend-1", 5, reservation_id="reservation:run-a:one"),
            event("budget.released", "release-1", 8, reservation_id="reservation:run-a:one"),
        ],
        100,
    )

    assert (state.available, state.reserved, state.committed, state.spent, state.released) == (88, 0, 7, 5, 8)


def test_budget_cannot_overdraw_authorized_limit():
    with pytest.raises(BudgetOverdrawn):
        reduce_budget([reservation(amount=101)], 100)


@pytest.mark.parametrize("amount", [True, 0, -1, 1.5])
def test_budget_rejects_non_positive_or_non_integer_amounts(amount):
    with pytest.raises(BudgetTransitionError):
        reduce_budget([reservation(amount=amount)], 100)


def test_budget_rejects_reused_command_and_reservation_identities():
    with pytest.raises(IdempotencyError, match="command"):
        reduce_budget(
            [
                reservation(),
                event("budget.committed", "reserve-1", 1, reservation_id="reservation:run-a:one"),
            ],
            100,
        )
    with pytest.raises(IdempotencyError, match="reservation"):
        reduce_budget(
            [
                reservation(),
                reservation("reserve-2", reservation_id="reservation:run-a:one"),
            ],
            100,
        )


def test_correction_reservations_require_the_complete_obligation_set():
    valid = reservation(task_id="task-a", obligations=list(OBLIGATIONS))
    validate_budget_history([valid], authorized=100, runs=RUNS, tasks=TASKS)

    invalid = reservation(task_id="task-a", obligations=["verification"])
    with pytest.raises(BudgetTransitionError, match="obligations"):
        validate_budget_history([invalid], authorized=100, runs=RUNS, tasks=TASKS)


def test_retry_or_replan_requires_a_fresh_unconsumed_admission():
    admitted = event(
        "budget.retry_admitted",
        "admit-1",
        10,
        reservation_id="retry:run-a:task-a:one",
        admission_id="admission:run-a:task-a:one",
        task_id="task-a",
    )
    retried = event(
        "budget.retry_task",
        "retry-1",
        10,
        reservation_id="retry:run-a:task-a:one",
        admission_id="admission:run-a:task-a:one",
        task_id="task-a",
    )
    replanned = event(
        "budget.replan_task",
        "replan-1",
        10,
        reservation_id="retry:run-a:task-a:one",
        admission_id="admission:run-a:task-a:one",
        task_id="task-a",
    )

    _, _, admissions = reduce_budget([admitted, retried], 100)
    assert admissions["admission:run-a:task-a:one"]["consumed"] is True
    with pytest.raises(FreshAdmissionRequired):
        reduce_budget([admitted, retried, replanned], 100)


def test_spending_an_admission_consumes_it_before_retry():
    events = [
        event(
            "budget.retry_admitted",
            "admit-1",
            10,
            reservation_id="retry:run-a:task-a:one",
            admission_id="admission:run-a:task-a:one",
            task_id="task-a",
        ),
        event("budget.committed", "commit-1", 4, reservation_id="retry:run-a:task-a:one"),
        event("budget.spent", "spend-1", 4, reservation_id="retry:run-a:task-a:one"),
        event(
            "budget.retry_task",
            "retry-1",
            10,
            reservation_id="retry:run-a:task-a:one",
            admission_id="admission:run-a:task-a:one",
            task_id="task-a",
        ),
    ]

    with pytest.raises(FreshAdmissionRequired):
        reduce_budget(events, 100)


def test_history_validation_requires_explicit_run_and_task_projections():
    with pytest.raises(BudgetTransitionError, match="projection"):
        validate_budget_history([reservation()], authorized=100)

    validate_budget_history([reservation()], authorized=100, runs=RUNS, tasks=TASKS)


def test_history_validation_rejects_unknown_runs_contracts_and_tasks():
    ghost_run = {**reservation(), "aggregate": "budget:ghost"}
    ghost_run["payload"] = {**ghost_run["payload"], "run_id": "ghost"}
    with pytest.raises(BudgetTransitionError, match="run"):
        validate_budget_history([ghost_run], authorized=100, runs=RUNS, tasks=TASKS)

    wrong_contract = reservation()
    wrong_contract["payload"] = {**wrong_contract["payload"], "contract_id": "contract-b"}
    with pytest.raises(BudgetTransitionError, match="contract"):
        validate_budget_history([wrong_contract], authorized=100, runs=RUNS, tasks=TASKS)

    ghost_task = reservation(task_id="ghost", obligations=list(OBLIGATIONS))
    with pytest.raises(BudgetTransitionError, match="task"):
        validate_budget_history([ghost_task], authorized=100, runs=RUNS, tasks=TASKS)
