"""Olympus v2 Event Translator — converts Pi Agent JSONL RPC events to Hermes-compatible format.

Translates the Pi Agent RPC event stream into the format that Hermes talk_to() expects.
This solves the three ACP bugs:
- Bug A: Spinner noise → Pi reports thinking_delta separately from content text
- Bug B: tool_calls always 0 → Pi reports tool_call_start/end events
- Bug C: LLM reasoning not visible → Pi sends thinking_delta events

Pi RPC Event Types (actual format from Pi Agent JSONL output):
- response: Internal acknowledgment (skip)
- agent_start: Agent has started processing
- turn_start: Turn started
- message_start: Message started (informational, content comes in message_update)
- message_update: Incremental content via assistantMessageEvent sub-types:
    thinking_start, thinking_delta, thinking_end,
    text_start, text_delta, text_end,
    tool_call_start, tool_call_delta, tool_call_end
- message_end: Message completed (stop_reason, full content, usage)
- turn_end: Turn ended
- agent_end: Agent session complete (includes full messages array)
- error: Pi reported an error

Hermes talk_to Response Format:
- {"status": "open|active|done|error", "thoughts": N, "tool_calls": N, "response": "...", ...}
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("olympus_v2.event_translator")


# Patterns that indicate spinner noise (kawaii, decorative, non-substantive)
# This mirrors the ACP _is_spinner_noise logic but is more conservative since
# Pi separates thinking from content more cleanly
_SPINNER_PATTERN = re.compile(
    r'^[\(\[（）【].*?[\)\]）】]'       # Brackets wrapping content
    r'|^\\s*(thinking|analyzing|processing|brainstorming|working|loading'
    r'|ruminating|cogitating|mulling|pondering|reflecting|synthesizing'
    r'|contemplating|deliberating|musing|meditating|calculating|formulating)'
    r'\\.{1,3}\\s*$',                  # Status words with ellipsis
    re.IGNORECASE
)


@dataclass
class SessionBuffer:
    """Accumulates Pi Agent events for a session and tracks state."""

    session_id: str
    accumulated_text: str = ""
    accumulated_reasoning: str = ""
    thoughts_count: int = 0
    tool_calls_count: int = 0
    tool_calls_detail: list[dict[str, Any]] = field(default_factory=list)
    is_done: bool = False
    stop_reason: str = ""
    final_response: str = ""
    started_at: float = field(default_factory=time.time)
    last_turn_response: str = ""   # Extracted from turn_end.message — the clean response from the last completed turn
    turn_count: int = 0           # Number of turns completed


def is_spinner_noise(text: str) -> bool:
    """Check if a text chunk is spinner noise rather than substantive content.

    More conservative than the ACP version since Pi reports reasoning
    separately via thinking_delta events.
    """
    stripped = text.strip()
    if not stripped or len(stripped) < 3:
        return True
    return bool(_SPINNER_PATTERN.match(stripped))


def translate_event(event: dict[str, Any], buffer: SessionBuffer) -> dict[str, Any] | None:
    """Translate a single Pi Agent RPC event into a Hermes-compatible status update.

    Args:
        event: A parsed JSON event from Pi Agent's stdout.
        buffer: The session buffer tracking accumulated state.

    Returns:
        A dict suitable for returning via MCP talk_to response, or None
        if the event is an internal acknowledgment (e.g., response type).
    """
    event_type = event.get("type", "")

    if event_type == "agent_start":
        # Agent has started processing — signal active state
        return {
            "status": "active",
            "thoughts": buffer.thoughts_count,
            "tool_calls": buffer.tool_calls_count,
            "response": buffer.last_turn_response or buffer.accumulated_text,
        }

    elif event_type == "turn_start":
        # Turn started — reset per-turn accumulators so tool output from previous turns
        # doesn't contaminate the text buffer for subsequent turns.
        buffer.accumulated_text = ""
        buffer.accumulated_reasoning = ""
        return {
            "status": "active",
            "thoughts": buffer.thoughts_count,
            "tool_calls": buffer.tool_calls_count,
            "response": buffer.last_turn_response or buffer.accumulated_text,
        }

    elif event_type == "turn_end":
        # Turn ended — extract the assistant's message from this turn.
        # turn_end.message contains the COMPLETE assistant response for this turn,
        # clean of any tool output from previous turns.
        message = event.get("message", {})
        if isinstance(message, dict):
            content = message.get("content", [])
            if isinstance(content, list):
                text = _extract_text_from_content(content)
                if text:
                    buffer.last_turn_response = text

        buffer.turn_count += 1
        return {
            "status": "active",
            "thoughts": buffer.thoughts_count,
            "tool_calls": buffer.tool_calls_count,
            "response": buffer.last_turn_response or buffer.accumulated_text,
        }

    elif event_type == "message_start":
        # Informational — content comes in message_update events, skip
        return None

    elif event_type == "message_update":
        return _translate_message_update(event, buffer)

    elif event_type == "message_end":
        return _translate_message_end(event, buffer)

    elif event_type == "agent_end":
        return _translate_agent_end(event, buffer)

    elif event_type == "tool_execution_start":
        # Pi sends this when it starts executing a tool (after toolcall_end)
        tool_name = event.get("toolName", "unknown")
        tool_call_id = event.get("toolCallId", "")
        logger.debug(f"[event_translator] Tool execution started: {tool_name} ({tool_call_id})")
        # Increment tool_calls_count for each actual execution
        buffer.tool_calls_count += 1
        buffer.tool_calls_detail.append({
            "name": tool_name,
            "id": tool_call_id,
            "status": "executing",
        })
        return {
            "status": "active",
            "thoughts": buffer.thoughts_count,
            "tool_calls": buffer.tool_calls_count,
            "response": buffer.last_turn_response or buffer.accumulated_text,
            "tool_calls_detail": buffer.tool_calls_detail,
        }

    elif event_type == "tool_execution_end":
        # Pi sends this when tool execution completes
        tool_name = event.get("toolName", "unknown")
        tool_call_id = event.get("toolCallId", "")
        # Update the last matching tool detail to "completed"
        for detail in reversed(buffer.tool_calls_detail):
            if detail.get("id") == tool_call_id or detail.get("name") == tool_name:
                detail["status"] = "completed"
                break
        logger.debug(f"[event_translator] Tool execution completed: {tool_name} ({tool_call_id})")
        return {
            "status": "active",
            "thoughts": buffer.thoughts_count,
            "tool_calls": buffer.tool_calls_count,
            "response": buffer.last_turn_response or buffer.accumulated_text,
            "tool_calls_detail": buffer.tool_calls_detail,
        }

    elif event_type == "response":
        # Internal acknowledgment from Pi — don't report to Hermes
        logger.debug(f"[event_translator] Skipping response event: {event}")
        return None

    elif event_type == "error":
        # Pi reported an error
        error_msg = event.get("message", event.get("error", "Unknown Pi Agent error"))
        buffer.is_done = True
        buffer.stop_reason = "error"
        return {
            "status": "error",
            "error": error_msg,
            "thoughts": buffer.thoughts_count,
            "tool_calls": buffer.tool_calls_count,
            "response": buffer.last_turn_response or buffer.accumulated_text,
        }

    else:
        # Unknown event type — log at DEBUG (too noisy at WARNING)
        logger.debug(f"[event_translator] Unknown event type: {event_type}")
        return None


def _translate_message_update(event: dict[str, Any], buffer: SessionBuffer) -> dict[str, Any]:
    """Translate a message_update event, which can contain text, thinking, or tool call deltas.

    Pi Agent uses assistantMessageEvent with a type field to indicate the kind of update.
    The old format used content.text_delta / content.thinking_delta at the top level, which
    is kept as a fallback for backwards compatibility.
    """
    ame = event.get("assistantMessageEvent", {})
    ame_type = ame.get("type", "")

    # ── Pi Agent format: assistantMessageEvent ──────────────────────────────
    if ame_type:
        if ame_type == "thinking_start":
            buffer.thoughts_count += 1
            return {
                "status": "active",
                "thoughts": buffer.thoughts_count,
                "tool_calls": buffer.tool_calls_count,
                "response": buffer.last_turn_response or buffer.accumulated_text,
                "reasoning": buffer.accumulated_reasoning or None,
            }

        elif ame_type == "thinking_delta":
            delta = ame.get("delta", "")
            if delta:
                buffer.accumulated_reasoning += delta
                buffer.thoughts_count += 1
            return {
                "status": "active",
                "thoughts": buffer.thoughts_count,
                "tool_calls": buffer.tool_calls_count,
                "response": buffer.last_turn_response or buffer.accumulated_text,
                "reasoning": buffer.accumulated_reasoning or None,
            }

        elif ame_type == "thinking_end":
            # Full thinking content may be in ame["content"] if not accumulated
            content = ame.get("content", "")
            if content and not buffer.accumulated_reasoning:
                buffer.accumulated_reasoning = content
            buffer.thoughts_count += 1
            return {
                "status": "active",
                "thoughts": buffer.thoughts_count,
                "tool_calls": buffer.tool_calls_count,
                "response": buffer.last_turn_response or buffer.accumulated_text,
                "reasoning": buffer.accumulated_reasoning or None,
            }

        elif ame_type == "text_start":
            return {
                "status": "active",
                "thoughts": buffer.thoughts_count,
                "tool_calls": buffer.tool_calls_count,
                "response": buffer.last_turn_response or buffer.accumulated_text,
            }

        elif ame_type == "text_delta":
            delta = ame.get("delta", "")
            if delta:
                buffer.accumulated_text += delta
                if not is_spinner_noise(delta):
                    buffer.thoughts_count += 1
            return {
                "status": "active",
                "thoughts": buffer.thoughts_count,
                "tool_calls": buffer.tool_calls_count,
                "response": buffer.last_turn_response or buffer.accumulated_text,
            }

        elif ame_type == "text_end":
            # Final text content may be in ame["content"] if not accumulated
            content = ame.get("content", "")
            if content and not buffer.accumulated_text:
                buffer.accumulated_text = content
            buffer.final_response = buffer.last_turn_response or buffer.accumulated_text
            return {
                "status": "active",
                "thoughts": buffer.thoughts_count,
                "tool_calls": buffer.tool_calls_count,
                "response": buffer.last_turn_response or buffer.accumulated_text,
            }

        elif ame_type in ("tool_call_start", "toolcall_start"):
            buffer.tool_calls_count += 1
            tool_name = (
                ame.get("name", "")
                or ame.get("toolName", "")
                or (ame.get("function", {}).get("name", "") if isinstance(ame.get("function"), dict) else "")
                or "unknown"
            )
            buffer.tool_calls_detail.append({
                "name": tool_name,
                "status": "started",
            })
            return {
                "status": "active",
                "thoughts": buffer.thoughts_count,
                "tool_calls": buffer.tool_calls_count,
                "response": buffer.last_turn_response or buffer.accumulated_text,
                "tool_calls_detail": buffer.tool_calls_detail,
            }

        elif ame_type in ("tool_call_delta", "toolcall_delta"):
            # Intermediate tool call data — no buffer changes needed
            return {
                "status": "active",
                "thoughts": buffer.thoughts_count,
                "tool_calls": buffer.tool_calls_count,
                "response": buffer.last_turn_response or buffer.accumulated_text,
                "tool_calls_detail": buffer.tool_calls_detail,
            }

        elif ame_type in ("tool_call_end", "toolcall_end"):
            if buffer.tool_calls_detail:
                buffer.tool_calls_detail[-1]["status"] = "completed"
            return {
                "status": "active",
                "thoughts": buffer.thoughts_count,
                "tool_calls": buffer.tool_calls_count,
                "tool_calls_detail": buffer.tool_calls_detail,
                "response": buffer.last_turn_response or buffer.accumulated_text,
            }

        else:
            # Unknown assistantMessageEvent type — log at DEBUG
            logger.debug(f"[event_translator] Unknown assistantMessageEvent type: {ame_type}")
            return {
                "status": "active",
                "thoughts": buffer.thoughts_count,
                "tool_calls": buffer.tool_calls_count,
                "response": buffer.last_turn_response or buffer.accumulated_text,
            }

    # ── Fallback: old content.* format (backwards compat) ──────────────────
    content = event.get("content", {})

    # Handle text_delta — substantive agent output
    text_delta = content.get("text_delta", content.get("text", ""))
    if text_delta:
        buffer.accumulated_text += text_delta
        if not is_spinner_noise(text_delta):
            buffer.thoughts_count += 1

    # Handle thinking_delta — LLM reasoning
    thinking_delta = content.get("thinking_delta", content.get("thinking", ""))
    if thinking_delta:
        buffer.accumulated_reasoning += thinking_delta
        buffer.thoughts_count += 1

    # Handle tool_call_start — agent is invoking a tool
    tool_call_start = content.get("tool_call_start", content.get("toolCallStart"))
    if tool_call_start:
        buffer.tool_calls_count += 1
        tool_name = ""
        if isinstance(tool_call_start, dict):
            tool_name = tool_call_start.get("toolName", tool_call_start.get("name", tool_call_start.get("function", "unknown")))
        elif isinstance(tool_call_start, str):
            tool_name = tool_call_start

        buffer.tool_calls_detail.append({
            "name": tool_name,
            "status": "started",
        })

    # Handle tool_call_delta — intermediate tool call data
    tool_call_delta = content.get("tool_call_delta", content.get("toolCallDelta"))
    if tool_call_delta:
        if buffer.tool_calls_detail:
            last_call = buffer.tool_calls_detail[-1]
            if isinstance(tool_call_delta, dict):
                last_call.update(tool_call_delta)

    # Handle tool_call_end — tool execution completed
    tool_call_end = content.get("tool_call_end", content.get("toolCallEnd"))
    if tool_call_end:
        if buffer.tool_calls_detail:
            last_call = buffer.tool_calls_detail[-1]
            last_call["status"] = "completed"
            if isinstance(tool_call_end, dict):
                last_call.update(tool_call_end)
            elif isinstance(tool_call_end, str):
                last_call["result_preview"] = tool_call_end[:200]

    # Return current state
    return {
        "status": "active",
        "thoughts": buffer.thoughts_count,
        "tool_calls": buffer.tool_calls_count,
        "response": buffer.last_turn_response or buffer.accumulated_text,
        "reasoning": buffer.accumulated_reasoning if buffer.accumulated_reasoning else None,
        "tool_calls_detail": buffer.tool_calls_detail if buffer.tool_calls_detail else None,
    }


def _extract_text_from_content(content: list[dict[str, Any]]) -> str:
    """Extract plain text from a Pi message content array.

    Pi's content is an array of objects like:
      [{"type": "thinking", "thinking": "..."}, {"type": "text", "text": "..."}]
    Returns the concatenated text from all items with type="text".
    """
    texts: list[str] = []
    for item in content:
        if isinstance(item, dict) and item.get("type") == "text":
            text = item.get("text", "")
            if text:
                texts.append(text)
    return "".join(texts)


def _translate_message_end(event: dict[str, Any], buffer: SessionBuffer) -> dict[str, Any]:
    """Translate a message_end event — the agent has finished its response.

    Pi's message_end for assistant messages includes the full message with content
    array and usage info. We extract the text if buffer hasn't accumulated it.
    """
    stop_reason = event.get("stopReason", event.get("stop_reason", "end_turn"))

    # Try to extract stop_reason from nested message if not at top level
    message = event.get("message", {})
    if not stop_reason or stop_reason == "end_turn":
        stop_reason = message.get("stopReason", message.get("stop_reason", stop_reason))

    buffer.stop_reason = stop_reason

    # Extract text from message content if available (structured event)
    if message:
        content = message.get("content", [])
        if isinstance(content, list):
            extracted = _extract_text_from_content(content)
            if extracted:
                buffer.last_turn_response = extracted

    # Final response priority: last_turn_response (clean, from structured event)
    # > accumulated_text (may contain tool output, but still useful as fallback)
    if buffer.last_turn_response:
        buffer.final_response = buffer.last_turn_response
    elif buffer.accumulated_text:
        buffer.final_response = buffer.accumulated_text

    if stop_reason in ("end_turn", "stop"):
        buffer.is_done = True
        return {
            "status": "done",
            "thoughts": buffer.thoughts_count,
            "tool_calls": buffer.tool_calls_count,
            "response": buffer.final_response,
            "stop_reason": stop_reason,
        }
    else:
        # Other stop reasons (tool_use, max_tokens, etc.) — agent may continue
        return {
            "status": "active",
            "thoughts": buffer.thoughts_count,
            "tool_calls": buffer.tool_calls_count,
            "response": buffer.last_turn_response or buffer.accumulated_text,
            "stop_reason": stop_reason,
        }


def _translate_agent_end(event: dict[str, Any], buffer: SessionBuffer) -> dict[str, Any]:
    """Translate an agent_end event — the entire agent session is complete.

    Pi's agent_end includes a messages array with all messages. We extract
    the assistant's text content from the last assistant message as the
    final response if we haven't accumulated it yet.
    """
    buffer.is_done = True

    # CANONICAL RESPONSE EXTRACTION: agent_end.messages is the single source of truth.
    # It contains ALL messages from the session with clear roles:
    #   role="assistant" → model-generated text (what we want)
    #   role="toolResult" → tool execution output (SKIP — can be 48K+ chars of noise)
    #   role="user" → user messages (skip)
    #
    # We ALWAYS check agent_end.messages first, regardless of what last_turn_response
    # says (last_turn_response from message_end/turn_end can contain tool output
    # for models like kimi-k2.6 and mimo-v2-omni that don't produce text_delta after tools).
    messages = event.get("messages", [])
    canonical_text = ""
    if isinstance(messages, list) and messages:
        # Walk BACKWARDS to find the LAST assistant message with substantive text
        for msg in reversed(messages):
            if isinstance(msg, dict) and msg.get("role") == "assistant":
                content = msg.get("content", [])
                if isinstance(content, list):
                    extracted = _extract_text_from_content(content)
                    if extracted:
                        canonical_text = extracted
                        break

    if canonical_text:
        # Canonical source found — override any potentially contaminated buffers
        buffer.last_turn_response = canonical_text
        buffer.final_response = canonical_text
    elif buffer.last_turn_response:
        # No text in agent_end.messages? Fall back to turn_end extraction
        buffer.final_response = buffer.last_turn_response
    elif buffer.accumulated_text:
        # Last resort: accumulated_text from current turn
        buffer.final_response = buffer.accumulated_text

    return {
        "status": "done",
        "thoughts": buffer.thoughts_count,
        "tool_calls": buffer.tool_calls_count,
        "response": buffer.final_response or "",
        "stop_reason": buffer.stop_reason or "agent_end",
    }


def translate_events_batch(
    events: list[dict[str, Any]],
    buffer: SessionBuffer,
) -> dict[str, Any]:
    """Process a batch of Pi events and return the latest consolidated state.

    This is the main entry point for the server's poll action. It processes
    all new events since the last poll and returns the current state.

    Args:
        events: List of Pi Agent events (already parsed from JSONL).
        buffer: The session buffer to update.

    Returns:
        Consolidated state dict with status, thoughts, tool_calls, response.
    """
    last_result: dict[str, Any] = {
        "status": "active",
        "thoughts": buffer.thoughts_count,
        "tool_calls": buffer.tool_calls_count,
        "response": buffer.last_turn_response or buffer.accumulated_text,
    }

    for event in events:
        result = translate_event(event, buffer)
        if result is not None:
            last_result = result

    return last_result