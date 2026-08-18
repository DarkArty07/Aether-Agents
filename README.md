# Aether Agents

**You design and decide once, well. Then agents build for hours without you.**

Aether is a multi-agent software-engineering method. It is not a framework and it ships no runtime: it is a role model, a contract, and a configuration layered on top of two existing systems — [Hermes Agent](https://github.com/NousResearch/hermes-agent) for the runtime and [GitHub Spec Kit](https://github.com/github/spec-kit) for the method.

The owner states intent once, in conversation. From that point the system works unattended: it turns intent into a specification, breaks the specification into units of work, executes those units in parallel as separate operating-system processes, reviews and integrates them, and reports back at the end. The owner is not asked to approve steps along the way, and nothing waits on his attention unless the work genuinely cannot proceed without a decision he alone can make.

## The problem it solves

An agent session is only as good as what it was told, and the owner is the bottleneck. Aether splits his involvement into two asymmetric phases:

**Extraction — high bandwidth, owner present.** One role, Morfeo, gets everything out of his head in a single pass: what he wants, what he assumed without saying, what he left ambiguous. There is no second chance to ask.

**Autonomy — hours, owner absent.** Everything downstream runs on what was captured. Difficulties are reported at the end, not as they occur.

The whole design follows from that split. Every rule about handoffs, evidence, and escalation exists to make the second phase survive the absence of the first.

## The three roles

| Role | Talks to the owner | Owns | Model tier |
|---|---|---|---|
| **Morfeo** | Yes — the only one | Constitution, specification, clarification, technical plan | Frontier |
| **Supervisor** | No | Task breakdown, executability analysis, review, decisions, convergence, integration | Capable |
| **Implementer** | No | Writing the code. Many run concurrently | Inexpensive |

Every role is a real operating-system process with its own Hermes profile: its own configuration, credentials, memory, skills, and model. Two agent processes never share a profile.

Roles are never added to solve an execution problem. Fresh context, a card-pinned skill, or a per-card model override are tried first; a fourth role requires an explicit owner decision.

## How work flows

```text
owner ──conversation──► morfeo
                          │  writes the contract, creates ONE card
                          ▼
                    [ supervisor ]
                          │  derives the breakdown, analyses executability,
                          │  stamps shared decisions, creates child cards
              ┌───────────┼───────────┐
              ▼           ▼           ▼
      [ implementer ] [ implementer ] [ implementer ]
              │           │           │   each in its own git worktree
              └───────────┼───────────┘   each completes with evidence
                          ▼  promoted automatically when all parents finish
                  [ integration card ]
                          ▼
                  owner reviews the running product
```

The coordination substrate is Hermes's durable board: a SQLite table where each row is one unit of work, plus a dispatcher loop that launches the assigned profile as a process. Nothing in Aether queues, retries, reclaims, or audits — all of that already exists.

**Nobody administers the board.** Routing lives in the dependency graph, state lives in the table, execution lives in short-lived processes. No agent holds two of the three, which is what keeps the architecture from collapsing back into the hub-and-spoke shape that failed before.

## Escalation has exactly two tiers

This is the part most systems get wrong, and Aether's answer is verified against the runtime rather than assumed.

**Tier 1 — the system resolves it.** An implementer that hits a question the contract does not answer does *not* stop and does *not* wake anyone. It creates a decision card addressed to the supervisor and links that card as a parent of its own. The link alone moves its own card back to waiting. A fresh supervisor process picks up the decision card, decides with the whole contract in view, and completes. The implementer's card then promotes itself automatically and re-spawns with the decision delivered verbatim in its context.

No human is involved, no privileged tool is required, and the block-loop counter is never touched.

**Tier 2 — the contract is genuinely defective.** If the supervisor finds the answer is not derivable from the contract, it blocks the decision card as needing input. That surfaces to Morfeo, who is the only role permitted to revise a contract, and who asks the owner. Work on every unrelated unit continues untouched.

The rule that separates the tiers: **a question the contract can answer is never escalated to a human; a question the contract cannot answer is never invented by an agent.**

## Where Hermes ends and Aether begins

| Hermes owns | Aether owns |
|---|---|
| Conversation loop, tools, terminal backends | Which roles exist and what each is for |
| The durable board, dispatcher, retries, reclaim | Which Spec Kit phase each role performs |
| Worktrees, attempt history, audit trail | The contract and what makes it complete |
| Convergence judging, steering, hooks | The instructions that make each role behave |
| Profiles, memory, skills, scheduling | Quality standards and evidence expectations |

Aether does not fork, vendor, or patch Hermes. It expresses itself entirely through profiles, configuration, skills, and prompts. Where Hermes enforces something structurally that Aether specified as an instruction, the structural guarantee is primary and the instruction is reinforcement.

## The method

Aether does not invent a software process. It distributes Spec Kit's across three roles and resolves every point where upstream would stop and ask a human:

| Phase | Owner |
|---|---|
| `constitution` | Owner decides, Morfeo drafts |
| `specify`, `clarify`, `plan` | Morfeo |
| `tasks`, `analyze`, `checklist`, `converge` | Supervisor |
| `implement` | Implementers |

The contract is the Spec Kit artifact set — `spec.md`, `plan.md`, `tasks.md`, and friends — carried in the project's own repository. Aether adds no competing contract artifact; it adds an execution envelope inside `plan.md` (authority, budget, brownfield boundary) that upstream has no reason to carry.

## Status

**Design is complete through R13. Nothing is built.** No profile exists, no configuration is applied, no agent has run. The design deliberately stops at the boundary where implementation would begin.

What has been verified by direct execution against Hermes 0.20.1, revision `411903b6fa258f81afcc3869eb615f6218e1776a` — with no profile created, no agent spawned, and no model called:

- Dependency gating, automatic promotion, and parallel release of sibling units
- Verbatim forward delivery of a completed unit's summary and structured metadata
- Durable blocking, human answer by comment, and resumption with full history
- The two-tier escalation pattern, end to end, using only worker-available tools
- Worker dispatch: atomic claim, workspace preparation, spawn, and attempt records
- Per-card git worktrees — separate directories on separate branches, concurrently
- Concurrency as a live cap rather than a per-tick budget
- Crash detection and reclaim, including that a crash also consumes a failure
- The review lane end to end, without touching the block budget
- Enforcement: a hook denying a forbidden call, and three ways it can be silently inert
- That disabling automatic decomposition is honoured

What remains assumed, and needs a real run with a model:

- Goal-mode convergence judging
- Wake delivery to Morfeo through a live gateway
- Whether a real worker's evidence is good enough to accept by

The design labels these as assumptions wherever it depends on them. The verification method — the runtime's own injectable spawn seam and directly callable board kernel — is recorded in [`specs/r13-synthesis-and-release/research.md`](specs/r13-synthesis-and-release/research.md), because most runtime assumptions in this project are testable for free.

## For whoever implements this

Read in this order: this file, then [`DESIGN.md`](DESIGN.md) for the accepted product decisions, then [`ROADMAP.md`](ROADMAP.md) as the index of design areas, then the specification of the area you are about to build. [`AGENTS.md`](AGENTS.md) states the working method and is not optional — in particular, the rule that upstream is read before anything is designed, and that a capability claim must cite the tree the runtime actually loads.

Implementation order that the design supports:

1. Create three profiles, one per role, each with its own description.
2. Apply the configuration in [R12](specs/r12-models-and-economics/spec.md) (model tiers) and [R7](specs/r7-supervision-and-convergence/spec.md) (concurrency, budgets, and the defaults that must be turned off).
3. Write the three system prompts to the behavioural specifications in [R1](specs/r1-authority-and-interaction/spec.md), [R7](specs/r7-supervision-and-convergence/spec.md), and [R13](specs/r13-synthesis-and-release/spec.md). Writing the wording is build, not design, and is deliberately left open.
4. Install the enforcement hooks in [R10](specs/r10-security-and-authority/spec.md).
5. Run the walking-skeleton checkpoint described in [`ROADMAP.md`](ROADMAP.md) before trusting any runtime claim this design labels as assumed.

Two defaults must be changed before the first unattended run, and both are recorded with their reasons in [R7](specs/r7-supervision-and-convergence/spec.md). Leaving them alone produces a system that quietly reassigns work the contract never authorised.

## Repository map

| Path | Owns |
|---|---|
| [`DESIGN.md`](DESIGN.md) | Conceptual product design and accepted decisions |
| [`ROADMAP.md`](ROADMAP.md) | Design-area index, dependencies, status |
| [`AGENTS.md`](AGENTS.md) | How Aether is built, and the evidence rules |
| [`specs/`](specs) | One directory per design area, each owning its requirements |
| `home/` | A live Hermes profile used as runtime evidence. Not documentation of intent |

## Principles that must not be violated

1. **Read upstream before designing.** Most of the thinking already exists. A long gap list means the reading was too shallow.
2. **Resolve which source the runtime actually loads before reading it.** Recording a revision proves what was read, not that the right thing was read. This mistake has already cost this project a full stage.
3. **Verify in code what a decision rests on.** Documentation states intent; the registry states what is actually exposed.
4. **Never re-concentrate roles.** The previous architecture failed by role overload. Every convenience that moves work back toward one agent is the beginning of that failure.
5. **Do not build what the runtime already provides.** No queue, no state machine, no retry, no reclaim, no audit trail.
6. **Design and build are separate authorities.** Accepting a design authorises nothing to run.

## License

MIT — see [LICENSE](LICENSE).
