# Etalides v0.10.0 Rework — Case Study

**Date:** 2026-05-19
**Branch:** `feature/etalides-rework` → merged to `dev`
**Commit:** `e429d8f` (main), `5a6d01e` (template fix)

## Before (v0.9.0)

- SOUL.md: 417 lines — manual de referencia, no system prompt
- Role: "Web Researcher puro" (Spanish)
- Toolsets: web, browser, file
- Model: deepseek-v4-flash
- `link_budget` concept counting only web actions
- 5 few-shot examples (80+ lines)
- Curl fallback technique embedded in SOUL.md (200+ lines)
- Output format defined TWICE (§6 and Protocol 4)
- Hard limits defined TWICE (§4 and Protocol 5)
- Research persisted to `AETHER_HOME/research/` — plain markdown, no frontmatter

## After (v0.10.0)

- SOUL.md: 126 lines — role-focused system prompt
- Role: "Researcher — internet and codebase contact for deep investigation" (English)
- Toolsets: web, browser, file, terminal
- Model: deepseek-v4-flash (unchanged — confirmed by Chris)
- `action_budget` concept counting web + file + terminal actions
- 0 few-shot examples (format is self-evident from structure)
- Curl fallback and search strategy moved to skill (on-demand)
- Output format defined ONCE
- Hard limits defined ONCE
- New: Code Research Protocol with tool hierarchy (search_files → read_file → terminal)
- New: Dual persistence — web research → Obsidian vault, code research → direct response to Hermes
- New: `code-search` capability added

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| Skills are on-demand, not bloat | Chris corrected this assumption — don't prune skill lists |
| Terminal as secondary tool | For `git log`, `wc -l`, `grep -c`, `radon cc` — structure analysis that file tools can't do |
| Dual persistence model | Web knowledge is reusable (→ Obsidian), code answers are situational (→ response only) |
| Obsidian-flavored research | YAML frontmatter, wikilinks, tags — openable in any Markdown editor, fully functional in Obsidian |
| Research at `__AETHER_ROOT__/research/` | Universal path — anyone cloning has the structure ready |
| config.yaml documented toolsets | Each toolset has an inline comment explaining WHY it's included |
| No pruning of skills | Skills load on-demand when the agent decides it needs them |

## User Corrections Applied

1. **"Skills are loaded on-demand, not bloat"** — I initially proposed pruning Etalides' skill list. Chris corrected: skills load when the agent requests them, not at session start. A large skill list is more options, not more context cost.

2. **"The config was already excellent"** — I proposed changing all toolsets. Chris pointed out only `terminal` was missing and the toolsets were correct. Don't over-change what works.

3. **"Research persistence distinction"** — I proposed persisting all research to Obsidian. Chris distinguished: web research persists (reusable knowledge), code research delivers directly to Hermes (situational).

4. **"Terminal only when file tools insufficient"** — I proposed terminal as a primary tool. Chris specified: terminal is secondary, only when search_files and read_file can't do the job.

5. **"Add explanatory README and push to GitHub"** — The research/ directory needed a README.md and .obsidian/ config so anyone cloning can use it.

## config.yaml.template Drift Bug

Etalides' test run found that `config.yaml.template` was out of sync with the live `config.yaml`:
- `role: web-researcher` (stale) instead of `role: researcher`
- Description in Spanish instead of English
- Missing `code-search` capability
- Missing `terminal` toolset

This is a recurring pattern: after updating live config, always update the template too.

## Files Changed

| File | Change |
|------|--------|
| `home/profiles/etalides/SOUL.md` | 417→126 lines, complete rewrite |
| `home/profiles/etalides/config.yaml` | Added terminal, code-search, updated description/role |
| `home/profiles/etalides/config.yaml.template` | Synced with live config (separate commit) |
| `home/SOUL.md` | Routing table: split "Web/codebase research" into two rows + Code research rule |
| `research/.gitkeep` | New vault directory |
| `research/README.md` | Documentation for the vault |
| `research/.obsidian/app.json` | Obsidian config |
| `research/.obsidian/workspace.json` | Obsidian workspace |
| `research/INDEX.md` | Index of existing research files |