# Plugins and tools

Aether declares two public [Hermes plugin entry points](https://hermes-agent.nousresearch.com/docs/). Generic plugin installation, configuration, and toolset behavior remain documented by Hermes; this page covers the Aether-owned registration rules.

## Package entry points

| Entry point | Module | Current behavior |
| --- | --- | --- |
| `aether-contract-observer` | `aether_agents.observation.capture.hermes_plugin` | Passive Contract Observation capture. A configured Morfeo resource can expose the curated `aether_observe` tool. |
| `aether-objective-contracts` | `aether_agents.objective_contracts.hermes_plugin` | Morfeo-only transactional Objective Contract authoring and execution-board preparation. |

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

## Observer hook boundary

The observer plugin is fail-open with respect to Hermes lifecycle: callbacks are observers, not directives. It bounds metadata and avoids prompt/result/error copying. Plugin hook support is a generic Hermes capability; inspect the [Hermes hooks documentation](https://hermes-agent.nousresearch.com/docs/) for its host-side interface.

For full source/test traceability and current qualification limits, see [Capability coverage](capabilities.md).
