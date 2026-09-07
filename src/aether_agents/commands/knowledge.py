"""Explicit operator commands for the optional project-knowledge component."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _project_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--project-id", required=True, help="Portable project UUID, not a folder name."
    )
    parser.add_argument("--role", choices=("morfeo", "supervisor", "implementer"), default="morfeo")
    parser.add_argument(
        "--workspace", type=Path, default=None, help="Verified registered checkout or worktree."
    )


def build_subparser(subparsers: Any) -> None:
    parser = subparsers.add_parser(
        "knowledge", help="Manage optional Graphify knowledge and role experiences."
    )
    children = parser.add_subparsers(dest="knowledge_command", required=True)
    for name in (
        "install",
        "configure",
        "disable",
        "doctor",
        "bind",
        "status",
        "query",
        "update",
        "call",
        "export",
        "delete",
    ):
        child = children.add_parser(name)
        child.add_argument("--json", action="store_true")
        if name == "configure":
            child.add_argument(
                "--python", type=Path, required=True, help="Isolated Graphify 0.9.54 interpreter."
            )
        if name in ("bind", "status", "query", "update", "call", "export", "delete"):
            _project_arguments(child)
        if name == "bind":
            child.add_argument("--session", required=True)
            child.add_argument("--replace", action="store_true")
        if name == "query":
            child.add_argument("--question", required=True)
            child.add_argument("--budget-tokens", type=int, default=2000)
        if name == "update":
            child.add_argument("--reason", default="Operator requested project refresh")
            child.add_argument("--mode", choices=("configured", "structural"), default="configured")
        if name == "call":
            child.add_argument(
                "--tool", choices=("project_knowledge", "work_memory"), required=True
            )
            child.add_argument(
                "--arguments", required=True, help="JSON object matching the native tool contract."
            )
        if name == "delete":
            child.add_argument("--note-id", required=True)
            child.add_argument(
                "--yes",
                action="store_true",
                help="Confirm deletion of this note and its retained revisions.",
            )


def run_knowledge(args: argparse.Namespace, service: Any = None) -> int:
    from aether_agents.knowledge.bindings import bind_session
    from aether_agents.knowledge.common import KnowledgeError
    from aether_agents.knowledge.component import configure, disable, install
    from aether_agents.knowledge.context import resolve_context
    from aether_agents.knowledge.memory import WorkMemoryStore
    from aether_agents.knowledge.service import KnowledgeService, error_response

    service = service or KnowledgeService()
    name = args.knowledge_command
    try:
        if name == "configure":
            result = configure(service, args.python)
        elif name == "install":
            result = install(service)
        elif name == "disable":
            result = disable(service)
        elif name == "doctor":
            configuration = service.configuration()
            probe = service.backend().probe()
            semantic_cfg = configuration.get("semantic", {})
            semantic_enabled = configuration.get("semantic_enabled", False) or semantic_cfg.get(
                "enabled", False
            )
            result = {
                "ok": True,
                "component": probe,
                "ownership": configuration.get("ownership"),
                "lock_id": configuration.get("lock_id"),
                "semantic_enabled": bool(semantic_enabled),
                "warning": "Component health does not prove agent E2E behavior or token savings.",
            }
        elif name == "bind":
            ctx = bind_session(
                service.state_root,
                args.project_id,
                args.role,
                args.session,
                root=args.workspace,
                replace=args.replace,
            )
            result = {
                "ok": True,
                "project_id": ctx.project_id,
                "view_id": ctx.view_id,
                "role_id": ctx.role_id,
                "session_id": ctx.session_id,
            }
        else:
            ctx = resolve_context(
                args.project_id, args.role, state_root=service.state_root, root=args.workspace
            )
            if name in ("export", "delete"):
                if name == "delete" and not args.yes:
                    raise KnowledgeError(
                        "CONFIRMATION_REQUIRED",
                        "Use --yes to delete this note and retained revisions.",
                    )
                store = WorkMemoryStore(service.state_root)
                result = store.execute(
                    ctx, name, {"note_id": args.note_id} if name == "delete" else {}
                )
            else:
                tool = "project_knowledge"
                if name == "call":
                    tool = args.tool
                    try:
                        parameters = json.loads(args.arguments)
                    except ValueError as exc:
                        raise KnowledgeError(
                            "ARGUMENT_INVALID", "--arguments must be a JSON object."
                        ) from exc
                elif name == "query":
                    parameters = {
                        "action": "query",
                        "question": args.question,
                        "budget_tokens": args.budget_tokens,
                    }
                elif name == "update":
                    parameters = {"action": "update", "reason": args.reason, "mode": args.mode}
                else:
                    parameters = {"action": "status"}
                result = service.execute(ctx, tool, parameters)
    except KnowledgeError as exc:
        result = error_response("project_knowledge", name, exc)
    except (OSError, ValueError, TypeError, KeyError):
        result = error_response(
            "project_knowledge",
            name,
            KnowledgeError("COMPONENT_UNAVAILABLE", "The knowledge operation could not complete."),
        )
    print(json.dumps(result, ensure_ascii=False, indent=None if args.json else 2))
    return 0 if result.get("ok") else 1
