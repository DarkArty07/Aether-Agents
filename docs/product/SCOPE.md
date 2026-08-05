# Product Scope

> **Status:** APPROVED PRODUCT BASELINE — discovery complete
> **Owner:** Christopher (DarkArty07)
> **Governing decisions:** `../decisions/PDR-0002-generic-adaptive-software-product.md`, `../decisions/PDR-0003-quality-doctrine-and-model-economics.md`, `../decisions/PDR-0004-product-owner-authority-and-bounded-autonomy.md`, `../decisions/PDR-0005-multi-agent-participation-and-coordination.md`, `../decisions/PDR-0006-hermes-native-user-memory-without-honcho.md`, `../decisions/PDR-0007-studio-experience-progressive-visibility-and-ui.md`, `../decisions/PDR-0008-canonical-definition-and-project-completion.md`
> **v0.22.0 runtime decision:** `../decisions/PDR-0011-orca-substrate-and-olympus-retirement.md`
> **Implementation authorization:** None

## Scope model

Every major capability should be placed in exactly one primary category. Product scope is determined by contribution to Aether's purpose, not by technical possibility or by whether an implementation already exists.

## Core product

The approved core identity includes:

- a generic product for producing software projects;
- adaptation to each user's preferences, standards, recurring decisions, and useful procedures;
- transformation of user ideas and vision into high-quality software outcomes;
- specialized artificial intelligence used where it contributes material value;
- memories, tools, procedures, and coordination mechanisms that compensate for observed LLM limitations;
- preservation of user vision while expanding the intellectual capacity available to execute it;
- reduction of manual coordination burden;
- Hermes-led requirements discovery, preservation, and outcome validation;
- project completion defined by the user obtaining and accepting the intended result;
- project-appropriate testing and evidence;
- comparative validation against strong general-purpose coding agents.

The detailed project lifecycle and formal benchmark implementation remain open design questions. The semantic completion contract is approved in `COMPLETION.md`.

## Supported project domain

Aether produces software projects. This includes, without making the list exhaustive:

- applications and user-facing software products;
- services and APIs;
- developer tools and automation;
- AI systems and model-related software;
- infrastructure and operational software;
- libraries and frameworks;
- technical experiments and prototypes intended to inform software production.

Research, product design, UX, architecture, testing, security, documentation, deployment planning, and operations are in scope when they contribute to a software project.

## Daimon expansion

The Daimon team is not permanently limited to its current members. New Daimons may be designed for additional software disciplines when their specialization is expected to improve project quality materially.

A new Daimon is not justified by mythology, novelty, or role naming alone. Its contribution must be distinct, reusable, and valuable enough to exceed the coordination cost it introduces.

## Daimon participation policy

The product owner may classify each Daimon as `required`, `allowed`, `disabled`, or `forbidden` in the applicable global, project, run, or task scope.

This policy applies to direct selection, peer proposals, automatic routing, fallback, retry, recovery, and equivalent-role substitution. Aether may recommend consequences and alternatives, but cannot silently override current user policy.

Authorized Daimons may collaborate laterally inside an approved contract. Lateral coordination is in scope only when it preserves participant policy, role authority, task boundaries, evidence requirements, budgets, and durable traceability.

## Adaptive user knowledge

Aether learns from the user through Hermes Agent's native mechanisms.

Approved placement:

- `USER.md` for user identity, preferences, and recurring corrections;
- `MEMORY.md` for stable environment facts and durable conventions;
- Hermes skills for reusable procedures;
- version-controlled project documents for vision, scope, requirements, architecture, and durable decisions;
- `.aether` for hot project continuity;
- session history for historical conversation recall.

Hermes is the global user-profile custodian. Daimons may report observations, but they do not own independent global profiles.

Honcho is outside the target product. The v0.22.0 candidate has removed its provider configuration, submodule, container stack, setup commands, and active operational documentation while retaining historical decisions and release evidence.

The exact review, correction, export, reset, deletion, shared-skill ownership, and optional private-skill experience remain later design decisions.

## Product experience and future UI

The approved product experience is an intelligent software studio directed by a product owner through Hermes.

Progressive visibility is core product behavior:

- product outcome, current stage, meaningful progress, decisions, blockers, risks, and evidence summary by default;
- Daimons, task graph, dependencies, handoffs, models, costs, tests, findings, and ledger detail on demand.

A dedicated UI is in future scope. Its exact platform is undecided, but it should support conversation, project overview, decision inbox, studio activity, evidence and quality, resource use, continuity and memory controls, and deep diagnostics.

The UI is a projection and command surface over authoritative subsystems. Maintaining independent semantic task, runtime, evidence, memory, or completion truth inside the UI is outside scope.

## Configurable variation

Models, providers, specialist assignments, toolsets, thresholds, and workflows may vary without changing Aether's identity, provided the variation preserves product purpose, quality standards, and authority boundaries.

## Optional modules and integrations

An integration is optional when Aether remains recognizably useful without it. Memories, MCP servers, skills, external services, and specialist modules must not be classified as core merely because they are available.

Their classification must be justified by the observed failure they address and the measurable value they provide.

## Experimental

Historical release documents contain the retired default-off kernel and Harmonia migration. That evidence remains preserved, but the v0.22.0 candidate has no active multi-agent execution runtime.

An experiment does not redefine the product merely because it is newer or technically ambitious.

## Future

The following remain future or unresolved rather than silently assumed:

- exact target user segments;
- primary UI platform and relationship among chat, desktop, web, and TUI surfaces;
- project overview, decision inbox, studio activity, evidence, resource, continuity, and diagnostic interaction design;
- progress representation without false precision;
- privacy and access boundaries for memory, prompts, evidence, and diagnostics;
- user-facing review, correction, export, reset, and deletion of Hermes-managed memory;
- shared-skill write ownership and optional private per-user skills;
- the comparative benchmark corpus and evaluators;
- runtime enforcement of participant policy and lateral authority;
- production migration, activation, and broader participant-policy enforcement beyond the validated bounded v0.19.5 no-relay topology;
- which additional software-specialist Daimons become justified by evidence.

## Out of scope

The following identities and behaviors are explicitly outside the approved product direction:

- general production of unrelated non-software projects;
- a generic coding assistant that never adapts to its user;
- Honcho or another required external semantic memory service as part of normal operation;
- a parallel Aether-native general memory engine, skill format, or skill curator that duplicates Hermes Agent;
- independent conflicting global user profiles owned by individual Daimons;
- shared skills that hard-code one user's preferences as universal rules;
- a clone of another coding agent differentiated only by configuration;
- a multi-agent showcase whose primary value is the number of agents;
- a default experience that exposes every peer message, tool call, retry, or internal transition;
- a black-box experience that hides material risks, blockers, and unsupported completion claims;
- a UI that maintains independent product, coordination, runtime, memory, evidence, or completion truth;
- agent theater, animation, or gamification presented as evidence of progress;
- mandatory participation of many specialists in every task;
- invocation of a Daimon that current user or project policy marks disabled or forbidden;
- routing every routine specialist handoff through Hermes;
- autonomous bureaucracy that slows development or increases supervision;
- silent replacement of user vision by specialist interpretation;
- silent requirement changes or retrospective rewriting of the goal to match the produced artifact;
- declaring agent, session, test, commit, or workflow terminality as user-outcome completion;
- accumulation of tools, memories, integrations, skills, or Daimons without demonstrated product value;
- treating generated code, agent activity, or internal test counts as sufficient proof of product superiority.

## Authorization boundaries

Documentation, research, and design do not automatically authorize:

- production code changes;
- creation or activation of new Daimons;
- live agent sessions or runtime activation;
- collection or migration of user data;
- credentials or provider changes;
- deployment or publication;
- external spending;
- irreversible migration or deletion.
