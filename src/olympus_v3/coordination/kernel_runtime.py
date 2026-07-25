"""Authenticated semantic command boundary for the durable kernel workflow."""

from __future__ import annotations

import hashlib
import json
import time
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
from .contracts import ContractState, TaskState
from .ledger import HMACWriterAuthenticator, Result, SignedEventDraft, SQLiteLedger, WriterContext
from .workflow import (
    AttemptRecord,
    AuthorityError,
    InvalidTransition,
    RunRecord,
    RuntimeMode,
    RuntimeModeError,
    SessionBinding,
    TaskRecord,
    transition_state,
)


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
        if row["kind"] == "outbox.poison":
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
                raise AuthorityError("internal poison authentication failed")
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
            run_id: (self.ledger.read_contract(contract_id).limits.model_budget if self.ledger.read_contract(contract_id) else 0)
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
        self._sessions = {
            key: [SessionBinding(key[0], key[1], value) for value in values] for key, values in sessions.items()
        }
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

    def complete_task(self, run_id, task_id):
        raise InvalidTransition("completion gates are not implemented")


__all__ = ["KernelRunService", "KernelWriter", "InvalidTransition", "RuntimeModeError"]
