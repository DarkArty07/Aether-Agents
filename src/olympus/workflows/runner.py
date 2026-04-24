"""Workflow Runner engine."""

import logging
import time
from typing import Dict, Any

from .definitions import get_workflow
from ..acp_client import ACPManager
from ..registry import OlympusRegistry

logger = logging.getLogger("olympus.workflows.runner")

class WorkflowRunner:
    def __init__(self, registry: OlympusRegistry, acp_manager: ACPManager):
        self.registry = registry
        self.acp_manager = acp_manager

    async def run(
        self,
        workflow_name: str,
        prompt: str,
        project_root: str,
        max_review_cycles: int = 3,
    ) -> Dict[str, Any]:
        """Execute a full workflow."""
        try:
            logger.info(f"Starting workflow: {workflow_name}")

            # 1. Get CompiledStateGraph
            app = get_workflow(workflow_name, self.acp_manager)

            # 2. Build initial state
            # CHANGE 4: Added errors, status, started_at, node_name fields
            initial_state = {
                "user_prompt": prompt,
                "project_root": project_root,
                "max_review_cycles": max_review_cycles,
                "review_cycles": 0,
                "audit_passed": False,
                "messages": [],
                "errors": [],
                "status": "running",
                "started_at": time.monotonic(),
                "node_name": "",
            }

            # 3. Run the graph
            final_state = await app.ainvoke(initial_state)

            # 4. Extract final response or fallback
            result = final_state.get("final_response")
            if not result:
                result = f"Workflow {workflow_name} completed but no final response was generated."

            return {"status": "success", "result": result}

        except ValueError as ve:
            logger.error(f"Invalid workflow: {ve}")
            return {"status": "error", "error": str(ve)}
        except Exception as e:
            logger.exception(f"Workflow execution failed: {e}")
            return {"status": "error", "error": f"Workflow failed: {str(e)}"}
