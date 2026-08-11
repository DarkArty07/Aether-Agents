# Aether Agents v0.24.0 Roadmap — Gradual Workflow Migration

> **Status:** PRESERVED PROPOSAL — INACTIVE; EXPLICIT OWNER DECISION REQUIRED
> **Date:** 2026-08-09; gate amended 2026-08-11
> **Product owner:** Christopher (DarkArty07)
> **Governing decision:** `../../decisions/PDR-0014-versioned-orca-production-adoption.md`
> **GitHub ledger:** https://github.com/DarkArty07/Aether-Agents/issues/168
> **Potential predecessor:** accepted v0.23.0 generic production operation

This document preserves a possible future direction. It is not an active
release roadmap, implementation plan, reserved next version, or authorization
to create a branch, migrate a workflow, activate a process, or retire a legacy
path. Christopher must explicitly decide whether and when v0.24.0 begins.

## 1. Product goal

Migrate Aether's process-specific workflows to Orca one at a time, using v0.23.0 production evidence to select order, define contracts, compare outcomes, repair gaps, activate each process, and prove rollback before retiring its legacy path.

v0.24.0 answers:

> Can Aether compose stable generic agents with explicit process contracts and migrate real workflows without creating duplicate authority, agent proliferation, or a big-bang cutover?

## 2. Entry gate

v0.24.0 does not begin merely because its roadmap exists or because v0.23.0 is
accepted or released. It requires:

- a new explicit product-owner decision opening v0.24.0;
- v0.23.0 generic Orca operation accepted and released;
- real-session incident and measurement evidence;
- an inventory of current process-specific workflows and consumers;
- one first process selected for demonstrated product value;
- exact baseline, Task contract, owner, inputs, outputs, tools, evidence, acceptance, activation, rollback, and retirement boundary;
- no unresolved v0.23.0 incident that invalidates the selected process foundation.

The process order intentionally remains unfrozen until this evidence exists and
the owner explicitly opens the version. Evidence is an input to that decision,
not implicit authorization.

## 3. Design rules

1. Stable archetypes remain generic: Hefesto, Daedalus, and Ictinus.
2. A process is a versioned contract/skill/task template, not a new personality.
3. One process migration has one accountable owner and one exact legacy baseline.
4. A Run or Task has one operational authority; no dual-write.
5. Shadow comparison may observe both paths only when neither performs conflicting effects and the authority is explicit.
6. Activation and source integration are separate gates.
7. Rollback is proved before legacy retirement.
8. Unmigrated behavior remains visibly legacy, direct, or unavailable; it never becomes a hidden fallback.
9. A migrated process must improve or preserve scope fidelity, correctness, product quality, continuity, verification, safety, time, and cost according to frozen priorities.
10. Process-specific evidence cannot silently broaden participant policy or reactivate retired roles.

## 4. Candidate process families

The following are candidates, not a frozen sequence:

- bounded implementation, bug fix, refactor, and TDD;
- product/UX discovery, prototype, rendered review, and implementation review;
- backend architecture, API/data contract, performance, and migration consultation;
- independent verification only if v0.23.0 admits a Verifier;
- continuity/handoff curation only if v0.23.0 admits Ariadna;
- release-candidate review, GitHub integration, release, and operational cutover last because their effects are more consequential.

Etalides is retired and no v0.24.0 workflow may depend on it. Research gaps are handled directly by Hermes or remain explicit until a separately approved replacement exists. Athena remains forbidden; security evidence is proportional and tool/evidence based, with any independent authority separately approved.

## 5. Preserved milestone proposal

Every milestone below is `NOT STARTED / BLOCKED ON EXPLICIT OWNER DECISION`.
Their presence preserves design work only.

### M0 — Inventory and choose the first migration

- inventory every process-specific path, consumer, trigger, authority, tool, state, evidence, failure mode, and legacy dependency;
- distinguish product process from runtime mechanics already owned by Orca;
- rank candidates by user value, frequency, incident burden, reversibility, and dependency risk;
- select one process and freeze its baseline before designing the Orca contract;
- record processes explicitly deferred or unavailable.

**Pass:** one migration target is selected from evidence and the inventory exposes every legacy consumer relevant to it.

### M1 — Freeze the reusable process contract pattern

Every process contract defines:

- trigger and product goal;
- user-visible acceptance and non-goals;
- direct-versus-swarm decision;
- admitted generic archetype(s) and participant policy;
- Task decomposition, dependencies, write scopes, and parallelism;
- exact inputs, tools, model/profile constraints, and data access;
- required artifact/evidence output;
- question, escalation, retry, timeout, cancel, close, and cleanup behavior;
- deterministic and real-path verification;
- activation, rollback, and retirement criteria;
- metrics and stop condition.

The pattern must compose Aether MCP and public Orca operations without reimplementing Runs, Tasks, workers, messages, worktrees, or cleanup.

**Pass:** the first process can be expressed without changing generic personality authority or creating a parallel coordinator.

### M2 — Migrate and activate the first process

For the selected process:

1. preserve the legacy/direct baseline;
2. implement the minimum Orca contract;
3. prove deterministic validation and policy failure paths;
4. execute one bounded real candidate;
5. compare against the frozen baseline;
6. repair integration and process defects through the v0.23 incident protocol;
7. rerun the affected case family;
8. accept and activate only this process;
9. execute rollback and return to the accepted target state;
10. retire only the proved legacy entry points for this process.

**Pass:** users can invoke the process through Aether, outcomes meet acceptance, rollback works, and no hidden legacy path remains for the migrated scope.

### M3 — Repeat per process without batch authority

Each additional process receives its own issue, contract, branch/candidate, evidence, activation, rollback, and retirement decision. Completion of one process does not authorize the next and does not waive its evidence.

Common contracts may be refactored only after at least two migrations demonstrate the same stable equivalence class. Avoid speculative workflow frameworks.

**Pass:** every activated process has independent traceability and unaffected processes remain stable.

### M4 — Retire legacy coordination only when consumers reach zero

- rebuild the live consumer inventory from source, config, tools, profiles, services, wrappers, imports, processes, and session paths;
- require zero required consumers, zero hidden fallback, and zero dual-write;
- freeze before-state and rollback sources;
- remove/disable legacy runtime only under separate activation authority;
- restart/recover and run representative migrated processes;
- prove project isolation, privacy, cleanup, and rollback;
- preserve historical evidence and protected data stores.

**Pass:** the accepted runtime has no active Olympus/ACP tool, import, process, service, registration, or fallback, and rollback is reproducible.

### M5 — Aggregate evaluation and v0.24.0 release

- compare every migrated process against its frozen baseline;
- evaluate aggregate quality, correctness, rework, latency, model/tool calls, cost, reliability, incident rate, recovery, cleanup, privacy, and complexity;
- reject or roll back processes that do not justify their operating cost;
- freeze exact source and installed-state claims separately;
- validate one exact candidate, obtain product-owner acceptance, integrate, tag, publish, and prove convergence;
- list every process still legacy, direct, deferred, or unavailable.

**Pass:** v0.24.0 publishes only the process migrations with evidence and no completion claim extends to deferred workflows.

## 6. Per-process acceptance template

| Dimension | Required evidence |
|---|---|
| Scope fidelity | Same user intent and explicit non-goals across baseline/candidate |
| Correctness | Focused regression plus real artifact/behavior verification |
| Product contribution | Role-specific value beyond generic startup or prose |
| Authority | One coordinator, immutable Task ownership, no participant escalation |
| Reliability | Retry/recovery/failure behavior and bounded incident handling |
| Integration | Real project outcome integrated and verified by Hermes |
| Cleanup | Zero owned survivors and no foreign-resource mutation |
| Privacy | Redacted evidence, project isolation, no secret/CoT persistence |
| Efficiency | Time, calls, cost, rework, and coordination overhead |
| Rollback | Exact before-state restored without losing project data/evidence |

Thresholds and case inputs are frozen before each candidate run. A process cannot modify its own evaluator or acceptance threshold.

## 7. Non-goals

- big-bang migration;
- one personality per process or technology;
- automatic process generation, activation, or promotion;
- reimplementation of Orca mechanics inside Aether;
- hidden legacy fallback;
- automatic dataset export, training, fine-tuning, or spending;
- claiming all workflows migrated because one representative process passed.

## 8. Completion definition

v0.24.0 is complete when:

1. each included process has its own accepted contract, evidence, activation, rollback, and legacy disposition;
2. generic personalities remain stable and process-independent;
3. aggregate evaluation justifies the included migrations;
4. every deferred process is named honestly;
5. any legacy runtime retirement has zero-consumer and rollback proof;
6. one exact source candidate and its separate installed-state claims are accepted and published.

A full learning-dataset or model-improvement release remains separately scoped
unless the product owner later places it explicitly inside v0.24.0. Completion
of v0.23.0 does not change this roadmap's inactive status.
