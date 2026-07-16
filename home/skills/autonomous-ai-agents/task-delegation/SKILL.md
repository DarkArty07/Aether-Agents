---
name: task-delegation
description: "Delegate tasks to specialist Daimons — decompose, delegate, monitor, and report results."
version: 1.6.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [delegation, orchestration, daimons, monitoring, workflow]
    related_skills: [kanban, claude-code, codex, opencode]
---

# Task Delegation

Delegate implementation work to specialist Daimons (Hefesto, Etalides, Athena, etc.). Hermes plans, decomposes, coordinates, and implements fine-tuning directly (v0.16.0 "Hermes Can Write Now"). Bulk implementation goes to Hefesto; small precise edits, config tweaks, bug fixes, and doc edits are Hermes' domain.

## When to Delegate vs Implement Directly (v0.16.0+)

**Decision rule:**
- **Fine-tuning** (small edit, config, bug fix, doc tweak, 1-3 file change) → Hermes implements directly
- **Bulk implementation** (scaffolding, new feature, multi-file refactor) → Hefesto
- **Research** (web or codebase) → Etalides
- **Security review** → Athena
- **Design/UX consultation** → Daedalus
- **Backend architecture** → Ictinus

If a fine-tuning task takes >3 turns and isn't done → delegate to Hefesto as bulk.

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

- **Hermes fine-tuning vs delegation threshold (v0.16.0+)** — As of v0.16.0 "Hermes Can Write Now", Hermes has `write_file`, `patch`, and `search_files` tools and is expected to handle fine-tuning directly. The old pitfall ("Hermes is blocked from writing files directly") is OBSOLETE. The new rule: if a task is fine-tuning (small edit, config, bug fix, 1-3 files), Hermes does it directly. If it's bulk (scaffolding, new feature, multi-file refactor), delegate to Hefesto. If a fine-tuning task exceeds 3 turns without finishing, escalate to Hefesto as a bulk task with full context.

- **Hermes using process.wait on Daimon sessions** — `process(action="wait")` only works for terminal processes with `background=true`. Use `talk_to(action="poll")` for Daimon sessions. Same session_id format but different tools and command structure.

- **docker compose up -d blocked by Hermes terminal** — Hermes detects `docker compose up -d` as a "long-lived server" even though `-d` detaches immediately. Always delegate Docker start/stop commands to Hefesto, or use `terminal(background=true, notify_on_complete=true)` if doing it directly.

- **Hefesto's "Nothing to save" last_turn is unreliable after structured task delegation** — When a structured task has clear PASS/FAIL-shaped tool calls (e.g., 4 git commands, 3 file writes, all completed) but the final `last_turn` is a meta-reflection like "Nothing to save — this was mechanical" or "Nothing to learn from this session", DO NOT trust the last_turn alone. Verify actual state directly: `git diff` for commits, `ls -la` for new files, `head -5 <file>` for version bumps. The "Nothing to save" line is Hefesto's reflection on the meta-session (whether the conversation itself produced a skill-worthy insight), not on the task (which is often done correctly). Pattern: when last_turn is reflective AND recent_tool_calls show completed work, treat the work as done and verify directly. Pattern: when last_turn is reflective AND recent_tool_calls show a stall or skipped work, then trust the "Nothing to save" signal.

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

### Pitfall #N — Hefesto "Nothing to Save" Last-Turn Is Unreliable

**Síntoma:** Le delegas una tarea estructurada y con comandos copy-pasteables a Hefesto. Hefesto ejecuta todos los comandos correctamente, hace el trabajo, pero su `last_turn` final en el `poll()` reporta `"Nothing to save. This session was purely mechanical"` en vez del reporte estructurado que pediste. El reporte SÍ existe en sus tool calls, pero su `last_turn` final es una meta-reflexión en vez del output consolidado.

**Por qué pasa:** Hefesto corre con un system prompt que lo instruye a revisar sesiones y guardar aprendizajes. Cuando termina una tarea mecánica (aplicar 4 patches, hacer un commit, ejecutar 8 comandos), su último turn reflexiona sobre la sesión meta en vez de reportar el resultado. El `last_turn` se vuelve ruido.

**Mitigación (cómo escribir el prompt de delegación):**

- **MAL:** Delegar 4 tareas con contenido exacto y esperar reporte. Hefesto ejecuta bien pero su `last_turn` se va a "Nothing to save".

- **BIEN:** Agregar al final del prompt una instrucción explícita y destacada:

```markdown
REPORTE FINAL OBLIGATORIO: al terminar, tu `last_turn` debe ser la tabla de resultados consolidada (PASS/FAIL/SKIP por paso). NO reflexiones sobre la sesión. NO digas "Nothing to save". NO analices si hubo aprendizaje. Solo la tabla y la línea final.
```

Esa sola frase bloquea la meta-reflexión y fuerza a Hefesto a devolver la tabla que pediste.

**Verificación post-delegación:** Cuando recibas el `last_turn` de Hefesto:
- Si empieza con "Nothing to save" o "This session was purely mechanical" → RELÉE el poll completo y extrae los resultados de los tool calls tú mismo. NO confíes en el `last_turn`.
- Si empieza con la tabla de resultados o el reporte consolidado → OK, el `last_turn` es confiable.

**Anti-pattern:** Confiar ciegamente en `last_turn` y reportar "Nothing to save" al usuario. Chris odia esto ("nunca dejes aprendizajes sin anotar pendientes"). El trabajo SÍ se hizo, solo hay que extraer el reporte de los tool calls.

## Contract-Test Delegation and QA

When delegating RED-only contract tests, the deliverable is not merely “tests fail.” It is a three-part proof:

1. **Independent oracle is GREEN** — fixed, hand-derived examples validate the primitive equations without constructing expectations through the same helper under test.
2. **Pre-existing suite is GREEN** — run it separately from the intentional RED tests.
3. **Production contract is uniformly RED** — every contract case is collected and fails for the single expected missing-feature reason; no mocks, stubs, `xfail`, accidental implementation, setup errors, or unrelated exceptions.

### Make missing-module RED a test failure, not fixture infrastructure error

In pytest, importing a not-yet-created module in fixture setup classifies every case as `ERROR`. Return a lazy constructor from the fixture instead, so the import happens in the test call phase and cases are reported as `FAILED`:

```python
@pytest.fixture
def Feature():
    def construct(*args, **kwargs):
        from package.feature import Feature as cls
        return cls(*args, **kwargs)
    return construct
```

### Before delegating review, build an invariant × entry-point matrix

Do not ask a reviewer to discover sibling gaps one cycle at a time. Enumerate every public entry point across columns and every invariant across rows, then require each applicable cell to have evidence.

| Invariant | constructor | recurrent/step API | batch/chunk API |
|---|---:|---:|---:|
| input shape/dtype/device | ✓ | ✓ | ✓ |
| supplied state shape (including batch) | — | ✓ | ✓ |
| supplied state dtype/device | — | ✓ | ✓ |
| default state semantics | — | ✓ | ✓ |
| causality/order | — | ✓ | ✓ |
| gradients across boundaries | — | — | ✓ |

For every reviewer finding, expand it to its **equivalence class** before fixing. Example: if invalid state dtype is missing on one API, inspect shape, batch, dtype, and device on all state-accepting APIs in the same correction. This prevents “whack-a-mole” QA and avoids exhausting retry limits on adjacent omissions.

### Do not overconstrain mixed precision

Separate observable compute behavior from parameter-storage policy:

- Contract projection/output dtypes and FP32 accumulation/state explicitly.
- Do not require `weight.dtype == compute_dtype` unless the architecture deliberately forbids FP32 master weights.
- Build expected projections from public weights cast to the compute dtype, then compare state against an independent FP32 scan.
- Parameterize CPU and accelerator paths when both are contractual; skip only when capability is genuinely unavailable.

### Re-review preflight

Before consuming another independent-review cycle:

- [ ] Re-run the full invariant × entry-point matrix.
- [ ] Verify all siblings of each prior finding, not only the literal reported line.
- [ ] Run oracle GREEN, regression GREEN, and intentional RED as separate commands.
- [ ] Record exact counts: passed / failed / errors / skipped and the common RED cause.
- [ ] Confirm no production file, mock, stub, or fallback was introduced.
- [ ] Run lint, format check, and diff whitespace check.

Detailed worked pattern: `references/contract-tdd-qa.md`.

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