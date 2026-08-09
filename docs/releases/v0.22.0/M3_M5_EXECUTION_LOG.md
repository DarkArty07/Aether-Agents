# M3-M5 Autonomous Execution Log

> **Authorized horizon:** M3, M4 and M5 only
> **Started:** 2026-08-09T03:32:17-06:00 (CST)
> **Start epoch:** 1786267937
> **Branch:** `feature/v0.22.0-orca-transition`
> **Baseline:** `c5e359e589ce5661d665314e125443331c083eca`
> **Status:** IN PROGRESS — M5 deterministic slice

## Authority and stop boundary

Christopher authorized autonomous implementation and qualification of M3, M4 and
M5, including installation of required local dependencies. Work stops after M5.

Authorized:

- repository source, tests, fixtures, schemas and documentation for M3-M5;
- isolated Orca 1.4.167 desktop-renderer/public-CLI qualification;
- deterministic fixture workers without external models;
- local reversible dependency installation;
- atomic local English commits.

Not authorized by this task:

- M6 or later roadmap work;
- real model-backed workers, provider credentials or spend;
- MCP registration or activation;
- persistent services or workstation activation;
- push, PR mutation, merge, rebase, amend, tag, GitHub Release or deployment;
- hidden Headless compatibility shims, private Orca APIs/databases or UI automation.

## Milestone status

| Milestone | Status | Acceptance boundary |
|---|---|---|
| M3 | COMPLETE | Lifecycle without workers: start/status/reconcile/cancel/close, restart recovery and zero survivors |
| M4 | COMPLETE | One deterministic no-model worker: dispatch/message/retry/evidence/episode and zero survivors |
| M5 | IN PROGRESS | Two deterministic workers with proved overlap, bounded peer handoff, partial failure/cancel and zero survivors; model-backed gate remains UNKNOWN/not authorized |

## Orca technical-debt ledger

| ID | Finding | Current consequence | Closure criterion | Status |
|---|---|---|---|---|
| ORCA-DEBT-001 | `serve` cannot publicly create/admit the trusted coordinator terminal required by this candidate | Qualification uses the desktop renderer plus public structured CLI | A version-pinned public Headless coordinator-admission primitive passes the M3 lifecycle matrix without renderer | OPEN |
| ORCA-DEBT-002 | `status --json` can block during cold start/recovery rather than expose a bounded readiness result | Callers require timeout, explicit readiness polling and honest `UNKNOWN` | Repeated cold/restart probes return bounded structured readiness or a stable typed failure | OPEN |
| ORCA-DEBT-003 | Coordinator terminal handles are instance-scoped across renderer restart | Recovery must create a new terminal and execute `orchestration run-use`, advancing consumer generation | Public recovery returns or atomically rebinds a durable coordinator identity | OPEN |
| ORCA-DEBT-004 | Public command discovery/documentation did not make `repo add --path` obvious at the qualification boundary | Adapter/catalog must pin exact argv by Orca version | Versioned machine-readable command schema covers required flags and drift | PARTIALLY MITIGATED BY PINNED CATALOG |
| ORCA-DEBT-005 | Renderer stop/cleanup spans app, daemon, terminals, orchestration state and AppImage extraction residue | Harness must inventory and clean every owned resource explicitly | Provider-native close reports complete bounded resource disposition and zero survivors | OPEN |
| ORCA-DEBT-006 | Global Xvfb install requires an interactive sudo password unavailable to the unattended agent | Global `Xvfb` remains absent | Owner installs the official package globally or accepts the reproducible user-local toolchain | MITIGATED USER-LOCALLY |
| ORCA-DEBT-007 | AppImage extract-and-run cache can abort with `Failed to clean up cache directory` | Repeated exact-candidate starts can fail before Orca readiness | A versioned launch path prepares one AppDir once and supports bounded repeat starts without extraction-cache state | OPEN; HARNESS PREPARES EXACT APPDIR |
| ORCA-DEBT-008 | Stopping the renderer process group may leave reparented Orca daemon and terminal shells alive | A naïve process-group cleanup can report false closure and delete a still-used root | Provider close returns a complete root-correlated inventory and terminates every owned process before acknowledgement | OPEN; HARNESS CLOSES TERMINALS AND INVENTORIES CMDLINE/CWD |
| ORCA-DEBT-009 | `worker-start --terminal` rejects a deterministic bare shell with `agent_unconfigured` | A model-free fixture cannot use Orca's supervised-worker primitive without impersonating a supported agent | Orca admits an explicit generic/process fixture worker kind with normal Dispatch/cleanup semantics | OPEN; USE PUBLIC TRACKING DISPATCH |
| ORCA-DEBT-010 | Public tracking `dispatch --to` has no `retry-of` relation | Orca cannot natively preserve fixture retry lineage | Tracking Dispatch supports immutable predecessor identity or generic worker-start accepts the fixture | OPEN; AETHER RECORDS LINEAGE AND CREATES A NEW ORCA DISPATCH |
| ORCA-DEBT-011 | `worker_done` rejects a tracking shell Dispatch | Fixture technical completion cannot use the agent-bound worker signal | Orca accepts exact-assignee completion for generic tracking Dispatches | OPEN; AETHER CAPTURES COMPLETION AND COMPOSES PUBLIC TASK UPDATE |
| ORCA-DEBT-012 | `terminal list` to `terminal close --tab` can race to `tab_not_found` across renderer generations | Per-handle cleanup is non-convergent despite the terminal already being absent | Close returns idempotent already-absent success or a generation/fence token | OPEN; USE SCOPED `terminal stop --worktree` |

## Progress log

- 2026-08-09T03:32:17-06:00 — Began autonomous M3-M5 tranche from a clean M2 candidate.
- 2026-08-09T03:32:17-06:00 — Recorded explicit stop boundary: finish M5; do not begin M6.
- M3 RED/GREEN — Added restart-safe manifest, Run and Task correlations; intent-before-effect, exact replay, `UNKNOWN` reconciliation, source-labelled status, cancellation and semantic closure. Focused result: 10 passed.
- Dependency — Global `xorg-server-xvfb` installation was blocked by interactive sudo. Installed official Arch package 21.1.24-1 under `~/.local/opt/aether-xvfb`; package SHA-256 `7f2116f869aedf51eb899dcfee4cf1f3bf6f9f42c71e089dcdbc0907d529e985`.
- M3 provider qualification — First apparent PASS was invalidated after an external process audit found a reparented daemon and terminal shell. The corrected harness closes every listed terminal and inventories root-correlated cmdline/cwd processes before deleting state.
- M3 COMPLETE — Exact Orca 1.4.167 desktop-renderer/public-CLI Run + two-Task lifecycle passed restart/rebind/recovery/cancel/close with zero workers, models, credentials, spend or survivors. Technical commit `7e3f1049ee78ec12fe29e8b4326f34000e1f95e1`; detached clean verification: 141 tests, Ruff, compileall and evidence invariants PASS.
- M4 fixture — Deterministic success/question/failure/cancel/barrier fixture committed at `ba49f4c25d0599625a0056cbfca97396e3fd34d8`.
- M4 compatibility findings — `worker-start --terminal` and `worker_done` are agent-bound in Orca 1.4.167; the accepted no-model route uses public tracking Dispatch, Aether-owned retry lineage/completion content and public Task updates without impersonating an agent.
- M4 COMPLETE — Real failed first attempt, new retry generation/worktree, question, renderer restart/rebind, dedicated reply, successful artifact, encrypted six-item episode replay, aggregate cleanup and a second active-worker cancellation Run all passed with zero models, credentials, spend or survivors. Technical commit `037b9ccf8698ab59c73275f3b4fb8d98a5e434af`; detached verification: 153 tests, Ruff, compileall and evidence invariants PASS.
