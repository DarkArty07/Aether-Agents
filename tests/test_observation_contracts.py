from __future__ import annotations

import json
import os
import secrets
import stat
from copy import deepcopy
from datetime import timedelta
from pathlib import Path

import pytest
from jsonschema import ValidationError
from observation_helpers import (
    BASE,
    PROJECT_ID,
    TRACE_ID,
    EventFactory,
    complete_trace,
    native_pseudonym,
    project_marker,
)

from aether_agents import paths as paths_module
from aether_agents.observation import checkpoint as checkpoint_module
from aether_agents.observation import query
from aether_agents.observation.capture.collector import Collector, reentrancy_guard
from aether_agents.observation.capture.projectors import EventBuilder
from aether_agents.observation.checkpoint import AuthorityContext, CheckpointSink
from aether_agents.observation.context import (
    HealthCounters,
    ObservationContextResolver,
    ProjectRegistry,
    canonical_project_id,
)
from aether_agents.observation.contracts import (
    ARTIFACT_REF_PATTERN,
    OPAQUE_REF_PATTERN,
    VERSION_REF_PATTERN,
    canonical_json_bytes,
    event_validator,
    manifest_validator,
    normalize_native_status,
    schema_bytes,
    schema_digest,
    summary_validator,
    validate_event,
    validate_manifest,
    validate_summary,
)
from aether_agents.observation.correlation import OwnerMessageCandidates, WorkGraphBinder
from aether_agents.observation.fingerprints import FingerprintKeyring, keyed_fingerprint
from aether_agents.observation.identity import (
    ProducerSequence,
    correlation_token,
    deterministic_event_id,
    fingerprint_key_id,
    native_identity,
    new_event_id,
    new_producer_epoch,
    new_trace_id,
    parse_correlation_token,
    summary_id,
)
from aether_agents.observation.privacy import (
    ForbiddenPayload,
    assert_clean,
    native_agent_task_ref,
    native_kanban_task_ref,
    native_profile_ref,
    native_run_id,
    relative_artifact_ref,
    safe_error_class,
    safe_ref,
)
from aether_agents.paths import (
    ObservationPaths,
    UnsafeObservationPath,
    atomic_private_write,
    ensure_private_dir,
    harden_file,
    state_root,
)


def test_all_three_normative_schemas_compile_and_have_stable_digests() -> None:
    assert event_validator().schema["$id"].endswith("observation-event.schema.json")
    assert summary_validator().schema["$id"].endswith("observation-summary.schema.json")
    assert manifest_validator().schema["$id"].endswith("observation-segment-manifest.schema.json")
    for name in ("event", "summary", "manifest"):
        assert len(schema_bytes(name)) > 100
        assert len(schema_digest(name)) == 64


def test_event_schema_rejects_arbitrary_payload_and_extra_fields() -> None:
    f = EventFactory()
    event = f.opened()
    event["payload"] = {"content": "must never survive"}
    with pytest.raises(ValidationError):
        validate_event(event)


def test_event_schema_requires_structured_completion_verification_claim() -> None:
    fixture = EventFactory()
    fixture.opened()
    event = fixture.contract("contract.completion_verified", "verified", 1)

    missing_contract = deepcopy(event)
    missing_contract.pop("contract")
    with pytest.raises(ValidationError):
        validate_event(missing_contract)

    missing_product_identity = deepcopy(event)
    missing_product_identity["actor"].pop("profile")
    missing_product_identity["actor"].pop("role")
    with pytest.raises(ValidationError):
        validate_event(missing_product_identity)

    contradictory_status = deepcopy(event)
    contradictory_status["status"] = "pending"
    with pytest.raises(ValidationError):
        validate_event(contradictory_status)


@pytest.mark.parametrize(
    ("event_type", "valid_status"),
    (
        ("trace.cancelled", "cancelled"),
        ("trace.abandoned", "unknown"),
        ("trace.failed", "failed"),
    ),
)
def test_event_schema_requires_matching_non_success_terminal_status(
    event_type: str, valid_status: str
) -> None:
    fixture = EventFactory()
    fixture.opened()
    event = fixture.contract(event_type, valid_status, 1)
    event["status"] = "completed"

    with pytest.raises(ValidationError):
        validate_event(event)


@pytest.mark.parametrize(
    ("event_type", "valid_status", "contradictory_status"),
    [
        ("invariant.passed", "passed", "failed"),
        ("invariant.failed", "failed", "passed"),
    ],
)
def test_event_schema_requires_invariant_key_and_matching_status(
    event_type: str, valid_status: str, contradictory_status: str
) -> None:
    fixture = EventFactory()
    fixture.opened()
    event = fixture.contract(
        event_type,
        valid_status,
        1,
        invariant_key="OBS-INV-001",
    )

    missing_key = deepcopy(event)
    missing_key["contract"]["invariant_key"] = None
    with pytest.raises(ValidationError):
        validate_event(missing_key)

    contradictory = deepcopy(event)
    contradictory["status"] = contradictory_status
    with pytest.raises(ValidationError):
        validate_event(contradictory)


def test_event_schema_requires_structured_review_approval_claim() -> None:
    fixture = EventFactory()
    event = fixture.unit(
        "review.approved",
        "passed",
        1,
        task_ref="review-unit",
        relation="review",
        actor_id="assigned-reviewer",
        profile="supervisor",
        role="supervision",
    )

    missing_product_identity = deepcopy(event)
    missing_product_identity["actor"]["role"] = None
    with pytest.raises(ValidationError):
        validate_event(missing_product_identity)

    contradictory_status = deepcopy(event)
    contradictory_status["status"] = "failed"
    with pytest.raises(ValidationError):
        validate_event(contradictory_status)


def test_work_unit_projector_preserves_unknown_relation_and_requirement() -> None:
    builder = EventFactory().builder
    event = builder.work_unit(
        event_type="work_unit.bound",
        status="reported",
        task_ref="native-unit",
        relation="unknown",
        required=None,
        binding="bnd_native_unit_0123456789abcdef",
    )
    assert event["work_unit"]["relation"] == "unknown"
    assert event["work_unit"]["required"] is None
    validate_event(event)


def test_work_unit_projector_preserves_protocol_violation_outcome_losslessly() -> None:
    event = EventFactory().builder.work_unit(
        event_type="run.finished",
        status="failed",
        task_ref="native-unit",
        relation="unknown",
        required=None,
        binding="bnd_native_unit_0123456789abcdef",
        run_status="failed",
        run_outcome="protocol_violation",
        run_id=1,
    )
    assert event["work_unit"]["run_outcome"] == "protocol_violation"
    validate_event(event)


@pytest.mark.parametrize(
    "native_outcome",
    ["rate_limited", "stale", "review_requested", "changes_requested", "scheduled"],
)
def test_work_unit_projector_keeps_each_native_run_outcome_distinct(
    native_outcome: str,
) -> None:
    event = EventFactory().builder.work_unit(
        event_type="run.finished",
        status="unknown",
        task_ref="native-unit",
        relation="unknown",
        required=None,
        binding="bnd_native_unit_0123456789abcdef",
        run_status="unknown",
        run_outcome=native_outcome,
        run_id=1,
    )
    assert event["work_unit"]["run_outcome"] == native_outcome
    validate_event(event)


def test_event_validation_rejects_task_envelope_work_unit_mismatch() -> None:
    event = EventFactory().unit(
        "work_unit.bound",
        "reported",
        1,
        task_ref="canonical-task",
        relation="root",
        task_status="running",
    )
    event["task_id"] = "different-task"
    with pytest.raises(ValidationError, match="task_id"):
        validate_event(event)


@pytest.mark.parametrize(
    "payload",
    [
        {"prompt": "synthetic"},
        {"nested": {"args": {"x": 1}}},
        {"api_key": "synthetic"},
        {"safe": "sk-" + "0123456789abcdefghijklmnop"},
        {"safe": "/" + "home/example/private/file"},
        {"safe": b"raw"},
    ],
)
def test_privacy_guard_rejects_content_secret_and_machine_path_shapes(payload: object) -> None:
    with pytest.raises(ForbiddenPayload):
        assert_clean(payload)


def test_privacy_guard_allows_only_closed_summary_invariant_keys() -> None:
    assert_clean({"invariants": [{"key": "OBS-INV-001"}]})
    with pytest.raises(ForbiddenPayload):
        assert_clean({"key": "OBS-INV-001"})
    with pytest.raises(ForbiddenPayload):
        assert_clean({"invariants": [{"key": "api-secret"}]})


def test_privacy_helpers_keep_only_bounded_classes_and_relative_paths() -> None:
    assert safe_error_class("TimeoutError") == "TimeoutError"
    assert safe_error_class("failure: leaked detail with whitespace") is None
    assert (
        relative_artifact_ref("/workspace/project/specs/contract.md", "/workspace/project")
        == "specs/contract.md"
    )
    assert relative_artifact_ref("/" + "home/example/secret.txt") is None
    assert relative_artifact_ref("../other-project/file") is None


def test_locked_hermes_identity_grammar_matches_projector_schema_and_guard() -> None:
    """Strict native identities do not narrow product-owned references globally."""
    assert native_kanban_task_ref("t_deadbeef") == "t_deadbeef"
    assert native_agent_task_ref("t_deadbeef") == "t_deadbeef"
    assert (
        native_agent_task_ref("01234567-89ab-cdef-0123-456789abcdef")
        == "01234567-89ab-cdef-0123-456789abcdef"
    )
    assert native_profile_ref("morfeo") == "morfeo"
    assert native_profile_ref("root") == "root"
    assert native_run_id(1) == 1
    for rejected in ("PRIVATE_RUN_ERROR", "/etc/passwd", "prompt-like raw error"):
        assert native_kanban_task_ref(rejected) is None
    for rejected in ("PROMPT_LIKE_RAW_ERROR", "/etc/passwd", "prompt like"):
        assert native_profile_ref(rejected) is None
    for rejected in (0, -1, True, "1"):
        assert native_run_id(rejected) is None

    builder = EventFactory().builder
    native_event = builder.work_unit(
        event_type="work_unit.bound",
        status="reported",
        task_ref="t_deadbeef",
        relation="unknown",
        required=None,
        binding="bnd_native_unit_0123456789abcdef",
        parent_task_refs=("t_cafebabe",),
        source_kind="native_reconciliation",
        source_hook="kanban_read",
        profile="morfeo",
    )
    validate_event(native_event)
    assert_clean(native_event)

    for path, hostile in (
        (("task_id",), "PRIVATE_RUN_ERROR"),
        (("work_unit", "task_ref"), "/etc/passwd"),
        (("work_unit", "parent_task_refs", 0), "prompt-like raw error"),
        (("actor", "profile"), "PROMPT_LIKE_RAW_ERROR"),
    ):
        candidate = deepcopy(native_event)
        target = candidate
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = hostile
        with pytest.raises(ValidationError):
            validate_event(candidate)
        with pytest.raises(ForbiddenPayload):
            assert_clean(candidate)

    projected = builder.work_unit(
        event_type="work_unit.bound",
        status="reported",
        task_ref="PRIVATE_RUN_ERROR",
        relation="unknown",
        required=None,
        binding="bnd_native_unit_0123456789abcdef",
        parent_task_refs=("/etc/passwd",),
        source_kind="native_reconciliation",
        source_hook="kanban_read",
    )
    assert b"PRIVATE_RUN_ERROR" not in canonical_json_bytes(projected)
    assert b"/etc/passwd" not in canonical_json_bytes(projected)
    with pytest.raises(ValidationError):
        validate_event(projected)

    product_owned = builder.work_unit(
        event_type="work_unit.bound",
        status="reported",
        task_ref="root",
        relation="root",
        required=True,
        binding="bnd_product_unit_0123456789abcdef",
        source_kind="aether_checkpoint",
        source_hook="work_unit_classified",
    )
    validate_event(product_owned)
    assert_clean(product_owned)


def test_native_identity_pseudonyms_match_projector_schema_and_structural_guard() -> None:
    builder = EventFactory().builder
    call_id = native_pseudonym("tool_call", "provider-call")
    session_id = native_pseudonym("session", "supplied-session")
    turn_id = native_pseudonym("turn", "native-turn")
    request_id = native_pseudonym("api_request", "native-request")
    tool = builder.tool_started(
        call_id=call_id,
        name="terminal",
        category="terminal",
        session_id=session_id,
        turn_id=turn_id,
        api_request_id=request_id,
        task_id="t_deadbeef",
        profile="morfeo",
    )
    validate_event(tool)
    assert_clean(tool)

    for path, raw_identity in (
        (("task_id",), "PRIVATE_RUN_ERROR"),
        (("session_id",), "PRIVATE_SESSION_ERROR"),
        (("turn_id",), "PRIVATE_TURN_ERROR"),
        (("api_request_id",), "PRIVATE_API_ERROR"),
        (("tool", "call_id"), "PRIVATE_CALL_ERROR"),
    ):
        candidate = deepcopy(tool)
        target = candidate
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = raw_identity
        with pytest.raises(ValidationError):
            validate_event(candidate)
        with pytest.raises(ForbiddenPayload):
            assert_clean(candidate)

    model = builder.model_request(
        state="started",
        request_ref=request_id,
        session_id=session_id,
        turn_id=turn_id,
        api_request_id=request_id,
        task_id="01234567-89ab-cdef-0123-456789abcdef",
    )
    validate_event(model)
    assert_clean(model)
    model["model_request"]["request_ref"] = "PRIVATE_API_ERROR"
    with pytest.raises(ValidationError):
        validate_event(model)
    with pytest.raises(ForbiddenPayload):
        assert_clean(model)

    retry = builder.tool_terminal(
        call_id=call_id,
        retry_of_call_id=native_pseudonym("tool_call", "provider-call-previous"),
        name="terminal",
        category="terminal",
        status="completed",
        session_id=session_id,
    )
    validate_event(retry)
    retry["tool"]["retry_of_call_id"] = "PRIVATE_RETRY_ERROR"
    with pytest.raises(ValidationError):
        validate_event(retry)
    with pytest.raises(ForbiddenPayload):
        assert_clean(retry)

    participant = builder.build(
        "participant.joined",
        status="started",
        source_hook="subagent_start",
        actor_kind="subagent",
        actor_id=session_id,
        session_id=session_id,
        tool={
            "call_id": session_id,
            "name": "subagent.start",
            "category": "delegation",
            "target_kind": "session",
            "target_ref": native_pseudonym("session", "parent-session"),
        },
    )
    validate_event(participant)
    assert_clean(participant)
    for path in (("actor", "id"), ("tool", "call_id"), ("tool", "target_ref")):
        candidate = deepcopy(participant)
        candidate[path[0]][path[1]] = "PRIVATE_SESSION_ERROR"
        with pytest.raises(ValidationError):
            validate_event(candidate)
        with pytest.raises(ForbiddenPayload):
            assert_clean(candidate)

    configuration = builder.configuration(
        fingerprint_id="0" * 64,
        scope="participant",
        participant_ref=session_id,
        fingerprint_key_id="fpk_" + "0" * 32,
        observer_version="1.0.0",
        field_coverage={"model": "unavailable"},
        source_hook="subagent_start",
        actor_kind="subagent",
        actor_id=session_id,
        session_id=session_id,
    )
    validate_event(configuration)
    assert_clean(configuration)
    configuration["configuration"]["participant_ref"] = "PRIVATE_SESSION_ERROR"
    with pytest.raises(ValidationError):
        validate_event(configuration)
    with pytest.raises(ForbiddenPayload):
        assert_clean(configuration)

    approval = builder.wait(
        started=True,
        wait_id=native_pseudonym("approval_request", "approval-request"),
        kind="approval",
        source_hook="pre_approval_request",
        session_id=session_id,
    )
    validate_event(approval)
    assert_clean(approval)
    approval["wait"]["wait_id"] = "PRIVATE_APPROVAL_ERROR"
    with pytest.raises(ValidationError):
        validate_event(approval)
    with pytest.raises(ForbiddenPayload):
        assert_clean(approval)

    projected = builder.tool_started(
        call_id="PRIVATE_CALL_ERROR",
        name="terminal",
        category="terminal",
        session_id="PRIVATE_SESSION_ERROR",
        turn_id="PRIVATE_TURN_ERROR",
        api_request_id="PRIVATE_API_ERROR",
        task_id="PRIVATE_RUN_ERROR",
    )
    projected_bytes = canonical_json_bytes(projected)
    for raw_identity in (
        b"PRIVATE_CALL_ERROR",
        b"PRIVATE_SESSION_ERROR",
        b"PRIVATE_TURN_ERROR",
        b"PRIVATE_API_ERROR",
        b"PRIVATE_RUN_ERROR",
    ):
        assert raw_identity not in projected_bytes
    with pytest.raises(ValidationError):
        validate_event(projected)

    projected_participant = builder.build(
        "participant.joined",
        status="started",
        source_hook="subagent_start",
        actor_kind="subagent",
        actor_id="PRIVATE_SESSION_ERROR",
        session_id="PRIVATE_SESSION_ERROR",
        tool={
            "call_id": "PRIVATE_SESSION_ERROR",
            "name": "subagent.start",
            "category": "delegation",
            "target_kind": "session",
            "target_ref": "PRIVATE_SESSION_ERROR",
        },
    )
    assert b"PRIVATE_SESSION_ERROR" not in canonical_json_bytes(projected_participant)
    with pytest.raises(ValidationError):
        validate_event(projected_participant)


def _native_reconciliation_without_verifiable_source() -> dict[str, object]:
    """Return a complete native envelope whose raw identities must not persist."""

    builder = EventFactory().builder
    request_id = native_pseudonym("api_request", "native-request")
    event = builder.model_request(
        state="completed",
        request_ref=request_id,
        model="model-a",
        provider="provider-a",
        attempt_count=1,
        occurred_at=BASE,
        session_id=native_pseudonym("session", "native-session"),
        turn_id=native_pseudonym("turn", "native-turn"),
        api_request_id=request_id,
        source_kind="native_reconciliation",
        source_hook="post_api_request",
    )
    event["source_hook"] = None
    raw_native_id = "123e4567-e89b-12d3-a456-426614174000"
    event["session_id"] = raw_native_id
    event["turn_id"] = raw_native_id
    event["api_request_id"] = raw_native_id
    event["model_request"]["request_ref"] = raw_native_id
    return event


def test_schema_rejects_native_reconciliation_without_verifiable_source() -> None:
    with pytest.raises(ValidationError):
        validate_event(_native_reconciliation_without_verifiable_source())


def test_privacy_guard_rejects_native_reconciliation_without_verifiable_source() -> None:
    with pytest.raises(ForbiddenPayload) as rejection:
        assert_clean(_native_reconciliation_without_verifiable_source())

    assert rejection.value.reason_code == "INVALID_NATIVE_SOURCE_PROVENANCE"


def test_error_class_provenance_grammar_matches_schema_guard_and_projector() -> None:
    fixture = EventFactory()
    event = fixture.add(
        fixture.builder.tool_terminal(
            call_id=native_pseudonym("tool_call", "call-1"),
            name="terminal",
            category="terminal",
            status="failed",
            error_class="TimeoutError",
        )
    )
    event["tool"]["error_class"] = "runtime_secret_0123456789abcdef"

    with pytest.raises(ValidationError):
        validate_event(event)
    with pytest.raises(ForbiddenPayload):
        assert_clean(event)


@pytest.mark.parametrize(
    "value",
    [
        "/etc/passwd",
        "prompt body: alice@example.invalid private diagnosis",
        "run command and return output",
        "token=ZXhhbXBsZV9wcml2YXRl",
        "identifier\x1b[31m",
        "identifiеr",  # Cyrillic small e, visually confusable with ASCII.
        "https://example.invalid/private",
        "C:\\Users\\alice\\private.txt",
    ],
)
def test_opaque_reference_projection_rejects_content_paths_controls_and_confusables(
    value: str,
) -> None:
    assert safe_ref(value) is None


@pytest.mark.parametrize(
    "value",
    [
        "reports/../../outside.txt",
        "reports\\..\\outside.txt",
        "/etc/passwd",
        "C:\\Windows\\System32\\drivers\\etc\\hosts",
        "https://example.invalid/evidence",
        "file:///etc/passwd",
        "reports/control\x00.txt",
        "reports/confusablе.txt",
        "reports//empty.txt",
        "./reports/evidence.txt",
    ],
)
def test_artifact_reference_projection_rejects_every_escape_grammar(value: str) -> None:
    assert relative_artifact_ref(value, "/workspace/project") is None


def test_artifact_reference_projection_canonicalizes_only_paths_under_project() -> None:
    assert (
        relative_artifact_ref("/workspace/project/reports/evidence.json", "/workspace/project")
        == "reports/evidence.json"
    )
    assert (
        relative_artifact_ref(
            r"C:\workspace\project\reports\evidence.json", r"C:\workspace\project"
        )
        == "reports/evidence.json"
    )
    assert (
        relative_artifact_ref("/workspace/project-escape/evidence.json", "/workspace/project")
        is None
    )


@pytest.mark.parametrize(
    "payload",
    [
        {
            "source_hook": "post_tool_call",
            "tool": {
                "call_id": "call-1",
                "name": "terminal",
                "args": {"command": "cat /etc/passwd"},
                "result": "PRIVATE_OUTPUT",
                "error_message": "PRIVATE_ERROR",
            },
        },
        {
            "actor": {"id": "prompt body: alice@example.invalid"},
            "contract": {
                "origin_message_id": "prompt body: alice@example.invalid",
                "artifact_ref": "/etc/passwd",
                "evidence_refs": ["reports/../../outside.txt"],
            },
        },
        {"task_id": "task\x1b[2J", "session_id": "sessiоn"},
    ],
)
def test_structural_guard_rejects_complete_malicious_native_payloads(payload: object) -> None:
    with pytest.raises(ForbiddenPayload):
        assert_clean(payload)


def test_privacy_rejection_diagnostic_never_echoes_a_malicious_key_or_value() -> None:
    private_key = "prompt body alice@example.invalid"
    private_value = "PRIVATE_COMMAND_OUTPUT_ERROR"
    with pytest.raises(ForbiddenPayload) as rejected:
        assert_clean({private_key: private_value})
    diagnostic = str(rejected.value)
    assert private_key not in diagnostic
    assert private_value not in diagnostic
    assert diagnostic == "INVALID_METADATA_KEY at $.<field_0>"


def test_projector_never_copies_native_content_via_string_fallback() -> None:
    builder = EventBuilder(
        trace_id=TRACE_ID,
        project_id=PROJECT_ID,
        collector_version="0.24.0",
        runtime_fingerprint="3" * 64,
    )

    contract = builder.contract(
        event_type="contract.persisted",
        status="completed",
        origin_message_id="prompt body: alice@example.invalid private diagnosis",
        artifact_ref="/etc/passwd",
        decision_refs=("decision-1", {"command": "rm -rf /"}),
        evidence_refs=("reports/../../outside.txt", "evidence-1"),
        message_id="prompt body",
    )
    assert contract["message_id"] is None
    assert contract["contract"]["origin_message_id"] is None
    assert contract["contract"]["artifact_ref"] is None
    assert contract["contract"]["decision_refs"] == ["decision-1"]
    assert contract["contract"]["evidence_refs"] == ["evidence-1"]
    validate_event(contract)
    serialized = canonical_json_bytes(contract)
    for forbidden in (b"alice@example.invalid", b"/etc/passwd", b"rm -rf", b"../"):
        assert forbidden not in serialized


def test_normative_schemas_reject_content_in_every_reference_class() -> None:
    factory = EventFactory()
    event = factory.contract(
        "contract.persisted",
        "completed",
        0,
        artifact_ref="specs/contract.md",
        decision_refs=("decision-1",),
        evidence_refs=("evidence-1",),
    )
    mutations = []
    for path, malicious in (
        (("actor", "id"), "prompt body: alice@example.invalid"),
        (("session_id",), "/etc/passwd"),
        (("contract", "origin_message_id"), "prompt body"),
        (("contract", "artifact_ref"), "reports/../../outside.txt"),
        (("contract", "decision_refs", 0), "command output error"),
        (("contract", "evidence_refs", 0), r"C:\\private\\evidence.txt"),
    ):
        candidate = deepcopy(event)
        target = candidate
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = malicious
        mutations.append(candidate)
    for candidate in mutations:
        with pytest.raises(ValidationError):
            validate_event(candidate)

    summary = complete_trace().summary()
    summary["tools"]["by_name"] = [
        {
            "name": "terminal",
            "calls": 0,
            "completed": 0,
            "failed": 0,
            "blocked": 0,
            "cancelled": 0,
            "timed_out": 0,
            "interrupted": 0,
            "unknown": 0,
            "duration_ms": 0,
        }
    ]
    for path, malicious in (
        (("contract_id",), "prompt body: alice@example.invalid"),
        (("work_graph", "units", 0, "task_ref"), "/etc/passwd"),
        (("acceptance", "criteria", 0, "evidence_refs", 0), "../outside"),
        (("participants", 0, "actor_id"), "actor\x1b[31m"),
        (("tools", "by_name", 0, "name"), "terminal output"),
    ):
        candidate = deepcopy(summary)
        target = candidate
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = malicious
        with pytest.raises(ValidationError):
            validate_summary(candidate)

    manifest = {
        "schema_version": "aether.observation.segment-manifest.v1",
        "segment_id": "seg_" + "a" * 64,
        "project_id": PROJECT_ID,
        "producer_epoch": "prd_" + "b" * 32,
        "first_seq": 0,
        "last_seq": 0,
        "event_count": 1,
        "line_count": 1,
        "source_name": f"{'prd_' + 'b' * 32}.0-0.jsonl",
        "archive_name": f"{'prd_' + 'b' * 32}.0-0.jsonl.gz",
        "uncompressed_length": 1,
        "uncompressed_sha256": "c" * 64,
        "compressed_length": 1,
        "compressed_sha256": "d" * 64,
        "event_schema_versions": ["aether.observation.event.v1"],
        "collector_versions": ["prompt body: alice@example.invalid"],
        "runtime_fingerprints": ["e" * 64],
        "compression": {
            "algorithm": "gzip",
            "level": 9,
            "mtime": 0,
            "header_filename": None,
            "header_comment": None,
            "os_byte": 255,
        },
    }
    with pytest.raises(ValidationError):
        validate_manifest(manifest)


def test_reference_grammars_are_identical_at_schema_and_projection_boundaries() -> None:
    event = event_validator().schema
    summary = summary_validator().schema
    manifest = manifest_validator().schema
    assert event["properties"]["normalizer_ref"]["pattern"] == OPAQUE_REF_PATTERN
    assert event["$defs"]["contract"]["properties"]["artifact_ref"]["pattern"] == (
        ARTIFACT_REF_PATTERN
    )
    assert (
        event["$defs"]["contract"]["properties"]["evidence_refs"]["items"]["pattern"]
        == ARTIFACT_REF_PATTERN
    )
    assert event["properties"]["collector_version"]["pattern"] == VERSION_REF_PATTERN
    assert summary["properties"]["reducer_version"]["pattern"] == VERSION_REF_PATTERN
    assert manifest["properties"]["collector_versions"]["items"]["pattern"] == (VERSION_REF_PATTERN)
    assert event["properties"]["message_id"] == {
        "type": ["integer", "null"],
        "minimum": 1,
    }
    assert event["$defs"]["contract"]["properties"]["origin_message_id"] == {
        "type": ["integer", "null"],
        "minimum": 1,
    }


@pytest.mark.parametrize(
    ("native", "expected", "recognized"),
    [
        ("ok", "completed", True),
        ("error", "failed", True),
        ("blocked", "blocked", True),
        ("cancelled", "cancelled", True),
        ("timeout", "timed_out", True),
        ("novel", "unknown", False),
        (None, "unknown", False),
    ],
)
def test_native_statuses_never_fold_non_success_into_success(
    native: object, expected: str, recognized: bool
) -> None:
    assert normalize_native_status(native) == (expected, recognized)


def test_canonical_json_and_content_addressed_summary_identity_are_repeatable() -> None:
    one = {"z": [3, 2, 1], "a": {"b": True}, "summary_id": "ignored"}
    reordered = {"a": {"b": True}, "summary_id": "ignored", "z": [3, 2, 1]}
    different_id = {**reordered, "summary_id": "different"}
    assert canonical_json_bytes(one) == canonical_json_bytes(reordered)
    assert summary_id(one) == summary_id(different_id)


def test_random_and_deterministic_identities_obey_the_closed_formats() -> None:
    assert new_trace_id().startswith("ctr_") and len(new_trace_id()) == 36
    assert new_producer_epoch().startswith("prd_") and len(new_producer_epoch()) == 36
    assert new_event_id().startswith("evt_") and len(new_event_id()) == 36
    identity = native_identity(kind="tool", session="s", call="c")
    assert identity is not None
    assert deterministic_event_id(identity) == deterministic_event_id(dict(identity))
    assert len(deterministic_event_id(identity)) == 68
    assert native_identity(kind="tool", session=None, call="c") is None


@pytest.mark.parametrize(
    "malicious",
    [
        "/etc/passwd",
        "prompt body: alice@example.invalid",
        "command output error",
        "call\x00id",
        "call-іd",
        {"command": "cat /etc/passwd"},
    ],
)
def test_native_identity_never_hashes_content_as_an_opaque_identifier(malicious: object) -> None:
    assert native_identity(kind="tool", session="safe-session", call=malicious) is None


def test_producer_sequences_restart_per_epoch_and_never_reissue_after_resume() -> None:
    first = ProducerSequence("prd_" + "1" * 32)
    assert [first.allocate(), first.allocate()] == [0, 1]
    first.resume_after(7)
    assert first.allocate() == 8
    restarted = ProducerSequence("prd_" + "2" * 32)
    assert restarted.allocate() == 0


def test_strict_correlation_token_accepts_only_opaque_aether_shape() -> None:
    token = correlation_token(TRACE_ID, "unit-1")
    assert parse_correlation_token(token) == (TRACE_ID, "unit-1")
    assert parse_correlation_token("ordinary-idempotency-key") is None
    assert parse_correlation_token(token + ":extra") is None
    with pytest.raises(ValueError):
        correlation_token("contains:delimiter", "unit")
    with pytest.raises(ValueError):
        correlation_token("trace-without-typed-prefix", "unit")
    with pytest.raises(ValueError):
        correlation_token(TRACE_ID, "prompt body: alice@example.invalid")
    assert parse_correlation_token("aether.obs.v1:trace-without-typed-prefix:unit") is None


def test_owner_origin_selection_exact_single_zero_and_multiple() -> None:
    candidates = OwnerMessageCandidates()
    candidates.observe("session-a", 10, BASE)
    assert candidates.select(exact_message_id=10, session_lineage=("session-a",)).started_at == BASE
    assert candidates.select(session_lineage=("missing",)).reason_code == "ORIGIN_NO_CANDIDATE"
    candidates.observe("session-b", 11, BASE + timedelta(seconds=1))
    selection = candidates.select(session_lineage=("session-a", "session-b"))
    assert selection.candidate is None
    assert selection.reason_code == "ORIGIN_MULTIPLE_CANDIDATES"


def test_owner_candidate_lru_and_ttl_are_bounded() -> None:
    candidates = OwnerMessageCandidates(max_sessions=1, ttl=timedelta(seconds=1))
    candidates.observe("a", 1, BASE)
    candidates.observe("b", 2, BASE)
    assert len(candidates) == 1 and candidates.evictions == 1
    candidates.expire(BASE + timedelta(seconds=2))
    assert len(candidates) == 0 and candidates.expirations == 1


def test_owner_origin_accepts_only_native_positive_integer_message_ids() -> None:
    candidates = OwnerMessageCandidates()
    candidates.observe("session-safe", "prompt body: alice@example.invalid", BASE)
    candidates.observe("session-control", "7\x1b[31m", BASE)
    candidates.observe("session-negative", -1, BASE)
    assert len(candidates) == 0

    candidates.observe("session-safe", 7, BASE)
    assert candidates.peek("session-safe").message_id == 7
    assert (
        candidates.select(
            exact_message_id="prompt body", session_lineage=("session-safe",)
        ).candidate
        is None
    )


def test_work_graph_root_and_descendant_binding_refuse_ambiguity() -> None:
    binder = WorkGraphBinder(PROJECT_ID)
    token = correlation_token(TRACE_ID, "root-unit")
    root = binder.bind_root(trace_id=TRACE_ID, task_ref="task-root", token=token)
    assert root.bound and binder.trace_for("task-root") == TRACE_ID
    child = binder.inherit(task_ref="task-child", parent_task_refs=("task-root",))
    assert child.bound and child.parent_task_refs == ("task-root",)
    unrelated = binder.inherit(task_ref="task-other", parent_task_refs=("unknown",))
    assert not unrelated.bound and unrelated.reason_code == "BINDING_PARENT_UNBOUND"
    mismatch = binder.bind_root(
        trace_id=TRACE_ID,
        task_ref="cross",
        token=token,
        project_id="22222222-2222-4222-8222-222222222222",
    )
    assert not mismatch.bound and mismatch.reason_code == "BINDING_CROSS_PROJECT"


def test_work_graph_never_retains_malicious_native_identifiers() -> None:
    binder = WorkGraphBinder(PROJECT_ID)
    result = binder.bind_root(
        trace_id=TRACE_ID,
        task_ref="prompt body: alice@example.invalid",
    )
    assert not result.bound
    assert result.task_ref is None
    assert binder.trace_for("prompt body: alice@example.invalid") is None

    root = binder.bind_root(trace_id=TRACE_ID, task_ref="safe-root")
    assert root.bound
    child = binder.inherit(
        task_ref="safe-child",
        parent_task_refs=("safe-root", "reports/../../outside"),
    )
    assert not child.bound
    assert "reports/../../outside" not in child.parent_task_refs


def _registered_project(tmp_path, project_id: str = PROJECT_ID):
    state = tmp_path / "state"
    project = tmp_path / "project"
    marker = project / ".aether" / "project.toml"
    marker.parent.mkdir(parents=True)
    marker.write_text(project_marker(project_id), encoding="utf-8")
    registry = ProjectRegistry(state)
    assert registry.register(project_id, project, "fixture")
    return state, project, registry


def test_project_resolution_requires_verified_sources_and_detects_conflicts(tmp_path) -> None:
    state, _, registry = _registered_project(tmp_path)
    second = "22222222-2222-4222-8222-222222222222"
    project2 = tmp_path / "project2"
    (project2 / ".aether").mkdir(parents=True)
    (project2 / ".aether" / "project.toml").write_text(project_marker(second), encoding="utf-8")
    assert registry.register(second, project2, "fixture2")
    health = HealthCounters(state)
    resolver = ObservationContextResolver(registry=registry, health=health)
    assert resolver.resolve(task_binding=PROJECT_ID).project_id == PROJECT_ID
    assert resolver.resolve(launch_binding=PROJECT_ID).source == "launch_binding"
    conflict = resolver.resolve(task_binding=PROJECT_ID, session_binding=second)
    assert conflict.status == "conflict" and conflict.project_id is None
    unresolved = resolver.resolve(launch_binding="33333333-3333-4333-8333-333333333333")
    assert unresolved.status == "unresolved"
    assert health.read()["PROJECT_CONFLICT"] == 1


@pytest.mark.skipif(os.name != "posix", reason="POSIX dirfd/no-follow confinement")
def test_project_registry_temp_symlink_never_overwrites_external_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    state = tmp_path / "state"
    project = tmp_path / "project"
    project.mkdir()
    registry = ProjectRegistry(state)
    ensure_private_dir(registry.path.parent)
    external = tmp_path / "external-registry-user-file"
    external_bytes = b"registry external bytes must remain intact\n"
    external.write_bytes(external_bytes)
    before = external.stat()
    temporary = registry.path.parent / "registry.deadbeef.tmp"
    temporary.symlink_to(external)
    monkeypatch.setattr(secrets, "token_hex", lambda _count: "deadbeef")

    with pytest.raises(UnsafeObservationPath) as rejected:
        registry.register(PROJECT_ID, project, "fixture")

    after = external.stat()
    assert external.read_bytes() == external_bytes
    assert (after.st_dev, after.st_ino) == (before.st_dev, before.st_ino)
    assert external_bytes.decode().strip() not in str(rejected.value)
    assert temporary.is_symlink()
    assert not registry.path.exists()

    temporary.unlink()
    assert registry.register(PROJECT_ID, project, "fixture")
    assert registry.knows(PROJECT_ID)
    assert external.read_bytes() == external_bytes


@pytest.mark.skipif(os.name != "posix", reason="POSIX component-wise no-follow confinement")
def test_registry_write_rejects_state_ancestor_swapped_after_directory_check(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    state = tmp_path / "state"
    detached_state = tmp_path / "detached-state"
    external_state = tmp_path / "external-state"
    external_registry = external_state / "projects" / "registry.json"
    external_registry.parent.mkdir(parents=True)
    external_bytes = b"external registry bytes must not change\n"
    external_registry.write_bytes(external_bytes)
    project = tmp_path / "project"
    project.mkdir()
    registry = ProjectRegistry(state)
    ensure_private_dir(registry.path.parent)

    original_ensure = paths_module.ensure_private_dir
    swapped = False

    def ensure_then_swap(path: Path) -> Path:
        nonlocal swapped
        result = original_ensure(path)
        if Path(path) == registry.path.parent and not swapped:
            state.rename(detached_state)
            state.symlink_to(external_state, target_is_directory=True)
            swapped = True
        return result

    monkeypatch.setattr(paths_module, "ensure_private_dir", ensure_then_swap)

    with pytest.raises(UnsafeObservationPath):
        registry.register(PROJECT_ID, project, "must-not-persist")

    assert swapped
    assert external_registry.read_bytes() == external_bytes
    assert not (external_state / "projects" / "registry.deadbeef.tmp").exists()


@pytest.mark.skipif(os.name != "posix", reason="POSIX dirfd/no-follow confinement")
def test_health_counter_temp_symlink_is_fail_open_and_never_overwrites_external_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    health = HealthCounters(tmp_path / "state")
    ensure_private_dir(health.path.parent)
    external = tmp_path / "external-health-user-file"
    external_bytes = b"health external bytes must remain intact\n"
    external.write_bytes(external_bytes)
    before = external.stat()
    temporary = health.path.parent / "counters.deadbeef.tmp"
    temporary.symlink_to(external)
    monkeypatch.setattr(secrets, "token_hex", lambda _count: "deadbeef")

    error: Exception | None = None
    try:
        health.increment("SYNTHETIC_HEALTH")
    except Exception as exc:  # pragma: no branch - assert the documented never-raises API
        error = exc

    assert error is None, f"{type(error).__name__}: {error}"
    after = external.stat()
    assert external.read_bytes() == external_bytes
    assert (after.st_dev, after.st_ino) == (before.st_dev, before.st_ino)
    assert temporary.is_symlink()
    assert not health.path.exists()

    temporary.unlink()
    health.increment("SYNTHETIC_HEALTH")
    assert health.read() == {"SYNTHETIC_HEALTH": 1}
    assert external.read_bytes() == external_bytes


def _install_external_alias(alias: Path, external: Path, link_kind: str) -> None:
    if link_kind == "symlink":
        alias.symlink_to(external)
    else:
        os.link(external, alias)


@pytest.mark.skipif(os.name != "posix", reason="POSIX no-follow/link-count confinement")
@pytest.mark.parametrize("link_kind", ("symlink", "hardlink"))
def test_registry_and_health_reads_reject_external_state_aliases(
    link_kind: str, tmp_path: Path
) -> None:
    state = tmp_path / "state"
    project = tmp_path / "project"
    project.mkdir()
    registry = ProjectRegistry(state)
    ensure_private_dir(registry.path.parent)
    registry_external = tmp_path / f"external-registry-{link_kind}"
    registry_bytes = json.dumps(
        {
            "schema_version": 1,
            "projects": {PROJECT_ID: {"path": str(project), "name": "external-authority"}},
        }
    ).encode("utf-8")
    registry_external.write_bytes(registry_bytes)
    _install_external_alias(registry.path, registry_external, link_kind)

    health = HealthCounters(state)
    ensure_private_dir(health.path.parent)
    health_external = tmp_path / f"external-health-{link_kind}"
    health_bytes = b'{"EXTERNAL_HEALTH": 999}'
    health_external.write_bytes(health_bytes)
    _install_external_alias(health.path, health_external, link_kind)

    assert not registry.knows(PROJECT_ID)
    assert registry.project_path(PROJECT_ID) is None
    assert health.read() == {}
    assert registry_external.read_bytes() == registry_bytes
    assert health_external.read_bytes() == health_bytes


@pytest.mark.skipif(os.name != "posix", reason="POSIX component-wise no-follow confinement")
def test_registry_read_rejects_symlinked_state_ancestor(tmp_path: Path) -> None:
    state = tmp_path / "state"
    project = tmp_path / "project"
    project.mkdir()
    registry = ProjectRegistry(state)
    assert registry.register(PROJECT_ID, project, "original-authority")

    external_state = tmp_path / "external-state"
    state.rename(external_state)
    state.symlink_to(external_state, target_is_directory=True)
    external_bytes = (external_state / "projects" / "registry.json").read_bytes()

    assert not registry.knows(PROJECT_ID)
    assert registry.project_path(PROJECT_ID) is None
    assert (external_state / "projects" / "registry.json").read_bytes() == external_bytes


@pytest.mark.skipif(os.name != "posix", reason="POSIX no-follow/link-count confinement")
@pytest.mark.parametrize("link_kind", ("symlink", "hardlink"))
def test_fingerprint_pointer_read_rejects_external_alias_and_starts_lost_epoch(
    link_kind: str, tmp_path: Path
) -> None:
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path / "state")
    ensure_private_dir(paths.keys)
    seeded_key = b"p" * 32
    seeded_key_id = fingerprint_key_id(seeded_key)
    atomic_private_write(paths.key_file(seeded_key_id), seeded_key)
    external = tmp_path / f"external-key-pointer-{link_kind}"
    external_bytes = (seeded_key_id + "\n").encode("utf-8")
    external.write_bytes(external_bytes)
    _install_external_alias(paths.key_pointer, external, link_kind)

    keyring = FingerprintKeyring(paths)
    recovered_key_id = keyring.load_or_create()

    assert recovered_key_id != seeded_key_id
    assert keyring.last_change is not None
    assert keyring.last_change.reason == "key_lost"
    assert external.read_bytes() == external_bytes
    assert not paths.key_pointer.is_symlink()


@pytest.mark.skipif(os.name != "posix", reason="POSIX no-follow/link-count confinement")
@pytest.mark.parametrize("link_kind", ("symlink", "hardlink"))
def test_fingerprint_key_read_rejects_external_alias_and_rotates_lost_epoch(
    link_kind: str, tmp_path: Path
) -> None:
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path / "state")
    ensure_private_dir(paths.keys)
    external_key = b"k" * 32
    external_key_id = fingerprint_key_id(external_key)
    atomic_private_write(paths.key_pointer, (external_key_id + "\n").encode("utf-8"))
    external = tmp_path / f"external-key-material-{link_kind}"
    external.write_bytes(external_key)
    _install_external_alias(paths.key_file(external_key_id), external, link_kind)

    keyring = FingerprintKeyring(paths)
    recovered_key_id = keyring.load_or_create()

    assert recovered_key_id != external_key_id
    assert keyring.last_change is not None
    assert keyring.last_change.reason == "key_lost"
    assert keyring.last_change.previous_key_id == external_key_id
    assert external.read_bytes() == external_key


@pytest.mark.skipif(os.name != "posix", reason="POSIX no-follow/link-count confinement")
@pytest.mark.parametrize("link_kind", ("symlink", "hardlink"))
def test_previous_summary_read_rejects_external_alias(link_kind: str, tmp_path: Path) -> None:
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path / "state")
    ensure_private_dir(paths.summaries)
    summary = complete_trace().summary()
    summary_ref = summary["summary_id"]
    external = tmp_path / f"external-summary-{link_kind}"
    external_bytes = canonical_json_bytes(summary)
    external.write_bytes(external_bytes)
    alias = paths.summary_file(summary_ref)
    _install_external_alias(alias, external, link_kind)

    with pytest.raises(query.StateUnreadableError) as rejected:
        query.load_previous_summary(paths, summary_ref)

    assert str(external) not in str(rejected.value)
    assert external.read_bytes() == external_bytes


def test_project_paths_reject_noncanonical_and_traversal_components(tmp_path) -> None:
    with pytest.raises(ValueError):
        ObservationPaths.for_project("../escape", root=tmp_path)
    with pytest.raises(ValueError):
        ObservationPaths.for_project("AAAAAAAA-AAAA-4AAA-8AAA-AAAAAAAAAAAA", root=tmp_path)
    assert ObservationPaths.for_project(PROJECT_ID, root=tmp_path).project_id == PROJECT_ID
    assert canonical_project_id(PROJECT_ID.upper()) == PROJECT_ID


def test_relative_xdg_state_home_is_never_resolved_from_cwd(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("XDG_STATE_HOME", "relative/state")
    with pytest.raises(ValueError):
        state_root()
    assert not (tmp_path / "relative" / "state" / "aether").exists()


def test_tilde_xdg_state_home_is_rejected_before_expanduser(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("XDG_STATE_HOME", "~/relative-state")
    with pytest.raises(ValueError, match="XDG_STATE_HOME must be absolute"):
        state_root()
    assert not (tmp_path / "home" / "relative-state" / "aether").exists()


@pytest.mark.parametrize(
    ("method", "value"),
    [
        ("lock_file", "../../outside"),
        ("lock_file", "prd_" + "a" * 31 + "/"),
        ("key_file", "../fpk_" + "a" * 32),
        ("key_file", "fpk_" + "A" * 32),
        ("projection_db", "../../outside_projection"),
        ("projection_db", r"..\\outside_projection"),
        ("summary_file", "../../outside_summary"),
    ],
)
def test_every_dynamic_observation_path_component_has_a_closed_grammar(
    tmp_path, method: str, value: str
) -> None:
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path)
    with pytest.raises(ValueError):
        getattr(paths, method)(value)


def test_valid_dynamic_observation_paths_are_confined_and_sidecars_are_explicit(tmp_path) -> None:
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path)
    epoch = "prd_" + "a" * 32
    key_id = "fpk_" + "b" * 32
    schema = "aether.observation.projection.v1"
    summary = "sum_" + "c" * 64
    assert paths.lock_file(epoch).parent == paths.locks
    assert paths.key_file(key_id).parent == paths.keys
    assert paths.summary_file(summary).parent == paths.summaries
    assert paths.projection_files(schema) == (
        paths.projection_db(schema),
        paths.projection_db(schema).with_name(paths.projection_db(schema).name + "-wal"),
        paths.projection_db(schema).with_name(paths.projection_db(schema).name + "-shm"),
    )


@pytest.mark.skipif(os.name != "posix", reason="POSIX resolved-path confinement")
def test_dynamic_child_rejects_parent_symlink_resolving_outside_state_root(tmp_path) -> None:
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path / "state").ensure()
    outside = tmp_path / "outside"
    outside.mkdir()
    paths.projections.rmdir()
    paths.projections.symlink_to(outside, target_is_directory=True)

    with pytest.raises(ValueError):
        paths.projection_db("aether.observation.projection.v1")
    assert list(outside.iterdir()) == []


@pytest.mark.skipif(os.name != "posix", reason="POSIX private-file modes")
def test_projection_db_and_every_sqlite_sidecar_are_hardened_together(tmp_path) -> None:
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path).ensure()
    schema = "aether.observation.projection.v1"
    for candidate in paths.projection_files(schema):
        candidate.write_bytes(b"bounded")
        candidate.chmod(0o644)

    paths.harden_projection_files(schema)

    assert {
        stat.S_IMODE(candidate.stat().st_mode) for candidate in paths.projection_files(schema)
    } == {0o600}


@pytest.mark.skipif(os.name != "posix", reason="POSIX symlink confinement")
def test_private_directory_creation_rejects_preexisting_symlink_escape(tmp_path) -> None:
    root = tmp_path / "state"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    (root / "observations").symlink_to(outside, target_is_directory=True)
    paths = ObservationPaths.for_project(PROJECT_ID, root=root)
    with pytest.raises(ValueError):
        paths.ensure()
    assert not (outside / "projects").exists()


@pytest.mark.skipif(os.name != "posix", reason="POSIX inode confinement")
def test_private_file_hardening_rejects_symlinks_and_multiply_linked_files(tmp_path) -> None:
    private = tmp_path / "private"
    private.write_text("bounded", encoding="utf-8")
    hardlink = tmp_path / "hardlink"
    os.link(private, hardlink)
    with pytest.raises(ValueError):
        harden_file(hardlink)

    target = tmp_path / "target"
    target.write_text("outside", encoding="utf-8")
    symlink = tmp_path / "symlink"
    symlink.symlink_to(target)
    before = stat.S_IMODE(target.stat().st_mode)
    with pytest.raises(ValueError):
        harden_file(symlink)
    assert stat.S_IMODE(target.stat().st_mode) == before


@pytest.mark.skipif(os.name != "posix", reason="POSIX no-follow directory primitive")
def test_private_directory_helper_rejects_symlink_leaf(tmp_path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    symlink = tmp_path / "leaf"
    symlink.symlink_to(target, target_is_directory=True)
    with pytest.raises(ValueError):
        ensure_private_dir(symlink)


@pytest.mark.skipif(os.name != "posix", reason="POSIX no-follow directory primitive")
def test_private_directory_helper_rejects_symlink_swap_at_open(monkeypatch, tmp_path) -> None:
    parent = tmp_path / "parent"
    outside = tmp_path / "outside"
    parent.mkdir()
    outside.mkdir()
    real_open = os.open
    swapped = False

    def swap_then_open(path, flags, *args, dir_fd=None, **kwargs):
        nonlocal swapped
        if path == "leaf" and dir_fd is not None and not swapped:
            swapped = True
            (parent / "leaf").rmdir()
            (parent / "leaf").symlink_to(outside, target_is_directory=True)
        return real_open(path, flags, *args, dir_fd=dir_fd, **kwargs)

    monkeypatch.setattr(os, "open", swap_then_open)
    with pytest.raises(ValueError):
        ensure_private_dir(parent / "leaf")
    assert swapped
    assert list(outside.iterdir()) == []


@pytest.mark.skipif(os.name != "posix", reason="POSIX inode confinement")
def test_private_file_hardening_detects_name_swap_after_secure_open(monkeypatch, tmp_path) -> None:
    victim = tmp_path / "victim"
    held = tmp_path / "held"
    outside = tmp_path / "outside"
    victim.write_text("private", encoding="utf-8")
    outside.write_text("outside", encoding="utf-8")
    outside.chmod(0o644)
    before = stat.S_IMODE(outside.stat().st_mode)
    real_stat = os.stat
    swapped = False

    def swap_then_stat(path, *args, follow_symlinks=True, **kwargs):
        nonlocal swapped
        if Path(path) == victim and follow_symlinks is False and not swapped:
            swapped = True
            victim.rename(held)
            victim.symlink_to(outside)
        return real_stat(path, *args, follow_symlinks=follow_symlinks, **kwargs)

    monkeypatch.setattr(os, "stat", swap_then_stat)
    with pytest.raises(ValueError):
        harden_file(victim)
    assert swapped
    assert stat.S_IMODE(real_stat(outside).st_mode) == before


@pytest.mark.skipif(os.name != "posix", reason="POSIX directory durability boundary")
def test_atomic_private_write_fsyncs_file_and_directory_before_return(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    target = tmp_path / "private" / "current"
    fsync_kinds: list[str] = []
    real_fsync = os.fsync

    def record_fsync(descriptor: int) -> None:
        mode = os.fstat(descriptor).st_mode
        fsync_kinds.append("directory" if stat.S_ISDIR(mode) else "file")
        real_fsync(descriptor)

    monkeypatch.setattr("aether_agents.paths.os.fsync", record_fsync)
    atomic_private_write(target, b"fpk_00000000000000000000000000000000\n")

    assert target.read_bytes() == b"fpk_00000000000000000000000000000000\n"
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    assert fsync_kinds == ["file", "directory"]
    assert not list(target.parent.glob("*.tmp"))


def test_keyed_fingerprints_are_field_and_key_epoch_separated(tmp_path) -> None:
    value = ["tool-a", "tool-b"]
    assert keyed_fingerprint(b"a" * 32, "declared_toolset", value) != keyed_fingerprint(
        b"a" * 32, "observed_skill_set", value
    )
    assert keyed_fingerprint(b"a" * 32, "declared_toolset", value) != keyed_fingerprint(
        b"b" * 32, "declared_toolset", value
    )
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path)
    keyring = FingerprintKeyring(paths)
    first = keyring.load_or_create()
    rotation = keyring.rotate()
    assert rotation.previous_key_id == first and rotation.key_id != first
    if os.name == "posix":
        assert stat.S_IMODE(paths.key_file(first).stat().st_mode) == 0o600
        assert stat.S_IMODE(paths.key_file(rotation.key_id).stat().st_mode) == 0o600


@pytest.mark.skipif(os.name != "posix", reason="POSIX dirfd/no-follow confinement")
def test_fingerprint_pointer_temp_symlink_never_overwrites_external_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path / "state")
    ensure_private_dir(paths.keys)
    external = tmp_path / "external-user-file"
    external_bytes = b"external user bytes must remain intact\n"
    external.write_bytes(external_bytes)
    external.chmod(0o640)
    before = external.stat()
    temporary = paths.keys / "current.deadbeef.tmp"
    temporary.symlink_to(external)
    monkeypatch.setattr(secrets, "token_hex", lambda _count: "deadbeef")

    keyring = FingerprintKeyring(paths)
    with pytest.raises(UnsafeObservationPath) as rejected:
        keyring.load_or_create()

    after = external.stat()
    assert external.read_bytes() == external_bytes
    assert (after.st_dev, after.st_ino, stat.S_IMODE(after.st_mode)) == (
        before.st_dev,
        before.st_ino,
        stat.S_IMODE(before.st_mode),
    )
    assert external_bytes.decode().strip() not in str(rejected.value)
    assert temporary.is_symlink()
    assert not paths.key_pointer.exists()

    temporary.unlink()
    key_id = keyring.load_or_create()
    assert paths.key_pointer.read_text(encoding="utf-8") == key_id + "\n"
    assert external.read_bytes() == external_bytes


def test_key_loss_and_rotation_materialize_one_explicit_coverage_boundary(tmp_path) -> None:
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path)
    initial = FingerprintKeyring(paths)
    lost_key_id = initial.load_or_create()
    paths.key_file(lost_key_id).unlink()
    recovered = FingerprintKeyring(paths)
    recovered_key_id = recovered.load_or_create()
    assert recovered_key_id != lost_key_id
    assert recovered.last_change is not None
    assert recovered.last_change.reason == "key_lost"
    assert recovered.last_change.previous_key_id == lost_key_id

    collector = Collector(paths=paths, runtime_fingerprint="3" * 64)
    collector.keyring = recovered
    collector.start()
    try:
        collector.record_fingerprint_epoch_boundary(TRACE_ID)
        collector.record_fingerprint_epoch_boundary(TRACE_ID)
        rotation = collector.keyring.rotate()
        raw_rotated_key = paths.key_file(rotation.key_id).read_bytes()
        collector.record_fingerprint_epoch_boundary(TRACE_ID)
        collector.record_fingerprint_epoch_boundary(TRACE_ID)
    finally:
        collector.stop()
    events = [
        json.loads(line)
        for segment in paths.closed.iterdir()
        for line in segment.read_text(encoding="utf-8").splitlines()
    ]
    reasons = [
        (event.get("coverage") or {}).get("reason_code")
        for event in events
        if event.get("event_type") == "coverage.gap"
    ]
    assert reasons.count("FINGERPRINT_KEY_LOST") == 1
    assert reasons.count("FINGERPRINT_KEY_ROTATED") == 1
    journal_bytes = b"".join(segment.read_bytes() for segment in paths.closed.iterdir())
    assert raw_rotated_key not in journal_bytes
    assert raw_rotated_key.hex().encode() not in journal_bytes


def test_key_bytes_never_enter_summary_or_event_payload(tmp_path) -> None:
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path)
    keyring = FingerprintKeyring(paths)
    key_id = keyring.load_or_create()
    raw_key = paths.key_file(key_id).read_bytes()
    summary = complete_trace().summary()
    serialized = canonical_json_bytes(summary)
    assert raw_key not in serialized
    assert raw_key.hex().encode() not in serialized


def test_checkpoint_rejects_unknown_reference_without_persisting_it(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path)
    collector = Collector(paths=paths, runtime_fingerprint="3" * 64)
    collector.start()
    try:
        monkeypatch.setattr(
            checkpoint_module,
            "authority_context_from_state_root",
            lambda _root: AuthorityContext.product_default(),
        )
        sink = CheckpointSink(collector)
        result = sink.emit(
            "contract_persisted", trace_id=TRACE_ID, arbitrary_metadata="synthetic-private"
        )
        assert not result.accepted
        assert result.reason_code == "CHECKPOINT_REFERENCE_UNKNOWN"
    finally:
        collector.stop()
    journal = b"".join(path.read_bytes() for path in paths.closed.iterdir())
    assert b"synthetic-private" not in journal


def test_checkpoint_constructor_rejects_caller_selected_authority(tmp_path: Path) -> None:
    """A caller cannot turn strings or an injected context into Morfeo authority."""
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path)
    collector = Collector(paths=paths, runtime_fingerprint="3" * 64)

    with pytest.raises(TypeError):
        CheckpointSink(
            collector,
            profile="morfeo",
            role="verification",
            actor_id="morfeo",
            authority_context=AuthorityContext.product_default(),
        )


def test_checkpoint_without_active_product_authority_rejects_forged_role(
    tmp_path,
) -> None:
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path)
    collector = Collector(paths=paths, runtime_fingerprint="3" * 64)
    collector.start()
    try:
        sink = CheckpointSink(collector)
        result = sink.emit(
            "contract_completion_verified",
            trace_id=TRACE_ID,
            contract_id="ctr_0123456789abcdef0123456789abcdef",
        )
        assert not result.accepted
        assert result.reason_code == "CHECKPOINT_AUTHORITY_UNVERIFIED"
    finally:
        collector.stop()

    events = [
        json.loads(line)
        for segment in paths.closed.iterdir()
        for line in segment.read_text(encoding="utf-8").splitlines()
    ]
    assert not any(event["event_type"] == "contract.completion_verified" for event in events)


def test_product_checkpoint_can_classify_a_required_unit_without_native_inference(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path)
    native = EventFactory().unit(
        "work_unit.bound",
        "reported",
        1,
        task_ref="root",
        relation="unknown",
        required=None,
        actor_id="supervisor",
        profile="supervisor",
    )
    native_collector = Collector(paths=paths, runtime_fingerprint="3" * 64)
    native_collector.start()
    try:
        assert native_collector.emit(native).accepted
    finally:
        native_collector.stop()

    collector = Collector(paths=paths, runtime_fingerprint="3" * 64)
    collector.start()
    try:
        monkeypatch.setattr(
            checkpoint_module,
            "authority_context_from_state_root",
            lambda _root: AuthorityContext.product_default(),
        )
        result = CheckpointSink(collector).emit(
            "work_unit_classified",
            trace_id=TRACE_ID,
            task_ref="root",
            relation="root",
            required=True,
            binding_ref="bnd_root_0123456789abcdef",
            task_status="running",
        )
        assert result.accepted
    finally:
        collector.stop()

    events = [
        json.loads(line)
        for segment in paths.closed.iterdir()
        for line in segment.read_text(encoding="utf-8").splitlines()
    ]
    classified = next(
        event
        for event in events
        if event["event_type"] == "work_unit.bound" and event["source_kind"] == "aether_checkpoint"
    )
    assert classified["source_kind"] == "aether_checkpoint"
    assert classified["parent_event_id"] == native["event_id"]
    assert classified["work_unit"]["relation"] == "root"
    assert classified["work_unit"]["required"] is True


def test_product_checkpoint_rejects_unknown_work_unit_classification(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path)
    collector = Collector(paths=paths, runtime_fingerprint="3" * 64)
    collector.start()
    try:
        monkeypatch.setattr(
            checkpoint_module,
            "authority_context_from_state_root",
            lambda _root: AuthorityContext.product_default(),
        )
        result = CheckpointSink(collector).emit(
            "work_unit_classified",
            trace_id=TRACE_ID,
            task_ref="review-unit",
            relation="unknown",
            required=True,
            binding_ref="bnd_review_unit_0123456789abcdef",
        )
        assert not result.accepted
        assert result.reason_code == "CHECKPOINT_REFERENCE_INVALID"
    finally:
        collector.stop()


def test_checkpoint_never_stringifies_untyped_native_reference(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class StringificationTrap:
        calls = 0

        def __str__(self) -> str:
            self.calls += 1
            return "/etc/passwd"

    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path)
    collector = Collector(paths=paths, runtime_fingerprint="3" * 64)
    collector.start()
    trap = StringificationTrap()
    try:
        monkeypatch.setattr(
            checkpoint_module,
            "authority_context_from_state_root",
            lambda _root: AuthorityContext.product_default(),
        )
        sink = CheckpointSink(collector)
        result = sink.emit(
            "contract_persisted",
            trace_id=TRACE_ID,
            artifact_ref=trap,
        )
        assert not result.accepted
        assert result.reason_code == "INVALID_ARTIFACT_REFERENCE"
        assert trap.calls == 0
    finally:
        collector.stop()


def test_checkpoint_reentrancy_fails_open_and_creates_no_nested_span(tmp_path) -> None:
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path)
    collector = Collector(paths=paths, runtime_fingerprint="3" * 64)
    collector.start()
    try:
        sink = CheckpointSink(collector)
        with reentrancy_guard() as entered:
            assert entered
            result = sink.emit("trace_closed", trace_id=TRACE_ID)
        assert not result.accepted and result.reason_code == "REENTRANT"
    finally:
        collector.stop()
