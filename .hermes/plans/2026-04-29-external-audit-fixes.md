# External Audit Fixes — Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Fix 20 issues detected by external audit of Aether Agents project

**Architecture:** Three-phase approach — Fase 1 is quick documentation/dependency fixes (< 1 línea each), Fase 2 is code bug fixes, Fase 3 is architectural documentation. Each phase gets its own commit.

**Tech Stack:** Python 3.11+, LangGraph, hermes-agent ACP, MCP protocol

**Project Root:** /home/prometeo/Aether-Agents

---

## FASE 1 — 8 Documentation & Dependency Fixes

### Task 1: Unificar versión a 0.3.0 en pyproject.toml

**Objective:** Set consistent project version across all files

**Files:**
- Modify: `pyproject.toml:7`

**Step 1:** Change version in pyproject.toml

```toml
# BEFORE:
version = "0.1.0"

# AFTER:
version = "0.3.0"
```

**Step 2:** Verify change

Run: `grep 'version' pyproject.toml | head -3`
Expected: `version = "0.3.0"`

---

### Task 2: Unificar versión a 0.3.0 en README.md

**Objective:** Match version in top-level README

**Files:**
- Modify: `README.md:69`

**Step 1:** Change version line

```markdown
# BEFORE:
**Current version:** v0.2.0 — Workflow Engine + Conventions Formalized

# AFTER:
**Current version:** v0.3.0 — External Audit Fixes
```

**Step 2:** Verify

Run: `grep 'version' README.md | head -3`
Expected: line with `v0.3.0`

---

### Task 3: Agregar sección 0.3.0 al CHANGELOG.md

**Objective:** Document this release in changelog with all 20 fixes

**Files:**
- Modify: `CHANGELOG.md` (prepend new section after header)

**Step 1:** Add new version section

```markdown
## [0.3.0] — 2026-04-29

### Fixed

- Unified project version across README (0.2.0), pyproject.toml (0.1.0), and CHANGELOG (2.0.0) to 0.3.0
- Added `langgraph-checkpoint-sqlite>=2.0.0` to pyproject.toml dependencies (was missing but required by server.py)
- Fixed QUICKSTART.md: `pip install -e ./src/olympus` → `pip install -e .` (pyproject.toml is at root)
- Replaced `langchain_core.utils.uuid.uuid7` with stdlib `uuid.uuid4()` in runner.py (removes fragile dependency)
- Fixed Olympus README: "two tools" → "three tools" (discover, talk_to, run_workflow)
- Removed redundant `talk_to(action="discover")` — `mcp_olympus_discover` is the canonical tool
- Documented that STALL_TIMEOUT=120s is the only timeout (removed phantom "30 min hard limit" reference)
- Created `home/config.yaml.example` for MCP server configuration

### Changed

- `shutdown_agent` now terminates process (`proc.terminate()` + `proc.wait()`) instead of only setting status to DEAD
- Added `modification_feedback` field to WorkflowState for HITL modify decision routing
- Added permission audit logging in `request_permission()` — auto-approve still default, but now logged
- Created `tests/test_workflows.py` with basic workflow compilation tests

### Security

- Auto-approve of Daimon permissions is now logged with agent name, permission type, and timestamp
- Created `SECURITY.md` documenting the permission model and current MVP auto-approve behavior
```

**Step 2:** Verify

Run: `head -30 CHANGELOG.md`
Expected: Section `[0.3.0] — 2026-04-29` visible

---

### Task 4: Agregar langgraph-checkpoint-sqlite a dependencias

**Objective:** Fix missing runtime dependency that causes ImportError at production

**Files:**
- Modify: `pyproject.toml` (dependencies list)

**Step 1:** Add the missing dependency

```toml
# BEFORE:
dependencies = [
    "mcp>=1.0.0",
    "agent-client-protocol>=0.1.0",
    "langgraph>=0.2.0",
    "pyyaml>=6.0",
]

# AFTER:
dependencies = [
    "mcp>=1.0.0",
    "agent-client-protocol>=0.1.0",
    "langgraph>=0.2.0",
    "langgraph-checkpoint-sqlite>=2.0.0",
    "pyyaml>=6.0",
]
```

**Step 2:** Verify

Run: `grep 'langgraph' pyproject.toml`
Expected: both `langgraph>=0.2.0` and `langgraph-checkpoint-sqlite>=2.0.0`

---

### Task 5: Corregir QUICKSTART.md — pip install path

**Objective:** Fix installation command that fails for newcomers

**Files:**
- Modify: `docs/guides/QUICKSTART.md`

**Step 1:** Fix the pip install command

Find the line:
```bash
pip install -e ./src/olympus
```

Replace with:
```bash
pip install -e .
```

**Step 2:** Verify

Run: `grep 'pip install' docs/guides/QUICKSTART.md`
Expected: `pip install -e .` (no `./src/olympus`)

---

### Task 6: Migrar uuid7 a uuid4 en runner.py

**Objective:** Remove fragile dependency on langchain_core.utils.uuid.uuid7

**Files:**
- Modify: `src/olympus/workflows/runner.py`

**Step 1:** Replace import and usage

```python
# BEFORE (line 8):
from langchain_core.utils.uuid import uuid7

# AFTER:
import uuid

# BEFORE (line 41):
thread_id = str(uuid7())

# AFTER:
thread_id = str(uuid.uuid4())
```

**Step 2:** Verify no other uuid7 references

Run: `grep -rn 'uuid7\|langchain_core.utils.uuid' src/olympus/`
Expected: No results

**Step 3:** Verify uuid import

Run: `grep 'import uuid' src/olympus/workflows/runner.py`
Expected: `import uuid`

---

### Task 7: Corregir Olympus README — three tools, no two

**Objective:** Fix incorrect tool count in Olympus README

**Files:**
- Modify: `src/olympus/README.md`

**Step 1:** Fix line 3

```markdown
# BEFORE:
Olympus is the MCP server that powers Aether Agents' multi-agent orchestration. It exposes two tools to Hermes (or any MCP-compatible agent):

# AFTER:
Olympus is the MCP server that powers Aether Agents' multi-agent orchestration. It exposes three tools to Hermes (or any MCP-compatible agent):
```

**Step 2:** Verify the tool list matches

The README should list:
1. **`discover`** — List available Daimons and their capabilities
2. **`talk_to`** — Communicate with Daimons (open, message, poll, wait, cancel, close)
3. **`run_workflow`** — Execute structured multi-step workflows with HITL

If the list only shows talk_to and run_workflow, add discover.

**Step 3:** Verify

Run: `head -10 src/olympus/README.md`
Expected: "three tools" on line 3

---

### Task 8: Eliminar talk_to(action="discover") redundante

**Objective:** Remove duplicate discovery mechanism — `mcp_olympus_discover` is the canonical tool

**Files:**
- Modify: `src/olympus/server.py`

**Step 1:** Remove the discover action from talk_to handler

In server.py, find the talk_to handler's action enum/validation (around line 108):
```python
"enum": ["discover", "open", "message", "poll", "wait", "cancel", "close"],
```

Change to:
```python
"enum": ["open", "message", "poll", "wait", "cancel", "close"],
```

**Step 2:** Remove the discover branch from the talk_to handler

Find (around line 244):
```python
if action == "discover" or agent_name == "?" or not agent_name:
```

Remove the `action == "discover"` condition. The `agent_name == "?"` fallback can stay as a convenience alias that redirects to the discover tool, OR remove it entirely. Decision: keep `agent_name == "?"` as alias that calls _handle_discover().

The updated code:
```python
if agent_name == "?" or not agent_name:
```

**Step 3:** Update error message

Find (around line 300):
```python
text=json.dumps({"error": f"Unknown action: {action}. Valid: discover, open, message, poll, wait, cancel, close"}),
```

Change to:
```python
text=json.dumps({"error": f"Unknown action: {action}. Valid: open, message, poll, wait, cancel, close. For discovery, use the 'discover' tool."}),
```

**Step 4:** Verify

Run: `grep -n 'discover' src/olympus/server.py`
Expected: Only references to the `_handle_discover` function and the separate discover tool definition. No "discover" in the talk_to action enum or handler.

---

### Task 9: Documentar timeout real en nodes.py

**Objective:** Remove phantom "30 min hard limit" reference, document actual behavior

**Files:**
- Modify: `src/olympus/workflows/nodes.py` (add comment)
- Modify: `aether-diagnostics/SKILL.md` (remove 30 min reference from skill)

**Note:** The aether-diagnostics skill was already loaded and says:
> "Progress Watchdog: polls every 10s for activity. Stalls after 120s of no activity"
> "total_safety_timeout = 1800s (30 min) — emergency ceiling in runner (not operational limit)"

The aether-diagnostics skill text says 1800s but runner.py has NO such constant. Fix the skill and add a clarifying comment in nodes.py.

**Step 1:** Add comment to nodes.py (after STALL_TIMEOUT definition, around line 17-18)

```python
STALL_TIMEOUT = 120   # 2 minutes without activity = STALLED
# NOTE: There is NO separate "hard timeout" or "safety ceiling" in runner.py.
# STALL_TIMEOUT is the only timeout mechanism. If an agent produces activity
# (thoughts, messages, or tool calls) within this window, it gets unlimited time.
# Only agents with zero activity for STALL_TIMEOUT seconds are considered stalled.
```

**Step 2:** Update aether-diagnostics skill

In the aether-diagnostics SKILL.md, find the reference to "total_safety_timeout = 1800s (30 min) — emergency ceiling in runner (not operational limit)" and remove it or update to:

```markdown
- `STALL_TIMEOUT = 120s` — if no activity for 2 minutes, agent is considered stalled
- There is NO separate "hard timeout" or "30 min safety ceiling" — this was previously
  documented but never implemented. STALL_TIMEOUT is the only timeout mechanism.
```

**Step 3:** Verify

Run: `grep -n 'STALL_TIMEOUT\|1800\|30.*min\|30 min' src/olympus/workflows/nodes.py src/olympus/workflows/runner.py`
Expected: Only STALL_TIMEOUT = 120 in nodes.py, no 1800 references in either file

---

### Task 10: Crear home/config.yaml.example

**Objective:** Provide example configuration for MCP server setup

**Files:**
- Create: `home/config.yaml.example`

**Step 1:** Create the file

```yaml
# Example configuration for Olympus MCP Server
# Copy this file to home/config.yaml and adjust paths for your system.

mcp_servers:
  olympus:
    command: /path/to/hermes-agent/venv/bin/python
    args:
      - -m
      - olympus.server
    env:
      AETHER_HOME: /path/to/Aether-Agents/home
      PYTHONPATH: /path/to/Aether-Agents/src
    enabled: true

# Context7 — for documentation lookups (optional)
  context7:
    command: npx
    args:
      - -y
      - "@upstash/context7-mcp"
    enabled: true
```

**Step 2:** Verify file exists

Run: `test -f home/config.yaml.example && echo "OK"`
Expected: OK

---

### Task 11: Commit Fase 1

**Objective:** Commit all Fase 1 changes

```bash
git add pyproject.toml README.md CHANGELOG.md docs/guides/QUICKSTART.md \
        src/olympus/workflows/runner.py src/olympus/README.md \
        src/olympus/server.py src/olympus/workflows/nodes.py \
        home/config.yaml.example
git commit -m "fix: external audit — 8 documentation and dependency fixes (v0.3.0)

- Unified version to 0.3.0 (README, pyproject.toml, CHANGELOG)
- Added langgraph-checkpoint-sqlite to dependencies
- Fixed QUICKSTART: pip install -e . (not ./src/olympus)
- Replaced uuid7 with stdlib uuid4 (removed langchain_core dependency)
- Fixed Olympus README: three tools (not two)
- Removed redundant talk_to(action='discover')
- Documented STALL_TIMEOUT as the only timeout (no 30min limit)
- Created home/config.yaml.example for MCP server setup"
```

---

## FASE 2 — 4 Code Bug Fixes

### Task 12: Fix shutdown_agent — matar el proceso realmente

**Objective:** Ensure zombie processes are terminated when a Daimon is shut down

**Files:**
- Modify: `src/olympus/acp_client.py`

**Context:** Current `shutdown_agent()` only sets status to DEAD without terminating the process. This leaves zombie hermes processes consuming memory.

**Step 1:** Find the shutdown method (around line 404-428) and add process termination

The current code approximately:
```python
async def shutdown_agent(self, name: str) -> dict:
    ...
    if agent.status == AgentStatus.DEAD:
        ...
    agent.status = AgentStatus.DEAD
```

Add process termination logic after setting status:
```python
async def shutdown_agent(self, name: str) -> dict:
    ...
    agent.status = AgentStatus.DEAD
    
    # Terminate the process if it exists
    if agent.process is not None:
        try:
            agent.process.terminate()
            try:
                await asyncio.wait_for(agent.process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                # Process didn't terminate gracefully, force kill
                agent.process.kill()
                await agent.process.wait()
            logger.info(f"[olympus] Terminated process for {name} (PID: {agent.process.pid})")
        except ProcessLookupError:
            # Process already dead
            logger.info(f"[olympus] Process for {name} already terminated")
        except Exception as e:
            logger.warning(f"[olympus] Error terminating process for {name}: {e}")
```

**Step 2:** Verify asyncio is imported

Run: `grep 'import asyncio' src/olympus/acp_client.py`
Expected: `import asyncio` present (it should already be there)

**Step 3:** Verify

Run: `grep -n 'terminate\|kill\|wait()' src/olympus/acp_client.py`
Expected: terminate(), kill(), and wait() calls in shutdown_agent method

---

### Task 13: Agregar modification_feedback al WorkflowState

**Objective:** Enable HITL "modify" decisions to pass feedback back to the design node

**Files:**
- Modify: `src/olympus/workflows/state.py`
- Modify: `src/olympus/workflows/nodes.py`
- Modify: `src/olympus/workflows/definitions.py`

**Context:** When a user selects "modify" at a design_review HITL checkpoint, the workflow routes back to the design node but never tells Daedalus WHAT to modify. This makes "modify" equivalent to "start over from scratch."

**Step 1:** Add field to WorkflowState (state.py)

Add `modification_feedback: str` field:
```python
# Add to WorkflowState TypedDict:
modification_feedback: str  # HITL modify decision feedback — passes user instructions to redesign
```

**Step 2:** Update HITL node to capture modification feedback (nodes.py)

In the `make_node_hitl` function, when the user's decision is "modify", include their feedback in the state update. The HITL node should pass the interrupt context (which contains the user's reasoning) as modification_feedback:

```python
# When user selects "modify", capture their feedback
if resume_value == "modify":
    return Command(
        update={
            "hitl_decisions": [f"{key}: modify"],
            "modification_feedback": interrupt_data.get("context", ""),
        },
        goto=hits["modify"],
    )
```

**Step 3:** Update design node prompt to include modification_feedback (nodes.py)

In the design node prompt construction, check if modification_feedback exists:
```python
# In make_node_design prompt:
if state.get("modification_feedback"):
    prompt += f"\n\nMODIFICATION FEEDBACK FROM USER:\n{state['modification_feedback']}\nPlease revise the design based on this feedback."
```

**Step 4:** Verify state.py compiles

Run: `cd /home/prometeo/Aether-Agents && python -c "from src.olympus.workflows.state import WorkflowState; print('OK')"`
Expected: OK

**Step 5:** Verify definitions.py compiles

Run: `cd /home/prometeo/Aether-Agents && python -c "from src.olympus.workflows.definitions import get_workflow; print('OK')"`
Expected: OK

---

### Task 14: Agregar logging de permisos auto-aprobados + SECURITY.md

**Objective:** Document and log the auto-approve permission model for security auditability

**Files:**
- Modify: `src/olympus/acp_client.py`
- Create: `SECURITY.md`

**Step 1:** Add logging to request_permission (acp_client.py, around line 67-77)

```python
async def request_permission(
    self, agent_name: str, session_id: str, permission_request: dict
) -> RequestPermissionResponse:
    """Handle permission requests from Daimons — auto-approved for MVP.
    
    SECURITY NOTICE: All permission requests are currently auto-approved.
    This is acceptable for local development but MUST be reviewed before
    production deployment. See SECURITY.md for details.
    """
    permission_type = permission_request.get("type", "unknown")
    description = permission_request.get("description", "no description")
    logger.warning(
        f"[olympus] AUTO-APPROVED permission for {agent_name}: "
        f"type={permission_type}, description={description}, session={session_id}"
    )
    return RequestPermissionResponse(outcome={"outcome": "approved"})
```

**Step 2:** Create SECURITY.md at project root

```markdown
# Security Model — Aether Agents

## Permission Auto-Approve (MVP)

Olympus currently **auto-approves all permission requests** from Daimons. This means:

- Any Daimon can execute any terminal command, write to any file, or access any network resource that hermes-agent grants
- There is no human-in-the-loop for permission decisions
- All auto-approvals are logged with WARNING level: agent name, permission type, description, and session ID

### Risk Assessment

| Permission Type | Risk Level | Current Mitigation |
|----------------|------------|-------------------|
| Terminal commands | High | Logged only |
| File writes | Medium | Logged only |
| Network requests | Medium | Logged only |
| Environment access | Low | Logged only |

### Production Recommendations

Before deploying Aether Agents in production:

1. **Replace auto-approve with allowlist:** Define which permissions each Daimon role can receive without approval (e.g., Hefesto can write to project directories but not ~/.bashrc)
2. **Add HITL for dangerous permissions:** Terminal commands, file writes outside project root, and network requests to unknown domains should require explicit approval
3. **Rate-limit permissions:** Prevent Daimons from flooding the permission system
4. **Audit log:** Store all permission decisions (approved/denied) in a persistent log file

### Architecture Note

Permission requests flow through the ACP protocol. When a Daimon (running as a hermes-agent process) encounters an action requiring permission, it sends a request through the ACP connection. Olympus (the MCP server) receives this request and currently responds with "approved" automatically.

The permission system is designed to be extended with:
- Per-Daimon permission policies
- Allowlist/denylist configurations
- Human approval workflows (similar to workflow HITL)

## Daimon Process Isolation

Daimons run as separate hermes-agent processes. Each Daimon:
- Has its own HERMES_HOME pointing to its profile directory
- Has its own .env file with API keys
- Has its own set of toolsets (defined in config.yaml)
- Cannot access other Daimons' environments

However, all Daimons share the same:
- System Python and pip packages
- Network access
- Filesystem access (within HERMES_HOME boundaries)
```

**Step 3:** Verify logging works

Run: `grep -n 'logger.warning.*AUTO-APPROVED' src/olympus/acp_client.py`
Expected: 1 match in the request_permission method

---

### Task 15: Crear tests/test_workflows.py con mocks básicos

**Objective:** Add basic test coverage for workflow engine compilation and state

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/test_workflows.py`

**Step 1:** Create tests directory

```bash
mkdir -p tests
```

**Step 2:** Create `tests/__init__.py` (empty)

**Step 3:** Create `tests/test_workflows.py`

```python
"""Basic workflow engine tests — compilation, state, and edge cases.

These tests use mocks for the ACP manager, so they can run without
a live hermes-agent or Daimon processes.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from olympus.workflows.state import WorkflowState


class TestWorkflowState:
    """Test WorkflowState TypedDict structure."""

    def test_state_has_required_fields(self):
        """WorkflowState must have all fields needed by workflow nodes."""
        state = WorkflowState(
            user_prompt="Test prompt",
            context="",
            code="",
            audit_result="",
            audit_passed=False,
            research="",
            messages=[],
            review_cycles=0,
            max_review_cycles=3,
            final_response="",
            project_root="/tmp/test",
            errors=[],
            status="running",
            started_at=0.0,
            node_name="",
            needs_research=True,
            has_ui=False,
            workflow_type="feature",
            modification_feedback="",
        )
        assert state["workflow_type"] == "feature"
        assert state["modification_feedback"] == ""

    def test_state_modification_feedback_default(self):
        """modification_feedback should default to empty string."""
        state = WorkflowState(
            user_prompt="Test",
            context="",
            code="",
            audit_result="",
            audit_passed=False,
            research="",
            messages=[],
            review_cycles=0,
            max_review_cycles=3,
            final_response="",
            project_root="/tmp",
            errors=[],
            status="running",
            started_at=0.0,
            node_name="",
            needs_research=False,
            has_ui=False,
            workflow_type="bug-fix",
            modification_feedback="",
        )
        assert state["modification_feedback"] == ""


class TestWorkflowCompilation:
    """Test that workflow graphs compile without errors."""

    def _get_mock_acp(self):
        """Create a mock ACPManager for workflow compilation."""
        mock = MagicMock()
        mock.ensure_agent = AsyncMock()
        mock.open_session = AsyncMock()
        mock.send_prompt = AsyncMock()
        mock.close_session = AsyncMock()
        mock.shutdown_agent = AsyncMock()
        return mock

    def test_feature_workflow_compiles(self):
        """Feature workflow graph should compile without errors."""
        from olympus.workflows.definitions import get_workflow
        acp = self._get_mock_acp()
        graph = get_workflow("feature", acp)
        assert graph is not None

    def test_bug_fix_workflow_compiles(self):
        """Bug-fix workflow graph should compile without errors."""
        from olympus.workflows.definitions import get_workflow
        acp = self._get_mock_acp()
        graph = get_workflow("bug-fix", acp)
        assert graph is not None

    def test_research_workflow_compiles(self):
        """Research workflow graph should compile without errors."""
        from olympus.workflows.definitions import get_workflow
        acp = self._get_mock_acp()
        graph = get_workflow("research", acp)
        assert graph is not None

    def test_security_review_workflow_compiles(self):
        """Security review workflow graph should compile without errors."""
        from olympus.workflows.definitions import get_workflow
        acp = self._get_mock_acp()
        graph = get_workflow("security-review", acp)
        assert graph is not None

    def test_refactor_workflow_compiles(self):
        """Refactor workflow graph should compile without errors."""
        from olympus.workflows.definitions import get_workflow
        acp = self._get_mock_acp()
        graph = get_workflow("refactor", acp)
        assert graph is not None

    def test_project_init_workflow_compiles(self):
        """Project init workflow graph should compile without errors."""
        from olympus.workflows.definitions import get_workflow
        acp = self._get_mock_acp()
        graph = get_workflow("project-init", acp)
        assert graph is not None

    def test_invalid_workflow_raises(self):
        """Invalid workflow name should raise ValueError."""
        from olympus.workflows.definitions import get_workflow
        acp = self._get_mock_acp()
        with pytest.raises(ValueError):
            get_workflow("nonexistent", acp)


class TestConditionalEdges:
    """Test conditional edge functions."""

    def test_should_enter_research_true(self):
        """needs_research=True should route to research node."""
        from olympus.workflows.definitions import should_enter_research
        state = WorkflowState(
            user_prompt="test",
            needs_research=True,
            workflow_type="feature",
            # ... other defaults through **kwargs not available in TypedDict
        )
        # Note: TypedDict doesn't enforce at runtime, so we test the function directly
        # The function checks state["needs_research"]
        assert should_enter_research({"needs_research": True}) == "research"

    def test_should_enter_research_false(self):
        """needs_research=False should skip research."""
        from olympus.workflows.definitions import should_enter_research
        assert should_enter_research({"needs_research": False}) == "design"

    def test_should_terminate_on_error_no_errors(self):
        """No errors should continue."""
        from olympus.workflows.definitions import should_terminate_on_error
        assert should_terminate_on_error({"errors": []}) == "continue"

    def test_should_terminate_on_error_with_errors(self):
        """Errors should terminate."""
        from olympus.workflows.definitions import should_terminate_on_error
        assert should_terminate_on_error({"errors": ["something failed"]}) == "finalize"


class TestSTALLTIMEOUT:
    """Test that STALL_TIMEOUT is documented correctly."""

    def test_stall_timeout_is_120(self):
        """STALL_TIMEOUT should be 120 seconds (2 minutes)."""
        from olympus.workflows.nodes import STALL_TIMEOUT
        assert STALL_TIMEOUT == 120

    def test_no_1800_timeout_in_runner(self):
        """There should be NO 1800-second 'hard timeout' in runner.py."""
        import subprocess
        result = subprocess.run(
            ["grep", "-c", "1800", "src/olympus/workflows/runner.py"],
            capture_output=True, text=True
        )
        # grep -c returns the count of matching lines
        # "0" means no matches (which is what we want)
        assert result.stdout.strip() == "0", \
            "runner.py should not contain any 1800-second timeout reference"
```

**Step 4:** Run tests

```bash
cd /home/prometeo/Aether-Agents
PYTHONPATH=src:$PYTHONPATH python -m pytest tests/test_workflows.py -v
```

Expected: All tests pass

**Step 5:** Verify test file exists

Run: `test -f tests/test_workflows.py && echo "OK"`
Expected: OK

---

### Task 16: Commit Fase 2

**Objective:** Commit all Fase 2 changes

```bash
git add src/olympus/acp_client.py \
        src/olympus/workflows/state.py \
        src/olympus/workflows/nodes.py \
        src/olympus/workflows/definitions.py \
        tests/__init__.py tests/test_workflows.py \
        SECURITY.md
git commit -m "fix: external audit — 4 code and architecture fixes

- shutdown_agent now terminates process (terminate + kill fallback)
- Added modification_feedback to WorkflowState for HITL modify routing
- Added permission audit logging + SECURITY.md documenting auto-approve
- Created tests/test_workflows.py with compilation and state tests"
```

---

## FASE 3 — Architectural Documentation (FUTURE SPRINT)

These items are documentation and architectural decisions, not code bugs. They require more discussion and dedicated time:

| # | Item | Type |
|---|------|------|
| 5 | docs/ACP.md — What is ACP, how it works, how to implement a Daimon in another language | Documentation |
| 7 | Explain Daimon tool model (mcp_servers=[], toolsets come from config.yaml) | Documentation |
| 8 | Document SKILL.md format (frontmatter schema + markdown body) | Documentation |
| 9 | Fix session ID mapping for concurrency (fallback to "exactly one" is a hack) | Code refactor |
| 12 | Externalize workflow prompts (i18n-ready, template system) | Architecture |
| 14 | Already fixed in this plan (three tools) | Done |
| 15 | Already fixed in this plan (removed redundant discover) | Done |
| 18 | Document .eter/ as local-only (not for team sync) | Documentation |
| 19 | Document AETHER_HOME vs HERMES_HOME clearly in ARCHITECTURE.md | Documentation |
| 20 | Add deploy instructions for website/ (GitHub Pages or similar) | Documentation |