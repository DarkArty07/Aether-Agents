# Hermes Prompt 0.4.0 migration

- **Status:** implemented and verified locally
- **Date:** 2026-08-11
- **Product version:** `0.23.0.dev0` (unchanged)
- **Prompt transition:** `3.0.0-hot.3` → deliberate lean line `0.4.0`
- **Decision:** [PDR-0015](../../decisions/PDR-0015-hermes-prompt-0.4.0-autonomous-routing.md)

## Goal

Make Hermes autonomously own routine execution and orchestration choices while keeping product authority with the user. Reduce the active identity prompt to durable behavior, move volatile details to one canonical layer, reconcile contradictory live preferences, and prevent regression with executable checks.

## Information migration map

| Removed or compressed prompt topic | Canonical destination |
|---|---|
| product authority and protected effects | `docs/knowledge/AUTHORITY.md` |
| user-facing autonomy and escalation behavior | `docs/product/EXPERIENCE.md` |
| quality ordering | `docs/product/PRINCIPLES.md` |
| task completion and horizon boundaries | `docs/product/COMPLETION.md` |
| direct-versus-swarm decision | `docs/architecture/ORCHESTRATION.md` |
| lifecycle calls, identities, retry and cleanup | `docs/architecture/AETHER_MCP.md`, `docs/reference/`, tool schemas/descriptions |
| current roster and profile roles | `docs/architecture/DAIMONS.md` |
| exact tool count and installed runtime state | `docs/releases/v0.23.0/STATUS.yaml` |
| production-entry gates and next work | `docs/releases/v0.23.0/ROADMAP.md` and `PRODUCTION_OPERATING_POLICY.md` |
| memory, skills and evidence placement | `docs/knowledge/HERMES_LEARNING_MODEL.md` |
| prompt experiment/promotion mechanics | PDR-0009 as decision history plus PDR-0015/current release evidence |
| prompt version pointers and rollback archive | `home/README.md`, `home/prompts/hermes/` and this document |
| retired tools and components | repository/runtime retirement tests and historical decisions; not the identity prompt |

No redirect stubs restore `SELF_IMPROVEMENT_CYCLE.md` or `MULTI_AGENT_MODEL.md`; their superseded narratives remain intentionally absent. `docs/decisions/README.md` directs current readers to the governing architecture and knowledge documents while historical PDRs preserve why the old paths existed.

## Implementation plan

1. **Freeze baseline and rollback** — keep `home/prompts/hermes/3.0.0-hot.3/SOUL.md` untouched and identify the clean source baseline.
2. **Define expected behavior** — approve PDR-0015 and encode the seven-axis contract.
3. **Replace and archive** — make `home/SOUL.md` and `home/prompts/hermes/0.4.0/SOUL.md` byte-identical.
4. **Redirect volatile policy** — update the canonical authority, experience, orchestration, learning, configuration, and release documents instead of repeating them in the prompt.
5. **Reconcile live preferences** — remove per-step and explicit-swarm confirmation rules from machine-local `USER.md` while preserving Hermes' standard automatic skill-review, generated-skill and curator behavior.
6. **Add regression checks** — verify identity/archive parity, seven sections, size, absence of volatile runtime names, current pointers, rollback preservation, and configuration intent.
7. **Validate** — review links/diff, run focused prompt tests, then run the full repository suite because a shared behavioral contract changed.
8. **Activate later** — use a fresh Hermes session to observe the new prompt; do not restart the current runtime or claim production swarm acceptance as part of this local migration.

## Runtime gap separated from prompt policy

Prompt `0.4.0` is allowed to decide that economical orchestration is preferable. The current v0.23 runtime still cannot prove that it executed that decision because:

- the swarm manifest has no provider/account/model/cost selection fields;
- model dispatch uses a configured generic Codex worker and does not pass a model selector;
- reported `expected_model` is observational metadata, not enforced routing;
- model-worker retry and the production-entry qualification gate remain incomplete.

The next runtime change must add a typed, inspectable routing/budget contract, pass the selected model through the supported Orca boundary, capture actual model/cost evidence, and qualify one bounded case. Until then Hermes must report the limitation rather than ask the user to micromanage an unavailable selector or pretend that cost routing occurred.

## Rollback

Rollback is a local file operation: restore the byte-exact archived `3.0.0-hot.3` prompt to `home/SOUL.md`, restore its version pointers, and start a fresh Hermes session. Do not delete either archive. No open session reloads a changed prompt automatically.

## Acceptance evidence

- [x] predecessor archive preserved;
- [x] expected behavior and information destinations documented;
- [x] active and archived `0.4.0` prompt created;
- [x] current documentation and machine-local policy synchronized;
- [x] standard automatic skill-review and curator values preserved;
- [x] deterministic prompt-contract checks pass;
- [x] full repository suite passes;
- [x] final diff confirms no historical evidence was rewritten.
