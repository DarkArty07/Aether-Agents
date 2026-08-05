# Shared Project Knowledge

> **Status:** STRUCTURE CURRENT; content expansion pending

This area contains stable, reusable knowledge needed by humans and agents to reason correctly about Aether Agents. It is descriptive and evidence-based; product intent remains canonical in `docs/product/`.

## Planned knowledge set

| Document | Purpose |
|---|---|
| `PROJECT_MODEL.md` | Concise mental model of the whole system |
| `GLOSSARY.md` | Canonical and historical terms: Hermes, Daimon, `.aether`, retired runtimes, and related concepts |
| `CURRENT_SYSTEM.md` | Verified capabilities and limitations of the active runtime |
| `TARGET_SYSTEM.md` | Approved future state, clearly separated from current behavior |
| `CONSTRAINTS.md` | Stable technical, operational, authorization, and compatibility constraints |
| [AUTHORITY.md](./AUTHORITY.md) | Approved target model for product-owner authority, technical autonomy, delegation, and escalation boundaries |
| [MULTI_AGENT_MODEL.md](./MULTI_AGENT_MODEL.md) | Historical v0.19 model for Daimon participation and retired lateral-coordination experiments; PDR-0012 governs the Hermes-led Orca replacement |
| [HERMES_LEARNING_MODEL.md](./HERMES_LEARNING_MODEL.md) | Verified current Hermes learning mechanics plus approved governance: Hermes owns user memory, native learning is canonical, and Honcho is retired |
| [SELF_IMPROVEMENT_CYCLE.md](./SELF_IMPROVEMENT_CYCLE.md) | Current policy and historical cycle evidence; v0.22.0 has no ledger, causality, promotion, hook, or executable bootstrap implementation |
| `KNOWN_LIMITATIONS.md` | Confirmed limitations and where they are tracked |

## Knowledge rules

1. Cite code, tests, configuration, decisions, or executed evidence for mechanical claims.
2. Label current, target, proposed, historical, and unknown states.
3. Do not duplicate release narratives; link to evidence.
4. Do not store transient session progress here.
5. Do not store secrets or user-specific runtime state.
6. Update knowledge when a release changes a stable public contract.
