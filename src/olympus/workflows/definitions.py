"""Predefined workflow definitions for Olympus."""

from langgraph.graph import StateGraph, START, END
from .state import WorkflowState
from .nodes import (
    make_node_design,
    make_node_implement,
    make_node_audit,
    make_node_research,
    node_finalize,
    should_retry_implementation,
    should_terminate_on_error,  # CHANGE 6: imported new function
)
from ..acp_client import ACPManager

def get_workflow(name: str, acp: ACPManager, checkpointer=None):
    """Factory builder for predefined workflows."""

    # Initialize the graph builder
    workflow = StateGraph(WorkflowState)

    # Pre-bind the ACP manager to our nodes
    node_design = make_node_design(acp)
    node_implement = make_node_implement(acp)
    node_audit = make_node_audit(acp)
    node_research = make_node_research(acp)

    if name == "dev_and_audit":
        workflow.add_node("design", node_design)
        workflow.add_node("implement", node_implement)
        workflow.add_node("audit", node_audit)
        workflow.add_node("finalize", node_finalize)

        workflow.add_edge(START, "design")
        # CHANGE 7: Error-check edge after design
        workflow.add_conditional_edges(
            "design",
            should_terminate_on_error,
            {"continue": "implement", "finalize": "finalize"}
        )
        workflow.add_edge("implement", "audit")

        workflow.add_conditional_edges(
            "audit",
            should_retry_implementation,
            {"implement": "implement", "finalize": "finalize"}
        )
        workflow.add_edge("finalize", END)

    elif name == "research_and_implement":
        # Simplified linear workflow without audit
        workflow.add_node("research", node_research)
        workflow.add_node("design", node_design)
        workflow.add_node("implement", node_implement)
        workflow.add_node("finalize", node_finalize)

        workflow.add_edge(START, "research")
        # CHANGE 7: Error-check edges after research and design
        workflow.add_conditional_edges(
            "research",
            should_terminate_on_error,
            {"continue": "design", "finalize": "finalize"}
        )
        workflow.add_conditional_edges(
            "design",
            should_terminate_on_error,
            {"continue": "implement", "finalize": "finalize"}
        )
        workflow.add_edge("implement", "finalize")
        workflow.add_edge("finalize", END)

    elif name == "full_pipeline":
        # Research -> Design -> Implement <-> Audit -> Finalize
        workflow.add_node("research", node_research)
        workflow.add_node("design", node_design)
        workflow.add_node("implement", node_implement)
        workflow.add_node("audit", node_audit)
        workflow.add_node("finalize", node_finalize)

        workflow.add_edge(START, "research")
        # CHANGE 7: Error-check edges after research and design
        workflow.add_conditional_edges(
            "research",
            should_terminate_on_error,
            {"continue": "design", "finalize": "finalize"}
        )
        workflow.add_conditional_edges(
            "design",
            should_terminate_on_error,
            {"continue": "implement", "finalize": "finalize"}
        )
        workflow.add_edge("implement", "audit")

        workflow.add_conditional_edges(
            "audit",
            should_retry_implementation,
            {"implement": "implement", "finalize": "finalize"}
        )
        workflow.add_edge("finalize", END)

    else:
        raise ValueError(f"Unknown workflow name: {name}")

    return workflow.compile(checkpointer=checkpointer)
