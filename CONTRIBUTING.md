# Contributing to Aether Agents

Thank you for your interest in contributing! This guide covers everything you need to get started.

## Quick Start

```bash
git clone https://github.com/DarkArty07/Aether-Agents.git
cd Aether-Agents
python3 -m venv venv
source venv/bin/activate
pip install pytest ruff pyyaml
```

## Development Setup

1. Synchronize local `main` with `origin/main`.
2. Create one bounded feature branch from `main`.
3. Make your changes.
4. Run tests: `pytest`.
5. Run linter: `ruff check tests/ scripts/check_release_governance.py`.
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

The v0.22.0 candidate contains three product boundaries:

1. **Hermes Agent** — user-facing agent framework, memory, skills, tools, and gateways.
2. **Aether product layer** — Hermes behavior, decisions, profiles, skills, participation policy, verification, semantic acceptance, and release authority.
3. **Orca execution substrate** — accepted bounded owner of Runs, Tasks, Dispatches, workers, messages, terminals, worktrees, recovery, and cleanup on the exact qualified binding; production registration remains a separate v0.23.0 gate.

The Olympus runtime, extracted native Python core, continuity plugins, package distribution, and legacy MCP facade are absent from the candidate source. Do not restore a compatibility shim, hidden fallback, or pre-emptive policy kernel. PDR-0014 closes v0.22.0 at bounded integration, governs production dogfooding through v0.23.0, and defers process-specific migration to v0.24.0.

### Protected `.aether` history

Existing `.aether` databases and `CONTEXT.md` files are preserved local/historical
state. This candidate has no profile plugin, hook, reader, writer, or migration path
for them. Never edit `.aether/CONTEXT.md` or its databases manually as a substitute.

Potentially conflicting parallel writers must use Orca child worktrees under one
feature integration branch. Sharing the current checkout is permitted only for
explicitly disjoint file scopes. Orca does not infer conflicts or file ownership.

## Questions?

Open an issue with the `question` label or start a discussion on GitHub.
