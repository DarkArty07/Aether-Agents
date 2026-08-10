# M3 Lifecycle Acceptance

## Verdict

`PASS_DEFAULT_OFF_M4_GATE_OPEN`

M3 is accepted at technical commit
`7e3f1049ee78ec12fe29e8b4326f34000e1f95e1` and tree
`623b7a530358ff67ef1950839119cfa78a729978`.

This acceptance permits the already owner-authorized M4 deterministic fixture
worker. It does not register or activate Aether MCP, admit a real model-backed
worker, enable credentials or spending, or authorize M6.

## Accepted behavior

- immutable validated manifest registration and exact generation lookup;
- intent-before-effect journaling for lifecycle mutations;
- deterministic logical Run and Task identities correlated to Orca identities;
- exact idempotent replay and conflict rejection;
- partial/timeout preservation as `UNKNOWN` without blind retry;
- compare-and-set reconciliation under concurrent observers;
- source-labelled status projected from Orca rather than mirrored locally;
- restart-safe correlation and coordinator replacement through public
  `orchestration run-use`;
- bounded Run/Task cancellation and evidence-bound semantic close;
- explicit terminal inventory and zero-survivor cleanup.

## Real provider qualification

The exact Orca 1.4.167 AppImage was exercised through the admitted
`desktop-renderer+public-cli` binding in a fresh HOME, HERMES_HOME, XDG state,
Git repository, X display and Aether state root.

The probe created one Run and two dependency-ordered Tasks with zero workers,
stopped and restarted the renderer, created a replacement coordinator terminal,
rebound the persisted Run, recovered exact Aether correlations, cancelled both
Tasks, closed the Run semantically, closed both Orca terminals, reset only the
isolated orchestration profile and proved zero process, display, mount and root
survivors.

Canonical evidence:
`docs/releases/v0.22.0/M3_LIFECYCLE_EVIDENCE.json`.

## Exact-candidate verification

A detached clean worktree at the accepted commit produced:

- `141 passed` for `tests/aether_mcp`;
- Ruff PASS for M3 source, tests and qualifier;
- compileall PASS;
- evidence invariant check PASS;
- clean worktree before and after verification.

The real M3 qualification itself passed separately before the technical commit.
No worker, model, credential, secret or budget was used.

## Orca debt retained

M3 does not claim Headless compatibility. The following Orca debts remain open
and are tracked in `M3_M5_EXECUTION_LOG.md`:

- no public Headless coordinator-terminal admission primitive;
- status readiness can exceed a bounded client budget;
- coordinator terminal handles change across renderer restart;
- complete cleanup requires explicit terminal and process inventory;
- the AppImage extract-and-run cache can fail cleanup; the qualified harness
  prepares one exact AppDir instead;
- the renderer may leave reparented daemon or shell processes unless terminals
  and root-correlated descendants are closed explicitly.

## Gate

M4 may begin only with the deterministic no-model fixture worker. MCP remains
unregistered, default-off and zero-tool. M5 remains conditional on M4 closure.
