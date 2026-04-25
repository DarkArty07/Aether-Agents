"""Predefined workflow definitions for Olympus."""

from langgraph.graph import StateGraph, START, END
from .state import WorkflowState
from .nodes import (
    make_node_design,
    make_node_implement,
    make_node_audit,
    make_node_research,
    make_node_onboard,
    make_node_hitl,
    node_finalize,
    should_terminate_on_error,
)
from ..acp_client import ACPManager

VALID_WORKFLOWS = [
    "project-init",
    "feature",
    "bug-fix",
    "security-review",
    "research",
    "refactor",
]


# ---------------------------------------------------------------------------
# Helper conditional-edge functions
# ---------------------------------------------------------------------------

def should_research(state: WorkflowState) -> str:
    """Route: include research branch only if needed (feature workflow)."""
    if state.get("needs_research", True):
        return "research"
    return "design"


def should_audit_pass(state: WorkflowState, fix_node: str = "implement") -> str:
    """Generic audit-pass router for bug-fix, refactor workflows.
    - errors → finalize
    - audit_passed → finalize
    - cycles < max → fix_node (loop)
    - cycles >= max → finalize
    """
    if state.get("errors") and len(state["errors"]) > 0:
        return "finalize"
    if state.get("audit_passed", False):
        return "finalize"
    cycles = state.get("review_cycles", 0)
    max_cycles = state.get("max_review_cycles", 2)
    if cycles < max_cycles:
        return fix_node
    return "finalize"


def should_reaudit_pass(state: WorkflowState, fix_node: str = "implement_fix") -> str:
    """Route for re-audit nodes (feature, security-review).
    - errors → finalize
    - audit_passed → finalize
    - cycles < max → fix_node
    - cycles >= max → finalize
    """
    if state.get("errors") and len(state["errors"]) > 0:
        return "finalize"
    if state.get("audit_passed", False):
        return "finalize"
    cycles = state.get("review_cycles", 0)
    if cycles < state.get("max_review_cycles", 2):
        return fix_node
    return "finalize"


# ---------------------------------------------------------------------------
# Workflow factory
# ---------------------------------------------------------------------------

def get_workflow(name: str, acp: ACPManager, checkpointer=None):
    """Factory builder for predefined workflows."""

    if name not in VALID_WORKFLOWS:
        raise ValueError(
            f"Unknown workflow: {name!r}. Valid: {VALID_WORKFLOWS}"
        )

    workflow = StateGraph(WorkflowState)

    # Pre-bind node factories
    node_design = make_node_design(acp)
    node_implement = make_node_implement(acp)
    node_audit = make_node_audit(acp)
    node_research = make_node_research(acp)
    node_onboard = make_node_onboard(acp)

    # ---- 1. project-init ------------------------------------------------
    if name == "project-init":
        workflow.add_node("onboard", node_onboard)
        workflow.add_node("finalize", node_finalize)

        workflow.add_edge(START, "onboard")
        workflow.add_edge("onboard", "finalize")
        workflow.add_edge("finalize", END)

    # ---- 2. feature -----------------------------------------------------
    elif name == "feature":
        # Regular nodes
        workflow.add_node("research", node_research)
        workflow.add_node("design", node_design)
        workflow.add_node("implement", node_implement)
        workflow.add_node("implement_fix", make_node_implement(acp))
        workflow.add_node("audit", node_audit)
        workflow.add_node("re_audit", make_node_audit(acp))
        workflow.add_node("finalize", node_finalize)

        # HITL nodes (return Command — no outgoing edges needed)
        research_review = make_node_hitl(
            "research_review",
            "Is the research sufficient to proceed?",
            ["approve", "reject"],
            {"approve": "design", "reject": "finalize"},
            include_context_key="research",
        )
        design_review = make_node_hitl(
            "design_review",
            "Do you approve this design? You may also request modifications.",
            ["approve", "reject", "modify"],
            {"approve": "implement", "reject": "finalize", "modify": "design"},
            include_context_key="context",
        )
        audit_review = make_node_hitl(
            "audit_review",
            "Review audit findings. Choose an action.",
            ["approve", "accept_risk", "reject"],
            {"approve": "implement_fix", "accept_risk": "finalize", "reject": "finalize"},
            include_context_key="audit_result",
        )
        workflow.add_node("research_review", research_review)
        workflow.add_node("design_review", design_review)
        workflow.add_node("audit_review", audit_review)

        # Edges — START routes via conditional (should_research)

        # START → conditional: needs_research?
        workflow.add_conditional_edges(
            START,
            should_research,
            {"research": "research", "design": "design"},
        )

        # research → error check → research_review
        workflow.add_conditional_edges(
            "research",
            should_terminate_on_error,
            {"continue": "research_review", "finalize": "finalize"},
        )

        # design → error check → design_review
        workflow.add_conditional_edges(
            "design",
            should_terminate_on_error,
            {"continue": "design_review", "finalize": "finalize"},
        )

        # implement → audit → audit_review
        workflow.add_edge("implement", "audit")
        workflow.add_edge("audit", "audit_review")

        # HITL audit_review → implement_fix → re_audit → conditional
        workflow.add_edge("implement_fix", "re_audit")
        workflow.add_conditional_edges(
            "re_audit",
            should_reaudit_pass,
            {"implement_fix": "implement_fix", "finalize": "finalize"},
        )

        workflow.add_edge("finalize", END)

    # ---- 3. bug-fix -----------------------------------------------------
    elif name == "bug-fix":
        workflow.add_node("research", node_research)
        workflow.add_node("implement", node_implement)
        workflow.add_node("audit", node_audit)
        workflow.add_node("finalize", node_finalize)

        # HITL
        diagnosis_review = make_node_hitl(
            "diagnosis_review",
            "Confirm the diagnosis before proceeding with the fix.",
            ["confirm", "reject"],
            {"confirm": "implement", "reject": "finalize"},
            include_context_key="research",
        )
        workflow.add_node("diagnosis_review", diagnosis_review)

        # Edges
        workflow.add_edge(START, "research")

        # research → error check → diagnosis_review
        workflow.add_conditional_edges(
            "research",
            should_terminate_on_error,
            {"continue": "diagnosis_review", "finalize": "finalize"},
        )

        # implement → audit → conditional
        workflow.add_edge("implement", "audit")
        workflow.add_conditional_edges(
            "audit",
            lambda state: should_audit_pass(state, fix_node="implement"),
            {"implement": "implement", "finalize": "finalize"},
        )

        workflow.add_edge("finalize", END)

    # ---- 4. security-review ---------------------------------------------
    elif name == "security-review":
        workflow.add_node("research", node_research)
        workflow.add_node("audit", node_audit)
        workflow.add_node("implement_fix", make_node_implement(acp))
        workflow.add_node("re_audit", make_node_audit(acp))
        workflow.add_node("finalize", node_finalize)

        # HITL
        findings_review = make_node_hitl(
            "findings_review",
            "Review security findings. Choose an action.",
            ["approve", "accept_risk", "reject"],
            {"approve": "implement_fix", "accept_risk": "finalize", "reject": "finalize"},
            include_context_key="audit_result",
        )
        workflow.add_node("findings_review", findings_review)

        # Edges
        workflow.add_edge(START, "research")

        # research → error check → audit
        workflow.add_conditional_edges(
            "research",
            should_terminate_on_error,
            {"continue": "audit", "finalize": "finalize"},
        )

        # audit → findings_review
        workflow.add_edge("audit", "findings_review")

        # implement_fix → re_audit → conditional
        workflow.add_edge("implement_fix", "re_audit")
        workflow.add_conditional_edges(
            "re_audit",
            should_reaudit_pass,
            {"implement_fix": "implement_fix", "finalize": "finalize"},
        )

        workflow.add_edge("finalize", END)

    # ---- 5. research ----------------------------------------------------
    elif name == "research":
        workflow.add_node("research", node_research)
        workflow.add_node("finalize", node_finalize)

        workflow.add_edge(START, "research")
        workflow.add_edge("research", "finalize")
        workflow.add_edge("finalize", END)

    # ---- 6. refactor ----------------------------------------------------
    elif name == "refactor":
        workflow.add_node("research", node_research)
        workflow.add_node("implement", node_implement)
        workflow.add_node("audit", node_audit)
        workflow.add_node("finalize", node_finalize)

        # HITL
        scope_review = make_node_hitl(
            "scope_review",
            "Approve the refactoring scope?",
            ["approve", "reject"],
            {"approve": "implement", "reject": "finalize"},
            include_context_key="research",
        )
        workflow.add_node("scope_review", scope_review)

        # Edges
        workflow.add_edge(START, "research")

        # research → error check → scope_review
        workflow.add_conditional_edges(
            "research",
            should_terminate_on_error,
            {"continue": "scope_review", "finalize": "finalize"},
        )

        # implement → audit → conditional
        workflow.add_edge("implement", "audit")
        workflow.add_conditional_edges(
            "audit",
            lambda state: should_audit_pass(state, fix_node="implement"),
            {"implement": "implement", "finalize": "finalize"},
        )

        workflow.add_edge("finalize", END)

    return workflow.compile(checkpointer=checkpointer)
