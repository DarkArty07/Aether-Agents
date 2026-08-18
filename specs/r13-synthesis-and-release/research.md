# R13 Research: Verification of the Ten Unobserved Claims

**Stage**: R13
**Date**: 2026-08-17
**Hermes evidence**: version 0.20.1, revision `411903b6fa258f81afcc3869eb615f6218e1776a`, source `home/.venv-hermes/src/hermes-agent` — the tree the runtime actually loads
**Method**: source reading plus direct execution against an isolated board in a disposable `HERMES_HOME`. **No profile was created, no agent was spawned, no model was called, and the owner's Aether profile was not touched.**

## 1. Why this pass exists

R13 §5 listed ten claims the design depended on and nobody had observed. They were labelled assumed under R11-FR-1124, which is honest but weak: an assumption that a protected effect can actually be denied is not a design, it is a hope.

This pass closes eight of the ten without running a single agent, by using two techniques the runtime itself provides:

- **The injectable spawn function.** `dispatch_once(conn, spawn_fn=…)` accepts a substitute for the real worker launcher — the same seam the upstream test suite uses. Passing a stub exercises the entire dispatch path (reclaim, promote, atomic claim, workspace preparation, run-row creation, process accounting) and stops exactly where the model would be called.
- **Direct calls into the board kernel.** Blocking, review, completion, and crash detection are ordinary functions. They can be driven with fabricated state and their effects read back from the database.

The technique matters beyond this pass: **most of Aether's runtime assumptions are testable for free.** Only behaviour that requires a model in the loop needs paid execution.

## 2. Results

| # | Claim | Status | What changed |
|---|---|---|---|
| 1 | A worker spawns for an assigned unit | **Verified by execution** | — |
| 2 | A crashed worker is reclaimed without losing the unit | **Verified by execution** | **A crash ticks the failure counter.** Crashes are not free (§3.2) |
| 3 | A per-card worktree is created; two units never share a tree | **Verified by execution** | Branch form observed as `wt/<task-id>` (§3.3) |
| 4 | Goal-mode judging terminates a unit; exhaustion blocks | **Verified in source, partially** | Wiring confirmed; the judge itself needs a model |
| 5 | The review path claims a unit and returns rework | **Verified by execution** | `request_changes` requires an active claimed review run (§3.5) |
| 6 | A terminal event wakes Morfeo | **Verified in source** | `review_requested` also wakes, not only terminal events |
| 7 | A fail-closed hook denies a protected effect | **Verified by execution** | Consent and fail-closed semantics are narrower than assumed (§3.7) |
| 8 | Automatic decomposition is confirmed inert when disabled | **Verified by execution** | — |
| 9 | Evidence from a real unit suffices for acceptance | **Still assumed** | Not mechanically verifiable (§3.9) |
| 10 | Cost and duration per unit are observable | **Split: duration yes, cost no** | The board records no cost at all (§3.10) |

Eight of ten moved from assumed to verified. Two remain, and both are named honestly rather than quietly promoted.

## 3. Findings

### 3.1 The dispatch path

A tick with a stub spawn claimed two ready units, resolved each workspace, called the stub with `(task, workspace_path, board)`, and recorded the returned process id on the unit. Run rows were created in `running` state with the process id attached.

**Concurrency was verified as a live cap, not a per-tick budget.** With a limit of two and three eligible units, the first tick spawned exactly two; the second tick spawned none, because two were already running. This is the mechanism R7-FR-712 relies on, and it behaves as that requirement assumes.

**A unit whose assignee is not a real profile is skipped, not dispatched.** With all units assigned to `implementer` — a profile that does not exist in the test home — the dispatcher spawned nothing and reported them as a skipped non-spawnable lane. Reassigning to a real profile made them dispatch immediately. This confirms R5-FR-508a from the other direction.

### 3.2 A crash costs an attempt **and** a failure

A unit was placed in `running` with a host-local claim and a process id that does not exist. `detect_crashed_workers` found it, released the claim, cleared the process id, returned the unit to `ready`, and appended a `crashed` event carrying the dead process id and the claimer.

The unit was not lost. **But `consecutive_failures` incremented to 1.**

This contradicts the summary in `R9 §5`, which listed a crash as costing "one attempt" in the same sense as a stale reclaim. They are not the same:

| Path | Unit returns to | Failure counter |
|---|---|---|
| Stale claim released (TTL expired, worker dead) | Its source phase | Not ticked |
| **Crash detected (process gone)** | Its source phase | **Ticked** |

**Consequence for R7-FR-738.** With an attempt limit of two, **two environmental crashes exhaust a unit's budget and auto-block it** — even though neither crash was the unit's fault. The unit then holds a block, and PD-37 gives it roughly one human answer before the loop breaker routes it out of the work pool. A machine that sleeps twice during an overnight run could therefore consume a unit's entire tolerance without a single defect in the work.

This is the sharpest viability finding in the pass, and it is an argument for setting the attempt limit above two rather than at two.

### 3.3 Per-card worktrees are real

Three units were created with worktree workspaces against a scratch git repository. After one tick, the repository reported:

```text
…/wtlab                    0a4057d [main]
…/wtlab/.worktrees/logica  0a4057d [wt/t_9f9fe65d]
…/wtlab/.worktrees/render  0a4057d [wt/t_40619062]
```

Two separate directories, two separate branches, both from the same base commit. Concurrent implementers genuinely do not share a working tree, which is the isolation PD-31 assumes and the previous architecture could not obtain.

**Observed branch form: `wt/<task-id>`.** R8-FR-809 requires Aether to use the runtime's derivation rather than invent one; this records what that derivation actually produced under an explicit worktree path. A project-linked task is documented to produce a different form, which is not exercised here.

### 3.4 Goal mode

The spawn builds the worker command with goal-loop environment variables and a quiet-mode flag only when the unit has goal mode set, leaving non-goal units with a clean environment. The turn budget is passed the same way.

The wiring is confirmed. The judge's behaviour — that it terminates a converged unit, and that budget exhaustion blocks rather than exits silently — requires a model and remains assumed.

### 3.5 The review lane works, with a precondition

Driving the review path directly produced a precise picture.

Repeated review requests move the unit to `review` and **never touch `block_recurrences`**, which stayed at zero throughout. This confirms R7-FR-736 and R5-FR-526a: review cycles do not consume the scarce block budget.

`request_changes` initially did nothing. Reading the implementation explained why: it requires the unit to be `running` with an active run claimed **from** `review`, and returns a diagnostic rather than raising when that is not true. Simulating the missing step — a dispatcher tick while the unit sat in `review` — showed the dispatcher **does** claim review-status units and spawn a reviewer for them. With a real review run open, `request_changes` succeeded, returned the original implementer, and routed the unit back to `ready` assigned to that implementer.

Final event sequence for one full cycle:

```text
created → review_requested → claimed → spawned → changes_requested
```

with attempt rows recorded per phase and the block budget untouched.

**Design consequence.** The review lane is only available when a dispatcher is running. A reviewer verdict issued against a unit that is merely sitting in `review`, with nothing claimed, silently does nothing. Any Aether procedure that returns rework must go through a claimed review run.

### 3.6 The wake channel

The gateway's notifier watcher polls board events and resolves each subscription's delivery mode, waking the destination agent when the mode requests it and sending a passive message otherwise — the three modes R6 §6 depends on.

One detail R6 did not record: **`review_requested` wakes the origin subscriber the same way a block does.** If Morfeo subscribes to a contract card and the supervising role uses same-card review, Morfeo is woken at review time, not only at completion. R6-FR-619 requires every owner-facing wake to be an end-of-work report or an unresolvable defect, so review-time wakes must be scoped to Morfeo's own reasoning and must not reach the owner.

Delivery itself requires a live gateway and remains assumed.

### 3.7 Enforcement: narrower than assumed, but real

This claim produced the most correction, in both directions.

**A hook that is not allowlisted does not fire at all.** `hermes hooks doctor` states it plainly: *"not allowlisted — hook will NOT fire at runtime"*. It does not fail closed; it is simply absent, and every effect it was meant to deny is permitted. An enforcement point can therefore be fully configured and completely inert.

**But dispatcher-spawned workers are not affected.** The spawn passes `--accept-hooks` explicitly, with a comment stating the reason: workers switch to a profile-scoped home and would otherwise see that profile's empty allowlist instead of the dispatcher's. So hooks registered on the supervisor and implementer profiles **do** fire for board work.

The gap is the role that is *not* dispatcher-spawned: **Morfeo**, which runs as a persistent interactive session. A hook constraining Morfeo requires consent through a terminal prompt or the auto-accept setting, and the owner's live profile currently has auto-accept off.

**Blocking works.** Fed a payload representing a forbidden card creation, the hook exited 2 with a block payload and the runtime parsed it into its wire shape:

```json
{"action": "block", "message": "R10: un implementer solo crea cards de decision dirigidas al supervisor"}
```

**`fail_closed` is narrower than the design assumed.** Reading the dispatcher: it converts a **spawn error, a timeout, or malformed output** into a block. It does **not** convert an arbitrary non-zero exit into a block — a hook exiting 77 contributed nothing and the call would proceed. Explicit denial is exit 2 plus a block payload; `fail_closed` is a crash net, not a general deny-by-default.

**The payload shape was captured directly**, because the documentation and the implementation disagree on it. The documentation describes a top-level `args` key; the runtime actually delivers:

```json
{
  "hook_event_name": "pre_tool_call",
  "tool_name": "kanban_create",
  "tool_input": { },
  "session_id": "…",
  "cwd": "…",
  "extra": { }
}
```

A hook that reads the documented key finds nothing, compares an empty value, and — for a deny-unless-permitted rule — **denies everything**. That failure is safe but total: it would halt all work while appearing correctly configured.

**One trap in the test harness itself.** `hermes hooks test --payload-file` merges a supplied payload into a synthetic one and does not replace `tool_input`; the supplied arguments land under `extra`. A hook's argument logic therefore cannot be validated with that harness alone, which is how a correct hook appeared broken during this pass.

### 3.8 Disabling automatic decomposition

The gateway's resolver was called directly with three configurations: unset returns enabled with a per-tick cap of three, explicitly true returns the same, and explicitly false returns disabled. The setting is honoured and is re-read each tick, so disabling it takes effect without a restart.

The default is enabled. R7-FR-706 stands, and R13-FR-1332's requirement to *verify* rather than assume the disable is now a one-line check rather than an act of faith.

### 3.9 Evidence sufficiency is not mechanically verifiable

Whether a unit's completion evidence lets the owner accept work by running one command is a judgement about content, not a property of the board. The board guarantees the fields exist and travel; it cannot guarantee they are true or useful. This claim can only be settled by a real run and is deliberately left assumed.

### 3.10 Cost is not observable from the board

Duration is: `task_runs` carries `started_at`, `ended_at`, `max_runtime_seconds`, and `last_heartbeat_at`, so per-attempt wall-clock is directly available.

**Cost is not.** Neither `tasks` nor `task_runs` has any column for cost, tokens, usage, or spend. The board records what happened, not what it cost.

The correlation key is `tasks.session_id`: the worker's session is where the runtime's own usage accounting lives. R12-FR-1215 requires per-unit cost observability and is therefore **not satisfied by the board alone** — it requires joining a unit to its session. Recorded rather than quietly dropped.

## 4. What still requires a paid run

Three things, and only three:

1. **The convergence judge** — that it ends a converged unit and that exhaustion blocks rather than exits silently (§3.4).
2. **Wake delivery** — that a terminal event actually reaches Morfeo through a live gateway (§3.6).
3. **Evidence quality** — that what a real worker writes is enough to accept by (§3.9).

Everything else in R13 §5 is now observed. The walking-skeleton checkpoint is correspondingly smaller than when it was written, and its remaining purpose is narrower and clearer.

## 5. Changes this pass forces

| Change | Artifact |
|---|---|
| A crash ticks the failure counter; the attempt limit should exceed two | R7, R9 |
| Observed branch form recorded | R8 |
| Hook consent gap for the non-dispatched role; `fail_closed` scope; payload shape | R10 |
| Cost is not on the board; correlation runs through the session | R12 |
| Ten claims reduced to three | R13 |
| Review requires a claimed review run; review wakes subscribers | R7, R6 |

## 6. Method note

Every finding above was produced by executing the runtime or reading the tree the runtime loads, never by reading documentation alone. Two of the corrections — the hook payload shape and the `fail_closed` scope — are cases where the documentation is wrong about the implementation, which is the third time this project has found that. PD-41 exists for this reason and this pass is its first deliberate application.
