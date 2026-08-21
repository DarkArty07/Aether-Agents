# Implementation Plan: EC1 — The Walking-Skeleton Checkpoint

**Roadmap ID**: R13 / EC1
**Plan status**: Phases 0–5 complete; Phase 5 produced live evidence with recorded deviations; Phase 6 is **closed** by explicit owner instruction on 2026-08-20 (`research.md` §17) rather than re-executed
**Decision authority**: Christopher
**Derived from**: [`spec.md`](spec.md) §5, §6, and §11, against the accepted R0–R13 baseline
**Parent roadmap**: [`../../ROADMAP.md`](../../ROADMAP.md) §6
**Hermes evidence**: version 0.20.1, revision `411903b6fa258f81afcc3869eb615f6218e1776a`, source `home/.venv-hermes/src/hermes-agent`
**Written**: 2026-08-17
**Amended**: 2026-08-18 — Phase 6 formalized, then Phase 5 executed under separate explicit owner authorization
**Amended**: 2026-08-18 — PD-44 proportional direct execution contract added; obsolete EC1 Morfeo containment superseded
**Amended**: 2026-08-20 — Christopher closed Phase 6 as a required gate; see `research.md` §17

## Summary

EC1 answers **three questions and no others**. Eight of the ten originally unobserved claims were
settled on 2026-08-17 by executing the runtime through its own seams, without creating a profile,
spawning an agent, or calling a model. What remains cannot be settled that way, because each needs a
real model, a live gateway, or a real worker's output.

| # | Claim | Why a run is unavoidable | Answered in |
|---|---|---|---|
| 1 | The convergence judge ends a converged unit, and budget exhaustion blocks rather than exiting silently | The judge *is* a model. Its wiring is verified in source; its behaviour is not observable without calling it (FR-1333) | Phase 5 |
| 2 | A terminal event reaches Morfeo through a live gateway | The wake path is verified in source; delivery needs a running gateway (R6-FR-613) | Phase 5 |
| 3 | A real worker's evidence is sufficient for the owner to accept by running one command | Not mechanically verifiable at all. Only real output answers it (R11 §3) | Phase 5 |

Everything before Phase 5 exists **only** to make those three answerable. Phase 5 produces the evidence;
Phase 6 qualifies it without running more work. This plan therefore specifies the smallest build that
can run one trivial contract end to end — not the product build.

## Technical Context

**Language/Version**: None. EC1 produces no product source. Its artifacts are three profile
configurations, three hook scripts, and three system prompts.

**Primary dependencies**: Hermes Agent 0.20.1 at the revision above — the tree the Aether profile
actually loads, `home/.venv-hermes/src/hermes-agent`, never `/home/darkarty/.hermes/hermes-agent`.
Spec Kit 0.16.4 under `.specify/`.

**Storage**: the board's local database and three separate profile homes. No store is added
(R9-FR-901).

**Testing**: the runtime's own seams — an injectable spawn function and a directly callable board
kernel — for everything that does not need a model (FR-1333a). One paid run for the three claims above.

**Target platform**: one Linux host, single trusted local user (R10-FR-1001).

**Project type**: configuration and prompts layered on an existing runtime. Hermes core is never
forked, vendored, or patched (R4-FR-403).

**Constraints**: three roles, three profiles, no fourth (R5-FR-504). Attempt, turn, and wall-clock
budgets set before any unattended run, because no spending gate bounds a loop (R12-FR-1214). The work
must be trivial, bounded, reversible, and unrelated to product delivery (FR-1334).

**Scale**: one board, three profiles, one contract, one converging unit. Concurrency of one — EC1 is
not a parallelism test, because parallel worktrees are already verified.

## Constitution Check

*Gate: must pass before Phase 0, and be re-checked after Phase 4.*

| Principle | Assessment |
|---|---|
| I — Current intent and human authority | Pass. This plan is written; it executes nothing. Each phase names the authority it needs and stops without it. |
| II — Specification owns intent | Pass. Every step below cites the accepted requirement that produced it. Where a step and a spec disagree, the spec is corrected first, not this plan. |
| III — Autonomous, bounded design | Pass. The phase order is not a code-enforced pipeline; it is the order the design supports. |
| IV — Evidence and traceable convergence | Pass. Every claim EC1 tests is currently labelled *assumed*, and each phase states how it is verified rather than inferred. |
| V — Simplicity over ceremony | Pass. `data-model.md`, `contracts/`, and `quickstart.md` are **deliberately not created** — see *Artifacts not created* below. R0 §6 forbids creating optional artifacts with no content. |
| VI — Separate design, build, and activation | **This is the gate that matters.** Phases 1–4 are *build*, Phase 5 is *activation*, and Phase 6 is evidence qualification. Phase 6 cannot authorize or substitute Phase 5 and produces no cutover authority (FR-1335, FR-1343, FR-1350). |

No violations. The Complexity Tracking table is therefore omitted.

## Authorization state

The current authority ledger is:

| Scope | Covers | Status |
|---|---|---|
| Design | R0–R13, including the Phase 6 amendment | **Granted** 2026-08-17; amended by current owner instruction 2026-08-18 |
| Build | Phases 1–4: profiles, configuration, prompts, hooks | **Granted and completed** 2026-08-18 |
| Activation | Phase 5: the run itself | **Granted and completed** 2026-08-18 by the owner's explicit instruction to execute Phase 5 |
| Qualification | Phase 6: consume Phase 5 evidence; no new run | Autonomous preparation completed as pre-run `HOLD`; **not re-executed** after Phase 5 in this run |

Phase 0 needed neither, because it only read.

## Project structure

### Documentation

```text
specs/r13-synthesis-and-release/
├── spec.md          # Accepted requirements
├── research.md      # Evidence, including the two verification passes
└── plan.md          # This file
```

### Artifacts not created, and why

- **`data-model.md`** — EC1 has no data model. The board's schema is the runtime's, and Aether adds
  nothing to it (R9-FR-901, R12-FR-1215c).
- **`contracts/`** — EC1 exposes no external interface. The outward MCP surface of R6 §5 is a
  legitimate integration but belongs to whoever builds it, not to EC1.
- **`quickstart.md`** — deferred, with a reason. R11-FR-1102 requires a runnable validation path with
  prerequisites, commands, and expected outcomes. Writing one now would mean inventing commands.
  **Verified while writing this plan**: the Hermes CLI declares three entry points
  (`hermes`, `hermes-agent`, `hermes-acp`) and registers **no `board` subcommand** — the board is
  driven through agent-side tools in board mode and observed through the dashboard, not from a shell.
  The exact invocation for standing up a board run is therefore build-time knowledge that must be
  read from the runtime during build and recorded against the installed checkpoint. That record still
  depends on Phase 5 setup and is carried explicitly as P6-D08. A quickstart written from documentation
  would be the third time this project treated documentation as evidence (PD-41).

### Artifacts created by Phases 1–4

```text
home/                          # Already exists; gitignored except three template files
├── profiles/morfeo/           # Rejected by policy.yml if ever tracked
│   └── hooks/aether_pre_tool_policy.py
├── profiles/supervisor/
│   └── hooks/aether_pre_tool_policy.py
└── profiles/implementer/
    └── hooks/aether_pre_tool_policy.py
```

**Structure decision**: everything lives inside profile homes, which are runtime state rather than
repository content. `policy.yml` actively rejects `home/{profiles,skills,plugins,prompts}/` from
version control, so none of it is committed. The reproducible parts already tracked are
`home/.env.example`, `home/SOUL.md`, and `home/config.yaml.template`.

## Phase 0 — Preconditions

Needs no authorization; reads only. Every item is a gate, not a task.

1. **Confirm the evidence tree.** `home/.venv-hermes/src/hermes-agent` is at 0.20.1, revision
   `411903b6…`. If it moved, every claim in R4–R13 is re-reviewed before proceeding (R4-FR-424).
2. **Confirm the three claims are still the only three.** Read [`spec.md`](spec.md) §5. If any of the
   eight verified claims was invalidated by an upgrade, EC1 grows and this plan is rewritten.
3. **Confirm no product work is in flight.** EC1 uses work unrelated to product delivery (FR-1334),
   so nothing of value can be waiting on the board.

**Exit**: the three claims are unchanged and the tree is the one the design was written against.

## Phase 1 — Profiles *(build)*

Three profiles, one per role, each a separate Hermes home (R5-FR-504, PD-27).

| Step | Requirement | Verification |
|---|---|---|
| 1.1 Create `morfeo`, `supervisor`, `implementer`, each with its own description | R5-FR-504 | Three homes exist; no two processes point at one home (R4-FR-411) |
| 1.2 **Historical EC1 baseline, superseded by PD-44**: Morfeo originally lacked terminal and staged generic file access behind contract-path enforcement | Historical R5-D07 | Preserved as build evidence; it is not the current target configuration |
| 1.3 Give each profile a description that does **not** read as a routing hint | R7-FR-706 context | Descriptions are read by the automatic decomposer if it is ever enabled; they must not invite it |

**Reversible**: entirely. Deleting a profile home removes it. Nothing outside `home/` changes.

**Do not** write prompts here. Prompts are Phase 3, and Phase 4 must precede trusting them.

## Phase 2 — Configuration *(build)*

Apply the complete inventory in [`spec.md`](spec.md) §4. It is the whole list: anything absent from
it is a runtime default Aether accepts as-is (FR-1331).

**The two that are not optional:**

| Setting | Value | Why it cannot be skipped |
|---|---|---|
| Automatic triage decomposition | **Disabled** | It fans out any triage card using a model that never read the contract, routing by profile description (R7-FR-706) |
| Automatic triage specification | **Disabled** | It rewrites the body of a card tracing to a contract Aether owns (R7-FR-707) |

These compose with the unblock-loop breaker: a unit that blocks twice for one cause is routed to
triage, where the decomposer would consume it and split it across profiles — the exact role-overload
failure PD-13 names (R7-FR-709).

**Budgets, before anything runs unattended** (R12-FR-1214). All provisional (R7-FR-713):

- Board-wide concurrent units: **4**; per implementer profile: **3** — but EC1 runs at **1**
- Attempts per unit: **3**, never 2, because a crash consumes an attempt (R7-FR-738b)
- Wall-clock per attempt: **2 hours**
- Goal-mode turn budget: **20**

**Also set**: model tier per profile (frontier / capable / inexpensive, provisional); convergence
judge slot configured explicitly (R12-FR-1211); decomposer and specifier slots left unused *and* their
behaviours disabled (R12-FR-1210); dashboard bound to loopback only (R10-FR-1003); inbound
agent-to-agent adapter disabled (R6-FR-608); one board.

**Verification**: FR-1332 requires the two disabled behaviours be *verified* as disabled, not assumed
from configuration having been written. Place a card in triage on an isolated board and confirm it is
neither fanned out nor rewritten.

**Reversible**: yes. Configuration is a file per profile.

## Phase 3 — Prompts *(build)*

Three system prompts, written to the guarantees in [`spec.md`](spec.md) §3 — thirty-two requirements
across Morfeo, the supervisor, the implementer, and all three. Writing the wording is build and is
deliberately left open (R1 §1, PD-09).

Two rules that constrain every line:

- A prompt **must not** restate what the runtime already injects into every board worker. Duplication
  produces two sources of instruction that will drift (FR-1328, PD-25).
- A prompt **must not** be the only thing preventing a protected effect. Everything on R10 §5 is
  enforced by a hook and the prompt is reinforcement (FR-1330).

**Historical EC1 correction, superseded by PD-44**: EC1 activated generic file access only for
contract authorship. The current Morfeo build target is the coherent direct-stewardship doctrine in
`spec.md` FR-1307 and FR-1310c through FR-1310h: general project file access plus terminal, with route
selection performed agentically and no obsolete no-execution or contract-only language retained.

For EC1 specifically, one guarantee is load-bearing and must be right on the first attempt:
**the supervisor writes each card body as explicit acceptance criteria** (FR-1313, R7-FR-705). The
convergence judge reads that body as its acceptance criteria, so a prose body makes claim 1
untestable — a unit whose body is prose must not run in goal mode at all (R7-FR-733).

**Reversible**: yes, prompts are text.

## Phase 4 — Enforcement *(build)*

**Result: PASS with a recorded deviation on 2026-08-18.** Installed evidence and the Constitution
Check are recorded in [`research.md`](research.md) §12. A separately launched Morfeo TUI temporarily
held operational closure; it was closed, checkpointed, and the final audit passed. This result does not
authorize Phase 5.

Prompts before enforcement would leave protected effects resting on instruction alone (FR-1338).
One fail-closed pre-tool-call hook per constrained profile (R10-FR-1008).

**Historical EC1 capability gate, superseded in scope by PD-44**: the atomic-transition lesson remains,
but contract-only path denial does not. The current transition prepares the complete SOUL, effective
`file + terminal` toolsets, and reconciled hook before applying them together while Morfeo is stopped.
The hook retains independent protected effects and other-role limits; it neither blocks terminal in
general nor chooses the direct/pipeline route (R5-FR-506e, R10-FR-1008h).

**The three ways this phase can succeed on paper and be inert in fact** — each verified by execution,
each must be actively disproved before Phase 5:

1. **An unconsented hook never fires.** The runtime keeps a first-use allowlist and skips anything
   absent from it. Dispatcher-spawned workers are safe, because the dispatcher passes an explicit
   accept-hooks flag (R10-FR-1008b). **Morfeo is not**, because it runs as a persistent interactive
   session — its hooks stay inert until consented explicitly (R10-FR-1008c, PD-43).
2. **`fail_closed` is a crash net, not deny-by-default.** It converts a spawn error, timeout, or
   malformed output into a block. An ordinary non-zero exit lets the call proceed. A hook must deny
   explicitly with the runtime's block exit code and a block payload (R10-FR-1008d, FR-1008e).
3. **The payload shape is not what the documentation says.** A real capture showed `tool_name`,
   `tool_input`, and `session_id` at the top level; `task_id`, `tool_call_id`, `turn_id`,
   `api_request_id`, and `middleware_trace` are under `extra`. There is no top-level `args` key. A hook
   reading a missing key sees an empty value and, for a deny-unless-permitted rule, denies *everything*
   while looking correct (R10-FR-1008f).

**Verification, in this order:**

1. Confirm every hook is allowlisted on its profile — especially Morfeo's (R10-FR-1008a).
2. Capture one real payload and confirm the hook reads the keys the runtime actually delivers. Do not
   validate with the built-in test harness alone: it merges into a synthetic payload rather than
   replacing it (R10-FR-1008g).
3. Deny one protected effect from R10 §5 and observe the block, then confirm a *permitted* call still
   proceeds — proving the rule is not denying everything.

**Re-run the Constitution Check here.** Principle VI's boundary is crossed next.

**Reversible**: yes, but note the asymmetry — an implementer's containment is enforced, not structural
(R10-FR-1005). Removing the hook removes the containment.

## Phase 5 — The run *(activation — separate authorization)*

**This phase requires its own explicit approval. Accepting the design did not grant it, and neither
does completing Phases 1–4** (FR-1335).

The work: trivial, bounded, reversible, unrelated to product delivery (FR-1334). One contract, one
supervisor decomposition, one implementer unit that converges, one integration.

At least one unit must run in **goal mode** with an acceptance-criteria body, or claim 1 is not tested.

| Observation | Answers | Success looks like |
|---|---|---|
| The judge ends the unit when criteria are met | Claim 1 | Terminal state reached without the turn budget running out |
| A deliberately unsatisfiable unit exhausts its budget | Claim 1 | Reported *not converged* and **blocked for review** — not a silent exit, not a failure (R7-FR-732) |
| The terminal event wakes Morfeo | Claim 2 | Morfeo resumes and assembles the report from durable board state, never from memory (R11-FR-1114) |
| The completion evidence | Claim 3 | Answers what changed, how it was verified, what would unblock a retry, and what risk is left open — and the owner can accept by running one command (R11-FR-1105) |

**Execution result (2026-08-18): Phase 5 completed with live evidence and material runtime findings.**
The authorized run created one sacrificial contract, one Supervisor decomposition, one Implementer unit,
one independently reviewed integration, and one separate impossible negative-control unit. The positive
unit reached `done`; the negative control exhausted `2/2` goal turns and reached `blocked` without a false
success or workspace mutation. A terminal parent event and the final unit event both resumed the same
live Morfeo TUI session, whose final report was assembled from board state. The owner validation command
`python3 verify.py` exits `0` and prints `PASS: EC1 result is exact` in the canonical fixture repository.

The run also exposed lifecycle contradictions: initial `blocked` cards auto-promoted, the worker-side
creation tool omitted `max_retries`, a same-card goal predicate had to be rebound between Implementer
handoff and Supervisor completion, and a `needs_input` block entered triage and redispatched without a
controller unblock. These are evidence, not silently repaired design claims. The exact trace, session
identifiers, token account, and debts are in [`research.md`](research.md) §14.

**Expect to be woken mid-flight.** Requesting review wakes a subscribed originator the same way a
block does (R6-FR-617a). Those wakes must be absorbed by Morfeo and must not reach the owner
(R6-FR-619). A wake that reaches the owner during EC1 is a finding, not noise.

**Reversible**: the repository work is revertible per unit (R8-FR-820). The board rows are permanent
and are the acceptance record — that is intended, not a leak.

## Phase 6 — Qualification and release decision *(closed 2026-08-20; never activation)*

**Closed by explicit owner instruction on 2026-08-20** (`research.md` §17): Christopher chose closure over
deferral, preferring his own direct use of the system to a formal qualification packet. What follows is
retained as the historical record of what that packet would have required — it is not a live obligation,
and it will not be produced without a new owner decision to reopen it.

Phase 6 would have consumed the completed Phase 5 record. It would have started no profile, worker, judge, gateway, or model.
Its authority is analytical: qualify evidence, revise provisional decisions, expose debt, and return a
`READY` or `HOLD` recommendation to the owner. Neither result performs a cutover or starts product work
(FR-1343, FR-1350).

**Entry gate:** Phase 5 completed under its own explicit authorization, with stable board rows, worker
session identifiers, completion evidence, wake evidence, and both convergence outcomes. If any input is
absent, record the corresponding debt and continue every independent review; the phase remains `HOLD`
(FR-1344, FR-1349).

**Current handoff:** Phase 5 now supplies the live entry evidence. Research §13 remains the truthful
pre-run `HOLD` packet and is not retroactively rewritten as a qualification result. Phase 6 must be run
again, without model or profile activation, against research §14 before any claim is promoted or any new
`READY`/`HOLD` recommendation is issued.

1. **Promote or retain.** Each of the three claims becomes *verified* with its evidence, or stays
   *assumed* with the missing observation and impact. A claim not answered is not quietly promoted
   (FR-1336, FR-1345).
2. **Revise every provisional value** against what was observed, or retain it explicitly as provisional
   with the evidence still needed (FR-1331, FR-1346, R7-FR-713).
3. **Record cost.** It is not on the board — there is no column for cost, tokens, or spend. Correlate the
   unit to its worker session and use runtime accounting. Missing correlation is debt; unknown is never
   zero (R12-FR-1215a, FR-1215b, FR-1347).
4. **Correct the owner first.** If EC1 contradicts an accepted decision, return the owning stage to
   active status with the contradiction and evidence. Do not absorb it into this plan (FR-1339,
   FR-1348).
5. **Assemble the qualification packet.** It contains the claim ledger, provisional-value review, cost
   account, contradiction review, and debt register. Every debt names prerequisite, owner, unblock
   condition, impact, and existing evidence (FR-1351).
6. **Recommend, never activate.** Return `READY` only when all Phase 6 outputs are complete and no
   unresolved item makes a first sacrificial product contract unsafe. Otherwise return `HOLD` with the
   exact debts. Both outcomes still require a later owner decision (FR-1350).

Owner unavailability widens none of these authorities. Phase 6 continues through every safe analytical
step and records protected or missing decisions as debt; it never guesses credentials, acceptance,
spending authority, Phase 5 evidence, or cutover consent (FR-1349).

**Reversible**: Phase 6 changes qualification documents only. Phase 5 board rows remain the permanent
acceptance record, and no runtime state is changed.

## What EC1 does not test

Stated so nothing is silently assumed to have been proven:

- Parallelism and per-card worktrees — already verified by execution; EC1 runs at concurrency 1
- Crash reclaim and the attempt/failure accounting — already verified
- The two-tier escalation — already verified end to end
- Integration of several units, conflict reconciliation, and hotspot decomposition — no second unit
- Brownfield work, publication, and any irreversible external effect — excluded by FR-1334
- Whether the tier assignments are right — that needs a controlled comparison, not one run
  (R12-FR-1217)

## Owner-authorized task: documentation closure and first system exercise

This task is the first real task the owner has assigned to Aether itself. It is a brownfield
documentation task against this repository, not a new design stage and not product delivery.

### Scope

1. Audit the canonical documentation, derived indexes, materialized constitution, runtime evidence,
   and local instruction files for omissions, contradictions, stale claims, and unverified assertions.
2. Update each finding in its owning artifact first, preserve historical evidence, and reconcile only
   dependent artifacts.
3. Keep accepted design, completed build, executed EC1 evidence, and post-EC1 qualification as distinct
   statuses; do not promote a runtime claim or declare `READY` without the Phase 6 contract.
4. Use the task itself as a bounded, reversible system exercise through the durable board. Any workflow
   defect that cannot be corrected within the active authority is diagnosed with its evidence,
   owner, impact, and unblock condition.

### Brownfield boundary

- Follow the repository constitution, `AGENTS.md`, the owning-spec rule, and the canonical manifest.
- Modify canonical documentation only through the owning role and on the integration branch.
- Do not modify upstream Hermes or Spec Kit trees, credentials, sessions, databases, or live runtime state
  outside the already-authorized bounded exercise.
- Treat `CLAUDE.md` as a non-canonical local instruction file until its protected correction authority is
  explicitly available; its stale status must be reported rather than silently incorporated.
- Do not create a fourth role, a parallel contract artifact, a product source tree, or a new roadmap stage.

### Acceptance and evaluation standard

The task is complete only when all of the following are evidenced:

- canonical source ownership and document order are explicit;
- contradictory status statements are reconciled or explicitly retained as historical evidence;
- every remaining unchecked item is classified as closed, owner review, unverified evidence, or accepted
  debt with an owner and unblock condition;
- internal links and repository policy checks pass;
- the real board exercise produces durable handoff, execution/review outcomes, and an evidence-based
  completion report;
- any discovered runtime or authority defect is corrected in its owning artifact or returned as a
  diagnosed blocker;
- no publication, deployment, credential change, cutover, or irreversible effect occurs.

The repository's existing policy workflow remains the only automated repository gate. The board exercise
is additional runtime evidence for this task, not a replacement gate and not a qualification of every
general Aether scenario.

### Owner amendment: prioritize Hermes defect mitigation

The owner has reprioritized this task after the board exercise exposed DOC-05/P5-F03. The documentation
audit is retained as evidence and its remaining cleanup is paused. The active work now prioritizes a local,
tested downstream correction in an isolated checkout/worktree of the loaded Hermes source, followed by
validation through a separate Aether runtime instance and preparation of an upstream Hermes change request.

The local patch must add `max_retries` to the agent-facing `kanban_create` schema and handler, validate and
forward it to the existing database API, and include focused regression coverage. The patch must not be
applied to the active Aether checkout while its current board exercise is running. A child worktree may
modify the Hermes source only under this amended contract; it must not modify canonical Aether documents,
credentials, sessions, databases, or live profile state. Upstream push/publication remains a separate
protected effect: local preparation and verification precede any request to publish a PR.

### Owner correction: qualify and update against current upstream

The owner has corrected the execution record: the requested Hermes update was intended to determine whether
the newest upstream revision already contained the `max_retries` correction. The prior `fetch` updated the
remote reference, but the active checkout's `pull --ff-only` stopped on divergence; the isolated downstream
candidate was then implemented and verified without completing the requested latest-upstream comparison or
active local update. A successful fetch or an isolated patch is not completion of this requirement.

Supervisor must now execute one bounded continuation with this order:

1. preserve the active checkout's current revision, divergence, and candidate `8b0234418` as rollback
   evidence; do not merge or overwrite unknown local history;
2. fetch and identify the exact current `origin/main`, then create a pristine isolated worktree or checkout
   at that revision;
3. determine from source and execution whether upstream already exposes, validates, and forwards
   `kanban_create.max_retries` with the required omission and invalid-input behavior;
4. apply the previously accepted test standard to pristine upstream: the focused Kanban tool suite, narrow
   Kanban DB suite, Ruff on the scoped files, `git diff --check`, and the isolated runtime behavior matrix;
5. if upstream already fixes the defect, record the owning upstream commit and do not prepare a redundant
   patch; if it does not, port the reviewed candidate onto the current upstream base in isolation, retain the
   two-file scope, and rerun the same standard;
6. only after the latest-based candidate passes, update the Hermes installation used by Aether through a
   reversible local integration that preserves an explicit rollback reference, verify the installed source
   and import path, and stop before restarting this TUI;
7. return the exact installed revision, rollback reference, test evidence, upstream-fix determination, and
   the explicit signal that the owner may restart. After restart, the live agent-facing smoke test remains
   required before the correction is called active.

No force-push, upstream push, pull-request publication, merge, release, credential/session/database mutation,
or automatic TUI restart is authorized. Publication remains a separate owner decision.

### Owner cancellation: latest-upstream continuation withdrawn

The owner has cancelled the continuation above before Supervisor fan-out. It is retained as historical
evidence of the requested operation but is no longer executable authority. Card `t_ac0d4ba6` was stopped
before creating children; no fetch, Hermes update, active-installation mutation, publication, or restart is
authorized by this cancelled contract.

The cancellation exposes DOC-09/P5-F13: routing a routine local framework update through the complete
Morfeo → Supervisor → decomposition → Implementer → independent-review path can impose multi-minute or
near-hour latency disproportionate to the task. The owner requested a simple update and should not have to
wait for a full pipeline merely because the operation entered the general project workflow.

No fast path is selected here. A replacement design requires an owner decision defining which risk,
authority, reversibility, testing, and observability conditions permit direct or expedited execution, and
which conditions still require full supervision. Until that decision is accepted and materialized, there is
no active contract to update Hermes.

### Owner emergency authorization: repair the orchestration substrate directly

After the delegated path and the manual update attempt obstructed repair of the very Kanban surface needed
to operate that path, the owner explicitly authorized Morfeo to apply DOC-05/P5-F03 directly to the active
local Hermes source. This is a bounded break-glass authorization for this defect, not general product-
implementation authority and not permission to publish upstream.

The authorized mutation is limited to `tools/kanban_tools.py` and its focused regression coverage in
`tests/tools/test_kanban_tools.py`: expose optional integer `max_retries` with minimum `1`, reject booleans,
strings, floats, zero, and negative values before any database row is created, forward accepted values to
the existing `kanban_db.create_task` API, and preserve omission as `NULL`/existing fallback. The previously
accepted test standard remains binding: focused Kanban tool tests, narrow DB tests, Ruff, diff validation,
and a post-restart live tool smoke test. No Git history rewrite, dependency update, profile/config/database
mutation, restart, or publication is authorized by this exception.

The constitutional follow-up is separate: DOC-10/P5-F14 must define an owner-approved emergency repair path
for failures in the orchestration substrate, including trigger, scope, evidence, rollback, review, expiry,
and restoration of normal role separation. This one-time authorization must not silently become that rule.

## PD-44 amendment — proportional direct execution for Morfeo

**Authority**: Christopher explicitly authorized the design and local build on 2026-08-18. At that checkpoint
this did not authorize commit, push, pull request, issue closure, release, deployment, history rewrite,
cleanup of unknown local work, or any other external protected effect. Subsequent owner decisions on
2026-08-20 expanded the capability surface, accepted PD-45, accepted functional evidence for #196, and later
authorized repository consolidation and publication; those later effects are recorded in R13 research rather
than retroactively presented as part of the original authority.

**Goal**: Morfeo remains the owner's interlocutor and contract architect and also becomes the owner's direct
operational steward. It acts directly on bounded complete objectives when the full pipeline adds no
proportionate guarantee; substantial work still uses Morfeo → Supervisor → Implementer(s). The route is an
agentic judgement, not a classifier or workflow mechanism.

### Exact build order

1. Reconcile `DESIGN.md` and R1/R5/R7/R8/R10/R12/R13 against PD-44 before product mutation.
2. Rewrite `home/profiles/morfeo/SOUL.md` as one coherent doctrine, including identity, direct route,
   pipeline route, conceptual signals, whole-objective anti-fragmentation, direct scope inspection,
   direct-to-pipeline route change, proportionality, and unchanged authority limits.
3. Update `home/profiles/morfeo/config.yaml` so the effective toolsets include `kanban`, `file`, and
   `terminal`, preserving existing auxiliary composition and enabling no unrelated toolset.
4. Reconcile `home/profiles/morfeo/hooks/aether_pre_tool_policy.py` surgically: remove obsolete Morfeo
   general execution denial and contract-only writes; retain secret/credential protection and every
   Supervisor/Implementer protection; add no route classifier or size gate.
5. Apply SOUL + configuration + policy together while Morfeo is stopped. There is no deliberate runnable
   intermediate state with mixed doctrine.
6. Reconcile README, ROADMAP, current boundary, configuration inventory, and documentary stage status.
7. Review consistency and the complete diff without resetting, cleaning, stashing, or discarding the
   uncommitted Aether baseline.
8. Deliver the local result to Christopher for his later manual direct-versus-pipeline validation.

### Ignored live-profile workspace mechanism

The Morfeo profile is ignored runtime state, so a clean worktree does not contain it; a shared `dir`
workspace also lacks the branch binding required by the active Implementer hook. Resolve that substrate gap
without changing roles:

1. Supervisor creates the single atomic Implementer card initially blocked with a worktree path and records
   its returned task id.
2. Supervisor prepares that task's `wt/<task-id>` worktree and copies only the current non-secret target
   files — Morfeo SOUL, config, policy hook, README, and ROADMAP — plus immutable baseline copies into it.
   No `.env`, credential, token, session, memory, database, keyring, or other private runtime state is copied.
3. Supervisor verifies the worktree branch binding and staged-file manifest, then unblocks the card. This is
   workspace preparation, not content implementation.
4. Implementer edits and mechanically verifies the atomic candidate in the branch-bound worktree, then
   requests same-card independent Supervisor review.
5. A dependent Supervisor integration card applies only the independently approved candidate bytes or
   reviewed diff to the live stopped profile and current README/ROADMAP, repeats the mechanical checks, and
   reports the exact application. Supervisor may not introduce new content during integration.
6. Preserve the candidate worktree and baseline evidence until Christopher completes the deferred manual
   validation. If any required target contains a secret, block instead of staging it.

**Execution status — local repair verified; external gateway reload required.** Real preflight created and
safely seeded candidate `t_b02bdbad`, then exposed #198. Christopher authorized the bounded runtime repair.
The editable Hermes source now propagates the effective branch to the in-memory claimed task before first
spawn in both ready and review lanes. Focused regression is 3/3; the full Kanban DB test file is 32 passed,
1 skipped; Ruff, compilation, and diff checks pass. The defect is published upstream as
`NousResearch/hermes-agent#89677`.

Dispatcher PID 883 loaded the module before the edit. Restarting `hermes-gateway.service` from this session
was denied by the gateway's self-termination guard and must not be worked around. Christopher must restart
that service from a separate shell. Until its PID/reload is verified, do not release `t_b02bdbad`, create a
replacement PD-44 card, consume a retry, edit the Kanban database, set a global branch in `.env`, weaken the
hook, or accept auto-decomposed branchless work. Morfeo remains stopped and no PD-44 functional test has run.

### Prompt acceptance

- Morfeo is explicitly the owner interlocutor, designer, contract architect, memory/adaptation steward,
  and direct operational assistant — neither an exceptional file toucher nor Aether's general Implementer.
- Direct action is appropriate when the complete objective is understood and bounded, consequences are
  inspectable, correction or reversal is reasonably simple, significant decomposition or parallel context
  is unnecessary, and independent review adds no proportionate value.
- Features, architectural changes, multiple responsibilities, complex integration, valuable independent
  review, or material uncertainty use the pipeline.
- No numeric threshold, line/file/time count, score, classifier, special workflow, fast lane, or external
  gate decides the route.
- Morfeo evaluates the owner's complete objective and may not fragment substantial work into small direct
  mutations. It may inspect directly to determine scope; if the real work grows, it stops expansion,
  finalizes the canonical contract, and hands exactly one card to Supervisor.
- The prompt says: use the process that fits the problem, not the maximum process available.
- Current instruction, scope, credentials, product decisions, protected effects, incidental-work disclosure,
  and the distinction between capability and authority remain binding.

### Capability and hook acceptance

- Effective Morfeo platform toolsets include exactly the newly decided operational surface:
  `kanban + file + terminal`, plus pre-existing auxiliary memory/research composition.
- File access is not restricted to contract artifacts inside the managed project.
- Terminal is not generally denied to Morfeo, and no denial text says Morfeo has no execution or
  implementation authority.
- Browser execution, computer use, sandboxed code execution, cron, and delegation are not enabled by this
  amendment.
- The hook retains transversal secret and credential controls and all Supervisor/Implementer controls.
- R10 does not classify direct versus pipeline work and does not treat Morfeo writing project code as a
  protected effect in itself.
- Implementation of ignored live profile state uses the isolated staged-candidate and dependent Supervisor
  integration mechanism above; neither a branchless Implementer `dir` task nor direct Supervisor authoring
  is permitted.

### Explicit non-goals and verification standard

No classifier, decision engine, database, new card type, fast board lane, new agent, fourth role, numeric
threshold, risk score, prompt benchmark, classification suite, or external route mechanism is built.
Supervisor and Implementer are not redesigned.

Verification is deliberately mechanical only: parse the changed configuration, compile/check hook syntax,
check Markdown/config validity as available, run `git diff --check`, inspect the complete diff for doctrinal
contradictions, and confirm no unrelated toolset was enabled. Do not run a live Morfeo behaviour test, prompt
benchmark, route-classification suite, or functional hook test as part of this implementation. The final
report must state that functional behaviour remains unverified until Christopher's manual exercise and must
leave issue #196 open.

## Next artifact

`tasks.md` is **not** created by this plan. Under R3's phase assignment the breakdown belongs to the
supervising role, not to the designer — and that role does not exist until Phase 1. Whoever holds
build authority derives it from this plan.
