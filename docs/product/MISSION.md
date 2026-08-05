# Product Mission

> **Status:** APPROVED PRODUCT BASELINE — discovery complete
> **Owner:** Christopher (DarkArty07)
> **Governing decisions:** `../decisions/PDR-0002-generic-adaptive-software-product.md`, `../decisions/PDR-0003-quality-doctrine-and-model-economics.md`, `../decisions/PDR-0004-product-owner-authority-and-bounded-autonomy.md`, `../decisions/PDR-0005-multi-agent-participation-and-coordination.md`, `../decisions/PDR-0006-hermes-native-user-memory-without-honcho.md`, `../decisions/PDR-0007-studio-experience-progressive-visibility-and-ui.md`, `../decisions/PDR-0008-canonical-definition-and-project-completion.md`
> **v0.22.0 runtime decision:** `../decisions/PDR-0011-orca-substrate-and-olympus-retirement.md`
> **Implementation authorization:** None

## Mission statement

Aether Agents helps software builders turn ideas and vision into complete, high-quality software projects by combining specialized artificial intelligence, persistent context, adaptive user knowledge, purpose-built tools, reusable procedures, coordinated execution, and proportional verification.

Its promise is to produce a better project than a strong general-purpose coding agent from the same request, without doing work the user did not ask for and without requiring the user to manually manage every specialist.

## Primary users

Aether is intended to become a product that other software builders can use.

The user acts primarily as a product owner: they define the product, desired behavior, priorities, and acceptable trade-offs. Aether must not require advanced technical knowledge in order to obtain a high-quality software project.

It provides a coherent generic foundation, then learns each user's preferences, standards, recurring decisions, and useful working procedures. Personalization is part of the product behavior; the product itself is not restricted to the owner's private configuration.

The exact market segment, experience level, onboarding model, and distribution strategy remain open.

## User problem

A person producing software must normally provide or coordinate many forms of expertise: product judgment, research, design, architecture, implementation, verification, security, documentation, and continuity.

A single general-purpose coding agent can help, but it may add unrequested work, lose context, drift from the intended vision, generate generic frontend experiences, introduce logical or architectural defects, lack sufficient specialist depth, or report completion without adequate evidence.

A poorly governed multi-agent system can be equally harmful by adding bureaucracy, conflicting recommendations, security overengineering, and excessive cost.

## Core value proposition

Aether brings the right software specialist, memory, tool, procedure, and model capability into a project when that contribution materially improves the result. The product owner may require, allow, disable, or forbid individual Daimons. Aether should respect that policy while coordinating authorized specialists laterally, without forcing the user to manage every agent, handoff, or internal state transition.

As Aether learns the user, it should become more aligned with that person's standards and workflow while preserving a stable common product foundation and giving current explicit instructions precedence over historical preferences.

The value is not that multiple agents exist. The value is that a software builder gains broader, better-coordinated intellectual capacity and produces better projects while retaining direction.

## Requirements and completion commitment

Hermes is responsible for discovering, clarifying, structuring, preserving, and validating what the user wants. It must translate product-owner language into a bounded contract without asking the user to solve routine technical mechanics.

A project is complete when the user obtained the intended software outcome and accepts it as satisfying the approved product result. Tests, documentation, commits, agent sessions, and workflow terminality support that judgment but do not replace it.

Aether must not silently rewrite requirements to match what it produced. Material requirement changes and material completion deviations require visible product-owner authority.

## Experience commitment

Aether should feel like an intelligent software studio directed through Hermes, not a collection of agents the user must manage.

The default interaction should show the product objective, meaningful progress, decisions, blockers, risks, and evidence-backed outcomes. Internal Daimon activity, task graphs, handoffs, models, costs, tests, findings, and ledger detail should be progressively available rather than forced into the main conversation.

A dedicated UI is an approved future product direction. Its purpose is to make product state and evidence understandable, not to become a second coordination authority.

## Quality commitment

Aether must prioritize:

1. exact fidelity to the requested scope;
2. minimal logical, architectural, integration, and syntax defects;
3. creative and coherent product, frontend, and UX quality;
4. durable project order and continuity;
5. necessary and proportional tests;
6. security proportional to actual risk;
7. current, authoritative documentation.

The product should reserve expensive models for orchestration, design, architecture, complex reasoning, and consequential work. Capable smaller models should perform routine coding and mechanical tasks when they can satisfy the same quality and evidence requirements.

## Current product category

Aether is an **adaptive AI software production studio**.

This category describes its purpose without reducing it to a code assistant, inflating it into a universal autonomous organization, or treating its multi-agent architecture as the product itself.

## Relationship to `hermes-agent`

Aether uses `hermes-agent` as its underlying agent framework so that it does not reinvent general capabilities such as model access, tools, sessions, memory, skills, scheduling, and gateways.

`hermes-agent` is enabling infrastructure. Aether's product identity lies in the integrated specialist system, empirical operating practices, adaptive user knowledge, project continuity, coordination, verification, quality doctrine, and preservation of user vision built on top of that infrastructure.

Hermes' native `USER.md`, `MEMORY.md`, automatic review, `skill_manage`, `/learn`, session search, and Curator are the canonical learning stack. Hermes is responsible for detecting, organizing, correcting, and selectively sharing the user's durable preferences and profile.

Honcho is not part of the approved target product. The v0.22.0 candidate uses Hermes-native memory and has removed the tracked Honcho provider, installation, and operational surfaces.

## Mission boundaries

The mission does not require Aether to:

- replace the user as the source of product vision;
- perform work that was not requested;
- invoke multiple Daimons for every task;
- invoke a Daimon that user or project policy marks disabled or forbidden;
- route every routine Daimon interaction through Hermes;
- apply maximum security review or maximum test ceremony universally;
- use the most expensive model for every operation;
- build every foundational agent capability itself;
- build a parallel general memory, skill, or curation framework that duplicates Hermes Agent;
- depend on Honcho for normal operation, personalization, or continuity;
- allow Daimons to maintain conflicting global user profiles;
- maximize agent activity, delegation count, or architectural complexity;
- produce general non-software projects;
- accept a capability merely because it is technically possible;
- claim product value without comparison against strong general-agent alternatives.

## Open implementation and product-design questions

- Exact target segments and onboarding experience.
- Primary UI platform and relationship among chat, desktop, web, and TUI surfaces.
- Product overview, decision inbox, studio activity, evidence, resource, continuity, and diagnostic information architecture.
- Detailed benchmark corpus, evaluators, thresholds, cost, and latency limits.
- Optional autonomy profiles for users who want more or less technical control.
- Exact UI and policy for reviewing, correcting, exporting, resetting, and deleting Hermes-managed user memory.
- Shared-skill write ownership and whether private per-user skills are needed.
- Exact ownership model for documentation and continuity.
- Exact escalation budgets and bounded-attempt limits.
- Runtime enforcement of required, allowed, disabled, and forbidden Daimon policy.
- Production migration, activation, and broader participant-policy enforcement beyond the validated bounded v0.19.5 no-relay topology.
