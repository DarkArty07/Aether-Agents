# R7 Default-Off Completion Matrix

**Status:** ACTIVE — reconciled 2026-07-22

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
| Official config/schema flag default `false` | `PENDING` | `src/olympus_v3/config_loader.py`; canonical tracked template/schema | `tests/test_config_loader.py`, `tests/coordination/test_shadow_config.py` | absent=false; explicit false identical; malformed rejected; true parses without activation | No live config edit or startup side effect |
| Five MCP tools compatible while disabled | `PENDING` | existing `server.py` public registration | new compatibility matrix plus existing server tests | `talk_to`, `discover`, `aether_status`, `aether_update`, `aether_curate` unchanged | No coordination dependency at startup |
| Seven `talk_to` actions compatible while disabled | `PARTIAL` | existing Olympus handlers | current real probes cover open/message/poll/close; add cancel/delegate/steer and full equivalence | all seven actions pass isolated absent-vs-disabled comparison | No second lifecycle owner |
| Multi-project/reusable/steering/curation/teardown | `PENDING` | existing Olympus public APIs | isolated compatibility tests | exact project/AETHER_HOME isolation and teardown/curation semantics pass | No private runtime registry access |
| Duplicate/runtime/stale-generation/reviewer/budget observations | `DONE` | shadow conditions and verified comparison | focused fail-closed tests | typed mismatch/fail-closed; never semantic complete | Observational only |
| Stale lease and revocation race | `PENDING` | reuse leases/capabilities public APIs | `test_shadow_recovery.py` | stale fence/generation and revocation interleavings rejected | No automatic cancel/retry/effect |
| Tampered ledger and projection loss/rebuild | `PENDING` | reuse ledger/projections public APIs | disposable-store recovery tests | tamper rejected; rebuild equals authoritative events | No production DB |
| Unknown effects and partial/missing Olympus evidence | `PARTIAL` | reuse effects + evidence producer | extend recovery matrix | unknown/partial evidence fails closed | No effect execution |
| Restart with feature disabled | `PARTIAL` | current disabled return path | existing disabled no-effect test; add process/restart integration | no coordination state/import requirement after restart | Old path remains default |
| Durable restart-safe correlation/replay | `PENDING` | planned `shadow_store.py` disposable SQLite adapter | planned `test_shadow_store.py` | transactional uniqueness, idempotence, replay and corrupted-record tests | Test/disposable persistence only; not production identity |
| Isolated end-to-end system benchmark | `PENDING` | planned benchmark script | planned system test + JSON evidence/report | clean, dependency, parallel, failure, recovery and rollback scenarios | Zero lifecycle/effect calls by shadow |
| Documentation/config/runbook/release evidence | `PARTIAL` | roadmap, plan, current shadow evidence | link/requirement/diff review | README, AGENTS, site, notes, benchmark, rollback all agree | Activation remains unexecuted |
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