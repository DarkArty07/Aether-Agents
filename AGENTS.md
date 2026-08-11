# Aether repository contract

This file describes the current repository and runtime. Historical release evidence and superseded decisions are context only.

## Source of truth

Use this precedence when claims disagree:

1. the user's current explicit instruction;
2. safety, permissions and exact project boundaries;
3. executable source, schemas, tests and observed runtime status;
4. current product/architecture documents and accepted decisions;
5. release evidence and historical records.

Never describe a planned, historical or merely installed capability as active without executable evidence.

## Current runtime

- Product source: `0.23.0.dev0` on local `main`.
- Active prompt: `home/SOUL.md`, Hermes Prompt SemVer `3.0.0-hot.3`.
- MCP surface: 15 tools, registered in the named local Hermes runtime.
- Allowed profiles: Hefesto, Daedalus and Ictinus.
- Retired paths: Olympus, ACPManager, Harmonia, `talk_to`, Honcho, `aether_status`, `aether_update` and `aether_curate`.
- Runtime state: machine-local under `home/`; never commit credentials, databases, sessions, logs or installed binaries.

The qualified provider is a runtime dependency, not product authority. Hermes owns intent, scope, routing and semantic acceptance. Aether MCP owns admission, typed operations and trace. The provider owns its execution resources.

## Repository topology

Maintain this project from the single checkout at `/home/darkarty/Desktop/agentes/aether`. Do not create a new worktree or hand work to another agent unless the user explicitly requests it. Preserve unrelated local runtime state.

Local implementation does not authorize push, pull request, merge, tag, publication, activation, restart, migration, spending or credential changes.

## Change discipline

- Resolve the exact project root before acting.
- Read the nearest contract, affected source and tests before changing shared behavior.
- Keep source, templates, docs and tests synchronized.
- Use current names and identities; do not reintroduce retired aliases or compatibility shims.
- Treat unknown mutation effects as non-retryable until reconciled.
- Use the smallest verification that covers the actual failure modes; run the full suite for shared runtime or contract changes.
- Do not edit generated runtime state to make a source test pass.

## Definition of done

A change is done when the requested outcome exists, relevant tests/checks pass, current docs match runtime truth, no secret or generated state is staged, and remaining limitations are stated plainly.
