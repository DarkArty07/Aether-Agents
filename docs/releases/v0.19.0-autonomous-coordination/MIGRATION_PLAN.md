# v0.19.0 Autonomous Coordination — Migration Plan

**Status:** **AUTHORIZED FOR PHASE 0 THROUGH DEFAULT-OFF R7 IMPLEMENTATION.** The user's 2026-07-18 approval permits isolated proofs, source, tests, docs, Daimon execution, and atomic commits. It does not permit live gateway restart/activation, credential repair, Cotal/NATS/JetStream installation, real effects, merge, tag, or release.

**Continuation note (2026-07-25):** stages 0–4 below are historical implementation governance. R9–R14 now follow `KERNEL_CONVERGENCE_ROADMAP.md`. Athena is suspended globally until explicit user reactivation; future convergence gates use deterministic adversarial evidence and direct Hermes acceptance.

**Dependencies:** [DESIGN.md](DESIGN.md) is normative; [BASELINE.md](BASELINE.md) defines non-regression constraints; [FEASIBILITY.md](FEASIBILITY.md) defines stop conditions.

## Frozen approval boundaries

| Boundary | Frozen decision | Requires separate future approval |
|---|---|---|
| Initial architecture | Aether-native control plane over Olympus | Any change of semantic/lifecycle authority |
| Runtime ownership | Olympus/ACP is sole owner | Any Manager/broker/connector owning process/session |
| Transport | Native ledger-backed dispatch | Direct JetStream deployment; any Cotal connector |
| Cotal | Not adopted or forked | Evaluation, install, fork, connector modification, runtime use |
| Effects | E2–E4 require hard boundary design | Real target access, credentials, external execution |
| Version behavior | v0.18.2 preserved | Public tool/action/lifecycle breaking change |

## Reversible staged sequence

| Stage | Scope | Entry gate | Exit evidence | Rollback |
|---|---|---|---|---|
| 0. Extension-seam verification | Read-only source/schema inspection and isolated design validation | Explicit Phase 0 authorization | Documented actual seam map and GO/NO-GO against feasibility conditions | No production changes; discard isolated evidence artifacts only if separately authorized |
| 1. Pure domain model | Additive contract/event/state code behind disabled feature flag | Phase 0 GO + explicit coding authorization | TDD proof of immutable generations, transitions, projection rebuild | Disable flag; retain ledger records read-only |
| 2. Integrity/identity substrate | Store, hash/checkpoint, lease/fence, PoP capability validator | Stage 1 security review | TDD tamper/revocation/stale-fence/restore proof | Disable issuance; preserve append-only evidence |
| 3. Admission and native dispatch | Admission engine, inbox/outbox, Olympus Runtime Adapter in shadow mode | Historical security gate + lifecycle compatibility proof | Shadow records match old execution without semantic activation | Disable adapter/shadow writer; old `talk_to` flow remains |
| 4. Effects/reviews/closure | Tool-bound capability checks, reconciler, two-stage completion | E2/E3 test proof; no E4 live use | Deterministic reconciliation and independent-review tests | Disable new effect path; unresolved work enters safe reconciliation |
| 5. Limited opt-in pilot | Explicitly selected E0/E1 contract only | User-approved pilot contract and budget | Observed recovery/quota/closure evidence; no invariant breach | Stop admissions, revoke caps, reconcile, return to old execution |
| 6. Scale assessment | Consider direct JetStream transport seam only | Separate architecture/operations approval | Cost/security/runbook evidence | Retain native transport |

## Authorized isolated evidence proofs

The user authorized these proofs under the exact isolation, budget, cleanup, and gateway-survival boundaries in `IMPLEMENTATION_PLAN.md`. They must not access production secrets/targets.

1. **Olympus seam inventory:** inspect installed ACP types and existing call paths to determine whether project/session/runtime correlation can be propagated without changing `ACPManager` ownership.
2. **Ledger semantics micro-proof:** exercise a disposable proposed store for CAS/serializable transition conflicts, hash-chain checkpoint/rebuild, and backup/restore verification. No migration of `.aether` or Olympus data.
3. **Capability boundary micro-proof:** show a disposable fake tool refuses expired/revoked/wrong-audience/wrong-task/stale-fence PoP credentials. No real credentials or effects.
4. **Failure-recovery model proof:** controlled fake runtime/target validates recovery ordering and unknown-effect handling.
5. **Cotal compatibility proof (only if reconsidered):** source/API compatibility analysis first; no Cotal install/fork/runtime until an additional approval. Passing transport messages alone is insufficient.

## Gate discipline

- Every stage has a written entry decision, exact allowed paths, and explicit prohibited effects.
- Historical stage reviews remain evidence only. New milestones require deterministic adversarial matrices, direct Hermes verification, and explicit user authorization for a pilot; Athena must not be dispatched while suspended.
- Hermes decides contract/amendment/escalation; the user decides required architecture/product/release/E4/scope/waiver/external delivery acceptance.
- Failure of integrity, identity, independent review, secret handling, critical evidence, or unknown E4 is non-waivable for autonomous continuation.
- Rollback means safely disabling new authority, revoking capabilities, reconciling effects/sessions, preserving ledger evidence, and restoring baseline paths—not deleting history.

## Current authorization

**ACTIVE:** Stage 0 may execute now, followed by stages 1–4 only when each prior evidence/review gate passes. Stage 5 live pilot, stage 6 scale assessment, gateway activation, credential changes, merge, tag, and release remain blocked pending a later user-present approval.
