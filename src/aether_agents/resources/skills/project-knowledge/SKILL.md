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
operations. The project tool exposes fourteen actions
(`status`, `query`, `explain`, `neighbors`, `community`, `path`, `impact`, `update`,
`stats`, `god_nodes`, `list_prs`, `pr_impact`, `triage_prs`, `visualize`). Work-memory
has five unchanged actions (`save`, `search`, `read`, `correct`, `reflect`). Consult the
returned revision, coverage, warnings and freshness.

Tool parameters use action-discriminated schemas: each action accepts only its specific
declared parameters (such as `question` for `query` or `node` for `explain`), and extra or
inapplicable arguments are rejected.

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
{"action":"community","community_id":42,"budget_tokens":2000}
```

```json
{"action":"path","source":"prepare_contract","target":"validate_contract","max_hops":6,"undirected":true}
```

```json
{"action":"impact","node":"validate_contract","depth":2,"relations":["CALLS"],"budget_tokens":2000}
```

```json
{"action":"god_nodes","top_n":10,"exclude_hubs_percentile":95,"budget_tokens":2000}
```

```json
{"action":"list_prs","base":"main","limit":10,"budget_tokens":2000}
```

```json
{"action":"pr_impact","pr_number":123,"budget_tokens":2000}
```

```json
{"action":"triage_prs","base":"main","limit":10,"budget_tokens":2000}
```

```json
{"action":"visualize","format":"graph","detail":"auto"}
```

```json
{"action":"update","reason":"Committed the scoped contract-validation changes","changed_paths":["src/contracts.py"],"mode":"configured"}
```

Identifiers and pull-request numbers in examples above are illustrative. Community IDs are
snapshot-local: discover a real ID by calling `explain` on a returned node
(`resolved_node.community_id`). Never treat `0` or any other community ID as a portable
default across rebuilds.

## Procedure

1. Confirm the current task and normal project guidance. Discover only relevant canonical
   procedures; do not load every project document or graph report into the prompt.
2. Query → Explain → Community discovery: Ask a bounded question with `query`. You may
   select `traversal` (`bfs` or `dfs`), `depth` (1–6) and a `context_filter` for query
   refinement only. When a promising symbol is returned, call `explain` with `node` to
   inspect connections. The response returns `resolved_node` with
   `{id, community_id, community_name}` (community fields are `null` if the node is
   unclassified). Use the returned snapshot-local `community_id` to call `community`
   for cluster context (`community` returns `{id, name, node_count}`).
3. Cumulative truncation and references: `truncated` is `true` if Graphify omitted nodes
   or lines at budget, if Aether's byte limit bounded output, or if visible sources reached
   the 50-reference cap. A complete native response that only exceeds its requested token
   estimate remains `truncated=false` with an explicit warning. Source-bearing actions
   (`query`, `explain`, `neighbors`, `community`, `path`, `impact`) return project-relative,
   revision-bound, deduplicated `{path, location, revision}` references in stable order for
   visible definitions and relation sites. The 50-reference cap is never silent: reaching
   it sets `truncated=true` and adds a warning. No snapshot or private absolute paths escape.
4. Supported recovery and exploration: When output is truncated or a query needs refinement,
   use a narrower `question`, a higher `budget_tokens` within the supported range (128–8000),
   or `explain` on a returned node. `context_filter` is supported only on `query`; `undirected`
   is supported only on `path`. `relations` narrows `impact`. `god_nodes`, the read-only PR
   actions and `visualize` are bounded optional views; GitHub and auxiliary availability are
   reported rather than replaced with a different project or model. Never use an external
   graph path, command or tool as a substitute for these supported actions.
5. Follow references to current source files before changing code or making a behavioral
   claim. Documentation can describe a requirement that the implementation does not meet.
6. Perform the authorized work with the role's existing responsibilities, tools, tests
   and review. Owning a tool does not widen scope or transfer another role's authority.
7. After an appropriate committed checkpoint, call `update` for the bound revision.
   Any role can do this; there is no Morfeo-only writer or new human approval for an
   ordinary in-scope update. `changed_paths` is an efficiency hint, not permission to
   omit other changed sources. The integration deduplicates and serializes publication.
8. Check `updated`, `unchanged` or failure and the revision actually covered. Dirty files
   are not indexed by this candidate. Never label a worker branch as the integrated
   result or union graphs from incompatible branches.
9. When a durable lesson is worth preserving, use the work-memory procedure. Shared
   project facts belong in the appropriate source document or verified code, not only
   in a private experience. Do not inject private notes into the shared index.

## Pitfalls

- Do not treat `community_id: 0` or any community ID as a portable default across snapshots
  or rebuilds. Always discover community IDs dynamically from `explain.resolved_node`.
- `context_filter` is a query-only refinement and `undirected` is a path-only traversal
  option. Do not pass either field to unrelated actions.
- Do not invoke or document external recovery mechanisms. Supported recovery is a narrower
  `question`, higher `budget_tokens` (128–8000), or `explain`.
- Do not assume `truncated=false` means output was under budget when an explicit
  complete-over-budget warning is present; conversely, `truncated=true` indicates cumulative
  truncation from native node omission, byte bounds, or the 50-reference cap.
- Do not run Graphify's global install, hooks, watch, graph merge or raw path-based
  commands to bypass the integration. No global `GRAPHIFY_OUT` destination is assumed.
- Do not read or write another project's index because the intended index is missing.
- Do not edit published `graph.json` files manually. Updates derive from source files.
- Do not demand a complete reindex on every turn or hide failed/unfinished updates.
- Structural update mode never calls a model. Configured update mode may run the selected
  `semantic.auxiliary_task` (currently `web_extract`) when semantic extraction is explicitly
  enabled in the existing component configuration. Missing or ambiguous auxiliary access is
  reported as unavailable; there is no primary-model fallback or watcher. Coverage, pending
  paths and observed usage remain explicit. This skill makes no token-saving or universal
  quality claim.
- A component error is not a reason to stop otherwise authorized development. Continue
  with direct inspection and report the knowledge limitation accurately.

## Verification

Confirm that the receipt names the bound project and intended revision, with no unexpected
sources from another project. Check actual current files and relevant tests before reporting
behavior. Verify that references and community IDs match the active snapshot. A graph update
does not certify the implementation, close a task, or satisfy an acceptance criterion by
itself. Record meaningful errors without copying private runtime paths, credentials, personal
memories or entire graph payloads into public deliverables.
