# Aether–Orca Supervised Sessions Design

> **Status:** SUPERSEDED RESEARCHED DESIGN; NOT IMPLEMENTED OR ACTIVATED
> **Date:** 2026-08-04
> **Decision authority:** Superseded by PDR-0012
> **Pinned Orca AppImage:** `sha256:813b11e99f7caa4bf8e4fc47200dd6c465f34a04d61e855adbd8822190592e33`

> **Supersession:** The installed-capability findings and Hermes-led parallel
> outcome remain useful evidence. PDR-0012 rejects the proposed stable Aether
> session service, private adapter ledger, and pre-emptive product API. A future
> integration must begin from Orca's public Run/Task/Dispatch/message/worktree
> contract and add only the smallest observed Aether-specific seam.

## 1. Product outcome

Aether should let its primary Hermes session start several bounded worker sessions concurrently, place every worker in its own Orca-managed Git worktree, observe and steer them without blocking the primary conversation, and accept their work only after Aether-owned verification.

The intended topology is:

```text
User
  |
  v
Aether Hermes (one accountable supervisor)
  |
  +-- Aether execution contracts, participant policy, budgets and acceptance
  |
  v
Aether session service (stable product API)
  |
  v
Aether-Orca adapter (replaceable JSON client)
  |
  +-- Orca Run
      +-- Task A -> Dispatch A -> Hermes worker -> Worktree A
      +-- Task B -> Dispatch B -> Hermes worker -> Worktree B
      +-- Task C -> Dispatch C -> Hermes worker -> Worktree C
```

This is not a topology of several peer Hermes coordinators. Only the primary Hermes session decomposes work, authorizes participants, changes contracts, resolves material decisions, verifies results, and proposes semantic closure. Worker sessions cannot delegate recursively.

## 2. What Orca CLI is

The installed Orca CLI is a JSON-capable control surface for the Orca desktop/headless runtime. It manages:

- registered repositories and project host setups;
- Git worktrees and their parent/top-level lineage;
- persistent terminal sessions and bounded terminal reads;
- orchestration Runs, Tasks and Dispatch attempts;
- supervised worker startup, inspection, messaging, retry, stop and abandonment;
- durable coordinator mail, questions, replies, escalations and acknowledgements;
- local or explicitly connected remote execution environments;
- recovery metadata, created/reused effects and residual resources.

The key operational identities are:

- **Run:** durable namespace and coordinator inbox;
- **Task:** operational work item and dependency node;
- **Dispatch:** one attempt of one Task assigned to one worker terminal;
- **terminal handle:** routing metadata for the live PTY;
- **worktree ID:** routing and filesystem-placement metadata.

None of these identities establishes Aether product completion or protected-effect authority.

## 3. Verified installed capabilities

The following findings come from the installed AppImage and its version-matched bundled guides, not from a hypothetical Orca API.

### 3.1 Native Hermes support exists

The installed catalog includes `hermes` as a first-class TUI agent. Its configuration is:

```text
detect command: hermes
launch command: hermes --tui
expected process: hermes
prompt mode: hermes-query
```

For a startup task, Orca constructs a bounded `hermes chat --query=... --tui` invocation. The query is transported through `ORCA_HERMES_STARTUP_QUERY`, removed from the long-lived child environment before Hermes executes, and limited to a 24,000-byte command/environment envelope.

This means Aether does not need a fake Codex/Claude wrapper to host Hermes.

### 3.2 Supervised parallel dispatch exists

The public orchestration contract supports:

```text
run-create
  -> task-create A
  -> task-create B
  -> worker-start A
  -> worker-start B
  -> check / worker-show / worker-read
```

All independent Tasks can be created and started before any wait. Orca does not choose participants, schedule work, infer write conflicts, or enforce Aether concurrency budgets; the Aether adapter must do so.

### 3.3 One worktree per worker is supported

`worker-start` supports `new-child` and `new-top-level` placement. The low-level path also supports `worktree create`, `terminal create`, and tracked `dispatch --inject` for custom launch commands.

Aether requires the low-level path initially because the installed `worker-start` command accepts an agent ID but no per-dispatch `HERMES_HOME` or agent environment.

### 3.4 Hermes lifecycle observation exists, with a privacy caveat

Orca can install an `orca-status` Hermes plugin. It reports lifecycle and tool events to an authenticated local `127.0.0.1` endpoint and recognizes Hermes states such as working, waiting and done.

The current machine reports the plugin installed for the primary Aether home:

```text
/home/darkarty/Desktop/agentes/aether/home/config.yaml
```

It is not installed in the individual Aether profile homes. More importantly, its current payload selection may include bounded tool arguments, tool results, prompts, and assistant responses. Bounded size is not equivalent to redaction. Live Aether adoption must not copy potentially sensitive payloads into Orca merely for status presentation.

Therefore:

- the credential-free synthetic pilot may evaluate the managed hook;
- live profiles require an explicit privacy acceptance or a public privacy-safe Orca mode;
- explicit Dispatch lifecycle reports remain the authoritative completion path;
- Aether must not depend on undocumented Orca hook internals or fork the plugin as the initial solution.

### 3.5 Hermes cold resume is not yet native in Orca

The installed Orca source does not extract a Hermes provider session or build a Hermes resume argv. It can preserve/recover an already-live PTY and orchestration assignment, but automatic cold reconstruction of a terminated Hermes conversation is not established.

Aether must initially recover from durable Aether contracts, Orca Dispatch state, Git/worktree state and evidence. It must not claim conversational resume parity until a public, tested Hermes resume seam exists.

### 3.6 Transcript fidelity is limited

`worker-read` can return exact hook-reported transcripts for a bounded set of agents. Hermes is not currently one of the explicitly guaranteed exact transcript sources; it may fall back to bounded terminal output.

Aether acceptance must use structured worker evidence and repository verification, never terminal transcript prose alone.

### 3.7 Current runtime blocker

The current local CLI reports:

```text
app.running: false
runtime.state: stale_bootstrap
runtime.reachable: false
graph.state: not_running
```

GitHub issue `#150` remains the immediate runtime blocker. No Aether Dispatch may be activated until an isolated runtime starts and recovers deterministically.

## 4. Aether-owned product API

Hermes should use a substrate-neutral Aether tool surface. Orca command names and IDs remain adapter details.

### Coordinator-only operations

#### `aether_sessions_start`

Input:

- admitted Aether execution contract;
- objective;
- one or more immutable Task contracts;
- approved worker profile for each Task;
- child or top-level worktree placement;
- concurrency, time, retry and model budgets;
- evidence and cleanup requirements.

Behavior:

1. validate identity, authority, participant and budget;
2. create one Orca Run;
3. create all ready independent Tasks;
4. create one worktree and Hermes terminal per Task;
5. attach one Dispatch per Task;
6. return after Dispatch acceptance, without waiting for completion.

Output:

- Aether run ID;
- per-Task Aether session ID;
- technical start state;
- worktree/Dispatch routing references;
- created/reused effects;
- residual resources and uncertainty.

#### `aether_sessions_status`

A non-blocking read by default. It reads the oldest available Run Delivery, Task/Dispatch state and bounded worker status, then returns immediately.

It must distinguish:

- accepted for dispatch;
- starting;
- running or apparently live;
- waiting for a coordinator answer;
- worker-reported success/failure;
- stopped;
- outcome unknown;
- evidence pending;
- review pending;
- semantically accepted;
- cleanup pending or closed.

A timeout or no new message is not worker failure.

#### `aether_sessions_message`

Sends attempt-scoped guidance to `dispatch:<id>`. It rejects stale generations, superseded attempts and unauthorized scope changes.

#### `aether_sessions_read`

Returns bounded output with a cursor, source and fallback reason. It is diagnostic evidence, not semantic acceptance.

#### `aether_sessions_cancel`

Records an Aether cancellation decision, fences the exact active attempt, invokes `worker-stop`, then transitions to cleanup. It never assumes the worktree or setup process was removed.

#### `aether_sessions_close`

Reconciles terminal, setup process, worktree, branch, pending mail, adapter records and survivors. It returns an aggregate `CleanupReceipt` and closes only when zero survivors and zero unknowns are proven or an authorized retained-resource disposition exists.

### Worker-only operations

Workers should not receive coordinator operations or general delegation authority. A minimal Aether worker bridge exposes only:

- `aether_worker_report(outcome, summary, files, evidence_reference)`;
- `aether_worker_ask(question, options)`;
- `aether_worker_heartbeat(phase)` when requested by the contract.

The bridge binds its operation to the current Dispatch capability and derives Task, Dispatch, project and attempt identity from authenticated launch state. Workers cannot choose another Run, recipient, project or attempt.

This bridge is necessary for profiles such as Ariadna or Ictinus that should not receive the general terminal tool merely to report lifecycle.

## 5. Durable identity and correlation

Aether IDs remain authoritative. Orca IDs are correlated routing identities.

### Required correlation record

```text
Aether installation_id
Aether project_id
Aether contract_id + generation + revocation_epoch
Aether run_id
Aether task_id + attempt
Aether worker principal/profile
Aether workspace binding
<->
Orca build digest + runtime_id
Orca run_id
Orca task_id
Orca dispatch_id
Orca terminal handle
Orca full worktree_id
```

The mapping belongs in a project-local, private Aether adapter ledger. It must not duplicate raw turns, reasoning, tool arguments or terminal transcripts. Orca keeps operational state; Aether keeps only correlation, product authority, verified receipts and closure evidence.

### Worktree identity gap

Current `ProjectIdentity` derives `project_id` from the canonical filesystem root. Two Git worktrees of the same repository therefore become two different Aether projects. That is correct for ordinary path isolation but insufficient for the proposed topology.

The adapter needs a new immutable `WorkspaceBinding` that proves:

- one stable admitted Aether project identity;
- exact canonical workspace root;
- common Git repository identity;
- Orca full worktree ID;
- parent/top-level lineage;
- base commit and current commit;
- allowed paths and execution domain.

Path containment remains relative to the worker workspace. Product authority and contract identity remain relative to the admitted Aether project. A worker cannot supply or change this binding.

### Evidence schema gap

The current evidence identity still contains `acp_session_id`. Mapping an Orca Dispatch into that field would preserve bytes but misrepresent semantics. The Orca path should introduce a versioned substrate-neutral evidence identity containing `runtime`, `runtime_session_id`, `workspace_id` and `dispatch_attempt`, while retaining explicit read compatibility for historical V1 ACP artifacts.

## 6. Per-session Hermes launch

The installed Aether Hermes is version `0.19.1`. It has profile-management commands but no invocation-level `--profile` flag. The initial adapter must therefore launch every worker with an explicit process environment:

```text
HERMES_HOME=<approved absolute profile home>
AETHER_HOME=<approved admitted project root or explicit continuity binding>
PYTHONPATH unset
PYTHONHOME unset
PATH containing the exact Aether Hermes venv and Orca CLI
cwd=<exact Orca worker worktree>
```

Additional rules:

- never copy `.env`, `auth.json` or credentials into worktrees;
- never inherit ambient `HERMES_HOME` as worker identity;
- use the exact Aether venv binary, not a PATH-ambiguous global installation;
- do not pass Hermes `--worktree`; Orca already owns worktree creation;
- keep Yolo off and preserve the approved profile toolsets;
- verify the loaded config, plugin and model/provider request before dispatch;
- fail closed if the profile is missing, disabled, forbidden or has drifted.

Because `worker-start --agent hermes` cannot express a per-task profile environment, the first implementation should use:

```text
worktree create
-> terminal create with an Aether-owned, profile-specific launch command
-> terminal wait for TUI readiness
-> orchestration dispatch --inject
```

After Orca exposes a public per-worker environment/profile seam, the adapter may switch to composed `worker-start` without changing the Aether product API.

## 7. Non-blocking supervision model

“Non-blocking” has a precise initial meaning:

1. `aether_sessions_start` starts every ready worker and returns after Dispatch acceptance.
2. The primary Hermes conversation remains usable while workers continue in Orca.
3. `aether_sessions_status` performs a zero-wait poll by default.
4. Hermes may continue local work or answer the user between polls.
5. A bounded wait is used only when the user explicitly asks Hermes to wait for results.
6. Aether never runs a hidden LLM coordinator loop.

The first release uses durable pull supervision: Hermes checks status at turn boundaries or when the user requests it. Push notifications require a later, separately accepted bridge from Orca Run Delivery into the active Hermes gateway/session. The TUI has no honest asynchronous message-delivery guarantee today, so the initial product must not promise one.

## 8. Worktree and concurrency policy

The user-selected product rule is one worker session per worktree.

- Use a **child worktree** only when the Task depends on the current candidate branch.
- Use a **top-level worktree** for independent work based on the repository default branch.
- Require a committed, known base before creating a child; uncommitted parent changes are not inherited.
- Allow one writer per worktree.
- Start all independent workers before observing any of them.
- Enforce `ExecutionContract.limits.concurrency` before every Dispatch.
- Keep the first pilot at two workers.
- Keep task DAG depth bounded to three or four levels.
- Workers cannot create Tasks, Dispatches or child workers.
- A worker-reported completion moves the Aether Task to review, not completion.

## 9. Operational-to-semantic state mapping

Orca and Aether state machines must not be merged.

| Orca observation | Aether interpretation |
|---|---|
| Run/Task created | admitted operational namespace only |
| Dispatch accepted | `DISPATCHED` |
| live terminal/status activity | `RUNNING` with liveness observation |
| question | `RUNNING`, coordinator input required |
| `worker_done: succeeded` | `REVIEW`, evidence still required |
| `worker_done: failed` | failed attempt; reconcile before retry |
| terminal stopped/disappeared | stopped observation, outcome may be unknown |
| Task completed in Orca | no automatic semantic transition |
| evidence verified | closure may be proposed |
| Aether completion authority accepts | `ACCEPTED` then terminal semantic outcome |
| zero-survivor cleanup | `CLOSED` operational resources |

## 10. Implementation increments

### Increment A — unblock and harden Orca

- fix `stale_bootstrap` / issue `#150` in isolated state;
- prove cold start, restart and shutdown;
- verify sandbox, private paths, Manual permissions and Yolo off;
- disable remotes, relay, telemetry, automations and credentials;
- run cross-project/profile negative probes.

**Gate:** runtime reachable and graph ready; rollback leaves no process or state outside the approved isolation root.

### Increment B — substrate-neutral identity and schemas

- add `WorkspaceBinding`;
- add substrate-neutral Evidence Identity V2 with V1 read compatibility;
- define strict Run, Task, Dispatch, Worker and Cleanup DTOs;
- reject unknown authority-bearing fields and states.

**Gate:** deterministic unit tests for forged roots, sibling worktrees, stale generations, foreign profiles and V1/V2 evidence.

### Increment C — read-only Orca client

- status/build identity;
- Run/Task/Dispatch inspection;
- worker/terminal/worktree inspection;
- strict JSON decoding and typed uncertainty;
- no mutation methods enabled.

**Gate:** fixture and live isolated read tests, including unknown-field/runtime-version failures.

### Increment D — one synthetic worker

- create one Run and Task;
- create one worktree;
- launch one Hermes worker with explicit profile home;
- inject one Dispatch;
- receive one worker report;
- verify artifact and repository behavior;
- clean all resources.

**Gate:** exact evidence, restart observation, rollback and zero survivors.

### Increment E — two non-blocking parallel workers

- create two independent Tasks first;
- launch both before polling;
- return a start receipt immediately;
- process questions and completions without duplicate delivery;
- verify each worktree independently;
- synthesize results in primary Hermes.

**Gate:** both attempts remain isolated, the primary session remains responsive, and worker completion cannot bypass Aether review.

### Increment F — recovery, cancellation and active-path candidate

- retry only after a proven terminal failure or reconciled unknown;
- reject stale Dispatch messages and terminal handles;
- recover after runtime restart without duplicate editors;
- cancel and aggregate cleanup;
- expose the Aether coordinator and worker tool surfaces;
- keep configuration default-off.

**Gate:** the complete M3 case set passes on the exact candidate before any active consumer switches.

## 11. Explicit non-goals for the first implementation

- no production activation or live Olympus cutover;
- no remote Orca servers;
- no recursive worker delegation;
- no dynamic Daimon hiring;
- no new workflow around Etalides, whose retirement is already intended;
- no Athena participation;
- no automatic acceptance, merge, release or deployment;
- no raw transcript migration;
- no Orca mutation of `.aether` continuity;
- no hidden fallback to ACP, Olympus or Harmonia;
- no fork of Orca before public seams prove insufficient.

## 12. Recommendation

The architecture is viable and substantially simpler than rebuilding process, terminal, worktree and message lifecycle inside Aether. Native Hermes support removes the largest integration uncertainty.

Implementation should begin, but only as the default-off M2 sequence above. The immediate engineering task is `stale_bootstrap`, followed by substrate-neutral worktree identity and a read-only adapter. A live migration is premature until the synthetic one-worker and bounded two-worker gates prove profile isolation, evidence, recovery, privacy and zero-survivor cleanup.
