# Aether 1.0 CLI Contract

**Status**: normative public interface
**Owner**: [`../spec.md`](../spec.md)

## 1. General rules

- Executable: `aether`.
- Human output goes to stdout for successful results and stderr for errors.
- `--json` emits exactly one UTF-8 JSON object to stdout and no decorative output.
- `--dry-run` performs discovery and validation but no persistent mutation, process activation, network publication, authentication, or model call. Downloads required only for discovery MUST be represented in the plan rather than performed.
- No command accepts an API key, OAuth token, password, or raw credential as an argument.
- Commands never acquire, widen, or silently share credentials.
- A command that encounters a protected external gate returns `blocked`, explains the required owner action, and preserves state.
- `--help` and `--version` work even when the managed Hermes runtime is absent or broken.

## 2. Commands

### `aether setup`

```text
aether setup [--config PATH] [--dry-run] [--json]
```

Guided mode is used when `--config` is absent. Declarative mode parses the TOML file into the data model defined by `setup-config.schema.json`. Both modes call one planner/validator/effect engine.

Effects may include creating XDG directories, staging the lock-selected upstream or transitional-fork Hermes runtime, writing product-owned profile policy/configuration, and preparing the user service. Login autostart is opt-in. Provider authentication is delegated to the managed Hermes native mechanism.

### `aether init`

```text
aether init [PATH] [--name NAME] [--forge local|github] [--dry-run] [--json]
```

- Defaults `PATH` to the current directory.
- May initialize Git in an empty greenfield directory because `init` is explicit.
- Never creates a remote, GitHub repository, issue, pull request, commit, or push.
- Preserves a brownfield repository and refuses conflicting Aether identity.
- Writes `.aether/project.toml` conforming to `project.schema.json` plus only the minimum portable contract/bootstrap artifacts approved by the specification.
- Creates local board/workspace mappings outside tracked project content.

### `aether`

```text
aether [--project PATH] [--json]
```

Validates setup, active release, project identity, service readiness, and Morfeo profile. An explicit invocation may visibly start the Aether user service if it is stopped. It then launches Morfeo in the selected project. It never initializes a project implicitly.

`--json` validates and reports the launch plan but does not replace an interactive TUI with a JSON conversation.

### Service lifecycle

```text
aether start [--json]
aether stop [--json]
aether restart [--json]
aether status [--json]
```

These commands address only the Aether-managed user service and never another Hermes or system-wide service.

### `aether doctor`

```text
aether doctor [--project PATH] [--json]
```

Validates platform, XDG paths and permissions, manager/product compatibility, release lock, runtime artifact and executable, profile-policy parity, service state, required tools, project identity, board mapping, and WSL2 filesystem constraints. It is read-only.

### `aether update`

```text
aether update [VERSION] [--prerelease] [--dry-run] [--yes] [--json]
```

- Defaults to the newest stable compatible release.
- Prereleases require either an explicit prerelease version or `--prerelease`.
- Shows current/target versions, release notes, state preserved, local effects, and protected external effects.
- Stages and verifies before atomic activation.
- Does not adopt mutable Hermes upstream.
- Does not run on startup or a timer.

### `aether rollback`

```text
aether rollback [VERSION] [--dry-run] [--yes] [--json]
```

Defaults to the most recent prior coherent product version. Switches product-owned runtime/policy pointers and never overwrites newer user data with an old backup.

### `aether reconcile`

```text
aether reconcile [--to installed|active] [--dry-run] [--yes] [--json]
```

Resolves a manager/product mismatch caused by an external package-manager change. It either stages the product matching the installed manager or restores the manager/product relationship to the active release. It never activates an unverified mixed set.

### `aether uninstall`

```text
aether uninstall [--purge] [--export PATH] [--dry-run] [--yes] [--json]
```

Normal uninstall stops/removes the Aether service and product-owned runtime while preserving projects and exportable user state. `--purge` deletes Aether user state only after explicit confirmation. The command must leave or execute a safe finalizer for removing its uv tool environment; it must never remove uv or unrelated tools.

### Version

```text
aether version [--json]
aether --version
```

Reports manager version, active product version, selected Hermes source mode and version/tag/commit, profile-policy version, and mismatch state.

## 3. Stable JSON envelope

Every command supporting `--json` returns:

```json
{
  "schema_version": 1,
  "command": "doctor",
  "result": "ready",
  "changed": false,
  "manager_version": "1.0.0rc1",
  "active_version": "1.0.0-rc.1",
  "warnings": [],
  "errors": [],
  "data": {}
}
```

Required keys are `schema_version`, `command`, `result`, `changed`, `warnings`, `errors`, and `data`.

Allowed `result` values:

- `ready`: validation succeeded and no mutation was needed;
- `changed`: requested mutation completed and verified;
- `no_change`: requested state already held;
- `planned`: dry-run produced a valid effect plan;
- `blocked`: a protected effect, credential, spending, publication, or owner decision is required;
- `unsupported`: platform or requested capability is outside the support contract;
- `error`: validation or execution failed.

Errors and warnings are arrays of objects containing stable `code`, human `message`, and optional structured `details`. They must contain no secret value.

## 4. Exit codes

| Code | Meaning |
|---|---|
| `0` | `ready`, `changed`, `no_change`, or `planned` |
| `2` | Invalid command or user/config input |
| `3` | Missing prerequisite or unsupported platform |
| `4` | Integrity, verification, or compatibility failure |
| `5` | Protected effect or owner/input gate (`blocked`) |
| `6` | Service or runtime execution failure |
| `10` | Unexpected internal error |

Commands MUST NOT encode detailed domain state only in exit codes; JSON/human output carries the diagnosis.

## 5. Compatibility

- Patch releases may add optional JSON fields but may not remove required keys, rename commands, or change exit meanings.
- Minor releases may add commands or schema versions while continuing to read version 1 project/setup files.
- Breaking CLI/schema changes require an Aether major release and an explicit migration/rollback path.
