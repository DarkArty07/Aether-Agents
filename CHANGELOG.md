# Changelog

### Fixed
- **Gateway MCP servers now inherit `home/.env`**: Drop-in systemd override added at `~/.config/systemd/user/hermes-gateway.service.d/override.conf` with `EnvironmentFile=` pointing to `home/.env`. Previously, MCP servers like Graphify (semantic retrieval) failed silently when invoked by the gateway because the unit file only injected PATH/VIRTUAL_ENV/HERMES_HOME. See skill `aether-agents-orchestration` pitfall #N and `references/gateway-mcp-env-injection.md` for the full diagnostic chain.

### Documentation
- **aether-agents-orchestration v1.11.0**: New pitfall "Gateway MCP Servers Don't Inherit home/.env" with drop-in fix recipe.
- **task-delegation v1.4.0**: New pitfall "Hefesto Over-Investigates Source Code on Diagnostic Prompts" with prompt-writing pattern.
- **New reference `gateway-mcp-env-injection.md`**: 3-step diagnostic chain + drop-in override fix + rationale.

### v0.15.0 (2026-06-02)

- **feat**: `aether setup` CLI skeleton — modern Python CLI with 7 subcommands (init, status, doctor, daimon, keys, model, reset) replacing legacy `scripts/setup.sh` UX.
- **feat**: ASCII art banner "OLYMPUS THE FORGE" displayed on CLI startup.
- **feat**: Wrapper auto-generation — `scripts/setup.sh` v0.13.0 creates `~/.local/bin/aether-setup` on each run, matching the `hermes`/`aether`/`hefesto` wrapper pattern.
- **feat**: `aether-setup` entry point registered in `pyproject.toml [project.scripts]` — installable globally via `pip install -e .`.
- **test**: 13 unit tests in `tests/test_aether_setup_cli.py` (9 CLI + 4 wrapper helper).

## [0.15.0] — 2026-06-02

### Added
- **`aether setup` CLI skeleton** (`src/olympus_v3/cli/setup.py`): Modern Python CLI replacing the legacy `scripts/setup.sh` UX. Provides 7 subcommands — `init` (bootstrap project), `status` (check health), `doctor` (diagnose issues), `daimon` (manage agents), `keys` (manage API keys), `model` (configure AI models), `reset` (factory reset). Entry point `aether-setup` available globally or via `python -m olympus_v3.cli.setup` from the repo root.
- **ASCII art banner** (`src/olympus_v3/cli/ui/banner.py`): "OLYMPUS THE FORGE" ASCII art displayed on CLI startup, matching the Aether Agents visual identity.
- **Wrapper auto-generation** (`src/olympus_v3/cli/wrappers.py`): `scripts/setup.sh` now auto-generates a `~/.local/bin/aether-setup` wrapper script on each run, following the same pattern used for `hermes`, `aether`, and `hefesto` wrappers.

### Changed
- **`scripts/setup.sh`**: Now detects the project root and generates `~/.local/bin/aether-setup` wrapper pointing to the local `aether-setup` entry point.
- **New Python module**: `src/olympus_v3/cli/setup.py` (main CLI), `src/olympus_v3/cli/ui/banner.py` (ASCII banner), `src/olympus_v3/cli/wrappers.py` (wrapper generation logic).

### Testing
- **13 new unit tests** in `tests/test_aether_setup_cli.py`: 9 CLI tests covering all subcommands and flags; 4 wrapper helper tests for path resolution, shebang generation, wrapper installation, and idempotent re-installation.

### v0.13.0 (2026-06-02)

- **feat**: Graphify integrated as primary codebase intelligence tool — 71x token reduction for architecture navigation, replaces 3-5 manual file reads per codebase query.
- **feat**: `graphifyy>=0.8.0` dependency added with custom `aether-openai` provider in `.graphify/providers.json` (deepseek-v4-flash model via opencode-go endpoint).
- **feat**: Hermes SOUL.md §7 "Codebase Intelligence — Graphify" documents 7 MCP tools, 6-step query funnel, and known limitations.
- **feat**: New reference `graphify-usage-patterns.md` — query patterns, pitfalls, extraction modes, advanced techniques (context_filter, method labels for shortest_path).
- **feat**: Knowledge graph covers entire codebase — 23,942 nodes, 41,209 edges, 1,513 communities (80% AST-extracted, 20% semantically inferred).

## [0.13.0] — 2026-06-02

### Added
- **Graphify as primary codebase intelligence tool**: Hermes can now navigate the Aether Agents codebase as a knowledge graph (23,942 nodes, 41,209 edges) via 7 MCP tools — `query_graph`, `get_node`, `get_neighbors`, `shortest_path`, `graph_stats`, `god_nodes`, `get_community`, plus 3 PR-impact tools. Architecture queries that previously required opening 3-4 files (read 3-5K tokens) now resolve in a single MCP call (~500 tokens) — a 71x token reduction.
- **graphifyy dependency**: `graphifyy>=0.8.0` added to `pyproject.toml`. The package handles AST extraction (zero tokens) and optional LLM semantic inference.
- **aether-openai custom provider**: `.graphify/providers.json` configured to use the same `OPENCODE_API_KEY` as the rest of the system, pointing to opencode-go v1 endpoint with `deepseek-v4-flash` as default model. Provider is overridable via `GRAPHIFY_AETHER_MODEL` env var.
- **Hermes SOUL.md §7**: New section "Codebase Intelligence — Graphify" (91 lines) with: when to use / when to skip, all 7 MCP tools documented, 6-step query funnel (ORIENT→LOCATE→SEARCH→EXPLORE→CONTEXT→TRACE), maintenance schedule, anti-patterns, and known limitations (BFS/DFS Honcho bias, shortest_path ambiguity, context_filter workaround).
- **graphify-usage-patterns.md reference**: New support file under `aether-agents-orchestration/references/` documenting query patterns, pitfalls, extraction modes (AST vs LLM), CLI quick reference, provider configuration, and advanced techniques (context_filter for edge-type filtering, method labels for shortest_path).
- **Graph generation scope**: Knowledge graph built from 1,321 source files across `src/`, `home/profiles/`, `home/skills/`, and `honcho-server/`. AST extraction covers 80% of edges; semantic LLM inference (via `aether-openai`/`deepseek-v4-flash`) covers 20% and produces community labels.

### Documentation
- **Hermes SOUL.md §7**: Updated with 5 corrections after live testing — "0 tokens" clarification, skip-when-known rule, BFS vs DFS guidance, `graphify explain` CLI alternative, and Known Limitations table.
- **aether-agents-orchestration SKILL.md**: Added reference pointer to new `graphify-usage-patterns.md` and pitfall #12 "Reading Files Manually Instead of Querying Graphify First".

### Performance
- **Token reduction**: Graph queries consume ~200-500 tokens per result vs ~15K tokens for 3-5 manual file reads — a 71x reduction in context cost for codebase navigation tasks.
- **Response latency**: Graph MCP queries return in milliseconds (no process startup, no shell commands) vs ~2 seconds for delegated file reading.

### v0.12.0 (2026-05-27)

- **feat**: Integrate Honcho as official memory provider for Aether Agents — persistent user profiles, semantic memory search, and dialectic reasoning across sessions.
- **feat**: Honcho added as git submodule at honcho-server/ (plastic-labs/honcho) with 4 documented patches for DeepSeek/OpenCode Go compatibility.
- **feat**: Unified API key — Honcho uses OPENCODE_GO_API_KEY from parent .env, eliminating manual sync across 11 config locations.
- **feat**: Docker Compose at project root with services (api, deriver, postgres, redis) on ports 8010/5434/6380.
- **feat**: Setup script scripts/setup-honcho.sh + Makefile targets (setup-honcho, honcho-up/down/logs/status).
- **feat**: Hermes profile max context window set to 256k (context_length: 256000).
- **docs**: README "Memory Provider (Honcho)" section, docs/honcho-setup.md, honcho-server/PATCHES.md.

All notable changes to Aether Agents are documented here.

## [0.12.0] — 2026-05-27

### Added
- **Honcho as official memory provider**: Persistent user profiles, semantic memory search, and dialectic reasoning synthesized from accumulated observations across sessions.
- **Honcho git submodule**: Added at `honcho-server/` (plastic-labs/honcho) with 4 documented patches for DeepSeek/OpenCode Go compatibility (3-level structured output fallback, thinking disable, embedding dimensions, config validation).
- **Unified API key management**: Honcho now uses the same `OPENCODE_GO_API_KEY` as all Daimons, eliminating manual key synchronization across 11 config locations.
- **Docker Compose integration**: Root `docker-compose.yml` with services (api, deriver, postgres, redis) on ports 8010/5434/6380 — includes deriver service for automatic observation processing.
- **Setup script**: `scripts/setup-honcho.sh` automates submodule initialization, `.env` generation, and service startup.
- **Makefile targets**: `setup-honcho`, `honcho-up`, `honcho-down`, `honcho-logs`, `honcho-status`.
- **256k max context window**: Hermes profile configured with `context_length: 256000` on the orchestrator config.

### Documentation
- **README**: New "Memory Provider (Honcho)" section covering setup, commands, and architecture.
- **docs/honcho-setup.md**: Complete service configuration, troubleshooting, and data persistence guide.
- **honcho-server/PATCHES.md**: Catalog of all applied patches with upgrade notes.

## [0.11.1] — 2026-05-19

### Changed
- **Athena SOUL.md rewritten**: 342 → 121 lines. Removed LangGraph workflow context (§7), duplicate Protocol 5, Ariadna reference, detailed checklists, and few-shot examples
- **Athena type**: Generic Daimon → Consultant-Analyst (reads code, produces audits, never implements)
- **Athena role**: `security-engineer` → `security-analyst`
- **Athena config**: Removed `execute_code`, `memory`, `search_files` toolsets; removed `dependency-audit`, `risk-communication` capabilities; added YAML comments justifying toolsets; English description
- **Athena config template**: Uses `__AETHER_ROOT__` placeholders instead of hardcoded paths

### Added
- **Context-aware severity guidance**: Athena now evaluates deployment context (local dev vs production) when assigning severity levels
- **"Do NOT write files" hard limit**: Explicit Consultant-Analyst boundary in SOUL.md
- **athena-security-checklists skill**: Moved content from SOUL.md (checklists, dependency audit protocol, STRIDE detail, few-shot examples) into an on-demand skill under `red-teaming/`
- **Design reference**: `daimon-design/references/athena-v0.11.1-rework-design.md`

### Removed
- §7 "In Workflow Context" (LangGraph/workflows don't exist in olympus_v3)
- Duplicate Protocol 5 and dead reference to non-existent file
- `execute_code` toolset (Consultant-Analyst doesn't execute code)
- `memory` toolset (single-turn consultant, no persistent state)
- `search_files` separate toolset (already bundled in `file`)
- `dependency-audit` capability (merged into `security-review`)
- `risk-communication` capability (all Daimons communicate via Hermes)

## [0.11.0] — 2026-05-19

### Changed
- **Hefesto SOUL.md rewritten**: 284 → 114 lines
- **Hefesto identity**: "Senior Developer / Tech Lead" → "Senior Developer"
- **Hefesto responsibilities**: Removed "decompose by role" and "coordinate Ergates"
- **Hefesto limits**: Added "Do NOT decompose tasks"
- **Hefesto config**: Removed `delegate_task` toolset and `delegation` section. Added documented YAML comments. English description
- **Hermes SOUL.md §1**: Manifesto "I plan, I delegate, I synthesize" → "I plan, I decompose, I delegate, I synthesize"
- **Hermes SOUL.md §1**: Added Hard Rule #10: never delegate vague tasks
- **Hermes SOUL.md §6**: Added Task Decomposition section with Role Catalog

### Removed
- Hefesto: Ergates concept, delegate_task toolset, subagent-driven-development skill
- Hefesto: LangGraph workflow context (§7)
- Hefesto: Role-Based Task Decomposition protocol (moved to Hermes §6)
- Hefesto: Sub-Agent Template protocol
- Hefesto: `.hefesto/TASKS.md` tracking

## [0.10.2] — 2026-05-19

### Changed
- **Ariadna config cleaned up**: role `project-manager` → `context-curator`, description in English, capabilities match reality (`context-curation`, `synthesis` instead of `project-tracking`, `sprint-tracking`)
- **Ariadna toolsets minimized**: `file` + `skills` only (was `file`, `terminal`, `memory`, `session_search`, `todo`, `clarify`). Ariadna only writes CONTEXT.md — `terminal`, `memory`, `session_search`, `todo` were unused, `clarify` does not exist as a toolset
- **Ariadna level**: 2 → 1 (curation is a simple transformation, not an intermediate task)
- **Ariadna SOUL.md**: added invocation note — Ariadna is invoked programmatically via `aether_curate`, not by `delegate`

### Note
Ariadna remains a registered Daimon for v0.10.2. Removing Ariadna from the Daimon system (replacing the ACP `spawn_agent` call with a direct model API call in `aether_curate`) is deferred to v0.11.0+.

## [0.10.1] — 2026-05-19

### Changed
- **Daedalus reworked as Consultant-Creator**: SOUL.md rewritten from 296 to ~120 lines
  - Identity: Consultant-Creator — UX/UI Designer (was Frontend Developer)
  - Eponym: Daedalus, architect of the Labyrinth — his lesson: a design so complex that users cannot escape is a design failure
  - Output format: Observations / Risks / Recommendations / Prototype (if applicable)
  - Removed §7 Workflow Context (Hermes handles pipeline), §8 long protocols (consolidated into core), and few-shot examples
  - Hard limits: never implement production code, never make product decisions, never research the web, never decide tech stack, never talk to user directly
- **Hermes SOUL.md §13 rewritten**: Consultation Workflow now documents the real delegate-based flow (the `consult` tool does not exist). Includes Agent Types taxonomy (Actor / Consultant-Creator / Consultant-Analyst), structured consultation prompt format, and sequential consultation pattern
- **Hermes SOUL.md §6 updated**: Daedalus routing row changed from "UX/UI design" to "Design consultation", added Consultation rule
- **Hermes SOUL.md §7 updated**: Feature workflow pattern now shows Daedalus as consultation step: `Etalides → Daedalus (consult) → Hefesto → Athena`
- **Daedalus config.yaml.template updated**: role changed to `consultant-creator`, description updated, toolsets documented with YAML comments, removed `patch` and `execute_code` (not needed for prototypes)

## [0.10.0] — 2026-05-19

### Changed
- **Etalides reworked as web+codebase researcher**: SOUL.md rewritten from 417 to 125 lines
  - Identity: Researcher (web + codebase), not just web researcher
  - Dual persistence model: web research → Obsidian vault (`research/`), code research → direct response to Hermes
  - Code Research Protocol: search_files → read_file → terminal (escalation hierarchy)
  - Action budget: renamed from "link budget" to "action budget", counting web, file, and terminal actions
  - Removed 4 of 5 few-shot examples, duplicated output format sections, and curl fallback technique
- **Etalides config.yaml.template updated**: added `terminal` toolset, `code-search` capability, English description, documented YAML comments
- **Hermes SOUL.md routing updated**: separate rows for web research and code research in §6, Code research rule added
- **Research vault created**: `research/` directory with Obsidian config (`.obsidian/`), `INDEX.md`, and `README.md`

### Fixed
- **Etalides config.yaml.template drift**: synchronized template with live config (role, description, capabilities, toolsets)

## [0.9.0] — 2026-05-19

### Changed
- **Bidirectional ACP communication**: sessions are now persistent (like tmux) — `delegate()` returns `session_id` and keeps session open
- **`steer()` action**: inject directives into a working Daimon without interrupting its current turn
- **`clarification_needed` detection**: Daimons that need clarification are detected and sessions stay open for follow-up
- **Enriched `poll()`**: `last_turn`, `last_reasoning`, `recent_tool_calls`, `heartbeat_timestamp`, `clarification_needed`
- **Progress indicator**: when `last_turn` is null but tool calls are active, `[Working] tool_name(args) → status` fallback
- **SOUL.md rewritten**: §5 persistent sessions, §6 routing with situation→tool patterns, §9 multi-Daimon coordination, §10 session management, §11 anti-patterns, §13 Daimon models table removed
- **WAL checkpoint fix**: `PRAGMA wal_checkpoint = TRUNCATE` before reads in `get_session_progress()` to prevent stale data

### Fixed
- **WAL snapshot staleness**: async/sync readers in SQLite now see fresh data with explicit checkpoint before reads
- **Session persistence**: `delegate` keeps session open after completion, enabling follow-up `message()` calls

## [0.8.7] — 2025-05-18

### Changed
- **Skill updates:** post-migration audit patterns added to hermes-agent and github-pr-workflow skills

## [0.8.6] — 2026-05-18

### Changed
- **README rewritten** — Aether Agents now positioned as an extension of hermes-agent framework, not a standalone tool
  - Tagline: "A multi-agent team built on hermes-agent"
  - "What is Aether Agents?" section explains hermes-agent first, then what Aether adds
  - Key Features clarifies each Daimon is a hermes-agent instance
  - Architecture diagram updated (removed `-p` flag confusion)
  - License section streamlined

### Fixed
- **Stale reference cleanup (3-pass audit):**
  - Docs: INSTALLATION, QUICKSTART, USER_PROFILE, CONFIGURATION, CONTRIBUTING, Makefile, deploy-site.yml
  - Source: acp_manager.py, config_loader.py comments (profiles/hermes → default home dir)
  - Daimon configs: .env.example broken PROVIDERS.md link → CONFIGURATION.md
  - Skills: hermes-agent SKILL.md, auxiliary-models.md, verify_cuda_stt.sh, github-pr-workflow
  - hefesto SOUL.md: removed "Ergates" and TASKS.md legacy references
- **consulting_db.py**: `.eter` → `.aether` path (3 locations)
- **4 Daimon SOUL.md**: `.eter` → `.aether`
- **Website**: `.eter` → `.aether`, `profiles/hermes` → default profile
- **.eter directory**: migrated consulting.db to .aether/, deleted legacy .eter/

### Removed
- PLAN.md (completed v0.8.0 multi-project isolation plan)
- .eter/ directory (migrated to .aether/)

### Chore
- Deleted 7 stale git branches (3 local, 4 remote)
- Pruned remote tracking branches

## [0.8.5] — 2026-05-18

### Changed
- **`.eter` → `.aether` migration complete**: All source code, Daimon SOULs, website, and skill references now use `.aether/` consistently
  - `consulting_db.py`: consulting database path updated from `.eter/.consulting/` to `.aether/.consulting/`
  - 4 Daimon SOUL.md files: `.eter/` references → `.aether/`
  - Website: `.eter/` → `.aether/`, `profiles/hermes/` → default profile (`home/`)

### Removed
- **PLAN.md** — completed multi-project isolation plan from v0.8.0, no longer needed
- **.eter/ directory** — migrated to `.aether/`, legacy directory deleted

### Fixed
- **hermes-agent skill**: hardcoded `/home/prometeo/` paths replaced with `__AETHER_ROOT__` placeholders for portability

## [0.8.4] - 2026-05-18

- **refactor**: Consolidated aether-agents skill into SOUL.md (monolithic)
  - All Daimon ecosystem info (protocols, workflows, diagnostics, agent creation, models) now lives exclusively in SOUL.md
  - Deleted home/skills/devops/aether-agents/ (was broken: nested directory, missing SKILL.md, never committed to git)
  - Added 3 diagnostic rows to §11 Anti-Patterns (0 tool_calls, invisible skill, agent-hooks mismatch)
  - Fixed §13 "Olympus v2" → "olympus_v3"
  - Removed all aether-agents skill references from §5, §6, §11, §12
- **docs**: Added Daimon config pitfall, skill structure warning, and monolithic SOUL.md note to hermes-agent skill
- **chore**: Removed tracked .usage.json and .usage.json.lock, added to .gitignore

## [0.8.2] - 2026-05-18

- **fix**: ACP delegation returned empty results — PID-suffixed file mismatch in olympus_v3 hooks (`_get_session_id()` read `.olympus_session` but `acp_manager` writes `.olympus_session.{PID}`)
- **fix**: Added `api_mode: chat_completions` to all 6 Daimon config.yaml templates (hefesto, etalides, ariadna, athena, daedalus, ictinus)
- **docs**: README rewritten with impact-first design, hermes-agent attribution, Daimon personality table, and .aether architecture
- **refactor**: Daimon config templates include `api_mode: chat_completions` for proper ACP compatibility

## [0.8.1] - 2026-05-18

### 🧹 Repository Cleanup

Removed deprecated and obsolete files after pip install migration (v0.8.0). The repository now contains only active, maintained code and documentation.

### Removed

- `scripts/configure.sh` — replaced by `scripts/setup.sh` in v0.8.0. Referenced obsolete `~/.hermes/` paths.
- `scripts/start.sh` — replaced by `scripts/setup.sh` + `scripts/start-gateway.sh` in v0.8.0. Referenced Olympus v2 and obsolete paths.
- `src/olympus_v2/` — entire directory (9 files). Olympus v2 was deprecated in v0.7.0, replaced by v3. Removed: `__init__.py`, `config_loader.py`, `consult_action.py`, `consulting_db.py`, `event_translator.py`, `pi_adapter.py`, `requirements.txt`, `server.py`, `soul_to_system.py`.
- `home/.pi-daimons/` — entire directory (18 files). Pi Agent RPC was deprecated in v0.7.0, replaced by ACP. Removed all 6 Daimon `.pi/` directories with SYSTEM.md, extensions, and settings.json.
- `tests/olympus/` — entire directory (3 files). Tests for olympus_v2 module.
- `docs/hermes-profile-setup.md` — referenced obsolete `~/.hermes/` paths.
- `docs/workflow-engine-experiment.md` — experiment document, not official guide.
- `home/config.yaml.example` — confusing duplication of per-profile templates.

### Changed

- **Daimon configs are now templates**: All 6 Daimon `config.yaml` files (ariadna, hefesto, etalides, athena, daedalus, ictinus) are no longer tracked in git. Each now has a `config.yaml.template` with `__AETHER_ROOT__` and `__HERMES_PYTHON__` placeholders. `setup.sh` generates the live `config.yaml` from templates.
- **`home/profiles/hermes/config.yaml`** untracked from git (was already gitignored, now properly removed from tracking). The `config.yaml.template` is the tracked version.
- **`.gitignore`** updated with entries for all Daimon live configs, `home/config.yaml`, and `home/profiles/orchestrator/config.yaml`.
- **`home/profiles/hermes/config.yaml.template`** comment updated to reference `setup.sh` instead of `configure.sh`.
- **`scripts/setup.sh`** already iterates over all profiles with `config.yaml.template` files — no changes needed.
- **References updated**: AGENTS.md, CONFIGURATION.md, INSTALLATION.md, website HTML, and other docs updated to reference `setup.sh` instead of deprecated scripts.

### Migration from v0.8.0

No action required. If you already ran `setup.sh` in v0.8.0, your config files are already generated. If cloning fresh, `setup.sh` will generate all Daimon configs from templates.

## [0.8.0] - 2026-05-17

### 🚀 Distribution & Installation Overhaul

Streamlined project setup from a multi-step manual process to a single command. Replaces the old git-clone-and-configure workflow with automated scripts.

### What's New

- **`scripts/setup.sh`** — Fully automated installation: detects Python 3.11+, creates `.venv-hermes`, installs hermes-agent + olympus-mcp + CUDA extras, generates config from templates, creates `~/.local/bin/aether` and `hermes` wrappers, configures shell environment. Idempotent — safe to re-run.
- **`scripts/update.sh`** — Updates repo (`git pull` with stash), upgrades hermes-agent from PyPI, reinstalls local olympus-mcp, regenerates configs if placeholders are unresolved.
- **`scripts/start-gateway.sh`** — Manages Hermes Gateway systemd service (start/stop/restart/status). Supports custom profiles via `-p`.
- **`Makefile`** — Common targets: `setup`, `update`, `gateway`, `doctor`, `clean`, `test`.
- **`config.yaml.template`** for orchestrator — Machine-independent config with `__AETHER_ROOT__` and `__HERMES_PYTHON__` placeholders. Generated by setup.sh into config.yaml.
- **`docs/`** — README.md, INSTALLATION.md, and QUICKSTART.md rewritten with setup.sh Quick Start, WSL instructions, GPU setup, and migration from v0.7.x.

### Deprecations

- `scripts/configure.sh` — replaced by `scripts/setup.sh`. Old script references `~/.hermes/sdk/venv/bin/python` paths that no longer exist.
- `scripts/start.sh` — replaced by `scripts/setup.sh` + `scripts/start-gateway.sh`. Old script references Olympus v2 and deprecated Python paths.

### Migration from v0.7.x

If upgrading from a git-clone installation (v0.7.x or earlier):

1. The new `.venv-hermes/` lives *inside* the repo at `home/.venv-hermes/` (not `~/.hermes/hermes-agent/venv/`)
2. Wrapper scripts in `~/.local/bin/` now point to the new venv
3. `config.yaml.template` replaces manual config editing — run `bash scripts/setup.sh` to regenerate
4. The old `~/.hermes/` directory is no longer needed and can be deleted post-migration

## [0.7.0] - 2026-05-14

### 🔥 .aether — Project Continuity System

Three-layer architecture for providing hot start context to Daimons. When Hermes delegates to a Daimon, the only context the Daimon receives is the prompt string. If Hermes doesn't include enough context, the Daimon works blind. `.aether` solves this by automatically capturing, curating, and injecting project context.

| Layer | Component | What it does |
|-------|-----------|--------------|
| 1. Capture | Plugin hooks | Automatically capture session data, file changes, decisions, issues in `aether.db` |
| 2. Curation | Ariadna via `aether_curate` | Synthesize aether.db into readable `.aether/CONTEXT.md` (5 sections, max 1500 chars) |
| 3. Injection | `pre_llm_call` hook | On first turn, inject `[.aether Context]` into Daimon if CONTEXT.md exists |

### Why This Change

Session crossover bugs occurred when Hermes delegated to a Daimon — the Daimon had no project identity and could respond about the wrong project. The `.eter/` system (Scrum Master, CURRENT.md, LOG.md) was manual and never maintained. `.aether` replaces `.eter/` with an automated 3-layer system that ensures Daimons always know what project they're in.

### What's New

- **aether_db.py** (689 lines): 5 tables (hot_state, sessions, file_changes, decisions, issues), async + sync DB classes, `get_aether_db_path()` with 3-tier resolution
- **aether_hooks/hooks.py** (511 lines): 5 hooks — `pre_llm_call` (injects CONTEXT.md on first turn), `on_session_start`, `post_tool_call`, `on_post_llm_call`, `on_session_end`
- **3 MCP tools for Hermes**: `aether_status` (read state), `aether_update` (7 intentional update actions), `aether_curate` (invoke Ariadna to synthesize CONTEXT.md)
- **Plugin in 6 Daimons**: hefesto, etalides, ariadna, daedalus, athena, ictinus (NOT Hermes)
- **Ariadna reworked**: From Scrum Master (200+ lines, .eter/, CURRENT.md, sprints) to Context Curator (~73 lines, .aether/CONTEXT.md, 5 sections, 1500 chars max)
- **Hermes SOUL.md**: §3 .eter/ → .aether/, §4 full .aether 3-layer architecture, §6/§10/§11 updated
- **acp_manager.py**: Always passes `AETHER_HOME` to Daimon. `SessionInfo.project_root` added. `.aether_home` writes project_root
- **talk_to schema**: New `project_root` parameter
- **CONTEXT_SCHEMA.md**: 5-section convention, max 1500 chars
- **AGENTS.md**: Git conventions + .aether documentation

### Breaking Changes

- `.eter/` NO LONGER USED — replaced by `.aether/` (gitignored, project-local)
- Ariadna: Scrum Master → Context Curator. CURRENT.md/LOG.md workflow removed
- Raw `hot_start` injection removed — if no CONTEXT.md, no injection (no raw fallback)
- Session management: `delegate ariadna` → MCP tools (`aether_status`, `aether_update`, `aether_curate`)

### Bugs Fixed

- **AETHER_HOME not passed to Daimon**: Only passed if in server env. Now always set with project_root > env > cwd priority
- **`.aether_home` wrote wrong path**: Used `Path.cwd()` instead of `session.project_root`. Fixed
- **CONTEXT.md staleness race condition**: Hooks updated `updated_at` after curate, marking CONTEXT.md as stale immediately. Fix: removed staleness check — CONTEXT.md always injected if exists

### Migration

1. Run `aether_curate(project_root="/path/to/project")` to generate initial CONTEXT.md
2. Use `aether_status` / `aether_update` instead of delegating to Ariadna
3. Remove `.eter/` directories (no longer used)
4. Plugin auto-creates `.aether/aether.db` on first Daimon session

### Full Commit History

- 3d17a3c: feat: add .aether continuity system — 3-layer architecture for Daimon context injection
- 3b89281: Merge pull request #11 from DarkArty07/feature/aether-continuity

## [0.6.0] - 2026-05-09

### 🔥 Architecture: Pi Agent RPC → ACP + Plugin Hooks + SQLite (Olympus v3)

Replaced Pi Agent RPC with Olympus v3: ACP protocol for session lifecycle, hermes-agent plugin hooks for per-turn observability, and SQLite as the shared data channel between Daimon and orchestrator.

### Why This Change

Pi Agent was a black box: `prompt → black box → agent_end`. We could OBSERVE events but not CONTROL them. Two critical problems:

1. **No per-turn visibility:** Pi Agent's `agent_end` event did not guarantee a text response. Daimons frequently completed sessions without synthesizing their analysis. The `event_translator.py` was fragile and required constant patches for different model behaviors (kimi-k2.6, mimo-v2-omni).

2. **No controllability:** The only real control endpoints were `prompt` (send message) and `agent_end` (session over). We could not inject steering directives, audit tool calls in real-time, or guarantee session completion.

Olympus v3 solves both by moving observability INTO the agent process via plugin hooks:

| Feature | Pi Agent RPC (v2) | Olympus v3 (ACP + Plugin + SQLite) |
|---------|-------------------|--------------------------------------|
| Per-turn visibility | Accumulated buffer (fragile) | `post_llm_call` hook writes each turn to SQLite |
| Tool audit trail | Partial (Bug B: always 0) | `post_tool_call` hook captures every invocation |
| Session completion | `agent_end` not guaranteed | `on_session_end` always fires |
| Mid-conversation steering | Impossible | `pre_llm_call` reads steering directives from SQLite |
| Response extraction | Fragile (3 fallback sources) | Canonical: `agent_end.messages` → SQLite turn |
| Protocol | Pi JSONL (typed but black-box) | ACP (standard) + Plugin (inside agent) + SQLite (shared) |

### What's New

- **Olympus v3 MCP server** (`src/olympus_v3/`): talk_to, discover, consult via ACP
- **Plugin hooks** (`olympus_v3_hooks/`): 4 hooks (post_llm_call, post_tool_call, on_session_end, pre_llm_call)
- **SQLite persistence** (`db.py`): 4 tables (sessions, turns, tool_calls, steering) with WAL mode
- **ACP Manager** (`acp_manager.py`): spawns hermes-agent processes as ACP servers
- **Consult workflow** (`consult_action.py`): migrated from v2, uses ACPManager + SQLite
- **Config loader** (`config_loader.py`): discovers 7 Daimon profiles from AETHER_HOME
- **Ictinus**: New Level 1 Consultant (Backend Architect)
- **Write restrictions** restored: file-write in disabled_toolsets + pre_tool_call hook

### Breaking Changes

- Pi Agent config (`.pi/` directories) is NO LONGER USED — replaced by hermes-agent profiles
- `event_translator.py` and `pi_adapter.py` removed from v3 (kept in v2 for rollback)
- DB path unified: AETHER_HOME/.olympus/olympus_v3.db (not HERMES_HOME)

### Migration

1. Install olympus_v3 plugin in each Daimon profile
2. Enable `olympus_v3` MCP server in Hermes config
3. Set `plugins.enabled: [olympus_v3]` in each Daimon config
4. Restart gateway: `systemctl --user restart hermes-gateway-hermes`

### Full Commit History

- f3dfc07: feat: olympus v3 implementation (T1-T7)
- 153e0d3: fix: restore write restrictions (T8)
- eb3ff1f: feat: olympus v3 improvements - stale session cleanup + DB path unification
- c49418d: docs: update PLAN.md with full implementation status

## [0.5.0] - 2026-05-07

### 🔥 Breaking Change: ACP → Pi Agent RPC

All 5 Daimons (Hefesto, Etalides, Ariadna, Athena, Daedalus) now use **Pi Agent RPC** instead of Hermes Agent's ACP protocol for sub-agent communication. ACP remains available as instant rollback (`backend: acp` in config).

### Why This Change

ACP had 3 critical bugs that made Daimon delegation unreliable:

1. **Spinner noise (Bug A):** ACP's `AgentThoughtChunk` mixed kawaii progress indicators with substantive reasoning. A regex filter tried to separate them but leaked Unicode spinners (ಠ_ಠ), inflating `substantive_thoughts` and making stall detection unreliable.

2. **Tool calls invisible (Bug B):** `total_tool_calls` was always `0` even when the Daimon executed 8+ tools. The ACP event stream never emitted tool execution events, making it impossible to distinguish a working agent from a frozen one.

3. **No reasoning visibility (Bug C):** Provider chain-of-thought (DeepSeek `reasoning_content`, Anthropic `thinking`) was never forwarded. LLMs that stream via thoughts had their reasoning lost entirely, causing empty responses from Daimons.

These bugs meant Daimon sessions could: stall for minutes with zero output, complete work but report no tool calls, or return empty responses when the LLM used the thoughts channel exclusively.

### What Pi Agent RPC Solves

| Feature | ACP (old) | Pi RPC (new) |
|---------|-----------|---------------|
| Event protocol | ACP binary (spinner noise) | Typed JSONL (text_delta, thinking_delta, tool_call) |
| Tool calls | Always 0 (Bug B) | Explicit `tool_execution_start/end` events |
| Reasoning visibility | None (Bug C) | `thinking_delta` events, configurable via `set_thinking_level` |
| Spinner filtering | Regex whitelist (leaks) | Not needed — events are typed |
| Steering (live intervention) | None | `steer` command mid-stream |
| Thinking levels | None | `off/minimal/low/medium/high/xhigh` |
| Session persistence | None | Built-in with `--session-dir` |
| Model switching | Restart required | `set_model` at runtime |
| Compaction | Manual | `compact` + auto-compaction |

### New: `delegate` Action (Single-Call Auto-Poll)

The biggest UX improvement: `delegate` replaces the entire open→message→poll→close cycle with one MCP call.

**Before (10-20 tool calls, LLM-driven polling):**
```
open(agent) → session_id
message(session_id, prompt) → active
poll(session_id) → active ... (repeat 8-15 times)
poll(session_id) → done
close(session_id) → closed
```

**After (1 tool call, server-driven polling):**
```
delegate(agent, prompt, poll_interval=15, timeout=300) → done
```

The MCP server handles polling internally with `asyncio.sleep(poll_interval)`. Parameters:
- `poll_interval`: seconds between polls (default 15, min 1)
- `timeout`: max seconds to wait (default 300, max 600)

Returns final result with `delegate: {timed_out, elapsed_seconds, poll_iterations}` metadata. On timeout: returns last known state WITHOUT closing session (allows manual follow-up).

Manual `open/message/poll/close` actions remain available for fine-grained control.

### Architecture

- **Hermes** continues using Hermes Agent (orchestrator with MCP, memory, skills)
- **Daimons** now use Pi Agent RPC (headless subprocess, `@mariozechner/pi-coding-agent`)
- **Olympus v2** MCP server bridges the two — same `talk_to` interface, different backend
- **Per-agent backend** in `config.yaml`: `backend: pi_rpc` (default) or `backend: acp` (rollback)
- **Pi configs** at `home/.pi-daimons/{name}/.pi/` with SYSTEM.md, settings.json, extensions

### 5 Optimizations to Olympus MCP v2 Server

1. **Buffer reset timing fix (CRITICAL):** Moved from `_action_poll` (after done) to `_action_message` (before new prompt). Prevents losing the final response between polls.

2. **Response truncation (HIGH):** Responses >4000 chars auto-truncate with `response_truncated: true` + `response_total_length` metadata. Prevents MCP token overflow.

3. **Progress metadata (MEDIUM):** `progress` field in every poll: `{total_thoughts, substantive_thoughts, total_messages, total_tool_calls, elapsed_seconds}`. Enables stall detection.

4. **Better error messages (MEDIUM):** Distinct `"expired"` (process terminated) vs `"unknown"` (never existed) session errors.

5. **Tool name fallbacks (LOW):** Chain: `name` → `toolName` → `function.name` → `"unknown"`. Fixed empty tool names in `tool_calls_detail`.

### SOUL.md Reinforcement (Hermes Orchestrator)

Hermes' SOUL.md received 4 surgical patches establishing orchestrator identity:

1. **HARD RULES** (§1): Never edit configs, never write SYSTEM.md, never execute implementation commands, never work >2 turns without delegating, never bypass Daimons, never poll >5 times without reporting.
2. **Delegation checkpoint** (§2): Mandatory check before starting any task — "Can a Daimon do this?"
3. **Expanded anti-patterns** (§12): 6 new rows covering config editing, SYSTEM.md writing, implementation, answering+implementing, solo architecture decisions, session close skipping.
4. **Known issues update** (§13): GLM-5.1 AgentThoughtChunk, LLM delegation reluctance, workflow MCP timeout, personality override, platform_toolsets override.

### All 5 Daimons Migrated

| Daimon | Backend | Tools | Thinking | Status |
|--------|---------|-------|----------|--------|
| Hefesto | pi_rpc | read/write/edit/bash/grep/find/ls | medium | ✅ Production |
| Etalides | pi_rpc | read/write/edit/bash/grep/find/ls | medium | ✅ Production |
| Ariadna | pi_rpc | read/write/edit/bash | medium | ✅ Production |
| Athena | pi_rpc | read/write/edit/bash/grep/find/ls | high | ✅ Production |
| Daedalus | pi_rpc | read/write/edit/bash/grep/find/ls | medium | ✅ Production |

### 10 Bugs Fixed (Olympus V2 Development)

| # | Bug | Fix |
|---|-----|-----|
| A | auth.json `${ENV_VAR}` not resolved | Hardcode real key, extension reads process.env |
| B | `--provider` validated before extension loads | Use settings.json instead of CLI flags |
| C | `--cwd` CLI flag doesn't exist in Pi | Use `subprocess.Popen(cwd=...)` |
| D | registerProvider models[] requires per-model apiKey | Remove models[], let Pi auto-discover via /v1/models |
| E | No stderr reader thread | Added _stderr_reader() daemon |
| F | OPENCODE_GO_API_KEY not in subprocess env | Added _load_dotenv() to read AETHER_HOME/.env |
| G | event_translator didn't handle Pi's JSONL format | Rewrote for assistantMessageEvent nesting |
| H | Server deleted session before draining events | Drain buffer on process death |
| I | agent_end killed Pi process with --session-dir | Reset buffer for next turn, keep process alive |
| J | `arguments` vs `args` NameError in _action_delegate | Fixed parameter name in route handler |

### Files Changed

- `src/olympus_v2/server.py` — delegate action, buffer reset, truncation, progress metadata, error messages
- `src/olympus_v2/event_translator.py` — tool name fallbacks, progress metadata builder
- `src/olympus_v2/pi_adapter.py` — get_state, multi-turn fixes, session-dir support
- `home/profiles/hermes/SOUL.md` — HARD RULES, delegation checkpoint, anti-patterns
- `home/.pi-daimons/ariadna/` — Pi config (SYSTEM.md, settings.json, extension)
- `home/.pi-daimons/athena/` — Pi config (SYSTEM.md, settings.json, extension)
- `home/.pi-daimons/daedalus/` — Pi config (SYSTEM.md, settings.json, extension)
- `home/.pi-daimons/etalides/` — Pi config (SYSTEM.md, settings.json, extension)
- `.gitignore` — Removed old profile-level pi-daimons entry

[0.11.1]: https://github.com/DarkArty07/Aether-Agents/compare/v0.11.0...v0.11.1
[0.11.0]: https://github.com/DarkArty07/Aether-Agents/compare/v0.10.2...v0.11.0
[0.10.1]: https://github.com/DarkArty07/Aether-Agents/compare/v0.10.0...v0.10.1
[0.10.0]: https://github.com/DarkArty07/Aether-Agents/compare/v0.9.0...v0.10.0
[0.9.0]: https://github.com/DarkArty07/Aether-Agents/compare/v0.8.7...v0.9.0
[0.8.7]: https://github.com/DarkArty07/Aether-Agents/compare/v0.8.6...v0.8.7
[0.7.0]: https://github.com/DarkArty07/Aether-Agents/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/DarkArty07/Aether-Agents/compare/v0.5.1...v0.6.0
[0.5.0]: https://github.com/DarkArty07/Aether-Agents/compare/v0.4.0...v0.5.0
