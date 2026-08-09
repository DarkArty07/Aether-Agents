"""M2.2 contract tests for canonical protocol, schemas, bounds, and errors."""

from __future__ import annotations

import hashlib
import json
import math
import uuid
from collections.abc import Mapping
from pathlib import Path

import pytest

from aether_mcp import server
from aether_mcp.protocol import (
    CALLABLE_TOOL_NAMES,
    EFFECT_CLASSES,
    ERROR_MESSAGES,
    MAX_CURSOR_BYTES,
    MAX_REQUEST_BYTES,
    OUTCOMES,
    PROTOCOL_VERSION,
    TOOL_SCHEMAS,
    ProtocolError,
    canonical_request_bytes,
    canonical_request_digest,
    ensure_idempotent_replay,
    error_envelope,
    export_schema_bundle,
    safe_internal_error,
    schema_bundle_bytes,
    success_envelope,
    validate_request,
)

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT / "schemas/aether-mcp/v1alpha2/bundle.json"
HISTORICAL_SNAPSHOT = ROOT / "schemas/aether-mcp/v1alpha1/bundle.json"
HISTORICAL_SNAPSHOT_SHA256 = "e7f39a76ac4795ade2ec0a15bf64b4cab2233b912cf2285b0ce76d2805a2e605"

EXPECTED_TOOL_NAMES = {
    "project_admit",
    "project_inspect",
    "swarm_validate",
    "swarm_start",
    "swarm_status",
    "swarm_dispatch",
    "swarm_message",
    "swarm_reconcile",
    "swarm_retry",
    "swarm_cancel",
    "swarm_close",
    "swarm_trace",
    "orca_search",
    "orca_describe",
    "orca_call",
}

REMOVED_OPERATIONAL_TOOL_NAMES = {
    "swarm_record_decision",
    "swarm_record_evidence",
    "orca_batch",
    "orca_events",
    "learning_capture",
    "learning_label",
    "learning_dataset",
    "learning_export",
    "project_forget",
}

EXPECTED_ERROR_CODES = {
    "INVALID_INPUT",
    "INVALID_CURSOR",
    "PROTOCOL_MISMATCH",
    "PRINCIPAL_UNAUTHENTICATED",
    "PRINCIPAL_UNAUTHORIZED",
    "PROJECT_NOT_ADMITTED",
    "PROJECT_IDENTITY_MISMATCH",
    "PROJECT_HAS_OPEN_RUNS",
    "PROJECT_FORGET_CONFIRMATION_MISMATCH",
    "CONTRACT_STALE",
    "MANIFEST_INVALID",
    "DEPENDENCY_CYCLE",
    "TASK_NOT_READY",
    "WRITE_SCOPE_CONFLICT",
    "PARTICIPANT_REQUIRED_MISSING",
    "PARTICIPANT_DISABLED",
    "PARTICIPANT_FORBIDDEN",
    "PARTICIPANT_RETIRED",
    "PARTICIPANT_UNAVAILABLE",
    "CAPABILITY_UNAVAILABLE",
    "PROVIDER_UNAVAILABLE",
    "PROVIDER_SCHEMA_DRIFT",
    "PROVIDER_RESPONSE_INVALID",
    "EFFECT_NOT_AUTHORIZED",
    "EFFECT_UNKNOWN",
    "IDEMPOTENCY_CONFLICT",
    "OPERATION_IN_PROGRESS",
    "DELIVERY_UNKNOWN",
    "TRACE_STORE_BUSY",
    "RECONCILIATION_REQUIRED",
    "STALE_DISPATCH",
    "ATTEMPT_NOT_FENCED",
    "ATTEMPT_BUDGET_EXHAUSTED",
    "EVIDENCE_INSUFFICIENT",
    "CLEANUP_INCOMPLETE",
    "SURVIVOR_UNKNOWN",
    "TRACE_INTEGRITY_FAILURE",
    "PRIVACY_POLICY_VIOLATION",
    "RETENTION_POLICY_VIOLATION",
    "CAPTURE_DISABLED",
    "CAPTURE_POLICY_ESCALATION",
    "CAPTURE_INCOMPLETE",
    "CAPTURE_QUOTA_EXCEEDED",
    "EPISODE_NOT_SEALED",
    "SENSITIVE_CONTENT_QUARANTINED",
    "LABEL_AUTHORITY_INSUFFICIENT",
    "DATASET_CONTAMINATION",
    "DATASET_LINEAGE_INCOMPLETE",
    "EXPORT_NOT_AUTHORIZED",
    "INTERNAL_ERROR",
}

PROJECT_ID = "01989f1d-54a7-7a9e-9dc4-8206cad0f6e3"
RUN_ID = "01989f2f-8b67-7a42-8e1e-2c5d23ff6b50"
OPERATION_ID = "01989f3f-8b67-7a42-8e1e-2c5d23ff6b51"
DIGEST = "a" * 64


def _expect_error(code: str, tool: str, arguments: dict[str, object]) -> ProtocolError:
    with pytest.raises(ProtocolError) as captured:
        validate_request(tool, arguments)
    assert captured.value.code == code
    return captured.value


def _operation() -> dict[str, object]:
    return {
        "operation_id": OPERATION_ID,
        "project_id": PROJECT_ID,
        "contract_id": "contract:test/1",
        "use_case_id": None,
        "reason": {
            "code": "TEST",
            "summary": "bounded test request",
            "authority_ref": "decision:test",
        },
        "expected_effect": "LOCAL_REVERSIBLE",
    }


def _trace_operation() -> dict[str, object]:
    operation = _operation()
    operation["expected_effect"] = "LOCAL_APPEND_ONLY"
    return operation


def _trace_query() -> dict[str, object]:
    return {
        "action": "query",
        "project_id": PROJECT_ID,
        "run_id": RUN_ID,
        "operation": None,
        "mode": "timeline",
        "filters": {},
        "cursor": None,
        "limit": 50,
        "decision": None,
        "evidence": None,
    }


def _trace_decision() -> dict[str, object]:
    return {
        "action": "record_decision",
        "project_id": PROJECT_ID,
        "run_id": RUN_ID,
        "operation": _trace_operation(),
        "mode": None,
        "filters": None,
        "cursor": None,
        "limit": None,
        "decision": {
            "kind": "route_selected",
            "decision": "use the bounded synthetic path",
            "rationale": "proves the provider boundary without model spend",
            "authority_ref": "decision:test",
            "affected_ids": ["task:synthetic-a"],
            "prior_generation": None,
        },
        "evidence": None,
    }


def _trace_evidence() -> dict[str, object]:
    return {
        "action": "record_evidence",
        "project_id": PROJECT_ID,
        "run_id": RUN_ID,
        "operation": _trace_operation(),
        "mode": None,
        "filters": None,
        "cursor": None,
        "limit": None,
        "decision": None,
        "evidence": {
            "evidence_type": "test_result",
            "reference": "artifact:synthetic/result.json",
            "source": "pytest",
            "producer": "hermes",
            "artifact_digest": DIGEST,
            "check_identity": "pytest tests/aether_mcp/test_protocol.py",
            "observed_outcome": "SUCCEEDED",
            "criteria": ["successor protocol contract"],
            "unknowns": [],
            "limitations": [],
            "verifier_id": None,
        },
    }


def test_protocol_constants_match_frozen_contract() -> None:
    assert PROTOCOL_VERSION == "aether.mcp/v1alpha2"
    assert set(EFFECT_CLASSES) == {
        "READ_ONLY",
        "LOCAL_APPEND_ONLY",
        "LOCAL_REVERSIBLE",
        "LOCAL_DESTRUCTIVE",
        "EXTERNAL_REVERSIBLE",
        "EXTERNAL_IRREVERSIBLE",
        "UNKNOWN",
    }
    assert set(ERROR_MESSAGES) == EXPECTED_ERROR_CODES
    assert MAX_REQUEST_BYTES == 65_536
    assert MAX_CURSOR_BYTES == 1_024


def test_all_15_exact_tool_schemas_are_strict_and_none_callable_yet() -> None:
    assert set(TOOL_SCHEMAS) == EXPECTED_TOOL_NAMES
    assert len(TOOL_SCHEMAS) == 15
    assert CALLABLE_TOOL_NAMES == frozenset()
    for name, schema in TOOL_SCHEMAS.items():
        assert schema["type"] == "object", name
        assert schema["additionalProperties"] is False, name
        assert isinstance(schema["properties"], Mapping), name


def test_removed_and_deferred_tool_names_are_not_exported_or_validated() -> None:
    assert set(TOOL_SCHEMAS).isdisjoint(REMOVED_OPERATIONAL_TOOL_NAMES)
    exported_names = {item["name"] for item in export_schema_bundle()["tools"]}
    assert exported_names.isdisjoint(REMOVED_OPERATIONAL_TOOL_NAMES)
    for name in REMOVED_OPERATIONAL_TOOL_NAMES:
        _expect_error("INVALID_INPUT", name, {})


def test_cancellation_and_cleanup_outcomes_are_explicit() -> None:
    assert {"CANCELLED", "CANCEL_FAILED", "CLEANUP_FAILED"}.issubset(OUTCOMES)


def test_swarm_trace_query_and_append_actions_validate_exactly() -> None:
    assert validate_request("swarm_trace", _trace_query())["action"] == "query"
    assert validate_request("swarm_trace", _trace_decision())["action"] == "record_decision"
    assert validate_request("swarm_trace", _trace_evidence())["action"] == "record_evidence"


def test_swarm_trace_action_modes_fail_closed() -> None:
    query_with_operation = _trace_query()
    query_with_operation["operation"] = _trace_operation()
    _expect_error("INVALID_INPUT", "swarm_trace", query_with_operation)

    decision_without_operation = _trace_decision()
    decision_without_operation["operation"] = None
    _expect_error("INVALID_INPUT", "swarm_trace", decision_without_operation)

    decision_with_wrong_effect = _trace_decision()
    decision_with_wrong_effect["operation"] = _operation()
    _expect_error("INVALID_INPUT", "swarm_trace", decision_with_wrong_effect)

    evidence_with_decision = _trace_evidence()
    evidence_with_decision["decision"] = _trace_decision()["decision"]
    _expect_error("INVALID_INPUT", "swarm_trace", evidence_with_decision)

    decision_without_run = _trace_decision()
    decision_without_run["run_id"] = None
    _expect_error("INVALID_INPUT", "swarm_trace", decision_without_run)

    decision_for_foreign_project = _trace_decision()
    assert isinstance(decision_for_foreign_project["operation"], dict)
    decision_for_foreign_project["operation"]["project_id"] = str(uuid.uuid4())
    _expect_error("INVALID_INPUT", "swarm_trace", decision_for_foreign_project)


def test_exported_registry_is_deeply_immutable() -> None:
    with pytest.raises(TypeError):
        TOOL_SCHEMAS["project_inspect"] = {}  # type: ignore[index]
    with pytest.raises(TypeError):
        TOOL_SCHEMAS["project_inspect"]["properties"]["project_id"] = {}  # type: ignore[index]


def test_schema_bundle_snapshot_matches_generated_bytes_exactly() -> None:
    generated = schema_bundle_bytes()
    assert generated == SNAPSHOT.read_bytes()
    assert json.loads(generated) == export_schema_bundle()
    assert generated.endswith(b"\n")


def test_historical_v1alpha1_snapshot_is_preserved_byte_exactly() -> None:
    assert hashlib.sha256(HISTORICAL_SNAPSHOT.read_bytes()).hexdigest() == HISTORICAL_SNAPSHOT_SHA256


def test_canonical_request_bytes_and_digest_are_deterministic() -> None:
    first = {"project_id": PROJECT_ID, "detail": "summary", "wait_ms": 0}
    second = {"wait_ms": 0, "detail": "summary", "project_id": PROJECT_ID}
    first_bytes = canonical_request_bytes("swarm_status", first)
    second_bytes = canonical_request_bytes("swarm_status", second)
    assert first_bytes == second_bytes
    assert first_bytes == (
        b'{"arguments":{"detail":"summary","project_id":"01989f1d-54a7-7a9e-9dc4-8206cad0f6e3",'
        b'"wait_ms":0},"protocol":"aether.mcp/v1alpha2","tool":"swarm_status"}'
    )
    assert canonical_request_digest("swarm_status", first) == hashlib.sha256(first_bytes).hexdigest()


def test_representative_read_and_mutation_requests_validate() -> None:
    inspect = validate_request("project_inspect", {"project_id": PROJECT_ID})
    assert inspect == {"project_id": PROJECT_ID}
    call = validate_request(
        "orca_call",
        {
            "project_id": PROJECT_ID,
            "command_id": "agent-context",
            "arguments": {"json": True},
            "catalog_digest": DIGEST,
            "schema_bundle_digest": None,
            "expected_effect": "READ_ONLY",
            "reason": {"code": "INSPECT", "summary": "inspect catalog", "authority_ref": "contract:test"},
            "operation": None,
        },
    )
    assert call["command_id"] == "agent-context"


def test_unknown_field_and_caller_principal_are_rejected() -> None:
    _expect_error("INVALID_INPUT", "project_inspect", {"project_id": PROJECT_ID, "extra": True})
    error = _expect_error(
        "PRINCIPAL_UNAUTHENTICATED",
        "project_inspect",
        {"project_id": PROJECT_ID, "principal": "admin"},
    )
    assert "admin" not in error.message


def test_oversized_body_cursor_string_and_array_are_rejected() -> None:
    _expect_error("INVALID_INPUT", "orca_search", {"project_id": PROJECT_ID, "query": "x" * MAX_REQUEST_BYTES})
    _expect_error(
        "INVALID_CURSOR",
        "swarm_status",
        {"project_id": PROJECT_ID, "cursor": "x" * (MAX_CURSOR_BYTES + 1), "wait_ms": 0, "detail": "summary"},
    )
    _expect_error(
        "INVALID_INPUT",
        "swarm_dispatch",
        {"operation": _operation(), "run_id": RUN_ID, "task_keys": [f"task-{index}" for index in range(65)]},
    )


def test_malformed_uuid_and_digest_are_rejected_without_echo() -> None:
    error = _expect_error("INVALID_INPUT", "project_inspect", {"project_id": "NOT-A-UUID-SECRET"})
    assert "NOT-A-UUID-SECRET" not in error.message
    error = _expect_error(
        "INVALID_INPUT",
        "orca_describe",
        {"project_id": PROJECT_ID, "command_id": "agent-context", "catalog_digest": "bad-secret-digest"},
    )
    assert "bad-secret-digest" not in error.message


def test_wrong_protocol_version_is_a_stable_protocol_mismatch() -> None:
    error = _expect_error("PROTOCOL_MISMATCH", "swarm_validate", {"manifest": {"protocol": "aether.mcp/v9-secret"}})
    assert "v9-secret" not in error.message


def test_arbitrary_command_and_shell_fields_are_not_admitted() -> None:
    base = {
        "project_id": PROJECT_ID,
        "command_id": "agent-context",
        "arguments": {},
        "catalog_digest": DIGEST,
        "schema_bundle_digest": None,
        "expected_effect": "READ_ONLY",
        "reason": {"code": "TEST", "summary": "bounded", "authority_ref": "decision:test"},
        "operation": None,
    }
    for field in ("command", "shell", "argv", "interpolation"):
        _expect_error("INVALID_INPUT", "orca_call", {**base, field: "rm -rf /synthetic-secret"})


@pytest.mark.parametrize("value", [1.5, math.nan, math.inf, -math.inf])
def test_floats_and_non_finite_numbers_are_rejected(value: float) -> None:
    _expect_error(
        "INVALID_INPUT",
        "orca_call",
        {
            "project_id": PROJECT_ID,
            "command_id": "agent-context",
            "arguments": {"value": value},
            "catalog_digest": DIGEST,
            "schema_bundle_digest": None,
            "expected_effect": "READ_ONLY",
            "reason": {"code": "TEST", "summary": "bounded", "authority_ref": "decision:test"},
            "operation": None,
        },
    )


def test_idempotent_replay_requires_same_canonical_digest() -> None:
    digest = canonical_request_digest("project_inspect", {"project_id": PROJECT_ID})
    assert ensure_idempotent_replay(digest, digest) == digest
    with pytest.raises(ProtocolError) as captured:
        ensure_idempotent_replay(digest, "b" * 64)
    assert captured.value.code == "IDEMPOTENCY_CONFLICT"


def test_result_and_error_envelopes_have_exact_stable_shape() -> None:
    success = success_envelope(
        request_id=RUN_ID,
        operation_id=OPERATION_ID,
        trace_event_ids=(PROJECT_ID,),
        effect="LOCAL_REVERSIBLE",
        outcome="SUCCEEDED",
        result={"accepted": True},
    )
    assert success == {
        "protocol": PROTOCOL_VERSION,
        "ok": True,
        "request_id": RUN_ID,
        "operation_id": OPERATION_ID,
        "trace_event_ids": [PROJECT_ID],
        "effect": "LOCAL_REVERSIBLE",
        "outcome": "SUCCEEDED",
        "result": {"accepted": True},
        "unknowns": [],
        "warnings": [],
        "error": None,
    }
    failure = error_envelope(
        request_id=RUN_ID,
        operation_id=None,
        trace_event_ids=(),
        code="PARTICIPANT_FORBIDDEN",
    )
    assert failure["ok"] is False
    assert failure["effect"] == "UNKNOWN"
    assert failure["outcome"] == "REJECTED"
    assert failure["result"] is None
    assert failure["error"] == {
        "code": "PARTICIPANT_FORBIDDEN",
        "message": ERROR_MESSAGES["PARTICIPANT_FORBIDDEN"],
        "retryable": False,
        "reconciliation_required": False,
    }


def test_internal_exception_and_error_envelope_never_include_secret_text() -> None:
    canary = "SYNTHETIC-SECRET-PROVIDER-BODY-DO-NOT-ECHO"
    safe = safe_internal_error(RuntimeError(canary))
    envelope = error_envelope(request_id=RUN_ID, operation_id=None, trace_event_ids=(), code=safe.code)
    serialized = json.dumps(envelope, sort_keys=True)
    assert canary not in safe.message
    assert canary not in serialized
    assert "traceback" not in serialized.lower()


def test_invalid_error_code_is_replaced_by_safe_internal_error() -> None:
    envelope = error_envelope(
        request_id=RUN_ID,
        operation_id=None,
        trace_event_ids=(),
        code="CALLER_SECRET_ERROR_CODE",
    )
    assert envelope["error"]["code"] == "INTERNAL_ERROR"
    assert "CALLER_SECRET" not in json.dumps(envelope)


def test_request_validation_returns_detached_canonical_value() -> None:
    original = {"project_id": PROJECT_ID}
    validated = validate_request("project_inspect", original)
    assert validated == original
    assert validated is not original
    original["project_id"] = str(uuid.uuid4())
    assert validated["project_id"] == PROJECT_ID


@pytest.mark.filterwarnings("ignore:Field 'lifespan' has an incomplete definition:UserWarning")
def test_stdio_server_remains_default_off_and_zero_tool() -> None:
    assert tuple(server.create_server()._tool_manager.list_tools()) == ()
