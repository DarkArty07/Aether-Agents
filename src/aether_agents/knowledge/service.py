"""Shared validated tool contracts; no role-specific reduction of capabilities."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from aether_agents.paths import state_root as product_state_root

from .common import KnowledgeError, load_json
from .context import KnowledgeContext
from .graphify import GraphifyBackend
from .memory import WorkMemoryStore
from .snapshots import KnowledgeStore

KNOWLEDGE_ACTIONS = (
    "status",
    "query",
    "explain",
    "neighbors",
    "community",
    "path",
    "impact",
    "update",
)
MEMORY_ACTIONS = ("save", "search", "read", "correct", "reflect")
_TEXT = {"type": "string", "minLength": 1, "maxLength": 16000}
_BUDGET = {"type": "integer", "minimum": 128, "maximum": 8000}
_EVIDENCE = {
    "type": "array",
    "maxItems": 20,
    "items": {
        "type": "object",
        "additionalProperties": False,
        "required": ["path"],
        "properties": {
            "path": {"type": "string", "minLength": 1, "maxLength": 500},
            "revision": {"type": "string", "pattern": "^[a-f0-9]{40,64}$"},
            "locator": {"type": "string", "maxLength": 1500},
            "result": {"type": "string", "maxLength": 1500},
        },
    },
}
_FIELDS: dict[str, dict[str, Any]] = {
    "question": _TEXT,
    "node": _TEXT,
    "relation": _TEXT,
    "source": _TEXT,
    "target": _TEXT,
    "community_id": {"type": "integer", "minimum": 0},
    "depth": {"type": "integer", "minimum": 1, "maximum": 6},
    "max_hops": {"type": "integer", "minimum": 1, "maximum": 20},
    "budget_tokens": _BUDGET,
    "reason": _TEXT,
    "mode": {"type": "string", "enum": ["configured", "structural"]},
    "changed_paths": {
        "type": "array",
        "maxItems": 500,
        "items": {"type": "string", "maxLength": 500},
    },
    "situation": {"type": "string", "minLength": 1, "maxLength": 4096},
    "lesson": _TEXT,
    "applicability": {"type": "string", "minLength": 1, "maxLength": 4096},
    "outcome": {"type": "string", "enum": ["useful", "dead_end", "corrected"]},
    "evidence": _EVIDENCE,
    "source_nodes": {
        "type": "array",
        "maxItems": 10,
        "items": {"type": "string", "maxLength": 500},
    },
    "query": {"type": "string", "minLength": 1, "maxLength": 2000},
    "limit": {"type": "integer", "minimum": 1, "maximum": 20},
    "note_id": {"type": "string", "pattern": "^wn_[a-f0-9]{32}$"},
    "cursor": {"type": "string", "pattern": "^[0-9]+:[0-9]+$"},
    "expected_revision": {"type": "integer", "minimum": 1},
    "replacement": {
        "type": "object",
        "additionalProperties": False,
        "required": ["lesson", "applicability"],
        "properties": {"lesson": _TEXT, "applicability": _TEXT},
    },
}
_ACTION_FIELDS: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "status": ((), ()),
    "query": (("question",), ("budget_tokens",)),
    "explain": (("node",), ("budget_tokens",)),
    "neighbors": (("node",), ("relation", "budget_tokens")),
    "community": (("community_id",), ("budget_tokens",)),
    "path": (("source", "target"), ("max_hops", "budget_tokens")),
    "impact": (("node",), ("depth", "budget_tokens")),
    "update": (("reason",), ("changed_paths", "mode")),
    "save": (("situation", "lesson", "applicability", "outcome", "evidence"), ("source_nodes",)),
    "search": (("query",), ("limit", "budget_tokens")),
    "read": (("note_id",), ("cursor",)),
    "correct": (("note_id", "expected_revision", "reason", "replacement", "evidence"), ()),
    "reflect": ((), ()),
}


def parameters(tool: str) -> dict[str, Any]:
    actions = KNOWLEDGE_ACTIONS if tool == "project_knowledge" else MEMORY_ACTIONS
    names = {name for action in actions for group in _ACTION_FIELDS[action] for name in group}
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["action"],
        "properties": {
            "action": {"type": "string", "enum": list(actions)},
            **{name: _FIELDS[name] for name in sorted(names)},
        },
    }


def validate_arguments(tool: str, args: dict[str, Any]) -> str:
    if tool not in ("project_knowledge", "work_memory"):
        raise KnowledgeError("ARGUMENT_INVALID", "Unknown knowledge tool.")
    validator = Draft202012Validator(parameters(tool))
    if not isinstance(args, dict) or not validator.is_valid(args):
        raise KnowledgeError(
            "ARGUMENT_INVALID",
            "Arguments do not match the tool schema; identity and paths are runtime-owned.",
        )
    action = args["action"]
    required, optional = _ACTION_FIELDS[action]
    if any(key not in args for key in required) or set(args) - {"action", *required, *optional}:
        raise KnowledgeError(
            "ARGUMENT_INVALID", "Missing or inapplicable arguments for this action."
        )
    return action


def error_response(tool: str, action: str, exc: KnowledgeError) -> dict[str, Any]:
    return {
        "schema_version": "aether.project-knowledge.v1"
        if tool == "project_knowledge"
        else "aether.work-memory.v1",
        "ok": False,
        "action": action,
        "error": {"code": exc.code, "message": exc.message},
        "fallback": "Continue with authorized source-file inspection; no knowledge result was substituted.",
    }


class KnowledgeService:
    def __init__(self, state_root: Path | None = None, cache_root: Path | None = None):
        self.state_root = state_root or product_state_root()
        self.cache_root = (
            cache_root
            or Path(os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache"))) / "aether"
        )

    @property
    def config_path(self) -> Path:
        return self.state_root / "knowledge" / "component.json"

    def configuration(self) -> dict[str, Any]:
        try:
            config = load_json(self.config_path)
        except FileNotFoundError:
            return {}
        if not isinstance(config, dict) or config.get("schema_version") != 1:
            raise KnowledgeError("COMPONENT_UNAVAILABLE", "The component configuration is invalid.")
        return config

    def backend(self) -> GraphifyBackend:
        config = self.configuration()
        value = config.get("python")
        if not config.get("enabled") or not isinstance(value, str) or not Path(value).is_absolute():
            raise KnowledgeError(
                "COMPONENT_UNAVAILABLE",
                "Configure and enable the isolated Graphify component first.",
            )
        return GraphifyBackend(Path(value), timeout=config.get("timeout_seconds", 60))

    def execute(
        self, context: KnowledgeContext, tool: str, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        action = validate_arguments(tool, arguments)
        # Browsing existing notes and metadata must remain possible when Graphify is unavailable.
        backend: GraphifyBackend | None = None
        try:
            backend = self.backend()
        except KnowledgeError:
            if not (tool == "work_memory" and action in ("search", "read")) and not (
                tool == "project_knowledge" and action == "status"
            ):
                raise
        if tool == "project_knowledge":
            result = KnowledgeStore(self.state_root, self.cache_root, backend).execute(
                context, action, arguments
            )
        else:
            result = WorkMemoryStore(self.state_root, backend.python if backend else None).execute(
                context, action, arguments
            )
        return result
