# Daimon Delegation Patterns

Operational patterns for delegating work to Aether Daimons via the Olympus MCP server
(`mcp_olympus_v3_talk_to`). These supplement the protocol documentation in SOUL.md §5
with practical lessons from real usage.

## Timeout Guidance

| Task type | Recommended timeout | Example |
|-----------|-------------------|---------|
| Simple response (greeting, Q&A) | 120s | "Present yourself" |
| Single-file review | 180s | "Review config.yaml for security issues" |
| Multi-file analysis (3-10 files) | 300s | "Audit the profiles/ directory" |
| Comprehensive audit (20+ files) | **600s** | "Full security audit of project" |
| Research + synthesis (20+ sources) | 600s | "Research all dependencies for CVEs" |

**Default delegate timeout is 300s.** Complex multi-file tasks (security audits,
dependency analysis, cross-project refactoring) will time out at 300s. Always set
`timeout=600` for tasks that require reading 15+ files or producing structured
reports with 10+ findings.

The `poll_interval` can stay at 15-20s. The delegate action handles polling internally;
there's no benefit to polling more frequently.

## Structured Output Schema

When delegating analysis or audit tasks, include an `OUTPUT SCHEMA` block in the prompt.
Daimons produce significantly better structured output when given explicit field names,
types, and required/optional markers.

**Pattern:**

```
OUTPUT SCHEMA:
{
  "findings": [
    {
      "id": "SEC-NNN",
      "severity": "CRITICAL|HIGH|MEDIUM|LOW|INFO",
      "category": "string",
      "title": "string",
      "description": "string",
      "evidence": "string (file path + line number)",
      "affected_files": ["string"],
      "remediation": "string"
    }
  ],
  "summary": { "critical": int, "high": int, "medium": int, "low": int, "info": int },
  "top_5_actions": ["string"]
}
```

Without this schema, Daimons tend to produce free-form prose that's harder to parse
and synthesize. With it, output is consistently structured and actionable.

**Also include these sections in the prompt:**
- `CONTEXT:` — project root, relevant background (2-4 lines)
- `TASK:` — specific, concrete deliverable (not vague)
- `CONSTRAINTS:` — hard limits (READ-ONLY, no file modifications, etc.)
- `OUTPUT FORMAT:` — description of expected format
- `OUTPUT SCHEMA:` — structured format definition (the JSON above)

## Recovery: Stuck Manual Sessions

If using the manual `open → message → poll` pattern (instead of `delegate`) and the
Daimon shows 0 thoughts, 0 messages, and 0 tool_calls after 5+ polls (150+ seconds):

1. **Cancel the session** (`cancel` action)
2. **Retry with `delegate`** — the delegate action handles session lifecycle automatically
3. **Increase timeout** — set `timeout=600` for complex tasks

The `delegate` action is preferred over manual `talk_to` for one-shot tasks. Manual
mode is only needed for multi-turn conversations where you need intermediate status
or want to send follow-up messages.

## Delegation Prompt Template

Use this template for all Daimon delegations to ensure consistency:

```
CONTEXT:
PROJECT_ROOT: /absolute/path/to/project
[2-4 lines of project context the Daimon needs]

TASK:
[Specific task. Concrete deliverable, not vague.]

CONSTRAINTS:
[Hard limits: budget, scope, time, what NOT to do.]

OUTPUT FORMAT:
[Exactly what format you expect back. Be explicit.]

OUTPUT SCHEMA:
[Structured format definition — field names, types, required vs optional.
This eliminates 60-70% of handoff errors between agents.]
```

## Daimon-Specific Notes

| Daimon | Best for | Typical file reads | Timeout |
|--------|----------|-------------------|---------|
| Hefesto | Code implementation, file writes | 5-15 | 300s |
| Etalides | Research, documentation, CVEs | 3-10 | 180-300s |
| Athena | Security audit, threat modeling | 15-40 | **600s** |
| Daedalus | UX design, mockups | 3-8 | 180s |
| Ariadna | Context curation | 1-3 | 120s |

Athena is the most file-intensive Daimon — security audits require reading config files,
.env files, auth.json, permissions, and hooks across all profiles. Always give her 600s.

## Bidirectional Communication — Current State & Implementation Plan

Daimons delegated via `talk_to`/`delegate` have **two communication gaps**:

1. **No progress visibility** — `poll()` returns aggregate counts (`tool_calls: 10`)
   with no detail about what the Daimon is doing. LLM orchestrators are impatient
   ("desesperados") when they see a counter incrementing with no context.
2. **No clarification channel** — Daimons cannot ask questions mid-execution.
   The Daimon outputs "CLARIFICATION NEEDED:" in `last_turn`, but `delegate()`
   treats this as normal completion.

**Priority order** (per user): visibility/heartbeat FIRST, then clarification.

### Implementation Plan: Option A — Steering + Enriched Poll

After a deep code analysis (2026-05-19) of `acp_manager.py`, `server.py`,
`db.py`, and `olympus_v3_hooks/hooks.py`, the recommended implementation is:

**Change 1: Add `steer` action** (`server.py`, ~30 lines)
The `steering` table in `db.py` already exists with full CRUD. The
`pre_llm_call` hook already consumes steering directives. But no MCP action
writes to it. Add `steer` to the `talk_to` inputSchema enum + handler that
calls `db.insert_steering(session_id, directive, priority)`.

**Change 2: Enrich `get_session_progress()`** (`db.py`, ~20 lines)
Add three fields to the progress dict:
- `recent_tool_calls`: last 5 tool calls with `(tool_name, status, timestamp)`
  — so Hermes sees "read_file, terminal" instead of just `tool_calls: 10`
- `clarification_needed`: regex on `last_turn` for "CLARIFICATION NEEDED"
- `last_activity`: timestamp of most recent turn

Data is already in SQLite (`get_tool_calls()` returns full records).

**Change 3: Detect clarification in `delegate()`** (`acp_manager.py`, ~15 lines)
After `status: "completed"`, check `last_turn` for `/CLARIFICATION\s+NEEDED:/i`.
If matched, return `status: "clarification_needed"` WITHOUT closing the session.

Same change in `server.py`'s delegate handler.

**Change 4: SOUL.md protocols** (Hermes + all 6 Daimons)
- Hermes: when `delegate` returns `clarification_needed`, send `message()` in
  the same session, then poll. When `poll` shows `recent_tool_calls`, report
  progress to user ("Athena is auditing security (step 3/8)...").
- Daimons: after every 3 tool calls, emit progress line. When needing
  clarification, output "CLARIFICATION NEEDED:" with specific questions.

**What NOT to do:**
- Do NOT create new MCP actions for clarification — reuse `message` + `poll`
- Do NOT create `ask_orchestrator` tool — requires hermes-agent upstream changes
- Do NOT add file-based progress — steering table + enriched poll covers it
- Do NOT modify the ACP protocol itself — changes are all in Olympus v3 layer

**Full details:** See `references/bidirectional-implementation-plan.md`

### Layer 1: `delegate_tool.py` blocks `clarify`

```python
# delegate_tool.py line 40-47
DELEGATE_BLOCKED_TOOLS = frozenset([
    "delegate_task",  # no recursive delegation
    "clarify",        # no user interaction ← BLOCKS QUESTIONS
    "memory",         # no writes to shared MEMORY.md
    "send_message",   # no cross-platform side effects
    "execute_code",   # children should reason step-by-step
])
```

Even if a Daimon's SOUL.md says "return CLARIFICATION NEEDED", the `clarify` tool
is removed from the Daimon's tool schema. A Daimon can only output a text string
saying it needs clarification — it cannot pause and wait for an answer.

### Layer 2: ACP is unidirectional (prompt → response)

The Olympus `acp_manager.py` communication model is:
1. `spawn_agent()` → create process
2. `send_message()` → fire prompt, returns immediately with `status: "sent"`
3. `poll()` → reads SQLite (not ACP streaming), no mid-turn channel
4. `close()`/`cancel()` → terminate

There is no mechanism for the Daimon to send a message *back* during execution.
ACP has `new_session`, `prompt`, and `cancel` — no "question" method.

### Layer 3: Plugin hooks are one-way

Available hooks (pre_tool_call, post_tool_call, pre_llm_call, post_llm_call,
on_session_start, on_session_end, subagent_stop, transform_*) all fire in one
direction. None allow the Daimon to pause execution and ask a question.

### Current workaround: "CLARIFICATION NEEDED" string

Daimon SOULs instruct agents to return a special string when they need more context:

> "If the task is unclear or missing context, return immediately:
> 'CLARIFICATION NEEDED: [specific question]. Cannot proceed until: [what is missing].'"

This is **unidirectional with stop** — the Daimon stops, Hermes reads the string,
and re-delegates with more context. The original session is lost; the new session
starts from scratch.

### Validated Solution: Option B (Persistent ACP Session) + Option A (Enriched Poll)

**Empirically verified on 2026-05-18** (multi-turn context) and **2026-05-19**
(real-world timeout test with Athena security audit).

**2026-05-19 test results (Athena security audit):**
- First attempt: `delegate` timeout at 300s (11 tool_calls, no response visible)
- Second attempt: `delegate` timeout at 600s (same pattern)
- Third attempt: manual `open → message → poll` cycle
  - After 30s: tool_calls:3, thoughts:0, messages:0
  - After 75s: tool_calls:10, still no response text
  - After 135s: tool_calls:10, status completed, thoughts:2, messages:2
  - **Response only visible after `close()`** — poll couldn't see it during execution

This confirms both gaps: (1) no progress visibility beyond counters, (2) response
content not accessible until session close.

**Test results:**
- Etalides correctly recalled Turno 1 context when sent Turno 2 in same session.
- Athena returned "CLARIFICATION NEEDED: ..." pattern detectable in `last_turn`.
- A second `message()` after clarification WAS processed (close() showed
  tool_calls:2), but `poll()` showed stale SQLite data — there's a race
  condition between aether_hooks writing progress and poll() reading it.

**Implementation approach for Option B:**

1. Modify `delegate()` in `acp_manager.py` to check `last_turn` for
   `/CLARIFICATION\s+NEEDED:/i` pattern when `status: "completed"`
2. If matched: return `{status: "clarification_needed", questions: [...], session_id: "..."}` 
   instead of closing the session
3. Hermes re-sends context via `talk_to(action="message")` in the SAME session_id
4. Then `talk_to(action="delegate")` or `poll` to wait for the completed response
5. Add a delay between `send_message()` completion and first `poll()` for
   follow-up messages — SQLite progress writes lag behind ACP response
6. Consider reading in-memory session state (via `acp_manager._sessions`)
   as fallback for stale SQLite reads

**Caveat:** The `poll()` race condition means that after sending a follow-up
message to a completed session, Hermes must wait longer than usual (60s+) or
poll multiple times looking for counter changes before concluding the message
wasn't processed. The `close()` method reads in-memory state which is more
current than SQLite — use it as a sanity check if poll appears stale.

### ⚠ Pitfall: Don't Create New MCP Actions for Bidirectional Comms

**Rejected approach (commit 62e59c8, reverted 2026-05-18):** Creating a separate
`clarify` action in the `talk_to` MCP tool with a `clarification_response`
field, plus a `continue_session()` method in `acp_manager.py`. This was
implemented by Hefesto and explicitly rejected by the project lead.

**Why it was wrong:** The correct approach uses the existing `message` and
`poll` actions in the same ACP session — no new MCP actions needed. The
`delegate()` method should detect `CLARIFICATION_NEEDED` in `last_turn` and
return `status: "clarification_needed"` WITHOUT closing the session. Then
Hermes sends context via `talk_to(action="message", session_id=...)` and
polls for the result. This reuses the existing session lifecycle rather
than inventing a parallel one.

**The spec said "find the event that determines when an agent finished its
turn and use it to convert the session to multi-turn automatically."**
Hefesto interpreted this as "add a new action," which is a common delegation
pitfall: when the spec allows multiple interpretations, the implementer
chooses the most straightforward one (add new endpoint) rather than reusing
existing mechanisms (same session, existing actions). To prevent this:

1. **Be explicit in specs:** State "use existing actions (message, poll) —
   do NOT create new MCP actions or methods"
2. **Specify negative constraints:** "No new actions, no new methods on
   acp_manager, no new fields in inputSchema" leaves no room for drift
3. **Test the simplest path first:** If `message()` already works for
   follow-ups (Test 1 proved it does), the implementation should start
   from that, not build a new path

### Other proposed solutions (higher effort)

**Option A: Disk-based clarification (moderate effort)**
- Daimon writes question to `.aether/clarifications/{session_id}.json`
- Olympus `poll()` reads this file as part of progress data
- Hermes decides whether to answer (new session) or cancel
- Pro: No hermes-agent core changes. Con: Session restart, context loss.
- **Note:** Now superseded by Option B — persistent sessions preserve context,
  making disk-based restarts unnecessary.

**Option C: `ask_orchestrator` tool (major effort, hermes-agent core change)**
- New tool exempt from `DELEGATE_BLOCKED_TOOLS`
- Daimon calls `ask_orchestrator(question, options)`
- `delegate_tool.py` intercepts, Hermes responds, injected as `tool_result`
- Pro: Natural flow, no context loss. Con: Requires hermes-agent core changes.
- **Note:** Still valuable for true mid-turn clarification (agent pauses mid-task
  to ask one question, then continues), but Option B handles most use cases
  (task-level clarification at turn boundaries) with far less effort.
For code-level details on ACP adapter, `run_conversation()`, `turn_exit_reason`, and the three bidirectional integration points, see `references/olympus-acp-architecture.md`.

## Daimon Output Quality: Contextual Calibration

Daimons with audit/checklist responsibilities (especially Athena) can over-escalate
severity ratings when their SOUL.md lacks a **contextualization step**.

### The problem

Athena's Protocol 2 (Security Review Checklist) has binary rules:
> "No secrets in code, config files, or logs"

This produces CRITICAL findings for `.env` plaintext even when mitigations exist
(gitignore, permissions 600, local-only machine). The severity definitions are
correct (Critical = "exploitable now"), but the checklist doesn't prompt the
agent to evaluate existing mitigations or deployment context before assigning severity.

### The fix

Add to the Daimon's SOUL.md (before severity assignment):

```markdown
**Before assigning severity, evaluate:**
1. Is this exploitable in the current deployment context? (local dev, staging, production)
2. What mitigations already exist? (gitignore, file permissions, network isolation, TLS)
3. Adjust severity DOWN if mitigations reduce likelihood or impact below the nominal level.
4. Note contextual adjustments in the finding (e.g., "Downgraded from Critical to Medium:
   plaintext .env with gitignore and 600 permissions on a personal dev machine").
```

This pattern applies to any Daimon that classifies findings with severity levels —
security auditors, code reviewers, risk assessors. Always include a contextualization
step that forces the agent to consider *where* and *how* the system runs before
assigning severity.

### Pitfall: Generic recommendations

Athena's audit recommended "use HashiCorp Vault" for a personal WSL development
environment. Daimons should be instructed to provide **context-appropriate**
recommendations — for a single developer on WSL, suggesting OS keyring or
`.env` + gitignore is more practical than a full vault deployment.