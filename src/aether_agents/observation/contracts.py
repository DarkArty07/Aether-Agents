"""Hermes-independent typed contracts for Aether Contract Observation.

This module owns the vocabulary and the canonical serialization that every other
observation module shares: schema identity, bounded enumerations, canonical JSON,
the runtime compatibility fingerprint, and the native-status normalization boundary.

Import boundary (``specs/001-aether-v1-productization/plan.md`` section 5): this module
MUST NOT import Hermes. The adapter in :mod:`aether_agents.observation.capture.hermes_plugin`
resolves native normalizers and passes their results in.
"""

from __future__ import annotations

import hashlib
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Final

from aether_agents import product_version

__all__ = [
    "COLLECTOR_VERSION",
    "EVENT_SCHEMA_VERSION",
    "EVENT_TYPES",
    "MANIFEST_SCHEMA_VERSION",
    "MAX_EVENT_LINE_BYTES",
    "ARTIFACT_REF_PATTERN",
    "OPAQUE_REF_PATTERN",
    "READ_MODEL_SCHEMA",
    "REDUCER_VERSION",
    "RUNTIME_FINGERPRINT_FILES",
    "SUMMARY_SCHEMA_VERSION",
    "SUPPORTED_EVENT_SCHEMA_VERSIONS",
    "VERSION_REF_PATTERN",
    "CoverageClass",
    "canonical_json_bytes",
    "canonical_json_str",
    "compute_runtime_fingerprint",
    "event_validator",
    "manifest_validator",
    "is_artifact_ref",
    "is_native_message_id",
    "is_opaque_ref",
    "is_version_ref",
    "normalize_native_status",
    "schema_bytes",
    "schema_digest",
    "schema_path",
    "summary_validator",
    "validate_event",
    "validate_manifest",
    "validate_summary",
]

# --------------------------------------------------------------------------------------
# Schema identity
# --------------------------------------------------------------------------------------

EVENT_SCHEMA_VERSION: Final = "aether.observation.event.v1"
SUMMARY_SCHEMA_VERSION: Final = "aether.observation.summary.v1"
MANIFEST_SCHEMA_VERSION: Final = "aether.observation.segment-manifest.v1"

#: Every event schema version this release can read through pure upcasters (OBS-D-026).
SUPPORTED_EVENT_SCHEMA_VERSIONS: Final = ("aether.observation.event.v1",)

#: Section 6.2: a canonical line larger than this (LF included) is rejected before append.
MAX_EVENT_LINE_BYTES: Final = 65_536

#: One product version is shared by collector, reducer, and CLI (OBS-FR-071).
COLLECTOR_VERSION: Final = product_version()

#: Bumped whenever reduction output can change for an unchanged event set.
REDUCER_VERSION: Final = f"aether.observation.reducer.v1+{COLLECTOR_VERSION}"

#: Versioned, rebuildable derived projection (section 6.3).
READ_MODEL_SCHEMA: Final = "aether.observation.projection.v1"

SCHEMA_FILES: Final = {
    "event": "observation-event.schema.json",
    "summary": "observation-summary.schema.json",
    "manifest": "observation-segment-manifest.schema.json",
}

#: Section 6.2: SHA-256 over canonical JSON mapping each normalized relative path to its
#: file SHA-256, sorted by path. A missing file yields ``compatibility_mismatch``.
RUNTIME_FINGERPRINT_FILES: Final = (
    "hermes_cli/kanban_db.py",
    "hermes_cli/lifecycle.py",
    "hermes_cli/observability/shared_metrics_contract.py",
    "hermes_cli/plugins.py",
    "hermes_cli/profiles.py",
    "hermes_cli/web_server.py",
    "hermes_state_common.py",
    "model_tools.py",
    "tools/delegate_tool.py",
)

#: Used when no runtime tree can be inspected at all; always paired with a diagnostic.
NULL_RUNTIME_FINGERPRINT: Final = "0" * 64

# These ASCII-only grammars are deliberately shared by projectors, guards, identities,
# and the normative JSON schemas.  A reference is metadata, not a convenient place to
# truncate arbitrary native content.  Artifact references are canonical POSIX-style
# project-relative names; their component grammar makes ``.``, ``..``, URI schemes,
# alternate separators, controls, and Unicode confusables unrepresentable.
OPAQUE_REF_PATTERN: Final = r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$"
ARTIFACT_REF_PATTERN: Final = r"^[A-Za-z0-9][A-Za-z0-9._-]*(?:/[A-Za-z0-9][A-Za-z0-9._-]*)*$"
VERSION_REF_PATTERN: Final = r"^[A-Za-z0-9][A-Za-z0-9_.+:-]*$"

_OPAQUE_REF_RE: Final = re.compile(OPAQUE_REF_PATTERN, re.ASCII)
_ARTIFACT_REF_RE: Final = re.compile(ARTIFACT_REF_PATTERN, re.ASCII)
_VERSION_REF_RE: Final = re.compile(VERSION_REF_PATTERN, re.ASCII)


def is_opaque_ref(value: Any, *, max_len: int = 128) -> bool:
    """Return whether ``value`` is one bounded, ASCII-only opaque reference."""
    return (
        isinstance(value, str)
        and 0 < len(value) <= max_len
        and value == value.strip()
        and _OPAQUE_REF_RE.fullmatch(value) is not None
    )


def is_artifact_ref(value: Any, *, max_len: int = 512) -> bool:
    """Return whether ``value`` is a canonical project-relative artifact reference."""
    return (
        isinstance(value, str)
        and 0 < len(value) <= max_len
        and value == value.strip()
        and _ARTIFACT_REF_RE.fullmatch(value) is not None
    )


def is_version_ref(value: Any, *, max_len: int = 128) -> bool:
    """Return whether ``value`` is a bounded product/schema version token."""
    return (
        isinstance(value, str)
        and 0 < len(value) <= max_len
        and value == value.strip()
        and _VERSION_REF_RE.fullmatch(value) is not None
    )


def is_native_message_id(value: Any) -> bool:
    """Hermes SessionDB message identities are positive SQLite INTEGER values."""
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


# --------------------------------------------------------------------------------------
# Bounded enumerations (mirrors of the normative schemas; the schemas remain authoritative)
# --------------------------------------------------------------------------------------

SOURCE_KINDS: Final = (
    "aether_checkpoint",
    "hermes_hook",
    "native_reconciliation",
    "observer_diagnostic",
)

EVENT_TYPES: Final = (
    "trace.opened",
    "trace.resumed",
    "trace.closed",
    "trace.cancelled",
    "trace.abandoned",
    "trace.failed",
    "clarification.requested",
    "clarification.resolved",
    "decision.recorded",
    "decision.superseded",
    "decision.rejected",
    "contract.revision",
    "contract.executable",
    "contract.persisted",
    "contract.execution_started",
    "contract.completion_candidate",
    "contract.completion_verified",
    "evidence.added",
    "evidence.rejected",
    "participant.joined",
    "participant.left",
    "tool.started",
    "tool.completed",
    "tool.failed",
    "tool.blocked",
    "tool.cancelled",
    "tool.timed_out",
    "tool.interrupted",
    "wait.started",
    "wait.ended",
    "handoff.started",
    "handoff.completed",
    "handoff.failed",
    "handoff.blocked",
    "work_unit.bound",
    "work_unit.unbound",
    "work_unit.status",
    "run.started",
    "run.finished",
    "review.requested",
    "review.approved",
    "review.changes_requested",
    "acceptance.declared",
    "acceptance.evaluated",
    "invariant.passed",
    "invariant.failed",
    "coverage.gap",
    "coverage.restored",
    "configuration.observed",
    "tool_surface.observed",
    "skill.loaded",
    "model.request_started",
    "model.request_completed",
    "model.request_failed",
    "context.compression_observed",
    "context.overflow_observed",
    "dispatch.observed",
    "bottleneck.attributed",
    "defect.attributed",
)

TOOL_EVENT_TYPES: Final = (
    "tool.started",
    "tool.completed",
    "tool.failed",
    "tool.blocked",
    "tool.cancelled",
    "tool.timed_out",
    "tool.interrupted",
)

WORK_UNIT_EVENT_TYPES: Final = (
    "work_unit.bound",
    "work_unit.unbound",
    "work_unit.status",
    "run.started",
    "run.finished",
    "review.requested",
    "review.approved",
    "review.changes_requested",
)

STATUSES: Final = (
    "started",
    "completed",
    "failed",
    "interrupted",
    "blocked",
    "cancelled",
    "timed_out",
    "crashed",
    "spawn_failed",
    "gave_up",
    "reclaimed",
    "released",
    "pending",
    "passed",
    "reported",
    "verified",
    "rejected",
    "superseded",
    "unknown",
)

TOOL_CATEGORIES: Final = (
    "file",
    "terminal",
    "web",
    "delegation",
    "memory",
    "skill",
    "project",
    "browser",
    "code_execution",
    "communication",
    "computer_use",
    "home_automation",
    "mcp",
    "media",
    "planning",
    "scheduler",
    "unknown",
    "other",
)

TARGET_KINDS: Final = (
    "contract_artifact",
    "project_file",
    "web_domain",
    "process",
    "task",
    "session",
    "skill",
    "none",
    "other",
)

COVERAGE_CLASSES: Final = (
    "event_drop",
    "unpaired_span",
    "corrupt_segment",
    "unknown_schema",
    "native_source_unavailable",
    "clock_anomaly",
    "observer_io_failure",
    "compatibility_mismatch",
    "reconciliation_ambiguous",
    "forbidden_payload_rejected",
    "other",
)

FIELD_COVERAGE: Final = (
    "exact",
    "partial",
    "estimated",
    "unavailable",
    "not_applicable",
)

TASK_STATUSES: Final = (
    "triage",
    "todo",
    "scheduled",
    "ready",
    "running",
    "blocked",
    "review",
    "done",
    "archived",
    "unknown",
)

#: Section 7.3: statuses that keep a required unit open.
OPEN_TASK_STATUSES: Final = (
    "triage",
    "todo",
    "scheduled",
    "ready",
    "running",
    "blocked",
    "review",
)

RUN_STATUSES: Final = (
    "running",
    "done",
    "blocked",
    "crashed",
    "timed_out",
    "failed",
    "spawn_failed",
    "gave_up",
    "reclaimed",
    "released",
    "rate_limited",
    "stale",
    "review_requested",
    "changes_requested",
    "scheduled",
    "unknown",
)

RUN_OUTCOMES: Final = (
    "completed",
    "blocked",
    "crashed",
    "timed_out",
    "failed",
    "spawn_failed",
    "gave_up",
    "reclaimed",
    "protocol_violation",
    "rate_limited",
    "stale",
    "review_requested",
    "changes_requested",
    "scheduled",
    "unknown",
)

#: OBS-FR-043: counted separately, and none of them closes the trace on its own.
ANOMALOUS_RUN_OUTCOMES: Final = (
    "crashed",
    "timed_out",
    "failed",
    "spawn_failed",
    "gave_up",
    "reclaimed",
    "protocol_violation",
    "stale",
)

WORK_UNIT_RELATIONS: Final = (
    "root",
    "decomposition",
    "implementation",
    "review",
    "qa",
    "integration",
    "release",
    "follow_up",
    "other",
    "unknown",
)

WAIT_KINDS: Final = (
    "owner",
    "external",
    "provider_backoff",
    "approval",
    "process",
    "dependency",
    "unknown",
)

COMPLETION_STATES: Final = (
    "open",
    "completion_candidate",
    "persisted",
    "handed_off",
    "executing",
    "blocked",
    "in_review",
    "awaiting_final_verification",
    "completed",
    "cancelled",
    "abandoned",
    "failed",
)

TERMINATION_STATES: Final = ("open", "completed", "cancelled", "abandoned", "failed")

CLASSIFICATION_KINDS: Final = (
    "useful_iteration",
    "technical_retry",
    "cycle",
    "semantic_loop",
    "regression",
    "authorized_reversion",
    "unexplained_reversion",
    "owner_direction_change",
)

BOTTLENECK_CLASSES: Final = (
    "dependency_bound",
    "capacity_bound",
    "review_bound",
    "owner_bound",
    "provider_bound",
    "unassigned",
    "unknown",
)

DEFECT_CLASSES: Final = (
    "instruction_defect",
    "missing_capability",
    "contract_ambiguity",
    "coordination_defect",
    "runtime_failure",
    "policy_denial",
    "genuine_discovery",
    "undeclared",
)

PROVENANCE: Final = (
    "native_observed",
    "deterministic_derived",
    "actor_declared",
    "morfeo_judgment",
    "undeclared",
)

#: OBS-FR-064: natively derived facts must stay structurally distinguishable from judgment.
JUDGMENT_PROVENANCE: Final = ("actor_declared", "morfeo_judgment")

ROUND_TRIGGERS: Final = (
    "initial_dispatch",
    "review_rework",
    "resumption",
    "redispatch",
    "protocol_correction",
    "owner_direction_change",
    "other",
    "unknown",
)

WAVE_BARRIERS: Final = (
    "dependency",
    "review",
    "capacity",
    "owner",
    "provider",
    "unassigned",
    "integration",
    "terminal",
    "unknown",
)

VERDICTS: Final = (
    "terminal_failure",
    "cancelled",
    "abandoned",
    "blocked",
    "changes_requested",
    "attention",
    "work_remaining",
    "completion_candidate",
    "completed",
    "unknown",
)

NEXT_GATE_KINDS: Final = (
    "owner_decision",
    "dependency_resolution",
    "provider_recovery",
    "policy_resolution",
    "dispatch",
    "implementation",
    "review",
    "rework",
    "integration",
    "acceptance_verification",
    "morfeo_verification",
    "closure",
    "none",
    "unknown",
)

CHANGE_CLASSES: Final = (
    "verdict",
    "next_gate",
    "required_work",
    "acceptance",
    "anomaly",
    "bottleneck",
    "defect",
    "process",
    "configuration",
    "coverage",
)


class CoverageClass:
    """Named coverage classes, so call sites never spell a literal by hand."""

    EVENT_DROP = "event_drop"
    UNPAIRED_SPAN = "unpaired_span"
    CORRUPT_SEGMENT = "corrupt_segment"
    UNKNOWN_SCHEMA = "unknown_schema"
    NATIVE_SOURCE_UNAVAILABLE = "native_source_unavailable"
    CLOCK_ANOMALY = "clock_anomaly"
    OBSERVER_IO_FAILURE = "observer_io_failure"
    COMPATIBILITY_MISMATCH = "compatibility_mismatch"
    RECONCILIATION_AMBIGUOUS = "reconciliation_ambiguous"
    FORBIDDEN_PAYLOAD_REJECTED = "forbidden_payload_rejected"
    OTHER = "other"


# --------------------------------------------------------------------------------------
# Canonical serialization
# --------------------------------------------------------------------------------------


def _reject_floats(value: Any, path: str = "$") -> None:
    """Floats are not canonically representable; observation payloads never carry one."""
    if isinstance(value, float):
        raise ValueError(f"non-canonical float at {path}")
    if isinstance(value, dict):
        for key, item in value.items():
            _reject_floats(item, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _reject_floats(item, f"{path}[{index}]")


def canonical_json_str(value: Any) -> str:
    """Serialize ``value`` deterministically: sorted keys, no padding, UTF-8 text.

    The same function serializes journal lines, HMAC fingerprint input, segment
    manifests, and summaries, so byte-equivalence is one property, not four.
    """
    _reject_floats(value)
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def canonical_json_bytes(value: Any) -> bytes:
    return canonical_json_str(value).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_digest(value: Any) -> str:
    """SHA-256 over the canonical JSON encoding of ``value``."""
    return sha256_hex(canonical_json_bytes(value))


# --------------------------------------------------------------------------------------
# Normative schema access
# --------------------------------------------------------------------------------------

_PACKAGED_SCHEMAS = Path(__file__).resolve().parent.parent / "resources" / "schemas"
_SOURCE_SCHEMAS = (
    Path(__file__).resolve().parents[3] / "specs" / "002-aether-contract-observation" / "contracts"
)


def schema_path(name: str) -> Path:
    """Locate a normative schema.

    The packaged copy under ``resources/schemas`` wins when present (installed wheel).
    A source checkout falls back to the single editable source under ``specs/`` so that
    development never maintains a second hand-edited copy (OBS-FR-075).
    """
    filename = SCHEMA_FILES[name]
    packaged = _PACKAGED_SCHEMAS / filename
    if packaged.is_file():
        return packaged
    source = _SOURCE_SCHEMAS / filename
    if source.is_file():
        return source
    raise FileNotFoundError(f"observation schema not found: {filename}")


@lru_cache(maxsize=8)
def schema_bytes(name: str) -> bytes:
    return schema_path(name).read_bytes()


@lru_cache(maxsize=8)
def schema_digest(name: str) -> str:
    return sha256_hex(schema_bytes(name))


@lru_cache(maxsize=8)
def load_schema(name: str) -> dict[str, Any]:
    return json.loads(schema_bytes(name).decode("utf-8"))


@lru_cache(maxsize=8)
def _validator(name: str):
    from jsonschema import Draft202012Validator, FormatChecker

    schema = load_schema(name)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def event_validator():
    """Compiled validator for the normative event schema (compiled once, reused)."""
    return _validator("event")


def summary_validator():
    return _validator("summary")


def manifest_validator():
    return _validator("manifest")


def validate_event(event: dict[str, Any]) -> None:
    """Raise ``jsonschema.ValidationError`` when ``event`` is not schema-valid."""
    event_validator().validate(event)
    work_unit = event.get("work_unit")
    task_id = event.get("task_id")
    if (
        isinstance(work_unit, dict)
        and isinstance(task_id, str)
        and isinstance(work_unit.get("task_ref"), str)
        and task_id != work_unit["task_ref"]
    ):
        from jsonschema import ValidationError

        raise ValidationError("task_id must equal work_unit.task_ref")


def validate_summary(summary: dict[str, Any]) -> None:
    summary_validator().validate(summary)


def validate_manifest(manifest: dict[str, Any]) -> None:
    manifest_validator().validate(manifest)


def event_errors(event: dict[str, Any]) -> list[str]:
    """Return bounded schema diagnostics without echoing offending values."""
    errors = [
        f"{'/'.join(str(p) for p in error.absolute_path) or '$'}:{error.validator}"
        for error in sorted(event_validator().iter_errors(event), key=str)
    ]
    work_unit = event.get("work_unit")
    if (
        isinstance(work_unit, dict)
        and isinstance(event.get("task_id"), str)
        and isinstance(work_unit.get("task_ref"), str)
        and event["task_id"] != work_unit["task_ref"]
    ):
        errors.append("task_id:cross_field")
    return errors


# --------------------------------------------------------------------------------------
# Runtime compatibility fingerprint
# --------------------------------------------------------------------------------------


def compute_runtime_fingerprint(runtime_root: Path | str | None) -> tuple[str, list[str]]:
    """Fingerprint the locked Hermes compatibility surface.

    Returns ``(fingerprint, missing_relative_paths)``. Missing files are recorded as
    ``null`` in the canonical mapping rather than skipped, so the fingerprint states
    exactly what was observed; the caller raises a ``compatibility_mismatch`` coverage
    diagnostic when the list is non-empty. The collector never invents a fingerprint
    for an inspectable tree (section 6.2).
    """
    if runtime_root is None:
        return NULL_RUNTIME_FINGERPRINT, list(RUNTIME_FINGERPRINT_FILES)
    root = Path(runtime_root)
    mapping: dict[str, str | None] = {}
    missing: list[str] = []
    for relative in RUNTIME_FINGERPRINT_FILES:
        candidate = root / relative
        try:
            mapping[relative] = sha256_hex(candidate.read_bytes())
        except OSError:
            mapping[relative] = None
            missing.append(relative)
    if len(missing) == len(RUNTIME_FINGERPRINT_FILES):
        return NULL_RUNTIME_FINGERPRINT, missing
    return canonical_digest(mapping), missing


# --------------------------------------------------------------------------------------
# Native status normalization boundary (section 6.1)
# --------------------------------------------------------------------------------------

#: ``ok|success`` become ``completed``; ``error|failed`` become ``failed``;
#: ``blocked|cancelled|timed_out|timeout`` stay distinct. Anything else is ``unknown``.
_NATIVE_STATUS_MAP: Final = {
    "ok": "completed",
    "success": "completed",
    "succeeded": "completed",
    "completed": "completed",
    "error": "failed",
    "failed": "failed",
    "failure": "failed",
    "blocked": "blocked",
    "cancelled": "cancelled",
    "canceled": "cancelled",
    "timed_out": "timed_out",
    "timeout": "timed_out",
    "interrupted": "interrupted",
    "crashed": "crashed",
    "spawn_failed": "spawn_failed",
    "gave_up": "gave_up",
    "reclaimed": "reclaimed",
    "released": "released",
    "running": "started",
    "started": "started",
    "pending": "pending",
}


def normalize_native_status(native: Any) -> tuple[str, bool]:
    """Map a native Hermes result value onto the observation status vocabulary.

    Returns ``(status, recognized)``. An unrecognized value becomes ``unknown`` and the
    caller records a coverage diagnostic; it is never invented into success or failure.
    """
    if not isinstance(native, str):
        return "unknown", False
    key = native.strip().lower()
    mapped = _NATIVE_STATUS_MAP.get(key)
    if mapped is None:
        return "unknown", False
    return mapped, True


#: Terminal tool statuses, kept separate forever (OBS-FR-034).
TOOL_TERMINAL_STATUSES: Final = (
    "completed",
    "failed",
    "blocked",
    "cancelled",
    "timed_out",
    "interrupted",
    "unknown",
)

TOOL_STATUS_TO_EVENT_TYPE: Final = {
    "completed": "tool.completed",
    "failed": "tool.failed",
    "blocked": "tool.blocked",
    "cancelled": "tool.cancelled",
    "timed_out": "tool.timed_out",
    "interrupted": "tool.interrupted",
    "unknown": "tool.completed",
}


#: Bounded local fallback taxonomy. It is used only when the locked runtime's
#: ``tool_category()`` cannot be resolved, and that case also raises a
#: ``compatibility_mismatch`` diagnostic so the release gate fails rather than the
#: taxonomy silently forking (OBS-D-009, section 6.5).
_FALLBACK_CATEGORY_PREFIXES: Final = (
    ("kanban", "project"),
    ("delegate", "delegation"),
    ("subagent", "delegation"),
    ("memory", "memory"),
    ("skill", "skill"),
    ("web", "web"),
    ("browser", "browser"),
    ("shell", "terminal"),
    ("terminal", "terminal"),
    ("bash", "terminal"),
    ("file", "file"),
    ("read", "file"),
    ("write", "file"),
    ("edit", "file"),
    ("glob", "file"),
    ("grep", "file"),
    ("code_execution", "code_execution"),
    ("python", "code_execution"),
    ("cron", "scheduler"),
    ("schedule", "scheduler"),
    ("mcp", "mcp"),
    ("computer", "computer_use"),
    ("plan", "planning"),
    ("todo", "planning"),
)


def fallback_tool_category(tool_name: Any) -> str:
    """Bounded fallback category. Always paired with a compatibility diagnostic."""
    if not isinstance(tool_name, str) or not tool_name:
        return "unknown"
    lowered = tool_name.strip().lower()
    for prefix, category in _FALLBACK_CATEGORY_PREFIXES:
        if lowered.startswith(prefix) or prefix in lowered:
            return category
    return "other"
