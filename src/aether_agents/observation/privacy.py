"""Allowlist projection and forbidden-content guards.

Normative source: ``specs/002-aether-contract-observation/spec.md`` section 8.3 and
section 6.1. Observation events are built field by field from a bounded allowlist, so
this module is defence in depth after projection — never permission to persist a
forbidden field.

The guard runs before any write, debug log, queue, retry buffer, or exception report:
a rejected payload must not leak through the diagnostic path either.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import PurePosixPath, PureWindowsPath
from typing import Any, Final, Literal

from aether_agents.observation.contracts import (
    is_artifact_ref,
    is_native_message_id,
    is_opaque_ref,
)

__all__ = [
    "FORBIDDEN_KEYS",
    "ForbiddenPayload",
    "NativePseudonymKind",
    "assert_clean",
    "contains_secret_shape",
    "is_native_kanban_source_hook",
    "is_native_source_hook",
    "native_agent_task_ref",
    "native_kanban_task_ref",
    "native_pseudonym_ref",
    "native_profile_ref",
    "native_run_id",
    "is_clean",
    "relative_artifact_ref",
    "safe_error_class",
    "safe_ref",
    "scan",
]


class ForbiddenPayload(ValueError):
    """Raised when a value that must never be persisted reaches a serializer."""

    def __init__(self, reason_code: str, location: str) -> None:
        # The message names the location and the reason code only. It never quotes the
        # offending value, because exception text is itself a persistence boundary.
        super().__init__(f"{reason_code} at {location}")
        self.reason_code = reason_code
        self.location = location


#: Native payload keys that must be discarded during projection (section 6.1) plus the
#: content-bearing SessionDB/Kanban columns the reconciler must never copy.
FORBIDDEN_KEYS: Final[frozenset[str]] = frozenset(
    {
        # Hermes tool payloads
        "args",
        "arguments",
        "result",
        "results",
        "error_message",
        "middleware_trace",
        "user_task",
        "tool_args",
        "tool_result",
        "raw_result",
        # Model traffic
        "prompt",
        "prompts",
        "system_prompt",
        "response",
        "responses",
        "completion",
        "message",
        "messages",
        "content",
        "text",
        "reasoning",
        "reasoning_content",
        "thinking",
        "chain_of_thought",
        "api_content",
        "request_body",
        "response_body",
        "delta",
        # Delegation / subagents
        "goal",
        "child_goal",
        "tool_history",
        "transcript",
        "history",
        # Kanban / SessionDB text and blobs
        "body",
        "task_body",
        "description",
        "summary",
        "run_summary",
        "run_metadata",
        "run_error",
        "error",
        "error_text",
        "reason",
        "block_reason",
        "payload",
        "event_payload",
        "comments",
        "attachments",
        "origin_json",
        "display_metadata",
        "tool_call_json",
        "tool_calls",
        "workspace_path",
        "handoff_error",
        # Terminal, web, files
        "command",
        "cmd",
        "argv",
        "stdout",
        "stderr",
        "output",
        "diff",
        "patch",
        "file_content",
        "contents",
        "query",
        "search_query",
        "page_content",
        "html",
        "url",
        # Secrets
        "secret",
        "secrets",
        "token",
        "tokens_raw",
        "access_token",
        "refresh_token",
        "api_key",
        "apikey",
        "key",
        "private_key",
        "password",
        "passwd",
        "credential",
        "credentials",
        "credential_id",
        "cookie",
        "cookies",
        "authorization",
        "auth",
        "session_key",
        "fingerprint_key",
        "hmac_input",
    }
)

#: Substrings that mark a key as secret-shaped even under an unexpected native name.
_FORBIDDEN_KEY_SUBSTRINGS: Final = (
    "password",
    "passphrase",
    "secret",
    "api_key",
    "apikey",
    "private_key",
    "access_token",
    "refresh_token",
    "bearer",
    "cookie",
    "credential",
)

#: Keys that legitimately end in a forbidden substring but carry only bounded metadata.
_KEY_ALLOWLIST: Final = frozenset(
    {
        "fingerprint_key_id",
        "tokens",
        "input_tokens",
        "output_tokens",
        "cache_read_tokens",
        "cache_write_tokens",
        "reasoning_tokens",
        "total_tokens",
        "token_coverage",
        "schema_estimated_tokens",
        "key",  # rejected by FORBIDDEN_KEYS; listed here only for reader clarity
    }
    - {"key"}
)

_HOME_PATH_RE: Final = re.compile(r"(?:^|[\s\"'=:])(?:/home/[^/\s]+|/Users/[^/\s]+|/root)(?:/|\b)")
_WINDOWS_HOME_RE: Final = re.compile(r"[A-Za-z]:\\+Users\\+[^\\\s]+", re.IGNORECASE)

#: Common credential shapes. Bounded and deterministic; construction is the real defence.
_SECRET_VALUE_RES: Final = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
)


def contains_secret_shape(value: Any) -> bool:
    """Whether a string contains a recognized credential value shape."""
    return isinstance(value, str) and any(pattern.search(value) for pattern in _SECRET_VALUE_RES)


#: A projected metadata string is short by construction. Anything longer is prose.
MAX_METADATA_STRING = 512

_ERROR_CLASS_RES: Final = (
    # Native exception class names carry a type-shaped provenance signal.
    re.compile(
        r"^(?:[A-Z][A-Za-z0-9]{0,110}(?:Error|Exception|Warning)|Exception|Warning)$",
        re.ASCII,
    ),
    # Product/OS reason codes use a closed, visibly code-shaped grammar.
    re.compile(r"^(?:[A-Z][A-Z0-9]*)(?:_[A-Z][A-Z0-9]*)+$", re.ASCII),
    re.compile(r"^E[A-Z0-9]{1,31}$", re.ASCII),
    # Namespaced native codes have at least one explicit namespace separator.
    re.compile(
        r"^[a-z][a-z0-9_]*(?:[.:][a-z][a-z0-9_]*)+$",
        re.ASCII,
    ),
)
_EMAIL_RE: Final = re.compile(
    r"(?<![A-Za-z0-9._%+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
)
_URI_RE: Final = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*://")
_WINDOWS_ABSOLUTE_RE: Final = re.compile(r"^[A-Za-z]:[\\/]")
_REFERENCE_KEYS: Final = frozenset({"id"})
_ARTIFACT_REFERENCE_KEYS: Final = frozenset({"artifact_ref"})
_TARGET_REFERENCE_KEYS: Final = frozenset({"target_ref"})
_ARTIFACT_REFERENCE_LIST_KEYS: Final = frozenset({"evidence_refs"})
_NATIVE_MESSAGE_ID_KEYS: Final = frozenset({"message_id", "origin_message_id"})
_INVARIANT_KEY_LOCATION_RE: Final = re.compile(r"(?:^|\.)invariants\[[0-9]+\]\.key$")
_INVARIANT_KEY_RE: Final = re.compile(r"^OBS-INV-[0-9]{3}$", re.ASCII)

# Locked Hermes v2026.8.18 identity grammars.  These helpers are intentionally
# separate from ``safe_ref``: product-owned contract/work-unit references remain
# opaque identifiers, while values claimed to originate at a Hermes native boundary
# must have a shape that that producer can actually generate.
_NATIVE_KANBAN_TASK_RE: Final = re.compile(r"^t_[a-f0-9]{8}$", re.ASCII)
_NATIVE_AGENT_TASK_RE: Final = re.compile(
    r"^(?:t_[a-f0-9]{8}|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$",
    re.ASCII,
)
_NATIVE_PROFILE_RE: Final = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$", re.ASCII)
NativePseudonymKind = Literal[
    "session",
    "turn",
    "api_request",
    "tool_call",
    "approval_request",
]
_NATIVE_PSEUDONYM_PREFIXES: Final[dict[NativePseudonymKind, str]] = {
    "session": "sid",
    "turn": "trn",
    "api_request": "api",
    "tool_call": "call",
    "approval_request": "apr",
}
_NATIVE_PSEUDONYM_RE: Final = re.compile(
    r"^(?:sid|trn|api|call|apr)_fpk_[a-f0-9]{32}_[a-f0-9]{64}$",
    re.ASCII,
)
_NATIVE_KANBAN_SOURCE_HOOKS: Final = frozenset(
    {
        "kanban_read",
        "post_tool_call",
        "kanban_task_claimed",
        "kanban_task_completed",
        "kanban_task_blocked",
        "on_kanban_worker_spawned",
        "on_kanban_worker_exited",
        "on_kanban_worker_stale_claim",
        "on_kanban_task_updated",
    }
)
_NATIVE_SOURCE_HOOKS: Final = frozenset(
    {
        "kanban_read",
        "on_session_start",
        "on_session_end",
        "on_session_finalize",
        "on_session_reset",
        "pre_api_request",
        "post_api_request",
        "api_request_error",
        "pre_tool_call",
        "post_tool_call",
        "pre_approval_request",
        "post_approval_response",
        "subagent_start",
        "subagent_stop",
        "kanban_task_claimed",
        "kanban_task_completed",
        "kanban_task_blocked",
        "on_kanban_worker_spawned",
        "on_kanban_worker_exited",
        "on_kanban_worker_stale_claim",
        "on_kanban_task_updated",
        "on_kanban_dispatch_tick",
        "on_skill_lifecycle",
    }
)
_WORK_UNIT_EVENTS: Final = frozenset(
    {
        "work_unit.bound",
        "work_unit.unbound",
        "work_unit.status",
        "run.started",
        "run.finished",
    }
)


def _normalize_key(key: str) -> str:
    return key.strip().lower()


def _key_is_forbidden(key: str) -> bool:
    if key in _KEY_ALLOWLIST:
        return False
    if key in FORBIDDEN_KEYS:
        return True
    return any(fragment in key for fragment in _FORBIDDEN_KEY_SUBSTRINGS)


def _value_reason(value: str) -> str | None:
    if len(value) > MAX_METADATA_STRING:
        return "OVERSIZED_STRING"
    if not value.isascii():
        return "NON_ASCII_METADATA"
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        return "CONTROL_CHARACTER"
    if value.startswith("/") or _WINDOWS_ABSOLUTE_RE.match(value):
        return "ABSOLUTE_MACHINE_PATH"
    if _HOME_PATH_RE.search(value) or _WINDOWS_HOME_RE.search(value):
        return "ABSOLUTE_HOME_PATH"
    if _URI_RE.match(value):
        return "URI_SHAPED_VALUE"
    if _EMAIL_RE.search(value):
        return "EMAIL_SHAPED_VALUE"
    if contains_secret_shape(value):
        return "SECRET_SHAPED_VALUE"
    return None


def _reference_reason(key: str, value: Any) -> str | None:
    """Validate reference-bearing shapes before recursively scanning their values."""
    if key == "error_class":
        if value is not None and safe_error_class(value) != value:
            return "INVALID_ERROR_CLASS"
        return None
    if key in _NATIVE_MESSAGE_ID_KEYS:
        if value is not None and not is_native_message_id(value):
            return "INVALID_NATIVE_MESSAGE_ID"
        return None
    if key.endswith("run_id"):
        if value is not None and (
            not isinstance(value, int) or isinstance(value, bool) or value < 1
        ):
            return "INVALID_NATIVE_RUN_ID"
        return None
    if key in _ARTIFACT_REFERENCE_KEYS:
        if value is not None and not is_artifact_ref(value):
            return "INVALID_ARTIFACT_REFERENCE"
        return None
    if key in _TARGET_REFERENCE_KEYS:
        if value is not None and not (is_artifact_ref(value) or is_opaque_ref(value, max_len=256)):
            return "INVALID_OPAQUE_REFERENCE"
        return None
    if key in _ARTIFACT_REFERENCE_LIST_KEYS:
        if not isinstance(value, (list, tuple)) or any(not is_artifact_ref(item) for item in value):
            return "INVALID_ARTIFACT_REFERENCE"
        return None
    if key.endswith("_refs"):
        if not isinstance(value, (list, tuple)) or any(
            not is_opaque_ref(item, max_len=256) for item in value
        ):
            return "INVALID_OPAQUE_REFERENCE"
        return None
    if key in _REFERENCE_KEYS or key.endswith("_id") or key.endswith("_ref"):
        if value is not None and not is_opaque_ref(value, max_len=256):
            return "INVALID_OPAQUE_REFERENCE"
    return None


def scan(payload: Any, location: str = "$") -> tuple[str, str] | None:
    """Return ``(reason_code, location)`` for the first violation, else ``None``."""
    if isinstance(payload, dict):
        native_source_kind = payload.get("source_kind")
        if native_source_kind == "native_reconciliation" and not is_native_source_hook(
            payload.get("source_hook")
        ):
            return "INVALID_NATIVE_SOURCE_PROVENANCE", f"{location}.source_hook"
        native_event = native_source_kind in {
            "hermes_hook",
            "native_reconciliation",
        } and is_native_source_hook(payload.get("source_hook"))
        if native_event:
            task_id = payload.get("task_id")
            if task_id is not None and native_agent_task_ref(task_id) is None:
                return "INVALID_NATIVE_AGENT_TASK_ID", f"{location}.task_id"
            for key, kind in (
                ("session_id", "session"),
                ("turn_id", "turn"),
                ("api_request_id", "api_request"),
            ):
                value = payload.get(key)
                if value is not None and native_pseudonym_ref(value, kind=kind) is None:
                    return "INVALID_NATIVE_PSEUDONYM", f"{location}.{key}"
            actor = payload.get("actor")
            if isinstance(actor, dict):
                profile = actor.get("profile")
                if profile is not None and native_profile_ref(profile) is None:
                    return "INVALID_NATIVE_PROFILE_ID", f"{location}.actor.profile"
                if payload.get("source_hook") in {"subagent_start", "subagent_stop"} and (
                    actor.get("kind") == "subagent"
                ):
                    if native_pseudonym_ref(actor.get("id"), kind="session") is None:
                        return "INVALID_NATIVE_PSEUDONYM", f"{location}.actor.id"
            if payload.get("event_type") in {
                "tool.started",
                "tool.completed",
                "tool.failed",
                "tool.blocked",
                "tool.cancelled",
                "tool.timed_out",
                "tool.interrupted",
            }:
                tool = payload.get("tool")
                if (
                    not isinstance(tool, dict)
                    or native_pseudonym_ref(tool.get("call_id"), kind="tool_call") is None
                ):
                    return "INVALID_NATIVE_PSEUDONYM", f"{location}.tool.call_id"
                retry_of = tool.get("retry_of_call_id")
                if (
                    retry_of is not None
                    and native_pseudonym_ref(retry_of, kind="tool_call") is None
                ):
                    return "INVALID_NATIVE_PSEUDONYM", (f"{location}.tool.retry_of_call_id")
            if payload.get("source_hook") in {"subagent_start", "subagent_stop"}:
                tool = payload.get("tool")
                if isinstance(tool, dict):
                    if native_pseudonym_ref(tool.get("call_id"), kind="session") is None:
                        return "INVALID_NATIVE_PSEUDONYM", f"{location}.tool.call_id"
                    target_ref = tool.get("target_ref")
                    if (
                        target_ref is not None
                        and native_pseudonym_ref(target_ref, kind="session") is None
                    ):
                        return "INVALID_NATIVE_PSEUDONYM", f"{location}.tool.target_ref"
                configuration = payload.get("configuration")
                if isinstance(configuration, dict):
                    participant_ref = configuration.get("participant_ref")
                    if (
                        participant_ref is not None
                        and native_pseudonym_ref(participant_ref, kind="session") is None
                    ):
                        return "INVALID_NATIVE_PSEUDONYM", (
                            f"{location}.configuration.participant_ref"
                        )
            model_request = payload.get("model_request")
            if (
                isinstance(model_request, dict)
                and native_pseudonym_ref(model_request.get("request_ref"), kind="api_request")
                is None
            ):
                return "INVALID_NATIVE_PSEUDONYM", (f"{location}.model_request.request_ref")
            tool_surface = payload.get("tool_surface")
            if (
                isinstance(tool_surface, dict)
                and native_pseudonym_ref(tool_surface.get("request_ref"), kind="api_request")
                is None
            ):
                return "INVALID_NATIVE_PSEUDONYM", f"{location}.tool_surface.request_ref"
            if payload.get("source_hook") in {
                "pre_approval_request",
                "post_approval_response",
            }:
                wait = payload.get("wait")
                if (
                    isinstance(wait, dict)
                    and native_pseudonym_ref(wait.get("wait_id"), kind="approval_request") is None
                ):
                    return "INVALID_NATIVE_PSEUDONYM", f"{location}.wait.wait_id"
        # Schema/projector parity for events emitted from a locked native Kanban
        # boundary.  Do not apply this rule to product-owned checkpoint references.
        if (
            payload.get("event_type") in _WORK_UNIT_EVENTS
            and payload.get("source_hook") in _NATIVE_KANBAN_SOURCE_HOOKS
        ):
            task_id = payload.get("task_id")
            unit = payload.get("work_unit")
            if native_kanban_task_ref(task_id) is None:
                return "INVALID_NATIVE_KANBAN_TASK_ID", f"{location}.task_id"
            if not isinstance(unit, dict) or native_kanban_task_ref(unit.get("task_ref")) is None:
                return "INVALID_NATIVE_KANBAN_TASK_ID", f"{location}.work_unit.task_ref"
            parents = unit.get("parent_task_refs")
            if not isinstance(parents, (list, tuple)) or any(
                native_kanban_task_ref(parent) is None for parent in parents
            ):
                return "INVALID_NATIVE_KANBAN_PARENT_ID", (f"{location}.work_unit.parent_task_refs")
            actor = payload.get("actor")
            if isinstance(actor, dict):
                profile = actor.get("profile")
                if profile is not None and native_profile_ref(profile) is None:
                    return "INVALID_NATIVE_PROFILE_ID", f"{location}.actor.profile"
        for index, (raw_key, value) in enumerate(payload.items()):
            if (
                not isinstance(raw_key, str)
                or not is_opaque_ref(raw_key)
                or _value_reason(raw_key) is not None
            ):
                return "INVALID_METADATA_KEY", f"{location}.<field_{index}>"
            key = _normalize_key(raw_key)
            where = f"{location}.{raw_key}"
            invariant_key = key == "key" and _INVARIANT_KEY_LOCATION_RE.search(where)
            if invariant_key and (
                not isinstance(value, str) or _INVARIANT_KEY_RE.fullmatch(value) is None
            ):
                return "INVALID_INVARIANT_KEY", where
            if not invariant_key and _key_is_forbidden(key):
                return "FORBIDDEN_KEY", where
            reference_reason = _reference_reason(key, value)
            if reference_reason is not None:
                return reference_reason, where
            found = scan(value, where)
            if found is not None:
                return found
        return None
    if isinstance(payload, (list, tuple)):
        for index, value in enumerate(payload):
            found = scan(value, f"{location}[{index}]")
            if found is not None:
                return found
        return None
    if isinstance(payload, str):
        reason = _value_reason(payload)
        if reason is not None:
            return reason, location
        return None
    if isinstance(payload, bytes):
        return "RAW_BYTES", location
    if payload is None or isinstance(payload, (bool, int, float, date, datetime)):
        return None
    return "UNSUPPORTED_METADATA_TYPE", location


def is_clean(payload: Any) -> bool:
    return scan(payload) is None


def assert_clean(payload: Any, location: str = "$") -> None:
    """Raise :class:`ForbiddenPayload` when ``payload`` carries anything prohibited."""
    found = scan(payload, location)
    if found is not None:
        raise ForbiddenPayload(*found)


def safe_ref(value: Any, *, max_len: int = 128) -> str | None:
    """Keep a typed opaque identifier; never stringify or truncate native content."""
    if not is_opaque_ref(value, max_len=max_len):
        return None
    return value if _value_reason(value) is None else None


def native_kanban_task_ref(value: Any) -> str | None:
    """Return an exact v2026.8.18 Kanban task ID, never generic metadata."""
    return value if isinstance(value, str) and _NATIVE_KANBAN_TASK_RE.fullmatch(value) else None


def is_native_kanban_source_hook(value: Any) -> bool:
    """Whether a source hook is one locked Hermes Kanban identity boundary."""
    return isinstance(value, str) and value in _NATIVE_KANBAN_SOURCE_HOOKS


def is_native_source_hook(value: Any) -> bool:
    """Whether a source hook is emitted by the locked Hermes public surface."""
    return isinstance(value, str) and value in _NATIVE_SOURCE_HOOKS


def native_agent_task_ref(value: Any) -> str | None:
    """Return a task identity Hermes itself can place on agent/API/tool hooks.

    A Kanban worker carries its ``t_<8 hex>`` card identity.  An ordinary agent
    turn uses the canonical UUID generated in ``agent.turn_context``.
    """
    return value if isinstance(value, str) and _NATIVE_AGENT_TASK_RE.fullmatch(value) else None


def native_pseudonym_ref(
    value: Any,
    *,
    kind: NativePseudonymKind,
) -> str | None:
    """Return a project-keyed native-identity pseudonym of the requested kind.

    The embedded ``fpk_<epoch>`` makes a key rotation visible.  This function
    validates an already-keyed value; capture owns the HMAC operation.
    """
    if not isinstance(value, str) or _NATIVE_PSEUDONYM_RE.fullmatch(value) is None:
        return None
    prefix = _NATIVE_PSEUDONYM_PREFIXES[kind] + "_"
    return value if value.startswith(prefix) else None


def native_profile_ref(value: Any) -> str | None:
    """Return a canonical Hermes profile ID from the locked profile grammar."""
    return value if isinstance(value, str) and _NATIVE_PROFILE_RE.fullmatch(value) else None


def native_run_id(value: Any) -> int | None:
    """Return a native positive SQLite run identity without bool coercion."""
    return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else None


def safe_error_class(value: Any) -> str | None:
    """Keep a stable error class or code; never raw error text.

    A native ``error_type`` such as ``TimeoutError`` or ``policy.denied`` passes through.
    A sentence, a traceback, or anything with whitespace is dropped entirely.
    """
    if value is None:
        return None
    if isinstance(value, type):
        value = value.__name__
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not any(pattern.fullmatch(text) for pattern in _ERROR_CLASS_RES):
        return None
    if _value_reason(text) is not None:
        return None
    return text


def opaque_ref(value: Any) -> str | None:
    """Reference constrained to the schema's generic reference pattern."""
    return safe_ref(value)


def relative_artifact_ref(path: Any, project_root: Any = None) -> str | None:
    """Project-relative artifact reference, or ``None`` when it cannot be made safe.

    Absolute home paths are forbidden metadata (section 8.3), so an absolute path is
    only ever emitted after it has been made relative to the project root.
    """
    if not isinstance(path, str) or not path or path != path.strip():
        return None
    raw = path
    if len(raw) > 512:
        return None

    if _URI_RE.match(raw) or raw.startswith(("\\\\", "//")):
        return None

    windows_absolute = _WINDOWS_ABSOLUTE_RE.match(raw) is not None
    if windows_absolute:
        # A native absolute Windows path is accepted only with an absolute Windows
        # project root, then emitted using the single canonical '/' separator.
        raw_parts = re.split(r"[\\/]", raw)
        if any(part in ("", ".", "..") for part in raw_parts[1:]):
            return None
        if project_root is None:
            return None
        root_text = str(project_root)
        if _WINDOWS_ABSOLUTE_RE.match(root_text) is None:
            return None
        pure = PureWindowsPath(raw)
        root = PureWindowsPath(root_text)
        try:
            pure = pure.relative_to(root)
        except ValueError:
            return None
    else:
        # Backslash is never an alternate separator in a persisted reference.
        if "\\" in raw:
            return None
        absolute = raw.startswith("/")
        parts = raw.split("/")
        meaningful = parts[1:] if absolute else parts
        if any(part in ("", ".", "..") for part in meaningful):
            return None
        pure = PurePosixPath(raw)
        if absolute:
            if project_root is None:
                return None
            root_text = str(project_root)
            if not root_text.startswith("/") or _WINDOWS_ABSOLUTE_RE.match(root_text):
                return None
            try:
                pure = pure.relative_to(PurePosixPath(root_text))
            except ValueError:
                return None

    relative = pure.as_posix()
    if not is_artifact_ref(relative) or _value_reason(relative) is not None:
        return None
    return relative
