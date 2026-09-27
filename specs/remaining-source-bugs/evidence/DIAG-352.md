# DIAG-352 — bounded concurrent lifecycle CAS result diagnosis (#352)

## Disposition

**Inconclusive on the product surface; exact residual question named. No causal RED, no
product or fixture change. Issue #352 stays OPEN.**

This unit reused the retained 4 sequential + 8 bounded-concurrent + 20 further sequential
green runs and did **not** repeat them, per `plan.md` §"#352 and #444 — bounded intermittent
diagnosis" and the contract's stop conditions. Instead it inspected current source and
history for a concrete clue, then executed **one** focused discriminating check with a
**proven-to-fail negative control**. No causal product or fixture defect was reproduced, so
no correction was made. Only this evidence file was committed; no product or fixture
source was changed.

Unit compatibility impact: `none` (diagnosis only; `src/aether_agents/lifecycle.py` and
`tests/test_observation_lifecycle.py` are byte-unchanged from the base commit).

## Contract and source receipt

- Objective Contract: `oc_3f280963213d234e@v1`
- Contract SHA-256: `2b10b433911293a00879aba0c48d24c895012b79ccbb5e0bb9a91c60bd1adfa0`
  (recomputed from `.aether/objective-contracts/oc_3f280963213d234e/v1.md` at run time)
- Aether base: `8721f54b9a2d3be4638812f5fd660800ed07bd41`
- Source revision examined: `8721f54b9a2d3be4638812f5fd660800ed07bd41`.
- Evidence-file commit: `5ece4f76af71325b487e6dee15edcb9a6c67d7c5`
  (no product or fixture source delta).
- Supervisor breakdown: `dabeeb6af25d18d3e2dc7307673159d418c49ac0`
- Changed files in this unit: this evidence file only.
- Issue source: https://github.com/DarkArty07/Aether-Agents/issues/352 (observed `OPEN`
  at the start of this run via `gh issue view`).

Source hexsha receipts measured on HEAD at the start of this unit:

- `tests/test_observation_lifecycle.py` — `git rev-parse HEAD:...`/blob compared against the
  FU-352 qualification revision; the named test body is byte-identical to that revision
  (see "Named-test identity" below).
- `src/aether_agents/lifecycle.py` — differs from the FU-352 qualification revision
  (3921 insertions, 251 deletions since `ba100d14`). Only one of those deltas lies inside
  this named test's critical section, and it is the clue this unit pursued.

Relevant source anchors (HEAD):

- `tests/test_observation_lifecycle.py:101-138` — `_run_cas_transition`: spawn-safe
  contender; constructs `ReleaseStore`, signals the per-child ready event, waits on the
  shared start event, takes `store.mutation_lock()`, calls `begin_transition`, calls
  `activate_existing`, maps `IntegrityError` to `ACTIVE_RELEASE_CAS_MISMATCH`/`stale`, maps
  success to `committed`, converts **every** other `BaseException` to
  `f"error:{type}"`, and finally `results.put(outcome)`.
- `tests/test_observation_lifecycle.py:3023-3076` — the named test: two real `spawn`
  children, per-child ready events, one shared start event, the unmodified 10 s result and
  join deadlines, per-child exit-code assertions, exactly one `committed` + one `stale`,
  one journalled `committed` + one journalled
  `failed`/`ACTIVE_RELEASE_CAS_MISMATCH`.
- `src/aether_agents/lifecycle.py:2119-2146` — `mutation_lock`: thread-local reentrancy
  dict plus a cross-process `fcntl.flock(LOCK_EX)` on a private, inode-verified lock file.
- `src/aether_agents/lifecycle.py:2411-2430` — `_commit_active`: retained expected-active
  CAS check, then the atomic active-pointer write.
- `src/aether_agents/lifecycle.py:2470-2487` — `activate_existing`.
- `src/aether_agents/lifecycle.py:2373-2409` — `_target_active_payload` (the newest seam;
  see below).

## Named-test identity

`git show ba100d1470ee79e7f7de60e53a5f4f4c8e8098e7:tests/test_observation_lifecycle.py`
lines 2690-2743 are byte-identical to HEAD lines 3023-3076. The FU-352 1/1, 20/20
sequential and 16/16 bounded-concurrent passes therefore describe **this** fixture.
`src/aether_agents/lifecycle.py` is **not** byte-identical. The relevant critical
section now calls `_target_active_payload`, so the older green runs do not cover
its current implementation even though the named fixture body is unchanged.

## Concrete current-source clue (found by inspection, not by rerunning the green test)

The retained green evidence is attributed to revisions whose `_commit_active` tail was:

```python
_atomic_json(self.active_pointer, asdict(record))
```

Commit `f426c829` ("fix(lifecycle): honor target release semantics") introduced
`ReleaseStore._target_active_payload` and wired it into `_commit_active`, so on HEAD the
same critical section additionally performs an inode-verified `stat` pair plus a
`record.json` read **inside the cross-process mutation lock**, per child, per activation.

This was established from history rather than assumed:

| Revision | `grep -c _target_active_payload` |
| --- | --- |
| `ba100d1470ee79e7f7de60e53a5f4f4c8e8098e7` (FU-352 qualification) | `0` |
| `410c172ae69ffa87f6e32960ae4aef3b8d6598f0` (20/20 comment) | `0` |
| `8721f54b` (this unit's base) | `5` |

So the retained 4 sequential + 8 bounded-concurrent + 20 sequential passes do **not**
exercise the present critical section, which makes this seam the one current, source-backed
place a *new* `_queue.Empty` mechanism could have entered after the evidence was taken.

## The one focused discriminating check

Two arms on the **unchanged** fixture body (identical `spawn` children, identical ready/start
gating, identical real `ReleaseStore` mutation lock / CAS / journals, the existing unmodified
10 s deadline, the existing one-commit assertions). Only a child-side fault differs. No source
file is edited; the injected fault lives in memory inside the child process only.

**Arm A (current source, no fault).** Reproduces the named test's critical section and
records per-stage timestamps so any failure is classified as admission, critical-section,
result-publication, exit-code, or CAS/candidate.

**Arm B (oracle; child-only fault).** Replaces `_target_active_payload` **in the spawned
child only** with a function raising a non-`IntegrityError`, forcing the OUTER
`except BaseException` path of `_run_cas_transition` — exactly the path that would produce a
missing child result if the fixture failed to publish it.

**Negative control (oracle power proof).** The same arm B with child 0's `results.put`
suppressed. This must report `RESULT_PUBLICATION` / `_queue.Empty`, otherwise a green Arm B
would be vacuous.

| Check (exact command) | Observed result |
| --- | --- |
| Baseline sanity: `HERMES_TEST_FILE_RETRIES=0 uv run --frozen python scripts/run_tests.py -- -q --tb=short tests/test_observation_lifecycle.py::test_two_process_transitions_with_one_expected_active_have_one_commit` | `1 passed in 0.96s` |
| Arm A: 10 trials × 2 spawned children, unmodified 10 s deadline, current source | 10/10 `verdict=OK`; outcomes exactly `['committed','stale']` every trial; `journal_states=['committed','failed']`, `journal_failure_codes=['ACTIVE_RELEASE_CAS_MISMATCH']`, `active_is_candidate=True`, `one_commit_invariant_ok=True` every trial; both children reached `published` every trial; `stage_published_per_trial=[2]*10`; `result_seconds` min `0.0671`, median `0.0822`, max `0.1263`; critical-section seconds n=20, min `0.0046`, median `0.0080`, max `0.0138`; `queue_empty_count=0` |
| Arm B: 6 trials × 2 spawned children with the injected non-`IntegrityError` at the newest seam | 6/6 `verdict=OK`; **both** children still reached `published` every trial (`stage_published_per_trial=[2]*6`); outcomes `['error:RuntimeError','error:RuntimeError']` (the outer `except BaseException` path); every child `exitcode=0`; `result_seconds` min `0.0659`, median `0.0848`, max `0.1144`; `queue_empty_count=0` |
| Negative control: 2 trials, child 0's `results.put` suppressed | 2/2 `verdict=RESULT_PUBLICATION`; `collect_failure='_queue.Empty'`; `result_seconds` `10.0077` and `10.0012` (the full unmodified deadline); child 0 `exitcode=0` — reproducing the historical symptom exactly |

The negative control reproduced the historical signature (`_queue.Empty`, deadline fully
consumed, child exit code 0), which proves Arm B's green result is a real observation rather
than a check that cannot fail.

## What the check establishes — and what it does not

Established (direct, this unit, current source):

1. On the current source, the named test's critical section meets its **unchanged** 10 s
   deadline by roughly two orders of magnitude (max observed 0.1263 s of 10 s) in an idle
   environment, and preserves the one-commit / one-`ACTIVE_RELEASE_CAS_MISMATCH` invariant.
2. In the injected non-`IntegrityError` case **inside the cross-process mutation lock at
   the newest post-qualification seam**, both children published a queue result and
   exited 0 in six idle-context trials. The current helper catches exceptions raised
   within its `try` block and attempts `results.put(outcome)` afterward. These trials
   do not exclude a lock stall beyond the deadline, an exception before that `try`
   (`ReleaseStore` construction, `ready.set` or `start.wait`), process termination,
   or a delayed/failed queue publication. No component is eliminated as the historical
   cause without the missing failure-time stage and exit evidence.

Not established (and cannot be established on this machine with the retained evidence):

3. The historical failure occurred in a **full canonical run** (`1 failed, 1059 passed,
   58 skipped, 373 subtests passed`), i.e. under a loaded, ~285 s pytest process with many
   other tests before and after it. This unit ran in an idle environment. A
   starvation/scheduling-in-full-suite-context mechanism was **not** reproduced.
4. The exact stage of the historical failure is still unknown — the original report never
   captured it, and no later recurrence has been recorded. The named test has no
   per-stage instrumentation upstream, and none was added (adding it would be a fixture
   change this unit is not authorized to make without a causal RED).
5. A child process hard death, lock/child stall, or queue publication/flush delay are
   **unresolved hypotheses**, not an exhaustive list or a determination that the
   lifecycle product surface is uninvolved. This unit did not establish which mechanism
   occurred in the historical full-suite failure.

## Exact residual question (the next investigation's target)

> In the **full canonical pytest run**, when `results.get(timeout=10)` raises
> `_queue.Empty`, what was the failing child's `exitcode` and `waitstatus`, and did the
> child reach `store.mutation_lock()`?
>
> Specifically: capture, at the failure site, (a) `child.exitcode` and `child.sentinel`
> state, (b) whether the per-child `ready` event was set, and (c) whether
> `store.root / "transitions"` contains that child's journal. The instrumentation must be a
> temporary diagnostic (a private scratch test, never a committed deadline increase or a
> weakened assertion) so that the retained one-commit invariant stays intact.

This is answerable **only** from a recurrence in the real full-suite context. Re-running the
named node, the sequential repetitions or the bounded-concurrent repetitions cannot answer
it, because those regimes have never reproduced it (1/1, 20/20, 16/16, 8/8, 4/4, 90/90 module,
plus this unit's Arm A 10/10 and Arm B 6/6).

## Verification matrix

| Obligation | Check actually run | Observed result |
| --- | --- | --- |
| Reuse retained evidence without repeating it | Inspected FU-352, its independent review continuation, the `410c172a` issue comment, `plan.md` §#352 and the Supervisor breakdown; consumed their producer/revision | 4 sequential + 8 bounded-concurrent + 20 sequential + 16 concurrent + module 90 all identified as prior work, attributed to their producers; none re-executed as a "fix" |
| Confirm the fixture the retained evidence describes | Byte-range diff of `ba100d14` lines 2690-2743 vs HEAD lines 3023-3076 | Identical |
| Find a concrete current clue | `git log -S`, targeted diffs and `grep -c` across `ba100d14`, `410c172a` and HEAD; AST-level function comparison of `mutation_lock`, `_open_mutation_lock`, `_acquire_platform_lock`, `begin_transition`, `_read_transition`, `_finish_transition_locked`, `finish_transition`, `activate_existing` | `mutation_lock`, `_open_mutation_lock`, `_acquire_platform_lock`, `begin_transition`, `_read_transition`, `_finish_transition_locked`, `finish_transition`, `activate_existing` **identically** implemented at both revisions; `_atomic_lifecycle_write` and the whole POSIX lock-open body byte-identical; the **only** delta inside this test's critical section is `_target_active_payload`, introduced by `f426c829` after the evidence was taken (`0` hits then, `5` now) |
| One focused discriminating check | Probe Arm A, 10 trials, real `spawn` children, real lock/CAS/journals, unchanged 10 s deadline | 10/10 `OK`; one-commit invariant held 10/10; max `result_seconds` `0.1263` |
| Discriminating power | Probe Arm B, child-only fault at the newest seam, 6 trials | 6/6 published both results; `_queue.Empty` count 0 |
| Oracle can fail (negative control) | Probe Arm B with child 0's `results.put` suppressed, 2 trials | 2/2 `RESULT_PUBLICATION` / `_queue.Empty`, `result_seconds≈10` |
| Preserve the unmodified named test | `git status` / `git diff` after the unit | `src/aether_agents/lifecycle.py` and `tests/test_observation_lifecycle.py` byte-unchanged; only this evidence file added |
| Named test still green on the candidate | `HERMES_TEST_FILE_RETRIES=0 uv run --frozen python scripts/run_tests.py -- -q --tb=short tests/test_observation_lifecycle.py::test_two_process_transitions_with_one_expected_active_have_one_commit` | `1 passed in 0.96s` |
| Touched-file lint | `uv run --frozen ruff check src/aether_agents/lifecycle.py tests/test_observation_lifecycle.py` | Passed: `All checks passed!` |
| Touched-file format | `uv run --frozen ruff format --check src/aether_agents/lifecycle.py tests/test_observation_lifecycle.py` | Passed: `2 files already formatted` |
| Syntax | `uv run --frozen python -m compileall -q src/aether_agents/lifecycle.py tests/test_observation_lifecycle.py` | Passed |
| Documentation gate (evidence file is documentation under `specs/`) | `uv run --frozen python scripts/check_documentation.py` | Passed |
| Patch whitespace | `git diff --check` | Passed; no trailing whitespace or blank-line-at-EOF defects |

NOT RUN in this unit (declared, not claimed): full canonical runner, affected-module
90-test run, MyPy across `src/aether_agents`, stress/concurrent repetitions, and any
live-board/profile/runtime/resource effect. The documentation gate was run (above);
the public-artifact scan was reported in the unit's review handoff, not in this table.
`scripts/run_tests.sh` does not exist in this repository; the Aether wrapper is
`scripts/run_tests.py`, which is what the exact-Hermes invocations above used.

## Remaining risk

- The historical mechanism is uncharacterized. This unit observed a short critical
  section and successful publication from an injected exception at one seam in an idle
  environment. Neither result excludes a lifecycle stall, exception before the helper's
  `try`, child failure or queue delay in the failing full-suite context. The required
  discriminating observation (a recurrence with per-stage capture) does not exist.
- The probe's environment (idle, 24-core, CPython 3.13.15, not inside a full pytest process)
  differs from the historical failure's environment. Load-sensitive starvation remains a
  live hypothesis that this unit cannot test without repeating the full-suite campaign the
  plan forbids.
- No live profile, board, database, provider, credential, activation, publication, push,
  PR, merge, or issue mutation was performed. No Objective Contract or plan file was
  created, copied, staged, committed or modified.

## Supervisor review correction

The original evidence candidate was commit `5ece4f76af71325b487e6dee15edcb9a6c67d7c5`.
In same-card review, Supervisor independently inspected the unchanged fixture and
lifecycle source, and ran the named test once on the candidate (`1 passed in 1.92s`).
Supervisor then made a bounded **documentation-only correction**: the original text
incorrectly said nothing had been committed, listed a passing documentation check as
NOT RUN, called a changed critical section identical, and inferred from idle fault
injection that lifecycle code could not cause a missing queue result. The final text
limits that conclusion to what the worker-reported probe observed; it does not certify
those probe measurements independently or claim the historical flake is fixed.
After the correction, `scripts/check_documentation.py`,
`scripts/check_public_artifacts.py --root .` and `git diff --check` all passed.
This verification of the Supervisor-authored delta is **not** an independent review
of that delta. The #352 issue remains OPEN. Unit conclusions: `release_impact=none`,
`release_action=defer`, `release_channel=none`.
