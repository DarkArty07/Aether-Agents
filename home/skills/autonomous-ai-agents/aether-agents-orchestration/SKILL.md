---
name: aether-agents-orchestration
description: "Use when coordinating Aether specialists. Enforces the Hermes-Orca boundary."
version: 2.1.0
---

# Aether execution boundary

## Current truth

The v0.22.0 candidate has no specialist execution runtime, native Python core, continuity plugin, Aether MCP facade, or compatibility fallback. `talk_to`, `discover`, ACPManager, Harmonia, and ACP-backed curation are absent, not disabled. PDR-0012 assigns product judgment to Hermes/Aether and targets Orca for Run, Task, Dispatch, worker, message, worktree, recovery, and cleanup mechanics after separate acceptance.

## Procedure

1. Resolve the exact `PROJECT_ROOT`.
2. Inspect the tools actually available in the current runtime; do not infer them from a profile name or historical documentation.
3. If Hermes can complete a bounded task directly with proportional evidence, do so.
4. If the task materially requires an unavailable specialist, stop with an explicit capability gap.
5. Never restore a retired module, tool name, wrapper, plugin, database, or process solely to obtain delegation.
6. Never use another project's runtime or profile as an Aether fallback.
7. Preserve profile definitions, skills, product decisions, and acceptance policy independently of execution availability.
8. When the accepted Orca path exists, create all independent Tasks and Dispatches before waiting, allow direct/group worker messaging, and use child worktrees for potentially conflicting writers under one feature integration branch.

## Verification

Before claiming specialist execution is available, require deterministic evidence for the exact candidate covering project/profile isolation, task authority, messaging, retries, restart recovery, stale-worker fencing, cancellation, cleanup, zero survivors, and rollback.

## Forbidden shortcuts

- compatibility shims under a renamed package;
- a disconnected Aether policy kernel or pre-emptive stable adapter API;
- hidden ACP or legacy-store fallback;
- treating a profile definition as a running worker;
- treating terminal/process completion as semantic acceptance;
- activating Orca, credentials, deployment, or production runtime without the corresponding gate.
