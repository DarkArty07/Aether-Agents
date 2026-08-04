---
name: daimon-design
description: "Use when designing Aether specialist profiles without assuming an execution runtime."
version: 2.0.0
---

# Daimon profile design

A Daimon profile defines specialist judgment, limits, evidence, and output quality. It does not prove that an invocation path exists.

## Design contract

For each profile define:

1. **Identity and scope** — one distinct specialist contribution.
2. **Authority** — decisions the profile may make and boundaries reserved for Hermes/user.
3. **Inputs** — exact context required; no ambient project inference.
4. **Deliverable** — one concrete artifact or structured consultation.
5. **Evidence** — observations, uncertainty, tests, and acceptance format.
6. **Tool policy** — smallest toolset needed for the role.
7. **Forbidden effects** — credentials, spending, publication, deployment, cross-project access, or production writes unless separately authorized.
8. **Failure behavior** — fail visibly when context, authority, or runtime is unavailable.

## Current candidate boundary

The v0.22.0 candidate preserves profile definitions but has no Aether specialist execution or curation facade. Do not add invocation commands, session actions, polling recipes, or runtime-specific database assumptions to a SOUL until an accepted execution substrate exists.

## SOUL quality

- Keep role policy concise and stable.
- Put reusable long procedures in skills, not SOUL files.
- Do not embed obsolete architecture, version history, or implementation paths.
- Require evidence rather than self-certified completion.
- Preserve Hermes as product-intent owner and final synthesizer.

## Verification

Review the profile template, enabled plugins/toolsets, cross-references, and current runtime surface. A profile is design-complete when its role contract is coherent; it is operational only after a separate real invocation test succeeds.
