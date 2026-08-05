# Product Vision

> **Status:** APPROVED PRODUCT BASELINE — discovery complete
> **Owner:** Christopher (DarkArty07)
> **Governing decisions:** `../decisions/PDR-0002-generic-adaptive-software-product.md`, `../decisions/PDR-0003-quality-doctrine-and-model-economics.md`, `../decisions/PDR-0004-product-owner-authority-and-bounded-autonomy.md`, `../decisions/PDR-0005-multi-agent-participation-and-coordination.md`, `../decisions/PDR-0006-hermes-native-user-memory-without-honcho.md`, `../decisions/PDR-0007-studio-experience-progressive-visibility-and-ui.md`, `../decisions/PDR-0008-canonical-definition-and-project-completion.md`
> **v0.22.0 runtime decision:** `../decisions/PDR-0011-orca-substrate-and-olympus-retirement.md`
> **Implementation authorization:** None

## Canonical definition

Aether Agents is an adaptive AI software production studio built on specialized artificial intelligence and Hermes Agent. It is the empirical convergence of experience with the strengths and recurring failures of LLMs.

Aether allows a person to act primarily as product owner and turn their vision into complete, high-quality software through appropriate specialists, tools, memory, continuity, coordination, and evidence without requiring that person to manage the internal technical complexity.

Its multi-agent architecture is a means rather than the product. Aether's value must be demonstrated by producing, under equivalent requests and conditions, software whose overall quality equals or exceeds strong general-purpose coding agents while imposing less manual coordination on the user.

## Desired future

A software builder can act primarily as a product owner and turn an idea and personal vision into a complete, high-quality software project without having to provide every discipline personally, possess advanced technical knowledge, or coordinate every specialist step by hand.

Aether begins with a reusable foundation, then accumulates user-specific value by learning preferences, standards, recurring decisions, working patterns, and useful procedures. The user remains the source of project direction; adaptation and technical autonomy exist to serve that direction rather than redefine it.

## Product promise

Aether should turn a software idea into a project of higher quality than a strong general-purpose coding agent by combining only the specialist intelligence necessary and adapting to the user's standards.

Higher quality begins with producing the project that was actually requested. Aether must not treat extra features, additional abstraction, redesign, or expanded scope as improvements unless they are necessary and authorized.

## Enduring problem

General-purpose coding agents are powerful but repeatedly fail in ways that damage project outcomes. They can add things the user did not request, introduce logical or architectural defects, generate generic product and frontend experiences, lose context, drift from the user's vision, provide uneven specialist depth, skip necessary evidence, and require the user to perform excessive coordination.

A multi-agent system introduces its own risk: specialists can slow work, fragment intent, overcomplicate security or architecture, and create more process than value. Aether must solve both problems rather than merely replacing one with the other.

These problems remain worth solving even when models, providers, protocols, agent frameworks, or individual Daimons change.

## Intended impact

Aether should give software builders access to the right kinds of intelligence, continuity, tools, procedures, creativity, and verification at the right time while preserving ownership of the original vision.

Projects should be technically correct, product-coherent, creatively designed where appropriate, resumable across sessions, proportionally tested and secured, and supported by current documentation.

Its success is not measured by how many agents run. It is measured by whether, from the same project prompt, Aether produces software projects whose quality equals or exceeds the work of strong general-purpose coding agents.

## Quality doctrine

Aether's quality hierarchy is:

1. Do not do things the user did not request.
2. Minimize logical, architectural, integration, and syntactic errors.
3. Produce a coherent and creative product, especially where frontend and UX quality matter.
4. Preserve project order and continuity across agents and sessions.
5. Execute tests and verification when necessary and proportional to risk.
6. Apply security expertise proportionally rather than adding universal complexity.
7. Keep product and technical documentation current.

A lower quality dimension cannot compensate for violating a higher one. A polished implementation still fails when it solves the wrong problem.

## Differentiating belief

Effective AI project-production systems should be shaped by observed model limitations, accumulated user knowledge, and proven working practices rather than by multi-agent novelty.

Specialists, memories, MCP integrations, skills, and coordination mechanisms are valuable only when they correct a known failure, materially improve project quality, or reduce the burden required to obtain that improvement.

A generic product should not remain generic in its behavior forever. It should learn the individual user without losing a coherent common foundation.

Model capability should be spent according to cognitive difficulty. Expensive models create the most value in orchestration, design, architecture, complex reasoning, and consequential tasks; capable smaller models can perform much routine coding and mechanical work efficiently when held to the same evidence gates.

Multi-agent architecture is a means. Preserved intent, adaptive assistance, software-project quality, and useful autonomy are the ends.

## Multi-agent doctrine

Aether centralizes product vision but decentralizes routine coordination.

The product owner may classify any Daimon as required, allowed, disabled, or forbidden. Aether must respect that policy across direct selection, peer proposals, fallback routing, and recovery. The current suspension of Athena is the empirical precedent for this general rule.

Hermes remains responsible for understanding intent, preparing the contract, product synthesis, material amendments, and escalation. It should not relay every routine message or handoff.

Authorized Daimons may eventually collaborate laterally within an approved contract. A future accepted coordination substrate may own task state, dependencies, evidence, budgets, and recovery without acquiring product authority. The v0.22.0 candidate intentionally has no such execution runtime.

Specialist disagreements are resolved through current user intent, approved decisions, contract, artifacts, reproducible evidence, quality doctrine, and domain authority—not majority vote.

The v0.19.0 design was aligned with this target, but its release closeout did not prove replacement of the live Hermes hub-and-spoke path. The later v0.19.x migration closed at v0.19.5 with a `VIABLE — BOUNDED` verdict for its fixed historical topology. PDR-0011 subsequently retired that runtime from the v0.22.0 candidate; broader topology and replacement execution remain unimplemented.

## Learning and user-model doctrine

Aether reuses Hermes Agent as its canonical learning framework. Native `USER.md`, `MEMORY.md`, automatic background review, `skill_manage`, `/learn`, session search, and Curator provide the foundation; Aether must not create a parallel general memory or skill system without a verified need.

Hermes is the custodian of the global user model. As the primary agent, it detects preferences and recurring corrections, distinguishes durable patterns from one-off instructions, organizes and corrects memory, and passes relevant context to Daimons.

Honcho is excluded from the target product. Aether should operate without an external semantic memory service and without depending on Honcho for installation, personalization, continuity, or authority.

Daimons may contribute observations, but they do not independently own the user profile. Current project-specific knowledge remains in version-controlled project documentation; existing `.aether` stores are protected historical/local state. User preferences remain in Hermes-managed profile and memory; reusable procedures remain in skills.

## Product experience and ambition

Aether should feel like directing an intelligent software studio rather than administering a set of agents. The user remains focused on product vision, priorities, meaningful decisions, and outcomes while Aether organizes specialists, models, tools, evidence, and continuity.

Visibility is progressive. The default experience shows the approved outcome, current stage, meaningful progress, decisions, blockers, risks, and evidence-backed results. Detailed Daimon activity, tasks, handoffs, model usage, costs, tests, findings, and ledger history remain available on demand.

A dedicated future UI is part of the approved product direction. It should combine conversation with Hermes, project overview, decision inbox, studio activity, evidence, resource visibility, continuity controls, and deep diagnostics. The UI is a projection of authoritative state, never an independent source of truth.

Aether's long-term ambition is to become an adaptive AI software production studio that enables individuals and small teams to produce software with quality approaching a competent multidisciplinary team while preserving human product ownership.

## Completion doctrine

A project is complete when the user obtained the software result they intended and accepts it as satisfying the approved product outcome.

Hermes is accountable for discovering, clarifying, structuring, preserving, and validating that intended outcome. Technical completion, tests, documentation, and agent terminal states support the completion claim but do not replace user-outcome acceptance.

Aether must never rewrite the goal after the fact to match what it happened to produce. Material changes to requirements must be visible, attributable, and reflected in the active contract.

## Product validation thesis

Aether's added complexity is justified only if controlled evaluation demonstrates its value.

Under the same representative software-project prompt and equivalent starting conditions, Aether should produce projects of equal or higher overall quality than strong general-agent baselines such as Claude Code, Codex, OpenCode, `hermes-agent`, or their contemporary equivalents.

Project-specific tests prove whether one project satisfies its requirements. Comparative same-prompt evaluation proves whether Aether's product approach is better than a simpler general-agent alternative.

Evaluation must include scope fidelity, technical defects, product and frontend quality, continuity, verification, proportional security, documentation, cost, latency, and rework. The benchmark corpus, evaluator design, and acceptable thresholds remain open.

## Non-vision

Aether does not seek to become:

- a generic coding assistant that never learns the user;
- a clone of another coding agent differentiated only by configuration;
- a system that equates extra unrequested work with helpfulness;
- a demonstration whose value is merely the number of agents involved;
- an autonomous bureaucracy that makes simple work slower;
- a system that lets specialists silently replace the user's vision;
- a universal producer of unrelated non-software projects;
- a system that applies maximum security, testing, or documentation ceremony to every task;
- a system that spends the largest model on every operation regardless of difficulty;
- a collection of memories, MCP servers, skills, or Daimons without demonstrated product value.

## Evidence and open questions

| Claim or question | Basis | Status |
|---|---|---|
| Aether is the empirical convergence of experience with LLM limitations | Explicit owner approval, Phase 1 | APPROVED |
| It exists to turn ideas and vision into high-quality projects | Explicit owner approval, Phase 1 | APPROVED |
| It must not become a generic assistant, multi-agent showcase, or autonomous bureaucracy | Explicit owner approval, Phase 1 | APPROVED |
| Aether is a generic product that adapts to each user | Explicit owner approval, Phase 2 | APPROVED |
| The current product domain is software | Explicit owner approval, Phase 2 | APPROVED |
| New software-specialist Daimons may be created when justified | Explicit owner approval, Phase 2 | APPROVED |
| Product value requires same-prompt quality parity or superiority against strong general agents | Explicit owner approval, Phase 2 | APPROVED |
| Unrequested work is the highest-priority quality defect | Explicit owner approval, Phase 3 | APPROVED |
| The seven-part quality hierarchy | Explicit owner approval, Phase 3 | APPROVED |
| Model capability should be allocated by cognitive difficulty and consequence | Explicit owner approval, Phase 3 | APPROVED |
| A project is complete when the user obtains and accepts the intended outcome | Explicit owner approval, Phase 8 | APPROVED |
| Hermes owns requirements discovery, preservation, and final outcome validation | Explicit owner approval, Phase 8 | APPROVED |
| Aether may trade speed, model expense, Daimon count, secondary scope, ceremony, and nonessential polish | Explicit owner approval, Phase 8 | APPROVED |
| Aether must preserve intent, honesty, essential correctness, user authority, material safety, data protection, evidence, known-deviation disclosure, and continuity | Explicit owner approval, Phase 8 | APPROVED |
| Detailed comparative benchmark design and thresholds | Later evaluation design | OPEN |
| User acts as product owner and is not required to provide advanced technical decisions | Explicit owner approval, Phase 4 | APPROVED |
| Material product decisions remain human while routine technical execution is autonomous | Explicit owner approval, Phase 4 | APPROVED |
| Escalation is required only for product-material ambiguity, consequential effects, or inability to meet the contract | Explicit owner approval, Phase 4 | APPROVED |
| Exact autonomy profiles and deterministic enforcement boundaries | Later operating-model design | OPEN |
| Product owner may require, allow, disable, or forbid any Daimon | Explicit owner approval, Phase 5 | APPROVED |
| Hermes centralizes intent but must not relay every routine specialist interaction | Explicit owner approval, Phase 5 | APPROVED |
| Authorized Daimons may coordinate laterally inside an approved contract | Explicit owner approval and v0.19.0 alignment analysis, Phase 5 | APPROVED TARGET |
| Daimon disagreements resolve through authority and evidence rather than voting | Explicit owner approval, Phase 5 | APPROVED |
| v0.19.0 replaced the live hub-and-spoke path | v0.19.0 release closeout | NOT DEMONSTRATED |
| Bounded no-relay coordination in the historical v0.19.5 topology | v0.19.5 Gate C and roadmap closeout | HISTORICAL — VALIDATED, THEN RETIRED BY PDR-0011 |
| Global participant-policy enforcement, broader topology, and production activation | Later design, implementation, and validation | OPEN |
| Hermes Agent native learning is Aether's canonical learning framework | Explicit owner approval and installed-source verification, Phase 6 | APPROVED |
| Honcho is excluded from Aether's target product | Explicit owner approval, Phase 6 | APPROVED |
| Hermes owns global user-profile and memory curation | Explicit owner approval, Phase 6 | APPROVED |
| Tracked configuration and setup require an external semantic-memory service | v0.22.0 post-retirement cleanup | NO — RETIREMENT COMPLETE |
| Shared-skill write enforcement and optional private user skills | Later operating-model design | OPEN |
| Aether should feel like directing an intelligent software studio | Explicit owner approval, Phase 7 | APPROVED |
| Visibility should be progressive rather than raw or opaque | Explicit owner approval, Phase 7 | APPROVED |
| A dedicated UI is part of the future product direction | Explicit owner approval, Phase 7 | APPROVED TARGET |
| The UI projects authoritative state and does not own competing truth | Explicit owner approval, Phase 7 | APPROVED |
| Long-term ambition is multidisciplinary software-production quality for individuals and small teams | Explicit owner approval, Phase 7 | APPROVED |
