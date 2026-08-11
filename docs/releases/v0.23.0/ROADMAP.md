# Aether Agents v0.23.0 Roadmap — Orca Production Dogfood

> **Status:** IN PROGRESS — M1.2 ACTIVE; M1.3 NOT STARTED
> **Date:** 2026-08-09
> **Product owner:** Christopher (DarkArty07)
> **Governing decision:** `../../decisions/PDR-0014-versioned-orca-production-adoption.md`
> **Production policy:** `PRODUCTION_OPERATING_POLICY.md`
> **GitHub ledger:** https://github.com/DarkArty07/Aether-Agents/issues/167
> **Predecessor:** v0.22.0 Orca Integration Foundation

## 1. Product goal

Make Aether MCP + Orca the normal execution path for real Aether multi-agent work, qualify the retained generic roster, and improve the integration and personalities from observed production incidents and user corrections.

v0.23.0 answers:

> Can Aether use Orca repeatedly for real project work, fail visibly, repair the correct layer, retry through the same path, and remain understandable and reversible?

## 2. Meaning of production

Production is the named local Aether installation and the sessions Christopher uses for real projects. It is not a public hosted service, but it is not a fixture or demo:

- Tasks and repositories are real;
- workers use the approved model/provider routes;
- effects, failures, cost, latency, artifacts, cleanup, and rollback are reported honestly;
- a synthetic harness may reproduce an incident but cannot replace the required real-path retry;
- unavailable evidence remains `UNKNOWN` or `BLOCKED`, never PASS.

The named local v0.23.0 candidate is installed and active with the approved 15-tool Aether MCP surface, and Olympus is retired from that runtime. M1.3 and the M1.4 production-entry decision remain incomplete; production begins only after all of M1 below passes.

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

## 4. Entry prerequisites

- v0.22.0 is integrated and published, unless the product owner explicitly approves an exact frozen predecessor exception;
- the installed Aether/Hermes/Orca identity and rollback source are inventoried without revealing secrets;
- the first implementation Task freezes exact files, tests, effects, rollback, acceptance, and stop condition;
- offline/deterministic implementation is accepted before any live activation;
- runtime activation receives a separate explicit authorization.

This roadmap does not itself authorize source changes or activation.

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
`M1_3_TOOL_QUALIFICATION_CHECKPOINT.md`.

The first live pass invoked all 15 tools, closed its bounded Run with zero
survivors, and found one MCP facade defect: FastMCP coerced JSON-shaped string
arguments before protocol validation. Candidate `0542cdc` corrects that defect;
206 Aether MCP tests, Ruff and compileall pass, and a fresh installed process
discovers exactly 15 tools while preserving the string payload. The Hermes
session that predates installation still requires restart convergence. Fixture
dispatch is unavailable in the production binding, so this evidence is
`PARTIAL`, not the real-Task PASS required below.

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

Record exact source, model/profile/tool identities; liveness; timing; receipts; artifact verification; closure; cleanup; and unknowns without secrets.

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

**Pass:** incidents are visible and traceable, no task falls through silently, and accepted repairs have same-path retry evidence.

### M4 — Refine generic personalities from evidence

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

### M5 — Decide optional roles from production evidence

- compare Ariadna against Hermes-native memory, session history, skills, Curator, and versioned documentation;
- compare a proposed Independent Verifier contribution against deterministic verification and Hermes review;
- record `ADMIT`, `REJECT`, or `INSUFFICIENT` independently for each;
- if admitted, freeze a separate profile implementation and benchmark gate;
- if rejected, create no compatibility role or renamed substitute.

**Pass:** optional roles no longer survive as ambiguous future dependencies.

### M6 — Harden, measure, and prepare the exact v0.23.0 candidate

- stabilize setup/update/status/doctor/restart/cleanup/rollback;
- verify project and profile isolation;
- verify secret redaction and privacy-safe operational traces;
- compare representative direct and Orca-backed cases under frozen equivalent conditions;
- report quality, correctness, user rework, first-use latency, total latency, model/tool calls, reported cost, reliability, repair frequency, cleanup, and coordination overhead;
- preserve unavailable telemetry as `UNKNOWN`;
- permit bounded correction rounds without lowering frozen thresholds.

Minimum v0.23 trace contains structured context visible to the model, tool/Orca operations, artifacts, errors, corrections, retries, verification, outcome, timing, and identities needed for diagnosis. It does not include hidden chain-of-thought and does not automatically become training data.

**Pass:** the production path is observably usable, reversible, privacy-safe, and no worse than the accepted baseline on mandatory cases.

### M7 — Accept and publish v0.23.0

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
4. accepted personality refinements have baseline-relative evidence;
5. status, doctor, restart/rebind, cleanup, privacy, and rollback are verified;
6. representative controlled cases meet frozen acceptance thresholds;
7. one exact candidate is released and its installed activation state is recorded separately;
8. v0.24.0 receives evidence identifying the first process-specific migration candidate.

## 8. Stop condition and successor gate

Stop v0.23.0 scope expansion when the generic operating contract above is satisfied. Do not absorb broad process-specific migration or full dataset/training infrastructure merely because production sessions expose future opportunities.

v0.24.0 begins only after v0.23.0 acceptance and selects its first workflow from the observed evidence in `../v0.24.0/ROADMAP.md`.
