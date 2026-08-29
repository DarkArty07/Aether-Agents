# Incomplete implementation report

## Purpose and decision boundary

This report records verified incomplete or disconnected product seams in the current
repository. It is a decision aid for a later owner decision, not a roadmap replacement,
implementation authorization, activation instruction, or release claim. The accepted
cleanup objective permits only the limited repair and documentation work described here.
Nothing in this report authorizes setup, profile activation, service management, model
use, credential handling, publication, deployment, or completion of an item below.

Evidence paths are repository-relative and identify the source that establishes the
current behavior. “Deferred owner decision” means a later contract must decide whether
the capability remains required, define its acceptance boundary, and explicitly authorize
any protected or live effect.

## Classification summary

| Class | Meaning in this objective | Disposition |
|---|---|---|
| Authorized cleanup | High-confidence dead or duplicate implementation with a tested canonical replacement | Remove only the four named paths below. |
| Confirmed repair | A bounded defect or migration residue accepted for repair without deciding new product behavior | Repair and test locally; do not use it to activate a deferred capability. |
| Capability wall | An honest result that identifies a missing native boundary | Preserve the wall and keep it non-qualifying. |
| Dormant optional maintenance | A compatibility or candidate surface retained intentionally | Retain it; do not delete it merely because present callers are absent. |
| Unfinished product capability | A promised or candidate product behavior whose complete public/live boundary is not qualified | Document it and defer completion or activation to the owner. |

## 1. Authorized cleanup items

The following are the complete, four-item cleanup allowance. They are classified as
cleanup, not as evidence that the adjacent capability is complete.

| Authorized path | Current finding | Canonical replacement or retained boundary | Evidence |
|---|---|---|---|
| `observation.reduce.review.apply_since` and its private-only helpers | Duplicate/unreachable review reduction path | `report.diff_summaries` remains the exercised report-diff path | `src/aether_agents/observation/reduce/review.py`, `src/aether_agents/observation/report.py`, `tests/test_observation_reducer.py` |
| `lab.validation.validate_scenario` | Unused duplicate laboratory validator | `lab.synthetic_owner.validate_scenario` remains the canonical validator and lazy export | `src/aether_agents/lab/{validation.py,synthetic_owner.py,__init__.py}`, `tests/test_authorized_cleanup.py` |
| `lab.resources.schema_resource` | Unused duplicate resource accessor | `lab.validation.schema_bytes` remains the bounded public schema accessor | `src/aether_agents/lab/{resources.py,validation.py,__init__.py}`, `tests/test_authorized_cleanup.py` |
| `_Observer._run_id` | Unused private wrapper | `privacy.native_run_id` remains the production identity validator used by the observer | `src/aether_agents/observation/{capture/hermes_plugin.py,privacy.py}`, `tests/test_authorized_cleanup.py` |

No compatibility wrapper, public API, scaffold, capability wall, or frozen-phase candidate
is included in this cleanup set.

## 2. Confirmed defects repaired by this objective

These repairs are bounded correctness work. Their acceptance is the named focused test
and local validation, not a claim that a larger product phase has completed.

| Defect | Repair boundary | Evidence and validation |
|---|---|---|
| E2E-15 could present a false pass or enter the rolling reliability score without qualified native persistent wake evidence | An unqualified wake observation must remain a `CAPABILITY_WALL` and cannot count; this objective does not create wake delivery | `src/aether_agents/lab/{runner.py,matrix.py,persistent.py}`, `lab/scenarios/e2e-15.json`, `tests/test_e2e15_qualification.py`, `tests/test_e2e_matrix.py`, `specs/004-operational-simplification-and-e2e-reliability/plan.md` |
| Policy workflow inventory was stale after repository growth and laboratory migration | The committed expected inventory must equal tracked files except documented `specs/**`; the spec inventory is checked separately for nonempty safe content | `.github/workflows/policy.yml`, `lab/**`, `.aether/**`, `tests/test_public_artifacts.py` |
| Active project-marker readers did not share complete schema behavior | All active readers use the canonical project schema; valid markers and reject cases have the same policy | `specs/001-aether-v1-productization/contracts/project.schema.json`, `src/aether_agents/project_marker.py`, `src/aether_agents/observation/{context.py,query.py}`, `src/aether_agents/objective_contracts/store.py`, `scripts/aether_tui.py`, `tests/test_project_marker_validation.py` |
| Laboratory project registry path could nest `projects/projects/registry.json` | The registry is written once below the state root’s `projects/registry.json` | `src/aether_agents/lab/observation.py`, `tests/test_lab_formalization.py` |
| Update or rollback planning could recover or mutate before returning a dry-run/confirmation plan | Plan and `--dry-run` paths return without recovery, pointer change, transition write, or release deletion | `src/aether_agents/{cli.py,lifecycle.py}`, `tests/test_observation_lifecycle.py` |

The public report tests also protect both accepted root reports: the integration index is
byte-locked and both report contents must pass the tracked public-artifact scanner.

## 3. Capability walls

### E2E-15 native same-session wake

- **Current behavior:** deterministic preparation is available, but the native probe
  reports `CAPABILITY_WALL/native_same_session_wake_unobserved`. A one-shot harness
  continuation is recorded as harness input and is explicitly non-qualifying.
- **Missing boundary:** a supported native CLI, TUI, or gateway surface must wake the
  same persistent Morfeo session from a terminal board event without a second owner
  message.
- **Dependencies and risks:** this requires the exact candidate runtime, disposable
  profiles, explicit model-spend authority, and a live controlled run. A notifier or
  synthetic continuation would fabricate the property the gate is meant to observe.
- **Evidence:** `README.md`, `scripts/e2e/README.md`, `lab/scenarios/e2e-15.json`,
  `src/aether_agents/lab/runner.py`, and
  `specs/004-operational-simplification-and-e2e-reliability/plan.md`.
- **Deferred owner decision:** decide whether native persistent wake remains a required
  release gate and, if so, authorize a separately scoped native-surface investigation and
  controlled live qualification. Do not implement or activate wake in this objective.

### Triage-to-origin wake

- **Current behavior:** the reliability/release reconciliation records an open flow that
  can stall in triage without waking the originating Morfeo flow.
- **Missing boundary:** a verified native lifecycle signal from triage to the originating
  flow, with clear ownership and retry semantics.
- **Dependencies and risks:** depends on Hermes lifecycle behavior and must not be
  replaced with an unqualified second message or polling workaround. Incorrect routing
  can silently strand owner work.
- **Evidence:** `ROADMAP.md`, `HERMES_LOCAL_PATCHES.md`, and
  `specs/r7-supervision-and-convergence/spec.md`.
- **Deferred owner decision:** decide whether to carry this as a product requirement and
  authorize the native fix or upstream/downstream qualification separately.

## 4. Dormant optional maintenance retained intentionally

### Historical E2E command wrappers

- **Current behavior:** `scripts/e2e/` preserves command-compatible wrappers while
  canonical laboratory implementation, scenarios, schemas, fixtures, and documentation
  reside in `src/aether_agents/lab` and `lab/`.
- **Missing boundary:** no deletion boundary has been accepted; consumers of the
  historical commands have not been retired by this objective.
- **Dependencies and risks:** removing wrappers can break operator and qualification
  invocation surfaces even though the canonical package is present.
- **Evidence:** `README.md`, `lab/README.md`, `scripts/e2e/README.md`,
  `scripts/e2e/{collect.py,dispatch.py,matrix.py,run.py,synthetic_owner.py}`.
- **Deferred owner decision:** decide a compatibility retirement policy only after
  verified consumers and a replacement/notice boundary exist.

### Candidate lifecycle, profile bundle, and observer resources

- **Current behavior:** lifecycle code can validate and stage a release candidate and
  contains packaged role resources plus activation metadata. This is candidate local
  lifecycle machinery, not a completed installed product or live profile activation.
- **Missing boundary:** clean-install, activation, service, profile-policy, and exact
  runtime qualification must prove the complete boundary without using private runtime
  state.
- **Dependencies and risks:** depends on release lock identity, immutable artifacts,
  native Hermes integration, private-state controls, and explicit authorization for
  protected lifecycle effects. Calling this complete now would confuse staged bytes with
  activation.
- **Evidence:** `src/aether_agents/lifecycle.py`,
  `src/aether_agents/resources/profiles/**`, `pyproject.toml`,
  `tests/test_observation_lifecycle.py`, and `ROADMAP.md`.
- **Deferred owner decision:** retain the candidate surface; authorize a later clean
  lifecycle qualification only when its phase and external-effect gates are open.

## 5. Unfinished product capabilities

### Prerelease selection and RC publication

- **Current behavior:** `aether update` accepts `--prerelease`, while release workflow
  validation currently recognizes stable-looking semantic tags and the repository states
  that the build is a beta stabilization build, not an RC.
- **Missing boundary:** end-to-end prerelease selection, RC artifact validation, release
  metadata, and public publication behavior that cannot present an RC as stable.
- **Dependencies and risks:** exact artifact provenance, protected CI, release policy,
  external credentials, and owner authorization are required. Premature publication or
  stable labeling would be an external product claim.
- **Evidence:** `src/aether_agents/cli.py`, `.github/workflows/release.yml`,
  `DESIGN.md`, `README.md`, and `specs/001-aether-v1-productization/spec.md`.
- **Deferred owner decision:** decide the RC lifecycle and separately authorize any tag,
  release, registry, or public artifact operation.

### Project-specific `doctor`

- **Current behavior:** the CLI accepts `doctor --project PATH`, but the current doctor
  dispatch inspects the active lifecycle manager and does not establish the full
  project-mapping diagnosis promised by the A1 contract.
- **Missing boundary:** project identity, board/workspace mapping, platform, service,
  profile-policy, and runtime diagnostics must be resolved under one verified
  project-aware boundary.
- **Dependencies and risks:** requires implemented project initialization/isolation,
  installed runtime evidence, and no reliance on private operator state. A superficial
  ready result could conceal a wrong project mapping.
- **Evidence:** `src/aether_agents/cli.py`, `src/aether_agents/lifecycle.py`,
  `specs/001-aether-v1-productization/spec.md`, and `ROADMAP.md`.
- **Deferred owner decision:** decide the final project-aware diagnostic contract and
  authorize implementation after its prerequisites are accepted.

### Guided/declarative setup

- **Current behavior:** the CLI exposes a local wheel/check-out/release-lock setup path
  and can return a non-mutating plan before confirmation. It is not the complete guided
  and declarative setup capability promised for a clean public installation.
- **Missing boundary:** shared guided/config parser, planner, validator, effect engine,
  credential-safe configuration boundary, and clean-install proof.
- **Dependencies and risks:** depends on immutable release material, source verification,
  profile policy, and native credential mechanisms. Inventing defaults or accepting
  secrets in versioned input would violate the product contract.
- **Evidence:** `src/aether_agents/cli.py`, `src/aether_agents/lifecycle.py`,
  `specs/001-aether-v1-productization/contracts/setup-config.schema.json`,
  `specs/001-aether-v1-productization/spec.md`, and
  `tests/test_observation_lifecycle.py`.
- **Deferred owner decision:** decide when the setup phase may be completed and authorize
  the clean-environment qualification; do not run setup or activate a profile here.

### Project initialization and launch

- **Current behavior:** `init` and bare launch are explicit unsupported results rather
  than hidden mutations.
- **Missing boundary:** greenfield/brownfield handling, constitution confirmation,
  portable project identity, native Project/board mapping, workspace isolation, and
  unsupported platform controls.
- **Dependencies and risks:** requires native Hermes Project semantics and a complete
  project-aware lifecycle. Silent initialization could alter a repository or attach work
  to the wrong board.
- **Evidence:** `src/aether_agents/cli.py`, `src/aether_agents/observation/context.py`,
  `DESIGN.md`, `specs/001-aether-v1-productization/spec.md`, and `ROADMAP.md`.
- **Deferred owner decision:** decide the init contract and authorize its separate
  implementation and isolation qualification.

### Aether-managed service lifecycle

- **Current behavior:** `start`, `stop`, `restart`, and `status` are explicit unsupported
  results. The repository does not claim an active Aether-managed service.
- **Missing boundary:** generated user-service ownership, immutable runtime launch,
  readiness/reconciliation, unrelated-service refusal, and recovery semantics.
- **Dependencies and risks:** requires the runtime lifecycle, project mapping, native
  Hermes gateway behavior, and a protected service-effect authorization. An unscoped
  service action can affect unrelated processes.
- **Evidence:** `src/aether_agents/cli.py`, `src/aether_agents/lifecycle.py`,
  `specs/001-aether-v1-productization/spec.md`, `ROADMAP.md`, and
  `tests/test_observation_lifecycle.py`.
- **Deferred owner decision:** decide the service implementation and activation gate;
  do not start, stop, restart, or install a service under this objective.

### State export and complete uninstall preservation

- **Current behavior:** `uninstall --export` returns `EXPORT_NOT_IMPLEMENTED` without
  taking uninstall action. The ordinary lifecycle candidate has dry-run/protection paths,
  but the promised export boundary is absent.
- **Missing boundary:** a privacy-safe, integrity-checked export format and the full
  preserve-versus-purge recovery contract.
- **Dependencies and risks:** depends on retention, private key handling, versioned
  state, permissions, and a separately authorized destructive-purge path. An incomplete
  export can disclose private state or give false recovery assurance.
- **Evidence:** `src/aether_agents/cli.py`, `src/aether_agents/lifecycle.py`,
  `specs/r9-state-and-recovery/spec.md`, and
  `specs/001-aether-v1-productization/spec.md`.
- **Deferred owner decision:** choose export scope and recovery guarantees before any
  implementation or activation.

### Semantic closing checkpoints

- **Current behavior:** `CheckpointSink` defines bounded, fail-open semantic checkpoint
  kinds and rejects unverified authority or unsafe payloads. This is an optional
  observation side effect; it does not itself close a contract or make a workflow
  complete.
- **Missing boundary:** every authoritative closing action needs a verified native source
  binding and a complete, independently qualified terminal/review/acceptance path.
- **Dependencies and risks:** depends on native Hermes lifecycle facts, authority context,
  observer activation, and controlled trace reconciliation. Emitting synthetic checkpoint
  facts would distort semantic coverage.
- **Evidence:** `src/aether_agents/observation/checkpoint.py`,
  `src/aether_agents/observation/capture/hermes_plugin.py`,
  `specs/002-aether-contract-observation/spec.md`, and `ROADMAP.md`.
- **Deferred owner decision:** decide which closing checkpoints are required and
  authorize their native integration/qualification separately.

### Managed profile composition and observer activation

- **Current behavior:** portable Morfeo, Supervisor, and Implementer resources declare
  the observer plugin, with Morfeo also declaring the Objective Contract plugin. Lifecycle
  candidate code can materialize activation metadata for managed role homes.
- **Missing boundary:** clean installed composition, exact runtime entry-point proof,
  per-profile enablement, observer health, and active/live profile boundary are not
  accepted as complete.
- **Dependencies and risks:** depends on verified release lock, immutable wheel/runtime
  parity, managed profile policy, native plugin loading, and privacy constraints. Copying
  or activating local profile state would violate the product boundary.
- **Evidence:** `src/aether_agents/resources/profiles/**`, `pyproject.toml`,
  `src/aether_agents/lifecycle.py`, `specs/001-aether-v1-productization/spec.md`, and
  `ROADMAP.md`.
- **Deferred owner decision:** decide when managed profiles and observer activation can
  move from candidate resources to an installed, qualified capability.

### Retention scheduling and full observation lifecycle

- **Current behavior:** retention code supports deterministic compaction only for verified
  closed segments, rejects unsafe/ineligible source changes, and has no automatic
  time-based pruning or scheduler.
- **Missing boundary:** an owner-approved lifecycle policy and scheduler that can decide
  when terminal work is eligible while preserving unfinished dependencies and private
  state guarantees.
- **Dependencies and risks:** depends on closed-segment proof, replay verification,
  project state, privacy keys, retention policy, and lifecycle recovery. Premature
  compaction or deletion can lose evidence needed by unfinished work.
- **Evidence:** `src/aether_agents/observation/retention.py`,
  `tests/test_observation_journal_storage.py`, `specs/r9-state-and-recovery/spec.md`,
  and `ROADMAP.md`.
- **Deferred owner decision:** decide retention scheduling and deletion/compaction policy;
  do not schedule, prune, or activate it in this objective.

### Public release, protected CI, and immutable runtime qualification

- **Current behavior:** release automation and candidate artifacts exist, while the
  roadmap records protected remote CI and immutable runtime set as open; public release
  and trusted publication remain external gates.
- **Missing boundary:** independently verified exact public artifact/runtime provenance,
  protected CI evidence, RC/public-path qualification, and authorized publication.
- **Dependencies and risks:** external credentials, source/release identity, build and
  install proof, and explicit owner authorization are required. A local candidate does
  not prove a release or authorize publication.
- **Evidence:** `.github/workflows/{policy.yml,release.yml}`, `HERMES_LOCAL_PATCHES.md`,
  `ROADMAP.md`, `DESIGN.md`, and
  `specs/001-aether-v1-productization/spec.md`.
- **Deferred owner decision:** decide when to open the external qualification and
  publication gates; do not tag, publish, deploy, or alter remote settings here.

## Required reading of this report

The classifications are deliberately separate: an item can be implemented in a local
candidate and still be an unfinished product capability; a capability wall is evidence
of absence, not a request to work around it; and optional maintenance is not dead code.
Completion, activation, removal outside the four named cleanup items, or any live and
external effect remains deferred until a later owner-authorized contract resolves the
listed decision.