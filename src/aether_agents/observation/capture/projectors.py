"""Pure projection of bounded native facts into schema-valid observation events.

Normative sources: spec sections 6.1 and 8, requirements OBS-FR-032, OBS-FR-033,
OBS-FR-034, OBS-FR-036.

Every function here takes already-extracted scalar arguments — never a native payload
dictionary. That is deliberate: projection happens by explicit field pick, so a native
``args``, ``result``, ``error_message``, ``middleware_trace``, ``user_task``, prompt,
response, or child goal/summary value has no path into an event object at all. The
privacy guard in :mod:`aether_agents.observation.privacy` is the second line, not the first.

This module imports no Hermes.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from aether_agents.observation.contracts import (
    BOTTLENECK_CLASSES,
    COVERAGE_CLASSES,
    DEFECT_CLASSES,
    EVENT_SCHEMA_VERSION,
    EVENT_TYPES,
    FIELD_COVERAGE,
    PROVENANCE,
    RUN_OUTCOMES,
    RUN_STATUSES,
    SOURCE_KINDS,
    STATUSES,
    TARGET_KINDS,
    TASK_STATUSES,
    TOOL_CATEGORIES,
    TOOL_STATUS_TO_EVENT_TYPE,
    WAIT_KINDS,
    WORK_UNIT_RELATIONS,
    CoverageClass,
    is_native_message_id,
    is_version_ref,
)
from aether_agents.observation.identity import (
    deterministic_event_id,
    native_identity,
    new_event_id,
)
from aether_agents.observation.privacy import (
    is_native_kanban_source_hook,
    is_native_source_hook,
    native_agent_task_ref,
    native_kanban_task_ref,
    native_profile_ref,
    native_pseudonym_ref,
    opaque_ref,
    relative_artifact_ref,
    safe_error_class,
    safe_ref,
)

__all__ = ["EventBuilder", "utc_now", "to_utc_text", "utc_offset_minutes"]

_TRACE_ID_RE = re.compile(r"^ctr_[a-f0-9]{32}$", re.ASCII)
_PROJECT_ID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.ASCII,
)
_EVENT_ID_RE = re.compile(r"^evt_(?:[a-f0-9]{32}|[a-f0-9]{64})$", re.ASCII)
_DIGEST_RE = re.compile(r"^[a-f0-9]{64}$", re.ASCII)
_KEY_ID_RE = re.compile(r"^fpk_[a-f0-9]{32}$", re.ASCII)
_BINDING_RE = re.compile(r"^bnd_[A-Za-z0-9_-]{16,124}$", re.ASCII)
_SOURCE_HOOK_RE = re.compile(r"^[a-z][a-z0-9_]{1,63}$", re.ASCII)
_INVARIANT_RE = re.compile(r"^OBS-INV-[0-9]{3}$", re.ASCII)
_REASON_CODE_RE = re.compile(r"^[A-Z0-9_]{2,64}$", re.ASCII)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def to_utc_text(value: datetime | None) -> str | None:
    """RFC 3339 in UTC with millisecond precision, so canonical bytes are stable."""
    if value is None:
        return None
    moment = value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return moment.strftime("%Y-%m-%dT%H:%M:%S.") + f"{moment.microsecond // 1000:03d}Z"


def utc_offset_minutes(value: datetime | None) -> int | None:
    """Preserve the originating local offset so an archived trace is dated correctly."""
    if value is None or value.tzinfo is None:
        return None
    offset = value.utcoffset()
    return None if offset is None else int(offset.total_seconds() // 60)


def _positive_int(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value if value >= 0 else None


def _strict_positive_int(value: Any) -> int | None:
    parsed = _positive_int(value)
    return parsed if parsed is not None and parsed > 0 else None


def _bounded_category(value: Any) -> str:
    return value if isinstance(value, str) and value in TOOL_CATEGORIES else "unknown"


def _bounded(value: Any, allowed: tuple[str, ...], fallback: str) -> str:
    return value if isinstance(value, str) and value in allowed else fallback


def _safe_refs(values: Any, *, max_len: int = 128) -> list[str]:
    if not isinstance(values, (list, tuple)):
        return []
    return [
        reference for value in values if (reference := safe_ref(value, max_len=max_len)) is not None
    ]


def _safe_artifact_refs(values: Any, project_root: Any = None) -> list[str]:
    if not isinstance(values, (list, tuple)):
        return []
    return [
        reference
        for value in values
        if (reference := relative_artifact_ref(value, project_root)) is not None
    ]


def _safe_digest(value: Any) -> str | None:
    return value if isinstance(value, str) and _DIGEST_RE.fullmatch(value) else None


def _safe_key_id(value: Any) -> str | None:
    return value if isinstance(value, str) and _KEY_ID_RE.fullmatch(value) else None


def _safe_field_coverage(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {"unknown_field": "unavailable"}
    projected = {
        key: coverage
        for key, coverage in value.items()
        if isinstance(key, str) and _SOURCE_HOOK_RE.fullmatch(key) and coverage in FIELD_COVERAGE
    }
    return projected or {"unknown_field": "unavailable"}


def _project_native_identity_blocks(
    source_hook: str | None,
    blocks: dict[str, Any],
) -> dict[str, Any]:
    """Remove unkeyed producer identities before an event can reach a sink."""
    projected = dict(blocks)

    tool = projected.get("tool")
    if isinstance(tool, dict):
        tool = dict(tool)
        if source_hook in {"pre_tool_call", "post_tool_call"}:
            tool["call_id"] = (
                native_pseudonym_ref(tool.get("call_id"), kind="tool_call") or "unknown"
            )
            if tool.get("retry_of_call_id") is not None:
                tool["retry_of_call_id"] = native_pseudonym_ref(
                    tool.get("retry_of_call_id"), kind="tool_call"
                )
        elif source_hook in {"subagent_start", "subagent_stop"}:
            tool["call_id"] = native_pseudonym_ref(tool.get("call_id"), kind="session") or "unknown"
            if tool.get("target_ref") is not None:
                tool["target_ref"] = native_pseudonym_ref(tool.get("target_ref"), kind="session")
        projected["tool"] = tool

    model_request = projected.get("model_request")
    if isinstance(model_request, dict):
        model_request = dict(model_request)
        model_request["request_ref"] = (
            native_pseudonym_ref(model_request.get("request_ref"), kind="api_request") or "unknown"
        )
        projected["model_request"] = model_request

    tool_surface = projected.get("tool_surface")
    if isinstance(tool_surface, dict):
        tool_surface = dict(tool_surface)
        tool_surface["request_ref"] = (
            native_pseudonym_ref(tool_surface.get("request_ref"), kind="api_request") or "unknown"
        )
        projected["tool_surface"] = tool_surface

    if source_hook in {"subagent_start", "subagent_stop"}:
        configuration = projected.get("configuration")
        if isinstance(configuration, dict):
            configuration = dict(configuration)
            if configuration.get("participant_ref") is not None:
                configuration["participant_ref"] = native_pseudonym_ref(
                    configuration.get("participant_ref"), kind="session"
                )
            projected["configuration"] = configuration

    if source_hook in {"pre_approval_request", "post_approval_response"}:
        wait = projected.get("wait")
        if isinstance(wait, dict):
            wait = dict(wait)
            wait["wait_id"] = (
                native_pseudonym_ref(wait.get("wait_id"), kind="approval_request") or "unknown"
            )
            projected["wait"] = wait

    return projected


@dataclass(slots=True)
class EventBuilder:
    """Holds the invariant envelope for one producer and stamps every event with it.

    ``producer_epoch`` and ``producer_seq`` are intentionally absent: the journal assigns
    them atomically with the append, so on-disk order and sequence order cannot diverge.
    """

    trace_id: str
    project_id: str
    collector_version: str
    runtime_fingerprint: str
    normalizer_ref: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.trace_id, str) or not _TRACE_ID_RE.fullmatch(self.trace_id):
            raise ValueError("trace_id must use the ctr_<128-bit-hex> grammar")
        if not isinstance(self.project_id, str) or not _PROJECT_ID_RE.fullmatch(self.project_id):
            raise ValueError("project_id must be a canonical lower-case UUID")
        if not is_version_ref(self.collector_version, max_len=64):
            raise ValueError("collector_version must be a bounded version token")
        if _safe_digest(self.runtime_fingerprint) is None:
            raise ValueError("runtime_fingerprint must be a lower-case SHA-256 digest")
        if self.normalizer_ref is not None and safe_ref(self.normalizer_ref) is None:
            raise ValueError("normalizer_ref must be a bounded opaque reference")

    # -- envelope -----------------------------------------------------------------
    def build(
        self,
        event_type: str,
        *,
        status: str,
        actor_kind: str = "agent",
        actor_id: str = "unknown",
        profile: str | None = None,
        role: str | None = None,
        source_kind: str = "hermes_hook",
        source_hook: str | None = None,
        occurred_at: datetime | None = None,
        timestamp_source: str = "collector",
        monotonic: bool = True,
        identity: dict[str, Any] | None = None,
        parent_event_id: str | None = None,
        contract_id: Any = None,
        task_id: Any = None,
        run_id: Any = None,
        session_id: Any = None,
        turn_id: Any = None,
        api_request_id: Any = None,
        message_id: Any = None,
        **blocks: Any,
    ) -> dict[str, Any]:
        """Assemble one event. Optional blocks are omitted when ``None``."""
        if event_type not in EVENT_TYPES:
            raise ValueError("event_type is outside the observation vocabulary")
        if status not in STATUSES:
            raise ValueError("status is outside the observation vocabulary")
        native_boundary = source_kind in {
            "hermes_hook",
            "native_reconciliation",
        } and is_native_source_hook(source_hook)
        if native_boundary:
            blocks = _project_native_identity_blocks(source_hook, blocks)
        moment = occurred_at or utc_now()
        recorded = utc_now()
        event: dict[str, Any] = {
            "schema_version": EVENT_SCHEMA_VERSION,
            # A complete native tuple gives a deterministic ID so a replayed hook and a
            # later reconciliation of the same fact collapse to one row; an incomplete
            # tuple gets randomness once and is never fuzzy-matched.
            "event_id": deterministic_event_id(identity) if identity else new_event_id(),
            "trace_id": self.trace_id,
            "project_id": self.project_id,
            "producer_epoch": "prd_" + "0" * 32,  # replaced atomically on append
            "producer_seq": 0,  # replaced atomically on append
            "collector_version": self.collector_version,
            "runtime_fingerprint": self.runtime_fingerprint,
            "normalizer_ref": self.normalizer_ref,
            "source_kind": _bounded(source_kind, SOURCE_KINDS, "observer_diagnostic"),
            "source_hook": source_hook
            if isinstance(source_hook, str) and _SOURCE_HOOK_RE.fullmatch(source_hook)
            else None,
            "contract_id": safe_ref(contract_id),
            "task_id": native_agent_task_ref(task_id) if native_boundary else safe_ref(task_id),
            "run_id": _strict_positive_int(run_id),
            "session_id": (
                native_pseudonym_ref(session_id, kind="session")
                if native_boundary
                else safe_ref(session_id, max_len=256)
            ),
            "turn_id": (
                native_pseudonym_ref(turn_id, kind="turn")
                if native_boundary
                else safe_ref(turn_id, max_len=256)
            ),
            "api_request_id": (
                native_pseudonym_ref(api_request_id, kind="api_request")
                if native_boundary
                else safe_ref(api_request_id, max_len=256)
            ),
            "message_id": message_id if is_native_message_id(message_id) else None,
            "parent_event_id": parent_event_id
            if isinstance(parent_event_id, str) and _EVENT_ID_RE.fullmatch(parent_event_id)
            else None,
            "occurred_at": to_utc_text(moment),
            "source_utc_offset_minutes": utc_offset_minutes(occurred_at),
            "recorded_at": to_utc_text(recorded),
            "timestamp_source": timestamp_source
            if timestamp_source in ("native", "collector", "reconciled", "unknown")
            else "unknown",
            # Validates local hook timing; reconciled events have no native sample.
            "monotonic_ns": time.monotonic_ns() if monotonic else None,
            "actor": _actor(
                actor_kind,
                (
                    native_pseudonym_ref(actor_id, kind="session") or "unknown"
                    if native_boundary and source_hook in {"subagent_start", "subagent_stop"}
                    else actor_id
                ),
                native_profile_ref(profile) if native_boundary else profile,
                role,
            ),
            "event_type": event_type,
            "status": status,
        }
        for name, block in blocks.items():
            if block is not None:
                event[name] = block
        return event

    # -- tools --------------------------------------------------------------------
    def tool_started(
        self,
        *,
        call_id: str,
        name: str,
        category: str,
        target_kind: str = "none",
        target_ref: Any = None,
        project_root: Any = None,
        **envelope: Any,
    ) -> dict[str, Any]:
        """``pre_tool_call`` opens an identifiable span and nothing more (OBS-D-008)."""
        return self.build(
            "tool.started",
            status="started",
            source_hook="pre_tool_call",
            identity=native_identity(
                kind="tool.started",
                session=envelope.get("session_id"),
                call=call_id,
            ),
            tool={
                "call_id": native_pseudonym_ref(call_id, kind="tool_call") or "unknown",
                "name": safe_ref(name) or "unknown",
                "category": _bounded_category(category),
                "target_kind": _bounded(target_kind, TARGET_KINDS, "other"),
                "target_ref": relative_artifact_ref(target_ref, project_root),
            },
            **envelope,
        )

    def tool_terminal(
        self,
        *,
        call_id: str,
        name: str,
        category: str,
        status: str,
        duration_ms: Any = None,
        exit_code: Any = None,
        error_class: Any = None,
        approval_outcome: Any = None,
        retry_count: Any = None,
        retry_of_call_id: Any = None,
        target_kind: str = "none",
        target_ref: Any = None,
        project_root: Any = None,
        **envelope: Any,
    ) -> dict[str, Any]:
        """``post_tool_call`` is the terminal tool fact.

        Every terminal state stays its own total; none is ever folded into success
        (OBS-FR-034). ``error_class`` keeps a stable class token only — never raw text.
        """
        return self.build(
            TOOL_STATUS_TO_EVENT_TYPE.get(status, "tool.completed"),
            status=status,
            source_hook="post_tool_call",
            identity=native_identity(
                kind="tool.terminal",
                session=envelope.get("session_id"),
                call=call_id,
            ),
            tool={
                "call_id": native_pseudonym_ref(call_id, kind="tool_call") or "unknown",
                "name": safe_ref(name) or "unknown",
                "category": _bounded_category(category),
                "target_kind": _bounded(target_kind, TARGET_KINDS, "other"),
                "target_ref": relative_artifact_ref(target_ref, project_root),
                "duration_ms": _positive_int(duration_ms),
                "exit_code": exit_code
                if isinstance(exit_code, int) and not isinstance(exit_code, bool)
                else None,
                "error_class": safe_error_class(error_class),
                "approval_outcome": approval_outcome
                if approval_outcome
                in ("approved", "denied", "not_required", "timed_out", "unknown")
                else None,
                "retry_count": _positive_int(retry_count),
                "retry_of_call_id": native_pseudonym_ref(retry_of_call_id, kind="tool_call"),
            },
            **envelope,
        )

    # -- model requests -------------------------------------------------------------
    def model_request(
        self,
        *,
        state: str,
        request_ref: str,
        model: Any = None,
        provider: Any = None,
        response_model: Any = None,
        started_at: datetime | None = None,
        ended_at: datetime | None = None,
        duration_ms: Any = None,
        finish_reason: Any = None,
        message_count: Any = None,
        tool_count: Any = None,
        attempt_count: int = 1,
        tokens: dict[str, Any] | None = None,
        usage_coverage: str = "unavailable",
        structured_reason_code: Any = None,
        **envelope: Any,
    ) -> dict[str, Any]:
        """Model traffic is never counted as a tool (OBS-FR-015).

        Unavailable provider counters stay unavailable; they are not estimated, and no
        prompt, response, reasoning, request body, or error text is carried.
        """
        event_type = {
            "started": "model.request_started",
            "completed": "model.request_completed",
            "failed": "model.request_failed",
            "context_compressed": "context.compression_observed",
            "context_overflow": "context.overflow_observed",
        }[state]
        status = {"started": "started", "completed": "completed", "failed": "failed"}.get(
            state, "reported"
        )
        buckets = tokens if isinstance(tokens, dict) else {}
        return self.build(
            event_type,
            status=status,
            source_hook=envelope.pop("source_hook", "post_api_request"),
            identity=native_identity(
                kind=event_type,
                session=envelope.get("session_id"),
                request=request_ref,
                attempt=max(1, attempt_count if isinstance(attempt_count, int) else 1),
            ),
            model_request={
                "request_ref": (native_pseudonym_ref(request_ref, kind="api_request") or "unknown"),
                "state": state,
                "model": opaque_ref(model),
                "provider": opaque_ref(provider),
                "response_model": opaque_ref(response_model),
                "started_at": to_utc_text(started_at),
                "ended_at": to_utc_text(ended_at),
                "duration_ms": _positive_int(duration_ms),
                "finish_reason": opaque_ref(finish_reason),
                "message_count": _positive_int(message_count),
                "tool_count": _positive_int(tool_count),
                "attempt_count": max(1, attempt_count if isinstance(attempt_count, int) else 1),
                "input_tokens": _positive_int(buckets.get("input_tokens")),
                "output_tokens": _positive_int(buckets.get("output_tokens")),
                "cache_read_tokens": _positive_int(buckets.get("cache_read_tokens")),
                "cache_write_tokens": _positive_int(buckets.get("cache_write_tokens")),
                "reasoning_tokens": _positive_int(buckets.get("reasoning_tokens")),
                "total_tokens": _positive_int(buckets.get("total_tokens")),
                "usage_coverage": _bounded(usage_coverage, FIELD_COVERAGE, "unavailable"),
                "structured_reason_code": opaque_ref(structured_reason_code),
            },
            **envelope,
        )

    # -- work graph ------------------------------------------------------------------
    def work_unit(
        self,
        *,
        event_type: str,
        status: str,
        task_ref: str,
        relation: Any,
        required: Any,
        binding: str,
        parent_task_refs: tuple[str, ...] = (),
        task_status: Any = None,
        run_status: Any = None,
        run_outcome: Any = None,
        **envelope: Any,
    ) -> dict[str, Any]:
        """Bind, unbind, or restate one work unit's authoritative state."""
        native_boundary = is_native_kanban_source_hook(envelope.get("source_hook"))
        project_task = native_kanban_task_ref if native_boundary else safe_ref
        projected_task = project_task(task_ref)
        envelope.setdefault("task_id", projected_task)
        projected_parents = tuple(
            ref for parent in parent_task_refs if (ref := project_task(parent)) is not None
        )
        return self.build(
            event_type,
            status=status,
            work_unit={
                "task_ref": projected_task or "unknown",
                "relation": _bounded(relation, WORK_UNIT_RELATIONS, "unknown"),
                "required": required if isinstance(required, bool) else None,
                "parent_task_refs": list(dict.fromkeys(projected_parents)),
                "task_status": (task_status if task_status in TASK_STATUSES else "unknown"),
                "run_status": run_status if run_status in RUN_STATUSES else None,
                "run_outcome": run_outcome if run_outcome in RUN_OUTCOMES else None,
                "binding_ref": binding
                if isinstance(binding, str) and _BINDING_RE.fullmatch(binding)
                else "bnd_unknown_0000000000000000",
            },
            **envelope,
        )

    # -- coverage ---------------------------------------------------------------------
    def coverage_gap(
        self,
        *,
        gap_class: str,
        reason_code: str,
        started_at: datetime | None = None,
        ended_at: datetime | None = None,
        **envelope: Any,
    ) -> dict[str, Any]:
        """A collector-known gap is a source event (OBS-D-025).

        Reducer-discovered corruption is *not*: a reducer that writes into its own input
        makes replay history-dependent and can recursively duplicate diagnostics.
        """
        envelope.setdefault("source_kind", "observer_diagnostic")
        return self.build(
            "coverage.gap",
            status="reported",
            coverage={
                "class": _bounded(gap_class, COVERAGE_CLASSES, CoverageClass.OTHER),
                "reason_code": reason_code
                if isinstance(reason_code, str) and _REASON_CODE_RE.fullmatch(reason_code)
                else "UNKNOWN_GAP",
                "started_at": to_utc_text(started_at),
                "ended_at": to_utc_text(ended_at),
            },
            **envelope,
        )

    # -- acceptance / wait / dispatch / attribution ------------------------------------
    def acceptance(
        self,
        *,
        event_type: str,
        criterion_ref: str,
        state: str,
        evidence_refs: tuple[str, ...] = (),
        assigned_task_ref: Any = None,
        review_task_ref: Any = None,
        **envelope: Any,
    ) -> dict[str, Any]:
        status = {"passed": "passed", "failed": "failed", "pending": "pending"}.get(
            state, "unknown"
        )
        return self.build(
            event_type,
            status=status,
            acceptance={
                "criterion_ref": safe_ref(criterion_ref) or "unknown",
                "state": state
                if state in ("pending", "passed", "failed", "unknown")
                else "unknown",
                "evidence_refs": _safe_artifact_refs(evidence_refs),
                "assigned_task_ref": safe_ref(assigned_task_ref),
                "review_task_ref": safe_ref(review_task_ref),
            },
            **envelope,
        )

    def wait(self, *, started: bool, wait_id: str, kind: str, **envelope: Any) -> dict[str, Any]:
        return self.build(
            "wait.started" if started else "wait.ended",
            status="started" if started else "completed",
            wait={
                "wait_id": safe_ref(wait_id, max_len=256) or "unknown",
                "kind": _bounded(kind, WAIT_KINDS, "unknown"),
            },
            **envelope,
        )

    def dispatch(
        self,
        *,
        tick_ref: str,
        outcome: str,
        bottleneck_class: str,
        eligible_count: Any = None,
        running_count: Any = None,
        global_limit: Any = None,
        per_profile_limit: Any = None,
        precision_ms: Any = None,
        evidence_refs: tuple[str, ...] = (),
        **envelope: Any,
    ) -> dict[str, Any]:
        """Dispatch pressure is sampled at tick cadence, and says so (OBS-FR-061)."""
        return self.build(
            "dispatch.observed",
            status="reported",
            source_hook="on_kanban_dispatch_tick",
            identity=native_identity(kind="dispatch.observed", tick=tick_ref),
            dispatch={
                "tick_ref": safe_ref(tick_ref) or "unknown",
                "sampling": "dispatch_tick",
                "outcome": safe_ref(outcome) or "unknown",
                "eligible_count": _positive_int(eligible_count),
                "running_count": _positive_int(running_count),
                "global_limit": _positive_int(global_limit),
                "per_profile_limit": _positive_int(per_profile_limit),
                "bottleneck_class": _bounded(bottleneck_class, BOTTLENECK_CLASSES, "unknown"),
                "precision_ms": _positive_int(precision_ms),
                "evidence_refs": _safe_artifact_refs(evidence_refs),
            },
            **envelope,
        )

    def attribution(
        self,
        *,
        kind: str,
        attribution_class: str,
        provenance: str,
        started_at: datetime | None = None,
        ended_at: datetime | None = None,
        precision_ms: Any = None,
        evidence_refs: tuple[str, ...] = (),
        **envelope: Any,
    ) -> dict[str, Any]:
        """Attribution always carries its provenance, so judgment never reads as measurement."""
        return self.build(
            "bottleneck.attributed" if kind == "bottleneck" else "defect.attributed",
            status="reported",
            attribution={
                "kind": kind if kind in ("bottleneck", "defect") else "defect",
                "class": _bounded(
                    attribution_class,
                    BOTTLENECK_CLASSES if kind == "bottleneck" else DEFECT_CLASSES,
                    "unknown" if kind == "bottleneck" else "undeclared",
                ),
                "provenance": _bounded(provenance, PROVENANCE, "undeclared"),
                "started_at": to_utc_text(started_at),
                "ended_at": to_utc_text(ended_at),
                "precision_ms": _positive_int(precision_ms),
                "evidence_refs": _safe_artifact_refs(evidence_refs),
            },
            **envelope,
        )

    # -- configuration / capability ------------------------------------------------
    def configuration(
        self,
        *,
        fingerprint_id: str,
        scope: str,
        fingerprint_key_id: str,
        observer_version: str,
        field_coverage: dict[str, str],
        participant_ref: Any = None,
        model: Any = None,
        provider: Any = None,
        system_prompt_fingerprint: str | None = None,
        observed_skill_set_fingerprint: str | None = None,
        declared_toolset_fingerprint: str | None = None,
        effective_tool_surface_fingerprint: str | None = None,
        global_concurrency_limit: Any = None,
        per_profile_concurrency_limit: Any = None,
        **envelope: Any,
    ) -> dict[str, Any]:
        """Configured and effective values are never conflated (OBS-FR-058)."""
        return self.build(
            "configuration.observed",
            status="reported",
            configuration={
                "fingerprint_id": _safe_digest(fingerprint_id) or "0" * 64,
                "scope": scope if scope in ("trace", "participant", "request") else "trace",
                "participant_ref": opaque_ref(participant_ref),
                "model": opaque_ref(model),
                "provider": opaque_ref(provider),
                "system_prompt_fingerprint": _safe_digest(system_prompt_fingerprint),
                "observed_skill_set_fingerprint": _safe_digest(observed_skill_set_fingerprint),
                "declared_toolset_fingerprint": _safe_digest(declared_toolset_fingerprint),
                "effective_tool_surface_fingerprint": _safe_digest(
                    effective_tool_surface_fingerprint
                ),
                "global_concurrency_limit": _positive_int(global_concurrency_limit),
                "per_profile_concurrency_limit": _positive_int(per_profile_concurrency_limit),
                "observer_version": observer_version
                if is_version_ref(observer_version)
                else "unknown",
                "fingerprint_key_id": _safe_key_id(fingerprint_key_id) or "fpk_" + "0" * 32,
                "runtime_fingerprint": self.runtime_fingerprint,
                "field_coverage": _safe_field_coverage(field_coverage),
            },
            **envelope,
        )

    def tool_surface(
        self,
        *,
        request_ref: str,
        completeness: str,
        fingerprint_key_id: str,
        observed_tool_count: Any = None,
        granted_tool_refs: tuple[str, ...] = (),
        never_used_tool_refs: tuple[str, ...] = (),
        declared_toolset_fingerprint: str | None = None,
        effective_direct_surface_fingerprint: str | None = None,
        effective_deferred_surface_fingerprint: str | None = None,
        schema_serialized_bytes: Any = None,
        schema_estimated_tokens: Any = None,
        estimator_ref: Any = None,
        **envelope: Any,
    ) -> dict[str, Any]:
        """``never_used`` is claimed only from a demonstrably complete snapshot.

        On the locked runtime the final effective surface is not guaranteed complete, so
        a partial snapshot must produce no negative claim at all (OBS-FR-059).
        """
        never_used = tuple(never_used_tool_refs) if completeness == "exact" else ()
        return self.build(
            "tool_surface.observed",
            status="reported",
            tool_surface={
                "request_ref": (native_pseudonym_ref(request_ref, kind="api_request") or "unknown"),
                "completeness": completeness if completeness in FIELD_COVERAGE else "unavailable",
                "declared_toolset_fingerprint": _safe_digest(declared_toolset_fingerprint),
                "effective_direct_surface_fingerprint": _safe_digest(
                    effective_direct_surface_fingerprint
                ),
                "effective_deferred_surface_fingerprint": _safe_digest(
                    effective_deferred_surface_fingerprint
                ),
                "observed_tool_count": _positive_int(observed_tool_count),
                "granted_tool_refs": _safe_refs(granted_tool_refs),
                "never_used_tool_refs": _safe_refs(never_used),
                "schema_serialized_bytes": _positive_int(schema_serialized_bytes),
                "schema_estimated_tokens": _positive_int(schema_estimated_tokens),
                "estimator_ref": opaque_ref(estimator_ref),
                "fingerprint_key_id": _safe_key_id(fingerprint_key_id) or "fpk_" + "0" * 32,
            },
            **envelope,
        )

    # -- contract semantics ---------------------------------------------------------
    def contract(
        self,
        *,
        event_type: str,
        status: str,
        origin_message_id: Any = None,
        revision: Any = None,
        artifact_ref: Any = None,
        project_root: Any = None,
        before_sha256: str | None = None,
        after_sha256: str | None = None,
        decision_refs: tuple[str, ...] = (),
        supersedes_decision_ref: Any = None,
        evidence_refs: tuple[str, ...] = (),
        ambiguity_ref: Any = None,
        invariant_key: str | None = None,
        semantic_delta: str | None = None,
        **envelope: Any,
    ) -> dict[str, Any]:
        block = {
            "origin_message_id": origin_message_id
            if is_native_message_id(origin_message_id)
            else None,
            "revision": _strict_positive_int(revision),
            "artifact_ref": relative_artifact_ref(artifact_ref, project_root),
            "before_sha256": _safe_digest(before_sha256),
            "after_sha256": _safe_digest(after_sha256),
            "decision_refs": _safe_refs(decision_refs),
            "supersedes_decision_ref": safe_ref(supersedes_decision_ref),
            "evidence_refs": _safe_artifact_refs(evidence_refs, project_root),
            "ambiguity_ref": safe_ref(ambiguity_ref),
            "invariant_key": invariant_key
            if isinstance(invariant_key, str) and _INVARIANT_RE.fullmatch(invariant_key)
            else None,
            "semantic_delta": semantic_delta
            if semantic_delta
            in ("decision", "evidence", "ambiguity", "invariant", "revision", "none")
            else None,
        }
        return self.build(event_type, status=status, contract=block, **envelope)


def _actor(kind: str, actor_id: str, profile: str | None, role: str | None) -> dict[str, Any]:
    return {
        "kind": kind if kind in ("owner", "agent", "subagent", "system") else "system",
        "id": (safe_ref(actor_id) or "unknown")[:128],
        "profile": safe_ref(profile),
        "role": safe_ref(role),
    }
