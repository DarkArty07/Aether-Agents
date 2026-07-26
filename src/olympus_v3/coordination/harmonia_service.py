"""Default-off orchestration for one durable Harmonia kernel task."""

from __future__ import annotations

import asyncio
import hashlib
import json
import sqlite3
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
    {"admitted", "dispatch_staged", "retry_wait", "session_bound", "reconciliation_required", "cancel_requested"}
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
        if request.contract.worker not in self._workers:
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
        contract_id = _identifier("contract-", _canonical(spec.to_dict()).decode())
        owner = Principal(identity.project_id, "harmonia", "hermes")
        worker = Principal(identity.project_id, "harmonia", spec.worker)
        return ExecutionContract(
            contract_id=contract_id,
            project_id=identity.project_id,
            generation=0,
            owner=owner,
            participants=(owner, worker),
            objective=spec.objective,
            expected_outcome=spec.expected_outcome,
            included_scopes=spec.included_scopes,
            excluded_scopes=spec.excluded_scopes,
            role_permissions={spec.worker: spec.worker_permissions},
            evidence_gates=(),
            side_effect_policy=SideEffectPolicy((), 0, True),
            limits=ContractLimits(
                1,
                spec.time_seconds,
                0,
                spec.model_budget,
                spec.qa_reserve,
                spec.recovery_reserve,
            ),
            escalation_conditions=spec.escalation_conditions,
            completion_authority=owner,
            amendment_authority=owner,
            status=ContractState.ACTIVE,
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
            task_id = _identifier("task-", run_id + "\0primary")
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
            try:
                task = context.runtime.task(run_id, task_id)
            except KeyError:
                task = context.runtime.create_task(run_id, task_id=task_id)
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
                run_id,
                task_id,
                attempt=attempt.attempt,
                project_root=str(request.project_root),
                plan_revision=request.plan_revision,
                snapshot_digest=request.snapshot_digest,
            )
            try:
                await context.dispatcher.dispatch_with(envelope.authority)
            except ReconciliationRequired:
                pass
            return self._status(request.project_root, run_id, action="start")

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
        cancelled = any(event["kind"] == "cancel.intent" for event in events)
        outbox = snapshot.outbox[-1] if snapshot.outbox else {}
        unknown = outbox.get("status") == "UNKNOWN" or outbox.get("reconciliation_required") == 1
        if unknown:
            state, uncertainty = "reconciliation_required", "external_effect_unknown"
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
        if state not in _STATES:
            raise RuntimeError("invalid Harmonia projection")
        return {
            "action": action,
            "ok": True,
            "runtime_authority": "kernel",
            "project_id": identity.project_id,
            "run_id": run_id,
            "task_id": task_event.get("task_id"),
            "contract_id": run.get("contract_id"),
            "state": state,
            "durable": True,
            "attempt": attempt_event.get("attempt"),
            "outbox_status": outbox.get("status"),
            "acp_session_id": binding.get("acp_session_id"),
            "uncertainty": uncertainty,
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
