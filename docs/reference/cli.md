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

Top-level `aether [--project PATH] [--json]` validates project identity and launches Morfeo into the active release-owned TUI using packaged manager code without importing Hermes or requiring checkout scripts. Project selection is exact and never inferred from a name or recent activity: an explicit `--project PATH` wins, then `AETHER_PROJECT_ROOT` (which also outranks the current directory), then a verified `AETHER_PROJECT_ID`, then the current or nearest initialized parent directory, and finally the single registered project; several registered projects with no explicit selection produce a bounded ambiguity error. Identity values fail visibly instead of falling back to the current directory: an empty `--project` value is refused while a relative `--project PATH` is resolved against the current working directory, `AETHER_PROJECT_ROOT` must be an absolute path (an empty or relative value is refused with `must not be empty` / `must be an absolute path`), and `AETHER_PROJECT_ID` must be a canonical UUID that agrees with the portable marker, so `--project /path/to/project` may be given from anywhere while `--project project` is resolved relative to where you run it. `--resume latest` continues the project's latest session; the installed desktop and Windows Terminal `Aether` and `Continue Aether` actions launch the same two forms. See [Getting started](../getting-started.md#launch-aether-in-an-initialized-project). Top-level `--json` emits a non-mutating launch plan containing exact sorted keys (`command`, `cwd`, `hermes_executable`, `hermes_home`, `project_id`, `repo_root`, `required_toolsets`, `result`, `tui_dir`). Reserved binding overrides (`--in`, `--profile`, `--tui`, `--cli`, `--toolsets`, `-t`, `-p`, `--safe-mode`, `--ignore-user-config`, `--ignore-rules`) are rejected; `--resume` (such as `--resume latest`) is passed through.

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
| `aether update` | `[VERSION]`, `--prerelease`, `--wheel PATH`, `--hermes-checkout PATH`, `--release-lock PATH`, `--dry-run`, `--yes`, `--json`; local-candidate route: `--local`, `--aether-checkout PATH`, `--aether-commit SHA`, `--fork-checkout PATH`, `--fork-commit SHA` |
| `aether rollback` | `[VERSION]`, `--dry-run`, `--yes`, `--json` |
| `aether reconcile` | `--to active` (required for a supported mode), `--dry-run`, `--yes`, `--json` |
| `aether uninstall` | `--purge`, `--export PATH`, `--dry-run`, `--yes`, `--json` |

`setup` accepts only locally supplied wheel/check-out/lock inputs. `update` and `rollback` can plan or select staged candidates. `uninstall --export` reports `EXPORT_NOT_IMPLEMENTED`; `--purge` requires `--yes`. See [Policy and recovery](../guides/policy-and-recovery.md).

### `update` local-candidate route

`aether update` is the only supported promotion and activation boundary. Its `--local` route
takes explicit identities — an Aether checkout with its exact commit and a maintained-fork
checkout with its exact commit — and is mutually exclusive with `[VERSION]`, `--prerelease`,
`--wheel`, `--hermes-checkout` and `--release-lock`. Identity never comes from the current
directory, checkout recency or a mutable branch tip.

Without `--yes` (or with `--dry-run`) the command prints a non-mutating preview: exact Aether
and fork revisions, target version and release ID, active HLP coverage, artifacts and hashes,
expected service interruption, preserved state and any blockers. It refuses dirty trees,
ambiguous or missing checkouts, a wrong repository or branch, unknown or mismatched commits,
bad hashes and incompatible Python, and it stages or activates nothing.

Activation is explicit (`--yes`) and may interrupt Aether-owned TUI, gateway and worker
processes immediately; there is no drain or wait-for-idle semantics, unrelated services are
never stopped, and a partial transition is detected and recoverable. `aether rollback`
restores product code, runtime and service without rolling user state backward.

Release-lock `schema_version` 4 declares the maintained-fork source mode
(`hermes.source_mode = maintained_fork`, `hermes.repository =
https://github.com/DarkArty07/aether-hermes`); the retired `transitional_fork` mode is refused
for new preparation. This page documents tested local candidate behavior — it is not a claim
of a published, installed or released channel.

### `reconcile --to active`

`aether reconcile --to active` is the bounded repair surface for the **already active,
authenticated** release. It reconciles the managed projections and selector of that release
against its own authoritative active record; it never selects another release, installs a
package, edits a release record, or restarts a service where read-only reconciliation
suffices.

```bash
aether reconcile --to active --json            # plan only: mismatches, no mutation
aether reconcile --to active --dry-run --json  # same non-mutating preview
aether reconcile --to active --yes --json      # apply the reconciliation
```

Without `--yes` (or with `--dry-run`) the command reports the current mismatches and changes
nothing; the plan result is `planned` when a mismatch exists and `no_change` otherwise, and a
`CONFIRMATION_REQUIRED` warning asks for `--yes`. With `--yes` it repairs the managed
projections, reports the reconciled count, and is idempotent on a second run. `--to installed`
and a missing `--to` are refused with `UNSUPPORTED_RECONCILE_MODE` (exit 3), and an active
release that cannot prove authentication — for example a legacy record without an installed-file
fingerprint or a pre-schema-3 record — is refused with `RECONCILE_REFUSED` before any byte
changes, as an unsupported legacy route.

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

Configured mode uses semantic maintenance only when the existing component configuration enables it and binds an auxiliary task; that update operates under one authoritative monotonic 300-second budget starting at `KnowledgeStore.update()` entry through terminal receipt and pointer publication. Every budget-consuming Graphify call (including prepare, validate, and compose) consumes the remaining time with shared cancellation, and late results returned after the deadline are fenced. Only a validated, structurally preserved candidate is published, while structural mode remains no-model and snapshot-state warnings (never the loaded configuration) describe semantic coverage. `call` rejects unknown or inapplicable action fields. Use `budget_tokens` inside `--arguments` for tool actions; recovery is expressed through the validated tool contract rather than an extra CLI flag. `correct` requires `expected_revision`; a read may return `next_cursor` for the rest of a long original note. The [project-knowledge guide](../guides/project-knowledge.md) covers configuration, data placement, isolation, canonical skills, read-only GitHub/visualization behavior and qualification limits.

Knowledge commands return JSON objects with `ok`, typed errors and action-specific data, using exit 0 for success, 1 for a failed operation and argparse exit 2 for invalid CLI syntax. Without `--json`, the same object is pretty-printed. This is the knowledge-specific contract, not the lifecycle `Envelope` categories. Disabling this optional component does not delete an environment or remove tools from an already running session.

## Explicitly unsupported commands

`aether start`, `aether stop`, `aether restart`, and `aether status` are parser-visible placeholders. They return an explicit unsupported result rather than managing a service or mixed runtime state. `aether reconcile` is parser-visible for its bounded `--to active` mode only; `--to installed` and a missing `--to` return the same explicit unsupported result. The detailed limitation record is in [limitations and troubleshooting](limitations-and-troubleshooting.md).

## Exit and output behavior

For the lifecycle/version/init/observe commands, successful human results use stdout and errors use stderr. A JSON result uses stdout. Their result envelope retains the standard result categories (`ready`, `changed`, `no_change`, `planned`, `blocked`, `unsupported`, and `error`); use output diagnostics rather than assuming a detailed state from an exit code alone.
