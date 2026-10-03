# Tutorial: give every role a map of your project

Aether's optional project knowledge gives Morfeo, the Supervisor and the Implementers the
same structural map of your repository, built by [Graphify](https://github.com/Graphify-Labs/graphify),
plus a durable work memory per role. The agents query the map before reading sources,
then verify against the current files. The map is navigation, never authority.

This tutorial installs the component, enables it for the three roles, builds the first
snapshot and shows the queries the agents run.

## Before you start

- An initialized project ([Getting started](../getting-started.md)) with at least one
  commit. Indexing reads a committed revision; uncommitted files are reported as not indexed.
- Python 3.11 available to `uv`. Graphify runs in its own isolated environment.

## 1. Install the component

```bash
aether knowledge install --json
aether knowledge doctor --json
```

`install` installs the pinned Graphify release and its dependencies from a hash lock. It
enables no profile, installs no Git hook and downloads no Python.

## 2. Enable the plugin for each role

The packaged role profiles include the `aether-project-knowledge` plugin with its setting
off. For each role you want to use it, edit the profile's `config.yaml` under
`~/.local/state/aether/hermes/profiles/<role>/` and set the existing entry to enabled:

```yaml
plugins:
  entries:
    aether-project-knowledge:
      settings:
        enabled: true
```

Keep the rest of the plugin list unchanged. Then make the `aether_knowledge` toolset
available to that role:

```bash
hermes_bin=~/.local/share/aether/runtime/current/runtime/bin/hermes
for role in morfeo supervisor implementer; do
  HERMES_HOME=~/.local/state/aether/hermes/profiles/$role "$hermes_bin" tools enable aether_knowledge
done
```

The change applies to new sessions. Start a new Morfeo session after enabling it.

## 3. Build the first snapshot

Read the project ID from the portable marker, then build a structural snapshot of the
committed revision:

```bash
project_id=$(sed -n 's/^project_id = "\(.*\)"/\1/p' .aether/project.toml)
aether knowledge update --project-id "$project_id" --mode structural --reason "first map" --json
aether knowledge status --project-id "$project_id" --json
```

`status` reports the indexed revision, the coverage and any dirty paths that were not
indexed. Structural mode makes no model call.

## 4. Query the map

Try the same bounded query the agents use:

```bash
aether knowledge query --project-id "$project_id" \
  --question "Where is the greeting implemented and tested?" --budget-tokens 2000 --json
```

Inside a session, the agents call the `project_knowledge` tool with the same contract:
`query` to search, `explain` for one symbol, `community` for its cluster, and `neighbors`,
`impact` and `path` for exploration. After relevant commits, any role can request an
`update`; agents refresh the map at coherent checkpoints, including on the integrated
branch before closeout.

## 5. Work memory

The `work_memory` tool keeps each role's notes about this project across sessions:
decisions, pitfalls and outcomes. Notes remain agent-reported evidence. Read them
alongside the sources, and correct a note by its expected revision rather than
overwriting it. Inspect or remove notes from the CLI:

```bash
aether knowledge export --project-id "$project_id" --role morfeo --json
aether knowledge delete --project-id "$project_id" --role morfeo --note-id NOTE_ID --yes --json
```

## Turn it off

```bash
aether knowledge disable --json
```

Disabling keeps your notes and indices. It does not remove tools from sessions that are
already running.

## Learn more

- [Project knowledge and role work memory](../guides/project-knowledge.md) covers session
  binding, semantic maintenance, storage and limits.
- [CLI reference](../reference/cli.md#optional-project-knowledge) lists every `aether knowledge` option.
