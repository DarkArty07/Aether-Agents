"""Olympus structured logging — placeholder for Session 3.

Currently uses Python stdlib logging. Will be enriched in Session 3 with:
- JSON structured log format
- Session lifecycle events
- ACP message logging
- Tool call tracking
- Token usage aggregation
"""

from __future__ import annotations

import logging
import sys

# All Olympus modules use "olympus.<module>" logger namespace
# Logging goes to stderr (stdout is reserved for MCP stdio protocol)


def setup_logging(level: str = "INFO", log_file: str | None = None) -> None:
    """Configure logging for Olympus."""
    handlers: list[logging.Handler] = []

    # stderr handler (for MCP compatibility — stdout is the protocol channel)
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    ))
    handlers.append(stderr_handler)

    # Optional file handler
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        ))
        handlers.append(file_handler)

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        handlers=handlers,
        force=True,
    )