# Daedalus v0.10.1 Rework — Design Decisions

**Date:** 2026-05-20
**Branch:** pending (feature/daedalus-rework, not yet created)
**Based on:** `dev` at commit `5a6d01e`

## Identity Shift

| Aspect | Before (v0.9.0) | After (v0.10.1) |
|--------|-----------------|------------------|
| Role | Frontend Developer | Consultant-Creator (UX/UI Design) |
| Type | Actor (implicit) | Consultant-Creator (explicit) |
| Writes | Production code | Prototypes only (HTML/CSS mockups) |
| SOUL.md | 296 lines, implementation-focused | Target: 80-130 lines, consultation-focused |

## Toolset Decisions

Current config (v0.9.0):
```yaml
toolsets:
  - terminal
  - file
  - search_files
  - patch
  - execute_code
  - skills
```

Proposed changes:

| Tool | Decision | Rationale |
|------|----------|-----------|
| `file` | Keep | Needs `read_file` for codebase review + `write_file` for prototypes |
| `search_files` | Keep | Needs to find relevant files in codebase |
| `terminal` | Keep | Secondary tool (git, structure analysis) |
| `skills` | Keep | Loads design patterns on demand |
| `patch` | **Remove** | Consultant-Creator prototypes from scratch, doesn't patch production files |
| `execute_code` | **Remove** | Doesn't need arbitrary code execution — prototypes are static HTML/CSS |

**Open question (pending Chris decision):** Does Daedalus need the `file` toolset for `write_file` to create HTML/CSS prototypes? Alternative: Daedalus delivers prototype code in its response and Hefesto writes it. But this breaks the "prototype and iterate" loop — Daedalus needs to see files it created to iterate on them.

**Resolution (from session):** Daedalus IS a Consultant-Creator. It prototypes. Prototyping requires writing files. So `file` (which includes `write_file`) stays. But `patch` and `execute_code` go — those are Actor tools.

## Consulting Output Format

Daedalus' standard response format for consultations:

1. **Observations** — What works, what's well-designed
2. **Risks** — What could go wrong, UX anti-patterns, accessibility gaps
3. **Recommendations** — Specific, actionable, prioritized changes
4. **Prototype (optional)** — If the task warrants it, an HTML/CSS mockup

## Hermes SOUL.md Changes (Pending)

### §6 Routing Table
- Change `| UX/UI design | Daedalus | delegate |` to `| Design consultation | Daedalus | delegate |`
- Add **Consultation rule:** "When you need expert design, architecture, or security opinion, delegate to the right consultant..."

### §7 Workflow Patterns
- `Feature` pattern: `Etalides → Daedalus (consult) → Hefesto → Athena`
- Daedalus is marked as a **consultation** step, not an implementation step

### §13 Complete Rewrite
- Remove all references to the non-existent `consult` tool
- Document the delegate-based workflow with agent types table
- Include consultant prompt format and sequential consultation pattern
- Map each consultant to their domain (Daedalus → UX, Ictinus → architecture, Athena → security)

## Ictinus Note

Ictinus (Backend Architect, Consultant-Analyst) has a **completely empty SOUL.md** (0 lines). It falls back to hermes-agent's default prompt with no customization. This is a known gap — scheduled for v0.10.2. Ictinus should NOT have `execute_code`, `patch`, or `write_file` — it only reads and opines.

## Reference: Test Consultation

Daedalus was tested via `delegate` during the v0.10.0 session with this prompt:

> PROJECT_ROOT: /home/prometeo/Aether-Agents
> CONTEXT: Setting up a research persistence vault for Etalides...
> TASK: Review this structure and provide design feedback...

Daedalus responded with Observations/Risks/Recommendations/Summary Table format — the consultation format worked naturally without the `consult` tool. This validates the delegate-based approach.