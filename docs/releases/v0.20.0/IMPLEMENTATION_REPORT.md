# v0.20.0 Self-Improvement Bootstrap — Implementation Report

## Verdict

`IMPLEMENTED — DEFAULT OFF`

The source increment approved under PDR-0009 is implemented and deterministically verified. It is not activated, operationally piloted, merged, tagged, released, deployed, or published.

## Delivered components

- `src/olympus_v3/self_improvement/manifest.py`
  - Strict `CYCLE.yaml` loader.
  - Canonical Aether project identity checks at the nearest Git repository boundary.
  - Fail-closed provider, persistence, authorization, and next-version invariants.
- `src/olympus_v3/self_improvement/ledger.py`
  - Project-local SQLite ledger at `.aether/self_improvement.db`.
  - Exact-once sessions, tool/model measurements, Harmonia classifications, interruption state, and deterministic aggregates.
  - `0600` file creation, symlink rejection, parameterized SQL, and atomic tool/coordination observations.
- `src/olympus_v3/self_improvement/hooks.py`
  - Hermes Agent hooks for session initialization, first-turn context, tool/model measurements, turn outcome, and finalization.
  - Concurrent live sessions are preserved; only provably stale owners require reconciliation.
  - Arguments, tool results, user messages, assistant responses, and conversation history are discarded.
- `src/olympus_v3/self_improvement/evidence.py`
  - Deterministic next-version signal aggregation.
  - Atomic release-evidence projection with no model-generated prose.
- `home/plugins/aether-self-improvement/`
  - Discoverable Hermes Agent plugin wrapper and manifest.
  - Deliberately absent from `plugins.enabled`.
- `tests/test_self_improvement.py`
  - Behavioral and adversarial contract for identity, isolation, exact-once initialization, concurrency, interruption, redaction, atomicity, evidence, and default-off discovery.

## Runtime boundaries

The plugin appears in `hermes plugins list` as:

- source: `user`
- version: `0.20.0`
- status: `not enabled`

The versioned Olympus MCP configuration excludes `talk_to`. The existing `harmonia` tool remains present but feature-disabled by configuration. No fallback was restored.

## Verification

- Bootstrap tests: `26 passed`
- Existing Aether continuity tests: `80 passed`
- Coordination subsystem tests: `943 passed`
- MCP server schema tests: `11 passed`
- Full repository suite: `1163 passed`
- Ruff: pass
- Python compilation: pass
- Manifest/default-off smoke: pass
- Plugin discovery smoke: pass, not enabled

## Remaining gates

The following remain intentionally open or blocked:

- live plugin activation;
- runtime restart;
- live Aether session observation;
- bounded Harmonia pilot;
- causal before/after acceptance;
- coordination key creation;
- merge, tag, release, deployment, and publication.

The next minor architecture remains undecided pending operational evidence and product-owner approval.
