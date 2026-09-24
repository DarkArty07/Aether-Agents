---
name: project-knowledge
description: Orient on project architecture, dependencies, or decisions.
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

- On the first substantive request to understand a bound project's architecture,
  dependencies, implementation, or documented decisions, discover this skill and
  consult the graph without waiting for the owner to name Graphify.
- Orient within a project, investigate dependencies, locate implementation or documented
  decisions, or return to a project in a later session.
- Refresh knowledge after a coherent committed change to relevant code or documentation,
  including on integrated main before closeout, through configured update (`mode="configured"`).
- Do not use for greetings, trivial questions, a directly supplied source or URL, or as
  ceremony before every file read. Ordinary queries, status checks, and greetings never call
  a model; no background watcher is installed.

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
inapplicable arguments are rejected. Natural-language questions can return noisy nodes
because `knowledge/graph_worker.py` passes the text directly to Graphify; refine
subsequent queries using symbols or names actually observed, or fall back to native source
search (`search_files`).

Use native file tools to inspect the relevant current sources after orientation.
A source reference in an older snapshot is a lead, not evidence that the source still
has that behavior. Read current source files before designing, changing code, or concluding.
Do not bypass a genuine protected-edge denial through another tool.

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
2. Query → Explain → Community discovery: Ask a bounded question with `query`. Natural-language
   queries can be noisy because `knowledge/graph_worker.py` passes the text directly to
   Graphify. You may select `traversal` (`bfs` or `dfs`), `depth` (1–6) and a `context_filter`
   for query refinement only. When a promising symbol is returned, call `explain` with `node`
   to inspect connections. The response returns `resolved_node` with
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
   refine using symbols or names actually observed, or fall back to source search with
   `search_files`. Alternatively, use a narrower `question`, a higher `budget_tokens` within
   the supported range (128–8000), or `explain` on a returned node. `context_filter` is
   supported only on `query`; `undirected` is supported only on `path`. `relations` narrows
   `impact`. `god_nodes`, the read-only PR actions and `visualize` are bounded optional views;
   GitHub and auxiliary availability are reported rather than replaced with a different project
   or model. Never use an external graph path, command or tool as a substitute for these
   supported actions.
5. Follow references to current source files before designing, changing code, or making a
   behavioral claim. Read returned revision, coverage, and warnings honestly. Documentation
   can describe a requirement that the implementation does not meet, and dirty files are not
   indexed.
6. Perform the authorized work with the role's existing responsibilities, tools, tests
   and review. Owning a tool does not widen scope or transfer another role's authority.
7. Perform or resume a configured update (`mode="configured"`, default) at coherent
   committed checkpoints whenever covered code or documentation changed, including
   on integrated main before closeout. Any role can do this; there is no Morfeo-only
   writer or mandatory separate human semantic request. Ordinary queries, status checks,
   and greetings never call a model, and no background watcher is installed. `changed_paths`
   is an efficiency hint, not permission to omit other changed sources. If temporary
   failures occur, at most one bounded retry is allowed; persistent unavailable or
   deferred work is reported rather than looping to force completion. The integration
   deduplicates and serializes publication.
8. Check `updated`, `unchanged` or failure and the revision actually covered. Dirty files
   are not indexed by this candidate. Never label a worker branch as the integrated
   result or union graphs from incompatible branches.
9. When a durable lesson is worth preserving, use the work-memory procedure. Shared
   project facts belong in the appropriate source document or verified code, not only
   in a private experience. Do not inject private notes into the shared index.

## Pitfalls

- Do not treat `community_id: 0` or any community ID as a portable default across snapshots
  or rebuilds. Always discover community IDs dynamically from `explain.resolved_node`.
- Natural-language queries can return noisy nodes because `knowledge/graph_worker.py` passes
  the raw text to Graphify. Refine subsequent exploration with exact symbols or names actually
  observed, or fall back to source search (`search_files`).
- Do not design or conclude based on graph output alone without reading current source files.
- Read returned `revision`, `coverage`, and warnings honestly: dirty files are not indexed,
  and a snapshot is not proof of current source behavior.
- Proportionality: do not make ceremonial graph calls for greetings, trivial questions, or
  directly supplied sources or URLs.
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
- Structural update mode never calls a model. Configured update mode (`mode="configured"`, default)
  performs or resumes semantic extraction when enabled in the existing component configuration
  (`semantic.auxiliary_task`, currently `web_extract`). One configured update is a single
  bounded transaction: at most two concurrent auxiliary calls inside a 300-second total budget,
  with cooperative cancellation, no hidden continuation and no publication of a cancelled or
  unvalidated candidate. Accepted additions are an additive `origin=llm` overlay on an immutable
  structural base — never a global graph merge — and the canonical structural projection is
  compared before publication. Only a response whose effective route matches the configured
  primary auxiliary is cached or applied. Query, status, and greetings never invoke a model, and
  no background watcher is installed. Missing or ambiguous auxiliary access is reported as
  unavailable/deferred; there is no primary-model fallback. One bounded retry is allowed for
  temporary failures; persistent unavailable/deferred work is reported, not looped.
  Snapshot warnings describe the immutable snapshot state (`complete`, `partial`, `pending`,
  `unavailable`, `disabled`, or unknown/inconsistent) rather than the configuration loaded at
  read time, so a pending snapshot never means extraction is disabled. A semantic snapshot
  without the current integrity identity is not trusted: report it as legacy/structural, keep
  the retained artifacts, and rebuild the revision. Structural query and status stay available
  when semantic work fails. Coverage, pending paths and observed usage remain explicit. This
  skill makes no token-saving or universal quality claim.
- A component error is not a reason to stop otherwise authorized development. Continue
  with direct inspection and report the knowledge limitation accurately.

## Verification

Confirm that the receipt names the bound project and intended revision, with no unexpected
sources from another project. Check actual current files and relevant tests before reporting
behavior. Verify that references and community IDs match the active snapshot. A graph update
does not certify the implementation, close a task, or satisfy an acceptance criterion by
itself. Record meaningful errors without copying private runtime paths, credentials, personal
memories or entire graph payloads into public deliverables.
