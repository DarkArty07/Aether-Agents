# R7 Default-Off Completion Matrix

**Status:** COMPLETE / DEFAULT-OFF — user decision gate 2026-07-22

**Baseline:** `8c2ddf9 feat(coordination): add verified shadow correlation`

**Boundary:** this matrix authorizes repository implementation, disposable stores, isolated tests, controlled zero-tool Olympus observation, documentation, and atomic commits. It does not authorize live configuration changes, gateway restart, runtime activation, production migration, real effects, R8, merge, tag, release, or publication.

## Classification

| State | Meaning |
|---|---|
| `DONE` | Committed artifact and executable evidence exist |
| `PARTIAL` | A verified slice exists but the normative matrix is incomplete |
| `PENDING` | Required R7 artifact/evidence does not yet exist |
| `ACTIVATION-ONLY` | Deliberately excluded from default-off completion; requires a later user gate |

## Task manifest

| Requirement | State | Production/artifact path | Test/evidence path | Completion command/gate | Authority/exclusion |
|---|---|---|---|---|---|
| Default-off observational core | `DONE` | `src/olympus_v3/coordination/shadow.py`, package exports | `tests/coordination/test_shadow.py`, `R7_SHADOW_EVIDENCE.md` | 30 focused / 444 coordination / 635 full tests; Athena PASS | Reads/computes only; `semantic_complete=false` |
| Actual Olympus evidence binding | `DONE` | `observe_olympus_session()` | exact-envelope and tamper tests; third controlled run | Exact `AETHER_SHADOW_V1` envelope and real OlympusDB re-read | Olympus remains authoritative for actual session/status |
| Deterministic↔actual session correlation | `DONE` | `ShadowSessionCorrelation`, bounded process registry | cross-binding, idempotence, capacity, signature tests | assignment/participant/session/status true; no mismatches | Correlation never rewrites either ID |
| Official config/schema flag default `false` | `DONE` | `src/olympus_v3/config_loader.py`, `home/olympus_v3.yaml.template` | `tests/coordination/test_shadow_config.py` | absent/false identical; malformed rejected; true parses without activation | No live config edit or startup side effect |
| Five MCP tools compatible while disabled | `DONE` | existing `server.py` public registration | `test_shadow_compatibility.py` plus existing server tests | all five handlers/schema remain usable | No coordination dependency at startup |
| Seven `talk_to` actions compatible while disabled | `DONE` | existing Olympus handlers | complete isolated action matrix | all seven actions preserve existing ownership/behavior | No second lifecycle owner |
| Multi-project/reusable/steering/curation/teardown | `DONE` | existing Olympus public APIs | compatibility + lifecycle/curation regression matrix | project isolation, reuse, steering and cleanup pass | No private runtime registry access |
| Duplicate/runtime/stale-generation/reviewer/budget observations | `DONE` | shadow conditions and verified comparison | focused fail-closed tests | typed mismatch/fail-closed; never semantic complete | Observational only |
| Stale lease and revocation race | `DONE` | leases/capabilities public APIs | `test_shadow_recovery.py` | stale fence/generation and revocation observations reject agreement | No automatic cancel/retry/effect |
| Tampered ledger and projection loss/rebuild | `DONE` | ledger/projections public APIs | disposable-store recovery tests | tamper rejected; rebuild equals authoritative events | No production DB |
| Unknown effects and partial/missing Olympus evidence | `DONE` | effects + evidence producer | recovery matrix | unknown/partial evidence fails closed | No effect execution |
| Restart with feature disabled | `DONE` | disabled return and config path | compatibility/system rollback tests | no observer/session/store access | Old path remains default |
| Durable restart-safe correlation/replay | `DONE` | `shadow_store.py` disposable SQLite adapter | `test_shadow_store.py` | transactional uniqueness, recreation, contention, bounds and corruption pass | Test/disposable persistence only; not production identity |
| Isolated end-to-end system benchmark | `DONE` | `scripts/run_r7_shadow_benchmark.py` | `test_r7_system.py`, JSON evidence/report | ten scenarios × five repetitions, twice; 25/25 faults, zero clean FP/calls | Zero lifecycle/effect calls by shadow |
| Documentation/config/runbook/release evidence | `DONE` | README, AGENTS, roadmap, plan, matrix, benchmark, runbook | link/requirement/diff review | current-facing docs distinguish completion from activation | Activation remains unexecuted |
| Live gateway/runtime activation | `ACTIVATION-ONLY` | none in R7 default-off work | later user-present pilot gate | explicit authorization + backup/rollback/health contract | Forbidden during this matrix |
| Production key custody, distributed identity/replay/mapping | `ACTIVATION-ONLY` | future design | future security/runtime tests | separately approved and independently reviewed | Process-local/disposable evidence is not production authority |
| R8, merge, tag, release/publication | `ACTIVATION-ONLY` | future release gate | future pilot/release evidence | explicit user decision after final benchmark | Forbidden during R7 completion |

## Per-milestone verification

Every code milestone must produce:

1. behavioral RED observed before production implementation;
2. focused GREEN and focused Ruff;
3. coordination regression and full suite when shared contracts/persistence change;
4. Ruff format check, `compileall`, and `git diff --check`;
5. negative ownership/dependency checks;
6. baseline-relative scope audit against `/tmp/aether-r7-completion-baseline.paths`;
7. explicit path staging and one atomic commit.

Never use `git add -A`. Existing unrelated `home/` changes and runtime artifacts remain outside every R7 commit.

## Closure gate

R7 may become `COMPLETE` only when every non-activation row is `DONE`, the complete default-off candidate has independent risk evidence, all sessions are logically closed, continuity is curated and read back, and the user receives the benchmark/decision package. Completion still leaves activation, pilot, merge, tag, and release on HOLD.

Closure evidence: final corrections at `317b359`; 70 focused R7, 514 coordination, and 705 full-suite tests pass. Athena attempts 1–2 provided actionable review and the named Medium findings were corrected. Attempt 3/3 completed without a payload, so no Athena PASS is claimed; this limitation is accepted only for inactive/default-off closure and cannot be carried into activation approval.