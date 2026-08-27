# Aether Agents

**You design and decide once, well. Then agents build for hours without you.**

Aether is a multi-agent software-engineering product and method built around two existing systems — [Hermes Agent](https://github.com/NousResearch/hermes-agent) for the agent/runtime substrate and [GitHub Spec Kit](https://github.com/github/spec-kit) for the specification method. Aether owns the three-role contract, portable profile/policy resources, project/release management, and reliability qualification; it does not replace Hermes's board, worker lifecycle, worktrees, retries, review, or tools.

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

## Escalation is proportional

Aether no longer treats every unspecified technical detail as a coordination event.

**Tier 0 — Implementer decides.** A reversible technical choice stays with Implementer when it preserves scope, acceptance criteria, shared interfaces, sibling independence, and authority. Naming, internal organization, equivalent implementation approaches, local test arrangement, and similar details do not create decision-card ceremony.

**Tier 1 — Supervisor decides a material shared question.** When a choice affects shared execution and the canonical contract settles it, the verified decision-card/dependency pattern remains available: the unit waits, Supervisor answers durably, and the unit resumes without waking the owner.

**Tier 2 — product intent is genuinely missing.** If the material answer is not derivable from the contract, it returns through Morfeo to the owner. Unrelated units continue.

The separation rule is: **local implementation judgement stays local; shared contract judgement belongs to Supervisor; genuinely missing product intent belongs to the owner.**

## Where Hermes ends and Aether begins

| Hermes owns | Aether owns |
|---|---|
| Conversation loop, tools, terminal backends | Which roles exist and what each is for |
| The durable board, dispatcher, retries, reclaim | Which Spec Kit phase each role performs |
| Worktrees, attempt history, audit trail | The contract and what makes it complete |
| Convergence judging, steering, hook dispatcher | Role responsibilities, contracts, review rules, and the small edge-effect policy |
| Profiles, memory, skills, scheduling | Quality standards and evidence expectations |

Aether reuses Hermes first and carries a documented transitional downstream only while indispensable runtime defects remain. Role behavior lives primarily in contracts, prompts, worktree isolation, tests and review. The versioned pre-tool hook is deliberately narrow: it protects secrets/credentials, credential widening, unauthorized remote/external mutation, and clearly destructive irreversible effects; it does not try to encode the role chart or interpret ordinary local work.

## The method

Aether does not invent a software process. It distributes Spec Kit's across three roles and resolves every point where upstream would stop and ask a human:

| Phase | Owner |
|---|---|
| `constitution` | Owner decides, Morfeo drafts |
| `specify`, `clarify`, `plan` | Morfeo |
| `tasks`, `analyze`, `checklist`, `converge` | Supervisor |
| `implement` | Implementers |

Spec Kit remains the canonical project specification method. For a pipeline objective, Morfeo additionally finalizes one small Aether **Objective Contract** that binds the owner-approved outcome, scope, authority, acceptance, testing and stop conditions to the relevant Spec Kit/project artifacts; it references those artifacts rather than duplicating them. Supervisor owns decomposition and `tasks.md`.

## Status

**Aether is in operational reliability stabilization under PD-71 through PD-74.** Repeated end-to-end failures and guard false positives reopened R7, R8, R10 and R13 on 2026-08-26. Feature expansion, Hermes upgrades, nonessential downstream patches, observation expansion and release qualification are frozen until the reliability gate passes.

The stabilization work has four priorities:

1. keep local/reversible work permissive and move safety to worktrees, Git, tests, review and rollback;
2. reduce the pre-tool hook to the irreversible/external edge;
3. make Morfeo recovery rollback-first and bounded instead of an invitation to redesign Aether;
4. prove behavior through a disposable E2E harness that starts with an owner message and measures the real Morfeo → Supervisor → Implementer → review → integration path.

Historical EC1/live evidence remains useful evidence in [`R13 research`](specs/r13-synthesis-and-release/research.md), but it no longer substitutes for the new rolling reliability gate. A paid/provider-backed real matrix still requires its explicit credential/spend authority; deterministic harness and policy qualification do not grant it.

### Implemented product surface

The current `0.24.0` package is a **beta stabilization build, not a release candidate**. Its implemented public surface is:

- the `aether` CLI for `--version`, `observe`, `doctor`, verified local `setup`/`update`, `rollback`, and `uninstall`;
- the Contract Observer and Objective Contract Hermes plugins;
- the portable Morfeo, Supervisor, and Implementer profile bundle;
- release-lock validation, isolated manager/runtime staging, and deterministic qualification.

The operational `init`, `start`, `stop`, `restart`, `status`, and `reconcile` commands remain explicit unsupported placeholders until the immutable runtime set and activation semantics are completed. Public OIDC release publication and the owner-authorized live reliability matrix are also pending. The CLI returns an unsupported/error result rather than pretending those effects occurred.

Non-destructive candidate inspection:

```bash
aether --version
aether observe --help
aether doctor --json
```

`doctor` may return a non-zero readiness result in a clean environment with no installed release; that is the expected truthful response, not a failed installation attempt.

## Canonical Morfeo TUI activation

The versioned launcher is the supported entry point for a local Morfeo TUI:

```bash
python3 scripts/aether_tui.py --check
python3 scripts/aether_tui.py
```

`--check` performs no model or network call. It fails visibly unless the repository-local Morfeo profile, Hermes executable, `SOUL.md`, and the `file` and `kanban` toolsets are present. A real launch clears inherited Python path overrides, sets `HERMES_HOME` to Morfeo, and starts Hermes with `--tui --in <repository>`, so profile and working directory do not depend on the caller's shell or previous session.

A short user-local `aether` command may delegate to this versioned script. The wrapper itself remains local because machine paths and profile state are not repository artifacts.

On 2026-08-20, amended PD-44 and PD-45 were mechanically delivered to the stopped local profiles. Morfeo now has the accepted proportional direct-execution surface with CLI/Telegram parity; Supervisor and Implementer retain their separate authority. Christopher accepted the active direct-execution experience as sufficient functional validation for #196 and closed that issue. That same standard led him to separately close the Phase 6 qualification gate the same day, rather than have it re-run against the EC1 evidence — see above. Neither closure closes the remaining runtime/debt issues.

## For whoever implements this

Read in this order: this file, then [`DESIGN.md`](DESIGN.md) for the accepted product decisions, then [`ROADMAP.md`](ROADMAP.md) as the index of design areas, then the specification of the area you are about to build. [`AGENTS.md`](AGENTS.md) states the working method and is not optional — in particular, the rule that upstream is read before anything is designed, and that a capability claim must cite the tree the runtime actually loads.

Current implementation order during stabilization:

1. Keep `DESIGN.md`, R7/R8/R10/A1/R13 and the three portable role identities aligned on PD-71 through PD-74.
2. Install and qualify the minimal edge hook in isolated profile homes; never patch the live hook in place to chase a false positive.
3. Build the disposable E2E canary and fixtures without adding a daemon, database, dashboard or mandatory evaluator model.
4. Run deterministic positive/negative policy and harness tests after each infrastructure change.
5. Once the existing credential/spend gate is explicitly opened, run the real model-backed canary and rolling reliability matrix.
6. Resume A1 feature/release work only after the reliability gate passes.

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
4. **Do not re-concentrate product responsibility.** Morfeo recovery and Supervisor integration glue are bounded exceptions for restoring/combining work, not permission to absorb feature implementation. Judge role separation by who owns product decisions and deliverables, not by forbidding every local tool action.
5. **Do not build what the runtime already provides.** No queue, no state machine, no retry, no reclaim, no audit trail.
6. **Design and build are separate authorities.** Accepting a design authorises nothing to run.

## License

MIT — see [LICENSE](LICENSE).
