"""Substrate-neutral Aether budget contracts and reducers."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass


class BudgetError(ValueError):
    pass


class BudgetTransitionError(BudgetError):
    pass


class BudgetOverdrawn(BudgetError):
    pass


class InsufficientObligations(BudgetError):
    pass


class FreshAdmissionRequired(BudgetError):
    pass


class IdempotencyError(BudgetError):
    pass


BUDGET_KINDS = frozenset(
    {
        "budget.reserved",
        "budget.committed",
        "budget.spent",
        "budget.released",
        "budget.retry_admitted",
        "budget.retry_task",
        "budget.replan_task",
    }
)
OBLIGATIONS = ("verification", "re_review", "recovery", "cleanup")
_IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9._:-]{0,127}$")
_MAX_INTEGER = (1 << 63) - 1


@dataclass(frozen=True, slots=True)
class BudgetState:
    authorized: int
    available: int
    reserved: int
    committed: int
    spent: int
    released: int


@dataclass(frozen=True, slots=True)
class Reservation:
    id: str
    run_id: str
    amount: int
    obligations: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Admission:
    id: str
    reservation_id: str
    run_id: str
    task_id: str
    amount: int


@dataclass(frozen=True, slots=True)
class RetryState:
    status: str
    admission_id: str
    task_id: str


def _events(events):
    return [e for e in events if e.get("kind") in BUDGET_KINDS]


def reduce_budget(events, authorized: int):
    if not isinstance(authorized, int) or authorized < 0:
        raise BudgetTransitionError("invalid authorized budget")
    reserved = committed = spent = released = 0
    reservations = {}
    admissions = {}
    commands = set()
    for event in _events(events):
        kind = event["kind"]
        payload = event.get("payload", {})
        if isinstance(payload, str):
            payload = json.loads(payload)
        if not isinstance(payload, dict):
            raise BudgetTransitionError("invalid budget payload")
        command = payload.get("command_id")
        if not isinstance(command, str) or command in commands:
            raise IdempotencyError("reused command identity")
        commands.add(command)
        amount = payload.get("amount", 0)
        if not isinstance(amount, int) or isinstance(amount, bool) or amount <= 0 or amount > _MAX_INTEGER:
            raise BudgetTransitionError("invalid budget amount")
        if kind == "budget.reserved":
            rid = payload.get("reservation_id")
            if rid in reservations:
                raise IdempotencyError("reused reservation identity")
            if reserved + committed + spent + amount > authorized:
                raise BudgetOverdrawn("budget overdrawn")
            obligations = tuple(payload.get("obligations", ()))
            if obligations not in ((), OBLIGATIONS):
                raise BudgetTransitionError("invalid correction obligations")
            reservations[rid] = {
                "run_id": payload["run_id"],
                "amount": amount,
                "reserved": amount,
                "committed": 0,
                "spent": 0,
                "released": 0,
                "obligations": obligations,
            }
            reserved += amount
        elif kind == "budget.retry_admitted":
            rid, aid = payload.get("reservation_id"), payload.get("admission_id")
            if rid in reservations or aid in admissions:
                raise IdempotencyError("reused admission identity")
            if reserved + committed + spent + amount > authorized:
                raise BudgetOverdrawn("budget overdrawn")
            reservations[rid] = {
                "run_id": payload["run_id"],
                "amount": amount,
                "reserved": amount,
                "committed": 0,
                "spent": 0,
                "released": 0,
                "obligations": (),
            }
            admissions[aid] = {
                "reservation_id": rid,
                "run_id": payload["run_id"],
                "task_id": payload["task_id"],
                "amount": amount,
                "consumed": False,
            }
            reserved += amount
        else:
            rid = payload.get("reservation_id")
            r = reservations.get(rid)
            if r is None:
                raise BudgetTransitionError("unknown reservation")
            if kind == "budget.committed":
                if amount <= 0 or amount > r["reserved"]:
                    raise BudgetTransitionError("invalid commit")
                r["reserved"] -= amount
                r["committed"] += amount
                reserved -= amount
                committed += amount
            elif kind == "budget.spent":
                if amount <= 0 or amount > r["committed"]:
                    raise BudgetTransitionError("invalid spend")
                r["committed"] -= amount
                r["spent"] += amount
                committed -= amount
                spent += amount
                for a in admissions.values():
                    if a["reservation_id"] == rid:
                        a["consumed"] = True
            elif kind == "budget.released":
                if amount <= 0 or amount > r["reserved"]:
                    raise BudgetTransitionError("invalid release")
                r["reserved"] -= amount
                r["released"] += amount
                reserved -= amount
                released += amount
            elif kind in {"budget.retry_task", "budget.replan_task"}:
                aid = payload.get("admission_id")
                a = admissions.get(aid)
                if not a or a["consumed"] or a["task_id"] != payload.get("task_id"):
                    raise FreshAdmissionRequired("fresh admission required")
                a["consumed"] = True
    if min(reserved, committed, spent, released) < 0 or reserved + committed + spent > authorized:
        raise BudgetTransitionError("budget conservation failure")
    return (
        BudgetState(authorized, authorized - reserved - committed - spent, reserved, committed, spent, released),
        reservations,
        admissions,
    )


def _identifier(value):
    return isinstance(value, str) and bool(_IDENTIFIER.fullmatch(value))


def _payload(event):
    value = event.get("payload") if isinstance(event, dict) else None
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (TypeError, ValueError) as exc:
            raise BudgetTransitionError("invalid budget payload") from exc
    if not isinstance(value, dict):
        raise BudgetTransitionError("invalid budget payload")
    return value


def _require_keys(payload, expected):
    if set(payload) != expected:
        raise BudgetTransitionError("invalid budget event schema")


def validate_budget_history(events, *, authorized=None, runs=None, tasks=None):
    """Validate every budget event as a closed, run-bound event language.

    This function is intentionally usable both before an append and during
    replay.  It validates the complete mixed workflow/budget stream so an
    event cannot be made valid merely by filtering it into a smaller history.
    """
    if runs is None or tasks is None:
        raise BudgetTransitionError("run and task projection required")
    by_run = {}
    for event in _events(events):
        payload = _payload(event)
        kind = event.get("kind")
        run_id = payload.get("run_id")
        if not _identifier(run_id) or run_id not in runs:
            raise BudgetTransitionError("unknown budget run")
        if event.get("aggregate") != "budget:" + run_id:
            raise BudgetTransitionError("invalid budget aggregate")
        if payload.get("contract_id") != runs[run_id] or not _identifier(payload.get("contract_id")):
            raise BudgetTransitionError("budget contract mismatch")
        amount = payload.get("amount")
        if not isinstance(amount, int) or isinstance(amount, bool) or amount <= 0 or amount > _MAX_INTEGER:
            raise BudgetTransitionError("invalid budget amount")
        common = {"run_id", "contract_id", "command_id", "amount"}
        if not _identifier(payload.get("command_id")):
            raise IdempotencyError("invalid command identity")
        if kind == "budget.reserved":
            base = common | {"reservation_id", "obligations"}
            correction = common | {"reservation_id", "task_id", "obligations"}
            if set(payload) not in (base, correction):
                raise BudgetTransitionError("invalid reserved event schema")
            if not _identifier(payload.get("reservation_id")):
                raise BudgetTransitionError("invalid reservation identity")
            obligations = payload.get("obligations")
            if not isinstance(obligations, list) or obligations not in ([], list(OBLIGATIONS)):
                raise BudgetTransitionError("invalid correction obligations")
            if obligations == list(OBLIGATIONS):
                if not _identifier(payload.get("task_id")):
                    raise BudgetTransitionError("invalid correction task identity")
                if (run_id, payload["task_id"]) not in tasks:
                    raise BudgetTransitionError("correction task history missing")
            elif "task_id" in payload:
                raise BudgetTransitionError("unexpected correction task identity")
        elif kind == "budget.retry_admitted":
            _require_keys(payload, common | {"reservation_id", "admission_id", "task_id"})
            for key in ("reservation_id", "admission_id", "task_id"):
                if not _identifier(payload.get(key)):
                    raise BudgetTransitionError("invalid admission identity")
            if (run_id, payload["task_id"]) not in tasks:
                raise BudgetTransitionError("retry task history missing")
        elif kind in {"budget.committed", "budget.spent", "budget.released"}:
            _require_keys(payload, common | {"reservation_id"})
            if not _identifier(payload.get("reservation_id")):
                raise BudgetTransitionError("invalid reservation identity")
        else:
            _require_keys(payload, common | {"reservation_id", "admission_id", "task_id"})
            for key in ("reservation_id", "admission_id", "task_id"):
                if not _identifier(payload.get(key)):
                    raise BudgetTransitionError("invalid admission identity")
            if (run_id, payload["task_id"]) not in tasks:
                raise BudgetTransitionError("action task history missing")
        by_run.setdefault(run_id, []).append({"aggregate": event.get("aggregate"), "kind": kind, "payload": payload})
    for run_id, history in by_run.items():
        limit = authorized
        if isinstance(authorized, dict):
            limit = authorized.get(run_id)
        if limit is None:
            limit = _MAX_INTEGER
        reduce_budget(history, limit)


__all__ = [
    "Admission",
    "BUDGET_KINDS",
    "BudgetError",
    "BudgetOverdrawn",
    "BudgetState",
    "BudgetTransitionError",
    "FreshAdmissionRequired",
    "IdempotencyError",
    "InsufficientObligations",
    "OBLIGATIONS",
    "Reservation",
    "RetryState",
    "reduce_budget",
    "validate_budget_history",
]
