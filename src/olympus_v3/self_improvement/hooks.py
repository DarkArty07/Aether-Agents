"""Hermes lifecycle hooks for the project-scoped Aether improvement cycle."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import subprocess
import threading
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from olympus_v3.coordination.harmonia_contract import HARMONIA_ERROR_CODES
from olympus_v3.self_improvement.ledger import SelfImprovementLedger
from olympus_v3.self_improvement.manifest import CycleManifest, verify_project_identity

logger = logging.getLogger("olympus_v3.self_improvement")
_HEX_COMMIT = re.compile(r"^[0-9a-f]{40,64}$")

# Codes `HarmoniaService._start_admission_error` returns before any durable run
# exists. Every other public code may surface once a run could already be
# durable, so it is never downgraded to pre-admission.
_PRE_ADMISSION_CODES = frozenset(
    {"feature_disabled", "invalid_request", "project_not_allowed", "admission_limit"}
)
# Durable lifecycle states a successful Harmonia response reports in `state`.
# `tests/test_self_improvement_contract.py` asserts this stays equal to the
# kernel's own state set, so a rename upstream breaks the build instead of
# silently degrading every classification to "unknown".
_POST_ADMISSION_STATES = frozenset(
    {
        "admitted",
        "dispatch_staged",
        "retry_wait",
        "session_bound",
        "terminal_observed",
        "cleanup_pending",
        "cleaned",
        "reconciliation_required",
        "cancel_requested",
    }
)


@dataclass(frozen=True)
class _Runtime:
    manifest: CycleManifest
    ledger: SelfImprovementLedger
    baseline_commit: str


_runtime_by_session: dict[str, _Runtime] = {}
_runtime_lock = threading.RLock()
_runtime_instance_id = str(uuid.uuid4())


def reset_runtime_state() -> None:
    """Drop process-local handles; durable ledger state is intentionally preserved."""

    global _runtime_instance_id
    with _runtime_lock:
        _runtime_by_session.clear()
        _runtime_instance_id = str(uuid.uuid4())


def _walk_to_project(start: Path) -> Path | None:
    candidate = start.expanduser().resolve()
    for path in (candidate, *candidate.parents):
        if (path / ".git").exists():
            manifest = path / "docs" / "releases" / "v0.20.0" / "CYCLE.yaml"
            return path if manifest.is_file() else None
    return None


def _project_root(kwargs: dict[str, Any]) -> Path | None:
    explicit = kwargs.get("project_root")
    if explicit:
        return Path(str(explicit)).expanduser().resolve()
    return _walk_to_project(Path.cwd())


def _git_dir(project_root: Path) -> Path | None:
    marker = project_root / ".git"
    if marker.is_dir():
        return marker
    if marker.is_file():
        text = marker.read_text(encoding="utf-8").strip()
        if text.startswith("gitdir:"):
            path = Path(text.split(":", 1)[1].strip())
            return (project_root / path).resolve() if not path.is_absolute() else path.resolve()
    return None


def _git_head(project_root: Path) -> str:
    try:
        git_dir = _git_dir(project_root)
        if git_dir is None:
            return "unknown"
        head = (git_dir / "HEAD").read_text(encoding="utf-8").strip()
        if _HEX_COMMIT.fullmatch(head):
            return head
        if not head.startswith("ref:"):
            return "unknown"
        ref = head.split(":", 1)[1].strip()
        common_dir = git_dir
        commondir = git_dir / "commondir"
        if commondir.is_file():
            common_dir = (git_dir / commondir.read_text(encoding="utf-8").strip()).resolve()
        # A linked worktree keeps HEAD in its private gitdir but the branch ref
        # itself lives in the common dir, so both have to be consulted before
        # falling back to packed-refs.
        for base in (git_dir, common_dir):
            loose = base / ref
            if loose.is_file():
                commit = loose.read_text(encoding="utf-8").strip()
                return commit if _HEX_COMMIT.fullmatch(commit) else "unknown"
        packed = common_dir / "packed-refs"
        if packed.is_file():
            for line in packed.read_text(encoding="utf-8").splitlines():
                if line.endswith(f" {ref}"):
                    commit = line.split(" ", 1)[0]
                    return commit if _HEX_COMMIT.fullmatch(commit) else "unknown"
    except (OSError, UnicodeError, ValueError):
        pass
    return "unknown"


def _baseline_dirty_digest(project_root: Path) -> str:
    """Digest the uncommitted working set so changes stay attributable.

    A baseline commit alone cannot support a before/after claim: an unrelated
    dirty tree silently changes what "the same suite" even means. Runs once per
    session, off the hot path, and degrades to `unknown` rather than failing.
    """

    try:
        completed = subprocess.run(
            ["git", "-C", str(project_root), "status", "--porcelain=v1"],
            capture_output=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    if completed.returncode != 0:
        return "unknown"
    payload = completed.stdout
    if not payload.strip():
        return "clean"
    entries = sorted(line for line in payload.splitlines() if line.strip())
    digest = hashlib.sha256(b"\n".join(entries)).hexdigest()
    return f"dirty:{len(entries)}:sha256:{digest}"


def _initialize(session_id: str, model: str, platform: str, kwargs: dict[str, Any]) -> _Runtime | None:
    with _runtime_lock:
        existing = _runtime_by_session.get(session_id)
        if existing is not None:
            return existing

        root = _project_root(kwargs)
        if root is None:
            return None
        manifest = verify_project_identity(root)
        if manifest is None:
            # A directory that carries a cycle manifest but fails verification is
            # an operator-visible condition (malformed contract, or an authorized
            # gate the loader rejects), not a quiet no-op.
            if (root / "docs" / "releases" / "v0.20.0" / "CYCLE.yaml").is_file():
                logger.warning(
                    "Self-improvement cycle disabled: %s carries a cycle manifest that failed verification", root
                )
            return None

        ledger = SelfImprovementLedger(manifest.ledger_path)
        baseline = _git_head(root)
        ledger.start_session(
            session_id=session_id,
            project_root=root,
            candidate_version=manifest.candidate_version,
            manifest_digest=manifest.digest,
            baseline_commit=baseline,
            baseline_dirty_digest=_baseline_dirty_digest(root),
            logical_provider=manifest.logical_provider,
            requested_model=model or manifest.current_hermes_model,
            platform=platform or "unknown",
            runtime_instance=_runtime_instance_id,
            process_id=os.getpid(),
        )
        reconciled = ledger.mark_abandoned_sessions(
            current_session_id=session_id,
            current_runtime_instance=_runtime_instance_id,
            current_process_id=os.getpid(),
            protected_session_ids=set(_runtime_by_session),
        )
        runtime = _Runtime(manifest=manifest, ledger=ledger, baseline_commit=baseline)
        _runtime_by_session[session_id] = runtime
        if reconciled:
            logger.warning("Marked %d prior self-improvement session(s) for reconciliation", reconciled)
        return runtime


def _runtime(session_id: str) -> _Runtime | None:
    with _runtime_lock:
        return _runtime_by_session.get(session_id)


def on_session_start(session_id: str, model: str = "", platform: str = "", **kwargs: Any) -> None:
    """Initialize exactly one durable cycle record for a verified Aether session."""

    try:
        _initialize(session_id, model, platform, kwargs)
    except Exception as exc:  # hooks must never crash Hermes
        logger.warning("Self-improvement session initialization failed: %s", exc)


def on_pre_llm_call(
    session_id: str,
    user_message: str,
    conversation_history: list,
    is_first_turn: bool,
    model: str,
    platform: str,
    **kwargs: Any,
) -> dict[str, str] | None:
    """Inject the bounded cycle contract on the first model turn only."""

    del user_message, conversation_history
    if not is_first_turn:
        return None
    try:
        runtime = _runtime(session_id) or _initialize(session_id, model, platform, kwargs)
        if runtime is None:
            return None
        manifest = runtime.manifest
        context = "\n".join(
            (
                "[Aether Self-Improvement Cycle]",
                f"Candidate: v{manifest.candidate_version} — {manifest.candidate_name}",
                f"Provider substrate: {manifest.logical_provider}; deterministic evidence remains authoritative.",
                "Use Harmonia only when specialist work applies; ceremonial runs are forbidden.",
                "The talk_to fallback is forbidden for this cycle.",
                "Direct takeover requires reconciliation and cleanup evidence.",
                "Other projects must never initialize or mutate this ledger.",
                "Next minor architecture: undecided pending accumulated evidence.",
                f"Manifest: {manifest.digest}",
            )
        )
        return {"context": context}
    except Exception as exc:
        logger.warning("Self-improvement context injection failed: %s", exc)
        return None


def _tool_outcome(result: Any, host_status: Any = None) -> str:
    """Prefer the host's own verdict; only parse the payload when it is absent.

    Hermes already classifies every tool result in `_tool_result_observer_fields`
    and passes it as `status`. Re-deriving it here was strictly worse: a payload
    that reports failure without an `error` key or an `exit_code` (`{"ok": false}`,
    `{"success": false}`, `{"status": "failed"}`) was recorded as a success.
    """

    if isinstance(host_status, str):
        if host_status == "ok":
            return "success"
        if host_status in {"error", "blocked"}:
            return "error"
    if not isinstance(result, str) or not result.strip():
        return "unknown"
    try:
        payload = json.loads(result)
    except (json.JSONDecodeError, TypeError):
        lowered = result.lower()
        return "error" if "error" in lowered or "traceback" in lowered else "unknown"
    if not isinstance(payload, dict):
        return "unknown"
    if payload.get("error") not in (None, "", False):
        return "error"
    if payload.get("ok") is False or payload.get("success") is False:
        return "error"
    status = payload.get("status")
    if isinstance(status, str) and status.lower() in {
        "failed",
        "failure",
        "error",
        "timeout",
        "timed_out",
        "cancelled",
        "canceled",
        "blocked",
    }:
        return "error"
    exit_code = payload.get("exit_code")
    if isinstance(exit_code, int):
        return "success" if exit_code == 0 else "error"
    return "success"


def _harmonia_classification(result: Any) -> tuple[str, str, str | None]:
    """Classify one Harmonia response against its real public wire contract.

    Returns `(phase, outcome, uncertainty)`. Harmonia reports failures as
    `{"ok": false, "error": {"code": ...}}` and successes as
    `{"ok": true, "state": ..., "uncertainty": ...}`; it never emits `status`
    or `success`. Anything that is not provably pre-admission is treated as
    post-admission, because a durable run may already exist.
    """

    payload: Any = None
    if isinstance(result, str):
        try:
            payload = json.loads(result)
        except (json.JSONDecodeError, TypeError):
            payload = None
    if not isinstance(payload, dict):
        return "unknown", "unknown", None

    uncertainty = payload.get("uncertainty")
    uncertainty = uncertainty if isinstance(uncertainty, str) and uncertainty else None

    error = payload.get("error")
    if isinstance(error, dict) and isinstance(error.get("code"), str):
        code = error["code"]
        if code in _PRE_ADMISSION_CODES:
            return "pre_admission", code, uncertainty
        if code in HARMONIA_ERROR_CODES:
            return "post_admission", code, uncertainty
        return "unknown", code, uncertainty

    state = payload.get("state")
    if isinstance(state, str) and state in _POST_ADMISSION_STATES:
        return "post_admission", state, uncertainty
    if payload.get("ok") is True:
        return "post_admission", "unknown", uncertainty
    return "unknown", "unknown", uncertainty


def on_post_tool_call(
    tool_name: str,
    args: dict,
    result: str,
    task_id: str,
    session_id: str,
    tool_call_id: str,
    duration_ms: int = 0,
    **kwargs: Any,
) -> None:
    """Persist only a redacted tool metric; never persist args or result payloads."""

    del task_id
    try:
        # A continued session never fires `on_session_start`, so initialize
        # lazily here as well or every resumed session records nothing.
        runtime = _runtime(session_id) or _initialize(session_id, "", "", kwargs)
        if runtime is None:
            return
        event_id = tool_call_id or str(uuid.uuid4())
        coordination = None
        if tool_name in {"harmonia", "mcp__olympus_v3__harmonia"}:
            phase, outcome, uncertainty = _harmonia_classification(result)
            action = args.get("action") if isinstance(args, dict) else None
            coordination = {
                "system": "harmonia",
                "action": action if action in {"start", "status", "stop"} else "unknown",
                "phase": phase,
                "outcome": outcome,
                "uncertainty": uncertainty,
            }
        runtime.ledger.record_tool_observation(
            session_id=session_id,
            tool_call_id=event_id,
            turn_id=str(kwargs.get("turn_id") or ""),
            tool_name=tool_name,
            duration_ms=duration_ms,
            outcome=_tool_outcome(result, kwargs.get("status")),
            coordination=coordination,
        )
    except Exception as exc:
        logger.warning("Self-improvement tool measurement failed: %s", exc)


def on_post_llm_call(
    session_id: str,
    user_message: str,
    assistant_response: str,
    conversation_history: list,
    model: str,
    platform: str,
    **kwargs: Any,
) -> None:
    """Persist whitelisted router metrics while discarding conversation payloads."""

    del user_message, assistant_response, conversation_history
    try:
        runtime = _runtime(session_id) or _initialize(session_id, model, platform, kwargs)
        if runtime is None:
            return
        turn_id = kwargs.get("turn_id") or kwargs.get("api_request_id") or str(uuid.uuid4())
        runtime.ledger.record_model_call(
            session_id=session_id,
            turn_id=str(turn_id),
            api_request_id=kwargs.get("api_request_id"),
            requested_model=model,
            resolved_route=kwargs.get("resolved_route"),
            resolved_model=kwargs.get("resolved_model"),
            latency_ms=kwargs.get("latency_ms"),
            input_tokens=kwargs.get("input_tokens"),
            output_tokens=kwargs.get("output_tokens"),
            reported_cost=kwargs.get("reported_cost", kwargs.get("cost")),
            error_code=kwargs.get("error_code"),
        )
    except Exception as exc:
        logger.warning("Self-improvement model measurement failed: %s", exc)


def on_session_end(
    session_id: str,
    completed: bool,
    interrupted: bool,
    model: str,
    platform: str,
    **kwargs: Any,
) -> None:
    """Record a turn outcome without falsely finalizing a continuing session."""

    del model, platform, kwargs
    try:
        runtime = _runtime(session_id)
        if runtime is not None:
            runtime.ledger.record_turn_outcome(session_id, completed=completed, interrupted=interrupted)
    except Exception as exc:
        logger.warning("Self-improvement turn finalization failed: %s", exc)


def on_session_finalize(session_id: str | None, platform: str, **kwargs: Any) -> None:
    """Finalize clean sessions; preserve interrupted sessions for reconciliation."""

    del platform, kwargs
    if not session_id:
        return
    try:
        runtime = _runtime(session_id)
        if runtime is not None:
            # Re-read the contract: evidence accrued under a digest that no
            # longer matches the file on disk must be marked, not presented as
            # if it had been produced under the shipped manifest.
            current = verify_project_identity(runtime.manifest.project_root)
            drifted = current is None or current.digest != runtime.manifest.digest
            runtime.ledger.finalize_session(session_id, manifest_drifted=drifted)
            if drifted:
                logger.warning("Cycle manifest changed during session %s; evidence marked as drifted", session_id)
            with _runtime_lock:
                _runtime_by_session.pop(session_id, None)
    except Exception as exc:
        logger.warning("Self-improvement session finalization failed: %s", exc)


def register(ctx) -> None:
    """Register the default-off lifecycle plugin with Hermes Agent."""

    ctx.register_hook("on_session_start", on_session_start)
    ctx.register_hook("pre_llm_call", on_pre_llm_call)
    ctx.register_hook("post_tool_call", on_post_tool_call)
    ctx.register_hook("post_llm_call", on_post_llm_call)
    ctx.register_hook("on_session_end", on_session_end)
    ctx.register_hook("on_session_finalize", on_session_finalize)
