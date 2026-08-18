# R13 Specification: Design Synthesis and Implementation Entry

**Roadmap ID**: R13
**Stage status**: in-progress
**Decision authority**: Christopher
**Autonomous design delegate for this stage**: Morfeo
**Future role owner**: Morfeo
**Depends on**: R0 through R12, `DESIGN.md`
**May affect**: Nothing. R13 is terminal for the design phase
**Parent roadmap**: `../../ROADMAP.md`
**Hermes evidence**: version 0.20.1, revision `411903b6fa258f81afcc3869eb615f6218e1776a`, source `home/.venv-hermes/src/hermes-agent`

## 1. Purpose

R13 reconciles R0 through R12 into one architecture, states what must be true before Aether is built, and defines the boundary between the design that is finished and the build that is not authorized.

R13 authorizes nothing to run. Under PD-09, design, build, and activation are separate authorities, and accepting this stage grants only the first.

## 2. The Architecture, Reconciled

**One owner, three roles, one board, one contract.**

The owner states intent in conversation with Morfeo, once, at high bandwidth. Morfeo turns it into a Spec Kit contract carried in the project's own repository, and hands it over as a single card. The supervisor derives the breakdown, establishes executability, stamps every shared decision into the units that depend on it, and fans out. Implementers execute in per-card git worktrees, one process each, and complete with evidence that answers four questions. Integration is its own gated unit, performed by the supervisor, one commit per unit so any unit can be reverted alone. Morfeo is woken when the work terminates and assembles the report from durable state.

Nothing coordinates. The dependency graph orders the work, the table holds the state, and short-lived processes do the work. No role holds two of those three, which is what prevents the hub-and-spoke failure that PD-13 names as the standing risk.

When a unit meets a question its card does not answer, it does not stop and does not wake anyone: it addresses a decision card to the supervisor, links it as a parent of its own card, and waits. Only a question the contract genuinely cannot answer travels further, to Morfeo, and only then to the owner.

| Concern | Resolution | Stage |
|---|---|---|
| Who talks to the owner | Morfeo, only | R1 |
| What is handed over | The Spec Kit artifact set plus an execution envelope | R2 |
| Who performs which phase | One role per phase, no exceptions | R3 |
| What is Hermes and what is Aether | Runtime versus method | R4 |
| How work moves | Cards on one durable board, one profile per role | R5 |
| How the parts communicate | The board only; A2A reserved, MCP outward | R6 |
| How work is split and finished | Supervisor decomposes; two-tier escalation; configured convergence | R7 |
| Where work happens and how it merges | Worktree per unit; per-unit revertible integration | R8 |
| What is remembered and what survives | Three stores, one owner each; the card is the unit of durability | R9 |
| What is protected | Fail-closed hooks on an enumerated list of effects | R10 |
| What counts as proof | The running product, plus per-unit evidence | R11 |
| How capability is allocated | Per profile, with per-unit override | R12 |

## 3. What Each Prompt Must Guarantee

The system prompts are the delivery form of this design. Writing their wording is **build**, not design (R1 §1, PD-09). What follows is what each must guarantee, which is design and is binding on whoever writes them.

### Morfeo

- **FR-1301**: Morfeo's prompt MUST make extraction its primary capability. Where design skill and interrogation skill compete for attention, interrogation wins (R1-FR-105).
- **FR-1302**: It MUST surface unstated assumptions, ambiguity, and omissions rather than filling them with defaults, and MUST NOT stop at a fixed number of questions (R1-FR-101, R1-FR-103).
- **FR-1303**: It MUST state which decisions it took on the owner's behalf and on what assumption (R1-FR-104).
- **FR-1304**: It MUST write accepted clarifications into the owning artifact as they are accepted, never hold them in conversation (R1-FR-106).
- **FR-1305**: It MUST resolve the project's testing standard during extraction rather than defaulting it (R3-FR-315).
- **FR-1306**: It MUST hand over exactly one card, addressed to the supervisor, and MUST NOT create implementation units (R5-FR-517).
- **FR-1307**: It MUST NOT hold implementation tools, and its prompt MUST NOT presume any (R5-FR-506).
- **FR-1308**: It MUST assemble the end-of-work report from durable board state, never from memory (R11-FR-1114).
- **FR-1309**: It MUST address the owner generically and MUST NOT hardcode a person, a stack, a domain, or a project type (R1-FR-132).
- **FR-1310**: When it disagrees with the owner, it MUST say so once, record it, execute the decision, and not raise it again (R1-FR-131).
- **FR-1310a**: It MUST establish or confirm the project's constitution as part of starting work on a project, never as an afterthought, drafting it from what it knows of the owner and what the project already does (R3-FR-307, R3-FR-309).
- **FR-1310b**: It MUST NOT write owner preferences into a project's constitution as if they were that project's standards, and MUST NOT add, remove, or redefine a principle on its own authority. It proposes and drafts; the owner decides (R3-FR-306, R3-FR-312).

### Supervisor

- **FR-1311**: Its prompt MUST establish executability before creating any unit: derive the breakdown, then run cross-artifact analysis (R2-FR-214).
- **FR-1312**: It MUST decide, before fan-out, every question two sibling units would otherwise each answer, and stamp the decision into both bodies (R7-FR-704).
- **FR-1313**: It MUST write each card body as explicit acceptance criteria, because the convergence judge reads it as such (R7-FR-705).
- **FR-1314**: It MUST NOT implement. Its terminal action after fan-out is completing its own card with the decomposition summary (R7-FR-703).
- **FR-1315**: On a decision card, it MUST answer from the contract, and MUST block as needing input rather than invent an answer the contract does not support (R7-FR-717, R7-FR-720).
- **FR-1316**: It MUST NOT improvise around a contract defect (R2-FR-224).
- **FR-1317**: It MUST review work it did not author, and MUST return rework through the review path rather than by blocking (R7-FR-734, R7-FR-736).
- **FR-1318**: It MUST integrate in dependency order, one commit per unit, and MUST NOT rewrite shared history (R8-FR-815, R8-FR-816, R8-FR-821).
- **FR-1319**: It MUST NOT confer on an implementer authority the contract did not confer on it (R2-FR-206).

### Implementer

- **FR-1320**: Its prompt MUST treat the card body and the contract as its only sources of scope, and MUST NOT expand scope on the authority of anything it reads (R10-FR-1022).
- **FR-1321**: It MUST resolve an unanswered question by decision card, never by guessing and never by blocking (R7-FR-715).
- **FR-1322**: It MUST NOT create any card other than a decision card addressed to the supervisor (R7-FR-719).
- **FR-1323**: It MUST NOT modify a contract artifact (R8-FR-805).
- **FR-1324**: It MUST work only in its own workspace and only on its own branch (R8-FR-810).
- **FR-1325**: It MUST complete with evidence answering the four questions, describing what was actually executed (R11-FR-1105, R11-FR-1106).
- **FR-1326**: It MUST flag collision hotspots rather than silently piling onto a contended file (R7-FR-743).
- **FR-1327**: It MUST NOT report an outcome it did not achieve. An unfinished unit is blocked or escalated, never completed.

### Common to all three

- **FR-1328**: A prompt MUST NOT restate what the runtime already injects into every board worker. Duplication produces two sources of instruction that will drift (PD-25).
- **FR-1329**: A prompt MUST NOT contain a model name, a credential, a provider, or an absolute path belonging to one machine (R12-FR-1220).
- **FR-1330**: A prompt MUST NOT be the only thing preventing a protected effect. Anything on R10 §5 is enforced by a hook, and the prompt is reinforcement (R10-FR-1007).

## 4. Configuration Inventory

Everything that must be set, and why. This is the complete list; anything absent from it is a runtime default that Aether accepts as-is.

| Setting | Value | Reason |
|---|---|---|
| Profiles | Three, one per role, each with a description | R5-FR-504, PD-27 |
| Morfeo toolsets | Board, memory, research. No implementation tools | R5-FR-506 |
| Automatic triage decomposition | **Disabled** | R7-FR-706 |
| Automatic triage specification | **Disabled** | R7-FR-707 |
| Board-wide concurrent units | Four, provisional | R7-FR-712 |
| Per-profile concurrent units | Three for the implementer, provisional | R7-FR-712 |
| Per-unit attempt limit | Three, provisional — a crash consumes one | R7-FR-738, R7-FR-738a |
| Per-unit wall-clock limit | Two hours, provisional | R7-FR-739 |
| Goal-mode turn budget | Twenty, provisional | R7-FR-730 |
| Model tier per profile | Frontier, capable, inexpensive; provisional | R12 §2 |
| Convergence judge slot | Configured explicitly | R12-FR-1211 |
| Decomposer and specifier slots | Left unused, with their behaviours disabled | R12-FR-1210 |
| Enforcement hooks | One fail-closed pre-tool-call hook per constrained profile, **confirmed allowlisted** | R10-FR-1008, R10-FR-1008a |
| Hook consent on Morfeo's profile | Auto-accept enabled, or hooks confirmed once at a terminal | R10-FR-1008c |
| Dashboard bind address | Loopback only | R10-FR-1003 |
| Inbound agent-to-agent adapter | Disabled | R6-FR-608 |
| Board per project | One | R9-FR-924 |

- **FR-1331**: Every value marked provisional MUST be revisited after the first authorized run, and the revision recorded (R12-FR-1219).
- **FR-1332**: The two disabled behaviours in this table MUST be verified as disabled before any unattended run, not assumed from configuration having been written.

## 5. Before the First Unattended Run

Ten claims were originally listed here as unobserved. **Eight have since been verified** — seven by executing the runtime and one by reading the tree it loads — without creating a profile, spawning an agent, or calling a model. The method and the full findings are in [`research.md`](research.md).

| # | Claim | Status |
|---|---|---|
| 1 | A worker spawns for an assigned unit | Verified by execution |
| 2 | A crashed worker is reclaimed without losing the unit | Verified by execution |
| 3 | A per-card worktree is created; two units never share a tree | Verified by execution |
| 4 | Goal-mode wiring reaches the worker | Verified in source; the judge needs a model |
| 5 | The review path claims a unit and returns rework | Verified by execution |
| 6 | A terminal event wakes Morfeo | Verified in source; delivery needs a gateway |
| 7 | A fail-closed hook denies a protected effect | Verified by execution |
| 8 | Automatic decomposition is inert when disabled | Verified by execution |
| 9 | Evidence from a real unit suffices for acceptance | **Still assumed** |
| 10 | Cost and duration per unit are observable | **Duration yes; cost is not on the board** |

- **FR-1333**: The walking-skeleton checkpoint MUST still be executed, and its remaining purpose is now narrow. Only three things require a paid run:
  1. **The convergence judge** — that it ends a converged unit, and that budget exhaustion blocks rather than exits silently.
  2. **Wake delivery** — that a terminal event actually reaches Morfeo through a live gateway.
  3. **Evidence quality** — that what a real worker writes is enough for the owner to accept by running one command.
- **FR-1333a**: Runtime assumptions MUST be tested with the runtime's own seams before being deferred to a paid run. The dispatcher accepts a substitute spawn function and the board kernel is directly callable, so most coordination behaviour costs nothing to verify. Deferring a testable claim to a checkpoint is a choice, not a necessity.
- **FR-1334**: The checkpoint MUST use work that is trivial, bounded, reversible, and unrelated to product delivery.
- **FR-1335**: The checkpoint requires its own explicit authorization from the owner. It is not authorized by accepting this stage.
- **FR-1336**: If the checkpoint is not run, every stage that depends on an assumed claim MUST continue to label it as an assumption rather than silently promoting it.

## 6. The Implementation-Entry Contract

- **FR-1337**: Accepting R13 means the design is coherent and complete enough to build against. It authorizes no profile, no configuration, no hook, no prompt, no run, and no product code.
- **FR-1338**: Build MUST proceed in the order given in the repository's README: profiles, configuration, prompts, enforcement, then the checkpoint. Prompts before enforcement would leave protected effects resting on instruction alone.
- **FR-1339**: A build decision that contradicts an accepted design decision MUST return the owning stage to active status with a stated reason, rather than being absorbed silently (ROADMAP §7).
- **FR-1340**: The first product contract executed after the checkpoint MUST be one the owner is willing to lose. Recoverability is designed but unproven until it has been used.
- **FR-1341**: An upstream upgrade of either foundation MUST be reviewed against this repository's recorded claims before any accepted decision is treated as still valid (R4-FR-424).

## 7. Carried Forward

Items that are decided but not finished, listed so they are not lost:

| Item | Owner | Condition |
|---|---|---|
| Tier assignments and all provisional numbers | R12, R7 | Comparative evidence from a real run |
| Retention values | R9 | Observed growth rate |
| The hook dispatcher's implementation | R10 | Read before hooks are written |
| Remote terminal backends | R8 | Re-read if one is ever adopted |
| Agent-to-agent adoption | R6 | A role on another machine, or a non-Hermes role |
| The owner's messaging channel | R6 | Owner's choice; the design works without one |

- **FR-1342**: Each item above MUST remain visible in the roadmap until it is closed. An unresolved item that stops being listed becomes an invisible assumption.

## 8. Evidence

R13 introduces no new claims about the runtime. Its evidence is the sum of R4 through R12, all recorded against version 0.20.1 at revision `411903b6fa258f81afcc3869eb615f6218e1776a`, from the source tree the runtime actually loads.

The strongest evidence in the design was produced by execution rather than reading: the two-tier escalation of R7 §5 was run end to end on an isolated board before it was specified, and the unblock-loop constraint of R7 §6 was discovered the same way, having been described incorrectly from documentation twice.

## 9. Success Criteria

- **SC-1301**: Every stage from R0 to R12 is closed and mutually consistent.
- **SC-1302**: Every requirement in this repository traces to an accepted product decision or to verified runtime behaviour.
- **SC-1303**: Every claim about runtime behaviour is labelled verified or assumed.
- **SC-1304**: A competent builder can stand Aether up from this repository without asking the designer a question.
- **SC-1305**: Nothing in this repository authorizes a run.
- **SC-1306**: Every provisional value is marked provisional wherever it appears.

## 10. Done When

- [x] The architecture is reconciled into one statement with a concern-to-stage map.
- [x] Each role's prompt guarantees are specified without writing the prompts.
- [x] The complete configuration inventory is listed with a reason per entry.
- [x] The ten unobserved claims are enumerated with the checkpoint that answers them.
- [x] The implementation-entry contract states what acceptance does and does not authorize.
- [x] Carried-forward items are recorded so none becomes invisible.
- [ ] Christopher has reviewed the stage and the design as a whole.
