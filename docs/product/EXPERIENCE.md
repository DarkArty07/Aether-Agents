# Product Experience

> **Status:** APPROVED PRODUCT BASELINE — future UI not implemented
> **Owner:** Christopher (DarkArty07)
> **Governing decisions:** `../decisions/PDR-0007-studio-experience-progressive-visibility-and-ui.md`, `../decisions/PDR-0008-canonical-definition-and-project-completion.md`
> **v0.22.0 runtime decision:** `../decisions/PDR-0011-orca-substrate-and-olympus-retirement.md`
> **Implementation authorization:** None

## Experience statement

Aether should feel like directing an intelligent software studio, not administering a collection of agents.

The user acts as product owner. They express the product they want, clarify meaningful ambiguity, choose material trade-offs, and evaluate outcomes. Aether organizes specialist intelligence, models, tools, project state, evidence, and recovery behind that interaction.

## Desired qualities

The experience should feel:

- capable without being boastful;
- autonomous without becoming opaque;
- organized without becoming bureaucratic;
- creative without changing the user's vision;
- technically deep without demanding technical expertise from the user;
- continuous across sessions;
- trustworthy because claims are connected to evidence;
- increasingly personalized through Hermes-managed user knowledge.

## Experience anti-patterns

Aether should not feel like:

- a permanent settings panel;
- a noisy swarm of agents;
- six competing personalities asking the user to coordinate them;
- a terminal that requires architectural expertise for ordinary decisions;
- a chain of confirmations for reversible internal work;
- a black box that reports completion without evidence;
- a gamified animation that confuses activity with progress.

## Core interaction model

```text
User describes desired product outcome
        ↓
Hermes understands intent and prepares contract
        ↓
Aether coordinates authorized specialists and tools
        ↓
User sees meaningful progress, risks, and decisions
        ↓
Aether presents evidence-backed result
        ↓
User accepts, redirects, or rejects product outcome
```

The user should interact primarily with Hermes. Direct specialist access may exist for focused consultation, but it must not require the user to manage the team.

## Progressive visibility

### Level 1 — Product-owner summary

Visible by default:

- what Aether is trying to deliver;
- current phase or meaningful stage;
- recent material progress;
- current blocker or risk, when present;
- decisions requiring user authority;
- next meaningful outcome;
- evidence-backed completion summary.

### Level 2 — Studio view

Available on demand:

- active Daimons and responsibilities;
- task graph and dependencies;
- current owners and handoffs;
- contract scope and exclusions;
- quality gates and findings;
- retries, blocked work, and recovery state;
- meaningful milestones and artifact lineage.

### Level 3 — Evidence and resources

Available for verification and optimization:

- tests, builds, screenshots, reviews, and receipts;
- model and provider routing;
- inference cost and latency;
- budgets, attempts, and concurrency;
- accepted limitations and waivers;
- residual risk and incomplete criteria.

### Level 4 — Deep inspection

Available to advanced users and maintainers:

- coordination ledger events;
- historical runtime sessions and lifecycle evidence, when explicitly retained;
- raw evidence references;
- contract generations and amendments;
- capability, fence, lease, and reconciliation state;
- diagnostic and failure history.

No user is required to inspect deeper levels to use Aether normally.

## Future UI direction

A dedicated UI is part of Aether's future product direction.

It should combine:

- a primary conversation with Hermes;
- a project overview;
- a product-owner decision inbox;
- an optional studio/activity view;
- evidence and quality inspection;
- resource and cost visibility;
- continuity and memory controls;
- advanced diagnostics.

The exact platform remains open. Desktop, web, TUI, or multiple clients may be considered later, but all surfaces should share the same projection contracts and authority model.

## Conceptual information architecture

### Conversation

Purpose: define and refine product intent through Hermes.

Should show:

- current approved objective;
- concise responses and recommendations;
- material decisions;
- final product synthesis.

Should not show by default:

- raw agent chatter;
- repetitive tool output;
- internal retries;
- hidden chain-of-thought.

### Project overview

Purpose: answer "What are we building, where are we, and what matters now?"

Should show:

- product vision and current contract;
- phase and milestone state;
- progress expressed through completed outcomes, not theatrical percentages;
- blockers, risks, and next meaningful result;
- current versus planned capability.

### Decision inbox

Purpose: reserve user attention for genuine product-owner authority.

Each decision should include:

- product consequence;
- Aether's recommendation;
- meaningful alternative;
- evidence or uncertainty;
- urgency and affected work.

### Studio activity

Purpose: make specialist collaboration understandable.

Should show:

- participating Daimons;
- why each was selected;
- task ownership;
- dependencies and handoffs;
- current stage and blockers;
- participant-policy status such as required, allowed, disabled, or forbidden.

The view must not turn normal interaction into agent micromanagement.

### Evidence and quality

Purpose: demonstrate why a result should be trusted.

Should show:

- acceptance criteria;
- executed tests and results;
- visual artifacts and screenshots when relevant;
- independent review findings;
- unresolved defects and limitations;
- project acceptance versus Aether benchmark validation.

### Resources

Purpose: expose model economics without making model selection the user's routine burden.

Should show:

- model tiers and task classes;
- cost, tokens, latency, and attempts;
- why an expensive model was used;
- savings from smaller models;
- rework or quality impact when relevant.

### Continuity and personalization

Purpose: let the user understand and control what Aether remembers.

Should show:

- Hermes-managed user profile;
- memory entries and provenance;
- correction, supersession, reset, export, and deletion controls;
- project-local continuity and durable decisions;
- distinction between user memory, project knowledge, and skills.

### Diagnostics

Purpose: support debugging and operational trust.

Should show authoritative runtime and ledger projections without claiming that the UI itself owns those facts.

## Authority and projection rules

The UI is not a source of truth.

| UI information | Authoritative source |
|---|---|
| Product vision and decisions | Version-controlled product docs and decision records |
| Contract, task, gate, retry, and semantic state | Version-controlled Aether policy now; future Orca operational state plus Hermes semantic acceptance after separate validation |
| Retired process and session state | Read-only historical release/runtime evidence only |
| Current project continuity | Version-controlled project documents and Hermes session context; existing `.aether` stores are protected historical/local state |
| User profile and global memory | Hermes-native memory stores |
| Source and artifact content | Repository and artifact stores |
| Test or build claims | Executed reports and receipts |
| Costs and model usage | Provider/router/runtime accounting |

The UI may issue authorized commands, but every accepted action must be recorded by the authoritative subsystem.

## Status vocabulary

The interface must distinguish:

- proposed;
- approved;
- planned;
- experimental;
- default-off;
- implemented;
- enabled;
- executing;
- blocked;
- failed;
- technically complete;
- semantically accepted;
- partially completed;
- cancelled;
- retired.

Avoid a single ambiguous "done" state.

## Long-term ambition

Aether aims to become an adaptive AI software production studio for individuals and small teams.

The target outcome is access to coordinated product, research, design, architecture, implementation, verification, security, documentation, and operational capability comparable in quality to a competent multidisciplinary software team when the project requires those disciplines.

This ambition does not remove the product owner. Human vision, material trade-offs, risk acceptance, and final acceptance remain central.

## Open questions

- Primary UI platform and deployment model.
- Relationship between chat, desktop, web, and TUI surfaces.
- Exact project overview and decision-inbox interaction patterns.
- Progress representation without false precision.
- Privacy boundaries for memory, prompts, raw evidence, and diagnostics.
- Multi-project navigation and concurrent activity.
- Notification model for decisions, stalls, milestones, and completion.
- Accessibility, localization, and responsive behavior.
- Which controls belong in product-owner mode versus advanced operator mode.
