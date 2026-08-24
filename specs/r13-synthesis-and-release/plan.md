# Implementation Plan: A1 Public Product and Release Entry

**Roadmap ID**: R13 / A1
**Plan status**: canonical reconciliation complete; implementation, qualification, and publication not performed
**Decision authority**: Christopher
**Plan owner**: Morfeo
**Execution owner**: Supervisor
**Derived from**: `spec.md`, R4/R8–R12, `../001-aether-v1-productization/`, and `../002-aether-contract-observation/`
**Selected Hermes baseline**: `NousResearch/hermes-agent` `v2026.8.18`, annotated tag object `9f13bbbf8423427e159c78066356ca0e27ca6b74`, commit `e624e9fde561e1add9388384012b295fde669ade`, `hermes-agent` `0.20.4`, Python `>=3.11,<3.14`
**Initial release mode**: `transitional_fork` under PD-65
**Written**: 2026-08-21

## 1. Summary

Build Aether 1.0 as a public Python product that manages one coherent, isolated Aether installation while reusing Hermes's native profiles, Projects, boards, worktrees, review, and lifecycle. The product adds one bounded local metadata-only contract observer without becoming a second execution authority. The manager ships no private state or binding and never replaces another Hermes installation.

Two independently versioned components are locked together:

1. `aether-agents` on PyPI, exposing `aether`; and
2. the original `hermes-agent` distribution from the exact public `upstream` or `transitional_fork` artifact named by the manager's release lock.

The selected stable upstream base is exact. A1 begins in transitional mode only because six existing indispensable workflow guarantees are not yet qualifying behavior in that release. The fork is a retirement-bound bridge, not an architecture destination and not a place for new Aether-only capabilities.

## 2. Fixed implementation decisions

### 2.1 Package and version ownership

| Concern | Owner and rule |
|---|---|
| PyPI distribution | `aether-agents` |
| Console command | `aether` |
| Import package | Fixed as `aether_agents` by PD-69; implementation findings cannot rename it without an owner-approved contract revision |
| Contract observer | Same `aether-agents` wheel and product version; official `hermes_agent.plugins` entry point `aether-contract-observer = "aether_agents.observation.capture.hermes_plugin"`; no second distribution or per-profile source copy |
| Aether version | One source of truth; SemVer display/tag and PEP 440 package form must normalize to the same release |
| Public schema versions | Aether manager owns them; setup/project schemas are integer `1`; release-lock schema is integer `3` after PD-65/69/70 and declares the observer entry point plus event/summary/segment-manifest read/write versions and projection schema version |
| Observation evolution/privacy | PD-70: immutable versioned event journals, pure upcasters, per-reader versioned projections, preserved unknown-newer bytes, exact context resolution, private project HMAC key epochs, and deterministic closed-segment compaction |
| Profile-policy bundle version | Aether release-owned and digest-bound; independent field, never inferred from file timestamps |
| Hermes version | Native `hermes-agent` version plus exact public source/tag/commit/artifact identity in the lock |
| Downstream build identity | Phase 2 decides a PEP 440-conforming artifact version without renaming the distribution; it must remain traceable to upstream `0.20.4` and the Aether patch ledger |

The A1 `release-lock.schema.json` is reconciled at schema version `3`: `upstream` mode forbids downstream-only coordinates, `transitional_fork` mode requires the upstream base and residual patch ledger, both modes require immutable Hermes coordinates/digests/provenance/Python compatibility, and the Aether section binds the single distribution plus official observer entry point. The wheel's final digest remains in external release provenance and local transition records to avoid self-reference. Phase 1 implements and validates this accepted public contract; it does not redesign it.

### 2.2 Manager/runtime boundary

- The manager uses Python `>=3.11,<3.14`, PEP 621, src layout, wheel/sdist, and `uv` for development/build/install.
- Standard library is preferred. A runtime dependency is added only for a demonstrated reliability/security need and is exactly locked.
- The manager MUST NOT import Hermes modules. It invokes and diagnoses the locked Hermes executable, so a broken runtime cannot disable manager rollback/doctor.
- The exact same staged immutable `aether-agents` wheel is installed in the `uv tool` manager environment and with `--no-deps` in the versioned Hermes runtime. The release lock binds distribution/version/pre-build identity/entry point; external provenance and the transition record bind wheel filename/SHA-256; doctor verifies installed build/file-fingerprint parity before activation. Only the manager environment owns the public `aether` command.
- The plugin adapter is the sole Hermes-facing Aether module; shared observation modules are Hermes-independent, and the adapter may not import manager commands/transitions/release/service/auth.
- Hermes MUST NOT update the manager or fetch mutable Aether policy. Product transitions originate in the manager and consume one immutable release lock.
- The runtime is installed in an Aether-owned versioned environment and never shadows or mutates another `hermes` executable.

### 2.3 State layout

Honor all `XDG_*_HOME` values; default logical layout:

```text
~/.config/aether/
├── config.toml
└── systemd/

~/.local/share/aether/
├── active.json
├── releases/<aether-semver>/
│   ├── release-lock.json
│   ├── runtime/
│   └── product-resources/
├── profiles/{morfeo,supervisor,implementer}/
└── projects/<project-uuid>/{board,workspaces,mapping.json}

~/.local/state/aether/
├── {transitions,backups,logs}/
└── observations/
    ├── health/
    └── <project-uuid>/
        ├── journal/{active,closed,archive,quarantine}/
        ├── keys/
        ├── projections/
        ├── projection.current.json
        ├── summaries/
        └── locks/
~/.cache/aether/downloads/
```

Immutable release artifacts, persistent user/profile/project state, transition evidence, and replaceable cache are separate. `active.json` is atomically replaced only after the candidate is coherent. No runtime/user state enters project Git.

### 2.4 Native Hermes adaptation

Selected commit evidence:

- `hermes_cli/projects_db.py:1-21,57-96` provides per-profile Projects, primary paths, and board binding while boards remain shared across profiles.
- `hermes_cli/projects_cmd.py:22-104` provides the public project operations.
- `tests/hermes_cli/test_kanban_project_link.py:29-64` and `test_kanban_board_project.py:40-87` prove project-linked worktree/branch derivation and board inheritance.
- `tools/kanban_tools.py:467-480,2132-2140,2455-2462` confirms Aether still needs role policy around card creation.

`aether init` therefore owns portable UUID/repository identity, brownfield validation, local mapping, and role policy. It registers/binds native Hermes Projects and boards; it does not create a second board/project/worktree engine or hardcode Hermes branch syntax.

### 2.5 Release mode and patch ledger

R4 research §13 owns the patch-by-patch disposition. Phase 2 carries only:

1. sticky initial blocking;
2. agent-facing retry override;
3. human-gated escalation recovery;
4. one durable terminal handoff;
5. first-spawn branch propagation; and
6. asymmetric per-profile concurrency.

The directory-versus-script lifecycle-guard correction is already contained in the selected tag and is omitted unless its exact qualification regression fails. Every carried patch has an upstream issue/PR and a behavior-based retirement gate. No open PR head or private editable checkout is a release dependency.

### 2.6 Portable profile/policy resources

- Package an explicit allowlist of Morfeo, Supervisor, and Implementer role identities, non-secret configuration templates, Aether policy/hooks, and Aether-specific skills.
- Preserve the accepted authority and tool-surface contracts without private provider/model/router names, owner identifiers, credentials, absolute paths, sessions, memories, boards, logs, repositories, or generic skill catalogs.
- Guided and declarative setup produce the same desired state and merge only Aether-owned fields. User-owned bindings and unrelated Hermes settings are preserved.
- Task-bound Morfeo contract authoring follows PD-67 exactly and is exercised through native structured file tools; shell/code execution is a negative control for contract mutation.

## 3. Testing standard

The A1 release standard is explicit and is not inherited from a downstream project's constitution.

### 3.1 Deterministic layers

| Layer | Required evidence |
|---|---|
| Contracts/schemas | JSON Schema validation; conditional release-mode cases; CLI help/version/result envelope/exit-code snapshots |
| Unit | version normalization, path mapping, hashing, redaction, desired-state merge, transition planning, project identity/collision |
| Filesystem/security | traversal, symlink/hardlink escape, malicious archive entries, special files, permissions, atomic replacement, interrupted transition, race controls |
| Package | build wheel/sdist, inspect contents/metadata/license, install exact wheel with `uv`, import/execute outside source tree |
| Runtime integrity | lock coordinates, digest/provenance, original package identity/version, Python range, executable resolution |
| Profiles/policy | allowlist/no-private-data, role invariants, hook parity, drift backup/restore, positive/negative controls, both known false-positive regressions |
| Service | generated unit inspection, user-only lifecycle, readiness/failure, environment cleanup, unrelated-service refusal |
| Projects | empty/brownfield init, dirty-tree preservation, UUID collision, moved-clone remap, native Project/board binding, two-project isolation, WSL `/mnt/c` refusal |
| Update/recovery | fault injection before/after download/install/activation, external-upgrade mismatch, reconcile, immutable-journal rollback/re-update with unknown-newer events, per-version projections, private key preservation, safe uninstall, destructive purge gate |
| Platform | Ubuntu 24.04 native; Ubuntu 24.04 WSL2 with `systemd` and Linux-filesystem state; continued Garuda/Arch validation |
| Release | exact RC commit/version/artifact consistency, SBOM/provenance/checksums, docs/package/GitHub agreement, retained machine-readable evidence |

### 3.2 Live RC layer

Preregister the scenario, realistic Git fixture, owner acceptance command, exact package/runtime artifacts, provider/model bindings, budgets, redaction plan, and expected outputs. Then, only with explicit credential/spend/live-run authority:

1. install the public PyPI RC in a clean lane;
2. consume the exact locked public Hermes artifact;
3. run Morfeo → Supervisor → Implementer → independent review → integration;
4. verify the running deliverable by the preregistered command; and
5. retain redacted evidence that distinguishes liveness, activity, semantic progress, waiting, anomalies, termination, retries, resumptions, redispatches, reviews, and lifecycle corrections.

Heartbeat alone is never progress. Issue `#192` remains an open limitation until its own acceptance matrix passes. Under PD-68, issue `#195` is a stable-1.0 prerequisite satisfied only by the deterministic and controlled-real-trace matrix in `../002-aether-contract-observation/`. Issues `#211` and `#212` separately keep per-flow session affinity and the invalid TUI notification path visible; no RC may claim automatic TUI return while `platform=tui` subscriptions are discarded.

## 4. Dependency phases and exit gates

These are dependency phases, not implementation cards. Supervisor derives the real board graph and may parallelize only when dependencies and hotspot ownership permit it.

### Phase 0 — Canonical reconciliation

Completed by this candidate: R4/R8–R13 and derived ROADMAP/AGENTS describe the public product, selected base, transitional rule, exact evidence, privacy boundary, and qualification gates. Historical rationale remains in research/Git.

**Exit**: independent review confirms no stale no-fork/private-binding/private-local execution instruction survives in current canonical entry.

### Phase 1 — Manager/package skeleton and public contracts

Implement package/version sources, CLI parser/result envelope, schemas including conditional release mode, resource inclusion, XDG path model, and wheel-installed test path.

**Exit**: exact built wheel installs through `uv` in a disposable environment and `help`, `version`, and no-runtime `doctor` run outside the source tree.

### Phase 2 — Transitional downstream artifacts

Reconcile only the six patch lines onto selected upstream commit `e624e9f…`; build wheel/sdist/source artifacts; inspect package identity/license/history; create patch ledger, checksums, SBOM, provenance, and qualification evidence.

**External gate**: create/publish public downstream repository/tag/release assets.

**Exit**: local candidate artifacts pass all patch gates; exact future public coordinates can populate a release lock. If an upstream artifact passes every gate, switch candidate mode to `upstream` and omit downstream publication.

### Phase 3 — Runtime lifecycle and recovery

Implement schema-3 lock validation, one-wheel verified download staging, dual isolated installation, external-provenance/transition digest binding, installed-file fingerprint and entry-point parity, active-release record, transition journal, doctor, update, mismatch detection, reconcile, rollback, and safe uninstall.

**Exit**: fault injection proves no mixed active release and no damage to unrelated Hermes/user state.

### Phase 4 — Profiles, setup, policy, and service

Package sanitized role resources; implement guided/declarative setup parity and user-binding merge; install/verify precise policy; generate only an Aether user service; launch Morfeo through the active runtime.

**Exit**: clean disposable setup reaches doctor-ready without credentials/model call; service controls refuse another Hermes; policy positives/negatives pass.

### Phase 5 — Project initialization and isolation

Implement greenfield/brownfield init, portable identity, local native Project/board mapping, one-board/workspace-per-project, moved-clone/collision controls, and local/GitHub boundary checks.

**Exit**: two disposable projects and all role profiles resolve the correct isolated project; init performs no remote effect.

### Phase 6 — Contract observation

First recreate the clean locked Hermes checkout and run the disposable callback/append/async-flush/reducer/corrupt-tail/ENOSPC spike; no broad observer fan-out begins until the evidence supports the closed contract or Morfeo records a revision. Then implement the 002 public-hook collector as the official entry-point module inside the same product wheel, exact project-context resolution, bounded owner-message candidates, optional fail-open checkpoints, restart-safe identities, per-process immutable journal plus out-of-callback flusher, pure upcasters, versioned deterministic full-lifecycle projections, private project HMAC key epochs, deterministic closed-segment compaction, explicit task/run/review/acceptance binding, causal semantic steps, parallel deployment waves, execution/rework rounds, deployed agent/unit accounting, critical-path and acceleration evidence, one schema-valid Morfeo-oriented CLI review surface, retention, gap semantics, and privacy allowlist. Dashboard/API and a separate read-only agent query tool remain deferred.

**Exit**: deterministic fixtures and one controlled real contract trace reconcile the complete owner-message-to-terminal lifecycle, participant/action causality, exact observed tool totals with field coverage, bound task/run/review/acceptance state, flow classifications, invariant transitions, separate liveness/activity/progress/wait/anomaly/termination state, and coverage; project/origin ambiguity never guesses or leaks; update/rollback/re-update preserves source bytes and key epochs; callbacks contain no synchronous durability/reduction work; `#195` closes; and degraded collection does not block work.

### Phase 7 — Security, privacy, and package hardening

Implement path/archive/race protections, permissions/redaction, observer allowlist/retention/local-only controls, source/built-artifact private-data scans, metadata/license/attribution, process/environment isolation, and PD-66 guard precision.

**Exit**: independent security review and full positive/negative/no-recovery pipeline pass against built distributions and installed state.

### Phase 8 — Public docs/GitHub surface

Align repository identity, README/quickstart, support matrix, architecture asset, policy/templates, Pages pipeline, RC-derived demo, changelog, release workflow, OIDC, attestations, and issue/security routes.

**External gates**: repository settings, Pages, Discussions/private reporting, trusted publisher.

**Exit**: local/docs CI is green; every external step is explicit and unperformed until approved.

### Phase 9 — Deterministic RC qualification

Build all exact RC artifacts and execute §3.1 on clean native Linux and WSL2 lanes, retaining machine-readable evidence.

**External gates**: downstream release if needed, trusted-publisher configuration, Aether RC publication.

**Exit**: public RC installs and passes all deterministic criteria or remains blocked with exact deviations.

### Phase 10 — Live RC qualification

Execute §3.2 only after credential/spend/live-run authority.

**Exit**: complete realistic public-path evidence is independently reviewed, or the release remains RC.

### Phase 11 — Stable release decision

Reconcile findings without weakening requirements; verify versions/commits/artifacts/docs; produce rationale, alternatives, impact, rollback, limitations, issue status, and evidence index.

**External gate**: stable tag, GitHub Release, PyPI publication, announcements, and any existing-install cutover.

**Exit**: `v1.0.0` is published and verified only after explicit authority, or publication stays blocked.

## 5. External authority ledger

| Effect | Authority state after this plan |
|---|---|
| Local documentation edits and verification in this task | Authorized by the assigned C0 contract |
| Product implementation | Released only through the Supervisor-owned board graph after C0 review/integration |
| Public fork/release assets | Not authorized |
| Push, PR, repository settings, Pages/Discussions/private reporting | Not authorized |
| PyPI trusted publisher or package upload | Not authorized |
| Credentials, paid provider use, live RC run | Not authorized |
| Stable release/public announcement | Not authorized |
| Existing private-install cutover or destructive purge | Not authorized |

A tool denial is authoritative. No phase may substitute another tool, account, package index, mutable branch, or local artifact to simulate a protected public path.

## 6. Risks and rollback

| Risk | Control / rollback |
|---|---|
| Transitional fork becomes permanent | No new downstream-only feature; per-patch owner/upstream state/retirement gate; requalify every upstream release |
| Release lock accepts a wrong source | Annotated-tag and commit are separate fields; conditional mode schema; digest/provenance before execution |
| Manager/runtime versions drift | Atomic active record, doctor mismatch refusal, explicit reconcile/rollback |
| Update damages user state | immutable releases, pre-transition backup, fault injection, user-preserving uninstall, unrelated-Hermes refusal |
| Public artifacts or observation state leak private content | allowlist packaging plus source/wheel/sdist/bundle/observer scans; no remote telemetry; metadata-only local redacted state |
| Native Hermes capability is duplicated | source-backed R4/R8/R9 adaptation review before design/build changes |
| Guard blocks ordinary work | positive controls, every false positive becomes regression, three-category redesign trigger, full no-recovery pipeline |
| Heartbeat misreported as progress | issue `#195` blocks stable 1.0; 002 deterministic reducer, invariant/flow taxonomy, coverage gaps, and controlled real-trace reconciliation |
| Zero failure count hides logical retries | issue `#192` remains visible; separate attempt/retry/resumption/review/lifecycle counters |
| Platform claim exceeds evidence | fixed Linux/WSL2 matrix and exact-lane evidence; other results labelled additional only |

Rollback of implementation work uses per-unit commits/reverts and immutable release directories. Rollback never rewrites shared history, mutates unrelated Hermes state, or bypasses an external gate.

## 7. Supervisor handoff

Supervisor MUST:

1. re-run cross-artifact analysis on this plan, `spec.md`, A1, R4, and R8–R12;
2. settle the conditional release-lock schema, downstream artifact version, public API/CLI shapes, and shared file ownership before fan-out;
3. build one dependency graph across manager, transitional downstream, lifecycle, profiles/policy, project integration, security, docs/GitHub, deterministic qualification, and live/release gates;
4. attach exact acceptance criteria and source decisions to every card;
5. create independent review/qualification lanes where evidence value is real;
6. preserve external gates rather than assigning them to workers; and
7. treat `specs/r13-synthesis-and-release/tasks.md` as historical EC1 evidence, not an A1 work queue.

Morfeo creates no A1 implementation units. This plan creates no new `tasks.md`.