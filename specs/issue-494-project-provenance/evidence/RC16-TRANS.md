# RC16-TRANS evidence — exact RC15 -> RC16 isolated transition, rollback, and refusal oracle

## Context and boundaries

- **Unit:** `RC16-TRANS` (task `t_bb6dcddc`)
- **Producer:** Implementer (Aether role)
- **Objective Contract:** `oc_c770cea3db51d97e@v2` (`cd80efb52125f45af5340baf8119aeaddc4756f9d04ae7722137ae5df1f9adc7`)
- **Execution breakdown:** `specs/issue-494-project-provenance/tasks-rc16.md` (commit `96c200e0`)
- **Base commit:** `dc4872834a2c670c506100fd60c69960247124f2`
- **Reviewed parent commits consumed:**
  - `RC16-IDENT`: `513c9dd3381ed1f802e3453e705fdb68eb880962`
  - `RC16-HLP`: `c2b4a9010efba3fdeebbe949488af3b576a38b69`
- **Candidate composition identity:**
  - Package version: `1.0.0rc16`
  - Display version: `1.0.0-rc.16`
  - Local release tag identity: `v1.0.0-rc.16` (annotated tag created only inside disposable candidate clone, never in shared primary checkout)
  - Release lock schema version: `5`
  - Hermes source mode: `maintained_fork`
  - Hermes repository: `https://github.com/DarkArty07/aether-hermes`
  - Hermes branch: `aether-main`
  - Hermes pinned commit: `58f8c37a49b341f25b8fdd6310542fe932031b8d`
  - Hermes Git tree: `a93162c1a867202b03c12fa372c71029152fdcf7`
  - Materialized source-tree SHA-256: `a2a9b374bd2022c7f96242b0ab2c95691119262c925389eb3820ca627c581144` (9,378 files)
  - Hermes extras: `["mcp"]`
- **Predecessor RC15 identity:**
  - Package version: `1.0.0rc15`
  - Display version: `1.0.0-rc.15`
  - Release ID: `1.0.0rc15-5dc9cd69da8d18f3`
  - Aether commit: `20f3a2cb8a3360be050c13a0a9c73ed1d17456e2`
  - Hermes commit: `5b2b6ba543680c6fe8a62de4b467d1107be3abf4`
  - Hermes source-tree SHA-256: `adf77d5840028f490818a3f78304a9f3835bff176df3ad34255aea2f9882aba2`
- **Explicit non-claims:** This document records unit-level implementation evidence and verification only. It does NOT constitute independent review, integration, live managed cutover, canary verification, activation, publication, deployment, or agent-behavior qualification.

## Supervisor repair attribution (round 3)

The candidate delivered for review was `0ba79130` (the file states 16 focused tests). During the third review round the reviewer reproduced a further instance of the confinement failure class: with a pre-planted symlink at a derived directory (for example `<work_root>/home` pointing at the operator's live data root), the entry accepted the input (`live_overlaps()` returned no overlap) and a full run materialized files outside the work root. Both ordinary review returns for this logical unit were already spent, so the reviewer performed one bounded, invariant-level repair instead of a third return:

- `Isolation.destination_escapes()` resolves every derived destination (HOME, XDG roots, TMPDIR, `HERMES_HOME`, store/state roots, projections, project dir, and the candidate/fork/staging directories under the work root) and requires each to stay inside the disposable work root.
- `Inputs.resolve` refuses with exit 2 before any mutation when a destination escapes; `scenario_isolation` re-checks it.
- New control `test_entry_refuses_symlinked_derived_destination_outside_work_root`; the focused entry guards docstring and this evidence's Environment-limits section were corrected.

The controls were mutation-tested: `test_entry_refuses_symlinked_derived_destination_outside_work_root` fails on both earlier candidates (`fd204928`, `0ba79130`), and the round-2 discriminator control (`test_entry_refuses_custom_tmpdir_work_root_outside_fixed_system_roots`) fails on `fd204928`. On the repaired tree the escaped-destination input refuses with exit 2 and materializes zero files, and the decisive run, focused suite (17) and the mixed-version/projection lane all pass.

**This repair and its verification are the reviewer's own work, not independent review of the reviewer's change.** The round-3 verdict on the repaired candidate therefore rests on reviewer-authored code plus reviewer-run verification only; a further independent check would need a different reviewer. The implementation-phase provenance of the underlying unit (its design, its real-reader requirement and the round-1/round-2 corrections above) is unchanged.

## Scenario results matrix

All eight decisive scenarios implemented in `scripts/qualify_rc16_transition.py` were executed against an isolated disposable store:

| Scenario | Objective obligation | Observed result | Status |
| --- | --- | --- | --- |
| `isolation` | Derived paths strictly under disposable work root; refusal of live overlap; scrubbed environment | 0 filesystem directory overlaps detected against configured live directories by path-listing; all 12 derived paths relative to temp work root; every derived destination resolves inside the work root (escaped-destination refusal included); service boundary positively confined under fixed system temp roots (/tmp, /var/tmp, /private/tmp, /private/var/tmp); operator environment variables scrubbed | PASS |
| `rc15-immutability` | RC15 active-record and release-lock bytes readable, coherent, and byte-immutable | Initial SHA-256 recorded; verified identical across forward transition, rollback, and reselection | PASS |
| `candidate-identity` | RC16 candidate release-lock and record bind exact pin `58f8c37a49...` and digest `a2a9b374...` | Verified `schema_version: 5`, Hermes commit `58f8c37a49...`, source tree digest `a2a9b374...`, extras `["mcp"]`, package version `1.0.0rc16`, display `1.0.0-rc.16`, tag `v1.0.0-rc.16` | PASS |
| `transition-cycle` | RC15 -> RC16 transition with mutable state preserved; rollback target RC15 coherent; RC16 reselection | Complete cycle executed: RC15 initial -> RC16 update -> RC15 rollback -> RC16 reselect; profile memory, session data, project registry, and board database bytes 100% preserved; record and lock bytes immutable | PASS |
| `refusal-matrix` | Refusal before activation for wrong commit, wrong digest, missing HLP-428 component, dirty fork, foreign fork, malformed lock | 6/6 refusal test cases refused with `IntegrityError` before mutation; active pointer `active.json` remained 100% unmutated | PASS |
| `hlp-reconciliation` | HLP-428 required/present; HLP-433 deferred/absent (presence=absent) and unretired | `--candidate-check` passed with `status: qualified`; `HLP-428` in `required_hlps`; `HLP-433` in `deferred_hlps` with `presence: absent` and missing regression module visible; `refusing_hlps: []` | PASS |
| `review-fallback` | Retained RC15 review guidance absence-tolerant path verified; durable-history fallback when context line absent | Verified fallback phrasing in `SOUL.md` and `SKILL.md`; verified absence of context line at pin `58f8c37a49`; verified deterministic fallback counts prior returns from durable task runs without claiming behavior qualification | PASS |
| `fork-regression` | Maintained-fork regression module and affected kanban battery at exact pin `58f8c37a49...` | `tests/hermes_cli/test_kanban_project_provenance.py` + 4 related kanban tests executed via `scripts/run_tests.sh`: 5 test files, 30 tests passed, 0 failed, exit 0 | PASS |

## Environment limits

1. **Service manager and bus boundary confinement**:
   - The isolated transition qualification confines gateway unit materialization through the product's temp-root guard: the work root must resolve under a fixed system temporary directory (`/tmp`, `/var/tmp`, `/private/tmp`, `/private/var/tmp`). In the child execution frame (where child `TMPDIR` is rewritten to `<work_root>/tmp` while `HERMES_HOME` is `<work_root>/home/.hermes`), `HERMES_HOME` is recognized as temporary only when `<work_root>` is under one of these fixed system roots, triggering `hermes_cli/gateway.py:3465 _refuse_temp_home_service_write`. This guard prevents writing real systemd service units to disk and avoids invoking `systemctl --user daemon-reload` or connecting to the D-Bus user scope bus.
   - Any work root resolving outside the fixed system temp roots (including under a custom `TMPDIR`) is fail-closed refused with exit code 2 before any filesystem mutation occurs (`test_entry_refuses_non_temp_work_root_to_confine_service_boundary` and `test_entry_refuses_custom_tmpdir_work_root_outside_fixed_system_roots`).
   - **Accepted set == guard-covered set**: the entry accepts exactly the fixed system roots, and the child frame's `TMPDIR` is set to `<work_root>/tmp`, so the guard's own `tempfile.gettempdir()` term always evaluates inside the already-accepted set. Verified in the exact child frame: feeding the real emitted unit text into the pin's `_temp_home_in_service_definition` returns `would_refuse=True` for an accepted work root, and the real CLI (`hermes_cli.main --profile morfeo gateway install --force --no-start-now --start-on-login`) prints `✗ Refusing to write the gateway systemd unit` and writes no unit file. A full shimmed decisive run recorded `systemctl is-system-running` only — **zero** `daemon-reload` and zero `enable` invocations, with no unit written anywhere in the work root.
   - **What this lane does NOT prove**: No real user-systemd unit materialization, service reload, or live D-Bus session interaction was executed or claimed. This qualification lane does not prove host systemd service supervisor behavior, unit file validation by an active systemd daemon, or user-bus activation under a live operator session manager.

2. **Filesystem path-listing isolation scope**:
   - The isolation check verifies path resolution against configured live data/state/config/service directories (`~/.local/share/aether`, `~/.local/state/aether`, `~/.config/aether`, `~/.hermes`, `/etc/systemd/user`).
   - This check is strictly a filesystem path-listing and environment-scrubbing check; it does not probe or monitor the host service manager, active IPC sockets, or background daemons.
   - **Destination containment**: every derived destination is additionally resolved and required to stay inside the disposable work root before the first mutating step. A pre-planted symlink at a derived directory (e.g. `<work_root>/home` pointing at the operator's live data root), which the lexical live-overlap check alone does not catch, is refused with exit code 2 (`test_entry_refuses_symlinked_derived_destination_outside_work_root`); the same input previously accepted and materialized files outside the work root.

3. **Durable private receipts root**:
   - Raw qualification receipts are stored in a durable private root (`.aether/receipts/rc16-trans/`, ignored by Git) rather than an ephemeral `/tmp` location. The temporary work root containing candidate builds, isolated stores, and clones remains strictly disposable and temp-confined.

4. **Candidate tag timing and git boundaries**:
   - The candidate tag `v1.0.0-rc.16` was tested exclusively inside a disposable Git clone under the temporary work root. No release tag was created in the shared primary checkout. The real annotated release tag is created once after merge by integration unit `RC16-INT`.

5. **Unit-level evidence only**:
   - This evidence certifies unit-level contract compliance for the RC15 -> RC16 isolated transition, rollback, immutable release records, and refusal matrix. It does NOT constitute independent review, integration, live managed cutover, canary verification, activation, publication, deployment, or agent-behavior qualification.

## Exact execution commands and verification receipts

### 1. Focused transition qualification test suite

Command:
```bash
uv run --frozen python scripts/run_tests.py -- tests/test_rc16_transition_qualification.py -q
```

Result:
```text
.................                                                        [100%]
17 passed in 90.84s (0:01:30)
```
Exit code: `0`.
Includes the service boundary confinement controls asserting that non-temp work roots (`test_entry_refuses_non_temp_work_root_to_confine_service_boundary`) and custom TMPDIR work roots outside fixed system temp roots (`test_entry_refuses_custom_tmpdir_work_root_outside_fixed_system_roots`) are refused before mutation, and the destination-containment control (`test_entry_refuses_symlinked_derived_destination_outside_work_root`).

### 2. Mixed-version lifecycle and projection regression suites

Command:
```bash
uv run --frozen python scripts/run_tests.py -- tests/test_mixed_version_lifecycle_qualification.py tests/test_lifecycle_projections.py -q
```

Result:
```text
.....................................................................    [100%]
69 passed in 46.44s
```
Exit code: `0`.
Confirms that neither `scripts/qualify_mixed_version_lifecycle.py` nor `tests/test_lifecycle_projections.py` was modified or weakened.

### 3. Decisive transition qualification entry execution

Command:
```bash
uv run --frozen python scripts/qualify_rc16_transition.py run \
    --work-root <disposable-work-root> \
    --receipts-root <durable-private-receipts-root> \
    --json
```

Raw JSON receipt output:
```json
{
  "schema_version": "aether.rc16-transition-qualification.v1",
  "timestamp_utc": "2026-09-26T04:57:40.421879+00:00",
  "overall_status": "passed",
  "total_duration_s": 87.614,
  "scenarios_selected": [
    "isolation",
    "rc15-immutability",
    "candidate-identity",
    "transition-cycle",
    "refusal-matrix",
    "hlp-reconciliation",
    "review-fallback",
    "fork-regression"
  ],
  "scenarios": [
    {
      "name": "isolation",
      "passed": true,
      "duration_s": 0.001,
      "details": {
        "live_witnesses_recorded": 5
      },
      "error": null
    },
    {
      "name": "rc15-immutability",
      "passed": true,
      "duration_s": 2.709,
      "details": {
        "rc15_record_sha256": "a4b584c06cac60482bac5203ebb24e7948626d2e213162df12518dadc67534c6",
        "rc15_lock_sha256": "ebd5a85a3851bff49156a70988996880bcd79ac71031348f0dde90a2d753f1c7",
        "rc15_release_id": "1.0.0rc15-5dc9cd69da8d18f3"
      },
      "error": null
    },
    {
      "name": "candidate-identity",
      "passed": true,
      "duration_s": 13.562,
      "details": {
        "candidate_commit": "<candidate-commit>",
        "candidate_lock": "<disposable-work-root>/candidate-staging/release-lock.json",
        "candidate_wheel": "<disposable-work-root>/candidate-staging/dist/aether_agents-1.0.0rc16-py3-none-any.whl",
        "derived_fork_tree_digest": "a2a9b374bd2022c7f96242b0ab2c95691119262c925389eb3820ca627c581144"
      },
      "error": null
    },
    {
      "name": "transition-cycle",
      "passed": true,
      "duration_s": 45.867,
      "details": {
        "cycle_steps": [
          "rc15_initial",
          "rc16_update",
          "rc15_rollback",
          "rc16_reselect"
        ],
        "rc16_release_id": "1.0.0rc16-14fa64728b9aaeae"
      },
      "error": null
    },
    {
      "name": "refusal-matrix",
      "passed": true,
      "duration_s": 13.342,
      "details": {
        "refusals_tested": [
          "wrong_commit",
          "wrong_source_digest",
          "missing_required_hlp428_component",
          "dirty_fork_checkout",
          "foreign_fork_origin",
          "malformed_lock"
        ]
      },
      "error": null
    },
    {
      "name": "hlp-reconciliation",
      "passed": true,
      "duration_s": 0.259,
      "details": {
        "required_hlps_count": 32,
        "deferred_hlps": [
          "HLP-433"
        ]
      },
      "error": null
    },
    {
      "name": "review-fallback",
      "passed": true,
      "duration_s": 0.451,
      "details": {
        "fallback_phrases_verified": [
          "If the field is absent, consult existing durable history.",
          "If absent, use the existing complete history"
        ],
        "pin_omits_optional_line": true,
        "durable_count_derived": 2
      },
      "error": null
    },
    {
      "name": "fork-regression",
      "passed": true,
      "duration_s": 11.422,
      "details": {
        "test_files": [
          "tests/hermes_cli/test_kanban_project_provenance.py",
          "tests/hermes_cli/test_kanban_board_project.py",
          "tests/hermes_cli/test_kanban_project_link.py",
          "tests/hermes_cli/test_kanban_worktree_isolation.py",
          "tests/hermes_cli/test_kanban_worktree_base_ref.py"
        ],
        "hermes_python": "<venv>/bin/python",
        "runner": "<disposable-work-root>/fork-pin-clone/scripts/run_tests.sh",
        "exit_code": 0,
        "stdout_summary": [
          "=== Summary: 5 files, 30 tests passed, 0 failed (100% complete) in 3.7s (48 workers) ==="
        ]
      },
      "error": null
    }
  ],
  "identities": {
    "rc15_version": "1.0.0rc15",
    "rc15_release_id": "1.0.0rc15-5dc9cd69da8d18f3",
    "rc16_version": "1.0.0rc16",
    "rc16_display_version": "1.0.0-rc.16",
    "rc16_hermes_commit": "58f8c37a49b341f25b8fdd6310542fe932031b8d",
    "rc16_hermes_tree_sha256": "a2a9b374bd2022c7f96242b0ab2c95691119262c925389eb3820ca627c581144"
  },
  "receipt_path": "<durable-private-receipts-root>/rc16-transition-receipt-1790398660.json"
}
```
Exit code: `0`.

### 4. Maintained-fork battery execution at exact pin

Runner script: `./scripts/run_tests.sh` inside disposable fork clone targeting remote-tracking `origin/aether-main` at commit `58f8c37a49b341f25b8fdd6310542fe932031b8d`.

Command:
```bash
./scripts/run_tests.sh \
    tests/hermes_cli/test_kanban_project_provenance.py \
    tests/hermes_cli/test_kanban_board_project.py \
    tests/hermes_cli/test_kanban_project_link.py \
    tests/hermes_cli/test_kanban_worktree_isolation.py \
    tests/hermes_cli/test_kanban_worktree_base_ref.py
```

Result:
```text
▶ running per-file parallel test suite via run_tests_parallel.py
  (TZ=UTC LANG=C.UTF-8 PYTHONHASHSEED=0; clean env)
▶ pre-compiling bytecode cache
▶ launching test runner
Discovered 5 test files (~22 tests) under ['tests/hermes_cli/test_kanban_project_provenance.py', 'tests/hermes_cli/test_kanban_board_project.py', 'tests/hermes_cli/test_kanban_project_link.py', 'tests/hermes_cli/test_kanban_worktree_isolation.py', 'tests/hermes_cli/test_kanban_worktree_base_ref.py']; running with -j 48
[ 18.2% |     4/~22 | ✓4 | ✗0] ✓ tests/hermes_cli/test_kanban_board_project.py (4✓, 0.8s)
[ 27.3% |     6/~22 | ✓6 | ✗0] ✓ tests/hermes_cli/test_kanban_worktree_isolation.py (2✓, 0.8s)
[ 40.9% |     9/~22 | ✓9 | ✗0] ✓ tests/hermes_cli/test_kanban_project_link.py (3✓, 0.8s)
[ 63.6% |    14/~22 | ✓14 | ✗ 0] ✓ tests/hermes_cli/test_kanban_project_provenance.py (5✓, 1.7s)
[100.0% |    22/~22 | ✓30 | ✗ 0] ✓ tests/hermes_cli/test_kanban_worktree_base_ref.py (16✓, 2.9s)

=== Summary: 5 files, 30 tests passed, 0 failed (100% complete) in 2.9s (48 workers) ===
```
Exit code: `0`. Reviewer re-run of the same battery against an independent clone at the same pin (`HERMES_PYTHON` = the fork's dev venv): `5 files, 30 tests passed, 0 failed`, exit `0` (3.8s wall; per-file times vary with host load). This battery exercises the maintained fork at the pin, not the Aether candidate; the same battery also runs inside the decisive entry's `fork-regression` scenario, whose receipt records exit `0`.

### 5. Static quality and code formatting checks

Commands:
```bash
uv run --frozen ruff check src/aether_agents tests scripts
uv run --frozen ruff format --check src/aether_agents tests scripts
git diff --check
```

Result:
```text
All checks passed!
200 files already formatted
```
Exit code: `0`. `git diff --check` clean.

### 6. Pinned fork source digest derivation recipe

Recipe: `aether_agents.lifecycle._materialize_git_archive` followed by `aether_agents.lifecycle._tree_sha256` over the materialized source tree at commit `58f8c37a49b341f25b8fdd6310542fe932031b8d`.
- Materialized file count: 9,378 files.
- Resulting source tree digest: `a2a9b374bd2022c7f96242b0ab2c95691119262c925389eb3820ca627c581144` (matches Objective Contract `oc_c770cea3db51d97e@v2` exactly).

## Modified surface and preservation audit

### Writable surface (this unit):
- `scripts/qualify_rc16_transition.py` (isolated qualification entry with service boundary confinement)
- `tests/test_rc16_transition_qualification.py` (test suite verifying entry contract, oracles, and non-temp work root refusal)
- `tests/fixtures/rc16-transition/rc15-record.json` (published RC15 active record fixture)
- `tests/fixtures/rc16-transition/rc15-release-lock.json` (published RC15 release lock fixture)
- `specs/issue-494-project-provenance/evidence/RC16-TRANS.md` (this evidence document)

### Preserved surface (untouched):
- `VERSION`, `CHANGELOG.md`, `README.md`, `docs/**` (owned by `RC16-IDENT`)
- `.github/workflows/**` (CI policy and release workflows preserved)
- `entries/HLP-*.json`, aggregate, preflight, `HERMES_LOCAL_PATCHES.md` (owned by `RC16-HLP`)
- `scripts/qualify_mixed_version_lifecycle.py` (untouched and passing)
- `tests/test_lifecycle_projections.py` (untouched and passing)
- `tests/test_release_bundle.py` (untouched)
- `src/aether_agents/resources/**` (untouched)
- Primary worktree file `specs/001-aether-v1-productization/plan-rc6.md` (preserved)

## Downstream handoff notes for Supervisor (`RC16-INT`)

- **Manifest roster completion:** The new files added by this unit (`scripts/qualify_rc16_transition.py`, `tests/test_rc16_transition_qualification.py`, `tests/fixtures/rc16-transition/rc15-record.json`, `tests/fixtures/rc16-transition/rc15-release-lock.json`) are non-`specs/` files and are left for integration unit `RC16-INT` to add to the policy manifest in `.github/workflows/policy.yml`, following the established coordination pattern.
- **Candidate tag:** The candidate tag `v1.0.0-rc.16` was tested exclusively inside disposable clones in isolated work roots. The real annotated release tag is created by `RC16-INT` after merge on the integrated commit.
- **Unit review boundary:** Same-card review is requested (`kanban_request_review`, reviewer `supervisor`). Local commit only.
