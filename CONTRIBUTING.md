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

1. Synchronize local `main` with `origin/main`.
2. Create one bounded feature branch from `main`.
3. Make your changes.
4. Run tests: `pytest`.
5. Run linter: `ruff check src/`.
6. Push and open a PR directly to `main`.

Before starting a new SemVer candidate, run:

```bash
python scripts/check_release_governance.py preflight-next-version --version X.Y.Z
```

## Branching Model

```text
feature/{name}  →  main
```

- **`main`** — Latest integrated, tested state. It may be ahead of the latest published release.
- **`feature/{name}`** — One bounded change, branched from current `origin/main` and merged back through a PR.
- **`vX.Y.Z` tag + GitHub Release** — Official published version, separate from integration.

Ordinary stacked PRs and long-lived integration branches are not supported. See `docs/decisions/ODR-0001-main-integration-and-release-automation.md`.

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

- **Feature → main:** Merge only after required checks pass. Preserve audited atomic history when it matters; squash only disposable branch history.
- **Release:** Tag the exact integrated `main` commit with annotated `vX.Y.Z`. The automated release workflow verifies metadata and creates or reconciles the GitHub Release.
- **Separation:** Merge, release, activation and deployment are distinct operations.

## Pull Requests

- Target `main`.
- Include a clear description of what and why.
- Reference related issues (`Fixes #12`, `Related to #8`).
- Ensure CI and release-governance checks pass.
- Do not start the next SemVer candidate while an earlier candidate PR remains unresolved.

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
- `home/config.yaml` — Orchestrator live config with secrets (gitignored)
- `home/.env` — Environment variables (gitignored)
- `home/profiles/<daimon>/config.yaml` — Daimon live configs (gitignored)
- Any `.venv/`, `node_modules/`, `dist/`, `__pycache__/` directory
- `.aether/` — Runtime state (gitignored)

## Architecture Overview

The v0.22.0 candidate contains three source boundaries:

1. **Hermes Agent** — user-facing agent framework, memory, skills, tools, and gateways.
2. **`aether_agents`** — product identity, contracts, continuity, evidence, effects, review, and inert self-improvement primitives.
3. **Daimon profiles** — versioned specialist contracts with no active execution runtime in this candidate.

The legacy execution package and MCP facade are absent. Do not restore a compatibility shim or hidden fallback; replacement execution remains gated by PDR-0011 and the v0.22 roadmap.

### .aether Continuity System

Daimon profiles launched independently may receive project context via the `.aether` plugin:
- **Capture:** Hooks write session data to `aether.db`
- **Injection:** `pre_llm_call` hook injects `[.aether Context]` on first turn

The candidate provides no Hermes continuity MCP facade and no supported Ariadna invocation path. Never edit `.aether/CONTEXT.md` or its database manually as a substitute.

## Questions?

Open an issue with the `question` label or start a discussion on GitHub.
