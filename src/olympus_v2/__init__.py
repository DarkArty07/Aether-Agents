"""Olympus v2 — Pi Agent RPC-based MCP server for Daimon orchestration.

Replaces ACP (Agent Client Protocol) with Pi Agent's JSONL RPC protocol.
This is a separate, non-invasive module that coexists with Olympus v1.

Key improvements over ACP:
- Bug A fix: Spinner noise no longer inflates substantive_thoughts (Pi reports thinking_delta separately)
- Bug B fix: tool_calls are properly reported (Pi's tool_call_start/end events)
- Bug C fix: LLM reasoning is visible via thinking_delta events
"""

__version__ = "0.1.0"