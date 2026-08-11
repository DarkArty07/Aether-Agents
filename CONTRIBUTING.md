# Contributing

Aether currently uses one local checkout and one integration line: `main`. Do not create worktrees for routine changes. Publication remains a separate owner-authorized action.

Before changing the runtime:

1. read `AGENTS.md` and `docs/README.md`;
2. confirm the exact active contract in `src/aether_mcp`, `schemas/` and tests;
3. keep live files under `home/` out of Git;
4. implement one coherent scope;
5. run focused tests, Ruff and broader tests when a shared contract changed;
6. update canonical documentation in the same change.

Useful checks:

```bash
PYTHONPATH=src python -m pytest tests/aether_mcp -q
python -m ruff check src scripts tests
python -m compileall -q src scripts
make doctor
```

Do not restore Olympus, ACPManager, Harmonia, `talk_to`, Honcho, retired profiles or a hidden compatibility path. Do not commit secrets, runtime databases, installed provider binaries, session artifacts or generated graphs.
