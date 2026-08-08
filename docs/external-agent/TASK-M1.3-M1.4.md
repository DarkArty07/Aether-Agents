# TASK M1.3–M1.4 — Isolated Orca lifecycle qualification and provider verdict

> **Status:** AUTHORIZED / FROZEN
> **Authorized by:** Christopher (DarkArty07)
> **Authorization date:** 2026-08-08
> **Executor and evidence owner:** Hermes
> **Baseline:** `ab276b8f0f5e252f71b3f6ba43fbd8877230aac3`
> **Branch:** `feature/v0.22.0-orca-transition`
> **Draft PR:** #163

## 1. Goal

Complete exactly two milestones:

1. **M1.3:** qualify cold start, status, restart, stop, rollback and cleanup for the exact authenticated Orca 1.4.167 candidate inside an M1-owned temporary root.
2. **M1.4:** reconcile the observed public command schemas and the six M1.2 missing aggregate seams, then issue a fail-closed technical verdict for the product owner.

Stop after M1.4. The executor must not grant D1, implement an adapter, begin M2.3 or M3, register/activate MCP, merge, tag, Release or operate an installed/global Orca runtime.

## 2. Governing authority

- `docs/releases/v0.22.0/ORCA_PROVIDER_MANIFEST.json`
- `docs/releases/v0.22.0/M1_1B_ACCEPTANCE.md`
- `docs/releases/v0.22.0/M1_ORCA_PROVIDER_SEAM_MATRIX.json`
- `docs/releases/v0.22.0/M1_2_INDEPENDENT_REVIEW.md`
- `docs/releases/v0.22.0/M0_PROVIDER_SEAM_AMENDMENT.md`
- `docs/releases/v0.22.0/ROADMAP.md`, M1.3 and M1.4

Current user intent supersedes stale passages that still say M1.3 is unauthorized. This task and the authority reconciliation committed with it replace those stale passages only for M1.3 and M1.4.

## 3. Exact candidate and isolation

Before every real fixture:

- verify launcher path, size and SHA-256;
- verify AppImage path, size and SHA-256;
- verify the canonical manifest digest and Orca product/catalog identity;
- reject symlinks, non-executables, identity drift and unexpected environment roots.

Every child receives only an explicit environment rooted below one `mkdtemp` directory under `/tmp`, including `HOME`, all XDG roots and `TMPDIR`. Runtime traffic is limited to one harness-selected loopback port. Pairing is disabled. No credential, account, model, worker, browser, GUI or remote environment is admitted.

The harness owns the foreground `serve` child and its process group. It may send bounded `SIGINT`, then `SIGTERM` and finally `SIGKILL` only to that owned group. Broad name-based process termination is forbidden.

## 4. Authorized public commands

Only the exact authenticated launcher may execute these command families in the isolated fixture:

- `agent-context --json`;
- `serve --port <loopback-port> --no-pairing --project-root <isolated-project> --json`;
- `status --json`;
- `orchestration run-create|run-current|run-list|run-show|run-use`;
- `orchestration task-create|task-list|task-update`;
- `orchestration reset --tasks|--messages|--all`;
- read-only `orchestration inbox|gate-list`;
- read-only `terminal list`, `worktree list`, and `worktree ps`.

`serve` is stopped only by the documented foreground `Ctrl+C` equivalent delivered to the owned child group. The fixture may create only synthetic Run/Task records containing fixed non-sensitive text.

Not authorized: dispatch, worker start, terminal create/send, worktree/repo/project creation or removal, account/environment mutation, automation, browser/computer/emulator use, GUI startup, private storage access, arbitrary shell execution, installed/global state writes, credentials, models or external network access.

## 5. M1.3 behavioral contract

The implementation must provide one reusable repository script and durable tests.

### Required positive path

1. Prove exact candidate identity.
2. Capture an opaque before-fingerprint of installed/global Orca state without storing private content.
3. Cold-start the foreground headless runtime in an isolated root.
4. Poll structured status to readiness with a bounded timeout.
5. Create one synthetic Run and one synthetic Task using public commands.
6. Read the Run/Task and the admitted read-only inventory projections.
7. Stop the runtime through the owned foreground process boundary.
8. Restart against the same isolated root and prove the Run/Task state is either durably recovered or explicitly absent with a structured, classified result; never infer success from silence.
9. Exercise only documented reset scopes and record exact results.
10. Stop again, remove the entire isolated root, prove cleanup idempotent, zero owned processes/listeners/mounts/roots survive, and the protected before/after fingerprints match.

### Fault matrix

Durable tests must cover:

- launcher/AppImage/manifest drift before execution;
- malformed structured output;
- startup timeout;
- child exit before readiness;
- killed qualification/harness path;
- partial isolated state creation;
- response timeout classified `UNKNOWN` rather than retried blindly;
- surviving owned descendant cleanup;
- repeated stop/cleanup;
- ambient or out-of-root path rejection;
- global state fingerprint drift rejection;
- schema drift and unknown required fields fail closed.

Synthetic fixtures may emulate Orca for deterministic unit tests. At least one real exact-candidate fixture must execute the authorized lifecycle; no mandatory real test may be converted to a skip when the canonical candidate is present.

## 6. Six missing aggregate seams

M1.3 must evaluate, separately and explicitly:

1. `events_read`;
2. `resource_inventory`;
3. `resource_cleanup`;
4. `run_cancel`;
5. `run_close`;
6. `task_cancel`.

Each receives exactly one verdict:

- `PROVEN_COMPOSED`: the isolated fixture proves an ordered public-command plan, preconditions, step identities, effects, timeout/UNKNOWN handling, reconciliation, cleanup, partial-result semantics and rollback limits; or
- `UNSUPPORTED`: the evidence cannot prove semantic equivalence safely.

An empty fixture, a successful low-level command, human prose or absence of survivors cannot by itself prove a general aggregate. `task-update --status failed`, `orchestration reset`, harness-owned process termination and root deletion must not be renamed as provider-native cancel/close/cleanup semantics.

## 7. M1.4 decision rule

M1.4 produces a version-pinned schema/evidence bundle and one technical verdict:

- `D1_READY_FOR_OWNER_DECISION` only if all M2–M5 required provider capabilities are either public structured native seams or accepted `PROVEN_COMPOSED` plans, with lifecycle rollback and zero survivors proven; or
- `D1_BLOCKED_PROVIDER_SEAM_INSUFFICIENT` if any required seam remains partial, missing, ambiguous or unqualified.

Hermes may recommend a product decision but must not grant D1. Only the product owner decides whether to require an Orca change, reduce scope, replace the provider or authorize a revised design.

## 8. Planned repository scope

Implementation/evidence may touch only:

- `scripts/aether_mcp/qualify_orca_lifecycle.py`;
- `tests/aether_mcp/provider/test_lifecycle_qualification.py`;
- `docs/releases/v0.22.0/M1_3_LIFECYCLE_EVIDENCE.json`;
- `docs/releases/v0.22.0/M1_3_ACCEPTANCE.md`;
- `docs/releases/v0.22.0/M1_4_PROVIDER_DECISION.md`;
- this task file;
- authority/status summaries in `AGENTS.md`, `ROADMAP.md` and `STATUS.yaml`;
- exact workflow/source-inventory allowlists only if the new tracked script/test requires them.

No `src/aether_mcp` implementation change is allowed. M1.3/M1.4 qualify the provider; they do not implement the provider adapter.

## 9. TDD and commits

Required chronology:

1. commit this frozen authorization/contract reconciliation;
2. add behavioral tests and observe an intended RED before production script code;
3. implement the minimum reusable lifecycle qualifier;
4. commit M1.3 technical implementation and evidence only after focused/full gates;
5. independently re-read artifacts and produce the M1.4 documentary verdict;
6. validate the exact final commit in a detached clean checkout;
7. push the existing Draft PR, wait for terminal CI, clean owned temporaries and stop.

No amend, rebase, force-push, merge, tag or Release.

## 10. Stop condition

Stop immediately after M1.4 evidence, exact-commit verification, Draft PR update, terminal CI and cleanup. Report:

- exact commits and tests;
- protected-state and zero-survivor evidence;
- each missing-seam verdict;
- D1 technical readiness or blocker;
- the bounded product choices.

Do not start any later milestone while waiting for the owner's decision.
