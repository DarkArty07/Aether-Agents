# v0.20.0 — Independent Phase 1 Review

> **Status:** `PHASE 1 ACCEPTED — TRUTHFUL INSTRUMENTATION ONLY`
> **Reviewer:** Local Dev agent, independent from the external model that authored the audit and correction candidate
> **Reviewed candidate:** `89cba0e82d6273a722f6f9e83c0960af89f54590`
> **Independent correction commit:** `b2cabfa`
> **Date:** 2026-07-28

## Scope

This review evaluates only Phase 1 of `EXTERNAL_LOGIC_AUDIT.md`: make the default-off instrumentation report truthful facts. It does not evaluate or claim causal self-improvement. No evaluator, frozen task set, candidate worktree runner, before/after comparison, promotion decision or runtime rollback exists yet.

The original correction author was not permitted to accept their own work. This review re-read the real Hermes hook contract, replayed adversarial cases, inspected the committed diff, preserved the original 26-case contract, added independent regressions only where a residual claim failed, and reran focused, subsystem and repository gates.

## Initial result: blocked

The correction candidate at `89cba0e` was not accepted on first inspection. Two findings reported as fixed remained incomplete.

### IR-01 — F-06 explicit project-root redirection remained open

`hooks._project_root()` rejected `AETHER_PROJECT_ROOT` and stopped at the nearest `.git`, but still accepted an arbitrary `project_root` hook kwarg as authority. From a foreign repository, the following created Aether's ledger and wrote a session row:

```python
on_session_start(
    "foreign-explicit-project-root",
    model="gpt-5.6-sol",
    platform="cli",
    project_root=aether_root,
)
```

Reproduced result before correction:

```text
ledger_created=True
row_written=True
```

The real Hermes lifecycle hooks were inspected directly. `on_session_start`, `pre_llm_call`, `post_tool_call` and `post_llm_call` do not supply a trusted `project_root`; session identity is derived from the active process workspace. Therefore an explicit plugin kwarg cannot safely grant cross-repository authority.

**Correction:** the nearest Git repository discovered from `Path.cwd()` is authoritative. An explicit root may only confirm that same discovered root. A mismatch or absence of a discoverable Aether root is rejected and logged.

**Independent tests:**

- `test_explicit_project_root_cannot_redirect_a_foreign_repository`
- `test_explicit_project_root_may_confirm_the_discovered_aether_root`

### IR-02 — F-03 still collapsed identical calls within one turn

The candidate changed tool identity from global `tool_call_id` to:

```text
(session_id, turn_id, tool_call_id)
```

That fixes cross-session and cross-turn collisions, but Hermes may generate a deterministic tool ID from call content and a per-response index. The index resets on each model request. Two identical calls in separate model requests inside one turn can therefore share the same `session_id`, `turn_id` and `tool_call_id` and still collapse under `INSERT OR IGNORE`.

The existing new test covered only a later turn, not a later request in the same turn.

**Correction:** tool and coordination identity is now:

```text
(session_id, turn_id, api_request_id, tool_call_id)
```

Hermes already supplies `api_request_id` to `post_tool_call`. This preserves two genuine executions across requests while retaining idempotence when the exact same observer event is delivered twice.

The durable ledger schema was bumped from 2 to 3 and continues to fail loudly on incompatible files.

**Independent tests:**

- `test_same_deterministic_call_repeated_in_one_turn_is_counted_per_request`
- `test_duplicate_observer_delivery_remains_idempotent`

## Review of the original correction claims

After the independent corrections:

| Finding | Review result |
|---|---|
| F-01 real Harmonia contract classification | PASS — real public error codes and kernel states are imported and exercised |
| F-02 failing payloads reported as success | PASS — host status wins; fallback rejects known failure forms |
| F-03 repeated tool-call evidence | PASS after IR-02 — request-scoped identity closes the same-turn case |
| F-05 candidate/tests changed together | PARTIAL by design — original 26 tests remain byte-identical; structural immutable evaluator remains Phase 2 |
| F-06 cross-project ledger mutation | PASS after IR-01 — env, nested repository and explicit-root redirection are rejected |
| F-07 candidate version binding | PASS |
| F-08 authorization semantics | PARTIAL/DEFERRED — refusal remains intentional; failure is now operator-visible |
| F-09 router telemetry availability | HONESTLY DEFERRED — unreachable fields are no longer claimed |
| F-10 failed/interrupted model-call survivorship bias | DEFERRED with F-09 |
| F-11 continuation initialization | PASS |
| F-12 linked-worktree HEAD | PASS |
| F-13 dirty baseline attribution | PASS |
| F-14 interruption recovery | PASS |
| F-15 session-ID reuse | PASS |
| F-16 schema compatibility | PASS — schema v3 refuses incompatible files loudly |
| F-17 public coordination path | HONESTLY PARTIAL — no automatic participation or general delegation path is claimed |
| F-19 manifest drift | PASS |
| F-20/F-21 documentation and digest truth | PASS after reconciliation |
| F-24 activity volume versus quality | PARTIAL by design — evidence names its limits; causal quality remains Phase 2 |

No Phase 2 or Phase 3 mechanism was introduced by this review.

## Verification

The reviewed tree passed:

```text
Original self-improvement contract: 26 passed, unchanged
Audit and independent regressions: 28 passed
Combined self-improvement scope: 54 passed
Coordination subsystem: 943 passed
Full repository suite: 1197 passed
Ruff: PASS
compileall: PASS
release-governance policy: PASS
git diff --check: PASS
```

The repository-wide count includes the six new integration/release-governance tests that are part of the consolidated PR. The self-improvement delta itself adds 28 cases over the 26-case preserved contract.

## Accepted claims

Phase 1 may now claim that:

1. the observer is default-off and project-scoped to the active Aether repository;
2. an environment variable or arbitrary explicit root cannot redirect a foreign repository into Aether's ledger;
3. Harmonia outcomes are classified from the real public contract;
4. known tool failures are not recorded as success;
5. distinct repeated calls are preserved across sessions, turns and model requests;
6. exact duplicate observer delivery remains idempotent;
7. resumed sessions, linked worktrees, dirty baselines, turn interruptions, manifest drift and incompatible schemas are represented truthfully;
8. generated evidence explicitly refuses causal and release-approval claims it cannot support.

## Claims that remain invalid

This acceptance does not permit Aether to claim:

- that it improves itself;
- that activity counts demonstrate software quality;
- that every session participates automatically;
- that the current template provides a live specialist-coordination path;
- that framework-defect classification, safe takeover, repair verification or Harmonia retry are mechanically implemented;
- that a next-version signal is causally derived;
- that Phase 2 or Phase 3 is complete;
- that the plugin is ready for live activation or production deployment.

## Verdict

`PHASE 1 ACCEPTED — TRUTHFUL INSTRUMENTATION ONLY`

The source is acceptable for integration into `main` as default-off instrumentation. Integration does not authorize activation, runtime restart, deployment, tag or GitHub Release. A real self-improvement claim remains blocked on the independent evaluator and disposable-candidate work of Phases 2 and 3.
