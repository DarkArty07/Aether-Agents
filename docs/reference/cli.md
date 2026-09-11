# CLI reference

This reference describes the parser currently implemented by `aether`, not the larger normative CLI contract. Every command that supports `--json` emits one envelope; parser help and `--version` remain Hermes-free. Generic Hermes CLI behavior belongs to the [Hermes documentation](https://hermes-agent.nousresearch.com/docs/).

## Implemented commands

| Command | Current behavior | Arguments and options |
| --- | --- | --- |
| `aether --version` | Prints the package version. | `--version` |
| `aether version` | Reports the package version and warns that managed Hermes/profile-policy detail is unavailable. | `--json` |
| `aether init` | Initializes an existing Git repository root after exact native Project resolution. | `[PATH]`, `--name NAME`, `--forge local|github`, `--hermes-project ID`, `--dry-run`, `--json` |
| `aether observe` | Reads a deterministic observation brief or stable JSON envelope. | `[REF]`, `--project PATH`, `--since SUMMARY_ID`, `--watch`, `--json` |
| `aether monitor` | Controls and reads the Telegram Monitor: state, owned native hourly job, next cut, coverage gaps, last report and delivery outcomes. | `status`, `on`, `off`, `history`; `--json` on every action; `history --limit N` |
| `aether doctor` | Inspects candidate lifecycle coherence without importing Hermes. | `--project PATH`, `--json` |

Top-level `aether [--project PATH] [--json]` accepts an explicit project selector for the bare command. In the source tree it delegates to the local Morfeo launcher when no `--json` flag is used; the complete installed project-aware launch contract is not yet qualified. Top-level `--json` returns an explicit unsupported result instead of claiming a launch plan.

### `init` details

`init` requires an existing Git root and an exact non-archived Hermes Project `primary_path` match. It has no greenfield `git init` behavior. `--hermes-project` selects among multiple exact matches and is rejected if that ID's primary path differs. The command never creates or changes a native Hermes Project. Read [Project initialization](../guides/project-initialization.md).

### `observe` details

`REF` identifies an observation trace, contract, or bound task. `--watch` and `--json` are mutually exclusive. The command is read-only and provider-free. Read [Observation](../guides/observation.md).

### `monitor` details

`aether monitor` requires one of the four actions. Every action accepts `--json`; `history` also accepts `--limit N` (1–200, default 20). No action accepts a token, destination, provider or model argument: the destination and the model route come from the existing installation configuration.

```bash
aether monitor status --json
aether monitor on --json
aether monitor off --json
aether monitor history --limit 10 --json
```

Each action prints one envelope `{"schema_version": "aether.telegram-monitor.v1", "ok", "action", "result"|"error"}`. `status` and `history` read durable monitor state and remain available without Hermes; `on` and `off` need the provisioned runtime and otherwise return `RUNTIME_UNAVAILABLE` without changing state. Malformed actions, extra arguments and out-of-range limits fail closed (`INVALID_ARGUMENT`/`INVALID_LIMIT`, argparse exit 2). Offline qualification of this surface:

```bash
uv run --frozen python scripts/qualify_telegram_monitor.py --json
```

The deterministic lane is effect-free and now also proves the isolated laboratory's
bootstrap and fail-closed preflight: the private root, its decision-only configuration,
the borrowed access names and the child containment. Read
[Telegram Monitor](../guides/telegram-monitor.md) for activation, rollback, privacy and the
current qualification limits.

## Local lifecycle candidates

These commands have tested local candidate behavior, but their registry status is not a claim of a qualified public installation or release channel.

| Command | Parser surface |
| --- | --- |
| `aether setup` | `--wheel PATH` (required), `--hermes-checkout PATH` (required), `--release-lock PATH` (required), `--dry-run`, `--yes`, `--json` |
| `aether update` | `[VERSION]`, `--prerelease`, `--wheel PATH`, `--hermes-checkout PATH`, `--release-lock PATH`, `--dry-run`, `--yes`, `--json` |
| `aether rollback` | `[VERSION]`, `--dry-run`, `--yes`, `--json` |
| `aether uninstall` | `--purge`, `--export PATH`, `--dry-run`, `--yes`, `--json` |

`setup` accepts only locally supplied wheel/check-out/lock inputs. `update` and `rollback` can plan or select staged candidates. `uninstall --export` reports `EXPORT_NOT_IMPLEMENTED`; `--purge` requires `--yes`. See [Policy and recovery](../guides/policy-and-recovery.md).

## Optional project knowledge

`aether knowledge` requires a subcommand. It does not activate Hermes profiles or start an MCP server. All subcommands accept `--json`. Project-scoped operator commands accept required `--project-id UUID`, optional `--role morfeo|supervisor|implementer` (default `morfeo`) and `--workspace PATH` for a verified attached worktree. These operator selectors are not exposed as model-tool arguments.

| Subcommand | Additional options | Behavior |
| --- | --- | --- |
| `install` | None. | Explicitly install the hash-locked Graphify component with local Python 3.11 and configure it. |
| `configure` | `--python PATH` (required). | Validate an existing isolated Graphify 0.9.54 interpreter; does not certify its dependency provenance. |
| `disable` | None. | Disable component-dependent operations, preserving notes and indices. |
| `doctor` | None. | Probe version and component readiness; not a live-agent or savings test. |
| `bind` | Project options; `--session ID` (required), `--replace`. | Create or deliberately replace a per-role/session project binding. |
| `status` | Project options. | Report availability, committed revision, coverage and dirty paths. |
| `query` | Project options; `--question TEXT` (required), `--budget-tokens N`. | Return bounded graph context from the selected snapshot. |
| `update` | Project options; `--reason TEXT`, `--mode configured|structural`. | Build or reuse a committed snapshot; configured mode may run explicitly enabled semantic maintenance. |
| `call` | Project options; `--tool project_knowledge|work_memory`, `--arguments JSON` (both required). | Execute the same validated 14/5 action contract as the native tools, including exploration, read-only PR and visualization actions. |
| `export` | Project options. | Emit effective work-note records for that role/project as JSON to stdout. |
| `delete` | Project options; `--note-id ID` and `--yes` (required to delete). | Remove a note and retained local revisions, invalidating its reflection. |

Configured mode uses semantic maintenance only when the existing component configuration enables it and binds an auxiliary task; structural mode remains no-model. `call` rejects unknown or inapplicable action fields. Use `budget_tokens` inside `--arguments` for tool actions; recovery is expressed through the validated tool contract rather than an extra CLI flag. `correct` requires `expected_revision`; a read may return `next_cursor` for the rest of a long original note. The [project-knowledge guide](../guides/project-knowledge.md) covers configuration, data placement, isolation, canonical skills, read-only GitHub/visualization behavior and qualification limits.

Knowledge commands return JSON objects with `ok`, typed errors and action-specific data, using exit 0 for success, 1 for a failed operation and argparse exit 2 for invalid CLI syntax. Without `--json`, the same object is pretty-printed. This is the knowledge-specific contract, not the lifecycle `Envelope` categories. Disabling this optional component does not delete an environment or remove tools from an already running session.

## Explicitly unsupported commands

`aether start`, `aether stop`, `aether restart`, `aether status`, and `aether reconcile` are parser-visible placeholders. They return an explicit unsupported result rather than managing a service or mixed runtime state. The detailed limitation record is in [limitations and troubleshooting](limitations-and-troubleshooting.md).

## Exit and output behavior

For the lifecycle/version/init/observe commands, successful human results use stdout and errors use stderr. A JSON result uses stdout. Their result envelope retains the standard result categories (`ready`, `changed`, `no_change`, `planned`, `blocked`, `unsupported`, and `error`); use output diagnostics rather than assuming a detailed state from an exit code alone.
