# M5 Parallel Coordination Acceptance

## Verdict

`PASS_DETERMINISTIC_M5 / M5.4_BLOCKED_MODEL_WORKER_TIMEOUT`

The deterministic M5 scope is accepted at technical commit
`f356c21a65310d2d8c41112d407658e0a64f945a` and tree
`5bbaba1ce672101f60ed223c3a5d101ca167a913`.

M5.4 was subsequently admitted as one bounded Orca/Codex slice. UC-C05 passed,
but UC-C03 produced no accepted artifacts before the 600-second hard stop and is
`INSUFFICIENT_NOT_ACCEPTED`. See `M5_4_MODEL_ACCEPTANCE.md`. The deterministic
fixture is not reported as a substitute for that gate. This verdict does not
authorize M6, MCP registration, activation, push, merge, release or deployment.

## Accepted deterministic behavior

- two independent Task/Dispatch intents are persisted and accepted before either
  worker is polled;
- static and runtime write-scope conflict guards prevent overlapping writer
  authority;
- two child-worktree fixtures reach a shared bounded barrier before either is
  released;
- nanosecond filesystem evidence proves `ready_latest <= overlap_earliest`;
- peer handoff is rejected before immutable predecessor evidence exists;
- beta emits a technical question and alpha answers its exact provider message
  identity with artifact/evidence digests;
- coordinator integration reads the two still-bound child-worktree artifacts,
  rechecks digests, rejects failed components and writes one atomic artifact in
  coordinator-owned `integration/` scope;
- a separate real Run proves one worker can fail after producing evidence while
  the other remains live, followed by exact Run/Dispatch cancel and aggregate
  cleanup;
- child placements, terminals and worktrees are removed before semantic close;
- neither successful nor cancelled Run leaves processes, displays, mounts or
  temporary roots.

## Real provider qualification

The exact Orca 1.4.167 desktop renderer and public structured CLI executed two
isolated Runs.

### Success Run

1. Run plus `alpha` and `beta` Tasks were created without workers.
2. Two child worktrees, terminals and tracking Dispatches were created.
3. Both Dispatch receipts existed before polling began.
4. Both workers wrote `.ready`; neither wrote `.overlap` until both were ready.
5. Beta published a peer technical question.
6. Alpha completed with independently validated artifact/evidence.
7. Alpha answered beta's exact provider message with a dependency handoff.
8. Beta completed.
9. The coordinator integrated both artifacts and verified its output digest.
10. Aggregate close removed both worker worktrees and all related resources.

### Partial-failure/cancel Run

1. Alpha and beta were dispatched before polling.
2. Alpha produced an artifact and failed with deterministic exit code `22`.
3. Beta independently produced its artifact and remained waiting.
4. The Run was cancelled and beta's exact Dispatch was stopped/fenced.
5. Aggregate close removed both worktrees and reported zero survivors.

Canonical evidence:
`docs/releases/v0.22.0/M5_PARALLEL_EVIDENCE.json`.

## Exact-candidate verification

A detached clean worktree at the accepted commit produced:

- `156 passed` for `tests/aether_mcp`;
- Ruff PASS;
- compileall PASS;
- M5 evidence invariant check PASS;
- clean worktree before and after verification.

The final branch additionally fixes the previously ambient-install-dependent
`make test` target at commit `7e8436aafc056a0a6b3f9476426f8a97ecdc8e2c`.
Commit `1c641a1c297609009aba76c78fbf16325d644389` also stages and hash-verifies
the durable user-local Xvfb inside every M1.3 lifecycle sandbox, removing the
former `/tmp` toolchain dependency. After both corrections, the canonical
complete repository command passed `183/183` tests from the candidate source
tree with no retained temporary Xvfb root.

## Orca debt retained

- Model-free terminals remain tracking Dispatches rather than Orca supervised
  workers because `worker-start --terminal` requires a configured agent.
- Direct shell-to-shell `send --to dispatch:<id>` returns `invalid_argument` for
  tracking Dispatches. The qualified peer flow uses a Run-mailbox technical
  question followed by `orchestration reply` to its exact provider message ID.
- Tracking Dispatches still lack native retry lineage and agent-style
  `worker_done`; M4's explicit Aether lineage plus Task-state composition remains
  necessary.
- Shared-barrier evidence is a qualification-fixture control surface, not a
  proposed production synchronization primitive.
- Coordinator artifact integration is internal/default-off and not an active MCP
  tool.
- The bounded M5.4 slice timed out without artifacts. Model-backed coordination
  remains unavailable pending a new gate with provider-start observability.

## Stop condition

The owner-authorized M3-M5 deterministic sequence remains complete. M5.4 closed
blocked after its one bounded attempt; no retry or later implementation horizon
is entered automatically.
