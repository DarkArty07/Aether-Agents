"""TypedDict definition for the Workflow State."""

from typing import Annotated, TypedDict
from langgraph.graph.message import add_messages

class WorkflowState(TypedDict):
    """State shared across all nodes in a Hermes orchestrated workflow."""
    user_prompt: str
    context: str
    code: str
    audit_result: str
    audit_passed: bool
    research: str
    messages: Annotated[list, add_messages]
    review_cycles: int
    max_review_cycles: int
    final_response: str
    project_root: str
    # CHANGE 4: New fields for error tracking and lifecycle management
    errors: Annotated[list[str], add_messages]  # Accumulated errors
    status: str          # "running" | "completed" | "failed" | "stalled"
    started_at: float    # timestamp (time.monotonic())
    node_name: str       # current node for logging
