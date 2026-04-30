"""Workflow Runner engine."""

import logging
import time
from typing import Dict, Any

from langgraph.types import Command
import uuid

from .definitions import get_workflow
from ..acp_client import ACPManager
from ..registry import OlympusRegistry

logger = logging.getLogger("olympus.workflows.runner")

class WorkflowRunner:
    def __init__(self, registry: OlympusRegistry, acp_manager: ACPManager, checkpointer):
        self.registry = registry
        self.acp_manager = acp_manager
        self.checkpointer = checkpointer

    async def run(
        self,
        workflow_name: str,
        prompt: str,
        project_root: str,
        max_review_cycles: int = 3,
        params: dict | None = None,
        thread_id: str | None = None,
        resume: str | None = None,
    ) -> Dict[str, Any]:
        """Execute a full workflow."""
        try:
            logger.info(f"Starting workflow: {workflow_name}")

            # 1. Get CompiledStateGraph with checkpointer
            app = get_workflow(workflow_name, self.acp_manager, self.checkpointer)

            # 2. Generate thread_id if not provided
            if thread_id is None:
                thread_id = str(uuid.uuid4())

            config = {"configurable": {"thread_id": thread_id}}

            # 3. Parse workflow-specific params
            if params is None:
                params = {}
            needs_research = params.get("needs_research", False)
            has_ui = params.get("has_ui", False)
            workflow_type = params.get("workflow_type", workflow_name)

            # 4. Resume from interrupt or run fresh
            if resume is not None:
                logger.info(f"Resuming workflow {workflow_name} with thread_id={thread_id}")
                final_state = await app.ainvoke(Command(resume=resume), config=config)
            else:
                # Build initial state
                initial_state = {
                    "user_prompt": prompt,
                    "project_root": project_root,
                    "max_review_cycles": max_review_cycles,
                    "review_cycles": 0,
                    "audit_passed": False,
                    "messages": [],
                    "errors": [],
                    "status": "running",
                    "started_at": time.time(),
                    "node_name": "",
                    "needs_research": needs_research,
                    "has_ui": has_ui,
                    "workflow_type": workflow_type,
                    "hitl_decisions": [],
                }

                final_state = await app.ainvoke(initial_state, config=config)

            # 4.5 Normalize final_state to dict if needed
            # LangGraph may return a State dict or a dict-like object
            if final_state is not None and not isinstance(final_state, dict):
                # Some LangGraph versions return a State object — convert to dict
                try:
                    final_state = dict(final_state)
                except (TypeError, ValueError):
                    logger.warning(f"Could not convert final_state to dict: {type(final_state)}")
                    final_state = {"final_response": str(final_state)}

            # 5. Check for interrupt
            if isinstance(final_state, dict) and "__interrupt__" in final_state:
                interrupt_data = final_state["__interrupt__"]
                # Convert Interrupt objects to JSON-serializable dicts.
                # LangGraph returns Interrupt objects (not plain dicts) inside the
                # __interrupt__ list. Each Interrupt has .value (the payload) and
                # .ns (namespace). We extract .value which is the dict we passed
                # to interrupt() in make_node_hitl.
                serializable_interrupt = []
                for entry in interrupt_data:
                    if hasattr(entry, "value"):
                        # LangGraph Interrupt object — extract .value
                        val = entry.value
                        if isinstance(val, dict):
                            serializable_interrupt.append(val)
                        else:
                            serializable_interrupt.append(str(val))
                    elif isinstance(entry, dict):
                        serializable_interrupt.append(entry)
                    else:
                        serializable_interrupt.append(str(entry))
                return {
                    "status": "interrupted",
                    "thread_id": thread_id,
                    "interrupt": serializable_interrupt,
                }

            # 6. Extract final response or fallback
            result = final_state.get("final_response")
            if not result:
                result = f"Workflow {workflow_name} completed but no final response was generated."

            return {"status": "success", "result": result, "thread_id": thread_id}

        except ValueError as ve:
            logger.error(f"Invalid workflow: {ve}")
            return {"status": "error", "error": str(ve)}
        except Exception as e:
            logger.exception(f"Workflow execution failed: {e}")
            return {"status": "error", "error": f"Workflow failed: {str(e)}"}
