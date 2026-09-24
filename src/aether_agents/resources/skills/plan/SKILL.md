---
name: plan
description: Author a project-local Objective Plan for Morfeo.
version: 0.1.0
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
Project. This is Morfeo's user-invoked planning procedure, not an execution tool
or a competing artifact authority. It cannot grant authority. The owner and
canonical specifications govern; Supervisor owns execution decomposition and
review, and Implementer executes bounded units.

## When to Use

- Use when an explicit planning request (such as `/plan`) or cross-session route is requested for an objective with Morfeo.
- Use for establishing a durable plan without executing code or creating cards.
- Do not use for executing implementation tasks, creating Kanban boards or cards, or certifying independent review.
- Do not add mandatory planning ceremony to simple questions or bounded direct work.

## Prerequisites

Resolve the target Aether Project and objective explicitly; do not guess or select
by recency or current working directory alone. Follow the `project-relative`
convention for all project files and resources. Discover Project Canonical Skills
under `.aether/skills/<name>/SKILL.md` and Aether Canonical Skills through native
discovery. This procedure provides reusable process and cannot grant authority.

## Procedure

1. **Resolve Project and Objective.** Confirm the bound project root and target
   objective slug explicitly. Stop and surface ambiguity if no single project or
   objective can be identified.
2. **Project-Local Plan Location.** Keep the plan at one stable
   `.aether/plans/<objective-slug>.md` inside the explicitly resolved project.
   Reuse and update the existing file across invocations for the same objective;
   never create duplicate files or global plans. Keep it ignored by version control
   by default unless publication is explicitly decided.
3. **Plan Structure.** Include only necessary operational sections:
   - **Destination:** requested outcome, scope boundaries, explicit exclusions, and
     closure criteria.
   - **Route:** sequenced milestones, necessary dependencies, and current approach.
   - **Operational continuity:** status, verified evidence, failed approaches with
     reasons, and stop or replan triggers.
4. **Anticipated Contracts.** Treat anticipated Objective Contracts as a revisable
   forecast (never a cap). Mark uncertainty honestly; new contracts are justified
   by remaining obligations, not forced by a predetermined quota.
5. **Contract Method Reference.** Defer deeper contract design, requirement
   formalization, and handoff criteria to `objective-contract-design` by reference.
6. **Stop After Planning.** Honor the planning-only boundary. End after writing or
   updating the plan file without writing implementation code, dispatching workers,
   or creating task cards.

## Pitfalls

- Writing plans to global, user home, or framework default locations instead of
  the project-local `.aether/plans/<objective-slug>.md` path.
- Treating anticipated Objective Contracts as a numerical cap or mandatory quota.
- Proceeding into code editing, task dispatch, or card creation on a planning request.
- Overwriting historical failure reasons or learning records when refreshing a plan.

## Verification

- Confirm that exactly one plan file exists at `.aether/plans/<objective-slug>.md`
  within the resolved project root.
- Confirm the plan contains destination, route, and operational continuity sections.
- Verify that no task cards, boards, or code edits were created during planning.
