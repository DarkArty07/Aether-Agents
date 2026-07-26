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


class AttemptState(StrEnum):
    ACTIVE = "active"
    ORPHANED = "orphaned"
    SUPERSEDED = "superseded"


WORKFLOW_KINDS = frozenset(
    {
        "run.created",
        "task.created",
        "task.admitted",
        "task.ready",
        "task.dispatched",
        "attempt.started",
        "session.bound",
        "dispatch.staged",
        "dispatch.unknown",
        "observation.accepted",
        "cancel.intent",
        "reconciliation.completed",
        "attempt.orphaned",
        "attempt.superseded",
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
_SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
_SCHEMAS = {
    "run.created": {"run_id", "contract_id", "mode"},
    "task.created": {"run_id", "task_id", "prerequisites", "contract_id"},
    "task.admitted": {"run_id", "task_id", "contract_id"},
    "task.ready": {"run_id", "task_id", "contract_id"},
    "task.dispatched": {"run_id", "task_id", "contract_id"},
    "attempt.started": {"run_id", "task_id", "attempt", "contract_id"},
    "session.bound": {"run_id", "task_id", "logical_session", "contract_id"},
    "dispatch.staged": {
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
        "envelope",
    },
    "dispatch.unknown": {"run_id", "task_id", "attempt", "contract_id", "message_id", "reason"},
    "observation.accepted": {"run_id", "task_id", "attempt", "contract_id", "message_id", "status"},
    "cancel.intent": {"run_id", "task_id", "attempt", "contract_id", "message_id"},
    "reconciliation.completed": {
        "run_id",
        "task_id",
        "attempt",
        "contract_id",
        "message_id",
        "status",
        "observation",
    },
    "attempt.orphaned": {"run_id", "task_id", "attempt", "contract_id"},
    "attempt.superseded": {"run_id", "task_id", "attempt", "replacement_attempt", "contract_id"},
}
_RUN_CREATED_SCHEMAS = (
    _SCHEMAS["run.created"],
    _SCHEMAS["run.created"] | {"request_id", "request_digest"},
)
_R11_DISPATCH_KINDS = {
    "dispatch.unknown",
    "observation.accepted",
    "cancel.intent",
    "reconciliation.completed",
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
    attempt_states = {}
    sessions = {}
    staged = {}
    for event in events:
        kind = event.get("kind")
        if kind not in WORKFLOW_KINDS:
            continue
        payload = _event_payload(event)
        session_schemas = (
            _SCHEMAS["session.bound"],
            _SCHEMAS["session.bound"] | {"acp_session_id", "attempt", "message_id", "fence"},
        )
        if not isinstance(payload, dict) or (
            kind == "session.bound" and set(payload) not in session_schemas
        ) or (
            kind == "run.created" and set(payload) not in _RUN_CREATED_SCHEMAS
        ) or (kind not in {"session.bound", "run.created"} and set(payload) != _SCHEMAS[kind]):
            raise _bad("invalid workflow payload schema")
        aggregate = event.get("aggregate")
        run_id, task_id = payload.get("run_id"), payload.get("task_id")
        contract_id = payload.get("contract_id")
        if not all(isinstance(value, str) and _ID.fullmatch(value) for value in (contract_id, run_id)):
            raise _bad("invalid workflow identifiers")
        if kind == "run.created":
            request_id = payload.get("request_id")
            request_digest = payload.get("request_digest")
            if (
                aggregate != f"run:{run_id}"
                or payload["mode"] != RuntimeMode.KERNEL.value
                or run_id in runs
                or (
                    request_id is not None
                    and (not isinstance(request_id, str) or not _ID.fullmatch(request_id))
                )
                or (
                    request_digest is not None
                    and (not isinstance(request_digest, str) or not _SHA256.fullmatch(request_digest))
                )
            ):
                raise _bad("duplicate or invalid run creation")
            runs[run_id] = contract_id
            continue
        if kind == "dispatch.staged":
            key = (run_id, task_id)
            attempt = payload["attempt"]
            message_id = payload["message_id"]
            if (
                not isinstance(task_id, str)
                or not _ID.fullmatch(task_id)
                or key not in tasks
                or tasks[key][0] is not TaskState.RUNNING
                or attempt not in attempts.get(key, ())
                or attempt_states.get((run_id, task_id, attempt)) is not AttemptState.ACTIVE
                or not isinstance(message_id, str)
                or not _ID.fullmatch(message_id)
                or aggregate != "dispatch:" + message_id
                or message_id in staged
                or payload["lease_resource"] != f"dispatch:{run_id}:{task_id}:{attempt}"
                or payload["logical_session"] != f"kernel:{payload['project_id']}:{run_id}:{task_id}:{attempt}"
                or payload["envelope"] != {"run_id": run_id, "task_id": task_id, "attempt": attempt}
                or not isinstance(payload["project_root"], str)
                or not payload["project_root"].startswith("/")
                or any(
                    not isinstance(payload[name], str) or not payload[name]
                    for name in (
                        "installation_id",
                        "project_id",
                        "agent_name",
                        "plan_id",
                        "snapshot_digest",
                        "lease_owner",
                        "lease_token",
                    )
                )
                or any(
                    not isinstance(payload[name], int) or isinstance(payload[name], bool) or payload[name] < 0
                    for name in (
                        "contract_generation",
                        "revocation_epoch",
                        "plan_revision",
                        "lease_epoch",
                        "lease_until",
                    )
                )
            ):
                raise _bad("invalid durable dispatch authority")
            staged[message_id] = payload
            continue
        if kind in _R11_DISPATCH_KINDS:
            message_id = payload["message_id"]
            source = staged.get(message_id)
            if (
                source is None
                or aggregate != "dispatch:" + message_id
                or any(payload[name] != source[name] for name in ("run_id", "task_id", "attempt", "contract_id"))
            ):
                raise _bad("dispatch authority mismatch")
            continue
        if kind in {"attempt.orphaned", "attempt.superseded"}:
            key = (run_id, task_id)
            attempt = payload["attempt"]
            current_state = attempt_states.get((run_id, task_id, attempt))
            if (
                aggregate != f"task:{run_id}:{task_id}"
                or (kind == "attempt.orphaned" and current_state is not AttemptState.ACTIVE)
                or (
                    kind == "attempt.superseded"
                    and current_state not in {AttemptState.ACTIVE, AttemptState.ORPHANED}
                )
                or not any(
                    item["run_id"] == run_id and item["task_id"] == task_id and item["attempt"] == attempt
                    for item in staged.values()
                )
            ):
                raise _bad("invalid attempt reconciliation")
            if kind == "attempt.orphaned":
                attempt_states[(run_id, task_id, attempt)] = AttemptState.ORPHANED
            elif payload["replacement_attempt"] != attempt + 1:
                raise _bad("non-monotonic attempt supersession")
            else:
                attempt_states[(run_id, task_id, attempt)] = AttemptState.SUPERSEDED
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
                attempt_states[(run_id, task_id, attempt)] = AttemptState.ACTIVE
        elif kind == "session.bound":
            logical = payload["logical_session"]
            if (
                not isinstance(logical, str)
                or not _ID.fullmatch(logical)
                or logical in sessions.get(key, ())
                or not attempts.get(key)
            ):
                raise _bad("invalid session binding")
            if "message_id" in payload:
                source = staged.get(payload["message_id"])
                if (
                    source is None
                    or payload["attempt"] != source["attempt"]
                    or payload["logical_session"] != source["logical_session"]
                    or payload["contract_id"] != source["contract_id"]
                    or not isinstance(payload["acp_session_id"], str)
                    or not payload["acp_session_id"]
                    or payload["fence"] != source["lease_epoch"]
                ):
                    raise _bad("session binding authority mismatch")
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
    state: AttemptState = AttemptState.ACTIVE


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
    "AttemptState",
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
