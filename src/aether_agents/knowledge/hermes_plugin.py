"""Optional native Hermes plugin: identical tools for all three Aether roles."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .bindings import context_for_session
from .common import ROLES, KnowledgeError
from .service import KnowledgeService, error_response, parameters, validate_arguments


def _call(ctx: Any, tool: str, arguments: dict[str, Any], **runtime: Any) -> str:
    action = arguments.get("action", "") if isinstance(arguments, dict) else ""
    try:
        validate_arguments(tool, arguments)
        role = getattr(ctx, "profile_name", "")
        if role not in ROLES:
            raise KnowledgeError("PROJECT_UNRESOLVED", "This plugin requires an Aether role.")
        state_setting = ctx.get_config("state_root", None)
        cache_setting = ctx.get_config("cache_root", None)
        service = KnowledgeService(
            Path(state_setting) if state_setting else None,
            Path(cache_setting) if cache_setting else None,
        )
        # Hermes supplies these callback kwargs; identity fields in model args are rejected.
        session = runtime.get("session_id") or ""
        if not isinstance(session, str):
            raise KnowledgeError("PROJECT_UNRESOLVED", "Invalid native session identity.")
        from hermes_constants import get_hermes_home

        context = context_for_session(
            service.state_root,
            role,
            session,
            hermes_home=get_hermes_home(),
            task_id=str(runtime.get("task_id") or ""),
            run_id=str(runtime.get("run_id") or ""),
        )
        result = service.execute(context, tool, arguments)
    except KnowledgeError as exc:
        result = error_response(tool, str(action), exc)
    except Exception:
        result = error_response(
            tool,
            str(action),
            KnowledgeError(
                "COMPONENT_UNAVAILABLE",
                "Knowledge integration failed; ordinary file tools remain available.",
            ),
        )
    return json.dumps(result, ensure_ascii=False)


def register(ctx: Any) -> None:
    """Register without importing Graphify, starting a process, or accessing project data."""
    if getattr(ctx, "profile_name", "") not in ROLES or not callable(
        getattr(ctx, "get_config", None)
    ):
        return
    if ctx.get_config("enabled", False) is not True:
        return

    def knowledge_handler(args: dict[str, Any], **runtime: Any) -> str:
        return _call(ctx, "project_knowledge", args, **runtime)

    def memory_handler(args: dict[str, Any], **runtime: Any) -> str:
        return _call(ctx, "work_memory", args, **runtime)

    ctx.register_tool(
        name="project_knowledge",
        toolset="aether_knowledge",
        description="Query and update the current project revision's derived technical map.",
        schema={
            "name": "project_knowledge",
            "description": "Consult or refresh the bound project graph. Sources and revision accompany results; no identity or filesystem path override is accepted.",
            "parameters": parameters("project_knowledge"),
        },
        handler=knowledge_handler,
    )
    ctx.register_tool(
        name="work_memory",
        toolset="aether_knowledge",
        description="Save, retrieve, correct and reflect this role's project experiences.",
        schema={
            "name": "work_memory",
            "description": "Maintain project-scoped role experiences. Read original notes for full lessons; reflect aggregates signals only. Correct requires the revision returned by read.",
            "parameters": parameters("work_memory"),
        },
        handler=memory_handler,
    )
