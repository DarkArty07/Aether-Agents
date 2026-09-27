---
name: aether-plan
description: Author a project-local Objective Plan for Morfeo.
version: 0.2.0
author: Morfeo (Aether role), Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [planning, objective, morfeo]
    related_skills: []
---

# Project-Local Objective Plan

Author and maintain a bounded, durable Objective Plan inside the active Aether
Project. This is Morfeo's explicit planning entry, `/aether-plan`, not an execution
tool or a competing artifact authority. It cannot grant authority. The owner and
canonical specifications govern; Supervisor owns execution decomposition and
review, and Implementer executes bounded units. Generic `/plan` is not an alias.

The installed directory remains `skills/plan/` as a backward-compatible distribution
key. Its public name is `aether-plan`; use native name-based discovery, not the storage
key, to select this procedure. This does not rename project plan files.

## When to Use

- Use when an explicit planning request (such as `/aether-plan`) or cross-session route is requested for an objective with Morfeo.
- Use for establishing a durable plan without executing code or creating cards.
- Do not use for executing implementation tasks, creating Kanban boards or cards, or certifying independent review.
- Do not add mandatory planning ceremony to simple questions or bounded direct work.

## Prerequisites

Resolve the target Aether Project and objective explicitly; do not guess or select
by recency or current working directory alone. Follow the `project-relative`
operating map in root `AGENTS.md`. Discover Project Canonical Skills under
`.aether/skills/<name>/SKILL.md` and Aether Canonical Skills through native discovery.
This procedure provides reusable process and cannot grant authority.

## Procedure

1. **Resolve Project and Objective.** Confirm the bound project root and target
   objective slug explicitly. Stop and surface ambiguity if no single project or
   objective can be identified. Do not initialize a project merely to store a plan.
2. **Recover Relevant Context.** Read an existing plan and pertinent
   `.aether/observations/<topic>.md` notes when present. Preserve attribution and
   separate approved scope from hypotheses, proposals and unresolved decisions.
   Do not create an observation as a prerequisite or turn exploration into approval.
3. **Project-Local Plan Location.** Keep the plan at one stable
   `.aether/plans/<objective-slug>.md` inside the explicitly resolved project.
   Reuse and update it across invocations for the same objective; never create
   duplicate files or global plans. Keep it ignored by version control by default
   unless publication is explicitly decided. This is not the technical
   `specs/<feature>/plan.md`, which stays with the product's specification artifacts.
4. **Plan Structure.** Include only necessary operational sections:
   - **Destination:** requested outcome, scope boundaries, explicit exclusions, and
     closure criteria, referring to the canonical owners of accepted obligations.
   - **Route:** useful milestones, necessary dependencies, and current approach.
   - **Operational continuity:** status, attributed verified evidence, failed
     approaches with reasons, and stop or replan triggers.
   Reference existing research and decisions instead of copying them into a second
   authoritative document. Refresh changeable facts without erasing prior failures.
5. **Anticipated Contracts.** Treat anticipated Objective Contracts as a revisable
   forecast (never a cap). Mark uncertainty honestly; new contracts are justified
   by remaining obligations, not forced by a predetermined quota.
6. **Shared Method Reference.** Use `objective-contract-design` for project adoption,
   exploratory observations, substantive planning and contract extraction. Authorized
   work can maintain continuity without an explicit slash command; this entry does
   not create a second planning method.
7. **Stop After Planning.** End after writing or updating the plan file, without
   writing implementation code, dispatching workers, creating contracts or task cards,
   or treating a plan as publication authority.

## Pitfalls

- Selecting a generic learned `plan` skill instead of the Aether-owned `aether-plan`.
- Writing plans to global, user home, or framework default locations.
- Treating anticipated contracts as a cap or an observation as approved scope.
- Turning every exploration into a plan, or executing merely because a plan exists.
- Overwriting historical failure reasons or duplicating specification decisions.

## Verification

- Confirm that the same objective uses one stable plan within the resolved project.
- Confirm destination, route and operational continuity are sufficient, not empty ceremony.
- Confirm references separate accepted obligations from exploratory context.
- Confirm the planning request produced no implementation, contracts, cards or workers.
