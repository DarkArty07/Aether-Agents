"""LangGraph nodes that execute Daimon operations via ACP."""

import asyncio
import logging
import re
import time

from langgraph.types import interrupt, Command

from .state import WorkflowState
from ..acp_client import ACPManager
from ..registry import SessionStatus

logger = logging.getLogger("olympus.workflows.nodes")

POLL_INTERVAL = 10    # seconds
STALL_TIMEOUT = 120   # 2 minutes without activity = STALLED
# NOTE: There is NO separate "hard timeout" or "safety ceiling" in runner.py.
# STALL_TIMEOUT is the only timeout mechanism. If an agent produces activity
# (thoughts, messages, or tool calls) within this window, it gets unlimited time.
# Only agents with zero activity for STALL_TIMEOUT seconds are considered stalled.

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

async def _run_acp_session(acp: ACPManager, agent_name: str, prompt: str) -> str:
    """Run a full ACP session with progress watchdog."""
    session = await acp.open_session(agent_name)
    try:
        await acp.send_prompt(session.session_id, prompt)

        last_thoughts_count = len(session.thoughts)
        last_messages_count = len(session.messages)
        last_tool_calls_count = len(session.tool_calls)
        last_activity_time = time.monotonic()
        start_time = time.monotonic()
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
                logger.info(f"[workflow] {agent_name} still working — {curr_t} thoughts, {curr_tc} tool_calls ({time.monotonic() - start_time:.0f}s elapsed)")
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


# Node factories that receive ACPManager and return async node functions.
# LangGraph state nodes only take ONE argument (state), so we use closures
# to bind the acp parameter.

def make_node_design(acp: ACPManager):
    async def node_design(state: WorkflowState) -> dict:
        """Daedalus node: generates design/plan based on user prompt."""
        node_name = "design"
        agent_name = "daedalus"
        start = time.monotonic()
        logger.info(f"[workflow] {node_name} started — agent={agent_name}")

        has_ui = state.get("has_ui", True)
        research = state.get("research", "")
        user_prompt = state.get("user_prompt", "")
        project_root = state.get("project_root", "")

        if has_ui:
            prompt = f"PROJECT_ROOT: {project_root}\nTASK: Design the user experience for this feature.\nProduce a user flow (minimum steps) and a layout specification (visual hierarchy, component list, states, accessibility notes).\n\nFEATURE DESCRIPTION:\n{user_prompt}"
        else:
            prompt = f"PROJECT_ROOT: {project_root}\nTASK: Design the internal flow and component specification for this feature.\nThis is a backend/internal feature — produce a data flow and component interaction spec that a developer can implement from.\n\nFEATURE DESCRIPTION:\n{user_prompt}"

        if research:
            prompt += f"\n\nRESEARCH CONTEXT:\n{research}"

        # Include modification feedback if this is a redesign
        if state.get("modification_feedback"):
            prompt += f"\n\nMODIFICATION FEEDBACK FROM USER:\n{state['modification_feedback']}\nPlease revise the design based on this feedback."

        try:
            result = await _run_acp_session(acp, "daedalus", prompt)
            elapsed = time.monotonic() - start
            if result.startswith("Error:"):
                logger.error(f"[workflow] {node_name} failed: {result}")
                return {"context": result, "errors": [f"daedalus: {result}"], "node_name": node_name, "status": "failed"}
            logger.info(f"[workflow] {node_name} completed in {elapsed:.1f}s")
            return {"context": result, "node_name": node_name}
        except Exception as e:
            elapsed = time.monotonic() - start
            logger.error(f"[workflow] {node_name} failed: {e}")
            return {"context": "", "errors": [f"daedalus: {str(e)}"], "node_name": node_name, "status": "failed"}
    return node_design

def make_node_implement(acp: ACPManager):
    async def node_implement(state: WorkflowState) -> dict:
        """Hefesto node: implements code based on context and feedback."""
        node_name = "implement"
        agent_name = "hefesto"
        start = time.monotonic()
        logger.info(f"[workflow] {node_name} started — agent={agent_name}")

        workflow_type = state.get("workflow_type", "feature")
        project_root = state.get("project_root", "")
        user_prompt = state.get("user_prompt", "")
        context = state.get("context", "")
        code = state.get("code", "")
        research = state.get("research", "")
        audit_result = state.get("audit_result", "")
        audit_passed = state.get("audit_passed", False)

        # Build prompt based on workflow type and context
        if workflow_type == "bug-fix":
            if audit_result and not audit_passed:
                prompt = f"PROJECT_ROOT: {project_root}\nTASK: Refine the bug fix based on the security review.\n\nAUDIT FEEDBACK:\n{audit_result}\n\nCURRENT FIX:\n{code}"
            else:
                prompt = f"PROJECT_ROOT: {project_root}\nTASK: Fix this bug based on the diagnosis.\n\nDIAGNOSIS:\n{research}\n\nBUG DESCRIPTION:\n{user_prompt}"
        elif workflow_type == "security-review":
            prompt = f"PROJECT_ROOT: {project_root}\nTASK: Fix the following security issues.\n\nSECURITY FINDINGS:\n{audit_result}\n\nORIGINAL CODE:\n{code}"
        elif workflow_type == "refactor":
            if audit_result and not audit_passed:
                prompt = f"PROJECT_ROOT: {project_root}\nTASK: Refine the refactoring based on security review.\n\nAUDIT FEEDBACK:\n{audit_result}\n\nCURRENT CODE:\n{code}"
            else:
                prompt = f"PROJECT_ROOT: {project_root}\nTASK: Refactor the following code. Preserve all existing functionality.\n\nIMPACT MAP:\n{research}\n\nREFACTOR DESCRIPTION:\n{user_prompt}"
        else:  # feature or default
            if audit_result and not audit_passed:
                prompt = f"PROJECT_ROOT: {project_root}\nTASK: Fix the security issues found in the audit.\n\nAUDIT FEEDBACK (Must fix these issues):\n{audit_result}\n\nORIGINAL IMPLEMENTATION:\n{code}"
            else:
                prompt = f"PROJECT_ROOT: {project_root}\nTASK: Implement the feature.\n\nDESIGN CONTEXT:\n{context}\n\nUSER PROMPT:\n{user_prompt}"

        try:
            result = await _run_acp_session(acp, "hefesto", prompt)
            elapsed = time.monotonic() - start
            if result.startswith("Error:"):
                logger.error(f"[workflow] {node_name} failed: {result}")
                return {"code": result, "errors": [f"hefesto: {result}"], "node_name": node_name, "status": "failed"}

            cycles = state.get("review_cycles", 0)
            if audit_result and not audit_passed:
                cycles += 1

            logger.info(f"[workflow] {node_name} completed in {elapsed:.1f}s")
            return {"code": result, "review_cycles": cycles, "node_name": node_name}
        except Exception as e:
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

        workflow_type = state.get("workflow_type", "feature")
        project_root = state.get("project_root", "")
        user_prompt = state.get("user_prompt", "")
        code = state.get("code", "")
        research = state.get("research", "")
        review_cycles = state.get("review_cycles", 0)

        if workflow_type == "security-review" and review_cycles == 0:
            prompt = f"PROJECT_ROOT: {project_root}\nTASK: Perform a comprehensive security review.\n\nSECURITY CONTEXT (from research):\n{research}\n\nSCOPE:\n{user_prompt}\n\nProvide a full threat assessment using the STRIDE methodology. Prioritize findings by severity."
        elif workflow_type == "security-review" and review_cycles > 0:
            prompt = f"PROJECT_ROOT: {project_root}\nTASK: Re-verify the security fixes. Confirm each finding from the original review has been addressed.\n\nORIGINAL FINDINGS:\n{state.get('audit_result', '')}\n\nFIXED CODE:\n{code}\n\nReply exactly with 'PASSED' if all findings are addressed. Otherwise list remaining issues."
        elif workflow_type == "bug-fix":
            prompt = f"PROJECT_ROOT: {project_root}\nTASK: Verify that this bug fix is correct and doesn't introduce new issues.\n\nBUG DESCRIPTION:\n{user_prompt}\n\nFIX IMPLEMENTATION:\n{code}\n\nReply exactly with 'PASSED' at the beginning of your response if the fix is correct. Otherwise list the issues."
        elif workflow_type == "refactor":
            prompt = f"PROJECT_ROOT: {project_root}\nTASK: Verify that this refactoring preserves all existing functionality and doesn't introduce security issues.\n\nREFACTOR DESCRIPTION:\n{user_prompt}\n\nREFACTORED CODE:\n{code}\n\nReply exactly with 'PASSED' if the refactoring is correct. Otherwise list issues."
        else:  # feature or default
            prompt = f"PROJECT_ROOT: {project_root}\nTASK: Audit this code for security, best practices, and correctness.\n\nUSER INTENT:\n{user_prompt}\n\nIMPLEMENTATION DETAILS:\n{code}\n\nReply exactly with 'PASSED' at the beginning of your response if the code is correct. Otherwise list the issues with severity levels."

        try:
            result = await _run_acp_session(acp, "athena", prompt)
            elapsed = time.monotonic() - start
            if result.startswith("Error:"):
                logger.error(f"[workflow] {node_name} failed: {result}")
                return {"audit_result": result, "audit_passed": False, "errors": [f"athena: {result}"], "node_name": node_name, "status": "failed"}

            passed = result.strip().startswith("PASSED")
            logger.info(f"[workflow] {node_name} completed in {elapsed:.1f}s — {'PASSED' if passed else 'FAILED'}")
            return {"audit_result": result, "audit_passed": passed, "node_name": node_name}
        except Exception as e:
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

        workflow_type = state.get("workflow_type", "feature")
        project_root = state.get("project_root", "")
        user_prompt = state.get("user_prompt", "")

        if workflow_type == "bug-fix":
            prompt = f"PROJECT_ROOT: {project_root}\nTASK: Research and diagnose this bug. Find known issues, error explanations, Stack Overflow answers, and potential root causes.\nDepth: standard (10 links max).\n\nBUG DESCRIPTION:\n{user_prompt}"
        elif workflow_type == "security-review":
            prompt = f"PROJECT_ROOT: {project_root}\nTASK: Research security context for this project. Find CVEs for project dependencies, known vulnerabilities in the tech stack, and security advisories.\nDepth: standard (10 links max).\n\nSCOPE:\n{user_prompt}"
        elif workflow_type == "refactor":
            prompt = f"PROJECT_ROOT: {project_root}\nTASK: Research the impact of refactoring this code. Map all dependencies, identify breaking changes, and find relevant documentation for the components involved.\nDepth: standard (10 links max).\n\nREFACTOR SCOPE:\n{user_prompt}"
        else:  # feature or research
            prompt = f"PROJECT_ROOT: {project_root}\nTASK: Research the following topic.\nDepth: standard (10 links max).\n\nTOPIC:\n{user_prompt}"

        try:
            result = await _run_acp_session(acp, "etalides", prompt)
            elapsed = time.monotonic() - start
            if result.startswith("Error:"):
                logger.error(f"[workflow] {node_name} failed: {result}")
                return {"research": result, "errors": [f"etalides: {result}"], "node_name": node_name, "status": "failed"}
            logger.info(f"[workflow] {node_name} completed in {elapsed:.1f}s")
            return {"research": result, "node_name": node_name}
        except Exception as e:
            elapsed = time.monotonic() - start
            logger.error(f"[workflow] {node_name} failed: {e}")
            return {"research": "", "errors": [f"etalides: {str(e)}"], "node_name": node_name, "status": "failed"}
    return node_research

def should_terminate_on_error(state: WorkflowState) -> str:
    """Conditional edge: terminate early if any errors accumulated."""
    if state.get("errors") and len(state["errors"]) > 0:
        return "finalize"
    return "continue"

async def node_finalize(state: WorkflowState) -> dict:
    """Consolidation node — produces final output adapted to workflow type."""
    workflow_type = state.get("workflow_type", "feature")
    errors = state.get("errors", [])
    passed = state.get("audit_passed", False)
    cycles = state.get("review_cycles", 0)
    hitl_decisions = state.get("hitl_decisions", [])

    # Determine overall status
    if errors:
        status = f"Failed — {'; '.join(errors)}"
    elif passed:
        status = "Approved"
    elif workflow_type == "research":
        status = "Completed"
    elif workflow_type == "project-init":
        status = "Completed"
    else:
        status = "Rejected (Reached max review cycles without passing)"

    # Build response adapted to workflow type
    final = f"Workflow Completed.\nType: {workflow_type}\nStatus: {status}\nReview Cycles: {cycles}\n"

    if hitl_decisions:
        final += f"\n--- User Decisions ---\n" + "\n".join(f"  {d}" for d in hitl_decisions) + "\n"

    if state.get("research"):
        final += f"\n--- Research ---\n{state['research']}\n"

    if state.get("context"):
        final += f"\n--- Design ---\n{state['context']}\n"

    if state.get("code"):
        final += f"\n--- Implementation ---\n{state['code']}\n"

    if state.get("audit_result"):
        final += f"\n--- Audit ---\n{state['audit_result']}\n"

    return {"final_response": final, "status": "failed" if errors else "completed", "node_name": "finalize"}


def make_node_onboard(acp: ACPManager):
    async def node_onboard(state: WorkflowState) -> dict:
        """Ariadna node: initialize .eter/ project tracking."""
        node_name = "onboard"
        agent_name = "ariadna"
        start = time.monotonic()
        logger.info(f"[workflow] {node_name} started — agent={agent_name}")
        prompt = f"PROJECT_ROOT: {state.get('project_root', '')}\nTASK: Initialize project tracking. Project description:\n{state.get('user_prompt', '')}\n\nCreate the .eter/ directory structure with CURRENT.md (initial status) and LOG.md (first entry). Use your standard output format: Status, Blockers, Risks, Next Steps, Last Session."
        try:
            result = await _run_acp_session(acp, "ariadna", prompt)
            elapsed = time.monotonic() - start
            if result.startswith("Error:"):
                logger.error(f"[workflow] {node_name} failed: {result}")
                return {"context": result, "errors": [f"ariadna: {result}"], "node_name": node_name, "status": "failed"}
            logger.info(f"[workflow] {node_name} completed in {elapsed:.1f}s")
            return {"context": result, "node_name": node_name}
        except Exception as e:
            elapsed = time.monotonic() - start
            logger.error(f"[workflow] {node_name} failed: {e}")
            return {"context": "", "errors": [f"ariadna: {str(e)}"], "node_name": node_name, "status": "failed"}
    return node_onboard


def make_node_hitl(
    key: str,
    question: str,
    options: list[str],
    routing: dict[str, str],
    include_context_key: str | None = None,
):
    """Factory for Human-in-the-Loop review nodes.

    Args:
        key: Identifier for this HITL point (e.g., "design_review", "audit_review")
        question: Question to present to the user
        options: Available options (e.g., ["approve", "reject", "modify"])
        routing: Maps each option to the next node name (e.g., {"approve": "implement", "reject": "finalize"})
        include_context_key: Optional state key to include as context in the interrupt payload
    """
    async def hitl_node(state: WorkflowState) -> Command:
        interrupt_payload = {
            "question": question,
            "options": options,
            "workflow_type": state.get("workflow_type", ""),
            "node": key,
        }
        if include_context_key and state.get(include_context_key):
            interrupt_payload["context"] = state[include_context_key]

        decision = interrupt(interrupt_payload)

        goto = routing.get(decision, "finalize")
        logger.info(f"[workflow] HITL {key}: user chose '{decision}' → going to '{goto}'")

        update = {"hitl_decisions": [f"{key}:{decision}"]}

        # When user selects "modify", capture their feedback for the design node
        if decision == "modify":
            update["modification_feedback"] = interrupt_payload.get("context", "")

        return Command(
            update=update,
            goto=goto,
        )

    return hitl_node