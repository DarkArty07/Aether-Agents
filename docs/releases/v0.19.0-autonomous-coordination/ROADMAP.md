# v0.19.0 Autonomous Coordination — Roadmap

**Status:** **APPROVED 2026-07-18 — R7 COMPLETE / DEFAULT-OFF (2026-07-22).** The complete isolated integration, benchmark, documentation, and bounded final review are closed. Live activation, pilot, R8, merge, tag, and release remain on hold pending the user's decision.

**Release objective:** migrate Aether Agents to a contract-bounded autonomous team using Cotal Core's transport-agnostic coordination concepts as inspiration, while preserving Hermes as user-facing design authority, Olympus/ACP as sole process/session lifecycle owner, `.aether` as project continuity, and the current Telegram gateway as a protected control channel.

**Normative sources:** [DESIGN.md](DESIGN.md), [BASELINE.md](BASELINE.md), [RESEARCH.md](RESEARCH.md), [FEASIBILITY.md](FEASIBILITY.md), [MIGRATION_PLAN.md](MIGRATION_PLAN.md), and [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md).

## 1. Non-negotiable release decisions

- Hermes: `openai-codex/gpt-5.6-sol`.
- All six Daimons: `openai-codex/gpt-5.6-luna`.
- Cotal Core is inspiration, not a dependency/fork/connector.
- Initial transport is native ledger-backed dispatch.
- Olympus owns every process and ACP session.
- Harmonia coordinates contracts/tasks but owns no runtime lifecycle.
- New coordination remains feature-gated and default-off through code completion.
- No current Telegram gateway restart or live activation while the user is away.
- No Cotal, NATS, or JetStream install in v0.19 initial implementation.
- At least 10% must remain in one healthy Codex account.

## 2. Current verified baseline

| Item | State |
|---|---|
| Published version | `v0.18.2` |
| Working branch | `feature/v0.19.0-autonomous-coordination-design` |
| Pre-code design package | Reconciled and committed |
| Coordination runtime | Protocol and immutable-contract core implemented; runtime integration not active |
| Gateway | Active |
| Telegram | Connected |
| Healthy Codex accounts | 2 active; revoked third credential removed |
| Available at planning baseline | 94% + 53% |
| Revoked account | `codex-secondary` |
| Protected reserve | `openai-codex-oauth-4`; stop initiating work at 15% to preserve ≥10% |
| Active blockers in `.aether` | None |
| Known source observation | stale Olympus module prose (#12) |

The old roadmap entry claiming Ariadna is blocked by HTTP 401 is resolved and is not an active release blocker.

## 3. Release path

```text
P0  Plan approval
      |
      v
R0  Baseline safety + Git/document reconciliation
      |
      v
R1  Phase 0 extension/store/enforcement evidence
      |
      +-- NO-GO --> stop with evidence
      |
      v GO
R2  Cotal-inspired protocol core + immutable contracts
      |
      v
R3  Ledger + projections + fencing + recovery
      |
      v
R4  PoP identity + capabilities + channels + presence + safe context
      |
      v
R5  Harmonia admission + native dispatch + Olympus adapter
      |
      v
R6  Effects + independent review + semantic closure
      |
      v
R7  Default-off shadow integration + hardening
      |
      v
HOLD  User-present activation gate
      |
      v
R8  Guarded E0/E1 pilot, merge, tag, and v0.19.0 publication
```

## 4. Status model

| Status | Meaning |
|---|---|
| `COMPLETE` | Evidence exists and the gate passed |
| `READY` | Fully planned and waiting for its entry authorization/dependency |
| `ACTIVE` | Currently executing |
| `BLOCKED` | Named condition prevents execution |
| `HOLD` | Intentionally deferred for user-present safety |
| `DEFERRED` | Outside initial v0.19 scope |

## 5. Milestones

### P0 — User approval

**Status:** `COMPLETE — APPROVED 2026-07-18`

Approval starts autonomous implementation under the exact scope in `IMPLEMENTATION_PLAN.md`. It permits code, isolated tests, documentation, Daimon work, balance checks, and atomic commits. It does not permit live gateway restart/activation, credential repair, external effects, merge, tag, or release.

**Exit gate:** satisfied; user authorized autonomous execution and directed Hermes to stop only for an unresolved problem.

### R0 — Safety baseline and pre-code consolidation

**Status:** `COMPLETE — 2026-07-18`

**Deliverables:**

1. exact dirty-tree baseline and path classification;
2. gateway PID/state and Telegram connection baseline;
3. Codex balance baseline and reserve marker;
4. reconciled seven-document pre-code package;
5. stale Ariadna blocker removed from canonical roadmap;
6. Luna locked in all six tracked Daimon templates, Hermes kept on Sol;
7. atomic documentation and model-template commits;
8. runtime `.olympus`, caches, secrets, auth, and unrelated skills excluded.

**Exit evidence:** clean scope audit, YAML parse, local-link validation, `git diff --check`, gateway/Telegram unchanged.

**Rollback:** commits are additive/documentary; revert exact commits without touching live gateway state.

### R1 — Phase 0 feasibility proof

**Status:** `COMPLETE — GO WITH NAMED LIMITS (2026-07-18)`

**Deliverable:** `PHASE_0_EVIDENCE.md` with exact source/type/schema evidence and per-seam verdicts.

**Proof obligations:**

- Olympus correlation seam without second lifecycle owner;
- hard tool/effect interception boundary;
- disposable store proving atomic transitions, fencing, inbox/outbox, integrity, checkpoint/restore, and rebuild;
- PoP identity binding to actual project/session/runtime;
- recovery model for duplicate delivery, stale lease, revocation, tamper, runtime loss, and unknown effects;
- gateway isolation proof.

**Exit:** `GO`, `GO WITH NAMED LIMITS`, or `NO-GO`.

**Stop:** any core authority or safety property cannot be enforced outside prompt prose.

### R2 — Cotal-inspired protocol core and immutable contracts

**Status:** `COMPLETE — ATHENA QA ATTEMPT 2 PASS (2026-07-18)`

**Scope:**

- project-scoped owner/actor principals;
- ParticipantCard;
- typed envelope/parts/schema;
- multicast, unicast, and role anycast;
- correlation and dedupe IDs;
- immutable contract generations and legal transitions.

**Cotal boundary:** reuse concepts and semantics, not source code, NATS subjects, connector lifecycle, or package dependency.

**Exit evidence:** focused RED/GREEN tests plus full regression suite; malformed/sender-mismatch/stale-generation routes fail closed.

**Verified result:** protocol and contracts committed in `11e5424` and `61497ba`; 30 coordination tests and 194 full-suite tests pass. Ruff, strict JSON round trips, active-contract authority, amendment-authority, actor, gate, role-permission, metadata-bound, and stale-generation checks pass. Athena attempt 1 found structural authority bypasses; the complete equivalence class was corrected and attempt 2 passed with no Critical/High finding.

### R3 — Ledger, projections, fencing, and recovery

**Status:** `R3 CLOSED — HITL EXCEPTION RECORDED / ATOMIC COMMIT (2026-07-19)`

**Scope:** append-only authenticated Coordination Ledger, deterministic projections, checkpoints, tamper detection, restore/rebuild, transactional inbox/outbox, Harmonia lease, and monotonic fence.

**Current evidence:** the committed default-off implementation at `1c8ba07` passes 131 coordination tests and 295 full-suite tests. Ruff, compileall, and `git diff --check` pass. The executable matrix covers contract/inbox/outbox atomicity, lease and authority fencing, authenticated tamper, external-anchor rollback protection, persisted projection equivalence, verified two-phase restore, bounded poison termination, input bounds, subprocess contention, abrupt writer death, takeover, and permanent rejection of old fences.

**Canonical handoff:** [`R3_SESSION_HANDOFF.md`](R3_SESSION_HANDOFF.md) records the original blocked handoff and the superseding 2026-07-19 evidence matrix. Athena attempt 1 produced no verdict because its selected credential returned `usage_limit_reached`; attempt 2 found a poison-projection consistency defect plus missing input bounds. Those findings are corrected and locally verified. Attempt 3 again produced no verdict because the profile selected the exhausted credential and received `HTTP 429` for all three internal retries. The maximum Athena execution count is exhausted. The user explicitly approved a bounded HITL exception to close R3 without another reviewer execution; R4 and runtime activation remain blocked independently.

**Exit evidence required:** conflict, replay, duplicate, authenticated tamper, stale-fence, external-anchor rollback, verified restore, projection-equivalence, bounded poison, and writer-death/contention tests.

**Athena gate:** exhausted without a final verdict after `qa_attempt=3`. The explicit HITL exception closed R3 after a fresh deterministic matrix, 20/20 contention stress, and protected-path/staging audit. It does not convert the absent verdict into PASS, permit a fourth Athena execution, or authorize R4/runtime activation.

### R4 — Identity, capabilities, channels, presence, and context

**Status:** `COMPLETE — ISOLATED / DEFAULT-OFF / ATHENA PASS (2026-07-20)`

**Scope:** Aether-issued PoP workload identity; task/effect/target/audience-scoped capabilities; online revocation; default-deny publishing; active/read/publish channel separation; live/durable metadata; presence projection; provenance/taint-preserving context renderer.

**Exit evidence:** expired, revoked, transferred, wrong-project, wrong-task, wrong-target, wrong-effect, stale-generation, and stale-fence authority is rejected. Peer/channel text never becomes system authority.

**Verified result:** the isolated implementation passes 304 coordination tests and 468 full-suite tests. Ruff, compileall, `git diff --check`, AST/secret scanning, protected-path isolation, key-purpose separation, issuer/audience/workload binding, atomic in-process replay consumption, channel/ACL exact binding, advisory-only presence, and bounded provenance/taint-preserving context checks pass. No runtime adapter or dispatcher call site was added.

**Athena gate:** `qa_attempt=1` found a blocking concurrent replay-cache race and an unbounded holder-proof transcript. Both equivalence classes were corrected with deterministic RED/GREEN tests. `qa_attempt=2` reproduced the fixes, reviewed identity root, ACLs, injection, secret handling, and the complete R4 boundary, then returned **PASS / BLOCKING: no** with no Critical/High finding. Production key custody, shared durable replay, authenticated presence-source admission, and trusted live `AuthoritySnapshot` derivation remain mandatory before runtime activation.

### R5 — Harmonia admission and native dispatch

**Status:** `COMPLETE — DEFAULT-OFF / ATHENA QA ATTEMPT 3 PASS (2026-07-20)`

**Scope:** deterministic subtask admission, dependency graph, all resource quotas, protected QA/recovery reserve, role anycast, native `TransportAdapter`, transactional dispatch, and Olympus Runtime Adapter.

**Hard invariant:** Harmonia never spawns/closes/cancels processes or ACP sessions. Adapter calls existing Olympus lifecycle operations only.

**Exit evidence:** admitted work maps to existing Olympus execution; duplicates do not duplicate semantic transitions; ambiguity escalates; old `talk_to` remains default.

**Athena gate:** lifecycle, quota, replay, fan-out, and authority review.

**Verified result:** deterministic admission, Harmonia planning, native protocol and ledger-backed dispatch, and the Olympus Runtime Adapter were committed in `4c910cf`, `03ef6e7`, `bd8d37c`, `718728f`, and `526d85a`. The final matrix passes 350 coordination tests and 541 full-suite tests; Ruff, compileall, diff checks, public-API ownership scanning, gateway stability, default-off isolation, cancellation rollback, canonical prompt binding, malformed-plan rejection, concurrent replay reservation, and canonical project-root separation pass. Athena attempt 1 found an admission/projection/prompt binding bypass; attempt 2 verified that closure and found a project-root replay collision; attempt 3 verified both complete equivalence classes and returned **PASS / BLOCKING: no**. Durable multi-process idempotency and issue #26 key custody remain mandatory before runtime activation.

### R6 — Effects, review independence, and closure

**Status:** `COMPLETE — DEFAULT-OFF / ATHENA QA ATTEMPT 3 PASS (2026-07-21)`

**Scope:** E0–E4 effects, receipts, idempotency, reconcile-before-retry, no automatic E4 retry, exact typed approvals, independent reviewer identity, owner proposal, Harmonia mechanical validation, and final semantic authority.

**Exit evidence:** unknown effects fail safe; self-review is rejected; cleanup order is deterministic; final states are only `completed`, `partially_completed`, `failed`, and `cancelled`.

**Athena gate:** no unresolved critical/high finding.

**Verified result:** the isolated implementation covers provenance-controlled E0–E4 lifecycle transitions, exact idempotency identity, authenticated single-use E4 approvals, bound receipts, independent review, typed findings/evidence, signed waivers, authenticated gate evaluations, two-stage semantic closure, and deterministic cleanup. The final matrix passes 64 focused R6 tests, 414 coordination tests, and 605 full-suite tests; Ruff, formatting, compileall, diff checks, adversarial tamper/replay/scope probes, and protected-path scope audit pass. Athena attempts 1 and 2 found four caller-assertion bypasses across receipts, gate evaluation, and closure; the complete equivalence classes were corrected. Attempt 3 reverified every prior finding and returned **PASS / BLOCKING: no** with high confidence.

**R7 activation prerequisites:** process-local HMAC/replay state, caller-provided test keys, durable distributed replay, production key custody, and ledger-derived closure facts remain explicit R7 blockers. No gateway/runtime activation occurred. The earlier capacity entry blocker was removed after the user explicitly authorized continued compute on 2026-07-21.

### R7 — Default-off shadow runtime and release hardening

**Status:** `COMPLETE — DEFAULT-OFF / USER DECISION GATE`

**Scope:** feature flag default `false`; isolated shadow end-to-end; failure/recovery suite; compatibility with five MCP tools and seven `talk_to` actions; docs/config schema/runbook/release evidence.

**Verified implementation:** commits `8c2ddf9`, `343bbeb`, `fa0cb58`, `1707f4b`, `74de60b`, and `8a39196` provide the authenticated shadow core, official default-false config seam, complete five-tool/seven-action compatibility matrix, advanced fail-closed recovery observations, disposable restart-safe correlation, and a ten-scenario benchmark. Three controlled zero-tool Olympus runs established the real correlation seam. The local benchmark ran 50 scenarios twice through actual shadow APIs, detected 25/25 injected failures, produced zero clean false positives, and made zero lifecycle/effect calls; `semantic_complete` remained false.

**Final closure:** Athena attempts 1 and 2 found process-local context/replay and same-instance SQLite boundary defects. They were corrected with deterministic regressions; final local validation passes 70 focused R7, 514 coordination, and 705 full-suite tests, and concurrent durable-store initialization was stress-repeated after correction in `9590159`. The third and maximum Athena execution returned no review payload, so it is recorded as an evidence-unavailable final attempt rather than a PASS. No Critical/High finding remained after attempt 2, and every named Medium equivalence class was corrected and reproduced locally. R7 default-off is therefore closed with this explicit review limitation; activation still requires a separate user-approved design and security gate.

**Exit evidence:**

- focused and full tests pass with actual output;
- lint and compile pass;
- no Cotal/NATS/JetStream dependency;
- no second lifecycle owner;
- old execution works when disabled;
- live Telegram gateway PID and connection stayed healthy;
- minimum Codex reserve remains;
- code is committed but not activated.

### HOLD — User-present activation gate

**Status:** `HOLD`

No gateway restart, live feature activation, production database migration, or real E0/E1 pilot occurs while the user cannot recover the machine.

**Required before release:**

1. user confirms presence or independent recovery access;
2. verified backup and rollback command;
3. current gateway health snapshot;
4. explicit pilot contract, participants, budget, paths, and stop conditions;
5. activation only after feature-disabled rollback is proven.

### R8 — Guarded pilot and v0.19.0 publication

**Status:** `HOLD AFTER R7`

**Scope:** one reversible E0/E1-only contract, then release hardening, PR, merge, synchronized version bump, tag, and release.

**Excluded:** E2–E4 autonomous rollout, Cotal connector, NATS/JetStream deployment, broad production rollout, or lifecycle replacement.

## 6. Budget gates

Every milestone uses this sequence:

```text
saldo-before
  -> gateway-health
  -> one atomic milestone
  -> focused/full verification
  -> saldo-after
  -> gateway-health
  -> commit/report
```

| Condition | Action |
|---|---|
| Two healthy accounts and reserve >15% | Continue |
| Reserve ≤15% | Finish only the current bounded verification; do not start another model-intensive milestone |
| Reserve would fall below 10% | Hard stop before another model call |
| No healthy credential | Stop and report; do not mutate auth |
| Saldo query fails | Retry once; if still unknown, stop before a new milestone |
| Revoked credential remains revoked | Ignore it; no repair while user is away |

## 7. Gateway health gates

Before and after every milestone require:

- `hermes-gateway.service` active/running;
- original live gateway process healthy;
- Telegram platform state `connected`;
- no restart requested;
- no live auth/config/systemd/runtime-state diff;
- no test touching live ports/databases/processes;
- no code path activated in the running gateway.

Gateway degradation overrides roadmap progress and budget permission. Stop; do not attempt a risky self-revival.

## 8. Atomic commit sequence

Planned boundaries:

1. `docs: finalize v0.19 autonomous coordination plan`
2. `config: keep Luna as the Daimon model`
3. `docs: record v0.19 phase 0 evidence`
4. `feat(coordination): add Cotal-inspired protocol core`
5. `feat(coordination): add immutable execution contracts`
6. `feat(coordination): add integrity ledger and fenced recovery`
7. `feat(coordination): add scoped identity channels and context`
8. `feat(coordination): add Harmonia admission and native dispatch`
9. `feat(coordination): add reconciled effects and semantic closure`
10. `feat(coordination): complete default-off shadow runtime`
11. `docs: add v0.19 release candidate evidence`

No commit uses blanket staging. Each commit includes only declared source/tests/docs.

## 9. Deferred work

- direct Cotal integration or fork;
- Cotal Hermes connector;
- NATS/JetStream deployment;
- multi-host scale-out;
- E2–E4 autonomous execution;
- live activation while the user is away;
- general production rollout;
- replacing Olympus lifecycle ownership;
- universal exactly-once claims.

## 10. Completion definition for the approved autonomous run

The autonomous run ends successfully at R7 when:

- the full default-off implementation and tests exist;
- Phase 0 and every security gate have evidence;
- atomic commits preserve clean scope;
- the current Telegram gateway has remained alive and connected;
- at least 10% remains in one healthy Codex account;
- no live migration, restart, merge, tag, or release was attempted;
- the user receives a concise report with commits, tests, balance, unresolved risks, and the exact user-present activation gate.

Execution is active at R7 under this roadmap, `IMPLEMENTATION_PLAN.md`, and `R7_COMPLETION_MATRIX.md`. Advancement remains evidence-gated; live activation and release stay on HOLD.
