"""Durable, fenced kernel dispatch composition for R11."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .contracts import ContractState
from .evidence import (
    EvidenceIdentity,
    EvidenceVerificationError,
    build_evidence_receipt,
    verify_artifact,
)
from .leases import Lease
from .ledger import Result, SQLiteLedger, StoreScope
from .workflow import AttemptState, kernel_logical_session


class DispatchRejected(ValueError):
    pass


class StaleFence(DispatchRejected):
    pass


class ReconciliationRequired(DispatchRejected):
    pass


@dataclass(frozen=True, slots=True)
class DispatchAuthority:
    installation_id: str
    project_id: str
    run_id: str
    task_id: str
    attempt: int
    contract_id: str
    contract_generation: int
    revocation_epoch: int
    agent_name: str
    plan_id: str
    plan_revision: int
    snapshot_digest: str
    project_root: str
    logical_session: str
    message_id: str
    lease_resource: str
    lease_owner: str
    lease_epoch: int
    lease_token: str
    lease_until: int

    def as_lease(self) -> Lease:
        return Lease(
            StoreScope(self.installation_id, self.project_id),
            self.lease_resource,
            self.lease_owner,
            self.lease_epoch,
            self.lease_until,
            self.lease_token,
        )


@dataclass(frozen=True, slots=True)
class DispatchEnvelope:
    authority: DispatchAuthority
    payload: Mapping[str, Any]

    @property
    def message_id(self):
        return self.authority.message_id


@dataclass(frozen=True, slots=True)
class DispatchObservation:
    status: str
    acp_session_id: str | None = None
    progress: Mapping[str, Any] = None


@dataclass(frozen=True, slots=True)
class ReconciliationEvidence:
    authority: DispatchAuthority
    observation: str


class KernelDispatcher:
    """Kernel command boundary; all replay authority remains in SQLiteLedger."""

    def __init__(self, *, ledger: SQLiteLedger, runtime: Any, runtime_adapter: Any, worker_id: str | None = None):
        if not isinstance(ledger, SQLiteLedger):
            raise TypeError("ledger required")
        self.ledger, self.runtime, self.runtime_adapter = ledger, runtime, runtime_adapter
        self._writer = getattr(runtime, "writer", None)
        if self._writer is None:
            raise DispatchRejected("writable kernel runtime required")
        derived = worker_id or getattr(runtime, "worker_id", None) or self._writer.context.writer_id
        if not isinstance(derived, str) or not derived or not derived.replace("-", "").replace("_", "").isalnum():
            raise DispatchRejected("stable worker identity required")
        self._owner = derived

    def _contract(self, run_id: str):
        try:
            run = self.runtime.run(run_id)
        except (KeyError, ValueError) as exc:
            raise DispatchRejected("unknown kernel run") from exc
        contract = self.ledger.read_contract(run.contract_id)
        if contract is None or contract.status is not ContractState.ACTIVE:
            raise DispatchRejected("active contract required")
        return run, contract

    def _lease(self, authority: DispatchAuthority) -> Lease:
        lease = Lease(
            self.ledger.scope,
            authority.lease_resource,
            authority.lease_owner,
            authority.lease_epoch,
            authority.lease_until,
            authority.lease_token,
        )
        checked = self.ledger.check_lease(lease, self._owner)
        if checked.lease is None:
            if checked.status.value == "LEASE_EXPIRED":
                raise StaleFence("expired fence")
            raise StaleFence("stale fence")
        return checked.lease

    def _authority_current(self, authority: DispatchAuthority) -> Lease:
        try:
            run, contract = self._contract(authority.run_id)
            task = self.runtime.task(authority.run_id, authority.task_id)
            attempts = self.runtime.attempts(authority.run_id, authority.task_id)
        except Exception as exc:
            raise DispatchRejected("unknown kernel authority") from exc
        if (
            run.contract_id != authority.contract_id
            or task.run_id != authority.run_id
            or not any(a.attempt == authority.attempt for a in attempts)
        ):
            raise DispatchRejected("authority mismatch")
        current = next(a for a in attempts if a.attempt == authority.attempt)
        if (
            current.state is not AttemptState.ACTIVE
            or contract.generation != authority.contract_generation
            or contract.revocation_epoch != authority.revocation_epoch
        ):
            raise StaleFence("replaced or revoked authority")
        return self._lease(authority)

    def _signed_draft(self, kind: str, aggregate: str, payload: Mapping[str, Any]):
        writer: Any = self._writer
        if writer is None:
            raise DispatchRejected("writable kernel runtime required")
        contract = self.ledger.read_contract(payload["contract_id"])
        if contract is None or contract.status is not ContractState.ACTIVE:
            raise DispatchRejected("active contract required")
        draft = self.ledger.draft(
            aggregate,
            kind,
            dict(payload),
            writer=writer.context,
            expected_version=self._version(aggregate),
            contract_generation=contract.generation,
            revocation_epoch=contract.revocation_epoch,
        )
        return writer.authenticator.sign(draft, writer.context)

    def _append(self, kind: str, aggregate: str, payload: Mapping[str, Any], *, message_id: str | None = None):
        writer: Any = self._writer
        if writer is None:
            raise DispatchRejected("writable kernel runtime required")
        signed = self._signed_draft(kind, aggregate, payload)
        result = self.ledger.append(signed, writer.context, message_id=message_id)
        if result.status not in (Result.APPLIED, Result.DUPLICATE):
            raise DispatchRejected(result.status.value)
        return result

    def _version(self, aggregate: str) -> int:
        return self.ledger.aggregate_version(aggregate)

    @staticmethod
    def _plan_id(run_id, task_id, attempt, revision, digest):
        return hashlib.sha256(f"{run_id}:{task_id}:{attempt}:{revision}:{digest}".encode()).hexdigest()[:32]

    def stage_ready(
        self, run_id: str, task_id: str, *, attempt: int, project_root: str, plan_revision: int, snapshot_digest: str
    ) -> DispatchEnvelope:
        run, contract = self._contract(run_id)
        try:
            task = self.runtime.task(run_id, task_id)
        except (KeyError, ValueError) as exc:
            raise DispatchRejected("unknown kernel task") from exc
        attempts = self.runtime.attempts(run_id, task_id)
        if task.state.value != "running" or not any(
            a.attempt == attempt and a.state is AttemptState.ACTIVE for a in attempts
        ):
            raise DispatchRejected("active running attempt required")
        if (
            not isinstance(project_root, str)
            or not project_root.startswith("/")
            or not isinstance(plan_revision, int)
            or not isinstance(snapshot_digest, str)
            or not snapshot_digest
        ):
            raise DispatchRejected("invalid dispatch inputs")
        project_root = str(Path(project_root).resolve())
        logical = kernel_logical_session(self.ledger.scope.project_id, run_id, task_id, attempt)
        workers = tuple(participant for participant in contract.participants if participant != contract.owner)
        if len(workers) != 1:
            raise DispatchRejected("dispatch requires exactly one contract worker")
        agent_name = workers[0].actor_id
        plan_id = self._plan_id(run_id, task_id, attempt, plan_revision, snapshot_digest + ":" + agent_name)
        message_id = "000" + hashlib.sha256(f"{plan_id}:{logical}:{self._owner}".encode()).hexdigest()[:29]
        existing = next(
            (
                event
                for event in self.ledger.events()
                if event["kind"] == "dispatch.staged" and json.loads(event["payload"]).get("message_id") == message_id
            ),
            None,
        )
        if existing:
            prior = self._envelope(json.loads(existing["payload"]))
            if self.ledger.check_lease(prior.authority.as_lease(), self._owner).lease is not None:
                return prior
        lease_resource = f"dispatch:{run_id}:{task_id}:{attempt}"
        now = self.ledger.clock()
        writer_remaining = max(1, self._writer.context.expires_at - now)
        acquired = self.ledger.acquire_lease(
            lease_resource,
            self._owner,
            ttl=min(10_000_000_000, writer_remaining),
        ).lease
        if acquired is None:
            raise StaleFence("attempt fence unavailable")
        authority = DispatchAuthority(
            self.ledger.scope.installation_id,
            self.ledger.scope.project_id,
            run_id,
            task_id,
            attempt,
            contract.contract_id,
            contract.generation,
            contract.revocation_epoch,
            agent_name,
            plan_id,
            plan_revision,
            snapshot_digest,
            project_root,
            logical,
            message_id,
            acquired.resource,
            self._owner,
            acquired.epoch,
            acquired.token,
            acquired.expires_at,
        )
        payload = {
            "installation_id": authority.installation_id,
            "project_id": authority.project_id,
            "run_id": run_id,
            "task_id": task_id,
            "attempt": attempt,
            "contract_id": contract.contract_id,
            "contract_generation": contract.generation,
            "revocation_epoch": contract.revocation_epoch,
            "agent_name": agent_name,
            "plan_id": plan_id,
            "plan_revision": plan_revision,
            "snapshot_digest": snapshot_digest,
            "project_root": project_root,
            "logical_session": logical,
            "message_id": message_id,
            "lease_resource": acquired.resource,
            "lease_owner": self._owner,
            "lease_epoch": acquired.epoch,
            "lease_token": acquired.token,
            "lease_until": acquired.expires_at,
            "envelope": {"run_id": run_id, "task_id": task_id, "attempt": attempt},
        }
        self._append("dispatch.staged", "dispatch:" + message_id, payload, message_id=message_id)
        return self._envelope(payload)

    @staticmethod
    def _envelope(payload):
        authority = DispatchAuthority(
            *(
                payload[name]
                for name in (
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
                )
            )
        )
        return DispatchEnvelope(authority, payload)

    def _row(self, authority):
        return self.ledger.outbox_message(authority.message_id)

    def _transport_lease(self) -> Lease:
        lease = self.ledger.lease("outbox")
        if lease is not None and self.ledger.check_lease(lease, self._owner).lease is not None:
            return lease
        acquired = self.ledger.acquire_lease("outbox", self._owner, ttl=10_000_000_000).lease
        if acquired is None:
            raise StaleFence("transport fence unavailable")
        return acquired

    def _claimed_transport_lease(self, row: Mapping[str, Any]) -> Lease:
        if (
            row.get("lease_owner") != self._owner
            or not isinstance(row.get("lease_epoch"), int)
            or not isinstance(row.get("lease_token"), str)
            or not isinstance(row.get("lease_until"), int)
        ):
            raise StaleFence("dispatch is not claimed by this dispatcher")
        lease = Lease(
            self.ledger.scope,
            "outbox",
            self._owner,
            row["lease_epoch"],
            row["lease_until"],
            row["lease_token"],
        )
        if self.ledger.check_lease(lease, self._owner).lease is None:
            raise StaleFence("stale transport fence")
        return lease

    def claim_with(self, authority):
        self._authority_current(authority)
        row = self._row(authority)
        if not row:
            raise DispatchRejected("missing dispatch")
        if row["status"] == "UNKNOWN":
            raise ReconciliationRequired("typed reconciliation required")
        if row["status"] == "SENT":
            return row
        if row["status"] == "LEASED":
            try:
                self._claimed_transport_lease(row)
                return row
            except StaleFence:
                pass
        if row["status"] == "RETRY_WAIT" and row["lease_until"] > self.ledger.clock():
            return None
        rows = self.ledger.claim_outbox(
            self._owner,
            lease=self._transport_lease(),
            message_id=authority.message_id,
            now=self.ledger.clock(),
        )
        return rows[0] if rows else self._row(authority)

    def claim_once(self):
        for event in self.ledger.events():
            if event["kind"] != "dispatch.staged":
                continue
            authority = self._envelope(json.loads(event["payload"])).authority
            row = self._row(authority)
            if row and row["status"] in {"PENDING", "RETRY_WAIT", "LEASED"}:
                claimed = self.claim_with(authority)
                if claimed is not None:
                    return claimed
        return None

    def _record_unknown(self, authority: DispatchAuthority, reason: str) -> None:
        row = self._row(authority)
        if row is None:
            raise DispatchRejected("missing dispatch")
        result = self.ledger.mark_outbox_unknown(
            authority.message_id,
            self._owner,
            lease=self._claimed_transport_lease(row),
            reason=reason,
            authority={
                "run_id": authority.run_id,
                "task_id": authority.task_id,
                "attempt": authority.attempt,
                "contract_id": authority.contract_id,
            },
        )
        if result is not Result.APPLIED:
            raise StaleFence(result.value)

    def _canonical_prompt(self, authority: DispatchAuthority) -> str:
        contract = self.ledger.read_contract(authority.contract_id)
        if contract is None or contract.status is not ContractState.ACTIVE:
            raise DispatchRejected("active contract required")
        prompt = {
            "kind": "aether.harmonia.task.v1",
            "authority": {
                "project_id": authority.project_id,
                "run_id": authority.run_id,
                "task_id": authority.task_id,
                "attempt": authority.attempt,
                "contract_id": authority.contract_id,
                "contract_generation": authority.contract_generation,
                "plan_id": authority.plan_id,
                "plan_revision": authority.plan_revision,
                "snapshot_digest": authority.snapshot_digest,
                "message_id": authority.message_id,
            },
            "contract": {
                "objective": contract.objective,
                "expected_outcome": contract.expected_outcome,
                "included_scopes": list(contract.included_scopes),
                "excluded_scopes": list(contract.excluded_scopes),
                "worker_id": authority.agent_name,
                "role_permissions": list(contract.role_permissions.get(authority.agent_name, ())),
                "limits": {
                    "max_parallel_tasks": contract.limits.concurrency,
                    "max_runtime_seconds": contract.limits.time_seconds,
                    "max_retries": contract.limits.retries,
                    "model_budget": contract.limits.model_budget,
                    "network_budget": contract.limits.qa_reserve,
                    "tool_budget": contract.limits.recovery_reserve,
                },
                "side_effect_policy": {
                    "allowed_effects": list(contract.side_effect_policy.allowed_effects),
                    "approval_threshold": contract.side_effect_policy.max_external_actions,
                    "rollback_required": contract.side_effect_policy.reversible,
                },
                "escalation_conditions": list(contract.escalation_conditions),
            },
            "task": {
                "task_id": authority.task_id,
                "attempt": authority.attempt,
                "project_root": authority.project_root,
            },
            "acceptance_evidence": [
                {"name": gate.name, "required": gate.required, "state": gate.state.value}
                for gate in contract.evidence_gates
            ],
            "instructions": [
                "Do not delegate.",
                "Do not widen scope.",
                "Do not modify the contract.",
                "Do not claim completion without evidence.",
                "Report blockers and stop when authority is insufficient.",
            ],
        }
        return json.dumps(prompt, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    async def dispatch_with(self, authority):
        self._authority_current(authority)
        row = self.claim_with(authority)
        if row is None:
            return None
        if row["status"] == "UNKNOWN":
            raise ReconciliationRequired("typed reconciliation required")
        if any(
            binding.logical_session == authority.logical_session
            for binding in self.runtime.sessions(authority.run_id, authority.task_id)
        ):
            return {"accepted": True, "replayed": True}
        # Persist this conservative pre-effect marker before the first external
        # await. A crash after Olympus may have accepted cannot be retried from
        # a merely leased row; recovery turns it into durable UNKNOWN instead.
        if row["reconciliation_required"]:
            self._record_unknown(authority, "recovered possible accepted dispatch")
            return None
        armed = self.ledger.mark_outbox_effect_started(
            authority.message_id,
            self._owner,
            lease=self._claimed_transport_lease(row),
        )
        if armed is not Result.APPLIED:
            raise StaleFence(armed.value)
        prompt = self._canonical_prompt(authority)
        request = {
            "run_id": authority.run_id,
            "task_id": authority.task_id,
            "attempt": authority.attempt,
            "project_root": authority.project_root,
            "logical_session": authority.logical_session,
            "message_id": authority.message_id,
            "plan_id": authority.plan_id,
            "agent_name": authority.agent_name,
            "prompt": prompt,
            "prompt_digest": "sha256:" + hashlib.sha256(prompt.encode()).hexdigest(),
        }
        try:
            if callable(getattr(self.runtime_adapter, "dispatch_kernel", None)):
                response = await self.runtime_adapter.dispatch_kernel(authority=authority, request=request)
            else:
                response = await self.runtime_adapter.dispatch(**request)
        except ConnectionError as exc:
            row = self._row(authority)
            result = self.ledger.mark_outbox_retry(
                authority.message_id,
                self._owner,
                lease=self._claimed_transport_lease(row or {}),
                now=self.ledger.clock(),
                error=str(exc),
            )
            if result not in {Result.RETRY_SCHEDULED, Result.POISON_TERMINATED}:
                raise StaleFence(result.value)
            return None
        except TimeoutError as exc:
            self._record_unknown(authority, str(exc))
            return None
        acp = response.get("acp_session_id") if isinstance(response, Mapping) else None
        if not isinstance(acp, str) or not acp:
            self._record_unknown(authority, "runtime accepted without durable ACP identity")
            return None
        if any(
            binding.logical_session == authority.logical_session
            for binding in self.runtime.sessions(authority.run_id, authority.task_id)
        ):
            return response
        try:
            self._append(
                "session.bound",
                f"task:{authority.run_id}:{authority.task_id}",
                {
                    "run_id": authority.run_id,
                    "task_id": authority.task_id,
                    "logical_session": authority.logical_session,
                    "contract_id": authority.contract_id,
                    "acp_session_id": acp,
                    "attempt": authority.attempt,
                    "message_id": authority.message_id,
                    "fence": authority.lease_epoch,
                },
            )
        except Exception as exc:
            self._record_unknown(authority, f"binding persistence failed: {exc}")
            return None
        row = self._row(authority)
        acknowledged = self.ledger.mark_outbox_sent(
            authority.message_id,
            self._owner,
            lease=self._claimed_transport_lease(row or {}),
        )
        if acknowledged is not Result.TRANSPORT_ACKNOWLEDGED:
            self._record_unknown(authority, f"transport acknowledgement failed: {acknowledged.value}")
            return None
        return response

    async def dispatch_once(self):
        for event in self.ledger.events():
            if event["kind"] != "dispatch.staged":
                continue
            authority = self._envelope(json.loads(event["payload"])).authority
            row = self._row(authority)
            if row and row["status"] in {"PENDING", "RETRY_WAIT", "LEASED"}:
                if row["status"] == "RETRY_WAIT" and row["lease_until"] > self.ledger.clock():
                    continue
                return await self.dispatch_with(authority)
        if any(
            event["kind"] == "dispatch.staged"
            and (self._row(self._envelope(json.loads(event["payload"])).authority) or {}).get("status") == "UNKNOWN"
            for event in self.ledger.events()
        ):
            raise ReconciliationRequired("typed reconciliation required")
        return None

    def ack_once(self):
        for event in self.ledger.events():
            if event["kind"] != "dispatch.staged":
                continue
            authority = self._envelope(json.loads(event["payload"])).authority
            row = self._row(authority)
            if row and row["status"] == "LEASED":
                return self.acknowledge(authority)
        return None

    def acknowledge(self, authority):
        self._authority_current(authority)
        row = self._row(authority)
        return self.ledger.mark_outbox_sent(
            authority.message_id,
            self._owner,
            lease=self._claimed_transport_lease(row or {}),
        )

    def renew_with(self, authority: DispatchAuthority, *, ttl: int):
        """Renew the exact dispatch fence, never reacquiring it."""
        current = self._authority_current(authority)
        now = self.ledger.clock()
        extension = current.expires_at - now + ttl
        outcome = self.ledger.renew_lease(current, self._owner, ttl=extension, token=authority.lease_token)
        if outcome.lease is None:
            raise StaleFence(outcome.status.value)
        return outcome

    def record_terminal_with(self, authority: DispatchAuthority, observation: Any):
        """Persist authenticated technical terminal evidence exactly once."""
        self._authority_current(authority)
        status = getattr(observation, "status", None)
        logical_session = getattr(observation, "logical_session", None)
        acp_session_id = getattr(observation, "acp_session_id", None)
        message_id = getattr(observation, "message_id", None)
        if (
            status not in {"completed", "error", "cancelled"}
            or logical_session != authority.logical_session
            or not isinstance(acp_session_id, str)
            or not acp_session_id
            or message_id != authority.message_id
        ):
            raise DispatchRejected("terminal evidence does not match dispatch authority")
        bindings = [
            json.loads(event["payload"])
            for event in self.ledger.events()
            if event["kind"] == "session.bound"
            and json.loads(event["payload"]).get("message_id") == authority.message_id
        ]
        if len(bindings) != 1 or bindings[0].get("acp_session_id") != acp_session_id:
            raise DispatchRejected("terminal evidence does not match durable session binding")
        payload = {
            "run_id": authority.run_id,
            "task_id": authority.task_id,
            "attempt": authority.attempt,
            "contract_id": authority.contract_id,
            "contract_generation": authority.contract_generation,
            "revocation_epoch": authority.revocation_epoch,
            "message_id": authority.message_id,
            "logical_session": authority.logical_session,
            "acp_session_id": acp_session_id,
            "status": status,
        }
        prior = [
            json.loads(event["payload"])
            for event in self.ledger.events()
            if event["kind"] == "runtime.terminal.observed"
            and json.loads(event["payload"]).get("message_id") == authority.message_id
        ]
        if prior:
            if prior[0] != payload:
                raise DispatchRejected("conflicting terminal evidence")
            return Result.APPLIED
        return self._append("runtime.terminal.observed", "dispatch:" + authority.message_id, payload).status

    @staticmethod
    def _evidence_identity(authority: DispatchAuthority, acp_session_id: str) -> EvidenceIdentity:
        return EvidenceIdentity(
            installation_id=authority.installation_id,
            project_id=authority.project_id,
            run_id=authority.run_id,
            task_id=authority.task_id,
            attempt=authority.attempt,
            contract_id=authority.contract_id,
            contract_generation=authority.contract_generation,
            revocation_epoch=authority.revocation_epoch,
            message_id=authority.message_id,
            logical_session=authority.logical_session,
            acp_session_id=acp_session_id,
        )

    def record_evidence_with(self, authority: DispatchAuthority):
        """Verify the fixed result artifact and persist one authority-bound receipt."""
        self._authority_current(authority)
        terminal_events = [
            json.loads(event["payload"])
            for event in self.ledger.events()
            if event["kind"] == "runtime.terminal.observed"
            and json.loads(event["payload"]).get("message_id") == authority.message_id
        ]
        if len(terminal_events) != 1:
            raise DispatchRejected("durable terminal evidence required")
        terminal = terminal_events[0]
        expected = {
            "run_id": authority.run_id,
            "task_id": authority.task_id,
            "attempt": authority.attempt,
            "contract_id": authority.contract_id,
            "contract_generation": authority.contract_generation,
            "revocation_epoch": authority.revocation_epoch,
            "message_id": authority.message_id,
            "logical_session": authority.logical_session,
        }
        if any(terminal.get(key) != value for key, value in expected.items()):
            raise DispatchRejected("terminal evidence does not match dispatch authority")
        acp_session_id = terminal.get("acp_session_id")
        status = terminal.get("status")
        if not isinstance(acp_session_id, str) or status not in {"completed", "error", "cancelled"}:
            raise DispatchRejected("invalid durable terminal evidence")
        identity = self._evidence_identity(authority, acp_session_id)
        try:
            artifact = verify_artifact(Path(authority.project_root), identity)
            receipt = build_evidence_receipt(identity, artifact, status)
        except EvidenceVerificationError as exc:
            raise DispatchRejected(exc.code) from exc
        self._authority_current(authority)
        payload = receipt.event_payload()
        receipt_message_id = "evidence:" + authority.message_id
        receipt_draft = self._signed_draft(
            "evidence.receipt.recorded",
            receipt_message_id,
            payload,
        )
        releases = self.runtime.release_drafts_for_receipt(payload)
        writer: Any = self._writer
        if writer is None:
            raise DispatchRejected("writable kernel runtime required")
        if releases:
            result = self.ledger.append_evidence_release_batch(
                receipt_draft,
                writer.context,
                receipt_message_id,
                releases,
            )
        else:
            result = self.ledger.append(
                receipt_draft,
                writer.context,
                message_id=receipt_message_id,
            )
        if result.status not in (Result.APPLIED, Result.DUPLICATE):
            raise DispatchRejected(result.status.value)
        return result.status

    async def observe_with(self, authority):
        self._authority_current(authority)
        request = {
            "run_id": authority.run_id,
            "task_id": authority.task_id,
            "attempt": authority.attempt,
            "project_root": authority.project_root,
            "logical_session": authority.logical_session,
            "message_id": authority.message_id,
        }
        if callable(getattr(self.runtime_adapter, "observe_kernel", None)):
            response = await self.runtime_adapter.observe_kernel(authority=authority, request=request)
        else:
            response = await self.runtime_adapter.observe(**request)
        status = response.get("status", "unknown")
        prior = next(
            (
                json.loads(event["payload"])
                for event in reversed(self.ledger.events())
                if event["kind"] == "observation.accepted"
                and json.loads(event["payload"]).get("message_id") == authority.message_id
            ),
            None,
        )
        if prior is None or prior.get("status") != status:
            self._append(
                "observation.accepted",
                "dispatch:" + authority.message_id,
                {
                    "run_id": authority.run_id,
                    "task_id": authority.task_id,
                    "attempt": authority.attempt,
                    "contract_id": authority.contract_id,
                    "message_id": authority.message_id,
                    "status": status,
                },
            )
        return DispatchObservation(status, response.get("acp_session_id"), response)

    async def observe_once(self, run_id, task_id, *, attempt):
        event = next(
            e
            for e in self.ledger.events()
            if e["kind"] == "dispatch.staged"
            and json.loads(e["payload"])["run_id"] == run_id
            and json.loads(e["payload"])["task_id"] == task_id
            and json.loads(e["payload"])["attempt"] == attempt
        )
        return await self.observe_with(self._envelope(json.loads(event["payload"])).authority)

    def cancel_with(self, authority):
        self._authority_current(authority)
        return self._append(
            "cancel.intent",
            "dispatch:" + authority.message_id,
            {
                "run_id": authority.run_id,
                "task_id": authority.task_id,
                "attempt": authority.attempt,
                "contract_id": authority.contract_id,
                "message_id": authority.message_id,
            },
        )

    def cancel(self, run_id, task_id, *, attempt):
        event = next(
            e
            for e in self.ledger.events()
            if e["kind"] == "dispatch.staged"
            and json.loads(e["payload"])["run_id"] == run_id
            and json.loads(e["payload"])["task_id"] == task_id
            and json.loads(e["payload"])["attempt"] == attempt
        )
        return self.cancel_with(self._envelope(json.loads(event["payload"])).authority)

    async def deliver_cancel_with(self, authority):
        self._authority_current(authority)
        if not any(
            event["kind"] == "cancel.intent" and json.loads(event["payload"]).get("message_id") == authority.message_id
            for event in self.ledger.events()
        ):
            raise DispatchRejected("cancellation intent must be durable before effect")
        request = {
            "run_id": authority.run_id,
            "task_id": authority.task_id,
            "attempt": authority.attempt,
            "project_root": authority.project_root,
            "logical_session": authority.logical_session,
            "message_id": authority.message_id,
        }
        if callable(getattr(self.runtime_adapter, "cancel_kernel", None)):
            return await self.runtime_adapter.cancel_kernel(authority=authority, request=request)
        return await self.runtime_adapter.cancel(**request)

    async def deliver_cancel_once(self, run_id, task_id, *, attempt):
        event = next(
            item
            for item in self.ledger.events()
            if item["kind"] == "dispatch.staged"
            and json.loads(item["payload"])["run_id"] == run_id
            and json.loads(item["payload"])["task_id"] == task_id
            and json.loads(item["payload"])["attempt"] == attempt
        )
        return await self.deliver_cancel_with(self._envelope(json.loads(event["payload"])).authority)

    def accept_result(self, authority, result):
        self._authority_current(authority)
        if not isinstance(result, Mapping) or not isinstance(result.get("status"), str):
            raise DispatchRejected("invalid technical observation")
        already = any(
            event["kind"] == "observation.accepted"
            and json.loads(event["payload"]).get("message_id") == authority.message_id
            and json.loads(event["payload"]).get("status") == result["status"]
            for event in self.ledger.events()
        )
        if not already:
            self._append(
                "observation.accepted",
                "dispatch:" + authority.message_id,
                {
                    "run_id": authority.run_id,
                    "task_id": authority.task_id,
                    "attempt": authority.attempt,
                    "contract_id": authority.contract_id,
                    "message_id": authority.message_id,
                    "status": result["status"],
                },
            )
        return result

    def reconcile_unknown(self, run_id, task_id, *, attempt, evidence):
        if evidence is None:
            raise ReconciliationRequired("typed evidence required")
        if not isinstance(evidence, ReconciliationEvidence):
            raise ReconciliationRequired("typed evidence required")
        event = next(
            e
            for e in self.ledger.events()
            if e["kind"] == "dispatch.staged"
            and json.loads(e["payload"])["run_id"] == run_id
            and json.loads(e["payload"])["task_id"] == task_id
            and json.loads(e["payload"])["attempt"] == attempt
        )
        authority = self._envelope(json.loads(event["payload"])).authority
        self._authority_current(authority)
        if evidence.authority != authority:
            raise ReconciliationRequired("evidence authority mismatch")
        self._append(
            "reconciliation.completed",
            "dispatch:" + authority.message_id,
            {
                "run_id": run_id,
                "task_id": task_id,
                "attempt": attempt,
                "contract_id": authority.contract_id,
                "message_id": authority.message_id,
                "status": "reconciled",
                "observation": evidence.observation,
            },
        )
        return (
            self.ledger.reconcile_outbox(
                authority.message_id,
                authority={
                    "contract_id": authority.contract_id,
                    "contract_generation": authority.contract_generation,
                    "revocation_epoch": authority.revocation_epoch,
                },
            )
            is Result.APPLIED
        )

    def reconcile_expired(self, run_id, task_id, *, attempt):
        event = next(
            e
            for e in self.ledger.events()
            if e["kind"] == "dispatch.staged"
            and json.loads(e["payload"])["run_id"] == run_id
            and json.loads(e["payload"])["task_id"] == task_id
            and json.loads(e["payload"])["attempt"] == attempt
        )
        authority = self._envelope(json.loads(event["payload"])).authority
        if self.ledger.check_lease(authority.as_lease(), authority.lease_owner).lease is not None:
            raise StaleFence("attempt fence is still live")
        # The original command lease is intentionally expired.  Rotate the
        # authenticated writer fence before recording the durable orphan.
        renewed = self.ledger.acquire_lease(
            self._writer.context.resource, self._writer.context.writer_id, ttl=10_000_000_000
        ).lease
        if renewed is not None:
            from .kernel_runtime import KernelWriter
            from .ledger import WriterContext

            context = WriterContext(
                self.ledger.scope,
                self._writer.context.writer_id,
                self._writer.context.key_id,
                renewed.resource,
                renewed.epoch,
                renewed.expires_at,
            )
            self._writer = KernelWriter(context, self._writer.authenticator)
        self._append(
            "attempt.orphaned",
            f"task:{run_id}:{task_id}",
            {"run_id": run_id, "task_id": task_id, "attempt": attempt, "contract_id": authority.contract_id},
        )
        self._append(
            "cancel.intent",
            "dispatch:" + authority.message_id,
            {
                "run_id": run_id,
                "task_id": task_id,
                "attempt": attempt,
                "contract_id": authority.contract_id,
                "message_id": authority.message_id,
            },
        )

    def supersede_attempt(self, run_id, task_id, *, attempt, replacement_attempt):
        if (
            not isinstance(replacement_attempt, int)
            or isinstance(replacement_attempt, bool)
            or replacement_attempt != attempt + 1
        ):
            raise DispatchRejected("replacement attempt must be the next monotonic attempt")
        event = next(
            e
            for e in self.ledger.events()
            if e["kind"] == "dispatch.staged"
            and json.loads(e["payload"])["run_id"] == run_id
            and json.loads(e["payload"])["task_id"] == task_id
            and json.loads(e["payload"])["attempt"] == attempt
        )
        authority = self._envelope(json.loads(event["payload"])).authority
        self._authority_current(authority)
        self._append(
            "attempt.superseded",
            f"task:{run_id}:{task_id}",
            {
                "run_id": run_id,
                "task_id": task_id,
                "attempt": attempt,
                "replacement_attempt": replacement_attempt,
                "contract_id": authority.contract_id,
            },
        )


__all__ = [
    "KernelDispatcher",
    "DispatchAuthority",
    "DispatchEnvelope",
    "DispatchObservation",
    "DispatchRejected",
    "StaleFence",
    "ReconciliationRequired",
    "ReconciliationEvidence",
]
