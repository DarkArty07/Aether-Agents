"""Worker MCP server for Claude Code Implementer attempts.

Per-attempt stdio server module named `aether-worker`, exposing the Kanban
worker tools granted by the Hermes tool registry under the attempt identity,
plus `project_knowledge` and `work_memory` when enabled.

Per specs/external-implementer-harness/plan.md §3.9.
"""

from __future__ import annotations

import inspect
import json
import logging
import os
import sys
from typing import Any

logger = logging.getLogger("aether_agents.worker_mcp")

# Excluded tool families per plan §3.9:
# No file, terminal, web, memory, session, skills, delegation, todo or Morfeo tools.
EXCLUDED_TOOL_NAMES = frozenset(
    {
        "terminal",
        "execute_code",
        "read_terminal",
        "read_preview",
        "read_window_below",
        "read_file",
        "write_file",
        "patch",
        "search_files",
        "web_search",
        "web_extract",
        "memory",
        "session_search",
        "skills_list",
        "skill_view",
        "skill_manage",
        "delegate_task",
        "todo",
        "clarify",
        "process",
        "vision_analyze",
        "objective_contract",
        "morfeo_bootstrap",
    }
)
EXCLUDED_TOOL_PREFIXES = ("file_", "web_", "skill_", "morfeo_")


def is_worker_tool(name: str) -> bool:
    """Determine whether a tool definition belongs to the worker surface.

    Derives the surface from the tool registry rather than hand-picking:
    includes kanban tools plus project_knowledge and work_memory when available,
    excluding file, terminal, web, memory, session, skills, delegation, todo
    and Morfeo tools.
    """
    if name in EXCLUDED_TOOL_NAMES or any(name.startswith(p) for p in EXCLUDED_TOOL_PREFIXES):
        return False
    if name.startswith("kanban_"):
        return True
    if name in ("project_knowledge", "work_memory"):
        return True
    return False


def discover_worker_tool_definitions() -> list[dict[str, Any]]:
    """Discover the active tool definitions and filter for the worker surface."""
    try:
        from hermes_cli.config import load_config
        from hermes_cli.plugins import discover_plugins
        from hermes_cli.tools_config import _get_platform_tools
        from model_tools import get_tool_definitions

        discover_plugins()
        config = load_config()
        toolsets = _get_platform_tools(config, "cli", include_default_mcp_servers=False)
        definitions = get_tool_definitions(
            enabled_toolsets=sorted(toolsets),
            quiet_mode=True,
            skip_tool_search_assembly=True,
        )
    except Exception as exc:
        logger.warning("Failed to discover tools through Hermes registry: %s", exc)
        return []

    worker_tools: list[dict[str, Any]] = []
    for item in definitions or []:
        if not isinstance(item, dict) or item.get("type") != "function":
            continue
        func = item.get("function") or {}
        name = func.get("name")
        if isinstance(name, str) and is_worker_tool(name):
            worker_tools.append(item)
    return worker_tools


def _schema_signature(schema: dict[str, Any] | None) -> inspect.Signature:
    """Convert a JSON Schema property dict into a Python inspect.Signature for FastMCP."""
    mapping = {
        "string": str,
        "integer": int,
        "number": float,
        "boolean": bool,
        "array": list,
        "object": dict,
    }
    properties = (schema or {}).get("properties") or {}
    required = set((schema or {}).get("required") or [])
    parameters = []
    for name, spec in properties.items():
        if not isinstance(name, str) or name.startswith("_"):
            continue
        declared = (spec or {}).get("type")
        py_type = mapping.get(declared, Any) if isinstance(declared, str) else Any
        default = inspect.Parameter.empty if name in required else None
        parameters.append(
            inspect.Parameter(
                name,
                inspect.Parameter.KEYWORD_ONLY,
                annotation=py_type,
                default=default,
            )
        )
    return inspect.Signature(parameters)


def dispatch_worker_call(name: str, arguments: dict[str, Any]) -> str:
    """Dispatch a tool call to Hermes native registry with supplied arguments."""
    try:
        import model_tools  # noqa: F401 - ensure tools are registered
        from tools.registry import registry

        result = registry.dispatch(name, arguments)
        if isinstance(result, str):
            return result
        return json.dumps(result, ensure_ascii=False)
    except Exception as exc:
        logger.exception("Failed to dispatch worker tool call %s: %s", name, exc)
        return json.dumps({"error": f"Tool execution failed: {type(exc).__name__}: {exc}"})


def create_worker_mcp_server() -> Any:
    """Create and configure the FastMCP aether-worker stdio server."""
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("aether-worker")
    definitions = discover_worker_tool_definitions()

    for item in definitions:
        func = item["function"]
        name = func["name"]
        description = func.get("description") or name
        schema = func.get("parameters") or {}

        def make_handler(tool_name: str):
            def handler(**arguments: Any) -> str:
                # Forward only supplied arguments (drop None values per #556 bridge behavior)
                supplied = {k: v for k, v in arguments.items() if v is not None}
                return dispatch_worker_call(tool_name, supplied)

            handler.__signature__ = _schema_signature(schema)  # type: ignore[attr-defined]
            handler.__name__ = tool_name
            return handler

        mcp.tool(name=name, description=description)(make_handler(name))

    return mcp


def main() -> int:
    """Run the aether-worker MCP server over stdio."""
    logging.basicConfig(level=logging.INFO, stream=sys.stderr, format="%(name)s: %(message)s")
    os.environ["HERMES_QUIET"] = "1"
    os.environ["HERMES_REDACT_SECRETS"] = "true"

    try:
        mcp = create_worker_mcp_server()
        mcp.run(transport="stdio")
        return 0
    except Exception as exc:
        print(f"aether-worker error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
