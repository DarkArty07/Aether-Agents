# v0.22.0 Aether–Orca Equivalence Matrix

> **Status:** SUPERSEDED CONTRACT ANALYSIS; ORCA NOT YET ACTIVATED FOR AETHER
> **Date:** 2026-08-03  
> **Orca CLI:** `/home/darkarty/.local/bin/orca-ide`  
> **Pinned AppImage digest:** `sha256:813b11e99f7caa4bf8e4fc47200dd6c465f34a04d61e855adbd8822190592e33`

> **Supersession:** PDR-0012 rejects the pre-emptive native core and stable
> adapter API proposed below. The verified Orca capability inventory remains
> evidence, but any adapter must be introduced only from an observed integration
> need and must not duplicate Orca lifecycle mechanics.

## 1. Boundary

Orca is evaluated as Aether's replaceable execution substrate. It is not Aether's product authority, requirements interpreter, acceptance authority, continuity curator, or release authority.

The live installed CLI contract was retrieved through:

```text
orca-ide skills get orchestration
orca-ide skills get orca-cli
orca-ide status --json
```

The CLI and embedded guides were available. The runtime reported `not_running`, so this analysis does not claim an executed Aether-Orca dispatch. The prior external evaluation observed Orca 1.4.167; the exact installed candidate is pinned here by AppImage digest until its runtime can report version/build identity directly.

## 2. Ownership model

```text
User / Hermes
    |
    | product intent, authority, participant policy, acceptance
    v
Aether native core
    |
    | stable request, contract, identity, evidence and cleanup envelopes
    v
Aether-Orca adapter
    |
    | JSON CLI/RPC contract
    v
Orca
    |
    | Run / Task / Dispatch / Worker / Terminal / Worktree / Message
    v
Approved local or remote execution environment
```

A Run is an operational namespace and coordinator inbox. A Task is an operational work item. A Dispatch is one execution attempt bound to a worker terminal. None of those objects defines whether the user received the intended product.

## 3. Capability equivalence

| Olympus capability | Orca primitive | Aether responsibility retained | Verdict |
|---|---|---|---|
| ACPManager process spawn | `worker-start`, `terminal create`, worktree selectors | Select Daimon/model/profile, exact project root, environment allowlist, authorization | `REPLACE WITH GATE` |
| ACP session identity | Run + Task + Dispatch identity | Map stable Aether contract/attempt IDs to Orca IDs | `REPLACE WITH ADAPTER` |
| `talk_to open/delegate` | `run-create`, `task-create`, `worker-start` or tracked `dispatch` | Contract creation, owner, acceptance, placement and conflict decisions | `REPLACE WITH ADAPTER` |
| `talk_to message/steer` | `send`, `reply`, `ask`, terminal send where explicitly appropriate | Determine whether guidance is authorized and attempt-scoped | `REPLACE WITH ADAPTER` |
| `talk_to poll` | `check`, `worker-show`, `worker-read`, task/dispatch inspection | Interpret liveness versus completion and preserve uncertainty | `REPLACE WITH ADAPTER` |
| `talk_to close/cancel` | `worker-stop` plus explicit terminal/worktree cleanup | Decide cancellation, prove all resources reconciled, preserve evidence | `PARTIAL; CLEANUP GAP` |
| `discover` profile capability registry | No equivalent product registry | Aether owns Daimon availability, roles, profiles, tools, models and restrictions | `KEEP IN AETHER` |
| Olympus sessions/turns/tools DB | Runs, Tasks, Dispatches, messages, terminal history | Retain only privacy-safe product/evidence records not owned by Orca | `REPLACE; NO PAYLOAD MIGRATION` |
| Steering queue | Dispatch-scoped `send`, questions and replies | Prevent stale or cross-attempt guidance | `REPLACE WITH ADAPTER` |
| Harmonia start/status/stop | Run creation, supervised worker lifecycle and inspection | Hermes/Aether decides whether coordination is needed | `RETIRE HARMONIA SURFACE` |
| Harmonia deterministic candidate selection | Orca does not schedule or infer conflicts | Hermes/Aether selects participants and concurrency | `RETIRE FIXED SELECTOR` |
| Kernel event ledger and outbox | Orca durable lifecycle and message delivery | Keep only Aether semantic/evidence records needed beyond Orca | `REPLACE WITH ORCA` |
| Kernel workflow reducer | Orca task/dispatch states | Keep Aether semantic states distinct from operational states | `REPLACE + SEMANTIC ADAPTER` |
| Leases and stale-writer fencing | Active Dispatch authority, generation/capability checks, explicit takeover/retry | Verify exact attempt identity and reject stale mutations | `PARITY MUST BE PROVED` |
| Dispatch retries | `worker-start --retry-of <dispatch>` with explicit placement | Enforce attempt budget and evidence separation | `REPLACE WITH ADAPTER` |
| Closure | `worker_done` settles Task/Dispatch | Product completion and semantic acceptance remain Aether-owned | `KEEP IN AETHER` |
| Review and waivers | Worker report/message only | Independent review, typed waiver and acceptance policy | `KEEP IN AETHER` |
| Effect lifecycle | No product-effect authority | Intent, approval, execution, observation and verification remain Aether-owned | `KEEP IN AETHER` |
| Budgets | Circuit break after repeated task failures; runtime resource information | Model/cost/attempt/time budgets and compromise policy | `KEEP IN AETHER` |
| Artifact verifier and handoff digests | `--result`, `files-modified`, optional report path | Canonical bytes, digest, attempt identity, handoff validation | `GAP; KEEP AETHER VERIFIER` |
| Project principal | Repository/worktree selectors and runtime identity | Canonical `PROJECT_ROOT`, Aether installation/profile, actor policy | `KEEP IN AETHER ADAPTER` |
| Olympus observability hooks | Orca terminal/worker state and messages | Sanitization, privacy, project isolation and product evidence | `REPLACE WITH BOUNDED RECEIPTS` |
| `.aether` continuity | None | Aether continuity service and Ariadna | `KEEP IN AETHER` |
| `aether_curate` | Orca can execute a worker, not define curation | Ariadna contract, validation and projection | `REWRITE ARIADNA` |
| Self-improvement ledger/evaluation | Worktrees may help isolate a candidate | Frozen evaluation, causal comparison and promotion authority | `KEEP IN AETHER` |
| Worktree lifecycle | Native worktree create/list/use/remove flows | Authorize placement, conflicts and cleanup acceptance | `USE ORCA` |
| Terminal lifecycle | Native terminal create/send/read/wait/close | Restrict command/env/project and protected effects | `USE ORCA` |
| Browser/runtime UI | Native Orca UI/browser/PTY views | Product authority and security policy | `USE AFTER HARDENING` |
| Runtime restart and adoption | Legacy adoption, Run takeover, terminal recovery | Prevent concurrent coordinators/editors and require stable handoff | `PILOT REQUIRED` |

## 4. Semantics Orca already provides

The current CLI contract explicitly provides:

- one Run namespace/inbox;
- Task dependency graphs and statuses;
- one Dispatch per execution attempt;
- Dispatch-scoped worker completion and heartbeat;
- durable questions, replies, escalations, and delivery acknowledgments;
- supervised `worker-start` composition over worktree, setup, terminal and dispatch;
- explicit retry lineage through `--retry-of`;
- recovery inspection and bounded legacy takeover;
- worktree and terminal lifecycle operations;
- structured JSON receipts, effects and residual resource reporting.

These are strong replacement seams for ACPManager, OlympusDB, the Harmonia service, and most of the kernel's operational persistence.

### 4.1 Verified Hermes integration in the pinned AppImage

Inspection of the pinned AppImage on 2026-08-04 established that Orca treats
`hermes` as a native TUI agent. Its public startup path detects `hermes`, launches
`hermes --tui`, and uses a bounded `hermes-query` transport that constructs
`hermes chat --query=... --tui`. Orca also recognizes Hermes lifecycle/tool
hooks and provides a managed `orca-status` plugin.

This removes the need for an agent-identity shim, but does not complete the
Aether adapter:

- `worker-start --agent hermes` has no per-dispatch `HERMES_HOME` option, so
  profile-bound Aether workers initially require low-level worktree, terminal,
  and tracked Dispatch composition;
- the installed Hermes 0.19.1 has no invocation-level `--profile` flag, so an
  exact profile home must be supplied in each worker process environment;
- Orca does not currently expose native cold-resume argv for Hermes sessions;
- exact Hermes transcript sourcing is not guaranteed by `worker-read`;
- the managed status plugin can report bounded prompts, assistant responses,
  tool arguments, and tool results, which requires a privacy gate before live
  credential-bearing profiles may use it.

The product topology and implementation increments are specified in
`ORCA_SUPERVISED_SESSIONS_DESIGN.md`.

## 5. Semantics Orca does not establish for Aether

### 5.1 Product authority

Orca does not decide:

- what the user intended;
- whether a Daimon is required, allowed, disabled or forbidden;
- which model/provider is appropriate;
- whether a protected effect is authorized;
- whether a worker result is semantically acceptable;
- whether a release or activation may proceed.

### 5.2 Complete cleanup

The Orca contract states that `worker-stop` closes only the exact supervised agent terminal. It does not delete the worktree, setup terminal, configured tabs, or unrelated processes.

Aether therefore needs an aggregate `CleanupReceipt` that inspects and records, at minimum:

- agent terminal;
- setup terminal/process;
- worktree and branch;
- Dispatch terminality;
- pending messages/questions;
- temporary directories and adapter state;
- residual resources reported by failed starts;
- any legacy ACP process still attached to the same project.

Zero survivors must be demonstrated; it cannot be inferred from worker status.

### 5.3 Evidence and handoff parity

`worker_done` can include outcome, files modified and a report path, and it settles the operational Task/Dispatch. That does not provide:

- canonical artifact encoding;
- digest verification;
- immutable attempt identity inside the artifact;
- safe file opening and path containment;
- digest-bound successor handoff;
- independent semantic acceptance.

The Aether evidence envelope and verifier must remain until equivalent guarantees are implemented and tested around Orca results.

### 5.4 Project/profile isolation

Run and terminal identity do not replace canonical Aether project identity. The adapter must fail closed unless it proves:

- exact canonical `PROJECT_ROOT`;
- expected repository identity;
- dedicated `HERMES_HOME` or profile;
- allowed agent/profile/model;
- environment allowlist;
- no cross-project worktree or profile reference;
- no unapproved remote or credential-bearing environment.

## 6. Historical adapter proposal (superseded)

The adapter should be introduced under an Aether-owned namespace such as:

```text
src/aether_agents/
  contracts/
  continuity/
  evidence/
  orca/
    client.py
    schemas.py
    adapter.py
    cleanup.py
  ariadna/
  mcp/
```

The exact file split may change, but the following public values must remain stable across Orca updates:

### `AetherRunRequest`

- Aether request/contract ID;
- canonical project root;
- objective;
- authorized participants;
- protected-effect policy;
- budget;
- acceptance reference;
- rollback reference.

### `AetherTaskContract`

- immutable task ID and generation;
- exact deliverable;
- allowed and forbidden paths/effects;
- dependencies;
- attempt budget;
- evidence and completion requirements.

### `DispatchAttempt`

- Aether task/generation/attempt;
- Orca Run/Task/Dispatch IDs;
- terminal and worktree identifiers as routing metadata;
- profile/model/provider request;
- start receipt and residual resources.

### `WorkerReceipt`

- operational status;
- exact Dispatch attempt;
- outcome and structured result;
- reported files;
- questions/escalations;
- terminal/worktree state;
- uncertainty.

### `EvidenceEnvelope`

- canonical artifact identity and digest;
- Aether task generation and attempt;
- producer Dispatch;
- verifier identity/version;
- technical result;
- semantic review and acceptance state.

### `CleanupReceipt`

- all created/reused effects;
- all reconciled resources;
- survivors;
- unknowns;
- rollback result;
- timestamp and adapter/build identity.

Orca IDs must never become the sole durable identity for Aether contracts or continuity.

## 7. Required hardening before first Aether dispatch

All are mandatory for the isolated pilot:

1. pin candidate version/build and checksum;
2. verify Chromium sandbox is active on Linux;
3. use dedicated Orca state and dedicated `HERMES_HOME`;
4. fix canonical project root and cwd in the launcher/adapter;
5. default to Manual permissions; Yolo remains off;
6. disable telemetry, mobile/LAN relay, plugins and external automations;
7. disallow production remotes and credentials;
8. constrain logs/state to private local paths and permissions;
9. verify no discovery or mutation of unrelated cron, profiles, repositories or projects;
10. document and execute rollback before the Aether mirror pilot.

The prior Orca evaluation recorded a conditional pilot verdict because sandbox and cross-project/profile isolation were not yet proven. The owner's v0.22.0 direction authorizes the hardened pilot; it does not waive these gates.

## 8. Pilot equivalence cases

The minimum synthetic and Aether mirror suites must cover:

1. one Run, one Task, one worker, successful evidence and full cleanup;
2. one Run, two independent Tasks, two workers, both Dispatches settled;
3. worker question/reply without duplicate delivery;
4. explicit retry with a new attempt and no stale mutation;
5. worker failure with residual resources reconciled;
6. runtime restart and recovery without duplicate editor or concurrent authority;
7. stale terminal handle replaced without dual-send;
8. protected effect refused without Aether authorization;
9. forbidden participant rejected before worker start;
10. cross-project and cross-profile negative tests;
11. digest-bound evidence and handoff validation;
12. Ariadna curation through the new service with valid `CONTEXT.md`;
13. final zero-survivor cleanup and reversible rollback.

## 9. Kill criteria

Stop the migration and keep Olympus frozen if any of these remains unresolved:

- Orca requires Aether to surrender product or protected-effect authority;
- the Linux sandbox cannot be restored;
- project/profile isolation fails;
- restart or retry creates concurrent editors or stale mutation authority;
- attempt evidence cannot be correlated deterministically;
- cleanup leaves unknown or surviving resources;
- `.aether` must be mutated by Orca directly;
- required adapter behavior depends on undocumented internals that repeatedly drift;
- rollback cannot restore the prior Aether path without data loss.
