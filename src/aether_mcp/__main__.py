"""Explicit stdio entry point for the default-off Aether MCP process."""

from __future__ import annotations

import asyncio
import logging
import sys

from aether_mcp.server import create_server, run_stdio


class _StdioEventLoop(asyncio.SelectorEventLoop):
    """Selector loop with its unused cross-thread wakeup socket disabled."""

    def disable_wakeup_socket(self) -> None:
        super()._close_self_pipe()

    def _close_self_pipe(self) -> None:
        if self._ssock is not None:
            super()._close_self_pipe()


def main() -> int:
    """Run one stdio-only MCP process until normal input closure."""
    logging.basicConfig(level=logging.ERROR, stream=sys.stderr)
    loop = _StdioEventLoop()
    loop.disable_wakeup_socket()
    try:
        loop.run_until_complete(run_stdio(create_server()))
    except KeyboardInterrupt:
        return 0
    except Exception:
        sys.stderr.write("aether-mcp server failed\n")
        return 1
    finally:
        loop.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
