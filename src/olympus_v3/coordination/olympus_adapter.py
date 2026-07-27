"""Default-off Olympus adapter over the public ``ACPManager`` lifecycle API."""

from __future__ import annotations

import asyncio
import hashlib
import json
import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from ..acp_manager import ACPManager
from .admission import AdmissionProposal, AdmissionStatus
from .contracts import TaskState
from .harmonia import HarmoniaPlan
from .protocol import Principal, ValidationError

MAX_RUNTIME_PROMPT_BYTES = 16_384


class RuntimeStatus(StrEnum):
    DISABLED = "disabled"
    SENT = "sent"
    REPLAYED = "replayed"
    REJECTED = "rejected"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class RuntimeReceipt:
    task_id: str
    participant: Principal
    session_id: str
    status: RuntimeStatus
    reason: str | None = None

    def __post_init__(self) -> None:
        if (
            not isinstance(self.task_id, str)
            or not isinstance(self.participant, Principal)
            or not isinstance(self.session_id, str)
            or not isinstance(self.status, RuntimeStatus)
            or (self.reason is not None and not isinstance(self.reason, str))
        ):
            raise ValidationError("invalid runtime receipt")


@dataclass(frozen=True, slots=True)
class RuntimeObservation:
    task_id: str
    participant: Principal
    session_id: str
    technical_status: str
    progress: Mapping[str, Any]
    semantic_complete: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        if (
            not isinstance(self.task_id, str)
            or not isinstance(self.participant, Principal)
            or not isinstance(self.session_id, str)
            or not isinstance(self.technical_status, str)
            or not isinstance(self.progress, Mapping)
        ):
            raise ValidationError("invalid runtime observation")
        object.__setattr__(self, "progress", MappingProxyType(dict(self.progress)))


class OlympusRuntimeAdapter:
    """Translate admitted assignments to public ACP operations.

    Session and process ownership remains entirely inside ``ACPManager``. This
    adapter only remembers deterministic task/session correlation for replay and
    technical observation. Its replay cache is process-local; live multi-process
    activation requires the shared durable idempotency prerequisite tracked for
    the coordination runtime.
    """

    def __init__(
        self,
        manager: ACPManager,
        *,
        project_id: str,
        enabled: bool = False,
        max_prompt_bytes: int = MAX_RUNTIME_PROMPT_BYTES,
    ):
        required = ("spawn_agent", "send_message", "poll", "close")
        if (
            any(not callable(getattr(manager, name, None)) for name in required)
            or not isinstance(project_id, str)
            or not project_id
            or project_id != project_id.strip()
            or not isinstance(enabled, bool)
            or isinstance(max_prompt_bytes, bool)
            or not isinstance(max_prompt_bytes, int)
            or max_prompt_bytes < 1
        ):
            raise ValidationError("invalid Olympus runtime adapter")
        self.manager = manager
        self.project_id = project_id
        self.enabled = enabled
        self.max_prompt_bytes = max_prompt_bytes
        self._task_sessions: dict[tuple[str, str, Principal], str] = {}
        self._inflight: set[tuple[str, str, Principal]] = set()

    @staticmethod
    def _kernel_session_id(logical_session: str) -> str:
        return str(uuid.uuid5(uuid.NAMESPACE_URL, "aether-r11:" + logical_session))

    @staticmethod
    def _session_id(task_id: str, participant: Principal, project_root: str) -> str:
        identity = ":".join(
            (
                "aether-r5",
                project_root,
                participant.project_id,
                task_id,
                participant.owner_id,
                participant.actor_id,
            )
        )
        return str(uuid.uuid5(uuid.NAMESPACE_URL, identity))

    async def _close_failed_session(self, session_id: str) -> bool:
        """Attempt manager-owned rollback without suppressing cancellation forever."""
        cleanup = asyncio.create_task(self.manager.close(session_id, terminal_status="error"))
        try:
            await asyncio.wait_for(asyncio.shield(cleanup), timeout=30)
        except (TimeoutError, asyncio.CancelledError):
            cleanup.cancel()
            await asyncio.gather(cleanup, return_exceptions=True)
            raise
        cleanup.result()
        return False

    def _plan_is_bound(self, plan: HarmoniaPlan) -> bool:
        admission_ids = tuple(item.task_id for item in plan.admissions)
        projection_ids = tuple(item.task_id for item in plan.projection.tasks)
        assignment_ids = tuple(item.task_id for item in plan.assignments)
        if (
            len(set(admission_ids)) != len(admission_ids)
            or len(set(assignment_ids)) != len(assignment_ids)
            or not set(admission_ids).issubset(projection_ids)
        ):
            return False
        decisions = {item.task_id: item for item in plan.admissions}
        projected = {item.task_id: item for item in plan.projection.tasks}
        ready_ids = {task_id for task_id in admission_ids if projected[task_id].state is TaskState.READY}
        if set(assignment_ids) != ready_ids:
            return False
        for task_id in admission_ids:
            task = projected[task_id]
            decision = decisions[task_id]
            if decision.proposal is None or decision.proposal != task.proposal:
                return False
        for assignment in plan.assignments:
            decision = decisions[assignment.task_id]
            task = projected[assignment.task_id]
            if (
                decision.status is not AdmissionStatus.ADMITTED
                or assignment.participant != task.assignee
                or assignment.participant.project_id != self.project_id
                or decision.proposal is None
                or decision.proposal.fan_out < 1
            ):
                return False
        return True

    @staticmethod
    def _canonical_prompt(proposal: AdmissionProposal, participant: Principal) -> str:
        payload = {
            "ambiguities": proposal.ambiguities,
            "assignee": {
                "actor_id": participant.actor_id,
                "owner_id": participant.owner_id,
                "project_id": participant.project_id,
            },
            "dependencies": proposal.dependencies,
            "effect_class": proposal.effect_class,
            "evidence": proposal.evidence,
            "fan_out": proposal.fan_out,
            "kind": "aether.admitted_work",
            "lease_resources": proposal.lease_resources,
            "model_cost": proposal.model_cost,
            "objective": proposal.objective,
            "objective_source": proposal.objective_source,
            "permission": proposal.permission,
            "payload_bytes": proposal.payload_bytes,
            "retries": proposal.retries,
            "role": proposal.role,
            "scopes": proposal.scopes,
            "task_id": proposal.task_id,
            "time_cost_seconds": proposal.time_cost_seconds,
            "tool_cost": proposal.tool_cost,
        }
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)

    async def dispatch(
        self,
        plan: HarmoniaPlan,
        *,
        project_root: str,
    ) -> tuple[RuntimeReceipt, ...]:
        if not isinstance(plan, HarmoniaPlan) or not isinstance(project_root, str) or not project_root.startswith("/"):
            raise ValidationError("invalid runtime dispatch")
        project_root = str(Path(project_root).resolve())
        receipts: list[RuntimeReceipt] = []
        assignments = sorted(
            plan.assignments,
            key=lambda item: (item.task_id, item.participant.owner_id, item.participant.actor_id),
        )
        if not self._plan_is_bound(plan):
            return tuple(
                RuntimeReceipt(
                    assignment.task_id,
                    assignment.participant,
                    self._session_id(assignment.task_id, assignment.participant, project_root),
                    RuntimeStatus.REJECTED,
                    "invalid_plan",
                )
                for assignment in assignments
            )
        decisions = {decision.task_id: decision for decision in plan.admissions}
        for assignment in assignments:
            key = (project_root, assignment.task_id, assignment.participant)
            session_id = self._session_id(assignment.task_id, assignment.participant, project_root)
            if not self.enabled:
                receipts.append(
                    RuntimeReceipt(
                        assignment.task_id,
                        assignment.participant,
                        session_id,
                        RuntimeStatus.DISABLED,
                        "coordination_disabled",
                    )
                )
                continue
            decision = decisions[assignment.task_id]
            proposal = decision.proposal
            if proposal is None:
                raise RuntimeError("validated admission lost proposal binding")
            prompt = self._canonical_prompt(proposal, assignment.participant)
            if len(prompt.encode()) > self.max_prompt_bytes:
                receipts.append(
                    RuntimeReceipt(
                        assignment.task_id,
                        assignment.participant,
                        session_id,
                        RuntimeStatus.REJECTED,
                        "prompt_limit_exceeded",
                    )
                )
                continue
            existing = self._task_sessions.get(key)
            if existing is not None or key in self._inflight:
                receipts.append(
                    RuntimeReceipt(
                        assignment.task_id,
                        assignment.participant,
                        existing or session_id,
                        RuntimeStatus.REPLAYED,
                        "duplicate_assignment",
                    )
                )
                continue

            opened_session: str | None = None
            self._inflight.add(key)
            try:
                try:
                    opened_session = await self.manager.spawn_agent(
                        agent_name=assignment.participant.actor_id,
                        session_id=session_id,
                        project_root=project_root,
                    )
                    if opened_session != session_id:
                        raise RuntimeError("ACPManager returned unexpected session identity")
                    await self.manager.send_message(session_id, prompt)
                except BaseException as exc:
                    cleanup_cancelled = False
                    if opened_session is not None:
                        cleanup_cancelled = await self._close_failed_session(opened_session)
                    if isinstance(exc, asyncio.CancelledError) or cleanup_cancelled:
                        raise asyncio.CancelledError from exc
                    if not isinstance(exc, Exception):
                        raise
                    receipts.append(
                        RuntimeReceipt(
                            assignment.task_id,
                            assignment.participant,
                            session_id,
                            RuntimeStatus.ERROR,
                            "dispatch_failed",
                        )
                    )
                    continue
                self._task_sessions[key] = session_id
                receipts.append(
                    RuntimeReceipt(
                        assignment.task_id,
                        assignment.participant,
                        session_id,
                        RuntimeStatus.SENT,
                    )
                )
            finally:
                self._inflight.discard(key)
        return tuple(receipts)

    async def dispatch_kernel(self, *, authority: Any, request: Mapping[str, Any]) -> Mapping[str, Any]:
        """Execute one ledger-authorized R11 dispatch through public ACP APIs.

        Durable retry and replay decisions remain in ``KernelDispatcher``.  This
        seam owns only the external ACP lifecycle effect and returns its observed
        identity.
        """
        if not isinstance(request, Mapping):
            raise ValidationError("invalid kernel dispatch request")
        project_root = request.get("project_root")
        logical_session = request.get("logical_session")
        agent_name = request.get("agent_name")
        prompt = request.get("prompt")
        prompt_digest = request.get("prompt_digest")
        try:
            prompt_payload = json.loads(prompt) if isinstance(prompt, str) else None
        except (TypeError, ValueError):
            prompt_payload = None
        expected_authority = {
            "project_id": getattr(authority, "project_id", None),
            "run_id": getattr(authority, "run_id", None),
            "task_id": getattr(authority, "task_id", None),
            "attempt": getattr(authority, "attempt", None),
            "contract_id": getattr(authority, "contract_id", None),
            "contract_generation": getattr(authority, "contract_generation", None),
            "plan_id": getattr(authority, "plan_id", None),
            "plan_revision": getattr(authority, "plan_revision", None),
            "snapshot_digest": getattr(authority, "snapshot_digest", None),
            "message_id": getattr(authority, "message_id", None),
        }
        expected_digest = (
            "sha256:" + hashlib.sha256(prompt.encode()).hexdigest() if isinstance(prompt, str) else None
        )
        if (
            getattr(authority, "project_id", None) != self.project_id
            or not isinstance(project_root, str)
            or not project_root.startswith("/")
            or not isinstance(logical_session, str)
            or not logical_session
            or not isinstance(agent_name, str)
            or not agent_name
            or not isinstance(prompt, str)
            or not prompt
            or len(prompt.encode()) > self.max_prompt_bytes
            or prompt_digest != expected_digest
            or not isinstance(prompt_payload, dict)
            or set(prompt_payload)
            != {"acceptance_evidence", "authority", "contract", "instructions", "kind", "task"}
            or prompt_payload.get("kind") != "aether.harmonia.task.v1"
            or prompt_payload.get("authority") != expected_authority
            or not isinstance(prompt_payload.get("contract"), dict)
            or prompt_payload["contract"].get("worker_id") != agent_name
            or prompt_payload.get("task")
            != {
                "task_id": getattr(authority, "task_id", None),
                "attempt": getattr(authority, "attempt", None),
                "project_root": project_root,
            }
            or json.dumps(prompt_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) != prompt
            or request.get("run_id") != getattr(authority, "run_id", None)
            or request.get("task_id") != getattr(authority, "task_id", None)
            or request.get("attempt") != getattr(authority, "attempt", None)
            or request.get("message_id") != getattr(authority, "message_id", None)
            or request.get("plan_id") != getattr(authority, "plan_id", None)
        ):
            raise ValidationError("invalid kernel dispatch authority")
        if not self.enabled:
            raise ConnectionError("coordination runtime disabled before ACP acceptance")
        session_id = self._kernel_session_id(logical_session)
        try:
            opened = await self.manager.spawn_agent(
                agent_name=agent_name,
                session_id=session_id,
                project_root=str(Path(project_root).resolve()),
            )
        except Exception as exc:
            raise ConnectionError("ACP session was not accepted") from exc
        if opened != session_id:
            raise TimeoutError("ACP accepted an unexpected session identity")
        try:
            await self.manager.send_message(session_id, prompt)
        except Exception as exc:
            raise TimeoutError("ACP session accepted but delivery response was lost") from exc
        return {"accepted": True, "acp_session_id": session_id}

    async def cleanup_kernel(
        self, *, project_id: str, logical_session: str, session_id: str, terminal_status: str
    ) -> Mapping[str, Any]:
        """Cleanup a persisted ACP session through the public manager boundary."""
        if (
            project_id != self.project_id
            or not isinstance(logical_session, str)
            or not logical_session
            or session_id != self._kernel_session_id(logical_session)
        ):
            raise ValidationError("invalid persisted cleanup authority")
        if terminal_status not in {"completed", "error", "cancelled"}:
            raise ValidationError("invalid terminal status")
        cleanup = getattr(self.manager, "cleanup_persisted", None)
        if not callable(cleanup):
            raise RuntimeError("persisted cleanup boundary unavailable")
        result = await cleanup(session_id, terminal_status=terminal_status, project_id=project_id)
        if not isinstance(result, Mapping):
            raise RuntimeError("invalid cleanup response")
        return {**result, "acp_session_id": session_id}

    async def observe_kernel(self, *, authority: Any, request: Mapping[str, Any]) -> Mapping[str, Any]:
        if not isinstance(request, Mapping) or getattr(authority, "project_id", None) != self.project_id:
            raise ValidationError("invalid kernel observation authority")
        session_id = self._kernel_session_id(str(request.get("logical_session", "")))
        progress = await self.manager.poll(session_id)
        if not isinstance(progress, Mapping):
            raise RuntimeError("ACPManager returned invalid progress")
        status = progress.get("status", "unknown")
        return {
            "status": status if isinstance(status, str) else "unknown",
            "acp_session_id": session_id,
            "progress": dict(progress),
        }

    async def cancel_kernel(self, *, authority: Any, request: Mapping[str, Any]) -> Mapping[str, Any]:
        if not isinstance(request, Mapping) or getattr(authority, "project_id", None) != self.project_id:
            raise ValidationError("invalid kernel cancellation authority")
        session_id = self._kernel_session_id(str(request.get("logical_session", "")))
        await self.manager.close(session_id, terminal_status="cancelled")
        return {"accepted": True, "acp_session_id": session_id}

    async def observe(
        self,
        task_id: str,
        participant: Principal,
        *,
        project_root: str,
    ) -> RuntimeObservation:
        if (
            not isinstance(task_id, str)
            or not isinstance(participant, Principal)
            or participant.project_id != self.project_id
            or not isinstance(project_root, str)
            or not project_root.startswith("/")
        ):
            raise ValidationError("invalid runtime observation request")
        project_root = str(Path(project_root).resolve())
        session_id = self._task_sessions.get((project_root, task_id, participant))
        if session_id is None:
            raise ValidationError("unknown runtime assignment")
        progress = await self.manager.poll(session_id)
        if not isinstance(progress, Mapping):
            raise RuntimeError("ACPManager returned invalid progress")
        technical_status = progress.get("status", "unknown")
        if not isinstance(technical_status, str):
            technical_status = "unknown"
        return RuntimeObservation(
            task_id,
            participant,
            session_id,
            technical_status,
            progress,
        )

    async def dispatch_pilot_task(
        self,
        task: Any,
        *,
        manifest: Any,
        session_id: str,
        project_root: str,
        envelope: Mapping[str, Any],
    ) -> RuntimeReceipt:
        """Dispatch one pre-bound R8 pilot envelope via public ACP operations."""
        from .pilot_model import PilotManifest, PilotTask

        if not isinstance(manifest, PilotManifest) or not isinstance(task, PilotTask):
            raise ValidationError("invalid pilot authority")
        try:
            authoritative_task = manifest.task(task.task_id)
        except Exception as exc:
            raise ValidationError("unknown pilot task") from exc
        if authoritative_task != task:
            participant = Principal(
                self.project_id,
                f"r8-{authoritative_task.assignee}",
                authoritative_task.assignee,
            )
            return RuntimeReceipt(
                task.task_id,
                participant,
                session_id,
                RuntimeStatus.REJECTED,
                "invalid_pilot_task",
            )
        participant = Principal(self.project_id, f"r8-{task.assignee}", task.assignee)
        if not self.enabled:
            return RuntimeReceipt(
                task.task_id, participant, session_id, RuntimeStatus.DISABLED, "coordination_disabled"
            )
        canonical_root = str(Path(project_root).resolve())
        key = (canonical_root, task.task_id, participant)
        expected = {
            "task_id": task.task_id,
            "session_id": session_id,
            "participant": participant,
            "pilot_id": self.project_id,
            "project_id": self.project_id,
            "manifest_hash": manifest.manifest_hash,
            "generation": manifest.generation,
            "role": task.role,
            "objective": task.objective,
            "permission": task.permission,
            "allowed_scopes": task.scopes,
            "dependencies": task.depends_on,
            "required_artifacts": task.required_artifacts,
            "result_schema": "AETHER_PILOT_RESULT_V1",
        }
        if (
            not isinstance(envelope, Mapping)
            or any(envelope.get(name) != value for name, value in expected.items())
            or envelope.get("kind") != "aether.snake.task.v1"
            or getattr(manifest, "project_id", None) != self.project_id
            or getattr(manifest, "root", None) != canonical_root
            or not isinstance(envelope.get("forbidden"), tuple)
            or len(envelope["forbidden"]) < 6
        ):
            return RuntimeReceipt(
                task.task_id, participant, session_id, RuntimeStatus.REJECTED, "invalid_pilot_envelope"
            )
        existing = self._task_sessions.get(key)
        if existing is not None or key in self._inflight:
            if existing not in {None, session_id}:
                return RuntimeReceipt(task.task_id, participant, session_id, RuntimeStatus.REJECTED, "session_conflict")
            return RuntimeReceipt(task.task_id, participant, session_id, RuntimeStatus.REPLAYED, "duplicate_assignment")
        prompt_payload = dict(envelope)
        prompt_payload["participant"] = {
            "project_id": participant.project_id,
            "owner_id": participant.owner_id,
            "actor_id": participant.actor_id,
        }
        prompt = json.dumps(prompt_payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        if len(prompt.encode()) > self.max_prompt_bytes:
            return RuntimeReceipt(
                task.task_id, participant, session_id, RuntimeStatus.REJECTED, "prompt_limit_exceeded"
            )
        self._inflight.add(key)
        actual_session: str | None = None
        try:
            try:
                actual_session = await asyncio.wait_for(
                    self.manager.spawn_agent(
                        agent_name=task.assignee,
                        session_id=session_id,
                        project_root=canonical_root,
                    ),
                    timeout=300,
                )
                if actual_session != session_id:
                    raise RuntimeError("ACPManager returned unexpected session identity")
                await asyncio.wait_for(self.manager.send_message(session_id, prompt), timeout=300)
            except BaseException as exc:
                if actual_session is not None:
                    await asyncio.wait_for(self._close_failed_session(actual_session), timeout=300)
                if isinstance(exc, asyncio.CancelledError):
                    raise
                return RuntimeReceipt(task.task_id, participant, session_id, RuntimeStatus.ERROR, "dispatch_failed")
            self._task_sessions[key] = session_id
            return RuntimeReceipt(task.task_id, participant, session_id, RuntimeStatus.SENT)
        finally:
            self._inflight.discard(key)

    async def observe_pilot_task(
        self,
        task: Any,
        *,
        session_id: str,
        project_root: str,
    ) -> RuntimeObservation:
        participant = Principal(self.project_id, f"r8-{task.assignee}", task.assignee)
        canonical_root = str(Path(project_root).resolve())
        key = (canonical_root, task.task_id, participant)
        known = self._task_sessions.get(key)
        if known not in {None, session_id}:
            raise ValidationError("pilot session binding mismatch")
        progress = await asyncio.wait_for(self.manager.poll(session_id), timeout=300)
        if not isinstance(progress, Mapping):
            raise RuntimeError("ACPManager returned invalid progress")
        technical_status = progress.get("status", "unknown")
        if not isinstance(technical_status, str):
            technical_status = "unknown"
        return RuntimeObservation(task.task_id, participant, session_id, technical_status, progress)


__all__ = [
    "MAX_RUNTIME_PROMPT_BYTES",
    "OlympusRuntimeAdapter",
    "RuntimeObservation",
    "RuntimeReceipt",
    "RuntimeStatus",
]
