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
| **Morfeo** | Yes — the only one | Constitution, specification, clarification, technical plan, and bounded direct operational stewardship | Frontier |
| **Supervisor** | No | Task breakdown, executability analysis, review, decisions, convergence, integration | Capable |
| **Implementer** | No | Writing the code. Many run concurrently | Inexpensive |

Every role is a real operating-system process with its own Hermes profile: its own configuration, credentials, memory, skills, and model. Two agent processes never share a profile.

Roles are never added to solve an execution problem. Fresh context, a card-pinned skill, or a per-card model override are tried first; a fourth role requires an explicit owner decision.

## How work flows

```text
owner ──conversation──► morfeo
                          │
              ┌───────────┴────────────┐
              │                        │
      bounded operational      substantial objective
      objective: Morfeo acts   writes the contract,
      directly and verifies    creates ONE card
              │                        ▼
              │                  [ supervisor ]
              │                        │  derives the breakdown, analyses executability,
              │                        │  stamps shared decisions, creates child cards
              │            ┌───────────┼───────────┐
              │            ▼           ▼           ▼
              │    [ implementer ] [ implementer ] [ implementer ]
              │            │           │           │   each in its own git worktree
              │            └───────────┼───────────┘   each completes with evidence
              │                        ▼  promoted automatically when all parents finish
              │                [ integration card ]
              │                        │
              └────────────┬───────────┘
                            ▼
                  owner reviews the result
```

Morfeo chooses between the two routes by reasoning over the owner's complete objective, never by a classifier, score, or threshold. **Direct action** fits a bounded objective whose consequences are inspectable and easy to correct, where decomposition or independent review would add no proportionate value — Morfeo completes it with its own file and terminal access and verifies the real result. **The pipeline** fits a feature, an architectural change, multiple responsibilities, complex integration, or material uncertainty — Morfeo hands over exactly one contract card, and Supervisor's breakdown, independent review, and controlled integration take it from there. Direct action never substitutes for that independent review and controlled integration on work that actually needs them; it exists only for work that doesn't.

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

Aether does not fork, vendor, or patch Hermes. It expresses itself through profiles, configuration, skills, prompts, and a versioned policy-hook template installed into those profiles. Where Hermes enforces something structurally that Aether specified as an instruction, the structural guarantee is primary and the instruction is reinforcement.

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

**Design R0–R13 and build Phases 0–4 are complete. The explicitly authorized Phase 5 EC1 run completed on 2026-08-18.** Morfeo, Supervisor, and Implementer exist as separate profiles with configured hooks; the checkpoint used live models, a shared durable board, an isolated worktree, independent review, and one local integration in a sacrificial repository unrelated to product delivery.

Phase 5 produced candidate evidence for the three previously assumed runtime claims:

- A converged goal-mode unit reached same-card review and final completion; a separate impossible unit exhausted `2/2` turns and was durably blocked without a false success or file mutation.
- Terminal board events resumed the same live Morfeo TUI session, including a final turn that assembled its report from board state.
- A real Implementer changed only `result.txt`; Supervisor independently reviewed and integrated it; `python3 verify.py` passes in the canonical fixture with `PASS: EC1 result is exact`.

The run also exposed material lifecycle findings: `initial_status: blocked` auto-promoted, worker-side creation omitted the retry field, `needs_input` entered triage and redispatched without an unblock, and one same-card goal needed distinct Implementer and Supervisor predicates. These findings and the complete task/session/commit trace are recorded in [`R13 research §14`](specs/r13-synthesis-and-release/research.md).

**Phase 6 has not been rerun after EC1.** Its earlier `HOLD` packet remains the historical pre-run qualification; no runtime claim has been formally promoted and no `READY`, product activation, publication, deployment, or Hermes-to-Morfeo cutover is authorized. The next protected step is Phase 6 evidence re-qualification, not another Phase 5 run.

## Canonical Morfeo TUI activation

The versioned launcher is the supported entry point for a local Morfeo TUI:

```bash
python3 scripts/aether_tui.py --check
python3 scripts/aether_tui.py
```

`--check` performs no model or network call. It fails visibly unless the repository-local Morfeo profile, Hermes executable, `SOUL.md`, and the `file` and `kanban` toolsets are present. A real launch clears inherited Python path overrides, sets `HERMES_HOME` to Morfeo, and starts Hermes with `--tui --in <repository>`, so profile and working directory do not depend on the caller's shell or previous session.

A short user-local `aether` command may delegate to this versioned script. The wrapper itself remains local because machine paths and profile state are not repository artifacts.

On 2026-08-20, amended PD-44 and PD-45 were mechanically delivered to the stopped local profiles. Morfeo now has the accepted proportional direct-execution surface with CLI/Telegram parity; Supervisor and Implementer retain their separate authority. Christopher accepted the active direct-execution experience as sufficient functional validation for #196 and closed that issue. This does not replace Phase 6 or close the remaining runtime/debt issues.

## For whoever implements this

Read in this order: this file, then [`DESIGN.md`](DESIGN.md) for the accepted product decisions, then [`ROADMAP.md`](ROADMAP.md) as the index of design areas, then the specification of the area you are about to build. [`AGENTS.md`](AGENTS.md) states the working method and is not optional — in particular, the rule that upstream is read before anything is designed, and that a capability claim must cite the tree the runtime actually loads.

Implementation order that the design supports:

1. Create three profiles, one per role, each with its own description.
2. Apply the configuration in [R12](specs/r12-models-and-economics/spec.md) (model tiers) and [R7](specs/r7-supervision-and-convergence/spec.md) (concurrency, budgets, and the defaults that must be turned off).
3. Write the three system prompts to the behavioural specifications in [R1](specs/r1-authority-and-interaction/spec.md), [R7](specs/r7-supervision-and-convergence/spec.md), and [R13](specs/r13-synthesis-and-release/spec.md). Writing the wording is build, not design, and is deliberately left open.
4. Install the enforcement hooks in [R10](specs/r10-security-and-authority/spec.md).
5. Run the walking-skeleton checkpoint described in [`ROADMAP.md`](ROADMAP.md) before trusting any runtime claim this design labels as assumed.
6. Qualify the checkpoint evidence through [R13 Phase 6](specs/r13-synthesis-and-release/plan.md): promote or retain claims, revisit provisional values, correlate cost, record debt, and return `READY` or `HOLD`. This step never performs cutover or product activation.

Two defaults must be changed before the first unattended run, and both are recorded with their reasons in [R7](specs/r7-supervision-and-convergence/spec.md). Leaving them alone produces a system that quietly reassigns work the contract never authorised.

## Repository map

| Path | Owns |
|---|---|
| [`DESIGN.md`](DESIGN.md) | Conceptual product design and accepted decisions |
| [`ROADMAP.md`](ROADMAP.md) | Design-area index, dependencies, status |
| [`AGENTS.md`](AGENTS.md) | How Aether is built, and the evidence rules |
| [`specs/`](specs) | One directory per design area, each owning its requirements |
| [`policy/hooks/`](policy/hooks) | Canonical sanitized pre-tool policy, synchronization, verification, and rollback instructions |
| [`scripts/aether_tui.py`](scripts/aether_tui.py) | Canonical validation and activation of the local Morfeo TUI |
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
