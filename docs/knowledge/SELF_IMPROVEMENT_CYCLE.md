# Aether SemVer Self-Improvement Instrumentation

> **Status:** v0.20 instrumentation preserved historically; executable bootstrap retired in v0.22
> **Approved:** 2026-07-28
> **Governing decision:** `../decisions/PDR-0009-semver-self-improvement-cycle.md`
> **Historical manifest:** `../releases/v0.20.0/CYCLE.yaml`

## Purpose

v0.20.0 introduced a default-off measurement substrate for a future SemVer self-improvement cycle. The v0.22.0 candidate retired its plugin, hooks, strict release-manifest reader, and manifest-bound evidence projector because they were coupled to the removed Harmonia/Olympus operating model. Historical reports remain authoritative for what v0.20 shipped.

The candidate preserves only schema-compatible ledger, deterministic comparison, isolated-candidate, and human-promotion primitives. They are inert: nothing initializes a session, injects model context, records tool/model calls, reads a cycle manifest, or projects release evidence automatically.

The approved target cycle wraps the user's task. It must not replace product intent, invent unrelated improvement work, invoke a Daimon ceremonially, or treat recorded activity as improvement.

## Current and target state

### Current verified state

- The latest official tag and GitHub Release are v0.20.0.
- The v0.19.x technical roadmap closed at v0.19.5 with a `VIABLE — BOUNDED` verdict and is integrated into v0.20.0 without separate public v0.19.x tags.
- The active Hermes profile uses `custom:aether-router` with `gpt-5.6-sol`.
- The v0.22.0 candidate contains no multi-agent execution runtime or Aether MCP facade.
- `talk_to`, `discover`, and ACP-backed curation are absent rather than disabled.
- Persistent Hermes memory contains the compact dogfooding policy.
- The `aether-self-improvement` plugin, strict manifest reader, session hooks, and deterministic evidence projector are absent.
- The project-local ledger, causality comparison, candidate isolation, and human-promotion primitives remain implemented and tested without an activation path.

### Approved target

The project-isolated measurement substrate remains independently reviewed and default-off. Activation, runtime restart, a live bounded pilot, causal evaluation, deployment, and production publication remain separately gated. It does not presume a coordinator or replacement runtime architecture.

## Session state machine

> **Status: operating model, not active runtime state.** The preserved ledger schema
> can represent `active`, `reconciliation_required`, and `finalized` sessions plus
> a per-turn outcome history, but no candidate hook writes those states.
> `WORK_CONTRACTED`, `CLASSIFIED`, `REPAIRING`,
> `VERIFYING` and `RETRYING_INTENDED_PATH` have no representation in code, no
> column and no transition. The sequence below describes how an agent should
> work; it is not a machine that enforces it. See `EXTERNAL_LOGIC_AUDIT.md` F-04.

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

Before any future instrumentation participates in project work, its accepted deterministic boundary and Hermes must establish:

1. the configured Aether root;
2. the resolved current project root;
3. the Git repository root;
4. the latest locally known official release and an approved current candidate contract;
5. the baseline commit and dirty-path inventory;
6. provider and requested model identity without secrets;
7. any unfinished prior improvement session requiring reconciliation;
8. the applicable user task and evidence level.

If project identity cannot be proven, a future instrumentation boundary must not write Aether state. The v0.22 candidate has no such executable boundary, so it performs no automatic identity check or write.

## Work applicability

| Work | Normal path |
|---|---|
| Precise edit, documentation, configuration, focused diagnostic | Hermes direct |
| Work that materially requires an unavailable specialist | Stop with an explicit capability gap |
| Framework defect discovered inside Aether | Preserve evidence, Hermes direct repair, verify, compare before and after |
| Contract defect | Correct the contract; do not rewrite the kernel by default |
| Worker defect | Correct or reject worker output; do not label it a framework defect |
| Intentional disabled/configuration state | Report the prerequisite; do not claim runtime failure |
| Work in another project | Hermes direct; never mutate Aether incidentally |

## Failure and takeover protocol

### Before admission

If no durable run or runtime session exists, direct work may begin after proving zero effect.

### After admission but before dispatch

If a future authorized runtime owns a durable run, stop or terminate it semantically, reconcile durable state, and only then open a separate direct authority. No such runtime exists in the current candidate.

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
-> retry the same intended path when that path still exists and is authorized
-> compare before and after
```

A direct workaround without retrying an available intended framework path is not evidence that Aether improved. When the legacy path has been deliberately retired, deterministic replacement acceptance—not compatibility retry—is required.

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
4. **Historical CYCLE.yaml files** — release evidence only; no active loader exists.
5. **Hermes memory** — compact fallback fact.
6. **Future accepted instrumentation boundary** — currently absent.
7. **`.aether/self_improvement.db`** — project-local operational events and measurements.
8. **Release evidence** — validated aggregate facts.

`.aether/CONTEXT.md` is a projection and cannot be the sole source because curation can fail or drift.

## Historical v0.20 hook contract

The retired v0.20.0 plugin used these Hermes Agent hooks. They remain documented only so historical evidence can be interpreted:

- `on_session_start` initialized one session record;
- `pre_llm_call` injected cycle context into the first model turn;
- `post_tool_call` recorded tool outcome and duration;
- `post_llm_call` recorded model-turn metadata without self-certifying prose;
- `on_session_end` recorded a turn outcome;
- `on_session_finalize` closed the conversation boundary;
- restart recovery reconciled records left open by crashes or forced termination.

No equivalent hooks are registered by the v0.22 candidate.

## v0.20.0 acceptance summary

The released v0.20.0 evidence proved project identity checks, lazy session initialization, SemVer manifest validation, interruption recovery, concurrent-session preservation, redacted storage, cross-project isolation, historical coordination classification, request-scoped tool-call identity, manifest-drift detection, and replay-safe internal unknown events. Its executable plugin, hooks, manifest reader, classifier, and evidence projector were removed in the v0.22.0 candidate. The remaining inert primitives do not prove automatic participation, provider telemetry coverage, safe takeover, framework repair/retry, evidence-derived version promotion, or causal before/after acceptance.

Detailed machine-readable scope and gates are in `../releases/v0.20.0/CYCLE.yaml`.
