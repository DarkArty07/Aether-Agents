# Plugins and tools

Aether declares three public [Hermes plugin entry points](https://hermes-agent.nousresearch.com/docs/). Generic plugin installation, configuration, and toolset behavior remain documented by Hermes; this page covers the Aether-owned registration rules.

This is reference material for an already understood installation boundary. New readers should begin with [Start here](../start-here.md) and [Getting started](../getting-started.md); the [glossary](glossary.md) defines the role and contract terms used here.

## Package entry points

| Entry point | Module | Current behavior |
| --- | --- | --- |
| `aether-contract-observer` | `aether_agents.observation.capture.hermes_plugin` | Passive Contract Observation capture. A configured Morfeo resource can expose the curated `aether_observe` tool. |
| `aether-objective-contracts` | `aether_agents.objective_contracts.hermes_plugin` | Morfeo-only transactional Objective Contract authoring and execution-board preparation. |
| `aether-project-knowledge` | `aether_agents.knowledge.hermes_plugin` | Optional shared structural graph and project/role work notes; identical tools for all three roles, disabled in the portable templates until configured. |

The entries are declared in `pyproject.toml` under `hermes_agent.plugins`. Presence in a portable resource bundle is not proof that a local live profile is activated.

## `aether_observe`

The observer plugin registers `aether_observe` only when all of the following hold:

- the profile is `morfeo`;
- the plugin context exposes tool registration; and
- the `curated_tool` setting is exactly enabled.

It belongs to the `aether_observation` toolset. Its action enum is `status`, `changes`, and `diagnose`; optional arguments are `ref`, `project`, and `since_summary_id`. It returns bounded deterministic information and rejects other roles at the runtime handler boundary. It does not return raw logs/events, prompts, results, errors, command lines, or diffs.

## `objective_contract`

The Objective Contract plugin registers `objective_contract` only in the configured Morfeo profile with `author_profile: morfeo`. It belongs to the `aether_contracts` toolset and requires `action` and the portable `project_id`.

Supported actions are:

- `begin`
- `set_section`
- `show`
- `list`
- `validate`
- `finalize`
- `supersede`
- `prepare_handoff`

`set_section` and finalization use revision-aware transactional behavior. `prepare_handoff` does not dispatch a card: it validates final Git-reachable bytes and returns opaque local root-card routing data after isolated board provisioning. See [Objective Contracts](../guides/objective-contracts.md).

## `project_knowledge` and `work_memory`

The knowledge plugin registers both tools in `aether_knowledge` when its `enabled` setting is exactly `true` and the native profile is Morfeo, Supervisor or Implementer. Registration does not import Graphify or start a process. Configuration and data remain installation-local; there is no model-selected role, project path or storage override. An exact native session workspace or an operator-created binding must resolve to the registered project and worktree on every call.

### Schema and parameter discrimination

Canonical parameter schemas use action-discriminated branches under `oneOf` while retaining root properties (`type=object`, `additionalProperties=false`, `required=["action"]`). Every field description names the actions that accept it. This ensures usability when Hermes schema sanitizers strip top-level combinators for strict LLM providers, while runtime `validate_arguments` continues to enforce action-specific schemas:

| Tool | Actions | Required arguments | Optional arguments |
| --- | --- | --- | --- |
| `project_knowledge` | `status` | None | None |
| `project_knowledge` | `query` | `question` | `budget_tokens`, `traversal`, `depth`, `context_filter` |
| `project_knowledge` | `explain` | `node` | `budget_tokens` |
| `project_knowledge` | `neighbors` | `node` | `relation`, `budget_tokens` |
| `project_knowledge` | `community` | `community_id` (snapshot-local) | `budget_tokens` |
| `project_knowledge` | `path` | `source`, `target` | `max_hops`, `budget_tokens`, `undirected` |
| `project_knowledge` | `impact` | `node` | `depth`, `budget_tokens`, `relations` |
| `project_knowledge` | `update` | `reason` | `changed_paths`, `mode` |
| `project_knowledge` | `stats` | None | None |
| `project_knowledge` | `god_nodes` | None | `top_n`, `exclude_hubs_percentile`, `budget_tokens` |
| `project_knowledge` | `list_prs` | None | `base`, `limit`, `budget_tokens` |
| `project_knowledge` | `pr_impact` | `pr_number` | `budget_tokens` |
| `project_knowledge` | `triage_prs` | None | `base`, `limit`, `budget_tokens` |
| `project_knowledge` | `visualize` | None | `format`, `detail` (graph only) |
| `work_memory` | `save` | `idempotency_key`, `situation`, `lesson`, `applicability`, `outcome`, `evidence` | `source_nodes` |
| `work_memory` | `search` | `query` | `limit`, `budget_tokens` |
| `work_memory` | `read` | `note_id` | `cursor` |
| `work_memory` | `correct` | `note_id`, `expected_revision`, `reason`, `replacement`, `evidence` | None |
| `work_memory` | `reflect` | None | None |

### Discovery, truncation, and provenance

Knowledge discovery follows a query→explain→community progression:
1. `query` locates relevant nodes. It alone accepts `traversal`, `depth` and `context_filter`;
   the filter is query refinement, not a general recovery mechanism.
2. `explain` provides symbol details and returns `resolved_node` (`{id, community_id, community_name}`, with `null` community fields if unclassified);
3. `community` consumes the snapshot-local `community_id` and returns `{id, name, node_count}`. Community IDs belong to the active snapshot and are not portable across rebuilds.

`path.undirected` controls reverse traversal only. `impact.relations` narrows impact edges.
`god_nodes` and `stats` are bounded local graph views. `list_prs`, `pr_impact` and
`triage_prs` are optional read-only GitHub views; `visualize` exports a graph or tree handle
without changing the published snapshot.

The `truncated` flag is cumulative across native omission at budget, the 32,768-byte content ceiling and the 50-reference cap. A complete native answer that exceeds its requested estimate remains `truncated=false` with an explicit warning. Supported recovery is restricted to narrower questions, higher `budget_tokens` (128–8,000), or `explain` on returned nodes. `context_filter` is valid only for `query`, and `undirected` only for `path`; other upstream recovery mechanisms are not exposed.

Source-bearing actions (`query`, `explain`, `neighbors`, `community`, `path`, `impact`) return deduplicated, project-relative, revision-bound `{path, location, revision}` references in stable order. The 50-reference cap sets `truncated=true` and emits an explicit warning. Private working-tree or snapshot-internal absolute paths never escape.

`outcome` is `useful`, `dead_end` or `corrected`; evidence is not independently verified merely because an agent supplies it.

All roles can update; a stable lock coordinates writes, not role permissions. Worktree revisions remain separate. Experiences are keyed by project and role; temporary implementers share role notes without sharing Hermes homes. Save keys are hashed and make exact retries return one note; reusing a key with different content is an explicit conflict, while separate contributions use separate keys. Corrections use optimistic revision checks and reflection includes only current complete notes. Original notes remain available through search/read because native `reflect` aggregates signals rather than full technical solutions.

Errors use `ok: false` and a typed `error.code`; identity conflicts return no substitute data. The integration falls back to ordinary file work, never to a different graph. See [project knowledge](../guides/project-knowledge.md) for setup, coverage, privacy and qualification limits. Graphify's global graph merging, HTTP serving and automatic learning sidecars are not exposed by this plugin.

Structural updates do not call a model. Configured updates may use the explicitly enabled,
profile-scoped auxiliary task and publish semantic coverage, pending/failed paths, fingerprint
and observed usage. Missing or ambiguous auxiliary access is unavailable/partial, with no
primary-model fallback or watcher. This is not a token-saving or universal-superiority claim.

## Observer hook boundary

The observer plugin is fail-open with respect to Hermes lifecycle: callbacks are observers, not directives. It bounds metadata and avoids prompt/result/error copying. Plugin hook support is a generic Hermes capability; inspect the [Hermes hooks documentation](https://hermes-agent.nousresearch.com/docs/) for its host-side interface.

For full source/test traceability and current qualification limits, see [Capability coverage](capabilities.md).

## Next step

For project and role context, read [Project knowledge and role work memory](../guides/project-knowledge.md); for the beginner vocabulary, use the [glossary](glossary.md).
