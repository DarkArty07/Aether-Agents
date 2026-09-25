# Changelog

## 1.0.0rc11 — local-only corrective release-lock compatibility bridge

Package identity `1.0.0rc11` / display `1.0.0-rc.11` / local annotated tag identity
`v1.0.0-rc.11`; `release_impact=patch`, `release_action=prepare`,
`release_channel=prerelease`. Issue #515. This candidate teaches the lifecycle to read
release-lock schema 4 and schema 5. Schema 4 keeps its historical meaning and
carries no Hermes extras. Schema 5 requires `hermes.extras`, initially only the
closed value `["mcp"]`. RC9 still emits schema 4, so an RC8 manager can install
it. Preparing a schema 5 target exports the declared extra from the authenticated
Hermes `uv.lock`. This is not Morfeo MCP, not a Hermes fork change, and not a
public feature claim. No tag is pushed or published.

- Duplicate, unknown, or non-canonical extras are refused.
- A schema 4 reader refuses a schema 5 lock before a release directory is created.
- The manager distribution does not depend on the MCP SDK.


## 1.0.0rc8 — local-only final instruction candidate

Package identity `1.0.0rc8` / display `1.0.0-rc.8` / local annotated tag identity
`v1.0.0-rc.8`; `release_impact=patch`, `release_action=prepare`,
`release_channel=prerelease`. This candidate follows the RC7 compatibility
bridge and restores the #495 Morfeo SOUL and canonical contract procedures.
It is not a claim of live activation or empirically improved agent behavior;
the selected runtime and state preservation require managed-cutover evidence.
Neither tag is pushed or published, and stable/PyPI/WSL2 gates remain open.

- Morfeo conducts resumable objectives through a project-local Objective Plan in
  `.aether/plans/`, using the existing planning and result-reception procedures.
  Plans preserve the destination, current route, verified results and failed
  approaches without replacing canonical obligations or adding a workflow engine.
- Continuation is distinguished from acceptance: a remaining defect does not by
  itself justify another attempt, and a new session or contract does not reset
  the objective's history or convergence boundaries. Simple bounded work remains
  free of mandatory planning ceremony.
- Documented the owner-selected tool recipe for all three roles. These are local
  user choices, not new mandatory packaged tool or model defaults.
- Resource, documentation and loader checks establish structural consistency,
  not empirical improvement in agent behavior. Live adoption still requires a
  coherent managed update; no existing release/tag is changed by this entry.

## 1.0.0rc7 — local-only compatibility bridge

Package identity `1.0.0rc7` / display `1.0.0-rc.7` / local annotated tag identity
`v1.0.0-rc.7`; `release_impact=patch`, `release_action=prepare`,
`release_channel=prerelease`. A tag is created only after reviewed commits are
reachable from `main` and candidate gates pass; it is never pushed or published.
Neither source nor tag proves live activation. This transitional release carries the #497 target-owned profile
transfer repair while retaining RC6-identical Morfeo SOUL and canonical contract
skills with matching resource tests. It does **not** activate the #495 guidance;
that belongs to the following final candidate. Operator configuration and other
mutable state must be preserved. Passing source checks is not live activation or
behavioral acceptance; RC6 and its release identity remain immutable.

- Lifecycle preparation binds SOUL and canonical skill bytes to the exact
  candidate wheel and has that candidate's installed manager materialize its
  profile bundle. Release validation checks the immutable manifest, wheel and
  target manager together instead of comparing target resources with the
  currently executing manager's version. Cross-version update and rollback
  preserve operator-owned profile configuration and local state.

## 1.0.0rc6 — release candidate (pre-stable, local-only activation candidate)

The release identity is package version `1.0.0rc6`, display version `1.0.0-rc.6`, annotated tag
`v1.0.0-rc.6` (`release_impact=patch`, `release_action=prepare`, `release_channel=prerelease`);
`VERSION` remains the single product-version source.

- This candidate is local-only: one local annotated tag `v1.0.0-rc.6` is prepared locally on
  accepted `main` and is never pushed, published, or released to GitHub in this objective.
- Predecessors: rc1–rc5 remain immutable history; the local rc.2, rc.3, rc.4 and rc.5 candidate
  tags and activation history remain immutable non-accepting history; `1.0.0rc1` /
  `v1.0.0-rc.1` remains published, byte-immutable and rejected, and must not be activated.
- Mixed-version lifecycle: the immutable target `record.json` owns the persisted active-record
  field shape, so the source manager no longer serializes its own defaults into an older target's
  pointer; optional-field absence versus explicit null and unknown keys are preserved.
- Pre-mutation target validation: the proposed active record is validated through the exact
  target's reader in an isolated subprocess (`-P -s`, target-root working directory, stripped
  `PYTHON*` environment, in-runner `aether_agents.__file__` provenance assertion) before any
  pointer or projection byte moves. An unavailable or out-of-bounds target projection plan
  refuses the transition instead of falling back to source-owned bytes.
- Byte-exact compensation: a failed transition restores the previously captured active-record
  bytes and its paired selector rather than reserializing through a failing release class.
- Target-owned projections: the authenticated target release's own code determines launcher,
  Desktop, WSL and service projection bytes, and the parent validates allowlisted destinations
  and digests before applying them and re-validates from the selected target afterwards. The
  service-unit version discriminator is brand-agnostic (no exact-version equality).
- Bounded reconciliation: the reserved `aether reconcile --to active [--dry-run] [--yes]
  [--json]` surface is implemented for the already active, authenticated release. Its preview is
  non-mutating, it never selects another release, installs packages or restarts a service where
  read-only reconciliation suffices, and `--to installed` remains explicitly unsupported with
  `UNSUPPORTED_RECONCILE_MODE`. An active release that cannot authenticate itself is refused
  before mutation.
- Passive observer startup: registration and synchronous native hooks install hooks/tools and
  record bounded events without replaying retained journal history or holding the maintenance
  lock. Retained bindings restore asynchronously through the existing plugin worker with one
  validated retained index per catch-up snapshot; segment enumeration failures and stale
  snapshots are reported as content-free health counters and incomplete coverage instead of a
  guessed trace.
- Native/CLI query parity under contention: known bounded catch-up conditions return the fixed
  public codes native `AETHER-OBSERVE-BUSY` / `AETHER-OBSERVE-CATCHUP-INCOMPLETE` and CLI
  `STATE_BUSY` / `CATCHUP_INCOMPLETE`, while genuine unreadable state stays fail-closed as
  `STATE_UNREADABLE`/`AETHER-OBSERVE-STATE-UNREADABLE`. A retryable error is not presented as a
  successful or fresh summary, and the existing callback/reduction gates and 22-callback
  qualification lock are unchanged.
- Launch: the packaged launcher clears inherited transport selectors (`HERMES_PYTHON`,
  `HERMES_PYTHON_SRC_ROOT`, Hermes RPC/gateway/session and desktop state, `PYTHON*`,
  `VIRTUAL_ENV`, task/board routing) and then binds the target release's interpreter, source
  root, TUI directory, Morfeo profile and exact project, so a nested old TUI cannot silently
  start the old backend. Fresh and `--resume latest` launches select the exact backend from a
  clean or contaminated parent environment, an unqualified or damaged release venv fails closed
  with `ActivationError`, and launches create no npm/build artefacts and leave the locked
  `hermes-source` tree bit-for-bit unchanged.
- Public startup, default-selection and recovery guidance: how `aether` selects an initialized
  project from the current directory, how `--project PATH` (or `AETHER_PROJECT_ROOT`) overrides
  that selection, the fresh and Continue actions, `--resume latest`, visible ambiguity instead of
  name/recency inference, and optional personal Bash/Zsh and Fish defaults with their matching
  removal commands. Aether never silently writes a personal shell preference.
- Reconciled canonical surfaces: the CLI contract, the A1 specification, the observation
  specification, the lifecycle/observation/CLI/limitations guides and the capability registry
  describe the frozen behavior above; `docs/reference/capabilities.md` is regenerated from
  `docs/capabilities.toml`.
- Registered tracked contract file `.aether/objective-contracts/oc_b5926701207812e8/v1.md`,
  the observation module and regression paths added by this objective, and its focused suites in
  `.github/workflows/policy.yml`.
- Pinned maintained-fork runtime source unchanged: `DarkArty07/aether-hermes` `aether-main`
  revision `aed6591a69f453a1867b73628603e7b53ba40ffc` (source-tree digest
  `cc1ebf94ad167979951e7b956ef3a8c448e96fd3389c93cddf60f8f883bb5ce7`); no Hermes-fork change.
- This is a pre-stable release candidate. It is not stable `1.0.0`, no PyPI or other
  package-index publication occurs, WSL2 (and any macOS/Windows lane) is unverified and
  recorded as such, and issue #261 remains open with the deferred stable, PyPI/OIDC and
  WSL2 obligations explicit. Mixed-version qualification, the local annotated tag, local
  activation, live canaries and issue closeout belong to the same objective's later units; this
  entry records the release identity, status, guidance, capability reconciliation, manifest and
  oracle updates performed here.

## 1.0.0rc5 — release candidate (pre-stable, local-only activation candidate)

The release identity is package version `1.0.0rc5`, display version `1.0.0-rc.5`, annotated tag `v1.0.0-rc.5`
(`release_impact=patch`, `release_action=prepare`, `release_channel=prerelease`);
`VERSION` remains the single product-version source.

- This candidate is local-only: one local annotated tag `v1.0.0-rc.5` is prepared locally on
  accepted `main` and is never pushed, published, or released to GitHub in this objective.
- Predecessors: rc1–rc4 remain immutable history; the local rc.2 and rc.3 candidate tags and activation
  history remain immutable non-accepting history; `1.0.0rc1` / `v1.0.0-rc.1` remains published, byte-immutable
  and rejected, and must not be activated; rc4's rejected doctor oracle is not repaired and rc4 is not
  reactivated.
- Hermes-owned gateway service boundary: Aether no longer writes or byte-owns
  `hermes-gateway-morfeo.service`, and does not include its exact bytes in projection digests. Fresh setup,
  update, rollback, and forward reactivation invoke the selected release's Hermes CLI
  (`hermes --profile morfeo gateway install --force --no-start-now --start-on-login`) to create or refresh the
  unit before restarting it. Normal uninstall requests removal through Hermes.
- Semantic doctor: `aether doctor` validates the service exists as a regular user unit and semantically selects
  the active `runtime/current` Python, Morfeo profile and home, and active virtualenv, without requiring or
  rejecting `HERMES_TUI_DIR` or comparing incidental Hermes-owned unit bytes.
- Preserved launcher, Desktop, and WSL release-TUI delivery: the packaged `aether` launcher continues to
  export `HERMES_TUI_DIR=<runtime/current>/tui` to the launched Hermes process, and Desktop and WSL actions
  keep targeting the stable `runtime/current/venv/bin/aether` entry point with the exact initialized project
  root and hash-bound release TUI asset. Gateway service operation does not depend on `HERMES_TUI_DIR`.
- Rollback qualification: explicit rollback targets restored coherent `1.0.0rc3` rather than known-defective
  `1.0.0rc4`, followed by forward reactivation of `1.0.0rc5`.
- Pinned maintained-fork runtime source unchanged: `DarkArty07/aether-hermes` `aether-main`
  revision `aed6591a69f453a1867b73628603e7b53ba40ffc` (merge of `#450` and `#461`).
- Reconciled root `AGENTS.md` and release workflow authority comments with the current
  Objective Contract `oc_a7a3cff05e82c148@v1` (reconciling issues #487, #480, #481, #482, and #485).
- Registered tracked contract file `.aether/objective-contracts/oc_a7a3cff05e82c148/v1.md` and
  focused test suite `tests/test_hermes_gateway_service.py` in `.github/workflows/policy.yml`.
- This is a pre-stable release candidate. It is not stable `1.0.0`, no PyPI or other
  package-index publication occurs, WSL2 (and any macOS/Windows lane) is unverified and
  recorded as such, and issue #261 remains open with the deferred stable, PyPI/OIDC and
  WSL2 obligations explicit. Gate measurements, local activation, live canaries, and issue closeout
  belong to the same objective's later units; this entry records the release identity, status,
  guidance, capabilities, and oracle reconciliation performed here.

## 1.0.0rc4 — release candidate (pre-stable, local-only activation candidate)

The release identity is package version `1.0.0rc4`, annotated tag `v1.0.0-rc.4`
(`release_impact=patch`, `release_action=prepare`, `release_channel=prerelease`);
`VERSION` remains the single product-version source.

- This candidate is local-only: the annotated tag `v1.0.0-rc.4` is prepared locally on
  accepted `main` and is not pushed, published, or released to GitHub in this objective.
- Predecessors: the local rc.2 and rc.3 candidate tags and activation history remain immutable
  and are not acceptance; `1.0.0rc1` / `v1.0.0-rc.1` remains published, byte-immutable and
  rejected, and must not be activated.
- Packaged launcher (`src/aether_agents/launcher.py`): bare `aether [--project PATH] [--json]`
  validates project identity and launches Morfeo into the release-owned TUI from packaged manager
  code without importing Hermes or executing checkout scripts; `--json` produces a non-mutating
  launch plan with exact sorted keys (`command`, `cwd`, `hermes_executable`, `hermes_home`,
  `project_id`, `repo_root`, `required_toolsets`, `result`, `tui_dir`). Reserved binding flags
  are rejected and `--resume latest` is preserved (#480).
- Release-owned prebuilt TUI asset and branded projections: candidate preparation builds and
  hash-binds `ui-tui` from the exact maintained-fork commit outside locked `hermes-source`,
  and launcher, service, doctor, update, and rollback agree on `HERMES_TUI_DIR`. Branded
  `Aether` and `Continue Aether` desktop actions target the stable `aether` selector with explicit
  project binding, and Windows Terminal WSL projections are supported (#480, #481).
- Operation-wide Graphify deadline: one monotonic 300-second deadline begins at native
  `KnowledgeStore.update()` entry and remains authoritative through terminal operation record
  and pointer publication. Prepare, validate, and compose consume the remaining time with shared
  cancellation; post-call fences reject late backend completions, and host cancel terminates
  the Graphify process group (#482).
- Pinned the maintained-fork runtime source unchanged: `DarkArty07/aether-hermes` `aether-main`
  revision `aed6591a69f453a1867b73628603e7b53ba40ffc` (merge of `#450` and `#461`).
- Reconciled root `AGENTS.md` with the current Objective Contract `oc_ff82ba151cdf3861@v2`.
- Registered tracked contract files `.aether/objective-contracts/oc_ff82ba151cdf3861/v1.md` and `v2.md`,
  packaged launcher `src/aether_agents/launcher.py`, and projection test suite `tests/test_tui_projections.py`
  in `.github/workflows/policy.yml`.
- This is a pre-stable release candidate. It is not stable `1.0.0`, no PyPI or other
  package-index publication occurs, WSL2 (and any macOS/Windows lane) is unverified and
  recorded as such, and issue #261 remains open with the deferred stable, PyPI/OIDC and
  WSL2 obligations explicit. Gate measurements, local activation, live canaries, and issue closeout
  belong to the same objective's later units; this entry records the release identity, status,
  guidance, capabilities, and oracle reconciliation performed here.

## 1.0.0rc3 — release candidate (pre-stable, local-only activation candidate)

The release identity is package version `1.0.0rc3`, annotated tag `v1.0.0-rc.3`
(`release_impact=major`, `release_action=prepare`, `release_channel=prerelease`);
`VERSION` remains the single product-version source.

- This candidate is local-only: the annotated tag `v1.0.0-rc.3` is prepared locally on
  accepted `main` and is not pushed, published, or released to GitHub in this objective.
- Predecessors: the local rc.2 candidate tag and activation history remain immutable and
  are not acceptance; `1.0.0rc1` / `v1.0.0-rc.1` remains published, byte-immutable and
  rejected, and must not be activated.
- Incorporates accepted observation ingestion, query, resume, flusher and test-synchronization
  work on `main` for issue #417 (PR #471 / PR #472, #476, #477), delivering scalable trace
  ingestion and deterministic test execution under load.
- Pinned the maintained-fork runtime source unchanged: `FORK_COMMIT` in
  `.github/workflows/release.yml` remains the accepted `DarkArty07/aether-hermes` `aether-main`
  revision `aed6591a69f453a1867b73628603e7b53ba40ffc` (merge of `#450` and `#461`).
- Reconciled root `AGENTS.md` and release workflow authority comments with the current
  Objective Contract `oc_a179da8d654aec8b@v1`.
- This is a pre-stable release candidate. It is not stable `1.0.0`, no PyPI or other
  package-index publication occurs, WSL2 (and any macOS/Windows lane) is unverified and
  recorded as such, and issue #261 remains open with the deferred stable, PyPI/OIDC and
  WSL2 obligations explicit. Gate measurements, local activation, #417 live qualification
  and rollback proof belong to the same objective's later units; this entry records only
  the release identity, status, guidance and oracle reconciliation performed here.

## 1.0.0rc2 — release candidate (pre-stable successor to the published-but-rejected rc.1)

The release identity is package version `1.0.0rc2`, annotated tag and GitHub prerelease
`v1.0.0-rc.2` (`release_impact=major`, `release_action=publish`,
`release_channel=prerelease`); `VERSION` remains the single product-version source.

- Rc.2 supersedes `1.0.0rc1` / `v1.0.0-rc.1` as the release candidate eligible for
  activation. The rc.1 annotated tag, its eight asset bytes and its rejection warning are
  unchanged: rc.1 remains published and byte-immutable but rejected, and it must not be
  activated. Rc.2 is not a repair of those published bytes — no asset was replaced and no
  tag was moved — it is the successor artifact that carries the corrected status.
- Reconciled `README.md` — embedded as this distribution's `METADATA` long description —
  with the release status it is part of: it names package version `1.0.0rc2` and the
  annotated prerelease `v1.0.0-rc.2`, states that rc.2 is the candidate eligible for
  activation, and records rc.1 as published, immutable, rejected and not to be activated,
  instead of denying that a release candidate exists.
- Pinned the maintained-fork source this release builds from: `FORK_COMMIT` in
  `.github/workflows/release.yml` is the accepted `DarkArty07/aether-hermes` `aether-main`
  revision `aed6591a69f453a1867b73628603e7b53ba40ffc`, the merge of reviewed `#450`
  (terminal-worker reap, fork PR #14) and `#461` (routed-recovery review-phase preservation,
  fork PR #15 / HLP-427). The earlier pin `7a4fdcd083409c31c09cfa3bfa345354e8576a7e`
  (`#450` only) remains historical evidence and must not be used for an rc.2 bundle;
  `scripts/release_bundle.py` still resolves and validates the exact pinned commit rather
  than a branch tip, and the workflow's fail-closed placeholder discipline, tag/identity
  validation and single release path are unchanged.
- Registered the rc.2 Objective Contract versions
  `.aether/objective-contracts/oc_742f9f4797494bf9/v1.md`, `v2.md`, `v3.md` and `v4.md` in
  the canonical repository policy manifest so the declared tracked surface matches the
  repository again, and reconciled the root `AGENTS.md` stabilization-authority paragraph
  with the current `@v4` objective (superseding `@v3`'s pre-merge tip hardcode), the rc.1
  disposition and automatic deployments to the existing Aether GitHub Pages site caused by
  reviewed green merges required by this objective (no manual Pages dispatch, other target
  or unrelated deployment). `@v4` selects the recovery/publish candidate as the clean
  `origin/main` merge of its own correction PR, with the exact SHA recorded only after
  merge in a local/durable preflight receipt, exactly one local annotated `v1.0.0-rc.2`
  tag on that frozen commit (never moved/retargeted), and public push of that same tag
  only after recovery canaries/REGATE/final gates; it also records supported immediate
  interruption/checkpoint semantics instead of false drain wording.
- This is a pre-stable release candidate. It is not stable `1.0.0`, no PyPI or other
  package-index publication occurs, WSL2 (and any macOS/Windows lane) is unverified and
  recorded as such, and issue #261 remains open with the deferred stable, PyPI/OIDC and
  WSL2 obligations explicit. Bundle qualification, gate measurements, publication,
  activation and rollback proof belong to the same objective's later units; this entry
  records only the release-identity, public-status, fork-pin, manifest and guidance
  reconciliation performed here.

## 1.0.0rc1 — release candidate (pre-stable, published but not accepted for activation)

The release identity is package version `1.0.0rc1`, annotated tag and GitHub prerelease
`v1.0.0-rc.1` (`release_impact=major`, `release_action=publish`,
`release_channel=prerelease`); `VERSION` remains the single product-version source.

- Added `scripts/release_bundle.py`: it builds one release bundle from exact clean Aether
  and maintained-fork commits — the `aether-agents` wheel and sdist, the maintained-fork
  runtime source closure at its exact commit, the schema-4 `maintained_fork` release lock,
  a provenance manifest, package-member and clean-install reports and a `SHA256SUMS` —
  and refuses a dirty checkout, a mismatched revision, a foreign repository, a build that
  is not byte-reproducible from the same commit, a private-path or canonical-secret
  finding in Aether-authored bytes, an incomplete member set, a tampered digest, and a
  missing release-identity surface. It also reports the exact member set a publication
  must attach and refuses a published release whose asset names or `sha256:` digests
  disagree with that bundle.
- Qualified the bundle before publication: member inspection of the wheel, sdist and
  source archive, a private-path and secret scan over the public bytes, a clean install of
  the exact wheel plus the locked runtime closure into fresh disposable roots with the
  normal resolver, and the CLI/runtime handshakes (`aether --version`,
  `aether version --json`, `aether --help`, `aether update --help`, the
  `doctor`/`status`/`setup`/`update`/`rollback` preview and refusal envelopes, the
  local-candidate preview and the pinned `aether update --local` option surface, Hermes
  import/version/plugin discovery, and the canonical TUI `--check`).
- Reconciled `.github/workflows/release.yml` with the existing tag and release-identity
  validation: the release job builds and qualifies the bundle from the tagged commit and
  attaches that exact member set — the verified members plus `SHA256SUMS` — to the GitHub
  prerelease, so the attached artifact set is the qualified artifact set. A re-run that
  finds the release already published attaches nothing (`gh release edit` takes no file
  arguments) and instead re-verifies the published assets by name and `sha256:` digest,
  failing closed when the release and the qualified bundle disagree. No second release
  path is introduced.
- This is a pre-stable release candidate. It is not stable `1.0.0`, no PyPI or other
  package-index publication occurs, WSL2 (and any macOS/Windows lane) is unverified and
  recorded as such, and issue #261 remains open with the deferred stable, PyPI/OIDC and
  WSL2 obligations explicit. The runtime, lifecycle, documentation and fork reconciliation
  content of this candidate is delivered and evidenced by the same objective's unit
  branches; this entry records only the release-identity, bundle-tooling and workflow
  reconciliation performed here.

## Unreleased

### Semantic project knowledge — trustworthy, bounded and honest snapshots (#416, #418, #419, #420, #423, #424)

- Replaced the destructive semantic graph merge with an additive `origin=llm` overlay: the committed structural graph stays the immutable base, hyperedges are included, label collisions are remapped only when uniquely proven and are otherwise omitted with a bounded reason, and a canonical structural projection (node identity, source/provenance attributes, edge endpoints/relation/site and direction) is compared before publication, aborting the update instead of rewriting `graph.json` on mismatch. Graphify's global `build_merge` is no longer part of the semantic application path.
- Withdrew the 600-second invocation deadline: one configured update now has a single 300-second total monotonic budget from entry through pointer publication, keeps concurrency at most two, reserves finalization time before another model call starts, returns a valid partial receipt at natural exhaustion, and stops scheduling on host/caller cancellation without publishing the cancelled candidate or leaving detached work, watcher or hidden continuation.
- Made the auxiliary route primary-only fail-closed: a response whose effective non-secret provider/model/protocol identity is unresolved or differs from the fingerprinted route is neither cached nor applied; that chunk stays pending/rejected with a bounded `route` reason, and cached fragments are read only while policy/version/content and stored route identity match. Multi-route snapshots and primary-model fallback remain absent.
- Persisted a semantic integrity/pipeline identity with a structural-base snapshot reference and digest, so a legacy semantic snapshot without that identity is no longer served as a trusted semantic result while its retained artifacts stay on disk and matching validated cache fragments are revalidated without new model calls.
- Corrected snapshot and query warnings to describe the immutable snapshot state (`complete`, `partial`, `pending`, `unavailable`, `disabled` or unknown/inconsistent) instead of the currently loaded component configuration, so a pending snapshot never reports extraction as disabled; an in-progress or interrupted update is reported separately as content-free operation metadata, and an operation record alone is never published evidence. Structural query and status stay available while semantic preparation, transport, validation, accounting or composition fails.
- Preserved auxiliary Responses terminal shape — phase, item status, incomplete reason, output-text fallback and tool calls — as the maintained portable Hermes patch `patches/hermes/HLP-420-responses-terminal-fidelity.patch` with its reconciliation entry, so incomplete or cancelled output can never become a completed answer.
- Reconciled the stage-005 expanded semantic contract (overlay composition, 300-second bound, route qualification, snapshot-state wording) and the user-facing guide, references, registry, packaged skills and changelog, and registered the objective contract, the HLP-420 patch and the new semantic-manager test in the repository policy manifest.
- No version bump, package publication, tag, deployment or live activation is part of this delivery (`release_action=defer`, `release_channel=none`); the bounded live canary, integrated qualification and issue closure belong to terminal integration.

### Active Morfeo collaboration through native contract execution (#334/#317/#407)

- Added optional native collaboration on the maintained Hermes fork: same-board `kanban_collaboration` adjunct table, optional `kanban_create(..., collaboration="advisory")` root opt-in, request/respond/ack/resolve on `kanban_comment`, and origin-bound TUI/gateway delivery that matches a runtime-derived `origin_route` before claim. Extra notify subscribers are not recipients. Legacy roots, ordinary comments, and the terminal-notification cursor remain unchanged.
- Reconciled the three sectorized SOULs and four existing canonical procedures with D6 stewardship wording. Independent review, three-role boundary, and owner authority remain intact. Early advice is not final result acceptance.
- Distinguished internal Morfeo collaboration from owner-facing notifications in DESIGN, R6/R7, AGENTS, and the execution guide. #317's open-ended observation gate is retired at owner direction without an organic PASS claim; #407 remains a closed postmortem.
- Exact maintained-fork merge: `DarkArty07/aether-hermes` PR #11, `bb5e9a422f3135371557e75bcd1db01c5f8fc3ba`. Portable patch `patches/hermes/HLP-334-native-collaboration.patch`.
- No version bump, package publication, tag, or live runtime activation is implied by this changelog entry (`release_action=defer`, `release_channel=none`).

### Hourly Telegram Monitor — implementation, offline qualification and documentation

- Added the principal `aether monitor status|on|off|history` control surface and the matching Morfeo-only `aether_monitor` tool over one private monitor state (`<state>/monitor/monitor.sqlite3`, 0700/0600) with an opaque pin on the existing Telegram destination, durable per-part delivery outcomes and thirty-day resolved retention.
- Added one native hourly job (`0 * * * *`, packaged pre-check, `deliver=local`, per-run `["aether_monitor_reporting", "no_mcp"]`) whose deterministic pre-check emits the native `{"wakeAgent": false}` gate for genuine idle before any inference, plus `aether_monitor_report_snapshot`, readable only by the monitor's own run.
- Added bounded read-only sources (registered, marker-verified projects; execution boards; exact user sessions) opened `mode=ro` with `query_only`, keeping project/origin-session/contract identity exact, labeling direct work as no-contract, and reporting coverage gaps instead of guessing.
- Added the `aether-telegram-monitor` plugin entry point, packaged pre-check and narration-context resources, and the type-named plugin tools; the portable opt-in remains Morfeo-only.
- Added `scripts/qualify_telegram_monitor.py`: the default lane is deterministic and provably free of model calls, Telegram sends and live-state writes; `--live --wait-hourly-boundaries 2 --output <protected path>` is the bounded provisioned lane owned by terminal integration.
- Reworked that lane onto the D13 isolated native-runtime laboratory and added `scripts/telegram_monitor_lab.py`: one private, exclusive root outside every Git worktree supplies the monitor's own `HOME`/`HERMES_HOME`/XDG roots/temporary directory/working directory and Aether state root; the decision-only configuration preserves the provisioned model/provider/fallback/toolset/timezone/limits/transport decisions without copying any credential; only already provisioned access for the exact route and destination is borrowed, in memory, through the lab children's process environment; the shipped writers seed the labelled synthetic scope; one lab monitor job is installed through the shipped control service; and one bounded supervised instance of the native cron scheduler executes the smoke, two natural hourly cuts and the later idle cut.
- Retired the shared-registry swap lane (`_isolate_registry`/`_restore_registry`, the no-replace/staging recovery machinery and the `scope-isolation-unsupported` refusal) with it: the harness no longer renames, unlinks, quarantines, replaces, merges, hides or restores any entry of this installation's project registry. The guarantees the swap existed to protect are carried by containment and retention, mapped explicitly in `docs/guides/telegram-monitor.md`; `--json` without `--live` now declares a `lab-bootstrap-preflight` check that proves the laboratory bootstrap and its fail-closed preflight with no external effect.
- Split the laboratory preflight into a read-only phase that runs before anything exists (the layout, the decision-only configuration, the borrowed access, the verified child context, the provisioned route and the native scheduler interface; a refused layout creates nothing and reads no credential) and an in-laboratory gate that resolves the loaded candidate and the native writer surface **inside the created private root**, before the synthetic scope is seeded and before any effect.
- Resolved the native writer surface before the fixture runs: the in-laboratory gate resolves every writer the fixture calls (presence and accepted keywords, at the funnel that validates them, including every keyword the fixture passes to the task writer), records the loaded module/artifact digests, entry points and installed distribution versions of every module the laboratory depends on, and verifies that those writers' effective board, project and session roots resolve inside the private laboratory. An unsupported runtime refuses fail-closed (`writer-interface-missing:…`, `writer-parameter-missing:…`, `writer-artifact-missing:…`, `writer-root-escape:…`, and `fixture-root-escape` inside the fixture child) with the bounded `lab-context-preflight` error — after the private root was created exclusively and retained, but before the scope is seeded, the job enabled, the scheduler started, a model called or a message sent — instead of failing mid-lane after the first write; a class-level instance property (the native scheduler's `name`) can no longer make the probe payload unserializable.
- Bound synthetic task identity to the shipped kanban writer: sessions are seeded only through parameters the provisioned revision accepts (the store owns the row timestamps, the title goes through the shipped title writer), the fixture reports the id every task call returned per manifest key, the harness binds exactly those ids into the manifest and refuses an unbound, duplicated or empty identity, and the links, the between-cut transition and every D12 case reference are derived from the returned ids alone — a lane that keeps an identity of its own cannot satisfy the case oracles.
- Corrected qualification preflight under D14: normalized `HERMES_HOME` to accept both the installation multi-profile root and the exact Morfeo profile home while refusing missing, ambiguous, linked, conflicting or differently named candidates; resolved the provisioned reference destination in a restricted child rooted at the normalized profile home using Hermes' native dotenv loader before gateway config, keeping lab access separate and ephemeral with no live effect.
- Corrected qualification preflight under D14R: gated the exact production module chain (`hermes_state` → `SessionDB` / writer surface) and exercised the fixture's import order in the preflight and laboratory native probes before `cron` or `gateway` imports, refusing a stale editable-install mapping fail-closed at read-only preflight before private laboratory creation without spending or external effects.
- Corrected qualification laboratory source evaluation under D15R: bound the harness's pre-enable coverage probe to the laboratory's own Hermes root (`lab["hermes_home"]`) rather than the parent's profile home, seeded synthetic boards through the shipped execution-board writer to populate complete Objective Contract bindings, eliminated the phantom default board coverage gap when no default store exists, and aligned the source phone-number pattern with reporting to prevent false task result safety rejections on ISO dates, achieving a genuinely gap-free laboratory before enable without external effects.
- The laboratory root, its record and the private receipt are retained as declared objective evidence (never self-deleted), and the lab scheduler is stopped cooperatively with its exit verified — a runner that does not stop is never success. The multi-hour live run, the production first delivery and activation remain with terminal integration; no live success is claimed here.
- Documented capability, control surface, privacy, failure, rollback, activation and qualification limits in `docs/guides/telegram-monitor.md`, registered the capability in `docs/capabilities.toml`, and reconciled the literal non-`specs/` policy manifest with every new path without weakening a check.
- No live activation, model call, Telegram send, credential or provider change is part of this delivery; real hourly Morfeo narration, real Bot API acceptance and installation-local activation remain pending terminal integration (`release_action=defer`, `release_channel=none`).

### Parent delegation identity, concurrent contract handoff, work-memory integrity, and semantic cache correctness

- Restored delegated-child snapshot isolation so `HERMES_DELEGATED_CHILD_CONTEXT` and dispatcher-owned `HERMES_KANBAN_*` cannot persist into reusable parent terminal snapshots (#310).
- Allowed Objective Contract authoring from a verified linked worktree without mutating the Project primary checkout, and stamped board `worktree_base_ref` so new Kanban worktrees start at the prepared contract HEAD (#354).
- Marked work-memory freshness dirty for untracked source changes, validated note metadata and markdown hashes before reflection cache hits, and returned `MEMORY_CORRUPT` for malformed records (#341).
- Included concrete non-secret auxiliary provider/model/api_mode in semantic fingerprints and refused to cache or apply incomplete explicit finish reasons such as `length` (#345).
- Exact maintained-fork merge: `DarkArty07/aether-hermes` PR #4, `28b593efa86bbc674b32f488c35932a4e7e85a51`.
- No version bump, package publication, tag, or live runtime activation is part of this delivery (`release_action=defer`, `release_channel=none`).

### Execute-code helper contract and search_files JSON framing

- Taught the actual explicit-import contract for `execute_code` helpers `json_parse`, `shell_quote`, and `retry` in schema, CLI tip, and sandbox failure hints (#313).
- Kept truncated `search_files` output as one JSON document by moving the pagination hint into structured `_hint`, so `execute_code` receives a dictionary instead of `JSONDecodeError` (#353).
- Exact maintained-fork merge: `DarkArty07/aether-hermes` PR #3, `6243e40ea6b06e85061bf3fedffaad43eed51dec`.
- No version bump, package publication, tag, or live runtime activation is part of this delivery (`release_action=defer`, `release_channel=none`).

### Runtime reliability (laboratory isolation and maintained-fork bugs)

- Isolated disposable-probe laboratory destinations so poisoned parent identity cannot reach a native Kanban child, and rejected symlink/escaped sandbox paths before writes (#267).
- Qualified named-custom auxiliary resolution as already working on the maintained Hermes fork and added integrated regressions for both admitted spellings (#292).
- Adapted background-review run-token admission and identity-qualified cleanup so pre-admission cancel and a superseding turn do not send review HTTP (#294).
- Classified the explicit exhausted-pool `503` phrase before generic overload so an authorized configured fallback is used (#295).
- Forwarded request-scoped extra headers through the Responses adapter, retries, and configured fallback without leaking destination authentication (#301).
- Recovered a durable same-run Kanban completion from a read-only snapshot when the transcript receipt is missing, without fabricating a terminal tool receipt (#304).
- No version bump, package publication, tag, or live runtime activation is part of this delivery (`release_action=defer`, `release_channel=none`).

### Contract design and execution procedures

- Added the personally authored `objective-contract-design`, `supervisor-decomposition`, and `implementation-evidence` canonical resources and focused role wording: material design before handoff, useful independent decomposition, and requirement-linked unit evidence.
- Registered the resources through the existing explicit skill distribution surface and reconciled the corresponding inventory expectations; no new tool, loader, role, schema, model, or concurrency setting is introduced.
- New behavior is under organic observation in [#317](https://github.com/DarkArty07/Aether-Agents/issues/317). At the owner's direction this delivery does not run a local synthetic qualification campaign; source registration and resource installation do not establish behavioral quality or speedup.

### Optional shared project knowledge and role experiences

- Fixed #342: work-memory corrections honor the published 16,000-character limits, retain readable maximum-length Unicode records, and reuse the configured component backend so subprocess timeouts are not reset to defaults.
- Fixed #344: work-memory evidence now checks the exact regular-file entry at a valid Git commit, rejecting directories, symlinks, gitlinks, missing objects and path-pattern expansion without claiming independent verification.
- Added the native `aether-project-knowledge` plugin with identical `project_knowledge` and `work_memory` action catalogs for Morfeo, Supervisor and Implementer; portable templates remain disabled until explicitly configured.
- Added revision/worktree-scoped structural Graphify snapshots, stable collaborative publication locks, native-session/operator bindings and explicit dirty-file coverage instead of a global graph or last-project fallback.
- Added project/role experiences with complete original notes, lexical retrieval, paginated reads, revision-aware corrections, idempotent save retries, private signal-only reflection, operator export and deletion. Save keys are stored only as digests; changed payload reuse fails explicitly, and reflection cannot write a personal sidecar into the shared technical graph.
- Added the two package-owned canonical skills and availability-guarded guidance in all three SOUL resources, plus optional hash-locked component installation and diagnostics outside the Hermes environment.
- Fixed boundary defects #324–#327: cumulative `truncated` flag reporting native omission, byte bounds, or the 50-reference cap; complete-over-budget native answers remain `truncated=false` with an explicit warning; unsupported upstream recovery wording is normalized to supported Aether actions.
- Added structured provenance: source-bearing actions (`query`, `explain`, `neighbors`, `community`, `path`, `impact`) return project-relative, revision-bound, deduplicated `{path, location, revision}` references in stable order; path queries include path nodes and relation sites; the 50-reference cap sets `truncated=true` with a warning; no private absolute paths escape.
- Added query→explain→community discovery: `explain` returns `resolved_node` with snapshot-local `community_id` and name; `community` returns community metadata matching the requested ID.
- Added canonical action-discriminated schemas for `project_knowledge` and `work_memory` with root properties retained and field descriptions naming accepted actions; runtime validation strictly rejects inapplicable fields and identity injection.
- Updated the `project-knowledge` and `work-memory` canonical skills and project knowledge guides with validated examples, discovery procedures, and honest truncation/reference semantics.
- Documented setup, all commands, ownership, isolation and limitations. Structural Markdown navigation is supported; live-agent E2E and measured token savings remain separate qualification work. No live profiles or services are activated by these source changes.
- Expanded the reusable project-knowledge catalog to fourteen project actions (`stats`, `god_nodes`, read-only PR views and graph/tree visualization included) while retaining the five work-memory actions. Query-only `context_filter`, path-only `undirected`, bounded traversal controls, semantic coverage metadata, and optional configured auxiliary maintenance are documented without enabling a primary-model fallback or watcher.
- Added `scripts/qualify_knowledge_expansion.py`, which validates the 14/5 schemas and exercises production service paths with disposable two-project fixtures offline. Optional auxiliary/GitHub lanes report unavailable access honestly; no token-saving, universal-superiority, live-agent adoption or release claim is made.
- Paged `semantic_prepare` so a full eligible corpus stays under the unchanged 2MB Graphify transport cap (#333). Deadline-deferred chunks stay pending rather than failed, and a file is covered only when every chunk that includes it succeeded (#337).

### Current beta project and documentation surface

- Added the user-visible `aether init` path for an existing Git repository root: it writes the portable project marker, preserves the required ignore boundary, and binds exactly one existing native Hermes Project by exact primary path; `--hermes-project ID` resolves an otherwise ambiguous exact match without creating or changing a native Project.
- Added the Morfeo-only Objective Contract authoring surface, including draft `validate`, immutable final versions, Git-base verification, and `prepare_handoff` routing data for one isolated execution board per `(project_id, contract_id, version)`.
- Added project-scoped execution-board routing, per-flow Supervisor session continuity, and isolated Implementer worktrees; board and Hermes Project identifiers remain local routing data rather than portable contract content.
- Added the bounded Contract Observer surface and deterministic observation summaries, including the read-only `aether observe` path and Morfeo-only observation views.
- Established maintainable current documentation and capability traceability: `docs/` owns current behavior and `docs/capabilities.toml` owns implementation status, while this changelog records deltas and root reports link rather than compete.

These entries describe Unreleased beta work only. They do not claim package publication, release qualification, public availability, or activation of any protected external effect.

### Routine GitHub lifecycle no longer deadlocks the pipeline

- Fixed #281 by removing normal branch/tag push, pull-request lifecycle, issue reconciliation, and non-destructive GitHub Release creation/edit/upload from the common pre-tool denial path. These operations are owner-preauthorized for already provisioned project repositories; Supervisor still owns pipeline publication after independent review, while role ownership remains a contract/review responsibility rather than a shell-text permission.
- Kept precise fail-closed controls for force/lease/mirror/history or tag rewrite, direct default-branch push, `--no-verify`, remote ref deletion, administrative PR merge, destructive Release/repository mutation, workflow dispatch/enable/disable and run cancel/delete, secret/variable mutation, arbitrary mutating APIs, package/container publication, deployment/infrastructure effects, credential widening, and irreversible destruction. Routine same-candidate CI reruns remain part of the allowed GitHub lifecycle.
- Added positive and negative three-role regressions, including global Git/GitHub flags and abbreviated force variants. Rollback is one Git revert plus restoration of the pre-install policy-hook backup; hook synchronization requires no process restart.

### Exact Hermes evidence lane restored

- Fixed the `hermes_exact` lane resolving its checkout from the *installed* Hermes runtime (#234). Under the declared `transitional_fork` mode that runtime always carries the local patch set and a newer commit, so it could never satisfy the locked baseline and the lane failed permanently on an environment fact that said nothing about Aether. The runner already documents that it "never consults a private/editable Hermes installation"; the tests now follow the same rule.
- Lanes that only read the Hermes tree honour `AETHER_EXACT_HERMES_CHECKOUT`; lanes that import the installed plugin skip with the baseline they need instead of failing.
- Reconciled the locked qualification manifest with the collected suite (#228): `core_test_files` now matches the runner's `CORE_TESTS`, which had gained `test_observation_path_confinement.py` and `test_projection_transition_runner.py` in the same checkpoint without the assertion following.
- Reproduce with `python scripts/qualify_observation.py checkout --path <dir>`, then run pytest with `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<dir> AETHER_EXACT_HERMES_CHECKOUT=<dir>`.

### Retired shell-text classification in the pre-tool policy

- Retired the generic command-text filesystem confinement for Implementer `terminal`/`execute_code` (#233). It could not enforce anything — an allowed interpreter derives its destination internally, so no path appears in argv — while denying legitimate work whose argv merely named a workspace-local venv launcher symlinked to a managed interpreter.
- Retired the Supervisor and Implementer contract-ownership checks that classified shell command text (#237), which read the `>` inside a quoted Git pretty-format such as `<%ae>` as redirection toward a contract path.
- Contract ownership, workspace ownership, branch/history, external-effect, credential, Kanban and Git integration guards are unchanged; ownership is enforced on structured file tools where the target is a typed argument.
- Added regressions for both blocked real commands and for contract ownership still denying a typed `write_file` against an owned artifact.

### Objective Contract prose boundary

- Separated Objective Contract secret-shape rejection from the observation metadata scanner so UTF-8, multiline and long contract prose remains authorable while recognized credential values stay denied.
- Added source and built-wheel regressions for the pipeline-blocking `#236` case.

### Reproducible Morfeo TUI activation

- Added a versioned, standard-library launcher that binds Morfeo to the repository-local profile and project directory.
- Added a side-effect-free `--check` mode with visible validation of profile state, executable availability, and required `file`/`kanban` toolsets.
- Added clean-process regression coverage for cwd independence, environment cleanup, reserved argument rejection, and missing prerequisites.

### Reproducible policy hooks

- Added a sanitized, versioned canonical source for the shared Morfeo, Supervisor, and Implementer pre-tool policy.
- Added an explicit standard-library synchronization tool with atomic installation, content-and-mode parity checks, drift-safe rollback, and no process or network activation surface.
- Added clean-clone tests for installation, verification, rollback, secret exclusion, and the #199 Implementer branch-inspection regression.

## 0.24.0 — 2026-08-17

### R0 design-governance baseline

- Accepted and versioned Aether's R0 governance specification, pinned Spec Kit research, and evidence-linked quality checklist.
- Established prompt-native agentic stages: agents form and conduct cognitive work from intent, prompts, instructions, and artifacts without a code-instantiated workflow engine.
- Adopted a living-spec model, a shallow spec-of-specs roadmap, three documentary stage labels, selective impact regression, and one consolidated human decision review.
- Defined canonical ownership across conceptual design, roadmap, stage specs, research, derived artifacts, implementation evidence, and agent context.
- Preserved Git history as the design-baseline mechanism while deferring branch, commit, worktree, and publication mechanics to R8.
- Added an explicitly unauthorized walking-skeleton evidence checkpoint after R2 and R5 so R6, R7, and R9 do not close runtime claims from documentation alone.

### Repository consistency

- Replaced the obsolete detailed roadmap and seven-state decision model with an English shallow roadmap linked to the accepted R0 spec.
- Consolidated accepted and open product decisions in `DESIGN.md`, added review triggers, and left model hierarchy subject to controlled R12 evaluation.
- Made the repository policy allow future `specs/**` artifacts while retaining an exact canonical base manifest and rejecting local runtime state.
- Added CI checks for R0 closure metadata, sequential IDs, Markdown links and fences, document mode, rejected legacy paths, and the fully checked evidence-linked requirements checklist.

### Rationale and alternatives

- Chose prompt-native agent reasoning over a deterministic stage orchestrator because no executable controller is needed to preserve design scope, authority, evidence, or review.
- Rejected seven per-decision states and custom B0/B1 registries because the living spec, research rationale, three roadmap labels, and Git history provide the required recovery with less cognitive machinery.
- Kept Spec Kit as pinned external evidence rather than vendoring it; future integration must begin with project-local adaptation layers.

### Impact and rollback

- This release changes documentation and repository policy only. It does not install Spec Kit, create agents, modify the live Hermes profile, implement A2A, activate services, or authorize build work.
- R0 is complete; R1 is the next recommended design area but does not start automatically.
- To roll back the complete versioned baseline, use tag `v0.23.0`. Local Hermes runtime state is unaffected by either version.

## 0.23.0 — 2026-08-16

### Hermes-only design reset

- Reset Aether Agents to a single Hermes Agent profile with reproducible configuration and GitHub governance.
- Removed the retired multi-agent product runtime, secondary profiles, custom MCP implementation, orchestration stack, product documentation, tests, schemas, scripts, and repository-owned skill catalog.
- Kept credentials, sessions, memories, databases, and runtime skills private and outside Git.
- Preserved Aether Router and Orca as independent external projects; this release does not modify or retire them.
- Replaced code-oriented CI with policy validation for the canonical 17-file manifest and simplified SemVer release automation.

### Breaking impact

- Previous multi-agent control, worker, coordination, installation, and qualification interfaces are no longer shipped.
- Pull requests and issues targeting the removed architecture are superseded by this reset.
- To roll back the versioned repository, use the `v0.22.0` tag or another earlier release.
