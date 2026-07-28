# v0.19.0 Autonomous Coordination — Feasibility and Recommendation

**Status:** **GO — staged default-off Aether-native implementation authorized on 2026-07-18.** **NO-GO for direct Cotal integration/fork in the initial v0.19 runtime.**

## 1. Fit-gap matrix

| Required property | Option A: Aether-native/Olympus | Option C: direct JetStream | Option B: Cotal transport-only |
|---|---|---|---|
| Hermes design/amendment authority | Strong: designed in | Strong if Aether control plane retained | Gap: connector/control model must be constrained |
| Olympus sole lifecycle owner | Strong | Strong | Blocking compatibility gap |
| Immutable semantic ledger/fencing | Strong: Aether-owned | Strong: Aether-owned | Not supplied as Aether semantic authority |
| Native current-profile/session fit | Strong baseline | Strong baseline | Blocking: temp home/no resume/launcher ownership evidence |
| PoP E2–E4 capability enforcement | Proposed, direct control | Proposed, direct control | Unknown connector/identity fit |
| Transport scale-out | Initial local only | Strong | Strong delivery features, but costly adaptation |
| Continuity `.aether` fit | Strong | Strong | Requires bridge and conflict prevention |
| Maturity/maintenance | Moderate new code, bounded surface | Operational burden | Draft/alpha plus significant adaptation surface |

Scoring is qualitative (5 best):

| Option | Authority fit | Lifecycle fit | Security control | Delivery scale | Maturity/maintenance | Total /25 |
|---|---:|---:|---:|---:|---:|---:|
| A: Aether-native + Olympus | 5 | 5 | 5 | 3 | 4 | **22** |
| C: direct JetStream adapter | 4 | 5 | 4 | 5 | 2 | **20** |
| B: Cotal transport-only | 2 | 1 | 2 | 4 | 1 | **10** |

## 2. Threat model (STRIDE plus agent-specific threats)

| Threat | Example | Hard control | Soft/residual control |
|---|---|---|---|
| Spoofing | Compromised runtime poses as reviewer | Aether PoP identity bound to project/role/session/instance/audience/expiry/revocation epoch | Model claims of identity are never trusted |
| Tampering | Rewrite gate/event history | Authenticated append-only ledger, sequence/time, hash chain, signed checkpoints, protected restore verification | Operational monitoring |
| Repudiation | Agent denies E4 request/review | Signed typed event, immutable approval/finding/receipt correlation | Narrative reports only summarize evidence |
| Information disclosure | Peer payload leaks secret or becomes privileged instruction | Opaque secret references, bounded taint/provenance renderer, target-scoped capabilities | Prompt instruction to avoid disclosure |
| Denial of service | Fan-out/retry/review challenge exhaustion | Quotas and protected QA/recovery reserve | Scheduler prioritization policy |
| Elevation of privilege | E1 token used for E3/E4 or stale coordinator authorizes action | PoP task/effect/target-scoped TTL capability, online E2–E4 revocation, fencing epoch checks at effect boundary | Role instructions |
| Replay/duplicate effects | Redelivered E3 causes duplicate mutation | Message/effect identity, transactional inbox/outbox, destination idempotency, reconcile before retry | Agent reminders |
| Prompt injection | External text asks recipient to change scope | Authority metadata separated from tainted payload; tools independently authorize | Prompt hardening |
| Collusive/self review | Same identity reviews own output | Distinct owner/runtime/credential/reviewer role | Shared-model systemic risk remains |
| Split brain | Old Harmonia writes after restart | Monotonic lease fencing; stale epoch rejection | Alerting |

**Hard controls** are enforced by cryptography, state transition logic, storage transaction/CAS semantics, or tool/effect boundary checks. **Soft controls** (prompt text, model judgment, advisory policy) cannot authorize effects and are recorded as residual risk.

## 3. Operational, cost, and maturity analysis

### Option A

- **Operational:** one Aether-owned store/control plane plus existing Olympus; no new broker on initial path.
- **Cost:** bounded implementation and operational scope; quotas reserve capacity for QA/recovery.
- **Maturity:** proposed new subsystem, so Phase 0 must prove seams and core failure modes before rollout.
- **Reversibility:** feature-gated and additive; old paths remain default through early stages.

### Option C

- **Operational:** adds broker deployment, retention, credentials, observability, and incident runbooks.
- **Cost:** infrastructure and operations cost are unknown; no spend is authorized.
- **Maturity:** JetStream is established, but its Aether adapter and authority boundary are unproven.

### Option B

- **Operational:** alpha connector and draft protocol plus possible Manager lifecycle conflict.
- **Cost/maintenance:** preserved LOC evidence shows a relevant adaptation surface comparable to Olympus production code.
- **Maturity:** insufficient compatibility evidence for a current-profile, resume, approval, and lifecycle-safe deployment.

## 4. GO/NO-GO conditions

### GO (future Phase 0 only)

All must be demonstrably true before implementation progresses beyond Phase 0:

1. Existing Olympus extension points can inject correlation/identity/capability context without changing Olympus lifecycle ownership.
2. A proposed Aether store can provide serializable/CAS transitions, durable transactionally recorded inbox/outbox, append-only chain/checkpoints, backup/restore verification, and projection rebuild.
3. Aether-controlled PoP identity and revocation model can be bound to the actual Olympus session/runtime and checked by the proposed tool/effect boundary.
4. Stale fencing epoch is rejected for every privileged mutation and E2–E4 authorization.
5. Context ingestion can preserve taint/provenance and prevents payload from becoming authority.
6. Failure/recovery test design covers ledger loss/tamper, transport duplication, runtime loss, unknown E4, stale lease, revocation, and independent-review violation.

### NO-GO / stop conditions

- Any non-waivable autonomous condition occurs.
- Phase 0 cannot demonstrate a sole lifecycle owner or a real enforcement boundary for E2–E4.
- Ledger integrity/checkpoint/restore cannot be verified.
- A required change breaks v0.18.2 compatibility invariants without separately approved migration.
- Direct Cotal integration/fork is proposed without separate user authorization and full compatibility proof.

## 5. Final recommendation

**APPROVED execution:** proceed with staged, reversible **Option A** under the authorized plan. Keep an explicit `TransportAdapter` seam; direct JetStream is a future scale-out candidate. **NO-GO:** direct Cotal integration or fork for initial v0.19 runtime. Candidate infrastructure and live activation remain unauthorized.
