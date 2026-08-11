# M1.3 Aether MCP Tool Qualification Checkpoint

**Status:** PARTIAL / DEBUGGING IN PROGRESS
**Recorded:** 2026-08-11T00:46:12+00:00
**Candidate branch:** `v0.23.0-orca-production-cutover`
**Candidate HEAD:** `0542cdcc1c6ce967f6b4678b37cb48ac126390ec`
**Active Hermes home:** `/home/darkarty/Desktop/agentes/aether/home`
**Admitted project root:** `/home/darkarty/Desktop/agentes/aether/.aether/worktrees/v0.23.0-orca-production-cutover`

This checkpoint is not M1.3 acceptance. It records the first live qualification and
correction cycle across all 15 operational Aether MCP tools. No model-backed worker,
provider inference, PAYG spend, push, merge, tag, release, deployment, credential
mutation or external publication occurred.

## Contract

The product owner authorized Hermes to use, debug and learn the complete Aether MCP
surface. The bounded first pass used:

- one exact admitted project;
- structured-only learning capture;
- one reversible fixture-first Run;
- no auto-dispatch;
- no model runtime;
- cancellation, semantic close and zero-survivor verification;
- deterministic RED/GREEN correction for defects found at the MCP facade.

The stop boundary for this pass was a closed Run, a clean candidate commit, an
installed rollback artifact and an explicit gate before model-backed execution.

## Exact identities

- `project_id`: `dc55e91f-f0a9-4ed1-b969-c3162c72a256`
- `run_id`: `5d2c1542-bc52-5c5d-84b4-10d0ddc35a25`
- `task_id`: `e7f10ef6-1f48-50ae-925a-c293934b0e48`
- provider Task: `task_e2593c3747c5`
- manifest digest: `9d2798f6498eea6de4b177ac31e8800f09634647713649adf479760d1c982173`
- provider/catalog binding digest:
  `00df83ec1686a56344c78a49d75ff8dec63d988e588642236172180742b23c25`
- Orca runtime observed by the public CLI: `a3035a94-09a4-47d9-a097-dde9ac4a5a3b`

## Fifteen-tool result matrix

| Tool | Live result | Learned contract |
|---|---|---|
| `project_admit` | PASS | Admission is local append-only, exact-root bound and returns one stable `project_id`. |
| `project_inspect` | PASS | Inspection returns the admitted root, aliases, policy and placements without mutation. |
| `swarm_validate` | PASS | Validation freezes the manifest, topological order, model requirement and provider binding. |
| `swarm_start` | PASS | `dispatch_ready=false` starts one Run and provider Task without a worker. |
| `swarm_status` | PASS | Baseline was `OPEN/ready`; final state is `CLOSED/terminal` with no live resources. |
| `swarm_dispatch` | TYPED DENIAL | The active binding has no fixture runtime; dispatch failed pre-effect with `CAPABILITY_UNAVAILABLE`. |
| `swarm_message` | DEFECT FOUND | JSON-shaped string payloads were coerced to objects by FastMCP, producing `INVALID_INPUT`. Corrected at `0542cdc`. |
| `swarm_reconcile` | TYPED DENIAL | The current implementation reconciles only `swarm_start` operations, not Tasks or Dispatches. |
| `swarm_retry` | TYPED DENIAL | Retry rejected an identity that never became an admitted Dispatch with `PRINCIPAL_UNAUTHORIZED`. |
| `swarm_cancel` | PASS | Run cancellation completed and returned the provider Task as the cancelled resource. |
| `swarm_close` | PASS | Semantic close returned `CLOSED`, `replayed=false`, `survivors=[]`. |
| `swarm_trace` | PASS / LIMITED | Decision and evidence append/query work. Query modes expose semantic events, not the technical operation journal. |
| `orca_search` | PASS | Search is term-sensitive; the minimal query `status` returned the public `status` command. |
| `orca_describe` | PASS | Description requires the exact catalog digest and returns the frozen public command schema. |
| `orca_call` | PASS / PLAN-ONLY | The current contract validates and plans read-only `argv`; it does not execute the command or return readiness output. |

Every endpoint was invoked. A typed denial counts as endpoint/guard qualification, not
as a functional worker-path PASS.

## Defect: JSON-shaped MCP strings were coerced

### Live failure

A valid `swarm_message` request carried `payload="{}"`. The active MCP process
returned:

- `ok=false`;
- `outcome=REJECTED`;
- `error.code=INVALID_INPUT`;
- `operation_id=null`.

The protocol validator accepted the same request when invoked directly.

### Root cause

`src/aether_mcp/server.py` dynamically annotated every FastMCP argument as
`object`. Pydantic therefore parsed a JSON-shaped string into a Python object before
`OperationalRuntime.invoke()` received it. The published versioned schema still said
`payload` was a string, so the facade and protocol disagreed.

### RED

`test_facade_preserves_json_shaped_string_arguments` exercised the real FastMCP tool
manager and observed:

```text
expected: '{"thread_id":"thread-1","answer":"approved"}'
actual:   {'thread_id': 'thread-1', 'answer': 'approved'}
```

The focused test failed before production correction.

### GREEN

The facade now derives top-level Python annotations for versioned string properties and
applies them to both `__annotations__` and the synthetic `__signature__`. Nested
contracts remain validated by the canonical protocol schema.

Verification for candidate `0542cdc`:

- `tests/aether_mcp`: **206 passed**, one pre-existing Pydantic warning;
- Ruff on changed source/tests: PASS;
- compileall on changed source/tests: PASS;
- `git diff --check`: PASS;
- commit: `0542cdcc1c6ce967f6b4678b37cb48ac126390ec` —
  `fix: preserve MCP string arguments`.

## Installed correction and rollback

The exact candidate wheel was installed into:

`/home/darkarty/Desktop/agentes/aether/home/.aether-mcp/venv`

Private rollback artifacts:

- fixed wheel:
  `/home/darkarty/Desktop/agentes/aether/home/.aether-mcp/backups/tool-debug-20260810/fixed/aether_mcp-0.23.0.dev0-py3-none-any.whl`
  - SHA-256: `450ad340f80a02d3e7d1c0994facc8baf334d8dc7dbdab0af9d86a9de99d19db`
- rollback wheel from `73f98f3`:
  `/home/darkarty/Desktop/agentes/aether/home/.aether-mcp/backups/tool-debug-20260810/rollback/aether_mcp-0.23.0.dev0-py3-none-any.whl`
  - SHA-256: `fcdea9641ffbf4d64b1ba6b37f29e31d30d280dfe6aa27c6ae1c81806150ce1f`

The backup root and subdirectories are mode `0700`; both wheel files are mode `0600`.
Rollback is a `uv pip install --reinstall --no-deps` of the preserved rollback wheel,
followed by session convergence verification.

Fresh-process evidence after installing the fix:

- `hermes mcp test aether_mcp`: connected in 885 ms;
- exactly 15 tools discovered;
- installed-package FastMCP probe preserved `payload` as the literal string `"{}"`;
- package source resolved from the active installation venv.

### Loaded-process distinction

The current Hermes session started Aether MCP before the fixed wheel was installed.
Its existing MCP child remains loaded with the old facade and still reproduces
`INVALID_INPUT`. A fresh independent MCP process uses the corrected facade. Therefore:

- code on disk: **corrected**;
- fresh-process handshake: **PASS, 15 tools**;
- current running-session convergence: **pending one Hermes session restart**.

This distinction must not be collapsed into either “not installed” or “already active in
this process.”

## Trace evidence

The Run contains two semantic records:

1. sequence 1, `DECISION`, route `fixture-first`;
2. sequence 2, `EVIDENCE`, outcome `PARTIAL`.

Both were queried successfully by `run_id`. Empty `timeline`/`operations` queries before
these records were expected from the current implementation because `swarm_trace`
queries `semantic_events`; it does not project the separate technical `events` journal.

## Cleanup

Final Aether MCP status:

- provider Run: `terminal`;
- semantic state: `CLOSED`;
- Task: `failed` after bounded cancellation;
- `live_resource_ids=[]`;
- close receipt: `survivors=[]`.

Public `worktree ps` showed:

- zero agents on the candidate worktree;
- zero child worktrees;
- one existing coordinator terminal on the candidate worktree;
- one existing coordinator terminal on the main Aether worktree.

Those two coordinator terminals predated and outlived the Run and are not claimed as
Run-owned resources.

## Remaining qualification gates

M1.3 remains open because the fixture runtime is intentionally not composed into the
active production binding. A functional PASS for `swarm_dispatch`, `swarm_message` and
`swarm_retry` requires one successful model-backed Dispatch.

Before that live gate:

1. restart Hermes so this session loads candidate `0542cdc`;
2. retry the original JSON payload through `swarm_message` and require a typed routing
   result with the preserved `operation_id`, not facade `INVALID_INPUT`;
3. freeze provider, account/profile, model, worker count, retry count, timeout and spend;
4. execute one low-risk child-worktree Task;
5. require real provider-correlated message, artifact verification, semantic close and
   zero survivors;
6. exercise retry only through an induced, bounded, safely recoverable attempt outcome.

No claim in this checkpoint authorizes M1.4, roster dogfooding, publication or runtime
deployment beyond the installed facade correction described above.
