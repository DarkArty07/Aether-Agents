"""Tests for the consult_action module."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from olympus_v2.consult_action import (
    ROLE_LABELS,
    ROLE_DESCRIPTIONS,
    CONSULT_PROMPT_TEMPLATE,
    SIGNING_PROMPT_TEMPLATE,
    VALID_CONSULTANTS,
    _extract_json_from_response,
    _parse_consultation_response,
    _parse_signing_response,
    handle_consult_action,
)


# Helper to create a minimal mock adapter/buffers for handler calls
def _mock_adapter():
    return MagicMock()


def _mock_buffers():
    return {}


# ---------------------------------------------------------------------------
# Unit tests for response parsing
# ---------------------------------------------------------------------------

class TestExtractJsonFromResponse:
    """Test _extract_json_from_response with various input formats."""

    def test_pure_json(self):
        """Should return pure JSON unchanged."""
        raw = json.dumps({"enrichments": [], "contract": {}, "plan_suggestion": ""})
        result = _extract_json_from_response(raw)
        assert json.loads(result) == json.loads(raw)

    def test_json_in_markdown_code_block(self):
        """Should extract JSON from ```json ... ``` blocks."""
        inner = {
            "enrichments": [],
            "contract": {"tasks": [], "refusals": []},
            "plan_suggestion": "Looks good",
        }
        raw = f"Here's my review:\n\n```json\n{json.dumps(inner, indent=2)}\n```\n\nLet me know!"
        result = _extract_json_from_response(raw)
        assert json.loads(result) == inner

    def test_json_in_plain_code_block(self):
        """Should extract JSON from ``` ... ``` blocks (without json tag)."""
        inner = {
            "enrichments": [],
            "contract": {"tasks": [], "refusals": []},
            "plan_suggestion": "",
        }
        raw = f"```\n{json.dumps(inner)}\n```"
        result = _extract_json_from_response(raw)
        assert json.loads(result) == inner

    def test_json_with_preamble_text(self):
        """Should find first { to last } when JSON is embedded in text."""
        inner = {"enrichments": [{"area": "UX", "insight": "test", "severity": "high"}]}
        raw = f"Let me analyze this plan.\n\n{json.dumps(inner)}\n\nThat's my review."
        result = _extract_json_from_response(raw)
        parsed = json.loads(result)
        assert parsed["enrichments"][0]["area"] == "UX"

    def test_nested_braces(self):
        """Should extract JSON with nested braces correctly."""
        inner = {
            "enrichments": [],
            "contract": {
                "tasks": [{"task_id": "t1", "description": "test"}],
                "refusals": [],
            },
            "plan_suggestion": "",
        }
        raw = f"Some preamble\n{json.dumps(inner)}\nSome postamble"
        result = _extract_json_from_response(raw)
        assert json.loads(result) == inner


class TestParseConsultationResponse:
    """Test _parse_consultation_response with various JSON formats."""

    def test_valid_json(self):
        """Should parse well-formed JSON response."""
        raw = json.dumps({
            "enrichments": [
                {"area": "UX", "insight": "Missing error states", "severity": "high"}
            ],
            "contract": {
                "tasks": [
                    {"task_id": "t1", "description": "Design error states"}
                ],
                "refusals": [
                    {"task_id": "t2", "reason": "Backend only"}
                ],
            },
            "plan_suggestion": "Add error handling",
        })
        result = _parse_consultation_response(raw)
        assert result["_parsed"] is True
        assert len(result["enrichments"]) == 1
        assert result["enrichments"][0]["area"] == "UX"
        assert result["contract"]["tasks"][0]["task_id"] == "t1"
        assert len(result["refusals"]) == 1
        assert result["plan_suggestion"] == "Add error handling"

    def test_json_in_markdown_code_block(self):
        """Should extract JSON from ```json ... ``` blocks."""
        inner = {
            "enrichments": [],
            "contract": {"tasks": [], "refusals": []},
            "plan_suggestion": "Looks good",
        }
        raw = f"Here's my review:\n\n```json\n{json.dumps(inner, indent=2)}\n```\n\nLet me know!"
        result = _parse_consultation_response(raw)
        assert result["_parsed"] is True
        assert result["plan_suggestion"] == "Looks good"

    def test_json_in_plain_code_block(self):
        """Should extract JSON from ``` ... ``` blocks (without json tag)."""
        inner = {
            "enrichments": [],
            "contract": {"tasks": [], "refusals": []},
            "plan_suggestion": "",
        }
        raw = f"```\n{json.dumps(inner)}\n```"
        result = _parse_consultation_response(raw)
        assert result["_parsed"] is True

    def test_invalid_json_returns_fallback(self):
        """Should return fallback dict when JSON cannot be parsed."""
        raw = "This is not JSON at all, just plain text."
        result = _parse_consultation_response(raw)
        assert result["_parsed"] is False
        assert "raw_response" in result
        assert result["raw_response"] == raw

    def test_empty_enrichments(self):
        """Should handle empty enrichments list."""
        raw = json.dumps({
            "enrichments": [],
            "contract": {"tasks": [], "refusals": []},
            "plan_suggestion": "",
        })
        result = _parse_consultation_response(raw)
        assert result["_parsed"] is True
        assert result["enrichments"] == []

    def test_missing_optional_keys(self):
        """Should handle missing optional keys gracefully."""
        raw = json.dumps({"enrichments": [{"area": "test", "insight": "test", "severity": "low"}]})
        result = _parse_consultation_response(raw)
        assert result["_parsed"] is True
        assert result["plan_suggestion"] == ""

    def test_json_embedded_in_text(self):
        """Should extract JSON from text with preamble and postamble."""
        inner = {
            "enrichments": [{"area": "UX", "insight": "Missing flow", "severity": "critical"}],
            "contract": {"tasks": [], "refusals": []},
            "plan_suggestion": "Fix the flow",
        }
        raw = f"I've analyzed the plan. Here's my JSON response:\n\n{json.dumps(inner)}\n\nHope this helps!"
        result = _parse_consultation_response(raw)
        assert result["_parsed"] is True
        assert result["enrichments"][0]["severity"] == "critical"


class TestParseSigningResponse:
    """Signing response parsing uses same logic as consultation."""

    def test_valid_signing(self):
        raw = json.dumps({
            "enrichments": [],
            "contract": {
                "tasks": [{"task_id": "t1", "description": "Design login", "deliverables": ["mockup"], "acceptance_criteria": ["AC1"], "complexity": "medium", "dependencies": []}],
                "refusals": [],
            },
            "plan_suggestion": "",
        })
        result = _parse_signing_response(raw)
        assert result["_parsed"] is True
        assert len(result["contract"]["tasks"]) == 1


# ---------------------------------------------------------------------------
# Unit tests for constant configuration
# ---------------------------------------------------------------------------

class TestConsultPrompts:
    """Validate the consult prompt constants."""

    def test_valid_consultants(self):
        assert VALID_CONSULTANTS == {"daedalus", "athena"}

    def test_daedalus_role(self):
        assert ROLE_LABELS["daedalus"] == "designer"

    def test_athena_role(self):
        assert ROLE_LABELS["athena"] == "auditor"

    def test_daedalus_description(self):
        assert "UX/UI" in ROLE_DESCRIPTIONS["daedalus"]

    def test_athena_description(self):
        assert "security auditor" in ROLE_DESCRIPTIONS["athena"]

    def test_signing_prompt_has_placeholders(self):
        assert "{plan}" in SIGNING_PROMPT_TEMPLATE
        assert "{tasks}" in SIGNING_PROMPT_TEMPLATE
        assert "{project_root}" in SIGNING_PROMPT_TEMPLATE

    def test_signing_prompt_has_readonly_restriction(self):
        """Signing prompt must include READ-ONLY restriction."""
        assert "READ-ONLY" in SIGNING_PROMPT_TEMPLATE

    def test_consult_template_has_placeholders(self):
        assert "{role}" in CONSULT_PROMPT_TEMPLATE
        assert "{role_description}" in CONSULT_PROMPT_TEMPLATE
        assert "{project_root}" in CONSULT_PROMPT_TEMPLATE
        assert "{plan}" in CONSULT_PROMPT_TEMPLATE
        assert "{context}" in CONSULT_PROMPT_TEMPLATE

    def test_consult_template_has_readonly_restriction(self):
        """Consult template must include READ-ONLY restriction."""
        assert "READ-ONLY" in CONSULT_PROMPT_TEMPLATE

    def test_consult_template_has_tool_instructions(self):
        """Consult template must instruct tool use for investigation."""
        assert "read" in CONSULT_PROMPT_TEMPLATE.lower()
        assert "grep" in CONSULT_PROMPT_TEMPLATE.lower()
        assert "find" in CONSULT_PROMPT_TEMPLATE.lower()

    def test_consult_template_is_english(self):
        """Consult template should be in English, not Spanish."""
        # No Spanish keywords that were in the old prompts
        assert "Enriquecimientos" not in CONSULT_PROMPT_TEMPLATE
        assert "Revisa" not in CONSULT_PROMPT_TEMPLATE

    def test_signing_template_is_english(self):
        """Signing template should be in English, not Spanish."""
        assert "Confirma" not in SIGNING_PROMPT_TEMPLATE
        assert "asumas" not in SIGNING_PROMPT_TEMPLATE


# ---------------------------------------------------------------------------
# Integration tests for handle_consult_action
# ---------------------------------------------------------------------------

class TestHandleConsultAction:
    """Integration tests for the main handler — focus on validation and error cases."""

    @pytest.mark.asyncio
    async def test_start_validates_empty_plan(self):
        """start action should reject empty plan."""
        result = await handle_consult_action(
            action="start", plan="", agents=["daedalus"],
            adapter=_mock_adapter(), buffers=_mock_buffers(),
        )
        assert "error" in result
        assert "plan" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_start_validates_empty_agents(self):
        """start action should reject empty agents."""
        result = await handle_consult_action(
            action="start", plan="Some plan", agents=[],
            adapter=_mock_adapter(), buffers=_mock_buffers(),
        )
        assert "error" in result
        assert "agents" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_start_validates_invalid_agents(self):
        """start action should reject invalid agent names."""
        result = await handle_consult_action(
            action="start", plan="Plan", agents=["daedalus", "nonexistent"],
            adapter=_mock_adapter(), buffers=_mock_buffers(),
        )
        assert "error" in result
        assert "Invalid" in result["error"]

    @pytest.mark.asyncio
    async def test_run_validates_missing_session_id(self):
        """run action should reject missing session_id."""
        result = await handle_consult_action(
            action="run", session_id="", agent="daedalus",
            adapter=_mock_adapter(), buffers=_mock_buffers(),
        )
        assert "error" in result

    @pytest.mark.asyncio
    async def test_run_validates_missing_agent(self):
        """run action should reject missing agent."""
        result = await handle_consult_action(
            action="run", session_id="abc123", agent="",
            adapter=_mock_adapter(), buffers=_mock_buffers(),
        )
        assert "error" in result

    @pytest.mark.asyncio
    async def test_run_validates_invalid_agent(self):
        """run action should reject invalid agent."""
        result = await handle_consult_action(
            action="run", session_id="abc123", agent="hefesto",
            adapter=_mock_adapter(), buffers=_mock_buffers(),
        )
        assert "error" in result
        assert "Invalid" in result["error"]

    @pytest.mark.asyncio
    async def test_sign_validates_missing_session_id(self):
        """sign action should reject missing session_id."""
        result = await handle_consult_action(
            action="sign", session_id="", agent="daedalus",
            adapter=_mock_adapter(), buffers=_mock_buffers(),
        )
        assert "error" in result

    @pytest.mark.asyncio
    async def test_add_agent_validates_empty_agent(self):
        """add_agent action should reject empty new_agent."""
        result = await handle_consult_action(
            action="add_agent", session_id="abc", new_agent="",
            adapter=_mock_adapter(), buffers=_mock_buffers(),
        )
        assert "error" in result

    @pytest.mark.asyncio
    async def test_status_validates_missing_session_id(self):
        """status action should reject missing session_id."""
        result = await handle_consult_action(
            action="status", session_id="",
            adapter=_mock_adapter(), buffers=_mock_buffers(),
        )
        assert "error" in result

    @pytest.mark.asyncio
    async def test_complete_validates_missing_session_id(self):
        """complete action should reject missing session_id."""
        result = await handle_consult_action(
            action="complete", session_id="",
            adapter=_mock_adapter(), buffers=_mock_buffers(),
        )
        assert "error" in result

    @pytest.mark.asyncio
    async def test_unknown_action(self):
        """Unknown action should return error."""
        result = await handle_consult_action(
            action="foobar",
            adapter=_mock_adapter(), buffers=_mock_buffers(),
        )
        assert "error" in result
        assert "Unknown" in result["error"]

    @pytest.mark.asyncio
    async def test_start_creates_session_in_db(self, tmp_path):
        """start action should actually create a session in SQLite with status 'planning'."""
        import olympus_v2.consulting_db as db_mod
        db_mod._db_instances.clear()

        project_root = str(tmp_path / "test-project")
        result = await handle_consult_action(
            action="start",
            plan="Build a great product",
            agents=["daedalus", "athena"],
            context="New project",
            project_root=project_root,
            adapter=_mock_adapter(),
            buffers=_mock_buffers(),
        )
        assert "session_id" in result
        assert result["status"] == "planning"
        assert result["agents"] == ["daedalus", "athena"]
        assert result["plan_version"] == 1

        # Verify DB was created
        db_path = tmp_path / "test-project" / ".eter" / ".consulting" / "consulting.db"
        assert db_path.exists()

        # Verify session in DB has status 'planning' (not changed to 'consulting')
        db = db_mod._db_instances[project_root]
        session = await db.get_session(result["session_id"])
        assert session["status"] == "planning"

        # Clean up
        for db_instance in db_mod._db_instances.values():
            await db_instance.close()
        db_mod._db_instances.clear()

    @pytest.mark.asyncio
    async def test_status_returns_session(self, tmp_path):
        """status action should return session info after start."""
        import olympus_v2.consulting_db as db_mod
        db_mod._db_instances.clear()

        project_root = str(tmp_path / "test-project")

        # Create session first
        start_result = await handle_consult_action(
            action="start",
            plan="My plan",
            agents=["daedalus"],
            project_root=project_root,
            adapter=_mock_adapter(),
            buffers=_mock_buffers(),
        )
        session_id = start_result["session_id"]

        # Check status
        status_result = await handle_consult_action(
            action="status",
            session_id=session_id,
            project_root=project_root,
            adapter=_mock_adapter(),
            buffers=_mock_buffers(),
        )
        assert "session" in status_result
        assert status_result["session"]["id"] == session_id
        assert status_result["session"]["plan"] == "My plan"

        # Clean up
        for db_instance in db_mod._db_instances.values():
            await db_instance.close()
        db_mod._db_instances.clear()

    @pytest.mark.asyncio
    async def test_add_agent_invalid_agent(self, tmp_path):
        """add_agent should reject an agent not in VALID_CONSULTANTS."""
        result = await handle_consult_action(
            action="add_agent",
            session_id="abc",
            new_agent="nonexistent",
            adapter=_mock_adapter(),
            buffers=_mock_buffers(),
        )
        assert "error" in result
        assert "Invalid" in result["error"]

    @pytest.mark.asyncio
    async def test_add_agent_determines_role(self, tmp_path):
        """add_agent should auto-determine role from ROLE_LABELS when not provided."""
        import olympus_v2.consulting_db as db_mod
        db_mod._db_instances.clear()

        project_root = str(tmp_path / "test-project")

        # Create session with just daedalus
        start_result = await handle_consult_action(
            action="start",
            plan="Test plan",
            agents=["daedalus"],
            project_root=project_root,
            adapter=_mock_adapter(),
            buffers=_mock_buffers(),
        )
        session_id = start_result["session_id"]

        # Add athena without specifying role
        add_result = await handle_consult_action(
            action="add_agent",
            session_id=session_id,
            new_agent="athena",
            reason="Need security review",
            project_root=project_root,
            adapter=_mock_adapter(),
            buffers=_mock_buffers(),
        )
        assert "error" not in add_result
        assert add_result["agent"] == "athena"
        assert add_result["role"] == "auditor"  # Auto-determined from ROLE_LABELS

        # Clean up
        for db_instance in db_mod._db_instances.values():
            await db_instance.close()
        db_mod._db_instances.clear()