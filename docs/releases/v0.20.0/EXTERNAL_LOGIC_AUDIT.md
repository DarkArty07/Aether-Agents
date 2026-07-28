# v0.20.0 — External Logic Audit

> **Auditor:** external, stateless, independent of Aether Agents. Not Hermes, not Harmonia, not a Daimon.
> **Method:** direct repository, source, test and runtime inspection. No Aether component was invoked, activated or asked to describe itself.
> **Date:** 2026-07-28
> **Audited working tree:** `/home/arty/Escritorio/agentes/aether`
> **Branch / HEAD:** `docs/canonical-product-documentation` @ `a88b5cc`
> **Second candidate copy:** `/home/arty/Escritorio/agentes/aether-v020-isolated` @ `48635b4` (`feature/v0.20.0-self-improvement-bootstrap`, clean)
> **Dirty baseline:** 131 `git status` entries (33 modified tracked, 98 untracked) present before this audit began and untouched by it.
> **Files created by this audit:** this file only.

---

## 1. Executive verdict

### `TELEMETRY BOOTSTRAP, NOT YET SELF-IMPROVEMENT`

v0.20.0 is a competent, fail-closed, privacy-respecting **session observer**. It is not a self-improvement machine, and in its current form it cannot become one by activation alone.

The audit question was:

> Can Aether v0.20.0 detect an improvement opportunity, establish a valid baseline, execute the intended path, distinguish the cause of a failure, repair only a framework defect, verify the correction, repeat the same path, demonstrate a causal improvement, and propose a SemVer signal without modifying the evaluation criterion or redefining success after observing the result?

Answer, step by step, from evidence:

| Required capability | Present? | Evidence |
|---|---|---|
| Detect an improvement opportunity | **No** | No code path detects, proposes or represents an opportunity. The behaviour exists only as nine sentences of prompt text (`hooks.py:173-185`). |
| Establish a valid baseline | **Partial** | `baseline_commit` only (`hooks.py:116`). The operating model requires "baseline commit **and dirty-path inventory**" (`SELF_IMPROVEMENT_CYCLE.md:57`). Measured impact of the missing dirty set: 1170 vs 1163 tests. |
| Execute the intended path | **Not measurable** | The template removes `talk_to`, Harmonia is default-off, and the plugin is not enabled. |
| Distinguish the cause of a failure | **No** | The four documented failure classes do not exist in code. The Harmonia classifier does not match Harmonia's real wire contract: 0 of 9 post-admission states and 3 of 13 error codes classify correctly (F-01). |
| Repair only a framework defect | **No** | Prompt text only. No classification, no gate, no scope enforcement. |
| Verify the correction | **No** | No verification step, no acceptance threshold, no comparison. |
| Repeat the same path | **Actively harmful** | Repeating an identical tool call is exactly the case the global `tool_call_id` primary key silently discards (F-03). |
| Demonstrate a causal improvement | **No** | `render_release_evidence` emits counts only (`evidence.py:36-71`). No task, no baseline run, no candidate run, no comparison, no rollback. |
| Propose a SemVer signal | **No** | The only production caller uses the default. The signal is a constant `REQUIRES_MORE_EVIDENCE` (F-04, probe 11). |
| Not change the criterion after seeing the result | **Already violated** | The implementation, its tests and the reported acceptance counts were changed together in this repository, and nothing detected it (F-05). |

The system currently satisfies **1.5 of 10** required capabilities.

The most consequential finding is not a bug. It is that the increment contains **no evaluator, no candidate isolation, no comparison and no rollback** — the four things that separate improvement from activity. What exists is a redacted event ledger plus an instruction string. Under the project's own PRINCIPLES ("Its success is not measured by how many agents run"), evidence that counts tool calls, model calls and coordination outcomes measures precisely the thing the product says must not be measured.

**This is not a criticism of the code that was written.** The manifest loader, the SQLite ledger, the redaction, the atomic transaction, the concurrency reconciliation and the default-off boundary are careful, adversarially tested work. The finding is that this work is *observability*, and the surrounding documents describe it as *a cycle*.

### What blocks what

- **Blocks activation:** F-01, F-02, F-03, F-06, F-08, F-17.
- **Blocks any causal-improvement claim:** F-04, F-05, F-09, F-10, F-11, F-13, F-18.
- **Blocks release / publication:** the above, plus F-20 and F-21 (documentation asserts unimplemented behaviour and a stale baseline digest).
- **Does not block anything:** F-25, F-26.

---

## 2. Product-language summary

Aether currently keeps a careful diary of what a session did: which tools ran, how long they took, whether they ended in error, how many model turns happened, and whether the session ended cleanly. The diary is private, it never records your prompts or the model's answers, it refuses to write itself into another project's folder, and it refuses to declare a version approved. All of that works.

What the diary cannot do is tell you whether Aether got **better**.

It never records what you actually asked for. It never records whether you got it. It never runs the same task twice to compare. It has no notion of "before" and "after". It has no way to undo a change that made things worse. And the one number it produces — the next-version signal — is fixed at "needs more evidence" no matter what happens, because nothing in the running system ever sets it to anything else.

There is also a governance problem that already occurred, not a hypothetical one. Two copies of this feature exist on your machine. The copy in your main folder — the one every document tells an incoming agent to read, and the one the configuration would load — is an **older, less safe version**, and three safety tests that would have caught the difference were removed from it. Running the tests in that folder reports "23 passed, all green". Running the same feature's own full test set reports 26. Nothing in the system noticed. That is exactly the failure mode a self-improvement cycle is supposed to prevent: the thing being changed also owns the test that decides whether the change was good.

Finally, the shipped configuration template removes the old coordination tool (`talk_to`) while the new one (Harmonia) is switched off and the diary plugin is not switched on. Anyone installing from that template gets a system with **no coordination path and no cycle at all**.

The honest description of v0.20.0 today is: *"a safe, private, default-off measurement substrate that a future self-improvement cycle could be built on."* It is a good foundation. It is not yet the thing.

---

## 3. Authority map

### 3.1 Reconstructed roles

| # | Role | Who fills it today | Independent? |
|---|---|---|---|
| 1 | System to be improved | Aether Agents source + coordination kernel + Daimon profiles | — |
| 2 | Observer / evidence collector | `hooks.py` + `ledger.py`, in-process inside Hermes | **No** — same process, same lifetime, same failure domain |
| 3 | Actor proposing the modification | Hermes (the LLM), guided by a prompt string | **No** |
| 4 | Actor implementing the modification | Hermes, writing directly into the same working tree | **No** |
| 5 | Evaluator of the modification | **Does not exist.** Substituted by "the test suite passes", where the suite is editable by role 4 | **No** |
| 6 | Accepting authority | Product owner (documented); in practice `pytest` exit status | Partial |
| 7 | Rollback mechanism | **Does not exist.** `grep -rn "rollback\|revert\|restore\|undo" src/olympus_v3/self_improvement/` → no match | — |

**Independence verdict: insufficient.** Roles 3, 4 and 5 collapse into one actor operating on one mutable working tree. F-05 is the empirical demonstration that this collapse has already produced a false green.

### 3.2 Source-of-truth boundaries

| Source of truth | May be mutated by | Enforcement |
|---|---|---|
| Hermes memory / user profile | Hermes | Prompt policy |
| Skills (`home/skills/`) | Hermes, human | None (filesystem) |
| Configuration (`home/config.yaml`) | Human; template is versioned | Gitignored runtime file |
| Aether source code | Hermes (direct), human | None — same working tree, no gate |
| External project code | Hermes | Prompt policy + (branch only) `.git`-boundary discovery |
| Release evidence (`SELF_IMPROVEMENT_EVIDENCE.md`) | `evidence.write_release_evidence` | Atomic replace; content is ledger-derived only |
| Operational ledger (`.aether/self_improvement.db`) | The plugin | 0600, symlink-refusing, project-scoped |
| Manifest (`CYCLE.yaml`) | Human | Digested once per session, never re-checked (F-19) |

The critical gap: **"Aether source code" has no writer boundary.** The actor that repairs the framework, the actor that writes the tests proving the repair, and the actor that reports the result are the same, with no intermediate artifact anyone else validates.

### 3.3 Component boundaries

- **Hermes** — user-facing intent authority. In v0.20.0 it is also, de facto, the proposer, implementer and evaluator.
- **Harmonia / kernel** — bounded task state, admission, dispatch, cleanup. Default-off (`config_loader.py:42` `enabled: bool = False`). Every start attempt fails closed with `feature_disabled` (`harmonia_service.py:110-111`).
- **Olympus / ACPManager** — sole owner of process and ACP session lifecycle. Untouched by v0.20.0. Correct.
- **Daimons** — bounded specialists. Unreachable from the shipped template (F-17).
- **User / product owner** — sole approval authority for version scope. Correctly preserved: `evidence.py` refuses to approve, and `render_release_evidence` states so explicitly.

`talk_to` does **not** reappear as a hidden fallback: it is excluded at the MCP registration layer (`home/config.yaml.template`, `mcp_servers.olympus_v3.tools.exclude: [talk_to]`), which is a configuration boundary, not a prompt. That invariant holds mechanically.

---

## 4. Real flow (as implemented)

```text
Hermes process starts
  │
  ├─ plugins.enabled read ──► "aether-self-improvement" NOT present ──► PLUGIN NEVER LOADS
  │                                                                     (end of real flow today)
  │
  └─ [counterfactual: if it were enabled]
       │
       on_session_start (fires ONLY for brand-new sessions, never on continuation)
         └─ _project_root: kwargs["project_root"] → $AETHER_PROJECT_ROOT → walk up from cwd
              └─ verify_project_identity: AGENTS.md first line + pyproject name + .git exists
                   └─ load_cycle_manifest: strict field validation
                        └─ ledger.start_session  (INSERT OR IGNORE, return value discarded)
                        └─ mark_abandoned_sessions (PID liveness heuristic)
       │
       pre_llm_call (is_first_turn only)
         └─ returns a 9-line instruction string injected into the user message
            ── THIS STRING IS THE ENTIRE "CYCLE" ──
       │
       post_tool_call  (per tool call)
         └─ discards Hermes' own canonical `status`/`error_type`
         └─ re-derives outcome with a weaker parser        ─► F-02
         └─ classifies Harmonia against a wire format
            Harmonia does not emit                          ─► F-01
         └─ INSERT OR IGNORE on a GLOBAL tool_call_id PK    ─► F-03
       │
       post_llm_call  (per turn, ONLY if final_response and not interrupted)
         └─ records requested_model; every other telemetry
            field is NULL because Hermes never sends them   ─► F-09, F-10
       │
       on_session_end  (per TURN — correctly not treated as finalization)
         └─ any single failed/interrupted turn pins the
            session to reconciliation_required forever      ─► F-14
       │
       on_session_finalize  (true conversation boundary)
         └─ finalize_session(default signal)                ─► F-04
       │
       [no evaluator]  [no comparison]  [no rollback]  [no promotion gate]
```

## 5. Documented flow (as written)

```text
SESSION_IDENTIFIED
  → BASELINE_CAPTURED          (commit + dirty-path inventory)
  → WORK_CONTRACTED
  → EXECUTING
  → MEASURING
  → CLASSIFIED                 (framework_defect | contract_defect |
                                worker_defect | configuration_state)
  → REPAIRING?                 (framework defect only)
  → VERIFYING                  (focused + proportional regression evidence)
  → RETRYING_INTENDED_PATH?    (retry through Harmonia)
  → EVIDENCE_RECORDED          (5-dimension metric vector)
  → SESSION_FINALIZED          (NONE | PATCH_CANDIDATE |
                                MINOR_CAPABILITY_SIGNAL | REQUIRES_MORE_EVIDENCE)
```

Source: `docs/knowledge/SELF_IMPROVEMENT_CYCLE.md:33-45`, `docs/releases/v0.20.0/CYCLE.yaml:48-66`.

**Gap:** of the eleven documented states, the implementation persists exactly three (`active`, `reconciliation_required`, `finalized` — `ledger.py:27`). `BASELINE_CAPTURED` is partial. `WORK_CONTRACTED`, `CLASSIFIED`, `REPAIRING`, `VERIFYING`, `RETRYING_INTENDED_PATH` have no representation in code, no column, no transition and no test. The four failure classes appear nowhere in `src/olympus_v3/self_improvement/`. Adversarial hypotheses 2 and 3 are **confirmed**.

---

## 6. Documented / implemented / tested / operationally validated matrix

| Capability | Documented | Implemented | Tested | Operationally validated |
|---|:--:|:--:|:--:|:--:|
| Strict manifest loading | ✅ | ✅ | ✅ behavioural | ❌ |
| Manifest pinned to its own candidate version | ✅ implied | ❌ (F-07) | ❌ | ❌ |
| Fail-closed project identity | ✅ | ⚠️ imitable, bypassable in main tree (F-06) | ⚠️ branch only | ❌ |
| Exactly one record per session | ✅ | ⚠️ ID-reuse merges (F-15) | ⚠️ structural | ❌ |
| Baseline commit | ✅ | ✅ (broken in worktrees, F-12) | ⚠️ synthetic `.git` only | ❌ |
| Baseline dirty-path inventory | ✅ | ❌ (F-13) | ❌ | ❌ |
| Session state machine | ✅ 11 states | ❌ 3 states | ❌ | ❌ |
| Failure classification (4 classes) | ✅ | ❌ | ❌ | ❌ |
| Pre/post-admission distinction | ✅ | ❌ (F-01) | ⚠️ tests a fabricated payload | ❌ |
| Safe takeover + cleanup receipt | ✅ | ❌ prompt only | ❌ | ❌ |
| Framework repair / verify / retry | ✅ | ❌ prompt only | ❌ | ❌ |
| Router telemetry recorded | ✅ | ❌ unreachable (F-09) | ⚠️ tests assert the NULLs | ❌ |
| No secrets / payloads in evidence | ✅ | ✅ | ✅ incl. WAL scan | ❌ |
| WAL/SHM privacy | ✅ | ✅ **0600 verified** | ⚠️ content only, not mode | ✅ verified by this audit |
| Interruption preserved | ✅ | ✅ (over-sticky, F-14) | ✅ | ❌ |
| Concurrent sessions preserved | ✅ | ⚠️ same-process only | ⚠️ same-process only | ❌ |
| Cross-project isolation | ✅ | ❌ main tree / ✅ branch | ❌ main tree / ✅ branch | ❌ |
| Atomic tool+coordination write | ✅ | ✅ | ✅ fault-injected | ❌ |
| Next-version signal from evidence | ✅ | ❌ constant (F-04) | ⚠️ direct call only | ❌ |
| Release evidence never approves | ✅ | ✅ | ✅ | ❌ |
| Ledger schema migration | ⚠️ risk noted | ❌ (F-16) | ❌ | ❌ |
| Rollback | ✅ implied by PDR | ❌ absent (F-18) | ❌ | ❌ |
| Causal before/after acceptance | ✅ | ❌ | ❌ | ❌ (declared pending) |
| Plugin default-off | ✅ | ✅ | ✅ | ✅ |

Legend: ✅ present · ⚠️ partial or misleading · ❌ absent.

---

## 7. Invariant catalogue

Enforcement levels: **M** = mechanically enforced in code · **P** = prompt-only · **D** = documentation only · **✗** = not enforced.

| # | Invariant | Level | Verdict |
|---|---|:--:|---|
| I-01 | A session produces at most one valid logical record | M | **Holds** for distinct IDs; **fails** on ID reuse (F-15) |
| I-02 | A reused identifier cannot mix evidence across sessions/manifests | ✗ | **Fails.** Probe 7: second `start_session` with a different digest/baseline is silently ignored; new evidence attaches to the old row |
| I-03 | An external project cannot initialize or mutate Aether's ledger | ✗ main / M branch | **Fails in the audited working tree.** Probe 3 wrote a session row into a target project from a foreign cwd |
| I-04 | A global env var cannot make a foreign session look like Aether | ✗ main / M branch | **Fails in the audited working tree.** `AETHER_PROJECT_ROOT` is honoured (`hooks.py:52`) |
| I-05 | The loaded manifest is exactly the expected candidate | ✗ | **Fails.** Probe 4: `candidate_version: 9.9.9` inside `docs/releases/v0.20.0/CYCLE.yaml` is accepted |
| I-06 | An authorization change must not make the manifest unloadable | ✗ | **Fails.** Probe 5: authorizing `harmonia_activation` raises `ManifestError`, `verify_project_identity` returns `None`, the cycle silently vanishes |
| I-07 | `talk_to` does not reappear as a hidden fallback | M | **Holds.** Excluded at MCP registration, not by prompt |
| I-08 | Harmonia is never run ceremonially | P | Prompt-only; unverifiable while default-off |
| I-09 | A durable admission cannot be lost if `post_tool_call` never runs | ✗ | **Fails.** Probe 13: a crash after admission leaves `status=active`, 0 tool rows, 0 coordination rows |
| I-10 | Hermes takes no direct authority while effects are uncertain | P | Prompt-only. No lease, no gate, no check |
| I-11 | A crash does not turn an interrupted session into a success | M | **Holds.** `finalize_session` only promotes `active` → `finalized` |
| I-12 | Two concurrent sessions do not invalidate each other | M | **Holds in-process** (`protected_session_ids`); **untested across processes** |
| I-13 | PID reuse cannot produce a false success | M | **Holds.** Conservative: a reused PID defers reconciliation, never fabricates success |
| I-14 | Evidence stores no prompts, responses, results, args or secrets | M | **Holds.** Schema has no payload columns; args/results are dropped at the hook |
| I-15 | WAL/SHM respect the privacy boundary | M | **Holds.** Probe 8 and the real ledger: `-wal`/`-shm` are `0600` |
| I-16 | Evaluator, benchmark and candidate cannot change together silently | ✗ | **Fails, demonstrably.** F-05 |
| I-17 | The SemVer signal derives from sufficient facts, not a default | ✗ | **Fails.** The only production call site uses the default (`hooks.py:344`) |
| I-18 | Release evidence demonstrates quality, not call counts | ✗ | **Fails.** `evidence.py:36-71` emits counts exclusively |
| I-19 | Increased activity is not mistaken for improvement | ✗ | **Fails.** Activity volume is the entire metric surface |
| I-20 | The user's objective is not rewritten after seeing the result | ✗ | Not represented at all — the objective is never recorded |
| I-21 | An Aether improvement cannot contaminate other projects | ✗ main / M branch | See I-03 |
| I-22 | A local project improvement is not auto-promoted to a global skill | D | Documented in the learning-placement table; no mechanism |
| I-23 | Every candidate modification has verifiable rollback | ✗ | **Fails.** No rollback code exists |
| I-24 | Public activation leaves an operational coordination route | ✗ | **Fails.** Template removes `talk_to`; Harmonia default-off; plugin not enabled (F-17) |

**Score: 6 of 24 mechanically enforced. 3 prompt-only. 1 documentation-only. 14 not enforced.**

---

## 8. Adversarial traces

Each trace states: initial state → active authority → transitions → expected persistence → possible durable effect → takeover condition → required evidence → **actual result** → correct result → missing test.

### T-01 — Clean Aether session that needs no Daimon
Initial: no ledger row. Authority: Hermes. Transitions: `on_session_start` → `pre_llm_call` → n×`post_tool_call` → `on_session_end` → `on_session_finalize`. Expected persistence: one `active` row → `finalized`. Durable effect: none. Takeover: n/a. Required evidence: task outcome + baseline.
**Actual:** works, *if the plugin were enabled*. Records counts. Never records what the user asked for or whether they got it. Signal = `REQUIRES_MORE_EVIDENCE`.
**Correct:** the same, plus a recorded task identity and outcome. **Missing test:** none needed — the gap is architectural.

### T-02 — Aether session where a Daimon does apply
**Actual:** Harmonia `start` → `feature_disabled` → recorded `pre_admission/feature_disabled` (this path is classified correctly). No specialist work occurs. The prompt forbids `talk_to`, so the work is done directly by Hermes, and the ledger cannot distinguish "no Daimon was needed" from "a Daimon was needed and was unavailable".
**Correct:** record applicability as an explicit field. **Missing test:** applicability vs availability distinction.

### T-03 — Pre-admission failure, invalid contract
**Actual:** `{"ok":false,"error":{"code":"invalid_request"}}` → `('pre_admission','invalid_request')`. **Correct.** One of only three error codes that classify correctly.

### T-04 — `feature_disabled`
**Actual:** classified correctly. This is also the only Harmonia outcome the project has ever actually observed (`BENCHMARK_REPORT.md`).

### T-05 — Successful admission, then crash before dispatch
**Actual (probe 13):** `status=active`, `tool_calls=0`, `coordination_events=0`. A durable kernel run may exist with **zero trace** in the cycle ledger. A later session's `mark_abandoned_sessions` will flip the row to `reconciliation_required` only if the PID is provably dead.
**Correct:** write an intent record *before* the tool call, reconcile after. **Missing test:** crash-consistency test with a pre-write intent row.

### T-06 — Dispatch with unknown outcome
**Actual:** Harmonia's real `uncertainty: "terminal_evidence_absent"` field is never read. The response classifies as `('unknown','unknown')` and `_tool_outcome` returns `'success'`. **An unknown durable effect is recorded as a success.**
**Correct:** map `uncertainty != null` to an explicit `unknown_effect` outcome. **Missing test:** real-payload classification (F-01).

### T-07 — Worker produces a technically valid but out-of-scope result
**Actual:** invisible. Nothing records scope, and `_tool_outcome` returns `success`. Objective 2 ("preserve the requested vision and scope") has no measurement.
**Correct:** scope-fidelity field, owner- or checker-assigned. **Missing test:** everything.

### T-08 — Real framework defect → repair → verify → correlated retry
**Actual:** no correlation exists. Worse, the retry is the exact case F-03 destroys: repeating the same verification command yields the same deterministic `tool_call_id`, so the "after" measurement is silently discarded and only the "before" survives.
**Correct:** attempt-scoped IDs plus an explicit repair/retry correlation key. **Missing test:** repeat-the-same-call counting test.

### T-09 — Session interrupted during repair
**Actual:** `record_turn_outcome(interrupted=True)` → `reconciliation_required`, sticky forever (probe 11). Correct in spirit, but no repair state existed to reconcile, and the session can never return to a clean state even if the user continues successfully for hours.
**Correct:** turn-level outcome table; session status derived, not latched. **Missing test:** multi-turn recovery.

### T-10 — Two concurrent sessions
**Actual:** in-process concurrency is correctly preserved (`protected_session_ids`, live-PID check). **Cross-process** concurrency is untested; `busy_timeout=5000` with a per-operation connection is plausible but unproven under real contention. The `SECURITY_REVIEW` acknowledges this.
**Correct:** as implemented. **Missing test:** multi-process contention.

### T-11 — ID reuse / collision
**Actual (probes 6, 7):** two sessions emitting `tool_call_id="call_1"` → the second row is silently dropped; `evidence_counts.tool_calls` reports 1 instead of 2. Coordination events collapse identically. Session-ID reuse binds new evidence to a stale manifest digest and baseline.
**Correct:** composite keys `(session_id, tool_call_id)`; reject or version a reused `session_id`. **Missing test:** cross-session ID collision.

### T-12 — Dirty baseline with unrelated changes
**Actual:** only HEAD is recorded. Concretely measured in this audit: the dirty tree yields **1170 passed**, the clean checkout yields **1163 passed** — a 7-test difference caused entirely by uncommitted third-party work. The committed `BENCHMARK_REPORT` documents this exact reconciliation; the working-tree copy silently reports the dirty number.
**Correct:** record a dirty-path digest at baseline and refuse causal claims when it is non-empty. **Missing test:** baseline integrity.

### T-13 — Foreign project with `HERMES_HOME` / `AETHER_PROJECT_ROOT` pointing at Aether
**Actual (probe 3):** in the audited working tree, **the isolation fails**. From an unrelated project directory, with `AETHER_PROJECT_ROOT` set, `on_session_start` created the target ledger and wrote a session row. The explicit `project_root` kwarg does the same. `HERMES_HOME` alone is harmless — and `HERMES_HOME` is the only vector the surviving test covers.
**Correct:** the committed branch's version — no ambient redirection, discovery stops at the nearest `.git`. **Missing test:** the two tests that were deleted (F-05).

### T-14 — Manifest modified during a session
**Actual (probe 14):** no re-verification. The digest captured at `on_session_start` is retained; evidence continues to accrue under a stale digest; injected context still advertises the old candidate name.
**Correct:** re-verify the digest at finalization and mark the session `manifest_drift`. **Missing test:** mid-session mutation.

### T-15 — Old / incompatible ledger schema
**Actual (probe 10):** a pre-existing `cycle_sessions(session_id, legacy_col)` table causes `CREATE TABLE IF NOT EXISTS` to no-op, the INSERT to raise, the hook to swallow it as a warning, and the session to proceed with **zero evidence**. No `schema_version` column exists.
**Correct:** a `schema_version` table with explicit migration or fail-closed refusal. **Missing test:** schema-migration test.

### T-16 — Hook or SQLite failure during a partial write
**Actual:** the tool+coordination pair is genuinely atomic (verified by the repo's own trigger-injection test, which is good practice). But the surrounding hook catches `Exception` broadly, so a failure degrades to a log line and silently missing evidence.
**Correct:** as implemented for atomicity; add a persistent `evidence_gap` counter. **Missing test:** gap accounting.

### T-17 — Evidence with unknown telemetry
**Actual:** `unknown` is honestly preserved and never inferred — this is done well. However `model_calls_missing_route` will equal `model_calls` in 100% of real sessions (probe 12), so the field carries no information.
**Correct:** either wire the telemetry through or remove the claim. **Missing test:** integration test against Hermes' real `post_llm_call` kwargs.

### T-18 — Improvement passes internal tests but regresses an external benchmark
**Actual:** cannot occur, because no external benchmark exists. `BENCHMARK_REPORT.md` contains test counts and two Harmonia error codes. Objective 1 requires "controlled comparative evaluation against systems such as Claude Code, Codex, OpenCode" — nothing of the sort is present or planned in this increment.
**Correct:** a held-out task set the candidate cannot modify. **Missing test:** the entire benchmark.

### T-19 — A change that modifies implementation, tests and acceptance criteria together
**Actual: this already happened, in this repository, and was not detected.** See F-05. This is the audit's strongest empirical result.

### T-20 — Plugin activation and rollback in a disposable pilot profile
**Actual:** activation requires adding `plugins.enabled: [aether-self-improvement]`. There is no rollback procedure, no uninstall path, no ledger-teardown routine, and no documented disposable profile. Activating in the main worktree would load the **vulnerable** copy (F-06).
**Correct:** pilot in the clean worktree with an explicit profile, and a documented teardown. **Missing test:** activation/rollback rehearsal.

---

## 9. Findings, ordered by severity

---

### F-01 · P0 · logical defect
**Affected claim:** `CYCLE.yaml:185` acceptance gate `pre_and_post_admission_failures_are_distinguished`; `gate_status.harmonia_outcome_classification: pass_deterministic_tests`; PDR-0009 validation gate 6.

**Evidence:** `src/olympus_v3/self_improvement/hooks.py:210-239` reads `payload["status"]` and `payload["success"]`. Harmonia never emits either. Its real envelopes are `harmonia_contract.py:364-376` (`{"action","ok","runtime_authority","durable","state","uncertainty","error":{"code","message","retryable"}}`) and `harmonia_service.py:398-420` (`{"ok":True,...,"state":<state>,"error":None}`). The allowlisted post-admission set `{accepted, running, completed, failed, timed_out, cleanup_failed, stopped}` (`hooks.py:234`) has **zero intersection** with Harmonia's real state set `{admitted, dispatch_staged, retry_wait, session_bound, terminal_observed, cleanup_pending, cleaned, reconciliation_required, cancel_requested}` (`harmonia_service.py:37-49`). Of 13 real error codes (`harmonia_contract.py:46-60`), only 3 appear in the plugin's pre-admission set; `capacity_exhausted` and `key_missing` are invented names for the real `admission_limit` and `key_provider_unavailable`.

**Reproduction:** classify a real success envelope → `('unknown','unknown')`; a real `admission_limit` error → `('unknown','admission_limit')`. Verified against both the working tree and the committed branch.

**Consequence:** the cycle cannot tell "the coordinator accepted the work and finished it" from "the coordinator did something unclassifiable". Every post-admission fact — dispatch, terminal outcome, cleanup receipt, survivor, reconciliation — is recorded as `unknown`. The `coordination` metric block in `CYCLE.yaml:75-87` is unreachable.

**Why current tests miss it:** `test_harmonia_outcomes_are_classified_without_contract_payloads` (`tests/test_self_improvement.py:451,460`) feeds `{"success":false,"error":{"code":...}}` — a payload shape Harmonia does not produce. It passes through the `error.code` branch by coincidence, which is why the pre-admission cases work.

**Minimal fix:** classify from `error.code` for failures and from `state` for successes; replace both allowlists with the constants already exported by `harmonia_contract.HARMONIA_ERROR_CODES` and `harmonia_service._STATES`; map `uncertainty is not None` to an explicit `unknown_effect`.
**Alternatives:** import Harmonia's own classifier; or have Harmonia emit an explicit `phase` field.
**Risk of the fix:** low; add a contract test that imports the real constants so drift breaks the build.
**Acceptance tests:** classify each of the 13 error codes and each of the 9 states from real envelopes; assert no `unknown` for known inputs.
**Blocks:** activation.

---

### F-02 · P0 · implementation bug
**Affected claim:** `tool_calls.outcome` semantics; `CYCLE.yaml` `correctness` measurements.

**Evidence:** `hooks.py:192-207`. Any JSON object without a truthy `error` and without an integer `exit_code` returns `"success"`.

**Reproduction:**
```
{"success": false}                              -> 'success'
{"ok": false, "error": null}                    -> 'success'
{"status": "failed"}                            -> 'success'
{"errors": ["boom"]}                            -> 'success'
{"ok": false, "state": "reconciliation_required"} -> 'success'
```

**Consequence:** failures are recorded as successes. The aggregate "success rate" is not a success rate.

**Aggravating factor:** Hermes **already computes** a canonical classification and passes it. `model_tools.py:1003-1018` sends `status`, `error_type` and `error_message` derived by `_tool_result_observer_fields` (`model_tools.py:964-971`). `on_post_tool_call` deletes them (`hooks.py:254 del task_id, kwargs`) and re-derives a weaker verdict.

**Why current tests miss it:** every fixture uses `exit_code: 0` or an `error` dict. No negative payload lacking both keys is tested.

**Minimal fix:** use the host-supplied `status` when present; fall back to the local parser only when it is absent.
**Alternatives:** extend the local parser to treat `ok is False` / `success is False` as errors.
**Risk:** low.
**Acceptance tests:** a table-driven test over the payload shapes above plus the real Harmonia envelopes.
**Blocks:** activation.

---

### F-03 · P0 · logical defect
**Affected claim:** every count in `SELF_IMPROVEMENT_EVIDENCE.md`; `CYCLE.yaml` `efficiency.tool_calls`; the retry-after-repair evidence required by PDR-0009 §2.

**Evidence:** `ledger.py:35` `tool_call_id TEXT PRIMARY KEY` and `ledger.py:59` `event_id TEXT PRIMARY KEY` are **global**, not per-session. Writes use `INSERT OR IGNORE` (`ledger.py:274`, `ledger.py:291`). `hooks.py:259` reuses `tool_call_id` verbatim as the coordination `event_id`.

**Reproduction (probe 6):** two sessions each emit `tool_call_id="call_1"`. Session A gets one row; session B gets zero; `evidence_counts.tool_calls == 1`.

**Aggravating factor:** Hermes' fallback ID generator is **content-deterministic**: `_deterministic_call_id(fn, args, index) → "call_" + sha256(f"{fn}:{args}:{index}")[:12]` (`agent/codex_responses_adapter.py:182-191`), used on the `chat_completions` path that this deployment is configured for (`agent/chat_completion_helpers.py:1424`). Two invocations of the same tool with the same arguments therefore produce the **identical ID**. Running `pytest -q` twice — the literal "verify the correction, then retry" step — yields one row, not two.

**Consequence:** counts systematically undercount, and they undercount *precisely the repeated calls that a before/after comparison depends on*. Any causal claim built on these counts is biased in the direction that favours "no change detected".

**Why current tests miss it:** every fixture uses unique IDs within a single session.

**Minimal fix:** `PRIMARY KEY (session_id, tool_call_id)`; same for `coordination_events`. Add an `attempt` or monotonic sequence column so repeated identical calls remain distinct within a session.
**Alternatives:** synthesize `f"{session_id}:{tool_call_id}:{seq}"`.
**Risk:** schema change — requires F-16's migration story first.
**Acceptance tests:** same ID across two sessions → 2 rows; same ID twice within one session → 2 rows with distinct sequence.
**Blocks:** activation and every counting claim.

---

### F-04 · P0 · architecture gap
**Affected claim:** the words "self-improvement" and "cycle"; `CYCLE.yaml:165` `next_version_signal_aggregation`; `CYCLE.yaml:193` `release_evidence_uses_validated_facts_not_model_prose`; PDR-0009 validation gate 13.

**Evidence:**
- `evidence.py:36-71` — the release projection contains: candidate name, digest, provider, signal, session-status counts, tool-call count, model-call count, missing-route count, coordination-outcome counts. Nothing else.
- `hooks.py:344` — the only production call is `finalize_session(session_id)`, using the default `next_version_signal="REQUIRES_MORE_EVIDENCE"` (`ledger.py:407`). `NONE`, `PATCH_CANDIDATE` and `MINOR_CAPABILITY_SIGNAL` are never assigned by any running code path.
- `aggregate_next_version_signal` (`evidence.py:15-27`) returns `REQUIRES_MORE_EVIDENCE` whenever any session is non-finalized **or** any signal is `REQUIRES_MORE_EVIDENCE` — which, given the above, is always.
- No column, table or function records the user's task, the intended outcome, an acceptance threshold, a baseline measurement, a candidate measurement, or a comparison.
- `grep -rn "rollback\|revert\|restore\|undo" src/olympus_v3/self_improvement/` → no match.

**Reproduction (probe 11):** a full session lifecycle ending in `finalize` yields `aggregate_next_version_signal() == 'REQUIRES_MORE_EVIDENCE'`.

**Consequence:** the increment cannot express, let alone demonstrate, a causal improvement. Adversarial hypotheses 1, 6, 7 and 23 are **confirmed**.

**Why current tests miss it:** `test_release_evidence_is_deterministic_and_never_approves_a_version` calls `finalize_session(..., next_version_signal="PATCH_CANDIDATE")` **directly**, exercising a parameter no production path supplies.

**Minimal fix:** out of scope for a patch. See §14.
**Blocks:** any improvement claim; does not block keeping v0.20.0 as instrumentation.

---

### F-05 · P0 · logical defect (self-certification)
**Affected claim:** "23 passed"; `IMPLEMENTATION_REPORT.md` verification block; the independence premise of the whole cycle.

**Evidence — two divergent copies of the candidate:**

| Artifact | main worktree (uncommitted) | branch `48635b4` (clean) |
|---|---|---|
| `hooks.py` sha256 (16) | `5e4619bcb05c7302` | `5da7a5d2b849fc0a` |
| `_project_root` | `kwargs["project_root"] or os.environ["AETHER_PROJECT_ROOT"]` | `kwargs["project_root"]` only |
| `_walk_to_project` | walks all parents for `CYCLE.yaml` | stops at nearest `.git` |
| bootstrap tests | **23** | **26** |
| full suite | 1170 | 1163 |
| isolation tests | **absent** | `test_environment_cannot_redirect_a_foreign_workspace_into_aether`, `test_nested_foreign_repository_cannot_inherit_parent_aether_identity`, `test_aether_subdirectory_resolves_the_nearest_repository_root` |
| `SECURITY_REVIEW` finding 4 | **absent** | present, "Severity: High … tracked in GitHub #125" |

**Reproduction:** running the branch's three isolation tests against the working-tree source:
```
FAILED test_environment_cannot_redirect_a_foreign_workspace_into_aether
FAILED test_nested_foreign_repository_cannot_inherit_parent_aether_identity
2 failed, 1 passed
```

**Consequence:** the implementation, its tests, its security review and its reported acceptance counts moved together. The working tree reports a fully green 23/23 while failing two safety properties the project itself identified as High severity. `AGENTS.md`, `README.md`, `SELF_IMPROVEMENT_CYCLE.md` and the MCP `PYTHONPATH` all point incoming agents and the runtime at the **weaker** copy. No mechanism — not the suite, not the manifest digest, not the evidence projection — detects the divergence.

This is trace T-19 occurring in reality, and it is the direct empirical answer to the audit's independence question.

**Note on attribution:** the committed branch is the *later, corrected* state; the working tree preserves the *earlier, vulnerable* one. This is a stale-worktree hygiene failure, not malice. The finding stands regardless of intent: nothing in the system can distinguish the two, and the green suite is in the wrong tree.

**Minimal fix:** make the candidate identity explicit and checkable — pin the audited tree to a commit, or delete/refresh the stale copy so only one candidate exists. Longer term, the evaluator must not live in the tree it evaluates (§13, option D).
**Risk:** none for the hygiene fix.
**Acceptance tests:** a check that the working tree's `self_improvement/` matches the candidate commit, or that no untracked copy shadows it.
**Blocks:** activation, release, and any acceptance claim made from the main worktree.

---

### F-06 · P1 · implementation bug (fixed on branch, live in the audited tree)
**Affected claim:** `CYCLE.yaml:191` `non_aether_projects_cannot_initialize_or_mutate_the_cycle`; `SECURITY_REVIEW.md` "Non-Aether workspaces cannot create or mutate the cycle ledger"; PDR-0009 gate 12; invariant I-03/I-04/I-21.

**Evidence:** `hooks.py:51-56` (working tree). `verify_project_identity` validates the *target* directory, never that the session belongs to it.

**Reproduction (probe 3):** cwd = unrelated project, `AETHER_PROJECT_ROOT=<aether-shaped root>` → ledger created, session row written. Same via the `project_root` kwarg.

**Consequence:** a global env var exported once in a shell profile silently attributes every session from every project to Aether's improvement evidence. Discovery also walks past a nearer foreign `.git`, so a repository nested under Aether inherits Aether's identity.

**Why current tests miss it:** the surviving `test_foreign_workspace_does_not_create_or_mutate_aether_storage` sets `HERMES_HOME` — a variable this code never reads. The tests that covered the real vectors were removed (F-05).

**Minimal fix:** adopt the committed branch's `hooks.py` verbatim.
**Risk:** none — the branch version passes 26/26.
**Blocks:** activation.

---

### F-07 · P1 · logical defect
**Affected claim:** `CYCLE.yaml:182` `manifest_and_semver_state_validate`.

**Evidence:** `manifest.py:87-89` validates only the `MAJOR.MINOR.PATCH` shape. The path is the hard-coded `docs/releases/v0.20.0/CYCLE.yaml` (`manifest.py:14`), but no check ties the declared version to that directory.

**Reproduction (probe 4):** `candidate_version: "9.9.9"` inside the v0.20.0 file → accepted, `manifest.candidate_version == '9.9.9'`.

**Consequence:** evidence can be attributed to a candidate that does not exist. The injected prompt would advertise the wrong candidate.

**Minimal fix:** assert `candidate_version` equals the version segment of `_MANIFEST`'s parent directory.
**Risk:** none. **Acceptance test:** mismatched version → `ManifestError`. **Blocks:** release integrity.

---

### F-08 · P1 · logical defect
**Affected claim:** the activation path itself; invariant I-06.

**Evidence:** `manifest.py:19-28, 131-133`. Every key in `_FORBIDDEN_AUTHORIZATIONS` must literally equal `"not_authorized"`, otherwise `ManifestError`. `verify_project_identity` swallows it (`manifest.py:170-171`) and returns `None`. Every hook then no-ops with **no warning** — `_initialize` returns `None` before any logging.

**Reproduction (probe 5):** setting `authorization.harmonia_activation: authorized` — the legitimate act of the product owner granting the next gate — silently deletes the entire cycle.

**Consequence:** the manifest cannot represent its own successor state. The owner's approval is indistinguishable from a corrupt manifest. The system fails *silently* rather than closed-and-loud.

**Why current tests miss it:** `test_rejects_contract_that_authorizes_activation_or_release` asserts this behaviour as **desired**, without covering the consequence.

**Minimal fix:** separate "this gate is open" from "this cycle is invalid". Accept `authorized` for gate keys and expose them as manifest fields the runtime can act on; keep fail-closed only for malformed values. At minimum, log at WARNING when identity verification fails for a directory that does contain a `CYCLE.yaml`.
**Risk:** medium — needs the owner to define what an authorized gate should *do*.
**Blocks:** activation.

---

### F-09 · P1 · architecture gap
**Affected claim:** `CYCLE.yaml:36-45` `provider.record_when_reported`; `CYCLE.yaml:189` `router_metadata_is_recorded_without_secrets`; PDR-0009 gate 10; `SELF_IMPROVEMENT_CYCLE.md:186-198`.

**Evidence:** `hooks.py:298-311` reads `resolved_route`, `resolved_model`, `latency_ms`, `input_tokens`, `output_tokens`, `reported_cost`, `error_code`, `api_request_id` from `**kwargs`. Hermes' `post_llm_call` invocation (`agent/turn_finalizer.py:484-494`) passes exactly: `session_id`, `task_id`, `turn_id`, `user_message`, `assistant_response`, `conversation_history`, `model`, `platform`. **None of the telemetry fields are sent.** The values exist on the agent object (`turn_finalizer.py:531-547` builds a result dict containing tokens, cost, provider, base_url) but are never forwarded to the hook.

**Reproduction (probe 12):** calling the hook with Hermes' verbatim kwarg set yields `NULL` for all eight fields.

**Consequence:** the entire `efficiency` measurement dimension is structurally empty. `model_calls_missing_route` equals `model_calls` in every real session, so the field is uninformative. The gate cannot be met by activation; it requires a Hermes-side change.

**Why current tests miss it:** `test_missing_router_telemetry_remains_unknown` asserts the NULLs are NULL — it encodes the gap as the expected behaviour rather than detecting it.

**Minimal fix:** none available inside Aether. Either (a) upstream a `post_llm_call` payload extension in Hermes Agent, or (b) delete the claim from `CYCLE.yaml` and mark the dimension deferred.
**Risk:** (a) is an external dependency; (b) is honest and free.
**Blocks:** the router-telemetry gate, not activation.

---

### F-10 · P1 · logical defect
**Affected claim:** every efficiency and cost aggregate.

**Evidence:** `agent/turn_finalizer.py:481` — `post_llm_call` fires only `if final_response and not interrupted`.

**Consequence:** failed, empty and interrupted turns are never measured. Cost, latency and token evidence describe only successful turns — a textbook survivorship bias, in the direction that makes the system look cheaper and faster than it is. This directly undermines "compare before and after" whenever the "before" state is the one that fails.

**Minimal fix:** record turn cost from `on_session_end`, which fires unconditionally.
**Risk:** low. **Acceptance test:** interrupted turn produces a model-call row. **Blocks:** efficiency claims.

---

### F-11 · P1 · logical defect
**Affected claim:** `AGENTS.md:15` "Every Hermes session … participates"; `CYCLE.yaml:180` `new_aether_session_initializes_exactly_one_cycle_record`.

**Evidence:** `agent/conversation_loop.py:387-388` — `on_session_start` is "fired once when a brand-new session is created (**not on continuation**)". The only lazy-initialization path is `on_pre_llm_call` (`hooks.py:169`), which returns `None` at line 167 when `is_first_turn` is false. `is_first_turn = (not bool(conversation_history))` (`agent/turn_context.py:704`). `on_post_tool_call` and `on_post_llm_call` do **not** lazily initialize (`hooks.py:256`, `hooks.py:295`).

**Consequence:** a resumed session, a session continued after a Hermes restart, or any session whose first turn is not the plugin's first observation produces **zero evidence**. Long-lived resumed sessions — the normal way this tool is used — are systematically excluded. The evidence set is biased toward short, fresh sessions.

**Minimal fix:** lazily initialize in `post_tool_call` and `post_llm_call` as `pre_llm_call` already does.
**Risk:** low. **Acceptance test:** a session whose first hook is `post_tool_call` still produces a record. **Blocks:** representativeness of all evidence.

---

### F-12 · P1 · implementation bug
**Affected claim:** `baseline_commit`; the viability of worktree-based candidate isolation.

**Evidence:** `hooks.py:70-97`. For a linked worktree, `.git` is a file; `_git_dir` resolves it correctly; `HEAD` is `ref: refs/heads/<branch>`; the loose ref is looked up **only** under the worktree's private gitdir (`hooks.py:81-84`), and `packed-refs` **only** under `commondir` (`hooks.py:89-94`). The common case — a loose ref under `commondir/refs/heads/` — is never consulted.

**Reproduction (probe 9):** `_git_head("/home/arty/Escritorio/agentes/aether-v020-isolated")` → `"unknown"`, while `git rev-parse HEAD` → `48635b41…`. Confirmed against both copies of the code.

**Consequence:** the candidate's own isolated worktree records `baseline_commit = "unknown"`. Worktrees are also the natural mechanism for the candidate isolation this audit recommends (§13 option E), so the defect blocks the fix path.

**Minimal fix:** after the private-gitdir loose lookup fails, try `common_dir / ref` before `packed-refs`.
**Alternatives:** shell out to `git rev-parse HEAD` (rejected — adds a subprocess to a hot hook).
**Risk:** none. **Acceptance test:** `_git_head` against a real linked worktree. **Blocks:** worktree-based isolation.

---

### F-13 · P1 · logical defect
**Affected claim:** `SELF_IMPROVEMENT_CYCLE.md:57` "the baseline commit **and dirty-path inventory**"; PDR-0009 §Entry protocol.

**Evidence:** `hooks.py:116` records `_git_head(root)` only. No dirty-set capture anywhere.

**Reproduction:** measured in this audit — dirty tree 1170 passed, clean checkout 1163 passed. The committed `BENCHMARK_REPORT` documents this exact reconciliation ("corrected the reported coordination count from 953 to 943 … ten removed tests belong to the uncommitted historical R8 pilot"); the working-tree copy silently reports the dirty numbers.

**Consequence:** changes cannot be attributed. A "before" and an "after" taken across an unrelated `git stash` are not comparable, and nothing records that they aren't.

**Minimal fix:** store a digest of `git status --porcelain` at baseline; refuse causal claims when it is non-empty or has changed between baseline and finalization.
**Risk:** low. **Acceptance test:** dirty baseline is recorded and surfaced in the evidence projection. **Blocks:** causal claims.

---

### F-14 · P1 · logical defect
**Affected claim:** interruption semantics; `aggregate_next_version_signal`.

**Evidence:** `ledger.py:384-405` — `completed=False` or `interrupted=True` sets `status='reconciliation_required'`, and the `CASE` only transitions *from* `active`, so the state is latched. `finalize_session` (`ledger.py:415`) cannot clear it. `evidence.py:19` returns `REQUIRES_MORE_EVIDENCE` if any session is non-finalized.

**Reproduction (probe 11):** turn 1 ok → `active`; turn 2 Ctrl-C → `reconciliation_required`; turns 3-5 ok → still `reconciliation_required`; after finalize → still `reconciliation_required`, with `finalized_at` set.

**Consequence:** one Ctrl-C in a multi-hour session permanently marks it as requiring reconciliation and pins the global signal. Combined with F-04 this is doubly moot today, but it makes the state meaningless as a diagnostic. Setting `finalized_at` on a non-finalized session is also semantically ambiguous (adversarial hypothesis 5, partially confirmed).

**Minimal fix:** record per-turn outcomes in their own table; derive session status rather than latching it; do not set `finalized_at` unless the status actually became `finalized`.
**Risk:** low. **Acceptance test:** interrupted turn followed by successful turns → session is finalizable, with the interruption still visible. **Blocks:** signal usefulness.

---

### F-15 · P1 · logical defect
**Affected claim:** invariant I-02; `exact_once_session_initialization`.

**Evidence:** `ledger.py:154` `INSERT OR IGNORE`; `hooks.py:115` discards the boolean return.

**Reproduction (probe 7):** `start_session("default", digest=AAA, baseline=aaa…)` then `start_session("default", digest=BBB, baseline=ccc…)` → the row keeps `AAA`/`aaa…`. All subsequent evidence attaches to the stale manifest and baseline.

**Consequence:** a reused session identifier merges two logically distinct sessions. Gateway and CLI session IDs are not guaranteed globally unique across restarts.

**Minimal fix:** on collision, compare `manifest_digest` and `baseline_commit`; on mismatch, write a new row under a derived key and record `session_id_collision`.
**Risk:** low. **Acceptance test:** reuse with a different digest → two distinct records. **Blocks:** evidence integrity.

---

### F-16 · P1 · architecture gap
**Affected claim:** operational durability; PDR-0009 §Consequences "Operational ledgers require schema, lifecycle, and privacy governance".

**Evidence:** `ledger.py:15-71` uses `CREATE TABLE IF NOT EXISTS` with no `schema_version` table and no migration.

**Reproduction (probe 10):** a pre-existing `cycle_sessions(session_id, legacy_col)` → `IF NOT EXISTS` no-ops, the INSERT raises `no column named runtime_instance`, `hooks.py:150` swallows it as a warning, 0 rows persist, and Hermes proceeds normally.

**Consequence:** any future schema change silently disables evidence collection on existing installations. F-03's fix requires a schema change, so this must be solved first.

**Minimal fix:** add `PRAGMA user_version` or a `schema_meta` table; on mismatch, either migrate or refuse loudly and rename the old file aside.
**Risk:** low. **Acceptance test:** v0 database → explicit, visible outcome. **Blocks:** any schema evolution.

---

### F-17 · P1 · operational risk
**Affected claim:** invariant I-24; `CYCLE.yaml:183` `talk_to_absent_and_harmonia_present`.

**Evidence:** `home/config.yaml.template` adds `mcp_servers.olympus_v3.tools.exclude: [talk_to]`. `CoordinationConfig.enabled` defaults to `False` (`config_loader.py:42`), so every Harmonia `start` returns `feature_disabled` (`harmonia_service.py:110-111`). The template contains **no `plugins:` key at all**, and plugins are opt-in (`hermes_cli/plugins.py:1381` "None = opt-in default (nothing enabled)").

**Consequence:** a fresh install from the versioned template has **no general delegation path** (only the narrow `aether_curate` → Ariadna route survives) **and no improvement cycle**. `AGENTS.md:15` states "Every Hermes session … participates in the active SemVer self-improvement cycle", which is false for every installation. Adversarial hypotheses 18 and 21 are **confirmed**.

**Minimal fix:** decide explicitly. Either keep `talk_to` until Harmonia is activatable, or document the template as a dogfood-only profile and state plainly that participation requires manual enablement.
**Risk:** low; this is a decision, not a code change.
**Blocks:** public activation. **Requires product-owner decision** (see §18, Q2).

---

### F-18 · P1 · architecture gap
**Affected claim:** invariant I-23; the "Correct" column of every improvement claim.

**Evidence:** no rollback, revert, snapshot or restore mechanism exists in `src/olympus_v3/self_improvement/`.

**Consequence:** a candidate modification that degrades the system has no defined undo path other than manual `git` work in the same tree the change was made in. Without rollback, "improvement" is unfalsifiable in practice: there is no cheap way to return to the baseline and re-measure.

**Minimal fix:** see §14 — candidate changes land in a disposable worktree and are promoted only after evaluation; the rollback is "discard the worktree".
**Blocks:** any improvement claim.

---

### F-19 · P2 · logical defect
**Affected claim:** manifest integrity.
**Evidence:** the digest is computed once at `on_session_start` (`manifest.py:147`) and never re-checked.
**Reproduction (probe 14):** editing `CYCLE.yaml` mid-session changes nothing — evidence continues under the stale digest and the injected context still advertises the old candidate.
**Minimal fix:** re-read and compare the digest at `on_session_finalize`; flag `manifest_drift`.
**Risk:** none. **Blocks:** evidence integrity, not activation.

---

### F-20 · P2 · documentation mismatch
**Affected claims:** several.

| Claim | Location | Reality |
|---|---|---|
| "Every Hermes session … participates" | `AGENTS.md:15` | The plugin is not enabled anywhere (F-17) |
| "injects an identity warning" on identity failure | `SELF_IMPROVEMENT_CYCLE.md:62` | Never happens — silent `None` (F-08) |
| 11-state session machine | `SELF_IMPROVEMENT_CYCLE.md:33-45` | 3 states in code |
| 4 failure classes | `CYCLE.yaml:61-66` | Absent from code |
| "safe direct takeover, framework repair verification, harmonia retry after repair" listed under `implementation_scope.included` | `CYCLE.yaml:161-164` | Prompt text only |
| `harmonia_outcome_classification: pass_deterministic_tests` | `CYCLE.yaml:203` | Tests a payload shape Harmonia does not emit (F-01) |
| "Non-Aether workspaces cannot create or mutate the cycle ledger" | `SECURITY_REVIEW.md` (working-tree copy) | False in that copy (F-06) |
| "Full repository suite: 1170 passed" | `IMPLEMENTATION_REPORT.md` (working-tree copy) | Dirty-tree number; clean candidate is 1163 (F-13) |

**Note:** work explicitly marked deferred (`live_plugin_activation`, `bounded_harmonia_pilot`, `causal_before_after_acceptance`, merge/tag/release) is **correctly** labelled and is not counted as a defect. The rows above are items presented as *implemented* or *passing* that are not.

**Minimal fix:** move the unimplemented items from `implementation_scope.included` to `excluded` or to a `deferred` block; correct the three false statements.
**Risk:** none. **Blocks:** release.

---

### F-21 · P2 · documentation mismatch
**Evidence:** `BENCHMARK_REPORT.md` records `Initial manifest digest: sha256:fd74b601…`. The shipped `CYCLE.yaml` digests to `sha256:7b715d2e…` (verified). The manifest was edited after the benchmark was written.
**Consequence:** the benchmark's stated baseline does not correspond to the artifact it benchmarks — the same class of error the cycle exists to prevent.
**Minimal fix:** regenerate the digest, or generate it mechanically at report time.
**Blocks:** release integrity.

---

### F-22 · P2 · operational risk
**Evidence:** the `.aether/` directory is `0755` (the database and its `-wal`/`-shm` are correctly `0600`, verified in both a synthetic project and the real repository).
**Consequence:** low — file contents are protected; only the directory listing is world-readable.
**Minimal fix:** `mkdir(mode=0o700)`. **Risk:** none.

---

### F-23 · P2 · operational risk
**Evidence:** across five full-suite runs during this audit, one produced `1 failed, 1169 passed` — `tests/coordination/test_v0194_successor_handoff.py::test_two_independent_contexts_reconcile_committed_b_once`, `AuthorityError: writer authentication failed` (`kernel_runtime.py:175`). Four subsequent full runs and three isolated runs of the same file and directory passed.
**Consequence:** the coordination kernel — the subsystem the cycle depends on and intends to improve — has an order- or state-dependent test. "Full repository suite: N passed" is therefore not reproducible-on-demand acceptance evidence.
**Minimal fix:** out of v0.20.0 scope; file an issue and quarantine or seed the test deterministically.
**Blocks:** nothing in v0.20.0; weakens all suite-count evidence.

---

### F-24 · P2 · architecture gap (Goodhart)
**Affected claim:** `docs/product/PRINCIPLES.md` / `VISION.md:42` "Its success is not measured by how many agents run."
**Evidence:** the complete metric surface is: session-status counts, tool-call count, model-call count, missing-route count, coordination-outcome counts.
**Consequence:** every quantity the system can report is an activity volume. If these numbers are ever used to justify a version, the system will have optimized exactly the metric its own product doctrine forbids. See §10.
**Minimal fix:** see §14 — the evidence projection must carry a task-outcome record or explicitly state that it carries none.

---

### F-25 · P3 · not a defect (documented residual risk)
`_process_alive` returns `True` on `PermissionError` (`ledger.py:186-187`), and PID reuse makes a dead owner appear live. The failure mode is *conservative*: a crashed session stays `active` and is never falsely finalized. `SECURITY_REVIEW.md` states this correctly. Invariant I-13 holds.

---

### F-26 · P3 · implementation bug
`ensure_schema()` runs at the top of every read and write (`ledger.py:149, 201, 269, 324, 362, 385, 408, 423, 429, 434, 446, 460, 472, 484, 513`), issuing `PRAGMA journal_mode=WAL` plus a full `executescript` on each call. Also, `with self._connect()` commits but does not close the connection — harmless under CPython refcounting, sloppy elsewhere. Minimal fix: memoize schema initialization per path; use `contextlib.closing`.

---

### Explicitly not defects

- `on_session_end` is correctly treated as a **per-turn** hook, not session finalization. Verified against `agent/turn_finalizer.py:610-624` and its comment at lines 603-608. The plugin's docstring says exactly this. This was the right call and is unusual to get right.
- The tool + coordination write is genuinely atomic, proven by the repository's own SQLite-trigger fault-injection test. Good practice.
- Redaction is effective: no prompts, responses, args or results reach the ledger; the schema has no payload columns; the WAL was scanned for secrets.
- `talk_to` exclusion is a configuration boundary, not a prompt instruction. Invariant I-07 holds mechanically.
- The evidence projection genuinely refuses to approve a version and says so in its output. Invariant preserved.
- Default-off is genuinely default-off.

---

## 10. Self-deception and Goodhart risks

**R-1 — Activity as achievement.** Everything measurable is a count of things the system did. A session that thrashes — 200 tool calls, 40 model turns — produces a *richer* evidence record than one that solves the problem in three steps. Nothing distinguishes them. Directly contradicts `VISION.md:42`.

**R-2 — Green-suite substitution.** With no evaluator, "the tests pass" becomes the acceptance criterion. The tests are in the same tree, editable by the same actor, in the same commit. F-05 is the realized instance.

**R-3 — Undercounting that flatters.** F-03 discards repeated identical calls — i.e. the retry half of every before/after pair. F-02 records failures as successes. F-10 excludes failed turns from cost. All three biases point the same way: toward "things went fine".

**R-4 — Prompt compliance mistaken for mechanism.** Nine sentences injected into the first user message constitute the cycle's entire behavioural specification. If the model follows them, the transcript will *read* like a disciplined improvement cycle. That narrative is produced by the same model whose improvement is being assessed, and no artifact corroborates it.

**R-5 — Silent disablement misread as clean operation.** F-08, F-11 and F-16 all fail to a state where the plugin does nothing and says nothing. An empty ledger is indistinguishable from a well-behaved run, and `REQUIRES_MORE_EVIDENCE` looks identical in both cases.

**R-6 — Documentation as evidence.** `CYCLE.yaml:196-211` `gate_status` asserts `pass_deterministic_tests` for gates whose tests exercise fabricated payloads (F-01) or parameters no production path supplies (F-04). A reader — human or agent — checking gate status would conclude the capability exists.

**R-7 — Digest theatre.** The manifest digest looks like an integrity control. It is computed once, never re-checked (F-19), does not bind the candidate version (F-07), and the one recorded in the benchmark does not match the shipped file (F-21).

---

## 11. Causality analysis

To claim "change C improved system S at task T", you need: a fixed T defined before C; a baseline measurement of S on T; C isolated from everything else; a measurement of S+C on T using an evaluator C could not modify; a comparison against a threshold set before the measurement; and a way to undo C.

| Requirement | v0.20.0 |
|---|---|
| Task defined before the change | ❌ never recorded |
| Reproducible baseline | ❌ HEAD only, no dirty set (F-13), broken in worktrees (F-12) |
| Isolated candidate | ❌ same mutable tree |
| Evaluator the candidate cannot modify | ❌ tests live in the tree (F-05) |
| Threshold fixed in advance | ❌ none |
| Before/after comparison | ❌ no mechanism |
| Rollback | ❌ none (F-18) |

**Zero of seven.** No causal claim about Aether improving is currently supportable. Correlational claims are also compromised by F-02, F-03, F-10 and F-11, each of which biases the counts.

**Terminology, applied honestly:**

| Term | Definition | v0.20.0 |
|---|---|---|
| Telemetry | Recording what happened | ✅ **this is what exists** |
| Learning | Durable behaviour change from experience | ❌ |
| Adaptation | Behaviour varies with context | ⚠️ prompt injection only |
| Automatic repair | Detects and fixes a fault without human action | ❌ |
| Optimization | Improves a metric under fixed semantics | ❌ |
| **Self-improvement** | Measurably better at a task distribution, causally attributed, independently evaluated | ❌ |
| Self-editing without proof | Modifies itself with no independent verification | ⚠️ **this is the current risk posture** |

---

## 12. Isolation and rollback analysis

**Project isolation.** Design intent is right (verify identity, fail closed, never touch another project). The committed branch achieves it. The audited working tree does not (F-06). Identity itself is weak-but-adequate for a trusted local model: two files with predictable contents (`AGENTS.md` first line, `pyproject.toml` name). Anyone who can write those files can claim to be Aether — acceptable, since anyone who can do that can already write the ledger directly. Adversarial hypothesis 10 is confirmed but **low impact**.

**Ledger isolation.** Good: project-local path, symlink refusal on both the directory and the file, `0600` creation before open, path constrained by manifest validation. `.aether/` at `0755` is the only nit (F-22).

**Process isolation.** None. The observer runs inside the observed process. A Hermes crash takes the observer with it, and a crash between a durable effect and its record leaves no trace (T-05).

**Change isolation.** None. Framework repairs are written directly into the working tree that is simultaneously the baseline, the candidate and the evaluator.

**Rollback.** Absent (F-18). The only recovery is manual `git`, performed by the same actor, in the same tree, with no record of what the baseline was.

---

## 13. Architecture options

Assessed against: causality, self-deception resistance, isolation, rollback, complexity, cost, latency, maintainability.

| | Option | Causality | Deception resistance | Isolation | Rollback | Complexity | Cost/latency | Verdict |
|---|---|---|---|---|---|---|---|---|
| **A** | Plugin inside the Hermes process *(current)* | ✗ | ✗ | Weak | ✗ | Low | Negligible | **Keep as the collector only** |
| **B** | Separate write-only observer process | ✗ | ~ | Good | ✗ | Medium | Low | Solves crash-consistency; solves nothing about causality. Not worth it yet |
| **C** | Ledger derived from authoritative Olympus/kernel events | ~ | Good | Good | ✗ | High | Low | **Right long-term source for coordination facts.** Blocked while Harmonia is off; premature now |
| **D** | External immutable evaluator | ✅ | ✅ | ✅ | n/a | Medium | Low | **Essential.** The single highest-value missing piece |
| **E** | Changes executed in disposable worktrees/sandboxes | ✅ | Good | ✅ | ✅ | Medium | Medium | **Essential.** Note: blocked today by F-12 |
| **F** | Full pipeline candidate → benchmark → acceptance → promotion → rollback | ✅ | ✅ | ✅ | ✅ | High | High | Correct destination; too large for one increment |
| **G** | Hybrid: model proposes, deterministic controls admit/evaluate/promote | ✅ | ✅ | ✅ | ✅ | Medium | Medium | **Recommended target.** Matches the existing kernel philosophy |
| **H** | Keep v0.20.0 as instrumentation only; defer real self-improvement | n/a | ✅ | n/a | n/a | Minimal | None | **Recommended now** |

### Recommendation: **H now, then the D+E subset of G.**

Rationale. The temptation is to conclude that v0.20.0 needs a bigger architecture. It does not. What it needs is to **stop describing itself as a cycle** and to add the two smallest components that make causality possible: an evaluator the candidate cannot edit (D), and a disposable place to run the candidate (E). Options B, C and F are all defensible and all premature — B solves a problem (crash consistency) that only matters once evidence is trustworthy; C depends on a Harmonia that is switched off; F is a platform, and building a platform before a single causal measurement has ever been taken is exactly the failure PDR-0009 was written to prevent.

Explicitly **not** recommended: a distributed evaluation service, a message bus, a separate evaluator daemon, or an LLM-backed coordinator. None is needed to answer the question "did this change make Aether better at task T?"

---

## 14. Minimum sufficient design for real self-improvement

Four components. Roughly 400-600 lines total, no new services, no new dependencies.

**① Task record (the missing noun).** One row per improvement attempt: `task_id`, a human-written task statement, the acceptance criterion **written before the change**, `baseline_commit`, `baseline_dirty_digest`, `created_at`. Written once, immutable thereafter. Without this the system does not know what it is trying to improve.

**② Frozen evaluation set (option D).** A directory of task fixtures plus an expected-outcome file, with `evaluation_digest = sha256` over the whole set. Recorded in the task record at baseline and re-verified at acceptance. **If the digest changed between baseline and acceptance, the result is `INVALID`, not `IMPROVED`.** This single rule mechanically prevents F-05 from recurring, and it is perhaps twenty lines of code.

**③ Disposable candidate worktree (option E).** `git worktree add` a throwaway tree; apply the candidate change there; run the frozen evaluation against it; record the result; discard the worktree. Rollback becomes free and total. Requires F-12 fixed first.

**④ Comparison and promotion gate.** Run the frozen evaluation twice — once against the baseline commit, once against the candidate — in the same session, and record both. Promotion requires: no regression on the frozen set, the acceptance criterion met, the evaluation digest unchanged, the baseline dirty digest empty, and an explicit product-owner approval. Promotion is a **separate, human-triggered** step; evaluation never promotes.

Everything already built — manifest, ledger, redaction, hooks, atomic writes, reconciliation, evidence projection — is retained unchanged and becomes the substrate these four components record into.

**What must be measured, per the project's own objectives:** requested-outcome achieved (owner-assigned, not model-assigned); scope fidelity (was anything added that was not asked for — Objective 2); technical defects found post-hoc (Objective 3); evidence actually executed (Objective 6); cost, latency and rework; regressions on the frozen set. Note that four of these six cannot be self-assigned by the system under evaluation.

---

## 15. Implementation plan — three phases

### Phase 1 — Make the instrumentation truthful *(no new capability)*
Prerequisite for everything else. Fixes only what is already claimed.

1. Adopt the committed branch's `hooks.py` and its three isolation tests; resolve the two-copy divergence (F-05, F-06).
2. Fix the Harmonia classifier against the real wire contract, importing `HARMONIA_ERROR_CODES` and the kernel state set so drift breaks the build (F-01).
3. Use Hermes' host-supplied `status` instead of re-deriving it (F-02).
4. Add `schema_version`, then make the tool/coordination keys composite `(session_id, id)` with a sequence column (F-16, then F-03).
5. Lazily initialize in `post_tool_call` / `post_llm_call` (F-11).
6. Fix `_git_head` for linked worktrees (F-12).
7. Pin `candidate_version` to its directory (F-07).
8. Record turn outcomes in their own table; stop latching session status (F-14).
9. Record the baseline dirty digest (F-13).
10. Correct the documentation in §9 F-20 and F-21; either wire router telemetry or delete the claim (F-09); decide the `talk_to` question (F-17).

**Exit criterion:** every `gate_status: pass` line in `CYCLE.yaml` is backed by a test that exercises a real payload or a real production call path.

### Phase 2 — Make causality possible
1. Task record ①.
2. Frozen evaluation set ② with digest verification and the `INVALID` rule.
3. Extend the evidence projection to carry the task, the criterion, both measurements and the digest — or to state explicitly that it carries none.

**Exit criterion:** one real improvement, measured before and after against an unmodified frozen set, with the comparison reproducible from the ledger by a third party.

### Phase 3 — Make it safe and repeatable
1. Disposable candidate worktrees ③.
2. Promotion gate ④ with explicit owner approval.
3. Only then: activation of the plugin in a disposable pilot profile, with a documented teardown.

Harmonia activation, keys, runtime restart, merge, tag, release, deployment and publication remain outside all three phases, exactly as `CYCLE.yaml` states.

---

## 16. Exact acceptance tests

Phase 1:
1. `test_harmonia_classification_matches_real_contract` — for each of the 13 codes in `HARMONIA_ERROR_CODES` and each of the 9 states in `harmonia_service._STATES`, build the real envelope and assert a non-`unknown` phase. Import the constants; do not restate them.
2. `test_tool_outcome_uses_host_status` — assert `{"success":false}`, `{"ok":false,"error":null}`, `{"status":"failed"}`, `{"errors":[...]}` never classify as `success`.
3. `test_identical_tool_call_ids_in_two_sessions_are_both_recorded` — 2 rows, `evidence_counts.tool_calls == 2`.
4. `test_repeated_identical_call_in_one_session_is_counted_twice` — the retry case.
5. `test_environment_cannot_redirect_a_foreign_workspace_into_aether` — restore verbatim from the branch.
6. `test_nested_foreign_repository_cannot_inherit_parent_aether_identity` — restore verbatim.
7. `test_aether_subdirectory_resolves_the_nearest_repository_root` — restore verbatim.
8. `test_git_head_resolves_a_linked_worktree` — create a real `git worktree`; assert it equals `git rev-parse HEAD`.
9. `test_incompatible_ledger_schema_fails_loudly` — v0 database → explicit refusal or migration, never silent zero-evidence.
10. `test_session_evidence_survives_a_continuation` — first hook is `post_tool_call`; a record still exists.
11. `test_reused_session_id_with_different_manifest_does_not_merge`.
12. `test_manifest_digest_is_reverified_at_finalization`.
13. `test_candidate_version_must_match_its_release_directory`.
14. `test_interrupted_turn_does_not_permanently_poison_the_session`.
15. `test_baseline_records_dirty_worktree_digest`.
16. `test_authorized_gate_does_not_silently_disable_the_cycle`.
17. `test_post_llm_call_hook_signature_matches_hermes` — import the real invocation kwargs from `agent/turn_finalizer.py` (or pin them in a fixture reviewed against it) and assert the hook tolerates exactly that set.

Phase 2:
18. `test_evaluation_digest_change_invalidates_the_comparison` — mutate the frozen set between baseline and acceptance; assert the verdict is `INVALID`, never `IMPROVED`. **This is the anti-F-05 test.**
19. `test_causal_claim_requires_both_measurements`.
20. `test_dirty_baseline_blocks_a_causal_claim`.
21. `test_signal_is_derived_from_the_comparison_not_a_default`.

Phase 3:
22. `test_candidate_runs_in_a_disposable_worktree_and_leaves_no_trace`.
23. `test_promotion_requires_explicit_owner_approval`.
24. `test_rollback_restores_the_baseline_exactly`.

---

## 17. Claims Aether cannot yet make honestly

1. "Aether improves itself." — No causal machinery exists.
2. "Every Hermes session in Aether participates in the cycle." — The plugin is enabled nowhere; continuations never initialize.
3. "Pre- and post-admission failures are distinguished." — 0 of 9 post-admission states classify.
4. "Router metadata is recorded." — Hermes never sends it.
5. "Another project cannot mutate the Aether cycle." — False in the audited working tree.
6. "The cycle produces a next-version signal from evidence." — It is a constant.
7. "Release evidence demonstrates quality." — It counts calls.
8. "The v0.20.0 implementation is verified by 23 passing tests." — The candidate's own suite is 26; the 23-test tree fails 2 of the missing 3.
9. "Full repository suite: 1170 passed." — That is the dirty-tree figure; the clean candidate is 1163, and one run in five was red.
10. "Interrupted sessions are preserved and reconciled." — Preserved, yes; reconciled, no — the state is permanent.
11. "The manifest guarantees the loaded candidate is v0.20.0." — It does not check.
12. "There is a safe direct-takeover protocol." — There is a sentence about one.

**What Aether *can* honestly claim today:** v0.20.0 provides a default-off, project-scoped, privacy-preserving session ledger with strict manifest validation, exactly-once initialization for distinct session IDs, atomic tool/coordination writes, in-process concurrency preservation, crash-conservative reconciliation, and a deterministic release-evidence projection that never approves a version. That is a real and useful contribution. It is instrumentation, and it should be named as such.

---

## 18. Questions that genuinely require the product owner

**Q1 — Should v0.20.0 be renamed?** The name "Self-Improvement Cycle Bootstrap" is the source of most of the mismatch. "Self-Improvement Instrumentation" or "Cycle Telemetry Substrate" would make every current document true without changing a line of code. *Recommendation: rename; keep the version number.*

**Q2 — `talk_to` (F-17).** Restore it until Harmonia can actually be activated, or accept that the versioned template ships a configuration with no delegation path? *Recommendation: restore it in the template and keep its exclusion in the dogfood profile only — the current template makes the product strictly less capable for anyone who installs it.*

**Q3 — What is the task distribution to improve on?** Real Aether sessions, a fixed synthetic set, or the external comparison against Claude Code / Codex that `OBJECTIVES.md` Objective 1 already names? This determines whether the frozen evaluation set is 5 fixtures or a benchmark harness. *This cannot be decided from the code.*

**Q4 — Who assigns "the user got what they asked for"?** Objective 2 (scope fidelity) and Objective 1 (quality) are owner judgements. Should the system prompt for a one-line verdict at session end, or is that friction the product is designed to eliminate? *This is the single hardest question and it gates Phase 2.*

**Q5 — Should the authorization block gate behaviour or only record it (F-08)?** Today, granting a gate deletes the cycle. What should `harmonia_activation: authorized` actually *do*?

**Q6 — Router telemetry (F-09).** Upstream a `post_llm_call` payload extension to Hermes Agent, or drop the efficiency dimension from the contract?

**Q7 — Which of the two candidate copies is authoritative (F-05)?** The clean branch is better in every respect. Confirm that the main worktree's copy is stale and may be refreshed.

---

## 19. Verification commands and results

All commands run from `/home/arty/Escritorio/agentes/aether` unless noted. No repository file was modified.

```
$ git rev-parse --abbrev-ref HEAD ; git rev-parse HEAD
docs/canonical-product-documentation
a88b5ccefe317b5794a445c117b89b570f7845c4

$ git status --porcelain=v1 | wc -l
131

$ git worktree list
/home/arty/Escritorio/agentes/aether               a88b5cc [docs/canonical-product-documentation]
/home/arty/Escritorio/agentes/aether-v020-isolated 48635b4 [feature/v0.20.0-self-improvement-bootstrap]

$ .venv/bin/python -m pytest tests/test_self_improvement.py -q
23 passed in 0.23s

$ .venv/bin/python -m pytest tests/ -q          # run 1 of 5
1 failed, 1169 passed in 23.79s
    FAILED tests/coordination/test_v0194_successor_handoff.py::
           test_two_independent_contexts_reconcile_committed_b_once
    olympus_v3.coordination.workflow.AuthorityError: writer authentication failed

$ .venv/bin/python -m pytest tests/ -q          # runs 2-5
1170 passed in 23.25s / 22.92s / 23.34s / 23.05s

$ .venv/bin/python -m pytest tests/coordination/test_v0194_successor_handoff.py -q   # x3
14 passed in 3.35s   (isolated: always green)

# clean committed candidate
$ cd ../aether-v020-isolated && git status --porcelain | wc -l
0
$ PYTHONPATH=.../aether-v020-isolated/src ... -m pytest tests/test_self_improvement.py -q
26 passed in 0.26s
$ PYTHONPATH=.../aether-v020-isolated/src ... -m pytest tests/ -q
1163 passed in 26.16s

# the three deleted isolation tests, run against the audited working tree
$ ... -m pytest <branch test file> -k "environment_cannot_redirect or nested_foreign or subdirectory_resolves"
2 failed, 1 passed, 23 deselected in 0.15s
```

Adversarial probes (scratchpad scripts, synthetic projects under `tempfile.mkdtemp`, deleted afterwards):

```
PROBE 1  Harmonia real payloads
  public_error feature_disabled        -> ('pre_admission','feature_disabled')  outcome='error'
  success state=session_bound          -> ('unknown','unknown')                 outcome='success'
  public_error admission_limit         -> ('unknown','admission_limit')         outcome='error'
  status state=reconciliation_required -> ('unknown','unknown')                 outcome='success'

PROBE 2  _tool_outcome on failures without an 'error' key
  {"success": false} / {"ok":false,"error":null} / {"status":"failed"}
  / {"errors":["boom"]} / {"ok":false,"state":"reconciliation_required"}  -> all 'success'

PROBE 3  cwd = foreign project, AETHER_PROJECT_ROOT = aether-shaped root
  ledger created: True
  row written:   session_id='foreign-session-via-env', status='active'
  same via explicit project_root kwarg: True

PROBE 4  candidate_version 9.9.9 inside docs/releases/v0.20.0/CYCLE.yaml
  verify_project_identity -> ACCEPTED, candidate_version='9.9.9'

PROBE 5  authorization.<gate> = authorized
  harmonia_activation / runtime_restart / merge -> verify_project_identity=None (silent)

PROBE 6  tool_call_id='call_1' from two sessions
  session-A: 1 row   session-B: 0 rows   evidence_counts.tool_calls=1  (expected 2)
  coordination_events: identical loss

PROBE 7  session_id reuse with a different manifest digest
  stored candidate_version='0.20.0', manifest_digest='sha256:AAA', baseline='aaaaaaaa…'  (old values kept)

PROBE 8  privacy of SQLite sidecars
  self_improvement.db 0600 · -shm 0600 · -wal 0600 · .aether/ 0755

PROBE 9  _git_head
  main worktree (.git dir)      -> a88b5ccefe317b5794a445c117b89b570f7845c4   (== git rev-parse)
  linked worktree (.git file)   -> unknown                                    (git rev-parse: 48635b41…)

PROBE 10 pre-existing v0 ledger schema
  columns ['session_id','legacy_col'] · rows after on_session_start: 0 · warning only

PROBE 11 turn outcomes
  ok -> active · Ctrl-C -> reconciliation_required · 3 more ok turns -> reconciliation_required
  after finalize -> reconciliation_required, finalized_at set
  aggregate_next_version_signal -> 'REQUIRES_MORE_EVIDENCE'

PROBE 12 post_llm_call with Hermes' verbatim kwargs (turn_finalizer.py:484-494)
  NULL: api_request_id, resolved_route, resolved_model, latency_ms,
        input_tokens, output_tokens, reported_cost, error_code

PROBE 13 crash after admission, before post_tool_call
  status=active · tool_calls=0 · coordination_events=0

PROBE 14 manifest mutated mid-session
  no re-verification; evidence continues under the stale digest

# same probes against the clean committed candidate
  _harmonia_classification / _tool_outcome / _git_head: identical results
  (only the isolation defect differs between the two copies)
```

Digest verification:

```
$ sha256(docs/releases/v0.20.0/CYCLE.yaml)  = sha256:7b715d2e176aca92fcf78268f38dc9002309cc819a3f9bfe71db380e1331df26
  SELF_IMPROVEMENT_EVIDENCE.md records         sha256:7b715d2e…   (matches)
  BENCHMARK_REPORT.md records                  sha256:fd74b601…   (stale)
```

Real ledger, opened read-only:

```
$ sqlite3 'file:.aether/self_improvement.db?mode=ro'
  cycle_sessions 0 · tool_calls 0 · model_calls 0 · coordination_events 0
```
Consistent with `BENCHMARK_REPORT.md`'s claim of zero lifecycle sessions.

**Disclosure:** opening that WAL-mode database read-only caused SQLite to materialize `.aether/self_improvement.db-wal` (0 bytes) and `.aether/self_improvement.db-shm`. `.aether/` is gitignored; no ledger row was written; no tracked file changed. Both sidecars were created `0600`, which is itself the empirical confirmation of invariant I-15 on the real repository.

---

## 20. Files inspected

**Aether — product and governance:** `AGENTS.md`, `README.md`, `docs/AGENT_ONBOARDING.md`, `docs/product/VISION.md`, `docs/product/OBJECTIVES.md`, `docs/product/PRINCIPLES.md`, `docs/product/COMPLETION.md`, `docs/knowledge/AUTHORITY.md`, `docs/knowledge/SELF_IMPROVEMENT_CYCLE.md`, `docs/decisions/PDR-0009-semver-self-improvement-cycle.md`, `docs/releases/v0.19.x-kernel-migration/ROADMAP_CLOSEOUT.md`.

**Aether — v0.20.0 candidate:** `docs/releases/v0.20.0/CYCLE.yaml`, `IMPLEMENTATION_REPORT.md`, `BENCHMARK_REPORT.md`, `SECURITY_REVIEW.md`, `SELF_IMPROVEMENT_EVIDENCE.md`.

**Aether — source:** `src/olympus_v3/self_improvement/{__init__,manifest,ledger,hooks,evidence}.py`, `src/olympus_v3/server.py`, `src/olympus_v3/config_loader.py`, `src/olympus_v3/coordination/{harmonia_service,harmonia_contract}.py`.

**Aether — configuration and tests:** `home/config.yaml.template`, `home/plugins/aether-self-improvement/{plugin.yaml,__init__.py}`, `tests/test_self_improvement.py`, `.gitignore`.

**Aether — committed candidate (branch `48635b4`):** `hooks.py`, `tests/test_self_improvement.py`, `IMPLEMENTATION_REPORT.md`, `BENCHMARK_REPORT.md`, `SECURITY_REVIEW.md`, `SELF_IMPROVEMENT_CYCLE.md`.

**Hermes Agent (`/home/arty/.hermes/hermes-agent`), read-only:** `hermes_cli/plugins.py`, `agent/turn_finalizer.py`, `agent/turn_context.py`, `agent/conversation_loop.py`, `model_tools.py`, `agent/codex_responses_adapter.py`, `agent/chat_completion_helpers.py`.

No `.env`, `auth.json`, token, cookie or credential file was opened at any point.

---

## 21. Modification statement

The only file this audit created or modified inside the repository is:

```
docs/releases/v0.20.0/EXTERNAL_LOGIC_AUDIT.md
```

No commit, push, merge, rebase, reset, checkout, stash or clean was performed. No plugin, service, gateway, Harmonia instance or persistent process was activated. No runtime was restarted. No credential or coordination key was created. No existing code, configuration, test or document was altered.

The 131-entry dirty working tree recorded in the header pre-existed this audit and is unchanged by it, with one disclosed exception: read-only inspection of the gitignored `.aether/self_improvement.db` caused SQLite to create the zero-byte `-wal` and `-shm` sidecar files described in §19. No tracked file and no database row was affected.

All adversarial probes ran against synthetic projects under `tempfile.mkdtemp`, outside the repository, and were deleted on completion.

### Concurrent third-party activity observed during the audit

The working tree changed **while this audit was running**, from activity that is not the auditor's. Between the opening `git status` (131 entries) and the closing one (135), the following appeared, none of them written by this audit:

| Path | State | mtime |
|---|---|---|
| `home/prompts/` (and `home/prompts/hermes/`) | new, untracked | 12:09 |
| `home/SOUL.md` | modified | 12:11 |
| `docs/decisions/PDR-0010-hermes-prompt-versioning-and-promotion.md` | new, untracked | 12:12 |

These are recorded, not attributed and not altered. They are noted here for two reasons. First, honesty about the audit's own baseline: the tree it measured was not stable for the duration of the measurement. Second, and more usefully, this is a **live instance of F-13 and F-05** — a second actor writing into the same working tree that simultaneously serves as baseline, candidate and evaluator, with no mechanism anywhere in v0.20.0 that would detect the overlap, attribute the changes, or prevent them from being folded into the next "before/after" comparison. The audit did not have to construct this scenario; it occurred unprompted within roughly three hours of the candidate being written.
