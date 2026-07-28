# v0.20.0 Self-Improvement Instrumentation — Benchmark Report

## Scope

This report covers the default-off implementation baseline. It does not claim live operational validation because plugin activation and runtime restart were not authorized.

## Baseline

- Git baseline: `a88b5cc`
- Last official release: `v0.18.2`
- Technical predecessor: `v0.19.5`, closed `VIABLE — BOUNDED`, unpublished
- Candidate: `v0.20.0 — Self-Improvement Instrumentation`
- Logical provider: `custom:aether-router`
- Manifest digest: `sha256:f31a60f234ed127d27759c56f2a9769233654b920d5ed0996ef8d2f177ff1f8d`

> The previously recorded digest (`sha256:fd74b601…`) had gone stale: the manifest
> was edited after the report was written, so the stated baseline no longer
> described the shipped artifact. That is the same class of error this cycle
> exists to catch, which is why the digest is regenerated whenever this report
> changes. See `EXTERNAL_LOGIC_AUDIT.md` F-21.

## Test-first evidence

The first focused run failed collection because the new package did not exist. After importable seams were introduced, the behavioral contract produced 17 failures. Implementation then advanced through deterministic RED/GREEN increments.

Final results:

| Scope | Result |
|---|---:|
| Self-improvement contract (26 original + 28 audit and independent-review regressions) | 54 passed |
| Coordination subsystem | 944 passed |
| Full consolidated repository | 1198 passed |
| Ruff | PASS |
| Plugin discovery | PASS — not enabled |

The 26 original cases were **not modified** while the audit findings were fixed.
That constraint is deliberate: the audit's central finding (F-05) was that an
implementation and the tests judging it had been changed together, leaving a
green suite in a tree that failed two of its own safety properties. Every
correction had to satisfy the pre-existing contract as well as the new
regressions in `tests/test_self_improvement_contract.py`.

A second independent review initially blocked the candidate at `89cba0e`: an
explicit `project_root` could still redirect a foreign repository, and identical
tool calls across model requests inside one turn still collided. Commit
`b2cabfa` closes both gaps with four independent regressions. The first exact
checkout then reproduced F-23: `dispatch.unknown` was signed by the internal
ledger signer but replay attempted external-writer authentication. Commit
`a0852d8` corrects the event class, adds a deterministic regression, and the
original concurrent test passed twenty consecutive executions. See
`INDEPENDENT_PHASE1_REVIEW.md`.

One intended fix was **withheld** for the same reason. Redesigning the
`authorization` block so that granting a gate opens it rather than invalidating
the manifest (F-08) would have required rewriting
`test_rejects_contract_that_authorizes_activation_or_release`. The interlock is
therefore left as designed and only its silence was fixed: an identity failure
against a directory that does carry a manifest is now logged. Changing the
interlock's semantics is a product-owner decision, not an implementation one.

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
