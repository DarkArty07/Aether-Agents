# Aether 1.0 Productization Research and Decision Record

**Contract**: [`spec.md`](spec.md)
**Observed**: 2026-08-20T22:47:52-06:00
**Repository commit inspected**: `00260254b497dc07f0c7d1922831612cc10114a5`

### Owner amendment — conversational greenfield intake and observer startup (2026-09-23)

**Current owner intent:** the human enters an existing new folder, runs `git init` explicitly, then `aether init`, then `aether`. The last command must open Morfeo on that empty/unborn repository for an initial conversation, not create principles or ask the owner to choose internal boards, agents, commits or workflows. Morfeo discovers the project intent and its testing standard with the owner and subsequently handles warranted setup and execution. The owner also requests a permanent correction of the observed MCP/plugin startup deadlock rather than a longer timeout or perpetual loss of Context7. This supersedes PD-52 and A1-FR-046/047/052 wherever they previously attributed Git, constitution or board creation to `init`; the previous wording is preserved in Git history, not replayed as current requirements.

**Upstream first, exact inspected source:** GitHub Spec Kit `github/spec-kit` main commit `583b1a5a0e10e725029ec1b34b65c011582fef17`, read from the pinned raw files on 2026-09-23. `templates/commands/constitution.md:21-30,75-99` limits constitution work to governance and derives user-supplied values from conversation/repository context; `templates/commands/clarify.md:80-127,182-196` inspects interaction, identity, failures and testable acceptance, then records accepted answers in the owning spec. These are methodological inputs only. Spec Kit's interactive command limit/next-human-step is not our unattended product mechanism; the Aether gap is the actor who continues after the owner has provided intent, plus the temporary ability to converse before the new project has guidance or a Git commit. No Spec Kit code is vendored or invoked as an implicit initializer.

**Current Aether/runtime evidence:** the installed rc8 observer's `_resolve_category_normalizer` imports `model_tools` while registering under Hermes's plugin discovery lock. The selected maintained-fork source's `model_tools.py:245-250` calls `discover_plugins()` during import, whereas `tools/registry.py:1171-1174,1262-1263` exposes the registry-owned lookup without importing the discovery module. A contemporaneous rc8 backend thread dump (private diagnostic, not published here) captured the MCP thread waiting for `model_tools` while holding plugin discovery, and the builder holding that module import while waiting for plugin discovery. Disabling one configured MCP server allowed a new backend to reach readiness but is an operational workaround, not proof that a code fix or model reply passed. The maintained fork need not change for this candidate; controlled concurrency and an installed MCP-enabled canary remain required.

**Decisions, assumptions and rejected alternatives:** reuse the supported native Hermes Project creation interface from the selected runtime via a bounded manager subprocess, rather than writing Hermes's DB directly or importing Hermes into the minimal manager (PD-69). Assumption: the exact native CLI remains available in the selected release and returns a verifiable same-profile Project/path; if not, refuse initialization rather than create a second registry. Reuse zero/one/many exact-path semantics and make partial failure retry-safe rather than deleting newly created state blindly. Defer the board until a real contract handoff, as the owner asked for conversation only and the existing handoff already provisions an isolated board; no board is needed to chat. Do not generate a placeholder constitution, `AGENTS.md`, testing standard, empty commit, remote, or Git repository. The observer fix uses the lightweight native registry plus the accepted Hermes shared-metrics taxonomy and marks missing native capability incomplete rather than inventing exact categories. Raising 600 seconds, optimizing SessionDB, disabling observation, and silently losing Context7 are not the requested correction. These choices do not authorize release activation, publication, credentials or spend.

### Source consolidation outcome — owner-authorized operation

The canonical source is now `DarkArty07/aether-hermes`, default branch `aether-main`. Renaming the existing fork preserved its repository identity and all historical refs; its old default branch is explicitly `historical-upstream-2026-08-19`. The local runtime's 39-path delta was preserved at fork commit `c3f275430` and identified by `96f3f59cc`; 9,348 source entries were hash-verified and the existing focused runner passed 453 tests with one Windows-only skip. No upstream checkout was downloaded or upgraded. Five incompletely attributed paths remain explicitly retained as preservation state, not silently certified as product requirements. See the fork's `AETHER_FORK.md` and Aether issue #348.

Inherited scheduled/publication Actions are intentionally disabled on the fork; local evidence is not described as GitHub CI. Distribution packaging, an Aether-specific CI setup, version-lock adoption and future frontend adaptations are not delivered by this source consolidation. Existing installer/release locks remain unchanged. The root AGENTS guidance amendment was refused by the live instruction-file approval guard (#315) and was not retried through another write surface; the accepted DESIGN source policy remains authoritative over that older guidance.

## 1. Why this contract exists

Aether's three-role method is functioning in Christopher's local environment, but the public repository still distributes a design and a few reconstruction pieces rather than the product that was tested. `v1.0.0` is therefore not a version bump over `v0.24.0`; it is the first release whose promise includes third-party installation, independent credentials and models, updates, rollback, privacy, and public qualification.

The owner accepted PD-48 through PD-64 in conversation before this contract was written, accepted PD-65 through PD-67 during canonical reconciliation, PD-68 on 2026-08-21 for pre-1.0 contract observation, and PD-69 on 2026-08-23 for the single-distribution modular project structure. Those decisions are canonical in `DESIGN.md`; this artifact records why the selected implementation direction is defensible and which alternatives were rejected.

**2026-08-21 amendment (historical):** PD-65 supersedes A1-D02, A1-D03, and A1-D05 wherever they described the fork as Aether's permanent or unconditional runtime path. Their original wording remains below as historical rationale. The transition-only policy stated here — upstream by default with a release-locked `transitional_fork` mode only while indispensable patches remain — was itself superseded by the 2026-09-07 maintained-fork amendment and by the 2026-09-15 RC reconciliation below; no new Aether capability may add a downstream-only Hermes core dependency.

### Owner amendment — maintained fork (2026-09-07)

- **Need and authority:** the owner explicitly chose a maintained Hermes fork for runtime ownership, future separately scoped frontend adaptations, and inclusion in Aether distribution, without updating to upstream now.
- **Decision:** DESIGN PD-49/61/64/65 own the new long-lived-fork source policy. The 2026-08-21 transition-only decision above is historical and superseded; the earlier A1-D02/D03/D05 implementation details are not automatically reapproved.
- **Evidence:** GitHub identifies `DarkArty07/hermes-agent` as a public fork of `NousResearch/hermes-agent`. Its observed main was `2163f7f8ca82f7c892c7e815dadd80a1486cc194`; the locally inspected framework base was `0b288979e2322c02ab42c05f1e183bb31cfa5aa9` with additional local changes. These are distinct observations, not a selected distribution candidate. The framework license permits modification and redistribution subject to retaining the MIT copyright and permission notice; bundled dependencies and frontend assets need their own license review.
- **Alternatives and trade-off:** upstream-only and a compulsory temporary-patch policy no longer meet the owner's intended product control. A maintained fork gives that control but transfers integration, security maintenance, regression testing and release support to Aether. Keeping Aether-specific changes localized reduces that burden without forbidding justified core changes.
- **Owner clarification:** the initial source is the actual local Hermes installation and its local changes, not the older remote fork branch. Remote fork main was dated 2026-08-19; the local base commit was dated 2026-08-28. The observed local delta included 34 tracked modified paths and five untracked paths; this inventory is not blanket acceptance of every change. Reusing the existing GitHub fork is a hosting proposal only. Preserve source/build state privately, classify changes and qualify the candidate before publication; exclude credentials and user state.
- **Pending design:** reuse or rename the existing fork, maintained branch/version scheme, upstream integration and contribution rules, source-mode/schema migration, package composition, and treatment of permanent features versus retireable fixes. These are recommendations to settle, not implied execution authority.
- **Bounded impact:** A1 source policy and release design are reopened for the fork transition. The current encoded baseline, active runtime, frontend, historical tests and release artifacts are not changed. PD-51 release qualification and privacy/isolation requirements remain applicable. Repairing the current TUI incident remains a distinct bounded objective.

### RC reconciliation — maintained fork, XDG layout, update boundary and the `1.0.0rc1` milestone (2026-09-15)

- **Need and authority:** Objective Contract `oc_3397f9f05d780f8e@v1` (owner-authorized) directs the `1.0.0rc1` release candidate; its in-scope item 1 directs the reconciliation of the A1 owning artifacts with the contract's accepted decisions.
- **Decision (recorded in `spec.md`, `plan.md` and `contracts/cli.md`):** release-lock `schema_version` 4 with `hermes.source_mode` `maintained_fork`, bound to `https://github.com/DarkArty07/aether-hermes`, branch `aether-main`, exact commit, source-tree digest, artifact closure and provenance. The retired `transitional_fork` mode is refused for new preparation, and `.patch` files are never replayed onto an active release. Immutable release code and Graphify components live under the Aether XDG data root while every mutable Hermes home and all product state stay under the Aether XDG state root. `aether update` — including its `--local` local-candidate route with a non-mutating preview and explicit interrupting activation — is the sole supported promotion/activation boundary, with transition recovery and a state-preserving rollback that never rolls user state backward. The milestone identity is package `1.0.0rc1` with annotated tag and GitHub prerelease `v1.0.0-rc.1`, `release_impact = major`, `release_action = publish`, `release_channel = prerelease`.
- **Why the earlier A1 design changed:** the 2026-08-21 transition-only policy assumed upstream retirement was the goal; PD-65 replaced it with a maintained fork. The 2026-09-07 amendment deliberately left the source-mode/schema migration, layout reconciliation and release identity open. This amendment closes those gaps and introduces no new product principle.
- **Bounds:** the RC is a pre-stable milestone. It is not stable `1.0.0`, not a PyPI or other package-index publication, and not a WSL2-qualified result; issue #261 stays open with the stable-1.0.0, PyPI/OIDC and WSL2 gates outstanding. The A1-D02/D03/D05 wording below stays as historical rationale and is not implementation instruction.
- **Evidence:** the fork repository, branch, candidate revision and the Hermes distribution identity used by the reconciliation were inspected read-only, as was the installed XDG data/state split. Machine paths and live-state values are deliberately absent from public artifacts.

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

**Historical decision (superseded by the 2026-09-15 RC reconciliation)**: `Aether-Agents` owns the product and all Aether-specific capability. `DarkArty07/hermes-agent` owns only the temporary downstream patch line while a release still selects `transitional_fork`; steady-state runtime ownership remains upstream. The current decision is `Aether-Agents` owning the product with `DarkArty07/aether-hermes` (`aether-main`) as the maintained release-locked runtime source, and deliberate upstream adoption rather than mandatory retirement.

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

**Historical decision (superseded by the 2026-09-15 RC reconciliation)**: when a release selects `transitional_fork`, build the original `hermes-agent` wheel/sdist from the downstream and publish them as verified GitHub Release assets. In normal `upstream` mode, lock and verify the stable upstream source archive and build the original distribution in a controlled environment. The current decision keeps the original distribution name and identity, builds it from the locked maintained-fork revision (or from a deliberately selected upstream source), and attaches it to the reviewed release bundle rather than publishing a renamed package.

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

### A1-D13 — No remote telemetry; bounded local observation only

**Current decision**: Aether ships no remote telemetry, hosted analytics, remote ingestion, or raw-content observation. PD-68 permits only the local, metadata-only, fail-open contract observer owned by specification 002; local redacted operational logs remain permitted.

**Why**: contracts and repositories can contain highly sensitive material. The pre-1.0 diagnosis requirement is satisfied locally without transmitting evidence or widening data collection.

### A1-D14 — RC before stable

**Decision**: public `v1.0.0-rc.N`, public-path deterministic and live qualification, then explicit owner authorization for `v1.0.0`.

**Rejected**: tag stable directly from a local editable checkout.

### A1-D15 — Known limitations remain honest

**Historical decision**: `#192` and `#195` were classified as non-blocking future-minor issues. Aether does not equate heartbeat with semantic progress or a technical failure count with all logical attempts.

**Superseded in part on 2026-08-21 by PD-68**: `#192` remains non-blocking; `#195` is now a 1.0 release prerequisite owned by `../002-aether-contract-observation/`. The reason is the owner's requirement to diagnose repeated system failures from deterministic contract-level duration, participant/action, tool-use, and flow evidence before stable release.

### A1-D16 — One modular distribution, dual isolated installation

**Decision**: keep Aether-specific code in the `Aether-Agents` monorepo and publish one versioned `aether-agents` wheel. Install the exact same staged wheel in the isolated manager environment and with `--no-deps` in the versioned Hermes runtime. The manager owns the public `aether` CLI; Hermes discovers only `aether_agents.observation.capture.hermes_plugin` through `hermes_agent.plugins`.

**Why**: one source, distribution, and version prevent manager/observer drift while an explicit import boundary preserves doctor and rollback when Hermes is broken. The locked Hermes loader natively supports module entry points exposing `register(ctx)`, so no core patch or profile-local source copy is needed.

**Artifact identity**: release-lock schema `4` binds the immutable maintained-fork source identity (repository, branch, exact commit, source-tree digest, artifact closure and provenance) plus the pre-build tuple (distribution, package version, tag, commit, Python range, observer entry point), the digest of the wheel-packaged hash-bound observer dependency closure, and a deterministic digest of the locally materialized Hermes Git tree. That tree digest is deliberately separate from remote source-artifact digests. External release provenance and the local transition record bind the final wheel filename/SHA-256 because a wheel cannot contain its own final digest without circularity. The validated lock bytes are retained per release; activation compares their digest, installed-file fingerprints, dependency versions, and source-tree identity across both environments.

**Rejected**: a second observer package/repository/version, copied per-profile plugin directories, mutable `PYTHONPATH` installation, a new observer daemon, or importing Hermes into manager modules.

## 8. Technical assumptions delegated to implementation

These are bounded choices Supervisor may settle during executability analysis if it records the decision and preserves the contract:

- the exact maintained-fork revision used by a release and its accepted-change ledger coverage at that revision (with the deliberately selectable upstream alternative);
- exact Hermes release tag naming for the maintained-fork artifacts;
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
