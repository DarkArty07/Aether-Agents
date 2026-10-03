# External Implementer harness: Claude Code by explicit contract request

**Decision authority:** project owner

**Accepted:** 2026-09-30 UTC (decisions recorded 2026-09-28 to 2026-09-30 in the owner's
conversation with Morfeo)

**Status:** implemented and integrated through the owner-directed completion (OD-11,
2026-10-03); the release and local update belong to the separate RC19 record (adopted through an RC18 bridge)

**Design steward:** Morfeo

**Objective issue:** [#563](https://github.com/DarkArty07/Aether-Agents/issues/563)

## 1. Owner decision

Aether is the owner's set of protocols, rules and way of developing. The owner wants other
agent harnesses to be able to act as the Implementer so that Aether can use each harness's
quotas, offers and particularities. The first harness is Claude Code, the most used one.
Hermes remains Aether's infrastructure and the default executor for every role: this is a
multiharness execution seam on top of Hermes, not independence from Hermes.

Accepted owner decisions:

- **OD-1 — Selection per contract; Hermes by default.** The owner requests another
  Implementer harness when a contract is started. Without that explicit request every role
  runs on Hermes, and Morfeo neither proposes, asks about nor selects another harness. The
  rule belongs in Morfeo's canonical instructions, not only in memory.
- **OD-2 — No permission prompts.** Every external harness runs without permission prompts
  of any kind; for Claude Code that is `--permission-mode bypassPermissions`, matching the
  Hermes Implementer's `approvals.mode: "off"` and local protection by worktree, Git, tests
  and review. The adapter enables and verifies that mode on every run instead of relying
  on the user's settings. The PD-71 edge guard is not a prompt: it remains a deterministic
  blocking pre-tool check. A harness is eligible only if it offers a blocking pre-tool hook
  and a no-prompt mode the adapter can enable and verify per run.
- **OD-3 — Simple per-card fallback.** If Claude Code cannot work a card (no quota or another
  technical failure) that attempt continues on Hermes; every other card decides on its own.
  There is no global state, circuit breaker or failure memory: each attempt tries Claude
  first. Contracts last hours and Claude's quota window renews, so later cards return to
  Claude naturally.
- **OD-4 — Aether exposes only minimum requirements.** Each harness's own configuration
  (plugins, own MCP servers, model, effort) is the user's decision. Aether neither manages,
  isolates nor curates it; it adds only what the role needs for that run.
- **OD-5 — Harnesses adapt to Aether.** Role identity and canonical skills reach every
  harness from their single canonical source; adding a skill to the Implementer must reach
  every harness without changing Aether per harness.
- **OD-6 — Goal-mode excluded.** Cards in goal-mode stay on Hermes. Removing goal-mode from
  Aether would be a separate objective because it changes R7 FR-729.
- **OD-7 — Minimal verification.** No comparisons or exhaustive testing. Real calls are
  permitted; if it works, that is enough and ordinary use informs the rest.
- **OD-8 — Implementation only.** The owner authorizes implementing this functionality —
  the explicit bounded-objective exception to the PD-74 feature freeze — but not a release,
  managed update, installed activation or tag.
- **OD-9 — Gateway delivery.** The worker-launcher override reaches the dispatching gateway
  through an Aether plugin that gateway already loads, not through a systemd drop-in
  (excluded by A1's #487 reconciliation) nor the profile's credential `.env`.
- **OD-10 — Design amendment.** The owner approved the PD-40 amendment: an external harness
  may execute Implementer work when the owner requests it for the contract; it receives and
  delivers work through the Kanban board like any Implementer, and its MCP connection to
  the board does not replace the board.
- **OD-11 — Owner-directed completion (2026-10-03).** After the consumed isolated run
  ended in a `needs_input` stop, the owner instructed direct completion of this objective,
  its integration into `main`, the next release candidate and the local update, granting
  the effects that requires («Necesito que ya termines ese trabajo lo lleves a main, y
  pases al siguente rc. Actulices lo local. Tienes todo permitido»). This authorizes the
  replacement isolated real run and supersedes OD-8 only for the separate RC19 release
  record (adopted through an RC18 bridge) that carries the release and local update.

Delegated Morfeo decisions, with their assumptions in [`plan.md`](plan.md): every review
attempt — including an independent review assigned to the Implementer profile — stays on
Hermes; one Objective Contract carries the whole increment because the stateless fallback
is small and the quota motivation needs it; per-card Hermes model/effort pins keep that
card on Hermes rather than being silently dropped.

## 2. Boundaries

**Transport.** The board remains the only inter-role transport ([`DESIGN.md`](../../DESIGN.md)
PD-40 as amended; [R6](../r6-protocol-and-communication/spec.md) FR-602, FR-609, FR-611b).

**Out of scope.** External Supervisor or Morfeo; harnesses other than Claude Code (only the
adapter seam is prepared); automatic quota-based harness selection; goal-mode on an
external harness; managing, isolating or curating the user's harness configuration; Aether
Router changes; modifying the Claude Code binary; Aether reading, copying, storing or
brokering Claude credentials or tokens; `--bare`; Hermes fork, source or pin changes;
release, managed update, installed activation, tag or publication; comparisons, benchmarks
and agent-behavior campaigns.

**Preserve.** The default Hermes path byte-for-byte; Supervisor flow session and affinity
(R7 FR-714a–e); native Kanban claims, worktrees, review and closeout; counters, budgets and
convergence bounds (R7 FR-736e, FR-738a); PD-71; existing contracts, boards, releases and
private state.

## 3. Required end state

- **EIH-01 — Default unchanged.** Without a selection, authored contract bytes and execution
  board metadata are identical to today's, and every attempt still reaches the Hermes entry
  point the dispatcher would have resolved, with exactly the argv tail and environment it
  built. The only additions are the launcher hop and its managed override variable.
- **EIH-02 — Structured selection.** Morfeo records the owner's request as an optional
  closed-set selection when beginning or superseding a contract. It is validated (an
  unknown value is rejected, never treated as absent), rendered in the final contract only
  when set, projected unchanged to the execution board when that board is created, and
  compared when the board is reused. Prose is never interpreted as a selection. Readers
  that predate this feature ignore the selection and run everything on Hermes.
- **EIH-03 — Worker launcher.** The Morfeo-profile Aether plugin points the dispatcher's
  documented `HERMES_BIN` override at its own release's worker launcher when that launcher
  is valid. The launcher routes an attempt to Claude Code only when every eligibility
  condition holds; otherwise, and on any launcher error, it executes the Hermes entry point
  the dispatcher would have resolved without the override, with identical argv and
  environment.
- **EIH-04 — Claude Code adapter.** Eligible attempts run the official, unmodified `claude`
  binary in the attempt's Kanban workspace with the user's normal configuration and
  session, headless with structured output, no-prompt mode explicitly enabled and verified,
  Aether's context, skills, worker MCP server and PD-71 hook added on top of the user's
  configuration, and a new harness session per attempt.
- **EIH-05 — Role context and skills.** Claude receives the Implementer SOUL,
  `implementation-evidence`, the running runtime's Kanban worker guidance, the task's
  durable worker context, task-pinned skills and a tool-name equivalence table. The
  Implementer's canonical skill set is mounted read-only for that run only, without writing
  into the project repository or the user's personal skill directories.
- **EIH-06 — Worker MCP surface.** A per-attempt stdio MCP server exposes the Kanban worker
  tools that Hermes grants a dispatched Implementer attempt, plus the role's
  project-knowledge and work-memory tools, bound to that attempt's identity and delegating
  to the native tools. It forwards only supplied arguments and exposes no bootstrap
  payload, Morfeo identity or unrelated tools.
- **EIH-07 — PD-71 on Claude.** Every Claude tool call passes through a blocking pre-tool
  command hook that translates Claude's event and tool names and applies the unchanged
  Aether policy. The adapter fails closed: malformed input, internal error or timeout
  blocks the call.
- **EIH-08 — Readiness and a single writer.** The work prompt reaches the model only after
  positive evidence that the worker MCP server is connected with its required tools, that
  bypass mode is active and that the PD-71 hook is active. Claude runs in its own process
  group tied to the launcher; termination is propagated; no fallback or successor starts
  while any process of that attempt may still write to the worktree. Heartbeats derive from
  real stream activity, never from a blind timer.
- **EIH-09 — Delivery and receipts.** Only native Kanban transitions count as results. Each
  Claude attempt leaves a bounded executor receipt (harness, version, session id, outcome,
  cause) in Aether local state and a structured Kanban comment. A Claude session is never
  recorded as a Hermes session.
- **EIH-10 — Stateless fallback.** A missing binary, authentication failure,
  quota/billing/rate limit, abnormal termination without delivery, MCP not ready, hook not
  active or bypass not active makes that attempt continue on Hermes inside the same claim,
  process identity and remaining deadline. Red tests, review returns, cancellation, PD-71
  denials, exhausted budgets and a clean exit without delivery never trigger fallback.
- **EIH-11 — Guidance and documentation.** Morfeo's SOUL and `objective-contract-design`
  state OD-1. The expected-behavior guide, user documentation, capabilities registry and
  changelog describe the opt-in, the minimum requirements, fallback and limits.
- **EIH-12 — Verified closeout without activation.** Normal project checks for touched
  boundaries, and one isolated real run in which an Implementer card executed by Claude
  Code reaches review through the real Kanban tools. Normal reviewed source closeout; no
  release or activation.

## 4. Acceptance

Acceptance uses EIH-01 through EIH-12, the decisions and interfaces in [`plan.md`](plan.md),
the runnable checks in [`quickstart.md`](quickstart.md) and the finalized Objective
Contract. Each result records exact revision, command or check, producer, outcome and
limits in this objective's `evidence/` location.

A Supervisor review of a Claude-executed card on the installed runtime and `aether doctor`
after a managed update belong to a later owner-authorized release (OD-8); they are not
acceptance criteria of this objective's contract. Source integration must never be
reported as installed availability.
