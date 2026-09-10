"""Native Hermes plugin exposing the Aether Telegram Monitor.

The plugin is Morfeo-only and gated by the Morfeo profile opt-in
(``plugins.entries.aether-telegram-monitor.settings.enabled``).  It deliberately keeps
two disjoint surfaces:

* ``aether_monitor`` in the ``aether_monitor`` toolset — the ordinary Morfeo control
  tool for ``status``/``on``/``off``/``history``.  It is refused inside monitor/reporter
  runs, which never control the monitor.
* ``aether_monitor_report_snapshot`` in the dedicated ``aether_monitor_reporting``
  toolset — the only tool a reporter run may use.  The hourly native job sets
  ``enabled_toolsets=["aether_monitor_reporting"]`` so terminal, file, messaging, board
  lifecycle, delegation, cron and control tools are provably absent from narration.

Hooks never send messages from ordinary sessions: ``post_tool_call`` only enrolls
project-bound direct work, ``post_llm_call`` validates and persists a reporter narrative,
and ``on_session_end`` closes a direct interval or commits the reporter outbox through
the accepted MON-04 delivery adapter.  All Hermes-adjacent work is delegated to
:mod:`aether_agents.monitor.runtime`, so this module stays a thin registration surface.
"""

from __future__ import annotations

import json
from typing import Any, Mapping

from aether_agents.monitor.runtime import (
    CONTROL_TOOL,
    CONTROL_TOOLSET,
    REPORTER_TOOL,
    REPORTER_TOOLSET,
)
from aether_agents.monitor.service import (
    ACTION_HISTORY,
    ACTIONS,
    MORFEO_PROFILE,
    MonitorActionError,
    error_envelope,
)
from aether_agents.monitor.store import MonitorStore

__all__ = ["register"]

ROLE = MORFEO_PROFILE

_CONTROL_DESCRIPTION = "Control and read the Aether Telegram Monitor: status, on, off and history."
_REPORT_DESCRIPTION = (
    "Read the exact bounded monitor snapshot awaiting narration for this monitor run."
)

_CONTROL_SCHEMA = {
    "name": CONTROL_TOOL,
    "description": (
        "Control the Aether Telegram Monitor for this installation. status reports the "
        "enabled state, owned native job, next cut, coverage gaps and last delivery "
        "outcomes; on validates the provisioned runtime and existing Telegram destination "
        "and creates or reuses the single owned hourly job; off durably disables the "
        "monitor before pausing that job; history lists bounded interval records without "
        "source content. No credential, destination, provider or model argument is "
        "accepted."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": list(ACTIONS)},
            "limit": {
                "type": "integer",
                "minimum": 1,
                "maximum": 200,
                "description": "History page size; only valid with action=history.",
            },
        },
        "required": ["action"],
        "additionalProperties": False,
    },
}

_REPORT_SCHEMA = {
    "name": REPORTER_TOOL,
    "description": (
        "Return the canonical bounded monitor snapshot for the pending report of this "
        "monitor run. Read-only: it cannot send messages, change the monitor, or read any "
        "other project data."
    ),
    "parameters": {
        "type": "object",
        "properties": {},
        "additionalProperties": False,
    },
}


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _store(ctx: Any) -> MonitorStore:
    return MonitorStore()


def _language(ctx: Any) -> str | None:
    try:
        value = ctx.get_config("language", None)
    except Exception:
        return None
    return value if isinstance(value, str) and value.strip() else None


def _session_id(runtime: Mapping[str, Any]) -> str:
    value = runtime.get("session_id")
    return value if isinstance(value, str) else ""


def _is_monitor_run(session_id: str) -> bool:
    """A monitor/reporter run is exactly a native cron session."""

    return session_id.startswith("cron_")


def _control_handler(ctx: Any, args: Mapping[str, Any], **runtime: Any) -> str:
    from aether_agents.monitor import runtime as monitor_runtime

    action = args.get("action") if isinstance(args, Mapping) else None
    limit = args.get("limit") if isinstance(args, Mapping) else None
    action_text = action if isinstance(action, str) else ""
    extra = set(args) - {"action", "limit"} if isinstance(args, Mapping) else set()
    session_id = _session_id(runtime)
    if extra or not isinstance(action, str) or action not in ACTIONS:
        return _json(
            error_envelope(
                action_text,
                "INVALID_ARGUMENT",
                "action must be status, on, off or history and no other argument is accepted",
            )
        )
    if limit is not None:
        if action != ACTION_HISTORY or isinstance(limit, bool) or not isinstance(limit, int):
            return _json(
                error_envelope(action, "INVALID_ARGUMENT", "limit is only valid with history")
            )
    if _is_monitor_run(session_id):
        return _json(
            error_envelope(
                action,
                "MONITOR_RUN_CONTROL_REFUSED",
                "monitor runs cannot control the monitor",
            )
        )
    envelope = monitor_runtime.execute_action(action, limit=limit, store=_store(ctx))
    return _json(envelope)


def _report_handler(ctx: Any, args: Mapping[str, Any], **runtime: Any) -> str:
    from aether_agents.monitor import runtime as monitor_runtime

    session_id = _session_id(runtime)
    if not _is_monitor_run(session_id):
        return _json(
            error_envelope(
                "report-snapshot",
                "REPORTER_CONTEXT_REQUIRED",
                "this read tool is only available to a monitor run",
            )
        )
    try:
        text = monitor_runtime.reporter_snapshot(
            {"session_id": session_id, "platform": "cron"},
            store=_store(ctx),
            profile_name=getattr(ctx, "profile_name", None),
        )
    except MonitorActionError as error:
        return _json(error_envelope("report-snapshot", error.code, error.message))
    except Exception:
        return _json(
            error_envelope(
                "report-snapshot",
                "SNAPSHOT_UNAVAILABLE",
                "the pending monitor snapshot is unavailable",
            )
        )
    return text


def register(ctx: Any) -> None:
    """Register the Morfeo monitor tools and hooks for one native profile."""

    if getattr(ctx, "profile_name", "") != ROLE:
        return
    if not callable(getattr(ctx, "get_config", None)):
        return
    if ctx.get_config("enabled", False) is not True:
        return

    def control_handler(args: dict[str, Any], **runtime: Any) -> str:
        return _control_handler(ctx, args, **runtime)

    def report_handler(args: dict[str, Any], **runtime: Any) -> str:
        return _report_handler(ctx, args, **runtime)

    ctx.register_tool(
        name=CONTROL_TOOL,
        toolset=CONTROL_TOOLSET,
        description=_CONTROL_DESCRIPTION,
        schema=_CONTROL_SCHEMA,
        handler=control_handler,
    )
    ctx.register_tool(
        name=REPORTER_TOOL,
        toolset=REPORTER_TOOLSET,
        description=_REPORT_DESCRIPTION,
        schema=_REPORT_SCHEMA,
        handler=report_handler,
    )

    register_hook = getattr(ctx, "register_hook", None)
    if not callable(register_hook):
        return

    from aether_agents.monitor import runtime as monitor_runtime

    def post_tool_call_callback(**payload: Any) -> None:
        monitor_runtime.handle_post_tool_call(
            payload, store=_store(ctx), profile_name=getattr(ctx, "profile_name", None)
        )

    def post_llm_call_callback(**payload: Any) -> None:
        report_id = monitor_runtime.handle_post_llm_call(
            payload,
            store=_store(ctx),
            profile_name=getattr(ctx, "profile_name", None),
            language=_language(ctx),
        )
        if report_id is None:
            monitor_runtime.handle_post_llm_call_direct(
                payload, store=_store(ctx), profile_name=getattr(ctx, "profile_name", None)
            )

    def session_end_callback(**payload: Any) -> None:
        run = monitor_runtime.handle_session_end(
            payload,
            store=_store(ctx),
            profile_name=getattr(ctx, "profile_name", None),
            language=_language(ctx),
        )
        if run is None:
            monitor_runtime.handle_session_end_direct(
                payload, store=_store(ctx), profile_name=getattr(ctx, "profile_name", None)
            )

    for name, callback in (
        ("post_tool_call", post_tool_call_callback),
        ("post_llm_call", post_llm_call_callback),
        ("on_session_end", session_end_callback),
    ):
        try:
            register_hook(name, callback)
        except Exception:
            # A missing future/older hook must not break plugin load; the monitor then
            # runs without that evidence surface instead of failing the whole profile.
            continue
