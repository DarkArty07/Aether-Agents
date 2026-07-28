# v0.19.0 Autonomous Coordination — Research

**Status:** evidence synthesis for the pre-code gate. Labels are deliberate: **VERIFIED** is source/repository evidence; **INFERRED** is a reasoned consequence; **UNKNOWN** needs a Phase 0 proof; **BLOCKED** is not authorized now.

## 1. Candidate landscape

| Candidate | Intended role | Fit status |
|---|---|---|
| Aether-native control plane + Olympus | Contract semantics, ledger, admission, capabilities, reconciliation | **APPROVED direction** |
| NATS JetStream directly | Future durable transport scale-out | **PROPOSED Option C** |
| Cotal transport-only | Future adapter candidate | **PROPOSED Option B; ranked last** |
| LangGraph persistence | Library-level workflow/checkpoint aid | **INFERRED insufficient as control-plane authority** |
| Temporal | Durable workflow engine | **INFERRED poor lifecycle/profile fit until proven** |

## 2. Cotal evidence and fit-gap

### Primary sources

- **VERIFIED source:** [Cotal repository](https://github.com/Cotal-AI/Cotal)
- **VERIFIED source:** [SPEC Draft v0.3](https://github.com/Cotal-AI/Cotal/blob/main/SPEC.md)
- **VERIFIED source:** [architecture](https://github.com/Cotal-AI/Cotal/blob/main/docs/architecture.md)
- **VERIFIED source:** [channels and permissions](https://github.com/Cotal-AI/Cotal/blob/main/docs/channels-and-permissions.md)
- **VERIFIED source:** [Hermes connector](https://github.com/Cotal-AI/Cotal/blob/main/docs/connect-hermes.md)
- **VERIFIED source:** [`launch.ts`](https://github.com/Cotal-AI/Cotal/blob/main/extensions/connector-hermes/src/launch.ts), [`sidecar.ts`](https://github.com/Cotal-AI/Cotal/blob/main/extensions/connector-hermes/src/sidecar.ts), and [`hooks.py`](https://github.com/Cotal-AI/Cotal/blob/main/extensions/connector-hermes/plugin/cotal/hooks.py)
- **VERIFIED source:** [NATS JetStream documentation](https://docs.nats.io/nats-concepts/jetstream)
- **VERIFIED source:** [LangGraph persistence documentation](https://langchain-ai.github.io/langgraph/concepts/persistence/)
- **VERIFIED source:** [Temporal durable execution documentation](https://docs.temporal.io/workflows)

Cotal SPEC Draft v0.3 and its Hermes connector are alpha/currently NATS/JetStream bound. It supplies multicast, unicast, anycast, presence, durable delivery, identities, and grants. It does **not** define Aether’s user-contract authority, semantic task graph, independent gates, completion/reconciliation, `.aether` continuity, or work-product correctness.

| Dimension | Evidence | Consequence for Aether |
|---|---|---|
| Delivery | **VERIFIED:** live at-most-once; durable/direct/anycast at-least-once within retention | **INFERRED:** dedupe and effect reconciliation remain Aether responsibilities |
| Ordering | **VERIFIED:** no global ordering across routes/consumers | **INFERRED:** transport cannot authorize semantic ordering/state transitions |
| Addressing | **VERIFIED:** multicast/unicast/anycast | Useful transport semantics, not product authority |
| Hermes connector | **VERIFIED:** pins 0.16 line, temporary `HERMES_HOME`, approvals off, no resume, launcher owns child gateway | **BLOCKED** against v0.19 initial runtime: conflicts with persistent Aether profiles and Olympus lifecycle ownership |
| Security boundary | **VERIFIED:** identity/grants are available | **UNKNOWN:** compatibility with Aether PoP credential, revocation epoch, and tool-bound E2–E4 enforcement |

**Conclusion:** direct Cotal integration/fork is **NO-GO** for the initial v0.19 runtime. Cotal adoption/fork is not approved. It may only re-enter evaluation as transport-only after an explicit compatibility proof; it must never become semantic or lifecycle authority.

### Why inspiration rather than a literal core dependency

This conclusion distinguishes three choices that must not be conflated:

1. **Concept adoption — selected:** use Cotal's transport-agnostic principal/card/envelope/addressing/presence/channel/ACL semantics as the vocabulary and behavioral reference for Aether's native coordination protocol.
2. **Wire compatibility — deferred:** a future Python `TransportAdapter` may conform to the Cotal Wire Specification and use a NATS binding after native measurements justify interoperability or multi-host scale.
3. **Reference implementation/connector adoption — rejected initially:** do not import `@cotal-ai/core`, run Cotal Manager, or use the current Hermes connector in v0.19's first runtime.

The rejection is integration-specific, not conceptual. The reference package is TypeScript and the current binding adds NATS/JetStream operations; the Hermes connector creates a temporary profile, owns a child gateway, disables approvals, targets Hermes 0.16, and cannot resume sessions. Those properties conflict with persistent Aether profiles, the live Telegram gateway, and Olympus lifecycle authority. Even if adopted, Cotal would still not supply Aether's immutable execution contracts, semantic ledger, QA authority, effect reconciliation, or `.aether` continuity.

The selected design therefore preserves a clean future interoperability seam without paying the broker/sidecar/lifecycle cost before there is evidence that Aether needs it.

## 3. Preserved LOC evidence

**Method (historical evidence):** Cotal checkout `c378569779af1b4a0426d0b9087ff3c34349b187`; local Aether v0.18.2 source state on 2026-07-18; `pygount 3.2.0`; code lines excluding comments/blanks and generated/dependency directories.

| Scope | Production LOC | Relevant test LOC | Combined |
|---|---:|---:|---:|
| Olympus v3 | 3,449 | 1,096 | 4,545 |
| Full Cotal repository | 60,336 | not isolated | — |
| Relevant Cotal subset | 11,024 | 9,464 | 20,488 |
| Cotal core | 5,555 | 5,690 | 11,245 |
| Cotal manager + delivery | 3,096 | 2,637 | 5,733 |
| connector-core + connector-hermes | 2,373 | 1,161 | 3,534 |

**INFERRED from the preserved measurement:** the relevant subset is 3.20x Olympus production LOC; core is 1.61x; manager+delivery is roughly 90%; connector surface is roughly 69% and comparable to Olympus production size. Size is maintenance evidence, not a proof of incompatibility.

## 4. Alternatives

### Option A — Aether-native coordination control plane over Olympus

**VERIFIED fit:** preserves current Olympus session/process ownership and Aether continuity ownership. **PROPOSED implementation:** Contract Registry, immutable ledger, deterministic admission/capabilities/effects, transactional inbox/outbox, Olympus Runtime Adapter, and native dispatch. **UNKNOWN:** exact extension seams and storage/identity implementation, deferred to Phase 0.

### Option C — Direct NATS JetStream transport

**VERIFIED:** JetStream provides durable streams/consumers and delivery primitives. **INFERRED:** it could implement `TransportAdapter` for scale-out without owning semantic state. **UNKNOWN:** deployment/security/cost and required operational support. Not initial runtime.

### LangGraph persistence

**VERIFIED:** checkpoint/persistence facilities exist. **INFERRED:** they do not establish Aether-wide cross-agent authority, independent review identity, or Olympus lifecycle ownership. No adoption decision.

### Temporal

**VERIFIED:** durable workflow execution exists. **INFERRED:** its worker/workflow lifecycle model does not demonstrate fit with existing Hermes profiles and Olympus ACP sessions. No adoption decision.

## 5. Research conclusions and open proof obligations

- **APPROVED:** Option A ranks first; Option C second; Cotal transport-only third.
- **AUTHORIZED:** isolated Aether-native Phase 0 proofs and default-off implementation. **BLOCKED:** installing, forking, or connecting Cotal/NATS/JetStream and any live runtime activation.
- **UNKNOWN Phase 0 evidence:** exact installed Hermes/ACP schema and extension seams; PoP/key-management integration; authoritative store transaction/checkpoint performance; ability to enforce capability checks at real tool/effect boundaries; a Cotal connector compatibility proof if Cotal is reconsidered.
- **Not claimed:** Cotal, NATS, LangGraph, or Temporal is selected for v0.19 initial runtime.
