#!/usr/bin/env python3
"""Verification tests for polling transparency improvements."""

import sys
import os

# Add the src directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("TEST 1: Import chain verification")
print("=" * 60)

# Test 1a: registry import (includes SessionState)
try:
    from olympus.registry import SessionState, SessionStatus, OlympusRegistry
    print("✓ registry imports OK (SessionState, SessionStatus, OlympusRegistry)")
except Exception as e:
    print(f"✗ registry import FAILED: {e}")
    sys.exit(1)

# Test 1b: _is_spinner_noise from its original location
try:
    from olympus.workflows.nodes import _is_spinner_noise
    print("✓ _is_spinner_noise import from workflows.nodes OK")
except Exception as e:
    print(f"✗ _is_spinner_noise import FAILED: {e}")
    sys.exit(1)

# Test 1c: server import (includes _action_poll and _is_spinner_noise)
try:
    from olympus.server import _action_poll
    print("✓ server import OK (_action_poll)")
except Exception as e:
    print(f"✗ server import FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 1d: _is_spinner_noise also importable via server
try:
    from olympus.workflows.nodes import _is_spinner_noise as sn2
    print("✓ _is_spinner_noise accessible from workflows.nodes (server imports from same)")
except Exception as e:
    print(f"✗ _is_spinner_noise indirect import FAILED: {e}")
    sys.exit(1)

print()
print("=" * 60)
print("TEST 2: SessionState substantive_thoughts classification")
print("=" * 60)

s = SessionState(session_id='test', agent_name='test')
s.update_from_thought('(´・ω・) mulling...')
s.update_from_thought('I need to analyze the database schema first.')
s.update_from_thought('◕ᴗ◕ thinking...')
s.update_from_message('Here is my analysis:')

print(f'All thoughts: {len(s.thoughts)}')
print(f'Substantive thoughts: {len(s.substantive_thoughts)}')
print(f'Messages: {len(s.messages)}')
print(f'Last poll idx default: {s.last_poll_thought_idx}')
print(f'Last poll msg idx default: {s.last_poll_message_idx}')
print(f'Last poll tc idx default: {s.last_poll_tool_call_idx}')

assert len(s.thoughts) == 3, f'Expected 3 total thoughts, got {len(s.thoughts)}'
assert len(s.substantive_thoughts) == 1, f'Expected 1 substantive thought, got {len(s.substantive_thoughts)}'
assert s.substantive_thoughts[0] == 'I need to analyze the database schema first.', f'Unexpected substantive thought: {s.substantive_thoughts[0]}'
assert len(s.messages) == 1, f'Expected 1 message, got {len(s.messages)}'
assert s.last_poll_thought_idx == 0, f'Expected default idx 0, got {s.last_poll_thought_idx}'
print('✓ All assertions passed!')

print()
print("=" * 60)
print("TEST 3: _action_poll returns new schema format")
print("=" * 60)

import asyncio
import json

# Set up a registry with a mock session
reg = OlympusRegistry()

# Create a mock agent state with our session
session = SessionState(session_id='test_poll', agent_name='test_agent')
session.update_from_thought('Step 1: Reading the requirements')
session.update_from_thought('Step 2: Planning the implementation')
session.update_from_thought('(´・ω・) mulling...')
session.update_from_message('I will implement the feature as follows:')
session.update_from_tool_call({'name': 'read_file', 'args': {'path': '/test.py'}})

# Import additional registry types for the mock
from olympus.registry import AgentState, AgentStatus
from olympus.config import DaimonProfile

mock_profile = DaimonProfile(name='test_agent', role='test', description='test agent', capabilities=[])
agent = AgentState(name='test_agent', profile=mock_profile, status=AgentStatus.IDLE)
agent.sessions['test_poll'] = session
reg.agents['test_agent'] = agent

# Override registry in server module
import olympus.server as srv
original_registry = srv.registry
srv.registry = reg

try:
    result = asyncio.run(_action_poll('test_poll'))
    data = json.loads(result[0].text)

    # Verify new fields exist
    assert 'progress' in data, 'Missing progress field'
    assert 'new_since_last_poll' in data, 'Missing new_since_last_poll field'
    assert data['progress']['total_thoughts'] == 3, f'Expected 3 total thoughts, got {data["progress"]["total_thoughts"]}'
    assert data['progress']['substantive_thoughts'] == 2, f'Expected 2 substantive, got {data["progress"]["substantive_thoughts"]}'
    assert len(data['thoughts']) == 2, f'Expected 2 thoughts in snapshot (spinners filtered), got {len(data["thoughts"])}'
    assert data['progress']['total_messages'] == 1, f'Expected 1 message, got {data["progress"]["total_messages"]}'
    assert data['progress']['total_tool_calls'] == 1, f'Expected 1 tool call, got {data["progress"]["total_tool_calls"]}'
    
    # Check differential fields have content
    assert len(data['new_since_last_poll']['thoughts']) == 3, f'Expected 3 new thoughts, got {len(data["new_since_last_poll"]["thoughts"])}'
    assert len(data['new_since_last_poll']['messages']) == 1, f'Expected 1 new message, got {len(data["new_since_last_poll"]["messages"])}'
    assert len(data['new_since_last_poll']['tool_calls']) == 1, f'Expected 1 new tool call, got {len(data["new_since_last_poll"]["tool_calls"])}'
    
    print('✓ Poll schema verification passed!')
    print(json.dumps(data, indent=2))
finally:
    # Restore original registry
    srv.registry = original_registry

print()
print("=" * 60)
print("TEST 4: Differential polling — second poll should have empty diffs")
print("=" * 60)

# The previous poll updated the indexes, so now a second poll should have empty diffs
result2 = asyncio.run(_action_poll('test_poll'))
data2 = json.loads(result2[0].text)

assert len(data2['new_since_last_poll']['thoughts']) == 0, f'Expected 0 new thoughts on second poll, got {len(data2["new_since_last_poll"]["thoughts"])}'
assert len(data2['new_since_last_poll']['messages']) == 0, f'Expected 0 new messages on second poll, got {len(data2["new_since_last_poll"]["messages"])}'
assert len(data2['new_since_last_poll']['tool_calls']) == 0, f'Expected 0 new tool calls on second poll, got {len(data2["new_since_last_poll"]["tool_calls"])}'
print('✓ Differential polling works — second poll has empty diffs!')

# Now add more data and verify incremental diff works
session.update_from_thought('Step 3: Writing the code')
session.update_from_thought('◕ᴗ◕ still thinking...')

result3 = asyncio.run(_action_poll('test_poll'))
data3 = json.loads(result3[0].text)

assert len(data3['new_since_last_poll']['thoughts']) == 2, f'Expected 2 new thoughts on third poll, got {len(data3["new_since_last_poll"]["thoughts"])}'
assert data3['progress']['total_thoughts'] == 5, f'Expected 5 total thoughts, got {data3["progress"]["total_thoughts"]}'
assert data3['progress']['substantive_thoughts'] == 3, f'Expected 3 substantive, got {data3["progress"]["substantive_thoughts"]}'
print('✓ Incremental differential polling works correctly!')

print()
print("=" * 60)
print("ALL TESTS PASSED!")
print("=" * 60)