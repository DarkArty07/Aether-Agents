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
    "stats",
    "god_nodes",
    "list_prs",
    "pr_impact",
    "triage_prs",
    "visualize",
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
    "idempotency_key": {
        "type": "string",
        "minLength": 8,
        "maxLength": 160,
        "pattern": "^[A-Za-z0-9][A-Za-z0-9._:-]{7,159}$",
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
    "limit": {"type": "integer", "minimum": 1, "maximum": 50},
    "note_id": {"type": "string", "pattern": "^wn_[a-f0-9]{32}$"},
    "cursor": {"type": "string", "pattern": "^[0-9]+:[0-9]+$"},
    "expected_revision": {"type": "integer", "minimum": 1},
    "replacement": {
        "type": "object",
        "additionalProperties": False,
        "required": ["lesson", "applicability"],
        "properties": {"lesson": _TEXT, "applicability": _TEXT},
    },
    "traversal": {"type": "string", "enum": ["bfs", "dfs"]},
    "context_filter": {
        "type": "array",
        "minItems": 1,
        "maxItems": 20,
        "items": {"type": "string", "minLength": 1, "maxLength": 80},
    },
    "relations": {
        "type": "array",
        "minItems": 1,
        "maxItems": 20,
        "items": {"type": "string", "minLength": 1, "maxLength": 80},
    },
    "undirected": {"type": "boolean"},
    "top_n": {"type": "integer", "minimum": 1, "maximum": 50},
    "exclude_hubs_percentile": {"type": "number", "minimum": 0, "maximum": 100},
    "base": {"type": "string", "minLength": 1, "maxLength": 255},
    "pr_number": {"type": "integer", "minimum": 1},
    "format": {"type": "string", "enum": ["graph", "tree"]},
    "detail": {"type": "string", "enum": ["auto", "full"]},
}
_ACTION_FIELDS: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "status": ((), ()),
    "query": (("question",), ("budget_tokens", "traversal", "depth", "context_filter")),
    "explain": (("node",), ("budget_tokens",)),
    "neighbors": (("node",), ("relation", "budget_tokens")),
    "community": (("community_id",), ("budget_tokens",)),
    "path": (("source", "target"), ("max_hops", "budget_tokens", "undirected")),
    "impact": (("node",), ("depth", "budget_tokens", "relations")),
    "update": (("reason",), ("changed_paths", "mode")),
    "stats": ((), ()),
    "god_nodes": ((), ("top_n", "exclude_hubs_percentile", "budget_tokens")),
    "list_prs": ((), ("base", "limit", "budget_tokens")),
    "pr_impact": (("pr_number",), ("budget_tokens",)),
    "triage_prs": ((), ("base", "limit", "budget_tokens")),
    "visualize": ((), ("format", "detail")),
    "save": (
        ("idempotency_key", "situation", "lesson", "applicability", "outcome", "evidence"),
        ("source_nodes",),
    ),
    "search": (("query",), ("limit", "budget_tokens")),
    "read": (("note_id",), ("cursor",)),
    "correct": (("note_id", "expected_revision", "reason", "replacement", "evidence"), ()),
    "reflect": ((), ()),
}

_FIELD_DESCRIPTIONS: dict[str, str] = {
    "question": "Natural language technical question about the project codebase.",
    "node": "Symbol or entity identifier in the project graph.",
    "relation": "Relationship type filter for neighboring nodes.",
    "source": "Starting symbol or entity identifier for path discovery.",
    "target": "Destination symbol or entity identifier for path discovery.",
    "community_id": "Snapshot-local community identifier discovered via explain.",
    "depth": "Maximum traversal depth (1..6).",
    "max_hops": "Maximum path length between source and target.",
    "budget_tokens": "Token estimate budget for response context.",
    "reason": "Explanation for the requested operation.",
    "mode": "Update strategy for graph re-indexing ('configured' or 'structural').",
    "changed_paths": "Optional hint list of modified project-relative paths.",
    "idempotency_key": "Caller-provided unique token for retry and replay deduplication.",
    "situation": "Context and trigger condition under which the experience occurred.",
    "lesson": "Core takeaway, recommendation, or procedure learned.",
    "applicability": "Boundary conditions and scope where this lesson applies.",
    "outcome": "Observed outcome classification ('useful', 'dead_end', or 'corrected').",
    "evidence": "Verification references and observed results backing the note.",
    "source_nodes": "Optional list of project graph node identifiers associated with this experience.",
    "query": "Search query string across role experience notes.",
    "limit": "Maximum number of items to return.",
    "note_id": "Unique identifier of the note.",
    "cursor": "Opaque continuation cursor for paginated note reads.",
    "expected_revision": "Expected note revision number for optimistic concurrency.",
    "replacement": "Updated lesson and applicability replacing the prior revision.",
    "traversal": "Graph traversal strategy ('bfs' or 'dfs', default 'bfs').",
    "context_filter": "Filter context by relation types or node labels (up to 20 nonempty strings, max 80 chars each).",
    "relations": "Relationship types to follow during impact analysis (up to 20 nonempty strings, max 80 chars each).",
    "undirected": "Whether to treat graph edges as undirected during path search (default false).",
    "top_n": "Number of top central nodes to return (1..50, default 10).",
    "exclude_hubs_percentile": "Percentile threshold to exclude high-degree hub nodes (0..100).",
    "base": "Base branch name to compare against for pull requests (1..255 characters).",
    "pr_number": "Positive integer pull request number.",
    "format": "Visualization export format ('graph' or 'tree', default 'graph').",
    "detail": "Visualization detail level for graph format ('auto' or 'full', default 'auto').",
}


def parameters(tool: str) -> dict[str, Any]:
    actions = KNOWLEDGE_ACTIONS if tool == "project_knowledge" else MEMORY_ACTIONS
    names = {name for action in actions for group in _ACTION_FIELDS[action] for name in group}
    props: dict[str, Any] = {
        "action": {
            "type": "string",
            "enum": list(actions),
            "description": f"The {tool} action to perform: {', '.join(actions)}.",
        }
    }
    for name in sorted(names):
        accepted = [
            act
            for act in actions
            if name in _ACTION_FIELDS[act][0] or name in _ACTION_FIELDS[act][1]
        ]
        if len(accepted) == 1:
            accepted_str = f"Accepted by action: {accepted[0]}."
        else:
            accepted_str = f"Accepted by actions: {', '.join(accepted)}."
        field_schema = dict(_FIELDS[name])
        desc = _FIELD_DESCRIPTIONS.get(name, "")
        field_schema["description"] = f"{desc} {accepted_str}".strip()
        props[name] = field_schema

    one_of = []
    for action in actions:
        req, opt = _ACTION_FIELDS[action]
        branch_props: dict[str, Any] = {
            "action": {
                "const": action,
                "description": f"Execute the '{action}' action.",
            },
            **{name: dict(props[name]) for name in sorted((*req, *opt))},
        }
        if action == "search" and "limit" in branch_props:
            branch_props["limit"] = {**branch_props["limit"], "maximum": 20}
        branch_schema: dict[str, Any] = {
            "type": "object",
            "properties": branch_props,
            "required": ["action", *sorted(req)],
            "additionalProperties": False,
        }
        if action == "visualize":
            branch_schema["dependentSchemas"] = {
                "detail": {
                    "properties": {
                        "format": {"enum": ["graph"]},
                    }
                }
            }
        one_of.append(branch_schema)

    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["action"],
        "properties": props,
        "oneOf": one_of,
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
    if action == "visualize" and args.get("format") == "tree" and "detail" in args:
        raise KnowledgeError(
            "ARGUMENT_INVALID", "The detail parameter is only valid for graph visualization."
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
