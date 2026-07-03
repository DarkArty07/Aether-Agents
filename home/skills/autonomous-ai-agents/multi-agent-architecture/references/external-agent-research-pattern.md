# External Agent Research Pattern

When the user acts as intermediary between Hermes and an external agent (Claude, ChatGPT, etc.) for research tasks. Distinct from Daimon delegation — no session management, no poll/steer/close.

## When This Pattern Applies

- User says "yo me encargo de la arquitectura" or "tu deber es investigar alternativas"
- User is chatting with another AI in parallel and pasting results back
- Research needs are beyond what Etalides can do (market analysis, regulatory research, pricing)
- User prefers to use a different agent for certain research types

## Key Differences from Daimon Delegation

| Aspect | Daimon (Etalides) | External Agent |
|--------|-------------------|----------------|
| Session management | open/message/poll/close | None — user copy-pastes |
| Context | Injected via .aether, SOUL.md, project files | ZERO — agent knows nothing |
| Prompt style | Template (CONTEXT/TASK/CONSTRAINTS/OUTPUT) | Fully self-contained essay |
| Iteration | Follow-up message in same session | New prompt each round |
| Documentation | Daimon writes to project files | Hermes writes findings to project files |

## Prompt Structure for External Agents

Each prompt MUST include:

1. **Project context** (2-3 sentences — what the product is, who it's for)
2. **What's already known** (so the agent doesn't repeat findings)
3. **What specifically to research** (numbered list, scoping to avoid vague tangents)
4. **Output format** (facts vs estimates, explicit "say I don't know" for gaps)
5. **Anti-invention clause** ("No inventes datos. Si algo no existe, dilo explícitamente.")

## Iteration Protocol

```
Round 1: Broad research (competitors, regulation, market)
  → User pastes results
  → Hermes analyzes gaps
  → Hermes documents findings to RESEARCH.md via Hefesto

Round 2: Targeted research (filling gaps from Round 1)
  → Hermes crafts follow-up prompt with specific questions
  → User pastes results
  → Hermes documents again

Round 3+: Only if critical unknowns remain
  → Same cycle
  → Stop when enough for DESIGN phase
```

## Prompt Quality Checklist

- [ ] Agent knows the product name, purpose, target market, and business model
- [ ] Agent knows what research is already done (don't repeat)
- [ ] Each question is specific (not "tell me about regulation" but "what does COFEPRIS classify as SaMD")
- [ ] Agent is told to mark estimates vs facts
- [ ] Agent is told to say "not found" instead of inventing
- [ ] Output format is specified (per-question: facts, status, implication for project)

## Example (Asclepio Session, 2026-06-18)

Round 1 prompt opened with full context:
"Estamos analizando la viabilidad de un proyecto llamado Asclepio. Necesito que investigues información específica sobre el mercado y regulación de salud digital en México. No asumas nada..."

Round 2 prompt was targeted:
"Ya tenemos mapeados los competidores... No repitas nada de eso. Ahora necesito que investigues SOLO estos 4 puntos específicos: 1. Costos de Google Places API... 2. Doctoralia API... 3. Mercado de viajeros... 4. CIE-10..."

Between rounds, Hermes delegated to Hefesto to write findings to RESEARCH.md. After Round 2, enough data existed to proceed to Phase 3 (DESIGN).

## Hermes's Role in This Pattern

Hermes is NOT just a message forwarder. Between rounds:
1. Analyze the research for gaps and contradictions
2. Identify what's missing for the next pipeline phase
3. Craft the next prompt targeting those specific gaps
4. Document all findings to project files (via Hefesto)
5. Synthesize a viability assessment for the user
