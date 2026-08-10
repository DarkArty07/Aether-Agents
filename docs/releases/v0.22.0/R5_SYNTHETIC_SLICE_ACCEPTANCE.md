# R5 — Provider-Backed Two-Worker Synthetic Slice Acceptance

> **Status:** CLOSED / BLOCKED / NOT EXECUTED
> **Date:** 2026-08-08
> **Blocking prerequisite:** trusted live Orca coordinator-terminal binding
> **Blocking evidence:** `R3_LIFECYCLE_ACCEPTANCE.md`
> **Lower-level foundation:** `R4_ADAPTER_FOUNDATION_ACCEPTANCE.md`
> **Models, credentials or provider accounts used:** No
> **MCP tools registered/callable:** 0 / 0
> **D1 granted:** No

## 1. Decision

R5 did not start a two-worker synthetic slice.

R3 proved that the exact candidate can be prepared and cold-started headlessly,
but every orchestration mutation requires a live admitted Orca terminal sender.
The bounded headless qualification did not prove a public way to obtain that
binding. R4 therefore keeps every mutation unavailable and contains no live
provider executor.

Executing R5 under those conditions would require at least one forbidden
substitution:

- inventing or impersonating a terminal handle;
- using private Orca state or IPC;
- driving the desktop/UI without an operation gate;
- adding an unqualified provider executor;
- bypassing R4's mutation-unavailable policy;
- relabeling synthetic fake-driver tests as a provider-backed slice.

None was used.

## 2. Intended fixture not admitted

The planned R5 fixture would require:

1. one admitted synthetic repository;
2. two independent Tasks/scopes;
3. two real Orca worktrees or equivalent isolated resources;
4. both workers started before either result is observed;
5. one acknowledged message/handoff;
6. deterministic artifacts from both workers;
7. restart/reconnect recovery with stable identities;
8. bounded cancel or retry evidence;
9. closeout and zero survivors.

The fixture was not frozen into runtime inputs because prerequisite 1 cannot yet
be connected to an admitted live coordinator identity. No partial provider effect
was attempted.

## 3. Preserved lower-level evidence

The block does not invalidate completed evidence:

- R1: adaptive ownership, 15-tool catalog, three-axis capability model and debt;
- R2: `aether.mcp/v1alpha2`, 15 exact schemas, zero callable tools;
- R3: exact AppImage extraction separated from runtime framing; structured cold
  readiness; coordinator bootstrap unqualified;
- R4: exact build/binding checks, immutable argv, atomic append-before-effect
  journal, receipts, idempotency, `UNKNOWN` and injected reconciliation.

Those are architecture/protocol/foundation results only. They are not agent-
orchestration acceptance.

## 4. No-execution evidence

At R5 closure:

```text
operational schemas:        15
registered tools:            0
callable tools:              0
live provider executor:      absent
adapter subprocess imports:  0
adapter network imports:     0
provider-backed workers:     0
models/provider calls:       0
owned runtime survivors:     0
```

No AppImage, Xvfb, worktree, terminal, worker, Run, Task, listener or mount was
started for R5.

## 5. Honest product conclusion

The redesign remains a plausible architecture and now has a safe deterministic
foundation. It is **not yet demonstrated as working agent orchestration**.

The next product gate must supply one of:

- a versioned public headless coordinator-admission primitive from Orca; or
- a separately authorized isolated desktop/UI-backed qualification with a trusted
  live coordinator terminal and the same cleanup/rollback requirements.

Only after that gate passes may a new R5-R1 execute the two-worker fixture.

R5 does not grant D1 or authorize MCP registration, activation, desktop automation,
models, credentials, integration, Release or deployment.
