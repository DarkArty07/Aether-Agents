"""Aether MCP v1alpha1 canonical protocol, schema, and safe error primitives."""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from collections.abc import Mapping, Sequence
from copy import deepcopy
from types import MappingProxyType
from typing import Any, NoReturn

PROTOCOL_VERSION = "aether.mcp/v1alpha1"
MAX_REQUEST_BYTES = 65_536
MAX_CURSOR_BYTES = 1_024
MAX_STRING_BYTES = 8_192
MAX_ARRAY_ITEMS = 256
MAX_NESTING_DEPTH = 16

EFFECT_CLASSES = (
    "READ_ONLY",
    "LOCAL_APPEND_ONLY",
    "LOCAL_REVERSIBLE",
    "LOCAL_DESTRUCTIVE",
    "EXTERNAL_REVERSIBLE",
    "EXTERNAL_IRREVERSIBLE",
    "UNKNOWN",
)
OUTCOMES = (
    "SUCCEEDED",
    "PARTIAL",
    "REJECTED",
    "FAILED",
    "UNKNOWN",
    "RECONCILIATION_REQUIRED",
    "CLOSED",
    "BLOCKED",
)

_ERROR_MESSAGES = {
    "INVALID_INPUT": "The request does not match the admitted input contract.",
    "INVALID_CURSOR": "The supplied cursor is invalid or exceeds its bound.",
    "PROTOCOL_MISMATCH": "The request uses an unsupported protocol version.",
    "PRINCIPAL_UNAUTHENTICATED": "Coordinator identity must be derived from trusted launch context.",
    "PRINCIPAL_UNAUTHORIZED": "The authenticated coordinator is not authorized for this operation.",
    "PROJECT_NOT_ADMITTED": "The requested project is not admitted for this coordinator.",
    "PROJECT_IDENTITY_MISMATCH": "The admitted project identity no longer matches current evidence.",
    "PROJECT_HAS_OPEN_RUNS": "The project still has open or unknown Runs.",
    "PROJECT_FORGET_CONFIRMATION_MISMATCH": "The project-forget confirmation does not match.",
    "CONTRACT_STALE": "The referenced contract generation is stale.",
    "MANIFEST_INVALID": "The supplied manifest is invalid.",
    "DEPENDENCY_CYCLE": "The task dependency graph contains a cycle.",
    "TASK_NOT_READY": "The requested Task is not ready for dispatch.",
    "WRITE_SCOPE_CONFLICT": "The requested write scope conflicts with another admitted writer.",
    "PARTICIPANT_REQUIRED_MISSING": "A required participant is missing.",
    "PARTICIPANT_DISABLED": "The requested participant is disabled.",
    "PARTICIPANT_FORBIDDEN": "The requested participant is not admitted for this task.",
    "PARTICIPANT_RETIRED": "The requested participant is retired.",
    "PARTICIPANT_UNAVAILABLE": "The requested participant is unavailable.",
    "CAPABILITY_UNAVAILABLE": "The requested capability is unavailable.",
    "PROVIDER_UNAVAILABLE": "The admitted provider is unavailable.",
    "PROVIDER_SCHEMA_DRIFT": "The provider schema differs from the admitted version.",
    "PROVIDER_RESPONSE_INVALID": "The provider response does not match the admitted schema.",
    "EFFECT_NOT_AUTHORIZED": "The requested effect is not authorized.",
    "EFFECT_UNKNOWN": "The operation effect cannot be classified safely.",
    "IDEMPOTENCY_CONFLICT": "The operation identity was reused with different canonical input.",
    "OPERATION_IN_PROGRESS": "The requested operation is already in progress.",
    "DELIVERY_UNKNOWN": "Delivery may have occurred and requires reconciliation.",
    "TRACE_STORE_BUSY": "The trace store is busy and could not accept this operation.",
    "RECONCILIATION_REQUIRED": "The operation requires reconciliation before further mutation.",
    "STALE_DISPATCH": "The referenced Dispatch is stale.",
    "ATTEMPT_NOT_FENCED": "The prior attempt is not terminal or safely fenced.",
    "ATTEMPT_BUDGET_EXHAUSTED": "The admitted attempt budget is exhausted.",
    "EVIDENCE_INSUFFICIENT": "The available evidence is insufficient for the requested conclusion.",
    "CLEANUP_INCOMPLETE": "Cleanup is incomplete.",
    "SURVIVOR_UNKNOWN": "One or more resource survivors have unknown disposition.",
    "TRACE_INTEGRITY_FAILURE": "Trace integrity verification failed.",
    "PRIVACY_POLICY_VIOLATION": "The request violates the admitted privacy policy.",
    "RETENTION_POLICY_VIOLATION": "The request violates the admitted retention policy.",
    "CAPTURE_DISABLED": "Learning capture is disabled.",
    "CAPTURE_POLICY_ESCALATION": "The request would escalate capture without sufficient authority.",
    "CAPTURE_INCOMPLETE": "The learning capture is incomplete.",
    "CAPTURE_QUOTA_EXCEEDED": "The learning capture quota is exhausted.",
    "EPISODE_NOT_SEALED": "The requested episode is not sealed.",
    "SENSITIVE_CONTENT_QUARANTINED": "Sensitive content remains quarantined.",
    "LABEL_AUTHORITY_INSUFFICIENT": "The label authority is insufficient.",
    "DATASET_CONTAMINATION": "The dataset violates the frozen contamination contract.",
    "DATASET_LINEAGE_INCOMPLETE": "Dataset lineage is incomplete.",
    "EXPORT_NOT_AUTHORIZED": "The requested export is not authorized.",
    "INTERNAL_ERROR": "The request could not be completed safely.",
}
ERROR_MESSAGES: Mapping[str, str] = MappingProxyType(_ERROR_MESSAGES)


class ProtocolError(Exception):
    """Stable protocol failure that cannot carry caller/provider text."""

    def __init__(self, code: str) -> None:
        safe_code = code if code in ERROR_MESSAGES else "INTERNAL_ERROR"
        self.code = safe_code
        self.message = ERROR_MESSAGES[safe_code]
        super().__init__(self.message)


def _raise(code: str) -> NoReturn:
    raise ProtocolError(code)


def safe_internal_error(_exception: BaseException) -> ProtocolError:
    """Collapse every unexpected exception to one static public failure."""
    return ProtocolError("INTERNAL_ERROR")


def _string(*, maximum: int = 512, minimum: int = 1, pattern: str | None = None, enum: Sequence[str] | None = None) -> dict[str, Any]:
    schema: dict[str, Any] = {"type": "string", "minLength": minimum, "maxLength": maximum}
    if pattern is not None:
        schema["pattern"] = pattern
    if enum is not None:
        schema["enum"] = list(enum)
    return schema


def _nullable(schema: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(schema)
    schema_type = result.get("type")
    result["type"] = [schema_type, "null"]
    return result


def _array(item: dict[str, Any], *, minimum: int = 0, maximum: int = 64, unique: bool = False) -> dict[str, Any]:
    schema: dict[str, Any] = {
        "type": "array",
        "items": item,
        "minItems": minimum,
        "maxItems": maximum,
    }
    if unique:
        schema["uniqueItems"] = True
    return schema


def _object(
    properties: Mapping[str, dict[str, Any]],
    *,
    required: Sequence[str] = (),
    additional: bool | dict[str, Any] = False,
) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": dict(properties),
        "required": list(required),
        "additionalProperties": additional,
    }


UUID_SCHEMA = {"type": "string", "format": "uuid", "minLength": 36, "maxLength": 36}
DIGEST_SCHEMA = _string(maximum=64, minimum=64, pattern=r"^[0-9a-f]{64}$")
SAFE_ID_SCHEMA = _string(maximum=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:/-]*$")
CURSOR_SCHEMA = _nullable(_string(maximum=MAX_CURSOR_BYTES, pattern=r"^[A-Za-z0-9_-]+$"))
EFFECT_SCHEMA = _string(maximum=32, enum=EFFECT_CLASSES)
OUTCOME_SCHEMA = _string(maximum=32, enum=OUTCOMES)
JSON_OBJECT_SCHEMA = _object({}, additional={})
REASON_SCHEMA = _object(
    {
        "code": _string(maximum=64, pattern=r"^[A-Z][A-Z0-9_]*$"),
        "summary": _string(maximum=512),
        "authority_ref": _string(maximum=512),
    },
    required=("code", "summary", "authority_ref"),
)


def _operation_schema(*, project_required: bool) -> dict[str, Any]:
    properties = {
        "operation_id": UUID_SCHEMA,
        "project_id": UUID_SCHEMA,
        "contract_id": SAFE_ID_SCHEMA,
        "use_case_id": _nullable(SAFE_ID_SCHEMA),
        "reason": REASON_SCHEMA,
        "expected_effect": EFFECT_SCHEMA,
    }
    required = ["operation_id", "contract_id", "use_case_id", "reason", "expected_effect"]
    if project_required:
        required.insert(1, "project_id")
    else:
        properties.pop("project_id")
    return _object(properties, required=required)


OPERATION_SCHEMA = _operation_schema(project_required=True)
ADMISSION_OPERATION_SCHEMA = _operation_schema(project_required=False)
CAPTURE_POLICIES = ("DISABLED", "STRUCTURED_ONLY", "FULL_EPISODE")
MESSAGE_KINDS = (
    "progress",
    "artifact_reference",
    "dependency_handoff",
    "technical_question",
    "reply",
    "review_request",
    "finding",
    "blocker",
    "completion_reference",
    "steering",
)
DECISION_KINDS = (
    "contract_created",
    "contract_amended",
    "route_selected",
    "participant_admitted",
    "participant_denied",
    "scope_assigned",
    "user_answered",
    "limitation_accepted",
    "waiver_granted",
    "completion_proposed",
    "product_accepted",
    "product_rejected",
    "later_horizon_authorized",
)

TASK_SCHEMA = _object(
    {
        "task_key": SAFE_ID_SCHEMA,
        "deliverable": _string(maximum=1024),
        "archetype": SAFE_ID_SCHEMA,
        "dependencies": _array(SAFE_ID_SCHEMA, maximum=64, unique=True),
        "read_scope": _array(_string(maximum=512), maximum=64, unique=True),
        "write_scope": _array(_string(maximum=512), maximum=64, unique=True),
        "evidence_requirements": _array(_string(maximum=512), maximum=64),
        "attempt_budget": {"type": "integer", "minimum": 1, "maximum": 16},
        "placement": _string(maximum=32, enum=("current", "child_worktree", "read_only")),
    },
    required=(
        "task_key",
        "deliverable",
        "archetype",
        "dependencies",
        "read_scope",
        "write_scope",
        "evidence_requirements",
        "attempt_budget",
        "placement",
    ),
)
SWARM_MANIFEST_SCHEMA = _object(
    {
        "protocol": {"type": "string", "const": PROTOCOL_VERSION, "minLength": len(PROTOCOL_VERSION), "maxLength": len(PROTOCOL_VERSION)},
        "project_id": UUID_SCHEMA,
        "contract": _object(
            {
                "contract_id": SAFE_ID_SCHEMA,
                "generation": {"type": "integer", "minimum": 1, "maximum": 2_147_483_647},
                "objective": _string(maximum=2048),
                "acceptance": _array(_string(maximum=1024), minimum=1, maximum=64),
                "non_goals": _array(_string(maximum=1024), maximum=64),
                "authorized_effects": _array(EFFECT_SCHEMA, minimum=1, maximum=7, unique=True),
                "stop_condition": _string(maximum=1024),
            },
            required=("contract_id", "generation", "objective", "acceptance", "non_goals", "authorized_effects", "stop_condition"),
        ),
        "evaluation": _object(
            {
                "enabled": {"type": "boolean"},
                "use_case_id": _nullable(SAFE_ID_SCHEMA),
                "variant": _nullable(SAFE_ID_SCHEMA),
                "measurement_contract": _nullable(_string(maximum=1024)),
            },
            required=("enabled", "use_case_id", "variant", "measurement_contract"),
        ),
        "learning": _object(
            {
                "capture_policy": _string(maximum=32, enum=CAPTURE_POLICIES),
                "purpose": _array(
                    _string(maximum=32, enum=("dogfood", "evaluation", "learning_candidate")),
                    maximum=3,
                    unique=True,
                ),
                "consent_authority_ref": _string(maximum=512),
            },
            required=("capture_policy", "purpose", "consent_authority_ref"),
        ),
        "tasks": _array(TASK_SCHEMA, minimum=1, maximum=64),
    },
    required=("protocol", "project_id", "contract", "evaluation", "learning", "tasks"),
)


def _build_tool_schemas() -> dict[str, dict[str, Any]]:
    reason = REASON_SCHEMA
    operation = OPERATION_SCHEMA
    schemas: dict[str, dict[str, Any]] = {
        "project_admit": _object(
            {
                "operation": ADMISSION_OPERATION_SCHEMA,
                "project_root": _string(maximum=4096),
                "safe_alias": _nullable(_string(maximum=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")),
                "capture_policy": _string(maximum=32, enum=CAPTURE_POLICIES),
                "consent_authority_ref": _string(maximum=512),
            },
            required=("operation", "project_root", "safe_alias", "capture_policy", "consent_authority_ref"),
        ),
        "project_inspect": _object({"project_id": UUID_SCHEMA}, required=("project_id",)),
        "swarm_validate": _object({"manifest": SWARM_MANIFEST_SCHEMA}, required=("manifest",)),
        "swarm_start": _object(
            {
                "operation": operation,
                "manifest_digest": DIGEST_SCHEMA,
                "manifest_ref": _string(maximum=1024),
                "provider_binding_digest": DIGEST_SCHEMA,
                "dispatch_ready": {"type": "boolean"},
            },
            required=("operation", "manifest_digest", "manifest_ref", "provider_binding_digest", "dispatch_ready"),
        ),
        "swarm_status": _object(
            {
                "project_id": UUID_SCHEMA,
                "run_id": UUID_SCHEMA,
                "cursor": CURSOR_SCHEMA,
                "wait_ms": {"type": "integer", "minimum": 0, "maximum": 30_000},
                "detail": _string(maximum=16, enum=("summary", "tasks", "questions", "evidence", "resources", "diagnostic")),
            },
            required=("project_id", "run_id", "cursor", "wait_ms", "detail"),
        ),
        "swarm_dispatch": _object(
            {"operation": operation, "run_id": UUID_SCHEMA, "task_keys": _array(SAFE_ID_SCHEMA, minimum=1, maximum=64, unique=True)},
            required=("operation", "run_id", "task_keys"),
        ),
        "swarm_message": _object(
            {
                "operation": operation,
                "run_id": UUID_SCHEMA,
                "sender_id": SAFE_ID_SCHEMA,
                "recipient_id": SAFE_ID_SCHEMA,
                "kind": _string(maximum=32, enum=MESSAGE_KINDS),
                "payload": _string(maximum=MAX_STRING_BYTES, minimum=0),
                "safe_summary": _string(maximum=512),
                "decision_required": {"type": "boolean"},
                "blocking_effect": _nullable(EFFECT_SCHEMA),
            },
            required=("operation", "run_id", "sender_id", "recipient_id", "kind", "payload", "safe_summary", "decision_required", "blocking_effect"),
        ),
        "swarm_reconcile": _object(
            {
                "operation": operation,
                "run_id": UUID_SCHEMA,
                "target_type": _string(maximum=16, enum=("operation", "task", "dispatch")),
                "target_id": UUID_SCHEMA,
                "mode": _string(maximum=8, enum=("observe", "fence")),
                "evidence_sources": _array(SAFE_ID_SCHEMA, minimum=1, maximum=32, unique=True),
            },
            required=("operation", "run_id", "target_type", "target_id", "mode", "evidence_sources"),
        ),
        "swarm_retry": _object(
            {
                "operation": operation,
                "run_id": UUID_SCHEMA,
                "task_id": UUID_SCHEMA,
                "dispatch_id": UUID_SCHEMA,
                "prior_outcome": OUTCOME_SCHEMA,
                "correction_summary": _string(maximum=1024),
                "contract_generation": _nullable({"type": "integer", "minimum": 1, "maximum": 2_147_483_647}),
            },
            required=("operation", "run_id", "task_id", "dispatch_id", "prior_outcome", "correction_summary", "contract_generation"),
        ),
        "swarm_cancel": _object(
            {
                "operation": operation,
                "run_id": UUID_SCHEMA,
                "target_type": _string(maximum=16, enum=("dispatch", "task", "run")),
                "target_id": UUID_SCHEMA,
            },
            required=("operation", "run_id", "target_type", "target_id"),
        ),
        "swarm_record_decision": _object(
            {
                "operation": operation,
                "run_id": UUID_SCHEMA,
                "kind": _string(maximum=64, enum=DECISION_KINDS),
                "decision": _string(maximum=2048),
                "rationale": _string(maximum=2048),
                "authority_ref": _string(maximum=512),
                "affected_ids": _array(SAFE_ID_SCHEMA, minimum=1, maximum=64, unique=True),
                "prior_generation": _nullable({"type": "integer", "minimum": 1, "maximum": 2_147_483_647}),
            },
            required=("operation", "run_id", "kind", "decision", "rationale", "authority_ref", "affected_ids", "prior_generation"),
        ),
        "swarm_record_evidence": _object(
            {
                "operation": operation,
                "run_id": UUID_SCHEMA,
                "evidence_type": SAFE_ID_SCHEMA,
                "reference": _string(maximum=2048),
                "source": SAFE_ID_SCHEMA,
                "producer": SAFE_ID_SCHEMA,
                "artifact_digest": _nullable(DIGEST_SCHEMA),
                "check_identity": _string(maximum=1024),
                "observed_outcome": OUTCOME_SCHEMA,
                "criteria": _array(_string(maximum=512), maximum=64),
                "unknowns": _array(_string(maximum=512), maximum=64),
                "limitations": _array(_string(maximum=512), maximum=64),
                "verifier_id": _nullable(SAFE_ID_SCHEMA),
            },
            required=("operation", "run_id", "evidence_type", "reference", "source", "producer", "artifact_digest", "check_identity", "observed_outcome", "criteria", "unknowns", "limitations", "verifier_id"),
        ),
        "swarm_close": _object(
            {
                "operation": operation,
                "run_id": UUID_SCHEMA,
                "effect_plan": _array(EFFECT_SCHEMA, minimum=1, maximum=7, unique=True),
                "retained_resource_ids": _array(UUID_SCHEMA, maximum=64, unique=True),
            },
            required=("operation", "run_id", "effect_plan", "retained_resource_ids"),
        ),
        "swarm_trace": _object(
            {
                "project_id": UUID_SCHEMA,
                "run_id": _nullable(UUID_SCHEMA),
                "mode": _string(maximum=16, enum=("timeline", "explain", "operations", "decisions", "evidence", "retries", "resources", "metrics", "integrity", "export")),
                "filters": JSON_OBJECT_SCHEMA,
                "cursor": CURSOR_SCHEMA,
                "limit": {"type": "integer", "minimum": 1, "maximum": 200},
            },
            required=("project_id", "run_id", "mode", "filters", "cursor", "limit"),
        ),
        "orca_search": _object(
            {
                "project_id": UUID_SCHEMA,
                "query": _string(maximum=512),
                "effect": _nullable(EFFECT_SCHEMA),
                "limit": {"type": "integer", "minimum": 1, "maximum": 50},
            },
            required=("project_id", "query", "effect", "limit"),
        ),
        "orca_describe": _object(
            {"project_id": UUID_SCHEMA, "command_id": SAFE_ID_SCHEMA, "catalog_digest": DIGEST_SCHEMA},
            required=("project_id", "command_id", "catalog_digest"),
        ),
        "orca_call": _object(
            {
                "project_id": UUID_SCHEMA,
                "command_id": SAFE_ID_SCHEMA,
                "arguments": JSON_OBJECT_SCHEMA,
                "catalog_digest": DIGEST_SCHEMA,
                "schema_bundle_digest": _nullable(DIGEST_SCHEMA),
                "expected_effect": EFFECT_SCHEMA,
                "reason": reason,
                "operation": _nullable(operation),
            },
            required=("project_id", "command_id", "arguments", "catalog_digest", "schema_bundle_digest", "expected_effect", "reason", "operation"),
        ),
        "orca_batch": _object(
            {
                "operation": operation,
                "catalog_digest": DIGEST_SCHEMA,
                "calls": _array(
                    _object(
                        {"command_id": SAFE_ID_SCHEMA, "arguments": JSON_OBJECT_SCHEMA, "expected_effect": EFFECT_SCHEMA, "reason": reason},
                        required=("command_id", "arguments", "expected_effect", "reason"),
                    ),
                    minimum=1,
                    maximum=32,
                ),
            },
            required=("operation", "catalog_digest", "calls"),
        ),
        "orca_events": _object(
            {
                "project_id": UUID_SCHEMA,
                "run_id": _nullable(UUID_SCHEMA),
                "provider_cursor": CURSOR_SCHEMA,
                "wait_ms": {"type": "integer", "minimum": 0, "maximum": 30_000},
                "limit": {"type": "integer", "minimum": 1, "maximum": 200},
            },
            required=("project_id", "run_id", "provider_cursor", "wait_ms", "limit"),
        ),
        "learning_capture": _object(
            {
                "operation": operation,
                "action": _string(maximum=16, enum=("inspect", "set", "reduce", "pause", "resume", "seal")),
                "episode_id": _nullable(UUID_SCHEMA),
                "capture_policy": _nullable(_string(maximum=32, enum=CAPTURE_POLICIES)),
                "consent_authority_ref": _string(maximum=512),
            },
            required=("operation", "action", "episode_id", "capture_policy", "consent_authority_ref"),
        ),
        "learning_label": _object(
            {
                "operation": operation,
                "episode_id": UUID_SCHEMA,
                "target_ids": _array(UUID_SCHEMA, minimum=1, maximum=64, unique=True),
                "label_type": _string(maximum=32, enum=("outcome", "correction", "preference", "failure", "quality", "eligibility", "contamination", "consent", "retraction")),
                "label": JSON_OBJECT_SCHEMA,
                "authority_ref": _string(maximum=512),
                "evidence_refs": _array(_string(maximum=1024), maximum=64),
                "superseded_label_ids": _array(UUID_SCHEMA, maximum=64, unique=True),
            },
            required=("operation", "episode_id", "target_ids", "label_type", "label", "authority_ref", "evidence_refs", "superseded_label_ids"),
        ),
        "learning_dataset": _object(
            {
                "operation": _nullable(operation),
                "project_id": UUID_SCHEMA,
                "action": _string(maximum=16, enum=("inspect", "build", "validate", "seal", "revoke")),
                "purpose": _string(maximum=128),
                "episode_ids": _array(UUID_SCHEMA, maximum=256, unique=True),
                "selection_contract_digest": DIGEST_SCHEMA,
            },
            required=("operation", "project_id", "action", "purpose", "episode_ids", "selection_contract_digest"),
        ),
        "learning_export": _object(
            {
                "operation": operation,
                "dataset_id": UUID_SCHEMA,
                "dataset_digest": DIGEST_SCHEMA,
                "destination": _string(maximum=4096),
                "authority_ref": _string(maximum=512),
            },
            required=("operation", "dataset_id", "dataset_digest", "destination", "authority_ref"),
        ),
        "project_forget": _object(
            {
                "operation": operation,
                "safe_alias_confirmation": _string(maximum=128),
                "mode": _string(maximum=32, enum=("normal", "privacy_emergency")),
                "reason": _string(maximum=1024),
                "owner_authority_ref": _string(maximum=512),
                "required_prior_export_digest": _nullable(DIGEST_SCHEMA),
            },
            required=("operation", "safe_alias_confirmation", "mode", "reason", "owner_authority_ref", "required_prior_export_digest"),
        ),
    }
    return schemas


def _deep_freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType({key: _deep_freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_deep_freeze(item) for item in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


TOOL_SCHEMAS: Mapping[str, Mapping[str, Any]] = _deep_freeze(_build_tool_schemas())
CALLABLE_TOOL_NAMES = frozenset()

_TOOL_PHASES = {
    "project_admit": "M2.3",
    "project_inspect": "M2.3",
    "swarm_validate": "M2.6",
    "swarm_trace": "M2.6",
    "orca_search": "M2.6",
    "orca_describe": "M2.6",
    "orca_call": "M2.6",
    "orca_events": "M2.6",
    "swarm_start": "M3.1",
    "swarm_status": "M3.2",
    "swarm_reconcile": "M3.3",
    "swarm_retry": "M3.3",
    "swarm_cancel": "M3.4",
    "swarm_close": "M3.4",
    "swarm_record_decision": "M3.2",
    "swarm_record_evidence": "M3.2",
    "swarm_dispatch": "M4.2",
    "swarm_message": "M4.2",
    "orca_batch": "M4.2",
    "learning_capture": "M5.1",
    "learning_label": "M5.2",
    "learning_dataset": "M5.3",
    "learning_export": "M5.4",
    "project_forget": "M5.6",
}

_FORBIDDEN_PRINCIPAL_KEYS = frozenset({"principal", "principal_id", "coordinator_principal", "actor_principal"})
_CURSOR_KEYS = frozenset({"cursor", "provider_cursor"})


def _validate_json_value(value: Any, *, depth: int = 0) -> None:
    if depth > MAX_NESTING_DEPTH:
        _raise("INVALID_INPUT")
    if value is None or isinstance(value, (str, bool)):
        if isinstance(value, str) and len(value.encode("utf-8")) > MAX_STRING_BYTES:
            _raise("INVALID_INPUT")
        return
    if isinstance(value, int) and not isinstance(value, bool):
        return
    if isinstance(value, float):
        _raise("INVALID_INPUT")
    if isinstance(value, list):
        if len(value) > MAX_ARRAY_ITEMS:
            _raise("INVALID_INPUT")
        for item in value:
            _validate_json_value(item, depth=depth + 1)
        return
    if isinstance(value, dict):
        if len(value) > MAX_ARRAY_ITEMS:
            _raise("INVALID_INPUT")
        for key, item in value.items():
            if not isinstance(key, str) or not key or len(key.encode("utf-8")) > 256:
                _raise("INVALID_INPUT")
            if key in _FORBIDDEN_PRINCIPAL_KEYS:
                _raise("PRINCIPAL_UNAUTHENTICATED")
            _validate_json_value(item, depth=depth + 1)
        return
    _raise("INVALID_INPUT")


def _matches_type(value: Any, expected: str) -> bool:
    if expected == "null":
        return value is None
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    return False


def _validate_schema(value: Any, schema: Mapping[str, Any], *, depth: int = 0) -> None:
    if depth > MAX_NESTING_DEPTH:
        _raise("INVALID_INPUT")
    expected_type = schema.get("type")
    types = tuple(expected_type) if isinstance(expected_type, (list, tuple)) else (expected_type,)
    if expected_type is not None and not any(_matches_type(value, item) for item in types):
        _raise("INVALID_INPUT")
    if value is None:
        return
    if "const" in schema and value != schema["const"]:
        _raise("INVALID_INPUT")
    if "enum" in schema and value not in schema["enum"]:
        _raise("INVALID_INPUT")

    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0) or len(value) > schema.get("maxLength", MAX_STRING_BYTES):
            _raise("INVALID_INPUT")
        if len(value.encode("utf-8")) > MAX_STRING_BYTES:
            _raise("INVALID_INPUT")
        pattern = schema.get("pattern")
        if pattern is not None and re.fullmatch(pattern, value) is None:
            _raise("INVALID_INPUT")
        if schema.get("format") == "uuid":
            try:
                parsed = uuid.UUID(value)
            except (ValueError, AttributeError):
                _raise("INVALID_INPUT")
            if str(parsed) != value:
                _raise("INVALID_INPUT")
        return

    if isinstance(value, int) and not isinstance(value, bool):
        if value < schema.get("minimum", value) or value > schema.get("maximum", value):
            _raise("INVALID_INPUT")
        return

    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0) or len(value) > schema.get("maxItems", MAX_ARRAY_ITEMS):
            _raise("INVALID_INPUT")
        if schema.get("uniqueItems"):
            canonical_items = [json.dumps(item, sort_keys=True, separators=(",", ":"), ensure_ascii=False) for item in value]
            if len(canonical_items) != len(set(canonical_items)):
                _raise("INVALID_INPUT")
        item_schema = schema.get("items", {})
        for item in value:
            _validate_schema(item, item_schema, depth=depth + 1)
        return

    if isinstance(value, dict):
        properties = schema.get("properties", {})
        required = set(schema.get("required", ()))
        if not required.issubset(value):
            _raise("INVALID_INPUT")
        additional = schema.get("additionalProperties", True)
        for key, item in value.items():
            if key in properties:
                _validate_schema(item, properties[key], depth=depth + 1)
            elif additional is False:
                _raise("INVALID_INPUT")
            elif isinstance(additional, Mapping) and additional:
                _validate_schema(item, additional, depth=depth + 1)
            else:
                _validate_json_value(item, depth=depth + 1)


def _scan_cursor_fields(value: Any) -> None:
    if not isinstance(value, dict):
        return
    for key, item in value.items():
        if key in _CURSOR_KEYS and item is not None:
            if not isinstance(item, str) or len(item.encode("utf-8")) > MAX_CURSOR_BYTES:
                _raise("INVALID_CURSOR")
            if re.fullmatch(r"[A-Za-z0-9_-]+", item) is None:
                _raise("INVALID_CURSOR")
        if isinstance(item, dict):
            _scan_cursor_fields(item)


def canonical_request_bytes(tool_name: str, arguments: Mapping[str, Any]) -> bytes:
    """Return deterministic canonical bytes for one bounded request."""
    if tool_name not in TOOL_SCHEMAS or not isinstance(arguments, Mapping):
        _raise("INVALID_INPUT")
    detached = dict(arguments)
    _validate_json_value(detached)
    payload = {"protocol": PROTOCOL_VERSION, "tool": tool_name, "arguments": detached}
    try:
        encoded = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError):
        _raise("INVALID_INPUT")
    if len(encoded) > MAX_REQUEST_BYTES:
        _raise("INVALID_INPUT")
    return encoded


def canonical_request_digest(tool_name: str, arguments: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_request_bytes(tool_name, arguments)).hexdigest()


def validate_request(tool_name: str, arguments: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and detach one strict tool request without executing it."""
    encoded = canonical_request_bytes(tool_name, arguments)
    detached = json.loads(encoded)["arguments"]
    _scan_cursor_fields(detached)
    if tool_name == "swarm_validate":
        manifest = detached.get("manifest")
        if isinstance(manifest, dict) and manifest.get("protocol") != PROTOCOL_VERSION:
            _raise("PROTOCOL_MISMATCH")
    _validate_schema(detached, TOOL_SCHEMAS[tool_name])
    return detached


def ensure_idempotent_replay(existing_digest: str, proposed_digest: str) -> str:
    """Accept only an exact canonical replay of one operation identity."""
    for value in (existing_digest, proposed_digest):
        if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
            _raise("INVALID_INPUT")
    if existing_digest != proposed_digest:
        _raise("IDEMPOTENCY_CONFLICT")
    return existing_digest


def _validate_envelope_identity(request_id: str, operation_id: str | None, trace_event_ids: Sequence[str]) -> None:
    _validate_schema(request_id, UUID_SCHEMA)
    if operation_id is not None:
        _validate_schema(operation_id, UUID_SCHEMA)
    if len(trace_event_ids) > 256:
        _raise("INVALID_INPUT")
    for event_id in trace_event_ids:
        _validate_schema(event_id, UUID_SCHEMA)


def success_envelope(
    *,
    request_id: str,
    operation_id: str | None,
    trace_event_ids: Sequence[str],
    effect: str,
    outcome: str,
    result: Any,
    unknowns: Sequence[str] = (),
    warnings: Sequence[str] = (),
) -> dict[str, Any]:
    _validate_envelope_identity(request_id, operation_id, trace_event_ids)
    if effect not in EFFECT_CLASSES or outcome not in OUTCOMES:
        _raise("INTERNAL_ERROR")
    _validate_json_value(result)
    _validate_json_value(list(unknowns))
    _validate_json_value(list(warnings))
    return {
        "protocol": PROTOCOL_VERSION,
        "ok": True,
        "request_id": request_id,
        "operation_id": operation_id,
        "trace_event_ids": list(trace_event_ids),
        "effect": effect,
        "outcome": outcome,
        "result": deepcopy(result),
        "unknowns": list(unknowns),
        "warnings": list(warnings),
        "error": None,
    }


def error_envelope(
    *,
    request_id: str,
    operation_id: str | None,
    trace_event_ids: Sequence[str],
    code: str,
    retryable: bool = False,
    reconciliation_required: bool = False,
    unknowns: Sequence[str] = (),
    warnings: Sequence[str] = (),
) -> dict[str, Any]:
    _validate_envelope_identity(request_id, operation_id, trace_event_ids)
    safe = ProtocolError(code)
    _validate_json_value(list(unknowns))
    _validate_json_value(list(warnings))
    return {
        "protocol": PROTOCOL_VERSION,
        "ok": False,
        "request_id": request_id,
        "operation_id": operation_id,
        "trace_event_ids": list(trace_event_ids),
        "effect": "UNKNOWN",
        "outcome": "REJECTED",
        "result": None,
        "unknowns": list(unknowns),
        "warnings": list(warnings),
        "error": {
            "code": safe.code,
            "message": safe.message,
            "retryable": bool(retryable),
            "reconciliation_required": bool(reconciliation_required),
        },
    }


def export_schema_bundle() -> dict[str, Any]:
    """Return a detached deterministic snapshot of the M2.2 contract."""
    tools = [
        {
            "name": name,
            "owner_milestone": _TOOL_PHASES[name],
            "callable": name in CALLABLE_TOOL_NAMES,
            "inputSchema": _thaw(TOOL_SCHEMAS[name]),
        }
        for name in sorted(TOOL_SCHEMAS)
    ]
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "protocol": PROTOCOL_VERSION,
        "limits": {
            "request_bytes": MAX_REQUEST_BYTES,
            "cursor_bytes": MAX_CURSOR_BYTES,
            "string_bytes": MAX_STRING_BYTES,
            "array_items": MAX_ARRAY_ITEMS,
            "nesting_depth": MAX_NESTING_DEPTH,
        },
        "effect_classes": list(EFFECT_CLASSES),
        "outcomes": list(OUTCOMES),
        "stable_errors": [{"code": code, "message": ERROR_MESSAGES[code]} for code in ERROR_MESSAGES],
        "callable_tool_names": sorted(CALLABLE_TOOL_NAMES),
        "tools": tools,
    }


def schema_bundle_bytes() -> bytes:
    return (json.dumps(export_schema_bundle(), indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
