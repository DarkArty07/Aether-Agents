"""Default-off Olympus adapter over the public ``ACPManager`` lifecycle API."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from ..acp_manager import ACPManager
from .evidence import ARTIFACT_RELATIVE_PATH, ARTIFACT_SCHEMA, EvidenceVerificationError, HandoffSnapshot
from .principal import ValidationError
from .workflow import kernel_acp_session_id

MAX_RUNTIME_PROMPT_BYTES = 16_384


class OlympusRuntimeAdapter:
    """Execute kernel-authorized lifecycle effects through public ACP operations."""

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

    @staticmethod
    def _kernel_session_id(logical_session: str) -> str:
        return kernel_acp_session_id(logical_session)

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
        session_id = kernel_acp_session_id(logical_session) if isinstance(logical_session, str) and logical_session else None
        prompt_permissions = (
            prompt_payload.get("contract", {}).get("role_permissions", ())
            if isinstance(prompt_payload, dict)
            and isinstance(prompt_payload.get("contract"), dict)
            else ()
        )
        response_delivery = (
            isinstance(prompt_permissions, list)
            and "return_evidence" in prompt_permissions
        )
        expected_result_artifact = {
            "delivery": "acp_response" if response_delivery else "worker_file",
            "relative_path": ARTIFACT_RELATIVE_PATH.format(
                run_id=getattr(authority, "run_id", None),
                task_id=getattr(authority, "task_id", None),
                attempt=getattr(authority, "attempt", None),
            ),
            "write_before_completion": not response_delivery,
            "document": {
                "schema": ARTIFACT_SCHEMA,
                "installation_id": getattr(authority, "installation_id", None),
                "project_id": getattr(authority, "project_id", None),
                "run_id": getattr(authority, "run_id", None),
                "task_id": getattr(authority, "task_id", None),
                "attempt": getattr(authority, "attempt", None),
                "contract_id": getattr(authority, "contract_id", None),
                "contract_generation": getattr(authority, "contract_generation", None),
                "revocation_epoch": getattr(authority, "revocation_epoch", None),
                "message_id": getattr(authority, "message_id", None),
                "logical_session": logical_session,
                "acp_session_id": session_id,
                "artifact_generation": 1,
                "result": {"answer": "REPLACE_WITH_TASK_RESULT"},
            },
        }
        expected_keys = {
            "acceptance_evidence", "authority", "contract", "instructions", "kind", "result_artifact", "task"
        }
        handoff_valid = True
        if isinstance(prompt_payload, dict) and "handoff" in prompt_payload:
            expected_keys.add("handoff")
            try:
                handoff = HandoffSnapshot.from_dict(prompt_payload["handoff"])
                handoff_valid = handoff.snapshot_digest == getattr(authority, "snapshot_digest", None)
            except EvidenceVerificationError:
                handoff_valid = False
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
            or set(prompt_payload) != expected_keys
            or prompt_payload.get("kind") != "aether.harmonia.task.v1"
            or prompt_payload.get("authority") != expected_authority
            or not isinstance(prompt_payload.get("contract"), dict)
            or prompt_payload["contract"].get("worker_id") != agent_name
            or prompt_payload.get("result_artifact") != expected_result_artifact
            or not handoff_valid
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
        proof = result.get("survivors")
        required = {"logical_manager_session", "acp_mapping", "prompt_task", "pid_session_mapping"}
        if (
            result.get("status") != terminal_status
            or result.get("project_id") != project_id
            or result.get("acp_session_id") != session_id
            or not isinstance(proof, Mapping)
            or set(proof) != required
            or any(proof[name] is not False for name in required)
        ):
            raise ValidationError("invalid cleanup proof")
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

__all__ = [
    "MAX_RUNTIME_PROMPT_BYTES",
    "OlympusRuntimeAdapter",
]
