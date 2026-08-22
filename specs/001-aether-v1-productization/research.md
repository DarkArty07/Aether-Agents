# Aether 1.0 Productization Research and Decision Record

**Contract**: [`spec.md`](spec.md)
**Observed**: 2026-08-20T22:47:52-06:00
**Repository commit inspected**: `00260254b497dc07f0c7d1922831612cc10114a5`

## 1. Why this contract exists

Aether's three-role method is functioning in Christopher's local environment, but the public repository still distributes a design and a few reconstruction pieces rather than the product that was tested. `v1.0.0` is therefore not a version bump over `v0.24.0`; it is the first release whose promise includes third-party installation, independent credentials and models, updates, rollback, privacy, and public qualification.

The owner accepted PD-48 through PD-64 in conversation before this contract was written and later accepted PD-65 through PD-67 during canonical reconciliation. Those decisions are canonical in `DESIGN.md`; this artifact records why the selected implementation direction is defensible and which alternatives were rejected.

**2026-08-21 amendment:** PD-65 supersedes A1-D02, A1-D03, and A1-D05 wherever they described the fork as Aether's permanent or unconditional runtime path. Their original wording remains below as historical rationale. The current decision is upstream-by-default with a release-locked `transitional_fork` mode only while indispensable patches remain, and no new Aether capability may add a downstream-only Hermes core dependency.

## 2. Observed Aether repository state

Source: the current Aether working tree and GitHub repository <https://github.com/DarkArty07/Aether-Agents>.

At inspection time:

- GitHub repository: public, MIT licensed, default branch `main`.
- Community profile health: 100 percent.
- Branch protection: strict required checks `policy` and `pull-request-target`; admins enforced; force-push and deletion disabled.
- Active workflows: Repository Policy, Publish Release, Dependabot Updates, and Pages deployment.
- Latest published Aether release: `v0.24.0`; it has no downloadable release assets beyond GitHub's automatic source archives.
- Public description still said: “One Hermes agent with its identity, reproducible configuration, private runtime skills, and GitHub governance.” This is inconsistent with the accepted three-role public product.
- Two open enhancement issues remained: `#192` (retry/recovery taxonomy) and `#195` (semantic progress beyond heartbeats). Christopher classified both as non-blocking future-minor work.
- `VERSION` remained `0.24.0`; `CHANGELOG.md` contained unreleased policy-hook and TUI-launcher work.
- The checkout already contained uncommitted design amendments and `HERMES_LOCAL_PATCHES.md`. The contract MUST NOT cause workers to discard, hide, or overwrite that pre-existing work.
- Existing deterministic tests executed during contract authoring: 19 tests passed in 4.005 seconds. They cover the local Morfeo launcher and policy-hook synchronization, not public package installation or release qualification.
- `git diff --check` passed before the contract artifacts were created.

### Gap demonstrated by the tracked files

- `home/config.yaml.template` contains Christopher-specific provider/model assumptions and toolsets inconsistent with the accepted public product.
- `home/SOUL.md` is a generic Hermes identity, not the tested Morfeo/Supervisor/Implementer set.
- `scripts/aether_tui.py` validates an already-existing repository-local venv and private profile layout; it does not install a public product.
- `.gitignore` and CI prohibit tracking the live profiles that actually implement the three roles.
- `README.md`, R4, and R13 explicitly say Aether does not fork, vendor, or patch Hermes, while the running system depends on downstream fixes.

Conclusion: the current repository is valuable design and evidence, but it is not the public artifact promised by PD-48.

## 3. Observed Hermes dependency state

### Runtime actually tested

The local Aether runtime resolves Hermes from:

```text
home/.venv-hermes/src/hermes-agent
```

Observed package version: `0.20.1`.

The checkout contained local changes and was behind current upstream. `HERMES_LOCAL_PATCHES.md` recorded six downstream lines with corresponding upstream pull requests:

- <https://github.com/NousResearch/hermes-agent/pull/91180> — open, merge state clean at inspection;
- <https://github.com/NousResearch/hermes-agent/pull/89590> — open;
- <https://github.com/NousResearch/hermes-agent/pull/91211> — open, blocked;
- <https://github.com/NousResearch/hermes-agent/pull/91220> — open, blocked;
- <https://github.com/NousResearch/hermes-agent/pull/89688> — open;
- <https://github.com/NousResearch/hermes-agent/pull/91266> — open, blocked.

Current upstream evidence inspected:

- repository: <https://github.com/NousResearch/hermes-agent>;
- latest GitHub release observed: `v2026.8.18`, “Hermes Agent v0.20.4 (2026.8.18)”;
- upstream `main` observed at `533886c8b8eb67ff8b389b7f48e7d5e5d9c575b9` on 2026-08-21 UTC.

The contract deliberately does not pin that mutable observation as the eventual 1.0 base. Implementation must select a current stable upstream tag, reconcile every patch, qualify it, and freeze the exact refs before the RC.

### Upstream package facts

Local `pyproject.toml` showed:

- distribution name `hermes-agent`;
- version `0.20.1` in the tested checkout;
- Python `>=3.11,<3.14`;
- MIT license and Nous Research authorship;
- console scripts `hermes` and `hermes-agent`;
- many exact core dependency pins and self-references to `hermes-agent[...]` in optional dependency groups.

This supports PD-61: renaming the downstream distribution would create a broad metadata fork unrelated to Aether's actual compatibility patches. Building the original package and publishing verified assets from the downstream GitHub Release keeps the patch delta smaller and attribution clearer.

## 4. Hermes-native distribution capability

Authoritative documentation inspected:

- <https://hermes-agent.nousresearch.com/docs/user-guide/profile-distributions>
- <https://hermes-agent.nousresearch.com/docs/reference/profile-commands>

Observed capabilities:

- `hermes profile install <source>` supports local directories, Git URLs, `owner/repo`, and GitHub shorthand.
- A distribution manifest may describe requirements, config, SOUL, AGENTS, skills, hooks, plugins, and MCP servers.
- Credentials, sessions, memories, user profile, and usage data are not distributed.
- Installed distributions retain origin metadata and support check/update.
- Updates preserve user-owned config/state and warn about customized file conflicts.

Observed limitation relevant to Aether:

- The native unit is one profile distribution. Aether is a coordinated set of three profiles, one shared policy, one compatible lock-selected Hermes runtime, project boards, and a service lifecycle.
- Remote Git install follows a repository/default branch and the first release did not support immutable `@ref` pinning.

Conclusion: Aether should reuse native profile semantics and file formats inside its managed bundle, but a small fleet manager is still required. Building a fourth orchestration framework would be wrong; managing a three-profile product release is the missing product layer.

## 5. Python CLI distribution evidence

### Name availability

PyPI JSON endpoints were checked at contract time:

- `aether-agents`: HTTP 404;
- normalized `aether_agents`: HTTP 404;
- `aether`: HTTP 200 and owned by an unrelated geospatial project.

PyPI normalizes hyphens and underscores, so `aether-agents` and `aether_agents` are one namespace. Availability is not ownership until publication; PD-57 includes a review trigger if the name becomes unavailable.

### uv tool behavior

Authoritative documentation:

- <https://docs.astral.sh/uv/guides/tools/>
- <https://docs.astral.sh/uv/concepts/tools/>
- <https://docs.astral.sh/uv/reference/storage/>

Observed local uv: `0.12.3`.

Relevant behavior:

- `uv tool install` installs commands from a Python package into a persistent isolated environment and exposes executables on `PATH`.
- `uv tool upgrade` can independently upgrade an installed tool while preserving its install constraints.
- users can always recreate or change their tool environment.

Conclusion: `uv tool install aether-agents` is a strong public entry point, but Aether cannot honestly claim it can prevent a user from independently upgrading the manager. PD-63 therefore requires detection and reconciliation, not impossible enforcement.

## 6. PyPI publication evidence

Authoritative documentation:

- <https://docs.pypi.org/trusted-publishers/>
- <https://docs.pypi.org/trusted-publishers/using-a-publisher/>
- <https://docs.pypi.org/trusted-publishers/security-model/>
- <https://docs.pypi.org/attestations/>

Trusted Publishing uses GitHub Actions OIDC to mint short-lived project-scoped credentials. PyPI recommends:

- a dedicated trusted workflow;
- job-level `id-token: write`;
- a protected GitHub environment;
- a minimal publication job that consumes distributions produced by a separate build job;
- no long-lived PyPI token.

Pending publishers can create a project on first trusted publication. Configuring the publisher and GitHub environment is a protected external owner action; the contract can prepare and verify workflow files but cannot claim the external trust relationship exists before Christopher configures it.

## 7. Material decisions and alternatives

### A1-D01 — Public stable product, not design release

**Decision**: `v1.0.0` means a third party can install, configure, use, update, recover, and remove the supported product.

**Why**: another documentation-only tag would not satisfy the owner's stated portfolio or user objective.

**Rejected**: label the accepted R0-R13 design `1.0.0`. It would misrepresent a local-only installation as public product maturity.

### A1-D02 — Qualified downstream fork (superseded as the permanent default by PD-65)

**Historical decision**: maintain a minimal public downstream and continue upstreaming generally useful fixes.

**Current disposition**: retain the fork only as a bounded transition. Each release targets a stable upstream tag and uses the fork only if its lock names indispensable residual patches and their retirement gates.

**Why**: core Aether guarantees currently depend on six changes outside upstream releases. Waiting gives upstream scheduling authority over Aether; silently using local patches destroys reproducibility.

**Rejected**:

- wait indefinitely for every PR;
- weaken Aether's guarantees to match unqualified upstream behavior;
- create a permanently divergent general-purpose Hermes fork.

### A1-D03 — Separate repositories (amended by PD-65)

**Current decision**: `Aether-Agents` owns the product and all Aether-specific capability. `DarkArty07/hermes-agent` owns only the temporary downstream patch line while a release still selects `transitional_fork`; steady-state runtime ownership remains upstream.

**Assumption**: preserving upstream history and package identity reduces maintenance and makes Aether's actual product layer inspectable.

**Rejected**: vendor Hermes into Aether or turn the fork itself into the Aether product.

### A1-D04 — Packaged CLI on PyPI

**Decision**: `aether-agents` on PyPI, executable `aether`, normally installed with uv.

**Why**: the owner wants a polished portfolio precedent and a user-grade first-run experience. A source clone is useful for contributors but not the primary product path.

**Rejected**:

- manual installation of three profile distributions;
- canonical `curl | bash` bootstrap;
- container-first distribution;
- fork-integrated monolith.

### A1-D05 — GitHub Release downstream artifacts (conditional under PD-65)

**Current decision**: when a release selects `transitional_fork`, build the original `hermes-agent` wheel/sdist from the downstream and publish them as verified GitHub Release assets. In normal `upstream` mode, lock and verify the stable upstream source archive and build the original distribution in a controlled environment.

**Why**: PyPI's `hermes-agent` namespace belongs to upstream and renaming would require unrelated metadata divergence. A GitHub asset can retain the original distribution name while remaining pinned and auditable.

**Rejected**:

- upload a renamed runtime package to PyPI;
- install from mutable fork `main`;
- build from a Git checkout on every user machine;
- embed Hermes source or wheel bytes inside `aether-agents`.

### A1-D06 — Two setup interfaces, one engine

**Decision**: guided `aether setup` and declarative `aether setup --config` share one parser/planner/validator/effect engine.

**Owner delegation**: Christopher delegated this choice.

**Assumption**: humans need guided discovery; CI and reproducible support need declarative input. Two independent implementations would drift.

### A1-D07 — Provider-independent descending models

**Decision**: public setup records user-selected Hermes provider/model identifiers for each role. The methodology descends from most capable to least expensive sufficient model. The same model may fill all roles.

**Rejected**: ship Christopher's private routing infrastructure, private model identifiers, or any other owner-specific default binding.

### A1-D08 — Linux native and WSL2

**Decision**: Linux native and WSL2 only; Ubuntu 24.04 LTS native and WSL2 are reference lanes, Garuda/Arch is the dogfood lane.

**Why**: this is the tested product environment and keeps the support claim honest. WSL2 is Linux behavior only when systemd and the Linux filesystem are used.

**Rejected**: claim Windows-native/macOS support because Hermes itself has broader support.

### A1-D09 — XDG and per-project isolation

**Decision**: runtime and user state use XDG boundaries. Portable project identity and contract artifacts are tracked; board/workspace/runtime state is local. One project identifier maps to one board and workspace root.

**Why**: repository-local private homes made the current product non-portable and risk mixing product source with personal state.

### A1-D10 — Explicit update and mismatch recovery

**Decision**: `aether update` stages and switches a coherent product set. External uv changes are detected and reconciled; they are not silently activated.

**Rejected**: automatic updates, automatic upstream sync, or pretending a user cannot alter their own uv environment.

### A1-D11 — TUI required, messaging optional

**Decision**: the local TUI is the qualified 1.0 user interaction surface. The managed gateway exists because the board dispatcher needs it. Messaging adapters remain Hermes capabilities but are not Aether 1.0 release claims.

**Assumption**: qualifying every messaging adapter would expand the release objective without improving the core public product guarantee.

### A1-D12 — Git required, GitHub is the qualified forge

**Decision**: Git is required. Local Aether work can run without a remote. GitHub is the only qualified 1.0 surface for remote issues, pull requests, and releases; `gh` is checked only when that effect is requested.

**Owner delegation**: this is a bounded implementation decision derived from the accepted GitHub and public-product objective.

**Rejected**: require GitHub authentication before local setup, or claim untested GitLab/Bitbucket support.

### A1-D13 — No telemetry

**Decision**: no Aether telemetry; local redacted logs only.

**Why**: contracts and repositories can contain highly sensitive material, and no demonstrated 1.0 need justifies collection.

### A1-D14 — RC before stable

**Decision**: public `v1.0.0-rc.N`, public-path deterministic and live qualification, then explicit owner authorization for `v1.0.0`.

**Rejected**: tag stable directly from a local editable checkout.

### A1-D15 — Known limitations remain honest

**Decision**: `#192` and `#195` are non-blocking future-minor issues. Aether does not equate heartbeat with semantic progress or a technical failure count with all logical attempts.

## 8. Technical assumptions delegated to implementation

These are bounded choices Supervisor may settle during executability analysis if it records the decision and preserves the contract:

- exact current stable upstream Hermes tag selected as the downstream base;
- exact downstream release tag naming;
- exact minimal Python CLI dependency set, with the requirement that doctor/rollback survive a broken runtime;
- exact atomic pointer mechanism where Linux/WSL2 semantics are verified;
- exact user-service unit content and activation command;
- exact realistic qualification project and public provider, subject to the owner credential/spend gate;
- documentation generator/theme, provided GitHub Pages and all required content remain maintainable and reproducible.

No worker may decide a question shared by sibling units independently. Supervisor owns these decisions before fan-out.

## 9. Impact scan

Direct contradictions were found in:

- `README.md`: “Aether does not fork, vendor, or patch Hermes.”
- `specs/r4-hermes-boundary/spec.md` FR-403: forbids modifying Hermes core.
- `specs/r13-synthesis-and-release/plan.md`: says the project is configuration and prompts layered on an existing unmodified runtime.
- `specs/r12-models-and-economics/spec.md`: binds Christopher's private model identifiers and local Router.

Affected ownership domains:

- R4 — foundation/downstream boundary;
- R9 — public state and recovery;
- R10 — supply-chain, publication, and privacy protections;
- R11 — public artifact evidence;
- R12 — public model methodology;
- R13 — implementation entry and release synthesis.

R8 must be checked for workspace-path consequences, but its one-worktree-per-unit and non-rewrite principles do not change. R7's `#192`/`#195` limitations remain future work and do not reopen the accepted three-role topology.

## 10. Evidence limitations

- No public Aether package exists yet.
- No downstream GitHub Release asset has been built or verified.
- No PyPI Trusted Publisher has been configured.
- No clean native Ubuntu or WSL2 installation has run.
- No public-provider RC flow has run.
- Existing 19 passing tests prove only the current launcher and policy synchronization baseline.

During contract validation, two read-only terminal commands that only parsed the new files and validated JSON Schemas were denied with the message reserved for stopping or restarting the live gateway, although neither command requested a service effect. Morfeo treated the denial as authoritative and did not route around it. This is a reproducible candidate policy false positive, not validation success; A1-FR-091 and A1-SC-013 require a bounded regression. It also requires a GitHub issue when the external issue-writing gate is authorized.

The contract labels these as work and release gates. It does not promote them to evidence because the design is accepted.
