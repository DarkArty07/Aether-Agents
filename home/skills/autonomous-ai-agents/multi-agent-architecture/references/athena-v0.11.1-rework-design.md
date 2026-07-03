# Athena v0.11.1 Rework Design

## Current State (v0.10.x)

- **SOUL.md**: 342 lines
- **Identity**: Security Engineer
- **Type**: Generic Daimon with workflow context
- **Model**: kimi-k2.6
- **Toolsets**: terminal, file, search_files, execute_code, memory, skills
- **Capabilities**: receives_from, threat-modeling, security-review, dependency-audit, risk-communication

## Architectural Changes

| What | Before | After |
|------|--------|-------|
| Type | Generic Daimon with LangGraph workflows | Consultant-Analyst |
| Role | security-engineer | security-analyst |
| SOUL.md | 342 lines | ~110 lines |
| Toolsets | terminal, file, search_files, execute_code, memory, skills | file, terminal, skills |
| Capabilities | receives_from, threat-modeling, security-review, dependency-audit, risk-communication | receives_from, threat-modeling, security-review |

## What Was Removed from SOUL.md

| Section | Lines | Reason |
|---------|-------|--------|
| §7 "In Workflow Context" | ~30 | LangGraph/workflows don't exist in olympus_v3 |
| Protocol 2 (Security Review Checklist) | ~35 | Moved to `athena-security-checklists` skill |
| Protocol 3 (Dependency Audit) detailed version | ~15 | Contracted; detailed version in skill |
| Protocol 4 (Risk Communication — Ariadna) | ~10 | Athena reports to Hermes only, not Ariadna |
| Two Protocol 5s | ~25 | Duplicate output format + dead reference removed |
| Few-Shot Examples A and B | ~60 | Moved to `athena-security-checklists` skill |
| `execute_code` toolset | — | Athena doesn't execute code |
| `memory` toolset | — | Single-turn consultant, no persistent state |
| `search_files` separate toolset | — | Already bundled in `file` |
| `dependency-audit` capability | — | Merged into security-review |
| `risk-communication` capability | — | All Daimons communicate via Hermes |

## What Was Added

- **Context-aware severity guidance** in §8 Protocol — Risk Assessment
- **Explicit Consultant-Analyst type** in §1 Identity
- **"Do NOT write files"** hard limit in §4
- **Skill reference** in §5 pointing to `athena-security-checklists`
- **Compact STRIDE table** in §7 (was verbose list)
- **YAML comments** in config.yaml.template explaining toolset justifications
- **English description** in config (was Spanish)
- **`__AETHER_ROOT__` placeholder** in template external_dirs (was hardcoded path)

## Config Drift Fixed

| Field | Old (config.yaml) | New |
|-------|-------------------|-----|
| role | security-engineer | security-analyst |
| description | "Security Engineer del ecosistema..." (Spanish) | "Security Analyst (Consultant-Analyst)..." (English) |
| capabilities | +dependency-audit, +risk-communication | removed (merged) |
| toolsets | +search_files, +execute_code, +memory | removed |
| external_dirs | hardcoded path | __AETHER_ROOT__/home/skills |
| YAML comments | None | Toolset justifications added |

## Skill Created: athena-security-checklists

Location: `home/skills/red-teaming/athena-security-checklists/`

Contains:
- `SKILL.md` — Compact guide with STRIDE table and review categories
- `references/security-review-checklist.md` — Full detailed checklist
- `references/dependency-audit-protocol.md` — Full audit protocol
- `references/few-shot-examples.md` — Examples A and B from original SOUL.md