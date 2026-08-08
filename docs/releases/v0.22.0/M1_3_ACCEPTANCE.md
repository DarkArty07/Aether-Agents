# M1.3 — Isolated Orca lifecycle qualification closure

> **Milestone status:** CLOSED
> **Provider gate:** REJECTED / BLOCKED
> **Lifecycle accepted:** No
> **D1 ready:** No
> **Technical commit:** `7dd413b86c1d4c0a44f1f39b1f9b86089f4c2239`
> **Technical tree:** `3974b33e096cde76c78f7427ca57b34fa9fff278`
> **Evidence:** `M1_3_LIFECYCLE_EVIDENCE.json`

## 1. Scope completed

M1.3 implemented and exercised a reusable exact-candidate qualification harness for Orca 1.4.167. The harness does not implement an adapter and does not activate Aether MCP.

The harness provides:

- exact launcher, AppImage, manifest and catalog authentication;
- fresh user, network, mount and PID namespaces;
- a loopback-only network namespace with no external interfaces;
- a non-root worker with zero effective capabilities and the Electron sandbox enabled;
- one ephemeral Xvfb process with TCP disabled;
- exact-byte candidate staging in a private read-only home view;
- fixed `APPIMAGE_EXTRACT_AND_RUN=1` to avoid a forbidden FUSE mount inside the user namespace;
- bounded startup, command and stop timeouts;
- process-group and namespace-owned descendant cleanup;
- metadata-only protected-state fingerprints;
- exact classification of malformed output, startup timeout and listener survival;
- fail-closed evaluation of all six missing aggregate seams.

No worker, dispatch, terminal creation, worktree creation, account, model, credential, global state mutation, adapter, registered tool or product activation was introduced.

## 2. Exact artifacts

| Artifact | SHA-256 |
|---|---|
| `M1_3_LIFECYCLE_EVIDENCE.json` | `4b0178b1951b1549591b28f28182b49e1f12ec05b8c2246ba4cff1b39bafdff5` |
| `scripts/aether_mcp/qualify_orca_lifecycle.py` | `dbf7862e8827e5c6e5a72ebb20de21530a4825817c15b1c58c7154eb5b5f0d9a` |
| `tests/aether_mcp/provider/test_lifecycle_qualification.py` | `2166e581c075e2ad19e9d6c20f0058eba3f96b1a7d2e7f1c72a0a83c39838268` |

The exact candidate remained bound to:

- manifest SHA-256 `186e7409a9d942319a802d2a6ac1b4cec95f0ab2c48c97907ec7729a3faa8cfe`;
- catalog SHA-256 `068e1d66737f19835536e4a1573a2f931bffe9821af9c1bdff855f902898944b`;
- candidate ID `orca-linux-x86_64-appimage-1.4.167`.

## 3. Final real probes

Two independent final probes ran with the completed harness.

| Probe | Status | Stage | Stable code | Elapsed | Root survived |
|---|---|---|---|---:|---:|
| 1 | `BLOCKED` | `cold_start` | `ERR_RUNTIME_START_SHAPE` | 9.241 s | No |
| 2 | `BLOCKED` | `cold_start` | `ERR_RUNTIME_START_SHAPE` | 9.210 s | No |

In both probes, the AppImage extraction stream and provider JSON did not form one unambiguous structured cold-start record admitted by the exact parser. M1.3 therefore stopped before Run/Task mutation in the final probes. It did not reinterpret paths, prose or interleaved output as control data.

This result is deterministic across the two final probes and is a provider-boundary failure, not a harness PASS.

## 4. Rollback and isolation evidence

Both final probes recorded:

- external network interfaces: `0`;
- namespace UID/GID: `1000/1000`;
- effective capabilities: `0`;
- Electron sandbox disabled: `false`;
- process survivors: `0`;
- listener survivors: `0`;
- mount survivors: `0`;
- staged candidate home unmounted: `true`;
- isolated root survived: `false`;
- global state unchanged: `true`.

The protected-state metadata fingerprint remained exactly:

`777187ea9badc967be59be641122f3d74f1f41b2290e59472141f3a200efa6d6`

before and after both probes. Private file contents were not retained in evidence.

## 5. Six missing aggregate seams

M1.3 did not promote any low-level command or harness cleanup into a provider-native semantic capability.

| Capability | Verdict |
|---|---|
| `events_read` | `UNSUPPORTED` |
| `resource_inventory` | `UNSUPPORTED` |
| `resource_cleanup` | `UNSUPPORTED` |
| `run_cancel` | `UNSUPPORTED` |
| `run_close` | `UNSUPPORTED` |
| `task_cancel` | `UNSUPPORTED` |

No complete public-command composition proved preconditions, identity, effects, timeout/UNKNOWN handling, reconciliation, partial results and rollback for any of these six aggregates.

## 6. Verification

The technical tree passed:

- `python3 -m compileall -q scripts/aether_mcp src tests/aether_mcp`;
- Ruff on the new script and tests;
- provider suite excluding only the already executed real lifecycle probe: `48 passed, 1 deselected`;
- lifecycle unit suite excluding only the real fixture: `19 passed, 1 deselected`;
- two real final probes with the exact candidate;
- evidence schema and invariant validation;
- diff check;
- staged secret scan: `4` files, `0` findings.

The real fixture is not skipped when the canonical candidate exists; it recognizes only a complete PASS or one of the closed, fail-closed provider findings observed during qualification. The durable M1.3 acceptance result remains BLOCKED regardless of a later isolated one-off PASS until a newly authorized requalification supersedes this record.

## 7. Acceptance decision

M1.3 implementation is complete, but its provider lifecycle acceptance condition is not satisfied:

- structured cold start was not proven;
- restart and provider rollback could not be accepted;
- six required aggregates remain unsupported.

Therefore:

- **M1.3 lifecycle acceptance: REJECTED / BLOCKED**;
- **D1: not ready and not granted**;
- **adapter implementation: forbidden**;
- **next action:** M1.4 records the technical provider decision, then execution stops for the product owner.
