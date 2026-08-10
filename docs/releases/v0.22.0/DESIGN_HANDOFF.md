# v0.22.0 CLI-First Design Session Handoff

> **Status:** SUPERSEDED HISTORICAL HANDOFF — ADR-0001 REJECTED THE CLI-FIRST CONTROL BOUNDARY ON 2026-08-06
> **Date:** 2026-08-06
> **Project root:** `/home/darkarty/Desktop/agentes/aether/.aether/worktrees/feature-v0.22.0-orca-transition`
> **Branch:** `feature/v0.22.0-orca-transition`
> **HEAD:** `99653b2e1c9c4e5e7c50e7be93a06cbc48156316`
> **Upstream:** `origin/feature/v0.22.0-orca-transition`
> **Current authorization:** Documentation and roadmap design only

This file preserves the prior session's state and rationale. It is not current
architecture or resume authority. Continue from:

- `docs/decisions/ADR-0001-aether-mcp-control-and-trace-plane.md`;
- `docs/architecture/AETHER_MCP.md`;
- `docs/reference/AETHER_MCP_CONTRACT.md`;
- `docs/reference/AETHER_TRACE_SCHEMA.md`;
- `docs/reference/AETHER_LEARNING_EPISODE_SCHEMA.md`;
- `docs/releases/v0.22.0/ROADMAP.md`.

Statements below that reject an Aether MCP or prescribe CLI-first control are
historical and explicitly superseded.

The owner additionally clarified on 2026-08-06 that the primary trace purpose is
system learning/refinement and future fine-tuning evidence, not audit alone. The
current design therefore separates compact semantic events from protected rich
learning episodes and versioned dataset lineage. No capture, training or
promotion implementation is authorized.

## 1. Session result

The session completed the documentation-only design of the v0.22.0
Hermes-led Orca swarm.

Established current target:

```text
User
  -> Hermes product contract and task selection
  -> Orca Run / Task / Dispatch / worker mechanics
  -> profile-bound Hermes workers in isolated worktrees
  -> bounded messages, questions, retries, recovery, and cleanup
  -> Hermes evidence review, synthesis, and semantic acceptance
  -> user acceptance
```

Aether remains the product layer: product intent, Hermes identity, profiles,
skills, policy, participant selection, synthesis, and acceptance. Orca is the
operational control plane. No Aether-owned Python runtime, MCP facade, private
ledger, or hidden Olympus/Harmonia fallback is approved.

## 2. Version boundary proposed for owner review

The canonical `ROADMAP.md` assigns all work required for a usable swarm to
v0.22.0:

- M0 — design closure and exact P0 runbook;
- M1 — isolated Orca lifecycle and rollback;
- M2 — public JSON control contract and least privilege;
- M3 — one synthetic Hermes worker;
- M4 — two-worker parallel swarm, messaging, retry, and recovery;
- M5 — retained Aether roster integration and physical retirement;
- M6 — Independent Verifier and Ariadna disposition;
- M7 — clean installation and on-demand usability;
- M8 — exact-candidate acceptance;
- M9 — integration and v0.22.0 publication.

M10, enabling the released capability in a persistent user installation and any
later automatic-activation decision, remains a separate operational effect.
The v0.22.0 candidate still requires real isolated Orca pilots before release.

The candidate must not close merely because Olympus was removed or the design is
complete. If a required M0–M9 gate remains unresolved, v0.22.0 remains
unreleased unless the product owner explicitly revises, abandons, or supersedes
its scope.

## 3. Canonical current documents

- `docs/decisions/PDR-0012-hermes-orca-swarm-boundary.md`
- `docs/decisions/PDR-0013-swarm-roster-and-personality-model.md`
- `docs/architecture/DAIMONS.md`
- `docs/architecture/ORCHESTRATION.md`
- `docs/releases/v0.22.0/ROADMAP.md`

The previous cumulative roadmap was preserved, not deleted, as:

- `docs/releases/v0.22.0/HISTORICAL_RETIREMENT_ROADMAP.md`

It is historical evidence and not current implementation authority.

## 4. Roster decision represented in the design

- Hermes — product-facing supervisor; not a Daimon.
- Hefesto — retained implementation archetype.
- Daedalus — retained UX and product-flow archetype.
- Ictinus — retained backend/data/architecture archetype.
- Athena — target state `RETIRED`, participant policy `FORBIDDEN`.
- Etalides — target state `RETIRED`, participant policy `FORBIDDEN`.
- Ariadna — `DISABLED` pending a measured release disposition.
- Independent Verifier — proposed; profile, name, benchmark, and authority
  boundary remain to be implemented and accepted.

No profile file was changed or removed during this session.

## 5. Control-surface decision represented in the roadmap

The proposed v0.22.0 default is CLI-first:

```text
Hermes
  -> version-matched Orca `orchestration` / `orca-cli` guides
  -> public structured Orca operations
  -> Orca runtime
```

There is no approved Aether-owned MCP. An official Orca MCP or minimal wrapper
may be considered only after executed evidence proves one exact required CLI
capability is missing. It may not duplicate Orca state or gain product
authority.

The exact CLI commands are intentionally not frozen from memory. M0 must obtain
them read-only from the installed Orca binary and record them in
`P0_ORCA_LIFECYCLE_RUNBOOK.md` before any runtime start.

## 6. Current working-tree state

The documentation set is intentionally uncommitted. It includes:

- reconciled product, architecture, authority, and knowledge documents;
- reconciled PDR-0012 and decision index;
- new PDR-0013;
- new `DAIMONS.md` and `ORCHESTRATION.md`;
- new canonical v0.22.0 roadmap;
- preserved historical retirement roadmap;
- supersession notices on prior Orca research artifacts;
- this handoff.

No source code, script, test, configuration, runtime profile, website code, or
protected `.aether` store was changed. No Orca process, worker, terminal,
worktree, server, or runtime was started. No commit, push, PR, merge, tag,
Release, deployment, credential operation, migration, or spend occurred.

Do not manually update `.aether/CONTEXT.md` or its databases. This candidate has
no accepted Aether continuity reader/writer. Versioned documents are the durable
handoff surface.

## 7. Verification completed before handoff

- `pytest -q tests/test_post_olympus_residue_retirement.py` — 13 passed;
- `git diff --check` — PASS;
- changed-path type guard — Markdown only;
- roadmap milestone/invariant check — PASS;
- changed-document local-link check — 39 links, 0 missing;
- all five session tasks — completed;
- non-document implementation or runtime effects — none.

These are documentation gates only. They are not Orca runtime, worker, release,
or activation evidence.

## 8. Resume sequence

On resume:

1. confirm this exact project root, branch, HEAD, upstream, and dirty paths;
2. read this handoff;
3. read `docs/releases/v0.22.0/ROADMAP.md`;
4. review the version boundary and M0–M10 separation with the product owner;
5. apply any owner-requested roadmap corrections;
6. rerun the documentation gate;
7. stop for acceptance of the final roadmap.

If the product owner accepts the roadmap, that authorizes M0 completion only:

1. record CLI-first/no-Aether-MCP as an approved architecture decision;
2. perform read-only executable/status discovery;
3. load the exact version-matched Orca guides;
4. draft `P0_ORCA_LIFECYCLE_RUNBOOK.md` with exact commands, sandbox, expected
   effects, evidence, cleanup, and rollback;
5. review the runbook before starting Orca.

Acceptance of the roadmap does not by itself authorize M1 runtime start. M1
requires separate approval of the exact P0 runbook. Workers remain blocked until
their corresponding later milestone gate.

## 9. Immediate product-owner questions

The next session should confirm or adjust only these material points:

1. Must M0–M9 remain mandatory for the v0.22.0 Release?
2. Is CLI-first/no-Aether-MCP accepted as the initial control boundary?
3. Is physical retirement of Athena and Etalides required in M5?
4. Must the Independent Verifier prove value in v0.22.0 unless scope is
   explicitly revised?
5. Must Ariadna receive a final evidence-backed disposition before release?
6. Is persistent-installation enablement correctly separated as M10?

Until those questions are resolved, the correct next state is documentation
review, not implementation or operation.