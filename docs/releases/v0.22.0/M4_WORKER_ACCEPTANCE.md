# M4 One-Worker Acceptance

## Verdict

`PASS_DEFAULT_OFF_M5_DETERMINISTIC_GATE_OPEN`

M4 is accepted at technical commit
`037b9ccf8698ab59c73275f3b4fb8d98a5e434af` and tree
`ae52db382e26adacced379154ff816c9e2aeaa97`.

This gate permits the owner-authorized deterministic two-worker M5 slice. It
does not authorize M5.4 model-backed execution, credentials, spending, MCP
registration, activation, M6, push, merge or release.

## Accepted behavior

- deterministic no-model fixture with success, question, failure-before,
  failure-after, cancellation and two-worker barrier modes;
- exact Dispatch/Task/terminal/worktree correlation;
- intent-before-effect journaling and exact replay;
- sender, recipient, thread and reply correlation;
- encrypted redaction-before-write capture for admitted `FULL_EPISODE` Runs;
- artifact path, placement, write-scope and digest validation before provider
  completion;
- immutable retry lineage with a new Dispatch/generation and fenced prior
  authority;
- late-message rejection after fencing;
- aggregate worker terminal/worktree cleanup before semantic Run close;
- immutable episode sealing only after semantic close and authenticated replay.

## Real provider qualification

The exact Orca 1.4.167 desktop renderer and public structured CLI executed:

1. a first child-worktree fixture attempt that wrote an artifact and failed with
   the expected exit code;
2. a new retry Dispatch/generation in a distinct child worktree;
3. a blocking technical question;
4. renderer restart, replacement coordinator terminal and Run rebind;
5. a provider-correlated reply;
6. independently validated successful output;
7. aggregate terminal/worktree cleanup and semantic close;
8. encrypted episode seal and six-item replay;
9. a second real Run cancelled while its worker was active, followed by exact
   Dispatch cancel, Run cancel and zero-survivor close.

Canonical evidence:
`docs/releases/v0.22.0/M4_WORKER_EVIDENCE.json`.

No external model, account, credential, secret or budget was used. The protected
content key existed only in the isolated test process and was not persisted.

## Exact-candidate verification

A detached clean worktree at the accepted commit produced:

- `153 passed` for `tests/aether_mcp`;
- Ruff PASS;
- compileall PASS;
- evidence invariant check PASS;
- clean worktree before and after verification.

## Orca debt retained

- `worker-start --terminal` rejects a bare deterministic shell as
  `agent_unconfigured`; it cannot supervise this fixture without pretending to
  be a supported model agent.
- Public tracking `dispatch --to` accepts the fixture terminal but has no
  `retry-of` flag. Aether records immutable retry lineage while Orca receives a
  new public Dispatch after an explicit Task readiness transition.
- `worker_done` rejects the tracking shell Dispatch. Aether preserves the
  completion message/content and composes public `task-update completed|failed`
  for Orca's Task state.
- `terminal list` followed by per-tab close can race to `tab_not_found` across
  renderer generations. Cleanup uses the scoped idempotent
  `terminal stop --worktree` primitive.
- Coordinator replies require the dedicated public `orchestration reply`
  command rather than `send --type guidance`.
- Child worktrees must be admitted as temporary placements and removed from
  admission before provider deletion.

These are compatibility debts, not hidden shims or claims that Orca natively
supports a model-free supervised worker.

## Gate

At the M4 boundary, M5 could begin with two independent deterministic fixture
workers, proved overlap, bounded peer handoff, partial failure/cancel and zero
survivors. M5.4 was then `UNKNOWN / NOT AUTHORIZED` pending a separate owner
decision on provider, accounts, models, budget and stop limits; that later gate is
now resolved in `M5_4_MODEL_ACCEPTANCE.md`.
