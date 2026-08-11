# Aether Agents v0.23.0 Roadmap — Orca Production Dogfood and MCP Optimization

> **Status:** IN PROGRESS — M1.2 PASS; M1.3 TOOL LEARNING ACTIVE
> **Date:** 2026-08-11
> **Product owner:** Christopher (DarkArty07)
> **Governing decision:** `../../decisions/PDR-0014-versioned-orca-production-adoption.md`
> **Production policy:** `PRODUCTION_OPERATING_POLICY.md`
> **GitHub ledger:** https://github.com/DarkArty07/Aether-Agents/issues/167
> **Predecessor:** v0.22.0 Orca Integration Foundation

## 1. Product goal

Make Aether MCP + Orca the normal execution path for real Aether multi-agent work, learn how Hermes uses the MCP under real conditions, reduce avoidable tool/context complexity, qualify the retained generic roster, and improve the integration and personalities from observed incidents and user corrections.

v0.23.0 answers:

> Can Aether use Orca repeatedly for real project work, select and sequence its MCP operations with proportionate context, fail visibly, repair the correct layer, retry through the same path, and remain understandable and reversible?

## 2. Meaning of production

Production is the named local Aether installation and the sessions Christopher uses for real projects. It is not a public hosted service, but it is not a fixture or demo:

- Tasks and repositories are real;
- workers use the approved model/provider routes;
- effects, failures, cost, latency, artifacts, cleanup, and rollback are reported honestly;
- a synthetic harness may reproduce an incident but cannot replace the required real-path retry;
- unavailable evidence remains `UNKNOWN` or `BLOCKED`, never PASS.

The named local v0.23.0 candidate is installed and active with the current 15-tool Aether MCP compatibility surface, and Olympus is retired from that runtime. M1.3 and the M1.4 production-entry decision remain incomplete; production begins only after all of M1 below passes. The tool surface may be improved inside v0.23.0, but no removal, hiding, rename, or replacement is accepted until a frozen comparison and explicit product-owner decision.

## 3. Invariants

1. Hermes owns user intent, task contracts, participant policy, product decisions, integration, acceptance synthesis, and protected-effect gates.
2. Aether MCP owns validation, admission, receipts, Aether semantic trace, idempotency, evidence, and policy enforcement.
3. Orca alone owns Runs, Tasks, Dispatches, workers, messages, terminals, worktrees, recovery, and cleanup mechanics.
4. A Run has one operational authority; no dual-write or mixed coordinator ownership.
5. Every real MCP tool returns real provider state or a typed failure; no placeholder success.
6. Every multi-agent Task after production entry uses Orca or stops as an explicit incident.
7. Direct Hermes work remains valid when one accountable owner is the deliberate product choice; it is not a fallback for a failed Orca Task.
8. Rollback restores control and evidence; it does not authorize silent continuation through Olympus.
9. Athena and Etalides are forbidden directly, indirectly, by alias, retry, recovery, peer proposal, or fallback.
10. Ariadna remains disabled and the Independent Verifier remains unimplemented until their evidence gates decide otherwise.
11. No worker may create another worker, change participant policy, redefine acceptance, or authorize protected effects.
12. No secret, private chain-of-thought, credential value, or foreign-project content may enter committed evidence.
13. Tool descriptions and progressive disclosure guide Hermes just in time; a large always-injected protocol manual is not the default solution.
14. Fewer visible tools are accepted only when measured evidence shows lower cognitive/context cost without hiding effects, weakening diagnostics, or moving authority.
15. The current 15-tool surface remains the compatibility baseline until a separate v0.23.0 tool-surface decision changes it.
16. v0.24.0 does not begin from schedule, roadmap existence, v0.23.0 acceptance, or v0.23.0 release alone; it requires an explicit product-owner decision.

## 4. Entry prerequisites

- v0.22.0 is integrated and published, unless the product owner explicitly approves an exact frozen predecessor exception;
- the installed Aether/Hermes/Orca identity and rollback source are inventoried without revealing secrets;
- the first implementation Task freezes exact files, tests, effects, rollback, acceptance, and stop condition;
- offline/deterministic implementation is accepted before any live activation;
- runtime activation receives a separate explicit authorization.

This roadmap does not itself authorize source changes, tool removal, runtime mutation, model use, activation, or transition to v0.24.0.

## 5. Milestones

### M0 — Establish the released predecessor and first Task contract

- close the v0.22.0 source release without adding capabilities;
- branch v0.23.0 from the exact released predecessor;
- freeze the operational entry Task against the approved 15-tool Aether MCP contract;
- inventory the named local installation, active MCP registrations, Orca build, profile root, processes, data roots, and rollback source;
- define a fail-fast deterministic gate before live mutation.

**Pass:** exact predecessor, exact candidate root, exact installation target, effects, tests, rollback, and stop condition are reproducible.

### M1 — Make Aether MCP + Orca operational and reversible

#### M1.1 — Real operational surface

Implement and register only real operations from the approved 15-tool contract:

```text
project_admit       project_inspect
swarm_validate      swarm_start
swarm_status        swarm_dispatch
swarm_message       swarm_reconcile
swarm_retry         swarm_cancel
swarm_close         swarm_trace
orca_search         orca_describe
orca_call
```

No arbitrary shell, placeholder, fabricated receipt, caller-selected authority, or private Orca store access is permitted. Worker profiles must not receive the coordinator control surface.

#### M1.2 — Setup, status, doctor, cleanup, and rollback

**Status:** PASS in the named active runtime. Canonical evidence:
`M1_2_ACCEPTANCE.md` and `M1_2_ACTIVE_RUNTIME_CUTOVER.md`.

- idempotent installation and registration;
- exact version/catalog/profile/model/toolset reporting;
- secret-safe diagnostics;
- no worker on registration alone;
- restart/rebind and stale-resource diagnosis;
- non-destructive rollback preserving diagnostic evidence and project data;
- proof that rollback leaves no stale MCP registration, worker, terminal, worktree, lease, listener, or process owned by the attempt.

#### M1.3 — First bounded production Task

**Status:** IN PROGRESS — fixture-first 15-tool qualification completed; the
model-backed Task remains pending. Canonical checkpoint:
`M1_3_TOOL_QUALIFICATION_CHECKPOINT.md`. The v0.23.0 learning and optimization
program is defined in `MCP_TOOL_SURFACE_LEARNING_PLAN.md`.

The first live pass invoked all 15 tools, closed its bounded Run with zero
survivors, and found one MCP facade defect: FastMCP coerced JSON-shaped string
arguments before protocol validation. Candidate `0542cdc` corrects that defect;
206 Aether MCP tests, Ruff and compileall pass, and a fresh installed process
discovers exactly 15 tools while preserving the string payload. The Hermes
session that predates installation still requires restart convergence. Fixture
dispatch is unavailable in the production binding, so this evidence is
`PARTIAL`, not the real-Task PASS required below.

M1.3 now proceeds through four explicit sub-gates:

1. **M1.3a — Fixture-first learning baseline: COMPLETE / PARTIAL EVIDENCE.**
   Invoke all 15 operations, preserve typed success/denial behavior, repair
   deterministic facade defects, and prove close/cleanup without model use.
2. **M1.3b — Cold-start guidance contract: DESIGN PASS / IMPLEMENTATION GATED.**
   `MCP_COLD_START_GUIDANCE_DESIGN.md` freezes the division between the isolated
   SOUL prompt candidate, concise catalog summaries, full tool/precondition
   descriptions, identity provenance, effect/model/cost warnings, typed
   state-dependent guidance, and repeated skill-independent cold-session
   evaluation. `MCP_COLD_START_IMPLEMENTATION_PLAN.md` and
   `MCP_COLD_START_HANDOFF.md` preserve execution and resume gates. The
   approximate five-tool intent surface remains a later candidate, not an
   approved contract.
3. **M1.3c — Compatible metadata correction: NOT AUTHORIZED.** After the design
   gate, improve the current 15-tool descriptions and schemas through RED/GREEN,
   isolated wheel/install discovery, and exact loaded-runtime convergence.
4. **M1.3d — Model-backed path: PENDING SEPARATE MODEL GATE.** Execute and verify
   the real `dispatch -> message -> retry -> artifact -> close` path under a
   frozen provider/account/model/budget contract.

Execute one low-risk, reversible, real repository Task through the installed path:

```text
Hermes
-> Aether MCP
-> Orca Run/Task/Dispatch
-> generic worker
-> artifact/evidence
-> Hermes verification
-> semantic close
-> cleanup
```

Record exact source, model/profile/tool identities; descriptions visible to
Hermes; liveness; timing; calls; avoidable invalid/precondition failures;
receipts; artifact verification; closure; cleanup; context/cost measurements;
and unknowns without secrets.

#### M1.4 — Production-entry decision

- if every deterministic and live gate passes, accept Orca as the normal multi-agent path;
- if any gate fails, preserve the incident, execute rollback, repair the owning layer, and rerun the same entry path;
- do not proceed to roster dogfooding while M1 is red.

**Pass:** one named installation performs a real reversible Task with status, restart/rebind, cleanup, and rollback evidence. From this point, `PRODUCTION_OPERATING_POLICY.md` is active for multi-agent work.

### M2 — Qualify the stable generic roster in production

#### M2.1 — Bind exact retained profiles

Freeze profile home, SOUL/config/template digest, model route, toolset, authority, input contract, output contract, retry, stop, and cleanup for:

- Hefesto — production implementation;
- Daedalus — product/UX design and implementation review;
- Ictinus — backend/data/architecture consultation.

#### M2.2 — Enforce participant policy

Prove `required`, `allowed`, `disabled`, and `forbidden` behavior at initial selection, retry, recovery, substitution, peer request, message, and proposed handoff boundaries.

Athena and Etalides must fail closed. Ariadna remains disabled. The Verifier remains unavailable.

#### M2.3 — Prove multiple instances and distinct contributions

- run two isolated instances of one archetype on independent Tasks;
- require unique Task/Dispatch/worker/worktree identities and the same immutable profile digest;
- exercise one representative real Task for each retained archetype;
- accept domain contribution, not mere startup or generic prose.

**Pass:** retained profiles are selectable and useful, forbidden profiles are unreachable, instances remain isolated, and cleanup is complete.

### M3 — Operate through Orca and repair integration incidents

After M1, use Orca for real multi-agent sessions instead of waiting for every future process contract.

For every incident:

1. preserve the original failure and user impact;
2. bound and clean only attempt-owned resources;
3. reproduce when safe;
4. classify the owning layer: Aether, adapter, Orca, environment, provider/account, or product contract;
5. create/update the v0.23.0 GitHub issue with redacted evidence;
6. add durable failing evidence or a reproducible diagnostic;
7. implement the smallest correction in the owning layer;
8. run focused and affected-path regressions;
9. retry the original Task through Orca;
10. record before/after outcome, residual risk, and cleanup.

Do not repeat the same failed repair approach more than three times. Stop honestly with an incident blocker when repair cannot be proved.

Tool-selection mistakes, missing preconditions, ambiguous IDs, excessive
always-visible context, non-actionable errors, misleading result semantics, and
loaded-versus-installed catalog drift are first-class Aether MCP integration
incidents when they cause wrong execution or user correction.

**Pass:** incidents are visible and traceable, no task falls through silently,
accepted repairs have same-path retry evidence, and durable tool-use learning is
stored in descriptions, schemas, tests, reference, trace, or the release plan as
appropriate.

### M4 — Optimize the Aether MCP tool surface from evidence

Follow `MCP_TOOL_SURFACE_LEARNING_PLAN.md`:

1. freeze a progressive context contract for catalog summaries, full tool and
   field descriptions, effects, preconditions, identity provenance, errors,
   reconciliation, retry, next-action guidance and an isolated mandatory SOUL
   boot contract — **complete as design; implementation not authorized**;
2. preregister equivalent cases, model/provider/account class, evaluator,
   thresholds, token/context measurement, timeout, cost ceiling, cleanup, and
   rollback before changing the surface;
3. implement and qualify the compatible 15-tool metadata candidate first;
4. complete repeated fixture and bounded real-path runs, including a model-backed
   artifact-producing Task under separate model authority;
5. only from that evidence, design any intent-level normal surface while
   preserving low-level diagnostics and one operational authority;
6. compare the baseline, enriched 15-tool candidate, and any separately approved
   intent-level candidate under equivalent initial conditions;
7. obtain an explicit product-owner disposition before removing, hiding,
   renaming, grouping, or deprecating any current operation.

Measure scope fidelity, correct tool selection, wrong-order calls,
`INVALID_INPUT` and precondition failures, calls/tokens/time to first useful
action, total latency/cost, user correction, hidden effects, recovery,
diagnostic sufficiency, and cleanup. Fewer tools or calls are not automatically
better.

Possible dispositions are `KEEP_15_ENRICHED`,
`ADOPT_INTENT_PLUS_DIAGNOSTIC`, `ADOPT_SELECTIVE_GROUPING`,
`INSUFFICIENT_CONTINUE_V0_23`, or `REJECT_AND_ROLL_BACK`.

**Pass:** the selected v0.23.0 surface has frozen comparative evidence, no
authority or diagnostic regression, exact installed/runtime convergence,
complete cleanup, rollback, and explicit product-owner acceptance.

### M5 — Refine generic personalities from evidence

For each personality change:

- preserve the observed behavior and exact Task context class;
- state a falsifiable behavioral hypothesis;
- freeze baseline and equivalent comparison conditions before editing;
- change the smallest relevant SOUL/profile/contract surface;
- compare scope fidelity, correctness, product contribution, user correction, time, cost, tool use, coordination overhead, and regressions;
- keep voice-only preferences separate from authority or routing changes;
- roll back changes that do not improve the metric vector.

Expected problem classes include overreach, passivity, weak evidence, tool misuse, poor escalation, role confusion, verbose handoff, premature completion, and failure to distinguish technical completion from product acceptance.

**Pass:** each accepted change has linked evidence and no material regression. Personality prose is not self-certifying.

### M6 — Decide optional roles from production evidence

- compare Ariadna against Hermes-native memory, session history, skills, Curator, and versioned documentation;
- compare a proposed Independent Verifier contribution against deterministic verification and Hermes review;
- record `ADMIT`, `REJECT`, or `INSUFFICIENT` independently for each;
- if admitted, freeze a separate profile implementation and benchmark gate;
- if rejected, create no compatibility role or renamed substitute.

**Pass:** optional roles no longer survive as ambiguous future dependencies.

### M7 — Harden, measure, and prepare the exact v0.23.0 candidate

- stabilize setup/update/status/doctor/restart/cleanup/rollback;
- verify project and profile isolation;
- verify secret redaction and privacy-safe operational traces;
- compare representative direct and Orca-backed cases under frozen equivalent conditions;
- report quality, correctness, user rework, first-use latency, total latency, model/tool calls, reported cost, reliability, repair frequency, cleanup, and coordination overhead;
- preserve unavailable telemetry as `UNKNOWN`;
- permit bounded correction rounds without lowering frozen thresholds.

Minimum v0.23 trace contains structured context visible to the model, tool/Orca operations, artifacts, errors, corrections, retries, verification, outcome, timing, and identities needed for diagnosis. It does not include hidden chain-of-thought and does not automatically become training data.

**Pass:** the production path is observably usable, reversible, privacy-safe, and no worse than the accepted baseline on mandatory cases.

### M8 — Accept and publish v0.23.0

- freeze exact scope and exclusions;
- reconcile version, changelog, docs, GitHub issues, incident dispositions, and rollback;
- validate one committed candidate in a clean isolated checkout;
- execute the named live acceptance and rollback evidence required by the release contract;
- obtain exact-candidate product-owner acceptance;
- merge, tag, publish, and prove remote convergence under source-release authority;
- preserve installed activation state separately from source publication state.

**Pass:** one exact v0.23.0 source Release and one explicitly accepted installed operating state are both identified without conflating them.

## 6. Non-goals

v0.23.0 does not include:

- migration of every process-specific workflow;
- beginning v0.24.0 workflow migration without a separate explicit owner decision;
- a new personality for every process or technology;
- full SFT/preference/routing dataset construction or export;
- training, fine-tuning, external upload, or model promotion;
- automatic self-modification or evaluator-controlled promotion;
- public hosting, multi-tenant service, or unbounded provider spend;
- hidden restoration of Olympus or ACP.

## 7. Completion definition

v0.23.0 is complete when:

1. Aether MCP + Orca is the normal real multi-agent path in the named installation;
2. retained generic profiles are qualified and forbidden profiles are unreachable;
3. real integration incidents follow repair-and-retry rather than fallback;
4. the Aether MCP tool surface has evidence-backed descriptions, progressive
   disclosure, recovery guidance, and an explicit accepted disposition;
5. accepted personality refinements have baseline-relative evidence;
6. status, doctor, restart/rebind, cleanup, privacy, and rollback are verified;
7. representative controlled cases meet frozen acceptance thresholds;
8. one exact candidate is released and its installed activation state is
   recorded separately;
9. remaining incidents and design alternatives are accepted, explicitly
   deferred inside v0.23.0 evidence, or honestly blocked.

## 8. Stop condition and successor gate

Stop unrelated v0.23.0 scope expansion when the generic operating and MCP
learning contract above is satisfied. Do not absorb process-specific migration
or full dataset/training infrastructure merely because production sessions
expose future opportunities.

v0.23.0 acceptance or release does not start v0.24.0. It may produce evidence
for a later discussion, but `../v0.24.0/ROADMAP.md` remains a preserved proposal
until the product owner explicitly decides whether and when to open that version.
