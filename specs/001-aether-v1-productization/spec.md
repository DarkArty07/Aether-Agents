# Aether 1.0 Productization and Public Release Specification

**Contract ID**: A1
**Status**: canonical reconciliation in progress under PD-65 through PD-67
**Accepted product decisions**: `DESIGN.md` PD-01 through PD-67
**Decision authority**: Christopher
**Contract owner**: Morfeo
**Execution owner**: Supervisor
**Written**: 2026-08-20
**Repository baseline inspected**: `00260254b497dc07f0c7d1922831612cc10114a5`
**Depends on**: `DESIGN.md`, R0-R13, the current public Aether repository, Hermes Agent upstream, the transitional public `DarkArty07/hermes-agent` fork only while indispensable patches remain, PyPI, uv, and GitHub Actions
**May affect**: R4, R8, R9, R10, R11, R12, R13, README, repository policy, release automation, and the live Aether installation only after a separately authorized cutover
**Research and rationale**: [`research.md`](research.md)
**Technical plan**: [`plan.md`](plan.md)

## 1. Purpose

Turn Aether from Christopher's locally configured three-role Hermes system into a public, stable, portfolio-quality product that a third party can install, configure with their own supported provider and models, use across isolated software projects, update, roll back, and uninstall on Linux native or WSL2.

The public product is a packaged Python CLI named `aether-agents`, exposing the `aether` executable. It manages an isolated, release-locked Hermes runtime without replacing a user's personal Hermes installation. The target source is a qualified stable upstream tag and commit; the public fork is permitted only as a documented transition while an indispensable accepted guarantee lacks an upstream replacement. Aether 1.0 is complete only after the exact public release candidate passes deterministic and live qualification through the same installation path offered to users.

## 2. Authority and execution boundary

Christopher's current request authorizes this contract and the reversible local build, documentation, and verification work needed to prepare Aether 1.0. It does not silently authorize a protected external effect.

The following remain separate gates:

- pushing branches or tags, merging or publishing pull requests, changing GitHub repository settings, enabling Discussions or Pages, publishing fork or Aether releases, and publishing to TestPyPI or PyPI;
- creating or changing PyPI trusted-publisher configuration;
- using credentials, sharing authentication across profiles, or spending against a live model provider;
- installing the candidate into, migrating, stopping, restarting, or replacing Christopher's current live Aether installation;
- deleting user state, repositories, releases, packages, or remote resources.

Supervisor MUST stop the affected lane at the relevant gate rather than interpreting the build objective as publication or activation authority.

## 3. Scope

### 3.1 In scope

- public Python packaging and the `aether` management CLI;
- a qualified upstream-first Hermes runtime with a bounded, explicitly retiring downstream transition when still necessary;
- reproducible role definitions and policy for Morfeo, Supervisor, and Implementer;
- guided and declarative setup without secret material;
- per-project initialization and isolation for greenfield and brownfield Git repositories;
- local service lifecycle needed by the Hermes board dispatcher;
- explicit update, mismatch detection, rollback, and safe uninstall;
- Linux-native and WSL2 support;
- public documentation, GitHub presentation, support surfaces, release automation, provenance, and known limitations;
- deterministic qualification and a preregistered live release-candidate flow;
- reconciliation of every canonical or derived artifact invalidated by PD-48 through PD-67.

### 3.2 Out of scope for 1.0

- Windows-native or macOS support;
- Aether-owned telemetry;
- a hosted Aether service, cloud control plane, centralized account, or credential broker;
- replacing or modifying another Hermes installation;
- Docker/Podman as the canonical product surface;
- publishing a renamed Hermes fork to PyPI;
- automatic adoption of Hermes upstream changes;
- supporting forges other than GitHub as a qualified external collaboration surface;
- guaranteeing semantic live progress beyond heartbeats or perfect retry/recovery taxonomy (`#195` and `#192`);
- a public model benchmark or a fixed vendor/model list;
- copying Christopher's Router, model aliases, credentials, memories, sessions, preferences, logs, databases, caches, or personal skill catalog;
- changing the three-role topology or adding a fourth role.

## 4. User scenarios and acceptance

### US1 — Install a public, isolated Aether

A Linux or WSL2 user installs `aether-agents` from PyPI with uv and runs guided setup. Aether verifies and installs the exact qualified Hermes source locked to that Aether release—upstream by default, transitional fork only when the lock documents an indispensable residual patch—creates the three portable profiles, and leaves any existing Hermes installation untouched.

**Acceptance scenarios**:

1. Given a supported clean user account with uv, Git, Python, and network access, when `uv tool install aether-agents` and `aether setup` complete, then `aether doctor` reports a coherent ready installation with exact versions and no reference to Christopher's private runtime.
2. Given an existing personal Hermes installation, when Aether is installed or removed, then the personal installation's files, config, credentials, processes, and state are byte-for-byte unchanged.
3. Given tampered or mismatched Hermes source or artifacts, when setup verifies the lock, then installation fails closed before executing or activating the runtime.

### US2 — Configure a provider-independent model hierarchy

A user selects any Hermes-supported provider and binds models by role. The methodology remains descending capability/cost rather than a private list of GPT identifiers.

**Acceptance scenarios**:

1. Given three supported model identifiers, when setup writes the role configs, then Morfeo, Supervisor, and Implementer receive the selected bindings without private owner defaults or embedded credentials.
2. Given one model selected for all roles, when setup validates the configuration, then it accepts the configuration while explaining that the descending allocation is a recommended methodology, not a requirement for three distinct vendors or models.
3. Given secrets embedded in a declarative setup file or command-line option, when setup parses the input, then it rejects the secret-bearing form and points to native Hermes authentication or environment provisioning.

### US3 — Initialize and use independent projects

A user runs `aether init` in a new or existing Git project, then invokes `aether`. The project gets portable contract identity while its board, workspaces, credentials, and runtime state remain local and isolated from every other project.

**Acceptance scenarios**:

1. Given an empty project directory, when the user explicitly initializes it, then Aether can create a Git repository and the minimum portable Aether project artifacts without inventing product principles.
2. Given an existing Git repository, when `aether init` runs, then it inspects current project reality, preserves existing content and governance, and creates only non-conflicting Aether artifacts.
3. Given two initialized repositories, when work is routed in both, then their boards, workspace paths, task state, and project memories cannot collide.
4. Given an uninitialized directory, when `aether` is invoked, then it does not silently initialize or mutate the project; it returns an actionable initialization error.

### US4 — Update and recover safely

A user requests an update. Aether previews the transition, stages and verifies a complete compatible set, and switches atomically. A failure returns to the previous coherent set. An external uv upgrade is detected rather than silently trusted.

**Acceptance scenarios**:

1. Given a valid newer Aether release, when `aether update` succeeds, then CLI compatibility, runtime, release lock, profile policy, and product metadata identify one coherent release while credentials, sessions, memories, projects, and board data remain preserved.
2. Given a verification failure after staging, when the update aborts, then the previously active release still launches and the failed candidate remains inspectable without becoming active.
3. Given `uv tool upgrade aether-agents` changed only the manager, when `aether doctor` runs, then it reports the mismatch and offers explicit reconciliation or rollback before incompatible activation.
4. Given a prior coherent version, when `aether rollback` completes, then the prior runtime and product-owned profile policy become active without restoring stale credentials or user state over newer user data.

### US5 — Uninstall without destroying user work

A user removes Aether. Product-owned services, runtimes, caches, and generated integration are removed while repositories and user state are preserved by default. Purging state is a distinct, explicit action.

**Acceptance scenarios**:

1. Given a normal uninstall, when it completes, then no Aether service or managed runtime remains active, but initialized projects and an exportable state backup remain.
2. Given `--purge`, when the user has not supplied the required explicit confirmation, then no user state is deleted.
3. Given a completed uninstall, then no personal Hermes installation or unrelated uv tool is altered.

### US6 — Evaluate a real public release candidate

A release operator installs the RC from PyPI and runs a preregistered realistic Git project through the complete Aether pipeline using a public Hermes-supported provider.

**Acceptance scenarios**:

1. Given the RC's exact PyPI package and locked Hermes source mode, when deterministic qualification runs, then every required test, package, manifest, provenance, documentation, secret, transition, and clean-install check passes against those inputs rather than a source-tree shortcut.
2. Given explicit credential and spend authorization, when the live qualification runs, then one objective proceeds through Morfeo, Supervisor, Implementer, independent review, and integration with durable evidence.
3. Given Linux-native and WSL2 evidence, when the final release review occurs, then unsupported, assumed, or waived claims remain visibly labelled and no RC is presented as stable.

## 5. Functional requirements

### 5.1 Product identity and platform

- **A1-FR-001**: The public Python distribution MUST be named `aether-agents` and MUST expose the `aether` executable.
- **A1-FR-002**: PyPI MUST be the canonical package index and `uv tool install aether-agents` the normal installation path.
- **A1-FR-003**: The stable product version MUST follow SemVer; Git tags MUST use `vMAJOR.MINOR.PATCH[-PRERELEASE]` and Python metadata MUST use the equivalent PEP 440 form.
- **A1-FR-004**: Aether 1.0 MUST support Linux native and WSL2 only.
- **A1-FR-005**: Ubuntu 24.04 LTS native and Ubuntu 24.04 LTS on WSL2 MUST be release qualification lanes; the current Garuda/Arch environment MUST remain a continuous dogfood lane.
- **A1-FR-006**: WSL2 support MUST require `systemd`, Linux-side tools, and repositories plus Aether state on the Linux filesystem rather than `/mnt/c`.
- **A1-FR-007**: Windows-native and macOS paths MUST fail or identify themselves as unsupported rather than implying qualification.
- **A1-FR-008**: Aether MUST remain MIT licensed and MUST preserve Hermes upstream license and attribution in every runtime source and release material.

### 5.2 Qualified Hermes runtime and fork retirement

- **A1-FR-009**: Aether MUST target one qualified stable Hermes upstream tag and commit; mutable upstream `main` MUST NOT be an installation or release input.
- **A1-FR-010**: The public `DarkArty07/hermes-agent` fork MAY be selected only as a transitional source when an accepted Aether guarantee still depends on an indispensable patch unavailable through a qualified upstream release or public extension surface.
- **A1-FR-011**: No new Aether product capability MAY require a downstream-only Hermes core change after PD-65; adaptation MUST prefer upstream interfaces, configuration, profiles, skills, plugins, and Aether-owned external control.
- **A1-FR-012**: Every downstream-only patch MUST have a durable ledger entry containing purpose, upstream base, affected guarantee, verification, upstream issue or PR when applicable, and an executable retirement condition.
- **A1-FR-013**: Generally applicable fixes MUST continue to be proposed upstream; an upstream equivalent MUST retire the downstream patch after parity and regression qualification.
- **A1-FR-014**: Upstream adoption MUST be explicit and release-bound; no job, startup path, or package update MAY merge or install mutable upstream `main` automatically.
- **A1-FR-015**: Each Aether release lock MUST declare `upstream` or `transitional_fork` as its Hermes source mode and bind the exact public repository, tag, commit, source or artifact location, SHA-256, Python compatibility, and provenance evidence used by that mode.
- **A1-FR-016**: Aether MUST install the original `hermes-agent` distribution into an isolated versioned runtime and MUST NOT rename it on PyPI, vendor its source into the Aether package, or modify another Hermes installation.
- **A1-FR-017**: A `transitional_fork` lock MUST additionally bind the exact upstream base and fork ref and MUST identify every residual downstream patch whose retirement gate prevents upstream mode.
- **A1-FR-018**: Setup and update MUST verify the complete release lock before installing or activating a runtime.
- **A1-FR-019**: Runtime artifacts MUST be installed into an Aether-owned versioned environment and MUST NOT modify another Hermes environment or executable.
- **A1-FR-020**: Every patch line recorded in `HERMES_LOCAL_PATCHES.md` MUST be reconciled against the selected stable upstream baseline and classified as retired, upstream-pending, or indispensable-transition; none MAY be copied blindly.

### 5.3 Package and publication

- **A1-FR-021**: `aether-agents` MUST build reproducible wheel and source distributions from a standard `pyproject.toml` src-layout package.
- **A1-FR-022**: The manager CLI MUST minimize its own dependencies so diagnosis and rollback remain available when the managed Hermes runtime is broken.
- **A1-FR-023**: Package tests MUST install and exercise the built wheel, not only import the source checkout.
- **A1-FR-024**: PyPI publication MUST use GitHub Actions OIDC Trusted Publishing and MUST NOT require a stored PyPI API token.
- **A1-FR-025**: The publish job MUST have job-scoped `id-token: write`, consume artifacts from a separate build/verification job, and use a protected `pypi` environment.
- **A1-FR-026**: Release automation MUST support SemVer RC tags and MUST mark RC GitHub Releases and PyPI versions as prereleases.
- **A1-FR-027**: Stable publication MUST refuse a tag that is not the verified commit at the protected default branch or whose package, lock, changelog, and tag versions differ.
- **A1-FR-028**: Package metadata MUST link source, documentation, changelog, issues, security policy, and license.

### 5.4 Setup and model binding

- **A1-FR-029**: `aether setup` MUST provide a guided interactive path.
- **A1-FR-030**: `aether setup --config <path>` MUST provide a declarative path using the same parser, planner, validation, and effect engine as the interactive path.
- **A1-FR-031**: Setup MUST support `--dry-run` and machine-readable `--json` output without exposing secrets.
- **A1-FR-032**: Declarative setup MUST conform to [`contracts/setup-config.schema.json`](contracts/setup-config.schema.json).
- **A1-FR-033**: Setup inputs MUST contain no API key, OAuth token, credential file content, or secret command-line value.
- **A1-FR-034**: Provider authentication MUST use native Hermes authentication or user-provisioned environment state and MUST remain explicit when shared across roles.
- **A1-FR-035**: Public templates, examples, tests, docs, and defaults MUST contain no private owner endpoint, key name, provider alias, or model identifier.
- **A1-FR-036**: The role configuration MUST express descending capability and cost: highest-capability Morfeo, strong independent Supervisor, and the least expensive Implementer that still passes the required quality gates.
- **A1-FR-037**: Users MUST be allowed to select the same supported model for two or all three roles.
- **A1-FR-038**: Model/provider identifiers MUST remain user configuration and MUST NOT become product decisions or prompt content.
- **A1-FR-039**: Setup MUST install sanitized Morfeo, Supervisor, and Implementer identities plus the shared canonical policy with a visible profile-policy version.
- **A1-FR-040**: The public distribution MUST use an explicit allowlist of Aether-owned profile resources; it MUST NOT recursively copy any local profile or skill directory.

### 5.5 Local service and launch

- **A1-FR-041**: Aether MUST manage the local Hermes gateway/dispatcher required for board work through an Aether-owned user service, never a system service requiring root.
- **A1-FR-042**: The CLI MUST expose `start`, `stop`, `restart`, and `status`; these commands MUST address only the Aether-managed service.
- **A1-FR-043**: Invoking `aether` in a valid initialized project MUST validate the active release, ensure the local service is ready, and launch Morfeo in that project.
- **A1-FR-044**: Automatic start caused by an explicit `aether` invocation MUST be visible; background startup at login MUST remain opt-in.
- **A1-FR-045**: Messaging channels MAY be configured through the managed Hermes runtime, but TUI is the required 1.0 interaction surface and no messaging adapter is part of the 1.0 release gate.

### 5.6 Project initialization and isolation

- **A1-FR-046**: `aether init [path]` MUST support both an empty greenfield directory and an existing brownfield Git repository.
- **A1-FR-047**: Greenfield initialization MAY create a Git repository only because the user explicitly invoked `init`; it MUST NOT create a remote or publish anything.
- **A1-FR-048**: Brownfield initialization MUST inspect and preserve existing repository governance, files, branches, remotes, and uncommitted changes.
- **A1-FR-049**: Initialization MUST create the minimum portable project identity conforming to [`contracts/project.schema.json`](contracts/project.schema.json).
- **A1-FR-050**: The project constitution MUST be established or confirmed through Morfeo and owner authority; `aether init` MUST NOT invent or silently accept project principles.
- **A1-FR-051**: Contract artifacts MUST be tracked in the project; board databases, sessions, memories, credentials, logs, caches, backups, and workspaces MUST remain local and untracked.
- **A1-FR-052**: Every initialized project MUST map to one board and one local workspace root keyed by a portable project identifier, not only by an absolute path.
- **A1-FR-053**: Two projects MUST NOT share board rows, workspace directories, project memories, or runtime activation state.
- **A1-FR-054**: Git MUST be required; GitHub MUST be the only qualified 1.0 forge for remote issues, pull requests, and releases, while local contract/build work MUST remain possible before a remote effect is requested.
- **A1-FR-055**: `gh` authentication MUST be checked only when a GitHub effect is requested and MUST NOT be acquired or widened automatically.
- **A1-FR-056**: Project initialization and inspection MUST refuse supported status for repositories or Aether state under `/mnt/c` on WSL2.

### 5.7 Update, rollback, doctor, and uninstall

- **A1-FR-057**: `aether doctor` MUST validate platform, CLI/product compatibility, release lock, artifact digests, runtime executable, profile-policy parity, service state, XDG ownership, project mapping, and required tools.
- **A1-FR-058**: `doctor --json` MUST use the stable output contract in [`contracts/cli.md`](contracts/cli.md).
- **A1-FR-059**: `aether update` MUST preview the current and target versions, protected effects, storage changes, and preserved user state before applying.
- **A1-FR-060**: Update MUST stage a complete candidate under a non-active version path, verify it, create a recoverable transition record, and switch active pointers atomically.
- **A1-FR-061**: Failed staging or verification MUST leave the current release active.
- **A1-FR-062**: Rollback MUST switch product-owned runtime and policy versions without overwriting newer credentials, memories, sessions, board data, or project content.
- **A1-FR-063**: A direct uv upgrade or other manager/runtime mismatch MUST be reported by doctor before incompatible activation and MUST offer explicit reconciliation or rollback.
- **A1-FR-064**: No update MAY run automatically, on startup, or on a timer in 1.0.
- **A1-FR-065**: `aether uninstall` MUST stop and remove the Aether-managed service and managed product artifacts while preserving projects and an exportable user-state backup by default.
- **A1-FR-066**: Destructive state deletion MUST require an explicit purge option and confirmation; unrelated Hermes or uv installations MUST remain untouched.

### 5.8 Privacy and security

- **A1-FR-067**: Aether 1.0 MUST add no telemetry or remote analytics.
- **A1-FR-068**: Aether MUST NOT upload projects, prompts, contracts, code, credentials, memories, sessions, or usage metrics except through a separate user-authorized product action such as a GitHub push or selected model call.
- **A1-FR-069**: Logs MUST remain local, apply secret redaction, and avoid raw prompt/code capture by default.
- **A1-FR-070**: Product-managed directories and credential-adjacent files MUST use least-privilege user permissions.
- **A1-FR-071**: Download, extraction, installation, backup, restore, and path resolution MUST defend against symlink escape, path traversal, partial writes, and replacement races.
- **A1-FR-072**: The shared pre-tool policy MUST remain fail-closed for secrets, credentials, cross-role boundaries, and protected effects while permitting the accepted role capabilities. For native structured file mutation tools, Morfeo contract authoring is permitted in either the launcher-bound integration context or an exact active task-bound linked worktree verified against the explicitly pinned board, task-owned run, assignee, status, `workspace_kind`, workspace, project root, and branch. Morfeo calls in either context MUST use absolute target paths; patch target extraction MUST be parser-equivalent to the lock-selected Hermes version, validate both move endpoints, and fail closed on unrecognized operation headers. This requirement does not claim that shell or code-execution tools are path-confined by the same parser.
- **A1-FR-073**: `computer_use` and browser execution MUST remain absent from Aether role configurations in 1.0.
- **A1-FR-074**: Secret scanning MUST cover tracked source, built wheel/sdist contents, generated docs, profile bundles, release manifests, and downstream release metadata.

### 5.9 Public repository and support surface

- **A1-FR-075**: GitHub repository description, topics, README, roadmap, changelog, contribution guide, security policy, issue forms, and release templates MUST describe the current three-role public product rather than the retired single-profile configuration.
- **A1-FR-076**: The README MUST include product value, architecture, supported platforms, prerequisites, a tested quickstart, provider/model flexibility, privacy statement, known limitations, docs link, and exact stable install command.
- **A1-FR-077**: GitHub Pages MUST publish maintained product documentation including install, setup, concepts, commands, projects, updates, troubleshooting, downstream policy, security, and contributing.
- **A1-FR-078**: The public architecture diagram and short terminal demonstration MUST derive from the verified RC and MUST NOT contain simulated success, private identifiers, credentials, or Christopher's project data.
- **A1-FR-079**: GitHub Issues MUST handle defects and features, Discussions MUST handle questions, and private vulnerability reporting MUST handle security disclosures, with no response-time SLA implied.
- **A1-FR-080**: Pre-1.0 history and releases MUST be preserved and described as experimental/legacy rather than rewritten or deleted.
- **A1-FR-081**: Issues `#192` and `#195` MUST remain visible non-blocking known limitations assigned to future minor release scope unless Christopher explicitly changes them.

### 5.10 Qualification and release gates

- **A1-FR-082**: Deterministic CI MUST test CLI parsing, schemas, path safety, manifest verification, profile-policy parity, project isolation, setup parity, service command boundaries, update staging, rollback, uninstall preservation, package metadata, built distributions, docs links, workflow validity, and secret absence.
- **A1-FR-083**: Clean-install tests MUST start from a disposable user environment and MUST NOT rely on Christopher's ignored `home/` state, editable Hermes checkout, credentials, cache, or existing services.
- **A1-FR-084**: The release candidate MUST be installed from PyPI and MUST consume the exact verified public Hermes source or artifact declared by its release-lock mode; `transitional_fork` qualification MUST use the locked downstream GitHub Release artifacts, while `upstream` qualification MUST use the locked stable upstream source and controlled original-package build path.
- **A1-FR-085**: A preregistered live scenario MUST use a realistic Git repository and a public Hermes-supported provider, never private owner infrastructure.
- **A1-FR-086**: Live qualification MUST require explicit credential and spend authority and MUST redact all resulting public evidence.
- **A1-FR-087**: The complete live path MUST include Morfeo contract extraction, one Supervisor handoff, Implementer execution, independent review, integration, and an owner-readable evidence report.
- **A1-FR-088**: Linux-native and WSL2 results MUST be separately recorded; Garuda/Arch dogfood MUST not substitute for either reference lane.
- **A1-FR-089**: No `v1.0.0` tag or stable publication MAY occur until the exact RC satisfies every non-waived success criterion and Christopher explicitly authorizes publication.
- **A1-FR-090**: A waiver MUST identify the failed criterion, evidence, impact, alternative, and owner decision; it MUST NOT silently rewrite the requirement or represent missing evidence as success.
- **A1-FR-091**: Release qualification MUST reproduce and prevent both observed policy false-positive classes: read-only validation classified as protected gateway lifecycle, and an exact active Morfeo task-bound contract workspace rejected solely because it is not the main worktree. The task-bound regression MUST use production-shaped Hermes hook identity and negative controls for missing board pin, stale or cross-task run, non-Morfeo assignee, inactive state, missing or mismatched workspace, non-worktree kind, standalone clone, branch mismatch, relative or out-of-workspace target, parser-recognized no-space operation markers, hidden mixed operations, both move endpoints, and unrecognized operation headers. Denials remain authoritative during development; each correction requires positive and negative regression evidence rather than a tool workaround.

## 6. Non-functional requirements

- **A1-NFR-001 — Recoverability**: Every local mutation made by setup, init, update, rollback, service management, or uninstall MUST either be atomic or have tested deterministic recovery.
- **A1-NFR-002 — Inspectability**: Every command that changes state MUST provide a dry-run or preview where meaningful and a machine-readable report of planned or completed effects.
- **A1-NFR-003 — Portability**: Product resources MUST contain no personal name requirement, absolute machine path, private provider, private model, secret, or local runtime identifier.
- **A1-NFR-004 — Minimal manager**: The management CLI MUST remain usable for doctor and rollback even when the managed Hermes runtime cannot import or start.
- **A1-NFR-005 — Determinism**: An Aether release lock and the same supported inputs MUST resolve to the same product-owned runtime/profile bytes.
- **A1-NFR-006 — Accessibility**: Human CLI output MUST be readable without color; JSON output MUST remain stable enough for automation and avoid prose-only error state.
- **A1-NFR-007 — Performance**: No numeric startup or install target is set without baseline evidence. The implementation MUST record install and launch timings on the qualification environments and treat material regression as a release finding rather than inventing a threshold now.
- **A1-NFR-008 — Documentation truth**: A command is documented as working only after it has executed through the public package path with the observed result retained as release evidence.

## 7. Canonical interfaces and data entities

- The normative CLI surface and exit/result contract are in [`contracts/cli.md`](contracts/cli.md).
- Parsed declarative setup input MUST conform to [`contracts/setup-config.schema.json`](contracts/setup-config.schema.json).
- Portable project identity MUST conform to [`contracts/project.schema.json`](contracts/project.schema.json).
- The release dependency lock MUST conform to [`contracts/release-lock.schema.json`](contracts/release-lock.schema.json).

Implementation MAY add private internal structures, but it MUST NOT change these public interfaces without correcting this contract first.

## 8. Success criteria

- **A1-SC-001**: From a clean Ubuntu 24.04 LTS user account, the documented PyPI install and guided setup produce `doctor: ready` without any local Aether files.
- **A1-SC-002**: The equivalent declarative setup produces byte-equivalent product-owned configuration for the same non-secret inputs.
- **A1-SC-003**: A pre-existing personal Hermes installation remains unchanged across Aether install, update, rollback, and uninstall tests.
- **A1-SC-004**: Tampering with any locked artifact causes fail-closed verification before activation.
- **A1-SC-005**: Two initialized projects operate with distinct boards, workspaces, and local state.
- **A1-SC-006**: Update failure at each injected transition point leaves either the old complete release or the new complete release active, never a mixed set.
- **A1-SC-007**: Normal uninstall preserves projects and recoverable user state; purge cannot occur without explicit confirmation.
- **A1-SC-008**: Built wheel, sdist, profile bundle, docs, release lock, and Hermes source-mode metadata contain zero detected secret/private-runtime material.
- **A1-SC-009**: Ubuntu native and Ubuntu WSL2 clean-install/platform checks pass; Garuda/Arch remains green as dogfood evidence.
- **A1-SC-010**: The public-provider live RC scenario completes the full three-role path with durable, owner-readable evidence.
- **A1-SC-011**: GitHub, PyPI, Pages, package metadata, changelog, and release notes agree on identity, version, support, privacy, limitations, and install command.
- **A1-SC-012**: `v1.0.0` is published only from the accepted RC commit after explicit publication authority.
- **A1-SC-013**: Read-only contract/package validation and exact board-verified Morfeo task-bound contract authoring through native structured file tools execute without false policy denial, while real gateway lifecycle violations, cross-role contract mutation, missing board identity, stale or cross-task run identity, standalone checkout, workspace-kind or branch mismatch, relative targets, parser-hidden operations, and writes outside the assigned workspace remain denied. Shell/code-execution authority is tested against its own protected-effect contract rather than counted as path confinement evidence.

## 9. Known assumptions and limitations

- The exact stable upstream tag and commit are selected and frozen during implementation. A transitional fork source remains permissible for an RC only if qualification proves that explicitly listed indispensable patches still lack an upstream replacement.
- The public provider used for live qualification remains an owner-gated execution choice because it depends on credentials and spend. The contract fixes that it cannot use private owner infrastructure.
- Git is mandatory. GitHub is the only qualified remote forge for 1.0, but local work can proceed before remote authorization.
- TUI is the required human surface. Hermes messaging adapters may work but are not 1.0 qualification claims.
- `#192` and `#195` are accepted non-blocking limitations for future minors.
- No response-time support commitment is made.

## 10. Impact and reconciliation

PD-48 through PD-67 supersede older text that described Aether as a private single-profile configuration layered on unmodified Hermes, as permanently bound to a downstream fork, or as requiring all Morfeo contract drafts to be written directly on the integration checkout. Before implementation closes, the owning and derived artifacts MUST be reconciled. At minimum:

- R4: replace both the absolute no-fork rule and the permanent-downstream assumption with the upstream-first transitional boundary;
- R9: reconcile public XDG state, project identity, backup, and update ownership;
- R10: add package supply-chain, downstream provenance, public installation, privacy, and publication gates;
- R11: add clean-package, update/rollback, platform, and public release evidence;
- R12: remove private model identifiers and preserve provider-independent descending allocation;
- R13: replace the private-local implementation-entry assumption with the public product/release entry contract;
- README, ROADMAP, AGENTS, templates, policy manifest, changelog, workflows, and GitHub metadata: describe and validate the product actually shipped.

Unrelated completed decisions remain closed. Reconciliation MUST preserve historical rationale in research and Git history rather than deleting it.

## 11. Supervisor handoff rule

Supervisor receives this complete artifact set as one contract. Supervisor MUST:

1. establish executability and run cross-artifact analysis before creating any implementation unit;
2. settle shared implementation decisions from this contract and stamp them into every dependent card;
3. decompose across Aether packaging, downstream Hermes, managed runtime, profile/policy, project integration, security, documentation/GitHub, and qualification responsibilities as the real dependency graph requires;
4. encode protected external gates instead of giving workers publication, credential, spend, live-cutover, or destructive authority;
5. create independent review/qualification lanes where they add evidence;
6. not reinterpret owner-approved requirements as optional portfolio polish.

Morfeo creates no implementation units and `tasks.md` is intentionally absent.