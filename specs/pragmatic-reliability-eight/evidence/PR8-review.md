# Evidence — PR8-REVIEW (#385)

**Unit:** PR8-REVIEW (`t_e6992ea2`)
**Objective:** `oc_c780a10d94b78d85@v1` (§R385, `plan.md` §D3 U-REVIEW)
**Issue:** #385 — review topology guidance cannot be mistaken for terminal integration
**Fork Repository:** `DarkArty07/aether-hermes`
**Base Commit (`origin/aether-main`):** `6551b7c31cc665d59103c6d89cb5e0c60666f803`
**Candidate Commit:** `9fba8552bba30004ab452823668a105dee1ee89d`
**Fork Branch:** `fix/pr8-385-review-guidance`
**Fork Pull Request:** https://github.com/DarkArty07/aether-hermes/pull/9

---

## 1. Description of Change

In `DarkArty07/aether-hermes`, `KANBAN_GUIDANCE` (in `agent/prompt_builder.py`) previously advised:
> "When any pre-created review, QA, or release child depends on your task, call `kanban_complete`: your implementation phase is done, and completion is what releases those children. Never sticky-block that parent for `review-required` and never request same-card review as well — either choice would strand or duplicate the downstream lane. Otherwise, when this same task needs review before it is final, call `kanban_request_review...`"

This wording caused workers to mistake terminal integration or release children as handling review for their unit, calling `kanban_complete` and bypassing unit review entirely.

### Corrected Guidance
The guidance in `agent/prompt_builder.py` is corrected to:
```text
5. **Finish with the review model encoded by the task graph.** Always include the structured handoff (`summary`, `metadata`) on the lifecycle transition itself; never put secrets, tokens, or raw PII in these durable fields. If `kanban_show()` lists child IDs, inspect those cards with `kanban_show(task_id=...)` before choosing the terminal action. A terminal integration, release, or evidence-only child alone does NOT replace unit review. Only when the card delivery or task graph explicitly identifies a distinct review/QA phase child depending on your task should you call `kanban_complete`: your implementation phase is done, and completion is what releases that downstream review lane. Never sticky-block that parent for `review-required` and never request same-card review as well — either choice would strand or duplicate the downstream lane. Otherwise, when this same task needs review before it is final, call `kanban_request_review(summary=..., metadata=..., reviewer=<optional-profile>)`. The reviewer approves with `kanban_complete`, returns actionable rework with `kanban_request_changes`, or uses `kanban_block` only for a genuine external escalation. Review is not a block, so repeated review cycles do not trip unblock-loop detection.
```

### Test Updates
In `tests/hermes_cli/test_kanban_review_surfaces.py`:
- Updated `test_worker_guidance_distinguishes_same_card_and_downstream_review` to assert:
  - `"A terminal integration, release, or evidence-only child alone does NOT replace unit review" in KANBAN_GUIDANCE`
  - `"Only when the card delivery or task graph explicitly identifies a distinct review/QA phase child" in KANBAN_GUIDANCE`
  - `"pre-created review, QA, or release child" not in KANBAN_GUIDANCE`
- Added `test_worker_guidance_terminal_child_does_not_replace_review` regression test asserting the same invariants.

---

## 2. Verification Evidence

### 2.1 Regression-First Verification: RED on Pristine Base

Command run against pristine `origin/aether-main` (`6551b7c31c`) with updated test assertions (`HERMES_TEST_FILE_RETRIES=0`):
```bash
HERMES_TEST_FILE_RETRIES=0 uv run pytest tests/hermes_cli/test_kanban_review_surfaces.py -k "worker_guidance" -v
```

Observed Output (Exit Code 1, FAILED):
```text
============================= test session starts ==============================
platform linux -- Python 3.11.15, pytest-9.1.1, pluggy-1.6.0
cachedir: .pytest_cache
rootdir: /tmp/pr8-review-worktree
configfile: pyproject.toml
plugins: asyncio-1.3.0, anyio-4.12.1
collecting ... collected 12 items / 10 deselected / 2 selected

tests/hermes_cli/test_kanban_review_surfaces.py::test_worker_guidance_distinguishes_same_card_and_downstream_review FAILED [ 50%]
tests/hermes_cli/test_kanban_review_surfaces.py::test_worker_guidance_terminal_child_does_not_replace_review FAILED [100%]

=================================== FAILURES ===================================
______ test_worker_guidance_distinguishes_same_card_and_downstream_review ______
...
>       assert (
            "A terminal integration, release, or evidence-only child alone does NOT "
            "replace unit review"
        ) in KANBAN_GUIDANCE
E       assert 'A terminal integration, release, or evidence-only child alone does NOT replace unit review' in "# Kanban task execution protocol\n..."

tests/hermes_cli/test_kanban_review_surfaces.py:236: AssertionError
_________ test_worker_guidance_terminal_child_does_not_replace_review __________
...
>       assert (
            "A terminal integration, release, or evidence-only child alone does NOT "
            "replace unit review"
        ) in KANBAN_GUIDANCE
E       assert 'A terminal integration, release, or evidence-only child alone does NOT replace unit review' in "# Kanban task execution protocol\n..."

tests/hermes_cli/test_kanban_review_surfaces.py:265: AssertionError
=========================== short test summary info ============================
FAILED tests/hermes_cli/test_kanban_review_surfaces.py::test_worker_guidance_distinguishes_same_card_and_downstream_review
FAILED tests/hermes_cli/test_kanban_review_surfaces.py::test_worker_guidance_terminal_child_does_not_replace_review
======================= 2 failed, 10 deselected in 0.43s =======================
```

### 2.2 Candidate Verification: GREEN

Command run against candidate commit `9fba8552bb` (`HERMES_TEST_FILE_RETRIES=0`):
```bash
HERMES_TEST_FILE_RETRIES=0 uv run pytest tests/hermes_cli/test_kanban_review_surfaces.py -k "worker_guidance" -v
```

Observed Output (Exit Code 0, PASSED):
```text
============================= test session starts ==============================
platform linux -- Python 3.11.15, pytest-9.1.1, pluggy-1.6.0
cachedir: .pytest_cache
rootdir: /tmp/pr8-review-worktree
configfile: pyproject.toml
plugins: asyncio-1.3.0, anyio-4.12.1
collecting ... collected 12 items / 10 deselected / 2 selected

tests/hermes_cli/test_kanban_review_surfaces.py::test_worker_guidance_distinguishes_same_card_and_downstream_review PASSED [ 50%]
tests/hermes_cli/test_kanban_review_surfaces.py::test_worker_guidance_terminal_child_does_not_replace_review PASSED [100%]

======================= 2 passed, 10 deselected in 0.32s =======================
```

Full file run (`tests/hermes_cli/test_kanban_review_surfaces.py`):
```bash
HERMES_TEST_FILE_RETRIES=0 uv run pytest tests/hermes_cli/test_kanban_review_surfaces.py -v
```
Output:
```text
tests/hermes_cli/test_kanban_review_surfaces.py::test_review_tools_redact_handoff_and_route_changes PASSED [  8%]
tests/hermes_cli/test_kanban_review_surfaces.py::test_review_tools_are_gated_and_visible_to_kanban_workers PASSED [ 16%]
tests/hermes_cli/test_kanban_review_surfaces.py::test_review_cli_round_trip_preserves_handoff PASSED [ 25%]
tests/hermes_cli/test_kanban_review_surfaces.py::test_domain_and_cli_review_handoffs_redact_before_persistence PASSED [ 33%]
tests/hermes_cli/test_kanban_review_surfaces.py::test_worker_guidance_distinguishes_same_card_and_downstream_review PASSED [ 41%]
tests/hermes_cli/test_kanban_review_surfaces.py::test_worker_guidance_terminal_child_does_not_replace_review PASSED [ 50%]
tests/hermes_cli/test_kanban_review_surfaces.py::test_cli_reopen_review_is_transition_first_and_redacts_reason PASSED [ 58%]
tests/hermes_cli/test_kanban_review_surfaces.py::test_goal_mode_completion_handoff_still_requires_judge PASSED [ 66%]
tests/hermes_cli/test_kanban_review_surfaces.py::test_goal_mode_review_handoff_uses_readiness_not_completion_judge PASSED [ 75%]
tests/hermes_cli/test_kanban_review_surfaces.py::test_goal_readiness_phase_uses_a_distinct_prompt PASSED [ 83%]
tests/hermes_cli/test_kanban_review_surfaces.py::test_goal_loop_stops_after_reviewer_requests_changes PASSED [ 91%]
tests/hermes_cli/test_kanban_review_surfaces.py::test_cli_and_dashboard_receive_graph_aware_deadlock_diagnostic PASSED [100%]

============================== 12 passed in 1.95s ==============================
```

Prompt size invariant check:
```bash
HERMES_TEST_FILE_RETRIES=0 uv run pytest tests/tools/test_kanban_tools.py -k "test_kanban_guidance" -v
```
Output:
```text
tests/tools/test_kanban_tools.py::test_kanban_guidance_prompt_size_bounded PASSED [ 50%]
tests/tools/test_kanban_tools.py::test_kanban_guidance_orchestrator_decision_ownership PASSED [100%]

======================= 2 passed, 46 deselected in 0.87s =======================
```

### 2.3 Neighboring Review-Lifecycle Suites and Canonical Runner

Command:
```bash
scripts/run_tests.sh tests/hermes_cli/test_kanban_review_surfaces.py tests/hermes_cli/test_kanban_review_independence.py tests/hermes_cli/test_kanban_review_lifecycle.py tests/hermes_cli/test_kanban_review_lifecycle_complete.py
```

Observed Output (Exit Code 0, PASSED):
```text
▶ running per-file parallel test suite via run_tests_parallel.py
  (TZ=UTC LANG=C.UTF-8 PYTHONHASHSEED=0; clean env)
▶ pre-compiling bytecode cache
▶ launching test runner
Discovered 4 test files (~50 tests) under ['tests/hermes_cli/test_kanban_review_surfaces.py', 'tests/hermes_cli/test_kanban_review_independence.py', 'tests/hermes_cli/test_kanban_review_lifecycle.py', 'tests/hermes_cli/test_kanban_review_lifecycle_complete.py']; running with -j 24
[ 10.0% |     5/~50 | ✓5 | ✗0] ✓ tests/hermes_cli/test_kanban_review_independence.py (5✓, 1.6s)
[ 34.0% |    17/~50 | ✓17 | ✗ 0] ✓ tests/hermes_cli/test_kanban_review_surfaces.py (12✓, 2.8s)
[ 66.0% |    33/~50 | ✓39 | ✗ 0] ✓ tests/hermes_cli/test_kanban_review_lifecycle_complete.py (22✓, 3.5s)
[100.0% |    50/~50 | ✓58 | ✗ 0] ✓ tests/hermes_cli/test_kanban_review_lifecycle.py (19✓, 3.9s)

=== Summary: 4 files, 58 tests passed, 0 failed (100% complete) in 3.9s (24 workers) ===
```

### 2.4 Preservation of HLP-362 Invariant

Command:
```bash
HERMES_TEST_FILE_RETRIES=0 uv run pytest tests/hermes_cli/test_kanban_review_independence.py -v
```

Observed Output (Exit Code 0, 5/5 PASSED):
```text
tests/hermes_cli/test_kanban_review_independence.py::test_initial_review_without_independent_reviewer_fails_closed PASSED [ 20%]
tests/hermes_cli/test_kanban_review_independence.py::test_worker_review_tool_rejects_missing_reviewer PASSED [ 40%]
tests/hermes_cli/test_kanban_review_independence.py::test_implementer_cannot_select_itself_as_reviewer PASSED [ 60%]
tests/hermes_cli/test_kanban_review_independence.py::test_legacy_review_without_reviewer_cannot_be_claimed PASSED [ 80%]
tests/hermes_cli/test_kanban_review_independence.py::test_explicit_reviewer_can_claim_and_re_review_reuses_provenance PASSED [100%]

============================== 5 passed in 0.87s ===============================
```

Checks verified:
- Initial review request without independent reviewer fails closed before mutation (`ok is False`, `task.status == 'running'`, claim intact, no `review_requested` event).
- Self-review is rejected (`reviewer == implementer` returns `ok is False`, reason indicates independent reviewer required, task status stays running).
- Legacy parked reviews without reviewer remain unclaimable.
- Explicit reviewer re-review reuses provenance from prior `changes_requested`.

### 2.5 Linter and Formatting Checks

```bash
uv run ruff check agent/prompt_builder.py tests/hermes_cli/test_kanban_review_surfaces.py
# Output: All checks passed!

git diff --check
# Output: (clean, exit code 0)
```

---

## 3. Exact Files and Hunks for Portable Patch

Commit: `9fba8552bba30004ab452823668a105dee1ee89d`
Diff against `6551b7c31cc665d59103c6d89cb5e0c60666f803`:

```diff
diff --git a/agent/prompt_builder.py b/agent/prompt_builder.py
index a42474bf7c..4d63895173 100644
--- a/agent/prompt_builder.py
+++ b/agent/prompt_builder.py
@@ -258,10 +258,12 @@ KANBAN_GUIDANCE = (
     "include the structured handoff (`summary`, `metadata`) on the lifecycle "
     "transition itself; never put secrets, tokens, or raw PII in these durable "
     "fields. If `kanban_show()` lists child IDs, inspect those cards with "
-    "`kanban_show(task_id=...)` before choosing the terminal action. When any "
-    "pre-created review, QA, or release child depends on your task, call "
+    "`kanban_show(task_id=...)` before choosing the terminal action. A terminal "
+    "integration, release, or evidence-only child alone does NOT replace unit "
+    "review. Only when the card delivery or task graph explicitly identifies a "
+    "distinct review/QA phase child depending on your task should you call "
     "`kanban_complete`: your implementation phase is done, and completion is "
-    "what releases those children. Never sticky-block that parent for "
+    "what releases that downstream review lane. Never sticky-block that parent for "
     "`review-required` and never request same-card review as well — either "
     "choice would strand or duplicate the downstream lane. Otherwise, when "
     "this same task needs review before it is final, call "
diff --git a/tests/hermes_cli/test_kanban_review_surfaces.py b/tests/hermes_cli/test_kanban_review_surfaces.py
index e0698f981d..02e50f40d9 100644
--- a/tests/hermes_cli/test_kanban_review_surfaces.py
+++ b/tests/hermes_cli/test_kanban_review_surfaces.py
@@ -233,7 +233,15 @@ def test_worker_guidance_distinguishes_same_card_and_downstream_review() -> None

     assert "lists child IDs" in KANBAN_GUIDANCE
     assert "inspect those cards" in KANBAN_GUIDANCE
-    assert "pre-created review, QA, or release child" in KANBAN_GUIDANCE
+    assert (
+        "A terminal integration, release, or evidence-only child alone does NOT "
+        "replace unit review"
+    ) in KANBAN_GUIDANCE
+    assert (
+        "Only when the card delivery or task graph explicitly identifies a "
+        "distinct review/QA phase child"
+    ) in KANBAN_GUIDANCE
+    assert "pre-created review, QA, or release child" not in KANBAN_GUIDANCE
     assert "call `kanban_complete`" in KANBAN_GUIDANCE
     assert "Never sticky-block that parent for `review-required`" in KANBAN_GUIDANCE
     assert "`kanban_request_changes`" in KANBAN_GUIDANCE
@@ -250,6 +258,21 @@ def test_worker_guidance_distinguishes_same_card_and_downstream_review() -> None
     assert "escalate" in skill_text.lower()


+def test_worker_guidance_terminal_child_does_not_replace_review() -> None:
+    """#385 regression: guidance must not treat terminal/release children as unit review."""
+    from agent.prompt_builder import KANBAN_GUIDANCE
+
+    assert (
+        "A terminal integration, release, or evidence-only child alone does NOT "
+        "replace unit review"
+    ) in KANBAN_GUIDANCE
+    assert (
+        "Only when the card delivery or task graph explicitly identifies a "
+        "distinct review/QA phase child"
+    ) in KANBAN_GUIDANCE
+    assert "pre-created review, QA, or release child" not in KANBAN_GUIDANCE
+
+
 def test_cli_reopen_review_is_transition_first_and_redacts_reason(
     monkeypatch: pytest.MonkeyPatch,
     tmp_path: Path,
```

---

## 4. Compatibility and Risk Assessment

- **Scope & Boundaries:** Only fork `agent/prompt_builder.py` and `tests/hermes_cli/test_kanban_review_surfaces.py` were modified. No reserved files (`tools/kanban_tools.py`, `hermes_cli/kanban_db.py`, cron files, ledger files) were touched.
- **Compatibility Impact:** Purely clarifications in prompt guidance text and regression test assertions. No runtime API signatures, DB schema, or CLI options changed. Fully backwards-compatible.
  - `release_impact`: patch
  - `release_action`: defer
  - `release_channel`: none
- **Remaining Risk:** None identified. Upstream/fork invariants verified intact.
