# v0.22.0 M0 MCP-First Design Acceptance

> **Status:** ACCEPTED HISTORICAL DESIGN BASELINE — VERSION PLACEMENT PARTIALLY SUPERSEDED BY PDR-0014
> **Accepted:** 2026-08-06
> **Owner:** Christopher (DarkArty07)
> **Candidate branch:** `feature/v0.22.0-orca-transition`
> **Implementation authorization:** M1.1 repository task only

## Accepted product boundary

The product owner accepted the detailed MCP-first architecture, contracts,
measurement model, frozen use-case catalog and M1–M12 roadmap on 2026-08-06.
PDR-0014 later preserves the architecture and accepted M0-M5.4 evidence while
superseding the placement of former M6-M12 inside v0.22.0.

The accepted topology is:

```text
User
  -> Hermes product intent, Task design, routing, supervision and synthesis
  -> Aether MCP typed control, validation, trace and learning-data plane
  -> Orca operational Run / Task / Dispatch / worker mechanics
  -> Task-bound temporary workers
  -> artifacts and executed evidence
  -> Hermes review and user acceptance
```

This acceptance preserves the following boundaries:

- Hermes owns product meaning, Task decomposition, participant selection,
  integration and acceptance synthesis.
- Aether MCP owns typed product operations, deterministic validation, operation
  receipts, semantic trace and admitted protected learning episodes/datasets.
- Orca remains the sole owner of mutable Run, Task, Dispatch, worker, message,
  terminal, worktree, recovery and cleanup state.
- Olympus, Harmonia, ACPManager, `talk_to` and the disconnected Aether-native
  runtime remain retired without compatibility or failure fallback.
- Release, persistent activation, credentials, spending, data migration,
  external upload, training, fine-tuning and model promotion remain separate.

## Accepted M0 artifacts

- `../../decisions/ADR-0001-aether-mcp-control-and-trace-plane.md`
- `../../architecture/AETHER_MCP.md`
- `../../architecture/ORCHESTRATION.md`
- `../../reference/AETHER_MCP_CONTRACT.md`
- `../../reference/AETHER_TRACE_SCHEMA.md`
- `../../reference/AETHER_LEARNING_EPISODE_SCHEMA.md`
- `MEASUREMENT_CONTRACT.md`
- `USE_CASE_CATALOG.md`
- `HISTORICAL_M0_M12_ROADMAP.md`
- `HISTORICAL_M0_M12_STATUS.yaml`

The accepted design freezes 24 MCP tools, 16 use cases, seven authority gates
(`D0`–`D6`), the M0–M11 source/Release path and separately gated M12 activation.
At this M0 boundary, acceptance did not claim that any MCP package, fixture,
store, tool, worker or runtime existed. Later evidence through M5.4 is governed by
the current `ROADMAP.md` and `RELEASE_BOUNDARY.md` rather than by this historical
implementation authorization.

## 2026-08-09 scope amendment

The product owner closed v0.22.0 capability scope at the accepted M5.4 Orca
integration boundary. Former M6-M12 work moved or split across v0.23.0, v0.24.0
and a separately deferred learning-dataset program. See PDR-0014. The remaining
v0.22.0 work is exact source acceptance and publication only; this historical M0
record does not authorize current implementation.

## Stepwise external-agent implementation protocol

The product owner selected a repository-local external coding agent for faster
implementation. Hermes remains the sole orchestrator and acceptance authority.

1. Hermes prepares one immutable, self-contained task at a time with exact root,
   branch, baseline, allowed paths, forbidden effects, tests and report schema.
2. The external agent implements only that task, may create atomic English
   Conventional Commits, writes its report and stops.
3. The external agent may not push, merge, rebase, amend, tag, create or switch
   branches/worktrees, start the next task, or touch protected local data.
4. Hermes inspects the real commits and test bodies, reruns every decision-critical
   gate and classifies the result as accepted, correction required or blocked.
5. Hermes issues the next prompt only after the current task is independently
   accepted. A successor agent is assumed to have no prior conversational state.

## Current implementation authorization

Only **M1.1 — Freeze source and executable identity** is authorized now.

M1.1 may:

- create the roadmap-declared qualification script, deterministic tests and M1
  evidence artifacts;
- inspect the installed Orca executable/AppImage, version, digest and public
  catalog metadata through read-only operations;
- use repository-local or temporary test state that is created and cleaned by
  the task;
- create branch-local atomic commits for the exact task.

M1.1 may not:

- start or open the Orca runtime, create a Run/Task/Dispatch or launch a worker;
- create `src/aether_mcp`, install dependencies or register an MCP server;
- mutate global/installed Orca state, configuration, profiles, credentials,
  protected `.aether` stores, historical evidence or another project;
- use network/provider/model calls, incur spending, push, open a PR, merge, tag,
  Release, deploy or activate anything;
- begin M1.2 or any later package.

## Stop condition

M1.1 stops after its report and branch-local commits exist. Hermes must then
audit the exact candidate and independently reproduce the gates. Only an
accepted M1.1 permits creation of the separate M1.2 prompt.
