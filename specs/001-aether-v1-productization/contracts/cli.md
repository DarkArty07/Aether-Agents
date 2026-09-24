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
aether setup [--config PATH] [--release-lock PATH] [--dry-run] [--json]
```

Guided mode is used when `--config` is absent. Declarative mode parses the TOML file into the data model defined by `setup-config.schema.json`. Both modes call one planner/validator/effect engine.

Effects may include creating XDG directories, staging the lock-selected maintained-fork Hermes runtime, writing product-owned profile policy/configuration, and preparing the user service. Login autostart is opt-in. Provider authentication is delegated to the managed Hermes native mechanism.

The local wheel/check-out implementation path requires an explicit schema-4
`--release-lock`. The manager validates its six-field Aether pre-build identity
against wheel metadata, its hash-bound observer dependency digest against the packaged
lock, and its Hermes source-tree digest against a tracked-commit archive. It retains
the exact validated lock in the staged release and never invents Git provenance from
a filename, remote artifact digest, or wheel digest.

A schema-4 lock declares `hermes.source_mode` `maintained_fork` with
`hermes.repository` `https://github.com/DarkArty07/aether-hermes` and binds the exact
fork commit, source-tree digest, Hermes package version/tag, Python compatibility and
artifact closure. The retired `transitional_fork` mode — a fixed public baseline plus
replayed residual `.patch` files — is refused for new preparation with an actionable
message; `patches/hermes/*.patch` records remain audit/reconstruction evidence and are
never applied to an active release. It also keeps the upstream `upstream` mode for a
deliberately selected public source. Hermes keeps its own distribution identity
(`hermes-agent`), which the lock records rather than renames.

### `aether init`

```text
aether init [PATH] [--name NAME] [--forge local|github] [--hermes-project ID] [--dry-run] [--json]
```

- Defaults `PATH` to the current directory and requires it to be the exact root of an existing Git repository. An unborn repository created explicitly by the owner with `git init` qualifies; an empty plain directory without Git does not.
- Never runs `git init`, creates a remote/GitHub repository, issue, pull request, commit (including an empty initial commit), or pushes.
- Preserves a brownfield repository and refuses conflicting Aether identity.
- Writes `.aether/project.toml` conforming to `project.schema.json` and only the minimum approved portable identity/ignore artifacts; it does not invent constitution, project guidance or a test standard. A `--dry-run`/`--json` preview reports the intended native-Project creation/reuse and local file/mapping effects without mutating them.
- Resolves exactly one non-archived native Hermes Project whose primary path exactly matches the repository root in the selected managed Morfeo profile. If no exact Project exists, it creates one through that release's supported native interface and verifies the returned ID/path; if one exists, it reuses it; multiple exact matches, a mismatched `--hermes-project ID`, archived identity or conflicting marker/mapping are refused. It never selects by name, slug, arbitrary current directory or approximate path. Retry after a partial failure reuses the already-created exact Project instead of duplicating it; failures expose what changed and what remains to retry without discarding unrelated state.
- Records the local Aether Project mapping outside tracked project content. No board, worktree, worker or first commit is required for onboarding. Execution boards are provisioned only by a ready Objective Contract handoff, not by `init` or by a conversation.

### `aether`

```text
aether [--project PATH] [--resume latest] [--json]
```

Validates setup, active release, project identity, service readiness, and Morfeo profile. An explicit invocation may visibly start the Aether user service if it is stopped. It then launches Morfeo in the selected project. A verified initialized repository with no commit or root `AGENTS.md` is allowed to open and continue the owner's project-intake conversation for as long as it takes to resolve intent, governance and the test standard. Morfeo inspects and confirms those questions before creating accurate guidance or starting execution. It never initializes a project, invents guidance, commits a scaffold or creates a board implicitly.

Project selection is exact and never inferred from a display name, session recency, board default, checkout recency, or approximate path. The precedence is: (1) a non-empty explicit `--project PATH`; (2) `AETHER_PROJECT_ROOT`, which also takes precedence over the current directory; (3) a verified `AETHER_PROJECT_ID` whose registry entry and portable marker agree; (4) the current directory or its nearest initialized parent. All routes verify the portable marker and the local exact-path registry binding; an explicit path containing only a copied/unregistered marker is refused.

Path input and project identity are distinct: a non-empty explicit `--project PATH` may be relative and is normalized against the invocation's current working directory before the exact marker, registry and conflict checks; an empty `--project` value is refused. `AETHER_PROJECT_ROOT` must instead be a non-empty absolute path, and an empty or relative environment value is refused rather than replaced with cwd. `AETHER_PROJECT_ID` must be a canonical UUID consistent with the selected project. Path normalization does not permit approximate, name-based or recency-based project selection.

A directory that is not an initialized root, a registry/marker disagreement, and an identity conflict are errors. A current directory with no matching initialized project and no explicit selection returns actionable `git init`/`aether init` guidance even when only one other project is registered; it never falls back to that other project. `--resume latest` continues the selected project's latest session and does not select a project.

Activation also installs the same two forms as branded desktop entries (`Aether` for a fresh session, `Continue Aether` for `--resume latest`) and, on WSL hosts, as Windows Terminal fragments, each targeting the stable `runtime/current` entry with the exact project root.

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

Validates platform, XDG paths and permissions, manager/product compatibility, release-lock schema `4`, external provenance and local transition digests, the runtime artifact/executable, manager/runtime `aether-agents` distribution/package/Git/source/installed-file identity parity, the exact `aether-contract-observer` entry-point target and per-profile enablement, declared observation write versions contained in their read sets and matched to packaged schemas/upcasters/projection code, runtime-local CLI non-shadowing, profile-policy parity, service state, required tools, project identity, board/session/launch context mappings, observation health counters, journal/archive integrity, projection compatibility, fingerprint-key permissions/epochs, and WSL2 filesystem constraints. It reports unresolved/conflicting context and preserved unknown-newer observation bytes without exposing their identifiers or key material. It is read-only and remains usable when Hermes cannot import. A mismatch between the authoritative active-release record, `runtime/current`, the launcher, the Desktop entry and the Aether-owned service projection is reported as an actionable fail-closed diagnostic instead of a silent degradation.

### `aether update`

```text
aether update [VERSION] [--prerelease] [--wheel PATH] [--hermes-checkout PATH] [--release-lock PATH] [--dry-run] [--yes] [--json]
aether update --local --aether-checkout PATH --aether-commit SHA --fork-checkout PATH --fork-commit SHA [--dry-run] [--yes] [--json]
```

`aether update` is the only supported coherent product promotion and activation
boundary. Nothing else stages, switches or activates a release, and no update runs on
startup or a timer.

- Defaults to the newest stable compatible release.
- Prereleases require either an explicit prerelease version or `--prerelease`.
- Shows current/target versions, release notes, state preserved, local effects, and protected external effects.
- Stages and verifies before atomic activation.
- Does not adopt mutable Hermes upstream.
- Does not run on startup or a timer.

Local-candidate mode:

- `--local` is mutually exclusive with `[VERSION]`, `--prerelease`, `--wheel`,
  `--hermes-checkout` and `--release-lock`.
- Inputs are explicit identities: an Aether checkout path with its exact commit and a
  maintained-fork checkout path with its exact commit. Identity is never taken from the
  current directory, checkout recency or a mutable branch tip.
- Without `--yes`, the command is a non-mutating preview that reports the exact
  Aether and fork revisions, target version and release ID, active HLP coverage,
  artifacts and hashes, expected service interruption, preserved state and any
  blockers. `--dry-run` requests the same preview explicitly.
- Preview performs no staging and no activation. It refuses dirty trees, ambiguous or
  missing checkouts, a wrong repository or branch, unknown or mismatched commits, bad
  hashes, changed inputs and incompatible Python.
- With `--yes`, activation is explicit and may interrupt Aether-owned TUI, gateway and
  worker processes immediately; there is no drain or wait-for-idle semantics. Unrelated
  services and processes are never stopped, and durable state must remain recoverable
  when the owner reopens instances.
- A partial transition is detected and recoverable rather than silently degraded, and
  `runtime/current`, the launcher, the Desktop entry and the Aether-owned service
  projection agree with the single authoritative active-release record after one
  transition.

### `aether rollback`

```text
aether rollback [VERSION] [--dry-run] [--yes] [--json]
```

Defaults to the most recent prior coherent product version. Switches product-owned runtime/policy pointers and never overwrites newer user data with an old backup; user state under the Aether state root is never rolled backward. Observation journals and key epochs continue forward unchanged; the selected reducer uses its versioned projection and preserves/indexes unknown newer bytes until a compatible forward update.

### `aether reconcile`

```text
aether reconcile [--to installed|active] [--dry-run] [--yes] [--json]
```

Resolves a manager/product mismatch caused by an external package-manager change. It either stages the product matching the installed manager or restores the manager/product relationship to the active release. It never activates an unverified mixed set.

Build-level scope (bounded, recorded under `oc_b5926701207812e8@v1`): only the `--to active` mode is implemented. It reconciles the managed projections and selector of the **already active, authenticated** release against that release's own authoritative record; the preview without `--yes` (or with `--dry-run`) is non-mutating, the applied run is idempotent, and nothing outside that release's own managed projections is touched. The command never selects another release, installs a package, edits a release record, or restarts a service where read-only reconciliation suffices. `--to installed` remains explicitly unsupported (`UNSUPPORTED_RECONCILE_MODE`) and MUST NOT be approximated by the `--to active` path. An active release that cannot prove authentication — for example a pre-schema-3 record or one without an installed-file fingerprint — is refused before any mutation (`RECONCILE_REFUSED`) as an unsupported legacy route rather than repaired from unverified bytes.

### `aether uninstall`

```text
aether uninstall [--purge] [--export PATH] [--dry-run] [--yes] [--json]
```

Normal uninstall stops/removes the Aether service and product-owned runtime while preserving projects and exportable user state. `--purge` deletes Aether user state only after explicit confirmation. The command must leave or execute a safe finalizer for removing its uv tool environment; it must never remove uv or unrelated tools.

### `aether observe`

```text
aether observe [REF] [--project PATH] [--since SUMMARY_ID] [--watch] [--json]
```

- `REF` resolves an exact observation `trace_id`, canonical `contract_id`, or bound Kanban `task_id`.
- Without `REF`, one open trace is selected; no trace returns an empty-state brief and multiple open traces return bounded ambiguity instead of guessing.
- Default human output is one coherent Morfeo-oriented review brief from the deterministic summary defined by `../../002-aether-contract-observation/contracts/observation-summary.schema.json`. It prioritizes conclusion, causal step/round/wave reconstruction, current state, verified progress, blockers/anomalies, unfinished required work and acceptance, critical path/acceleration evidence, configuration/tool/model coverage, execution quality, evidence coverage, and the next decision rather than exposing atomic per-section queries.
- `--since SUMMARY_ID` emphasizes deterministic semantic changes from a previous summary. If summary schema/reducer versions lack a declared normalization path, it reports comparison incompatibility instead of manufacturing a diff; fingerprint-key rotation alone is not a configuration change.
- `--watch` refreshes only when the summary ID, verdict, priority findings, coverage state, or next gate changes; it never tails raw journal events. It performs incremental ingestion, checks no faster than once per second, backs off to at most five seconds while unchanged, resets after a detected change, and never full-replays the journal on each check.
- `--watch` and `--json` are mutually exclusive. The stable `--json` contract emits exactly one envelope and does not silently become an NDJSON stream; the invalid combination returns one `WATCH_JSON_UNSUPPORTED` error envelope.
- Read failures distinguish retryable contention from genuine unreadability with fixed public codes. A currently held maintenance lock returns `STATE_BUSY` (native `AETHER-OBSERVE-BUSY`) and an unfinished ingestion pass within its bounded budget returns `CATCHUP_INCOMPLETE` (native `AETHER-OBSERVE-CATCHUP-INCOMPLETE`); both are retryable, neither is presented as a successful, fresh or empty summary, and the same read succeeds once the contention clears. Genuinely unreadable, schema-invalid, or privacy-refused state remains fail-closed as `STATE_UNREADABLE` (native `AETHER-OBSERVE-STATE-UNREADABLE`). No raw exception, filesystem path, payload, or lock-owner detail is exposed.
- For a resolved summary, `--json` sets the standard envelope's `data` object to
  `{"state":"summary","summary":{...}}`, where `summary` is exactly one normative
  observation-summary instance.
- With no open trace, `--json` sets `data` exactly to
  `{"state":"empty","summary":null}`. Human output is a projection of that same
  explicit state rather than an independently inferred absence.
- The envelope remains at `schema_version: 1`; clients discriminate the two
  observation variants through `data.state`, and the formerly underspecified `{}`
  empty payload is not a conforming observation result.
- The command is read-only, labels partial/estimated/unavailable fields, and makes no network or model call.

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
