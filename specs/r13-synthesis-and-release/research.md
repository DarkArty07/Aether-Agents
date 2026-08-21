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

## 7. Constitution materialization

**Need**: `.specify/memory/constitution.md` was still the unfilled Spec Kit core template
(`source: core`, sha `ce7549540fa45543cca797a150201d868e64495fdff39dc38246fb17bd4024b3`), while
R0 §4 held six accepted principles and `spec.md:155` directed that a future materialization
"must copy the accepted principles without creating a second competing governance source".

**Decision**: Materialize R0 §4 into `.specify/memory/constitution.md` at v1.0.0, treating the
Aether repository as the project it governs. The six principle bodies are copied verbatim; each
gains one added compliance line stating a verifiable criterion (R3-FR-310). The file declares R0
the canonical source and routes amendments through R0 §4 first, so no second authority is created.

**Rationale**: R0 §155 anticipates this artifact explicitly. Keeping the principles only in a
stage spec left the governance Spec Kit reads at runtime empty, so `analyze` and `converge` had no
constitution to score against — the highest-severity evidence class (R11-FR-1111) was unreachable.

**Evidence**: `specs/r0-design-governance/spec.md:97-127` (principles), `:155` (materialization
directive); `.specify/memory/.constitution-template.json` (template was upstream core, unmodified);
`.gitignore:11` (`/.specify/` — the artifact is untracked and outside the `policy.yml` manifest);
verbatim fidelity confirmed by paragraph-level comparison of all six principles against R0 §4.

**Alternatives considered**: Leaving the template unfilled was rejected because it leaves Spec Kit's
governance hook empty while accepted principles exist. Authoring new principles was rejected as
creating the second competing source R0 §155 forbids. Tracking the file in git was rejected because
it would require changing both `.gitignore` and the `policy.yml` manifest for no design benefit.

**Change forced in R13**: §3 assigned Morfeo no constitution guarantee at all, although R3 §2 gives
him the `constitution` phase and R3-FR-309 makes it part of starting work. Added FR-1310a and
FR-1310b. §4 was left unchanged: its inventory is runtime configuration, and a per-project
constitution is not a runtime default.

**Impact on other stages**: None. R0 is unchanged and remains canonical — its §155 condition is
satisfied, not superseded. R3 is unchanged; FR-1310a/b restate R3-FR-306/307/309/312 rather than
adding intent. `CLAUDE.md` was reconciled downward, since it stated the template was still unfilled
and read as forbidding what R0 §155 authorizes.

## 8. Cross-artifact coverage pass

**Need**: Spec Kit's `analyze` phase cannot run against this repository — it requires `spec.md`,
`plan.md` and `tasks.md` for one feature, and no plan or task artifact exists or should exist before
build. Its detection passes were therefore applied directly to the fourteen stage specifications.

**Method**: Requirement inventory (475 FR, 101 SC); cross-reference resolution for every
`RN-FR-nnn`, `RN-SC-nnn`, `PD-nn` and `RN-Dnn` citation; placeholder and vague-adjective scans over
576 requirement bodies; stage-status consistency between each `spec.md` and `ROADMAP.md`; and
coverage of the 76 requirements declared in the `Requirements Inherited by Later Stages` tables
against the stage each names as owner. Keyword overlap only nominated candidates; every finding was
then confirmed or discarded by reading the named stage.

**Clean**: no unresolved or mis-stage-prefixed cross-reference; no requirement number defined in two
stages; no placeholder; no vague adjective in any requirement body; no status mismatch. Three
nominated gaps were discarded as false positives — R2→R5 is satisfied by R5-FR-523, R3→R7 by
R7-FR-738/738a/738b, and R9→R10 by R10 §5.

**Findings and disposition**: six inherited requirements were declared by an upstream stage and never
landed in the stage named as their owner. None was a conflict; each was intent already accepted but
not carried through.

| Inherited requirement | Declared by | Owner | Disposition |
|---|---|---|---|
| Repeated denial attempts are a reportable condition | R10 §10 | R11 | Added R11-FR-1110a. R10-FR-1015 already declared the pattern reportable; R11-FR-1110 covered only a single denied call |
| Deliver an independently runnable increment per converged story | R3 §6 | R7, R8 | Added R8-FR-817a. Absent from both named owners |
| Decompose along independently testable user stories | R2 §8 | R7 | Added R7-FR-701a. R7-FR-701 required deriving the breakdown from the contract but never named its axis |
| Steering exists; redirecting a worker need not mean killing it | R4 §9 | R7 | Added R7-FR-742a, recording it as deliberately **not** adopted across role boundaries per PD-29, rather than leaving it unresolved |
| Enabling a messaging channel is a per-profile configuration decision | R6 §8 | R12 | Added R12-FR-1205a. Already carried in R13 §7, so the gap was tracked but unplaced |
| A runnable validation guide is a completion requirement | R1 §4 | R7 → **R11** | Owner corrected. The requirement is satisfied by R11-FR-1102; the row pointed at a stage that never carried it |

**Alternatives considered**: Deleting the uncovered rows was rejected — each states accepted intent,
so removing the row would discard the decision rather than fulfil it. Deferring all six to build was
rejected because an inherited requirement with no owning requirement becomes invisible the moment
the roadmap stops being read, which is the failure FR-1342 exists to prevent.

**Impact**: R4 through R13 were already `in-progress`, so five of the six additions touch stages
awaiting review and no accepted stage reopens. R1 is `done` and its change is a routing correction —
the decision it states is unchanged, only the stage named as its downstream owner — so R1 is
**not** returned to `in-progress`. R2, R3, R4, R6 and R10 are unchanged: each already stated its
requirement correctly and the defect was in the receiving stage.

**Recording note**: R7, R8, R11 and R12 carry inline `Evidence` sections rather than research
artifacts (ROADMAP §3). Those sections hold verified-or-assumed claims about the runtime, and these
six changes introduce no runtime claim, so the rationale is recorded here rather than being written
into them as evidence it is not.

## 9. Design acceptance and the EC1 plan

**Acceptance**: on 2026-08-17 Christopher accepted R4 through R13 after the R4–R13 Decision Review,
which presented 53 material decisions across the ten stages with the consequence of reversing each.
He changed none. R0–R3 were already accepted, so the design phase is now closed end to end.

A correction made during that review is worth recording, because it was mine. The review first
presented six decisions as "open questions for the owner". Two of them were not questions at all:
whether Aether should span machines is already settled, and R6-FR-606 records the two conditions that
reopen it on their own terms, and the provisional numbers cannot be chosen better before a run produces data
(R7-FR-713). Four of the remaining items are not decisions in any sense — they are limits of the
runtime that the design accommodates: the one-block budget, Morfeo's hook-consent gap, the asymmetry
of containment, and the absence of cost on the board. Presenting a constraint as a choice asks the
owner to decide something no answer can change, and it was corrected before acceptance.

**Plan**: [`plan.md`](plan.md) was written immediately after acceptance, scoped to EC1 alone at the
owner's direction rather than to the full build. Its shape follows from the three claims that survive:
Phases 1 through 4 exist only to make Phase 5 answerable, and the plan says so rather than presenting
itself as the product build.

Three decisions inside the plan are worth naming:

- **`data-model.md` and `contracts/` are not created.** EC1 has no data model and exposes no external
  interface. R0 §6 forbids creating optional artifacts with no content.
- **`quickstart.md` is deferred rather than written.** Verified while writing the plan: the Hermes CLI
  declares `hermes`, `hermes-agent` and `hermes-acp` as its entry points and registers no `board`
  subcommand — the board is driven through agent-side tools in board mode and observed through the
  dashboard. A runnable validation path therefore cannot be written from documentation without
  inventing commands, which is the failure PD-41 exists to prevent. It is written when Phase 1 begins,
  from the runtime.
- **`tasks.md` is not created either.** R3-D01 assigns the breakdown to the supervising role, which
  does not exist until Phase 1. Producing it here would be the designer performing another role's
  phase, which is what R4-FR-410a classifies as incompatible when the runtime does it.

**Authority**: acceptance granted design authority only. Phases 1–4 need build authorization and
Phase 5 needs a separate activation authorization (FR-1335, FR-1337). Neither exists. Writing this
plan changed no runtime state and created no profile, configuration, prompt, or hook.

**Impact**: R4–R13 move to `done`; `ROADMAP.md` §8, `README.md` §Status and `CLAUDE.md` were
reconciled downward, including the stale claim that ten runtime assumptions remained — three do.

## 10. Phase 3 build correction — Morfeo's contract writer

**Detected**: 2026-08-18, before any Phase 3 SOUL was written or any profile was started.

**What contradicted what**: R5-FR-506 had been materialized by removing all file tools from Morfeo,
which made its non-implementation containment structural. R8-FR-805 names Morfeo as the only writer
of `constitution.md`, `spec.md`, and `plan.md`, and R13-FR-1304 requires accepted clarifications to be
written into their owning artifact immediately. The canonical contract is repository state, not board
comments or memory. With the effective Morfeo tool surface, that required write was impossible.

**Runtime evidence**: Hermes 0.20.1 exposes `read_file`, `write_file`, `patch`, and `search_files`
together under the generic `file` toolset. It provides no native contract-only writer and no path
allowlist for that toolset. Board comments are durable but are not the Spec Kit contract. A prompt
therefore could not repair the capability gap, and enabling the generic toolset alone would have made
the earlier structural-containment claim false.

**Correction authorized by the owner**: preserve structural absence of terminal, code execution,
browser execution, delegation, and other execution capabilities. Treat the contract-file boundary as
enforced rather than structural. During Phase 4, while Morfeo remains stopped, install and consent a
fail-closed pre-tool-call hook, then enable the generic file toolset and prove both an allowed canonical
contract write and a denied out-of-contract write. Failure at any gate removes the toolset before the
profile may start.

**Why this option**: it keeps Morfeo as the contract author, keeps Supervisor from acquiring design
authority, avoids a competing board contract, adds no role, and changes no Hermes core or product
code. A purpose-built contract tool would be narrower but is unjustified product work for EC1.

**Bounded impact scan**: R5 changes because the strength of one containment claim changes; R10
changes because Morfeo gains a new protected effect and atomic activation rule; R13 changes because
its prompt and enforcement phases deliver the corrected boundary. R1, R2, R3, R6, R7, R8, R9, R11,
and R12 keep their accepted decisions: contract ownership, canonical storage, authority, evidence,
and model policy are unchanged. The three profiles remain stopped and Morfeo's file toolset remains
disabled until Phase 4.

## 11. Phase 3 prompt build and verification

The build produced three distinct identity files:

- `home/profiles/morfeo/SOUL.md`
- `home/profiles/supervisor/SOUL.md`
- `home/profiles/implementer/SOUL.md`

### 11.1 Binding coverage matrix

| Requirement | Role | Concrete SOUL line(s) |
|---|---|---|
| FR-1301 | Morfeo | `morfeo/SOUL.md:14` |
| FR-1302 | Morfeo | `morfeo/SOUL.md:15` |
| FR-1303 | Morfeo | `morfeo/SOUL.md:16` |
| FR-1304 | Morfeo | `morfeo/SOUL.md:18` |
| FR-1305 | Morfeo | `morfeo/SOUL.md:17` |
| FR-1306 | Morfeo | `morfeo/SOUL.md:22` |
| FR-1307 | Morfeo | `morfeo/SOUL.md:23`, `morfeo/SOUL.md:18` |
| FR-1308 | Morfeo | `morfeo/SOUL.md:24` |
| FR-1309 | Morfeo | `morfeo/SOUL.md:8` |
| FR-1310 | Morfeo | `morfeo/SOUL.md:9` |
| FR-1310a | Morfeo | `morfeo/SOUL.md:10` |
| FR-1310b | Morfeo | `morfeo/SOUL.md:10` |
| FR-1311 | Supervisor | `supervisor/SOUL.md:13` |
| FR-1312 | Supervisor | `supervisor/SOUL.md:14` |
| FR-1313 | Supervisor | `supervisor/SOUL.md:15` |
| FR-1314 | Supervisor | `supervisor/SOUL.md:9`, `supervisor/SOUL.md:17` |
| FR-1315 | Supervisor | `supervisor/SOUL.md:21` |
| FR-1316 | Supervisor | `supervisor/SOUL.md:22` |
| FR-1317 | Supervisor | `supervisor/SOUL.md:23` |
| FR-1318 | Supervisor | `supervisor/SOUL.md:24` |
| FR-1319 | Supervisor | `supervisor/SOUL.md:7` |
| FR-1320 | Implementer | `implementer/SOUL.md:7` |
| FR-1321 | Implementer | `implementer/SOUL.md:14` |
| FR-1322 | Implementer | `implementer/SOUL.md:15` |
| FR-1323 | Implementer | `implementer/SOUL.md:9` |
| FR-1324 | Implementer | `implementer/SOUL.md:10` |
| FR-1325 | Implementer | `implementer/SOUL.md:21` |
| FR-1326 | Implementer | `implementer/SOUL.md:16` |
| FR-1327 | Implementer | `implementer/SOUL.md:22` |
| FR-1328 | Common | `morfeo/SOUL.md:28`, `supervisor/SOUL.md:28`, `implementer/SOUL.md:26` |
| FR-1329 | Common | `morfeo/SOUL.md:30`, `supervisor/SOUL.md:30`, `implementer/SOUL.md:27` |
| FR-1330 | Common | `morfeo/SOUL.md:29`, `supervisor/SOUL.md:29`, `implementer/SOUL.md:17` |

**Coverage result**: **32/32 PASS**. Every anchor was required to resolve to exactly one concrete
line; common requirements had to resolve once in each identity.

### 11.2 Loader, identity, and safety evidence

The verifier called Hermes's real `load_soul_md(home_override=...)` for each profile and then called
`build_system_prompt_parts` with each profile's `state.db` as the home anchor. In all three cases the
loaded bytes matched the file and the SOUL was the identity prefix of the assembled system prompt.
The verifier used a static dummy object; it did not construct an agent, start a profile, or invoke a
model.

File hashes, including their final newline:

- Hermes rollback: `58dbb2eea7ea93c86bce48403698ae65d1e6f33e2b26c8acf7e6459d77e557f8`
- Morfeo: `8756422eac37b547a73ce5fcbe741ecbc53bda72e8d16bb97e878592116fd4dd`
- Supervisor: `979fe792099af8c3ba6ceb5739fb6682b2f1941b9c5e0a34a8fbedb8f9a9b950`
- Implementer: `ecc1855e2f73c38dd9ab0ac324e52baea2e0cd50aff0b4d8c45a89e7e2310c1e`

All four hashes differ. Static scanning found zero absolute machine paths, credential-shaped values,
configured model/provider identifiers, or verbatim lines copied from Hermes's board-worker protocol
in the three SOUL files. Supervisor's card budgets are explicit as `max_retries: 3`,
`max_runtime_seconds: 7200`, and conditional `goal_max_turns: 20`.

### 11.3 Operational boundary evidence

- No running process referenced the Morfeo, Supervisor, or Implementer profile homes.
- The shared board returned `PRAGMA quick_check = ok`, with zero tasks and zero task runs.
- Morfeo's effective configured toolsets still exclude `file`; Phase 4 remains the activation gate.
- No new profile had `state.db-wal` or `state.db-shm` residue.
- The shared board did have its own `kanban.db-wal` and `kanban.db-shm` sidecars. They are shared-board
  state, not cloned profile state, and were intentionally left untouched.
- No agent, gateway, or model was started by Phase 3 verification.

### 11.4 Phase result

**Phase 3 — Prompts: PASS (2026-08-18).** The three definitive identities are present, loaded by
the real Hermes prompt path, distinct from one another and from Hermes, and traceable 32/32 to the
binding requirements. The contradictory Morfeo capability claim is corrected and its deferred
activation is fail-closed by design.

At the Phase 3 gate, Phase 4 had not started. Morfeo's generic file capability was still disabled, no
enforcement hook had been installed, no profile had been started, no model had been invoked, EC1 had
not been executed, and no Hermes-to-Morfeo cutover had occurred. Section 12 records the later Phase 4
build.

## 12. Phase 4 enforcement build and verification

**Executed**: 2026-08-18, under the owner's explicit instruction to execute Phase 4. This authority
covered the reversible enforcement build only. It did not authorize Phase 5, EC1, a profile start, a
model call, or the Hermes-to-Morfeo cutover.

### 12.1 Installed enforcement

Each constrained profile now has exactly one `pre_tool_call` shell hook matching every tool name:

- `home/profiles/morfeo/hooks/aether_pre_tool_policy.py`
- `home/profiles/supervisor/hooks/aether_pre_tool_policy.py`
- `home/profiles/implementer/hooks/aether_pre_tool_policy.py`

The three installed copies are byte-identical with SHA-256
`7001243bacf2c5eb98ba8afd310d728bb70d0078d21956b0879af004d17a1a4b`. Each profile configuration
sets `matcher: '.*'`, `timeout: 5`, and `fail_closed: true`. `hooks_auto_accept` remains false. Each
exact event-command pair has one profile-local allowlist entry; configuration and allowlist files are
mode `0600`, and the hook is mode `0700`.

The hook never modifies or widens a call. It returns either no directive or an explicit block with exit
code 2 and a caller-visible reason. Malformed input, missing protected-effect context, policy errors,
and inability to decide a protected effect produce a block rather than a guessed permission.

The Morfeo capability gate followed the required order: install, configure fail-closed, consent the
exact command, validate a payload through Hermes's real plugin dispatcher, enable `file`, then run one
permitted and one denied write. Its effective CLI and Telegram surfaces now contain `read_file`,
`write_file`, `patch`, and `search_files` behind the hook. Terminal, code execution, browser execution,
computer use, delegation, and cron remain absent.

### 12.2 Runtime corrections discovered during verification

The real dispatcher capture refined R10-FR-1008f. `tool_name`, `tool_input`, and `session_id` are
at the top level. `task_id`, `tool_call_id`, `turn_id`, `api_request_id`, and `middleware_trace` are
under `extra`; no top-level `args` exists. R10 and the Phase 4 plan were corrected to state that exact
shape.

The first branch-negative test also found a real policy defect: when a repository had no remote and no
explicit integration-branch variable, the initial implementation treated whichever branch happened
to be checked out in the main worktree as integration. That would have permitted Morfeo to write a
contract on an arbitrary local branch. The fallback now resolves, in order, an explicit integration
branch, the remote default, local `main`, local `master`, or the sole local branch. Ambiguity remains a
denial. The corrected script was copied to all three profiles and all three exact allowlist entries were
re-recorded against its final mtime before the complete matrix was rerun.

The final alignment check found one unnecessary convention in the first policy draft: it required the
literal word `Decision` in the card title even though R7 defines the card by its destination and by a
body containing the question, candidate answers, and consequences. That title test was removed rather
than added to the SOUL. The final matrix proved a correctly shaped decision card with an arbitrary
title is permitted, while an ordinary card is still denied.

### 12.3 Protected-effect matrix

All checks used disposable Git repositories and isolated boards under `/tmp`. Denied actual file calls
were passed through `model_tools.handle_function_call`; the target bytes remained absent or unchanged.
Other policy calls used the production plugin dispatch path, not the built-in synthetic hook harness.

| R10 §5 effect | Executed evidence | Result |
|---|---|---|
| Implementer creates work beyond a decision card | Ordinary work card denied; structured decision card addressed to Supervisor permitted | PASS |
| Implementer links for another purpose | Decision-parent-to-own-card permitted; ordinary parent and foreign child denied | PASS |
| Supervisor or Implementer writes contract artifacts | Supervisor `tasks.md` and Implementer source writes proceeded; their Morfeo-owned contract writes were blocked | PASS |
| Morfeo writes outside owned contracts | Canonical plan write proceeded; source write, mixed patch, and non-integration-branch write were blocked | PASS |
| Implementer rewrites shared history | Force push was blocked | PASS |
| Implementer touches another branch | Branch switch was blocked | PASS |
| Implementer performs irreversible external effects | Destructive deployment CLI and interactive computer-use calls were blocked | PASS |
| Any role writes a credential shape into durable fields | Synthetic credential-shaped board comment was blocked in all three profiles | PASS |
| Any role acquires or widens credentials | Authentication and credential-file operations were blocked in all three profiles | PASS |

The Supervisor integration guard additionally inspected incoming Git diffs: a merge containing a
Morfeo-owned contract change was blocked, while a code-only merge was permitted.

| Profile | Permitted checks | Denied checks | Captured real payloads |
|---|---:|---:|---:|
| Morfeo | 1 | 8 | 8 |
| Supervisor | 2 | 7 | 8 |
| Implementer | 3 | 13 | 15 |

For each installed command, the executable bit was removed briefly while the profile remained stopped.
The live registered callback returned Hermes's canonical `failed closed` block on spawn failure; mode
`0700` was restored in `finally`, and the approval mtime still matched afterward. This proves the exact
configured hook, rather than a substitute fixture, takes the crash-net path.

Hermes's upstream hook suites also passed unchanged:

```text
60 passed in 2.51s
```

### 12.4 Constitution Check

| Principle | Phase 4 evidence | Result |
|---|---|---|
| I. Current Intent and Human Authority | The owner explicitly authorized Phase 4; activation and Phase 5 were not inferred | PASS |
| II. Specification Owns Intent | R10 remains the authority owner; runtime corrections were written back to R10 and R13 | PASS |
| III. Autonomous, Bounded Design | The Phase 4 procedure started no worker, model, EC1, or product implementation; the separate owner-launched Morfeo TUI was detected, recorded, and closed before final acceptance | PASS WITH DEVIATION |
| IV. Evidence and Traceable Convergence | Real dispatch, actual permitted/denied file calls, fail-closed spawn tests, and upstream tests back every claim | PASS |
| V. Simplicity Over Ceremony | One standard-library hook per profile; no Hermes-core change, new role, parallel contract, or product tool | PASS |
| VI. Separate Design, Build, and Activation | The build remained separate; closure was held while Morfeo ran and resumed only after the stopped-profile boundary was restored | PASS WITH DEVIATION |

**Constitution Check: PASS WITH DEVIATION.** The stopped-profile pre-activation boundary is restored;
the temporary owner-launched execution remains explicit evidence rather than being erased.

### 12.5 Operational boundary and phase result

The pre-close audit confirmed one hook and one exact approval per profile, unchanged Phase 3 SOUL
hashes, `PRAGMA quick_check = ok`, zero production tasks, and zero production task runs. It then found
a Morfeo TUI process started separately at 03:04:28 on `pts/2`, with a live Morfeo session and one API
call. The Phase 4 procedure did not start that process or invoke that model, but closure was placed on
HOLD because the required stopped-profile state and sidecar condition were no longer true.

The owner closed that TUI at `2026-08-18T03:11:14.267298-06:00`; its session records
`end_reason = tui_shutdown`. A `wal_checkpoint(TRUNCATE)` returned `(0, 0, 0)` and
`PRAGMA quick_check = ok`. The repeated final audit found zero profile WAL/SHM sidecars, zero running
new-profile processes, only the original Hermes TUI, one exact hook and approval per profile, unchanged
SOUL hashes, and an empty consistent production board. Morfeo's structurally excluded execution
capabilities remain absent from both CLI and Telegram surfaces. No credentials were read or printed.

**Phase 4 — Enforcement: PASS WITH DEVIATION (2026-08-18).** Installed enforcement and every
protected-effect matrix passed, and the stopped-profile final state is restored. The deviation is the
temporary owner-launched Morfeo session during closure; it was not an EC1 run or a Phase 5 cutover.
Phase 5 remains unstarted and requires separate explicit authorization. A real worker recording its own
denial remains an activation-stage claim, as stated in R10 §9; the controlled phase tests proved
caller-visible denial without starting a worker.

## 13. Phase 6 autonomous preparation and qualification hold

**Executed**: 2026-08-18, under the owner's explicit instruction to work autonomously on Phase 6,
record blockers as debt, continue every independent step, and finish without waiting for further input.
That instruction authorized the reversible design and evidence-closure work in this section. It did not
authorize Phase 5, model calls, a live worker, EC1, product work, publication, deployment, credentials,
or Hermes-to-Morfeo cutover.

### 13.1 Missing phase corrected without inventing activation

No Phase 6 existed when the instruction arrived. The only legitimate source for one was the plan's
existing “After the run” section and its owning requirements: FR-1331, FR-1336, FR-1339,
R12-FR-1215b, and R12-FR-1219. The correction is therefore deliberately narrow:

- `spec.md` now owns FR-1343 through FR-1351, the post-run qualification contract;
- `plan.md` formalizes “After the run” as Phase 6;
- `README.md` lists qualification after EC1;
- `ROADMAP.md` identifies Phase 6 as evidence closure inside R13, not a new design stage;
- Phase 6 returns only `READY` or `HOLD`; neither outcome activates anything.

The strongest safe progress available before Phase 5 is preparation plus truthful qualification as
`HOLD`. Synthesizing the missing live evidence would violate FR-1343 and R11-FR-1127.

### 13.2 Qualification packet at the current boundary

#### Claim ledger

| EC1 claim | Phase 6 status | Evidence available | Missing evidence and impact |
|---|---|---|---|
| The convergence judge ends a converged unit and budget exhaustion blocks | **Assumed** | Wiring verified in the loaded source; budgets configured | A live converged goal-mode unit and a deliberately unsatisfiable unit. Until then judge behaviour cannot be trusted as measured |
| A terminal event reaches Morfeo through a live gateway | **Assumed** | Wake path verified in source | A Phase 5 terminal event delivered through the live gateway. Until then end-of-work wake delivery remains unmeasured |
| A real worker's evidence supports owner acceptance through one command | **Assumed** | Evidence schema and handoff verified through runtime seams | A real worker completion and owner validation command. Until then evidence sufficiency remains a judgement claim |

No claim was promoted. The temporary owner-launched Morfeo TUI recorded during Phase 4 was not EC1,
did not exercise this contract, and supplies none of the three observations.

#### Provisional-value review

| Value | Current value | Phase 6 disposition | Evidence still required |
|---|---|---|---|
| EC1 concurrency | `1` | Retain as the controlled checkpoint cap | Phase 5 confirms the cap is respected; this does not revise later production concurrency |
| Board-wide / implementer concurrency | Design starting values `4` / `3`; the installed EC1 cap is `1` | Retain provisional; do not apply `4` / `3` to EC1 | Comparative multi-unit evidence; EC1 intentionally does not test parallelism |
| Attempt limit | `3` | Retain provisional | Phase 5 attempt history and later environmental-failure observations |
| Per-attempt runtime limit | `7200` seconds | Retain provisional | Observed duration and liveness from authorized runs |
| Goal-mode turn budget | `20` | Retain provisional | Converged and unsatisfiable Phase 5 outcomes |
| Morfeo / Supervisor / Implementer / judge tiers | Bound in profile configuration | Retain provisional | Controlled same-contract comparison; one EC1 run alone cannot select tiers under R12-FR-1217 |
| Retention values | Not empirically selected | Remain carried-forward debt | Observed growth rate from real runs |

#### Cost account and contradiction review

- **Cost**: unknown, not zero. There is no Phase 5 unit or worker session to correlate and no completed
  R12-FR-1215b integration to exercise. No board cost column was added.
- **Duration**: no Phase 5 attempt exists; configured limits are not observed duration.
- **Contradictions from EC1**: not evaluable because EC1 has not run. “None” would be a fabricated
  finding; the review remains open.
- **Readiness recommendation**: `HOLD`.

### 13.3 Debt register

| ID | Missing prerequisite | Owner | Unblock condition | Affected claim or decision | Evidence already available |
|---|---|---|---|---|---|
| P6-D01 | Explicit Phase 5 authorization and completed EC1 | Christopher | Owner authorizes the bounded paid run and EC1 reaches terminal recorded state | All Phase 6 qualification outputs | Phases 0–4 complete; Phase 5 plan exists; production board is empty |
| P6-D02 | Live convergence-judge outcomes | R13 / Phase 5 | One converged goal-mode unit and one deliberately unsatisfiable unit produce terminal evidence | Claim 1; turn and runtime budgets | Judge wiring verified in source; configured judge and budgets exist |
| P6-D03 | Live wake delivery | R6 / Phase 5 | A terminal EC1 event reaches Morfeo without waking the owner | Claim 2 | Wake path verified in loaded source |
| P6-D04 | Real acceptance-quality evidence | R11 / Phase 5 | Real worker completion supplies the four evidence answers and a runnable owner validation command | Claim 3 | Evidence schema, handoff, and durable board history verified through runtime seams |
| P6-D05 | Per-unit cost correlation | R12 builder | A Phase 5 unit carries a worker session ID and runtime usage is correlated without altering board schema | Cost visibility and model-economics review | Session accounting exists; board absence of cost fields is verified |
| P6-D06 | Comparative evidence for provisional tiers and limits | R7, R12 | Controlled same-contract comparisons and observed run histories exist | Tier assignment, retries, turns, runtime, concurrency | Current values are explicit and labelled provisional |
| P6-D07 | Observed retention growth | R9 | Real board, attempt, artifact, and session growth can be measured over time | Retention values | Store ownership and retention boundaries are designed |
| P6-D08 | Exact Phase 5 owner validation invocation | Phase 5 builder / R11 | The checkpoint quickstart records prerequisites, one command, and expected outcome against the installed runtime | Claim 3 and owner acceptance | CLI/runtime entry points were inspected; no truthful project-specific quickstart can precede EC1 setup |

No debt item grants its own authority. Owner absence is recorded in P6-D01 rather than treated as
permission to run Phase 5.

### 13.4 Constitution Check

| Principle | Phase 6 evidence | Result |
|---|---|---|
| I. Current Intent and Human Authority | Current instruction explicitly authorized autonomous Phase 6 work and debt recording; protected effects were not inferred | PASS |
| II. Specification Owns Intent | FR-1343–FR-1351 were written to the owning spec before the derived plan and indexes were reconciled | PASS |
| III. Autonomous, Bounded Design | Every independent analytical step continued; the Phase 5 dependency became debt rather than a question or fabricated result | PASS |
| IV. Evidence and Traceable Convergence | All three paid-run claims remain assumed; unknown cost remains unknown; direct evidence outranks synthesis | PASS |
| V. Simplicity Over Ceremony | The qualification packet and debt register live in existing R13 artifacts; no new database, workflow, role, or optional file was created | PASS |
| VI. Separate Design, Build, and Activation | Phase 6 started no profile, worker, gateway, judge, model, product work, or cutover and cannot substitute Phase 5 | PASS |

**Constitution Check: PASS for Phase 6 preparation.** Qualification itself remains `HOLD` because its
required Phase 5 evidence does not exist.

### 13.5 Result

**Phase 6 preparation: PASS. Phase 6 qualification: HOLD. Recommendation: HOLD.**

The phase is fully specified, its current packet is populated as far as evidence permits, every blocker
is debt with an owner and unblock condition, and no unsafe gap was hidden. The next protected gate is
still explicit Phase 5 authorization. Until Phase 5 completes, Phase 6 MUST be rerun rather than marked
`READY` from this preparation record.

## 14. Phase 5 authorized EC1 execution

**Executed**: 2026-08-18 after the owner's explicit correction and instruction to execute Phase 5.
That instruction granted activation of the bounded EC1 profiles, workers, goal judge, and model calls.
It granted no product work, publication, deployment, credential change, Hermes-to-Morfeo cutover, or
Phase 6 re-qualification.

**Execution result**: the walking skeleton and its separate negative control both reached their required
durable board outcomes. The positive unit is `done`; the deliberately impossible unit is `blocked` for
goal-turn exhaustion. The run produced evidence for all three EC1 questions and exposed material runtime
contradictions that Phase 6 must qualify before promoting any claim.

### 14.1 Bounded fixture and durable identities

The sacrificial repository is `home/ec1-phase5-fixture/`. It is standalone, local, reversible, and
unrelated to product delivery. Its trusted baseline is `verify.py`; the sole implementation output is
`result.txt` with the exact 20 bytes `b"Aether EC1 verified\n"`.

| Evidence item | Durable identity | Terminal state or role |
|---|---|---|
| Morfeo contract handoff | `t_565e4a9f` | `done`; Supervisor decomposition |
| Sole implementation/review unit | `t_d890f7fc` | `done`; same card used by Implementer and Supervisor |
| Impossible negative control | `t_a1d59043` | `blocked`; goal budget `2/2` exhausted |
| Contract checkpoint | `b78c3a8cc60d089ffe4229ca35709c5e68c93d3f` | Four contract artifacts on `main` |
| Candidate commit | `9352c069ab3ddf1629be2d1eb5a5db845e2d722a` | Worktree branch; adds only `result.txt` |
| Integration commit | `9df875097bd76147d075c8898b03ce8660df2ee8` | Sole implementation cherry-pick onto `main` |
| Post-run contract correction | `180d19e2db33dc2084580e5bae97df704208d277` | Documentation-only lifecycle predicate correction |
| Morfeo live session | `20260818_114836_d98f6c` | Contract creation, mid-flight wakes, final report |

The positive unit used board runs 2–8 after the parent decomposition in run 1. Runs 2–5 preserve the
checkpoint, lifecycle-conflict, and freeze/recovery history; run 6 reached `review_requested`; run 7
performed independent review and the one integration but blocked when the completion predicate was
wrong; run 8 validated the rebound Supervisor predicate and completed the same card. Run 9 is the
separate impossible control.

Real session identities retained by profile are:

- **Morfeo**: `20260818_114447_4a662a` (non-mutating activation probe) and
  `20260818_114836_d98f6c` (live TUI contract/wake session).
- **Supervisor**: `20260818_115430_e8255f`, `20260818_121346_4fdec3`, and
  `20260818_122457_2970ed`.
- **Implementer**: `20260818_115930_a9a870`, `20260818_120030_cef61c`,
  `20260818_120445_655987`, `20260818_120845_63d97d`, `20260818_121145_74d083`,
  and `20260818_123110_643e5d`.

### 14.2 The three EC1 observations

#### Convergence and exhaustion

The positive unit produced candidate `9352c06`, and the live goal judge accepted the run-6
`kanban_request_review` handoff after its predicate was limited to Implementer-owned acceptance. The live
judge then accepted run-8 `kanban_complete` after the same card was rebound to the Supervisor completion
phase. The card reached `done` without exhausting its 20-turn budget.

The negative-control worker received the contradictory requirement that one byte be simultaneously
`0x41` and `0x42`. It responded twice that `0x41 != 0x42`, made no mutation, used no lifecycle transition,
and never claimed success. The judge returned `continue`; the runner then emitted the durable block:

```text
Goal-mode worker exhausted its turn budget (2/2) without completing the task.
```

The scratch workspace contained zero files. This directly observes both branches of claim 1, while the
two-phase predicate correction remains a material finding rather than being hidden inside the pass.

#### Wake delivery

Morfeo created the parent card from a live TUI session, producing a `tui` notification subscription tied
to session `20260818_114836_d98f6c`. The parent `done` event was injected into that same session as an
automatic board message; Morfeo read current board state and re-blocked the prematurely promoted child
before implementation. Later block/review events were also absorbed in the same session. The final child
`done` event caused a further automatic turn in which Morfeo assembled the terminal report from
`kanban_show` evidence. No mid-flight event was sent to the owner.

This is live terminal-channel delivery and agent resumption, not a direct controller call or reconstructed
session memory.

#### Real acceptance evidence

Implementer created one commit that adds only `result.txt`; `verify.py` has no candidate or integration
diff. Supervisor independently inspected bytes and history, ran the validator in the candidate worktree,
performed exactly one local cherry-pick, and ran the validator again in canonical `main`. The final owner
command is:

```text
cd home/ec1-phase5-fixture
python3 verify.py
```

Observed result:

```text
exit 0
PASS: EC1 result is exact
```

The final durable evidence states what changed, both verification stages, retry/unblock accounting, and
the residual stdout-wording discrepancy. A separate isolated missing-result control exited `1` with
`FAIL: result.txt is missing`.

### 14.3 Material runtime findings

| ID | Observation | Controlled response during EC1 | Qualification impact |
|---|---|---|---|
| P5-F01 | The first Morfeo TUI path did not expose the configured `file`/`kanban` tools, and `--in` still opened at `$HOME` | Relaunched with only the already-authorized `file,kanban` toolsets and a temporary `terminal.cwd`; restored `cwd: .` after the run | Profile/TUI activation needs a reproducible supported invocation |
| P5-F02 | Both cards created with `initial_status: blocked` auto-promoted without a controller unblock | Morfeo's live wake re-blocked the child; later gates were recorded explicitly | The documented immediate-human gate is not durable under the active dispatcher |
| P5-F03 | Supervisor's worker-side `kanban_create` contract did not persist `max_retries`; the child row was `NULL` | Controller set the existing row to `3` and recorded a durable comment before execution | Worker-created card limits are not fully expressible through the exposed tool contract |
| P5-F04 | One static goal body cannot safely cover both same-card phases: downstream review criteria rejected Implementer handoff, while an Implementer-only body later made Supervisor completion look unauthorized | Morfeo authored two bounded amendments; controller rebound title/body on the same card, preserving unit, candidate, budgets, and history | R7/R8 same-card goal lifecycle requires a first-class phase predicate or explicit supported rebind |
| P5-F05 | `needs_input` moved the goal card into triage and redispatched Implementer without an explicit unblock, producing runs 4 and 5 | Controller froze by temporarily clearing assignee, preserved candidate `9352c06`, amended the predicate, then explicitly reassigned/unblocked | The active default gateway's triage policy can override profile-local decomposition settings |
| P5-F06 | Supervisor's hook denied integration from the wrong worktree and denied an undecidable compound Git command | Supervisor switched to canonical `main` and a simple inspected cherry-pick, which the hook permitted | Fail-closed enforcement worked and did not deny every valid integration path |
| P5-F07 | Contract wording expected `PASS: result.txt has exact bytes`; the trusted validator actually prints `PASS: EC1 result is exact` | Evidence preserved actual stdout and treated the semantic conclusion separately | Exact expected output must be derived from the installed validator, not prose |
| P5-F08 | Board failure accounting stayed at zero while several lifecycle correction runs occurred | Evidence distinguishes zero implementation/failure retries from one controller-authorized logical resume and multiple non-code lifecycle attempts | Retry terminology needs qualification before R7 values are promoted |
| P5-F09 | The untracked, non-canonical `CLAUDE.md` still says nothing is built and EC1 is pending; its targeted correction was rejected when protected instruction-file approval timed out | Do not bypass the guard; canonical `README.md` and `ROADMAP.md` are current | Reconcile the local instruction file only after explicit instruction-file consent |
| P5-F10 | The Supervisor's run exited with return code `0` without calling `kanban_complete` or `kanban_block`; the dispatcher recorded a protocol violation and re-ran the task | Preserve the run and retry evidence; require the active run to emit a terminal Kanban handoff before downstream promotion | Work can be performed without a durable terminal state, delaying dependency release; the root cause of the missing terminal call remains unverified |
| P5-F11 | Kanban exposes durable status, run state, and heartbeats, but Morfeo has no worker-progress telemetry or live tool/output inspection; a heartbeat cannot distinguish useful work from an idle loop or freeze | Audit status, child terminal states, heartbeat recency, and terminal events, but do not claim semantic progress from `running` alone; require durable milestones or supported progress telemetry before asserting total completion. The later run-21 final verification and `kanban_complete` event confirmed that this task did progress and finish; that evidence was available only retrospectively. | The system completed this exercise, but the available interface could not establish that fact while the Supervisor was still `running`; the observability gap remains a valid workflow issue, distinct from task failure or freeze. |
| P5-F13 | A routine local Hermes update/check was routed through the complete Morfeo → Supervisor → decomposition → Implementer → independent-review path with a 7200-second execution budget, despite the owner's intent to perform a simple update and quickly determine whether current upstream fixed the defect | The owner cancelled card `t_ac0d4ba6` before fan-out; no update or replacement execution remains authorized | The workflow lacks an owner-approved proportional fast path, so low-risk reversible tasks can incur multi-minute or near-hour latency designed for materially riskier project work |
| P5-F14 | Repair of the agent-facing Kanban contract depended on the same delegated Kanban workflow whose defect and process overhead were under repair; the fallback manual update then attempted to rebase an unrelated local contributor-mapping commit and produced widespread conflicts | The rebase was aborted; the owner granted Morfeo a one-time, two-file break-glass repair authorization for DOC-05/P5-F03 | Aether lacks a constitutional emergency path for repairing its own orchestration substrate when normal routing is unavailable, defective, or disproportionate |

At the close of the original Phase 5 exercise, no finding authorized a fourth role, replacement card, second
implementation commit, product work, publication, or Hermes core patch. The later owner authorization in
§15.5 is an explicit bounded exception and must not be projected backward into that evidence.

### 14.4 Session usage and monetary-cost boundary

Profile session databases provide the following Phase 5 accounting. These totals include the bounded
activation probe and all preserved lifecycle attempts; they exclude judge calls that have no separate
profile session row.

| Profile | Sessions | API calls | Input tokens | Output tokens | Cache-read tokens | Reasoning tokens |
|---|---:|---:|---:|---:|---:|---:|
| Morfeo | 2 | 34 | 215,013 | 22,157 | 1,276,928 | 13,073 |
| Supervisor | 3 | 39 | 257,155 | 50,725 | 2,022,400 | 33,125 |
| Implementer | 6 | 58 | 279,626 | 31,540 | 2,165,760 | 23,105 |
| **Total** | **11** | **131** | **751,794** | **104,422** | **5,465,088** | **69,303** |

Every one of those session rows records `cost_status=unknown`, `actual_cost_usd=NULL`, and
`cost_source=none`; its `estimated_cost_usd=0.0` therefore MUST NOT be interpreted as zero cost. The
router's read-only hourly aggregate was also insufficient for EC1 attribution: it exposed only the labels
`hermes` and `unknown`, mixed this control TUI with workers and judges, and carried no task/session key.
Consequently per-unit and total Phase 5 monetary cost remain **unknown**, not zero. P6-D05 has token
evidence but is not unblocked for monetary correlation.

### 14.5 Final runtime state

- Morfeo, Supervisor, and Implementer have zero active processes.
- Their three `state.db` files return `PRAGMA quick_check = ok`.
- The shared board returns `quick_check = ok` with three permanent tasks: two `done`, one intentionally
  `blocked`; its nine run rows preserve two `done`, one `review`, and six `blocked` attempt outcomes.
- Morfeo's temporary `terminal.cwd` is restored to `.` and the board's temporary `default_workdir` is
  restored to `null`.
- The completed worktree was removed without deleting its branch or candidate commit; canonical fixture
  `main` is clean at `180d19e`, and `python3 verify.py` remains `PASS`.
- The impossible scratch workspace remains empty as negative-control evidence.
- WAL/SHM sidecars exist only for the already-active default Hermes state and shared board used by this
  control session. No new-profile WAL/SHM or worker process remains. Stopping the default gateway to
  remove those inherited live sidecars was outside Phase 5 and would disrupt the controlling session.
- No cutover occurred; legacy Hermes remains available.

### 14.6 Handoff to Phase 6

Section 13 is retained as the truthful pre-run qualification packet. Phase 5 now supplies candidate
evidence for P6-D01 through P6-D04 and the exact validation path requested by P6-D08. P6-D05 remains
partially blocked by monetary attribution; P6-D06 and P6-D07 still require comparative and longitudinal
evidence. Phase 6 was **not** re-executed here, no claim was promoted, and no `READY` recommendation or
cutover authority was inferred.

## 15. Owner-authorized documentation closure and first real task

The owner has now authorized the current work to treat Aether as a real project and to use this
documentation-closure task as its first real system task. The scope is:

- audit and reconcile the canonical documentation and its derived indexes;
- identify omissions, contradictions, stale instructions, and runtime claims that lack direct evidence;
- correct each finding within the authority available to the current role, preserving historical evidence;
- use the task's bounded, reversible execution to expose defects in the Aether workflow itself;
- diagnose and report any blocker that cannot be corrected within the available authority or capabilities.

This authorization does not grant publication, deployment, credential changes, Hermes-to-Morfeo cutover,
or deletion of non-canonical evidence. A runtime or code correction discovered during the audit is not to
be silently folded into documentary closure: it must be diagnosed, bounded, and routed through the owning
execution authority. No qualification claim is promoted merely because this task has started; Phase 6 must
still consume the post-EC1 evidence before a current `READY` or `HOLD` recommendation is issued.

### 15.1 Initial documentary audit findings

| ID | Finding | Action | Status |
|---|---|---|---|
| DOC-01 / P5-F09 | The local, non-canonical `CLAUDE.md` still says nothing is built and EC1 is pending, contradicting the canonical post-EC1 record. Its protected instruction-file correction was not available. | Preserve the contradiction as a blocker; do not bypass the instruction-file guard or silently adopt the stale file. | **Blocked externally** |
| DOC-02 | The materialized repository constitution's sync report contained stale TODOs: it said R13 had not listed the constitution and was still in progress. | Add the constitution to R13's configuration inventory and replace the resolved TODOs with a durable status note. | **Corrected** |
| DOC-03 | R13's configuration inventory described Morfeo's bounded file capability as still disabled until Phase 4, despite Phase 4 being complete. Its claim table also read as current rather than historical. | State the pre-Phase-4 design boundary and current bounded build state separately; label the claim table as the pre-run baseline. | **Corrected** |
| DOC-04 | Nine accepted stages retained unchecked `Christopher has reviewed` items despite the recorded R0 and R4–R13 Decision Reviews. | Mark those review checks with the dated acceptance evidence. Retain unchecked empirical/dependency items for later evidence. | **Corrected; debt retained where evidence is absent** |
| DOC-05 / P5-F03 | The worker-facing `kanban_create` surface cannot express the per-task retry budget: `tools/kanban_tools.py:1398-1463` extracts and passes `max_runtime_seconds` but never reads or forwards `max_retries`, and its schema at `:2132-2310` declares `max_runtime_seconds` but no `max_retries`. The loaded Hermes CLI and DB do support it: `hermes_cli/kanban.py:364-372,1557-1584`, `hermes_cli/kanban_db.py:3158-3176,3493-3520`. | Controller-side row repair set `max_retries=3` for this exercise and recorded the defect. A general fix belongs in the loaded Hermes source, requires adding the tool property, parsing/validation, handler forwarding, and regression coverage; Aether must not modify that upstream tree during this task. | **Diagnosed; upstream correction required** |
| DOC-06 / P5-F10 | A Supervisor execution run exited cleanly without emitting the required terminal `kanban_complete` or `kanban_block` handoff. Kanban preserved the evidence as a protocol violation and launched a retry, but the original run did not release its downstream dependency. | Preserve the protocol-violation event and retry history; diagnose why the worker can exit without a terminal lifecycle call and verify that the replacement run closes durably. | **Observed; root-cause diagnosis required** |
| DOC-07 / P5-F11 | Morfeo can inspect Kanban status, child terminal states, run records, and heartbeat recency, but cannot inspect the worker's live operation, tool calls, output, or semantic progress. `running` plus heartbeats therefore could not prove that the total task was advancing or complete during execution; the later run-21 `kanban_complete` event confirmed completion retrospectively. | Preserve this observability boundary; distinguish scheduler liveness from semantic progress and require durable progress milestones or supported worker telemetry for a conclusive audit. Record this exercise as completed, not frozen, while retaining the gap as follow-up debt. | **Confirmed limitation; task completion established retrospectively; observability improvement still required** |
| DOC-09 / P5-F13 | The owner requested a routine Hermes update/check, but Morfeo routed it through the full multi-role project pipeline. That path can take several minutes or approach an hour even when the requested operation is simple, locally reversible, and narrowly testable. | The owner cancelled the continuation before child creation and accepted PD-44: Morfeo chooses agentically between bounded direct stewardship and the substantial-work pipeline against the complete objective, with anti-fragmentation and route change; no fast-lane mechanism or classifier is built. | **Design resolved; local build and owner manual validation pending** |
| DOC-10 / P5-F14 | When Aether's orchestration substrate itself is defective, strict reliance on that same substrate can prevent or excessively delay its repair. The failed delegated continuation and unrelated rebase conflict demonstrated that no accepted emergency repair path currently exists. | The owner authorized Morfeo to repair DOC-05/P5-F03 directly under a one-time two-file boundary. Design a durable break-glass rule with explicit trigger, owner authority, smallest viable scope, rollback, mandatory evidence/review, expiry, and restoration of normal separation. | **Observed; one-time repair authorized; constitutional design required** |

The remaining unchecked items are not blanket completion failures: they represent uninspected dependency
internals, provisional-value calibration, observed retention growth, comparative model evidence, or future
conditional re-reads. They remain visible and must be classified in the final closure report rather than
being marked complete by convention.

### 15.2 Owner clarification: runtime defect mitigation is now primary

The owner has clarified that the documentation audit was valuable primarily because it exposed a
runtime/tool-surface blocker. Documentation closure is therefore **paused**, not discarded: the completed
read-only audit and the canonical findings remain evidence, but no further README/roadmap cleanup is the
primary objective of the current execution.

The primary objective is now to:

1. retain a tested local downstream fix for DOC-05/P5-F03 in an isolated Hermes checkout or worktree;
2. validate that fix through a separate Aether runtime instance, without mutating the active Aether
   checkout or its live profile state;
3. prepare an upstream Hermes change request/PR containing the minimal schema, handler, validation, and
   regression-test correction;
4. keep the local mitigation until an upstream revision containing the fix is available and verified.

The current isolated fixture exercise may finish because it is direct evidence about Aether's board
workflow, but it is not documentation closure and it must not be confused with the Hermes patch. The
active task contract now permits no upstream modification from a child until the separate Hermes worktree,
test boundary, and local-versus-upstream handoff are explicitly recorded. No upstream push or publication
is inferred merely from this clarification.

### 15.3 Owner correction: the newest-upstream check remained incomplete

The owner has corrected the interpretation of the earlier update request. The intended outcome was to update
Hermes sufficiently to establish whether newer upstream revisions already fixed DOC-05/P5-F03. The recorded
execution did not complete that outcome: `fetch origin main --prune` advanced the remote reference, while
`pull --ff-only origin main` stopped because the active local `main` had diverged. No merge, rebase, reset, or
active-framework update followed. Candidate `8b0234418` was correctly developed and verified in isolation,
but that proves the downstream correction, not the state of current upstream and not activation in Aether.

This is now recorded as **DOC-08 / P5-F12 — latest-upstream qualification omitted**. Completion requires an
exact current upstream revision, source and runtime evidence showing whether that revision contains the fix,
the previously accepted focused tool/DB/Ruff/diff/runtime test standard, and a reversible update of the Hermes
installation used by Aether only after the latest-based candidate passes. If upstream already contains the
fix, no redundant PR is prepared. If it does not, the reviewed two-file candidate is ported onto the current
upstream base and reverified before local activation. Upstream publication and TUI restart remain separate;
the owner is told to restart only after the installed revision and rollback reference are verified.

### 15.4 Owner cancellation and proportionality issue

The owner cancelled the DOC-08/P5-F12 continuation after observing that the full delegated pipeline would
again turn a routine update/check into a potentially hour-long wait. Card `t_ac0d4ba6` had started only its
Supervisor qualification phase and had created no children; the binding cancellation stopped it before any
Hermes fetch/update, active-installation mutation, publication, or restart.

This cancellation does not reject validation or supervision as principles. It establishes DOC-09/P5-F13:
the system currently has no accepted way to scale process depth to a task's actual risk and reversibility.

### 15.5 Owner emergency repair authorization

The owner subsequently authorized Morfeo to repair DOC-05/P5-F03 directly because the defect affects the
Kanban surface required by normal delegation and the attempted manual framework update introduced unrelated
rebase conflicts. Inspection confirmed that the rebase had been aborted and that the active
`tools/kanban_tools.py` still omitted `max_retries` from both schema and handler.

The authorization is one-time and bounded to the minimal active-source correction and focused regression
tests described in the plan. It does not authorize upstream publication, dependency/framework update, Git
history mutation, profile/config/database changes, or restart. DOC-10/P5-F14 records the separate design
need: a constitutional break-glass path must be owner-approved before future incidents can rely on it.

The remaining decision concerns the permanent rule: which trigger, authority, rollback, testing, review,
expiry, and observability conditions permit Morfeo to use a direct or expedited repair path in future. The
owner approved the current exception explicitly; Morfeo must not generalize it beyond DOC-05/P5-F03.

### 15.6 Direct upstream qualification and publication result

The omitted upstream check was rerun from a clean clone of the official
`NousResearch/hermes-agent` repository. The valid upstream base at qualification and
implementation time was `2163f7f8ca82f7c892c7e815dadd80a1486cc194`. The earlier
`e02d0bd8dc86d0c9586d9804678034dc6ce1ae53` reference is retracted: GitHub returns
no such commit, so it must not be used as evidence or as an integration base.

The clean upstream source still omitted `max_retries` from the agent-facing
`KANBAN_CREATE_SCHEMA` and `_handle_create` forwarding path in
`tools/kanban_tools.py`. Its corresponding `tests/tools/test_kanban_tools.py` also
contained no focused `max_retries` regression coverage. In contrast, upstream CLI
and database sources already exposed, forwarded, validated, and persisted the
parameter. DOC-05/P5-F03 therefore remained a real upstream interface gap rather
than a redundant downstream patch.

A direct upstream contribution was published as
`NousResearch/hermes-agent` PR `#89590`:
`https://github.com/NousResearch/hermes-agent/pull/89590`. The PR is open from
`DarkArty07:fix/kanban-create-max-retries` at commit
`df163e582d306915aaf46f164b0f6460613d0da1`. GitHub confirms one commit, exactly
two changed files, 99 additions and no deletions: 20 additions in
`tools/kanban_tools.py` and 79 additions in `tests/tools/test_kanban_tools.py`.
The diff adds the optional integer schema field with minimum 1, rejects booleans,
non-integers, zero and negative values before task creation, forwards valid values,
and tests schema, persistence, omission fallback, and invalid-input no-row behavior.

The executor reported 40/40 focused Kanban tool tests passing, the listed narrow
Kanban DB/CLI suites passing, Ruff passing on both files, and `git diff --check`
clean. Broader `tests/tools/` failures were reproduced unchanged on pristine `main`
and classified as unrelated baseline failures. GitHub independently confirms that
the PR is open, non-draft, currently mergeable, and limited to the intended files.

CI is not green yet. Both GitHub Actions workflows (`CI` and
`Docker Build, Test, and Publish`) completed with `action_required`, and no check
runs have executed for the head SHA. A NousResearch maintainer must approve the
external-fork workflows before they can run. The contribution must therefore be
described as locally verified and awaiting upstream CI approval, not as upstream
CI-green, merged, released, or active.

The active Aether checkout remained on its prior `411903b6f...` history with the
pre-existing local uncommitted diff unchanged. It was not updated or restarted by
the upstream contribution. PR publication closes the missing-upstream-candidate
part of DOC-05/P5-F03; merge, release, latest-version local integration, restart,
and live agent-facing activation remain separate states.

### 15.7 Owner decision: PD-44 proportional execution

Christopher accepted Morfeo as owner interlocutor, contract architect, memory/adaptation steward, and
direct operational assistant. Morfeo chooses between direct action and the existing pipeline by reasoning
about the complete requested objective. Scope clarity, bounded consequences, practical reversibility,
decomposition need, parallel-context need, independent-review value, and architectural uncertainty are
conceptual signals rather than numeric thresholds. No classifier, score, special workflow, fast board lane,
new card type, auxiliary router, database, agent, or fourth role is added.

Permanent role reconcentration remains prohibited. Morfeo may not fragment a feature into small mutations
to execute it directly and must stop direct expansion, formalize the canonical contract, and hand exactly
one card to Supervisor when inspection reveals substantial scope. Technical capability does not widen
authority, credentials, product intent, or protected effects.

The owner authorized the local build and chose a mechanical-only implementation verification standard:
configuration parsing, hook syntax/compilation, Markdown/config validity where available, `git diff --check`,
and complete diff review. No live Morfeo behaviour test, prompt benchmark, classification suite,
or functional hook test belongs to this implementation. Christopher will validate the direct-versus-
pipeline behaviour manually afterwards; issue #196 must remain open and the build report must identify
functional behaviour as unverified until that exercise.

### 15.8 Execution-surface correction: stage ignored live state into an Implementer worktree

Supervisor preflight found that the first PD-44 breakdown was not executable as written. The Morfeo profile
targets are ignored live state and therefore absent from a clean Git worktree. A shared `dir` card can see
them, but Hermes 0.20.1 does not assign `HERMES_KANBAN_BRANCH` to that workspace kind, while the active
Implementer hook fails closed on every terminal or file mutation without a branch binding. Assigning content
work to Supervisor or Morfeo would violate the selected substantial-work pipeline.

The accepted correction preserves the roles: Supervisor prepares a blocked child worktree with copies of
only the five non-secret target files and immutable baselines; Implementer authors and mechanically verifies
the candidate under normal branch containment; independent same-card Supervisor review approves or returns
it; a dependent Supervisor integration unit applies exactly the accepted bytes or reviewed diff to the live
stopped profile and shared documents. Workspace seeding and byte-for-byte application are preparation and
integration, not content implementation.

Alternatives rejected: a branchless Implementer `dir` task would bypass active containment; a clean worktree
without staged live inputs cannot implement the requested state; Supervisor or Morfeo authoring would
collapse the selected pipeline; weakening the Implementer hook would enlarge the change and security scope.
Private runtime state is explicitly excluded from staging. A target containing a secret blocks the unit.
The candidate worktree is retained through Christopher's deferred manual validation because no commit or
publication is authorized and because the live application needs an inspectable rollback/reference source.

### 15.9 Current-upstream verification: first worktree spawn loses the branch binding

The staged mechanism was exercised up to its safe boundary. Supervisor created blocked card `t_b02bdbad`,
prepared `.worktrees/t_b02bdbad` on `wt/t_b02bdbad`, copied exactly the five non-secret targets and immutable
baselines, and verified their hashes. No candidate content was changed. The card still carried
`branch_name: null` before claim.

Source inspection explains why it could not be released. In loaded Hermes `0.20.1` revision `411903b6f`,
`_dispatch_once_locked` obtains `claimed`, resolves the fallback branch, persists it with `set_branch_name`,
then invokes `_default_spawn(claimed, ...)` with the stale object. `_default_spawn` exports
`HERMES_KANBAN_BRANCH` only from `task.branch_name`. The first spawn therefore lacks the binding that the
Implementer hook requires. A later retry could observe the persisted value, but deliberately consuming a
failed attempt is not an accepted mechanism.

The authoritative upstream remote was refreshed without modifying the loaded worktree. `origin/main` at
`74f99af470ae8ce47f0903cf431d106cecbd37f2` retains the same ordering and stale-object spawn. GitHub search
found no open NousResearch issue or PR matching the defect. Aether issue #198 now records the finding,
reproduction, impact, and acceptance criteria.

The runtime's automatic decomposition after the repeated block created a branchless Implementer `dir` card
whose body also contradicted Christopher's mechanical-only test standard by requesting broad and functional
tests. The active hook denied its first command before execution; no files changed. That decomposition is
evidence of the same substrate failure, not an authorized fallback. At that checkpoint PD-44 implementation remained blocked pending Christopher's Hermes-repair authority; section 15.10 records the subsequent authorization and verified local correction.

### 15.10 Authorized local correction and upstream report

Christopher authorized Morfeo to correct the Hermes defect locally and continue PD-44, and explicitly asked
that the finding be filed upstream. The loaded editable source was changed only in
`hermes_cli/kanban_db.py` and `tests/hermes_cli/test_kanban_db.py`: each worktree dispatch lane now computes
one effective branch, persists it, and assigns it to the already-claimed in-memory task before spawning.
Regression coverage exercises first ready spawn, first review spawn, and a directory-workspace negative
control that receives no invented branch.

Mechanical evidence: focused regression `3 passed`; full `tests/hermes_cli/test_kanban_db.py` `32 passed,
1 skipped`; Ruff clean; both files compile; scoped `git diff --check` clean. The change is reported at
`https://github.com/NousResearch/hermes-agent/issues/89677`; downstream #198 carries the cross-link.

Activation remains distinct from implementation. Gateway PID 883 imported the old module before the edit.
The runtime correctly denied an attempted `systemctl --user restart hermes-gateway.service` from inside the
gateway because self-restart can terminate the child command before completion. The denial is authoritative:
no alternate signal, process kill, nested dispatcher, database edit, or hook bypass is used. A separate shell
must restart the Aether gateway; only after the new PID is observed may PD-44 dispatch resume.

## 16. Final proportional-Morfeo delivery and owner acceptance

On 2026-08-20 Christopher replaced the earlier narrow capability decision with an explicit final surface.
Amended PD-44 gives Morfeo `code_execution`, `cronjob`, and `delegation` (`delegate_task`) on both CLI and
Telegram, while browser execution and computer use remain excluded. Cron may support Morfeo's bounded direct
work or schedule a future pipeline start; delegated subagents may assist Morfeo's own bounded work but may not
receive product implementation that belongs to Supervisor/Implementer. PD-45 gives `skills` and `vision` to
all three roles without changing their authority. Supervisor and Implementer preserve `code_execution` and
CLI/Telegram parity but do not receive cron or delegation.

The owner authorized a direct, bounded mechanical delivery after the protected-path approval transport made
the worker integration path disproportionate. Twelve of fifteen authorized files changed; the Supervisor and
Implementer hooks and README remained byte-identical. The three YAML configurations parsed, all three hooks
compiled without creating repository bytecode, Hermes resolved the intended effective toolsets on CLI and
Telegram, `git diff --check` was clean, the complete authorized diff was reviewed, and the high-confidence
secret scan returned zero findings. Morfeo, Supervisor, and Implementer remained stopped with zero live
profile processes. No runtime behaviour test was performed as part of that mechanical delivery.

The stable ignored runtime files were recorded by path and SHA-256 so the versioned evidence can identify the
exact delivered state without publishing private sessions, databases, memories, credentials, or other live
profile state:

| Ignored live file | SHA-256 |
|---|---|
| `home/profiles/morfeo/config.yaml` | `d94fa013ba01481a441e66e71aabcd6f8b5bcf6871ceb029432b4e54355db8b4` |
| `home/profiles/morfeo/SOUL.md` | `56a464cd4781b9e2a062c8bb751abae0a5fc1a7a354643cdfc9d8ed6b2c3ed97` |
| `home/profiles/morfeo/hooks/aether_pre_tool_policy.py` | `ab178c80ee6d3f076f8dfb4a53c5ea91ee373af61c71f750b44929fda9f1c3a4` |
| `home/profiles/morfeo/skins/morfeo-aegean.yaml` | `9e0f08b849bd3a45830567aa7b342e7f3ef01df1407c8ab60f8ec406f030a40e` |
| `home/profiles/supervisor/config.yaml` | `2d5d4c4c98e8d81800541b926064d32c10574e545320835ba086191b7808d9ca` |
| `home/profiles/supervisor/SOUL.md` | `cac7cb0c2f0b3242b3105420a9e600156846eeca0c3817deab9b6bedc27040d6` |
| `home/profiles/supervisor/hooks/aether_pre_tool_policy.py` | `ab178c80ee6d3f076f8dfb4a53c5ea91ee373af61c71f750b44929fda9f1c3a4` |
| `home/profiles/implementer/config.yaml` | `26be500d4d0bf8df2c7904403d920d5b77c5b74c87090e9118bb62d3c001a435` |
| `home/profiles/implementer/SOUL.md` | `56a9d07e0401233b15886bd0906f97e875357697272749a40944b3fb8502cb7c` |
| `home/profiles/implementer/hooks/aether_pre_tool_policy.py` | `ab178c80ee6d3f076f8dfb4a53c5ea91ee373af61c71f750b44929fda9f1c3a4` |

The hashes above are the final consolidation snapshot, not only the earlier PD-44/PD-45 transfer snapshot.
After #199 was solved, the three installed hooks were synchronized to one byte-identical policy containing
both the proportional-Morfeo rules and the exact read-only `git branch --show-current` exception. The
persisted Implementer regression suite passes 27/27 against that installed policy, and all three copies
compile. GitHub records #199 closed. Because the common hook and its regression still live only in ignored
profile state in the original local delivery, #200 was opened to make a clean clone reproducible. Merged PR
#201 subsequently closed that debt: `policy/hooks/aether_pre_tool_policy.py` is the sanitized canonical source,
`scripts/sync_policy_hooks.py` provides atomic install/check/restore operations, and
`tests/test_policy_hooks.py` verifies clean-clone reconstruction, secret exclusion, role contracts, and the
#199 regression. Its PR gate passed and all three live copies match the canonical SHA-256 above.

Christopher then exercised the active assistant's direct operational behaviour, accepted that experience as
sufficient functional validation for the proportional route, and explicitly authorized closing Aether issue
#196. GitHub records #196 closed as completed at `2026-08-20T07:39:24Z` with an owner comment preserving that
acceptance and the continuing scope/authority/protected-effect limits. This does not close unrelated issues,
promote Phase 6 to READY, activate a product, deploy, release, or prove every newly exposed tool individually.

During repository consolidation, four dirty Aether worktrees were compared with the final shared README and
ROADMAP. Their README changes were exact duplicates; their remaining ROADMAP lines described superseded
pre-reload or pre-delivery states. Other worktrees held immutable baselines or proposal manifests already
represented by this research record and the live hashes above. They are therefore superseded audit evidence,
not unmerged product work. The clean external Hermes worktree under the Aether `.worktrees` directory belongs
to the separate `max_retries` qualification and is not Aether repository content.

The local `CLAUDE.md` adapter remains non-canonical and ignored. Its reconciliation was attempted during
consolidation, but the protected instruction-file approval prompt expired without a user response. The write
was not retried or bypassed; Aether issue #193 therefore remains open.

## 17. Phase 6 formal qualification gate closed by owner instruction

**Decided**: 2026-08-20, in conversation with Christopher. Asked explicitly whether the §11 Phase 6
qualification gate should be treated as closed or postponed, Christopher chose closure: he is validating
the system through his own direct, ongoing use rather than through a formal analytical packet, and does
not want further work gated on producing one.

**What closes.** The §11 contract (FR-1343 through FR-1351) — claim ledger, provisional-value review, cost
account, contradiction review, debt register, and a `READY`/`HOLD` recommendation — will not be produced.
§13's pre-run `HOLD` packet and §14's Phase 5 candidate evidence remain the permanent, truthful record of
what was actually observed; neither is retroactively rewritten into a completed qualification, because none
was produced. Phase 6's terminal state is **closed**, not `READY` and not `HOLD` — the gate itself ended,
rather than being resolved through it.

**What does not close.**

- **No claim is promoted.** The three EC1 claims (convergence/exhaustion, wake delivery, acceptance
  evidence) keep the disposition §14.2 already recorded — candidate evidence from one live run, not a
  qualified verification. FR-1336's rule still applies: an unrun promotion step must not be treated as
  having silently promoted anything, and closing the gate does not change that.
- **No provisional value is revised.** Model tiers, retry/turn/wall-clock budgets, and concurrency limits
  (spec.md §4) remain provisional under R12-FR-1219 until an owner decision revises them by some other
  route.
- **No cost correlation, cutover, product activation, publication, deployment, or Hermes-to-Morfeo switch
  is authorized by this closure.** PD-09's separation of design, build, and activation is unaffected;
  closing an evidence-qualification gate is not an activation decision.
- **R4–R12's accepted claims are not reopened.** This is a decision about whether to keep running a
  post-hoc qualification process, not a finding that contradicts any accepted requirement, so FR-1339's
  reopen-the-owning-stage rule does not apply here.

**Reason.** Christopher judges his own direct use of the proportional-Morfeo surface — the same standard
already applied to close issue #196 (§16) — sufficient for his purposes, and does not want the design to
keep gating further work on a packet that would duplicate a judgement he has already made informally and
repeatedly.

**Alternative considered.** Deferral (keep Phase 6 as a still-required, merely postponed step) was offered
explicitly and declined in favor of closure.

**Impact.**

- `spec.md` §5's pre-run baseline note and §11's Phase 6 contract are marked closed; the FRs remain as a
  historical record of what a formal qualification would have required, not as live obligations.
- `plan.md`'s Phase 6 phase is marked closed with the same disposition.
- `ROADMAP.md` §6 and §8, and `README.md`'s status section, no longer name Phase 6 re-qualification as the
  next protected gate — there is no next protected evidence gate; the design's remaining protected
  boundary is PD-09 itself (no build authorization is granted by this closure, and no activation is
  authorized without separate explicit instruction).
