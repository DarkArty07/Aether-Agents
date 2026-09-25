"""Hermes-free Morfeo MCP contracts."""

from __future__ import annotations

from typing import Literal

McpMode = Literal["harness", "chatbot"]
McpTransport = Literal["stdio", "streamable-http"]

MODES = ("harness", "chatbot")
TRANSPORTS = ("stdio", "streamable-http")
LOOPBACK_HOST = "127.0.0.1"
MORFEO_CONTEXT_REQUIRED = "MORFEO_CONTEXT_REQUIRED"
PROFILE_NAME = "morfeo"
SESSION_SOURCE = "mcp"

HOST_DUPLICATE_TOOLS = frozenset(
    {
        "terminal",
        "process",
        "read_file",
        "write_file",
        "patch",
        "search_files",
        "execute_code",
    }
)

EXTERNAL_MCP_PREFIX = "mcp__"


class MorfeoMcpError(RuntimeError):
    """A Morfeo MCP request cannot be completed."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def visible_tool_names(names: set[str] | frozenset[str], mode: str) -> set[str]:
    """Return the MCP surface for one mode. Internal Morfeo toolsets stay intact."""

    if mode not in MODES:
        raise MorfeoMcpError("MORFEO_MODE_INVALID", f"unknown mode {mode}")
    visible = {name for name in names if not name.startswith(EXTERNAL_MCP_PREFIX)}
    if mode == "harness":
        visible -= HOST_DUPLICATE_TOOLS
    return visible


def mcp_delegate_runs_synchronously() -> bool:
    """External hosts have no Hermes conversation to receive a later injection."""

    return True
