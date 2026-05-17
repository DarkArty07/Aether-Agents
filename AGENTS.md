# Aether Agents — Project Context

This file is the canonical project context. It is read automatically by hermes-agent, Cursor, and Claude Code.

## Git Conventions

### Branching Model

```
feature/{name}  →  dev  →  main
```

- **`main`** — Production-ready. Only receives merges from `dev` tagged with a release.
- **`dev`** — Integration branch. All feature branches merge here first.
- **`feature/{name}`** — Individual features. Branch from `dev`, merge back to `dev`.

**Rules:**
1. Never commit directly to `main`. Always merge from `dev`.
2. Never work directly on `main`. Always branch from `dev`.
3. After a release merge, `dev` and `main` must be at the same commit.
4. Delete feature branches after merging.

### Versioning

Semantic versioning: `MAJOR.MINOR.PATCH`

- **PATCH** (`0.5.1`) — Bug fixes, hotfixes, minor improvements. No new features.
- **MINOR** (`0.6.0`) — New features, new Daimons, new MCP actions. Backward compatible.
- **MAJOR** (`1.0.0`) — Breaking changes. API changes, configuration migration required.

Tag format: `v{version}` (e.g., `v0.5.1`, `v0.6.0`)

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

### Merging

- **Feature → dev:** Squash merge preferred. Keeps dev history clean.
- **dev → main (release):** Merge commit with tag. Preserves full history.
- **After release:** Verify `dev` and `main` are at the same commit hash.

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

When a Daimon is spawned, the aether plugin hooks inject project context automatically:
- `pre_llm_call` (first turn): reads hot_state + recent sessions, injects as [.aether Hot Start] context
- `on_session_start`: creates a session row in aether.db
- `post_tool_call`: detects write_file/patch/git commit, records file_changes
- `on_post_llm_call` (first turn): updates hot_state.last_request
- `on_session_end`: updates session status and hot_state

Hermes interacts with .aether via MCP tools (aether_status, aether_update), NOT via plugin.

### Database tables

- `hot_state` — single-row project snapshot (phase, task, last session, blockers, etc.)
- `sessions` — per-Daimon session history (agent, request, result, files modified)
- `file_changes` — file write/patch/commit tracking (session, agent, path, action)
- `decisions` — architectural decisions (title, rationale, alternatives, status)
- `issues` — blockers and errors (description, resolution, status)

### Plugin vs MCP

- **Plugin (aether_hooks)**: installed in ALL Daimons (hefesto, etalides, ariadna, daedalus, athena, ictinus). NOT in Hermes.
- **MCP tools (aether_status, aether_update)**: available to Hermes via the olympus-v3 server.
- **Ariadna** (future): periodic cron that synthesizes aether.db data into DESIGN.md.

All Daimon configs include `aether` in `plugins.enabled` alongside `olympus_v3`.