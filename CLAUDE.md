# Aether Agents contributor guidance

This file guides coding assistants. Repository rules in [`AGENTS.md`](AGENTS.md) are
mandatory and take precedence; the contributing workflow is in
[`CONTRIBUTING.md`](CONTRIBUTING.md).

## Read before changing anything

1. Read [`README.md`](README.md), then [`DESIGN.md`](DESIGN.md),
   [`ROADMAP.md`](ROADMAP.md), and the specification for the affected area.
2. Read `AGENTS.md` before designing or making a capability claim. It requires upstream
   research before new design work and evidence from the source a runtime actually loads.
3. Keep changes within the relevant accepted specification or Objective Contract. Update
   the artifact that owns a decision before a derived artifact.

## Work safely and keep scope bounded

- Make one focused, reversible change at a time. Use the branch or worktree provided for
  the task, and do not absorb unrelated work.
- Do not add credentials, local profiles, sessions, databases, logs, caches,
  machine-specific paths, or generated runtime state to version control.
- A design, test result, or framework capability does not grant authority to activate a
  runtime, acquire credentials, publish, deploy, release, or make another external
  change. Follow the current task and repository authority for such effects.
- Do not weaken, remove, or skip tests to obtain a green result. Preserve accepted
  decisions and historical evidence unless their owning artifact changes.

## Set up and verify

From a fresh clone, install the locked development environment:

```bash
uv sync --frozen
```

Use the integrated exact-Hermes bootstrap for the full test suite; it owns the selected
Hermes checkout and test environment, so do not set `PYTHONPATH` manually:

```bash
uv run --frozen python scripts/run_tests.py
```

While iterating, run the narrowest relevant focused test. Before handoff, follow the
focused/full-test, Ruff, type-check, coverage, build, diff, and pull-request steps in
[`CONTRIBUTING.md`](CONTRIBUTING.md). Record the commands actually run, their results,
and any remaining material risk.
