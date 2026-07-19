# v0.19.0 Autonomous Coordination — Roadmap

**Status:** **APPROVED 2026-07-18 — R0 ACTIVE.** Autonomous execution is authorized through default-off R7; live activation and release remain on hold.

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
| Pre-code design package | Present; final Git reconciliation pending |
| Coordination runtime | Not implemented |
| Gateway | Active |
| Telegram | Connected |
| Healthy Codex accounts | 2 of 3 |
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

**Status:** `ACTIVE`

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

**Status:** `READY AFTER R1 GO`

**Scope:**

- project-scoped owner/actor principals;
- ParticipantCard;
- typed envelope/parts/schema;
- multicast, unicast, and role anycast;
- correlation and dedupe IDs;
- immutable contract generations and legal transitions.

**Cotal boundary:** reuse concepts and semantics, not source code, NATS subjects, connector lifecycle, or package dependency.

**Exit evidence:** focused RED/GREEN tests plus full regression suite; malformed/sender-mismatch/stale-generation routes fail closed.

### R3 — Ledger, projections, fencing, and recovery

**Status:** `READY AFTER R2`

**Scope:** append-only authenticated Coordination Ledger, deterministic projections, checkpoints, tamper detection, restore/rebuild, transactional inbox/outbox, Harmonia lease, and monotonic fence.

**Exit evidence:** conflict, replay, duplicate, tamper, stale-fence, restore, and projection-equivalence tests.

**Athena gate:** integrity and split-brain review.

### R4 — Identity, capabilities, channels, presence, and context

**Status:** `READY AFTER R3`

**Scope:** Aether-issued PoP workload identity; task/effect/target/audience-scoped capabilities; online revocation; default-deny publishing; active/read/publish channel separation; live/durable metadata; presence projection; provenance/taint-preserving context renderer.

**Exit evidence:** expired, revoked, transferred, wrong-project, wrong-task, wrong-target, wrong-effect, stale-generation, and stale-fence authority is rejected. Peer/channel text never becomes system authority.

**Athena gate:** identity root, ACLs, injection, and secret handling.

### R5 — Harmonia admission and native dispatch

**Status:** `READY AFTER R4`

**Scope:** deterministic subtask admission, dependency graph, all resource quotas, protected QA/recovery reserve, role anycast, native `TransportAdapter`, transactional dispatch, and Olympus Runtime Adapter.

**Hard invariant:** Harmonia never spawns/closes/cancels processes or ACP sessions. Adapter calls existing Olympus lifecycle operations only.

**Exit evidence:** admitted work maps to existing Olympus execution; duplicates do not duplicate semantic transitions; ambiguity escalates; old `talk_to` remains default.

**Athena gate:** lifecycle, quota, replay, fan-out, and authority review.

### R6 — Effects, review independence, and closure

**Status:** `READY AFTER R5`

**Scope:** E0–E4 effects, receipts, idempotency, reconcile-before-retry, no automatic E4 retry, exact typed approvals, independent reviewer identity, owner proposal, Harmonia mechanical validation, and final semantic authority.

**Exit evidence:** unknown effects fail safe; self-review is rejected; cleanup order is deterministic; final states are only `completed`, `partially_completed`, `failed`, and `cancelled`.

**Athena gate:** no unresolved critical/high finding.

### R7 — Default-off shadow runtime and release hardening

**Status:** `READY AFTER R6`

**Scope:** feature flag default `false`; isolated shadow end-to-end; failure/recovery suite; compatibility with five MCP tools and seven `talk_to` actions; docs/config schema/runbook/release evidence.

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

Execution is active at R0 under this roadmap and `IMPLEMENTATION_PLAN.md`. Advancement remains evidence-gated; live activation and release stay on HOLD.
