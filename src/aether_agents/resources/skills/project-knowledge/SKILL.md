---
name: project-knowledge
description: Query and maintain revision-bound project knowledge.
version: 0.1.0
author: Aether contributors
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [graphify, projects, knowledge, collaboration]
    related_skills: [work-memory, canonical-skill-governance]
---

# Project Knowledge Skill

Use the shared technical graph to locate relevant sources and maintain knowledge when
those sources change. A graph is derived navigation, never proof of current behavior,
project authority, a substitute for tests, or a record of personal preferences.

## When to Use

Use when the task benefits from project-relative source navigation. This procedure
cannot grant authority or replace the project's canonical decisions.

- Orient within a project, investigate dependencies, locate implementation or documented
  decisions, or return to a project in a later session.
- Refresh knowledge after a coherent committed change to relevant code or documentation.
- Do not use for greetings, unrelated questions, or as ceremony before every file read.

## Prerequisites

- The `aether-project-knowledge` plugin and its `project_knowledge` tool are available.
- The session is bound to a registered project and the Graphify component is configured.
- The current objective permits the work; the skill grants no additional authority.
- If the capability is unavailable, continue with `search_files`, `read_file` and the
  project's ordinary verification process. Do not install dependencies or alter profiles.

## How to Run

Use `project_knowledge`. Project, role, worktree, graph destination and runtime environment
are selected by the integration, not by model arguments. All three roles have the same
operations. Consult the returned revision, coverage, warnings and freshness.

Use native file tools to inspect the relevant current sources after orientation.
A source reference in an older snapshot is a lead, not evidence that the source still
has that behavior. Do not bypass a genuine protected-edge denial through another tool.

## Quick Reference

```json
{"action":"query","question":"Where is contract validation implemented?","budget_tokens":2000}
```

```json
{"action":"explain","node":"validate_contract","budget_tokens":1500}
```

```json
{"action":"neighbors","node":"validate_contract","budget_tokens":1500}
```

```json
{"action":"community","community_id":0,"budget_tokens":2000}
```

```json
{"action":"path","source":"prepare_contract","target":"validate_contract","max_hops":6}
```

```json
{"action":"impact","node":"validate_contract","depth":2,"budget_tokens":2000}
```

```json
{"action":"update","reason":"Committed the scoped contract-validation changes","changed_paths":["src/contracts.py"],"mode":"structural"}
```

## Procedure

1. Confirm the current task and normal project guidance. Discover only relevant canonical
   procedures; do not load every project document or graph report into the prompt.
2. Ask a bounded question about the area that matters. A normal query returns its own
   revision and coverage; a separate `status` call is not mandatory each time.
3. Interpret relations carefully. Extracted, inferred and ambiguous relations are not
   interchangeable, and absence from a graph does not prove absence from the system.
4. Follow references to current source files before changing code or making a behavioral
   claim. Documentation can describe a requirement that the implementation does not meet.
5. Perform the authorized work with the role's existing responsibilities, tools, tests
   and review. Owning a tool does not widen scope or transfer another role's authority.
6. After an appropriate committed checkpoint, call `update` for the bound revision.
   Any role can do this; there is no Morfeo-only writer or new human approval for an
   ordinary in-scope update. `changed_paths` is an efficiency hint, not permission to
   omit other changed sources. The integration deduplicates and serializes publication.
7. Check `updated`, `unchanged` or failure and the revision actually covered. Dirty files
   are not indexed by this candidate. Never label a worker branch as the integrated
   result or union graphs from incompatible branches.
8. When a durable lesson is worth preserving, use the work-memory procedure. Shared
   project facts belong in the appropriate source document or verified code, not only
   in a private experience. Do not inject private notes into the shared index.

## Pitfalls

- Do not run Graphify's global install, hooks, watch, graph merge or raw path-based
  commands to bypass the integration. No global `GRAPHIFY_OUT` destination is assumed.
- Do not read or write another project's index because the intended index is missing.
- Do not edit published `graph.json` files manually. Updates derive from source files.
- Do not demand a complete reindex on every turn or hide failed/unfinished updates.
- Structural document navigation is not LLM semantic extraction. The current candidate
  reports structural-only coverage and does not enable provider calls.
- A component error is not a reason to stop otherwise authorized development. Continue
  with direct inspection and report the knowledge limitation accurately.

## Verification

Confirm that the receipt names the bound project and intended revision, with no unexpected
sources from another project. Check actual current files and relevant tests before reporting
behavior. A graph update does not certify the implementation, close a task, or satisfy an
acceptance criterion by itself. Record meaningful errors without copying private runtime
paths, credentials, personal memories or entire graph payloads into public deliverables.
