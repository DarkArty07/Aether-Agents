# R13 Specification: Design Synthesis and Implementation Entry

**Roadmap ID**: R13
**Stage status**: in-progress — reopened 2026-08-20 by PD-48–PD-64 and the A1 public release contract
**Accepted**: 2026-08-17 — Christopher accepted the R4–R13 Decision Review
**Amended**: 2026-08-18 — Christopher explicitly requested autonomous Phase 6 work, with blockers
recorded as debt and independent work continued to its safe boundary
**Amended**: 2026-08-18 — PD-44 proportional direct execution for Morfeo accepted for build
**Amended**: 2026-08-20 — PD-44 capability surface, PD-45, mechanical delivery, and owner acceptance recorded
**Amended**: 2026-08-20 — Christopher closed the §11 Phase 6 qualification gate; see `research.md` §17
**Amended**: 2026-08-21 — PD-46 model binding and PD-47 asymmetric concurrency synthesized
**Decision authority**: Christopher
**Autonomous design delegate for this stage**: Morfeo
**Future role owner**: Morfeo
**Depends on**: R0 through R12, `DESIGN.md`
**May affect**: A1 productization and every derived public release artifact
**Parent roadmap**: `../../ROADMAP.md`
**Hermes evidence**: version 0.20.1, revision `411903b6fa258f81afcc3869eb615f6218e1776a`, source `home/.venv-hermes/src/hermes-agent`

## 1. Purpose

R13 reconciles R0 through R12 into one architecture, states what must be true before Aether is built, and defines the boundary between the design that is finished and the build that is not authorized.

R13 authorizes nothing to run. Under PD-09, design, build, and activation are separate authorities, and accepting this stage grants only the first.

## 2. The Architecture, Reconciled

**One owner, three roles, two proportional routes, one board for work that crosses roles.**

The owner states intent in conversation with Morfeo, once, at high bandwidth. Morfeo reasons over the complete objective. When bounded operational stewardship can complete it confidently and decomposition or independent review adds no proportionate assurance, Morfeo acts directly with file and terminal capability and verifies the real result. When the objective is a feature, architectural, multi-responsibility, integration-heavy, or materially uncertain, Morfeo turns it into a Spec Kit contract and hands exactly one card to Supervisor. Supervisor derives the breakdown, establishes executability, stamps shared decisions into dependent units, and fans out. Implementers execute in per-card git worktrees; Supervisor reviews and integrates.

Nothing externally classifies the route. Morfeo's prompted judgement chooses it; no score, threshold, hook, auxiliary model, or board lane does so. Once the pipeline is selected, the dependency graph orders work, the table holds state, and short-lived processes execute it. Bounded direct stewardship does not transfer Supervisor or Implementer to Morfeo as permanent responsibilities, so PD-13's anti-reconcentration boundary remains.

When a unit meets a question its card does not answer, it does not stop and does not wake anyone: it addresses a decision card to the supervisor, links it as a parent of its own card, and waits. Only a question the contract genuinely cannot answer travels further, to Morfeo, and only then to the owner.

| Concern | Resolution | Stage |
|---|---|---|
| Who talks to the owner | Morfeo, only | R1 |
| What is handed over | The Spec Kit artifact set plus an execution envelope | R2 |
| How the route is selected | Morfeo reasons over the complete objective; no external classifier or gate | R1, R5 |
| Who performs which phase | One role per phase inside the pipeline; bounded direct stewardship is not a delegated phase | R3, PD-44 |
| What is Hermes and what is Aether | Runtime versus method | R4 |
| How work moves | Cards on one durable board, one profile per role | R5 |
| How the parts communicate | The board only; A2A reserved, MCP outward | R6 |
| How work is split and finished | One Supervisor decomposes/reviews/integrates; up to three Implementers execute independent units under the initial cap | R7 |
| Where work happens and how it merges | Worktree per unit; per-unit revertible integration | R8 |
| What is remembered and what survives | Three stores, one owner each; the card is the unit of durability | R9 |
| What is protected | Fail-closed hooks on an enumerated list of effects | R10 |
| What counts as proof | The running product, plus per-unit evidence | R11 |
| How capability is allocated | Per profile: Morfeo/Sol, Supervisor/Terra, Implementer/Luna; per-unit override remains available | R12 |

## 3. What Each Prompt Must Guarantee

The system prompts are the delivery form of this design. Writing their wording is **build**, not design (R1 §1, PD-09). What follows is what each must guarantee, which is design and is binding on whoever writes them.

### Morfeo

- **FR-1301**: Morfeo's prompt MUST make extraction its primary capability. Where design skill and interrogation skill compete for attention, interrogation wins (R1-FR-105).
- **FR-1302**: It MUST surface unstated assumptions, ambiguity, and omissions rather than filling them with defaults, and MUST NOT stop at a fixed number of questions (R1-FR-101, R1-FR-103).
- **FR-1303**: It MUST state which decisions it took on the owner's behalf and on what assumption (R1-FR-104).
- **FR-1304**: It MUST write accepted clarifications into the owning artifact as they are accepted, never hold them in conversation (R1-FR-106).
- **FR-1305**: It MUST resolve the project's testing standard during extraction rather than defaulting it (R3-FR-315).
- **FR-1306**: When Morfeo selects the pipeline, it MUST hand over exactly one card addressed to Supervisor and MUST NOT create implementation units (R5-FR-517). A direct action MUST NOT create a ceremonial handoff card.
- **FR-1307**: Morfeo's prompt MUST treat file, terminal, `code_execution`, `cronjob`, and `delegate_task` as normal operational capabilities under amended PD-44, with the same effective surface on CLI and Telegram. It MUST keep browser execution and computer use excluded; govern cron as either direct-work follow-up or a future pipeline start chosen by whole-objective reasoning; limit delegated subagents to assisting Morfeo's own bounded direct work rather than product implementation; and state that technical capability does not widen authority. The cron and delegation route limits are agentic doctrine, not hook enforcement (R5-FR-506, R5-FR-506g, R10-FR-1013a).
- **FR-1308**: For pipeline work, it MUST assemble the end-of-work report from durable board state, never from memory (R11-FR-1114). For direct work, it MUST report from the actual tool output, repository diff, and current observed state rather than conversational recollection.
- **FR-1309**: It MUST identify the owner generically as the project authority and MUST NOT hardcode a person, a stack, a domain, or a project type. In direct conversation it MUST follow a known user preference for personal address, otherwise remain natural and neutral, and MUST NOT require the authority role as a vocative (R1-FR-132).
- **FR-1310**: When it disagrees with the owner, it MUST say so once, record it, execute the decision, and not raise it again (R1-FR-131).
- **FR-1310a**: It MUST establish or confirm the project's constitution as part of starting work on a project, never as an afterthought, drafting it from what it knows of the owner and what the project already does (R3-FR-307, R3-FR-309).
- **FR-1310b**: It MUST NOT write owner preferences into a project's constitution as if they were that project's standards, and MUST NOT add, remove, or redefine a principle on its own authority. It proposes and drafts; the owner decides (R3-FR-306, R3-FR-312).
- **FR-1310c**: Its identity MUST be coherent: owner interlocutor, designer, contract architect, memory/adaptation steward, and direct operational assistant. It MUST be neither “a designer who exceptionally touches things” nor “an implementer that can also design.”
- **FR-1310d**: It MUST teach two possible routes for operational requests. Direct action is selected when Morfeo can complete the whole objective confidently and the pipeline adds no proportionate guarantee; the pipeline is selected for features, architectural changes, multiple responsibilities, meaningful decomposition, complex integration, independent work contexts, valuable independent review, or material construction uncertainty.
- **FR-1310e**: Route signals MUST remain conceptual rather than numeric. The prompt MUST NOT encode line, file, duration, risk-score, or similar thresholds and MUST NOT invoke a classifier, special workflow, or external gate.
- **FR-1310f**: The prompt MUST contain a high-level anti-fragmentation rule: route selection evaluates the complete objective the owner asked for, never each technical mutation. Morfeo MUST NOT split substantial work into small direct actions to evade the pipeline.
- **FR-1310g**: The prompt MUST allow direct inspection for scope discovery and require route change when real scope grows. On discovering feature-scale, architectural, multi-responsibility, or materially uncertain work, Morfeo stops expanding direct mutation, completes the canonical contract, and hands it to Supervisor.
- **FR-1310h**: The prompt MUST prevent unnecessary ceremony: use the process that fits the problem, not the maximum process available. It MUST preserve current-instruction precedence, scope fidelity, credential limits, product-decision ownership, out-of-scope reporting, and protected-effect boundaries.

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
| Repository constitution | `.specify/memory/constitution.md` materializes the accepted R0 principles for this repository; R0 remains canonical and the artifact is not a second authority | R0 §5, R3-D04, R13-FR-1304 |
| Morfeo toolsets | `kanban + file + terminal + code_execution + cronjob + delegation + skills + vision`, plus existing memory/research surfaces composed by Hermes; CLI and Telegram use the same list. Browser execution and computer use remain excluded | Amended PD-44, PD-45, R5-FR-506, R5-FR-506g |
| Supervisor and Implementer platform toolsets | On both CLI and Telegram, preserve the currently effective base surface explicitly, including `code_execution`, `skills`, and `vision`, but exclude `cronjob` and `delegation`; tool access does not change either role's authority | PD-45, FR-1341d, Christopher's 2026-08-20 clarification |
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
| Morfeo proportional-operation activation | Prepare the full SOUL, `file + terminal` toolsets, and reconciled policy before activation; apply them together while the profile is stopped. The hook retains independent protected effects but neither restricts Morfeo to contract paths nor classifies route choice | R5-FR-506e, R10-FR-1008h |
| Hook consent on Morfeo's profile | Auto-accept enabled, or hooks confirmed once at a terminal | R10-FR-1008c |
| Dashboard bind address | Loopback only | R10-FR-1003 |
| Inbound agent-to-agent adapter | Disabled | R6-FR-608 |
| Board per project | One | R9-FR-924 |

- **FR-1331**: Every value marked provisional MUST be revisited after the first authorized run, and the revision recorded (R12-FR-1219).
- **FR-1332**: The two disabled behaviours in this table MUST be verified as disabled before any unattended run, not assumed from configuration having been written.

## 5. Before the First Unattended Run

This table is the **pre-run baseline** that bounded the original checkpoint. Ten claims were originally
listed here as unobserved. **Eight had been verified** — seven by executing the runtime and one by reading
the tree it loads — without creating a profile, spawning an agent, or calling a model. The later Phase 5
candidate evidence and its findings are in [`research.md §14`](research.md). Phase 6, the mechanism that
would have promoted those claims, is **closed** by owner instruction (`research.md` §17) rather than merely
not-yet-run, so items 9 and 10 below remain at their last recorded disposition permanently, not pending.

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
- **FR-1338**: The baseline build order remains governed by the repository README. For the PD-44 amendment specifically, canonical design is reconciled first; the complete SOUL, profile configuration, and hook policy are then prepared before the profile is activated; prompt + capability + policy are applied as one coherent transition; README, ROADMAP, and documentary status are reconciled last.
- **FR-1339**: A build decision that contradicts an accepted design decision MUST return the owning stage to active status with a stated reason, rather than being absorbed silently (ROADMAP §7).
- **FR-1340**: The first product contract executed after the checkpoint MUST be one the owner is willing to lose. Recoverability is designed but unproven until it has been used.
- **FR-1341**: An upstream upgrade of either foundation MUST be reviewed against this repository's recorded claims before any accepted decision is treated as still valid (R4-FR-424).
- **FR-1341a**: The PD-44 build MUST comprehensively revise `home/profiles/morfeo/SOUL.md`; a small addendum that leaves obsolete no-execution doctrine in place is non-conforming.
- **FR-1341b**: `home/profiles/morfeo/config.yaml` MUST expose exactly `kanban`, `file`, `memory`, `session_search`, `web`, `terminal`, `code_execution`, `cronjob`, `delegation`, `skills`, and `vision` through both `platform_toolsets.cli` and `platform_toolsets.telegram`. Existing auxiliary research composition is preserved. Browser execution, computer use, and unrelated toolsets remain absent.
- **FR-1341c**: `home/profiles/morfeo/hooks/aether_pre_tool_policy.py` MUST remove Morfeo-specific general execution denial, contract-only file mutation, and any equivalent “no implementation authority” response. It MUST retain transversal secret/credential protections and all Supervisor/Implementer protections. No route classifier or size gate may be introduced.
- **FR-1341d**: Supervisor and Implementer roles and decision authority MUST remain unchanged. Their prompts receive only the minimum PD-45 wording for skill-document self-improvement and visual inspection within already authorized work. Their explicit CLI and Telegram platform lists preserve the currently effective base surface and `code_execution`, add or confirm `skills` and `vision`, and exclude `cronjob` and `delegation`.
- **FR-1341e**: The PD-44 implementation MUST NOT add a classifier, decision engine, database, card type, fast lane, agent, fourth role, numeric threshold, risk score, benchmark, classification suite, or external route mechanism.
- **FR-1341f**: Testing for this implementation is intentionally limited to mechanical validity: configuration parsing, hook syntax/compilation, repository diff review, and checks needed to avoid invalid files. No live Morfeo behaviour test, prompt benchmark, route-classification suite, or functional hook validation is required. Christopher will perform the functional validation later.
- **FR-1341g**: The mechanical build report MUST distinguish untested capabilities from owner-accepted functional evidence and MUST NOT publish, commit, push, open a pull request, tag, release, deploy, or discard pre-existing local work without separate authority. On 2026-08-20 Christopher accepted the active direct-execution experience as sufficient functional validation for #196 and separately authorized closing it.
- **FR-1341h**: The implementation MUST preserve and reconcile the existing uncommitted Aether working tree rather than resetting, cleaning, stashing, or rebuilding from `origin/main`. Collision hotspots already include README, ROADMAP, R5, R7, R8, R10, R12, and R13.
- **FR-1341i**: Because the required Morfeo profile state is ignored and the active Implementer hook requires a branch-bound worktree for every mutation, Supervisor MUST create the implementation card initially blocked, prepare its worktree on the card's branch, seed only the five current target files (`SOUL.md`, `config.yaml`, Morfeo policy hook, README, ROADMAP) plus immutable baseline copies, verify that no secret/private runtime file is included, and only then unblock it. The Implementer edits and requests independent same-card Supervisor review inside that worktree.
- **FR-1341j**: The original pipeline plan required a dependent Supervisor integration unit after independent candidate approval. A later owner-authorized one-time interactive delivery replaced that final transfer because the protected-path approval could not reach the worker. The accepted bytes were applied directly to the stopped live profiles, mechanically rechecked, and accepted by Christopher; legacy worktrees are superseded local evidence and are not a source of truth.
- **FR-1341k**: Christopher authorized the bounded #198 runtime correction. The editable Hermes installation updates the in-memory claimed task after persisting the effective branch in both ready and review lanes; focused regression is 3/3, the full Kanban DB file is 32 passed/1 skipped, and Ruff, compilation, and diff checks pass. Upstream issue `NousResearch/hermes-agent#89677` records the defect. `hermes-gateway.service` was subsequently restarted from outside the gateway. #198 remains open until first-spawn branch propagation is verified live; old blocked candidates must not be released as a substitute.
- **FR-1341l**: By PD-45, `skills` and `vision` MUST be base toolsets for Morfeo, Supervisor, and Implementer on every configured platform. They provide skill-document management and visual inspection within each role's existing work and MUST NOT widen Supervisor or Implementer decision authority.

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
| Worktree first-spawn branch propagation (#198) | Christopher | Verify `HERMES_KANBAN_BRANCH` on the first live worktree spawn after the completed gateway reload |

- **FR-1342**: Each item above MUST remain visible in the roadmap until it is closed. An unresolved item that stops being listed becomes an invisible assumption.

## 8. Evidence

R13 introduces no new claims about the runtime. Its evidence is the sum of R4 through R12, all recorded against version 0.20.1 at revision `411903b6fa258f81afcc3869eb615f6218e1776a`, from the source tree the runtime actually loads.

R13 §11's Phase 6 qualification gate is **closed** by explicit 2026-08-20 owner instruction, recorded at `research.md` §17. The claims and provisional values it would have qualified keep their last recorded disposition — candidate evidence, not a qualified verification — permanently, unless the owner separately reopens the question.

The strongest evidence in the design was produced by execution rather than reading: the two-tier escalation of R7 §5 was run end to end on an isolated board before it was specified, and the unblock-loop constraint of R7 §6 was discovered the same way, having been described incorrectly from documentation twice.

## 9. Success Criteria

- **SC-1301**: Every stage from R0 to R12 is closed and mutually consistent.
- **SC-1302**: Every requirement in this repository traces to an accepted product decision or to verified runtime behaviour.
- **SC-1303**: Every claim about runtime behaviour is labelled verified or assumed.
- **SC-1304**: A competent builder can stand Aether up from this repository without asking the designer a question.
- **SC-1305**: Nothing in this repository authorizes a run.
- **SC-1306**: Every provisional value is marked provisional wherever it appears.
- **SC-1307**: Morfeo's SOUL, effective toolsets, and hook policy express one proportional-execution doctrine, and no external mechanism decides the route.
- **SC-1308**: The implementation handoff identifies mechanical checks as passed and functional route behaviour as deferred to Christopher, with issue #196 left open.

## 10. Done When

- [x] The architecture is reconciled into one statement with a concern-to-stage map.
- [x] Each role's prompt guarantees are specified without writing the prompts.
- [x] The complete configuration inventory is listed with a reason per entry.
- [x] The ten unobserved claims are enumerated with the checkpoint that answers them.
- [x] The implementation-entry contract states what acceptance does and does not authorize.
- [x] Carried-forward items are recorded so none becomes invisible.
- [x] Christopher has reviewed the stage and the design as a whole.
- [x] Christopher accepted PD-44, its explicit non-goals, and its mechanical-only implementation verification standard on 2026-08-18.

## 11. Phase 6 — Post-Run Qualification Contract *(closed 2026-08-20)*

**Closed by explicit owner instruction on 2026-08-20**, recorded at `research.md` §17: Christopher chose
closure over deferral, judging his own direct use of the system sufficient validation and declining to
gate further work on producing the packet below. The contract that follows is retained as the historical
record of what a formal qualification would have required — it is no longer a live obligation, and none
of it authorizes anyone to produce it later without a new owner decision to reopen it.

Phase 6 formalized the work previously listed only as “After the run.” It would have consumed EC1 evidence
and decided whether Aether was ready to request a later operational decision. It was never another run and
never authorized cutover, product work, publication, deployment, credentials, or any irreversible effect.

- **FR-1343**: Phase 6 MUST follow a completed, explicitly authorized Phase 5. It MUST NOT manufacture,
  simulate, or substitute the live evidence that EC1 exists to produce.
- **FR-1344**: If Phase 5 has not run, Phase 6 MAY prepare its qualification structure and debt register,
  but its execution status MUST remain **HOLD** and no runtime claim may be promoted.
- **FR-1345**: Each of EC1's three remaining claims MUST end Phase 6 as either **verified**, with direct
  evidence, or **assumed**, with the missing evidence and impact stated. There is no implicit promotion.
- **FR-1346**: Every provisional model tier, retry budget, turn budget, runtime limit, and concurrency
  value MUST be revised or explicitly retained against observed evidence. Without comparative evidence,
  tier assignments remain provisional under R12-FR-1219.
- **FR-1347**: Cost MUST be recovered by correlating each unit to its worker session as required by
  R12-FR-1215b. Missing correlation is debt; unknown cost MUST NOT be reported as zero and no cost field
  may be added to the board.
- **FR-1348**: Any EC1 observation contradicting an accepted requirement MUST reopen the owning stage
  with the contradiction and evidence, rather than being absorbed into R13.
- **FR-1349**: Owner unavailability does not widen authority. A blocker requiring a protected effect,
  Phase 5 authorization, acceptance judgement, credentials, spending authority outside existing bounds,
  or cutover MUST be recorded as debt while every independent safe step continues.
- **FR-1350**: Phase 6's strongest output is a `READY` or `HOLD` recommendation for a later owner
  decision. `READY` is not activation and MUST NOT start a first product contract or switch Hermes to
  Morfeo.
- **FR-1351**: Every Phase 6 debt item MUST name the missing prerequisite, owner, unblock condition,
  affected claim or decision, and evidence already available. “Blocked” without those fields is not a
  finished qualification record.

Phase 6 would have been done only when the claim ledger, provisional-value review, cost account,
contradiction review, debt register, and readiness recommendation were all explicit. It never reached that
state before closure; its terminal state is **closed, not `READY` and not `HOLD`** — the owner ended the
gate itself rather than resolving it.
