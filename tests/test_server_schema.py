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


@pytest.mark.parametrize("action", sorted(TALK_TO_ACTIONS))
def test_every_talk_to_schema_action_reaches_a_handler_branch(monkeypatch, action):
    """Each advertised talk_to action is handled rather than rejected as unknown."""
    monkeypatch.setattr(server, "_manager", object())

    response = asyncio.run(server._handle_talk_to({"action": action}))

    assert "Unknown action" not in response[0].text
