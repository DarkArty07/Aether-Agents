# ACP Runtime Boundary Audit for Kernel Convergence

**Status:** VERIFIED PLANNING INPUT — 2026-07-23

**Scope:** `src/olympus_v3/acp_manager.py`, `src/olympus_v3/coordination/olympus_adapter.py`, server call sites, and lifecycle tests. No runtime was started and no code was modified for this audit.

## Verdict

ACPManager is suitable to remain the exclusive lifecycle owner, but the kernel needs a durable adapter contract around it. ACPManager does not know run, task, attempt, lease, fence, plan revision, artifact generation, or semantic completion.

## Lifecycle map

| Boundary | Existing producer | Verified behavior | Kernel implication |
|---|---|---|---|
| Logical session ID | caller or UUID in `spawn_agent()` | globally reserved in manager event loop | kernel supplies deterministic ID bound to attempt |
| ACP session ID | `connection.new_session()` | stored separately from logical ID | persist both identities in session binding |
| Process ownership | ACPManager `AgentState` | keyed by `(agent_name, canonical project_root)` | kernel never spawns/kills directly |
| Dispatch acceptance | `send_message()` | returns `sent` after scheduling background prompt | delivery ACK only, never completion |
| Terminal transport status | ACP prompt `stop_reason` | maps end_turn/cancelled/other to completed/cancelled/error | semantic result still requires persisted structured evidence |
| Progress | `poll()` | SQLite plugin data plus newer in-memory status | adapter must snapshot and persist observed data |
| Cancel/close | `close()` / `cancel()` | cancels active ACP prompt and closes raw session | kernel emits cancellation intent; Olympus performs it |
| Teardown | async context manager disposal | bounded helpers exist; R8 observed `athrow()` re-entry warning | exact-once teardown remains a separate infrastructure blocker |
| Tool children | not modeled | ACPManager owns direct ACP process only | long-lived children need explicit registration/cleanup evidence |

## Verified call sites

- General adapter: `olympus_adapter.py:196-306` accepts caller-supplied `HarmoniaPlan`, calls `spawn_agent()` and `send_message()`, and deduplicates in memory.
- R8 adapter: `olympus_adapter.py:341-477` uses the special pilot envelope path.
- Public MCP actions: `server.py:305-345` call open/message/poll; delegate paths call the same public ACPManager methods.
- ACPManager opens a session atomically under an agent/project lifecycle lock: `acp_manager.py:402-536`.
- ACPManager schedules the prompt and immediately returns `sent`: `acp_manager.py:721-833`.
- ACPManager polls persisted plugin data and overlays terminal in-memory state: `acp_manager.py:839-863`.
- ACPManager cancel/close behavior: `acp_manager.py:869-949`.

## Identity available today

ACPManager can correlate:

- logical Olympus session ID;
- raw ACP session ID;
- agent profile;
- canonical project root;
- direct ACP process PID;
- prompt task in memory.

It cannot natively correlate:

- kernel run ID;
- task ID;
- attempt ID;
- contract generation;
- plan revision;
- lease owner/epoch/fence;
- base/result artifact generation;
- effect ID;
- evidence/gate/closure identity.

The kernel must persist that mapping; ACPManager must not absorb semantic ownership.

## Dispatch semantics

`send_message()` returns `{"status": "sent"}` after a background task is created. This proves only that ACPManager accepted the prompt request. It does not prove the ACP server consumed it, the agent began work, an effect occurred, or a terminal response exists.

Required kernel states:

```text
DELIVERY: STAGED -> CLAIMED -> ACCEPTED | FAILED
EXECUTION: NOT_STARTED -> RUNNING -> SUCCEEDED | FAILED | CANCELLED | UNKNOWN
SEMANTIC: PENDING -> VERIFIED -> REVIEWED -> ACCEPTED | REJECTED | BLOCKED
```

## Timeout and uncertain result

ACPManager's convenience delegate polls until terminal or timeout, but the kernel-backed dispatcher must not map timeout to retry. If delivery was accepted and terminal evidence is absent, execution becomes `UNKNOWN`; retry remains blocked until reconciliation checks Olympus, persisted turns, filesystem/Git snapshots, and attributable processes.

## Cancellation and stale fences

ACPManager can cancel an identified logical session. It does not watch kernel leases. The dispatcher/reconciler must:

1. detect expired or superseded attempt ownership;
2. persist cancellation intent;
3. call `ACPManager.cancel(session_id)`;
4. persist the returned lifecycle observation;
5. reject every late result carrying the old fence;
6. classify any possibly executed side effect as uncertain.

## Teardown and cleanup limits

`close()` catches and logs raw ACP `close_session()` failures and continues local cleanup. Therefore a returned closed/cancelled status alone is not proof that the raw ACP session closed successfully. The closure runtime needs cleanup receipts and a postcondition check.

The R8 warning:

```text
RuntimeError: athrow(): asynchronous generator is already running
```

remains a separate ACP framework defect. It must be covered before claiming exact-once teardown, but kernel convergence must not move context-manager ownership out of ACPManager.

ACPManager does not observe arbitrary long-lived children started by tools. For the local pilot, require explicit managed-child registration when a tool starts a server, plus listener/process postchecks. Full process-tree isolation is deferred.

## Existing lifecycle tests

Covered today in `tests/test_acp_manager_lifecycle.py`:

- same-key concurrent spawn serialization;
- independent project roots;
- dead receive-loop rejection;
- new-session timeout cleanup;
- duplicate logical session reservation;
- prompt overlap prevention;
- close cancels active prompt without manufacturing success;
- transport failure invalidation;
- registration rollback;
- cancellation-safe disposal;
- PID mapping isolation.

## Required integration RED tests

These belong to new kernel composition tests rather than ACPManager unit tests unless an ACP defect is isolated:

1. dispatch ACK cannot complete a task;
2. task-attempt-session binding persists both logical and ACP identities;
3. lease expiry produces cancellation intent and stale-result rejection;
4. accepted dispatch followed by missing terminal response becomes `UNKNOWN`;
5. close failure yields cleanup failure, not operational `CLOSED`;
6. late completed session after supersession cannot mutate task state;
7. managed child/listener surviving cleanup yields `CLOSE_FAILED`;
8. historical ACP status cannot override a newer fenced attempt.

## Integration contract

The future bridge may call only public ACPManager operations:

```text
spawn_agent
send_message
poll
close
cancel
```

It must not read or mutate `agents`, `sessions`, `prompt_tasks`, subprocess handles, connections, or private SQLite tables. Olympus continues to own all lifecycle mechanics.
