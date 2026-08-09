# M5 Parallel Coordination Acceptance

## Verdict

`PASS_DETERMINISTIC_M5 / M5.4_UNKNOWN_NOT_AUTHORIZED`

The deterministic M5 scope is accepted at technical commit
`f356c21a65310d2d8c41112d407658e0a64f945a` and tree
`5bbaba1ce672101f60ed223c3a5d101ca167a913`.

M5.4 remains `UNKNOWN_NOT_AUTHORIZED`: no model provider, account, credentials,
budget or explicit stop limits were admitted. The deterministic fixture is not
reported as a substitute for that gate. This bounded verdict closes the currently
authorized M5 work and does not authorize M6, MCP registration, activation,
push, merge, release or deployment.

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
After the correction, the canonical complete repository command passed
`183/183` tests from the candidate source tree.

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
- M5.4 cannot be evaluated without a separately authorized model-backed provider
  slice, bounded account, budget and stop limits.

## Stop condition

The owner-authorized M3-M5 deterministic sequence is complete. The next material
gate is an owner decision on M5.4 model-backed admission or an explicit decision
to retain `UNKNOWN` and proceed later. No further implementation horizon is
entered automatically.
