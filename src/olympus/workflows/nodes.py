"""LangGraph nodes that execute Daimon operations via ACP."""

import asyncio
import logging
import re
import time

from .state import WorkflowState
from ..acp_client import ACPManager
from ..registry import SessionStatus

logger = logging.getLogger("olympus.workflows.nodes")

# CHANGE 3: Module-level constants for the progress watchdog
POLL_INTERVAL = 10    # seconds
STALL_TIMEOUT = 120   # 2 minutes without activity = STALLED

# Spinner noise filter — identifies kawaii/progress text that isn't substantive content.
# The ACP protocol has two channels: AgentMessageChunk (response text) and
# AgentThoughtChunk (progress/spinner/leaning). Most providers use both correctly.
# Some providers (e.g., GLM-5.1) stream response content via AgentThoughtChunk
# instead of AgentMessageChunk. This filter helps separate signal from noise
# when falling back to the thoughts channel.
_SPINNER_PATTERN = re.compile(
    r'^[\(\[（【].*?[\)\]）】]'            # Brackets: (...), [...], （...）
    r'|(°ロ°|´･_･`|•̀ᴗ•́|ᕕᐛᕗ|◝ᴗ◝|◕ᴗ◕|ᕙᐛᕗ|¯\\_?\\(ツ\\)_?/¯)'  # Kawaii faces
    r'|^\s*(thinking|analyzing|processing|brainstorming|working|loading)\.{1,3}\s*$',  # Status text
    re.IGNORECASE
)


def _is_spinner_noise(text: str) -> bool:
    """Filter out kawaii spinner patterns that aren't substantive content."""
    text = text.strip()
    if not text or len(text) < 5:
        return True
    return bool(_SPINNER_PATTERN.match(text))

# CHANGE 2+3: Rewritten _run_acp_session with try/finally and progress watchdog
async def _run_acp_session(acp: ACPManager, agent_name: str, prompt: str) -> str:
    """Run a full ACP session with progress watchdog."""
    session = await acp.open_session(agent_name)
    try:
        await acp.send_prompt(session.session_id, prompt)

        last_thoughts_count = len(session.thoughts)
        last_messages_count = len(session.messages)
        last_tool_calls_count = len(session.tool_calls)
        last_activity_time = time.monotonic()
        logger.info(f"[workflow] {agent_name} session started")

        while True:
            try:
                await asyncio.wait_for(session.completion_event.wait(), timeout=POLL_INTERVAL)
                break  # Completed!
            except asyncio.TimeoutError:
                pass  # Poll interval expired

            if session.status in (SessionStatus.ERROR, SessionStatus.CANCELLED):
                return session.final_response or f"Error: Session {session.status.value}"

            curr_t = len(session.thoughts)
            curr_m = len(session.messages)
            curr_tc = len(session.tool_calls)

            if curr_t > last_thoughts_count or curr_m > last_messages_count or curr_tc > last_tool_calls_count:
                last_activity_time = time.monotonic()
                last_thoughts_count = curr_t
                last_messages_count = curr_m
                last_tool_calls_count = curr_tc
                logger.info(f"[workflow] {agent_name} still working — {curr_t} thoughts, {curr_tc} tool_calls ({time.monotonic() - last_activity_time:.0f}s elapsed)")
            else:
                if time.monotonic() - last_activity_time >= STALL_TIMEOUT:
                    logger.error(f"[workflow] {agent_name} STALLED — no activity for {STALL_TIMEOUT}s")
                    raise RuntimeError(f"Agent {agent_name} stalled — no activity for {STALL_TIMEOUT}s")

        if session.status == SessionStatus.DONE:
            result = session.final_response or ""
            # Recovery: if messages channel is empty but thoughts has content,
            # the agent may have streamed via AgentThoughtChunk instead of
            # AgentMessageChunk. Filter out spinner noise and use substantive
            # thoughts as a fallback — this avoids silent empty responses.
            if not result and session.thoughts:
                content_thoughts = [t for t in session.thoughts if not _is_spinner_noise(t)]
                if content_thoughts:
                    logger.warning(
                        f"[workflow] {agent_name} returned empty response but has "
                        f"{len(content_thoughts)}/{len(session.thoughts)} substantive thoughts. "
                        f"Agent may stream via thoughts channel instead of messages. "
                        f"Using filtered thoughts as fallback."
                    )
                    result = "\n".join(content_thoughts)
            return result
        elif session.status == SessionStatus.ERROR:
            return f"Error: {session.final_response}"
        return "Error: Session completed with unexpected status"
    finally:
        try:
            await acp.close_session(session.session_id)
        except Exception as e:
            logger.warning(f"Failed to close session {session.session_id}: {e}")


# A hack to pass the acp parameter correctly:
# LangGraph state nodes only take ONE argument (state). We can pass acp via partial
# or via closure. Let's make node factories that receive ACPManager and return the async func.

def make_node_design(acp: ACPManager):
    async def node_design(state: WorkflowState) -> dict:
        """Daedalus node: generates design/plan based on user prompt."""
        node_name = "design"
        agent_name = "daedalus"
        start = time.monotonic()
        logger.info(f"[workflow] {node_name} started — agent={agent_name}")
        # CHANGE 1: Fixed double-escape \\n -> \n (real newlines)
        prompt = f"PROJECT_ROOT: {state.get('project_root', '')}\nTASK: Design the following feature.\n{state.get('user_prompt', '')}"
        try:
            result = await _run_acp_session(acp, "daedalus", prompt)
            elapsed = time.monotonic() - start
            if result.startswith("Error:"):
                logger.error(f"[workflow] {node_name} failed: {result}")
                # CHANGE 7: Return errors in state
                return {"context": result, "errors": [f"daedalus: {result}"], "node_name": node_name, "status": "failed"}
            logger.info(f"[workflow] {node_name} completed in {elapsed:.1f}s")
            return {"context": result, "node_name": node_name}
        except RuntimeError as e:
            elapsed = time.monotonic() - start
            logger.error(f"[workflow] {node_name} failed: {e}")
            return {"context": "", "errors": [f"daedalus: {str(e)}"], "node_name": node_name, "status": "failed"}
    return node_design

def make_node_implement(acp: ACPManager):
    async def node_implement(state: WorkflowState) -> dict:
        """Hefesto node: implements code based on design and feedback."""
        node_name = "implement"
        agent_name = "hefesto"
        start = time.monotonic()
        logger.info(f"[workflow] {node_name} started — agent={agent_name}")
        # CHANGE 1: Fixed double-escape \\n -> \n (real newlines)
        prompt = f"PROJECT_ROOT: {state.get('project_root', '')}\nTASK: Implement the feature.\n"
        if state.get("context"):
            prompt += f"\nDESIGN CONTEXT:\n{state['context']}\n"
        if state.get("audit_result") and not state.get("audit_passed"):
            prompt += f"\nAUDIT FEEDBACK (Must fix these issues):\n{state['audit_result']}\n"
        else:
            prompt += f"\nUSER PROMPT:\n{state.get('user_prompt', '')}\n"

        try:
            result = await _run_acp_session(acp, "hefesto", prompt)
            elapsed = time.monotonic() - start
            if result.startswith("Error:"):
                logger.error(f"[workflow] {node_name} failed: {result}")
                return {"code": result, "errors": [f"hefesto: {result}"], "node_name": node_name, "status": "failed"}

            # Increment review cycle if coming from an audit failure
            cycles = state.get("review_cycles", 0)
            if state.get("audit_result") and not state.get("audit_passed"):
                cycles += 1

            logger.info(f"[workflow] {node_name} completed in {elapsed:.1f}s")
            return {"code": result, "review_cycles": cycles, "node_name": node_name}
        except RuntimeError as e:
            elapsed = time.monotonic() - start
            logger.error(f"[workflow] {node_name} failed: {e}")
            return {"code": "", "errors": [f"hefesto: {str(e)}"], "node_name": node_name, "status": "failed"}
    return node_implement

def make_node_audit(acp: ACPManager):
    async def node_audit(state: WorkflowState) -> dict:
        """Athena node: audits the code."""
        node_name = "audit"
        agent_name = "athena"
        start = time.monotonic()
        logger.info(f"[workflow] {node_name} started — agent={agent_name}")
        # CHANGE 1: Fixed double-escape \\n -> \n (real newlines)
        prompt = f"PROJECT_ROOT: {state.get('project_root', '')}\nTASK: Audit this code for security, best practices, and correctness.\n"
        prompt += f"USER INTENT:\n{state.get('user_prompt', '')}\n"
        prompt += f"IMPLEMENTATION DETAILS:\n{state.get('code', '')}\n"
        prompt += "Reply exactly with 'PASSED' at the beginning of your response if the code is correct. Otherwise list the issues."

        try:
            result = await _run_acp_session(acp, "athena", prompt)
            elapsed = time.monotonic() - start
            if result.startswith("Error:"):
                logger.error(f"[workflow] {node_name} failed: {result}")
                return {"audit_result": result, "audit_passed": False, "errors": [f"athena: {result}"], "node_name": node_name, "status": "failed"}

            passed = result.strip().startswith("PASSED")
            logger.info(f"[workflow] {node_name} completed in {elapsed:.1f}s — {'PASSED' if passed else 'FAILED'}")
            return {"audit_result": result, "audit_passed": passed, "node_name": node_name}
        except RuntimeError as e:
            elapsed = time.monotonic() - start
            logger.error(f"[workflow] {node_name} failed: {e}")
            return {"audit_result": "", "audit_passed": False, "errors": [f"athena: {str(e)}"], "node_name": node_name, "status": "failed"}
    return node_audit

def make_node_research(acp: ACPManager):
    async def node_research(state: WorkflowState) -> dict:
        """Etalides node: investigates a topic."""
        node_name = "research"
        agent_name = "etalides"
        start = time.monotonic()
        logger.info(f"[workflow] {node_name} started — agent={agent_name}")
        # CHANGE 1: Fixed double-escape \\n -> \n (real newlines)
        prompt = f"PROJECT_ROOT: {state.get('project_root', '')}\nTASK: Research the following topic.\n{state.get('user_prompt', '')}"
        try:
            result = await _run_acp_session(acp, "etalides", prompt)
            elapsed = time.monotonic() - start
            if result.startswith("Error:"):
                logger.error(f"[workflow] {node_name} failed: {result}")
                return {"research": result, "errors": [f"etalides: {result}"], "node_name": node_name, "status": "failed"}
            logger.info(f"[workflow] {node_name} completed in {elapsed:.1f}s")
            return {"research": result, "node_name": node_name}
        except RuntimeError as e:
            elapsed = time.monotonic() - start
            logger.error(f"[workflow] {node_name} failed: {e}")
            return {"research": "", "errors": [f"etalides: {str(e)}"], "node_name": node_name, "status": "failed"}
    return node_research

# CHANGE 6: New should_terminate_on_error function
def should_terminate_on_error(state: WorkflowState) -> str:
    """Conditional edge: terminate early if any errors accumulated."""
    if state.get("errors") and len(state["errors"]) > 0:
        return "finalize"
    return "continue"

# CHANGE 6: Updated should_retry_implementation to check errors FIRST
def should_retry_implementation(state: WorkflowState) -> str:
    """Conditional edge: retry if audit failed and under max cycles."""
    if state.get("errors") and len(state["errors"]) > 0:
        return "finalize"
    if state.get("audit_passed", False):
        return "finalize"
    if state.get("review_cycles", 0) < state.get("max_review_cycles", 3):
        return "implement"
    return "finalize"

async def node_finalize(state: WorkflowState) -> dict:
    """Consolidation node."""
    cycles = state.get("review_cycles", 0)
    passed = state.get("audit_passed", False)
    errors = state.get("errors", [])

    if errors:
        status = f"Failed — {'; '.join(errors)}"
    elif passed:
        status = "Approved"
    else:
        status = "Rejected (Reached max review cycles without passing)"

    # CHANGE 1: Fixed double-escape \\n -> \n (real newlines)
    final = f"Workflow Completed.\nStatus: {status}\nReview Cycles: {cycles}\n"
    if state.get("research"):
        final += f"\n--- Research ---\n{state['research']}\n"
    final += f"\n--- Implementation ---\n{state.get('code', 'None')}\n"
    if state.get("audit_result"):
        final += f"\n--- Final Audit ---\n{state['audit_result']}\n"

    # CHANGE 7: Include errors and status in output
    return {"final_response": final, "status": "failed" if errors else "completed", "node_name": "finalize"}
