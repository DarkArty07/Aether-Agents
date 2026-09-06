# Plugins and tools

Aether declares three public [Hermes plugin entry points](https://hermes-agent.nousresearch.com/docs/). Generic plugin installation, configuration, and toolset behavior remain documented by Hermes; this page covers the Aether-owned registration rules.

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

| Tool | Actions | Required arguments beyond `action` |
| --- | --- | --- |
| `project_knowledge` | `status` | None. |
| `project_knowledge` | `query` | `question`. |
| `project_knowledge` | `explain`, `neighbors`, `impact` | `node`. |
| `project_knowledge` | `community` | `community_id` from the same snapshot. |
| `project_knowledge` | `path` | `source`, `target`. |
| `project_knowledge` | `update` | `reason`; optional `mode` and `changed_paths`. |
| `work_memory` | `save` | `situation`, `lesson`, `applicability`, `outcome`, `evidence`. |
| `work_memory` | `search` | `query`; optional `limit` and `budget_tokens`. |
| `work_memory` | `read` | `note_id`; optional continuation `cursor`. |
| `work_memory` | `correct` | `note_id`, `expected_revision`, `reason`, `replacement`, `evidence`. |
| `work_memory` | `reflect` | None. |

Graph queries support bounded context. `neighbors` accepts an optional `relation`; `impact` accepts `depth`; `path` accepts `max_hops`. References and graph relations are derived evidence, not authority or exhaustive runtime analysis. `outcome` is `useful`, `dead_end` or `corrected`; evidence is not independently verified merely because an agent supplies it.

All roles can update; a stable lock coordinates writes, not role permissions. Worktree revisions remain separate. Experiences are keyed by project and role; temporary implementers share role notes without sharing Hermes homes. Corrections use optimistic revision checks and reflection includes only current complete notes. Original notes remain available through search/read because native `reflect` aggregates signals rather than full technical solutions.

Errors use `ok: false` and a typed `error.code`; identity conflicts return no substitute data. The integration falls back to ordinary file work, never to a different graph. See [project knowledge](../guides/project-knowledge.md) for setup, coverage, privacy and qualification limits. Graphify's PR tools, global graph merging, HTTP serving and automatic learning sidecars are not exposed by this plugin.

## Observer hook boundary

The observer plugin is fail-open with respect to Hermes lifecycle: callbacks are observers, not directives. It bounds metadata and avoids prompt/result/error copying. Plugin hook support is a generic Hermes capability; inspect the [Hermes hooks documentation](https://hermes-agent.nousresearch.com/docs/) for its host-side interface.

For full source/test traceability and current qualification limits, see [Capability coverage](capabilities.md).
