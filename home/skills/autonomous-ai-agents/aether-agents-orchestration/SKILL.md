---
name: aether-agents-orchestration
description: "Use when coordinating Aether specialists. Enforces the current runtime boundary."
version: 2.0.0
---

# Aether execution boundary

## Current truth

The v0.22.0 candidate has no specialist execution runtime, Aether MCP facade, or compatibility fallback. `talk_to`, `discover`, ACPManager, Harmonia, and ACP-backed curation are absent, not disabled.

## Procedure

1. Resolve the exact `PROJECT_ROOT`.
2. Inspect the tools actually available in the current runtime; do not infer them from a profile name or historical documentation.
3. If Hermes can complete a bounded task directly with proportional evidence, do so.
4. If the task materially requires an unavailable specialist, stop with an explicit capability gap.
5. Never restore a retired module, tool name, wrapper, plugin, database, or process solely to obtain delegation.
6. Never use another project's runtime or profile as an Aether fallback.
7. Preserve profile definitions and Aether product contracts independently of execution availability.

## Verification

Before claiming specialist execution is available, require deterministic evidence for the exact candidate covering project/profile isolation, task authority, messaging, retries, restart recovery, stale-worker fencing, cancellation, cleanup, zero survivors, and rollback.

## Forbidden shortcuts

- compatibility shims under a renamed package;
- hidden ACP or legacy-store fallback;
- treating a profile definition as a running worker;
- treating terminal/process completion as semantic acceptance;
- activating Orca, credentials, deployment, or production runtime without the corresponding gate.
