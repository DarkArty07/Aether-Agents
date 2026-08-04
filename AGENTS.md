# Aether Agents — Project Context

This file is the canonical project context. It is read automatically by hermes-agent, Cursor, and Claude Code.

## v0.22.0 Olympus retirement candidate

The candidate contains no `src/olympus_v3`, ACPManager, lifecycle database, Olympus hooks, MCP facade, CLI, profile plugins, configuration block, entry point, or runtime dependency. `talk_to`, `discover`, `aether_status`, `aether_update`, and `aether_curate` are not provided by the candidate. Identity, contracts, budgets, evidence, effects, review, closure, continuity, and default-off self-improvement remain under `src/aether_agents`. Multi-agent execution is intentionally unavailable until a replacement passes isolation, lifecycle, cleanup, recovery, and rollback gates. Do not create a compatibility shim or hidden fallback.

## v0.19.0 experimental coordination closeout

v0.19.0 is frozen at R11 as an experimental, default-off baseline and is not operationally validated. R7 shadow is observational; R8 is legacy-blocked; R9–R11 have deterministic evidence. At that historical boundary, `talk_to -> ACPManager` remained authoritative; that path has since been retired in the v0.22.0 candidate. R12–R14, active kernel composition, a kernel-backed pilot, production migration/rollback, activation, merge, tag and publication were outside the v0.19 closeout. Canonical truth: `docs/releases/v0.19.0-autonomous-coordination/RELEASE_CLOSEOUT.md`.

## v0.19.x incremental kernel migration

The v0.19.x roadmap is closed at v0.19.5 with verdict `VIABLE — BOUNDED`. The demonstrated topology covers one source, two immutable candidate successors, one deterministic committed selection, trusted semantic handoff, cleanup and zero survivors. v0.19.6 was closed without a separate patch; it is not pending. Harmonia remains default-off, and v0.19.5 remains an unpublished technical candidate. Canonical truth: `docs/releases/v0.19.x-kernel-migration/ROADMAP_CLOSEOUT.md`.

## Aether self-improvement cycle

**Operating policy** — no specialist execution runtime is registered in this candidate. Hermes may perform bounded implementation directly; work that materially requires an unavailable specialist stops as an explicit capability gap. Never introduce a hidden `talk_to`, Harmonia, ACP, or renamed fallback. Preserve and classify failures, verify cleanup, and accumulate evidence without presuming or approving the replacement architecture. Other projects must never mutate Aether incidentally. Read `docs/knowledge/SELF_IMPROVEMENT_CYCLE.md` and the active manifest `docs/releases/v0.20.0/CYCLE.yaml`.

**What is enforced by code, and what is not.** The default-off measurement substrate implements project-identity verification, a redacted project-local ledger, interruption recording, and deterministic evidence projection that cannot approve a version. Historical Harmonia wire classification was removed with its runtime. The substrate does **not** implement takeover gating, failure-class classification, repair verification, retry correlation, an evaluator, before/after comparison, or rollback. No causal claim that Aether improved can currently be derived from it.

The plugin is absent from `plugins.enabled` in the versioned template and plugins are opt-in, so **no installation participates automatically**; an operator must enable `aether-self-improvement` explicitly. A template-based install has no general delegation or Aether MCP path.

PDR-0009 governs the self-improvement policy. Phase 1 truthful-instrumentation corrections are independently accepted in `docs/releases/v0.20.0/INDEPENDENT_PHASE1_REVIEW.md`; causal self-improvement remains unimplemented. Replacement-runtime activation, credentials, restart, live pilot, deployment and production publication remain separately gated. Git commits, pushes, pull requests, merge to `main`, annotated tags and GitHub Releases follow the standing automation authority and deterministic gates in `docs/decisions/ODR-0001-main-integration-and-release-automation.md`. Findings, severities and the remediation plan: `docs/releases/v0.20.0/EXTERNAL_LOGIC_AUDIT.md`.

## Git Conventions

### Branching Model

```text
feature/{name}  →  main
```

- **`main`** — Latest integrated, tested repository state. It may be ahead of the latest published version while unreleased capabilities remain default-off.
- **`feature/{name}`** — One bounded change or candidate. Branch from the current `origin/main`, merge back to `main` through a PR, then delete it.
- **Tag / GitHub Release** — Official published version. Publication is separate from integration and must point to a commit already on `main`.

**Rules:**
1. Never commit or develop directly on `main`; use a feature branch and PR.
2. Every normal PR targets `main`. Stacked PRs are forbidden unless a versioned decision explicitly records the dependency, merge order and removal deadline.
3. Before opening a new SemVer candidate, the previous candidate must be `MERGED`, `ABANDONED`, or `SUPERSEDED`; `CLOSED` without one of those dispositions is invalid.
4. A roadmap may close technically while publication remains pending, but the next SemVer candidate must not start on top of an unmerged predecessor.
5. Merge to `main` does not imply activation, deployment, tag or GitHub Release.
6. Delete merged feature branches and reconcile issues, PRs and continuity immediately after integration.
7. Run `python scripts/check_release_governance.py preflight-next-version --version X.Y.Z` from a clean, synchronized `main` before creating a new version branch.

### Standing GitHub Automation Authority

For Aether Agents, the product owner grants agents standing authority to perform routine GitHub lifecycle operations without per-action confirmation:

- create atomic local commits;
- push feature branches;
- create, update, retarget and mark PRs ready;
- enable auto-merge or merge a PR after required checks pass;
- delete merged branches;
- create annotated SemVer tags on the integrated `main` commit;
- create or reconcile GitHub Releases for those tags;
- update and close related issues and milestones when their merge conditions are satisfied.

This authority applies only when the exact committed candidate passes its required gates in a clean checkout, the PR targets `main`, CI is green or an explicitly documented equivalent gate exists, and no unresolved release blocker remains. Agents must not force-push shared history, bypass required checks, merge a red or ambiguous candidate, publish secrets, or treat GitHub integration as authorization for runtime activation, deployment, data migration, credential changes, spending or production effects.

### Versioning

Semantic versioning: `MAJOR.MINOR.PATCH`

- **PATCH** (`0.5.1`) — Bug fixes, hotfixes, minor improvements. No new features.
- **MINOR** (`0.6.0`) — New features, new Daimons, new MCP actions. Backward compatible.
- **MAJOR** (`1.0.0`) — Breaking changes. API changes, configuration migration required.

Tag format: `v{version}` (e.g., `v0.5.1`, `v0.6.0`)

**Approved experimental exception:** the default-off v0.19.x kernel migration uses micro-patches v0.19.1–v0.19.6 so each authority hypothesis can freeze or stop independently. These patches do not imply production readiness and retain separate implementation and live-execution gates. Their integrated outcome is published through v0.20.0 rather than as separate public v0.19.x tags.

### v0.20.0 (2026-07-28)

- **release**: Official package metadata, `main`, annotated tag, and GitHub Release identify v0.20.0.
- **coordination**: The v0.19.x bounded Harmonia foundation is integrated but remains default-off; it does not claim general planning, global replacement, or production activation.
- **instrumentation**: The `aether-self-improvement` plugin provides privacy-preserving, project-scoped measurement and deterministic evidence while remaining disabled by default.
- **honesty**: Independent review accepts truthful instrumentation only. Causal evaluation, candidate isolation, promotion, activation, restart, and deployment remain future gates.
- **governance**: ODR-0001 keeps `main` integrated and automates gated PR, merge, tag, and GitHub Release operations without conflating them with runtime effects.
- **verification**: The exact release tree passes 54 self-improvement tests, 944 coordination tests, 1198 repository tests, Ruff, compileall, build, policy, and CI on Python 3.11/3.12.

### v0.18.2 (2026-07-16)

- **release**: Public metadata is synchronized to v0.18.2; v0.18.1/v0.18.0 history remains preserved.
- **fix**: Olympus ACP permissions now match installed ACP 0.9.0, selecting the least-privilege offered allow option deterministically or denying when none is offered.
- **lifecycle**: Async context-manager and subprocess ownership are distinct, with exact-once normal teardown and bounded fallback; real `aether_curate` E2E and all 121 tests pass. No runtime config/template migration is required.

### v0.18.1 (2026-07-16)

- **release**: Public metadata is synchronized to v0.18.1; v0.18.0 reliability evidence remains preserved at `docs/releases/v0.18.0-daimon-reliability/BENCHMARK_REPORT.md`.
- **fix**: `aether_curate` now waits for Ariadna completion, verifies a fresh `CONTEXT.md`, and preserves non-success ACP and curation outcomes.
- **verification**: Bounded timeout plus clarification, stale/invalid artifact, and strict schema/footer checks are covered by 90 focused tests and the 113-test suite; no runtime config/template migration is required.

### v0.18.0 (2026-07-16)

- **release**: Public release metadata is synchronized to v0.18.0; see `docs/releases/v0.18.0-daimon-reliability/BENCHMARK_REPORT.md` for the versioned reliability evidence.
- **reliability**: Six Daimon profiles now carry role-specific evidence/verification contracts. The isolated 19-case baseline and post runs each recorded 23 PASS, 0 FAIL, and 5 INSUFFICIENT trace/function assertions; INSUFFICIENT is not a pass because `hermes -z` exposes no traces.
- **config**: Templates and runtime configuration remain intentionally unchanged after parity verification; benchmark evidence did not justify tuning.

### v0.17.0 (2026-07-16)

- **release**: Public documentation and release metadata synchronized to v0.17.0; tracked configuration schema is v32.
- **models**: Hermes primary route is `openai-codex/gpt-5.6-sol`; all six Daimons use `openai-codex/gpt-5.6-terra` with profile-specific OpenRouter fallbacks retained for continuity.
- **exception**: Graphify intentionally uses `llmgateway/deepseek-v4-flash` for semantic inference; this is an explicit integration exception, not stale routing.
- **security**: Honcho documentation now states the network boundary correctly: only its API binds `127.0.0.1:8010`; PostgreSQL and Redis remain internal. Compose runtime detection supports Docker Compose, legacy `docker-compose`, and Podman Compose.
- **tests**: Olympus v3 test/documentation migration now reflects five public MCP tools (`talk_to`, `discover`, `aether_status`, `aether_update`, `aether_curate`) and seven `talk_to` actions (`open`, `message`, `poll`, `close`, `cancel`, `delegate`, `steer`); `run_workflow` is not a registered v3 tool.

### v0.16.0 (2026-07-08)

- **feat**: "Hermes Can Write Now" — Hermes upgraded from pure orchestrator to orchestrator + fine-tuning implementer
- **changed**: SOUL.md rewritten — §1 manifesto now includes implementation, HARD RULES relaxed (was 10, now 8), new FINE-TUNING vs BULK decision rule, §2 pipeline Phase 5 includes Hermes, §5 Delegation Checkpoint updated, §6 Routing table adds "Fine-tuning → Hermes direct", §8 Dev-QA Loop adds Hermes fine-tuning fallback, §12 Anti-patterns revised, §14 Agent Types adds Hermes as Orchestrator
- **changed**: config.yaml — `file-write` removed from disabled_toolsets (was silently ignored, invalid name), `file-read`→`file` in toolsets + platform_toolsets (enables read_file, write_file, patch, search_files), `pre_tool_call` hook block removed entirely (was dead in TUI mode anyway), agent.description updated, paths fixed from /home/prometeo/ to /home/arty/, graphify MCP server added, MCP python paths updated to shared venv
- **kept**: `code_execution` and `delegation` remain disabled in disabled_toolsets (valid restrictions)

### v0.11.1 (2026-05-19)

- **changed**: Athena SOUL.md rewritten 342→121 lines — removed LangGraph workflow context, duplicate protocols, detailed checklists, few-shot examples
- **changed**: Athena type → Consultant-Analyst, role → security-analyst, config → removed execute_code/memory/search_files toolsets and dependency-audit/risk-communication capabilities
- **added**: Context-aware severity guidance (deployment context), "Do NOT write files" hard limit, athena-security-checklists skill (red-teaming/)
- **removed**: §7 "In Workflow Context", duplicate Protocol 5, execute_code toolset, memory toolset, search_files toolset, dependency-audit capability, risk-communication capability

### v0.10.1 (2026-05-19)

- **feat**: Daedalus reworked as Consultant-Creator — SOUL.md 296→~120 lines, config updated, consultation workflow in Hermes SOUL.md
- **docs**: Hermes SOUL.md §6, §7, §13 updated — Consultation Workflow with delegate-based flow, Agent Types taxonomy

### v0.10.0 (2026-05-19)

- **feat**: Etalides reworked as web+codebase researcher — SOUL.md 417→125 lines, config.yaml.template synchronized, research/ vault created
- **feat**: Bidirectional ACP communication — persistent sessions, steer(), clarification_needed detection
- **feat**: Enriched poll() — last_turn, last_reasoning, recent_tool_calls, heartbeat_timestamp, clarification_needed
- **fix**: WAL checkpoint staleness — explicit PRAGMA wal_checkpoint = TRUNCATE before reads
- **fix**: Session persistence — delegate keeps session open after completion
- **docs**: Hermes SOUL.md §5-§13 rewritten with persistent sessions, routing patterns, anti-patterns

### v0.9.0 (2026-05-19)

- **feat**: Bidirectional ACP communication — persistent sessions (tmux-like), steer(), clarification_needed detection
- **feat**: Enriched poll() — last_turn, last_reasoning, recent_tool_calls, heartbeat_timestamp, clarification_needed
- **fix**: WAL snapshot staleness — async/sync readers now see fresh data
- **fix**: Session persistence — delegate keeps session open after completion
- **docs**: Hermes SOUL.md rewritten — §5 persistent sessions, §6 routing patterns, §9 multi-Daimon coordination

### v0.8.7 (2025-05-18)

- **docs**: Skill updates — post-migration audit patterns added to hermes-agent and github-pr-workflow skills

### v0.8.6 (2026-05-18)

- **docs**: README rewritten — Aether positioned as hermes-agent extension with clear framework/team relationship
- **fix**: 3-pass stale reference audit — docs, source comments, Daimon configs, skills, website
- **fix**: consulting_db.py .eter→.aether, 4 Daimon SOULs, hefesto Ergates/TASKS.md legacy
- **chore**: Deleted 7 stale branches, pruned remotes

### v0.8.5 (2026-05-18)

- **refactor**: `.eter` → `.aether` migration — consulting_db.py, 4 Daimon SOULs, website, skill references
- **chore**: Remove PLAN.md (completed v0.8.0), remove .eter/ directory (migrated to .aether/)
- **fix**: hermes-agent skill hardcoded paths → `__AETHER_ROOT__` placeholders

### v0.8.4 (2026-05-18)

- **refactor**: Consolidated aether-agents skill into SOUL.md — deleted skill directory, absorbed diagnostics into Anti-Patterns table, fixed Olympus v2 reference
- **docs**: Added Daimon config pitfall, skill directory structure warning, and monolithic SOUL.md note to hermes-agent skill references
- **chore**: Removed tracked .usage.json files, added to .gitignore

### v0.8.2 (2026-05-18)

- **fix**: olympus_v3 hooks `_get_session_id()` now reads PID-suffixed `.olympus_session.{PID}` files (fixes ACP delegation returning empty results)
- **fix**: All 6 Daimon config.yaml templates now include `api_mode: chat_completions`
- **docs**: README rewritten with hermes-agent attribution, Daimon personality table, .aether architecture diagram

### v0.8.1 (2026-05-18)

- **chore**: Removed deprecated scripts (configure.sh, start.sh), olympus_v2 code, .pi-daimons, and obsolete docs
- **chore**: Untracked Daimon config.yaml files — now generated from config.yaml.template by setup.sh
- **chore**: Removed home/config.yaml.example (replaced by per-profile templates)
- **refactor**: Daimon configs use __AETHER_ROOT__ placeholders instead of hardcoded paths
- **refactor**: Updated all doc references from configure.sh/start.sh to setup.sh/start-gateway.sh

### v0.8.0 (2026-05-17)

- **feat**: `scripts/setup.sh` — automated installation (Python venv, pip install, config generation, wrapper scripts)
- **feat**: `scripts/update.sh` — git pull + pip upgrade + config regeneration
- **feat**: `scripts/start-gateway.sh` — systemd gateway service manager (start/stop/restart/status)
- **feat**: `Makefile` — common commands (setup, update, gateway, doctor, clean, test)
- **feat**: `home/profiles/orchestrator/config.yaml.template` — machine-independent config template
- **feat**: `home/profiles/orchestrator/.env.example` — API key template (from v0.7.2)
- **docs**: README.md rewritten with Quick Start, installation scripts, architecture
- **docs**: INSTALLATION.md rewritten (setup.sh, manual install, WSL, GPU, troubleshooting)
- **docs**: QUICKSTART.md rewritten (clone, setup, .env, run)
- **chore**: .gitignore updated (home/.venv-hermes/, home/kanban.db)
- **chore**: Deprecated scripts/configure.sh and scripts/start.sh (replaced by setup.sh)

### v0.7.2 (2026-05-17)

- **feat**: pip installation migration guide (references/pip-installation-migration.md) — full plan to migrate from git-clone to `pip install hermes-agent`
- **feat**: orchestrator profile .env.example template
- **docs**: hermes-agent SKILL.md updated for v0.14.0 (pip install, lazy deps, cold start improvements)
- **docs**: hermes-agent terminal-write-restriction.md updated with TUI hook bug confirmation
- **docs**: hermes-agent profile-alias-wrapper.sh template updated
- **docs**: test-driven-development SKILL.md updated with module-level globals pitfall
- **chore**: gitignore PID-suffixed runtime files (.olympus_session*, .olympus_db_path*, .aether_home*, .clean_shutdown)
- **chore**: gitignore .env.bak files, subagent-driven-development references

### Language

All commit messages, GitHub releases, and changelog entries must be in **English**. No Spanish or other languages in version-controlled content.

### Commits

Format: `type: concise subject line`

Types:
- `feat:` — New feature (corresponds to MINOR bump)
- `fix:` — Bug fix (corresponds to PATCH bump)
- `refactor:` — Code restructure without behavior change
- `docs:` — Documentation, README, website, AGENTS.md
- `test:` — Adding or fixing tests
- `chore:` — Maintenance, config, dependencies

Examples:
```
feat: add Ictinus L1 consultant with consult_action.py
fix: buffer reset timing in event_translator.py
docs: update README for v0.5.1
refactor: extract consult logic from server.py to consult_action.py
chore: merge dev into main
```

**Rules:**
- One logical change per commit. Don't mix features and fixes.
- Subject line under 72 characters.
- Body is optional. Use it for "why", not "what".

### Merging and Release Reflection

- **Feature → main:** Merge through a PR after the committed candidate passes required gates. Preserve audited atomic history with a merge commit when traceability matters; squash only when the branch history is intentionally disposable.
- **After merge:** Verify local and remote `main`, close or update linked issues, delete the merged branch, and remove obsolete stacked PRs or worktrees.
- **Release:** Create an annotated `vX.Y.Z` tag only on the exact integrated `main` commit after version metadata and release evidence agree. Pushing the tag triggers `.github/workflows/release.yml`, which verifies the boundary, builds artifacts and creates or reconciles the GitHub Release automatically.
- **No conflation:** A merge can integrate default-off or unreleased work. A tag publishes a version. Runtime activation and deployment are separate operational decisions.

### README and Website

Every feature that changes something user-facing MUST update the README in the same commit or PR. This includes:

- New Daimons added or removed
- New MCP tools or actions
- Configuration format changes
- Architecture changes
- Version bumps

The website should be updated alongside or immediately after the README.

### What NOT to commit

Never commit:
- `home/profiles/hermes/config.yaml` — Contains live config
- `home/profiles/orchestrator/config.yaml` — Contains live config
- `home/profiles/hermes/.env` — Secrets (gitignored)
- Any `.venv/`, `node_modules/`, `dist/`, `__pycache__/` directory

## .aether — Project Continuity

`.aether/` is the project state database that provides hot start context to Daimons.
Lives at `PROJECT_ROOT/.aether/` (gitignored).

### How it works

When a profile is launched independently with the `aether` plugin enabled, its hooks inject project context automatically:
- `pre_llm_call` (first turn): reads hot_state + recent sessions, injects as [.aether Hot Start] context
- `on_session_start`: creates a session row in aether.db
- `post_tool_call`: detects write_file/patch/git commit, records file_changes
- `on_post_llm_call` (first turn): updates hot_state.last_request
- `on_session_end`: updates session status and hot_state

The candidate does not bundle a Hermes continuity MCP facade. Do not write `.aether` manually or restore the retired facade as a shortcut.

### Database tables

- `hot_state` — single-row project snapshot (phase, task, last session, blockers, etc.)
- `sessions` — per-Daimon session history (agent, request, result, files modified)
- `file_changes` — file write/patch/commit tracking (session, agent, path, action)
- `decisions` — architectural decisions (title, rationale, alternatives, status)
- `issues` — blockers and errors (description, resolution, status)

### Observations and Issues

When an authorized continuity surface is available, Hermes records important findings in the project continuity database. A clean v0.22.0 candidate installation has no such Hermes facade; until a native facade is accepted, preserve durable candidate findings in versioned status/evidence or the project issue tracker rather than mutating the database manually.

Durable findings include:

- **Observations** — architectural insights, codebase patterns discovered during work
- **Discomforts** — inconsistencies, smells, or potential problems noticed
- **Debug findings** — root causes identified during systematic debugging
- **Preferences** — user-stated or inferred preferences that should persist

**Rule:** If a finding would be valuable to a *future session*, it belongs in durable project evidence, not just in ephemeral memory.

### Plugin and candidate runtime

- **Plugin (`aether`)**: configured in all six specialist profiles; it acts only if a profile is launched independently.
- **Hermes MCP facade**: absent from the candidate.
- **Ariadna curation**: unavailable until an Aether-native invocation path is accepted.

All specialist templates include only `aether` in `plugins.enabled`; no Olympus plugin remains.