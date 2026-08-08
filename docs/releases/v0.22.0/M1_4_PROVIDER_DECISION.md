# M1.4 — Orca provider decision

> **Milestone status:** CLOSED
> **Technical verdict:** `D1_BLOCKED_PROVIDER_SEAM_INSUFFICIENT`
> **D1 granted:** No
> **Decision owner:** Christopher (DarkArty07)
> **Owner decision:** REQUIRED
> **Adapter authorized:** No

## 1. Decision rule

M1.4 may recommend `D1_READY_FOR_OWNER_DECISION` only when every provider capability required by M2–M5 is either:

1. a public, structured, version-pinned native seam; or
2. an accepted public-command composition with complete evidence for preconditions, identity, effects, timeout/UNKNOWN handling, reconciliation, cleanup, partial results and rollback.

The exact candidate must also pass isolated cold start, status, restart, stop and rollback with zero survivors.

If any required seam remains partial, missing, ambiguous or operationally unqualified, M1.4 must return `D1_BLOCKED_PROVIDER_SEAM_INSUFFICIENT` and stop without an adapter or fallback.

## 2. Inputs

M1.4 evaluated:

- `ORCA_PROVIDER_MANIFEST.json`;
- `M1_1B_ACCEPTANCE.md`;
- `M1_ORCA_PROVIDER_SEAM_MATRIX.json`;
- `M1_2_INDEPENDENT_REVIEW.md`;
- `M0_PROVIDER_SEAM_AMENDMENT.md`;
- `M1_3_LIFECYCLE_EVIDENCE.json`;
- `M1_3_ACCEPTANCE.md`;
- technical commit `7dd413b86c1d4c0a44f1f39b1f9b86089f4c2239`.

## 3. Evidence matrix

| Requirement | Evidence | Result |
|---|---|---|
| Exact candidate identity | M1.1b manifest/catalog qualification | PASS |
| Public-command catalog stability | 220 commands; two-run exact catalog | PASS |
| 55 required provider capabilities | 0 supported, 49 partial, 6 missing | FAIL |
| Exact structured cold start | two final M1.3 probes | FAIL |
| Status → restart → state recovery | blocked before accepted cold start | NOT PROVEN |
| Provider stop and rollback | namespace rollback works; provider lifecycle not accepted | NOT PROVEN |
| `events_read` | no complete composition | `UNSUPPORTED` |
| `resource_inventory` | no complete composition | `UNSUPPORTED` |
| `resource_cleanup` | no complete composition | `UNSUPPORTED` |
| `run_cancel` | no complete composition | `UNSUPPORTED` |
| `run_close` | no complete composition | `UNSUPPORTED` |
| `task_cancel` | no complete composition | `UNSUPPORTED` |
| Zero host survivors | two final M1.3 probes | PASS |
| Installed/global state unchanged | exact metadata fingerprint equality | PASS |

Isolation and cleanup prove that the qualification is safe. They do not prove that the provider seam is sufficient.

## 4. Technical verdict

The exact Orca 1.4.167 candidate does not satisfy D1.

Primary blockers:

1. The structured provider matrix remains insufficient: `0 SUPPORTED`, `49 PARTIAL`, `6 MISSING`.
2. Both final M1.3 probes failed at `cold_start` with `ERR_RUNTIME_START_SHAPE`.
3. The six product-required aggregate seams remain explicitly `UNSUPPORTED`.
4. Restart, durable Run/Task recovery, provider stop and provider rollback could not be accepted after the cold-start gate failed.
5. Harness-owned PID/mount/root cleanup cannot be relabeled as Orca-native lifecycle or aggregate semantics.

Therefore the M1.4 technical verdict is:

```text
D1_BLOCKED_PROVIDER_SEAM_INSUFFICIENT
D1_READY=false
D1_GRANTED=false
```

No adapter contract is frozen. No provider adapter, M2.3, M3, MCP registration or activation may begin under this verdict.

## 5. Forbidden fallbacks

This verdict does not authorize:

- private Orca database or storage access;
- parsing unrestricted diagnostic prose;
- GUI/browser automation;
- free-form shell composition;
- caller-managed hidden process cleanup;
- treating `task-update --status failed` as task cancellation;
- treating reset/root deletion as Run close or resource cleanup;
- reducing test thresholds or accepting a one-off successful probe;
- broad process termination outside a fresh owned PID namespace.

## 6. Owner decision options

### Option A — Require provider contract additions (recommended)

Require a new exact Orca build with public structured seams for:

- a quiet machine-readable startup mode whose stdout contains exactly one versioned record;
- explicit loopback bind control and telemetry-disable behavior;
- structured runtime stop/restart/status receipts;
- cursor-based events;
- complete resource inventory and cleanup;
- Run cancel and close;
- Task cancel;
- explicit result schemas, effect classes, timeout and recovery metadata.

Then authorize a new version-pinned M1.1b/M1.2/M1.3 requalification. D1 remains false until that candidate passes.

### Option B — Re-scope the product contract

Remove or defer capabilities that Orca cannot expose and amend the 24-tool contract, use cases, M2–M5 acceptance criteria and v0.22.0 roadmap.

This is a product compromise, not an implementation shortcut. It requires an explicit owner decision and a new M0 design amendment before code.

### Option C — Qualify a different provider boundary

Select another official structured provider interface or provider candidate and restart qualification from exact identity and catalog binding. Existing Orca evidence remains historical and cannot be transferred by assumption.

## 7. Recommendation and stop

Hermes recommends **Option A** if Orca can add the required official contracts; otherwise compare Option B and Option C as a product decision before further implementation.

M1.4 is complete. Execution stops here exactly as authorized:

- D1 remains false;
- no subsequent milestone is authorized;
- Draft PR #163 remains Draft;
- no merge, tag, Release, deployment or activation is performed;
- the product owner now decides the provider path.
