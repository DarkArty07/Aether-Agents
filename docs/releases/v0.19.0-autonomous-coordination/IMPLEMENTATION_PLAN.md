# v0.19.0 Autonomous Coordination — Implementation Plan

> **For Hermes:** execute this plan task by task only after the user says `aprobado`. Use Aether Daimons through Olympus, strict TDD, atomic commits, budget checks at every stage, and independent security gates where specified.

**Status:** **APPROVED 2026-07-18 — R5 COMPLETE, R6 BLOCKED BY THE CAPACITY GATE.** Authorization extends through code-complete, default-off R7; live activation and release remain on hold.

**Goal:** migrate Aether Agents from Hermes-relayed tool-style delegation to a contract-bounded autonomous team, using the transport-agnostic ideas of Cotal Core as design inspiration while preserving Aether semantic authority, Olympus lifecycle ownership, persistent Hermes profiles, and Telegram gateway continuity.

**Architecture:** implement an additive Aether-native coordination package behind a default-off feature flag. Cotal-inspired wire concepts provide principals, cards, envelopes, addressing modes, presence, channels, delivery classes, and default-deny ACL vocabulary. Aether adds the missing semantic control plane: immutable execution contracts, authoritative ledger, deterministic admission, PoP capabilities, effect reconciliation, independent review, Harmonia coordination, and evidenced closure. Native SQLite-backed dispatch is first; no NATS, JetStream, Cotal package, Cotal connector, fork, or second process manager is included.

**Tech stack:** Python `>=3.11`, existing Olympus/ACP, SQLite/aiosqlite only if Phase 0 proves the required transaction semantics, pytest, existing project lint/compile tools. No new runtime dependency is approved implicitly.

---

## 1. Approval contract

When the user says **`aprobado`**, that authorizes:

- Phase 0 source inspection and isolated tests;
- creation of v0.19.0 source, tests, schemas, and documentation in the declared paths;
- delegation to Aether Daimons with Luna as their fixed model;
- local test, lint, compile, and disposable-database execution;
- atomic commits on the v0.19.0 feature branch;
- read-only Codex balance checks using `/home/arty/Escritorio/codex-saldo.py`;
- autonomous execution through the code-complete, default-off shadow-mode gate.

Approval does **not** authorize:

- stopping, restarting, replacing, or killing `hermes-gateway.service`;
- editing the live gateway's `home/config.yaml`, `home/auth.json`, `.env`, systemd unit, Telegram token, or runtime state files;
- repairing or rotating the revoked Codex credential while the user is away;
- enabling v0.19 coordination in the current Telegram gateway;
- modifying or replacing Olympus as process/session lifecycle owner;
- installing Cotal, NATS, JetStream, or a Cotal connector;
- live E2–E4 effects, production migrations, external publication, PR merge, tag, or release;
- deleting `.aether`, `.olympus`, ledger history, credentials, branches, or user data.

Runtime activation and release publication require a later gate when the user can recover the gateway locally or an independently verified recovery channel exists.

## 2. Fixed decisions

1. Hermes remains `openai-codex/gpt-5.6-sol`.
2. All six Daimons remain `openai-codex/gpt-5.6-luna`; this is no longer a temporary experiment for v0.19 planning.
3. Hermes remains the only user-facing agent and the design/amendment/escalation authority.
4. Harmonia is the logical coordination steward, never a process or ACP-session manager.
5. Olympus/ACP remains the sole process/session lifecycle owner.
6. `.aether` remains project continuity; the Coordination Ledger is separate semantic runtime authority.
7. Cotal is inspiration, not a dependency, fork, connector, lifecycle owner, or semantic authority.
8. Initial dispatch is native and local behind `TransportAdapter`; JetStream remains post-v0.19 evidence-gated work.
9. v0.18.2 public MCP tools, `talk_to` actions, teardown, steering, and curation semantics remain compatible.
10. All new authority is additive, default-off, reversible, and fail-closed.

## 3. Cotal-Core inspiration boundary

| Cotal concept | Aether v0.19 adaptation | Explicit difference |
|---|---|---|
| Space | `project_id` / absolute `PROJECT_ROOT` boundary | No NATS account is required |
| Principal `(owner, actor)` | Aether installation/project + Daimon role/profile + Olympus session/runtime binding | Identity is Aether-issued and PoP-bound |
| AgentCard | `ParticipantCard` with role, capabilities, model, skills, status | Card metadata is descriptive, never authority |
| Message/Part/schema | Typed `CoordinationEnvelope` and namespaced parts | Envelope is also bound to contract generation and ledger sequence |
| Multicast | Contract/channel broadcast | Admission and ACL checks precede delivery |
| Unicast | Exact participant/session delivery | Recipient is contract-authorized and project-scoped |
| Anycast service | Deterministic role selection | Harmonia admission chooses only eligible Daimons |
| Presence | Durable participant status projection | Presence cannot authorize work or completion |
| Channel | Contract-scoped coordination channel | Channel instructions remain tainted advisory data |
| `live` / `durable` | Ephemeral notification / ledger-backed delivery | Native local implementation first; no JetStream requirement |
| `subscribe`, `allowSubscribe`, `allowPublish` | Active channels, read ACL, publish ACL | Publish remains default-deny and capability-bound |
| Message id dedupe | Inbox/outbox idempotency and semantic dedupe | Effects require separate receipts/reconciliation |
| Owner/actor forge isolation | PoP identity + audience/task/effect/target checks | Enforced at Aether mutation/effect boundary |

Not copied from Cotal:

- its Hermes connector, temporary `HERMES_HOME`, approvals-off mode, or no-resume lifecycle;
- its Manager as process supervisor;
- NATS subject grammar as Aether semantic authority;
- transport acknowledgements as task completion;
- static broker grants as sufficient E2–E4 capability enforcement;
- Cotal package structure or implementation code.

## 4. Gateway survival protocol

The current control channel is the live Telegram gateway. Until the user explicitly authorizes activation:

1. Record gateway PID, `ActiveState`, `SubState`, Telegram connection state, and current Git baseline before each implementation stage.
2. Never run `systemctl --user restart/stop`, `kill`, `pkill`, `hermes gateway`, gateway setup, auth reset, or configuration migration.
3. Freeze live-sensitive paths:
   - `home/config.yaml`
   - `home/auth.json`
   - `home/.env`
   - `home/gateway_state.json`
   - `~/.config/systemd/user/hermes-gateway.service*`
   - live profile `config.yaml` and auth stores
4. New runtime code must live behind a feature flag whose default is `false`; no startup import may require optional new state or dependencies.
5. Tests use `tmp_path`, unique database files, fake ACP/tool/effect adapters, and no live gateway ports, databases, processes, or credentials.
6. Source changes to `server.py`/`acp_manager.py` are delayed until the adapter phase and must preserve the old path as default.
7. After every stage, verify the original gateway PID is active and Telegram remains connected. Any degradation is a hard stop; do not attempt a risky restart.
8. Runtime activation, gateway restart, and E0/E1 pilot occur only under a later user-present gate.

## 5. Codex budget protocol

**Baseline captured 2026-07-18 18:45 CST:**

- `device_code`: 94% available;
- `codex-secondary`: unusable (`HTTP 401 token_revoked`);
- `openai-codex-oauth-4`: 53% available.

Budget rules:

1. Run `python /home/arty/Escritorio/codex-saldo.py`:
   - before Phase 0;
   - before and after every roadmap milestone;
   - before any bulk Hefesto delegation;
   - before every Athena review;
   - before final documentation/continuity closure.
2. Treat only healthy rows with numeric `Disponible` as usable capacity.
3. Use `openai-codex-oauth-4` as the logical reserve account.
4. Do not begin another model-intensive stage when the reserve account is at or below 15%; the 5-point margin protects the required final minimum of 10%.
5. Hard stop if all healthy accounts together cannot complete the current atomic gate without threatening the reserve.
6. Never repair, reorder, copy, rotate, or expose credentials while the user is away.
7. Record stage-level percentages without storing tokens, emails, account IDs, or JWT claims in the repository.
8. A completed atomic task is preferable to beginning the next stage and exhausting capacity midway.

## 6. Git and scope preparation

### Task 0.1 — Capture the pre-implementation baseline

**Objective:** preserve attribution in the existing dirty working tree.

**Evidence:** branch, HEAD, tracked diff, untracked path inventory, gateway state, test baseline label, and balance baseline.

**Actions after approval:**

1. Save a path-only baseline under `.aether`/session evidence, not credentials.
2. Classify every dirty path as v0.19 design, model lock, reusable skill, unrelated project skill, or runtime artifact.
3. Never use `git add -A`.
4. Exclude profile `.olympus/`, caches, runtime state, secrets, and unrelated skills.

### Task 0.2 — Reconcile and commit pre-code documentation

**Files:**

- Modify: `docs/releases/v0.19.0-autonomous-coordination/DESIGN.md`
- Modify: `docs/releases/v0.19.0-autonomous-coordination/RESEARCH.md`
- Modify: `docs/releases/v0.19.0-autonomous-coordination/FEASIBILITY.md`
- Modify: `docs/releases/v0.19.0-autonomous-coordination/MIGRATION_PLAN.md`
- Modify: `docs/releases/v0.19.0-autonomous-coordination/IMPLEMENTATION_PLAN.md`
- Modify: `docs/releases/v0.19.0-autonomous-coordination/ROADMAP.md`
- Add: `docs/releases/v0.19.0-autonomous-coordination/BASELINE.md`

**Acceptance:** all status language agrees; Ariadna's resolved 401 is not an active blocker; Luna is a fixed Daimon decision; Cotal inspiration boundary is consistent; local links and `git diff --check` pass.

**Atomic commit:** `docs: finalize v0.19 autonomous coordination plan`.

### Task 0.3 — Lock Luna reproducibly

**Files:**

- Verify/modify only tracked templates: `home/profiles/{hefesto,etalides,ariadna,daedalus,athena,ictinus}/config.yaml.template`
- Do not touch live profile configs during this gateway session.

**Acceptance:** six templates resolve to `openai-codex/gpt-5.6-luna`; Hermes template/config remains Sol; YAML parses; no credential or fallback is removed.

**Atomic commit:** `config: keep Luna as the Daimon model`.

## 7. Phase 0 — Prove extension seams before production code

### Task 1.1 — Map exact Olympus lifecycle and correlation seams

**Read:**

- `src/olympus_v3/server.py`
- `src/olympus_v3/acp_manager.py`
- `src/olympus_v3/db.py`
- `src/olympus_v3/aether_db.py`
- both Olympus/Aether hook packages
- installed Hermes/ACP types

**Test:** existing schema, lifecycle, steering, teardown, and curation tests.

**Acceptance:** document exact call sites where contract/session correlation can be added without another spawn/close owner.

### Task 1.2 — Prove storage semantics with a disposable micro-proof

Test a temporary SQLite store for:

- atomic append plus projection update;
- compare-and-swap contract transition;
- monotonic fencing epoch;
- transactional inbox/outbox;
- hash-chain/checkpoint verification;
- backup/restore and deterministic rebuild;
- conflicting writer rejection.

No production database migration is allowed.

### Task 1.3 — Prove capability/effect interception

Use fake tools and fake targets to prove expired, revoked, wrong-project, wrong-contract, wrong-generation, wrong-audience, wrong-task, wrong-target, wrong-effect, and stale-fence authority is rejected before execution.

### Task 1.4 — Produce the GO/NO-GO artifact

**Create:** `docs/releases/v0.19.0-autonomous-coordination/PHASE_0_EVIDENCE.md`

**Required verdict:** `GO`, `NO-GO`, or `GO WITH NAMED LIMITS` for each seam: lifecycle, store, identity, effect boundary, recovery, gateway isolation.

**Atomic commit:** `docs: record v0.19 phase 0 evidence`.

A Phase 0 NO-GO stops implementation and reports evidence; it does not trigger a speculative workaround.

## 8. Phase 1 — Cotal-inspired protocol core

### Task 2.1 — RED tests for principals and participant cards

**Create:**

- `src/olympus_v3/coordination/__init__.py`
- `src/olympus_v3/coordination/protocol.py`
- `tests/coordination/test_protocol.py`

Test immutable project-scoped principals, owner/actor separation, participant cards, role/model/skills metadata, and rejection of identity/card mismatch.

### Task 2.2 — RED tests for envelopes and addressing

Test exactly one route per envelope: channel multicast, exact-participant unicast, or role anycast. Test message IDs, timestamps, contract ID/generation, context/reply correlation, typed parts, payload bounds, sender mismatch, malformed routes, and unknown extension parts.

### Task 2.3 — Generate and validate schema

**Create:** `src/olympus_v3/coordination/schema.py` and a checked-in JSON schema under `docs/releases/v0.19.0-autonomous-coordination/schema/` only if repository conventions support generated schemas.

Shape authority is machine-verifiable; semantic authority remains the Aether design/contract.

**Atomic commit:** `feat(coordination): add Cotal-inspired protocol core`.

## 9. Phase 2 — Immutable contracts and state authority

### Task 3.1 — Contract-generation RED/GREEN cycle

**Create:**

- `src/olympus_v3/coordination/contracts.py`
- `tests/coordination/test_contracts.py`

Test immutable approved generations, scope/exclusions, owners/participants, evidence gates, side-effect policy, budget/retry limits, amendment creation, and stale-generation rejection.

### Task 3.2 — Legal state-machine RED/GREEN cycle

Test contract/task states, deterministic terminal states, ambiguity fail-closed behavior, and atomic amendment plus revocation-epoch advance.

**Atomic commit:** `feat(coordination): add immutable execution contracts`.

## 10. Phase 3 — Ledger, projections, fencing, and recovery

### Task 4.1 — Append-only ledger

**Create:**

- `src/olympus_v3/coordination/ledger.py`
- `src/olympus_v3/coordination/projections.py`
- `tests/coordination/test_ledger.py`

Test authenticated writer metadata, server sequence/time, hash continuity, checkpoints, tamper detection, projection rebuild, and restore verification.

### Task 4.2 — Harmonia lease and fencing

**Create:**

- `src/olympus_v3/coordination/leases.py`
- `tests/coordination/test_leases.py`

Test one logical lease, monotonic epoch, stale writer rejection, expiry, takeover, and restart recovery.

### Task 4.3 — Transactional inbox/outbox

Test durable intent before dispatch, duplicate receive dedupe, retry-safe delivery, poison-message termination, and no transport acknowledgement becoming semantic completion.

**Athena gate:** integrity, replay, stale authority, restore, and split-brain review.

**Atomic commit:** `feat(coordination): add integrity ledger and fenced recovery`.

## 11. Phase 4 — Identity, capabilities, channels, and presence

### Task 5.1 — Aether PoP workload identity

**Create:** `src/olympus_v3/coordination/identity.py` and tests.

Bind identity to installation, project, role, profile, Olympus session/runtime, audience, expiry, and revocation epoch. Phase 0 chooses the approved crypto/key boundary.

### Task 5.2 — Capability intersection and ACLs

**Create:** `src/olympus_v3/coordination/capabilities.py` and tests.

Effective authority is the intersection of role ceiling, contract grant, task grant, effect class, target, audience, generation, and fence. Channel publish is default-deny; active subscription never widens read ACL.

### Task 5.3 — Presence and channels as projections

**Create:**

- `src/olympus_v3/coordination/presence.py`
- `src/olympus_v3/coordination/channels.py`
- `tests/coordination/test_presence_channels.py`

Implement `idle`, `waiting`, `working`, `offline`; channel registry; active/read/publish separation; live/durable delivery class metadata; stale presence. Presence and channel instructions are advisory/tainted, never authority.

### Task 5.4 — Bounded context renderer

**Create:** `src/olympus_v3/coordination/context.py` and tests.

Preserve source, provenance, taint, authority separation, token/byte bounds, and safe omission summaries.

**Athena gate:** identity root, revocation, ACL containment, prompt injection, and secret references.

**Atomic commit:** `feat(coordination): add scoped identity channels and context`.

## 12. Phase 5 — Admission, Harmonia, and native dispatch

### Task 6.1 — Deterministic admission engine

**Create:** `src/olympus_v3/coordination/admission.py` and tests.

Check derivation from objective, scope, exclusions, dependencies/cycles, role ceiling, evidence, budget, retries, effect class, fan-out, payload, active leases, model/tool cost, and protected QA/recovery reserve.

### Task 6.2 — Harmonia logical coordinator

**Create:** `src/olympus_v3/coordination/harmonia.py` and tests.

Harmonia admits deterministic subtasks, maintains task graph/projections, selects eligible role anycast targets, monitors budgets/stalls/gates, and escalates ambiguity. It cannot spawn, close, cancel, amend contracts, make product decisions, or approve its own work.

### Task 6.3 — Native transport adapter

**Create:**

- `src/olympus_v3/coordination/transport.py`
- `src/olympus_v3/coordination/native_transport.py`
- `tests/coordination/test_transport.py`

Expose a protocol-only `TransportAdapter`; implement native ledger-backed dispatch. No Cotal/NATS/JetStream import or package.

### Task 6.4 — Olympus runtime adapter

**Create:** `src/olympus_v3/coordination/olympus_adapter.py` and tests.

Modify `server.py`/`acp_manager.py` only at the Phase 0-proven seam. Adapter maps admitted work to existing Olympus operations and observes technical results; it never owns processes/sessions.

**Athena gate:** lifecycle non-regression, fan-out, quota, replay, and Harmonia authority.

**Atomic commit:** `feat(coordination): add Harmonia admission and native dispatch`.

## 13. Phase 6 — Effects, independent review, and closure

### Task 7.1 — Effect classification and receipts

**Create:** `src/olympus_v3/coordination/effects.py` and tests.

Cover E0–E4, idempotency identities, unknown outcomes, E2/E3 reconcile-before-retry, no automatic E4 retry, exact typed approval binding, and secret-reference handling.

### Task 7.2 — Independent review

**Create:** `src/olympus_v3/coordination/review.py` and tests.

Reject owner/reviewer identity collision, self-review, stale review generation, and review outside role authority. Model prose is evidence, never the sole gate state.

### Task 7.3 — Two-stage semantic closure

**Create:** `src/olympus_v3/coordination/closure.py` and tests.

Owner proposes completion with evidence; Harmonia validates mechanically; Hermes/user retains reserved authority. Final states: `completed`, `partially_completed`, `failed`, `cancelled`.

Test cleanup order: stop admission → revoke capabilities → reconcile effects/sessions → release lease → publish continuity → idle shutdown.

**Athena gate:** E4, waivers, review independence, unknown effects, secrets, and recovery order.

**Atomic commit:** `feat(coordination): add reconciled effects and semantic closure`.

## 14. Phase 7 — Default-off shadow integration

### Task 8.1 — Feature flag and compatibility tests

Add a default-off coordination flag through the existing configuration schema/template path proven by Phase 0. The old `talk_to` flow remains unchanged when disabled.

Test five MCP tools, seven `talk_to` actions, multi-project isolation, steering, reusable sessions, curation, teardown, and no startup dependency on coordination state.

### Task 8.2 — Shadow-mode end-to-end

Use fake/local Daimons and disposable stores to compare ledger intent/results with existing Olympus execution without granting semantic authority or changing the live gateway.

### Task 8.3 — Failure and recovery suite

Exercise duplicate delivery, runtime loss, stale lease, revocation race, tampered ledger, projection loss/rebuild, unknown effects, reviewer violation, exhausted budget, and restart with feature disabled.

### Task 8.4 — Documentation and release-candidate evidence

Update README, AGENTS.md, website, release notes, config template documentation, migration/rollback runbook, and benchmark evidence. Keep runtime activation marked unexecuted.

**Atomic commit:** `feat(coordination): complete default-off shadow runtime`.

## 15. Validation matrix

After every atomic task:

```bash
python -m pytest <focused-test> -q
python /home/arty/Escritorio/codex-saldo.py
git diff --check -- <declared-paths>
```

After every phase:

```bash
python -m pytest tests -q
ruff check src tests
python -m compileall -q src
```

Also verify:

- gateway PID unchanged and service active;
- Telegram state `connected`;
- no live config/auth/runtime-state mutation;
- no Cotal/NATS/JetStream dependency;
- no second lifecycle owner;
- feature flag defaults off;
- old flow passes with coordination disabled;
- reserve account remains above the protected threshold.

If the full suite contains tests that manipulate the live gateway, replace them with isolated equivalents or defer them; never risk this Telegram control channel for test completeness.

## 16. Stop and escalation conditions

Stop immediately and report when any occurs:

- gateway or Telegram health degrades;
- a required test can run only by restarting/mutating the live gateway;
- reserve protection cannot be guaranteed;
- no healthy Codex credential remains;
- Phase 0 cannot prove a sole lifecycle owner or hard effect boundary;
- storage cannot provide atomic transitions/fencing/rebuild;
- a v0.18.2 invariant requires an unapproved breaking change;
- three Athena executions for one task fail;
- critical/high security finding remains unresolved;
- implementation requires Cotal/NATS/JetStream contrary to the approved architecture;
- unknown E2–E4 effect or credential mutation would be necessary.

## 17. Final gate

Successful completion of this plan means:

- v0.19.0 coordination code and tests exist in the feature branch;
- the subsystem is default-off and has passed isolated shadow-mode verification;
- the live Telegram gateway was never restarted or migrated;
- no live pilot, PR merge, tag, or release was performed;
- at least 10% remains in one healthy Codex account;
- the user receives exact commits, test output, budget state, residual risks, and activation instructions.

A later, user-present approval is required for live E0/E1 pilot, gateway restart, feature activation, merge, tag, and release publication.
