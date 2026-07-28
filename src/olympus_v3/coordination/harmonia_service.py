"""Default-off orchestration for one durable Harmonia kernel task."""

from __future__ import annotations

import asyncio
import hashlib
import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Iterable, Mapping

from olympus_v3.config_loader import CoordinationConfig

from .contracts import (
    ContractLimits,
    ContractState,
    ExecutionContract,
    Principal,
    SideEffectPolicy,
    TaskState,
)
from .harmonia_contract import (
    HarmoniaStartRequest,
    HarmoniaStatusRequest,
    HarmoniaStopRequest,
    InvalidHarmoniaRequest,
    parse_harmonia_request,
    public_error,
)
from .harmonia_runtime import CoordinationKeyProviderUnavailable, ProjectRuntimeRegistry
from .harmonia_store import InspectionCategory, ProjectInspector, derive_project_store
from .kernel_dispatcher import DispatchRejected, ReconciliationRequired, StaleFence
from .kernel_runtime import AdmissionLimitError, AuthorityError, IdempotencyConflictError
from .ledger import Result

_STATES = frozenset(
    {
        "admitted",
        "dispatch_staged",
        "retry_wait",
        "session_bound",
        "terminal_observed",
        "cleanup_pending",
        "cleaned",
        "reconciliation_required",
        "cancel_requested",
    }
)


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def _digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical(value)).hexdigest()


def _identifier(prefix: str, value: str) -> str:
    return prefix + hashlib.sha256(value.encode()).hexdigest()[:32]


class HarmoniaService:
    """Evaluate admission and orchestrate only the approved v0.19.1 path."""

    def __init__(
        self,
        *,
        aether_home: str | Path,
        config: CoordinationConfig,
        registry: ProjectRuntimeRegistry,
        discovered_workers: Iterable[str],
    ) -> None:
        if not isinstance(config, CoordinationConfig) or not isinstance(registry, ProjectRuntimeRegistry):
            raise TypeError("Harmonia configuration and runtime registry required")
        self._aether_home = Path(aether_home).expanduser().resolve()
        self._config = config
        self._registry = registry
        self._workers = frozenset(discovered_workers)
        self._locks: dict[str, asyncio.Lock] = {}

    async def handle(self, value: Mapping[str, Any]) -> dict[str, Any]:
        action = value.get("action") if isinstance(value, Mapping) else None
        public_action = action if action in {"start", "status", "stop"} else "status"
        try:
            request = parse_harmonia_request(value)
        except InvalidHarmoniaRequest:
            return public_error(public_action, "invalid_request")
        try:
            if isinstance(request, HarmoniaStartRequest):
                return await self._start(request)
            if isinstance(request, HarmoniaStatusRequest):
                return self._status(request.project_root, request.run_id, action="status")
            return await self._stop(request)
        except CoordinationKeyProviderUnavailable:
            return public_error(request.action, "key_provider_unavailable")
        except IdempotencyConflictError:
            return public_error(request.action, "idempotency_conflict")
        except AdmissionLimitError:
            return public_error(request.action, "admission_limit")
        except (StaleFence, AuthorityError):
            return public_error(request.action, "authority_mismatch")
        except (sqlite3.DatabaseError, OSError):
            return public_error(request.action, "storage_unavailable", retryable=True)
        except Exception:
            return public_error(request.action, "internal_failure")

    def _start_admission_error(self, request: HarmoniaStartRequest) -> str | None:
        if not self._config.enabled or "kernel-single-task" not in self._config.allowed_modes:
            return "feature_disabled"
        allowed = {str(Path(root).expanduser().resolve()) for root in self._config.project_allowlist}
        if str(request.project_root) not in allowed:
            return "project_not_allowed"
        if self._config.max_active_runs != 1:
            return "admission_limit"
        if request.contract.tasks:
            if any(task.worker not in self._workers for task in request.contract.tasks):
                return "invalid_request"
        elif request.contract.worker not in self._workers:
            return "invalid_request"
        return None

    @staticmethod
    def _request_digest(request: HarmoniaStartRequest) -> str:
        value = request.to_dict()
        value.pop("action")
        return _digest(value)

    @staticmethod
    def _contract(identity, request: HarmoniaStartRequest) -> ExecutionContract:
        spec = request.contract
        fixed = bool(spec.tasks)
        contract_id = _identifier("contract-", _canonical(spec.to_dict()).decode())
        owner = Principal(identity.project_id, "harmonia", "hermes")
        task_specs = spec.tasks or ()
        workers = tuple(Principal(identity.project_id, "harmonia", task.worker) for task in task_specs)
        if not fixed:
            workers = (Principal(identity.project_id, "harmonia", spec.worker),)
        participants = (owner, *workers)
        role_permissions = ({spec.worker: spec.worker_permissions} if not fixed else {
            task.worker: task.worker_permissions for task in task_specs
        })
        bindings = ({task.task_id: worker for task, worker in zip(task_specs, workers)} if fixed else None)
        return ExecutionContract(
            contract_id=contract_id,
            project_id=identity.project_id,
            generation=0,
            owner=owner,
            participants=participants,
            objective=spec.objective,
            expected_outcome=spec.expected_outcome,
            included_scopes=spec.included_scopes,
            excluded_scopes=spec.excluded_scopes,
            role_permissions=role_permissions,
            evidence_gates=(),
            side_effect_policy=SideEffectPolicy((), 0, True),
            limits=ContractLimits(2 if fixed else 1, spec.time_seconds, 0, spec.model_budget, spec.qa_reserve, spec.recovery_reserve),
            escalation_conditions=spec.escalation_conditions,
            completion_authority=owner,
            amendment_authority=owner,
            status=ContractState.ACTIVE,
            task_worker_bindings=bindings,
            selection_policy_id=spec.selection_policy_id,
            selection_candidate_task_ids=spec.selection_candidate_task_ids,
        )

    @staticmethod
    def _run_payloads(context) -> list[dict[str, Any]]:
        return [
            json.loads(event["payload"])
            for event in context.ledger.events()
            if event["kind"] == "run.created"
        ]

    async def _start(self, request: HarmoniaStartRequest) -> dict[str, Any]:
        error = self._start_admission_error(request)
        if error:
            return public_error("start", error)
        identity = derive_project_store(self._aether_home, request.project_root)
        lock = self._locks.setdefault(identity.project_id, asyncio.Lock())
        async with lock:
            context = await self._registry.get_or_create(request.project_root)
            request_digest = self._request_digest(request)
            run_id = _identifier("run-", identity.project_id + "\0" + request.request_id)
            task_specs = request.contract.tasks or ()
            task_ids = tuple(task.task_id for task in task_specs) or (_identifier("task-", run_id + "\0primary"),)
            contract = self._contract(identity, request)

            prior_runs = self._run_payloads(context)
            if prior_runs:
                prior = prior_runs[0]
                if prior.get("request_id") == request.request_id:
                    if prior.get("request_digest") != request_digest:
                        raise IdempotencyConflictError("idempotency conflict")
                elif prior.get("run_id") != run_id:
                    raise AdmissionLimitError("admission limit")

            existing_contract = context.ledger.read_contract(contract.contract_id)
            contract_count = context.ledger.conn.execute(
                "SELECT COUNT(*) FROM contract_heads WHERE installation_id=? AND project_id=?",
                (identity.installation_id, identity.project_id),
            ).fetchone()[0]
            if existing_contract is None:
                if contract_count:
                    return public_error("start", "contract_conflict")
                if context.ledger.create_contract(contract) not in (Result.APPLIED, Result.DUPLICATE):
                    return public_error("start", "contract_conflict")
            elif existing_contract != contract or existing_contract.status is not ContractState.ACTIVE:
                return public_error("start", "contract_conflict")

            context.runtime.ensure_run(
                run_id=run_id,
                contract_id=contract.contract_id,
                mode="kernel",
                request_id=request.request_id,
                request_digest=request_digest,
            )
            for index, task_id in enumerate(task_ids):
                prerequisites = task_specs[index].prerequisites if task_specs else ()
                try:
                    task = context.runtime.task(run_id, task_id)
                except KeyError:
                    task = context.runtime.create_task(run_id, task_id=task_id, prerequisites=prerequisites)
                if index != 0:
                    continue
                if task.state is TaskState.PROPOSED:
                    task = context.runtime.admit_task(run_id, task_id)
                if task.state is TaskState.ADMITTED:
                    task = context.runtime.mark_task_ready(run_id, task_id)
                if task.state is TaskState.READY:
                    task = context.runtime.dispatch_task(run_id, task_id)
                attempts = context.runtime.attempts(run_id, task_id)
                if task.state is TaskState.DISPATCHED:
                    attempt = context.runtime.start_attempt(run_id, task_id)
                elif len(attempts) == 1:
                    attempt = attempts[0]
                else:
                    raise AdmissionLimitError("admission limit")
                envelope = context.dispatcher.stage_ready(
                    run_id, task_id, attempt=attempt.attempt, project_root=str(request.project_root),
                    plan_revision=request.plan_revision, snapshot_digest=request.snapshot_digest,
                )

            try:
                await context.dispatcher.dispatch_with(envelope.authority)
            except ReconciliationRequired:
                pass
            result = self._status(request.project_root, run_id, action="start")
            if result.get("ok") and result.get("state") == "session_bound":
                await context.start_monitor(envelope.authority)
            return result

    async def _lifecycle_status(self, project_root: Path, run_id: str, *, action: str) -> dict[str, Any]:
        result = self._status(project_root, run_id, action=action)
        if not result.get("ok"):
            return result
        context = await self._registry.get_or_create(project_root)
        staged = next((event for event in context.ledger.events() if event["kind"] == "dispatch.staged"), None)
        if staged is None:
            return result
        payload = json.loads(staged["payload"])
        authority = context.dispatcher._envelope(payload).authority
        terminal = any(
            event["kind"] == "runtime.terminal.observed"
            and json.loads(event["payload"]).get("message_id") == authority.message_id
            for event in context.ledger.events()
        )
        lease = context.ledger.lease(authority.lease_resource)
        if not terminal and (lease is None or lease.expires_at <= context.ledger.clock()):
            result.update({"state": "reconciliation_required", "uncertainty": "terminal_evidence_absent"})
            return result
        if result.get("state") == "session_bound" and not terminal:
            await context.start_monitor(authority)
        return result

    def _status(self, project_root: Path, run_id: str, *, action: str) -> dict[str, Any]:
        identity = derive_project_store(self._aether_home, project_root)
        inspected = ProjectInspector(identity).inspect_run(run_id)
        if inspected.category is InspectionCategory.NOT_FOUND:
            return public_error(action, "not_found")
        if inspected.category is InspectionCategory.SCHEMA_INCOMPATIBLE:
            return public_error(action, "schema_incompatible")
        if inspected.category is not InspectionCategory.FOUND or inspected.snapshot is None:
            return public_error(action, "storage_unavailable", retryable=True)
        snapshot = inspected.snapshot
        events = snapshot.events
        run = next(event["payload"] for event in events if event["kind"] == "run.created")
        task_event = next((event["payload"] for event in events if event["kind"] == "task.created"), {})
        attempt_event = next((event["payload"] for event in reversed(events) if event["kind"] == "attempt.started"), {})
        staged = next((event["payload"] for event in reversed(events) if event["kind"] == "dispatch.staged"), {})
        binding = next((event["payload"] for event in reversed(events) if event["kind"] == "session.bound"), {})
        terminal = next((event["payload"] for event in reversed(events) if event["kind"] == "runtime.terminal.observed"), {})
        evidence = next((event["payload"] for event in reversed(events) if event["kind"] == "evidence.receipt.recorded"), {})
        cleanup_events = [event for event in events if event["kind"].startswith("cleanup.")]
        cleanup_state = "not_requested"
        if any(event["kind"] == "cleanup.unknown" for event in cleanup_events):
            cleanup_state = "unknown"
        elif any(event["kind"] == "cleanup.completed" for event in cleanup_events):
            cleanup_state = "completed"
        elif any(event["kind"] == "cleanup.requested" for event in cleanup_events):
            cleanup_state = "requested"
        cancelled = any(event["kind"] == "cancel.intent" for event in events)
        outbox = snapshot.outbox[-1] if snapshot.outbox else {}
        unknown = outbox.get("status") == "UNKNOWN" or outbox.get("reconciliation_required") == 1
        if unknown:
            state, uncertainty = "reconciliation_required", "external_effect_unknown"
        elif cleanup_state == "unknown":
            state, uncertainty = "reconciliation_required", "cleanup_unverified"
        elif cleanup_state == "completed":
            state, uncertainty = "cleaned", None
        elif cleanup_state == "requested":
            state, uncertainty = "cleanup_pending", None
        elif terminal:
            state, uncertainty = "terminal_observed", None
        elif cancelled:
            state, uncertainty = "cancel_requested", "cleanup_unverified"
        elif binding:
            state, uncertainty = "session_bound", None
        elif outbox.get("status") in {"RETRY_WAIT", "POISON"}:
            state, uncertainty = "retry_wait", None
        elif staged:
            state, uncertainty = "dispatch_staged", None
        else:
            state, uncertainty = "admitted", None
        if state == "session_bound" and not terminal:
            lease = snapshot.dispatch_lease
            lease_expires_at = lease.get("expires_at") if lease is not None else None
            matching_lease = (
                lease is not None
                and lease.get("owner") == staged.get("lease_owner")
                and lease.get("epoch") == staged.get("lease_epoch")
                and lease.get("token") == staged.get("lease_token")
                and isinstance(lease_expires_at, int)
            )
            lease_expired = not isinstance(lease_expires_at, int) or lease_expires_at <= time.time_ns()
            if not matching_lease or lease_expired:
                state, uncertainty = "reconciliation_required", "terminal_evidence_absent"
        if state not in _STATES:
            raise RuntimeError("invalid Harmonia projection")
        evidence_receipt = None
        if evidence:
            artifact = evidence.get("artifact", {})
            verifier = evidence.get("verifier", {})
            evidence_receipt = {
                "receipt_id": evidence.get("receipt_id"),
                "receipt_payload_digest": evidence.get("receipt_payload_digest"),
                "artifact_digest": artifact.get("digest"),
                "artifact_generation": artifact.get("generation"),
                "verifier_identity": verifier.get("identity"),
                "verifier_version": verifier.get("version"),
            }
        task_rows: dict[str, dict[str, Any]] = {}
        state_by_kind = {
            "task.created": "blocked", "task.admitted": "admitted", "task.ready": "ready",
            "task.dispatched": "dispatched", "attempt.started": "running", "task.released": "proposed",
            "task.closed": "closed",
        }
        for event in events:
            payload = event["payload"]
            task_id = payload.get("task_id")
            if not task_id:
                continue
            row = task_rows.setdefault(task_id, {"task_id": task_id})
            if event["kind"] == "task.created":
                row["prerequisites"] = payload.get("prerequisites", [])
            if event["kind"] in state_by_kind:
                row["state"] = state_by_kind[event["kind"]]
        document = snapshot.contract_document or {}
        bindings = document.get("task_worker_bindings") or {}
        for row in task_rows.values():
            principal = bindings.get(row["task_id"])
            if isinstance(principal, Mapping):
                row["worker"] = principal.get("actor_id")
        topology = tuple(task_rows.values())
        public_bindings = {
            task_id: principal.get("actor_id")
            for task_id, principal in bindings.items()
            if isinstance(principal, Mapping)
        }
        selection_policy = document.get("selection_policy_id")
        selection_candidates = document.get("selection_candidate_task_ids", [])
        selection_commits = [
            event["payload"] for event in events if event["kind"] == "task.selection.committed"
        ]
        selection_commit = selection_commits[-1] if selection_commits else {}
        selection_evidence = {
            "mode": "bounded" if selection_policy else "fixed",
            "policy_id": selection_policy,
            "candidate_task_ids": list(selection_candidates) if isinstance(selection_candidates, list) else [],
            "selection_epoch": selection_commit.get("selection_epoch"),
            "selected_task_id": selection_commit.get("selected_task_id"),
            "resolved_worker_id": selection_commit.get("resolved_worker_id"),
            "proposal_digest": selection_commit.get("proposal_digest"),
            "candidate_digest": selection_commit.get("eligibility_projection_digest"),
            "committed": bool(selection_commit),
        }
        return {
            "action": action,
            "ok": True,
            "runtime_authority": "kernel",
            "project_id": identity.project_id,
            "run_id": run_id,
            "task_id": task_event.get("task_id"),
            "tasks": list(topology),
            "bindings": public_bindings,
            "contract_id": run.get("contract_id"),
            "state": state,
            "durable": True,
            "attempt": attempt_event.get("attempt"),
            "outbox_status": outbox.get("status"),
            "acp_session_id": binding.get("acp_session_id"),
            "technical_status": terminal.get("status"),
            "evidence_receipt": evidence_receipt,
            "semantic_completion": False,
            "cleanup_state": cleanup_state,
            "uncertainty": uncertainty,
            "selection": selection_evidence,
            "error": None,
        }

    async def _stop(self, request: HarmoniaStopRequest) -> dict[str, Any]:
        current = self._status(request.project_root, request.run_id, action="stop")
        if not current.get("ok"):
            return current
        identity = derive_project_store(self._aether_home, request.project_root)
        lock = self._locks.setdefault(identity.project_id, asyncio.Lock())
        async with lock:
            inspected = ProjectInspector(identity).inspect_run(request.run_id)
            if inspected.snapshot is None:
                return public_error("stop", "not_found")
            if any(event["kind"] == "cancel.intent" for event in inspected.snapshot.events):
                return self._status(request.project_root, request.run_id, action="stop")
            context = await self._registry.get_or_create(request.project_root)
            stage = next(
                (
                    event
                    for event in context.ledger.events()
                    if event["kind"] == "dispatch.staged"
                    and json.loads(event["payload"]).get("run_id") == request.run_id
                ),
                None,
            )
            if stage is None:
                return public_error("stop", "authority_mismatch")
            authority = context.dispatcher._envelope(json.loads(stage["payload"])).authority
            terminal_event = next(
                (
                    event for event in context.ledger.events()
                    if event["kind"] == "runtime.terminal.observed"
                    and json.loads(event["payload"]).get("message_id") == authority.message_id
                ),
                None,
            )
            if terminal_event is not None:
                terminal_payload = json.loads(terminal_event["payload"])
                prior_cleanup = [
                    event for event in context.ledger.events()
                    if event["kind"] in {"cleanup.completed", "cleanup.unknown"}
                    and json.loads(event["payload"]).get("message_id") == authority.message_id
                ]
                if prior_cleanup:
                    result = self._status(request.project_root, request.run_id, action="stop")
                    result["cleanup_state"] = "unknown" if prior_cleanup[-1]["kind"] == "cleanup.unknown" else "completed"
                    return result
                context.dispatcher._append(
                    "cleanup.requested", "dispatch:" + authority.message_id,
                    {"run_id": authority.run_id, "task_id": authority.task_id, "attempt": authority.attempt,
                     "contract_id": authority.contract_id, "message_id": authority.message_id,
                     "logical_session": authority.logical_session},
                )
                try:
                    await context.adapter.cleanup_kernel(
                        project_id=authority.project_id,
                        logical_session=terminal_payload["logical_session"],
                        session_id=terminal_payload["acp_session_id"],
                        terminal_status=terminal_payload["status"],
                    )
                except Exception:
                    context.dispatcher._append(
                        "cleanup.unknown", "dispatch:" + authority.message_id,
                        {"run_id": authority.run_id, "task_id": authority.task_id, "attempt": authority.attempt,
                         "contract_id": authority.contract_id, "message_id": authority.message_id},
                    )
                else:
                    context.dispatcher._append(
                        "cleanup.completed", "dispatch:" + authority.message_id,
                        {"run_id": authority.run_id, "task_id": authority.task_id, "attempt": authority.attempt,
                         "contract_id": authority.contract_id, "message_id": authority.message_id},
                    )
                return self._status(request.project_root, request.run_id, action="stop")
            lease = context.ledger.lease(authority.lease_resource)
            if lease is None or lease.expires_at <= context.ledger.clock():
                result = self._status(request.project_root, request.run_id, action="stop")
                result.update({"state": "reconciliation_required", "uncertainty": "terminal_evidence_absent"})
                return result
            try:
                context.dispatcher.cancel_with(authority)
            except (DispatchRejected, StaleFence):
                return public_error("stop", "authority_mismatch")
            uncertainty = "cleanup_unverified"
            try:
                await context.dispatcher.deliver_cancel_with(authority)
            except asyncio.CancelledError:
                raise
            except Exception:
                uncertainty = "cancel_delivery_unknown"
            result = self._status(request.project_root, request.run_id, action="stop")
            if result.get("ok"):
                result["uncertainty"] = uncertainty
            return result


__all__ = ["HarmoniaService"]
