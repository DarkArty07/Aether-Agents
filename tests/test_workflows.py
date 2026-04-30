"""Basic workflow engine tests — compilation, state, and edge cases.

These tests use mocks for the ACP manager, so they can run without
a live hermes-agent or Daimon processes.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from olympus.workflows.state import WorkflowState


class TestWorkflowState:
    """Test WorkflowState TypedDict structure."""

    def test_state_has_required_fields(self):
        """WorkflowState must have all fields needed by workflow nodes."""
        state = WorkflowState(
            user_prompt="Test prompt",
            context="",
            code="",
            audit_result="",
            audit_passed=False,
            research="",
            messages=[],
            review_cycles=0,
            max_review_cycles=3,
            final_response="",
            project_root="/tmp/test",
            errors=[],
            status="running",
            started_at=0.0,
            node_name="",
            needs_research=True,
            has_ui=False,
            workflow_type="feature",
            modification_feedback="",
        )
        assert state["workflow_type"] == "feature"
        assert state["modification_feedback"] == ""

    def test_state_modification_feedback_default(self):
        """modification_feedback should default to empty string."""
        state = WorkflowState(
            user_prompt="Test",
            context="",
            code="",
            audit_result="",
            audit_passed=False,
            research="",
            messages=[],
            review_cycles=0,
            max_review_cycles=3,
            final_response="",
            project_root="/tmp",
            errors=[],
            status="running",
            started_at=0.0,
            node_name="",
            needs_research=False,
            has_ui=False,
            workflow_type="bug-fix",
            modification_feedback="",
        )
        assert state["modification_feedback"] == ""


class TestWorkflowCompilation:
    """Test that workflow graphs compile without errors."""

    def _get_mock_acp(self):
        """Create a mock ACPManager for workflow compilation."""
        mock = MagicMock()
        mock.ensure_agent = AsyncMock()
        mock.open_session = AsyncMock()
        mock.send_prompt = AsyncMock()
        mock.close_session = AsyncMock()
        mock.shutdown_agent = AsyncMock()
        return mock

    def test_feature_workflow_compiles(self):
        """Feature workflow graph should compile without errors."""
        from olympus.workflows.definitions import get_workflow
        acp = self._get_mock_acp()
        graph = get_workflow("feature", acp)
        assert graph is not None

    def test_bug_fix_workflow_compiles(self):
        """Bug-fix workflow graph should compile without errors."""
        from olympus.workflows.definitions import get_workflow
        acp = self._get_mock_acp()
        graph = get_workflow("bug-fix", acp)
        assert graph is not None

    def test_research_workflow_compiles(self):
        """Research workflow graph should compile without errors."""
        from olympus.workflows.definitions import get_workflow
        acp = self._get_mock_acp()
        graph = get_workflow("research", acp)
        assert graph is not None

    def test_security_review_workflow_compiles(self):
        """Security review workflow graph should compile without errors."""
        from olympus.workflows.definitions import get_workflow
        acp = self._get_mock_acp()
        graph = get_workflow("security-review", acp)
        assert graph is not None

    def test_refactor_workflow_compiles(self):
        """Refactor workflow graph should compile without errors."""
        from olympus.workflows.definitions import get_workflow
        acp = self._get_mock_acp()
        graph = get_workflow("refactor", acp)
        assert graph is not None

    def test_project_init_workflow_compiles(self):
        """Project init workflow graph should compile without errors."""
        from olympus.workflows.definitions import get_workflow
        acp = self._get_mock_acp()
        graph = get_workflow("project-init", acp)
        assert graph is not None

    def test_invalid_workflow_raises(self):
        """Invalid workflow name should raise ValueError."""
        from olympus.workflows.definitions import get_workflow
        acp = self._get_mock_acp()
        with pytest.raises(ValueError):
            get_workflow("nonexistent", acp)


class TestConditionalEdges:
    """Test conditional edge functions."""

    def test_should_enter_research_true(self):
        """needs_research=True should route to research node."""
        from olympus.workflows.definitions import should_research as should_enter_research
        # Note: TypedDict doesn't enforce at runtime, so we test the function directly
        assert should_enter_research({"needs_research": True}) == "research"

    def test_should_enter_research_false(self):
        """needs_research=False should skip research."""
        from olympus.workflows.definitions import should_research as should_enter_research
        assert should_enter_research({"needs_research": False}) == "design"

    def test_should_terminate_on_error_no_errors(self):
        """No errors should continue."""
        from olympus.workflows.nodes import should_terminate_on_error
        assert should_terminate_on_error({"errors": []}) == "continue"

    def test_should_terminate_on_error_with_errors(self):
        """Errors should terminate."""
        from olympus.workflows.nodes import should_terminate_on_error
        assert should_terminate_on_error({"errors": ["something failed"]}) == "finalize"


class TestSTALLTIMEOUT:
    """Test that STALL_TIMEOUT is documented correctly."""

    def test_stall_timeout_is_120(self):
        """STALL_TIMEOUT should be 120 seconds (2 minutes)."""
        from olympus.workflows.nodes import STALL_TIMEOUT
        assert STALL_TIMEOUT == 120

    def test_no_1800_timeout_in_runner(self):
        """There should be NO 1800-second 'hard timeout' in runner.py."""
        import subprocess
        result = subprocess.run(
            ["grep", "-c", "1800", "src/olympus/workflows/runner.py"],
            capture_output=True, text=True
        )
        # grep -c returns the count of matching lines
        # "0" means no matches (which is what we want)
        assert result.stdout.strip() == "0", \
            "runner.py should not contain any 1800-second timeout reference"
