# Requiem Agents — Plugin Reconstruction (v2.1)

Session log: 2026-06-24. Requiem's migration from MCP server to native hermes-agent plugin silently broke the hierarchical multi-agent architecture. This file documents the diagnosis, root causes, and reconstruction.

## The Three Critical Failures

### Failure 1: Plugin bypassed the Necromancer's decomposition

**Symptom:** Tasks that took 1 minute with MCP now took 5 minutes and produced worse results.

**Root cause:** The MCP server had 4 granular tools (decompose/execute/progress/result) that enforced the orchestrator flow. The plugin replacement collapsed these into 3 tools (investigate/execute/implement) that sent prompts directly to Shades — skipping `process_task()` (the Necromancer's decompose → route → audit loop).

**Fix:** Replaced 3 bypass tools with a single `delegate_to_necromancer(prompt, project_root)` that calls `process_task()` internally. Every entry point goes through the full orchestrator pipeline.

### Failure 2: LLM summarization blinded Raven

**Symptom:** Raven could not make quality decisions because it received compressed summaries instead of real worker output.

**Root cause:** The plugin's `_summarize_result()` function summarized any worker output >15K chars using DeepSeek V4 Flash (the cheapest model). This meant the most expensive model (Raven) was making decisions based on output filtered by the cheapest model.

**Fix:** Eliminated `_summarize_result()` entirely. Raw worker output passes to Raven with only head+tail truncation if >50K chars. Full result saved to disk for audit trail.

### Failure 3: SOUL.md contradicted config.yaml

**Symptom:** Raven tried to use read_file/search_files/terminal but the tools were disabled.

**Root cause:** The SOUL.md told Raven to "read code using read_file, search_files, and terminal" but config.yaml had `disabled_toolsets: [terminal, file]`. This contradiction caused Raven to fail and degrade.

**Fix:** Rewrote SOUL.md to match reality — Raven NEVER reads code, NEVER writes code, NEVER executes commands. Its ONLY code interaction is `delegate_to_necromancer`.

## Structured Delegation Template

Designed for the assistant→orchestrator handoff:

```
OBJETIVO: [What to achieve — technical specifics: filenames, functions, expected behavior]
CONTEXTO: [Stack, project structure, conventions, relevant files from graphify exploration]
RESTRICCIONES: [What NOT to do — edge cases, scope limits, existing dependencies to avoid]
CRITERIOS DE ACEPTACION: [How to verify completion — the Revenant uses this for audit]
```

The CRITERIOS section is the most important: it gives the Revenant concrete test conditions, turning vague "looks good" audits into pass/fail decisions.

## Graphify as Read-Layer

Added graphify as MCP server in Raven's config.yaml (separate from Aether Agents' graphify instance):

```yaml
graphify:
  command: /home/prometeo/Requiem/raven/.venv/bin/python3.11
  args:
    - -m
    - graphify.serve
    - /home/prometeo/Requiem/graphify-out/graph.json
  enabled: true
  timeout: 60
```

Graph: 10,175 nodes, 15,520 edges, 9.2MB. AST-only generation (no API cost).

Custom indexer.py (244 lines) discontinued in favor of the graphify MCP server — graphify is more specialized and self-maintaining.

## Files Modified

| File | Change |
|------|--------|
| `raven/plugins/requiem_tools/schemas.py` | 3 schemas → 1 DELEGATE_SCHEMA with template in description |
| `raven/plugins/requiem_tools/tools.py` | 3 handlers → 1 `handle_delegate_to_necromancer`; imports `process_task`; `_summarize_result` removed; `_MAX_RESULT_CHARS` 30K→50K |
| `raven/plugins/requiem_tools/__init__.py` | Registers 1 tool instead of 3 |
| `raven/plugins/requiem_tools/plugin.yaml` | v0.2.0, provides: delegate_to_necromancer |
| `raven/plugins/requiem_tools/indexer.py` | DELETED — replaced by graphify MCP |
| `raven/SOUL.md` | Rewritten: never touches code, explores via graphify, delegates with template |
| `raven/config.yaml` | graphify MCP server added |
| `DESIGN.md` | Clasificación arquitectónica formal appended |
| `PLAN.md` | Rewritten with reconstruction plan |

## Lesson for Future Migrations

When migrating a multi-agent system between integration mechanisms (MCP ↔ plugin), always verify that:
1. The orchestrator's decomposition phase is still in the call path for ALL entry points
2. Worker output reaches the expensive model unmodified (or with generous truncation, never LLM summarization)
3. The SOUL.md matches the actual enabled toolsets — no contradictions
4. The assistant has a code-understanding mechanism (graphify or similar) if file tools are disabled
