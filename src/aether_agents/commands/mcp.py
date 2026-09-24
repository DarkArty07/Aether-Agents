"""Manager-side Morfeo MCP launcher. This module does not import Hermes or the MCP SDK."""

from __future__ import annotations

import argparse
import os
import sys

from aether_agents.launcher import (
    ActivationError,
    _resolve_component_paths,
    _resolve_project,
    _resolve_target_python,
    _resolve_target_source_root,
    scrubbed_environment,
)
from aether_agents.mcp.contracts import LOOPBACK_HOST, MODES, TRANSPORTS
from aether_agents.paths import data_root

__all__ = ["build_subparser", "run_mcp"]


def build_subparser(subparsers: "argparse._SubParsersAction") -> argparse.ArgumentParser:
    parser = subparsers.add_parser("mcp", help="Expose the canonical Morfeo role over MCP.")
    commands = parser.add_subparsers(dest="mcp_command")
    morfeo = commands.add_parser("morfeo", help="Morfeo role surface.")
    morfeo_commands = morfeo.add_subparsers(dest="morfeo_command")
    serve = morfeo_commands.add_parser("serve", help="Serve Morfeo tools to one external MCP host.")
    serve.add_argument("--mode", choices=MODES, default="harness")
    serve.add_argument("--transport", choices=TRANSPORTS, default=None)
    serve.add_argument("--project", default=None)
    serve.add_argument("--port", type=int, default=8765)
    serve.add_argument("--host", default=LOOPBACK_HOST)
    return parser


def run_mcp(args: argparse.Namespace) -> int:
    if (
        getattr(args, "mcp_command", None) != "morfeo"
        or getattr(args, "morfeo_command", None) != "serve"
    ):
        print("aether: usage: aether mcp morfeo serve", file=sys.stderr)
        return 2
    if getattr(args, "host", LOOPBACK_HOST) != LOOPBACK_HOST:
        print("aether: Morfeo MCP accepts only 127.0.0.1", file=sys.stderr)
        return 2
    mode = args.mode
    transport = args.transport or ("streamable-http" if mode == "chatbot" else "stdio")
    try:
        repo, project_id = _resolve_project(args.project)
        profile, hermes, _tui = _resolve_component_paths(repo)
        runtime_root = data_root() / "runtime"
        python = _resolve_target_python(hermes, runtime_root)
        source_root = _resolve_target_source_root(hermes, runtime_root, repo)
    except (ActivationError, OSError) as exc:
        print(f"aether: {exc}", file=sys.stderr)
        return 2
    if not python.is_file():
        print("aether: active runtime Python is unavailable", file=sys.stderr)
        return 2
    environment = scrubbed_environment(
        hermes_home=str(profile),
        project_id=project_id,
        project_root=str(repo),
        target_python=str(python),
        target_source_root=None if source_root is None else str(source_root),
    )
    environment["HERMES_QUIET"] = "1"
    environment["HERMES_REDACT_SECRETS"] = "true"
    command = [
        str(python),
        "-m",
        "aether_agents.mcp.morfeo_server",
        "--mode",
        mode,
        "--transport",
        transport,
        "--project",
        str(repo),
        "--project-id",
        project_id,
        "--profile",
        str(profile),
        "--port",
        str(args.port),
        "--host",
        LOOPBACK_HOST,
    ]
    try:
        os.chdir(repo)
        os.execve(str(python), command, environment)
    except OSError as exc:
        print(f"aether: {exc}", file=sys.stderr)
        return 2
    raise AssertionError("os.execve returned unexpectedly")
