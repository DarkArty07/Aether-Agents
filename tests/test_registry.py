import time
import pytest
from olympus_v3.registry import SessionState, SessionStatus, AgentState, AgentStatus, OlympusRegistry
from olympus_v3.config import DaimonProfile
from pathlib import Path


def test_session_state_initial():
    s = SessionState(session_id="test", agent_name="hefesto")
    assert s.status == SessionStatus.ACTIVE
    assert s.thoughts == []
    assert s.messages == []
    assert s.tool_calls == []
    assert s.final_response is None
    assert s.stop_reason is None


def test_session_state_update_thought():
    s = SessionState(session_id="test", agent_name="hefesto")
    s.update_from_thought("thinking...")
    assert len(s.thoughts) == 1
    assert s.thoughts[0] == "thinking..."


def test_session_state_update_message():
    s = SessionState(session_id="test", agent_name="hefesto")
    s.update_from_message("hello")
    assert len(s.messages) == 1
    assert s.messages[0] == "hello"


def test_session_state_mark_done():
    s = SessionState(session_id="test", agent_name="hefesto")
    s.update_from_message("response")
    s.mark_done(response="test response", stop_reason="end_turn")
    assert s.status == SessionStatus.DONE
    assert s.final_response == "test response"
    assert s.stop_reason == "end_turn"
    assert s.completion_event.is_set()


def test_session_state_mark_error():
    s = SessionState(session_id="test", agent_name="hefesto")
    s.mark_error("something broke")
    assert s.status == SessionStatus.ERROR
    assert s.final_response == "something broke"
    assert s.stop_reason == "error"
    assert s.completion_event.is_set()


def test_session_state_mark_cancelled():
    s = SessionState(session_id="test", agent_name="hefesto")
    s.mark_cancelled()
    assert s.status == SessionStatus.CANCELLED
    assert s.stop_reason == "cancelled"
    assert s.completion_event.is_set()


def test_completion_event_not_set_on_creation():
    """Verify that completion_event is NOT set when SessionState is created."""
    s = SessionState(session_id="test", agent_name="hefesto")
    assert not s.completion_event.is_set()


def test_registry_get_session():
    reg = OlympusRegistry()
    profile = DaimonProfile(name="test", role="test", description="test")
    reg.register_discovery({"test": profile})
    agent = reg.get_agent("test")
    session = SessionState(session_id="s1", agent_name="test")
    agent.sessions["s1"] = session
    assert reg.get_session("s1") == session
    assert reg.get_session("nonexistent") is None


def test_registry_list_agents():
    reg = OlympusRegistry()
    profile = DaimonProfile(name="test", role="worker", description="test agent")
    reg.register_discovery({"test": profile})
    agents = reg.list_agents()
    assert len(agents) == 1
    assert agents[0]["name"] == "test"
    assert agents[0]["status"] == "dead"


def test_agent_state_next_session_id():
    """AgentState.next_session_id() produces incrementing IDs."""
    profile = DaimonProfile(name="test", role="worker", description="test")
    agent = AgentState(name="test", profile=profile)
    sid1 = agent.next_session_id()
    sid2 = agent.next_session_id()
    assert sid1.startswith("olympus_test_")
    assert sid2.startswith("olympus_test_")
    # IDs should be different and increment
    assert sid1 != sid2
    assert "_1" in sid1
    assert "_2" in sid2


def test_agent_state_initial_status():
    """AgentState starts DEAD by default."""
    profile = DaimonProfile(name="test", role="worker", description="test")
    agent = AgentState(name="test", profile=profile)
    assert agent.status == AgentStatus.DEAD
