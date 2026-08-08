"""Static identity and protocol exports for the default-off Aether MCP process."""

from aether_mcp.protocol import PROTOCOL_VERSION

__version__ = "0.22.0.dev0"
PROTOCOL_ID = PROTOCOL_VERSION
SERVER_NAME = "aether-mcp"

__all__ = ("PROTOCOL_ID", "PROTOCOL_VERSION", "SERVER_NAME", "__version__")
