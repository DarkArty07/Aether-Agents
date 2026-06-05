---
name: task-delegation
description: "Delegate tasks to specialist Daimons — decompose, delegate, monitor, and report results."
version: 1.4.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [delegation, orchestration, daimons, monitoring, workflow]
    related_skills: [kanban, claude-code, codex, opencode]
---

# Task Delegation

Delegate implementation work to specialist Daimons (Hefesto, Etalides, Athena, etc.). Hermes plans, decomposes, and coordinates — never implements directly.

## When to Delegate

- **Code implementation** → Hefesto
- **Research (web or codebase)** → Etalides
- **Security review** → Athena
- **Design/UX consultation** → Daedalus
- **Backend architecture** → Ictinus

## Delegation Workflow

### 1. Decompose

Break tasks into atomic units:
```
[#1] Task type — description
  → Daimon: [who]
  → CONTEXT: [what they need to know]
  → CONSTRAINTS: [hard limits]
  → ACCEPTANCE: [testable criteria]
```

### 2. Delegate

Use `delegate` for single tasks (auto-polls, returns result + session_id):
```
talk_to(action="delegate", agent="hefesto", prompt="...", project_root="...")
```

Use `open` + `message` for multi-turn conversations or when you need the session_id upfront.

### 3. Monitor

**Wait for completion silently.** Only report status if stuck >2 minutes.

**Pitfall — Verbose narration:** Don't describe every tool call ("Hefesto just read docker-compose.yml..."). Poll internally, report final result or ask for status if progress stalls.

### 4. Report

Synthesize results for the user:
- What was done
- Files created/modified
- Verification steps performed
- Any blockers or next steps

## Common Pitfalls

- **Asking for confirmation when path is clear** — If the user says "finish the plan" or "don't ask, just do it", proceed with execution. Don't present options or ask for approval when the task is obvious from context.

- **Verbose polling narration** — Don't narrate every tool call during monitoring. Wait for completion or report status only if stuck >2 minutes.

- **Timeout too short** — Complex tasks (5+ phases) may need 600s+. If delegate times out, check if the session is still active with `poll`.

- **Not closing sessions** — Always `close()` sessions when done. Open sessions consume resources.

- **Retrying failed approaches** — If delegation returns 0 tool_calls and status "completed", the Daimon config is missing. Run `setup.sh`, don't retry delegation.

- **Hefesto over-investigates source code when given a diagnostic prompt with "smoke test" intent** — Hefesto's default for "verify X works end-to-end" prompts is to read the tool's source code (`__main__.py`, `llm.py`, etc.) to find the exact CLI flags before running anything. For a 1-2 minute smoke test this burns 6+ minutes of investigation. **Mitigation:** when delegating a smoke test, include the EXACT command line — flags, env vars, expected output — not just the goal. If Hefesto is already investigating past 4 minutes without executing, `cancel` and re-delegate with a command-only prompt (no source-reading invitation). This is the operational pattern that complements the broader "stick to the plan" rule: for smoke tests, the plan IS the command.

- **Trusting delegation "completed" status blindly** — Daimons may report "completed" even when the actual work is incomplete or broken. Always verify the result: check that files exist with correct content, services are reachable (health endpoints), and the output matches acceptance criteria. Examples: Hefesto claimed docker-compose.yml was done but it was missing the deriver service and had wrong DB credentials; containers showed "Created" but never actually started. Verification caught these.

- **Hermes attempting to write files** — Hermes is blocked from writing files directly (cat, echo, write_file). When mid-task you discover a file needs editing or creation, delegate to Hefesto even for small fixes. Trying to write directly wastes turns and returns errors like "Delegate. You are an orchestrator, not an implementer."

- **Hermes using process.wait on Daimon sessions** — `process(action="wait")` only works for terminal processes with `background=true`. Use `talk_to(action="poll")` for Daimon sessions. Same session_id format but different tools and command structure.

- **docker compose up -d blocked by Hermes terminal** — Hermes detects `docker compose up -d` as a "long-lived server" even though `-d` detaches immediately. Always delegate Docker start/stop commands to Hefesto, or use `terminal(background=true, notify_on_complete=true)` if doing it directly.

### Pitfall #N — Hefesto Over-Investigates Source Code on Diagnostic Prompts

**Síntoma:** Le pides a Hefesto un smoke test (curl + python + verificar resultado). En vez de ejecutar, abre el código fuente de la herramienta (`__main__.py`, `llm.py`, etc.) y se queda leyendo/grep-eando durante 5+ minutos. 50+ tool calls, ningún comando de smoke test ejecutado. La sesión se alarga innecesariamente.

**Causa:** El prompt dice "verifica cómo funciona X" o "investiga los flags exactos". Hefesto interpreta "investiga" como "lee el source code", no como "ejecuta y reporta". El costo es: tiempo (5-10 min) + tokens (modelo caro leyendo archivos).

**Prevención (cómo escribir el prompt de delegación):**

- **MAL:** "Verifica que graphify funcione con deepseek-v4-flash. Investiga los flags exactos de `graphify extract` y corre un smoke test."

  → Hefesto lee 800 líneas de `__main__.py` buscando flags.

- **BIEN:** "Ejecuta EXACTAMENTE estos 3 comandos. NO leas código fuente. Reporta output crudo:
  ```bash
  curl -sS ... -H 'Authorization: Bearer $KEY' https://api/...
  python -m foo.bar --flag-a --flag-b
  systemctl --user status foo
  ```"

  → Hefesto ejecuta y reporta en 3-5 tool calls.

**Regla de oro para smoke tests:** El prompt debe contener comandos copy-pasteables Y una frase de prohibición explícita: "NO leas código fuente, NO investigues, NO busques flags — solo ejecuta y reporta". Sin esa frase, Hefesto puede caer en modo investigación.

**Cuándo SÍ dejar investigar:** Si el problema es genuinamente un bug de comportamiento y no hay comandos obvios para verificar. En ese caso, sí se justifica leer source. Pero el smoke test puro (verificar que algo funciona) NUNCA debe requerir leer código.

## Multi-Task Coordination

For batch workflows (multiple sequential tasks):
- Decompose all tasks upfront
- Delegate sequentially or in parallel based on dependencies
- Don't gate-check between steps unless there's a genuine decision point
- Report final consolidated result

## Quality Gates

Hermes gates at each Daimon handoff. Present results to user for approval before proceeding, UNLESS:
- User explicitly said "don't interrupt until done"
- Tasks are mechanical (no architectural decisions)
- User is in autonomous mode

## Session Management

- **delegate** — Open + message + auto-poll. Returns result + session_id. Session stays open.
- **open** — Spawn Daimon. Returns session_id. Use for multi-turn.
- **message** — Send prompt or follow-up to open session.
- **poll** — Check status (thoughts, messages, tool_calls, recent_tool_calls).
- **close** — End session. ALWAYS close when done.
- **cancel** — Force-terminate stuck session.

## Troubleshooting

### Delegate returns empty result
**Cause:** Daimon config.yaml missing.
**Fix:** Run `bash scripts/setup.sh` to regenerate configs.

### Session times out but work is ongoing
**Cause:** Timeout too short for task complexity.
**Fix:** Increase timeout or use `open` + `message` + manual `poll`.

### Daimon asks for clarification
**Fix:** Use `message` on same session_id to respond, don't restart delegation.