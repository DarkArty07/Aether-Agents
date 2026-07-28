# Aether SemVer Self-Improvement Cycle

> **Status:** IMPLEMENTED DEFAULT OFF; operational validation pending
> **Approved:** 2026-07-28
> **Governing decision:** `../decisions/PDR-0009-semver-self-improvement-cycle.md`
> **Active manifest:** `../releases/v0.20.0/CYCLE.yaml`

## Purpose

Every Hermes session that verifiably works inside Aether Agents participates in one active SemVer improvement cycle. The cycle uses real project work to evaluate Aether, preserves observable failures, permits direct Hermes framework repair under controlled takeover, verifies corrections, retries the intended path, and accumulates evidence for the next minor version.

The cycle wraps the user's task. It must not replace product intent, invent unrelated improvement work, or invoke a Daimon ceremonially.

## Current and target state

### Current verified state

- The latest official tag and GitHub Release are v0.18.2.
- The v0.19.x technical roadmap is closed at v0.19.5 with a `VIABLE — BOUNDED` verdict.
- v0.19.5 remains an unpublished technical candidate; merge, version reconciliation, tag, Release, and activation are separate gates.
- The active Hermes profile uses `custom:aether-router` with `gpt-5.6-sol`.
- `talk_to` is excluded from Hermes' Olympus tool registration.
- Harmonia remains available but is default-off; a valid admission currently fails closed with `feature_disabled` and no durable effect.
- Persistent Hermes memory contains the compact dogfooding policy.
- The `aether-self-improvement` plugin, strict manifest reader, project-local ledger, and deterministic evidence generator are implemented and tested but not enabled.

### Approved target

v0.20.0 bootstraps an automatic, measured, project-isolated improvement cycle. Source implementation is complete and default-off; activation, runtime restart, a live bounded pilot, merge, release, deployment, and publication remain separately gated. The implementation does not presume that Harmonia should become an LLM-backed agent.

## Session state machine

```text
SESSION_IDENTIFIED
  -> BASELINE_CAPTURED
  -> WORK_CONTRACTED
  -> EXECUTING
  -> MEASURING
  -> CLASSIFIED
  -> REPAIRING?           (framework defect only)
  -> VERIFYING
  -> RETRYING_INTENDED_PATH?
  -> EVIDENCE_RECORDED
  -> SESSION_FINALIZED
```

An interrupted process remains `INTERRUPTED` or `RECONCILIATION_REQUIRED`; it is never converted to complete merely because the conversational turn ended.

## Entry protocol

Before project work, the future deterministic hook and Hermes must establish:

1. the configured Aether root;
2. the resolved current project root;
3. the Git repository root;
4. the latest locally known official release and active candidate manifest;
5. the baseline commit and dirty-path inventory;
6. provider and requested model identity without secrets;
7. any unfinished prior improvement session requiring reconciliation;
8. the applicable user task and evidence level.

If project identity cannot be proven, the hook must not write Aether state. It injects an identity warning and leaves work direct and fail-closed.

## Work applicability

| Work | Normal path |
|---|---|
| Precise edit, documentation, configuration, focused diagnostic | Hermes direct |
| Work that materially benefits from an available Daimon | Harmonia |
| Framework defect discovered inside Aether | Reconcile, Hermes direct repair, verify, Harmonia retry |
| Contract defect | Correct the contract; do not rewrite the kernel by default |
| Worker defect | Correct or reject worker output; do not label it a framework defect |
| Intentional disabled/configuration state | Report the prerequisite; do not claim runtime failure |
| Work in another project | Hermes direct; never mutate Aether incidentally |

## Failure and takeover protocol

### Before admission

If no durable run or runtime session exists, direct work may begin after proving zero effect.

### After admission but before dispatch

Harmonia owns the run. Stop or terminate it semantically, reconcile durable state, and only then open a separate direct authority.

### After dispatch or unknown effect

```text
COORDINATOR_ACTIVE
-> TAKEOVER_REQUESTED
-> RECONCILING
-> CLEANUP_VERIFIED
-> HERMES_DIRECT
```

Before direct writes overlap the task scope, verify exact run/task/attempt/epoch state, resolve unknown dispatch outcome, request lifecycle-owner cleanup, prove no session/worker/lease/writer remains, and record terminal coordinator state.

## Repair protocol

A framework repair inside Aether follows:

```text
preserve reproducer and evidence
-> identify root cause and sibling paths
-> implement bounded correction
-> run focused and proportional regression evidence
-> retry the same intended path through Harmonia
-> compare before and after
```

A direct workaround without a Harmonia retry is not evidence that Aether improved.

## Measurement model

The cycle uses a metric vector, not one self-assigned score.

### Correctness

- focused, subsystem, and full-suite evidence as applicable;
- build, lint, type, schema, link, or runtime checks;
- semantic acceptance result;
- regressions and reverted changes.

### Coordination

- admission attempts and outcomes;
- dispatches and terminal outcomes;
- cleanup receipts and survivors;
- unknown effects;
- direct takeovers;
- hidden or visible legacy invocation count, which must remain zero.

### Efficiency

- wall time and time to first useful result;
- tool and model calls;
- retries and rework;
- input/output tokens, latency, and cost only when reported by the configured route.

### Process quality

- user corrections;
- requirement or scope drift;
- incomplete evidence caught before closure;
- repeated versus newly discovered defects;
- reusable skill corrections and durable decisions.

### Isolation and safety

- cross-project writes;
- concurrent coordinator/direct authority;
- surviving sessions, processes, leases, or writers;
- credentials or sensitive data in evidence;
- unauthorized external effects.

Unavailable metrics are recorded as `unknown`. They are not copied from another route, estimated from unrelated capacity, or converted to zero.

## Learning placement

| Learning | Canonical destination |
|---|---|
| User preference or correction | Hermes user profile or memory |
| Stable environment fact | Hermes memory |
| Reusable verified procedure | Hermes skill |
| Aether defect or interruption | GitHub issue plus `.aether` issue |
| Durable product or architecture decision | Versioned PDR/ADR plus `.aether` decision |
| Current session and measurements | Local improvement ledger |
| Release-level aggregate evidence | Versioned release evidence |
| Actual behavior | Source, tests, artifacts, and executed runtime evidence |

All Aether framework defects and interruptions follow the existing duplicate-check and GitHub issue policy. The ledger does not replace issue tracking.

## SemVer accumulation

Each active minor has one approved capability hypothesis. Sessions emit one closing signal:

- `NONE` — no version implication;
- `PATCH_CANDIDATE` — compatible correction candidate;
- `MINOR_CAPABILITY_SIGNAL` — possible new capability supported by evidence;
- `REQUIRES_MORE_EVIDENCE` — hypothesis remains unresolved.

Signals accumulate; they do not approve scope. At the minor closeout, Hermes synthesizes repeated evidence, rejected alternatives, unresolved risks, user value, compatibility, and cost. The product owner approves the next minor or chooses continued patches/maintenance.

No model-backed coordinator is a default destination. If deterministic coordination repeatedly fails on planning quality after runtime and contract defects are controlled, model-backed proposals may become one candidate hypothesis. They still require a separate decision.

## Aether Router boundary

`custom:aether-router` remains the compute substrate. Per session, record when available:

- logical provider;
- requested model;
- resolved route/model;
- latency;
- tokens;
- reported cost;
- provider or translation errors.

Never record credentials, tokens, account identifiers that expose private pools, or secret environment values. Router telemetry informs cost and reliability; it does not certify correctness or product acceptance.

## Persistence layers

1. **PDR-0009** — owner-approved authority and rationale.
2. **This document** — shared operating model.
3. **AGENTS.md and agent onboarding** — incoming-session discovery.
4. **CYCLE.yaml** — machine-readable candidate state.
5. **Hermes memory** — compact fallback fact.
6. **Default-off profile-scoped plugin** — deterministic session hooks.
7. **`.aether/self_improvement.db`** — project-local operational events and measurements.
8. **Release evidence** — validated aggregate facts.

`.aether/CONTEXT.md` is a projection and cannot be the sole source because curation can fail or drift.

## Implemented hook contract

The v0.20.0 plugin uses Hermes Agent hooks verified in source and official documentation. Project discovery is anchored to the nearest Git repository boundary; ambient process state cannot redirect a foreign workspace into Aether:

- `on_session_start` — initialize one session record;
- `pre_llm_call` — inject active cycle context into the first model turn;
- `post_tool_call` — record tool outcome and duration;
- `post_llm_call` — record model-turn metadata without self-certifying prose;
- `on_session_end` — record a turn outcome without treating it as conversation finalization;
- `on_session_finalize` — close the true conversation boundary;
- restart recovery — reconcile records left open by crashes or forced termination.

The implementation does not treat `on_session_end` alone as definitive finalization because its invocation semantics may include conversational-run boundaries.

## v0.20.0 acceptance summary

The default-off source candidate proves automatic single initialization, memory-independent context injection, SemVer manifest validation, `talk_to` exclusion in the versioned template, interruption recovery, concurrent-session preservation, Router telemetry without secrets, cross-project isolation, atomic Harmonia classification, evidence-derived version signals, and no predetermined next-minor architecture through deterministic tests. Live Harmonia use, safe takeover, repair/retry, causal before/after acceptance, and provider telemetry coverage remain operational gates after separately authorized activation.

Detailed machine-readable scope and gates are in `../releases/v0.20.0/CYCLE.yaml`.
