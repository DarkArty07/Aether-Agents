"""Immutable durable workflow records and deterministic event reduction."""

from __future__ import annotations

import hashlib
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
        "task.released",
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
        "close.requested",
        "cleanup.receipt.recorded",
        "task.closed",
        "close.failed",
        "close.reconciliation_required",
    }
)
_TASK_KIND_STATE = {
    "task.created": TaskState.PROPOSED,
    "task.released": TaskState.PROPOSED,
    "task.admitted": TaskState.ADMITTED,
    "task.ready": TaskState.READY,
    "task.dispatched": TaskState.DISPATCHED,
    "attempt.started": TaskState.RUNNING,
    "close.requested": TaskState.CLEANUP_PENDING,
    "task.closed": TaskState.CLOSED,
    "close.failed": TaskState.CLOSE_FAILED,
    "close.reconciliation_required": TaskState.RECONCILIATION_REQUIRED,
}
_ID = re.compile(r"^[a-z0-9][a-z0-9._:-]{0,127}$")
_SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
_RECEIPT_ID = re.compile(r"^receipt:[0-9a-f]{64}$")
_SCHEMAS = {
    "run.created": {"run_id", "contract_id", "mode"},
    "task.created": {"run_id", "task_id", "prerequisites", "contract_id"},
    "task.released": {"run_id", "task_id", "satisfied_prerequisites", "contract_id"},
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
    "close.requested": {
        "installation_id",
        "project_id",
        "run_id",
        "task_id",
        "attempt",
        "contract_id",
        "contract_generation",
        "revocation_epoch",
        "message_id",
        "logical_session",
        "fence",
        "acp_session_id",
        "evidence_receipt_id",
        "closure_proposal_hash",
        "cleanup_command_id",
        "command_id",
        "proposed_state",
    },
    "cleanup.receipt.recorded": {
        "run_id",
        "task_id",
        "attempt",
        "contract_id",
        "contract_generation",
        "revocation_epoch",
        "message_id",
        "logical_session",
        "acp_session_id",
        "evidence_receipt_id",
        "cleanup_command_id",
        "closure_proposal_hash",
        "lease_resource",
        "lease_owner",
        "lease_epoch",
        "lease_token",
        "lease_released",
        "receipt_id",
        "proof",
    },
    "task.closed": {"run_id", "task_id", "attempt", "contract_id", "receipt_id"},
    "close.failed": {"run_id", "task_id", "attempt", "contract_id", "cleanup_command_id", "outcome"},
    "close.reconciliation_required": {"run_id", "task_id", "attempt", "contract_id", "cleanup_command_id", "outcome"},
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


def kernel_logical_session(project_id: str, run_id: str, task_id: str, attempt: int) -> str:
    """Return a bounded deterministic session identity for full-width IDs."""
    material = f"{project_id}\0{run_id}\0{task_id}\0{attempt}".encode()
    return "kernel:" + hashlib.sha256(material).hexdigest()


def _event_payload(event):
    payload = event.get("payload") if isinstance(event, dict) else None
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except (TypeError, ValueError) as exc:
            raise _bad("malformed workflow payload") from exc
    return payload


def closure_proposal_hash(payload) -> str:
    """Bind close intent to its exact authority, evidence and semantic outcome."""
    fields = (
        "run_id",
        "task_id",
        "attempt",
        "contract_id",
        "contract_generation",
        "revocation_epoch",
        "message_id",
        "logical_session",
        "acp_session_id",
        "evidence_receipt_id",
        "proposed_state",
    )
    material = {name: payload.get(name) for name in fields}
    canonical = json.dumps(material, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return "sha256:" + hashlib.sha256(canonical).hexdigest()


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
    receipts = {}
    receipt_payloads = {}
    close_intents = {}
    cleanup_requests = {}
    cleanup_outcomes = {}
    cleanup_receipts = {}
    for event in events:
        kind = event.get("kind")
        if kind == "evidence.receipt.recorded":
            from .evidence import EvidenceVerificationError, validate_evidence_receipt_payload

            payload = _event_payload(event)
            if not isinstance(payload, dict):
                raise _bad("invalid evidence receipt")
            try:
                validate_evidence_receipt_payload(payload)
            except EvidenceVerificationError as exc:
                raise _bad("invalid evidence receipt") from exc
            receipt_key = (payload["run_id"], payload["task_id"])
            if receipt_key not in tasks or runs.get(payload["run_id"]) != payload["contract_id"]:
                raise _bad("evidence receipt task mismatch")
            receipts.setdefault(receipt_key, set()).add(payload["receipt_id"])
            receipt_payloads[payload["receipt_id"]] = payload
            continue
        if kind in {"cleanup.requested", "cleanup.completed", "cleanup.failed", "cleanup.unknown"}:
            payload = _event_payload(event)
            if not isinstance(payload, dict):
                raise _bad("invalid cleanup event")
            # v0.19.1 technical-stop cleanup remains a separate lifecycle path.
            # Only v0.19.3 semantic closure carries a cleanup command binding.
            if "cleanup_command_id" not in payload:
                continue
            key = (payload.get("run_id"), payload.get("task_id"))
            intent = close_intents.get(key)
            common = (
                "installation_id",
                "project_id",
                "run_id",
                "task_id",
                "attempt",
                "contract_id",
                "contract_generation",
                "revocation_epoch",
                "message_id",
                "logical_session",
                "acp_session_id",
                "evidence_receipt_id",
                "cleanup_command_id",
                "command_id",
                "proposed_state",
            )
            if (
                intent is None
                or event.get("aggregate") != "dispatch:" + payload.get("message_id", "")
                or any(payload.get(name) != intent.get(name) for name in common)
                or payload.get("expected_terminal_status")
                != {"completed": "completed", "failed": "error", "cancelled": "cancelled"}.get(
                    intent.get("proposed_state")
                )
            ):
                raise _bad("cleanup authority mismatch")
            command = payload["cleanup_command_id"]
            if kind == "cleanup.requested":
                if payload.get("outcome") != "requested" or command in cleanup_requests:
                    raise _bad("invalid cleanup request")
                cleanup_requests[command] = payload
            else:
                request = cleanup_requests.get(command)
                expected_outcome = kind.removeprefix("cleanup.")
                if (
                    request is None
                    or command in cleanup_outcomes
                    or payload.get("outcome") != expected_outcome
                    or any(payload.get(name) != request.get(name) for name in common + ("expected_terminal_status",))
                ):
                    raise _bad("invalid cleanup outcome")
                cleanup_outcomes[command] = payload
            continue
        if kind not in WORKFLOW_KINDS:
            continue
        payload = _event_payload(event)
        session_schemas = (
            _SCHEMAS["session.bound"],
            _SCHEMAS["session.bound"] | {"acp_session_id", "attempt", "message_id", "fence"},
        )
        if (
            not isinstance(payload, dict)
            or (kind == "session.bound" and set(payload) not in session_schemas)
            or (kind == "run.created" and set(payload) not in _RUN_CREATED_SCHEMAS)
            or (kind == "task.released" and set(payload) not in (_SCHEMAS[kind], _SCHEMAS[kind] | {"handoff"}))
            or (kind not in {"session.bound", "run.created", "task.released"} and set(payload) != _SCHEMAS[kind])
        ):
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
                or (request_id is not None and (not isinstance(request_id, str) or not _ID.fullmatch(request_id)))
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
                or payload["logical_session"]
                not in {
                    f"kernel:{payload['project_id']}:{run_id}:{task_id}:{attempt}",
                    kernel_logical_session(payload["project_id"], run_id, task_id, attempt),
                }
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
                or (kind == "attempt.superseded" and current_state not in {AttemptState.ACTIVE, AttemptState.ORPHANED})
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
        if kind == "close.requested":
            key = (run_id, task_id)
            source = staged.get(payload["message_id"])
            receipt = receipt_payloads.get(payload["evidence_receipt_id"])
            expected_state = {
                "completed": "completed",
                "error": "failed",
                "cancelled": "cancelled",
            }
            if (
                not isinstance(task_id, str)
                or not _ID.fullmatch(task_id)
                or aggregate != f"task:{run_id}:{task_id}"
                or key not in tasks
                or tasks[key][0] is not TaskState.RUNNING
                or source is None
                or receipt is None
                or key in close_intents
                or attempt_states.get((run_id, task_id, payload["attempt"])) is not AttemptState.ACTIVE
                or any(
                    payload[name] != source[name]
                    for name in (
                        "installation_id",
                        "project_id",
                        "run_id",
                        "task_id",
                        "attempt",
                        "contract_id",
                        "contract_generation",
                        "revocation_epoch",
                        "message_id",
                        "logical_session",
                    )
                )
                or payload["fence"] != source["lease_epoch"]
                or any(
                    payload[name] != receipt[name]
                    for name in (
                        "run_id",
                        "task_id",
                        "attempt",
                        "contract_id",
                        "contract_generation",
                        "revocation_epoch",
                        "message_id",
                        "logical_session",
                        "acp_session_id",
                    )
                )
                or expected_state.get(receipt["terminal"]["technical_status"]) != payload["proposed_state"]
                or not isinstance(payload["command_id"], str)
                or not _ID.fullmatch(payload["command_id"])
                or payload["cleanup_command_id"] != "cleanup:" + payload["command_id"]
                or not _SHA256.fullmatch(payload["closure_proposal_hash"])
                or payload["closure_proposal_hash"] != closure_proposal_hash(payload)
            ):
                raise _bad("invalid close intent")
            tasks[key] = (TaskState.CLEANUP_PENDING, tasks[key][1])
            close_intents[key] = payload
            continue
        if kind in {"cleanup.receipt.recorded", "task.closed", "close.failed", "close.reconciliation_required"}:
            key = (run_id, task_id)
            current = tasks.get(key)
            if current is None or aggregate != f"task:{run_id}:{task_id}":
                raise _bad("invalid close finalization aggregate")
            if kind == "cleanup.receipt.recorded":
                proof = payload.get("proof")
                intent = close_intents.get(key)
                outcome = cleanup_outcomes.get(payload.get("cleanup_command_id"))
                source = staged.get(payload.get("message_id"))
                intent_fields = (
                    "run_id",
                    "task_id",
                    "attempt",
                    "contract_id",
                    "contract_generation",
                    "revocation_epoch",
                    "message_id",
                    "logical_session",
                    "acp_session_id",
                    "evidence_receipt_id",
                    "cleanup_command_id",
                    "closure_proposal_hash",
                )
                lease_fields = ("lease_resource", "lease_owner", "lease_epoch", "lease_token")
                expected_receipt_id = (
                    "cleanup-receipt:"
                    + hashlib.sha256(str(payload.get("cleanup_command_id", "")).encode("utf-8")).hexdigest()
                )
                if (
                    current[0] is not TaskState.CLEANUP_PENDING
                    or key in cleanup_receipts
                    or intent is None
                    or outcome is None
                    or outcome.get("outcome") != "completed"
                    or source is None
                    or any(payload.get(name) != intent.get(name) for name in intent_fields)
                    or any(payload.get(name) != source.get(name) for name in lease_fields)
                    or payload.get("receipt_id") != expected_receipt_id
                    or payload.get("lease_released") is not True
                    or not isinstance(proof, dict)
                    or proof != outcome.get("proof", {}).get("survivors")
                    or set(proof) != {"logical_manager_session", "acp_mapping", "prompt_task", "pid_session_mapping"}
                    or any(value is not False for value in proof.values())
                ):
                    raise _bad("invalid cleanup receipt")
                cleanup_receipts[key] = payload["receipt_id"]
            elif kind == "task.closed":
                intent = close_intents.get(key)
                if (
                    key not in cleanup_receipts
                    or current[0] is not TaskState.CLEANUP_PENDING
                    or payload["receipt_id"] != cleanup_receipts[key]
                    or intent is None
                    or payload["attempt"] != intent["attempt"]
                    or payload["contract_id"] != intent["contract_id"]
                ):
                    raise _bad("task.closed requires prior cleanup receipt")
                tasks[key] = (TaskState.CLOSED, current[1])
            elif kind == "close.failed":
                intent = close_intents.get(key)
                outcome = cleanup_outcomes.get(payload.get("cleanup_command_id"))
                if (
                    current[0] is not TaskState.CLEANUP_PENDING
                    or payload.get("outcome") != "failed"
                    or intent is None
                    or outcome is None
                    or outcome.get("outcome") != "failed"
                    or payload["attempt"] != intent["attempt"]
                    or payload["contract_id"] != intent["contract_id"]
                ):
                    raise _bad("invalid close failure")
                tasks[key] = (TaskState.CLOSE_FAILED, current[1])
            else:
                intent = close_intents.get(key)
                outcome = cleanup_outcomes.get(payload.get("cleanup_command_id"))
                if (
                    current[0] is not TaskState.CLEANUP_PENDING
                    or payload.get("outcome") != "unknown"
                    or intent is None
                    or outcome is None
                    or outcome.get("outcome") != "unknown"
                    or payload["attempt"] != intent["attempt"]
                    or payload["contract_id"] != intent["contract_id"]
                ):
                    raise _bad("invalid close reconciliation requirement")
                tasks[key] = (TaskState.RECONCILIATION_REQUIRED, current[1])
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
                or len(set(prerequisites)) != len(prerequisites)
                or task_id in prerequisites
            ):
                raise _bad("invalid or duplicate task creation")
            if any((run_id, item) not in tasks for item in prerequisites):
                raise _bad("missing workflow prerequisite")
            tasks[key] = (
                TaskState.BLOCKED if prerequisites else TaskState.PROPOSED,
                tuple(prerequisites),
            )
        elif key not in tasks:
            raise _bad("workflow task parent missing")
        elif kind == "task.released":
            current, prerequisites = tasks[key]
            satisfied = payload["satisfied_prerequisites"]
            if (
                current is not TaskState.BLOCKED
                or not isinstance(satisfied, list)
                or satisfied
                != sorted(satisfied, key=lambda item: item.get("task_id", "") if isinstance(item, dict) else "")
                or any(
                    not isinstance(item, dict)
                    or set(item) != {"task_id", "receipt_id"}
                    or not isinstance(item["task_id"], str)
                    or not _ID.fullmatch(item["task_id"])
                    or not isinstance(item["receipt_id"], str)
                    or not _RECEIPT_ID.fullmatch(item["receipt_id"])
                    for item in satisfied
                )
                or tuple(item["task_id"] for item in satisfied) != tuple(sorted(prerequisites))
                or any(item["receipt_id"] not in receipts.get((run_id, item["task_id"]), set()) for item in satisfied)
            ):
                raise _bad("invalid task release")
            handoff = payload.get("handoff")
            if handoff is not None:
                from .evidence import EvidenceVerificationError, HandoffSnapshot
                try:
                    snapshot = HandoffSnapshot.from_dict(handoff)
                    matching = [item["receipt_id"] for item in satisfied if isinstance(item, dict) and item.get("receipt_id") in receipt_payloads and receipt_payloads[item["receipt_id"]].get("handoff") == handoff]
                    if len(matching) != 1 or snapshot.source_receipt_id != matching[0]:
                        raise ValueError("handoff binding mismatch")
                except (EvidenceVerificationError, ValueError):
                    raise _bad("invalid task release handoff")
            tasks[key] = (TaskState.PROPOSED, prerequisites)
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
    for (run_id, _task_id), (state, prerequisites) in tasks.items():
        if state is TaskState.BLOCKED and prerequisites and all(receipts.get((run_id, item)) for item in prerequisites):
            raise _bad("satisfied prerequisites require durable release")
    return runs, tasks, attempts, sessions


def reduce_workflow_projection(current, kind, payload):
    """Derive workflow projection fields from validated event intent."""
    value = {**(current or {}), **payload}
    state = TaskState.BLOCKED if kind == "task.created" and payload.get("prerequisites") else _TASK_KIND_STATE.get(kind)
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
    TaskState.BLOCKED: TaskState.PROPOSED,
    TaskState.PROPOSED: TaskState.ADMITTED,
    TaskState.ADMITTED: TaskState.READY,
    TaskState.READY: TaskState.DISPATCHED,
    TaskState.DISPATCHED: TaskState.RUNNING,
    TaskState.RUNNING: TaskState.CLEANUP_PENDING,
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
    "closure_proposal_hash",
    "reduce_workflow_projection",
    "transition_state",
]
