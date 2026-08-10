# v0.23.0 M1 Operational Entry Contract

> **Status:** FROZEN FOR IMPLEMENTATION
> **Frozen:** 2026-08-09
> **Owner:** Christopher (DarkArty07)
> **Coordinator:** Hermes
> **Candidate root:** `/home/darkarty/Desktop/agentes/aether/.aether/worktrees/v0.23.0-orca-production-cutover`
> **Predecessor:** annotated release tag `v0.22.0`, commit `719d83dab464fe2ea145aa00ef577c85f804dd57`
> **Orca binding:** desktop renderer + public structured CLI `1.4.167`

## Goal

Make the approved 15-tool Aether MCP surface executable, installable, diagnosable, reversible, and suitable for one real low-risk production Task without restoring Olympus or exposing Orca's private stores.

## Task decomposition

### Task A — M1.1 operational runtime

One writer implements only the runtime composition and FastMCP facade.

Expected primary files:

- `src/aether_mcp/runtime.py` — trusted runtime composition, state roots, public Orca transport and service routing;
- `src/aether_mcp/server.py` — exactly 15 FastMCP registrations;
- `src/aether_mcp/protocol.py` — make the approved 15 names callable without changing their schemas;
- `tests/aether_mcp/test_operational_server.py` — tool inventory, routing, envelopes, error collapse and no-side-effect bootstrap;
- focused provider/runtime tests when a seam requires them.

Permitted supporting edits are limited to existing `aether_mcp` modules and tests needed to compose the already-qualified services. No setup, live config mutation, prompt edit, worker start or activation belongs to Task A.

Acceptance:

1. MCP `tools/list` returns exactly:
   `project_admit`, `project_inspect`, `swarm_validate`, `swarm_start`, `swarm_status`, `swarm_dispatch`, `swarm_message`, `swarm_reconcile`, `swarm_retry`, `swarm_cancel`, `swarm_close`, `swarm_trace`, `orca_search`, `orca_describe`, `orca_call`.
2. Each tool routes to the existing foundation/lifecycle/worker implementation and returns real service state or a typed, secret-safe error envelope.
3. No arbitrary shell, caller-selected coordinator principal, placeholder receipt, fabricated success, private Orca store access, provider prose leak or unknown schema field is admitted.
4. Import, server construction and `tools/list` create no Run, Task, Dispatch, worker, terminal or worktree.
5. Public provider calls are bounded, structured `--json` calls to the qualified Orca interface, with timeout, output limit and strict envelope parsing.
6. State is under one explicit `AETHER_STATE_ROOT` owned by the named installation; project `.aether` history is not migrated or mutated.
7. Existing internal M2–M5 tests remain green; tests that asserted the v0.22 zero-tool boundary are updated only where the v0.23 product contract supersedes that boundary.

### Task B — M1.2 setup, status, doctor and rollback

Begins only after Task A is accepted.

Expected primary files:

- `scripts/aether_mcp/setup.py`;
- `scripts/aether_mcp/status.py`;
- `scripts/aether_mcp/doctor.py`;
- `scripts/aether_mcp/rollback.py`;
- focused tests using temporary `HERMES_HOME` and fake/public CLI seams;
- user-facing documentation under `docs/releases/v0.23.0/`.

Acceptance:

1. Install and registration are idempotent and preserve an exact pre-change backup.
2. Registration alone starts no worker and performs no project mutation.
3. Status reports Aether version, prompt version/hash, Orca version/profile/binding, tool inventory, config target and state root without secret values.
4. Doctor proves server startup, MCP initialize/tools-list, Orca readiness, state permissions and stale-resource inventory.
5. Rollback removes only the named Aether MCP registration and attempt-owned wrapper/process resources while preserving project data, historical `.aether` stores and redacted diagnostics.
6. Restart/rebind and rollback are exercised before live activation is accepted.

### Task C — Prompt candidate and controlled comparison

Hermes owns this task; workers may not change its cases, evaluator or thresholds.

- Baseline: active `home/SOUL.md` version `2.0.0`, SHA-256 `d981f4e805caa6dee222093cfcc0073aa8fbc6b2864c22335e104ec20e8be31a`.
- Candidate: `3.0.0`, because routing/delegation authority changes from Olympus/Harmonia to Aether MCP/Orca.
- Hypothesis and thresholds are frozen in `prompt/PROMPT_3_0_0_EXPERIMENT.yaml`.
- Cases are frozen in `prompt/cases.json`.
- The candidate is not copied to the active `HERMES_HOME/SOUL.md` until the A/B gate passes.

### Task D — M1.3 first real Task

Begins only after Task A, Task B, offline validation and explicit activation.

Required path:

`Hermes -> installed Aether MCP -> Orca Run/Task/Dispatch -> generic worker -> artifact/evidence -> Hermes verification -> semantic close -> cleanup`

The Task must be real, low-risk, local and reversible. A synthetic fixture can support diagnosis but cannot replace this path.

## Authorized effects

- Source edits and local commits in the isolated v0.23 worktree.
- Existing-provider model use needed for the bounded implementation worker and frozen prompt A/B.
- Orca Run/Task/Dispatch/worktree resources required by this contract.
- Registration and restart/rebind of the named local Aether installation after offline gates pass.
- Reversible replacement of active `SOUL.md` only after prompt acceptance.

Not authorized by this contract: push, merge, tag, GitHub Release, deployment, credential creation/rotation, PAYG enablement, model/account substitution, historical state migration, or unrelated cleanup.

## Rollback source

- Source: `v0.22.0` / `719d83dab464fe2ea145aa00ef577c85f804dd57`.
- Active prompt: pre-change byte-for-byte `SOUL.md` baseline hash above.
- Runtime config: pre-change `home/config.yaml` backup with mode preserved.
- Registration: remove only `mcp_servers.aether_mcp` and restore the exact prior tools lists if changed.
- Orca: stop and remove only Run/Task/Dispatch/terminal/worktree resources correlated to the M1 operation IDs.

## Stop condition

Stop M1 expansion when one named installation has: exactly 15 real Aether MCP tools, passing offline gates, verified restart/rebind, one verified real Task, semantic close, zero attempt-owned survivors, and a tested non-destructive rollback. Do not enter roster qualification or v0.24 workflow migration in this Task.
