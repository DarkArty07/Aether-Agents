"""LangGraph nodes that execute Daimon operations via ACP."""

import asyncio
import logging
from .state import WorkflowState
from ..acp_client import ACPManager
from ..registry import SessionStatus

logger = logging.getLogger("olympus.workflows.nodes")

async def _run_acp_session(acp: ACPManager, agent_name: str, prompt: str) -> str:
    """Helper to run a full ACP session with a specific agent and wait for completion."""
    try:
        session = await acp.open_session(agent_name)
        if not session:
            return f"Error: Failed to open session with {agent_name}"
            
        # open_session returns a SessionState; use its session_id for send_prompt
        await acp.send_prompt(session.session_id, prompt)
        
        # session is already the SessionState object from open_session
        # Wait for the session to complete
        await session.completion_event.wait()
        if session.status == SessionStatus.DONE:
            return session.final_response or ""
        elif session.status == SessionStatus.ERROR:
            return f"Error: {session.final_response}"
        return "Error: Session tracking failed"
    except Exception as e:
        logger.error(f"ACP Session failed for {agent_name}: {e}")
        return f"Error: {str(e)}"

# A hack to pass the acp parameter correctly:
# LangGraph state nodes only take ONE argument (state). We can pass acp via partial 
# or via closure. Let's make node factories that receive ACPManager and return the async func.

def make_node_design(acp: ACPManager):
    async def node_design(state: WorkflowState) -> dict:
        """Daedalus node: generates design/plan based on user prompt."""
        prompt = f"PROJECT_ROOT: {state.get('project_root', '')}\\nTASK: Design the following feature.\\n{state.get('user_prompt', '')}"
        result = await _run_acp_session(acp, "daedalus", prompt)
        return {"context": result}
    return node_design

def make_node_implement(acp: ACPManager):
    async def node_implement(state: WorkflowState) -> dict:
        """Hefesto node: implements code based on design and feedback."""
        prompt = f"PROJECT_ROOT: {state.get('project_root', '')}\\nTASK: Implement the feature.\\n"
        if state.get("context"):
            prompt += f"\\nDESIGN CONTEXT:\\n{state['context']}\\n"
        if state.get("audit_result") and not state.get("audit_passed"):
            prompt += f"\\nAUDIT FEEDBACK (Must fix these issues):\\n{state['audit_result']}\\n"
        else:
            prompt += f"\\nUSER PROMPT:\\n{state.get('user_prompt', '')}\\n"
            
        result = await _run_acp_session(acp, "hefesto", prompt)
        
        # Increment review cycle if coming from an audit failure
        cycles = state.get("review_cycles", 0)
        if state.get("audit_result") and not state.get("audit_passed"):
            cycles += 1
            
        return {"code": result, "review_cycles": cycles}
    return node_implement

def make_node_audit(acp: ACPManager):
    async def node_audit(state: WorkflowState) -> dict:
        """Athena node: audits the code."""
        prompt = f"PROJECT_ROOT: {state.get('project_root', '')}\\nTASK: Audit this code for security, best practices, and correctness.\\n"
        prompt += f"USER INTENT:\\n{state.get('user_prompt', '')}\\n"
        prompt += f"IMPLEMENTATION DETAILS:\\n{state.get('code', '')}\\n"
        prompt += "Reply exactly with 'PASSED' at the beginning of your response if the code is correct. Otherwise list the issues."
        
        result = await _run_acp_session(acp, "athena", prompt)
        
        passed = result.strip().startswith("PASSED")
        return {"audit_result": result, "audit_passed": passed}
    return node_audit

def make_node_research(acp: ACPManager):
    async def node_research(state: WorkflowState) -> dict:
        """Etalides node: investigates a topic."""
        prompt = f"PROJECT_ROOT: {state.get('project_root', '')}\\nTASK: Research the following topic.\\n{state.get('user_prompt', '')}"
        result = await _run_acp_session(acp, "etalides", prompt)
        return {"research": result}
    return node_research

def should_retry_implementation(state: WorkflowState) -> str:
    """Conditional edge: retry if audit failed and under max cycles."""
    if not state.get("audit_passed", False) and state.get("review_cycles", 0) < state.get("max_review_cycles", 3):
        return "implement"
    return "finalize"

async def node_finalize(state: WorkflowState) -> dict:
    """Consolidation node."""
    cycles = state.get("review_cycles", 0)
    passed = state.get("audit_passed", False)
    
    status = "Approved" if passed else "Rejected (Reached max review cycles without passing)"
    
    final = f"Workflow Completed.\\nStatus: {status}\\nReview Cycles: {cycles}\\n"
    if state.get("research"):
        final += f"\\n--- Research ---\\n{state['research']}\\n"
    final += f"\\n--- Implementation ---\\n{state.get('code', 'None')}\\n"
    if state.get("audit_result"):
        final += f"\\n--- Final Audit ---\\n{state['audit_result']}\\n"
        
    return {"final_response": final}
