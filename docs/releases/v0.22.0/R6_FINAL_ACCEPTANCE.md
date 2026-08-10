# R6 — Adaptive Orca Redesign Final Acceptance and Handoff

> **Status:** CLOSED WITH BLOCKED PRODUCT GATE
> **Date:** 2026-08-08
> **Audited input commit:** `fc4c5b1880eed956ce6e9a4dfd6a14ed07f08445`
> **Audited input tree:** `eb6753ebc7c3de0e0f9992e943f8e808c1220029`
> **Branch:** `feature/v0.22.0-orca-transition`
> **Integration/activation:** NOT AUTHORIZED / NOT PERFORMED
> **D1:** FALSE

## 1. Final result

The bounded redesign is complete at the architecture, successor-protocol and
restricted-foundation levels.

It is **not accepted as working provider-backed agent orchestration**.

Accepted:

- Aether/Hermes owns product intent, authority, contracts, correlation, journal,
  receipts, reconciliation and acceptance;
- Orca remains the sole mutable runtime authority;
- the operational MCP catalog is reduced from the historical 24 tools to 15;
- `aether.mcp/v1alpha2` implements those 15 schemas while preserving the historical
  `v1alpha1` bundle byte-for-byte;
- the local adapter foundation implements exact build/binding validation,
  immutable argv, append-before-effect, atomic intent fencing, idempotency,
  `UNKNOWN`, tamper-evident receipts and injected read-only reconciliation;
- all current provider mutations remain unavailable and MCP remains zero-tool.

Blocked:

- Orca `serve` headless did not prove a public way to admit the live coordinator
  terminal required by orchestration mutations;
- therefore the full Run/Task/restart/cancel/cleanup lifecycle was not accepted;
- therefore the two-worker provider-backed R5 slice was not executed;
- D1 and activation remain blocked.

## 2. Milestone disposition

| Milestone | Final state | Evidence |
|---|---|---|
| R0 | `COMPLETED` | frozen plan, isolated worktree and boundaries |
| R1 | `COMPLETED` | 15-tool design, three-axis 55-capability matrix, debt and revised D1 |
| R2 | `COMPLETED` | `v1alpha2`, 15 schemas, historical alpha1 preserved, zero tools |
| R3 | `CLOSED_BLOCKED` | framing fixed/cold status proven; coordinator bootstrap unqualified |
| R4 | `COMPLETED_RESTRICTED` | local journal/planner/reconciler; mutations unavailable |
| R5 | `CLOSED_BLOCKED_NOT_EXECUTED` | no trusted coordinator; zero workers/models/effects |
| R6 | `CLOSED_WITH_BLOCKED_PRODUCT_GATE` | final local audit and handoff |

A blocked later milestone does not invalidate lower-level deterministic evidence,
but lower-level evidence is not relabeled as orchestration acceptance.

## 3. Delivered architecture

```text
Hermes
  └─ product contract / DAG / authority / acceptance
       └─ Aether MCP v1alpha2 (15 schemas, 0 registered)
            └─ restricted planner + operation journal + reconciler
                 └─ [MUTATIONS UNAVAILABLE: coordinator binding unqualified]
                      └─ Orca 1.4.167 public structured primitives
```

No second Aether Run/Task scheduler or private Orca database was introduced. The
journal contains operation intent, digests, receipts and reconciliation results;
it does not claim mutable provider runtime state.

## 4. Protocol and capability result

Operational public schemas:

```text
project_admit
project_inspect
swarm_validate
swarm_start
swarm_status
swarm_dispatch
swarm_message
swarm_reconcile
swarm_retry
swarm_cancel
swarm_close
swarm_trace
orca_search
orca_describe
orca_call
```

Disposition of the nine removed/deferred names:

- decision/evidence append actions are absorbed by `swarm_trace`;
- Orca batch/events are internal adapter concerns;
- project forget is a future protected owner/admin boundary;
- four learning operations move to a future separate default-off boundary.

Capability design totals:

- delivery: `49 NATIVE`, `4 COMPOSED`, `2 AETHER_OWNED`;
- guarantee target: `49 FULL`, `6 DEGRADED`;
- qualification: `55 UNQUALIFIED`, `0 PROVEN`, `0 UNKNOWN`;
- cross-cutting coordinator binding: additionally `UNQUALIFIED`.

The qualification axis is the authoritative readiness signal. Delivery class does
not imply that a capability works.

## 5. Verification

Canonical local gate on the audited input:

```text
pytest:                 125 passed, 1 deselected
Ruff:                   PASS
compileall:             PASS
sdist:                  PASS
wheel:                  PASS
clean wheel install:    PASS
clean wheel imports:    PASS
stdio default-off:      exit 0, stdout/stderr empty
operational schemas:    15
registered tools:       0
callable tools:         0
changed secret hits:    0
runtime survivors:      0
```

Schema evidence:

```text
v1alpha1 SHA-256:
e7f39a76ac4795ade2ec0a15bf64b4cab2233b912cf2285b0ce76d2805a2e605

v1alpha2 SHA-256:
336e141d56563da882ae7426ae2a0b8647aef501962a56357f11652265d05723
```

`v1alpha2` regeneration is byte-exact. The installed Orca launcher/AppImage still
match the pinned R3 identity.

## 6. Isolation and Git state

- Main checkout retained at
  `a88b5ccefe317b5794a445c117b89b570f7845c4` on
  `docs/canonical-product-documentation`.
- Redesign work happened only in
  `.aether/worktrees/feature-v0.22.0-orca-redesign`.
- The local feature branch is six commits ahead of remote before the R6 closeout
  commit.
- Draft PR #163 remains open/draft and its five green checks cover only remote
  `b807c62`, not the local redesign commits.
- No push, merge, rebase, amend, tag, Release, deployment or activation occurred.

The retained Git worktree is the reproducible delivery artifact, not a leaked Orca
runtime resource.

## 7. Security and cleanup

The changed-file audit found zero credential/private-key shapes. The adapter and
journal import no subprocess, socket or HTTP client and do not read ambient
environment variables. No shell executor or private Orca DB/IPC access exists.

Final cleanup:

```text
task processes:          0
task mounts:             0
task temporary roots:    0
task Xvfb resources:     0
ignored build/caches:    0
```

The final blocked R3 probes did not complete the protected-metadata before/after
comparison, so that evidence remains `UNKNOWN`; it is not reported as unchanged.
The private mount namespace used a read-only staged home and cleanup is zero.

## 8. Reproducible local handoff

From the retained feature worktree:

```bash
export PYTHONPATH=src
export UV_CACHE_DIR=/tmp/aether-r6-recheck-cache
uv run --no-project --with 'pytest>=8,<9' --with 'mcp==1.28.1' \
  python -m pytest -q \
  -k 'not test_real_candidate_lifecycle_executes_without_skip_and_cleans'
uv run --no-project --with 'ruff>=0.14,<1' \
  ruff check src/aether_mcp scripts/aether_mcp tests/aether_mcp
python3 -m compileall -q src/aether_mcp scripts/aether_mcp tests/aether_mcp
```

The excluded test requires reconstruction of the signed ephemeral Xvfb fixture and
still closes blocked at coordinator admission; it must not be represented as a
passing orchestration probe.

## 9. Next product gate

One of these must be explicitly authorized and proven before R5-R1:

1. Orca exposes a versioned public headless coordinator-admission primitive; or
2. an isolated desktop/UI-backed qualification is authorized with a trusted live
   Orca terminal, exact identity pinning, no credentials/models, and the same
   rollback/cleanup requirements.

Only after that evidence may the two-worker slice run. Push/PR update, D1,
registration, activation and Release remain separate later gates.

## 10. Stop condition

R0-R6 are closed for the current authorization. The local redesign candidate and
its evidence are reproducible. The product gate is honestly blocked. Stop here;
do not expand into integration, activation, UI automation or a model-backed pilot.
