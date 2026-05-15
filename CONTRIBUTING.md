# Contributing to Aether Agents

Thank you for your interest in contributing! This guide covers everything you need to get started.

## Quick Start

```bash
git clone https://github.com/DarkArty07/Aether-Agents.git
cd Aether-Agents
python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
```

## Development Setup

1. Create a feature branch from `dev` (not `main`)
2. Make your changes
3. Run tests: `pytest`
4. Run linter: `ruff check src/`
5. Push and open a PR to `dev`

## Branching Model

```
feature/{name}  →  dev  →  main
```

- **`main`** — Production-ready. Only receives merges from `dev` with a release tag.
- **`dev`** — Integration branch. All feature branches merge here first.
- **`feature/{name}`** — Individual features. Branch from `dev`, merge back to `dev`.

## Commit Format

```
type: concise subject line
```

Types: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`

Examples:
- `feat: add Ictinus L1 consultant with consult_action.py`
- `fix: buffer reset timing in event_translator.py`
- `docs: update README for v0.7.0`

One logical change per commit. Subject line under 72 characters.

## Merging

- **Feature → dev:** Squash merge preferred.
- **dev → main (release):** Merge commit with tag (`v{version}`).

## Pull Requests

- Target `dev` (not `main`) unless it's a hotfix.
- Include a clear description of what and why.
- Reference related issues (`Fixes #12`, `Related to #8`).
- Ensure CI passes (lint + tests).

## Code Style

- Python 3.11+
- Line length: 120 (configured in `pyproject.toml`)
- Linter: `ruff` with E, F, I, W rules
- Type hints on public APIs

## Reporting Issues

Use the GitHub issue templates:
- **Bug Report:** Include steps to reproduce, expected vs actual behavior, and environment details.
- **Feature Request:** Describe the problem, proposed solution, and alternatives considered.

## What NOT to Commit

Never commit:
- `home/profiles/hermes/config.yaml` — Live config with secrets
- `home/.pi-daimons/*/auth.json` — Credentials (gitignored)
- `home/profiles/hermes/.env` — Environment variables (gitignored)
- Any `.venv/`, `node_modules/`, `dist/`, `__pycache__/` directory
- `.aether/` — Runtime state (gitignored)

## Architecture Overview

Aether Agents uses a 3-layer orchestrator pattern:

1. **Hermes** — Orchestrator (MCP tools, memory, skills, delegation)
2. **Olympus v3** — MCP server bridging Hermes to Daimons (ACP + Plugin + SQLite)
3. **Daimons** — Specialized sub-agents (Hefesto, Etalides, Ariadna, Athena, Daedalus, Ictinus)

### .aether Continuity System

Daimons receive project context via the `.aether` plugin:
- **Capture:** Hooks write session data to `aether.db`
- **Curation:** Ariadna synthesizes `CONTEXT.md` (5 sections, 1500 chars max)
- **Injection:** `pre_llm_call` hook injects `[.aether Context]` on first turn

Hermes interacts with `.aether` via MCP tools: `aether_status`, `aether_update`, `aether_curate`.

## Questions?

Open an issue with the `question` label or start a discussion on GitHub.
