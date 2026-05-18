---
name: aether-agents
description: Aether Agents Daimon ecosystem — protocols, config, delegation, diagnostics, agent creation, cron design
category: devops
tags: [aether, daimon, delegation, olympus, workflows, consulting]
version: 0.8.3
last_updated: 2025-05-18
---

# Aether Agents — Daimon Ecosystem

## 1. Daimon Protocols

### Daimon Roster

| Daimon | Model | Provider | Role | Trigger |
|--------|-------|----------|------|---------|
| Hefesto | glm-5.1 | opencode-go | Senior Developer | Code implementation, file editing, bash commands |
| Etalides | deepseek-v4-flash | opencode-go | Researcher | Web/codebase research, documentation, CVEs, APIs |
| Ariadna | kimi-k2.5 | opencode-go | Context Curator | .aether continuity, CONTEXT.md synthesis |
| Athena | kimi-k2.6 | opencode-go | QA Auditor | Security review, code quality, acceptance testing |
| Daedalus | mimo-v2-omni | opencode-go | UX Designer | Design specs, user flows, layouts |
| Ictinus | (consulting) | opencode-go | Consultant | Expert review of plans before implementation |

All Daimons use Pi Agent RPC (backend: pi_rpc) via olympus_v3. The `delegate` action is preferred (1 call vs 10-20 for manual polling).

### Delegation Prompt Template

Every Daimon delegation MUST include:
- `PROJECT_ROOT:` as the first line
- `CONTEXT:` — 2-4 lines of project context
- `TASK:` — specific, concrete deliverable
- `CONSTRAINTS:` — hard limits
- `OUTPUT FORMAT:` — exact format expected
- `OUTPUT SCHEMA:` — field names, types, required/optional

### Constraints
- Daimons do NOT speak to each other — all routing goes through Hermes
- Never chain Daimons without user visibility — gate at each step
- Max 3 retry cycles per task before escalating to user
- Each task must pass its Daimon before advancing phase

## 2. Workflow Engine

### Canonical Workflows (6)

| Workflow | Sequence | When |
|----------|----------|------|
| Feature | Etalides → Daedalus → Hefesto → Athena | New feature |
| Bug-fix | Etalides → Hefesto → Athena | Diagnose, fix, verify |
| Security | Etalides → Athena → Hefesto? | Proactive audit |
| Research | Etalides alone | Knowledge gathering |
| Refactor | Etalides → Hefesto → Athena | Improve code |
| Init | Ariadna (aether_curate) | New project |

### Dev-QA Loop

```
Task N → [Hefesto implements] → [Athena validates] → PASS → Task N+1
                                      ↓ FAIL (retries < 3)
                              [Hefesto corrects with feedback]
                                      ↓ FAIL (retries >= 3)
                              [Escalate to Hermes + user]
```

## 3. Ecosystem Diagnostics

### Common Failures

| Symptom | Cause | Fix |
|---------|-------|-----|
| Empty delegation result | PID-suffixed session file mismatch | Check `_get_session_id()` reads `.olympus_session.{PID}` first |
| Daimon config not found | `api_mode: chat_completions` missing | Add to all Daimon config.yaml files |
| Profile "hermes" crashes | Reserved name in `_RESERVED_NAMES` | Use default profile or different name |
| olympus_v3 MCP errors | DB path mismatch | Verify AETHER_HOME env points to project root |

## 4. Agent Creation

### Profile Setup
1. Create `home/profiles/<name>/` with: SOUL.md, config.yaml (from template), .env (keys)
2. Never use reserved names: hermes, default, test, tmp, root, sudo
3. Test with `hermes -p <name>` before committing
4. Agent name in config.yaml must match directory name

## 5. Polling & Delegation

### Delegate Action (Preferred)

Single call: `delegate(agent="hefesto", prompt="...", poll_interval=15, timeout=300)`

### Manual Polling Protocol
- Wait 30+ seconds before first poll
- Poll every 30+ seconds minimum
- If `response` empty but `thoughts` has content, use `thoughts`
- Cancel ONLY after 5+ polls with ALL counters at zero for 150+ seconds

## 6. Workflow Design

### Pitfalls
- Vague prompts → always use full template (CONTEXT, TASK, CONSTRAINTS, OUTPUT FORMAT, OUTPUT SCHEMA)
- Skipping quality gates → each task must pass its Daimon before proceeding
- Polling too fast → minimum 30 seconds between polls
- Chaining without visibility → always present results to user between steps

## References
- `references/athena-doc-verification.md` — Athena document verification protocol
- `references/etalides-acp-stall.md` — ACP stall diagnosis and fix
- `references/daedalus-website-pattern.md` — Website design patterns for Daedalus