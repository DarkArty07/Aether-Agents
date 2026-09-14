"""Semantic extraction lifecycle: bounded plan, route gate, accounting, composition.

The manager never applies a fragment itself. It prepares one private bounded plan
per compatible revision/policy, calls the auxiliary transport through the Hermes
session context, validates each candidate through the native worker, and composes
every accepted fragment once through the worker's `semantic_compose` protocol.

Protocol consumed here (owned by the native worker unit):

* `semantic_prepare` -> `chunks[]` with `chunk_id`, `files`, `system_prompt`,
  `user_prompt`, plus `total_chunks`/`has_more` for bounded paging.
* `semantic_validate` -> `fragment` for one model text (strict; no permissive
  parser lives in this module).
* `semantic_compose` -> one call carrying every accepted fragment as `fragments`
  (plus `allowed_sources`/`allow_empty`), returning at least `structural_digest`
  and `structural_preserved`. A false `structural_preserved` or a raised failure
  is reported as category `apply` and composes nothing.
"""

from __future__ import annotations

import concurrent.futures
import contextlib
import contextvars
import hashlib
import json
import logging
import re
import threading
import time
from collections import deque
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

from aether_agents.paths import atomic_private_write, ensure_private_dir

from .common import KnowledgeError
from .context import KnowledgeContext
from .graphify import GraphifyBackend

logger = logging.getLogger(__name__)

# Extensions eligible for semantic extraction (docs and source code)
_ELIGIBLE_EXTENSIONS = frozenset(
    ".md .txt .rst .py .js .jsx .ts .tsx .go .rs .java .c .h .cpp .hpp .cs .rb .php .swift .kt .sql .html".split()
)

# Persisted identity. Semantic snapshots/cache entries are trusted only when they
# carry this pipeline/cache identity; legacy entries are re-derived, never assumed.
PIPELINE_VERSION = "aether.semantic-pipeline.v2"
CACHE_VERSION = "aether.semantic-cache.v2"
PLAN_SCHEMA = "aether.semantic-plan.v1"
SCOPE_VERSION = "regular-tracked-v1"
SEMANTIC_POLICY: dict[str, Any] = {"deep": False, "token_budget": 4000}

# The former 600-second default is withdrawn: one configured update has a single
# total budget of at most 300 seconds from entry through return.
MAX_TOTAL_BUDGET_SECONDS = 300.0
DEFAULT_TOTAL_BUDGET_SECONDS = 300.0
# Time kept for validation/composition before another model call may start.
FINALIZATION_RESERVE_SECONDS = 5.0
MAX_AUXILIARY_CONCURRENCY = 2
SCHEDULER_POLL_SECONDS = 0.05
AUXILIARY_ATTEMPT_LIMIT = 2  # one bounded transient retry per chunk
AUXILIARY_TIMEOUT_SECONDS = 180.0
CANCEL_DRAIN_SECONDS = 5.0
# Plan/cache records stay size/path bounded: content never enters them.
MAX_PLAN_BYTES = 1_000_000
MAX_PLAN_ACCEPTED_BASES = 8
MAX_TOOL_CALLS = 2
MAX_MODEL_ARGUMENT_CHARS = 1_000_000
MAX_BOUNDED_COUNT = 2_000_000_000
STRUCTURED_FRAGMENT_TOOL = "submit_graph_fragment"

_CATEGORY_NAMES = (
    # Canonical outcome categories (content-free).
    "empty",
    "incomplete",
    "malformed_json",
    "schema",
    "source",
    "route",
    "cache",
    "apply",
    "deadline",
    # Compatibility aliases retained for existing receipts.
    "deadline_deferred",
    "auxiliary_failed",
    "validation_failed",
    "apply_failed",
)

_REASON_NAMES = (
    "unresolved_route",
    "route_mismatch",
    "deadline",
    "transport_error",
    "router_exhaustion",
    "content_filter",
    "cancelled_response",
    "max_output_tokens",
    "commentary_only",
    "response_failed",
    "unexpected_tool_call",
    "multiple_structured_calls",
    "structured_call_disabled",
    "ambiguous_response",
    "unknown_finish_reason",
    "empty_text",
    "not_scheduled",
    "hollow",
    "malformed_json",
    "schema",
    "source",
    "unqualified_cache_entry",
    "plan_mismatch",
    "prepare_failed",
    "worker_error",
    "structural_not_preserved",
    "compose_error",
)


# ── Small bounded helpers ─────────────────────────────────────────────────


def _now() -> float:
    """Monotonic clock for the total budget (patchable in tests)."""
    return time.monotonic()


def _bounded_int(value: Any) -> int:
    """Non-negative bounded integer for receipts; never a raw payload field."""
    try:
        number = int(value)
    except (TypeError, ValueError):
        return 0
    if number <= 0:
        return 0
    return min(number, MAX_BOUNDED_COUNT)


def _bounded_text(value: Any, limit: int = 64) -> str:
    """Short content-free label for classification and receipts."""
    if value is None:
        return ""
    return str(value).strip()[:limit]


def _is_router_exhaustion(error: Exception | None) -> bool:
    return isinstance(error, KnowledgeError) and error.code == "ROUTER_EXHAUSTION"


def _strict_json_parses(model_text: str) -> bool:
    """Probe only: exactly one optional fenced block, no repair, no coercion."""
    candidate = (model_text or "").strip()
    if candidate.startswith("```"):
        match = re.fullmatch(r"```(?:json)?\s*(\{.*\})\s*```", candidate, re.DOTALL)
        if match is None:
            return False
        candidate = match.group(1)
    try:
        json.loads(candidate)
    except (ValueError, TypeError, RecursionError):
        return False
    return True


def _failure_label(error: BaseException | None) -> str:
    """Bounded, content-free failure label: error code and exception type only."""
    if error is None:
        return "none"
    code = getattr(error, "code", "")
    if code:
        return _bounded_text(code, 48)
    return type(error).__name__[:48]


def _structured_call_text(meta: dict[str, Any]) -> str:
    """Exactly one expected structured fragment call is an eligible payload."""
    calls = meta.get("tool_calls")
    if not isinstance(calls, list):
        return ""
    for call in calls:
        if not isinstance(call, dict) or call.get("name") != STRUCTURED_FRAGMENT_TOOL:
            continue
        arguments = call.get("arguments")
        if isinstance(arguments, str) and arguments.strip():
            return arguments
    return ""


# ── Fingerprints and route resolution ─────────────────────────────────────


def compute_chunk_fingerprint(
    scope_version: str,
    prompt_text: str,
    policy: dict[str, Any],
    model_identity_digest: str,
    chunk_file_hashes: dict[str, str],
) -> str:
    """Calculate deterministic chunk fingerprint across all inputs and extraction policies."""
    hasher = hashlib.sha256()
    hasher.update(scope_version.encode("utf-8"))
    hasher.update(prompt_text.encode("utf-8"))
    hasher.update(json.dumps(policy, sort_keys=True).encode("utf-8"))
    hasher.update(model_identity_digest.encode("utf-8"))
    for path, fhash in sorted(chunk_file_hashes.items()):
        hasher.update(f"{path}:{fhash}".encode("utf-8"))
    return hasher.hexdigest()


def get_model_identity_digest(
    task: str,
    provider: str | None = None,
    model: str | None = None,
    api_mode: str | None = None,
) -> str:
    """Non-secret digest of model, provider, api_mode, and task binding."""
    identity = f"{task}:{provider or 'default'}:{model or 'default'}:{api_mode or 'default'}"
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def resolve_auxiliary_route(
    configuration: dict[str, Any],
    task: str | None = None,
) -> dict[str, str | None]:
    """Resolve non-secret concrete auxiliary route (provider, model, api_mode)."""
    task = task or resolve_auxiliary_task(configuration)
    semantic_cfg = configuration.get("semantic", {})
    if not isinstance(semantic_cfg, dict):
        semantic_cfg = {}

    provider = (
        semantic_cfg.get("provider")
        or configuration.get("semantic_provider")
        or configuration.get("provider")
    )
    model = (
        semantic_cfg.get("model")
        or configuration.get("semantic_model")
        or configuration.get("model")
    )
    api_mode = (
        semantic_cfg.get("api_mode")
        or configuration.get("semantic_api_mode")
        or configuration.get("api_mode")
    )

    if provider is not None:
        provider = str(provider).strip() or None
    if model is not None:
        model = str(model).strip() or None
    if api_mode is not None:
        api_mode = str(api_mode).strip() or None

    # Try resolving via Hermes auxiliary client if available and details are missing
    try:
        from agent.auxiliary_client import (  # type: ignore[import-not-found,import-untyped]  # pyright: ignore[reportMissingImports]
            _read_main_model,
            _read_main_provider,
            _resolve_task_provider_model,
        )

        res_provider, res_model, _base_url, _api_key, res_api_mode = _resolve_task_provider_model(
            task=task,
            provider=provider,
            model=model,
        )
        if provider is None and res_provider:
            if res_provider == "auto":
                main_p = _read_main_provider()
                provider = str(main_p).strip() if main_p else "auto"
            else:
                provider = str(res_provider).strip()

        if model is None and res_model:
            model = str(res_model).strip()
        elif model is None and provider and provider != "auto":
            main_m = _read_main_model()
            if main_m:
                model = str(main_m).strip()

        if api_mode is None and res_api_mode:
            api_mode = str(res_api_mode).strip()
    except Exception:
        pass

    if not api_mode and provider and provider not in ("auto", "unresolved"):
        if provider.lower() in ("anthropic", "claude"):
            api_mode = "anthropic_messages"
        else:
            api_mode = "chat_completions"

    return {
        "provider": provider or "default",
        "model": model or "default",
        "api_mode": api_mode or "default",
    }


def is_route_resolved(route: dict[str, Any] | None) -> bool:
    """Verify that concrete non-secret provider, model, and api_mode are resolved."""
    if not route or not isinstance(route, dict):
        return False
    provider = route.get("provider")
    model = route.get("model")
    api_mode = route.get("api_mode")
    if not provider or not model or not api_mode:
        return False
    unresolved_markers = {"", "none", "null", "auto", "unresolved"}
    if any(str(v).strip().casefold() in unresolved_markers for v in (provider, model, api_mode)):
        return False
    return True


def routes_match(expected: dict[str, Any] | None, actual: dict[str, Any] | None) -> bool:
    """Check if actual route matches expected route."""
    if not expected or not actual or not isinstance(expected, dict) or not isinstance(actual, dict):
        return False
    for k in ("provider", "model", "api_mode"):
        exp_v = expected.get(k)
        act_v = actual.get(k)
        if exp_v and act_v:
            if str(exp_v).strip().casefold() != str(act_v).strip().casefold():
                return False
    return True


def routes_match_strictly(expected: dict[str, Any] | None, actual: dict[str, Any] | None) -> bool:
    """Primary-only route qualification: every identity field must match exactly."""
    if not is_route_resolved(expected) or not is_route_resolved(actual):
        return False
    assert expected is not None and actual is not None  # narrowed above
    for key in ("provider", "model", "api_mode"):
        expected_value = str(expected.get(key) or "").strip().casefold()
        actual_value = str(actual.get(key) or "").strip().casefold()
        if expected_value != actual_value:
            return False
    return True


def resolve_auxiliary_task(configuration: dict[str, Any]) -> str | None:
    """Resolve auxiliary task name or None if missing/auto/ambiguous."""
    semantic_cfg = configuration.get("semantic", {})
    task_a = None
    if isinstance(semantic_cfg, dict):
        raw_a = semantic_cfg.get("auxiliary_task")
        if raw_a is not None:
            task_a = str(raw_a).strip()
    raw_b = configuration.get("semantic_auxiliary_task")
    task_b = str(raw_b).strip() if raw_b is not None else None

    # Check ambiguity: if both provided and different
    if task_a is not None and task_b is not None and task_a != task_b:
        return None

    task = task_a if task_a is not None else task_b
    if not task:
        return None
    if task.casefold() in ("", "auto", "none", "null"):
        return None
    return task


# ── Total budget ──────────────────────────────────────────────────────────


def resolve_total_budget(configuration: dict[str, Any], deadline_seconds: float | None) -> float:
    """Resolve the total monotonic budget; configuration may only lower 300s."""
    candidate: Any = (
        deadline_seconds if deadline_seconds is not None else DEFAULT_TOTAL_BUDGET_SECONDS
    )
    configured = configuration.get(
        "semantic_deadline_seconds", configuration.get("deadline_seconds")
    )
    if configured is not None:
        candidate = configured
    try:
        requested = float(candidate)
    except (TypeError, ValueError):
        requested = DEFAULT_TOTAL_BUDGET_SECONDS
    return max(0.0, min(requested, MAX_TOTAL_BUDGET_SECONDS))


def finalization_reserve(budget_seconds: float) -> float:
    """Reserve time for validation/composition inside the total budget."""
    return min(FINALIZATION_RESERVE_SECONDS, budget_seconds * 0.5)


# ── Private bounded plan ──────────────────────────────────────────────────


def _inputs_digest(inputs: dict[str, str]) -> str:
    hasher = hashlib.sha256()
    for path, fhash in sorted(inputs.items()):
        hasher.update(f"{path}:{fhash}".encode("utf-8"))
    return hasher.hexdigest()


def _structural_base_reference(graph_path: Path | None, revision: str) -> dict[str, Any]:
    """Content-free structural-base reference: digest, byte size and revision."""
    digest = hashlib.sha256(b"").hexdigest()
    size = 0
    if graph_path is not None:
        try:
            if graph_path.is_file():
                payload = graph_path.read_bytes()
                digest = hashlib.sha256(payload).hexdigest()
                size = len(payload)
        except OSError:
            pass
    return {"digest": digest, "bytes": size, "revision": str(revision or "")}


def plan_identity(
    *,
    scope_version: str,
    policy: dict[str, Any],
    model_digest: str,
    auxiliary_task: str,
    inputs_digest: str,
) -> str:
    """One plan per compatible revision/policy/route/input identity."""
    hasher = hashlib.sha256()
    hasher.update(PLAN_SCHEMA.encode("utf-8"))
    hasher.update(PIPELINE_VERSION.encode("utf-8"))
    hasher.update(CACHE_VERSION.encode("utf-8"))
    hasher.update(scope_version.encode("utf-8"))
    hasher.update(json.dumps(policy, sort_keys=True).encode("utf-8"))
    hasher.update(model_digest.encode("utf-8"))
    hasher.update(auxiliary_task.encode("utf-8"))
    hasher.update(inputs_digest.encode("utf-8"))
    return hasher.hexdigest()


def build_plan_record(
    chunk: dict[str, Any],
    inputs: dict[str, str],
    *,
    model_digest: str,
    scope_version: str = SCOPE_VERSION,
    policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Size/path-bounded plan record: paths, sizes and digests only, never content."""
    policy = policy if policy is not None else SEMANTIC_POLICY
    files = [str(name) for name in chunk.get("files", [])]
    file_hashes = {name: inputs[name] for name in files if name in inputs}
    prompt_text = str(chunk.get("system_prompt") or "") + "\n" + str(chunk.get("user_prompt") or "")
    fingerprint = compute_chunk_fingerprint(
        scope_version, prompt_text, policy, model_digest, file_hashes
    )
    return {
        "chunk_id": int(chunk["chunk_id"]),
        "files": files,
        "bytes": len(prompt_text),
        "fingerprint": fingerprint,
    }


def build_plan(
    records: list[dict[str, Any]],
    inputs: dict[str, str],
    *,
    plan_id: str,
    model_digest: str,
    auxiliary_task: str,
    structural_base: dict[str, Any],
    scope_version: str = SCOPE_VERSION,
    policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble the persisted plan header around its bounded chunk records."""
    policy = policy if policy is not None else SEMANTIC_POLICY
    ordered = sorted(records, key=lambda record: int(record["chunk_id"]))
    return {
        "schema": PLAN_SCHEMA,
        "plan_id": plan_id,
        "pipeline_version": PIPELINE_VERSION,
        "cache_version": CACHE_VERSION,
        "scope_version": scope_version,
        "policy": dict(policy),
        "model_digest": model_digest,
        "auxiliary_task": auxiliary_task,
        "inputs_digest": _inputs_digest(inputs),
        "structural_base": dict(structural_base),
        "accepted_bases": [str(structural_base.get("digest") or "")],
        "chunks": ordered,
        "total_chunks": len(ordered),
        "created_at": _now(),
    }


def plan_matches(
    plan: dict[str, Any] | None,
    *,
    plan_id: str,
    model_digest: str,
    auxiliary_task: str,
    inputs_digest: str,
) -> bool:
    """A plan is compatible only on the same schema/versions/policy/route/inputs."""
    if not isinstance(plan, dict):
        return False
    if plan.get("schema") != PLAN_SCHEMA or plan.get("plan_id") != plan_id:
        return False
    if plan.get("pipeline_version") != PIPELINE_VERSION:
        return False
    if plan.get("cache_version") != CACHE_VERSION:
        return False
    if plan.get("scope_version") != SCOPE_VERSION:
        return False
    if plan.get("policy") != SEMANTIC_POLICY:
        return False
    if plan.get("model_digest") != model_digest:
        return False
    if plan.get("auxiliary_task") != auxiliary_task:
        return False
    if plan.get("inputs_digest") != inputs_digest:
        return False
    return isinstance(plan.get("chunks"), list)


def plan_accepts_structural_base(plan: dict[str, Any], digest: str) -> bool:
    """Accept the recorded structural base or a base this plan already composed from."""
    accepted = plan.get("accepted_bases")
    if isinstance(accepted, list) and digest in {str(item) for item in accepted}:
        return True
    base = plan.get("structural_base")
    return bool(isinstance(base, dict) and base.get("digest") == digest)


def note_structural_base(plan: dict[str, Any] | None, digest: str) -> None:
    """Remember a base this plan already composed from, bounded and newest-last."""
    if plan is None:
        return
    accepted = [str(item) for item in plan.get("accepted_bases", []) if item]
    if digest in accepted:
        return
    accepted.append(digest)
    plan["accepted_bases"] = accepted[-MAX_PLAN_ACCEPTED_BASES:]


class SemanticPlanStore:
    """Private staging for bounded plans; records never carry source content."""

    def __init__(self, plan_dir: Path):
        self.plan_dir = plan_dir

    def load(self, plan_id: str) -> dict[str, Any] | None:
        path = self.plan_dir / f"{plan_id}.json"
        if not path.is_file():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        return data if isinstance(data, dict) else None

    def save(self, plan: dict[str, Any]) -> bool:
        """Persist one plan; a plan above its byte bound stays in memory only."""
        payload = json.dumps(plan, indent=2, sort_keys=True).encode("utf-8")
        if len(payload) > MAX_PLAN_BYTES:
            logger.warning("Semantic plan exceeds its bounded size; keeping it in memory only.")
            return False
        ensure_private_dir(self.plan_dir)
        atomic_private_write(self.plan_dir / f"{plan['plan_id']}.json", payload)
        return True


def _plan_store_for_graph(graph_path: Path | None) -> SemanticPlanStore | None:
    """Locate the plan staging for a snapshot graph path without new arguments."""
    if graph_path is None:
        return None
    try:
        project_dir = graph_path.parents[1].parent
    except IndexError:
        return None
    if project_dir.parent.name != "knowledge":
        return None
    return SemanticPlanStore(project_dir / "semantic_plans")


def _overall_fingerprint(records: list[dict[str, Any]]) -> str:
    ordered = sorted(records, key=lambda record: int(record["chunk_id"]))
    return hashlib.sha256(
        "".join(str(record["fingerprint"]) for record in ordered).encode("utf-8")
    ).hexdigest()


# ── Auxiliary response boundary ───────────────────────────────────────────


def _extract_tool_calls(message: Any) -> list[dict[str, str]]:
    raw = getattr(message, "tool_calls", None)
    if raw is None and isinstance(message, dict):
        raw = message.get("tool_calls")
    calls: list[dict[str, str]] = []
    if not isinstance(raw, list):
        return calls
    for item in raw[:MAX_TOOL_CALLS]:
        name: Any = None
        arguments: Any = None
        if isinstance(item, dict):
            name = item.get("name")
            arguments = item.get("arguments")
            function = item.get("function")
            if isinstance(function, dict):
                name = name or function.get("name")
                arguments = arguments if arguments is not None else function.get("arguments")
        else:
            name = getattr(item, "name", None)
            arguments = getattr(item, "arguments", None)
            function = getattr(item, "function", None)
            if function is not None:
                name = name or getattr(function, "name", None)
                arguments = (
                    arguments if arguments is not None else getattr(function, "arguments", None)
                )
        if arguments is None:
            continue
        text = arguments if isinstance(arguments, str) else json.dumps(arguments)
        if len(text) > MAX_MODEL_ARGUMENT_CHARS:
            continue
        calls.append({"name": _bounded_text(name, 64), "arguments": text})
    return calls


def extract_response_boundary(response: Any) -> tuple[str, dict[str, Any]]:
    """Preserve terminal/phase/shape metadata; accept only unambiguous final text."""
    meta: dict[str, Any] = {}
    for key in ("status", "phase", "incomplete_reason", "finish_reason"):
        value = getattr(response, key, None)
        if value is None and isinstance(response, dict):
            value = response.get(key)
        if value is not None:
            meta[key] = _bounded_text(value, 64)

    choices = getattr(response, "choices", None)
    if choices is None and isinstance(response, dict):
        choices = response.get("choices")
    choice = choices[0] if isinstance(choices, (list, tuple)) and choices else None
    message = getattr(choice, "message", None)
    if message is None and isinstance(choice, dict):
        message = choice.get("message")

    if "finish_reason" not in meta and choice is not None:
        value = getattr(choice, "finish_reason", None)
        if value is None and isinstance(choice, dict):
            value = choice.get("finish_reason")
        if value is not None:
            meta["finish_reason"] = _bounded_text(value, 64)

    text = ""
    content = getattr(message, "content", None)
    if content is None and isinstance(message, dict):
        content = message.get("content")
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        parts: list[str] = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict) and isinstance(part.get("text"), str):
                parts.append(part["text"])
            elif isinstance(part, dict) and isinstance(part.get("content"), str):
                parts.append(part["content"])
        text = "".join(parts)

    if message is not None:
        calls = _extract_tool_calls(message)
        if calls:
            meta["tool_calls"] = calls

    if not text.strip():
        fallback: Any = getattr(response, "output_text", None)
        if fallback is None and isinstance(response, dict):
            fallback = response.get("output_text")
        if not isinstance(fallback, str) and choice is not None:
            candidate = getattr(choice, "output_text", None)
            fallback = candidate if isinstance(candidate, str) else fallback
        if isinstance(fallback, str) and fallback.strip():
            text = fallback
            meta["output_text_used"] = True
    return text, meta


def extract_response_usage(response: Any) -> dict[str, Any]:
    """Bounded input/output/reasoning/total usage; never a content field."""
    usage: dict[str, Any] = {}
    raw = getattr(response, "usage", None)
    if raw is None and isinstance(response, dict):
        raw = response.get("usage")
    if raw is None:
        return usage

    def read(*names: str) -> Any:
        for name in names:
            value = getattr(raw, name, None)
            if value is None and isinstance(raw, dict):
                value = raw.get(name)
            if value is not None:
                return value
        return None

    prompt = _bounded_int(read("prompt_tokens", "input_tokens"))
    completion = _bounded_int(read("completion_tokens", "output_tokens"))
    total = _bounded_int(read("total_tokens"))
    reasoning = _bounded_int(read("reasoning_tokens"))
    if reasoning == 0:
        reasoning = _bounded_int(
            getattr(read("completion_tokens_details"), "reasoning_tokens", None)
        )

    if prompt:
        usage["prompt_tokens"] = prompt
    if completion:
        usage["completion_tokens"] = completion
    if reasoning:
        usage["reasoning_tokens"] = reasoning
    if total or prompt or completion:
        usage["total_tokens"] = total or (prompt + completion)
    return usage


def classify_auxiliary_response(text: str, meta: dict[str, Any]) -> tuple[str, str | None]:
    """Decide eligibility. Incomplete/cancelled output can never become `stop`."""
    status = _bounded_text(meta.get("status")).casefold()
    phase = _bounded_text(meta.get("phase")).casefold()
    incomplete_reason = _bounded_text(meta.get("incomplete_reason")).casefold()
    finish_reason = _bounded_text(meta.get("finish_reason")).casefold()
    raw_tool_calls = meta.get("tool_calls")
    tool_calls: list[Any] = raw_tool_calls if isinstance(raw_tool_calls, list) else []
    has_text = bool(str(text or "").strip())

    if "cancel" in status or "cancel" in phase or "cancel" in incomplete_reason:
        return "cancelled", "cancelled_response"
    if "content_filter" in incomplete_reason or finish_reason == "content_filter":
        return "filtered", "content_filter"
    if "length" in incomplete_reason:
        return "incomplete", "max_output_tokens"
    if status in ("incomplete", "in_progress") or incomplete_reason:
        return "incomplete", incomplete_reason or status
    if status in ("failed", "error"):
        return "incomplete", "response_failed"
    if finish_reason in ("length", "max_tokens", "max_output_tokens"):
        return "incomplete", "max_output_tokens"
    if finish_reason and finish_reason not in ("stop", "tool_calls"):
        return "incomplete", "unknown_finish_reason"

    expected_calls = [
        call
        for call in tool_calls
        if isinstance(call, dict) and call.get("name") == STRUCTURED_FRAGMENT_TOOL
    ]
    other_calls = [
        call
        for call in tool_calls
        if isinstance(call, dict) and call.get("name") != STRUCTURED_FRAGMENT_TOOL
    ]
    if other_calls:
        return "incomplete", "unexpected_tool_call"
    if len(expected_calls) > 1:
        return "incomplete", "multiple_structured_calls"
    if expected_calls:
        return ("incomplete", "ambiguous_response") if has_text else ("structured", None)

    if phase == "commentary" and not meta.get("output_text_used"):
        return "not_final", "commentary_only"
    if not has_text:
        return "empty", "empty_text"
    return "text", None


def classify_validation_failure(model_text: str, error: str) -> str:
    """Content-free category for a rejected complete response."""
    message = str(error or "").casefold()
    if "malformed" in message or "invalid json" in message or "json found" in message:
        return "malformed_json"
    if "source validation" in message or "do not bind" in message:
        return "source"
    if "hollow" in message or "schema validation" in message:
        return "schema"
    return "malformed_json" if not _strict_json_parses(model_text) else "schema"


def classify_validation_reason(model_text: str, error: str) -> str:
    """Bounded reason label paired with the validation category."""
    message = str(error or "").casefold()
    if "hollow" in message:
        return "hollow"
    return classify_validation_failure(model_text, error)


def _normalize_auxiliary_result(result: Any) -> tuple[str, dict[str, Any], dict[str, Any]]:
    """Accept the 3-field response boundary and the 2-field compatibility shape."""
    if not isinstance(result, tuple):
        text, meta = extract_response_boundary(result)
        return text, extract_response_usage(result), meta
    if len(result) == 3:
        raw_text, raw_usage, raw_meta = result
    elif len(result) == 2:
        raw_text, raw_usage = result
        raw_meta = {}
    else:
        raise KnowledgeError(
            "AUXILIARY_FAILED", "The auxiliary transport returned an unusable result."
        )
    text = raw_text if isinstance(raw_text, str) else ""
    usage = dict(raw_usage) if isinstance(raw_usage, dict) else {}
    meta = dict(raw_meta) if isinstance(raw_meta, dict) else {}
    if "finish_reason" in usage and "finish_reason" not in meta:
        meta["finish_reason"] = _bounded_text(usage.get("finish_reason"), 64)
    nested = usage.get("response")
    if isinstance(nested, dict):
        for key, value in nested.items():
            meta.setdefault(key, value)
    return text, usage, meta


try:
    from agent.auxiliary_client import (  # type: ignore[import-not-found,import-untyped]  # pyright: ignore[reportMissingImports]
        AuxiliaryExplicitCancellation,
    )
except Exception:

    class AuxiliaryExplicitCancellation(BaseException):  # type: ignore[no-redef]
        """Fallback cancellation exception type when Hermes is unimported."""


CANCELLATION_EXCEPTIONS: tuple[type[BaseException], ...] = (
    AuxiliaryExplicitCancellation,
    InterruptedError,
)


def _is_cancellation_exception(exc: BaseException) -> bool:
    if isinstance(exc, CANCELLATION_EXCEPTIONS):
        return True
    return exc.__class__.__name__ in ("AuxiliaryExplicitCancellation", "ExplicitCancellation")


def _call_auxiliary_model(
    task: str,
    system_prompt: str,
    user_prompt: str,
    timeout: float = 120.0,
    route_info: dict[str, Any] | None = None,
    api_mode: str | None = None,
) -> tuple[str, dict[str, Any], dict[str, Any]]:
    """Invoke the Hermes profile-scoped auxiliary client and preserve its shape."""
    try:
        from agent.auxiliary_client import (  # type: ignore[import-not-found,import-untyped]  # pyright: ignore[reportMissingImports]
            call_llm,
        )
    except ImportError as exc:
        raise KnowledgeError(
            "COMPONENT_UNAVAILABLE", "Hermes auxiliary client is not available in this environment."
        ) from exc

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    local_route_info: dict[str, str] = {}
    try:
        response = call_llm(
            task=task,
            messages=messages,
            timeout=timeout,
            route_info=local_route_info,
        )
    except TypeError:
        try:
            response = call_llm(task=task, messages=messages, timeout=timeout)
        except CANCELLATION_EXCEPTIONS:
            raise
        except Exception as exc:
            if _is_cancellation_exception(exc):
                raise
            err_msg = str(exc)
            if "429" in err_msg or "rate" in err_msg.casefold() or "quota" in err_msg.casefold():
                raise KnowledgeError(
                    "ROUTER_EXHAUSTION", f"Auxiliary model rate limit/quota: {exc}"
                ) from exc
            raise KnowledgeError("AUXILIARY_FAILED", f"Auxiliary model call failed: {exc}") from exc
    except CANCELLATION_EXCEPTIONS:
        raise
    except Exception as exc:
        if _is_cancellation_exception(exc):
            raise
        err_msg = str(exc)
        if "429" in err_msg or "rate" in err_msg.casefold() or "quota" in err_msg.casefold():
            raise KnowledgeError(
                "ROUTER_EXHAUSTION", f"Auxiliary model rate limit/quota: {exc}"
            ) from exc
        raise KnowledgeError("AUXILIARY_FAILED", f"Auxiliary model call failed: {exc}") from exc

    content, meta = extract_response_boundary(response)
    usage = extract_response_usage(response)

    if local_route_info:
        if api_mode and "api_mode" not in local_route_info:
            local_route_info["api_mode"] = api_mode
        usage["route"] = dict(local_route_info)
        if route_info is not None:
            route_info.update(local_route_info)

    return content, usage, meta


def _host_interrupt_requested() -> bool:
    """Host interrupt (`tools.interrupt.is_interrupted`) when the runtime exposes it."""
    try:
        from tools.interrupt import is_interrupted  # type: ignore[import-not-found,import-untyped]
    except Exception:
        return False
    try:
        return bool(is_interrupted())
    except Exception:
        return False


@contextlib.contextmanager
def _interrupt_protection(cancel_event: threading.Event) -> Iterator[None]:
    """Wrap an auxiliary call with the transport's cancel-aware protection."""
    manager: Any = None
    try:
        from agent.auxiliary_client import (  # type: ignore[import-not-found,import-untyped]  # pyright: ignore[reportMissingImports]
            aux_interrupt_protection,
        )
    except Exception:
        yield
        return
    try:
        manager = aux_interrupt_protection(active=True, cancel_event=cancel_event)
    except TypeError:
        try:
            manager = aux_interrupt_protection(True)
        except Exception:
            manager = None
    if manager is None:
        yield
        return
    with manager:
        yield


def _thread_target(target: Callable[..., Any]) -> Callable[..., Any]:
    """Run one submitted chunk under its own copied context (never shared)."""
    propagate: Callable[[Callable[..., Any]], Callable[..., Any]] | None = None
    try:
        from tools.thread_context import (  # type: ignore[import-not-found,import-untyped]
            propagate_context_to_thread,
        )

        propagate = propagate_context_to_thread
    except Exception:
        propagate = None
    if propagate is not None:
        try:
            return propagate(target)
        except Exception:
            pass
    copied = contextvars.copy_context()
    return lambda *args, **kwargs: copied.run(target, *args, **kwargs)


# ── Validated cache ───────────────────────────────────────────────────────


class SemanticCache:
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        ensure_private_dir(self.cache_dir)

    def get(self, fingerprint: str) -> dict[str, Any] | None:
        entry = self.get_entry(fingerprint)
        if entry is not None and "fragment" in entry:
            return entry["fragment"]
        return None

    def get_entry(self, fingerprint: str) -> dict[str, Any] | None:
        path = self.cache_dir / f"{fingerprint}.json"
        if not path.is_file():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except Exception:
            pass
        return None

    def put(
        self, fingerprint: str, fragment: dict[str, Any], meta: dict[str, Any] | None = None
    ) -> None:
        path = self.cache_dir / f"{fingerprint}.json"
        payload = {
            "fingerprint": fingerprint,
            "saved_at": time.time(),
            "meta": meta or {},
            "fragment": fragment,
        }
        atomic_private_write(path, json.dumps(payload, indent=2).encode("utf-8"))

    def put_qualified(
        self,
        fingerprint: str,
        fragment: dict[str, Any],
        *,
        usage: dict[str, Any],
        route: dict[str, Any],
        model_digest: str,
    ) -> None:
        """Cache a fragment with the pipeline/policy/route identity it was proven under."""
        self.put(
            fingerprint,
            fragment,
            meta={
                "pipeline_version": PIPELINE_VERSION,
                "cache_version": CACHE_VERSION,
                "scope_version": SCOPE_VERSION,
                "policy": dict(SEMANTIC_POLICY),
                "model_digest": model_digest,
                "usage": usage,
                "route": route,
            },
        )


def cache_entry_is_qualified(
    entry: dict[str, Any] | None,
    *,
    expected_route: dict[str, Any],
    model_digest: str,
) -> bool:
    """Cached fragments are read only under matching policy/version/route identity."""
    if not isinstance(entry, dict) or not isinstance(entry.get("fragment"), dict):
        return False
    meta = entry.get("meta")
    if not isinstance(meta, dict):
        return False
    if meta.get("pipeline_version") != PIPELINE_VERSION:
        return False
    if meta.get("cache_version") != CACHE_VERSION:
        return False
    if meta.get("scope_version") != SCOPE_VERSION:
        return False
    if meta.get("policy") != SEMANTIC_POLICY:
        return False
    if meta.get("model_digest") != model_digest:
        return False
    return routes_match_strictly(expected_route, meta.get("route"))


def _revalidated_legacy_entry(
    entry: dict[str, Any],
    *,
    revalidator: Callable[[dict[str, Any]], bool],
    cache: SemanticCache,
    fingerprint: str,
    route: dict[str, Any],
    model_digest: str,
) -> bool:
    """Integration seam: an unqualified entry may only be reused after revalidation."""
    fragment = entry.get("fragment")
    if not isinstance(fragment, dict):
        return False
    try:
        if not revalidator(fragment):
            return False
    except Exception:
        return False
    cache.put_qualified(fingerprint, fragment, usage={}, route=route, model_digest=model_digest)
    return True


# ── Native worker calls ───────────────────────────────────────────────────


def _fetch_all_prepared_chunks(
    backend: GraphifyBackend,
    source_root: Path,
    graph_path: Path,
    eligible_files: list[str],
    *,
    page_size: int = 25,
) -> list[dict[str, Any]]:
    """Fetch prepared semantic extraction chunks across bounded pages."""
    all_chunks: list[dict[str, Any]] = []
    offset = 0
    while True:
        prep_res = backend.run(
            "semantic_prepare",
            source_root=source_root,
            graph_path=graph_path,
            arguments={
                "files": eligible_files,
                "offset": offset,
                "limit": page_size,
            },
        )
        chunks = prep_res.get("chunks", [])
        if not chunks:
            break
        all_chunks.extend(chunks)
        total_chunks = prep_res.get("total_chunks")
        has_more = prep_res.get("has_more")
        if total_chunks is not None and len(all_chunks) >= total_chunks:
            break
        if has_more is False:
            break
        if total_chunks is None and len(chunks) < page_size:
            break
        offset += len(chunks)
    return all_chunks


def compute_semantic_fingerprint(
    backend: GraphifyBackend,
    source_root: Path,
    graph_path: Path,
    inputs: dict[str, str],
    configuration: dict[str, Any],
) -> str | None:
    """Deterministic overall fingerprint for configured semantic extraction without calling LLM."""
    aux_task = resolve_auxiliary_task(configuration)
    if not aux_task:
        return None

    eligible_files = sorted(
        [p for p in inputs if Path(p).suffix.casefold() in _ELIGIBLE_EXTENSIONS]
    )
    if not eligible_files:
        return hashlib.sha256(b"no_eligible_files").hexdigest()

    route = resolve_auxiliary_route(configuration, aux_task)
    model_digest = get_model_identity_digest(
        aux_task,
        provider=route.get("provider"),
        model=route.get("model"),
        api_mode=route.get("api_mode"),
    )

    # A compatible private plan answers the fingerprint without repacking the corpus.
    plan_store = _plan_store_for_graph(graph_path)
    if plan_store is not None:
        identity = plan_identity(
            scope_version=SCOPE_VERSION,
            policy=SEMANTIC_POLICY,
            model_digest=model_digest,
            auxiliary_task=aux_task,
            inputs_digest=_inputs_digest(inputs),
        )
        plan = plan_store.load(identity)
        if plan_matches(
            plan,
            plan_id=identity,
            model_digest=model_digest,
            auxiliary_task=aux_task,
            inputs_digest=_inputs_digest(inputs),
        ):
            assert plan is not None
            return _overall_fingerprint(plan["chunks"])

    try:
        chunks = _fetch_all_prepared_chunks(
            backend=backend,
            source_root=source_root,
            graph_path=graph_path,
            eligible_files=eligible_files,
        )
    except Exception:
        return None

    if not chunks:
        return hashlib.sha256(b"no_chunks").hexdigest()

    records = [build_plan_record(chunk, inputs, model_digest=model_digest) for chunk in chunks]
    return _overall_fingerprint(records)


# ── Receipt blocks ────────────────────────────────────────────────────────


def _pipeline_block(
    *,
    plan_id: str | None,
    plan_reused: bool,
    plan_persisted: bool,
    budget_seconds: float,
    structural_base: dict[str, Any] | None,
    deadline_exhausted: bool,
) -> dict[str, Any]:
    """Additive pipeline/plan identity carried by every semantic receipt."""
    return {
        "version": PIPELINE_VERSION,
        "cache_version": CACHE_VERSION,
        "scope_version": SCOPE_VERSION,
        "plan_id": plan_id,
        "plan_reused": plan_reused,
        "plan_persisted": plan_persisted,
        "budget_seconds": budget_seconds,
        "structural_base_digest": (structural_base or {}).get("digest"),
        "structural_base_revision": (structural_base or {}).get("revision") or None,
        "deadline_exhausted": deadline_exhausted,
    }


def _compose_block(raw_receipt: Any = None, *, fragments: int = 0) -> dict[str, Any]:
    """Compose receipt: one call, structural digest/preservation, bounded counts."""
    block: dict[str, Any] = {
        "invoked": raw_receipt is not None,
        "fragments": _bounded_int(fragments),
        "ok": True,
        "applied_nodes": 0,
        "applied_edges": 0,
        "applied_hyperedges": 0,
        "omitted_nodes": 0,
        "omitted_edges": 0,
        "omitted_hyperedges": 0,
        "structural_digest": None,
        "structural_preserved": None,
    }
    if isinstance(raw_receipt, dict):
        ok = raw_receipt.get("ok")
        block["ok"] = True if ok is None else bool(ok)
        for key in (
            "applied_nodes",
            "applied_edges",
            "applied_hyperedges",
            "omitted_nodes",
            "omitted_edges",
            "omitted_hyperedges",
        ):
            block[key] = _bounded_int(raw_receipt.get(key))
        digest = _bounded_text(raw_receipt.get("structural_digest"), 128)
        block["structural_digest"] = digest or None
        preserved = raw_receipt.get("structural_preserved")
        block["structural_preserved"] = None if preserved is None else bool(preserved)
    return block


class _OperationUsage:
    """Content-free operation counters: calls, bounded usage and outcome categories."""

    def __init__(self) -> None:
        self.model_calls = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.reasoning_tokens = 0
        self.total_tokens = 0
        self.categories: dict[str, int] = {name: 0 for name in _CATEGORY_NAMES}
        self.reasons: dict[str, int] = {name: 0 for name in _REASON_NAMES}

    def add_call(self) -> None:
        self.model_calls += 1

    def add_usage(self, usage: dict[str, Any]) -> None:
        prompt = _bounded_int(usage.get("prompt_tokens"))
        completion = _bounded_int(usage.get("completion_tokens"))
        reasoning = _bounded_int(usage.get("reasoning_tokens"))
        total = _bounded_int(usage.get("total_tokens")) or (prompt + completion)
        self.input_tokens += prompt
        self.output_tokens += completion
        self.reasoning_tokens += reasoning
        self.total_tokens += total

    def bump(self, category: str | None = None, reason: str | None = None, amount: int = 1) -> None:
        if category:
            self.categories[category] = self.categories.get(category, 0) + amount
            if category == "deadline":
                self.categories["deadline_deferred"] = (
                    self.categories.get("deadline_deferred", 0) + amount
                )
            elif category == "apply":
                self.categories["apply_failed"] = self.categories.get("apply_failed", 0) + amount
        if reason:
            self.reasons[reason] = self.reasons.get(reason, 0) + amount

    def usage_block(self) -> dict[str, Any]:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "reasoning_tokens": self.reasoning_tokens,
            "total_tokens": self.total_tokens,
        }


def _usage_block(
    usage: _OperationUsage,
    *,
    started: float,
    prepare_calls: int,
    chunk_total: int,
    cached: int = 0,
    validated: int = 0,
    pending: int = 0,
    failed: int = 0,
    deferred: int = 0,
    cancelled: int = 0,
) -> dict[str, Any]:
    """Content-free operation receipt: counts, categories and bounded usage."""
    return {
        "total_tokens": usage.total_tokens,
        "model_calls": usage.model_calls,
        "elapsed_seconds": round(max(0.0, _now() - started), 3),
        "prepare_calls": prepare_calls,
        "usage": usage.usage_block(),
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "reasoning_tokens": usage.reasoning_tokens,
        "chunk_counts": {
            "total": chunk_total,
            "cached": cached,
            "validated": validated,
            "pending": pending,
            "failed": failed,
            "deferred": deferred,
            "cancelled": cancelled,
        },
        "categories": dict(usage.categories),
        "reasons": dict(usage.reasons),
    }


# ── Executor ──────────────────────────────────────────────────────────────


def run_semantic_extraction(
    backend: GraphifyBackend,
    source_root: Path,
    graph_path: Path,
    inputs: dict[str, str],
    cache_root: Path,
    ctx: KnowledgeContext,
    configuration: dict[str, Any],
    *,
    deadline_seconds: float | None = DEFAULT_TOTAL_BUDGET_SECONDS,
    cancel_event: threading.Event | None = None,
    structured_call_enabled: bool = False,
    legacy_cache_revalidator: Callable[[dict[str, Any]], bool] | None = None,
) -> dict[str, Any]:
    """Orchestrate one bounded semantic update: plan, calls, validation, one composition.

    Total budget: 300 seconds (configurable only downwards) from entry through return,
    with finalization reserved before another model call starts. A host/caller cancel
    or the deadline stops scheduling, keeps the validated cache, and never composes
    after the signal. Only mutually unambiguous final text (or, behind the dormant
    `structured_call_enabled` hook, exactly one expected structured call) reaches the
    strict Graphify validator, and only route-qualified fragments reach the cache and
    the single `semantic_compose` call.
    """
    started = _now()
    budget = resolve_total_budget(configuration, deadline_seconds)
    deadline = started + budget
    reserve = finalization_reserve(budget)

    shared_cancel = cancel_event if cancel_event is not None else threading.Event()
    host_cancelled = False
    deadline_exhausted = False
    budget_abort = False

    def _cancel_requested() -> bool:
        """Host/user cancel only; never this operation's own budget abort."""
        nonlocal host_cancelled
        if shared_cancel.is_set() and not (budget_abort and not host_cancelled):
            return True
        if _host_interrupt_requested():
            host_cancelled = True
            shared_cancel.set()
            return True
        return False

    def _budget_expired(*, abort_in_flight: bool = False) -> bool:
        nonlocal deadline_exhausted, budget_abort
        if _now() < deadline:
            return False
        deadline_exhausted = True
        if abort_in_flight and not shared_cancel.is_set():
            # Abort in-flight auxiliary calls through the existing transport hook.
            budget_abort = True
            shared_cancel.set()
        return True

    def _early_receipt(
        state: str,
        *,
        pending_paths: list[str],
        fingerprint: str | None,
        plan_id: str | None = None,
        plan_reused: bool = False,
        plan_persisted: bool = False,
        base: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "state": state,
            "fingerprint": fingerprint,
            "covered_paths": [],
            "pending_paths": sorted(pending_paths),
            "failed_paths": [],
            "validated_chunk_ids": [],
            "observed_usage": _usage_block(usage, started=started, prepare_calls=0, chunk_total=0),
            "pipeline": _pipeline_block(
                plan_id=plan_id,
                plan_reused=plan_reused,
                plan_persisted=plan_persisted,
                budget_seconds=budget,
                structural_base=base,
                deadline_exhausted=deadline_exhausted,
            ),
            "compose": _compose_block(),
            "structural_digest": None,
            "structural_preserved": None,
        }

    usage = _OperationUsage()

    state_lock = threading.Lock()
    newly_validated_fragments: dict[int, dict[str, Any]] = {}
    failed_chunks: set[int] = set()
    pending_chunks: set[int] = set()
    deferred_chunks: set[int] = set()
    validation_failed_chunks: set[int] = set()
    cancelled_chunks: set[int] = set()

    def _mark(
        chunk_id: int,
        *,
        failed: bool = False,
        pending: bool = False,
        deferred: bool = False,
        cancelled: bool = False,
        category: str | None = None,
        reason: str | None = None,
    ) -> None:
        with state_lock:
            if failed:
                failed_chunks.add(chunk_id)
                if category is None:
                    category = "incomplete"
            if pending:
                pending_chunks.add(chunk_id)
            if deferred:
                deferred_chunks.add(chunk_id)
            if cancelled:
                cancelled_chunks.add(chunk_id)
            usage.bump(category=category, reason=reason)

    if _cancel_requested():
        raise KnowledgeError("OPERATION_CANCELLED", "Semantic extraction was cancelled.")

    aux_task = resolve_auxiliary_task(configuration)
    if not aux_task:
        return _early_receipt(
            "unavailable",
            pending_paths=[p for p in inputs if Path(p).suffix.casefold() in _ELIGIBLE_EXTENSIONS],
            fingerprint=None,
        )

    expected_route = resolve_auxiliary_route(configuration, aux_task)
    model_digest = get_model_identity_digest(
        aux_task,
        provider=expected_route.get("provider"),
        model=expected_route.get("model"),
        api_mode=expected_route.get("api_mode"),
    )

    eligible_files = sorted(
        [p for p in inputs if Path(p).suffix.casefold() in _ELIGIBLE_EXTENSIONS]
    )
    if not eligible_files:
        return _early_receipt(
            "complete",
            pending_paths=[],
            fingerprint=hashlib.sha256(b"no_eligible_files").hexdigest(),
        )

    structural_base = _structural_base_reference(graph_path, ctx.source_revision)

    # Primary-only fail-closed route policy: nothing can be qualified while the
    # effective primary route is unresolved.
    if not is_route_resolved(expected_route):
        usage.bump(category="route", reason="unresolved_route", amount=len(eligible_files))
        return _early_receipt(
            "pending",
            pending_paths=sorted(eligible_files),
            fingerprint=None,
            base=structural_base,
        )

    # ── Plan: build once per compatible revision/policy, then reuse it ────────
    inputs_digest = _inputs_digest(inputs)
    plan_dir = cache_root / "knowledge" / ctx.project_id / "semantic_plans"
    cache_dir = cache_root / "knowledge" / ctx.project_id / "semantic_cache"
    plan_store = SemanticPlanStore(plan_dir)
    plan_id = plan_identity(
        scope_version=SCOPE_VERSION,
        policy=SEMANTIC_POLICY,
        model_digest=model_digest,
        auxiliary_task=aux_task,
        inputs_digest=inputs_digest,
    )
    plan = plan_store.load(plan_id)
    if (
        plan_matches(
            plan,
            plan_id=plan_id,
            model_digest=model_digest,
            auxiliary_task=aux_task,
            inputs_digest=inputs_digest,
        )
        and plan is not None
    ):
        if not plan_accepts_structural_base(plan, str(structural_base["digest"])):
            plan = None
    else:
        plan = None

    prepare_calls = 0
    plan_reused = plan is not None
    prepared_by_id: dict[int, dict[str, Any]] = {}
    fresh_chunks: list[dict[str, Any]] | None = None

    if plan is None:
        try:
            fresh_chunks = _fetch_all_prepared_chunks(
                backend=backend,
                source_root=source_root,
                graph_path=graph_path,
                eligible_files=eligible_files,
            )
            prepare_calls += 1
        except Exception as exc:
            logger.warning("Semantic preparation failed (%s).", _failure_label(exc))
            return _early_receipt(
                "unavailable",
                pending_paths=sorted(eligible_files),
                fingerprint=None,
                plan_id=plan_id,
                base=structural_base,
            )

        if not fresh_chunks:
            return _early_receipt(
                "complete",
                pending_paths=[],
                fingerprint=hashlib.sha256(b"no_chunks").hexdigest(),
                plan_id=plan_id,
                base=structural_base,
            )

        records = [
            build_plan_record(chunk, inputs, model_digest=model_digest) for chunk in fresh_chunks
        ]
        records.sort(key=lambda record: record["chunk_id"])
        plan = build_plan(
            records,
            inputs,
            plan_id=plan_id,
            model_digest=model_digest,
            auxiliary_task=aux_task,
            structural_base=structural_base,
        )
        prepared_by_id = {int(chunk["chunk_id"]): chunk for chunk in fresh_chunks}
    else:
        records = list(plan["chunks"])

    plan_persisted = True if plan_reused else plan_store.save(plan)

    # ── Cache: policy/version/content identity plus the expected primary route ─
    cache = SemanticCache(cache_dir)
    cached_fragments: dict[int, dict[str, Any]] = {}
    needed_records: list[dict[str, Any]] = []
    for record in records:
        chunk_id = int(record["chunk_id"])
        entry = cache.get_entry(str(record["fingerprint"]))
        if entry is not None:
            if cache_entry_is_qualified(
                entry, expected_route=expected_route, model_digest=model_digest
            ):
                cached_fragments[chunk_id] = entry["fragment"]
                continue
            if legacy_cache_revalidator is not None and _revalidated_legacy_entry(
                entry,
                revalidator=legacy_cache_revalidator,
                cache=cache,
                fingerprint=str(record["fingerprint"]),
                route=expected_route,
                model_digest=model_digest,
            ):
                cached_fragments[chunk_id] = entry["fragment"]
                continue
            usage.bump(category="cache", reason="unqualified_cache_entry")
        needed_records.append(record)

    # Prompt material for pending work. A compatible plan that already carries every
    # accepted chunk performs no prepare call at all.
    unscheduled: list[dict[str, Any]] = []
    if needed_records and plan_reused and not _budget_expired():
        try:
            fetched = _fetch_all_prepared_chunks(
                backend=backend,
                source_root=source_root,
                graph_path=graph_path,
                eligible_files=eligible_files,
            )
            prepare_calls += 1
        except Exception as exc:
            logger.warning("Semantic prompt refetch failed (%s).", _failure_label(exc))
            fetched = []
            for record in needed_records:
                usage.bump(category="incomplete", reason="prepare_failed")
                unscheduled.append(record)
        by_fingerprint: dict[str, dict[str, Any]] = {}
        for chunk in fetched:
            refetched = build_plan_record(chunk, inputs, model_digest=model_digest)
            by_fingerprint.setdefault(str(refetched["fingerprint"]), chunk)
        matched: list[dict[str, Any]] = []
        for record in needed_records:
            matched_chunk = by_fingerprint.get(str(record["fingerprint"]))
            if matched_chunk is None:
                usage.bump(category="incomplete", reason="plan_mismatch")
                unscheduled.append(record)
                continue
            prepared_by_id[int(record["chunk_id"])] = matched_chunk
            matched.append(record)
        scheduled_records = matched
    else:
        scheduled_records = needed_records

    if _budget_expired():
        # The budget is already spent: nothing more may start, and every unit of
        # pending work is reported as a deadline outcome.
        for record in scheduled_records:
            _mark(
                int(record["chunk_id"]),
                pending=True,
                deferred=True,
                category="deadline",
                reason="deadline",
            )
        unscheduled.extend(scheduled_records)
        scheduled_records = []

    overall_fp = _overall_fingerprint(records)

    def _process_chunk(record: dict[str, Any], chunk: dict[str, Any]) -> None:
        chunk_id = int(record["chunk_id"])
        fingerprint = str(record["fingerprint"])
        if _cancel_requested():
            _mark(chunk_id, pending=True, cancelled=True, reason="cancelled_response")
            return
        if _budget_expired() or shared_cancel.is_set():
            _mark(chunk_id, pending=True, deferred=True, category="deadline", reason="deadline")
            return

        attempts = 0
        raw_text = ""
        usage_info: dict[str, Any] = {}
        meta: dict[str, Any] = {}
        chunk_route_info: dict[str, Any] = {}
        last_error: Exception | None = None
        cancelled_by_transport = False

        for _attempt in range(AUXILIARY_ATTEMPT_LIMIT):
            if _cancel_requested():
                cancelled_by_transport = True
                break
            if shared_cancel.is_set() or _budget_expired():
                break
            remaining = deadline - _now()
            if remaining <= 0:
                _budget_expired(abort_in_flight=True)
                break
            attempts += 1
            usage.add_call()
            chunk_route_info = {}
            try:
                with _interrupt_protection(shared_cancel):
                    result = _call_auxiliary_model(
                        task=aux_task,
                        system_prompt=str(chunk.get("system_prompt") or ""),
                        user_prompt=str(chunk.get("user_prompt") or ""),
                        timeout=min(AUXILIARY_TIMEOUT_SECONDS, max(1.0, remaining)),
                        route_info=chunk_route_info,
                        api_mode=expected_route.get("api_mode"),
                    )
            except TypeError:
                try:
                    with _interrupt_protection(shared_cancel):
                        result = _call_auxiliary_model(
                            task=aux_task,
                            system_prompt=str(chunk.get("system_prompt") or ""),
                            user_prompt=str(chunk.get("user_prompt") or ""),
                            timeout=min(AUXILIARY_TIMEOUT_SECONDS, max(1.0, remaining)),
                        )
                except CANCELLATION_EXCEPTIONS:
                    cancelled_by_transport = True
                    break
                except Exception as exc:
                    if _is_cancellation_exception(exc):
                        cancelled_by_transport = True
                        break
                    last_error = exc
                    if _is_router_exhaustion(exc):
                        break
                    shared_cancel.wait(0.5)
                    continue
            except CANCELLATION_EXCEPTIONS:
                cancelled_by_transport = True
                break
            except Exception as exc:
                if _is_cancellation_exception(exc):
                    cancelled_by_transport = True
                    break
                last_error = exc
                if _is_router_exhaustion(exc):
                    break
                shared_cancel.wait(0.5)
                continue

            try:
                raw_text, usage_info, meta = _normalize_auxiliary_result(result)
            except Exception as exc:
                last_error = exc
                continue
            break

        if cancelled_by_transport or _cancel_requested() or shared_cancel.is_set():
            if _cancel_requested():
                _mark(chunk_id, pending=True, cancelled=True, reason="cancelled_response")
            else:
                _mark(chunk_id, pending=True, deferred=True, category="deadline", reason="deadline")
            return
        if attempts == 0:
            _mark(chunk_id, pending=True, deferred=True, category="deadline", reason="deadline")
            return
        if not raw_text.strip() and last_error is not None:
            logger.warning(
                "Chunk %d failed auxiliary extraction (%s).",
                chunk_id,
                _failure_label(last_error),
            )
            failure_reason = (
                "router_exhaustion" if _is_router_exhaustion(last_error) else "transport_error"
            )
            with state_lock:
                usage.categories["auxiliary_failed"] = (
                    usage.categories.get("auxiliary_failed", 0) + 1
                )
            _mark(chunk_id, failed=True, category="incomplete", reason=failure_reason)
            return

        usage.add_usage(usage_info)
        label, label_reason = classify_auxiliary_response(raw_text, meta)
        if label == "structured":
            if not structured_call_enabled:
                _mark(
                    chunk_id,
                    pending=True,
                    category="incomplete",
                    reason="structured_call_disabled",
                )
                return
            raw_text = _structured_call_text(meta)
            if not raw_text:
                _mark(
                    chunk_id,
                    pending=True,
                    category="incomplete",
                    reason="unexpected_tool_call",
                )
                return
        elif label == "text":
            pass
        elif label == "empty":
            _mark(chunk_id, pending=True, category="empty", reason="empty_text")
            return
        else:
            _mark(
                chunk_id,
                pending=True,
                category="incomplete",
                reason=label_reason or label,
            )
            return

        actual_route = dict(expected_route)
        if isinstance(usage_info.get("route"), dict):
            actual_route.update(usage_info["route"])
        if chunk_route_info:
            actual_route.update(chunk_route_info)

        if not routes_match_strictly(expected_route, actual_route):
            _mark(
                chunk_id,
                pending=True,
                category="route",
                reason=(
                    "route_mismatch" if is_route_resolved(actual_route) else "unresolved_route"
                ),
            )
            return

        if _cancel_requested() or shared_cancel.is_set() or _budget_expired():
            return

        try:
            validation = backend.run(
                "semantic_validate",
                source_root=source_root,
                graph_path=graph_path,
                arguments={
                    "model_text": raw_text,
                    "allowed_sources": list(chunk.get("files", [])),
                    "allow_empty": False,
                },
            )
            fragment = validation.get("fragment", {}) if isinstance(validation, dict) else {}
            if not isinstance(fragment, dict) or not fragment:
                raise KnowledgeError("INDEX_CORRUPT", "Semantic validation returned no fragment.")
        except Exception as exc:
            logger.warning(
                "Chunk %d failed fragment validation (%s).", chunk_id, _failure_label(exc)
            )
            reason = classify_validation_reason(raw_text, str(exc))
            with state_lock:
                validation_failed_chunks.add(chunk_id)
                usage.categories["validation_failed"] = (
                    usage.categories.get("validation_failed", 0) + 1
                )
            _mark(
                chunk_id,
                failed=True,
                category=classify_validation_failure(raw_text, str(exc)),
                reason=reason,
            )
            return

        if _cancel_requested() or shared_cancel.is_set() or _budget_expired():
            return

        cache.put_qualified(
            fingerprint,
            fragment,
            usage=usage_info,
            route=actual_route,
            model_digest=model_digest,
        )
        with state_lock:
            newly_validated_fragments[chunk_id] = fragment

    # ── Bounded scheduling: at most two in flight, polled on the owning thread ──
    queue = deque(scheduled_records)
    if queue:
        pool = concurrent.futures.ThreadPoolExecutor(max_workers=MAX_AUXILIARY_CONCURRENCY)
        in_flight: dict[concurrent.futures.Future[Any], dict[str, Any]] = {}
        try:
            while True:
                while (
                    queue
                    and len(in_flight) < MAX_AUXILIARY_CONCURRENCY
                    and not shared_cancel.is_set()
                    and not _budget_expired()
                    and _now() < deadline - reserve
                ):
                    record = queue.popleft()
                    chunk = prepared_by_id[int(record["chunk_id"])]
                    target = _thread_target(_process_chunk)
                    in_flight[pool.submit(target, record, chunk)] = record
                if not in_flight:
                    break
                done, _pending = concurrent.futures.wait(
                    list(in_flight),
                    timeout=min(
                        SCHEDULER_POLL_SECONDS,
                        max(0.005, deadline - _now()) if _now() < deadline else 0.005,
                    ),
                    return_when=concurrent.futures.FIRST_COMPLETED,
                )
                for future in done:
                    record = in_flight.pop(future)
                    chunk_id = int(record["chunk_id"])
                    try:
                        future.result()
                    except CANCELLATION_EXCEPTIONS:
                        if _cancel_requested():
                            _mark(
                                chunk_id, pending=True, cancelled=True, reason="cancelled_response"
                            )
                        else:
                            _mark(
                                chunk_id,
                                pending=True,
                                deferred=True,
                                category="deadline",
                                reason="deadline",
                            )
                    except Exception as exc:  # pragma: no cover - defensive
                        if _is_cancellation_exception(exc):
                            if _cancel_requested():
                                _mark(
                                    chunk_id,
                                    pending=True,
                                    cancelled=True,
                                    reason="cancelled_response",
                                )
                            else:
                                _mark(
                                    chunk_id,
                                    pending=True,
                                    deferred=True,
                                    category="deadline",
                                    reason="deadline",
                                )
                        else:
                            logger.warning(
                                "Semantic chunk worker failed (%s).", _failure_label(exc)
                            )
                            _mark(
                                chunk_id,
                                failed=True,
                                category="incomplete",
                                reason="worker_error",
                            )
                    except BaseException as exc:  # pragma: no cover - defensive
                        if _is_cancellation_exception(exc):
                            if _cancel_requested():
                                _mark(
                                    chunk_id,
                                    pending=True,
                                    cancelled=True,
                                    reason="cancelled_response",
                                )
                            else:
                                _mark(
                                    chunk_id,
                                    pending=True,
                                    deferred=True,
                                    category="deadline",
                                    reason="deadline",
                                )
                        else:
                            logger.warning(
                                "Semantic chunk worker failed with BaseException (%s).",
                                _failure_label(exc),
                            )
                            _mark(
                                chunk_id,
                                failed=True,
                                category="incomplete",
                                reason="worker_error",
                            )
                if _cancel_requested():
                    break
                if _budget_expired(abort_in_flight=bool(in_flight)):
                    break
                if shared_cancel.is_set() or _now() >= deadline - reserve:
                    break
            if in_flight:
                if not shared_cancel.is_set():
                    if _now() >= deadline or _now() >= deadline - reserve:
                        deadline_exhausted = True
                        budget_abort = True
                    shared_cancel.set()
                drain_window = (
                    CANCEL_DRAIN_SECONDS
                    if host_cancelled or (_cancel_requested() and not budget_abort)
                    else max(
                        0.01,
                        min(
                            CANCEL_DRAIN_SECONDS,
                            deadline - _now() if _now() < deadline else 0.05,
                        ),
                    )
                )
                done, _pending = concurrent.futures.wait(
                    list(in_flight), timeout=max(0.01, drain_window)
                )
                for future in done:
                    if future in in_flight:
                        record = in_flight.pop(future)
                        chunk_id = int(record["chunk_id"])
                        try:
                            future.result()
                        except CANCELLATION_EXCEPTIONS:
                            pass
                        except Exception:
                            pass
                for future, record in list(in_flight.items()):
                    if future.done():
                        continue
                    chunk_id = int(record["chunk_id"])
                    if host_cancelled or (_cancel_requested() and not budget_abort):
                        _mark(chunk_id, pending=True, cancelled=True, reason="cancelled_response")
                    else:
                        _mark(
                            chunk_id,
                            pending=True,
                            deferred=True,
                            category="deadline",
                            reason="deadline",
                        )
        finally:
            has_running = any(not f.done() for f in in_flight)
            wait_for_workers = not has_running and not shared_cancel.is_set()
            pool.shutdown(wait=wait_for_workers, cancel_futures=True)

    # ── One composition per update over every accepted fragment ───────────────
    accepted: dict[int, dict[str, Any]] = dict(cached_fragments)
    accepted.update(newly_validated_fragments)
    compose = _compose_block()
    composed_chunks: set[int] = set()

    if accepted and (_cancel_requested() or _budget_expired()):
        # A cancelled or exhausted operation never composes and never publishes.
        cancelled_now = _cancel_requested()
        for chunk_id in accepted:
            if cancelled_now:
                _mark(chunk_id, pending=True, cancelled=True)
            else:
                _mark(chunk_id, pending=True, deferred=True, category="deadline", reason="deadline")
    elif accepted:
        fragments = [accepted[chunk_id] for chunk_id in sorted(accepted)]
        try:
            raw_receipt = backend.run(
                "semantic_compose",
                source_root=source_root,
                graph_path=graph_path,
                arguments={
                    "fragments": fragments,
                    "allowed_sources": list(inputs.keys()),
                    "allow_empty": True,
                },
            )
            compose = _compose_block(raw_receipt, fragments=len(fragments))
            if compose["ok"] and compose["structural_preserved"] is not False:
                composed_chunks = set(accepted)
                if compose["structural_digest"]:
                    # This plan already composed against the new candidate base.
                    refreshed = _structural_base_reference(graph_path, ctx.source_revision)
                    note_structural_base(plan, str(refreshed["digest"]))
                    plan_store.save(plan)
            else:
                usage.bump(category="apply", reason="structural_not_preserved")
                for chunk_id in accepted:
                    _mark(chunk_id, failed=True)
        except Exception as exc:
            logger.warning("Semantic composition failed (%s).", _failure_label(exc))
            usage.bump(category="apply", reason="compose_error")
            for chunk_id in accepted:
                _mark(chunk_id, failed=True)

    # Chunks that never obtained prompt material stay explicitly pending.
    for record in unscheduled:
        _mark(int(record["chunk_id"]), pending=True)

    # Anything neither composed, failed nor already marked stays explicitly pending.
    for record in records:
        chunk_id = int(record["chunk_id"])
        if chunk_id in composed_chunks or chunk_id in failed_chunks or chunk_id in pending_chunks:
            continue
        if _cancel_requested():
            _mark(chunk_id, pending=True, cancelled=True)
        elif _budget_expired() or _now() >= deadline - reserve:
            deadline_exhausted = True
            _mark(chunk_id, pending=True, deferred=True, category="deadline", reason="deadline")
        else:
            _mark(chunk_id, pending=True, category="incomplete", reason="not_scheduled")

    if shared_cancel.is_set() and not deadline_exhausted and not budget_abort:
        raise KnowledgeError("OPERATION_CANCELLED", "Semantic extraction was cancelled.")

    # ── Coverage and state ───────────────────────────────────────────────────
    file_to_chunks: dict[str, set[int]] = {p: set() for p in eligible_files}
    for record in records:
        chunk_id = int(record["chunk_id"])
        for path in record.get("files", []):
            file_to_chunks.setdefault(path, set()).add(chunk_id)

    covered_paths_set: set[str] = set()
    failed_paths_set: set[str] = set()
    pending_paths_set: set[str] = set()

    for path in sorted(file_to_chunks.keys()):
        chunk_ids = file_to_chunks[path]
        if not chunk_ids:
            pending_paths_set.add(path)
        elif chunk_ids.issubset(composed_chunks):
            covered_paths_set.add(path)
        else:
            if chunk_ids & failed_chunks:
                failed_paths_set.add(path)
            if chunk_ids & pending_chunks:
                pending_paths_set.add(path)

    if len(composed_chunks) == len(records):
        state = "complete"
    elif composed_chunks:
        state = "partial"
    elif pending_chunks:
        state = "partial" if failed_chunks else "pending"
    else:
        state = "unavailable"

    return {
        "state": state,
        "fingerprint": overall_fp,
        "covered_paths": sorted(covered_paths_set),
        "pending_paths": sorted(pending_paths_set),
        "failed_paths": sorted(failed_paths_set),
        "validated_chunk_ids": sorted(composed_chunks),
        "observed_usage": _usage_block(
            usage,
            started=started,
            prepare_calls=prepare_calls,
            chunk_total=len(records),
            cached=len(cached_fragments),
            validated=len(newly_validated_fragments),
            pending=len(pending_chunks),
            failed=len(failed_chunks),
            deferred=len(deferred_chunks),
            cancelled=len(cancelled_chunks),
        ),
        "pipeline": _pipeline_block(
            plan_id=plan_id,
            plan_reused=plan_reused,
            plan_persisted=plan_persisted,
            budget_seconds=budget,
            structural_base=structural_base,
            deadline_exhausted=deadline_exhausted,
        ),
        "compose": compose,
        "structural_digest": compose.get("structural_digest"),
        "structural_preserved": compose.get("structural_preserved"),
    }
