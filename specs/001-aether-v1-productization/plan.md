# Aether 1.0 Productization Technical Plan

**Contract**: [`spec.md`](spec.md)
**Research**: [`research.md`](research.md)
**Plan status**: normative plan active; implementation and release evidence are tracked separately
**Decision authority**: Christopher
**Plan owner**: Morfeo
**Execution owner**: Supervisor
**Written**: 2026-08-20

## 1. Summary

Build Aether 1.0 as one product with two independently versioned but release-locked components:

1. **Aether Manager** — the minimal `aether-agents` Python package on PyPI, exposing `aether` and managing setup, projects, service lifecycle, diagnosis, update, rollback, and uninstall.
2. **Managed Hermes runtime** — the original `hermes-agent` distribution from a locked stable upstream source by default, or from the public `DarkArty07/hermes-agent` fork only in declared `transitional_fork` mode while indispensable patches remain.

The manager includes a release lock and a sanitized three-profile resource bundle. It installs the selected locked Hermes source into an Aether-owned versioned runtime, keeps user state in stable XDG locations, and maps each project identity to one local board/workspace boundary. The manager never vendors Hermes, embeds private runtime state, or replaces another Hermes installation.

The stable release is produced only after an RC installed from PyPI consumes the exact public Hermes source or artifact declared by its lock and passes deterministic plus owner-authorized live qualification on Linux native and WSL2.

## 2. Technical context

**Manager language**: Python `>=3.11,<3.14`, matching the inspected Hermes support range unless the qualified locked runtime changes it before RC freeze.

**Manager packaging**: PEP 621 `pyproject.toml`, src layout, wheel and sdist, uv for development/build/install.

**Manager dependency policy**: standard-library first. Runtime download, hashing, atomic filesystem operations, subprocess execution, TOML reading, JSON output, and service inspection are available in Python 3.11. Add a manager dependency only when it removes a demonstrated reliability/security risk; exact-pin and lock it. The managed Hermes dependency tree is not imported by the manager.

**Runtime**: qualified original `hermes-agent` distribution built or consumed from the lock's `upstream` or `transitional_fork` public source and installed into a versioned virtual environment.

**Service**: systemd user service on supported Linux/WSL2, wrapping only the Aether-managed Hermes gateway/dispatcher.

**Persistence**: XDG directories plus portable `.aether/project.toml`; one local board/workspace namespace per project UUID.

**Remote services**: GitHub, GitHub Actions, GitHub Pages, PyPI Trusted Publishing, and an owner-selected public Hermes provider for the live RC gate.

**Canonical interfaces**: [`contracts/cli.md`](contracts/cli.md) and the three JSON Schemas under `contracts/`.

## 3. Constitution check

| Principle | Assessment |
|---|---|
| Current intent and human authority | Pass. Owner-approved PD-48–PD-70 define the public product. Publication, credentials, spend, live cutover, and destructive effects remain explicit gates. |
| Specification owns intent | Pass. `spec.md` is normative; this plan and future tasks may not weaken it. |
| Autonomous, bounded design | Pass. Technical defaults are chosen only where the owner delegated them and assumptions are recorded in `research.md`. |
| Evidence and traceable convergence | Pass. Existing local tests are distinguished from missing public-path qualification. Every release claim has an evidence path. |
| Simplicity over ceremony | Pass. One manager package and one source-mode-aware managed runtime are used. The transitional fork is retained only while indispensable. No control plane, installer daemon, container layer, renamed runtime package, or fourth agent is introduced. |
| Separate design, build, and activation | Pass. Build may prepare local artifacts. Remote publication, live model calls, and migration of Christopher's installation remain gated. |

No constitutional exception is authorized.

## 4. Architecture

### 4.1 Component boundary

```text
PyPI
└── aether-agents (single product wheel/sdist)
    ├── aether CLI
    ├── release-lock.json
    ├── profile-policy bundle
    ├── contract-observer entry point + shared observation modules
    ├── public schemas
    └── XDG/project/service lifecycle logic

Hermes public source selected by release-lock mode
├── upstream: NousResearch/hermes-agent stable tag + commit + source digest
└── transitional_fork: DarkArty07/hermes-agent release
    ├── original hermes-agent wheel/source distribution
    ├── SHA-256 checksums + provenance
    └── residual patch ledger + retirement evidence

User machine
├── uv-managed aether CLI environment (aether-agents wheel)
├── Aether-managed versioned Hermes runtime
│   ├── release-locked hermes-agent distribution
│   └── the exact same aether-agents wheel, installed --no-deps for the plugin
├── persistent Aether profile/user state
├── systemd user service
└── N isolated projects
    ├── tracked identity + contracts
    └── local board/workspaces/observations outside Git
```

### 4.2 Manager versus runtime

The manager MUST NOT import Hermes modules. It operates on Hermes as a versioned external executable. This preserves diagnosis and rollback if the runtime cannot import, has dependency damage, or is mid-transition.

One immutable `aether-agents` wheel is installed into two isolated environments. The `uv tool` environment owns the public `aether` command. The staged runtime installs that same wheel with `--no-deps` only so Hermes can discover `aether-contract-observer = "aether_agents.observation.capture.hermes_plugin"` through the public `hermes_agent.plugins` entry-point group and reuse Hermes-independent observation contracts/reducer code. Runtime-local console scripts are never put on the public manager path.

The import boundary is structural: manager commands/transitions/release/service/auth never import Hermes; the Hermes adapter never imports those manager modules; shared observation modules import neither. The schema-3 release lock binds the pre-build tuple `distribution + package_version + git_tag + git_commit + python_requires + observer entry point`, observation event/summary/segment-manifest read/write versions, and projection schema version. Doctor and every transition verify that each write version belongs to its read set and matches packaged schemas/upcasters/projection code. External provenance and the local transition record bind the staged wheel filename/SHA-256; activation verifies installed-file fingerprint and profile enablement. A second observer package, copied per-profile implementation, or independent observer version is not permitted.

The runtime MUST NOT update the manager or fetch mutable Aether product policy. Aether product updates originate in the manager and require a verified Aether release lock.

### 4.3 Release lock

Each manager release packages one `release-lock.json` conforming to `release-lock.schema.json`. The lock is immutable for that manager version and binds:

- SemVer and PEP 440 Aether versions;
- Aether Git tag and commit;
- Aether distribution name, normalized package version, Git tag/commit, Python requirement, and observer entry-point identity; together these form the pre-build identity tuple. External release provenance and each local transition record, rather than the self-contained lock, bind the staged wheel filename/SHA-256 used for runtime installation;
- source mode, repository, tag, and commit;
- stable upstream base and residual patch IDs when mode is `transitional_fork`;
- Python compatibility and the SHA-256 of the packaged, hash-bound observer
  dependency closure used to sync the manager and reconcile the runtime;
- the deterministic path-and-file-byte digest of the exact Hermes Git tree
  materialized locally, kept distinct from digests of remote source artifacts;
- source/artifact URLs, filenames, SHA-256 values, and provenance URLs required by the selected mode;
- exact profile-policy bundle version and digest.

A release is incoherent if any version, ref, artifact, source-tree, dependency-lock,
or profile-policy value differs. The validated external lock is copied byte-for-byte
to `<release>/release-lock.json`; its digest and both local materialization digests are
re-proved by doctor and before every activation.

### 4.4 XDG and version layout

Target logical layout:

```text
~/.config/aether/
├── config.toml                 # non-secret user/product choices
└── systemd/                    # source/records for generated user-service integration

~/.local/share/aether/
├── active.json                 # atomic pointer/record for active coherent release
├── releases/
│   └── <aether-semver>/
│       ├── release-lock.json
│       ├── runtime/            # isolated venv with locked Hermes + same Aether wheel
│       └── product-resources/  # immutable profile-policy bundle
├── profiles/                   # persistent per-role Hermes user state
│   ├── morfeo/
│   ├── supervisor/
│   └── implementer/
└── projects/
    └── <project-uuid>/
        ├── board/
        ├── workspaces/
        └── mapping.json

~/.local/state/aether/
├── transitions/                # update/rollback journals
├── backups/                    # metadata + safe state backups
├── observations/
│   ├── health/                 # content-free unresolved/IO counters only
│   └── <project-uuid>/
│       ├── journal/
│       │   ├── active/         # one append-only JSONL segment per producer epoch
│       │   ├── closed/         # immutable verified JSONL awaiting/without compaction
│       │   ├── archive/        # deterministic gzip + canonical manifests
│       │   └── quarantine/     # preserved corrupt/unknown segments
│       ├── keys/               # private 0600 HMAC fingerprint epochs
│       ├── projections/        # versioned deterministic rebuildable SQLite models
│       ├── projection.current.json # derived active-projection pointer
│       ├── summaries/          # durable schema-valid final summaries
│       └── locks/              # bounded reducer/compaction coordination
└── logs/                       # local redacted manager/service logs

~/.cache/aether/
└── downloads/                  # replaceable verified-download staging
```

Implementation may adjust leaf names during Supervisor analysis, but it MUST preserve:

- immutable release-owned artifacts versus persistent user state;
- no runtime/user state in project Git;
- no absolute path in portable project identity;
- atomic active-release selection;
- project UUID isolation;
- exact project-context resolution before any project journal write;
- immutable journals, versioned disposable projections, and preserved unknown-newer bytes across rollback;
- fingerprint keys remain private persistent state and never product/release resources;
- XDG ownership and least-privilege permissions.

### 4.5 Persistent profiles and product-owned policy

Each role home contains user-owned Hermes state plus product-owned files. The transition engine MUST classify each path before writing:

- **product-owned**: role SOUL, profile description, required policy hook, Aether config fragment/invariants, product-resource version marker;
- **user-owned**: authentication, secrets, sessions, memories, user profile, databases, logs, provider-specific choices;
- **merged/validated**: the effective profile configuration where model/provider selection is user input but required toolsets, role boundaries, dispatcher settings, and policy version are product invariants.

Updates may replace version-matched product-owned content after backup and drift analysis. They MUST never restore an old user-owned file over newer state. Unknown files are preserved and reported.

### 4.6 Project boundary

`.aether/project.toml` is the portable marker and conforms to `project.schema.json`. It contains no absolute machine path, board database location, credential, or provider data.

Local mapping resolves project UUID plus canonical repository identity to the local board/workspace root. A moved clone can be remapped explicitly; an identity collision must fail rather than attach to another project's state.

Greenfield `init` may create Git locally. Brownfield `init` must inspect existing constitution, governance, remotes, dirty state, ignore rules, and artifact conflicts. It prepares the minimum bootstrap but leaves project principles pending Morfeo/owner confirmation where none exist.

### 4.7 Service boundary

The user service runs the Aether-managed Hermes gateway/dispatcher with explicit:

- active runtime executable;
- Aether profile root;
- board/project registry location;
- redacted log destination;
- no inherited `PYTHONPATH`/`PYTHONHOME` or personal `HERMES_HOME`;
- restart behavior bounded by systemd user-service policy, not an Aether autonomous updater.

`aether` may visibly start the service because the user invoked the product. Enabling startup at login is opt-in. All service commands verify the unit belongs to Aether before acting.

## 5. Target repository structure

The exact final tree is implementation work, but Supervisor MUST preserve this ownership shape:

```text
Aether-Agents/
├── pyproject.toml
├── uv.lock
├── src/aether_agents/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py
│   ├── result.py
│   ├── platform.py
│   ├── paths.py
│   ├── integrity.py
│   ├── release.py
│   ├── transitions.py
│   ├── runtime.py
│   ├── profiles.py
│   ├── projects.py
│   ├── service.py
│   ├── auth.py
│   ├── commands/
│   │   └── observe.py
│   ├── observation/
│   │   ├── __init__.py
│   │   ├── contracts.py       # Hermes-independent typed contracts
│   │   ├── privacy.py         # allowlist projection and forbidden-content guards
│   │   ├── context.py         # exact project/session/task resolution
│   │   ├── identity.py        # trace/producer/event identity and dedup keys
│   │   ├── fingerprints.py    # private project-key epochs and HMAC domains
│   │   ├── correlation.py     # trace/task/session/request identities
│   │   ├── capture/
│   │   │   ├── __init__.py
│   │   │   ├── hermes_plugin.py  # sole Hermes-facing entry-point adapter
│   │   │   ├── projectors.py
│   │   │   ├── journal.py
│   │   │   └── flusher.py     # supervised durability outside callbacks
│   │   ├── reduce/
│   │   │   ├── __init__.py
│   │   │   ├── ingest.py
│   │   │   ├── upcast.py      # pure released-schema evolution
│   │   │   ├── reducer.py
│   │   │   ├── reconciliation.py
│   │   │   └── process.py
│   │   ├── storage.py
│   │   ├── retention.py       # closed-segment compaction/manifests
│   │   ├── query.py
│   │   └── report.py
│   └── resources/
│       ├── release-lock.json
│       ├── schemas/
│       ├── systemd/
│       └── profiles/
│           ├── morfeo/
│           ├── supervisor/
│           └── implementer/
├── tests/
│   ├── unit/
│   │   └── observation/
│   ├── integration/
│   │   └── observation/
│   ├── packaging/
│   ├── security/
│   │   └── observation/
│   ├── qualification/
│   │   └── observation/
│   └── fixtures/
│       └── observation/
├── docs/
├── scripts/
├── policy/
├── specs/001-aether-v1-productization/
├── specs/002-aether-contract-observation/
├── .github/workflows/
├── CHANGELOG.md
├── README.md
└── VERSION
```

When `transitional_fork` is selected, the downstream repository separately owns:

```text
hermes-agent/
├── upstream history
├── minimal Aether patch commits
├── AETHER_PATCHES.md
├── downstream qualification tests
└── release workflow for wheel/sdist/checksums/provenance
```

Supervisor may consolidate manager modules where that improves cohesion. It MUST NOT merge Hermes source into this tree or duplicate the private local profile catalog. The observer subpackage boundaries are normative: `capture/hermes_plugin.py` is the only Hermes-facing adapter; shared context/identity/fingerprint/contracts/reducer/storage/report modules remain Hermes-independent; callback and flusher responsibilities stay separate; public CLI ownership stays under `commands/observe.py`.

The editable normative observer schemas remain under `specs/002-aether-contract-observation/contracts/`. Build configuration includes those exact bytes in `aether_agents/resources/schemas/` inside wheel and sdist; that package path is generated build output, not a second hand-maintained source. Packaging tests compare bytes and SHA-256 across source, wheel, and sdist.

`pyproject.toml` declares one observer entry point:

```toml
[project.entry-points."hermes_agent.plugins"]
aether-contract-observer = "aether_agents.observation.capture.hermes_plugin"
```

The target is a module exposing `register(ctx)`, matching the release-locked Hermes entry-point loader. It is enabled by product-owned profile configuration, registers no public Aether CLI command inside Hermes, and must be idempotent per plugin-manager generation.

## 6. Public CLI implementation contract

The manager must implement exactly the commands and stable result contract in `contracts/cli.md`.

Cross-command design:

1. **Discover** current platform, paths, manager version, active release, service, and project without mutation.
2. **Parse** guided or declarative inputs into the same internal desired-state model.
3. **Plan** exact effects, preserved state, protected gates, and recovery record.
4. **Validate** paths, lock, compatibility, prerequisites, conflicts, authority, and dry-run invariants.
5. **Apply** through staged/atomic operations.
6. **Verify** the observed target state.
7. **Commit transition** by switching the active record only after verification.
8. **Report** through the stable human/JSON result envelope.

No command-specific shortcut may skip integrity or recovery checks that the shared engine would perform.

## 7. Update and rollback design

### 7.1 Update

1. Resolve one immutable target `aether-agents` wheel from canonical package/release metadata and record its filename/SHA-256 in the pending local transition.
2. Fetch its schema-3 release lock and verify the Aether distribution/package/tag/commit/Python/observer tuple, observation compatibility declaration, and external wheel provenance. Each declared write schema MUST belong to its corresponding read set and match packaged schemas/upcasters/projection code; never expect the wheel-contained lock to hash its containing wheel.
3. Preview version, storage, service interruption, and user-state treatment.
4. Download the locked upstream source or transitional-fork artifacts into cache staging.
5. Verify SHA-256, provenance, Python/platform compatibility, source mode, and package metadata.
6. Install the exact staged Aether wheel into the manager candidate and with `--no-deps` into the new immutable Hermes runtime; verify installed-file fingerprints, official entry-point discovery, per-profile enablement, and public-CLI non-shadowing.
7. Snapshot product-owned profile files and transition metadata. Preserve observation journals, versioned projections, summaries, and project fingerprint keys as persistent forward state; private local recovery backups MAY include the keys under `0600`, but release/publication artifacts, logs, summaries, and ordinary exports MUST NOT.
8. Apply product-owned profile/config changes to staging or through reversible atomic file operations.
9. Run doctor against the candidate while inactive.
10. Stop only the Aether service if required, switch the active record atomically, and start/verify it when previously active.
11. Mark transition complete only after runtime/profile/service verification.
12. On any failure, restore the prior active record and product-owned files, then verify the old release.

### 7.2 External manager mismatch

`uv tool upgrade` can change the manager outside Aether's transition. On every stateful launch:

- compare manager version with `active.json` and the active lock;
- permit read-only help/version/doctor;
- refuse incompatible runtime activation or mutation;
- offer `reconcile --to installed` or `--to active`;
- never infer compatibility from matching major/minor text alone.

### 7.3 Rollback

Rollback selects a previously verified release directory and restores only product-owned policy/config versions. Persistent user-owned state continues forward. Observation journals are never migrated or rewritten: the rollback reducer uses its own versioned projection, preserves/indexes unknown newer bytes, and forward re-update reingests them. Any other data migration introduced after 1.0 must declare backward compatibility or make rollback block before mutation; no such migration is authorized in this contract.

## 8. Downstream Hermes maintenance plan

### 8.1 Select the baseline

- Refresh upstream evidence.
- Choose a stable upstream release tag, not `main`.
- Record upstream tag, commit, package version, Python range, and release notes.
- Freeze that baseline for the RC unless a security/correctness blocker requires a documented restart.

### 8.2 Reconcile patches and select the source mode

For every entry in `HERMES_LOCAL_PATCHES.md`:

- inspect whether upstream merged an equivalent;
- test semantic parity before removing local code;
- prefer a stable upstream release with every accepted guarantee;
- select `transitional_fork` only if an indispensable residual patch remains;
- port only still-required behavior onto the stable baseline when that transition is necessary;
- keep one auditable logical patch commit per concern where practical;
- update the downstream ledger with upstream PR, Aether requirement, tests, and retirement condition;
- exclude unrelated local package-lock or generated drift.

No force-push or shared-history rewrite is authorized. Upstream updates enter through reviewable commits/merges according to the fork's protected branch policy.

### 8.3 Qualify the selected runtime source

- run the applicable complete upstream test suite plus Aether-specific regressions;
- in `upstream` mode, verify the locked source archive and build the original wheel/sdist in the controlled qualification environment;
- in `transitional_fork` mode, build wheel and sdist in CI from the downstream tag commit;
- inspect metadata and contents;
- produce SHA-256 checksums and provenance;
- test installing the wheel into a clean isolated environment;
- publish fork artifacts only when `transitional_fork` is selected and after its publication gate;
- record URLs/digests in the Aether lock; never point to mutable workflow artifacts.

## 9. Profile and policy productization

### 9.1 Sanitization

Derive public role resources from accepted design and the current effective profiles, not by recursively copying local homes.

Required public resources:

- portable Morfeo, Supervisor, and Implementer SOULs;
- descriptions that do not become accidental routing authority;
- product-owned configuration invariants and schema version;
- shared pre-tool policy and sync/verification logic;
- explicit allowlist of any Aether-owned skill resources actually required.

Forbidden resources:

- `.env`, auth stores, provider pools, memories, sessions, user profile, databases, logs, caches, generated state;
- private Router/provider/model identifiers;
- Christopher-specific preferences or personal skill catalog;
- absolute paths and machine-specific service identifiers.

### 9.2 Effective model/config merge

The setup model contains explicit provider/model bindings per role. The product merge layer owns role invariants; the user owns supported provider/model selection and credentials. The merge must be deterministic, inspectable, and fail on unknown conflict rather than silently dropping product or user state.

### 9.3 Policy verification

The existing canonical hook synchronization tests are retained and expanded for packaged resources, installed XDG profiles, update drift, backup/restore, and every role boundary. A public clean install must prove the same canonical bytes are active.

## 10. Project initialization and multi-project behavior

### 10.1 Greenfield

- require explicit `aether init`;
- validate supported filesystem and directory ownership;
- create Git only when absent and directory state permits;
- generate project UUID and portable marker;
- prepare contract directories and constitution placeholder/process without deciding principles;
- create local board/workspace mapping;
- show all created paths and no remote effect.

### 10.2 Brownfield

- inspect Git status, root, branch, remotes, worktrees, tracked `.aether` identity, constitution/governance artifacts, and file conflicts;
- preserve dirty files and existing governance;
- refuse conflicting identity or nested-project ambiguity;
- add only required ignore entries where safe and report rather than overwrite conflicts;
- create no commit or remote effect.

### 10.3 Isolation regression

Tests must operate two repositories simultaneously and prove distinct board DBs, workspace roots, sessions/memory scopes, and project mappings. Moving/cloning a project must require explicit local remapping and cannot attach silently to a different UUID.

## 11. GitHub and portfolio surface

### 11.1 Repository identity

Update description, topics, README, roadmap, changelog, contribution/security docs, issue forms, PR template, and policy manifest to describe:

- three roles and two routing paths;
- public CLI installation;
- upstream-first runtime boundary and transitional-fork retirement policy;
- Linux/WSL2 support;
- flexible descending model methodology;
- privacy/no remote telemetry and bounded local contract observation;
- known limitations and pre-1.0 legacy history.

### 11.2 Documentation

Publish GitHub Pages from versioned documentation. The generator/theme is a Supervisor decision, but build output must be reproducible and CI must check links, code snippets, navigation, and supported commands.

Required sections:

- overview and architecture;
- installation and prerequisites;
- guided/declarative setup;
- model/provider choices and authentication boundary;
- project initialization and contracts;
- commands and JSON/exit contracts;
- updates, rollback, uninstall, and recovery;
- Linux/WSL2 support matrix;
- Hermes source-mode policy and residual patch ledger;
- privacy/security/threat model;
- troubleshooting/doctor codes;
- contribution and release process;
- known limitations.

### 11.3 Demonstration

Record a short terminal demonstration from accepted RC evidence. It must show real commands/results from a disposable public-safe project and contain no private credentials, Router/model names, paths, or owner project data. Keep an editable/source form and a web-compatible asset.

### 11.4 Support configuration

Prepare Issues for bugs/features, Discussions for questions, private vulnerability reporting, and Pages. Changing GitHub settings is an external gate; local workflow/docs preparation may complete beforehand.

## 12. Implementation sequence and integration gates

These are dependency phases, not implementation cards. Supervisor derives and links the real units.

### Phase 0 — Canonical reconciliation and baseline freeze

- reconcile R4/R8/R9/R10/R11/R12/R13 and derived public docs with PD-48–PD-67;
- preserve historical rationale;
- freeze current repository diff and avoid swallowing unrelated local changes;
- refresh upstream Hermes evidence, select a stable baseline, and determine whether any indispensable patch requires `transitional_fork`;
- establish package/version/schema ownership.

**Exit**: no canonical artifact treats the fork as permanent or unconditional, and the exact upstream baseline plus any justified transitional source are recorded.

### Phase 1 — Manager/package skeleton and public contracts

- establish the single src-layout `aether-agents` package, version mapping, observer entry point, one-source schema/resource inclusion, build/lock tooling, command parser/result envelope, XDG path model, and dual isolated wheel-install test path.

**Exit**: one built wheel installs through uv in disposable manager and runtime environments; help/version/doctor operates without Hermes; runtime discovery resolves the exact observer entry point without making the runtime-local `aether` script public.

### Phase 2 — Hermes source reconciliation and runtime production

- reconcile patch stack on the stable upstream tag;
- classify every patch as retired, upstream-pending, or indispensable-transition and keep the residual ledger and regressions;
- build/install/inspect candidate wheel and sdist;
- prepare release workflow, checksums, and provenance.

**External gate**: publishing downstream GitHub Release assets, only if `transitional_fork` is selected.

**Exit**: local candidate artifacts are verified and their future immutable release coordinates can populate the Aether lock.

### Phase 3 — Runtime lifecycle, integrity, and recovery

- implement lock validation, download staging, runtime install, active release record, transition journal, doctor, update, mismatch detection, reconcile, rollback, and uninstall safety.

**Exit**: fault-injected local transitions prove no mixed active release and no damage to unrelated Hermes/user state.

### Phase 4 — Profiles, setup, and service

- package sanitized role resources;
- implement guided/declarative setup parity and model merge;
- install/verify profile policy;
- implement Aether-only systemd user service and lifecycle commands;
- launch Morfeo TUI through the active runtime.

**Exit**: clean disposable setup reaches doctor-ready without credentials/model call, and service controls cannot target another Hermes.

### Phase 5 — Project initialization and isolation

- implement greenfield/brownfield init;
- project identity and local mapping;
- one-board/workspace-per-project behavior;
- local/GitHub boundary checks.

**Exit**: two concurrent disposable projects remain isolated and no init path performs remote effects.

### Phase 6 — Contract observation

- before broad observer implementation fan-out, recreate the clean locked Hermes checkout and execute the disposable native-callback/append/flush/reducer/corrupt-tail/ENOSPC spike; retain measurements and return any infeasible contract threshold to Morfeo rather than silently redesigning it;
- package the public-hook observer and optional internal fail-open checkpoint sink inside the single product wheel, install that exact wheel `--no-deps` beside Hermes, and enable the official entry point in every participating profile with no role-facing observation step;
- implement exact project-context resolution, bounded owner-message candidates, restart-safe identities, the per-process append-only journal plus out-of-callback flusher, pure schema upcasters, versioned deterministic projections, project-keyed fingerprint epochs, verified closed-segment compaction, and schema validation;
- enforce product-owned completion authority, exact root/review/acceptance/invariant closure, and post-verification semantic-delta invalidation; reconstruct waves and every causal edge only from durable references/native span identity, never timestamp overlap;
- make partial hook registration, unpaired spans, missing turn/API IDs, heartbeat recency, and the complete native run-outcome taxonomy trace-visible coverage/state; preserve `unknown`/`unavailable` rather than inferring a positive fact;
- project and provenance-validate native payloads before every sink; confine absolute XDG paths and closed generated components; reject symlink/hard-link/mode violations before write; retain critical flush intent after failed `fsync`; atomically ingest each event and derived rows; preserve source through compaction failure; and guard projection pointers with lock/CAS transitions;
- expose one Morfeo-oriented `aether observe` review brief with human and JSON projections; defer the dashboard/API and separate read-only agent query tool;
- implement full-lifecycle duration partitioning, participants/actions, exact observed-tool accounting, causal semantic steps, parallel deployment waves, execution/rework rounds, deployed agent/unit counts, critical-path and dispatch-tick-sampled acceleration evidence, explicit bound task/run/review/acceptance state, field-covered configuration/tool/model evidence, provenance-bearing attribution, flow classification, invariant evaluation, separated lifecycle state, retention, and explicit coverage gaps;
- execute the 002 deterministic fixture matrix and one controlled real trace.

**Exit**: A1-SC-014 passes; issue `#195` closes from machine-readable evidence; configured/effective tool surfaces are not conflated; unresolved project/origin evidence never leaks or guesses; update/rollback/re-update preserves immutable source history; callbacks contain no synchronous durability/reduction work; unavailable signals remain explicit; the pipeline completes with no observation declaration; observer degradation is proven non-blocking; no downstream Hermes core patch is introduced; and privacy scans find no forbidden raw content or fingerprint key bytes.

### Phase 7 — Security, privacy, and package hardening

- path/symlink/race protections;
- permissions, log redaction, observer allowlist/retention, and local-only enforcement;
- secret/private-content scans of source and built artifacts;
- package metadata/license/attribution;
- service/process/environment isolation;
- threat-model review.

**Exit**: security tests and independent review pass on built distributions and installed state.

### Phase 8 — Public GitHub/docs surface

- update repository identity/docs/templates/policy;
- build Pages documentation, architecture asset, quickstart, support matrix, and RC-derived demo pipeline;
- update release workflow for build separation, RC SemVer, OIDC, attestations, and stable gates.

**External gates**: repository settings, Pages/Discussions/private reporting, PyPI trusted publisher.

**Exit**: local/docs CI is green and external configuration steps are explicit and ready.

### Phase 9 — Deterministic RC qualification

- build/verify the selected Hermes source mode, wheel, sdist, profile bundle, and release lock;
- install the exact RC package in clean native Linux and WSL2 lanes;
- exercise guided and declarative setup, init, service, project isolation, contract observation, update fault injection, rollback, uninstall, package/docs/security checks;
- retain machine-readable evidence.

**External gates**: publish a downstream release only if selected, configure trusted publisher, and publish the Aether RC.

**Exit**: the public RC can be installed and passes deterministic qualification with all deviations recorded.

### Phase 10 — Live RC qualification

- preregister realistic project/objective, expected artifacts, owner acceptance command, provider, model bindings, budgets, and redaction plan;
- obtain explicit credential and spending authorization;
- install from public PyPI RC, run the complete three-role path, and reconcile its full owner-message-to-terminal contract-observation summary against native evidence;
- review evidence independently and record Linux/WSL2 results without equating heartbeat with progress.

**Exit**: A1-SC-010 is evidenced or the release remains RC.

### Phase 11 — Stable release decision

- reconcile RC findings without weakening requirements;
- verify versions/commits/artifacts/docs all agree;
- produce final release rationale, alternatives, impact, rollback, known limitations, and evidence index;
- request explicit stable publication authority.

**External gate**: stable tag, GitHub Release, PyPI publication, public announcements, and any live-install cutover.

**Exit**: `v1.0.0` is public and verified, or publication remains blocked with the exact unmet gate visible.

## 13. Verification matrix

| Layer | Required evidence |
|---|---|
| Schemas/contracts | JSON Schema validation; command/help/version snapshots; JSON envelope and exit-code tests |
| Unit | parsing, version normalization, path mapping, hashing, redaction, merge ownership, transition planning |
| Filesystem/security | relative `XDG_STATE_HOME`, generated-component grammar, symlink/hard-link escape, traversal, DB/WAL/SHM private modes, atomic write, interrupted transition, malicious archive/filename |
| Package | build one wheel/sdist, inspect contents/metadata/license, install the same staged wheel in isolated manager/runtime environments, verify build/file-fingerprint, transition-digest, entry-point and schema parity plus import boundaries, execute outside source, and prove runtime-local CLI non-shadowing |
| Runtime integrity | locked download hash/provenance/metadata, clean wheel install, executable/version verification |
| Profiles/policy | public allowlist, no private data, role config invariants, hook parity, update drift/backup/restore, and read-only-validation versus real gateway-lifecycle denial regression |
| Service | generated unit inspection, user-only lifecycle, environment cleanup, readiness/failure, unrelated service safety |
| Projects | empty/brownfield init, dirty tree preservation, UUID collision, moved clone, two-project isolation, WSL `/mnt/c` refusal |
| Update/recovery | failure injection before/after every transition boundary, manager mismatch, rollback without user-state rollback |
| Contract observation | event/summary schema validation; exact product-owned completion authority, root/review/acceptance/invariant closure and semantic-delta invalidation; durable-reference-only causal step/wave/round reconstruction; deployed agent/unit and eligible-versus-running accounting; critical-path/queue/dependency/review/rework/capacity evidence; explicit task/run/review/acceptance graph; participant/action causality; exact tool totals and distinct run outcomes; missing-hook/unpaired-span/ID/heartbeat coverage; iteration/retry/loop/regression/reversion fixtures; blocked/review/crash/timeout/resume and no-premature-close tests; lifecycle-state separation; crash/restart/idempotence/atomic-ingest/pointer/compaction tests; CLI human/JSON summary parity; exact clean Hermes callback qualification; proof that deferred read surfaces are absent; controlled real full trace |
| Privacy | native malicious-payload projection before queue/log/journal/SQLite/summary/retry; source/build/docs/profile/release secret scans; local log redaction; observer allowlist/retention; no remote telemetry/network analytics or raw-content capture |
| Docs/workflows | link/code-snippet/nav validation; action linting; release tag/version gates; OIDC permission review |
| Platform | clean Ubuntu native, Ubuntu WSL2, Garuda/Arch dogfood |
| Live | public PyPI RC + lock-selected public Hermes source + public provider + complete three-role flow + independent evidence review |

No coverage percentage is invented. Supervisor must require tests that exercise every accepted guarantee and failure boundary and report uncovered risk explicitly.

## 14. Authorization gates

| Gate | Required owner action | Work allowed before it |
|---|---|---|
| Transitional-fork push/release | authorize remote publication, only if that source mode is selected | local residual-patch reconciliation, tests, artifact build |
| GitHub settings | authorize Pages/Discussions/private reporting/environment changes | workflow/docs/config preparation |
| PyPI project/publisher | configure/authorize pending Trusted Publisher | package build and TestPyPI-ready verification without publication |
| RC publication | authorize tag/GitHub/PyPI prerelease | complete deterministic local qualification |
| Live provider | choose/provision provider, credentials, and spend budget | preregistration and no-model qualification |
| Live Aether cutover | authorize migration/service changes to Christopher's installation | disposable clean-room installation |
| Stable publication | explicit final authorization | final evidence review and release candidate preparation |
| Destructive purge | explicit per-operation confirmation | normal uninstall and export |

A gate denial is authoritative. Workers must not route around it with another tool, account, package index, repository, or local substitution.

## 15. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Transitional fork becomes permanent or drifts into a general Hermes product | upstream-default source mode, prohibition on new downstream-only capability, residual patch ledger, stable-tag bases, upstream every general fix, executable retirement criteria |
| PyPI manager and runtime become mixed versions | immutable release lock, active record, doctor mismatch detection, reconcile/rollback |
| uv upgrades bypass Aether update | detect honestly; permit read-only recovery; refuse incompatible activation |
| Updating product policy overwrites personal state | path ownership classification, drift report, backup, unknown-file preservation, forward-only user data |
| WSL2 filesystem/systemd variation | explicit systemd and Linux-filesystem prerequisites; separate WSL qualification |
| Public package leaks private Aether state | explicit resource allowlist plus source/build/profile/docs/release secret scans |
| Polished docs outrun reality | derive quickstart/demo from public RC evidence; A1-NFR-008 |
| Upstream security release appears during RC | assess materiality; either restart baseline qualification or document why the pinned base remains safe; never silently move refs |
| Live model evidence is provider-specific | claim only Aether path compatibility through one public provider; preserve provider-agnostic configuration without claiming every provider was tested |
| Existing dirty work is swallowed | baseline inventory, narrow diffs, no reset/clean/discard, hotspot flags, review before commits |
| Policy denies benign validation as gateway lifecycle | preserve the denial as evidence, open the required issue when authorized, reproduce with a minimal test, and narrow classification without weakening real stop/restart protection |

## 16. Artifacts intentionally absent

- `tasks.md`: Supervisor owns decomposition and tasks.
- verified product/release completion evidence: source may exist as an implementation candidate, but deterministic validation and the owner-approved controlled real trace remain mandatory before A1 can be called complete or release-ready;
- credentials/provider config: protected user state.
- final quickstart/demo: commands are not called working until the public RC executes them.
- release lock instance: values do not exist until the selected Hermes source and Aether candidate artifacts are built or verified.
- stable release notes: derive from verified implementation and RC evidence.

## 17. Supervisor handoff

Supervisor must treat `spec.md`, this plan, `research.md`, and `contracts/` as one executable contract. Before fan-out it must:

- verify every requirement maps to at least one implementation and evidence owner;
- decide shared module boundaries, stable upstream base, source mode, dependency set, docs generator, transition primitive, conditional downstream tag scheme, and qualification scenario;
- expose cross-repository dependencies explicitly;
- isolate Aether manager, managed Hermes runtime, residual downstream transition when needed, public profiles/policy, project lifecycle, security, docs/GitHub, and qualification lanes where independent work adds value;
- create review and integration work that workers do not self-approve;
- preserve protected external gates and the current dirty-work baseline;
- return any genuine contract contradiction to Morfeo rather than choosing silently.
