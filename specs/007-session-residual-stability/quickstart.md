# Verification quickstart

Resolve exact test nodes from the final design and run focused RED/GREEN first.
All local test commands must remove inherited `HERMES_DELEGATED_CHILD_CONTEXT`,
`HERMES_KANBAN_*` and outer `HERMES_SESSION_*` selectors; a parent TUI can expose them
even though the candidate itself is not a delegated child. Record the scrubbed environment
shape, never identity values.

Minimum Aether gates:

```bash
uv sync --frozen
uv run --frozen pytest -q <focused nodes for #396/#397/#399>
uv run --frozen ruff check src/aether_agents tests scripts
uv run --frozen ruff format --check src/aether_agents tests scripts
uv run --frozen mypy src/aether_agents
uv run --frozen pytest -q --cov=aether_agents --cov-report=term-missing
uv run --frozen python scripts/run_tests.py
uv run --frozen python scripts/check_documentation.py
uv build
```

Fork lane when #399 changes packaging intent:

```bash
<fork runner> <focused packaging tests>
<fork runner> <neighboring import/startup tests>
```

## Runtime canaries

- #396: one new isolated contract board with root and child transition; `aether observe`
  from an exact fresh source must report those units and fresh `as_of`/coverage, with no raw content.
- #397: run the reviewed writer probe against a disposable board while hashing/counting
  the selected live board before and after; only the disposable DB may change.
- #399: both provisioned interpreters under `env -i` and `python -I` resolve every intended
  top-level module from the same exact source. The source and dirty-state manifest remain
  byte-identical across reconciliation.

## GitHub and cleanup

Required checks must be green without bypass. Close #396/#397/#399 only after their exact
canaries. Update the dedicated Aether runtime checkout to merged `main`, restart only if loaded
modules changed and only at a worker-safe boundary, verify the active import source, then remove
objective-owned merged branches/worktrees. Preserve the active Monitor flow, unrelated worktrees,
stashes and any unmerged branch with unique evidence.
