# R3 — Exact Orca Lifecycle Adaptation Acceptance

> **Status:** CLOSED / BLOCKED
> **Date:** 2026-08-08
> **Candidate:** Orca `1.4.167`
> **Historical framing defect fixed:** Yes
> **Full lifecycle accepted:** No
> **D1 granted:** No
> **MCP registration/activation:** Absent
> **Canonical evidence:** `R3_LIFECYCLE_EVIDENCE.json`

## 1. Result

R3 corrected the M1.3 AppImage framing defect, but it did not qualify the full
orchestration lifecycle.

The exact AppImage now follows this bounded sequence:

```text
verify exact size/hash
  -> extract once with --appimage-extract into the fresh owned root
  -> record bounded preparation-output sizes and digests separately
  -> validate AppRun remains inside the extracted AppDir
  -> invoke AppRun directly with the exact version-pinned public CLI bootstrap
  -> reserve serve stdout exclusively for structured readiness JSON
```

The real candidate emitted one valid `orca_server_ready` object and returned a
ready `status --json`. Therefore the original `ERR_RUNTIME_START_SHAPE` caused by
mixed extraction/framing is fixed by construction and execution.

The next required mutation, however, needs a live Orca terminal identity. The
headless standalone qualification boundary could not safely obtain one using the
public operations tested. R3 therefore closes `BLOCKED`, not `PASS`.

## 2. TDD evidence

Initial preparation/framing RED:

```text
3 failed
```

Coordinator-binding RED:

```text
2 failed
```

Final non-real R3 suite:

```text
23 passed, 1 deselected
Ruff:      PASS
compileall: PASS
```

The deselected test is the real full-lifecycle acceptance test. It cannot pass
until the coordinator bootstrap prerequisite is qualified.

## 3. Exact preparation evidence

| Fact | Result |
|---|---|
| AppImage SHA-256 | `813b11e99f7caa4bf8e4fc47200dd6c465f34a04d61e855adbd8822190592e33` |
| Explicit extraction | PASS |
| Preparation stdout | 213,838 bytes, SHA-256 `469f3adc47b40f1a998b6b8947f24748ce948e6365cfe6639d5a4d9b28bff011` |
| Preparation stderr | 0 bytes |
| `APPIMAGE_EXTRACT_AND_RUN` in runtime | No |
| AppRun confinement | PASS |
| Runtime stdout contains extraction paths | No |
| Structured readiness | PASS |
| Ready status/version | PASS |

## 4. Coordinator bootstrap evidence

### Direct orchestration mutation

`orchestration run-create` without a sender returned:

```text
no_active_sender_terminal
```

This proves that a live coordinator terminal is a public operational prerequisite,
not an optional tracing field.

### Synthetic `terminal create`

Without an explicit worktree, the provider returned `runtime_error` because no
renderer window was available.

With explicit `path:<isolated-project>`, the provider returned
`selector_not_found`: `serve --project-root` did not admit that path as an
Orca-managed worktree.

### Synthetic repo plus `worktree create`

The harness created a clean one-commit Git repository with zero remotes and used
only:

```text
worktree create --repo path:<isolated-repo> --name aether-m1.3-coordinator \
  --no-parent --setup skip --json
```

No agent, prompt, setup hook, provider account, or model was selected. The
whole-harness attempt still exited through `ERR_COMMAND_NONZERO` before producing a
structured lifecycle report. Its exact provider rejection remains unknown. Per the
three-approach stop rule, no fourth sender-bootstrap variant was attempted.

## 5. Cleanup and safety

After the probes:

```text
owned processes:      0
owned listeners:      0
owned mounts:         0
owned roots:          0
Xvfb runtime objects: 0
```

Every candidate/AppImage execution occurred behind a read-only staged `/home`
bind inside a private user/network/mount/PID namespace. The outer protected-state
metadata comparison did not complete after the blocked inner command, so that
specific comparison is `UNKNOWN`; it is not reported as PASS.

No private Orca DB, undocumented IPC, UI automation, global Orca mutation, model,
credential, network listener, or hidden fallback was used.

## 6. Consequence for the redesign

The adaptive design remains plausible only with an explicit trusted coordinator
binding:

- production mutations must receive an admitted live Orca terminal identity from
  trusted launch context;
- Aether may not invent, impersonate, or persist a stale handle;
- headless `serve` cannot currently be claimed as a standalone orchestration
  substrate;
- all mutation tools remain unavailable until coordinator binding is proven;
- R4 may implement default-off version binding, schemas, journal, correlation,
  reconciliation, and unavailable gates;
- R5's provider-backed two-worker slice is blocked under the current evidence.

R3 does not grant D1 or authorize registration, activation, a desktop/UI pilot,
models, credentials, integration, Release, or deployment.
