# Aether Agents Roadmap

**Decision authority**: Christopher
**Current conceptual baseline**: `DESIGN.md` through PD-70
**Current product contracts**: `specs/001-aether-v1-productization/` and `specs/002-aether-contract-observation/`
**Current synthesis/entry**: `specs/r13-synthesis-and-release/`
**Selected Hermes base**: `NousResearch/hermes-agent` `v2026.8.18`, annotated tag object `9f13bbbf8423427e159c78066356ca0e27ca6b74`, commit `e624e9fde561e1add9388384012b295fde669ade`, `hermes-agent` `0.20.4`, Python `>=3.11,<3.14`
**Initial A1 release mode**: `transitional_fork` under PD-65

## 1. What this roadmap means

Stages are scopes of reasoning and ownership, not a workflow engine. A stage is `done` when its accepted decisions are explicit and mutually consistent; implementation and release evidence are tracked separately. Tests provide evidence. Kanban provides durable coordination. Neither defines the method or grants authority.

The owner's current instruction outranks every artifact. Artifacts outrank memory. Design acceptance does not authorize implementation, activation, credentials, spend, publication, deployment, cutover, destructive migration, or history rewriting.

## 2. Canonical design stages

| Stage | Scope | Status | Current artifact |
|---|---|---|---|
| R0 | Design governance and constitution principles | done | `specs/r0-design-governance/` |
| R1 | Authority and owner interaction | done | `specs/r1-authority-and-interaction/` |
| R2 | Contract and handoff | done | `specs/r2-contract-and-handoff/` |
| R3 | Spec Kit multi-agent method | done | `specs/r3-speckit-multiagent-method/` |
| R4 | Hermes foundation/adaptation boundary | done; A1-reconciled | `specs/r4-hermes-boundary/` |
| R5 | Role topology and profile isolation | done | `specs/r5-topology-and-isolation/` |
| R6 | Protocol and communication | done | `specs/r6-protocol-and-communication/` |
| R7 | Supervision, convergence, review, integration | done | `specs/r7-supervision-and-convergence/` |
| R8 | Workspaces, canonical authoring, integration, publication | done; A1/PD-67-reconciled | `specs/r8-workspaces-and-integration/` |
| R9 | State, XDG ownership, projects, update/recovery | done; A1-reconciled | `specs/r9-state-and-recovery/` |
| R10 | Security, authority, supply chain, privacy, guard precision | done; A1/PD-66-reconciled | `specs/r10-security-and-authority/` |
| R11 | Evidence, observability, package/platform/release qualification | done; A1-reconciled | `specs/r11-evidence-and-observability/` |
| R12 | Provider-independent model allocation and economics | done; A1-reconciled | `specs/r12-models-and-economics/` |
| R13 | Synthesis and public product/release entry | done; A1-reconciled | `specs/r13-synthesis-and-release/` |

Historical EC1/private-profile build evidence remains in R13 research and Git history. It does not qualify the public product and is not the current implementation plan. R13 `tasks.md` is historical and must not be dispatched for A1.

## 3. A1 public product target

Aether 1.0 is a public stable product, not a documentation tag. It has two release-locked components:

1. `aether-agents` on PyPI, exposing `aether` and owning setup, project mapping, service lifecycle, diagnosis, update, rollback, uninstall, schemas, release lock, and sanitized product resources; and
2. the original `hermes-agent` distribution from the exact public `upstream` or `transitional_fork` source/artifact selected by that lock.

The public path supports Linux native and WSL2 only for 1.0. It installs into Aether-owned XDG roots, keeps persistent user/profile/project state outside immutable releases, reuses Hermes profiles/Projects/boards/worktrees/review/lifecycle, and never replaces an unrelated personal Hermes installation.

Public artifacts exclude private profiles, credentials/authentication, sessions, memories, boards, logs, repositories, owner identifiers, machine paths, ignored runtime state, and private provider/model/router bindings. Users select supported bindings during setup and provision credentials through Hermes-supported local flows.

## 4. Hermes adaptation and transition rule

The selected upstream tag is annotated: the tag object and commit are separate identities. A previously supplied `9f13bb131670169467d9b2453ae2e8848814ff6e` does not resolve and is not a release coordinate. The source archive observed during reconciliation had SHA-256 `1e3d39d3638ec15fa9d31af262568a953e9272090deb1c50c44cd401175f5b80`.

A1 starts in `transitional_fork` mode because the selected upstream artifact does not yet qualify six indispensable existing guarantees:

- sticky initial blocking;
- agent-facing retry override;
- human-gated escalation recovery;
- one durable terminal handoff;
- first-spawn branch propagation; and
- asymmetric per-profile concurrency.

R4 research §13 owns the exact source evidence, upstream issue/PR state, and retirement gates. No new product capability may require a downstream-only Hermes change. Each patch retires only when an exact released upstream artifact passes its behavior gate. If all six retire before the candidate lock is frozen, A1 switches to `upstream`; the fork is not published unnecessarily.

## 5. A1 dependency phases

These are dependency phases and release-evidence gates, not a claim that code must land in strict numeric order. Dependency-scoped candidate code may exist before an earlier phase reaches its exit, but that does not advance either phase, satisfy its missing A1 dependencies, or establish release readiness. Supervisor owns the actual implementation graph and preserves every independent review/integration gate.

| Phase | Scope | Status | Exit/gate |
|---|---|---|---|
| 0 | Canonical reconciliation and baseline freeze | complete in this artifact set; requires independent review/integration | No stale no-fork/private-binding/private-local entry; exact base/mode/evidence recorded |
| 1 | Manager/package skeleton and public contracts | pending | Built wheel installs with `uv`; help/version/no-runtime doctor run outside source tree |
| 2 | Transitional downstream reconciliation/artifacts | pending | Six-patch candidate passes exact gates; local wheel/sdist/source/provenance ready. **External gate** before public fork/tag/release |
| 3 | Runtime lifecycle and recovery | pending | Fault-injected install/update/rollback/reconcile/uninstall preserves coherent active release and unrelated state |
| 4 | Profiles, setup, policy, Aether-only service | pending | Clean setup reaches doctor-ready without credentials/model call; precise guard controls and unrelated-service refusal pass |
| 5 | Project initialization and isolation | pending | Empty/brownfield init, native Project/board mapping, moved clone/collision, two-project and WSL path controls pass |
| 6 | Contract observation | implementation candidate under validation; deterministic and external gates pending | The candidate must pass a clean-baseline spike for native callback/append/async-flush/reducer/ENOSPC budgets. Qualification must install one staged immutable `aether-agents` wheel in the isolated manager and versioned Hermes runtime, prove matching build/file fingerprints, and bind its filename/SHA-256 through external provenance plus the transition record without a circular self-digest. The official `hermes_agent.plugins` entry point must supply the observer without a second package or per-profile source copy. Deterministic fixtures must prove exact project resolution, bounded owner-message candidates, restart-safe identities, immutable journals, pure upcasters, per-reader projections, preserved unknown-newer bytes, private project HMAC key epochs, out-of-callback durability, verified closed-segment compaction, and a pipeline with zero observation declarations. At the separate owner-approved external gate, one Morfeo-oriented `aether observe` brief must reconcile the owner-message-to-terminal contract, causal steps, waves, rounds, deployed agents/units, critical path, dispatch-tick-sampled acceleration evidence, field-covered configuration/tool/model evidence, provenance-bearing attribution, the bound task/run/review/acceptance graph, duration, separated lifecycle state, flow, and coverage against native sources. Configured/effective tool surfaces must remain distinct, unavailable signals explicit, retention indefinite/indexed, and cross-trace comparison/query tools/dashboard deferred. `#195` remains open until that controlled real trace is actually executed and independently reconciled. |
| 7 | Security, privacy, package hardening | pending | Built distributions and installed state pass path/archive/race, private-data, observer allowlist/retention, permissions/redaction, service/process, and independent review |
| 8 | Public GitHub/docs surface | pending | Docs/package/GitHub agree; local/docs CI green. **External gates** for settings, Pages, Discussions/private reporting, trusted publisher |
| 9 | Deterministic RC qualification | pending | Exact RC passes clean-package, runtime, lifecycle, observer, guard, project, security, Linux/WSL2, and evidence matrices. **External gates** for downstream/RC publication |
| 10 | Live public-path RC qualification | pending | Preregistered realistic three-role path plus a controlled contract-observation trace pass with independently reviewed evidence. **External gates** for credentials, spend, and live run |
| 11 | Stable release decision | pending | Exact accepted RC and all non-waived criteria agree. **External gate** for stable tag/release/PyPI/announcement/cutover |

The complete testing standard and Supervisor handoff are in `specs/r13-synthesis-and-release/plan.md` §§3–7. Morfeo creates no implementation units.

## 6. Evidence boundary

Public release claims are verified against the exact locked public artifact and installed RC, not a private editable runtime. Required evidence includes:

- wheel/sdist build, content/metadata/license inspection, and `uv` install outside source;
- source/runtime digest and provenance verification before execution;
- guided/declarative setup parity, project isolation, service ownership, update interruption, rollback, mismatch reconciliation, safe uninstall, and destructive-purge controls;
- secret/private-content scans, path/symlink/archive/race/permission/log-redaction tests;
- representative authorized work for every role, every protected/undecidable negative, both known policy false positives, and one complete pipeline without guard-caused manual recovery;
- deterministic contract-observation fixtures plus one controlled real trace reconciling duration, participants/actions, exact tool totals, flow classifications, and coverage against native sources;
- Ubuntu 24.04 native, Ubuntu 24.04 WSL2 with `systemd` and Linux-filesystem state, and continued Garuda/Arch validation; and
- a preregistered public-PyPI/live-provider RC scenario after explicit credential/spend/live-run authority.

Liveness, semantic progress, and termination are separate. Failure retries, resumptions, redispatches, reviews, and lifecycle corrections are separate. Heartbeat never proves progress; a zero technical failure counter never proves zero logical attempts.

## 7. Open release-visible limitations

Read-only GitHub inspection on 2026-08-21 found:

- `#192` — retry/resumption/lifecycle accounting: **OPEN**;
- `#195` — semantic progress beyond heartbeat: **OPEN and blocking stable 1.0 until the 002 contract evidence passes**;
- `#210` — task-bound Morfeo canonical worktree policy mismatch: **OPEN** while the PD-67 candidate proceeds through review/integration;
- `#211` — per-flow Morfeo/Supervisor session affinity: **OPEN**; and
- `#212` — TUI Kanban subscriptions are not a valid notifier platform and their events are discarded: **OPEN**.

Issue `#198` is closed for the owner-authorized local repair, but the selected public Hermes tag still exhibits the first-spawn branch defect; that public behavior remains a transitional patch gate. An issue or upstream merge is not qualification by itself.

Deterministic implementation evidence cannot substitute for the owner-approved controlled real trace. Issue #195 remains open, and Aether 1.0 is not called complete, release-ready, or production-ready until that external gate is executed and independently reconciled against native sources.

## 8. Change and regression

When intent or evidence changes:

1. update the artifact that owns the decision;
2. record reason, evidence, alternatives, and impact in the owning research artifact;
3. inspect direct and transitive dependencies;
4. reopen only materially affected `done` stages with a short reason;
5. reconcile derived plans, prompts, tasks, code, runtime, package, and release evidence; and
6. present Christopher only changed material decisions and consequences.

For Hermes upgrades, resolve the actual public/release/runtime source before reading it; inspect the exact path and revision; re-run every applicable adaptation and patch-retirement gate; and never treat docs, branch containment, or another agent's claim as execution evidence.

Every material out-of-scope finding remains visible as a question. No worker silently fixes or discards it.

## 9. Current authority boundary

This roadmap and the reconciled contracts authorize no public or destructive effect. In particular, they do not authorize:

- public fork/release assets;
- push, pull request, tag, GitHub Release, repository settings, Pages, Discussions/private reporting, or announcements;
- PyPI trusted-publisher configuration or package publication;
- credential acquisition/widening, paid model use, or live RC execution;
- existing-install cutover, deployment, destructive migration/purge, or unrelated service/process mutation; or
- force-push, history rewrite, or discard of unknown local work.

The current operational route is deterministic validation, independent review, and integration of the contract-observation implementation candidate while every unmet dependency phase remains explicitly pending. The owner-approved controlled real trace, publication, and stable release remain separate external decisions; candidate code or deterministic evidence authorizes none of them.
