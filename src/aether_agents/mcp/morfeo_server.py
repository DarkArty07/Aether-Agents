"""Runtime entry for Morfeo MCP. Logs go to stderr. stdout is the protocol."""

from __future__ import annotations

import argparse
import inspect
import logging
import sys
import uuid
from pathlib import Path
from typing import Any

from aether_agents.mcp.bridge import ToolBridge, bootstrap_payload
from aether_agents.mcp.contracts import LOOPBACK_HOST, MODES, TRANSPORTS, MorfeoMcpError
from aether_agents.mcp.session import SessionTable

logger = logging.getLogger("aether_agents.mcp")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aether-agents-morfeo-mcp")
    parser.add_argument("--mode", choices=MODES, required=True)
    parser.add_argument("--transport", choices=TRANSPORTS, required=True)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--host", default=LOOPBACK_HOST)
    return parser


def client_key(ctx: Any) -> str:
    session = getattr(ctx, "session", None)
    if session is not None:
        return f"session:{id(session)}"
    request = getattr(ctx, "request_context", None)
    if request is not None:
        return f"request:{id(request)}"
    return "stdio"


def _schema_signature(schema: dict[str, Any] | None) -> inspect.Signature:
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
    parameters = [
        inspect.Parameter("ctx", inspect.Parameter.KEYWORD_ONLY, annotation=Any),
    ]
    for name, spec in properties.items():
        if not isinstance(name, str) or name.startswith("_") or name == "ctx":
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


def prepare_bridge(args: argparse.Namespace) -> ToolBridge:
    from aether_agents.mcp import hermes_adapter

    project = args.project.resolve()
    profile = args.profile.resolve()
    hermes_adapter.bind_profile(profile, project, args.project_id)
    definitions, toolsets = hermes_adapter.discover_effective_tools(profile)
    database = hermes_adapter.open_session_db()
    holder: dict[str, ToolBridge] = {}

    def on_bootstrap(session: Any) -> dict[str, Any]:
        if session.session_id is None:
            session.session_id = hermes_adapter.create_hermes_session(database, project)
            session.task_id = uuid.uuid4().hex
            session.agent = hermes_adapter.create_context_agent(
                session_id=session.session_id,
                session_db=database,
                task_id=session.task_id,
                project=project,
                toolsets=toolsets,
            )
        visible = sorted(holder["bridge"].visible)
        return hermes_adapter.make_snapshot(
            profile=profile,
            project=project,
            project_id=args.project_id,
            mode=args.mode,
            tool_names=visible,
        )

    def on_close(session: Any) -> None:
        if session.session_id:
            hermes_adapter.end_hermes_session(database, session.session_id)

    bridge = ToolBridge(
        sessions=SessionTable(),
        definitions=definitions,
        mode=args.mode,
        invoke=hermes_adapter.invoke,
        on_bootstrap=on_bootstrap,
        on_close=on_close,
    )
    holder["bridge"] = bridge
    return bridge


def install_tools(mcp: Any, bridge: ToolBridge, project_id: str, project: Path) -> None:
    from mcp.server.fastmcp import Context

    def bootstrap(ctx: Context) -> dict[str, Any]:
        session = bridge.ensure(client_key(ctx), project_id=project_id, project_root=project)
        try:
            snapshot = bridge.bootstrap(session)
        except MorfeoMcpError as exc:
            return {"error": exc.code, "message": exc.message}
        return bootstrap_payload(snapshot)

    mcp.tool(
        name="morfeo_bootstrap", description="Load the Morfeo role context for this connection."
    )(bootstrap)

    for item in bridge.published():
        function = item["function"]
        name = function["name"]
        description = function.get("description") or name
        schema = function.get("parameters") or {}

        def handler(ctx: Context, _name: str = name, **arguments: Any) -> str:
            session = bridge.ensure(client_key(ctx), project_id=project_id, project_root=project)
            try:
                return bridge.call(session, _name, arguments)
            except MorfeoMcpError as exc:
                return exc.code

        handler.__signature__ = _schema_signature(schema)  # type: ignore[attr-defined]
        handler.__name__ = name
        mcp.tool(name=name, description=description)(handler)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, stream=sys.stderr, format="%(name)s %(message)s")
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.host != LOOPBACK_HOST:
        print("aether: Morfeo MCP accepts only 127.0.0.1", file=sys.stderr)
        return 2
    if args.transport == "stdio":
        os_quiet()
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError:
        print("aether: the runtime MCP extra is not installed", file=sys.stderr)
        return 2
    bridge = prepare_bridge(args)
    mcp = FastMCP("morfeo")
    settings = getattr(mcp, "settings", None)
    if settings is not None:
        settings.host = LOOPBACK_HOST
        settings.port = args.port
    install_tools(mcp, bridge, args.project_id, args.project.resolve())
    mcp.run(transport=args.transport)
    return 0


def os_quiet() -> None:
    import os

    os.environ["HERMES_QUIET"] = "1"
    os.environ["HERMES_REDACT_SECRETS"] = "true"


if __name__ == "__main__":
    raise SystemExit(main())
