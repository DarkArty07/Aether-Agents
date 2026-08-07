"""Zero-tool stdio MCP server factory."""

from __future__ import annotations

import asyncio
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

INSTRUCTIONS = f"{PROTOCOL_ID}; Aether package {__version__}; default-off; no tools registered."


def create_server() -> FastMCP:
    """Create the bounded M2.1a server without registering capabilities."""
    return FastMCP(
        SERVER_NAME,
        instructions=INSTRUCTIONS,
        log_level="ERROR",
    )


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
