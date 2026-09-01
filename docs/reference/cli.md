# CLI reference

This reference describes the parser currently implemented by `aether`, not the larger normative CLI contract. Every command that supports `--json` emits one envelope; parser help and `--version` remain Hermes-free. Generic Hermes CLI behavior belongs to the [Hermes documentation](https://hermes-agent.nousresearch.com/docs/).

## Implemented commands

| Command | Current behavior | Arguments and options |
| --- | --- | --- |
| `aether --version` | Prints the package version. | `--version` |
| `aether version` | Reports the package version and warns that managed Hermes/profile-policy detail is unavailable. | `--json` |
| `aether init` | Initializes an existing Git repository root after exact native Project resolution. | `[PATH]`, `--name NAME`, `--forge local|github`, `--hermes-project ID`, `--dry-run`, `--json` |
| `aether observe` | Reads a deterministic observation brief or stable JSON envelope. | `[REF]`, `--project PATH`, `--since SUMMARY_ID`, `--watch`, `--json` |
| `aether doctor` | Inspects candidate lifecycle coherence without importing Hermes. | `--project PATH`, `--json` |

Top-level `aether [--project PATH] [--json]` accepts an explicit project selector for the bare command. In the source tree it delegates to the local Morfeo launcher when no `--json` flag is used; the complete installed project-aware launch contract is not yet qualified. Top-level `--json` returns an explicit unsupported result instead of claiming a launch plan.

### `init` details

`init` requires an existing Git root and an exact non-archived Hermes Project `primary_path` match. It has no greenfield `git init` behavior. `--hermes-project` selects among multiple exact matches and is rejected if that ID's primary path differs. The command never creates or changes a native Hermes Project. Read [Project initialization](../guides/project-initialization.md).

### `observe` details

`REF` identifies an observation trace, contract, or bound task. `--watch` and `--json` are mutually exclusive. The command is read-only and provider-free. Read [Observation](../guides/observation.md).

## Local lifecycle candidates

These commands have tested local candidate behavior, but their registry status is not a claim of a qualified public installation or release channel.

| Command | Parser surface |
| --- | --- |
| `aether setup` | `--wheel PATH` (required), `--hermes-checkout PATH` (required), `--release-lock PATH` (required), `--dry-run`, `--yes`, `--json` |
| `aether update` | `[VERSION]`, `--prerelease`, `--wheel PATH`, `--hermes-checkout PATH`, `--release-lock PATH`, `--dry-run`, `--yes`, `--json` |
| `aether rollback` | `[VERSION]`, `--dry-run`, `--yes`, `--json` |
| `aether uninstall` | `--purge`, `--export PATH`, `--dry-run`, `--yes`, `--json` |

`setup` accepts only locally supplied wheel/check-out/lock inputs. `update` and `rollback` can plan or select staged candidates. `uninstall --export` reports `EXPORT_NOT_IMPLEMENTED`; `--purge` requires `--yes`. See [Policy and recovery](../guides/policy-and-recovery.md).

## Explicitly unsupported commands

`aether start`, `aether stop`, `aether restart`, `aether status`, and `aether reconcile` are parser-visible placeholders. They return an explicit unsupported result rather than managing a service or mixed runtime state. The detailed limitation record is in [limitations and troubleshooting](limitations-and-troubleshooting.md).

## Exit and output behavior

Successful human results use stdout and errors use stderr. A JSON result uses stdout. The current result envelope retains the standard result categories (`ready`, `changed`, `no_change`, `planned`, `blocked`, `unsupported`, and `error`); use output diagnostics rather than assuming a detailed state from an exit code alone.
