# PR8-CRON Evidence: One Effective Cron Script Root, Trusted Commissioning Origin, and Persisted Cron Workdir

**Unit:** PR8-CRON (`t_2a1d88d1`)  
**Issues addressed:** #372, #393, and framework side of #388  
**Repository:** Maintained fork `DarkArty07/aether-hermes`  
**Base commit:** `6551b7c31cc665d59103c6d89cb5e0c60666f803` (`origin/aether-main`)  
**Branch:** `fix/pr8-cron-script-root-origin-cwd`  
**Pull Request:** [https://github.com/DarkArty07/aether-hermes/pull/10](https://github.com/DarkArty07/aether-hermes/pull/10)  

---

## 1. Candidate Commits

Three distinct, separately attributed commits on branch `fix/pr8-cron-script-root-origin-cwd`:

1. **#372 (Script Root Contract):**
   - **SHA:** `bd0f0ad6db0f9552b824cfc495a314a48e218af2`
   - **Subject:** `fix(cron): resolve cron scripts through profile-scoped root contract (#372)`
   - **Files:** `cron/jobs.py`, `cron/lifecycle_guard.py`, `cron/scheduler.py`, `cron/script_root.py` (new), `tools/cronjob_tools.py`, `tests/cron/test_cron_script_root_372.py` (new)

2. **#393 (Commissioning Origin & Kanban Auto-Subscription):**
   - **SHA:** `3c9f955ae4c9e9970a73db7fc435d102581b6350`
   - **Subject:** `fix(cron): preserve commissioning origin for kanban auto-subscription (#393)`
   - **Files:** `cron/jobs.py`, `cron/scheduler.py`, `gateway/session_context.py`, `tools/cronjob_tools.py`, `tools/kanban_tools.py`, `tests/cron/test_cron_commissioning_origin_393.py` (new)

3. **#388 (Framework Side - Launch Workdir Persistence):**
   - **SHA:** `62eee7baab1337a9e40a8312052cecd096caaed7`
   - **Subject:** `fix(cron): persist launch workdir in cron session row (#388)`
   - **Files:** `run_agent.py`, `tests/cron/test_cron_workdir_session_388.py` (new)

---

## 2. Per-Behavior Verification Evidence

All test executions used `HERMES_TEST_FILE_RETRIES=0` and disposable temporary state (`tmp_path`, temporary `HERMES_HOME`, temporary SQLite state).

### Behavior 1: #372 — One effective profile-scoped script root
- **Requirement:** Creation/update validation, lifecycle scanning, execution, and user-facing diagnostics resolve `script` and `monitor_script` through one effective profile-scoped script-root contract. Relative paths stay confined to the active `HERMES_HOME/scripts`; absolute, home-relative, traversal, symlink-escape, and non-regular targets fail closed. A create accepted for an existing script executes that same file (same inode/content). Error text names the effective profile root instead of the default-profile `~/.hermes/scripts` shorthand. Resolve the effective home at call time; no import-time/default-home capture.
- **RED Evidence on pristine `6551b7c31cc665d59103c6d89cb5e0c60666f803`:**
  - `TestIssue372ScriptRoot::test_validation_rejects_absolute_path_and_names_effective_profile_root`: FAILED (`AssertionError: '<profile>/scripts' in "Script path must be relative to ~/.hermes/scripts/..."`).
  - `TestIssue372ScriptRoot::test_validation_rejects_home_relative_path`: FAILED (hardcoded `~/.hermes/scripts/` in error).
  - `TestIssue372ScriptRoot::test_validation_rejects_non_regular_target`: FAILED (`AssertionError: None is not None` — directory was accepted).
  - `TestIssue372ScriptRoot::test_lifecycle_scanning_resolves_profile_scripts_root`: FAILED (`TypeError: check_gateway_lifecycle() got an unexpected keyword argument 'monitor_script'`).
- **GREEN Evidence on candidate (`bd0f0ad6db`):**
  - Command: `HERMES_TEST_FILE_RETRIES=0 uv run pytest -q tests/cron/test_cron_script_root_372.py`
  - Result: **9 passed in 0.43s**.
  - Verified:
    - Absolute, home-relative (`~`), traversal (`..`), symlink escapes, and directory/non-regular targets all fail closed.
    - Error diagnostics name the active profile root directory dynamically resolved at call time.
    - Inode and content match: a create accepted for a fingerprinted file in the profile scripts dir executes that exact file, and ignores default-root decoys.
    - `monitor_script` shares the identical resolver and containment contract.
    - `check_gateway_lifecycle` scans both `script` and `monitor_script` resolved against the active profile root.

### Behavior 2: #393 — Trusted commissioning origin and Kanban auto-subscription
- **Requirement:** Creating a cron job from a TUI/desktop or gateway session captures a trusted durable notification origin separately from ordinary `deliver` metadata (TUI: durable session key plus optional live UI id; gateway: its full stable route). At fire time that origin is restored only as a request-local context consumed by Kanban auto-subscription. A root created by such a cron run reports `subscribed=true`, persists exactly the originating subscription, and wakes that origin once on terminal flow. An unattached cron, CLI or test creates no subscription; wrong/stale origins fail closed and are surfaced in the creation receipt. It must not impersonate inbound authority, become a model-supplied session id, leak through process-global environment, or alter stateless cron delivery.
- **RED Evidence on pristine `6551b7c31cc665d59103c6d89cb5e0c60666f803`:**
  - `TestIssue393CommissioningOrigin::test_capture_tui_commissioning_origin_at_create`: FAILED (`AssertionError: None is not None` — `notification_origin` was not captured).
  - `TestIssue393CommissioningOrigin::test_capture_gateway_commissioning_origin_at_create`: FAILED (`AssertionError: None is not None`).
  - `TestIssue393CommissioningOrigin::test_fire_restores_request_local_context_for_kanban_auto_subscribe`: FAILED (`AssertionError: assert False is True` — `subscribed` was False, zero subscriptions written).
- **GREEN Evidence on candidate (`3c9f955ae4`):**
  - Command: `HERMES_TEST_FILE_RETRIES=0 uv run pytest -q tests/cron/test_cron_commissioning_origin_393.py`
  - Result: **6 passed in 1.13s**.
  - Verified:
    - TUI commissioning captures durable `session_key` and optional `ui_session_id`.
    - Gateway commissioning captures full stable route (`platform`, `chat_id`, `chat_type`, `thread_id`, `user_id`, `user_id_alt`, `message_id`).
    - Unattached cron/CLI/test captures no origin (`notification_origin=None`).
    - At fire time, origin is installed as a task-local `ContextVar` (`_KANBAN_NOTIFICATION_ORIGIN`) and reset on exit; `os.environ` is not mutated, and `HERMES_SESSION_PLATFORM` remains empty during the cron run.
    - `kanban_create` during fire consumes the context, writes the subscription row, and returns `subscribed=True`.
    - TUI notification poller delivers the terminal notification and advances cursor (single wake).

### Behavior 3: #388 (Framework side) — Persisted launch workdir in cron session row
- **Requirement:** The scheduler's context-local effective workdir is preserved and `run_agent._launch_cwd_for_session("cron")` persists that trusted value in the session row before tools run. A job with no workdir keeps a null cwd; never invent one.
- **RED Evidence on pristine `6551b7c31cc665d59103c6d89cb5e0c60666f803`:**
  - `TestIssue388FrameworkWorkdir::test_launch_cwd_for_cron_with_workdir`: FAILED (`AssertionError: assert None == '/tmp/...'`).
  - `TestIssue388FrameworkWorkdir::test_cron_session_row_persists_workdir_before_tools_run`: FAILED (`AssertionError: assert None == '/tmp/.../cron_project'`).
- **GREEN Evidence on candidate (`62eee7baab`):**
  - Command: `HERMES_TEST_FILE_RETRIES=0 uv run pytest -q tests/cron/test_cron_workdir_session_388.py`
  - Result: **3 passed in 1.37s**.
  - Verified:
    - `_launch_cwd_for_session("cron")` returns the verified absolute directory from `_session_cwd_override()`.
    - When `workdir` is unset/empty, returns `None` (keeps null cwd, never invents one).
    - `SessionDB` persists `cwd` in the `sessions` row before agent tools execute.

### Neighboring and Regression Suites
Executed together across the entire unit surface:
```bash
HERMES_TEST_FILE_RETRIES=0 uv run pytest -q \
  tests/cron/test_cron_script_root_372.py \
  tests/cron/test_cron_commissioning_origin_393.py \
  tests/cron/test_cron_workdir_session_388.py \
  tests/cron/test_cron_script.py \
  tests/cron/test_cron_workdir.py \
  tests/tools/test_cronjob_tools.py \
  tests/tools/test_kanban_tools.py \
  tests/gateway/test_kanban_notifier.py \
  tests/tui_gateway/test_kanban_notify_poller.py \
  tests/cron/test_cron_created_delivery.py \
  tests/cron/test_scheduler_cron_session_isolation.py
```
**Result:** **208 passed, 1 skipped in 19.36s**.

Static checks:
- `git diff --check 6551b7c..HEAD`: Clean (exit code 0).
- `uv run ruff check <changed_files>`: Clean (all checks passed).

---

## 3. Files and Hunks for Portable Patch Generation (PR8-LEDGER Input)

| File | Associated Issue | Changes Summary |
| --- | --- | --- |
| `cron/script_root.py` (new) | #372 | Implements `get_effective_scripts_dir`, `resolve_cron_script_path`, and `validate_cron_script_path` |
| `cron/lifecycle_guard.py` | #372 | Replaces private resolver with `resolve_cron_script_path`; adds `monitor_script` support to `check_gateway_lifecycle` |
| `cron/scheduler.py` | #372, #393 | In `_run_job_script`: resolves via `resolve_cron_script_path(..., for_execution=True)`. In `run_job`: sets and resets request-local `_KANBAN_NOTIFICATION_ORIGIN` |
| `cron/jobs.py` | #372, #393 | In `create_job`/`update_job`: passes `monitor_script` to `check_gateway_lifecycle`; validates and normalizes `notification_origin` |
| `gateway/session_context.py` | #393 | Adds `_KANBAN_NOTIFICATION_ORIGIN` ContextVar, `set_kanban_notification_origin`, `get_kanban_notification_origin`, and `reset_kanban_notification_origin` |
| `tools/cronjob_tools.py` | #372, #393 | In `_validate_cron_script_path`: delegates to `validate_cron_script_path`. In `cronjob_create`: captures commissioning origin via `_capture_commissioning_origin`, forwards to job registration, and exposes in format/receipt |
| `tools/kanban_tools.py` | #393 | In `_maybe_auto_subscribe`: when inbound platform/chat_id is absent, restores request-local notification origin from cron context |
| `run_agent.py` | #388 | In `_launch_cwd_for_session("cron")`: reads `_session_cwd_override()` and returns resolved directory if valid, else None |
| `tests/cron/test_cron_script_root_372.py` (new) | #372 | Focused unit and regression test suite for script root resolution |
| `tests/cron/test_cron_commissioning_origin_393.py` (new) | #393 | Focused unit and regression test suite for commissioning origin capture and auto-subscription |
| `tests/cron/test_cron_workdir_session_388.py` (new) | #388 | Focused unit and regression test suite for launch cwd persistence |

---

## 4. Remaining Risk Analysis

1. **ContextVar Scope in Custom Process Hosts:**
   If an external caller bypasses `run_job` and invokes `AIAgent` directly in a detached thread without copying context, the request-local origin context would remain unset (safe fail-closed fallback to no auto-subscription).
2. **Symlink Environments on Native Windows:**
   Symlink escape tests require filesystem symlink support, which is skipped when elevated privileges are absent on Windows; the path resolution logic falls back to `relative_to` checks which succeed regardless of platform.
3. **Multi-process Worker Dispatch:**
   Once a Kanban task is created and auto-subscribed, downstream worker lifecycle transitions are processed by the independent Kanban dispatcher; notification wake delivery relies on the existing verified TUI and gateway poller implementations.

---

## 5. Compatibility Evidence

- **Release impact:** `patch` (backward-compatible defect corrections).
- **Public API and CLI preservation:**
  - Cron tool schemas (`CRONJOB_SCHEMA`, `KANBAN_CREATE_SCHEMA`) remain unchanged. No model argument for session IDs is exposed.
  - Local cron delivery semantics (`deliver="local"`) are strictly preserved: cron output continues to be stored in `last_output` without creating interactive chat turns.
  - Default profile execution remains unchanged: scripts in `~/.hermes/scripts` continue to resolve identically when running under the default profile.
  - Jobs with no workdir continue to have a `NULL` `cwd` in the session row.
