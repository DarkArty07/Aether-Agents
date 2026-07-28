# v0.20.0 Self-Improvement Bootstrap — Benchmark Report

## Scope

This report covers the default-off implementation baseline. It does not claim live operational validation because plugin activation and runtime restart were not authorized.

## Baseline

- Git baseline: `a88b5cc`
- Last official release: `v0.18.2`
- Technical predecessor: `v0.19.5`, closed `VIABLE — BOUNDED`, unpublished
- Candidate: `v0.20.0 — Self-Improvement Cycle Bootstrap`
- Logical provider: `custom:aether-router`
- Initial manifest digest: `sha256:fd74b6019a5d60a5cda11c01e59492dd3f3d6e592a182778ba5def9324d1273a`

## Test-first evidence

The first focused run failed collection because the new package did not exist. After importable seams were introduced, the behavioral contract produced 17 failures. Implementation then advanced through deterministic RED/GREEN increments.

Final results:

| Scope | Result |
|---|---:|
| Self-improvement bootstrap | 26 passed |
| Existing Aether continuity | 80 passed |
| Coordination subsystem | 943 passed |
| MCP server schema | 11 passed |
| Full repository | 1163 passed |
| Ruff | PASS |
| Python compile smoke | PASS |
| Plugin discovery | PASS — not enabled |

## Harmonia dogfooding

Two bounded admission attempts were made for the real implementation task:

1. `invalid_request` before admission because the contract repeated one worker, violating the fixed distinct-worker topology.
2. Corrected contract reached the configured boundary and returned `feature_disabled`, with no durable run or dispatch.

The first result is classified as a contract-construction failure. The second is configuration state, not a kernel defect. No `talk_to` fallback was used and no hidden worker execution occurred.

## Operational evidence state

The real project ledger was initialized only to validate schema, permissions, and deterministic evidence generation. Because the plugin remains disabled, it contains zero lifecycle sessions. The generated signal is therefore `REQUIRES_MORE_EVIDENCE`.

No before/after quality improvement, live provider route coverage, bounded specialist completion, or causal acceptance is claimed.

## Clean-checkout reconciliation

Isolation from the preserved dirty worktree corrected the reported coordination count from 953 to 943 and the initial full-suite count from 1170 to 1160. The ten removed tests belong to the uncommitted historical R8 pilot and are not candidate evidence. Three new nearest-repository isolation regressions then raised the candidate full-suite result to 1163 and the bootstrap scope to 26.

## Verdict

`IMPLEMENTATION BASELINE PASS — OPERATIONAL ACCEPTANCE PENDING`
