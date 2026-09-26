# RC16-CANARY evidence — installed-runtime Project→child→same-card-review canary and AC7 controls

## Context and boundaries

- **Unit:** `RC16-CANARY` (Supervisor, same-flow card)
- **Objective Contract:** `oc_c770cea3db51d97e@v2` AC6 / AC7
- **Material design:** `specs/issue-494-project-provenance/plan-release.md` §5
- **Runtime under test:** the SELECTED installed release, binding maintained-fork Hermes
  `58f8c37a49b341f25b8fdd6310542fe932031b8d` with materialized digest
  `a2a9b374bd2022c7f96242b0ab2c95691119262c925389eb3820ca627c581144`
- **Result:** AC6 and all three AC7 control paths pass on the selected runtime.
- **Explicit non-claims:** This canary proves the #494 Project/child/review behaviour on the
  selected installed runtime. It does not prove any general speed improvement, agent-behaviour
  gain, or stable-release qualification.

## Precondition

`aether doctor` reported `result: ready` with `active_version 1.0.0rc16`, and the loaded
maintained-fork source at the pinned commit with the pinned digest. The canary was therefore
authorized to run as acceptance.

## Module origin (the result cannot be attributed to another tree)

The canary loaded the **installed release tree**, not a fork checkout, and printed the resolved
origins:

| Module | Origin |
| --- | --- |
| `hermes_cli.kanban_db` | the selected release's `hermes-source/hermes_cli/kanban_db.py` |
| `hermes_cli.projects_db` | the same release tree |
| `tools.kanban_tools` | the same release tree |

The exercised resolver file's SHA-256 is `465000e602df324fec8c39d36bfc7effcbf7b021d4a1a2d888afc53afd3b3a17`,
which matches the digest recorded for the reviewed HLP-428 fix, so the fixed source is the one
that answered.

Independently, the installed tree's own reviewed regression module was executed against that
same tree with its own interpreter resolution: **5 passed** (`test_kanban_project_provenance.py`,
covering AC1 red reproduction, AC2 supported route + early refusal, AC3 mismatch matrix, AC4
bounded containment).

## Disposable construction (reproducible)

All state is disposable: a scratch git repository under a system temp root, a disposable kanban
home containing the boards, and two separate profile homes.

- The **origin** profile home holds the canonical Project row in its own registry.
- The **child-creating** profile home deliberately holds no such row, reproducing the
  cross-profile boundary that caused the original defect.
- Board routing was pinned explicitly with the same variables the dispatcher injects into
  workers (`HERMES_KANBAN_HOME`, `HERMES_KANBAN_DB`, `HERMES_KANBAN_BOARD`,
  `HERMES_KANBAN_WORKSPACES_ROOT`), and `HERMES_KANBAN_TASK` / `HERMES_KANBAN_RUN_ID` /
  `HERMES_SESSION_ID` were cleared, so no live board could be reached by accident.

## AC6 — supported shape on the selected runtime

| # | Criterion | Observed |
| --- | --- | --- |
| 1 | Project-bound Supervisor continuation, explicit `dir` workspace, **no** session affinity | parent row: canonical Project persisted, `workspace_kind=dir`, absolute shared worktree path, `session_affinity=null`; claimable, then completed by the origin |
| 2 | Canonical Project in the origin binding; child-creating profile lacks a convenient row | origin registry holds the row; child-creating registry is empty; the child was still created through the supported path |
| 3 | Child created with the explicit canonical Project and a direct parent edge, child workspace left to the supported path | create returned ok; child row carries the same canonical Project; a direct parent edge exists |
| 4 | Non-null canonical Project persisted; **fresh project worktree** rather than scratch | child `project_id` equals the canonical Project (non-null), `workspace_kind=worktree`, path is `<repo>/.worktrees/<child-id>`, and the directory exists on disk with `git rev-parse --is-inside-work-tree` → `true`; branch is project-slug/task-keyed |
| 5 | Child reaches same-card review | the implementer run closed with outcome `review_requested`; the card moved to `review` with reviewer `supervisor` |
| 6 | Distinct Supervisor review claim/receipt with `source_status=review` | the review-lane claim event carries `source_status: "review"` and a `profile` of `supervisor` — a different identity from the implementer run |
| 7 | Review completes without a claim/reclaim loop, null worker identity or lost Project | the review claim is held by its own run with a concrete worker pid; the task keeps the canonical Project; the dispatcher reported no auto-block and a single spawn |

Raw rows, run rows and event payloads were captured to private receipts; the portable summaries
above are quoted from them.

## AC7 — control paths on the selected runtime

**8. Explicit cross-Project mismatch refuses before any persistence.** Creating a child with an
explicit different Project and the canary parent as a direct parent was refused with
`project_id '…' does not match parent task '…' project_id '…'`. Tasks, runs and events counts
were taken immediately before and after the attempt and are **identical** — zero rows inserted.

**9. Generic non-Aether scratch collaboration remains constructible.** A task created on a
non-Aether board with an ordinary `scratch` workspace has a null Project, and collaboration
opt-in on it succeeded. The generic path is not closed by the Aether-board hardening.

**10. Bounded deterministic review failure reaches an inspectable state.** A deterministic
failure recorded through the supported failure path with the breaker tripped produced:

- task status `blocked` (inspectable terminal state, no silent disappearance);
- claim ownership cleared (`claim_lock` null) and worker ownership cleared (`worker_pid` null);
- a `gave_up` event present;
- **no `origin_signal` present** — no unverified origin notification was emitted;
- **0 notified subscribers**;
- two subsequent dispatcher ticks spawned nothing and did not re-claim the task — no
  claim/reclaim loop.

## Isolation and preservation witnesses

| Witness | Observed |
| --- | --- |
| Live board count | unchanged (99 boards) |
| Live board task / comment / run totals | unchanged (567 / 1504 / 2300) across the whole canary window |
| Live board write attribution | of the 99 live board databases, **exactly one** was written during the window — this objective's own board — and its only new events belong to this canary card's own control-plane lifecycle (its claim, spawn, promote and heartbeats). Every other live board is untouched by mtime, so its bytes are unchanged. |
| Isolation proof | the canary ran with `HERMES_KANBAN_HOME`, `HERMES_KANBAN_DB` and `HERMES_KANBAN_BOARD` pinned to its own disposable board, with `HERMES_KANBAN_TASK` / `HERMES_KANBAN_RUN_ID` / `HERMES_SESSION_ID` cleared, so no live board was reachable |
| Project registry | unchanged |
| Active release record | unchanged |
| Unrelated services | the unrelated Hestia gateway and the other user services remain active |
| Selected release | still the RC16 release after the canary |
| Canary artifacts | created only under the disposable temp root; nothing committed as product source and no live board mutated |

Note on the live-board evidence: an earlier revision of this file claimed all 99 board hashes
were compared byte-identical before and after. That comparison is **withdrawn as invalid** — the
fingerprint helper wrote its reading to the same path it had read the pre-state from, so the
"post" value was not an independent second measurement. The checks recorded above (stable
structural totals, exact write attribution by mtime across all 99 boards, and the pinned
disposable board routing) are the ones actually observed, and they support the preservation
claim as stated here and no more.

No accidental live mutation was discovered, so no escalation was required.

## Limits

- The canary runs on a **disposable** board with disposable profile homes; it exercises the
  supported creation/resolution/review/failure code paths on the selected runtime, not a live
  production board.
- The review lane in the canary holds a real claim and a real distinct reviewer identity, but the
  reviewer process itself is simulated by the canary's spawn function. The claim/identity
  evidence is therefore about the runtime's lane semantics, not about a second live process.
- This proves #494's behaviour on the selected runtime. It is not a speed, throughput or
  general agent-behaviour measurement.
