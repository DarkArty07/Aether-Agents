"""Lazy operational composition for the approved Aether MCP facade.

Nothing in this module opens state or invokes Orca until an admitted tool call.
"""

from __future__ import annotations

import json
import os
import subprocess
import uuid
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from .admission import ProjectAdmissionRegistry, TrustedLaunchContext
from .catalog import OrcaCatalog
from .content_store import ProtectedContentStore, StaticKeyProvider
from .coordination import WorkerService, WorkerStore
from .foundation import M2Foundation
from .lifecycle import LifecycleService, LifecycleStore
from .orca_provider import PublicOrcaLifecycleProvider
from .protocol import ERROR_MESSAGES, ProtocolError, error_envelope, success_envelope, validate_request
from .trace_store import TraceStore

_MAX_PROVIDER_OUTPUT_BYTES = 4 * 1024 * 1024
_PUBLIC_TIMEOUT_SECONDS = 30
_QUALIFIED_BINDING_DIGEST = "813b11e99f7caa4bf8e4fc47200dd6c465f34a04d61e855adbd8822190592e33"


class PublicOrcaTransport:
    """Bounded structured transport; provider adapters own all command selection."""

    def __init__(self, executable: str) -> None:
        if not executable or "\x00" in executable:
            raise ValueError("invalid Orca executable")
        self.executable = executable

    def __call__(self, argv: tuple[str, ...]) -> dict[str, Any]:
        if not argv or argv[-1] != "--json":
            raise RuntimeError("unstructured provider call")
        try:
            completed = subprocess.run(
                (self.executable, *argv), capture_output=True, check=False,
                timeout=_PUBLIC_TIMEOUT_SECONDS,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise RuntimeError("public Orca transport unavailable") from exc
        if len(completed.stdout) > _MAX_PROVIDER_OUTPUT_BYTES or completed.returncode != 0:
            raise RuntimeError("public Orca transport failed")
        try:
            payload = json.loads(completed.stdout)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeError("public Orca transport returned malformed JSON") from exc
        if not isinstance(payload, dict):
            raise RuntimeError("public Orca transport returned malformed JSON")
        return payload


def _state_root(environment: Mapping[str, str]) -> Path:
    raw = environment.get("AETHER_STATE_ROOT")
    if not raw:
        raise ProtocolError("CAPABILITY_UNAVAILABLE")
    root = Path(raw)
    if not root.is_absolute() or root.is_symlink():
        raise ProtocolError("PRINCIPAL_UNAUTHENTICATED")
    return root


def _json_value(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if is_dataclass(value):
        return _json_value(asdict(value))
    if isinstance(value, tuple):
        return [_json_value(item) for item in value]
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    return value


class OperationalRuntime:
    """Compose M2--M5 services under one explicit installation-owned state root."""

    def __init__(self, environment: Mapping[str, str] | None = None) -> None:
        self.environment = dict(os.environ if environment is None else environment)
        self._services: tuple[M2Foundation, LifecycleService, WorkerService] | None = None

    def _build(self) -> tuple[M2Foundation, LifecycleService, WorkerService]:
        if self._services is not None:
            return self._services
        context = TrustedLaunchContext.from_environment(self.environment)
        root = _state_root(self.environment)
        transport = PublicOrcaTransport(self.environment.get("AETHER_ORCA_CLI", "orca"))
        handle = self.environment.get("AETHER_ORCA_COORDINATOR_HANDLE")
        if not handle:
            raise ProtocolError("PRINCIPAL_UNAUTHENTICATED")
        provider = PublicOrcaLifecycleProvider(
            transport=transport,
            binding_digest=self.environment.get("AETHER_ORCA_BINDING_DIGEST", _QUALIFIED_BINDING_DIGEST),
            coordinator_handle=handle,
        )
        foundation = M2Foundation(
            context=context,
            admissions=ProjectAdmissionRegistry(root / "admissions"),
            trace=TraceStore(root / "trace"),
            catalog=OrcaCatalog.bundled(),
        )
        lifecycle = LifecycleService(
            foundation=foundation,
            store=LifecycleStore(root / "lifecycle"),
            provider=provider,
        )
        worker = WorkerService(
            lifecycle=lifecycle,
            store=WorkerStore(root / "workers"),
            provider=provider,
            content_store=ProtectedContentStore(root / "content", key_provider=StaticKeyProvider({}), quota_bytes=16 * 1024 * 1024),
        )
        self._services = foundation, lifecycle, worker
        return self._services

    def invoke(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        request_id = str(uuid.uuid4())
        operation_id = None
        try:
            admitted = validate_request(name, arguments)
            operation = admitted.get("operation")
            if isinstance(operation, dict):
                operation_id = operation.get("operation_id")
            foundation, lifecycle, worker = self._build()
            routes: dict[str, Callable[[dict[str, Any]], Any]] = {
                "project_admit": foundation.project_admit,
                "project_inspect": foundation.project_inspect,
                "swarm_validate": foundation.swarm_validate,
                "swarm_start": lifecycle.swarm_start,
                "swarm_status": lifecycle.swarm_status,
                "swarm_dispatch": worker.swarm_dispatch,
                "swarm_message": worker.swarm_message,
                "swarm_reconcile": lifecycle.swarm_reconcile,
                "swarm_retry": worker.swarm_retry,
                "swarm_cancel": worker.swarm_cancel,
                "swarm_close": worker.swarm_close,
                "swarm_trace": foundation.swarm_trace,
                "orca_search": foundation.orca_search,
                "orca_describe": foundation.orca_describe,
                "orca_call": foundation.orca_call,
            }
            result = routes[name](admitted)
            if name == "swarm_validate":
                lifecycle.store.register_manifest(result, manifest_ref=f"manifest:{result.digest}")
            effect = "READ_ONLY" if name in {"project_inspect", "swarm_validate", "swarm_status", "orca_search", "orca_describe", "orca_call"} else "LOCAL_REVERSIBLE"
            outcome = "SUCCEEDED"
            if isinstance(result, dict) and isinstance(result.get("outcome"), str):
                candidate = result["outcome"]
                outcome = candidate if candidate in {"SUCCEEDED", "PARTIAL", "UNKNOWN", "CANCELLED", "CLOSED", "BLOCKED"} else "SUCCEEDED"
            return success_envelope(
                request_id=request_id, operation_id=operation_id, trace_event_ids=(), effect=effect,
                outcome=outcome, result=_json_value(result),
            )
        except Exception as exc:
            code = getattr(exc, "code", "INTERNAL_ERROR")
            if code not in ERROR_MESSAGES:
                code = "INTERNAL_ERROR"
            return error_envelope(
                request_id=request_id, operation_id=operation_id, trace_event_ids=(), code=code,
                reconciliation_required=code in {"DELIVERY_UNKNOWN", "RECONCILIATION_REQUIRED"},
            )
