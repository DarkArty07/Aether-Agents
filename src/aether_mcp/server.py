"""Operational stdio MCP server factory."""

from __future__ import annotations

import asyncio
import inspect
import queue
import sys
import threading
import warnings

import anyio
from mcp import types

warnings.filterwarnings(
    "ignore",
    message=r"Field 'lifespan' has an incomplete definition:.*",
    category=UserWarning,
    module=r"pydantic_settings\.sources\.utils",
)

from mcp.server.fastmcp import FastMCP  # noqa: E402
from mcp.shared.message import SessionMessage  # noqa: E402

from aether_mcp import PROTOCOL_ID, SERVER_NAME, __version__  # noqa: E402
from aether_mcp.protocol import TOOL_SCHEMAS, export_schema_bundle  # noqa: E402
from aether_mcp.runtime import OperationalRuntime  # noqa: E402

INSTRUCTIONS = f"{PROTOCOL_ID}; Aether package {__version__}; approved operational tool surface."

_TOOLS = (
    "project_admit", "project_inspect", "swarm_validate", "swarm_start", "swarm_status",
    "swarm_dispatch", "swarm_message", "swarm_reconcile", "swarm_retry", "swarm_cancel",
    "swarm_close", "swarm_trace", "orca_search", "orca_describe", "orca_call",
)


def _argument_annotation(schema: dict[str, object]) -> object:
    """Preserve string payloads that FastMCP would otherwise JSON-coerce."""
    schema_type = schema.get("type")
    if schema_type == "string":
        return str
    if isinstance(schema_type, list) and "string" in schema_type and "null" in schema_type:
        return str | None
    return object


def create_server(runtime: OperationalRuntime | None = None) -> FastMCP:
    """Create the 15-tool facade without opening state or contacting Orca."""
    server = FastMCP(
        SERVER_NAME,
        instructions=INSTRUCTIONS,
        log_level="ERROR",
    )
    active_runtime = runtime or OperationalRuntime()

    def register(name: str) -> None:
        schema = TOOL_SCHEMAS[name]

        def operation(**arguments: object) -> dict:
            return active_runtime.invoke(name, dict(arguments))

        operation.__name__ = name
        operation.__annotations__ = {
            key: _argument_annotation(property_schema)
            for key, property_schema in schema["properties"].items()
        }
        operation.__annotations__["return"] = dict
        operation.__signature__ = inspect.Signature(
            [
                inspect.Parameter(
                    key,
                    inspect.Parameter.KEYWORD_ONLY,
                    annotation=_argument_annotation(property_schema),
                )
                for key, property_schema in schema["properties"].items()
            ]
        )

        def registered_operation(**arguments: object) -> dict:
            return operation(**arguments)

        registered_operation.__signature__ = operation.__signature__
        registered_operation.__annotations__ = operation.__annotations__
        server.add_tool(registered_operation, name=name, description=f"Aether operational capability: {name}")
        tool = server._tool_manager.get_tool(name)
        assert tool is not None
        bundle = export_schema_bundle()
        tool.parameters = next(item["inputSchema"] for item in bundle["tools"] if item["name"] == name)
        tool.fn_metadata.arg_model.model_config["extra"] = "allow"
        tool.fn_metadata.arg_model.model_rebuild(force=True)

    for name in _TOOLS:
        register(name)
    return server


async def run_stdio(server: FastMCP) -> None:
    """Run FastMCP over line-delimited stdio with deterministic EOF cleanup."""
    read_send, read_receive = anyio.create_memory_object_stream[SessionMessage | Exception](0)
    write_send, write_receive = anyio.create_memory_object_stream[SessionMessage](0)

    async def read_stdin() -> None:
        lines: queue.Queue[bytes | None] = queue.Queue()

        def collect_lines() -> None:
            for line in sys.stdin.buffer:
                lines.put(line)
            lines.put(None)

        threading.Thread(target=collect_lines, name="aether-mcp-stdin", daemon=True).start()
        async with read_send:
            while True:
                try:
                    line = lines.get_nowait()
                except queue.Empty:
                    await asyncio.sleep(0.01)
                    continue
                if line is None:
                    break
                try:
                    message = types.JSONRPCMessage.model_validate_json(line)
                except Exception as exc:
                    await read_send.send(exc)
                else:
                    await read_send.send(SessionMessage(message))

    async def write_stdout() -> None:
        async with write_receive:
            async for session_message in write_receive:
                payload = session_message.message.model_dump_json(by_alias=True, exclude_none=True)
                sys.stdout.write(payload + "\n")
                sys.stdout.flush()

    async with asyncio.TaskGroup() as tasks:
        reader = tasks.create_task(read_stdin())
        writer = tasks.create_task(write_stdout())
        try:
            await server._mcp_server.run(
                read_receive,
                write_send,
                server._mcp_server.create_initialization_options(),
            )
        finally:
            await write_send.aclose()
            reader.cancel()
            writer.cancel()
