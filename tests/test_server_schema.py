"""Validate that the Olympus MCP server tool schemas are consistent
with the actual implementation — no phantom actions or parameters."""
import re
import inspect
import pytest


@pytest.fixture
def server_source():
    """Get the source code of the server module."""
    from olympus import server as server_module
    return inspect.getsource(server_module)


def test_talk_to_action_enum_no_wait(server_source):
    """talk_to action enum MUST NOT contain 'wait' — it was removed."""
    enum_values = _extract_action_enum(server_source)
    assert 'wait' not in enum_values, \
        f"talk_to action enum still contains 'wait' — this action was removed. Found: {enum_values}"


def test_talk_to_action_enum_no_discover(server_source):
    """talk_to action enum MUST NOT contain 'discover' — it's a separate tool.
    
    'discover' appears in the talk_to tool's enum but is NOT handled by the
    talk_to handler — it falls through to the error path. The else clause says:
    'For discovery, use the discover tool.' So it's a phantom action that
    shouldn't be in the enum.
    """
    enum_values = _extract_action_enum(server_source)
    assert 'discover' not in enum_values, \
        f"talk_to action enum still contains 'discover' — it's a phantom action. Found: {enum_values}"


def test_talk_to_no_timeout_parameter(server_source):
    """talk_to schema MUST NOT have a 'timeout' parameter — it's phantom.
    
    The 'timeout' parameter was only used by the removed 'wait' action.
    It is now unused in _handle_talk_to.
    """
    timeout_keys = _extract_property_keys(server_source)
    assert 'timeout' not in timeout_keys, \
        f"talk_to schema still has 'timeout' parameter — it's phantom and was removed. Found keys: {timeout_keys}"


def test_talk_to_handled_actions_match_schema(server_source):
    """The actions actually handled by _handle_talk_to should match the schema enum.
    
    Currently handled: open, message, poll, cancel, close
    The schema should only list these.
    """
    handled = {"open", "message", "poll", "cancel", "close", "delegate", "steer"}
    enum_values = set(_extract_action_enum(server_source))
    # Every value in the enum should be a handled action
    phantoms = enum_values - handled
    assert not phantoms, \
        f"Schema has phantom action(s) not handled by code: {phantoms}. " \
        f"Handled actions: {handled}"


# ---- Helper functions ----

def _extract_action_enum(source: str) -> list[str]:
    """Extract the action enum list from talk_to's inputSchema."""
    # Find the inputSchema block for talk_to
    # Strategy: find the talk_to tool definition, then its inputSchema, then action's enum
    idx = source.find('"talk_to"')
    if idx == -1:
        return []
    # Find the enum in the action property within this tool
    talk_to_block = source[idx:idx + 2000]
    match = re.search(r'"enum":\s*\[(.*?)\]', talk_to_block)
    if not match:
        return []
    items = match.group(1)
    return [item.strip().strip('"') for item in items.split(',')]


def _extract_property_keys(source: str) -> list[str]:
    """Extract the top-level property key names from the talk_to inputSchema."""
    idx = source.find('"talk_to"')
    if idx == -1:
        return []
    talk_to_block = source[idx:idx + 2000]
    # Find the properties block
    match = re.search(r'"properties":\s*\{(.*?)\}', talk_to_block)
    if not match:
        return []
    props_block = match.group(1)
    # Extract all quoted keys before ': {' or ': {'
    keys = re.findall(r'"(\w+)":\s*\{', props_block)
    return keys
