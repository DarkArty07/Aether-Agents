"""Prompt templates for Olympus workflow nodes.

Each agent gets a different prompt depending on the workflow type.
This separates prompt logic from node logic, making it easy to adjust
messages without touching the node code.
"""

# --- Research prompts (Etalides) ---

RESEARCH_PROMPTS = {
    "feature": (
        "PROJECT_ROOT: {project_root}\n"
        "TASK: Research the technical context needed to implement this feature. "
        "Find relevant APIs, libraries, patterns, and any gotchas.\n"
        "Depth: standard (10 links max).\n\n"
        "FEATURE DESCRIPTION:\n{user_prompt}"
    ),
    "bug-fix": (
        "PROJECT_ROOT: {project_root}\n"
        "TASK: Research and diagnose this bug. Find known issues, error explanations, "
        "Stack Overflow answers, and potential root causes.\n"
        "Depth: standard (10 links max).\n\n"
        "BUG DESCRIPTION:\n{user_prompt}"
    ),
    "security-review": (
        "PROJECT_ROOT: {project_root}\n"
        "TASK: Research security context for this project. Find CVEs for project dependencies, "
        "known vulnerabilities in the tech stack, and security advisories.\n"
        "Depth: standard (10 links max).\n\n"
        "SCOPE:\n{user_prompt}"
    ),
    "research": (
        "PROJECT_ROOT: {project_root}\n"
        "TASK: Research the following topic.\n"
        "Depth: standard (10 links max).\n\n"
        "TOPIC:\n{user_prompt}"
    ),
    "refactor": (
        "PROJECT_ROOT: {project_root}\n"
        "TASK: Research the impact of refactoring this code. Map all dependencies, "
        "identify breaking changes, and find relevant documentation for the components involved.\n"
        "Depth: standard (10 links max).\n\n"
        "REFACTOR SCOPE:\n{user_prompt}"
    ),
}

# --- Design prompts (Daedalus) ---

DESIGN_PROMPTS = {
    "feature_ui": (
        "PROJECT_ROOT: {project_root}\n"
        "TASK: Design the user experience for this feature.\n"
        "Produce a user flow (minimum steps) and a layout specification "
        "(visual hierarchy, component list, states, accessibility notes).\n\n"
        "FEATURE DESCRIPTION:\n{user_prompt}\n\n"
        "RESEARCH CONTEXT:\n{research}"
    ),
    "feature_internal": (
        "PROJECT_ROOT: {project_root}\n"
        "TASK: Design the internal flow and component specification for this feature.\n"
        "This is a backend/internal feature — produce a data flow and component interaction spec "
        "that a developer can implement from.\n\n"
        "FEATURE DESCRIPTION:\n{user_prompt}\n\n"
        "RESEARCH CONTEXT:\n{research}"
    ),
}

# --- Implement prompts (Hefesto) ---

IMPLEMENT_PROMPTS = {
    "feature": (
        "PROJECT_ROOT: {project_root}\n"
        "TASK: Implement the feature.\n\n"
        "DESIGN CONTEXT:\n{context}\n\n"
        "USER PROMPT:\n{user_prompt}"
    ),
    "feature_from_audit": (
        "PROJECT_ROOT: {project_root}\n"
        "TASK: Fix the security issues found in the audit.\n\n"
        "AUDIT FEEDBACK (Must fix these issues):\n{audit_result}\n\n"
        "ORIGINAL IMPLEMENTATION:\n{code}"
    ),
    "bug-fix": (
        "PROJECT_ROOT: {project_root}\n"
        "TASK: Fix this bug based on the diagnosis.\n\n"
        "DIAGNOSIS:\n{research}\n\n"
        "BUG DESCRIPTION:\n{user_prompt}"
    ),
    "bug-fix_from_audit": (
        "PROJECT_ROOT: {project_root}\n"
        "TASK: Refine the bug fix based on the security review.\n\n"
        "AUDIT FEEDBACK:\n{audit_result}\n\n"
        "CURRENT FIX:\n{code}"
    ),
    "security-fix": (
        "PROJECT_ROOT: {project_root}\n"
        "TASK: Fix the following security issues.\n\n"
        "SECURITY FINDINGS:\n{audit_result}\n\n"
        "ORIGINAL CODE:\n{code}"
    ),
    "security-fix_from_audit": (
        "PROJECT_ROOT: {project_root}\n"
        "TASK: Refine the security fix based on re-review.\n\n"
        "RE-AUDIT FEEDBACK:\n{audit_result}\n\n"
        "CURRENT FIX:\n{code}"
    ),
    "refactor": (
        "PROJECT_ROOT: {project_root}\n"
        "TASK: Refactor the following code. Preserve all existing functionality.\n\n"
        "IMPACT MAP:\n{research}\n\n"
        "REFACTOR DESCRIPTION:\n{user_prompt}"
    ),
    "refactor_from_audit": (
        "PROJECT_ROOT: {project_root}\n"
        "TASK: Refine the refactoring based on security review.\n\n"
        "AUDIT FEEDBACK:\n{audit_result}\n\n"
        "CURRENT CODE:\n{code}"
    ),
}

# --- Audit prompts (Athena) ---

AUDIT_PROMPTS = {
    "feature": (
        "PROJECT_ROOT: {project_root}\n"
        "TASK: Audit this code for security, best practices, and correctness.\n\n"
        "USER INTENT:\n{user_prompt}\n\n"
        "IMPLEMENTATION DETAILS:\n{code}\n\n"
        "Reply exactly with 'PASSED' at the beginning of your response if the code is correct. "
        "Otherwise list the issues with severity levels."
    ),
    "bug-fix": (
        "PROJECT_ROOT: {project_root}\n"
        "TASK: Verify that this bug fix is correct and doesn't introduce new issues.\n\n"
        "BUG DESCRIPTION:\n{user_prompt}\n\n"
        "FIX IMPLEMENTATION:\n{code}\n\n"
        "Reply exactly with 'PASSED' at the beginning of your response if the fix is correct. "
        "Otherwise list the issues."
    ),
    "security-review": (
        "PROJECT_ROOT: {project_root}\n"
        "TASK: Perform a comprehensive security review.\n\n"
        "SECURITY CONTEXT (from research):\n{research}\n\n"
        "SCOPE:\n{user_prompt}\n\n"
        "Provide a full threat assessment using the STRIDE methodology. "
        "Prioritize findings by severity."
    ),
    "security-review_fix": (
        "PROJECT_ROOT: {project_root}\n"
        "TASK: Re-verify the security fixes. Confirm each finding from the original "
        "review has been addressed.\n\n"
        "ORIGINAL FINDINGS:\n{audit_result}\n\n"
        "FIXED CODE:\n{code}\n\n"
        "Reply exactly with 'PASSED' if all findings are addressed. "
        "Otherwise list remaining issues."
    ),
    "refactor": (
        "PROJECT_ROOT: {project_root}\n"
        "TASK: Verify that this refactoring preserves all existing functionality "
        "and doesn't introduce security issues.\n\n"
        "REFACTOR DESCRIPTION:\n{user_prompt}\n\n"
        "REFACTORED CODE:\n{code}\n\n"
        "Reply exactly with 'PASSED' if the refactoring is correct. "
        "Otherwise list issues."
    ),
}

# --- Onboard prompt (Ariadna) ---

ONBOARD_PROMPT = (
    "PROJECT_ROOT: {project_root}\n"
    "TASK: Initialize project tracking. Project description:\n{user_prompt}\n\n"
    "Create the .eter/ directory structure with CURRENT.md (initial status) and LOG.md (first entry). "
    "Use your standard output format: Status, Blockers, Risks, Next Steps, Last Session."
)


def get_prompt(category: str, variant: str, **kwargs) -> str:
    """Get a prompt template and format it with the provided kwargs.

    Args:
        category: One of 'research', 'design', 'implement', 'audit', 'onboard'
        variant: The specific prompt variant within the category
        **kwargs: Values to format into the template

    Returns:
        Formatted prompt string
    """
    prompt_dict = {
        "research": RESEARCH_PROMPTS,
        "design": DESIGN_PROMPTS,
        "implement": IMPLEMENT_PROMPTS,
        "audit": AUDIT_PROMPTS,
    }

    if category == "onboard":
        return ONBOARD_PROMPT.format(**kwargs)

    if category not in prompt_dict:
        raise ValueError(f"Unknown prompt category: {category}")

    if variant not in prompt_dict[category]:
        raise ValueError(f"Unknown prompt variant '{variant}' for category '{category}'")

    return prompt_dict[category][variant].format(**kwargs)
