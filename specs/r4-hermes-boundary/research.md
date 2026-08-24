# R4 Research: What Hermes Already Provides

**Purpose**: Evidence for the Hermes capability classification and for the three gaps.  
**Upstream repository**: `https://github.com/NousResearch/hermes-agent.git`  
**Local checkout**: `/home/darkarty/.hermes/hermes-agent`  
**Inspected revision**: `9ceb0858abfd1d3c3b32bd6f76e98d14ed7a2fbd`  
**Version**: `hermes-agent` 0.19.1 (`pyproject.toml`)  
**Checkout state**: clean except a modified `package-lock.json`, which does not affect any claim below.  
**Live profile inspected**: `/home/darkarty/Desktop/agentes/aether/home/` — local runtime state, evidence only, never committed.

## 1. Research Question

Hermes is a fixed foundation (PD-05). What does that concretely provide, what must Aether still build, and does anything in the framework contradict an accepted Aether decision?

## 2. Central Finding

**Hermes already implements most of the multi-agent runtime Aether was preparing to design.** More importantly, it *structurally enforces* several invariants Aether had written as prompt-level rules — meaning those rules are guaranteed rather than requested.

The delegation subsystem is not an approximation of Aether's fan-out. It is the same shape: a parent agent spawns isolated children with fresh context, inherited-but-not-widenable tools, their own terminal sessions, per-child iteration budgets, cost rollups, append-only transcripts, and a stall monitor.

## 3. Verified Evidence

### Delegation — the fan-out already exists

`website/docs/user-guide/features/delegation.md:9-11, 22-32, 116-126`

Children are isolated agent instances with fresh conversations and their own terminal sessions. Only the final summary re-enters the parent's context. Batches run in parallel with a default of 3 concurrent children, configurable with no hard ceiling; an oversized batch returns a tool error rather than being silently truncated. Results are ordered by task index regardless of completion order.

### Aether's handoff completeness principle is framework-enforced

`delegation.md:36-55`; `guides/delegation-patterns.md:91-93`

> "Subagents start with a **completely fresh conversation**. They have zero knowledge of the parent's conversation history, prior tool calls, or anything discussed before delegation. The subagent's only context comes from the `goal` and `context` fields the parent agent populates."

R2 §2 stated: *"The contract is finished when the supervision role needs to ask nobody."* Hermes states the identical constraint as a hard property of the runtime, with worked bad/good examples. Aether's central handoff principle is not an Aether invention — it is the documented reality of the framework it selected.

### Four Aether invariants are structurally enforced

`delegation.md:156-167, 325-334`

| Aether rule | Hermes enforcement |
|---|---|
| R3-FR-320 — no phase blocks on the owner | Children cannot use the user-interaction capability at all: "subagents cannot interact with the user" |
| R2-FR-206 — authority is not inherited or widened | "Each subagent inherits the parent's enabled toolsets so the model cannot grant a child capabilities that the parent does not have" |
| PD-13 — no re-concentration | Leaf children are blocked from delegating, writing shared memory, sending cross-platform messages, and scheduling work |
| R2-FR-207 — attempt budget | Per-child iteration limit, default 50, settable per call |

These are the strongest form of validation Aether's design has received: an independently built framework arrived at the same boundaries.

### The runaway bound Aether needed already exists

`delegation.md:183-242`

There is deliberately **no wall-clock timeout** by default, because fixed caps kept killing legitimately busy children. Instead a progress-based stall monitor samples API-call count, current tool, and a last-activity timestamp that ticks on every streamed token. Progressing children are never touched. A frozen child past the threshold (450s idle, 1200s inside a tool) is interrupted with a 120s grace window; one that never returns is force-finalized with a terminal `stalled` outcome carrying structured metadata.

R1-D06 removed the spending gate and moved the bound to R7. This is that bound, already built, and better calibrated than a timeout would have been.

### Role tiering and economics

`delegation.md:143-154, 349-368`

A per-delegation model and provider override exists specifically for routing children to cheaper models. `DESIGN.md` §7's cost/capability tiering has a native mechanism.

### Evidence and observability

`delegation.md:245-286`

Every dispatch creates an append-only, human-readable log per task under the profile's cache, pre-created at dispatch, with a batch manifest describing goals and per-task status. Logs persist after completion as the full-fidelity operational record and are readable from remote terminal backends. A live subagent overlay provides a tree of running and finished children with per-branch cost, token and touched-file rollups, per-child kill and pause, and post-hoc turn-by-turn review.

R11 does not need to design an evidence base. It needs to decide which of these is authoritative.

### Parallelism is bounded by disjoint files

`delegation-patterns.md:116-130`; `delegation.md:24, 120`

The documented multi-file pattern splits work across children by **disjoint file sets**. This confirms the constraint predicted during the earlier design review: the real limit on parallelism is how much of the work touches non-overlapping files, not how many children can be spawned.

### Nested delegation, and the topology it implies

`delegation.md:288-306`

Delegation is flat by default: a parent at depth 0 spawns children at depth 1, and those children cannot delegate further. A child spawned with an orchestrator role retains the delegation capability, gated by a spawn-depth setting whose default of 1 makes the orchestrator role a no-op. Raising it to 2 allows orchestrator children to spawn leaf grandchildren.

Aether's three roles therefore map onto: Morfeo at depth 0, the supervising role as an orchestrator child at depth 1, implementers as leaf children at depth 2 — requiring spawn depth 2. Notably, an orchestrator child **waits for its own batch in the current turn so it can synthesize the results**, which is precisely the supervising role's convergence behaviour.

The cost consequence is explicit: depth 3 with concurrency 3 reaches 27 concurrent leaves, and each level multiplies spend. With no spending gate (R1-D12) this belongs to R7 and R12.

## 4. Gap 1 — Delegation Is One-Way

`delegation.md:160-166, 325-334`

Children return a final summary. There is no channel for a running child to consult its parent, and the user-interaction capability is blocked for children of both roles. An orchestrator child keeps delegation but keeps every other block.

**Consequence for PD-18.** Christopher decided that Morfeo remains reachable during execution for blocking situations. The framework does not support that as a mid-flight conversation. The supervising role's only route upward is to finish and return.

**Resolution recorded as R4-D01.** Escalation becomes terminal and by return: the supervising role stops, returns a structured contract-defect outcome, and Morfeo revises the contract and re-delegates. This is consistent with R3-D02's change impact, which already required a failed executability pass to be a terminal branch rather than a retry. The cost is a lost partial run, which is why work performed before escalation must be preserved as evidence.

## 5. Gap 2 — No Durability Across Restart

`delegation.md:128-141, 308-323`

Completion events are stored durably before delivery, and a child that finished before a restart but whose result was undelivered is restored and re-routed. But:

> "A Hermes process restart does **not** resume a running child. Its attempt becomes `unknown` because Hermes cannot prove which side effects happened."

Durable alternatives exist for scheduled runs and long-running shell commands, but not for a running delegated agent.

**Consequence.** Aether cannot promise that hours of unattended work survive a runtime restart. An interrupted run must be reported as indeterminate, and recovery must inspect real repository state rather than trust a prior report. This is an R9 requirement and a genuine limit on the product's promise.

## 6. ~~Gap 3 — Hermes Has No A2A~~ — RETRACTED

**The section below is false and is retained only as the record of the error. Read §11 instead.**

## 6b. Retracted text

Searched repository-wide, including vendored directories: the protocol name `agent2agent` appears in **zero files**. Every superficially matching `a2a` string is unrelated — `a2a2a` in a desktop theme palette and `A2A00` in a CLI colour constant were checked directly and are hex colour values.

A different agent protocol adapter **is** present natively as a first-class module, carrying authentication, permissions, provenance, sessions, tools, and events.

**Consequence for R6.** The earlier framing — evaluate the real coverage of Hermes's A2A implementation — has no referent. Three findings follow:

1. Adopting A2A means Aether implements it from scratch, not configures it.
2. A natively present alternative protocol exists and must be evaluated alongside it.
3. Most importantly, native delegation already crosses every Aether role boundary in-process, with authority containment, evidence, and cancellation. R6 must therefore seriously evaluate **no protocol at all**, which was not previously among the admissible outcomes.

## 7. Live Profile Observations

The live profile at `Desktop/agentes/aether/home/` shows subsystems present and initialized: session and state databases, a project database, curated memories, skills, plugins, a gateway with recorded state, sandboxes, agent hooks and a shell-hooks allowlist, messaging platforms and a channel directory, cron, an LSP integration, and a verification-evidence database.

Two observations matter for Aether:

- **The shell-hooks allowlist and agent hooks are the likely mechanism** for R1's protected-effect automation. Recorded as a lead; not yet inspected.
- **A task-board database is present and initialized.** The conceptual design explicitly does not select that subsystem. Its presence is not adoption, per FR-415.

## 8. Decisions

## R4-D01 — PD-18 is contradicted by the framework; the replacement is R7's to design

- **Need**: PD-18 states that Morfeo remains reachable during execution so a contract defect can be repaired without the owner. The framework provides no upward channel from a running child.
- **Decision**: R4 records the contradiction and hands the resolution to R7. It does **not** select a mechanism. Any design must work within the framework's supported route upward — a child finishing and returning — because PD-19 forbids modifying core to obtain a channel.
- **Rationale**: R4's scope is classification. Choosing how escalation works is supervision design, and deciding it here would be the same over-reach R4 warns against elsewhere. The constraint is a fact; the mechanism is a choice with alternatives R7 should weigh against convergence, retries, and partial-work handling.
- **Evidence**: `delegation.md:160-166, 325-334`.
- **Options R7 will need to weigh**, recorded so the finding is not re-derived: escalating by terminal return with partial work preserved as evidence; escalating at the executability check before implementation begins, so less is lost; or restructuring so that contract validation happens before any child is spawned at all.
- **Change impact**: PD-18 must be revised once R7 decides. R5 must keep Morfeo instantiated to receive returns regardless of which option R7 selects.

## R4-D02 — Native capabilities are the primary mechanism where they enforce an Aether rule

- **Need**: Several Aether requirements written as instructions turn out to be framework-guaranteed.
- **Decision**: Where Hermes enforces an invariant structurally, that enforcement is primary and Aether's instruction becomes reinforcement rather than the mechanism.
- **Rationale**: A structural guarantee cannot be talked out of by a model, which is exactly the weakness R1 acknowledged when it named the few things instructions cannot guarantee.
- **Evidence**: `delegation.md:156-167, 325-334`.
- **Alternatives considered**: Restating the rules only as prompts was rejected as weaker than available. Removing the instructions entirely was rejected because they carry intent that survives a framework change.
- **Change impact**: R10 gains a shorter enforcement list than R1 anticipated.

## R4-D03 — R6 must include the no-protocol outcome

- **Need**: A2A was the preferred candidate on the assumption that Hermes implemented it. It does not.
- **Decision**: R6 evaluates A2A, the natively present protocol adapter, and no protocol at all, on evidence.
- **Rationale**: Delegation already crosses every role boundary in-process with authority containment and evidence. Adopting a protocol to satisfy a preference when nothing requires it would violate FR-403 and PD-19.
- **Evidence**: repository-wide search returning zero occurrences; the native adapter module's presence.
- **Alternatives considered**: Keeping A2A as the default expectation was rejected as designing toward a mechanism rather than a requirement.
- **Change impact**: Materially reframes R6 and reduces its likely scope. `DESIGN.md` §10 and PD entries referencing A2A require review.

## 9. Not Yet Inspected

Claims about these remain pending and must not be relied upon by later stages until read directly:

- hooks and the shell-hooks allowlist — the likely home of R1's protected-effect automation;
- memory and memory-provider internals — R3-D04's personalization channel and R9's storage;
- profiles, multi-profile gateways, and profile routing — R5's isolation question;
- session lifecycle and the subagent lifecycle API — R5 and R9;
- the native protocol adapter's internals — R6;
- terminal backends — R8's execution isolation.

The capability table in `spec.md` marks the two rows that depend on unread sources as pending.

## 10. Risks

| Risk | Mitigation | Owner |
|---|---|---|
| Escalation-by-return wastes long partial runs | Escalate at the executability check, before implementation begins, wherever possible | R7 |
| A runtime restart silently loses hours of work | Report indeterminate rather than success; recover from real repository state | R9 |
| Depth 2 plus concurrency multiplies cost with no spending gate | Choose depth and concurrency against measured cost | R7, R12 |
| Version-specific claims silently expire | Every claim records the version; upgrades are reviewed against this classification | R4 |
| A present-but-unselected subsystem gets adopted by proximity | Unselected capabilities are named with reasons | R4 |

## 11. Correction — Hermes Ships A2A, and the Method Failure That Hid It

**Verified in the source Aether actually runs**: `/home/darkarty/Desktop/agentes/aether/home/.venv-hermes/src/hermes-agent`, version 0.20.1, revision `411903b6fa258f81afcc3869eb615f6218e1776a`. The Aether profile installs Hermes as an editable package pointing at that tree.

### What is actually there

`website/docs/user-guide/messaging/a2a.md`, plus `plugins/platforms/a2a/` and two test modules.

A2A is implemented as a **platform plugin** and works in both directions. Outbound, the agent gets tools to discover a peer's agent card, call it, hold multi-turn exchanges keyed by context, recall persisted conversations, and fan a task out to every peer advertising a capability. Inbound, Hermes serves an agent card at the canonical well-known path and JSON-RPC v1.0 methods including send, streaming send, get, list, cancel, subscribe, and push-notification configuration, with SSE streaming and HMAC-signed webhooks. Inbound tasks are injected into a live gateway session — the same agent, memory and tools that serve other channels.

The security model is secure-by-default: no token means localhost-only binding, remote exposure requires both a token and an explicit host, per-peer tokens drive rate limiting and audit, inbound text is filtered and framed as untrusted, credential-shaped strings are redacted from replies, every exchange is appended to an audit log, and per-context turn caps prevent two agents ping-ponging forever.

Interoperability is verified against the official SDK, and peers may be other Hermes instances or agents built on entirely different frameworks.

### Upstream's own guidance on when to use it

`a2a.md:13`:

> "When you want multiple agents on the **same machine**, prefer delegation (in-process subagents) or the kanban board (durable multi-profile work queue) — A2A is for crossing process/machine/framework boundaries."

Two things follow that matter more than the A2A correction itself:

1. **The durable multi-profile work queue is the native same-machine multi-profile mechanism.** The earlier claim that profiles cannot exchange work was false. It remains an unselected subsystem, but it is now a real option rather than a non-existent one.
2. **A2A explicitly targets cross-process, cross-machine and cross-framework boundaries.** Whether Aether has such a boundary is exactly the R5 topology question, which is why R5 cannot be settled before this correction is absorbed.

### How the error happened

Two Hermes checkouts exist on this machine. `~/.hermes/hermes-agent` is version 0.19.1. The Aether profile runs an editable install pointing at `home/.venv-hermes/src/hermes-agent`, version 0.20.1. R4 was researched entirely against the first.

The method in `AGENTS.md` required reading the actual file and recording the exact revision, and that was done — against the wrong tree. Recording a revision proves *what* was read, not *that the right thing* was read. The check that was missing is resolving which source the runtime actually loads before reading any of it.

`AGENTS.md` has been corrected to name the running source and to require that resolution step.

## 12. Evidence Verified Against 0.20.1

Source: `home/.venv-hermes/src/hermes-agent`, version 0.20.1, revision `411903b6fa258f81afcc3869eb615f6218e1776a`, remote `NousResearch/hermes-agent`. Working tree clean except `package-lock.json` and a TUI build script, neither affecting any claim.

Method note: rather than re-reading everything, the two trees were diffed directly, so what follows is specifically **what changed** plus the sections the diff showed as new.

### Retraction 2 — delegation is not one-way

`website/docs/user-guide/features/delegation.md`, section "Steering a Running Subagent" — **new in 0.20.1, absent from 0.19.1**.

> "Interrupting a child throws away its in-flight work; often you just want to redirect it."

The parent orchestrates its own running children through the same delegation tool, with three control actions: `list` returns live children with id, goal, status, running seconds, an `accepting_steer` flag and the live transcript path; `steer` queues a course correction into a running child **without stopping it**; `stop` ends a child at its next iteration boundary and its partial result still re-enters the conversation as a normal completion.

Control actions run synchronously in-turn, are scoped to the caller's own spawn tree so a conversation can never control another session's children, and never consume the per-turn spawn cap.

The delivery semantics are unusually honest and worth preserving in Aether's design: *"Queued is not delivered, but it is never synthetic success."* If a child accepted a steer but had already produced its final answer, the completion retains it as `missed_steer` with an explicit note, so the parent can tell a steered child from one that finished on the old instructions.

**Consequence.** R4's Gap 1 overstated the limit. There is no child-initiated upward channel, but there is a parent-initiated downward one, and mid-flight correction does not require killing the worker. R7's escalation design gains an option that did not exist under the earlier finding.

### Retraction 3 — Aether does not need to design convergence

Two mechanisms exist, both new relative to what R4 assumed:

- **Judge-driven persistent goals.** A standing objective survives across turns; after every turn a lightweight judge model checks whether it is satisfied, and if not a continuation prompt is fed back into the same session until the goal is met, the user clears it, or the turn budget runs out. Upstream names its lineage openly as an adaptation of the Ralph loop.
- **Timer-driven loops.** A prompt re-runs on a cadence inside a session, with "run the tests, fix what fails, repeat until they pass" given as a canonical use.

A board card created in goal mode runs the same continuation engine **inside that card's worker session** — borrowing the engine, not the board.

**Consequence.** R7 must not design a convergence engine. It configures one.

### The three coordination primitives

`website/docs/user-guide/features/kanban.md:1-60` establishes the third primitive and states the comparison directly. The board is a durable SQLite-backed task board shared across all profiles that

> "lets multiple named agents collaborate on work **without fragile in-process subagent swarms**. Every task is a row … every handoff is a row anyone can read and write; **every worker is a full OS process with its own identity**."

Its stated comparison against delegation is reproduced in `spec.md` §2. The load-bearing differences are resumability (delegation: *failed is failed*; board: block, unblock, re-run, and crash-reclaim), human-in-the-loop (unsupported versus comment-or-unblock at any point), audit trail (lost on context compression versus durable rows permanently), coordination shape (hierarchical versus peer), and per-task model override (absent versus present).

Upstream's selection rule:

> "Use `delegate_task` when the parent agent needs a short reasoning answer before continuing, no humans involved, result goes back into the parent's context. **Use Kanban when work crosses agent boundaries, needs to survive restarts, might need human input, might be picked up by a different role, or needs to be discoverable after the fact.**"

And among the workloads listed as covered by the board and not by delegation:

> "**Engineering pipelines — decompose → implement in parallel worktrees → review → iterate → PR.**"

**Consequence, and it is the largest finding of this stage.** That sentence is Aether's architecture. Every one of upstream's five criteria for choosing the board is an accepted Aether requirement, and two things R4's earlier version recorded as immovable framework limits — no durability across restart, and no per-worker working directory — are properties of delegation that the board does not share. `DESIGN.md` §9 declares the board not selected; that declaration predates any evidence and must be reopened rather than defended.

### Profiles — upstream instructs what Christopher asked for

`website/docs/user-guide/profiles.md:13-16` — **new caution in 0.20.1**:

> "**Give every agent its own profile.** Never point two agent processes at the same profile (the same Hermes home). Both write memory automatically, and each loads the other's writes into its system prompt at session start — so two writers on one home compound each other's state until it stops being anything you configured. Profiles exist exactly to prevent this; agents that need shared memory should use an external memory provider instead."

Christopher's stated preference for separate profiles is upstream's explicit instruction, with a concrete failure mode attached. The deleted R5 argued the opposite.

### Cost tiering, with upstream's reasoning

`delegation.md`, section "Cost strategy: frontier planner, inexpensive workers" — **new in 0.20.1**:

> "Decomposing a problem into well-specified subtasks takes frontier-level judgment; executing a subtask that already comes with a clear goal, full context, and an output contract usually doesn't. Meanwhile the children are where the tokens go — a parallel batch of subagents typically burns the large majority of a run's total tokens."

This is `DESIGN.md` §7's tiering with an argument attached, and it sharpens it: the reason to spend on the planner is that decomposition needs judgment, and the reason to economize on workers is that they carry the volume.

One limit matters for R12: the delegation model pin is **global** — there is no per-task model parameter — so a quality-sensitive subtask must either run with the pin unset for that session or be handed to the board, which does support per-task override.

### What remains a gap, narrowed

Only durability survives, and only for delegation. A running delegated child does not survive a runtime restart, reconnection is unavailable afterwards, and the attempt is recorded as unknown because side effects cannot be proven. The board's crash-reclaim behaviour means this is a property of the primitive, not of the framework.

### Consequences

- Every other capability claim in R4 describes 0.19.1 and is **unverified**, not necessarily wrong. R4 is reopened until re-checked against 0.20.1.
- `DESIGN.md` §10 and the R6 roadmap entry were rewritten on the false finding and are restored.
- R5 was designed on the premise that profiles cannot exchange work. That premise is void, and the stage was deleted rather than patched — Christopher had also stated he wanted separate profiles, which the false premise had ruled out.

## 13. A1 public-baseline reconciliation (2026-08-21)

### 13.1 Source resolution and factual correction

The release selected for A1 was `NousResearch/hermes-agent` `v2026.8.18`. Direct GitHub inspection showed that this is an **annotated tag**: ref `refs/tags/v2026.8.18` points to tag object `9f13bbbf8423427e159c78066356ca0e27ca6b74`, which dereferences to commit `e624e9fde561e1add9388384012b295fde669ade`. `pyproject.toml:3-15` at that commit records distribution version `0.20.4` and Python `>=3.11,<3.14`.

The Phase 0 handoff supplied `9f13bb131670169467d9b2453ae2e8848814ff6e` as the commit. GitHub returned “No commit found” for that object. The owner selected the named release and its version; the release's actual annotated-tag object and commit are therefore the controlling technical identity. This correction changes no product decision and is recorded prominently because an unresolvable commit cannot be a release lock.

The GitHub-generated archive fetched from `https://github.com/NousResearch/hermes-agent/archive/refs/tags/v2026.8.18.tar.gz` during this inspection was `66,313,931` bytes with SHA-256 `1e3d39d3638ec15fa9d31af262568a953e9272090deb1c50c44cd401175f5b80`. Phase 2 must either lock that exact byte stream or produce and lock its own immutable public artifact; a mutable branch is never an acceptable substitute.

### 13.2 What changed since the loaded 0.20.1 evidence

The selected release materially expands native surfaces that Aether should reuse:

- `hermes_cli/projects_db.py:1-21,57-96,235-261` defines per-profile first-class Projects with stable IDs/slugs, folders, primary paths, and optional board binding.
- `hermes_cli/projects_cmd.py:1-10,22-104` exposes create/list/show/folder/primary/use/archive/restore/board-binding commands.
- `tests/hermes_cli/test_kanban_project_link.py:29-64` and `test_kanban_board_project.py:40-87` prove project-linked deterministic worktrees/branches and board-project inheritance.
- `hermes_cli/provider_catalog.py:1-33,83-140` derives provider membership from Hermes's canonical/plugin-backed registry, so Aether needs no private provider list.
- `website/docs/user-guide/features/hooks.md:9-18,438-445,528-554` documents plugin and shell `pre_tool_call` interception and fail-closed approval behavior.

These findings narrow Aether's gap: `aether init` owns portable project identity, local mapping, validation, and policy, but it adapts Hermes Project/board/worktree primitives rather than implementing them again.

### 13.3 Downstream patch disposition

PD-65 makes the fork transitional rather than permanent. The selected upstream tag was compared with the active patch ledger and current upstream issue/PR state on 2026-08-21:

| Patch guarantee | Selected-tag finding | Upstream disposition at inspection | A1 disposition | Retirement gate |
|---|---|---|---|---|
| Sticky `initial_status=blocked` | Tag creates the status but no durable sticky block event; readiness recomputation can still promote it | PR `#91180` open | Carry in transitional fork | Exact released upstream artifact passes initial-block and negative promotion regressions |
| Agent-facing `max_retries` | `KANBAN_CREATE_SCHEMA` contains no `max_retries` | PR `#89590` open | Carry | Schema, validation, forwarding, omission, and invalid-input matrix pass on an exact upstream release |
| Human-gated needs-input escalation | Required escalation provenance/recovery contract absent | PR `#91211` open | Carry | Exact upstream release preserves human gate through recovery and passes the Aether lifecycle matrix |
| One durable terminal handoff | Selected tag has protocol-violation retries but not the accepted unique durable terminal-receipt rule | PR `#91220` open | Carry | Exact upstream release passes same-card phase handoff and duplicate/missing-terminal controls |
| First-spawn branch propagation | `kanban_db.py:10230-10265` persists the derived branch, then passes the stale claimed task to spawn | issue `#89677` and PR `#89688` open | Carry | First ready and review spawns receive the exact persisted branch; scratch/dir controls receive none |
| Per-profile cap overrides | Tag exposes one uniform `max_in_progress_per_profile`, not an asymmetric role map | issue `#91259` and PR `#91266` open | Carry | Ready/review/CLI/gateway paths pass against an exact upstream release with Aether's 1/3 profile allocation |
| Directory-versus-script gateway lifecycle guard | Commit `9ac1e65…` is an ancestor of the selected tag | upstream issue `#86753` closed | Do not carry by default | Reproduce the original directory false positive plus real script/process controls on the exact selected artifact |

**Decision.** A1 enters build work in `transitional_fork` mode, based on the assumption that the accepted workflow guarantees above remain mandatory and no qualified non-core adaptation currently satisfies them. This is delegated release-mode selection within PD-65, not authority to create or publish the fork.

**Rejected alternatives.** (1) Declare `upstream` now and silently drop guarantees: rejected because it weakens accepted behavior. (2) Treat open PR heads or the local editable checkout as the release dependency: rejected because neither is an immutable public release. (3) make the fork permanent: rejected by PD-65. (4) carry every historical patch regardless of upstream: rejected because the lifecycle-guard fix is already contained and patches retire on qualification evidence.

**Impact.** Phase 2 must reconcile only the six carried lines onto the selected base, build public artifacts, produce provenance/digests, and request a separate publication gate. No new downstream-only feature is allowed. Each later Hermes release is reviewed line by line and can move Aether back to `upstream` only after the exact release artifact passes all retirement gates.

### 13.4 Current Aether issue state

Read-only GitHub inspection on 2026-08-21 found Aether issues `#192` (retry/resumption/lifecycle accounting) and `#195` (semantic progress beyond heartbeat) still **OPEN**, both last updated 2026-08-19. Issue `#192` remains release-visible under its accepted limitation contract. PD-68 later changed `#195` into a stable-1.0 prerequisite governed by `../002-aether-contract-observation/`; an upstream tag does not close either Aether acceptance criterion without its required evidence.
