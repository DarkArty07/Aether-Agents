# Orca Production Adoption Plan

> **Status:** APPROVED CROSS-VERSION PLAN
> **Date:** 2026-08-09
> **Product owner:** Christopher (DarkArty07)
> **Current horizon:** Documentation and GitHub rebaseline only
> **Governing decision:** `../decisions/PDR-0014-versioned-orca-production-adoption.md`

## Goal

Close v0.22.0 at the accepted Orca integration boundary, enter real Orca-backed production work in v0.23.0, repair integration failures instead of bypassing them, and defer process-specific migration to evidence-driven v0.24.0 increments.

## Acceptance for this planning task

This documentation/GitHub task is complete when:

- v0.22.0 current roadmap ends at M5.4 and the former M0-M12 plan remains historical;
- v0.23.0 and v0.24.0 have separate canonical roadmaps, statuses, and GitHub milestones/issues;
- the repair-first/no-hidden-fallback production policy is explicit;
- Draft PR #163 describes the new release boundary;
- changed tracked paths are documentation only;
- links, YAML, Git diff, and secret scans pass;
- no source, tests, scripts, schemas, profile, SOUL, config, runtime, service, registration, credential, worker, model, spend, merge, tag, or Release effect occurs.

## Version sequence

```text
v0.22.0
Orca Integration Foundation
integration and model-backed qualification through M5.4
source release; no activation
        |
        v
v0.23.0
Orca Production Dogfood
real Aether MCP + Orca entry
stable generic roster
incident repair and same-path retry
personality refinement from evidence
        |
        v
v0.24.0
Gradual Workflow Migration
one process contract at a time
comparison, activation, rollback, legacy retirement
```

## Phase A — Rebaseline authority and GitHub

### Deliverables

- `docs/decisions/PDR-0014-versioned-orca-production-adoption.md`;
- `docs/releases/v0.22.0/ROADMAP.md`;
- `docs/releases/v0.22.0/STATUS.yaml`;
- `docs/releases/v0.22.0/RELEASE_BOUNDARY.md`;
- historical preservation of the former M0-M12 roadmap/status;
- `docs/releases/v0.23.0/ROADMAP.md`;
- `docs/releases/v0.23.0/STATUS.yaml`;
- `docs/releases/v0.23.0/PRODUCTION_OPERATING_POLICY.md`;
- `docs/releases/v0.24.0/ROADMAP.md`;
- `docs/releases/v0.24.0/STATUS.yaml`;
- canonical context/index/README reconciliation;
- GitHub milestones and ledgers #166, #167, and #168;
- updated Draft PR #163.

### Stop condition

Commit and push only the documentation rebaseline to the existing v0.22.0 Draft PR. Do not make the PR ready, merge, tag, publish, or activate.

## Phase B — Close and publish v0.22.0

### Goal

Publish one exact source tree containing the accepted integration foundation and documentary rebaseline without implementing v0.23.0 capabilities.

### Sequence

1. reconcile package/version/changelog/release identity;
2. scan the complete candidate range for scope and secrets;
3. validate the exact committed candidate in a detached clean worktree;
4. record final evidence and limitations;
5. obtain exact-candidate product-owner acceptance;
6. update/ready Draft PR #163;
7. preserve normal merge history;
8. verify integrated tree identity;
9. tag integrated `main` as `v0.22.0`;
10. publish/read back GitHub Release;
11. reconcile issue #166 and the v0.22.0 milestone.

### Gate

Source publication must state default-off, zero registered tools, no live activation, and the exact qualified Orca binding.

## Phase C — Freeze the first v0.23.0 production-entry Task

### Goal

Turn the accepted architecture into an executable, reversible Task contract without beginning implementation from an ambiguous roadmap.

### Required frozen manifest

- exact project root, predecessor commit, branch/worktree, and named installation;
- exact Aether MCP tool surface and public Orca operations;
- source/test/docs/config/profile path allowlists;
- active runtime and rollback before-state inventory;
- identity/idempotency chain;
- registration and coordinator-only visibility;
- deterministic RED and regression matrix;
- live E2E case, provider/model/account/budget authority;
- status/doctor/restart/cleanup/rollback gates;
- forbidden legacy/fallback scans;
- secret/privacy evidence;
- exact stop condition before broader roster work.

This is the next implementation-design gate after v0.22.0 publication. The current task does not create that source candidate.

## Phase D — Implement offline, then activate separately

1. implement the real operational surface and tests default-off;
2. validate the committed source candidate in isolation;
3. present exact operational effects and rollback;
4. obtain separate activation authority;
5. inventory the live installation again immediately before mutation;
6. register Aether MCP without starting a worker;
7. verify status/doctor and coordinator-only visibility;
8. execute one bounded real Task;
9. verify artifact, close, cleanup, restart/rebind, and rollback;
10. accept production entry or restore the baseline and open an incident.

Only after this phase passes does the production operating policy become active.

## Phase E — Use Orca for real work and repair it

For every subsequent real multi-agent Task:

```text
contract
-> Aether MCP + Orca
-> evidence and verification
-> close and cleanup
```

On failure:

```text
ORCA_INTEGRATION_INCIDENT
-> preserve
-> reproduce
-> classify
-> repair owning layer
-> verify
-> retry original Task through Orca
```

Hermes may repair the runtime directly in break-glass mode. Hermes must not finish the blocked multi-agent deliverable directly and count it as an Orca PASS.

Each material incident receives a GitHub issue or links to an existing equivalent. The issue records cause, evidence, correction, retry result, residual risk, and Release disposition without secrets.

## Phase F — Qualify and refine generic agents

- bind Hefesto, Daedalus, and Ictinus exactly;
- prove participant policy, isolation, distinct contribution, and cleanup;
- use real sessions to find overreach, passivity, evidence, tool, escalation, and completion defects;
- pre-register each behavioral hypothesis before changing a personality/contract;
- compare under equivalent conditions and roll back regressions;
- decide Ariadna and the proposed Verifier independently from evidence.

Do not encode process-specific workflows into stable personalities during this phase.

## Phase G — Harden, evaluate, and release v0.23.0

- make setup/update/status/doctor/recovery/rollback reliable;
- preserve minimum privacy-safe operational trace;
- freeze representative direct-versus-Orca cases;
- evaluate quality, correctness, user rework, latency, calls, cost, incidents, reliability, cleanup, and coordination overhead;
- close or explicitly defer every v0.23.0 incident;
- validate and publish one exact candidate;
- record source Release and installed activation as separate identities.

## Phase H — Begin v0.24.0 from evidence

1. inventory real process-specific workflows and consumers;
2. rank them from v0.23.0 use, failures, frequency, value, reversibility, and dependencies;
3. select exactly one process;
4. freeze baseline and process contract;
5. migrate, compare, repair, activate, and prove rollback;
6. retire only that process's legacy path;
7. repeat only after independent acceptance.

Legacy coordinator retirement is last and requires zero consumers, zero fallback, exact restart/recovery evidence, and rollback.

## Mapping from the former v0.22.0 roadmap

| Former item | New version |
|---|---|
| M6 roster | v0.23.0 |
| M7 traces/datasets | diagnostic trace in v0.23.0; full dataset program separately deferred |
| M8 optional roles | v0.23.0 |
| M9 productization | v0.23.0 operational entry; process packaging evolves in v0.24.0 |
| M10 evaluation | repeated per version |
| M11 source release | repeated per version |
| M12 activation | v0.23.0 entry plus v0.24.0 process cutovers |

## Gates that remain user-owned

- material product compromise or scope change;
- exact candidate acceptance;
- live registration/activation/restart;
- credentials, account changes, new model/provider, or spending;
- destructive migration or data removal;
- legacy runtime retirement;
- any exception to the no-hidden-fallback policy.

Routine documentation, deterministic verification, issue/PR maintenance, and source Git lifecycle follow repository policy and existing authority, but a failed gate is never waived silently.
