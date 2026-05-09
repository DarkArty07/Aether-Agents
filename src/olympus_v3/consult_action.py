"""Olympus v3 Consult Action — handles the consult MCP tool using ACP delegation.

Implements the consulting workflow where Daimons (Daedalus, Athena, Ictinus) act as
consultants: they review plans, provide enrichments, sign contracts, and refuse tasks
outside their scope.

Actions: start, run, sign, add_agent, status, complete.

The `run` and `sign` actions delegate to Daimons via ACPManager.delegate()
(spawn → message → auto-poll loop → close).  Response text is read from SQLite
via OlympusDB.get_latest_turn() after delegation completes.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from .acp_manager import ACPManager
from .config_loader import get_config
from .consulting_db import get_consulting_db

logger = logging.getLogger("olympus_v3.consult_action")

# Poll/stall constants — used as defaults for ACPManager.delegate()
POLL_INTERVAL = 15
STALL_TIMEOUT = 1200  # Total timeout for delegation (seconds)

# ---------------------------------------------------------------------------
# Consultation prompts — parameterized by role
# ---------------------------------------------------------------------------

# Agent hierarchy — Level 0: Orchestrator, Level 1: Consultants, Level 2: Utility
ROLE_LEVELS = {
    "hermes": 0,       # Orchestrator — max authority, never a consultant
    "daedalus": 1,     # Consultant — enriches, plans, signs tasks
    "athena": 1,       # Consultant — enriches, plans, signs tasks
    "ictinus": 1,      # Consultant — enriches, plans, signs tasks (Backend Architect)
    "etalides": 2,     # Utility — executes research, no consulting
    "hefesto": 2,      # Utility — executes implementation, no consulting
    "ariadna": 2,      # Utility — executes coordination, no consulting
}

ROLE_LABELS: dict[str, str] = {
    "daedalus": "frontend-developer",
    "athena": "auditor",
    "ictinus": "backend-architect",
}

ROLE_DESCRIPTIONS: dict[str, str] = {
    "daedalus": "Frontend developer and UI designer specializing in design systems, component architecture, visual tokens, performance optimization, accessibility, and developer handoff",
    "athena": "Quality and security auditor focused on edge cases, vulnerabilities, and acceptance criteria",
    "ictinus": "Backend architect specializing in scalable system design, database architecture, API development, cloud infrastructure, and security-first engineering",
}

CONSULT_PROMPT_TEMPLATE = """ROLE: You are a {role} — {role_description}. You are a Level 1 Consultant in the Aether Agents hierarchy. Your job is NOT to implement changes — it is to INVESTIGATE and OPINIONATE.

INVESTIGATION INSTRUCTIONS:
- USE your tools (read, grep, find, ls) to investigate the project at {project_root}
- Read relevant files, search for references, verify dependencies, check configs
- Your opinion must be GROUNDED in the actual codebase, not assumptions
- Diagnose thoroughly before giving your opinion

CRITICAL RESTRICTION — READ-ONLY MODE:
- You are in READ-ONLY mode during this consultation
- Do NOT modify, create, or delete any files
- Do NOT run commands that change state (mkdir, rm, pip install, npm, git commit, etc.)
- You may ONLY read, search, and diagnose
- Violating this restriction risks corrupting the project

RESPOND IN NATURAL LANGUAGE — respond clearly and organized. You do NOT need to use JSON.
IMPORTANT: Put your COMPLETE response in your text output. Your thinking process is for your internal reasoning only — the visible text output is what will be used as your response. Do not put your analysis only in your thinking — include all findings, enrichments, and suggestions in your text output.

Cover these areas in your response:
1. ENRICHMENTS: What problems, risks, or missed opportunities do you see? What could fail? What does nobody ask?
2. TASKS YOU WOULD SIGN: Which tasks can you take on? What would you deliver? What acceptance criteria apply?
3. TASKS YOU WOULD REFUSE: Which tasks are outside your scope? Why?
4. PLAN SUGGESTIONS: Any improvements to the overall plan?

PLAN:
{plan}

CONTEXT:
{context}"""

SIGNING_PROMPT_TEMPLATE = """Confirm your commitment to the following tasks per the final plan.

CRITICAL RESTRICTION — READ-ONLY MODE:
- You are still in READ-ONLY mode
- Do NOT modify, create, or delete any files
- You may ONLY read and investigate the project at {project_root}

FINAL PLAN:
{plan}

YOUR TASKS:
{tasks}

In your response, confirm:
1. Which tasks you sign — and the deliverables and acceptance criteria for each.
2. Any tasks you cannot sign — and why.
3. Any enrichments, risks, or suggestions you want to add.

Respond in natural language, clearly and organized. You do NOT need to use JSON."""

# Valid consultant agents — only those with role descriptions
VALID_CONSULTANTS = {name for name, level in ROLE_LEVELS.items() if level == 1}


# ---------------------------------------------------------------------------
# JSON response parsing
# ---------------------------------------------------------------------------

def _extract_json_from_response(raw: str) -> str:
    """Extract JSON content from a Daimon response.

    The Daimon may wrap its JSON in markdown code fences or add preamble text.
    This function tries, in order:
    1. ```json ... ``` blocks
    2. ``` ... ``` blocks (generic code fence)
    3. First { to last } brace matching (greedy)

    Returns the extracted JSON string, or the original text if no JSON structure is found.
    """
    import re

    text = raw.strip()

    # 1. Check for ```json ... ``` blocks
    json_fence_match = re.search(r"```json\s*\n(.*?)```", text, re.DOTALL)
    if json_fence_match:
        return json_fence_match.group(1).strip()

    # 2. Check for ``` ... ``` blocks (without language tag)
    plain_fence_match = re.search(r"```\s*\n(.*?)```", text, re.DOTALL)
    if plain_fence_match:
        return plain_fence_match.group(1).strip()

    # 3. Find first { and last } — greedy match for the outermost JSON object
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace > first_brace:
        return text[first_brace : last_brace + 1]

    # No JSON structure found — return as-is
    return text


def _parse_consultation_response(raw: str) -> dict[str, Any]:
    """Parse a Daimon's consultation response — best-effort JSON with raw-text fallback.

    Tries to extract and parse JSON first. If JSON is valid, fills structured
    fields and sets ``_parsed`` to True.  If no valid JSON is found, the full
    raw text is preserved in ``plan_suggestion`` and structured fields are left
    empty; ``_parsed`` is set to False.

    The ``raw_response`` field is ALWAYS included so Hermes can see the
    original text regardless of parse outcome.
    """
    text = _extract_json_from_response(raw)

    try:
        parsed = json.loads(text)
        enrichments = parsed.get("enrichments", [])
        contract = parsed.get("contract", {})
        refusals = contract.get("refusals", []) if isinstance(contract, dict) else []
        plan_suggestion = parsed.get("plan_suggestion", "")

        return {
            "enrichments": enrichments,
            "contract": contract,
            "refusals": refusals,
            "plan_suggestion": plan_suggestion,
            "raw_response": raw,
            "_parsed": True,
        }
    except (json.JSONDecodeError, ValueError) as e:
        logger.info(f"Consultation response not JSON — preserving raw text: {e}")
        return {
            "enrichments": [],
            "contract": {},
            "refusals": [],
            "plan_suggestion": raw,
            "raw_response": raw,
            "_parsed": False,
        }


def _parse_signing_response(raw: str) -> dict[str, Any]:
    """Parse a Daimon's signing response. Same logic as consultation parse."""
    return _parse_consultation_response(raw)


# ---------------------------------------------------------------------------
# Helper: extract response text from delegation result
# ---------------------------------------------------------------------------

def _extract_response_text(result: dict[str, Any]) -> str:
    """Extract response text from an ACPManager.delegate() result dict.

    Tries multiple keys in priority order:
    1. last_turn (from OlympusDB.get_session_progress)
    2. response (convenience key from _build_response)
    3. accumulated text from the progress dict

    Falls back to an error message if no text is found.
    """
    # Priority: last_turn > response > any text content
    text = result.get("last_turn") or result.get("response") or ""
    if isinstance(text, str) and text.strip():
        return text
    return "Error: Agent returned no response"


# ---------------------------------------------------------------------------
# Action handlers
# ---------------------------------------------------------------------------

async def _action_start(
    plan: str,
    agents: list[str],
    context: str | None = None,
    project_root: str | None = None,
) -> dict[str, Any]:
    """Create a new consulting session."""
    if not plan:
        return {"error": "plan is required for action=start"}
    if not agents:
        return {"error": "agents is required for action=start"}

    # Validate agents
    invalid = [a for a in agents if a not in VALID_CONSULTANTS]
    if invalid:
        return {
            "error": f"Invalid consultant agents: {invalid}. Valid: {sorted(VALID_CONSULTANTS)}"
        }

    config = get_config()
    pr = project_root or str(config.aether_home)
    db = await get_consulting_db(pr)
    session = await db.create_session(
        plan=plan,
        agents=agents,
        context=context,
        project_root=pr,
    )

    # If DB returned an error, propagate it
    if isinstance(session, dict) and "error" in session:
        return session

    return {
        "session_id": session["id"],
        "status": "planning",
        "agents": agents,
        "plan_version": 1,
    }


async def _action_run(
    session_id: str,
    agent: str,
    manager: ACPManager,
    project_root: str | None = None,
) -> dict[str, Any]:
    """Run a consultation with a specific agent via ACP delegation.

    Uses ACPManager.delegate() to spawn the agent, send the consultation
    prompt, and poll until completion.  The response text is extracted from
    the SQLite database (via the delegation result) rather than from an
    in-memory buffer.
    """
    if not session_id:
        return {"error": "session_id is required for action=run"}
    if not agent:
        return {"error": "agent is required for action=run"}
    if agent not in ROLE_DESCRIPTIONS:
        return {
            "error": f"Invalid consultant agent: {agent}. Valid: {sorted(VALID_CONSULTANTS)}"
        }

    # Load session from DB
    config = get_config()
    pr = project_root or str(config.aether_home)
    db = await get_consulting_db(pr)
    session = await db.get_session(session_id)
    if session is None:
        return {"error": f"Session not found: {session_id}"}
    if isinstance(session, dict) and "error" in session:
        return session

    # Verify agent is in session
    if agent not in session["agents"]:
        return {"error": f"Agent {agent} is not part of session {session_id}"}

    # Check if already consulted
    existing = await db.get_consultation(session_id, agent)
    if existing and existing["status"] == "consulted":
        return {
            "error": f"Agent {agent} already consulted for session {session_id}",
            "existing_consultation": existing,
        }

    # Build consultation prompt from template
    role = ROLE_LABELS.get(agent, agent)
    prompt_text = CONSULT_PROMPT_TEMPLATE.format(
        role=role,
        role_description=ROLE_DESCRIPTIONS.get(agent, agent),
        project_root=pr,
        plan=session["plan"],
        context=session["context"] or "No additional context provided.",
    )

    # Delegate to the Daimon via ACP
    try:
        result = await manager.delegate(
            agent_name=agent,
            prompt=prompt_text,
            project_root=pr,
            poll_interval=POLL_INTERVAL,
            timeout=STALL_TIMEOUT,
        )
    except Exception as e:
        logger.error("[consult] delegation failed for %s: %s", agent, e)
        return {"error": f"Failed to consult {agent}: {e!s}"}

    # Check for timeout/stall in delegation result
    if result.get("timed_out"):
        return {"error": f"Agent {agent} timed out during consultation"}
    if result.get("stalled"):
        return {"error": f"Agent {agent} stalled during consultation"}

    # Extract response text from the delegation result
    raw_response = _extract_response_text(result)

    # Parse the response
    parsed = _parse_consultation_response(raw_response)

    # Save to DB
    consultation = await db.save_consultation(
        session_id=session_id,
        agent=agent,
        role=role,
        enrichments=parsed.get("enrichments", []),
        contract=parsed.get("contract", {}),
        refusals=parsed.get("refusals", []),
        plan_suggestion=parsed.get("plan_suggestion", ""),
        raw_response=raw_response,
    )

    # If DB returned an error, propagate it
    if isinstance(consultation, dict) and "error" in consultation:
        return consultation

    # Create tasks from the contract
    contract = parsed.get("contract", {})
    tasks_data = contract.get("tasks", []) if isinstance(contract, dict) else []
    created_tasks = []
    for task in tasks_data:
        task_id = task.get("task_id", f"task_{len(created_tasks) + 1}")
        t = await db.create_task(
            session_id=session_id,
            task_id=task_id,
            description=task.get("description", ""),
            assigned_agent=agent,
            acceptance_criteria=task.get("acceptance_criteria", []),
            complexity=task.get("complexity"),
            dependencies=task.get("dependencies", []),
        )
        created_tasks.append(t)

    return {
        "session_id": session_id,
        "agent": agent,
        "role": role,
        "status": "consulted",
        "enrichments": parsed.get("enrichments", []),
        "contract": contract,
        "refusals": parsed.get("refusals", []),
        "plan_suggestion": parsed.get("plan_suggestion", ""),
        "raw_response": raw_response,
        "tasks_created": len(created_tasks),
        "parsed_successfully": parsed.get("_parsed", True),
    }


async def _action_sign(
    session_id: str,
    agent: str,
    tasks: list[dict] | None = None,
    manager: ACPManager | None = None,
    project_root: str | None = None,
) -> dict[str, Any]:
    """Get an agent to sign a final contract for specified tasks via ACP delegation.

    Uses ACPManager.delegate() to send the signing prompt and poll until
    completion.  Response text is extracted from the delegation result.
    """
    if not session_id:
        return {"error": "session_id is required for action=sign"}
    if not agent:
        return {"error": "agent is required for action=sign"}
    if agent not in VALID_CONSULTANTS:
        return {
            "error": f"Invalid consultant agent: {agent}. Valid: {sorted(VALID_CONSULTANTS)}"
        }

    config = get_config()
    pr = project_root or str(config.aether_home)
    db = await get_consulting_db(pr)
    session = await db.get_session(session_id)
    if session is None:
        return {"error": f"Session not found: {session_id}"}
    if isinstance(session, dict) and "error" in session:
        return session

    # Verify agent is in session
    if agent not in session["agents"]:
        return {"error": f"Agent {agent} is not part of session {session_id}"}

    # Check agent has consulted
    consultation = await db.get_consultation(session_id, agent)
    if consultation is None or consultation["status"] not in ("consulted", "pending"):
        if consultation is None:
            return {
                "error": f"Agent {agent} must be consulted before signing. No consultation found."
            }
        return {
            "error": f"Agent {agent} must be consulted before signing. Current status: {consultation['status']}"
        }

    # Build signing prompt
    tasks_text = json.dumps(tasks or [], indent=2)
    prompt_text = SIGNING_PROMPT_TEMPLATE.format(
        plan=session["plan"],
        tasks=tasks_text,
        project_root=pr,
    )

    # Delegate to the Daimon via ACP
    if manager is None:
        return {"error": "ACP manager not available for signing delegation"}

    try:
        result = await manager.delegate(
            agent_name=agent,
            prompt=prompt_text,
            project_root=pr,
            poll_interval=POLL_INTERVAL,
            timeout=STALL_TIMEOUT,
        )
    except Exception as e:
        logger.error("[consult] signing delegation failed for %s: %s", agent, e)
        return {"error": f"Failed to get signing from {agent}: {e!s}"}

    # Check for timeout/stall
    if result.get("timed_out"):
        return {"error": f"Agent {agent} timed out during signing"}
    if result.get("stalled"):
        return {"error": f"Agent {agent} stalled during signing"}

    # Extract response text
    raw_response = _extract_response_text(result)

    # Parse the signing response
    parsed = _parse_signing_response(raw_response)

    # Update consultation status in DB
    contract = parsed.get("contract", {})
    consultation_update = await db.update_consultation_status(
        session_id=session_id,
        agent=agent,
        status="signed",
        contract=contract,
    )

    # Check if all agents have signed
    session_status = await db.get_session_status(session_id)
    all_signed = False
    if session_status and "consultations" in session_status:
        all_signed = all(
            c["status"] == "signed"
            for c in session_status.get("consultations", [])
        )
        if all_signed:
            await db.update_session(session_id, status="signing")

    return {
        "session_id": session_id,
        "agent": agent,
        "status": "signed",
        "contract": contract,
        "all_agents_signed": all_signed,
        "raw_response": raw_response,
        "parsed_successfully": parsed.get("_parsed", True),
    }


async def _action_add_agent(
    session_id: str,
    new_agent: str,
    role: str | None = None,
    reason: str | None = None,
    project_root: str | None = None,
) -> dict[str, Any]:
    """Add a new agent to an ongoing consulting session."""
    if not session_id:
        return {"error": "session_id is required for action=add_agent"}
    if not new_agent:
        return {"error": "new_agent is required for action=add_agent"}
    if new_agent not in VALID_CONSULTANTS:
        return {
            "error": f"Invalid consultant agent: {new_agent}. Valid: {sorted(VALID_CONSULTANTS)}"
        }

    # Determine role from ROLE_LABELS if not provided
    if role is None:
        role = ROLE_LABELS.get(new_agent, new_agent)

    config = get_config()
    pr = project_root or str(config.aether_home)
    db = await get_consulting_db(pr)
    result = await db.add_agent(session_id, new_agent, role, reason)
    if result is None:
        return {"error": f"Session not found: {session_id}"}
    if isinstance(result, dict) and "error" in result:
        return result

    return {
        "session_id": session_id,
        "agent": new_agent,
        "role": role,
        "reason": reason or "",
        "status": "added",
    }


async def _action_status(
    session_id: str,
    project_root: str | None = None,
) -> dict[str, Any]:
    """Get the full status of a consulting session."""
    if not session_id:
        return {"error": "session_id is required for action=status"}

    config = get_config()
    pr = project_root or str(config.aether_home)
    db = await get_consulting_db(pr)
    status = await db.get_session_status(session_id)
    if status is None:
        return {"error": f"Session not found: {session_id}"}
    if isinstance(status, dict) and "error" in status:
        return status
    return status


async def _action_complete(
    session_id: str,
    project_root: str | None = None,
) -> dict[str, Any]:
    """Close a consulting session."""
    if not session_id:
        return {"error": "session_id is required for action=complete"}

    config = get_config()
    pr = project_root or str(config.aether_home)
    db = await get_consulting_db(pr)
    result = await db.complete_session(session_id)
    if result is None:
        return {"error": f"Session not found: {session_id}"}
    if isinstance(result, dict) and "error" in result:
        return result
    return result


# ---------------------------------------------------------------------------
# Main handler
# ---------------------------------------------------------------------------

async def handle_consult_action(
    action: str,
    manager: ACPManager,
    session_id: str | None = None,
    plan: str | None = None,
    agents: list | None = None,
    context: str | None = None,
    project_root: str | None = None,
    agent: str | None = None,
    tasks: list | None = None,
    new_agent: str | None = None,
    role: str | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    """Main handler for the consult MCP tool.

    Routes to the appropriate action handler based on the action parameter.
    Returns a dict — never raises exceptions to the MCP caller.

    Args:
        action: The consult action to execute.
        manager: The ACPManager instance for Daimon delegation.
        session_id: Session ID for actions that require it.
        plan: Plan text for start action.
        agents: Agent list for start action.
        context: Additional context for start action.
        project_root: Project root path.
        agent: Agent name for run/sign actions.
        tasks: Task list for sign action.
        new_agent: Agent name for add_agent action.
        role: Role for add_agent action.
        reason: Reason for add_agent action.
    """
    try:
        if action == "start":
            return await _action_start(
                plan=plan or "",
                agents=agents or [],
                context=context,
                project_root=project_root,
            )

        elif action == "run":
            # Validate agent before delegation
            if agent and agent not in ROLE_DESCRIPTIONS:
                return {
                    "error": f"Invalid consultant agent: {agent}. Valid: {sorted(VALID_CONSULTANTS)}"
                }
            return await _action_run(
                session_id=session_id or "",
                agent=agent or "",
                manager=manager,
                project_root=project_root,
            )

        elif action == "sign":
            # Validate agent before delegation
            if agent and agent not in VALID_CONSULTANTS:
                return {
                    "error": f"Invalid consultant agent: {agent}. Valid: {sorted(VALID_CONSULTANTS)}"
                }
            return await _action_sign(
                session_id=session_id or "",
                agent=agent or "",
                tasks=tasks,
                manager=manager,
                project_root=project_root,
            )

        elif action == "add_agent":
            return await _action_add_agent(
                session_id=session_id or "",
                new_agent=new_agent or "",
                role=role,
                reason=reason,
                project_root=project_root,
            )

        elif action == "status":
            return await _action_status(
                session_id=session_id or "",
                project_root=project_root,
            )

        elif action == "complete":
            return await _action_complete(
                session_id=session_id or "",
                project_root=project_root,
            )

        else:
            return {
                "error": f"Unknown action: {action}. Valid: start, run, sign, add_agent, status, complete"
            }

    except Exception as e:
        logger.exception(f"Unhandled error in consult action '{action}': {e}")
        return {"error": f"Internal error in consult/{action}: {e!s}"}