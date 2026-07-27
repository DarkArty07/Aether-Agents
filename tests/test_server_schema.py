"""Validate Olympus v3 MCP tool schemas against their registered tool objects."""

import asyncio

import pytest

from olympus_v3 import server

TALK_TO_ACTIONS = {"open", "message", "poll", "close", "cancel", "delegate", "steer"}
TALK_TO_PROPERTIES = {
    "agent",
    "action",
    "session_id",
    "prompt",
    "poll_interval",
    "timeout",
    "project_root",
    "directive",
    "priority",
}


def _registered_tools():
    """Return the MCP Tool objects exposed by the v3 server registration."""
    return {tool.name: tool for tool in asyncio.run(server.list_tools())}


def test_v3_registers_expected_tools():
    """The registered schema exposes the current v3 MCP tool surface."""
    tools = _registered_tools()

    assert set(tools) == {
        "talk_to",
        "discover",
        "aether_status",
        "aether_update",
        "aether_curate",
        "harmonia",
    }


def test_talk_to_schema_matches_v3_actions_and_properties():
    """talk_to's public schema includes every current action and its inputs."""
    schema = _registered_tools()["talk_to"].inputSchema

    assert set(schema["properties"]["action"]["enum"]) == TALK_TO_ACTIONS
    assert set(schema["properties"]) == TALK_TO_PROPERTIES
    assert schema["required"] == ["action"]
    assert schema["properties"]["timeout"]["default"] == 300
    assert schema["properties"]["poll_interval"]["default"] == 15


def test_aether_tool_schemas_expose_current_actions_and_required_roots():
    """Continuity tools keep their registered actions and project-root contract."""
    tools = _registered_tools()

    assert tools["discover"].inputSchema == {"type": "object", "properties": {}, "required": []}
    assert tools["aether_status"].inputSchema["required"] == ["project_root"]
    assert set(tools["aether_status"].inputSchema["properties"]["detail"]["enum"]) == {"summary", "full"}
    assert tools["aether_update"].inputSchema["required"] == ["action", "project_root"]
    assert set(tools["aether_update"].inputSchema["properties"]["action"]["enum"]) == {
        "set_phase",
        "set_task",
        "add_blocker",
        "remove_blocker",
        "add_decision",
        "add_issue",
        "resolve_issue",
    }
    assert tools["aether_curate"].inputSchema["required"] == ["project_root"]
    assert set(tools["aether_curate"].inputSchema["properties"]["focus"]["enum"]) == {
        "full",
        "recent",
        "decisions",
    }


def test_harmonia_schema_is_flat_strict_and_action_conditional():
    schema = _registered_tools()["harmonia"].inputSchema

    assert schema["additionalProperties"] is False
    assert schema["required"] == ["action", "project_root"]
    assert schema["properties"]["action"]["enum"] == ["start", "status", "stop"]
    assert set(schema["properties"]) == {
        "action", "project_root", "request_id", "contract", "plan_revision",
        "snapshot_digest", "run_id", "reason",
    }
    assert schema["allOf"] == [
        {
            "if": {"properties": {"action": {"const": "start"}}},
            "then": {"required": ["request_id", "contract", "plan_revision", "snapshot_digest"]},
        },
        {
            "if": {"properties": {"action": {"enum": ["status", "stop"]}}},
            "then": {"required": ["run_id"]},
        },
    ]
    contract = schema["properties"]["contract"]
    assert "tasks" not in contract["required"]
    assert "worker" not in contract["required"]
    assert "worker_permissions" not in contract["required"]
    assert {tuple(branch["required"]) for branch in contract["oneOf"]} == {
        ("worker", "worker_permissions"),
        ("tasks",),
    }
    assert contract["properties"]["tasks"]["minItems"] == 2
    assert contract["properties"]["tasks"]["maxItems"] == 2


@pytest.mark.parametrize("action", sorted(TALK_TO_ACTIONS))
def test_every_talk_to_schema_action_reaches_a_handler_branch(monkeypatch, action):
    """Each advertised talk_to action is handled rather than rejected as unknown."""
    monkeypatch.setattr(server, "_manager", object())

    response = asyncio.run(server._handle_talk_to({"action": action}))

    assert "Unknown action" not in response[0].text
