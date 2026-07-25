"""Immutable durable workflow records and deterministic event reduction."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import StrEnum

from .contracts import TaskState


class AuthorityError(ValueError):
    pass


class InvalidTransition(ValueError):
    pass


class RuntimeModeError(ValueError):
    pass


class RuntimeMode(StrEnum):
    KERNEL = "kernel"
    PILOT = "pilot"


WORKFLOW_KINDS = frozenset(
    {
        "run.created",
        "task.created",
        "task.admitted",
        "task.ready",
        "task.dispatched",
        "attempt.started",
        "session.bound",
    }
)
_TASK_KIND_STATE = {
    "task.created": TaskState.PROPOSED,
    "task.admitted": TaskState.ADMITTED,
    "task.ready": TaskState.READY,
    "task.dispatched": TaskState.DISPATCHED,
    "attempt.started": TaskState.RUNNING,
}
_ID = re.compile(r"^[a-z0-9][a-z0-9._:-]{0,127}$")
_SCHEMAS = {
    "run.created": {"run_id", "contract_id", "mode"},
    "task.created": {"run_id", "task_id", "prerequisites", "contract_id"},
    "task.admitted": {"run_id", "task_id", "contract_id"},
    "task.ready": {"run_id", "task_id", "contract_id"},
    "task.dispatched": {"run_id", "task_id", "contract_id"},
    "attempt.started": {"run_id", "task_id", "attempt", "contract_id"},
    "session.bound": {"run_id", "task_id", "logical_session", "contract_id"},
}


def _bad(message: str) -> InvalidTransition:
    return InvalidTransition(message)


def _event_payload(event):
    payload = event.get("payload") if isinstance(event, dict) else None
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except (TypeError, ValueError) as exc:
            raise _bad("malformed workflow payload") from exc
    return payload


def validate_workflow_history(events):
    """Validate the workflow subset as one deterministic, fail-closed reduction.

    The ledger calls this before inserting a workflow event and projection rebuild
    calls it for the complete stream.  Unknown event kinds are deliberately left
    to the legacy reducer.
    """
    runs = {}
    tasks = {}
    attempts = {}
    sessions = {}
    for event in events:
        kind = event.get("kind")
        if kind not in WORKFLOW_KINDS:
            continue
        payload = _event_payload(event)
        if not isinstance(payload, dict) or set(payload) != _SCHEMAS[kind]:
            raise _bad("invalid workflow payload schema")
        aggregate = event.get("aggregate")
        run_id, task_id = payload.get("run_id"), payload.get("task_id")
        contract_id = payload.get("contract_id")
        if not all(isinstance(value, str) and _ID.fullmatch(value) for value in (contract_id, run_id)):
            raise _bad("invalid workflow identifiers")
        if kind == "run.created":
            if aggregate != "run:" + run_id or payload["mode"] != RuntimeMode.KERNEL.value or run_id in runs:
                raise _bad("duplicate or invalid run creation")
            runs[run_id] = contract_id
            continue
        if (
            not isinstance(task_id, str)
            or not _ID.fullmatch(task_id)
            or aggregate != f"task:{run_id}:{task_id}"
            or run_id not in runs
        ):
            raise _bad("workflow parent or aggregate mismatch")
        if runs[run_id] != contract_id:
            raise AuthorityError("workflow contract mismatch")
        key = (run_id, task_id)
        if kind == "task.created":
            prerequisites = payload["prerequisites"]
            if (
                key in tasks
                or not isinstance(prerequisites, list)
                or any(not isinstance(item, str) or not _ID.fullmatch(item) for item in prerequisites)
            ):
                raise _bad("invalid or duplicate task creation")
            if any((run_id, item) not in tasks for item in prerequisites):
                raise _bad("missing workflow prerequisite")
            tasks[key] = (TaskState.PROPOSED, tuple(prerequisites))
        elif key not in tasks:
            raise _bad("workflow task parent missing")
        elif kind in _TASK_KIND_STATE:
            current, prerequisites = tasks[key]
            target = _TASK_KIND_STATE[kind]
            if transition_state(current, target) != target:
                raise _bad("invalid workflow transition")
            tasks[key] = (target, prerequisites)
            if kind == "attempt.started":
                attempt = payload["attempt"]
                if (
                    not isinstance(attempt, int)
                    or isinstance(attempt, bool)
                    or attempt != len(attempts.get(key, ())) + 1
                ):
                    raise _bad("non-monotonic attempt")
                attempts.setdefault(key, []).append(attempt)
        elif kind == "session.bound":
            logical = payload["logical_session"]
            if (
                not isinstance(logical, str)
                or not _ID.fullmatch(logical)
                or logical in sessions.get(key, ())
                or not attempts.get(key)
            ):
                raise _bad("invalid session binding")
            sessions.setdefault(key, []).append(logical)
    return runs, tasks, attempts, sessions


def reduce_workflow_projection(current, kind, payload):
    """Derive workflow projection fields from validated event intent."""
    value = {**(current or {}), **payload}
    state = _TASK_KIND_STATE.get(kind)
    if state is not None:
        value["state"] = state.value
    return value


@dataclass(frozen=True, slots=True)
class RunRecord:
    run_id: str
    contract_id: str
    mode: str


@dataclass(frozen=True, slots=True)
class TaskRecord:
    run_id: str
    task_id: str
    prerequisites: tuple[str, ...]
    state: TaskState = TaskState.PROPOSED


@dataclass(frozen=True, slots=True)
class AttemptRecord:
    run_id: str
    task_id: str
    attempt: int


@dataclass(frozen=True, slots=True)
class SessionBinding:
    run_id: str
    task_id: str
    logical_session: str


_ALLOWED = {
    TaskState.PROPOSED: TaskState.ADMITTED,
    TaskState.ADMITTED: TaskState.READY,
    TaskState.READY: TaskState.DISPATCHED,
    TaskState.DISPATCHED: TaskState.RUNNING,
}


def transition_state(current: TaskState, target: TaskState) -> TaskState:
    if _ALLOWED.get(current) is not target:
        raise InvalidTransition(f"illegal task transition: {current.value} -> {target.value}")
    return target


__all__ = [
    "AttemptRecord",
    "AuthorityError",
    "InvalidTransition",
    "RuntimeMode",
    "RuntimeModeError",
    "RunRecord",
    "SessionBinding",
    "TaskRecord",
    "reduce_workflow_projection",
    "transition_state",
]
