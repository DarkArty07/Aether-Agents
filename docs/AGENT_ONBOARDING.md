# Agent Onboarding — Aether Agents

> **Status:** CURRENT reading contract; canonical product baseline approved
> **Audience:** Any AI agent or human contributor entering the repository

## Purpose

This document defines how to acquire enough context before changing Aether Agents. It prevents a common failure mode: understanding implementation mechanics while missing what the project is for.

## Required reading order

1. `docs/product/VISION.md`
2. `docs/product/MISSION.md`
3. `docs/product/OBJECTIVES.md`
4. `docs/product/SCOPE.md`
5. `docs/product/PRINCIPLES.md`
6. `docs/product/EXPERIENCE.md`
7. `docs/product/COMPLETION.md`
8. `docs/knowledge/README.md` and the relevant knowledge documents
9. `docs/architecture/README.md` and the relevant subsystem document
10. Active decisions and only then the relevant plan or release evidence
11. Live project continuity through supported `.aether` tools when available

The product baseline is approved. State explicitly which implementation, market, UI, migration, benchmark, or runtime questions remain open, and do not reinterpret those open details as permission to change the canonical product definition.

## Authority model

- The user acts primarily as product owner and controls vision, visible behavior, material scope, priorities, accepted compromises, consequential external effects, and final acceptance.
- The user is not expected to select routine technologies, coordinate Daimons, design test mechanics, or diagnose ordinary technical failures.
- Hermes discovers and structures requirements, translates product intent into a bounded work contract, preserves current explicit intent, curates the global user profile and memory, passes only relevant user context to Daimons, validates the delivered outcome before proposing completion, and synthesizes material escalations in product language.
- Harmonia and the coordination kernel manage bounded task state, dependencies, handoffs, evidence, recovery, and semantic closure without redefining product intent.
- Olympus and ACPManager remain the sole owners of process and ACP-session lifecycle.
- Daimons perform bounded specialist work under explicit scope, authority, and evidence requirements.
- Deterministic policy and tools enforce permissions, budgets, gates, and irreversible-effect boundaries.
- Repository documents preserve durable intent; `.aether` preserves hot operational continuity.
- Source and tests prove current mechanical behavior. Release evidence proves only the scope and gates it names.
- Communicate through progressive visibility: product outcome, meaningful progress, decisions, blockers, risks, and evidence by default; operational detail on demand.
- Do not expose routine agent chatter or hide material uncertainty. Do not treat a future UI, dashboard card, or chat message as authority over its underlying source.

The approved target authority matrix is `docs/knowledge/AUTHORITY.md`. The approved experience contract is `docs/product/EXPERIENCE.md`. Do not assume the current runtime fully enforces either target model.

## Current versus target

Always label claims as one of:

- **Current verified behavior** — demonstrably exists now.
- **Approved target** — intended but not necessarily implemented.
- **Proposal** — not approved.
- **Historical experiment** — retained evidence, not active authority.
- **Unknown** — requires investigation or owner clarification.

Never collapse these categories.

## Before making changes

1. Confirm the absolute project root.
2. Inspect the current Git state and identify concurrent work.
3. Read project continuity when relevant.
4. Identify the canonical product, architecture, and decision documents for the task.
5. State the exact deliverable, exclusions, and acceptance evidence.
6. Avoid files owned by concurrent work unless coordination is explicit.
7. Verify the real artifact or observable result before claiming completion.

## What not to infer

Do not infer that:

- the newest release experiment defines the product vision;
- an available tool grants authority to use it;
- a Daimon's mythology defines its production permissions;
- a completed session, passing test suite, commit, or terminal workflow proves the user obtained or accepted the intended product;
- a plan is approved or authorized merely because it exists;
- target architecture is active runtime behavior;
- `.aether/CONTEXT.md` replaces version-controlled design documentation.

## Minimum handoff

A useful handoff states:

- intended user outcome and product purpose;
- exact scope and exclusions;
- current verified state;
- approved target state;
- decisions and assumptions;
- files changed;
- evidence actually executed;
- blockers and the next gate.
