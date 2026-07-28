"""Strict public request contract for the default-off Harmonia MCP surface.

This module validates only caller-proposable values. Runtime authority, durable
identities, signing capabilities and lifecycle state are derived by later
server-owned composition layers.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, NoReturn

_ID = re.compile(r"^[a-z0-9][a-z0-9._:-]{0,127}$")
_RUN_ID = re.compile(r"^run-[0-9a-f]{32}$")
_SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
_ACTIONS = frozenset({"start", "status", "stop"})
_RESTRICTED_WORKERS = frozenset({"hermes", "harmonia", "athena"})

_GENESIS_FIELDS = frozenset(
    {
        "worker",
        "objective",
        "expected_outcome",
        "included_scopes",
        "excluded_scopes",
        "worker_permissions",
        "time_seconds",
        "model_budget",
        "qa_reserve",
        "recovery_reserve",
        "escalation_conditions",
    }
)
_FIXED_GENESIS_FIELDS = _GENESIS_FIELDS - {"worker", "worker_permissions"} | {"tasks"}
_SELECTION_POLICY = "lowest-canonical-eligible-task-id"
_SELECTION_FIELDS = _FIXED_GENESIS_FIELDS | {"selection_policy_id", "selection_candidate_task_ids"}
_TASK_FIELDS = frozenset({"task_id", "worker", "worker_permissions", "prerequisites"})
_START_FIELDS = frozenset(
    {"action", "project_root", "request_id", "contract", "plan_revision", "snapshot_digest"}
)
_STATUS_FIELDS = frozenset({"action", "project_root", "run_id"})
_STOP_FIELDS = frozenset({"action", "project_root", "run_id", "reason"})

HARMONIA_ERROR_CODES = (
    "feature_disabled",
    "invalid_request",
    "project_not_allowed",
    "key_provider_unavailable",
    "storage_unavailable",
    "schema_incompatible",
    "contract_conflict",
    "idempotency_conflict",
    "admission_limit",
    "not_found",
    "authority_mismatch",
    "external_unknown",
    "internal_failure",
)

_PUBLIC_ERROR_MESSAGES = {
    "feature_disabled": "Harmonia is disabled.",
    "invalid_request": "The Harmonia request is invalid.",
    "project_not_allowed": "The project is not allowed for Harmonia.",
    "key_provider_unavailable": "Coordination signing keys are unavailable.",
    "storage_unavailable": "Coordination storage is unavailable.",
    "schema_incompatible": "Coordination storage has an incompatible schema.",
    "contract_conflict": "The durable contract conflicts with this request.",
    "idempotency_conflict": "The request identity conflicts with durable state.",
    "admission_limit": "The project already has its admitted Harmonia run.",
    "not_found": "The Harmonia run was not found.",
    "authority_mismatch": "The request does not match durable authority.",
    "external_unknown": "The external effect requires reconciliation.",
    "internal_failure": "Harmonia could not complete the request.",
}


class InvalidHarmoniaRequest(ValueError):
    """Raised for any malformed or caller-forged public request."""

    def __init__(self) -> None:
        super().__init__("invalid request")


def _invalid() -> NoReturn:
    raise InvalidHarmoniaRequest()


def _exact_fields(value: Any, fields: frozenset[str]) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != fields:
        _invalid()
    return value


def _text(value: Any, *, maximum: int = 4096) -> str:
    if not isinstance(value, str) or not value or value != value.strip() or len(value) > maximum:
        _invalid()
    return value


def _identifier(value: Any) -> str:
    if not isinstance(value, str) or value != value.strip() or not _ID.fullmatch(value):
        _invalid()
    return value


def _positive_integer(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        _invalid()
    return value


def _nonnegative_integer(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        _invalid()
    return value


def _string_list(value: Any, *, allow_empty: bool) -> tuple[str, ...]:
    if not isinstance(value, list) or (not allow_empty and not value):
        _invalid()
    items = tuple(_text(item, maximum=1024) for item in value)
    if len(set(items)) != len(items):
        _invalid()
    return items


def _project_root(value: Any) -> Path:
    if not isinstance(value, str) or not value or value != value.strip():
        _invalid()
    candidate = Path(value)
    if not candidate.is_absolute():
        _invalid()
    try:
        canonical = candidate.resolve(strict=True)
    except (OSError, RuntimeError):
        _invalid()
    if not canonical.is_dir():
        _invalid()
    return canonical


@dataclass(frozen=True, slots=True)
class HarmoniaGenesisSpec:
    worker: str
    objective: str
    expected_outcome: str
    included_scopes: tuple[str, ...]
    excluded_scopes: tuple[str, ...]
    worker_permissions: tuple[str, ...]
    time_seconds: int
    model_budget: int
    qa_reserve: int
    recovery_reserve: int
    escalation_conditions: tuple[str, ...]
    tasks: tuple["HarmoniaTaskSpec", ...] = ()
    selection_policy_id: str | None = None
    selection_candidate_task_ids: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, value: Any) -> HarmoniaGenesisSpec:
        fixed = isinstance(value, Mapping) and "tasks" in value
        bounded = fixed and ("selection_policy_id" in value or "selection_candidate_task_ids" in value)
        data = _exact_fields(value, _SELECTION_FIELDS if bounded else (_FIXED_GENESIS_FIELDS if fixed else _GENESIS_FIELDS))
        tasks: tuple[HarmoniaTaskSpec, ...] = ()
        candidate_ids: tuple[str, ...] = ()
        if fixed:
            expected_count = 3 if bounded else 2
            if not isinstance(data["tasks"], list) or len(data["tasks"]) != expected_count:
                _invalid()
            tasks = tuple(HarmoniaTaskSpec.from_dict(item) for item in data["tasks"])
            if len({item.task_id for item in tasks}) != expected_count or len({item.worker for item in tasks}) != expected_count:
                _invalid()
            if any(item.worker in _RESTRICTED_WORKERS for item in tasks):
                _invalid()
            if tasks[0].prerequisites or any(item.prerequisites != (tasks[0].task_id,) for item in tasks[1:]):
                _invalid()
            if bounded:
                if data["selection_policy_id"] != _SELECTION_POLICY:
                    _invalid()
                candidate_ids = _string_list(data["selection_candidate_task_ids"], allow_empty=False)
                if len(candidate_ids) != 2 or set(candidate_ids) != {tasks[1].task_id, tasks[2].task_id}:
                    _invalid()
            else:
                candidate_ids = ()
            worker, permissions = tasks[0].worker, tasks[0].worker_permissions
        else:
            worker = _identifier(data["worker"])
            if worker in _RESTRICTED_WORKERS:
                _invalid()
            permissions = _string_list(data["worker_permissions"], allow_empty=False)
        time_seconds = _positive_integer(data["time_seconds"])
        model_budget = _positive_integer(data["model_budget"])
        qa_reserve = _nonnegative_integer(data["qa_reserve"])
        recovery_reserve = _nonnegative_integer(data["recovery_reserve"])
        if qa_reserve + recovery_reserve > model_budget:
            _invalid()
        return cls(
            worker=worker,
            objective=_text(data["objective"]),
            expected_outcome=_text(data["expected_outcome"]),
            included_scopes=_string_list(data["included_scopes"], allow_empty=False),
            excluded_scopes=_string_list(data["excluded_scopes"], allow_empty=True),
            worker_permissions=permissions,
            time_seconds=time_seconds,
            model_budget=model_budget,
            qa_reserve=qa_reserve,
            recovery_reserve=recovery_reserve,
            escalation_conditions=_string_list(data["escalation_conditions"], allow_empty=True),
            tasks=tasks,
            selection_policy_id=_SELECTION_POLICY if bounded else None,
            selection_candidate_task_ids=candidate_ids,
        )

    def to_dict(self) -> dict[str, Any]:
        result = {
            "worker": self.worker,
            "objective": self.objective,
            "expected_outcome": self.expected_outcome,
            "included_scopes": list(self.included_scopes),
            "excluded_scopes": list(self.excluded_scopes),
            "worker_permissions": list(self.worker_permissions),
            "time_seconds": self.time_seconds,
            "model_budget": self.model_budget,
            "qa_reserve": self.qa_reserve,
            "recovery_reserve": self.recovery_reserve,
            "escalation_conditions": list(self.escalation_conditions),
        }
        if self.tasks:
            result.pop("worker")
            result.pop("worker_permissions")
            result["tasks"] = [task.to_dict() for task in self.tasks]
        if self.selection_policy_id is not None:
            result["selection_policy_id"] = self.selection_policy_id
            result["selection_candidate_task_ids"] = list(self.selection_candidate_task_ids)
        return result


@dataclass(frozen=True, slots=True)
class HarmoniaTaskSpec:
    task_id: str
    worker: str
    worker_permissions: tuple[str, ...]
    prerequisites: tuple[str, ...]

    @classmethod
    def from_dict(cls, value: Any) -> "HarmoniaTaskSpec":
        data = _exact_fields(value, _TASK_FIELDS)
        prerequisites = data["prerequisites"]
        if not isinstance(prerequisites, list):
            _invalid()
        return cls(
            task_id=_identifier(data["task_id"]),
            worker=_identifier(data["worker"]),
            worker_permissions=_string_list(data["worker_permissions"], allow_empty=False),
            prerequisites=tuple(_identifier(item) for item in prerequisites),
        )

    def to_dict(self) -> dict[str, Any]:
        return {"task_id": self.task_id, "worker": self.worker, "worker_permissions": list(self.worker_permissions), "prerequisites": list(self.prerequisites)}


@dataclass(frozen=True, slots=True)
class HarmoniaStartRequest:
    project_root: Path
    request_id: str
    contract: HarmoniaGenesisSpec
    plan_revision: int
    snapshot_digest: str
    action: str = "start"

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "project_root": str(self.project_root),
            "request_id": self.request_id,
            "contract": self.contract.to_dict(),
            "plan_revision": self.plan_revision,
            "snapshot_digest": self.snapshot_digest,
        }


@dataclass(frozen=True, slots=True)
class HarmoniaStatusRequest:
    project_root: Path
    run_id: str
    action: str = "status"

    def to_dict(self) -> dict[str, Any]:
        return {"action": self.action, "project_root": str(self.project_root), "run_id": self.run_id}


@dataclass(frozen=True, slots=True)
class HarmoniaStopRequest:
    project_root: Path
    run_id: str
    reason: str | None = None
    action: str = "stop"

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "action": self.action,
            "project_root": str(self.project_root),
            "run_id": self.run_id,
        }
        if self.reason is not None:
            result["reason"] = self.reason
        return result


HarmoniaRequest = HarmoniaStartRequest | HarmoniaStatusRequest | HarmoniaStopRequest


def parse_harmonia_request(value: Any) -> HarmoniaRequest:
    """Parse one strict action-typed request without composing runtime state."""
    if not isinstance(value, Mapping):
        _invalid()
    action = value.get("action")
    if action not in _ACTIONS:
        _invalid()

    if action == "start":
        data = _exact_fields(value, _START_FIELDS)
        request_id = _identifier(data["request_id"])
        plan_revision = _positive_integer(data["plan_revision"])
        snapshot_digest = data["snapshot_digest"]
        if not isinstance(snapshot_digest, str) or not _SHA256.fullmatch(snapshot_digest):
            _invalid()
        return HarmoniaStartRequest(
            project_root=_project_root(data["project_root"]),
            request_id=request_id,
            contract=HarmoniaGenesisSpec.from_dict(data["contract"]),
            plan_revision=plan_revision,
            snapshot_digest=snapshot_digest,
        )

    if action == "status":
        data = _exact_fields(value, _STATUS_FIELDS)
        run_id = data["run_id"]
        if not isinstance(run_id, str) or not _RUN_ID.fullmatch(run_id):
            _invalid()
        return HarmoniaStatusRequest(project_root=_project_root(data["project_root"]), run_id=run_id)

    if not isinstance(value, Mapping) or not set(value).issubset(_STOP_FIELDS):
        _invalid()
    if set(value) not in (_STOP_FIELDS, _STOP_FIELDS - {"reason"}):
        _invalid()
    run_id = value["run_id"]
    if not isinstance(run_id, str) or not _RUN_ID.fullmatch(run_id):
        _invalid()
    reason = value.get("reason")
    if reason is not None:
        reason = _text(reason, maximum=512)
    return HarmoniaStopRequest(project_root=_project_root(value["project_root"]), run_id=run_id, reason=reason)


def public_error(action: str, code: str, *, retryable: bool = False) -> dict[str, Any]:
    """Return a stable, non-sensitive public error envelope."""
    if code not in _PUBLIC_ERROR_MESSAGES:
        raise ValueError("unknown public error code")
    if action not in _ACTIONS or not isinstance(retryable, bool):
        raise ValueError("invalid public error envelope")
    return {
        "action": action,
        "ok": False,
        "runtime_authority": "kernel",
        "durable": False,
        "state": None,
        "uncertainty": None,
        "error": {
            "code": code,
            "message": _PUBLIC_ERROR_MESSAGES[code],
            "retryable": retryable,
        },
    }
