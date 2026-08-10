# M1.2 Gap Correction Implementation Plan

> **For Hermes:** Execute this plan through the current task contract; use `milestone-implementation-governance` for atomic milestone tracking. The implementation must run through the existing Orca Run and remain default-off. This document authorizes nothing by itself.

**Goal:** Correct the six known M1.2 installation gaps so Aether MCP can be installed, diagnosed, enabled, disabled, and rolled back against the qualified Orca 1.4.167 profile without touching the active Aether runtime.

**Architecture:** Keep one manifest-owned local installation under a temporary or explicitly selected `HERMES_HOME`. Separate the Aether/Hermes installation identity from the Orca provider profile identity, generate an Orca CLI wrapper that binds the exact qualified profile itself, run installer-owned children in attributable process groups, and classify shared Orca provider processes separately from attempt-owned MCP processes. Setup remains disabled; real runtime registration and activation stay outside this plan.

**Tech Stack:** Python 3.11, pytest 9.1.1, Ruff 0.16.1, `uv`, MCP 1.28.1 stdio, Orca AppImage 1.4.167, Linux `/proc`, Git worktree isolation, Orca orchestration.

**Execution result:** Completed and independently accepted at
`0debf07db3601a14c88262d741727e5a527f3444`. Canonical evidence is in
`M1_2_ACCEPTANCE.md`; active registration and activation remain later gates.

---

## 1. Frozen context

### Candidate

- Project root: `/home/darkarty/Desktop/agentes/aether/.aether/worktrees/v0.23.0-orca-production-cutover`
- Branch: `v0.23.0-orca-production-cutover`
- Plan baseline: `b843456cb242`
- Last technical correction: `4659c1f`
- Current focused baseline: `tests/aether_mcp/test_operational_installation.py` passes `5/5`.
- Current worktree was clean before this plan was written.

### Qualified provider

- Orca version: `1.4.167`
- AppImage: `/home/darkarty/.local/opt/orca/orca-linux.AppImage`
- AppImage SHA-256: `813b11e99f7caa4bf8e4fc47200dd6c465f34a04d61e855adbd8822190592e33`
- Stable Orca profile root: `/home/darkarty/Desktop/agentes/orca/home`
- Orca-side Hermes home: `<profile_root>/hermes-home`
- Orca XDG roots: `<profile_root>/xdg/{config,cache,data,state}`
- Aether profile ID: explicit `default`; never derive it from `profile_root.name`.

### Orca coordination continuity

- Existing Run: `run_6e48959461ec`
- Stored coordinator handle: `term_e75d9296-30d1-4955-8d6b-40c1fed3e29b` (stale handle)
- Current replacement terminal for the same coordinator pane: `term_cb7f19d0-6ecf-4024-8b7f-e2b35d5a2e8c`
- Existing Tasks: five completed; no new correction Task exists yet.
- Reuse this Run. Do not create another Run or another worktree.

## 2. Scope and stop boundary

### In scope

1. Direct Orca wrapper/profile binding.
2. Correct profile path semantics.
3. Explicit validated Aether profile ID.
4. Sanitized AppImage extraction environment.
5. Attempt-owned process cleanup during setup failure and rollback.
6. Truthful process/resource inventory without parent-shell false positives.
7. Focused, full-suite, detached-tree, and real isolated acceptance evidence.
8. Documentation of the corrected disabled installer.

### Out of scope

- Editing `/home/darkarty/Desktop/agentes/aether/home/config.yaml`.
- Registering Aether MCP in the active Aether home.
- Enabling or reloading Aether MCP in the active runtime.
- Restarting the active Aether gateway/TUI.
- Removing or disabling Olympus, Graphify, or Context7.
- Executing M1.3's first production Task.
- Changing the active Hermes prompt.
- Push, PR, merge, tag, Release, deployment, credentials, or spending.

### Stop condition

Stop after an exact committed candidate passes deterministic and real isolated M1.2 acceptance with the active Aether configuration unchanged. Runtime registration/activation remains a separate explicit gate.

## 3. Ownership model

The implementation must distinguish four process/resource classes:

| Class | Example | Ownership | Doctor treatment | Rollback treatment |
|---|---|---|---|---|
| Installer transient | AppImage extraction or `uv pip install` child | Current setup attempt | Must be gone after command | TERM → bounded wait → KILL if necessary |
| Installed MCP process | launcher, venv Python, exact wrapper, watchdog naming the exact launcher | Aether MCP installation | Surviving unexpectedly is stale | Terminate exact process tree only |
| Shared Orca provider | Orca app/daemon bound to the qualified profile | Orca, not this installation | Observe as provider state; never call it stale merely for existing | Never terminate |
| Foreign process | another Hermes, shell, test, or unrelated Orca profile | Foreign | Ignore | Never terminate |

A substring match on the broad `hermes_home` path is forbidden as an ownership claim. Ownership must come from an exact executable/argv path under `.aether-mcp`, a recorded process-group capability, or a watchdog invocation that contains the exact generated launcher path.

## 4. Execution plan

### Task 0: Reconcile the candidate and bind the existing Orca Run

**Objective:** Start from one clean candidate and one authoritative Orca Run without changing source or runtime.

**Files:** None.

**Steps:**

1. Verify branch, HEAD, tracked changes, untracked files, and ignored runtime residue separately.
2. Verify Orca runtime `ready` using the stable profile XDG roots.
3. In the live replacement coordinator terminal, bind the existing Run:

   ```bash
   orca orchestration run-use --id run_6e48959461ec --json
   ```

4. Create exactly one correction Task in that Run. Its spec must:
   - name the exact project root and baseline;
   - require Tasks 1–6 below in order;
   - require genuine RED before production changes;
   - permit only the listed files;
   - prohibit active configuration, activation, publication, and broad cleanup.
5. Start one Codex worker in the current candidate worktree. Do not create another worktree or parallel writer. If that worker fails or cannot complete the task, close/fence its write authority before Hermes takes direct ownership in the same worktree; do not launch Claude Code or a second overlapping writer.
6. Capture secret-safe before-state evidence:
   - active Aether config SHA-256;
   - active MCP registration names/enabled states;
   - exact Orca runtime ID/version;
   - Aether MCP installation roots absent;
   - attempt-owned process count zero.

**Acceptance:** One Run, one correction Task, one writer, clean baseline, and no live mutation.

---

### Task 1: Make profile identity and layout explicit

**Objective:** Correct gaps 2 and 3 by separating Aether profile identity from filesystem names and deriving the qualified Orca layout once.

**Files:**

- Modify: `scripts/aether_mcp/installation.py:160-345`
- Modify: `scripts/aether_mcp/setup.py:11-28`
- Test: `tests/aether_mcp/test_operational_installation.py`

**RED tests to add first:**

```python
def test_setup_persists_explicit_profile_id_and_qualified_layout(...): ...
def test_setup_rejects_invalid_profile_id_before_mutation(...): ...
def test_setup_conflicts_when_profile_id_changes(...): ...
```

The fixture must use the real layout shape:

```text
profile/
  hermes-home/
  xdg/
    config/
    cache/
    data/
    state/
```

Assertions:

- `setup(..., profile_id="default")` persists `default` in `installation.json`.
- `AETHER_PROFILE=default`; it is not `profile_root.name`.
- Stored Orca-side paths resolve to `profile_root/hermes-home` and `profile_root/xdg/*`.
- Values such as empty string, whitespace, path separators, and aliases outside `^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$` fail with `INVALID_PROFILE_ID` before config mutation.
- Repeating setup with the same profile ID is idempotent; changing only the ID produces `INSTALLATION_CONFLICT`.

**Verify RED:**

```bash
.venv/bin/python -m pytest -p no:cacheprovider \
  tests/aether_mcp/test_operational_installation.py \
  -k 'profile_id or qualified_layout' -vv
```

Expected: behavioral failures because `setup()` has no explicit `profile_id` and currently uses `profile.name` plus incorrect root paths.

**Minimal GREEN:**

- Add required `profile_id` to `setup()` and `setup.py --profile-id`.
- Add it to `Installation` and idempotency comparison.
- Introduce one internal immutable profile-layout value object/helper; do not duplicate path derivation.
- Create/chmod only the qualified profile-owned directories needed by the frozen contract.
- Remove the invented `profile_root/{config,cache,data,state}` derivation.
- Do not silently invent another profile ID or fallback.

**Verify GREEN:** Run the same focused command; all selected tests pass.

---

### Task 2: Bind the public Orca wrapper to the qualified profile

**Objective:** Correct gap 1 so every direct wrapper invocation, including `doctor()`, reaches the same Orca runtime as the stable AppImage profile.

**Files:**

- Modify: `scripts/aether_mcp/installation.py:270-320, 421-503`
- Test: `tests/aether_mcp/test_operational_installation.py`

**RED tests to add first:**

```python
def test_wrapper_overrides_poisoned_ambient_profile_with_qualified_profile(...): ...
def test_doctor_queries_exact_profile_through_direct_wrapper(...): ...
def test_mcp_launcher_keeps_aether_home_distinct_from_orca_hermes_home(...): ...
```

Use a fake `AppRun` that records only an allowlisted environment projection and returns the valid Orca status envelope. Poison ambient XDG/Hermes variables with a foreign profile before invoking the wrapper.

Required wrapper contract:

```text
HOME=<profile_root>
HERMES_HOME=<profile_root>/hermes-home
XDG_CONFIG_HOME=<profile_root>/xdg/config
XDG_CACHE_HOME=<profile_root>/xdg/cache
XDG_DATA_HOME=<profile_root>/xdg/data
XDG_STATE_HOME=<profile_root>/xdg/state
ORCA_TELEMETRY_DISABLED=1
APPDIR=<owned extraction>
ELECTRON_RUN_AS_NODE=1
```

Additional constraints:

- The Aether MCP launcher still receives its selected installation `HERMES_HOME` and explicit `AETHER_PROFILE`; do not overwrite those globally with the Orca-side Hermes home.
- Do not derive `XDG_RUNTIME_DIR` as `<profile_root>/runtime`. Preserve the host runtime directory unless a separately validated Orca profile contract supplies one.
- Preserve the existing display/X11 values only when present.
- `doctor()` must keep calling the generated wrapper, not an ambient `orca-ide` shim.

**Verify RED:** The fake wrapper observes poisoned/incorrect values under the current implementation.

**Minimal GREEN:** Generate all qualified provider exports inside `orca-public-cli` itself. Keep the MCP launcher and provider wrapper as separate environment boundaries.

**Verify GREEN:**

```bash
.venv/bin/python -m pytest -p no:cacheprovider \
  tests/aether_mcp/test_operational_installation.py \
  -k 'wrapper or exact_profile or distinct' -vv
```

Expected: all selected tests pass; no active Orca process or config is changed.

---

### Task 3: Sanitize extraction and own installer child groups

**Objective:** Correct gap 4 and prevent setup failures from leaving AppImage/uv descendants.

**Files:**

- Modify: `scripts/aether_mcp/installation.py:250-283`
- Test: `tests/aether_mcp/test_operational_installation.py`

**RED tests to add first:**

```python
def test_extraction_does_not_inherit_appimage_extract_and_run(...): ...
def test_setup_timeout_reaps_extraction_descendants(...): ...
def test_setup_failure_restores_config_and_leaves_no_owned_children(...): ...
```

The fake AppImage must fail if `APPIMAGE_EXTRACT_AND_RUN` is present and must optionally spawn a bounded sleeping descendant whose PID is written under the temporary test root.

**Verify RED:** At least the inherited-environment test fails because current extraction uses ambient `os.environ`; descendant cleanup must also fail under the current `subprocess.run()` path.

**Minimal GREEN:**

- Build an explicit child environment and remove `APPIMAGE_EXTRACT_AND_RUN` before the initial extraction command.
- Execute installer subprocesses in a new session/process group with bounded output capture.
- On success, allow a short natural descendant cleanup grace.
- On timeout/error, terminate the owned process group with TERM, bounded wait, then KILL.
- Never use process-name matching or broad `pkill`.
- Preserve typed, secret-safe installer errors.

**Verify GREEN:** Run the three selected tests and prove each recorded child PID no longer exists.

---

### Task 4: Implement exact rollback process cleanup

**Objective:** Correct gap 5 so rollback disables future launches, terminates only installation-owned processes, preserves evidence, and remains retryable.

**Files:**

- Modify: `scripts/aether_mcp/installation.py:376-394, 433-503`
- Modify only if output contract requires it: `scripts/aether_mcp/rollback.py`
- Test: `tests/aether_mcp/test_operational_installation.py`

**RED tests to add first:**

```python
def test_rollback_terminates_exact_installed_mcp_process_tree(...): ...
def test_rollback_preserves_foreign_process_with_similar_name(...): ...
def test_rollback_cleanup_failure_keeps_manifest_for_retry(...): ...
def test_second_rollback_is_idempotent_after_process_cleanup(...): ...
```

Use child processes created by the test under a temporary installation root. Keep direct `Popen` handles and clean them in fixture teardown even if the assertion fails.

**Required rollback order:**

1. Load and validate the installation manifest.
2. Restore/remove only `mcp_servers.aether_mcp`, preventing relaunch.
3. Inventory exact installation-owned processes.
4. TERM only those process trees.
5. Wait for a bounded grace period.
6. KILL only remaining owned members.
7. Re-inventory and require zero owned survivors.
8. Remove `.aether-mcp` payload only after successful cleanup.
9. Preserve `.aether-mcp-state` and diagnostic evidence.
10. On cleanup failure, return/raise a typed failure and retain enough manifest/payload state for deterministic retry.

**Foreign-process protection:** A process is not owned merely because its command contains `aether`, `mcp`, the project root, or broad `hermes_home`. The negative test must prove the foreign PID survives.

**Verify GREEN:** All four selected tests pass, the owned PID is gone, the foreign PID remains until test teardown, and config restoration remains exact.

---

### Task 5: Make doctor inventory truthful on the real profile

**Objective:** Correct gap 6 by replacing broad `ps` substring matching with classified, secret-safe inventory.

**Files:**

- Modify: `scripts/aether_mcp/installation.py:421-503`
- Test: `tests/aether_mcp/test_operational_installation.py`

**RED tests to add first:**

```python
def test_inventory_excludes_doctor_and_ancestor_shell(...): ...
def test_inventory_detects_exact_installed_launcher_descendant(...): ...
def test_inventory_reports_shared_profile_orca_as_provider_not_stale(...): ...
def test_inventory_failure_is_unknown_not_empty_pass(...): ...
```

**Implementation contract:**

- Read a bounded same-user Linux process snapshot from `/proc`; do not spawn `ps` and then accidentally inventory the `ps` command or its parent shell.
- Exclude the current doctor PID and its ancestor chain from stale classification.
- Classify exact install-path processes separately from shared profile-bound Orca processes.
- A shared Orca app/daemon is provider evidence, not rollback ownership.
- Do not return `stale_resources=[]` when process inventory could not be performed; return a typed/structured `UNKNOWN` and make `doctor.ok` false.
- Do not expose raw environment values, command lines, credentials, or arbitrary process arguments. Emit only classification, PID/PPID if needed, and allowlisted path/identity facts.
- Parse public Orca envelopes rather than trusting return code or output size.
- Continue requiring exact 15-tool names, permissions, AppImage/catalog/version identity, and runtime `ready`.

**Verify GREEN:**

```bash
.venv/bin/python -m pytest -p no:cacheprovider \
  tests/aether_mcp/test_operational_installation.py \
  -k 'inventory or ancestor or provider_not_stale or unknown' -vv
```

Expected: no false positive from the invoking shell; exact attempt child detected; unavailable inventory blocks `ok`.

---

### Task 6: Reconcile interfaces, documentation, and deterministic gates

**Objective:** Close the complete affected equivalence class before any real AppImage/profile run.

**Files:**

- Modify: `docs/releases/v0.23.0/M1_2_LOCAL_INSTALLATION.md`
- Modify if required by new status fields: `scripts/aether_mcp/status.py`
- Modify only already-listed source/tests needed by Tasks 1–5.

**Documentation changes:**

- Add required `--profile-id default` to setup usage.
- Document the exact qualified profile layout.
- State that setup remains `enabled: false` and starts no worker.
- Document process ownership classes and rollback order.
- Document typed failure/UNKNOWN behavior.
- Keep active registration/activation explicitly outside M1.2 correction implementation.

**Candidate-local test environment:**

```bash
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python \
  -e . pytest==9.1.1 ruff==0.16.1
```

**Gates, in order:**

```bash
env -u PYTHONPATH PYTHONDONTWRITEBYTECODE=1 \
  .venv/bin/python -m pytest -p no:cacheprovider \
  tests/aether_mcp/test_operational_installation.py -q

env -u PYTHONPATH \
  .venv/bin/python -m ruff check \
  scripts/aether_mcp tests/aether_mcp/test_operational_installation.py \
  src/aether_mcp

env -u PYTHONPATH PYTHONDONTWRITEBYTECODE=1 \
  .venv/bin/python -m pytest -p no:cacheprovider \
  tests/aether_mcp -q

env -u PYTHONPATH \
  .venv/bin/python -m compileall -q \
  src/aether_mcp scripts/aether_mcp

git diff --check
git status --short
```

**Expected:** All tests pass with no skips introduced for the corrected behavior; Ruff/compileall/diff pass; changed paths match this plan; active files are untouched.

**Atomic commit strategy:**

1. `fix: bind Aether MCP installer to qualified Orca profile` — gaps 1–4 and their tests.
2. `fix: enforce owned Aether MCP installation cleanup` — gaps 5–6 and their tests.
3. Acceptance documentation is committed only after independent real-profile verification; it must not claim PASS before that verification.

Do not amend earlier commits.

---

### Task 7: Run real isolated M1.2 acceptance

**Objective:** Prove the corrected committed source against the exact AppImage and stable Orca profile without touching the active Aether home.

**Files:**

- Create after PASS: `docs/releases/v0.23.0/M1_2_ACCEPTANCE.md`
- No active config or profile file modifications are allowed.

**Preconditions:**

- Deterministic gates are green on the implementation commits.
- Orca runtime reports `ready`, version `1.4.167`.
- AppImage hash matches the frozen value.
- The real sequence uses a temporary `HERMES_HOME`; never `/home/darkarty/Desktop/agentes/aether/home`.
- Capture active Aether config hash and active registrations before execution.

**Real sequence:**

```text
setup --profile-id default       → registration present, enabled false
status                           → exact identities and paths
MCP stdio initialize/tools-list  → exactly 15 approved tool names
doctor                           → ok true; exact Orca ready; inventory performed
activate                         → enabled true only in temporary config
status                           → enabled true
activate --disable               → enabled false
rollback                         → config restored byte-for-byte
rollback again                   → already_rolled_back true
final inventory                  → zero installation-owned survivors
```

The run must use:

```text
AppImage: /home/darkarty/.local/opt/orca/orca-linux.AppImage
Profile:  /home/darkarty/Desktop/agentes/orca/home
Profile ID: default
Project:  candidate worktree
```

**Acceptance assertions:**

- Temporary config equals its original bytes after rollback.
- `.aether-mcp` payload is absent after rollback.
- `.aether-mcp-state` evidence remains present.
- No installation-attempt-owned process, listener, wrapper, venv, extraction, operational terminal, worktree, Run, Task, or worker survives. The completed Orca correction Task/Dispatch is durable coordination evidence, not an installation resource, and is preserved.
- Existing Orca app/daemon remains running and is not terminated by rollback.
- Active Aether config hash and active registration set are unchanged before/after.
- No active Aether MCP process exists.
- No secrets or raw process environments enter committed evidence.

**Failure behavior:** Any false positive, UNKNOWN, survivor, config drift, profile mismatch, or non-idempotent rollback keeps M1.2 red. Preserve evidence, correct the owning layer with a new genuine RED, and rerun the entire real sequence. Do not activate the live runtime.

---

### Task 8: Independently accept the exact committed candidate

**Objective:** Prevent the implementer from being the sole acceptance authority and ensure test evidence belongs to the exact candidate tree.

**Files:**

- Finalize after PASS: `docs/releases/v0.23.0/M1_2_ACCEPTANCE.md`
- Update the handoff/roadmap status only if M1.2 truly passes; preserve historical handoff facts rather than rewriting them as if they never occurred.

**Independent review:**

1. Read every changed test body and production path.
2. Map each of the six gaps to at least one observed RED and final GREEN test.
3. Verify no test weakens `doctor`, changes a real failure into a skip, or treats missing inventory as PASS.
4. Verify no broad process-name/path termination can touch another Hermes/Orca instance.
5. Verify setup remains default-off and active config paths are absent from the diff.
6. Stage only the declared files and inspect the cached diff.
7. Create a fresh detached worktree at the exact candidate commit.
8. Create a disposable Python 3.11 venv there, install the candidate non-editably plus pinned test tools, and prove `aether_mcp.__file__` resolves from disposable `site-packages`, not another worktree.
9. Rerun focused tests, full `tests/aether_mcp`, Ruff, compileall, `git diff --check`, secret scan, and the real isolated acceptance as required by the frozen gate.
10. Remove the detached worktree and test environments only after evidence is captured and zero survivors are proven.

**M1.2 PASS requires:**

- all six gaps closed;
- deterministic and real-profile evidence green;
- exact committed tree verified;
- active runtime unchanged;
- no owned survivors;
- rollback reproducible and idempotent.

## 5. Gap-to-task traceability

| Gap | Owning task | Primary proof |
|---|---|---|
| 1. Wrapper lacks direct profile binding | Task 2 | Poisoned ambient profile is overridden; direct doctor reaches exact runtime |
| 2. Wrong profile path semantics | Task 1 | Manifest/wrapper use `hermes-home` and `xdg/*` layout |
| 3. Profile ID derived from basename | Task 1 | Explicit `default`, invalid IDs rejected, idempotency conflict tested |
| 4. Extraction inherits `APPIMAGE_EXTRACT_AND_RUN` | Task 3 | Canary fake AppImage observes variable absent |
| 5. Rollback lacks owned-process cleanup | Task 4 | Owned descendant terminated; foreign process survives; retryable failure |
| 6. Inventory false positives/missed children | Task 5 | Ancestors excluded; exact child detected; shared Orca classified separately |

## 6. Runtime gate after this plan

Completing this plan does **not** place Aether MCP in the active runtime. If M1.2 passes, the next separately authorized sequence is:

1. Register `mcp_servers.aether_mcp` in the active Aether home with `enabled: false`.
2. Run `doctor` against that named installation.
3. Obtain explicit activation/reload authority.
4. Enable and reload the exact runtime.
5. Verify exactly 15 tools from a fresh Hermes process.
6. Execute M1.3's first reversible production Task through Hermes → Aether MCP → Orca.

Plan complete and saved. Approval to execute it would authorize Tasks 0–8 only within the isolated candidate and temporary acceptance home. Active registration, runtime activation/reload, push, PR, merge, tag, Release, deployment, credentials, and spending remain separately gated.
