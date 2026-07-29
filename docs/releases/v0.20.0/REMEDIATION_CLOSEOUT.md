# v0.20.0 — Remediation Closeout

> **Status:** `REMEDIATION COMPLETE — SELF-IMPROVEMENT UNDEMONSTRATED`
> **Scope:** every finding raised by `EXTERNAL_LOGIC_AUDIT.md`, through Phases 1, 2 and 3.
> **Date:** 2026-07-28

---

## 1. The arc

| Stage | Result |
|---|---|
| External logic audit | `TELEMETRY BOOTSTRAP, NOT YET SELF-IMPROVEMENT` — 26 findings |
| Phase 1 correction (`EXTERNAL_CORRECTION_REPORT.md`) | 14 fixed, submitted as a candidate, **not** self-accepted |
| Independent Phase 1 review (`INDEPENDENT_PHASE1_REVIEW.md`) | **Rejected on first inspection** — IR-01, IR-02, IR-03 — then accepted for integration |
| v0.20.0 release | Merged (#128), tagged, published |
| Authorization truthfulness (#130) | The published contract no longer denies its own publication |
| Phase 2 (#130) | Before/after comparison that refuses when its preconditions fail |
| Phase 3 (this change) | Disposable candidates, structural rollback, promotion gate |

Two corrections were made to work this author had already reported as complete. The Phase 1 candidate claimed F-06 was closed when the explicit `project_root` vector was still open — a vector the audit itself had demonstrated. And F-23 was dismissed as a flaky test when it was a real defect in `dispatch.unknown` authentication. Both were caught by review, not by the author. That is the mechanism working as intended, and it is the reason none of this is self-accepted.

---

## 2. Final disposition

| ID | Status | Where |
|---|---|---|
| F-01 Harmonia classifier read fields the kernel never emits | **FIXED** | `7d8cb32` |
| F-02 failing payload recorded as success | **FIXED** | `7d8cb32` |
| F-03 global tool-call identity collapsed repeats | **FIXED** | `49128dd`, refined by `b2cabfa` (IR-02) |
| F-04 no evaluator, isolation, comparison or rollback | **FIXED** | `c56364e` (comparison), `6f68041` (isolation, rollback) |
| F-05 implementation and its tests changed together | **STRUCTURALLY ADDRESSED** | Evaluation digest makes a moved yardstick `INVALID`; the 26 original cases were never modified |
| F-06 cross-project ledger mutation | **FIXED** | baseline + `b2cabfa` (IR-01) |
| F-07 candidate version unbound | **FIXED** | `c03e771` |
| F-08 granting a gate deleted the cycle | **FIXED** | `1989837` |
| F-09 router telemetry unreachable | **DEFERRED — external** | Needs a change to Hermes Agent's `post_llm_call` payload. See §5. |
| F-10 failed and interrupted turns unmeasured | **FIXED** | `4a3a16b` |
| F-11 continued sessions recorded nothing | **FIXED** | `c03e771` |
| F-12 `_git_head` broken in linked worktrees | **FIXED** | `c03e771` |
| F-13 baseline ignored the dirty set | **FIXED** | `49128dd`, `c03e771` |
| F-14 one interrupted turn latched the session | **FIXED** | `49128dd`, `c03e771` |
| F-15 reused session id merged evidence | **FIXED** | `49128dd` |
| F-16 no schema versioning | **FIXED** | `49128dd` |
| F-17 template leaves no coordination path | **RETAINED BY OWNER** | `talk_to` deliberately removed; stated plainly rather than implied |
| F-18 no rollback | **FIXED** | `6f68041` |
| F-19 manifest never re-verified | **FIXED** | `c03e771` |
| F-20 documentation asserted unimplemented behaviour | **FIXED** | `ac2f263` |
| F-21 stale benchmark digest | **FIXED** | `ac2f263` |
| F-22 ledger directory world-readable | **FIXED** | `4a3a16b` |
| F-23 nondeterministic coordination test | **FIXED** | `a0852d8` (IR-03) — it was a real defect, not flakiness |
| F-24 evidence measured activity, not quality | **FIXED** | `6bb541b` (limits stated), `c56364e` (comparison exists) |
| F-25 PID reuse | **NOT A DEFECT** | Conservative by design; unchanged |
| F-26 `ensure_schema` on every operation | **FIXED** | `4a3a16b` |

**24 fixed · 1 structurally addressed · 1 deferred externally · 1 retained by owner · 1 not a defect.**

---

## 3. What the system can now do

1. Record a task, its acceptance criterion, its baseline commit and its dirty digest **before** the change that will be judged against them.
2. Freeze an evaluation set by content and refuse a comparison whose yardstick moved — `INVALID_EVALUATION_CHANGED`, never `IMPROVED`.
3. Refuse a comparison whose baseline worktree was dirty, because the change cannot be attributed.
4. Refuse a second measurement of the same phase, so re-running until the answer is favourable is impossible.
5. Derive a verdict from recorded facts alone, with no model judgement anywhere in the path.
6. Build a candidate in a throwaway worktree and discard it unconditionally, including when it raised mid-way.
7. Refuse to promote anything that is not a supported improvement approved by a named person, and refuse to restate a promotion afterwards.
8. Classify every Harmonia outcome against the kernel's real contract, and break the build if that contract is renamed.

## 4. What it still cannot claim

1. **That Aether has improved.** Every mechanism above is unexercised: no task has been recorded, no baseline measured, no candidate compared. A comparator with no comparison in it proves nothing.
2. **That any session participates.** The plugin remains absent from `plugins.enabled`; participation requires an operator to enable it.
3. **That efficiency is measured.** Turn coverage is now complete, but the fields remain NULL — see §5.
4. **That an installation has a general delegation path.** By owner decision.
5. **That the promotion gate cannot be opened by an automated caller.** It is procedural. It refuses unsupported evidence and names the approver; it does not prove the approver was human.

---

## 5. The one item that needs a decision

**F-09.** `agent/turn_finalizer.py` in Hermes Agent invokes `post_llm_call` with `session_id`, `task_id`, `turn_id`, `user_message`, `assistant_response`, `conversation_history`, `model` and `platform` — and nothing else. The route, resolved model, latency, tokens and cost all exist on the agent object at that moment and are simply not forwarded. Aether's hook already accepts them, so the fields would populate the moment the host supplies them.

Closing it means editing an installed third-party package, which diverges from upstream and is overwritten on update. The options are to upstream the payload extension, to carry a local patch knowingly, or to leave the dimension deferred and unclaimed. That is a product decision and is not made here.

---

## 6. Verification

Clean detached worktree at the final commit:

```
original self_improvement    26 passed
contract regressions         32 passed
causality contract           16 passed
promotion contract           10 passed
coordination                944 passed
full suite                 1228 passed
ruff check src/ tests/      All checks passed!
compileall src tests        OK
```

`tests/test_self_improvement.py` is byte-identical to its state at `48635b4`. Across Phases 1, 2 and 3, no pre-existing test was modified, removed or skipped; every correction had to satisfy the contract that existed before it.

---

## 7. Verdict

The remediation is complete. The instrumentation is truthful, the comparison machinery exists and refuses correctly, candidates are disposable and promotion is gated.

**None of that is self-improvement.** It is the apparatus that would let a self-improvement claim be made and checked. Whether Aether actually improves remains an open empirical question, and answering it requires the product owner to decide what task distribution matters and who judges that the requested outcome was obtained — the two questions the audit raised and that no code here has standing to answer.
