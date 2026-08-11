# Cold-start guidance evidence

Observed: 2026-08-11. Disposition: active local hot test; not a stable prompt or product release.

## Implemented

- `home/SOUL.md` identifies Hermes Prompt SemVer `3.0.0-hot.3`.
- `src/aether_mcp/guidance.py` owns descriptions for exactly 15 tools.
- Every description includes ordered `WHEN`, `REQUIRES`, `ACCEPTS`, `EFFECT`, `RETURNS`, `NEXT`, `DO NOT USE FOR` and `RETRY / RECONCILE` sections.
- `server.py` derives public argument annotations from the versioned schema and preserves JSON-shaped strings.
- The live installation reports package `0.23.0.dev0`, enabled registration and 15 tools.

## Behavioral evidence preserved from the hot test

Fresh sessions correctly distinguished start from dispatch, selected reconciliation for an uncertain start, recognized model/provider authority at dispatch and treated `orca_call` as plan-only. A retired-handler regression led to explicit prohibition of private Olympus imports and stale aliases.

## Current boundary

Open processes do not reload source or `SOUL.md`; fresh sessions are required after installation/prompt changes. Comparative stable-promotion evidence and the model-backed production-entry case remain pending. No push, tag or publication is implied.

## Consolidation verification

The 2026-08-11 consolidation was verified from the single persistent `main` checkout:

- full test suite: `235 passed`;
- Ruff, Python byte-compilation, release governance and Git whitespace checks: pass;
- source `guidance.py` and `server.py`: byte-identical to the active installed package;
- active prompt: byte-identical to the `3.0.0-hot.3` archive;
- runtime status: enabled registration, ready provider and exactly 15 tools;
- retired runtime/profile paths: absent.
