"""Authenticated semantic command boundary for the durable kernel workflow."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any, Mapping

from .budget import (
    OBLIGATIONS,
    Admission,
    BudgetTransitionError,
    FreshAdmissionRequired,
    IdempotencyError,
    InsufficientObligations,
    Reservation,
    RetryState,
    reduce_budget,
)
from .closure import CompletionState
from .contracts import ContractState, TaskState
from .ledger import HMACWriterAuthenticator, Result, SignedEventDraft, SQLiteLedger, WriterContext
from .workflow import (
    AttemptRecord,
    AttemptState,
    AuthorityError,
    InvalidTransition,
    RunRecord,
    RuntimeMode,
    RuntimeModeError,
    SessionBinding,
    TaskRecord,
    closure_proposal_hash,
    transition_state,
)

_INTERNAL_LEDGER_EVENT_KINDS = {"outbox.poison", "dispatch.unknown"}


class IdempotencyConflictError(ValueError):
    pass


class AdmissionLimitError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class RunRequestMetadata:
    request_id: str
    request_digest: str


class KernelWriter:
    """Capability that can create authenticated drafts, but not integrity tags."""

    def __init__(self, context: WriterContext, authenticator: HMACWriterAuthenticator):
        if not isinstance(context, WriterContext) or not isinstance(authenticator, HMACWriterAuthenticator):
            raise TypeError("authenticated kernel writer required")
        self.context, self.authenticator = context, authenticator

    def _author(
        self,
        ledger: SQLiteLedger,
        aggregate: str,
        kind: str,
        payload: Mapping[str, Any],
        expected_version: int,
        *,
        contract_generation: int,
        revocation_epoch: int,
    ):
        draft = ledger.draft(
            aggregate,
            kind,
            payload,
            writer=self.context,
            expected_version=expected_version,
            contract_generation=contract_generation,
            revocation_epoch=revocation_epoch,
        )
        return self.authenticator.sign(draft, self.context)


class KernelRunService:
    def __init__(self, ledger: SQLiteLedger, *, writer: KernelWriter, pilot_store: Any = None):
        if not isinstance(ledger, SQLiteLedger) or not isinstance(writer, KernelWriter):
            raise TypeError("ledger and authenticated kernel writer required")
        if pilot_store is not None:
            raise TypeError("pilot_store is not used by kernel runtime")
        self.ledger, self.writer = ledger, writer
        if writer.context.scope != ledger.scope:
            raise AuthorityError("writer scope mismatch")
        self._replay()

    @staticmethod
    def _check_event_authority(ledger, row, payload):
        if row["kind"] == "outbox.poison" or row["contract_generation"] is None:
            return
        contract_id = payload.get("contract_id") if isinstance(payload, dict) else row["contract_id"]
        version = ledger.conn.execute(
            "SELECT revocation_epoch FROM contract_versions WHERE installation_id=? AND project_id=? AND contract_id=? AND generation=?",
            (
                ledger.scope.installation_id,
                ledger.scope.project_id,
                contract_id,
                row["contract_generation"],
            ),
        ).fetchone()
        if not version or version[0] != row["revocation_epoch"]:
            raise AuthorityError("unknown workflow authority version")

    @staticmethod
    def _verify_event_authentication(ledger, row, payload):
        context = WriterContext(
            ledger.scope,
            row["writer_id"],
            row["key_id"],
            row["resource"],
            row["fence"],
            1,
        )
        if row["kind"] in _INTERNAL_LEDGER_EVENT_KINDS:
            material = json.dumps(
                [
                    1,
                    ledger.scope.installation_id,
                    ledger.scope.project_id,
                    row["sequence"],
                    row["server_time"],
                    row["event_id"],
                    row["aggregate"],
                    row["version"],
                    row["kind"],
                    row["payload"],
                    row["previous_hash"],
                    row["writer_id"],
                    row["key_id"],
                    row["resource"],
                    row["fence"],
                ],
                separators=(",", ":"),
            ).encode()
            if (row["writer_id"], row["key_id"], row["resource"]) != (
                "ledger-internal",
                ledger.integrity_signer.key_id,
                "ledger-integrity",
            ) or not ledger.integrity_signer.verify(material, row["writer_proof"]):
                raise AuthorityError("internal ledger event authentication failed")
            return
        if row["kind"] == "contract.advance":
            prior = payload.get("prior_contract", {})
            draft_generation = payload.get("prior_generation")
            draft_epoch = prior.get("revocation_epoch") if isinstance(prior, dict) else None
            expected_version = 0
        else:
            draft_generation = row["contract_generation"]
            draft_epoch = row["revocation_epoch"]
            expected_version = row["version"] - 1
        draft = SignedEventDraft(
            ledger.scope,
            row["aggregate"],
            row["kind"],
            payload,
            row["writer_id"],
            row["key_id"],
            row["resource"],
            row["fence"],
            row["writer_proof"],
            expected_version,
            draft_generation,
            draft_epoch,
        )
        if not ledger.writer_authenticator.verify(draft, context):
            raise AuthorityError("writer authentication failed")

    @classmethod
    def rebuild(cls, ledger):
        ledger.verify_chain()
        ledger.verify_projections()
        events = ledger.events()
        for row in events:
            payload = json.loads(row["payload"])
            cls._check_event_authority(ledger, row, payload)
            cls._verify_event_authentication(ledger, row, payload)
        service = object.__new__(cls)
        service.ledger = ledger
        service.writer = None
        service._replay(events)
        return service

    def _replay(self, events=None):
        events = self.ledger.events() if events is None else events
        from .budget import validate_budget_history
        from .workflow import validate_workflow_history

        try:
            runs, tasks, attempts, sessions = validate_workflow_history(events)
        except (AuthorityError, InvalidTransition):
            raise
        contracts = {
            run_id: (
                self.ledger.read_contract(contract_id).limits.model_budget
                if self.ledger.read_contract(contract_id)
                else 0
            )
            for run_id, contract_id in runs.items()
        }
        validate_budget_history(events, authorized=contracts, runs=runs)
        self._runs = {
            run_id: RunRecord(run_id, contract_id, RuntimeMode.KERNEL.value) for run_id, contract_id in runs.items()
        }
        self._tasks = {
            key: TaskRecord(key[0], key[1], prerequisites, state) for key, (state, prerequisites) in tasks.items()
        }
        self._attempts = {
            key: [AttemptRecord(key[0], key[1], attempt) for attempt in values] for key, values in attempts.items()
        }
        for event in events:
            if event.get("kind") in {"attempt.orphaned", "attempt.superseded"}:
                payload = json.loads(event["payload"])
                key = (payload["run_id"], payload["task_id"])
                state = AttemptState.ORPHANED if event["kind"] == "attempt.orphaned" else AttemptState.SUPERSEDED
                self._attempts[key] = [
                    AttemptRecord(a.run_id, a.task_id, a.attempt, state if a.attempt == payload["attempt"] else a.state)
                    for a in self._attempts.get(key, [])
                ]
        self._sessions = {
            key: [SessionBinding(key[0], key[1], value) for value in values] for key, values in sessions.items()
        }
        self._run_requests = {}
        for event in events:
            if event.get("kind") != "run.created":
                continue
            payload = json.loads(event["payload"])
            if "request_id" in payload:
                self._run_requests[payload["run_id"]] = RunRequestMetadata(
                    payload["request_id"], payload["request_digest"]
                )
        self._budget_states = {}
        self._reservations = {}
        self._admissions = {}
        for run_id, contract_id in runs.items():
            contract = self.ledger.read_contract(contract_id)
            authorized = contract.limits.model_budget if contract else 0
            history = [
                e
                for e in events
                if e.get("kind", "").startswith("budget.") and json.loads(e["payload"]).get("run_id") == run_id
            ]
            state, reservations, admissions = reduce_budget(history, authorized)
            self._budget_states[run_id] = state
            self._reservations.update(
                {
                    rid: Reservation(rid, r["run_id"], r["amount"], tuple(r["obligations"]))
                    for rid, r in reservations.items()
                }
            )
            self._admissions.update(
                {
                    aid: Admission(aid, a["reservation_id"], a["run_id"], a["task_id"], a["amount"])
                    for aid, a in admissions.items()
                }
            )

    def _require_writer(self):
        if self.writer is None:
            raise AuthorityError("read-only rebuilt facade")
        return self.writer

    def _append(self, aggregate, kind, payload, expected_version, *, contract_id):
        writer = self._require_writer()
        contract = self.ledger.read_contract(contract_id)
        if contract is None or contract.status is not ContractState.ACTIVE:
            raise AuthorityError("active execution contract required")
        draft = writer._author(
            self.ledger,
            aggregate,
            kind,
            {**payload, "contract_id": contract_id},
            expected_version,
            contract_generation=contract.generation,
            revocation_epoch=contract.revocation_epoch,
        )
        message_id = hashlib.sha256(draft.canonical()).hexdigest()[:32]
        result = self.ledger.append(draft, writer.context, message_id=message_id)
        for _ in range(4):
            if result.status is not Result.CONTENDED:
                break
            time.sleep(0.02)
            result = self.ledger.append(draft, writer.context, message_id=message_id)
        if result.status not in (Result.APPLIED, Result.DUPLICATE):
            raise ValueError(result.status.value)
        self._replay()
        return result

    def _verify_authentication(self):
        for row in self.ledger.events():
            payload = json.loads(row["payload"])
            self._check_event_authority(self.ledger, row, payload)
            # A live writer may only possess its own authentication key; the
            # ledger has already authenticated every append at the write boundary.
            if self.writer is None or row["writer_id"] == self.writer.context.writer_id:
                self._verify_event_authentication(self.ledger, row, payload)

    def _state(self):
        self.ledger.verify_chain()
        self.ledger.verify_projections()
        self._verify_authentication()
        self._replay()
        return self

    def run(self, run_id):
        return self._state()._runs[run_id]

    def run_request(self, run_id):
        self.run(run_id)
        return self._run_requests.get(run_id)

    def task(self, run_id, task_id):
        return self._state()._tasks[(run_id, task_id)]

    def attempts(self, run_id, task_id):
        return tuple(self._state()._attempts.get((run_id, task_id), ()))

    def sessions(self, run_id, task_id):
        return tuple(self._state()._sessions.get((run_id, task_id), ()))

    def _version(self, aggregate):
        row = self.ledger.conn.execute(
            "SELECT COALESCE(MAX(version),0) FROM events WHERE installation_id=? AND project_id=? AND aggregate=?",
            (self.ledger.scope.installation_id, self.ledger.scope.project_id, aggregate),
        ).fetchone()
        return row[0]

    def release_drafts_for_receipt(self, receipt_payload: Mapping[str, Any]):
        """Derive signed releases completed by one verifier-owned receipt."""
        self._state()
        writer = self._require_writer()
        run_id = receipt_payload.get("run_id")
        task_id = receipt_payload.get("task_id")
        receipt_id = receipt_payload.get("receipt_id")
        contract_id = receipt_payload.get("contract_id")
        if (
            not isinstance(run_id, str)
            or not isinstance(task_id, str)
            or not isinstance(receipt_id, str)
            or not isinstance(contract_id, str)
            or (run_id, task_id) not in self._tasks
            or run_id not in self._runs
            or self._runs[run_id].contract_id != contract_id
        ):
            raise AuthorityError("receipt does not match kernel workflow")
        contract = self.ledger.read_contract(contract_id)
        if contract is None or contract.status is not ContractState.ACTIVE:
            raise AuthorityError("active execution contract required")
        receipts: dict[tuple[str, str], set[str]] = {}
        for event in self.ledger.events():
            if event["kind"] != "evidence.receipt.recorded":
                continue
            payload = json.loads(event["payload"])
            receipts.setdefault((payload["run_id"], payload["task_id"]), set()).add(payload["receipt_id"])
        receipts.setdefault((run_id, task_id), set()).add(receipt_id)
        releases = []
        for (candidate_run, candidate_task), task in sorted(self._tasks.items()):
            if candidate_run != run_id or task.state is not TaskState.BLOCKED:
                continue
            if not all(receipts.get((run_id, prerequisite)) for prerequisite in task.prerequisites):
                continue
            satisfied = [
                {
                    "task_id": prerequisite,
                    "receipt_id": sorted(receipts[(run_id, prerequisite)])[0],
                }
                for prerequisite in sorted(task.prerequisites)
            ]
            aggregate = f"task:{run_id}:{candidate_task}"
            payload = {
                "run_id": run_id,
                "task_id": candidate_task,
                "satisfied_prerequisites": satisfied,
                "contract_id": contract_id,
            }
            draft = writer._author(
                self.ledger,
                aggregate,
                "task.released",
                payload,
                self._version(aggregate),
                contract_generation=contract.generation,
                revocation_epoch=contract.revocation_epoch,
            )
            message_material = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
            releases.append((draft, "release:" + hashlib.sha256(message_material).hexdigest()))
        return tuple(releases)

    def create_run(self, *, run_id, contract_id, mode):
        if mode != RuntimeMode.KERNEL.value:
            raise RuntimeModeError("kernel runs require kernel mode")
        self._state()
        if run_id in self._runs:
            existing = self.run(run_id)
            if existing != RunRecord(run_id, contract_id, mode):
                raise ValueError("conflicting run retry")
            return existing
        payload = {"run_id": run_id, "contract_id": contract_id, "mode": mode}
        self._append("run:" + run_id, "run.created", payload, 0, contract_id=contract_id)
        return self.run(run_id)

    def ensure_run(self, *, run_id, contract_id, mode, request_id, request_digest):
        """Idempotently create the single v0.19.1 run using aggregate CAS."""
        if mode != RuntimeMode.KERNEL.value:
            raise RuntimeModeError("kernel runs require kernel mode")

        def resolve_existing():
            self._state()
            if run_id not in self._runs:
                if self._runs:
                    raise AdmissionLimitError("admission limit")
                return None
            record = self._runs[run_id]
            metadata = self._run_requests.get(run_id)
            if (
                record.contract_id == contract_id
                and record.mode == mode
                and metadata == RunRequestMetadata(request_id, request_digest)
            ):
                return record
            raise IdempotencyConflictError("idempotency conflict")

        existing = resolve_existing()
        if existing is not None:
            return existing
        payload = {
            "run_id": run_id,
            "contract_id": contract_id,
            "mode": mode,
            "request_id": request_id,
            "request_digest": request_digest,
        }
        try:
            self._append("run:" + run_id, "run.created", payload, 0, contract_id=contract_id)
        except ValueError:
            raced = resolve_existing()
            if raced is not None:
                return raced
            raise
        return self.run(run_id)

    def set_runtime_mode(self, run_id, mode):
        if self.run(run_id).mode != mode:
            raise RuntimeModeError("runtime mode is immutable")
        return self.run(run_id)

    def create_task(self, run_id, *, task_id, prerequisites=()):
        self.run(run_id)
        key = (run_id, task_id)
        if key in getattr(self, "_tasks", {}):
            existing = self.task(*key)
            if existing.prerequisites != tuple(prerequisites):
                raise ValueError("conflicting task retry")
            return existing
        payload = {
            "run_id": run_id,
            "task_id": task_id,
            "prerequisites": list(prerequisites),
        }
        self._append(
            "task:%s:%s" % key,
            "task.created",
            payload,
            0,
            contract_id=self.run(run_id).contract_id,
        )
        return self.task(*key)

    def _advance(self, run_id, task_id, kind, target):
        task = self.task(run_id, task_id)
        if task.state is target:
            return task
        transition_state(task.state, target)
        aggregate = "task:%s:%s" % (run_id, task_id)
        payload = {"run_id": run_id, "task_id": task_id, "contract_id": self.run(run_id).contract_id}
        self._append(
            aggregate,
            kind,
            payload,
            self._version(aggregate),
            contract_id=self.run(run_id).contract_id,
        )
        return self.task(run_id, task_id)

    def admit_task(self, run_id, task_id):
        return self._advance(run_id, task_id, "task.admitted", TaskState.ADMITTED)

    def mark_task_ready(self, run_id, task_id):
        return self._advance(run_id, task_id, "task.ready", TaskState.READY)

    def dispatch_task(self, run_id, task_id):
        return self._advance(run_id, task_id, "task.dispatched", TaskState.DISPATCHED)

    def start_attempt(self, run_id, task_id):
        task = self.task(run_id, task_id)
        existing = self.attempts(run_id, task_id)
        if task.state is TaskState.RUNNING and existing:
            return existing[-1]
        transition_state(task.state, TaskState.RUNNING)
        key = (run_id, task_id)
        attempt = len(self.attempts(*key)) + 1
        aggregate = "task:%s:%s" % key
        self._append(
            aggregate,
            "attempt.started",
            {"run_id": run_id, "task_id": task_id, "attempt": attempt},
            self._version(aggregate),
            contract_id=self.run(run_id).contract_id,
        )
        return self.attempts(*key)[-1]

    def bind_logical_session(self, run_id, task_id, *, logical_session):
        self.task(run_id, task_id)
        key = (run_id, task_id)
        for binding in self.sessions(*key):
            if binding.logical_session == logical_session:
                return binding
        aggregate = "task:%s:%s" % key
        payload = {"run_id": run_id, "task_id": task_id, "logical_session": logical_session}
        self._append(
            aggregate,
            "session.bound",
            payload,
            self._version(aggregate),
            contract_id=self.run(run_id).contract_id,
        )
        return SessionBinding(*key, logical_session)

    def budget(self, run_id):
        self.run(run_id)
        return self._state()._budget_states[run_id]

    def _budget_command(self, run_id, kind, payload, command_id, *, amount=None, reservation_id=None):
        self.budget(run_id)
        if not isinstance(command_id, str) or not command_id:
            raise IdempotencyError("command identity required")
        if amount is not None and (not isinstance(amount, int) or isinstance(amount, bool) or amount <= 0):
            raise BudgetTransitionError("invalid amount")
        # Validate intent against the immutable replayed projection before append.
        history = self.ledger.events()
        candidate = {
            "aggregate": "budget:" + run_id,
            "kind": kind,
            "payload": {
                **payload,
                "run_id": run_id,
                "command_id": command_id,
                "contract_id": self.run(run_id).contract_id,
            },
        }
        contract = self.ledger.read_contract(self.run(run_id).contract_id)
        try:
            from .budget import validate_budget_history

            validate_budget_history(history + [candidate], authorized=contract.limits.model_budget)
        except Exception as exc:
            raise exc
        self._append(
            candidate["aggregate"],
            kind,
            candidate["payload"],
            self._version(candidate["aggregate"]),
            contract_id=self.run(run_id).contract_id,
        )
        self._state()

    def reserve_budget(self, run_id, *, amount, command_id):
        rid = "reservation:" + run_id + ":" + command_id
        self._budget_command(
            run_id,
            "budget.reserved",
            {"reservation_id": rid, "amount": amount, "obligations": []},
            command_id,
            amount=amount,
        )
        return self._reservations[rid]

    def reserve_correction(self, run_id, *, task_id, amount, command_id):
        if amount > self.budget(run_id).available:
            raise InsufficientObligations("correction obligations exceed available budget")
        rid = "correction:" + run_id + ":" + task_id + ":" + command_id
        self._budget_command(
            run_id,
            "budget.reserved",
            {"reservation_id": rid, "amount": amount, "task_id": task_id, "obligations": list(OBLIGATIONS)},
            command_id,
            amount=amount,
        )
        return self._reservations[rid]

    def commit_budget(self, run_id, *, reservation_id, amount, command_id):
        self._budget_command(
            run_id, "budget.committed", {"reservation_id": reservation_id, "amount": amount}, command_id, amount=amount
        )
        return self.budget(run_id)

    def spend_budget(self, run_id, *, reservation_id, amount, command_id):
        self._budget_command(
            run_id, "budget.spent", {"reservation_id": reservation_id, "amount": amount}, command_id, amount=amount
        )
        return self.budget(run_id)

    def release_budget(self, run_id, *, reservation_id, amount, command_id):
        self._budget_command(
            run_id, "budget.released", {"reservation_id": reservation_id, "amount": amount}, command_id, amount=amount
        )
        return self.budget(run_id)

    def admit_retry(self, run_id, *, task_id, amount, command_id):
        aid = "admission:" + run_id + ":" + task_id + ":" + command_id
        rid = "retry:" + run_id + ":" + task_id + ":" + command_id
        self._budget_command(
            run_id,
            "budget.retry_admitted",
            {"reservation_id": rid, "admission_id": aid, "task_id": task_id, "amount": amount},
            command_id,
            amount=amount,
        )
        return self._admissions[aid]

    def _admit_action(self, run_id, *, task_id, admission_id, command_id, kind):
        admission = self._admissions.get(admission_id)
        if not admission or admission.run_id != run_id or admission.task_id != task_id:
            raise FreshAdmissionRequired("fresh admission required")
        self._budget_command(
            run_id,
            kind,
            {
                "reservation_id": admission.reservation_id,
                "admission_id": admission_id,
                "task_id": task_id,
                "amount": admission.amount,
            },
            command_id,
        )
        return RetryState("admitted", admission_id, task_id)

    def retry_task(self, run_id, *, task_id, admission_id, command_id):
        return self._admit_action(
            run_id, task_id=task_id, admission_id=admission_id, command_id=command_id, kind="budget.retry_task"
        )

    def replan_task(self, run_id, *, task_id, admission_id, command_id):
        return self._admit_action(
            run_id, task_id=task_id, admission_id=admission_id, command_id=command_id, kind="budget.replan_task"
        )

    def refresh_contract_authority(self, run_id):
        return self.budget(run_id)

    def request_close(self, *, authority, proposed_state, command_id):
        """Persist one fail-closed cleanup obligation without performing cleanup."""
        self._state()
        if not isinstance(proposed_state, CompletionState) or proposed_state not in {
            CompletionState.COMPLETED,
            CompletionState.FAILED,
            CompletionState.CANCELLED,
        }:
            raise InvalidTransition("unsupported semantic closure state")
        if not isinstance(command_id, str) or not command_id:
            raise IdempotencyConflictError("close command identity required")
        required = (
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
            "lease_resource",
            "lease_owner",
            "lease_epoch",
            "lease_token",
        )
        if any(not hasattr(authority, name) for name in (*required, "lease_until")):
            raise AuthorityError("invalid dispatch authority")
        if (authority.installation_id, authority.project_id) != (
            self.ledger.scope.installation_id,
            self.ledger.scope.project_id,
        ):
            raise AuthorityError("dispatch authority scope mismatch")
        key = (authority.run_id, authority.task_id)
        task = self._tasks.get(key)
        run = self._runs.get(authority.run_id)
        if task is None or run is None or run.contract_id != authority.contract_id:
            raise AuthorityError("close authority does not match kernel workflow")
        contract = self.ledger.read_contract(authority.contract_id)
        if (
            contract is None
            or contract.status is not ContractState.ACTIVE
            or contract.generation != authority.contract_generation
            or contract.revocation_epoch != authority.revocation_epoch
        ):
            raise AuthorityError("stale close contract authority")
        if (
            contract.completion_authority.project_id != self.ledger.scope.project_id
            or contract.completion_authority.actor_id != self.writer.context.writer_id
        ):
            raise AuthorityError("contract completion authority required")
        active_attempts = [item for item in self._attempts.get(key, ()) if item.state is AttemptState.ACTIVE]
        if not active_attempts or active_attempts[-1].attempt != authority.attempt:
            raise AuthorityError("stale close attempt authority")
        lease = self.ledger.lease(authority.lease_resource)
        if (
            lease is None
            or lease.owner != authority.lease_owner
            or lease.epoch != authority.lease_epoch
            or lease.token != authority.lease_token
            or lease.expires_at != authority.lease_until
            or lease.expires_at <= self.ledger.clock()
        ):
            raise AuthorityError("stale close dispatch fence")
        staged = [
            json.loads(event["payload"])
            for event in self.ledger.events()
            if event["kind"] == "dispatch.staged"
            and json.loads(event["payload"]).get("message_id") == authority.message_id
        ]
        if len(staged) != 1 or any(staged[0].get(name) != getattr(authority, name) for name in required):
            raise AuthorityError("close authority does not match durable dispatch")
        receipts = [
            json.loads(event["payload"])
            for event in self.ledger.events()
            if event["kind"] == "evidence.receipt.recorded"
            and json.loads(event["payload"]).get("message_id") == authority.message_id
        ]
        if len(receipts) != 1:
            raise AuthorityError("trusted evidence receipt required")
        receipt = receipts[0]
        identity_fields = (
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
        if any(receipt.get(name) != getattr(authority, name) for name in identity_fields):
            raise AuthorityError("evidence receipt does not match close authority")
        expected_state = {
            "completed": CompletionState.COMPLETED,
            "error": CompletionState.FAILED,
            "cancelled": CompletionState.CANCELLED,
        }.get(receipt.get("terminal", {}).get("technical_status"))
        if expected_state is not proposed_state:
            raise InvalidTransition("semantic closure conflicts with trusted evidence")
        payload = {
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
            "fence": authority.lease_epoch,
            "lease_resource": authority.lease_resource,
            "lease_owner": authority.lease_owner,
            "lease_epoch": authority.lease_epoch,
            "lease_token": authority.lease_token,
            "lease_until": authority.lease_until,
            "acp_session_id": receipt["acp_session_id"],
            "evidence_receipt_id": receipt["receipt_id"],
            "cleanup_command_id": "cleanup:" + command_id,
            "command_id": command_id,
            "proposed_state": proposed_state.value,
        }
        payload["closure_proposal_hash"] = closure_proposal_hash(payload)
        prior = [
            json.loads(event["payload"])
            for event in self.ledger.events()
            if event["kind"] == "close.requested"
            and json.loads(event["payload"]).get("run_id") == authority.run_id
            and json.loads(event["payload"]).get("task_id") == authority.task_id
        ]
        if prior:
            if prior[0] != payload:
                raise IdempotencyConflictError("close command conflict")
            return self.task(*key)
        if task.state is not TaskState.RUNNING:
            raise InvalidTransition("task is not eligible for close intent")
        aggregate = f"task:{authority.run_id}:{authority.task_id}"
        self._append(
            aggregate,
            "close.requested",
            payload,
            self._version(aggregate),
            contract_id=authority.contract_id,
        )
        return self.task(*key)

    def complete_task(self, run_id, task_id):
        raise InvalidTransition("completion gates are not implemented")


__all__ = ["KernelRunService", "KernelWriter", "InvalidTransition", "RuntimeModeError"]
