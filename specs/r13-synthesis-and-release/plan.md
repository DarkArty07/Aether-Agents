# Implementation Plan: EC1 — The Walking-Skeleton Checkpoint

**Roadmap ID**: R13 / EC1
**Plan status**: written; **not authorized**
**Decision authority**: Christopher
**Derived from**: [`spec.md`](spec.md) §5 and §6, against the accepted R0–R13 baseline
**Parent roadmap**: [`../../ROADMAP.md`](../../ROADMAP.md) §6
**Hermes evidence**: version 0.20.1, revision `411903b6fa258f81afcc3869eb615f6218e1776a`, source `home/.venv-hermes/src/hermes-agent`
**Written**: 2026-08-17

## Summary

EC1 answers **three questions and no others**. Eight of the ten originally unobserved claims were
settled on 2026-08-17 by executing the runtime through its own seams, without creating a profile,
spawning an agent, or calling a model. What remains cannot be settled that way, because each needs a
real model, a live gateway, or a real worker's output.

| # | Claim | Why a run is unavoidable | Answered in |
|---|---|---|---|
| 1 | The convergence judge ends a converged unit, and budget exhaustion blocks rather than exiting silently | The judge *is* a model. Its wiring is verified in source; its behaviour is not observable without calling it (FR-1333) | Phase 5 |
| 2 | A terminal event reaches Morfeo through a live gateway | The wake path is verified in source; delivery needs a running gateway (R6-FR-613) | Phase 5 |
| 3 | A real worker's evidence is sufficient for the owner to accept by | Not mechanically verifiable at all. Only real output answers it (R11 §3) | Phase 5 |

Everything before Phase 5 exists **only** to make those three answerable. This plan therefore
specifies the smallest build that can run one trivial contract end to end — not the product build.

## Technical Context

**Language/Version**: None. EC1 produces no product source. Its artifacts are three profile
configurations, four hook scripts, and three system prompts.

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
| VI — Separate design, build, and activation | **This is the gate that matters.** Phases 1–4 are *build*. Phase 5 is *activation*. Neither is authorized by accepting the design (FR-1337), and Phase 5 needs its own approval separate from Phases 1–4 (FR-1335). |

No violations. The Complexity Tracking table is therefore omitted.

## Authorization state

Three separate authorities, none of them granted by accepting R0–R13:

| Scope | Covers | Status |
|---|---|---|
| Design | R0–R13 | **Granted** 2026-08-17 |
| Build | Phases 1–4: profiles, configuration, prompts, hooks | **Not granted** |
| Activation | Phase 5: the run itself | **Not granted** — separate from build (FR-1335) |

Phase 0 needs neither, because it only reads.

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
  read from the runtime at the time Phase 1 begins, and recorded then. A quickstart written from
  documentation would be the third time this project treated documentation as evidence (PD-41).

### What Phases 1–4 would create

```text
home/                          # Already exists; gitignored except three template files
├── profiles/morfeo/           # Rejected by policy.yml if ever tracked
├── profiles/supervisor/
├── profiles/implementer/
└── hooks/                     # Fail-closed pre-tool-call hooks, per constrained profile
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
| 1.2 Restrict `morfeo` to board, memory, and research tools — no implementation tools | R5-FR-506 | Attempt an implementation tool call as `morfeo` and observe it is unavailable, not merely unused |
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

For EC1 specifically, one guarantee is load-bearing and must be right on the first attempt:
**the supervisor writes each card body as explicit acceptance criteria** (FR-1313, R7-FR-705). The
convergence judge reads that body as its acceptance criteria, so a prose body makes claim 1
untestable — a unit whose body is prose must not run in goal mode at all (R7-FR-733).

**Reversible**: yes, prompts are text.

## Phase 4 — Enforcement *(build)*

Prompts before enforcement would leave protected effects resting on instruction alone (FR-1338).
One fail-closed pre-tool-call hook per constrained profile (R10-FR-1008).

**The three ways this phase can succeed on paper and be inert in fact** — each verified by execution,
each must be actively disproved before Phase 5:

1. **An unconsented hook never fires.** The runtime keeps a first-use allowlist and skips anything
   absent from it. Dispatcher-spawned workers are safe, because the dispatcher passes an explicit
   accept-hooks flag (R10-FR-1008b). **Morfeo is not**, because it runs as a persistent interactive
   session — its hooks stay inert until consented explicitly (R10-FR-1008c, PD-43).
2. **`fail_closed` is a crash net, not deny-by-default.** It converts a spawn error, timeout, or
   malformed output into a block. An ordinary non-zero exit lets the call proceed. A hook must deny
   explicitly with the runtime's block exit code and a block payload (R10-FR-1008d, FR-1008e).
3. **The payload shape is not what the documentation says.** The real payload carries `tool_name` and
   `tool_input` at the top level with call metadata under `extra` — there is no top-level arguments
   key. A hook reading a missing key sees an empty value and, for a deny-unless-permitted rule, denies
   *everything* while looking correct (R10-FR-1008f).

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

**Expect to be woken mid-flight.** Requesting review wakes a subscribed originator the same way a
block does (R6-FR-617a). Those wakes must be absorbed by Morfeo and must not reach the owner
(R6-FR-619). A wake that reaches the owner during EC1 is a finding, not noise.

**Reversible**: the repository work is revertible per unit (R8-FR-820). The board rows are permanent
and are the acceptance record — that is intended, not a leak.

## After the run

1. **Promote or retain.** Each of the three claims becomes *verified* with its evidence, or stays
   *assumed*. A claim not answered is not quietly promoted (FR-1336).
2. **Revise every provisional value** against what was observed, and record the revision
   (FR-1331, R7-FR-713).
3. **Record cost.** It is not on the board — there is no column for cost, tokens, or spend. It must be
   recovered by correlating the unit to its worker session (R12-FR-1215a, FR-1215b). If that
   correlation was not built, say so rather than reporting cost unknown as cost zero.
4. **Correct the owner first.** If EC1 contradicts an accepted decision, the owning stage returns to
   active status with a stated reason. It is not absorbed into this plan (FR-1339).

## What EC1 does not test

Stated so nothing is silently assumed to have been proven:

- Parallelism and per-card worktrees — already verified by execution; EC1 runs at concurrency 1
- Crash reclaim and the attempt/failure accounting — already verified
- The two-tier escalation — already verified end to end
- Integration of several units, conflict reconciliation, and hotspot decomposition — no second unit
- Brownfield work, publication, and any irreversible external effect — excluded by FR-1334
- Whether the tier assignments are right — that needs a controlled comparison, not one run
  (R12-FR-1217)

## Next artifact

`tasks.md` is **not** created by this plan. Under R3's phase assignment the breakdown belongs to the
supervising role, not to the designer — and that role does not exist until Phase 1. Whoever holds
build authority derives it from this plan.
