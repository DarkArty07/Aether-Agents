# Implementation Plan: A1 Public Product and Release Entry

**Roadmap ID**: R13 / A1
**Plan status**: canonical reconciliation complete; implementation, qualification, and publication not performed
**Decision authority**: Christopher
**Plan owner**: Morfeo
**Execution owner**: Supervisor
**Derived from**: `spec.md`, R4/R8–R12, and `../001-aether-v1-productization/`
**Selected Hermes baseline**: `NousResearch/hermes-agent` `v2026.8.18`, annotated tag object `9f13bbbf8423427e159c78066356ca0e27ca6b74`, commit `e624e9fde561e1add9388384012b295fde669ade`, `hermes-agent` `0.20.4`, Python `>=3.11,<3.14`
**Initial release mode**: `transitional_fork` under PD-65
**Written**: 2026-08-21

## 1. Summary

Build Aether 1.0 as a public Python product that manages one coherent, isolated Aether installation while reusing Hermes's native profiles, Projects, boards, worktrees, review, and lifecycle. The manager ships no private state or binding and never replaces another Hermes installation.

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
| Import package | `aether_agents` unless Phase 1 finds a packaging conflict; any change is decided once before fan-out |
| Aether version | One source of truth; SemVer display/tag and PEP 440 package form must normalize to the same release |
| Public schema versions | Aether manager owns them; setup/project schemas are integer `1`, while release-lock schema is integer `2` after the PD-65 source-mode correction |
| Profile-policy bundle version | Aether release-owned and digest-bound; independent field, never inferred from file timestamps |
| Hermes version | Native `hermes-agent` version plus exact public source/tag/commit/artifact identity in the lock |
| Downstream build identity | Phase 2 decides a PEP 440-conforming artifact version without renaming the distribution; it must remain traceable to upstream `0.20.4` and the Aether patch ledger |

The A1 `release-lock.schema.json` is already reconciled at schema version `2`: `upstream` mode forbids downstream-only coordinates, `transitional_fork` mode requires the upstream base and residual patch ledger, and both modes require immutable coordinates, digests, provenance, and Python compatibility. Phase 1 implements and validates that accepted public contract; it does not redesign it.

### 2.2 Manager/runtime boundary

- The manager uses Python `>=3.11,<3.14`, PEP 621, src layout, wheel/sdist, and `uv` for development/build/install.
- Standard library is preferred. A runtime dependency is added only for a demonstrated reliability/security need and is exactly locked.
- The manager MUST NOT import Hermes modules. It invokes and diagnoses the locked Hermes executable, so a broken runtime cannot disable manager rollback/doctor.
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

~/.local/state/aether/{transitions,backups,logs}/
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
| Update/recovery | fault injection before/after download/install/activation, external-upgrade mismatch, reconcile, rollback, safe uninstall, destructive purge gate |
| Platform | Ubuntu 24.04 native; Ubuntu 24.04 WSL2 with `systemd` and Linux-filesystem state; continued Garuda/Arch validation |
| Release | exact RC commit/version/artifact consistency, SBOM/provenance/checksums, docs/package/GitHub agreement, retained machine-readable evidence |

### 3.2 Live RC layer

Preregister the scenario, realistic Git fixture, owner acceptance command, exact package/runtime artifacts, provider/model bindings, budgets, redaction plan, and expected outputs. Then, only with explicit credential/spend/live-run authority:

1. install the public PyPI RC in a clean lane;
2. consume the exact locked public Hermes artifact;
3. run Morfeo → Supervisor → Implementer → independent review → integration;
4. verify the running deliverable by the preregistered command; and
5. retain redacted evidence that distinguishes liveness, semantic progress, completion, retries, resumptions, redispatches, reviews, and lifecycle corrections.

Heartbeat alone is never progress. Issues `#192` and `#195` remain open limitations until their own acceptance matrices pass. Issues `#211` and `#212` separately keep per-flow session affinity and the invalid TUI notification path visible; no RC may claim automatic TUI return while `platform=tui` subscriptions are discarded.

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

Implement lock validation, verified download staging, isolated install, active-release record, transition journal, doctor, update, mismatch detection, reconcile, rollback, and safe uninstall.

**Exit**: fault injection proves no mixed active release and no damage to unrelated Hermes/user state.

### Phase 4 — Profiles, setup, policy, and service

Package sanitized role resources; implement guided/declarative setup parity and user-binding merge; install/verify precise policy; generate only an Aether user service; launch Morfeo through the active runtime.

**Exit**: clean disposable setup reaches doctor-ready without credentials/model call; service controls refuse another Hermes; policy positives/negatives pass.

### Phase 5 — Project initialization and isolation

Implement greenfield/brownfield init, portable identity, local native Project/board mapping, one-board/workspace-per-project, moved-clone/collision controls, and local/GitHub boundary checks.

**Exit**: two disposable projects and all role profiles resolve the correct isolated project; init performs no remote effect.

### Phase 6 — Security, privacy, and package hardening

Implement path/archive/race protections, permissions/redaction, source/built-artifact private-data scans, metadata/license/attribution, process/environment isolation, and PD-66 guard precision.

**Exit**: independent security review and full positive/negative/no-recovery pipeline pass against built distributions and installed state.

### Phase 7 — Public docs/GitHub surface

Align repository identity, README/quickstart, support matrix, architecture asset, policy/templates, Pages pipeline, RC-derived demo, changelog, release workflow, OIDC, attestations, and issue/security routes.

**External gates**: repository settings, Pages, Discussions/private reporting, trusted publisher.

**Exit**: local/docs CI is green; every external step is explicit and unperformed until approved.

### Phase 8 — Deterministic RC qualification

Build all exact RC artifacts and execute §3.1 on clean native Linux and WSL2 lanes, retaining machine-readable evidence.

**External gates**: downstream release if needed, trusted-publisher configuration, Aether RC publication.

**Exit**: public RC installs and passes all deterministic criteria or remains blocked with exact deviations.

### Phase 9 — Live RC qualification

Execute §3.2 only after credential/spend/live-run authority.

**Exit**: complete realistic public-path evidence is independently reviewed, or the release remains RC.

### Phase 10 — Stable release decision

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
| Public artifacts leak private state | allowlist packaging plus source/wheel/sdist/bundle scans; no telemetry; local redacted logs |
| Native Hermes capability is duplicated | source-backed R4/R8/R9 adaptation review before design/build changes |
| Guard blocks ordinary work | positive controls, every false positive becomes regression, three-category redesign trigger, full no-recovery pipeline |
| Heartbeat misreported as progress | issue `#195` remains visible; evidence taxonomy and machine-readable reporting |
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