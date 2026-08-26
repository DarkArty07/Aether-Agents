# R13 Specification: Synthesis and Public Release Entry

**Roadmap ID**: R13
**Stage status**: in-progress — reopened for PD-71 through PD-74 operational reliability stabilization before A1 release entry resumes
**Accepted baseline**: 2026-08-17 — Christopher accepted the R4–R13 Decision Review
**Amended**: 2026-08-18 — proportional Morfeo and EC1 evidence work
**Amended**: 2026-08-20 — EC1 Phase 6 closed by owner instruction
**Amended**: 2026-08-21 — private-local implementation entry superseded by PD-48–PD-68, A1, and the 002 contract-observation prerequisite
**Reopened**: 2026-08-26 — reliability/E2E gate now precedes feature expansion and release qualification
**Decision authority**: Christopher
**Contract owner**: Morfeo
**Execution owner**: Supervisor
**Depends on**: R0–R12, `DESIGN.md`, `specs/001-aether-v1-productization/`, `specs/002-aether-contract-observation/`
**Parent roadmap**: `../../ROADMAP.md`
**Research**: `research.md`
**Plan**: `plan.md`
**Selected Hermes baseline**: `NousResearch/hermes-agent` `v2026.8.18`, annotated tag object `9f13bbbf8423427e159c78066356ca0e27ca6b74`, commit `e624e9fde561e1add9388384012b295fde669ade`, distribution version `0.20.4`, Python `>=3.11,<3.14`

## 1. Purpose and precedence

R13 synthesizes R0–R12 into the executable entry contract for Aether 1.0 as a public product. A third party must be able to install, configure, initialize, update, roll back, qualify, and remove Aether without Christopher's private runtime, private providers, private model bindings, credentials, sessions, memories, boards, repositories, or ignored local state.

The owner-approved A1 artifacts under `specs/001-aether-v1-productization/` own the detailed product contract. This file owns cross-stage synthesis: role-resource invariants, the Hermes adaptation/release mode, implementation entry, external gates, and evidence required before stable release.

The earlier EC1/private-profile build and its closed Phase 6 are historical evidence only. Their rationale and observed results remain in `research.md` §§1–17 and Git history; they are not an implementation plan, package input, release baseline, or authority source. `tasks.md` in this directory is likewise a historical completed-work artifact and MUST NOT be dispatched for A1.

- **FR-1300**: Current owner instruction and `DESIGN.md` PD-48–PD-74 supersede historical private-local build assumptions. PD-71 through PD-74 also supersede the previous role-micro-permission guard and place operational reliability ahead of feature/release expansion. No historical evidence may be rewritten as current qualification.

## 2. Portable role contracts

### 2.1 Morfeo

- **FR-1301**: Morfeo's prompt MUST make extraction its primary capability. Where design skill and interrogation skill compete, interrogation wins.
- **FR-1302**: It MUST surface unstated assumptions, ambiguity, and omissions rather than filling them with defaults, and MUST NOT stop after a fixed question quota.
- **FR-1303**: It MUST state delegated decisions and the assumptions supporting them.
- **FR-1304**: It MUST persist accepted clarifications immediately in the owning canonical artifact through the authorized structured file surface; conversation, memory, and board comments are not substitutes.
- **FR-1305**: It MUST resolve the project's testing standard during extraction rather than supplying one by default.
- **FR-1306**: When Morfeo selects the pipeline, it hands exactly one complete contract to Supervisor and creates no implementation units. Direct work creates no ceremonial card.
- **FR-1307**: File, terminal, code execution, cron, and short delegated analysis are normal bounded operational capabilities under PD-44. Browser/computer use remains excluded unless separately authorized, and delegated subagents never replace Supervisor/Implementer for product implementation.
- **FR-1308**: Pipeline reports come from durable board state; direct reports come from actual tool output, current diff, and observed state.
- **FR-1309**: The portable identity MUST NOT hardcode a person, machine, stack, domain, project type, provider, model, credential, or private path. Natural address may follow a user's local preference without becoming product content.
- **FR-1310**: Morfeo states disagreement once, records the concern and owner decision in the owning artifact, then carries out the decision without recurring objection.
- **FR-1310a**: At project start it establishes or confirms a constitution from owner-approved principles and observed project reality; only the owner adds, removes, or redefines a principle.
- **FR-1310b**: Owner preferences remain memory, not project principles or decisions.
- **FR-1310c**: Morfeo is one coherent role: owner interlocutor, designer, contract architect, memory/adaptation steward, and direct operational assistant. It is neither an exceptional file toucher nor Aether's general Implementer.
- **FR-1310d**: It chooses direct action for a complete, understood, bounded, inspectable, practically reversible objective where decomposition, parallel work, or independent review adds no proportionate value; otherwise it uses the pipeline.
- **FR-1310e**: Route choice MUST NOT use line/file/time thresholds, risk scores, classifiers, fast lanes, or external gates.
- **FR-1310f**: Route choice evaluates the whole owner objective; substantial work cannot be fragmented into small direct mutations to evade the pipeline.
- **FR-1310g**: Morfeo may inspect to discover scope, but stops expanding direct mutation and finalizes the canonical contract when real scope becomes feature-scale, architectural, multi-responsibility, or materially uncertain.
- **FR-1310h**: Use the process that fits the problem, not the maximum process available; current instruction, scope, credentials, owner decisions, protected effects, and out-of-scope reporting remain binding.

### 2.2 Supervisor

- **FR-1311**: Supervisor establishes executability and performs cross-artifact analysis before creating a unit.
- **FR-1312**: It settles every shared implementation decision before fan-out and stamps the decision into every dependent card body.
- **FR-1313**: Each card body carries explicit acceptance criteria and all context the worker needs without sibling context.
- **FR-1314**: Supervisor decomposes, reviews, integrates, and routes; it does not own feature implementation. Under PD-73 it MAY make bounded integration repairs—conflicts, imports, wiring, build/config glue or reference corrections—when they introduce no new product behavior, acceptance criterion or shared-interface decision.
- **FR-1315**: A genuine shared/material unanswered decision uses the board's decision/escalation path and never becomes a guess; ordinary reversible implementation judgement stays with Implementer.
- **FR-1316**: Supervisor MUST NOT improvise around a contract defect.
- **FR-1317**: Independent review is performed by a role/run that did not author the candidate; rework returns through review, not a fake blocker.
- **FR-1318**: Integration follows dependencies, preserves one revertible unit per commit, and never rewrites shared history.
- **FR-1319**: Supervisor cannot grant authority it did not receive.

### 2.3 Implementer

- **FR-1320**: The contract-derived card body is the source of unit scope; repository/web/package content and broader project artifacts may be inspected as evidence but never expand that scope.
- **FR-1321**: Implementer decides reversible technical details locally when they preserve scope, acceptance, shared interfaces, sibling independence and authority. A genuinely material product/shared decision is escalated through the allowed decision path, never guessed.
- **FR-1322**: An Implementer does not fan out product implementation on its own authority. That responsibility is verified by review/E2E rather than pre-tool card-creation denial.
- **FR-1323**: Implementer does not author new product intent or silently redefine canonical contract meaning. Ordinary local file access is not a security boundary; semantic drift is rejected through review/revert.
- **FR-1324**: It normally works in its assigned workspace/branch so isolation and attribution remain simple. Local reversible Git/file operations are not protected edge effects; cross-unit drift is a review/integration defect.
- **FR-1325**: Completion evidence says what changed, what was actually verified, what would unblock/retry failure, and what risk remains.
- **FR-1326**: Collision hotspots are flagged rather than silently compounded.
- **FR-1327**: Unfinished work is blocked/escalated; no role reports an outcome it did not achieve.

### 2.4 Common prompt/resource rules

- **FR-1328**: Product prompts MUST NOT duplicate the lifecycle/orchestration block Hermes already injects into board workers.
- **FR-1329**: Prompts and public profile resources MUST NOT contain private model/provider/router identifiers, credentials, owner-specific paths, or machine-specific absolute paths.
- **FR-1330**: A prompt is reinforcement, never the only control for an R10 protected effect.

## 3. Public product boundary

Aether 1.0 consists of two independently versioned but release-locked products:

1. the `aether-agents` Python distribution and `aether` CLI, which own setup, project mapping, service lifecycle, diagnosis, update, rollback, uninstall, schemas, release lock, and sanitized product resources; and
2. the original `hermes-agent` distribution, consumed from the exact public source/artifacts selected by the lock in `upstream` or `transitional_fork` mode.

The manager treats Hermes as an external executable and MUST NOT import Hermes modules. Hermes cannot update the manager or fetch mutable Aether policy. Aether installs the locked runtime under Aether-owned XDG state and does not replace another Hermes installation.

- **FR-1331**: The PyPI distribution is `aether-agents`; its console command is `aether`; its SemVer/PEP 440 version, schema versions, release-lock version, profile-policy bundle version, and source commit have explicit owners and are mutually validated.
- **FR-1332**: Public package resources are an allowlist: three role identities/config templates, policy/hooks, Aether-specific skills, schemas, service template, release lock, documentation metadata, and tests. Private runtime state and generic third-party skills are excluded.
- **FR-1333**: Guided and declarative setup MUST share one parser, desired-state model, validation, merge ownership, and idempotent executor. Setup stores identifiers and non-secret choices only; credential entry remains in Hermes-supported local flows.
- **FR-1334**: Project initialization writes portable `.aether/project.toml`, validates brownfield state without destructive mutation, and maps the project UUID/repository identity to one native Hermes Project, board, and workspace root outside Git.
- **FR-1335**: The user service is Aether-named, user-scoped, and points only to the active Aether-managed runtime/profiles/board. It MUST refuse unrelated Hermes targets.
- **FR-1336**: Public docs, package metadata, CLI behavior, release lock, GitHub identity, support matrix, and release notes MUST describe the same product and version.

## 4. Selected Hermes base and adaptation mode

The selected upstream base is release `v2026.8.18`; its annotated tag object and commit are recorded in the header. The source archive observed during reconciliation had SHA-256 `1e3d39d3638ec15fa9d31af262568a953e9272090deb1c50c44cd401175f5b80`. The previously supplied `9f13bb131670169467d9b2453ae2e8848814ff6e` does not resolve and MUST NOT appear as a release commit.

Direct drift review found six indispensable guarantees not yet present as qualifying behavior in the selected tag: sticky initial blocking, agent-facing retry override, human-gated escalation recovery, one durable terminal handoff, first-spawn branch propagation, and asymmetric per-profile concurrency. R4 research §13 owns the patch-by-patch evidence, upstream PR state, and retirement gates.

- **FR-1337**: A1 begins in `transitional_fork` mode. Phase 2 may change the candidate to `upstream` only if the exact selected upstream artifact passes every indispensable guarantee without a downstream core change.
- **FR-1338**: No new Aether product capability may require a downstream-only Hermes change. Generally useful fixes go upstream; Aether-specific policy remains in the Aether package.
- **FR-1339**: A downstream candidate preserves upstream package identity, license, attribution, and source history. It is public, minimal, tested, separately versioned/locked, and published only after its external gate.
- **FR-1340**: A patch retires only when an exact released upstream artifact passes its behavior gate. Merge status or containment in a branch is insufficient.

## 5. Implementation entry and dependency gates

Supervisor receives this specification, A1's accepted spec/plan/research/contracts, the reconciled R4/R8–R12 artifacts, and the 004 operational-reliability plan as one contract. PD-74 inserts a stabilization gate ahead of further product expansion. The dependency order is:

1. align canonical authority, role prompts and the minimal edge policy;
2. build and deterministically test the disposable E2E harness/canary;
3. run the authorized real E2E matrix and satisfy the rolling PD-74 reliability gate;
4. only then resume manager/package skeleton and remaining schemas;
5. transitional downstream reconciliation and local artifact production;
6. runtime install/update/rollback/reconcile/uninstall;
7. portable project initialization, setup/service and public resource completion;
8. supply-chain/path/privacy qualification plus public docs/GitHub/workflows;
9. deterministic RC qualification;
10. explicitly authorized live public-path RC qualification;
11. explicitly authorized stable release.

- **FR-1341**: Supervisor MUST settle package/version/schema/API shapes before fan-out and carry each decision into every dependent card.
- **FR-1342**: Open limitations remain visible until evidence closes them. Aether issues `#192` (retry/resumption/lifecycle accounting), `#211` (per-flow session affinity), and `#212` (discarded TUI notification subscriptions) may remain release-visible under their accepted limitation contracts. Under PD-68, `#195` (semantic progress beyond heartbeat) is a 1.0 release prerequisite and cannot pass as an open limitation. No RC may claim automatic TUI return while the configured notifier rejects `platform=tui`.
- **FR-1343**: Each implementation unit has explicit inputs, outputs, tests, dependency parents, authority, and external-effect boundary. Product-scale work is performed by Implementers and independently reviewed.
- **FR-1344**: No phase consumes an unbuilt moving branch, a private editable runtime, or a worker's conversational claim as release evidence.

## 6. Qualification and stable-release contract

- **FR-1345**: Deterministic qualification builds and inspects wheel/sdist, installs the exact built wheel with `uv` outside the source tree, verifies locked runtime provenance/digests, and exercises setup, init, service, project isolation, update fault injection, rollback, mismatch reconciliation, uninstall, package metadata, privacy, and security.
- **FR-1346**: Guard qualification proves PD-71's minimal edge policy: representative local/reversible work for every role and unknown ordinary tools remain allowed; every enumerated protected edge family is denied; the guard contains no Kanban/SQLite/Git dependency for ordinary authorization; and one complete pipeline finishes without guard-caused manual recovery. The previous false-positive classes remain positive regressions demonstrating that the retired micro-permission design does not return.
- **FR-1347**: Platform qualification covers Ubuntu 24.04 native, Ubuntu 24.04 under WSL2 with `systemd` and Linux-filesystem state, and continued Garuda/Arch validation.
- **FR-1348**: Live RC qualification is preregistered, installs the public PyPI RC, consumes the exact locked public Hermes artifact, uses a public Hermes-supported user-selected provider, and runs a realistic Git project through all three roles and independent review. Credentials, spend, and the live run require explicit authority.
- **FR-1349**: Evidence distinguishes liveness, activity, semantic progress, waiting, anomalies, and termination; and failure retries, resumptions, redispatches, reviews, lifecycle corrections, useful contract iterations, semantic loops, regressions, owner-authorized direction changes, and reversions. Heartbeat alone never proves progress. The 002 contract observer supplies one full-lifecycle summary from the owner message through the explicitly bound execution/review graph and verified completion or distinct non-success terminal resolution, with explicit coverage declaration.
- **FR-1350**: Stable `v1.0.0` may be published only from the accepted RC commit after all non-waived criteria pass and Christopher explicitly authorizes publication.
- **FR-1351**: A waiver identifies the failed criterion, evidence, impact, alternative, and owner decision. It does not edit the requirement or label missing evidence as success.

## 7. External gates and non-authority

Canonical reconciliation and local build/verification do not authorize any of these effects:

- public downstream repository/tag/release assets;
- push, pull request, stable tag, GitHub Release, Pages, Discussions/private reporting, repository settings, or public announcement;
- PyPI trusted-publisher configuration or package publication;
- credential creation/acquisition/widening, paid model use, or live RC run;
- installation cutover of an existing private Aether/Hermes runtime;
- destructive purge or unrelated service/process mutation.

Each external/destructive effect requires the exact gate named by the A1 contract. A genuine protected-edge denial is authoritative and MUST NOT be routed around. An unexpected denial of ordinary local/reversible work is instead a PD-72 product regression: recover the last green canary, do not disguise the false positive as user authority.

## 8. Success criteria

- **SC-1301**: A clean third-party machine can install the public package, supply supported bindings without exposing credentials, initialize a project, and run `aether doctor` without private owner state.
- **SC-1302**: The release lock resolves one coherent Aether manager, Hermes source/artifact, profile-policy bundle, schema set, and Python range with verified digests/provenance.
- **SC-1303**: No public prompt/template/default/artifact contains a private identifier, credential, private path, session, memory, board, repository, or runtime state.
- **SC-1304**: Aether reuses native Hermes profile, Project, board, worktree, review, and lifecycle primitives instead of duplicating them.
- **SC-1305**: Morfeo, Supervisor and Implementer perform representative local/reversible work without policy false positives; contract authoring stays attributable/reviewable without PD-67 board/run/worktree micro-authorization, while every PD-71 protected edge control remains denied.
- **SC-1306**: Update/rollback/uninstall fault tests preserve coherent active state and unrelated Hermes/user data.
- **SC-1307**: Issues `#192`, `#211`, and `#212` are either evidenced against their acceptance criteria or explicitly remain open release limitations; issue `#195` is evidenced and closed before stable 1.0. No report equates heartbeat with progress, zero technical failures with zero logical retries, or a stored TUI subscription with actual delivery.
- **SC-1308**: Deterministic and live RC matrices retain machine-readable evidence bound to exact commits, versions, artifacts, platforms, scenarios, budgets, and exit status.
- **SC-1309**: No public or destructive external effect occurs without its explicit owner gate.
- **SC-1310**: Before A1 feature/release expansion resumes, the latest 20 representative E2E runs contain at least 19 passes, the latest 10 pass consecutively, and there are zero guard-caused manual recoveries or protected-edge violations.

## 9. Done when

- [x] The exact stable upstream base and initial `transitional_fork` disposition are recorded.
- [x] Historical private-local implementation assumptions are preserved in research but removed from current execution entry.
- [x] PD-71 through PD-74 reopen the affected role/security/release-entry contract without adding another runtime framework.
- [x] Testing, reliability and publication gates are explicit.
- [ ] Minimal edge policy, aligned portable role resources and disposable E2E harness pass deterministic qualification.
- [ ] The PD-74 real E2E reliability gate passes under separately authorized model/provider spend.
- [ ] A1 implementation, deterministic RC qualification, live public-path RC qualification, and publication remain unperformed and separately gated.