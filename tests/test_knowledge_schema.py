"""Canonical parameter schema and validation tests for knowledge and memory tools."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from aether_agents.knowledge.common import KnowledgeError
from aether_agents.knowledge.service import (
    _ACTION_FIELDS,
    KNOWLEDGE_ACTIONS,
    MEMORY_ACTIONS,
    parameters,
    validate_arguments,
)
from aether_agents.lifecycle import HERMES_BASELINE


def _get_schema_sanitizer():
    try:
        from tools.schema_sanitizer import sanitize_tool_schemas  # type: ignore[import-not-found]

        return sanitize_tool_schemas
    except ImportError:
        checkout = os.environ.get("AETHER_EXACT_HERMES_CHECKOUT")
        if checkout:
            base_path = Path(checkout)
        else:
            cache_home = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
            base_path = cache_home / "aether-agents" / "hermes" / HERMES_BASELINE.tag
        if str(base_path) not in sys.path:
            sys.path.insert(0, str(base_path))
        from tools.schema_sanitizer import sanitize_tool_schemas  # type: ignore[import-not-found]

        return sanitize_tool_schemas


IDENTITY_FIELDS = (
    "role",
    "project_id",
    "project_path",
    "graph_path",
    "memory_dir",
    "executable",
    "env",
    "python",
)


@pytest.mark.parametrize("tool", ["project_knowledge", "work_memory"])
def test_parameter_schema_structure(tool: str) -> None:
    schema = parameters(tool)
    actions = KNOWLEDGE_ACTIONS if tool == "project_knowledge" else MEMORY_ACTIONS

    assert schema["type"] == "object"
    assert schema["additionalProperties"] is False
    assert schema["required"] == ["action"]

    # All identity fields must be rejected at schema root
    for field in IDENTITY_FIELDS:
        assert field not in schema["properties"]

    # Action property must have enum of supported actions
    action_prop = schema["properties"]["action"]
    assert action_prop["type"] == "string"
    assert set(action_prop["enum"]) == set(actions)
    assert isinstance(action_prop.get("description"), str) and action_prop["description"]

    # Every action-specific field must have a description naming the actions that accept it
    all_names = {name for act in actions for grp in _ACTION_FIELDS[act] for name in grp}
    for name in all_names:
        assert name in schema["properties"]
        desc = schema["properties"][name].get("description")
        assert isinstance(desc, str) and desc
        assert "accepted by" in desc.lower()
        accepted_actions = [
            act
            for act in actions
            if name in _ACTION_FIELDS[act][0] or name in _ACTION_FIELDS[act][1]
        ]
        for act in accepted_actions:
            assert act in desc

    # Must contain action-discriminated branches matching _ACTION_FIELDS
    assert "oneOf" in schema
    branches = schema["oneOf"]
    assert len(branches) == len(actions)

    branches_by_action: dict[str, dict[str, Any]] = {}
    for branch in branches:
        assert branch["type"] == "object"
        assert branch["additionalProperties"] is False
        act_val = branch["properties"]["action"]["const"]
        assert act_val in actions
        branches_by_action[act_val] = branch

    for act in actions:
        assert act in branches_by_action
        branch = branches_by_action[act]
        req_fields, opt_fields = _ACTION_FIELDS[act]
        assert set(branch["required"]) == {"action", *req_fields}
        assert set(branch["properties"].keys()) == {"action", *req_fields, *opt_fields}


PARITY_MATRIX: list[tuple[str, dict[str, Any], bool, str]] = [
    # project_knowledge - status
    ("project_knowledge", {"action": "status"}, True, "valid status"),
    (
        "project_knowledge",
        {"action": "status", "budget_tokens": 500},
        False,
        "status + budget_tokens extra",
    ),
    ("project_knowledge", {"action": "status", "role": "admin"}, False, "status + role injection"),
    (
        "project_knowledge",
        {"action": "status", "project_id": "p_123"},
        False,
        "status + project_id injection",
    ),
    (
        "project_knowledge",
        {"action": "status", "project_path": "/tmp"},
        False,
        "status + project_path injection",
    ),
    (
        "project_knowledge",
        {"action": "status", "graph_path": "/tmp"},
        False,
        "status + graph_path injection",
    ),
    (
        "project_knowledge",
        {"action": "status", "memory_dir": "/tmp"},
        False,
        "status + memory_dir injection",
    ),
    (
        "project_knowledge",
        {"action": "status", "python": "/usr/bin/python"},
        False,
        "status + python injection",
    ),
    ("project_knowledge", {"action": "status", "env": {"A": "B"}}, False, "status + env injection"),
    (
        "project_knowledge",
        {"action": "status", "executable": "bin"},
        False,
        "status + executable injection",
    ),
    # project_knowledge - query
    ("project_knowledge", {"action": "query"}, False, "query missing question"),
    ("project_knowledge", {"action": "query", "question": "where is foo?"}, True, "valid query"),
    (
        "project_knowledge",
        {"action": "query", "question": "where is foo?", "budget_tokens": 500},
        True,
        "query with budget",
    ),
    (
        "project_knowledge",
        {"action": "query", "question": "where is foo?", "budget_tokens": 50},
        False,
        "query budget too small",
    ),
    (
        "project_knowledge",
        {"action": "query", "question": "where is foo?", "budget_tokens": 10000},
        False,
        "query budget too large",
    ),
    (
        "project_knowledge",
        {"action": "query", "question": "where is foo?", "depth": 2},
        False,
        "query with inapplicable depth",
    ),
    # project_knowledge - explain
    ("project_knowledge", {"action": "explain"}, False, "explain missing node"),
    ("project_knowledge", {"action": "explain", "node": "my_symbol"}, True, "valid explain"),
    (
        "project_knowledge",
        {"action": "explain", "node": "my_symbol", "budget_tokens": 1000},
        True,
        "explain with budget",
    ),
    (
        "project_knowledge",
        {"action": "explain", "node": "my_symbol", "relation": "calls"},
        False,
        "explain with relation",
    ),
    # project_knowledge - neighbors
    ("project_knowledge", {"action": "neighbors"}, False, "neighbors missing node"),
    ("project_knowledge", {"action": "neighbors", "node": "my_symbol"}, True, "valid neighbors"),
    (
        "project_knowledge",
        {"action": "neighbors", "node": "my_symbol", "relation": "calls"},
        True,
        "neighbors with relation",
    ),
    (
        "project_knowledge",
        {"action": "neighbors", "node": "my_symbol", "budget_tokens": 1000},
        True,
        "neighbors with budget",
    ),
    (
        "project_knowledge",
        {"action": "neighbors", "node": "my_symbol", "max_hops": 3},
        False,
        "neighbors with max_hops",
    ),
    # project_knowledge - community
    ("project_knowledge", {"action": "community"}, False, "community missing community_id"),
    ("project_knowledge", {"action": "community", "community_id": 0}, True, "valid community 0"),
    ("project_knowledge", {"action": "community", "community_id": 42}, True, "valid community 42"),
    (
        "project_knowledge",
        {"action": "community", "community_id": -1},
        False,
        "community negative id",
    ),
    (
        "project_knowledge",
        {"action": "community", "community_id": 1, "budget_tokens": 2000},
        True,
        "community with budget",
    ),
    (
        "project_knowledge",
        {"action": "community", "community_id": 1, "node": "sym"},
        False,
        "community with node",
    ),
    # project_knowledge - path
    ("project_knowledge", {"action": "path"}, False, "path missing source and target"),
    ("project_knowledge", {"action": "path", "source": "A"}, False, "path missing target"),
    ("project_knowledge", {"action": "path", "target": "B"}, False, "path missing source"),
    ("project_knowledge", {"action": "path", "source": "A", "target": "B"}, True, "valid path"),
    (
        "project_knowledge",
        {"action": "path", "source": "A", "target": "B", "max_hops": 5},
        True,
        "path with max_hops",
    ),
    (
        "project_knowledge",
        {"action": "path", "source": "A", "target": "B", "max_hops": 25},
        False,
        "path max_hops too high",
    ),
    (
        "project_knowledge",
        {"action": "path", "source": "A", "target": "B", "budget_tokens": 1500},
        True,
        "path with budget",
    ),
    (
        "project_knowledge",
        {"action": "path", "source": "A", "target": "B", "depth": 2},
        False,
        "path with depth",
    ),
    # project_knowledge - impact
    ("project_knowledge", {"action": "impact"}, False, "impact missing node"),
    ("project_knowledge", {"action": "impact", "node": "sym"}, True, "valid impact"),
    (
        "project_knowledge",
        {"action": "impact", "node": "sym", "depth": 3},
        True,
        "impact with depth",
    ),
    (
        "project_knowledge",
        {"action": "impact", "node": "sym", "depth": 8},
        False,
        "impact depth too high",
    ),
    (
        "project_knowledge",
        {"action": "impact", "node": "sym", "budget_tokens": 1000},
        True,
        "impact with budget",
    ),
    (
        "project_knowledge",
        {"action": "impact", "node": "sym", "source": "A"},
        False,
        "impact with source",
    ),
    # project_knowledge - update
    ("project_knowledge", {"action": "update"}, False, "update missing reason"),
    ("project_knowledge", {"action": "update", "reason": "code changed"}, True, "valid update"),
    (
        "project_knowledge",
        {"action": "update", "reason": "code changed", "mode": "structural"},
        True,
        "update mode structural",
    ),
    (
        "project_knowledge",
        {"action": "update", "reason": "code changed", "mode": "configured"},
        True,
        "update mode configured",
    ),
    (
        "project_knowledge",
        {"action": "update", "reason": "code changed", "mode": "invalid_mode"},
        False,
        "update invalid mode",
    ),
    (
        "project_knowledge",
        {"action": "update", "reason": "code changed", "changed_paths": ["src/a.py"]},
        True,
        "update changed paths",
    ),
    (
        "project_knowledge",
        {"action": "update", "reason": "code changed", "budget_tokens": 500},
        False,
        "update with budget_tokens",
    ),
    # work_memory - reflect
    ("work_memory", {"action": "reflect"}, True, "valid reflect"),
    ("work_memory", {"action": "reflect", "query": "something"}, False, "reflect with query extra"),
    ("work_memory", {"action": "reflect", "role": "morfeo"}, False, "reflect with role injection"),
    (
        "work_memory",
        {"action": "reflect", "project_id": "p_123"},
        False,
        "reflect with project_id injection",
    ),
    # work_memory - search
    ("work_memory", {"action": "search"}, False, "search missing query"),
    ("work_memory", {"action": "search", "query": "find this"}, True, "valid search"),
    (
        "work_memory",
        {"action": "search", "query": "find this", "limit": 10},
        True,
        "search with limit",
    ),
    (
        "work_memory",
        {"action": "search", "query": "find this", "limit": 50},
        False,
        "search limit too high",
    ),
    (
        "work_memory",
        {"action": "search", "query": "find this", "budget_tokens": 1000},
        True,
        "search with budget",
    ),
    (
        "work_memory",
        {"action": "search", "query": "find this", "cursor": "1:2"},
        False,
        "search with cursor extra",
    ),
    # work_memory - read
    ("work_memory", {"action": "read"}, False, "read missing note_id"),
    ("work_memory", {"action": "read", "note_id": "invalid_id"}, False, "read malformed note_id"),
    ("work_memory", {"action": "read", "note_id": "wn_" + "a" * 32}, True, "valid read"),
    (
        "work_memory",
        {"action": "read", "note_id": "wn_" + "a" * 32, "cursor": "1:2"},
        True,
        "read with cursor",
    ),
    (
        "work_memory",
        {"action": "read", "note_id": "wn_" + "a" * 32, "cursor": "bad_cursor"},
        False,
        "read bad cursor",
    ),
    (
        "work_memory",
        {"action": "read", "note_id": "wn_" + "a" * 32, "query": "foo"},
        False,
        "read with query extra",
    ),
    # work_memory - save
    ("work_memory", {"action": "save"}, False, "save missing required fields"),
    (
        "work_memory",
        {
            "action": "save",
            "situation": "sit",
            "lesson": "les",
            "applicability": "app",
            "outcome": "useful",
            "evidence": [],
        },
        False,
        "save missing idempotency_key",
    ),
    (
        "work_memory",
        {
            "action": "save",
            "idempotency_key": "short",
            "situation": "sit",
            "lesson": "les",
            "applicability": "app",
            "outcome": "useful",
            "evidence": [],
        },
        False,
        "save idempotency_key too short (<8)",
    ),
    (
        "work_memory",
        {
            "action": "save",
            "idempotency_key": "valid-key-12345",
            "situation": "sit",
            "lesson": "les",
            "applicability": "app",
            "outcome": "useful",
            "evidence": [],
        },
        True,
        "valid save minimal",
    ),
    (
        "work_memory",
        {
            "action": "save",
            "idempotency_key": "valid-key-12345",
            "situation": "sit",
            "lesson": "les",
            "applicability": "app",
            "outcome": "useful",
            "evidence": [{"path": "a/b.py", "result": "passed"}],
            "source_nodes": ["node_1"],
        },
        True,
        "valid save with source_nodes and evidence",
    ),
    (
        "work_memory",
        {
            "action": "save",
            "idempotency_key": "valid-key-12345",
            "situation": "sit",
            "lesson": "les",
            "applicability": "app",
            "outcome": "unknown_outcome",
            "evidence": [],
        },
        False,
        "save invalid outcome enum",
    ),
    (
        "work_memory",
        {
            "action": "save",
            "idempotency_key": "valid-key-12345",
            "situation": "sit",
            "lesson": "les",
            "applicability": "app",
            "outcome": "useful",
            "evidence": [],
            "budget_tokens": 500,
        },
        False,
        "save with inapplicable budget_tokens",
    ),
    # work_memory - correct
    ("work_memory", {"action": "correct"}, False, "correct missing required fields"),
    (
        "work_memory",
        {
            "action": "correct",
            "note_id": "wn_" + "a" * 32,
            "expected_revision": 1,
            "reason": "updating lesson",
            "replacement": {"lesson": "new lesson", "applicability": "new app"},
            "evidence": [],
        },
        True,
        "valid correct",
    ),
    (
        "work_memory",
        {
            "action": "correct",
            "note_id": "wn_" + "a" * 32,
            "expected_revision": 0,
            "reason": "updating lesson",
            "replacement": {"lesson": "new lesson", "applicability": "new app"},
            "evidence": [],
        },
        False,
        "correct expected_revision < 1",
    ),
    (
        "work_memory",
        {
            "action": "correct",
            "note_id": "wn_" + "a" * 32,
            "expected_revision": 1,
            "reason": "updating lesson",
            "replacement": {"lesson": "new lesson", "applicability": "new app"},
            "evidence": [],
            "cursor": "1:2",
        },
        False,
        "correct with inapplicable cursor",
    ),
    # Unknown action
    ("project_knowledge", {"action": "destroy"}, False, "unknown action project_knowledge"),
    ("work_memory", {"action": "destroy"}, False, "unknown action work_memory"),
]


@pytest.mark.parametrize("tool,payload,expected,case_name", PARITY_MATRIX)
def test_schema_validation_parity_matrix(
    tool: str, payload: dict[str, Any], expected: bool, case_name: str
) -> None:
    schema = parameters(tool)
    validator = Draft202012Validator(schema)
    val_is_valid = validator.is_valid(payload)

    try:
        returned_action = validate_arguments(tool, payload)
        fn_is_valid = True
    except KnowledgeError as exc:
        assert exc.code == "ARGUMENT_INVALID"
        fn_is_valid = False
        returned_action = ""

    assert val_is_valid == expected, (
        f"Draft202012Validator disagreement on {tool} ({case_name}): "
        f"got {val_is_valid}, expected {expected}"
    )
    assert fn_is_valid == expected, (
        f"validate_arguments disagreement on {tool} ({case_name}): "
        f"got {fn_is_valid}, expected {expected}"
    )
    if expected:
        assert returned_action == payload["action"]


def test_schema_sanitizer_preserves_descriptions_and_strips_top_level_combinators() -> None:
    sanitizer = _get_schema_sanitizer()

    openai_tools = [
        {
            "type": "function",
            "function": {
                "name": "project_knowledge",
                "description": "Consult project graph.",
                "parameters": parameters("project_knowledge"),
            },
        },
        {
            "type": "function",
            "function": {
                "name": "work_memory",
                "description": "Maintain role memories.",
                "parameters": parameters("work_memory"),
            },
        },
    ]

    sanitized = sanitizer(openai_tools)
    assert len(sanitized) == 2

    for tool_entry in sanitized:
        tool_params = tool_entry["function"]["parameters"]
        tool_name = tool_entry["function"]["name"]
        actions = KNOWLEDGE_ACTIONS if tool_name == "project_knowledge" else MEMORY_ACTIONS

        # Top-level combinators must be stripped by sanitizer
        assert "oneOf" not in tool_params
        assert "allOf" not in tool_params
        assert "anyOf" not in tool_params

        # Root properties and object type preserved
        assert tool_params["type"] == "object"
        assert "properties" in tool_params

        # Property descriptions must remain usable and name accepted actions
        all_names = {name for act in actions for grp in _ACTION_FIELDS[act] for name in grp}
        for name in all_names:
            desc = tool_params["properties"][name].get("description")
            assert isinstance(desc, str) and desc
            assert "accepted by" in desc.lower()


def test_runtime_dispatch_rejects_invalid_after_sanitization() -> None:
    # Handler remains the authoritative runtime frontier even if model receives sanitized schema
    with pytest.raises(KnowledgeError) as exc1:
        validate_arguments("project_knowledge", {"action": "status", "budget_tokens": 500})
    assert exc1.value.code == "ARGUMENT_INVALID"

    with pytest.raises(KnowledgeError) as exc2:
        validate_arguments("work_memory", {"action": "reflect", "query": "fail"})
    assert exc2.value.code == "ARGUMENT_INVALID"

    with pytest.raises(KnowledgeError) as exc3:
        validate_arguments("project_knowledge", {"action": "status", "role": "admin"})
    assert exc3.value.code == "ARGUMENT_INVALID"

    with pytest.raises(KnowledgeError) as exc4:
        validate_arguments(
            "work_memory",
            {
                "action": "save",
                "situation": "s",
                "lesson": "l",
                "applicability": "a",
                "outcome": "useful",
                "evidence": [],
            },
        )
    assert exc4.value.code == "ARGUMENT_INVALID"
