# RC6-LIFE — Target-Compatible Active Record, Target-Owned Projections and Bounded Reconcile Evidence

**Unit**: RC6-LIFE (`t_60de3ef6`), role Implementer, worktree branch `aether-agents-2/t_60de3ef6-rc6-life-target-compatible-active-record`.
**Authority**: Objective Contract `oc_b5926701207812e8@v1` (SHA-256 `e7164c83862b747c7868706799c08ea63151ca388aa2dc2b1b89a40be33b01fc`), base `d2874c2f3fc839a82fbaa96ece6edebab3856298`, material design `specs/001-aether-v1-productization/plan-rc6.md` §L1/§L2, Supervisor breakdown `specs/001-aether-v1-productization/tasks-rc6.md`. Never edited or staged the canonical contract.
**Delivered scope**: Contract L1, L2; D1; Acceptance AC-1, AC-2; breakdown unit RC6-LIFE.
**Unit compatibility impact**: `patch` (internal bug fixes and completing reserved `--to active` reconcile surface without changing public schemas or breaking frozen interfaces).
**Revision note**: §7 records the second pass that answers the Supervisor review of candidate `f426c829`.

---

## 1. Summary of behavior and test coverage

This unit delivers the six required outcomes of the RC6-LIFE specification:

1. **Target-compatible active record**:
   - The immutable target `record.json` owns the persisted field set and values.
   - `ReleaseStore._target_active_payload(record)` reads the immutable `record.json` and updates only `previous_release_id` to the actual predecessor.
   - Optional-field absence versus explicit null is strictly preserved: absent fields are not serialized with source dataclass defaults (such as `tui_sha256: null`), and explicit nulls remain explicit nulls.
   - Unknown keys from the target record are preserved rather than dropped.
   - A target with no immutable `record.json` (absent or symlinked) now **refuses** instead of synthesizing a pointer from this process's dataclass, so source defaults can never be projected into an older target's field shape.
   - Concrete defect reproduced and verified: frozen rc3's authentic reader rejects `tui_sha256` (even when null) with `IntegrityError: malformed active release record`. With target-compatible active record serialization, the frozen rc3 reader parses the active pointer cleanly.
   - Tested in `tests/test_lifecycle_projections.py::test_target_compatible_active_record_preserves_target_field_shape_and_reader_semantics` and `::test_unreadable_target_record_refuses_instead_of_synthesizing_a_pointer`.

2. **Pre-mutation validation in the target manager subprocess**:
   - Before any pointer or projection mutation, the proposed active record runs through the exact target manager's reader in an isolated subprocess (`_validate_target_record_subprocess`).
   - Confirms target release identity and installed-record coherence (version, wheel_sha256, hermes_commit, authority_context, aether_identity, prebuild_identity, installed_file_fingerprint, observation_compatibility, observer).
   - Pure target-reader preparation in `activate_existing` runs before acquiring the cross-process lifecycle mutation lock and does not mutate live state.
   - The child is isolated so that the launcher's working directory cannot answer for the target: it runs with `-P -s`, `cwd` pinned to the target release root, and a `PYTHON*`-stripped environment; the embedded runner additionally asserts that `aether_agents.__file__` resolves inside the target release tree before it serves any request (`TARGET_IMPORT_PROVENANCE_MISMATCH` otherwise).
   - A target that cannot prove its record semantics or identity fails before cutover.
   - Tested in `tests/test_lifecycle_projections.py::test_incompatible_or_malformed_target_refuses_with_zero_byte_change` and `::test_target_runner_answers_only_from_the_target_release_not_the_invoking_directory`.

3. **Byte-exact compensation**:
   - Before cutover, the transition captures the exact active-record bytes from `self.store.active_pointer`.
   - On transition error, compensation restores the exact previously captured active-record bytes via `_atomic_bytes(self.store.active_pointer, prior_active_bytes)` rather than reserializing through a failing class.
   - Record and selector recovery stay strictly paired; selector symlink and opaque projection files are restored.
   - No success receipt precedes target-side validation: the transition journal is marked `failed` with `TRANSITION_VALIDATION_FAILED` on any cutover failure.
   - Tested in `tests/test_lifecycle_projections.py::test_transition_compensation_restores_byte_exact_previous_record_bytes`.

4. **Target-owned projections and brand-agnostic generalization**:
   - The authenticated target's Aether code determines launcher, Desktop, WSL and service projection bytes via `_prepare_target_projections_subprocess`.
   - Parent validates bounds and destination ownership against strict allowlists (`roots.launcher_dir / aether`, `roots.desktop_dir / {aether.desktop, hermes.desktop}`, `roots.service_dir / hermes-gateway-morfeo.service`, `roots.wsl_shortcuts_dir / {Aether.cmd, Continue-Aether.cmd}`).
   - Parent validates SHA-256 digests of all opaque projection bytes before applying.
   - An unavailable or refused target plan now **fails the transition before any pointer, unit, profile or projection byte moves**; the executing source's own `projection_spec` is never a silent substitute for a target that cannot produce its plan. `_activate_existing_locked` and `project_release` both propagate the refusal instead of degrading into a source-owned success.
   - The service-unit version discriminator remains brand-agnostic: `projection_spec` selects the later Hermes-owned service line with `_parse_version_tuple(version) >= (1, 0, 0, 3, 4)` (the `== "1.0.0rc4"` equality is gone). `_is_branded_version` is still used by other projection/doctor paths (`project_release` desktop ownership, `projection_status`, `_deactivate_lifecycle_projections`).
   - Service install/refresh runs through Hermes CLI only when the operation requires it (`hermes_owned` and `restart_service`); target projection preparation never calls service operations.
   - After applying projections, the parent validates from the selected target (`_validate_target_projections_subprocess`).
   - Tested in `tests/test_lifecycle_projections.py::test_reconcile_repairs_rc4_wrong_projection`, `::test_unavailable_target_projection_plan_refuses_before_any_mutation` and `tests/test_hermes_gateway_service.py`.

5. **Bounded reconcile surface (`aether reconcile --to active`)**:
   - Completed the reserved `aether reconcile --to active [--dry-run] [--yes] [--json]` CLI surface reusing the existing `recover()` / `_reconcile_release_projections_locked` path.
   - Preview (`--dry-run` or without `--yes`) is non-mutating: every managed byte on disk is identical before and after.
   - Authorized execution (`--yes`) reconciles only the already-active, authenticated release: does not select another release, does not install packages, does not restart services when read-only reconciliation suffices.
   - Unsupported modes (`--to installed` or omitting `--to active`) refuse explicitly with code 3 (`UNSUPPORTED_RECONCILE_MODE`).
   - *Correction (RC6-LIFE-2)*: An earlier revision claimed that CLI messages pointing operators at `aether reconcile --to active` were fully functional, but RC6-QUAL (`t_a99c2b55`) discovered that `_STATEFUL_COMMANDS` in `src/aether_agents/cli.py` omitted `"reconcile"`. As a result, entry-point invocations (launcher `<data>/runtime/current/venv/bin/aether`, release runtime `venv/bin/aether`, or public uv tool `aether`) ran `_run_reconcile` in the invoking process rather than dispatching to the manager, failing authority proof with `RECONCILE_REFUSED: executing process is not the active manager`. RC6-LIFE-2 (`t_6438f8d9`) fixed this wiring gap by adding `"reconcile"` to `_STATEFUL_COMMANDS` and routing entry points to the authenticated active manager subprocess.
   - Tested in `tests/test_lifecycle_projections.py::test_reconcile_to_active_surface` and `::test_reconcile_to_active_dispatches_to_active_manager_environment`.

6. **Safe refusal of unsupported legacy routes**:
   - An active release that cannot authenticate itself (e.g. legacy rc3 lacking `installed_file_fingerprint` or build identity) is refused before mutation under `aether reconcile --to active`.
   - Refusal is reported as `RECONCILE_REFUSED` / unsupported legacy route with zero byte change to record, selector, projections, or unit files.
   - Tested in `tests/test_lifecycle_projections.py::test_legacy_route_refusal_before_mutation`.

---

## 2. Requirement → Check → Observed Result → Evidence Path

| Obligation | Source Ref | Check Executed | Observed Result | Evidence Location |
|---|---|---|---|---|
| Target-compatible active record | AC-1, L1 | `test_target_compatible_active_record_preserves_target_field_shape_and_reader_semantics` | PASS: `tui_sha256` absent from active.json; absence vs null preserved; frozen rc3 `ReleaseRecord.from_json` parses successfully | `tests/test_lifecycle_projections.py:1262` |
| No source-shaped pointer synthesis | AC-1, L1 | `test_unreadable_target_record_refuses_instead_of_synthesizing_a_pointer` | PASS: absent `record.json` and symlinked `record.json` both raise `target release … has no immutable record to persist`; no `asdict` fallback remains | `tests/test_lifecycle_projections.py:1846`, `src/aether_agents/lifecycle.py:2343` |
| Pre-mutation target validation | AC-1, L1 | `test_incompatible_or_malformed_target_refuses_with_zero_byte_change` | PASS: unknown target keys refuse before cutover; hashes of active.json, selector, launcher, desktop, service unchanged | `tests/test_lifecycle_projections.py:1386` |
| Target import provenance is not spoofable from cwd | AC-1, L1 | `test_target_runner_answers_only_from_the_target_release_not_the_invoking_directory` | PASS: with a project-local `aether_agents` package in the launcher's cwd, the payload the real target reader refuses still refuses (`RECORD_SYNTAX_REJECTED`) and plan bytes equal the target's own spec | `tests/test_lifecycle_projections.py:1714`, `src/aether_agents/lifecycle.py:3345`, `src/aether_agents/lifecycle.py:3834` |
| Fail-closed target projection preparation | AC-2, L2 | `test_unavailable_target_projection_plan_refuses_before_any_mutation` | PASS: an unavailable target plan aborts the transition; active record bytes, selector, launcher, desktop and unit hashes identical; no service restart; no target-side promotion | `tests/test_lifecycle_projections.py:1765`, `src/aether_agents/lifecycle.py:6129`, `src/aether_agents/lifecycle.py:7328` |
| Byte-exact compensation | AC-1, L1 | `test_transition_compensation_restores_byte_exact_previous_record_bytes` | PASS: exact previously captured active-record bytes restored (SHA-256 match); selector symlink paired; no reserialization through the failing class | `tests/test_lifecycle_projections.py:1342` |
| Target-owned projections | AC-2, L2 | `test_reconcile_repairs_rc4_wrong_projection`, `tests/test_hermes_gateway_service.py` | PASS: target determines projection bytes; parent validates allowlisted destinations and digests; brand-agnostic version discriminator; service restart avoided when read-only suffices | `tests/test_lifecycle_projections.py:1511`, `src/aether_agents/lifecycle.py:3881` |
| Bounded reconcile surface | AC-2, L2 | `test_reconcile_to_active_surface` | PASS: `--dry-run` leaves every byte unchanged; `--yes` repairs active projections; idempotent on second run (`no_change`); `--to installed` exits 3 | `tests/test_lifecycle_projections.py:1449`, `src/aether_agents/cli.py:800` |
| Safe legacy route refusal | AC-2, L2 | `test_legacy_route_refusal_before_mutation` | PASS: rc3 active release refuses before mutation with `RECONCILE_REFUSED`; witnessed hashes byte-identical before/after | `tests/test_lifecycle_projections.py:1585` |
| Reconcile entry-point manager dispatch | AC-2, L2 | `test_reconcile_to_active_dispatches_to_active_manager_environment` | PASS: entry point running outside active manager dispatches `reconcile --to active` to active manager interpreter; preview and `--yes` apply verified | `tests/test_lifecycle_projections.py:1880`, `src/aether_agents/cli.py:43` |
| Reconcile refusal when no active manager | AC-2, L2 | `test_reconcile_refuses_when_no_active_manager` | PASS: returns exit 4 with `ACTIVE_MANAGER_AUTHORITY_REQUIRED` when target is None | `tests/test_lifecycle_projections.py:1970`, `src/aether_agents/cli.py:273` |
| Reconcile unsupported mode before bootstrap | AC-2, L2 | `test_reconcile_unsupported_mode_without_active_manager` | PASS: `--to installed` and missing `--to` return exit 3 with `UNSUPPORTED_RECONCILE_MODE` before dispatch | `tests/test_lifecycle_projections.py:1997`, `src/aether_agents/cli.py:946` |
| Reconcile recursion guard for stale manager | AC-2, L2 | `test_reconcile_stale_managed_manager_refuses_recursion` | PASS: stale managed manager refuses recursion with exit 4 (`ACTIVE_MANAGER_AUTHORITY_REQUIRED`) | `tests/test_lifecycle_projections.py:2022`, `src/aether_agents/cli.py:254` |
| Verification isolation | #439 lessons | `test_disposable_lane_cannot_reach_the_operator_unit_or_systemctl` | PASS: disposable store resolves confined roots and a disabled controller; operator destination witnesses unchanged | `tests/test_lifecycle_projections.py:1133` |
| Regression / Focused suite | AC-1, AC-2 | `uv run --frozen pytest -q tests/test_lifecycle_projections.py tests/test_tui_projections.py tests/test_hermes_gateway_service.py tests/test_observation_lifecycle.py` | PASS: **157 passed** (150 pre-existing + 3 pass-2 + 4 pass-3 nodes) | Terminal log, this revision |
| Code quality / Formatting / Types | AC-1, AC-2 | `uv run --frozen ruff check src/aether_agents tests scripts` && `uv run --frozen ruff format --check src/aether_agents tests scripts` && `uv run --frozen mypy src/aether_agents` | PASS: Ruff clean, 175 files already formatted, mypy clean (68 source files) | Terminal log, this revision |
| Public-artifact hygiene | shared decision 9 | `uv run --frozen python scripts/check_public_artifacts.py` | PASS: tracked surface scan passed; no operator-local paths, secrets or session content | Terminal log, this revision |
| Documentation validation gate | AC-1, AC-2 | `python scripts/check_documentation.py` | EXITS 1 on this branch (3 uncovered derived surfaces: `cli.option.aether.reconcile.--dry-run/--to/--yes`); identical to base `e9595d2e`; PASS (exit 0) on composed revision `3dbde1e4` / `5bf3dac7` where `docs/capabilities.toml` declares them (see section 8) | Terminal log, this revision |

### Oracle discipline (which nodes are decisive RED)

- **Decisive RED nodes**:
  - `test_reconcile_to_active_dispatches_to_active_manager_environment` (RC6-LIFE-2 pass 3): verified to fail at base `e9595d2e` with `assert 4 == 0` and stdout `RECONCILE_REFUSED: no active release to reconcile` because `_STATEFUL_COMMANDS` omitted `"reconcile"`, bypassing `_dispatch_stateful_to_active` and running `_run_reconcile` in-process where active manager authority failed.
  - `test_target_runner_answers_only_from_the_target_release_not_the_invoking_directory` (pass 2): failed on candidate `f426c829` as `DID NOT RAISE IntegrityError` (hostile-cwd spoof).
  - `test_unavailable_target_projection_plan_refuses_before_any_mutation` (pass 2): failed on candidate `f426c829` as `DID NOT RAISE IntegrityError` (swallowed plan).
  - `test_unreadable_target_record_refuses_instead_of_synthesizing_a_pointer` (pass 2): failed on candidate `f426c829` as `DID NOT RAISE IntegrityError` (`asdict(record)` fallback).
  - Pass 1 RED set: frozen-rc3 target-shape node, both reconcile nodes and legacy refusal (reproduced at base `d2874c2f`: `4 failed, 2 passed`).
- **Non-RED oracles (preservation, not defect reproductions)**:
  - `test_transition_compensation_restores_byte_exact_previous_record_bytes` is a preservation oracle.
  - `test_incompatible_or_malformed_target_refuses_with_zero_byte_change` documents refusal semantics.
- **Fixture boundary disclosed**:
  - `test_reconcile_to_active_surface` and `test_reconcile_repairs_rc4_wrong_projection` monkeypatch `LifecycleManager.executing_active_manager` / `cli._lifecycle_manager`, testing manager-internal reconciliation in-process. This monkeypatch was why the wiring gap survived in earlier passes.
  - `test_reconcile_to_active_dispatches_to_active_manager_environment` does not mock `executing_active_manager` (it executes `cli_main` as an external entry point), but it does monkeypatch `active_manager_dispatch_target` and uses a shim interpreter printing a canned envelope. It proves that `main()` → stateful command detection → `_dispatch_stateful_to_active()` launches a real subprocess with the exact argv and isolated environment (`-m aether_agents.cli reconcile --to active …`), and does not prove target resolution or execution inside a real manager environment.

---

## 3. Direct versus Reused Attribution

- **Direct implementation (this card)**:
  - Target-compatible active record serialization in `ReleaseStore._target_active_payload` and `ReleaseStore._commit_active`, including refusal when the target has no immutable record.
  - Target manager isolated subprocess runner `_TARGET_RUNNER_SCRIPT` supporting `validate_record`, `prepare_projections`, and `validate_projections`, with child isolation (`-P -s`, target-root `cwd`) and an in-runner import-provenance assertion.
  - Parent allowlist and bound validation in `LifecycleManager._prepare_target_projections_subprocess`.
  - Fail-closed target-plan preparation in `LifecycleManager._activate_existing_locked` and `LifecycleManager.project_release`.
  - Target projection application and target-side post-switch validation in `LifecycleManager.project_release`.
  - Byte-exact active record compensation via `self.store._restoring_prior_bytes` and `_atomic_bytes`.
  - Bounded CLI surface `aether reconcile --to active [--dry-run] [--yes] [--json]` in `src/aether_agents/cli.py`.
  - 9 focused verification nodes in `tests/test_lifecycle_projections.py` plus fixture updates in the four focused test modules.
- **Reused mechanisms (unchanged)**:
  - Cross-process lifecycle mutation lock and journal state machine (`ReleaseStore._begin_transition_locked`, `_finish_transition_locked`).
  - Observation projection transition protocol (`_run_projection_transition_locked`).
  - Projection roots isolation (`ProjectionRoots.disposable`).
  - Profile homes materialization and validation.
  - Existing recovery path in `LifecycleManager.recover()`.

---

## 4. Manifest Lines

Non-specs tracked files added, renamed, or removed: **NONE**.
All changes were made in existing tracked files:
- `src/aether_agents/lifecycle.py`
- `src/aether_agents/cli.py`
- `tests/test_lifecycle_projections.py`
- `tests/test_tui_projections.py`
- `tests/test_hermes_gateway_service.py`
- `tests/test_observation_lifecycle.py`
- `specs/001-aether-v1-productization/evidence/RC6-LIFE.md`

No additions or modifications to `.github/workflows/policy.yml` are required for this unit.

---

## 5. Residual Risk and Environment Limits

- **WSL Terminal Shortcuts**: Tested in disposable/mock directories in unit tests; end-to-end qualification on real WSL Windows Terminal paths is owned by RC6-QUAL.
- **Candidate Activation**: Actual live runtime cutover and service restart are owned by RC6-CLOSE; this unit performed zero live mutations or systemctl interactions.
- **Confinement**: All tests were confined to `tmp_path` with isolated `HOME`, `XDG_DATA_HOME`, `XDG_STATE_HOME`, `XDG_CONFIG_HOME`, and disposable projection roots. Live installation and operator configuration remained untouched.
- **Synthetic manager environments**: The focused test fixtures emulate an installed release by materializing the product package inside the release tree (plus the wheel's force-included schema bytes). They are labelled as emulations; real mixed-version interpreter behavior against frozen rc3/rc4/rc5 artifacts remains RC6-QUAL's campaign.
- **Documentation gate lineage dependency**: `python scripts/check_documentation.py` exits 1 on this unit's isolated branch due to three uncovered CLI reconcile options (`--to`, `--dry-run`, `--yes`) that are registered in the CLI parser but declared in `docs/capabilities.toml` only on the RC6-DOCS lineage. The failure is identical at base `e9595d2e` and cleanly resolves (exit 0) upon integration with the composed candidate (`3dbde1e4` / `5bf3dac7`). Neither `docs/**` nor `docs/capabilities.toml` is in this unit's writable boundary.
- **Pre-existing, outside this unit**: `tests/test_public_artifacts.py::test_canonical_base_manifest_matches_tracked_non_specs_files` fails identically on the unmodified branch tip (`website/tsconfig.json` is tracked but absent from `.github/workflows/policy.yml`); `.github/workflows/policy.yml` is explicitly not this unit's writable surface and stays untouched. `tests/test_observation_lifecycle.py::test_exact_public_lifecycle_uses_real_plugin_profiles_query_and_recovery` is an environment-dependent integration lane (it raised `ModuleNotFoundError: No module named 'hermes_cli'` when run standalone both before and after this change, and passes inside the full focused run).

---

## 6. Reproduction of the decisive defect (first pass)

The rc3 reader incompatibility is reproduced with the *real frozen* rc3 code (`git show d8ff984c…:src/aether_agents/lifecycle.py`), never an emulated dataclass: the frozen reader rejects a payload carrying `tui_sha256` (even `null`) and accepts the pointer written by the corrected path. The rc4 wrong-projection reproduction and the exact rc5 → candidate → rc5 → candidate cycle remain RC6-QUAL's decisive fixtures and are not duplicated here.

---

## 7. Second pass — Supervisor review of `f426c829` (findings and fixes)

The Supervisor review of candidate `f426c829b8bc3093b6b0594dda8d0872751c7108` (run 15) recorded three source-boundary findings. Each is fixed at the source and pinned by a decisive RED node.

1. **Blocking — the target boundary was spoofable from the launcher's cwd.**
   - Finding: `_run_target_lifecycle_subprocess()` ran `[target_python, "-c", script]` with no `cwd=` and no `-P`/`-I`, so `python -c` put the invoking directory at `sys.path[0]` ahead of the target's own environment; a project-local `aether_agents` package answered for the target (the Supervisor measured `ACCEPTED` where the real reader returned `RECORD_SYNTAX_REJECTED`).
   - Fix: the child now runs `[target_python, "-P", "-s", "-c", script]` with `cwd` pinned to the target release root and the existing `PYTHON*`-stripped environment, and the embedded runner asserts that the imported `aether_agents.__file__` resolves inside `store.release_path(release_id)` before it serves any operation, failing `TARGET_IMPORT_PROVENANCE_MISMATCH` otherwise. The fixed-operation request/response protocol and its bounds are unchanged.
   - Node: `test_target_runner_answers_only_from_the_target_release_not_the_invoking_directory`.

2. **Blocking — an unavailable target plan silently became a source-owned successful transition.**
   - Finding: `_activate_existing_locked` and `project_release` wrapped target-plan preparation in `except Exception: projection_plan = None`, then applied `self.projection_spec(record)` bytes and skipped `_validate_target_projections_subprocess`, converting allowlist/digest refusals, malformed responses, timeouts and incompatible target APIs into completed transitions.
   - Fix: both catch sites are gone. Plan preparation failure now propagates through the existing failure path — the transition is marked failed, the pre-transition active-record bytes are restored byte-exactly, and the operator sees the target refusal. No source-owned projection path remains in `project_release`.
   - Node: `test_unavailable_target_projection_plan_refuses_before_any_mutation`.

3. **Required hardening — no synthesized target shape.**
   - Finding: `_target_active_payload` fell back to `asdict(record)` when the target `record.json` was absent or a symlink, adding `tui_sha256`, `aether_identity`, `installed_file_fingerprint` and `prebuild_identity` for a target that has none (reachable through the public API only as defence-in-depth, since `_read_release` already refuses a missing record).
   - Fix: the branch is removed; a missing, symlinked or unreadable target record raises `IntegrityError` (`target release <id> has no immutable record to persist`) instead of producing a source-shaped pointer.
   - Node: `test_unreadable_target_record_refuses_instead_of_synthesizing_a_pointer`.

### Fixture consequence of the isolation fix (and why it is not a mock standing in for real behavior)

Because the child now proves that it runs the target's own code, the focused fixtures can no longer reach into the checkout for the product package. `_release_manager_python` (lifecycle projections), `_materialize_manager_environment` (TUI projections, gateway service) and `_prepared_release` (observation lifecycle) now materialize the package **inside the release tree** and point the synthetic interpreter at it, which is what an installed release has.

While doing so the fixtures surfaced a real byte-set difference between an installed wheel and a bare source copy: `aether_agents.observation.contracts.schema_path()` prefers `resources/schemas/*.schema.json` (present only in the wheel, force-included from `specs/**/contracts/`) and otherwise falls back to a repository-relative `specs/` path that a copy inside a release tree cannot reach. Without the packaged schemas the child silently validated no events (`EVENT_SCHEMA_OR_PRIVACY_INVALID`, 0 events ingested). The fixtures therefore reproduce the wheel's force-include mapping from `pyproject.toml` (`_materialize_packaged_resources`), so an emulated install carries the same schema bytes the real wheel does. This is documented behavior of the packaging recipe (OBS-FR-075), not a product defect: real releases install the wheel.

### Verification after the fixes

| Check | Command | Observed result |
|---|---|---|
| Focused suite | `uv run --frozen pytest -q tests/test_lifecycle_projections.py tests/test_tui_projections.py tests/test_hermes_gateway_service.py tests/test_observation_lifecycle.py` | **153 passed** in 165.03 s |
| New nodes against the previous candidate | same module, `-k "answers_only_from or unavailable_target_projection or unreadable_target_record"`, candidate source `f426c829` copied over `src/aether_agents/lifecycle.py` | **3 failed** — all three `DID NOT RAISE IntegrityError` (decisive RED), then the corrected source restored and re-verified byte-identical |
| Static gates | `ruff check`, `ruff format --check`, `mypy src/aether_agents`, `python scripts/check_public_artifacts.py` | clean (175 formatted, 68 source files, scan passed) |

### Read-only acceptance probe against the real frozen releases

The import-provenance rule must accept a genuinely installed release, not only the synthetic fixtures. A strictly read-only probe (`env -i … -B -P -s -c 'import aether_agents; …'`, bytecode writing disabled, no lifecycle call, no store access) of the three frozen manager interpreters that exist on this machine shows:

- every release's manager environment is Python 3.13, so `-P` and `-s` are supported by the interpreters this transition drives;
- `aether_agents.__file__` resolves to `<live-data-root>/releases/<release-id>/manager/lib/python3.13/site-packages/aether_agents/__init__.py` for `1.0.0rc3-*`, `1.0.0rc4-*` and `1.0.0rc5-*` alike — inside each release's own tree, so the runner's provenance assertion accepts them and no live byte was written by the probe.

---

## 8. Third pass — RC6-LIFE-2 (`t_6438f8d9`): Active manager dispatch wiring for `aether reconcile --to active`

### Confirmed defect and reproduction

During RC6-QUAL (`t_a99c2b55`), qualification revealed that `_STATEFUL_COMMANDS = ("setup", "update", "rollback", "uninstall")` in `src/aether_agents/cli.py` omitted `"reconcile"`. Although `_dispatch_stateful_to_active` contained a reconcile-specific branch at line 261, `main()` never dispatched reconcile invocations because `reconcile` was not member of `_STATEFUL_COMMANDS`. Consequently, entry-point invocations (the projected launcher `<data>/runtime/current/venv/bin/aether`, the release runtime `venv/bin/aether`, or the public uv tool `aether`) fell through to `_run_reconcile` in the invoking process. Since the invoking process is not the active manager, `manager.executing_active_manager()` raised `IntegrityError: executing process is not the active manager`, returning exit code 4 with `RECONCILE_REFUSED`.

This wiring gap went undetected in passes 1 and 2 because `test_reconcile_to_active_surface` monkeypatched `executing_active_manager` and `_lifecycle_manager`, satisfying authority checks in-process without exercising the entry-point dispatch path.

### Decisive RED receipt

`tests/test_lifecycle_projections.py::test_reconcile_to_active_dispatches_to_active_manager_environment` exercises the entry-point dispatch path without monkeypatching `executing_active_manager`. It sets up an isolated store with an authenticated active release record and a manager probe script (`probe_python`). When `cli_main(["reconcile", "--to", "active", "--json"])` is invoked from outside the active manager, the test asserts that dispatch routes execution to `probe_python`, writing a witness receipt and returning exit code 0 (`result: planned`).

- **Command**: `uv run --frozen pytest tests/test_lifecycle_projections.py -k "test_reconcile_to_active_dispatches_to_active_manager_environment"`
- **Revision**: `e9595d2e97aa85f2e0d7e4a501215865c0ab06ca` (unpatched base)
- **Observed Result**: `FAILED: assert 4 == 0`.
  Captured stdout: `{"changed":false,"command":"reconcile","data":{},"errors":[{"code":"RECONCILE_REFUSED","message":"no active release to reconcile"}],"manager_version":"1.0.0rc5","result":"error","schema_version":1,"warnings":[]}`.
  Witness file was not created because dispatch was never invoked.

*Fixture boundary disclosure*: The test node does not mock `executing_active_manager` (it executes `cli_main` as an external entry point), but it does monkeypatch `active_manager_dispatch_target` and uses a shim interpreter (`probe_python`) printing a canned envelope. It proves that `main()` → stateful command detection → `_dispatch_stateful_to_active()` launches a real subprocess with the exact argv and isolated environment (`-m aether_agents.cli reconcile --to active …`), and does not prove target resolution or execution inside a real manager environment.

### Changes implemented

1. **Declared stateful command**: Added `"reconcile"` to `_STATEFUL_COMMANDS = ("setup", "update", "rollback", "uninstall", "reconcile")` in `src/aether_agents/cli.py`.
2. **Early parse guard for unsupported modes**: In `main()`, if `args.command == "reconcile"` and `getattr(args, "to", None) != "active"`, control routes immediately to `_run_reconcile(args)` before dispatch. This returns exit code 3 (`UNSUPPORTED_RECONCILE_MODE`) with zero change, avoiding unnecessary subprocess spawning and functioning consistently before or after bootstrap.
3. **Execution context and non-recursive loop guard**: In `_dispatch_stateful_to_active`:
   - If the executing process is already the authenticated active manager (`executing_active_manager()` succeeds), returns `None` so the command runs in-process.
   - If the process is a stale managed manager (`executing_manager_is_release_scoped()` is true), refuses recursion with exit code 4 (`ACTIVE_MANAGER_AUTHORITY_REQUIRED`).
   - If `active_manager_dispatch_target()` raises `IntegrityError` (e.g. unauthenticated legacy release lacking an installed-file fingerprint), emits `RECONCILE_REFUSED` with exit code 4, satisfying obligation (4) and preserving `test_legacy_route_refusal_before_mutation`.
   - If `target is None` (uninitialized product), retains the existing reconcile branch returning `ACTIVE_MANAGER_AUTHORITY_REQUIRED` with exit code 4.
     *Design choice rationale*: For condition (5), returning `ACTIVE_MANAGER_AUTHORITY_REQUIRED` at the entry-point dispatch boundary matches how other stateful commands (`rollback`, `uninstall`) report the absence of an active release manager before product bootstrap, providing consistent remediation guidance (`aether setup`, etc.) from the entry point.
   - Otherwise, dispatches via `subprocess.run([str(manager_python), "-m", "aether_agents.cli", *args_list], env=environment)` in a clean environment.

### Entry-point route receipts and expected shapes

*Note on execution scope*: The projected-launcher (`<data>/aether-projections/bin/aether` or `<data>/runtime/current/venv/bin/aether`) and release-runtime (`venv/bin/aether`) entry-point forms are **not** exercised by this unit because the local candidate route refuses without an annotated release tag matching `VERSION` (`_release_tag_at` requires the tag to equal `v{display}`), this branch carries `VERSION=1.0.0rc5`, and the accepted rc5 tag is immutable — meaning any store the projected launcher or release runtime could run through holds other code. That complete entry-point qualification matrix belongs to RC6-QUAL's recomposed run, whose pre-fix refusal through the projected launcher (`<data>/aether-projections/bin/aether reconcile --to active --json` -> exit 4) is already recorded in `scenarios/legacy.json`.

Below, rows tested within this unit's test suite report the invocation form actually used and its verbatim observed output; entry-point invocations requiring candidate release packaging are explicitly identified as the documented expected shape:

1. **Preview route** (`--dry-run` or no `--yes`):
   - *Unit test invocation actually used*: `cli_main(["reconcile", "--to", "active", "--json"])` in `tests/test_lifecycle_projections.py::test_reconcile_to_active_surface` (in-process manager mode, verifying non-mutation) and `::test_reconcile_to_active_dispatches_to_active_manager_environment` (dispatch path launching subprocess).
   - *Documented expected shape via entry point*:
     ```text
     $ aether reconcile --to active --json
     {"schema_version": 1, "command": "reconcile", "result": "planned", "changed": false, "manager_version": "1.0.0rc6", "active_version": "1.0.0-rc.6", "warnings": [{"code": "CONFIRMATION_REQUIRED", "message": "Re-run reconcile with --yes to apply projections."}], "errors": [], "data": {"mode": "active", "active_release_id": "<active_id>", "mismatches": [...], "projections_reconciled": 0}}
     -> exit 0
     ```

2. **Apply route** (`--yes`):
   - *Unit test invocation actually used*: `cli_main(["reconcile", "--to", "active", "--yes", "--json"])` in `tests/test_lifecycle_projections.py::test_reconcile_to_active_surface` (in-process manager mode, verifying projection repair) and `::test_reconcile_to_active_dispatches_to_active_manager_environment` (dispatch path).
   - *Documented expected shape via entry point*:
     ```text
     $ aether reconcile --to active --yes --json
     {"schema_version": 1, "command": "reconcile", "result": "changed", "changed": true, "manager_version": "1.0.0rc6", "active_version": "1.0.0-rc.6", "warnings": [], "errors": [], "data": {"mode": "active", "active_release_id": "<active_id>", "mismatches": [], "projections_reconciled": 1, "recovered": {...}}}
     -> exit 0
     ```

3. **Idempotency** (subsequent `--yes`):
   - *Unit test invocation actually used*: consecutive `cli_main(["reconcile", "--to", "active", "--yes", "--json"])` in `tests/test_lifecycle_projections.py::test_reconcile_to_active_surface` observing `result: no_change` and `projections_reconciled: 0`.
   - *Documented expected shape via entry point*:
     ```text
     $ aether reconcile --to active --yes --json
     {"schema_version": 1, "command": "reconcile", "result": "no_change", "changed": false, "manager_version": "1.0.0rc6", "active_version": "1.0.0-rc.6", "warnings": [], "errors": [], "data": {"mode": "active", "active_release_id": "<active_id>", "mismatches": [], "projections_reconciled": 0, "recovered": {...}}}
     -> exit 0
     ```

4. **Unsupported modes** (`--to installed` or missing `--to`):
   - *Unit test invocation actually used*: `cli_main(["reconcile", "--to", "installed", "--json"])` and `cli_main(["reconcile", "--json"])` in `tests/test_lifecycle_projections.py::test_reconcile_unsupported_mode_without_active_manager`.
   - *Verbatim observed output* (evaluated before dispatch or bootstrap):
     ```text
     $ aether reconcile --to installed --json
     {"changed": false, "command": "reconcile", "data": {}, "errors": [{"code": "UNSUPPORTED_RECONCILE_MODE", "message": "'aether reconcile --to installed' is part of the A1 manager contract and is not implemented in this build; use 'aether reconcile --to active'"}], "manager_version": "1.0.0rc5", "result": "unsupported", "schema_version": 1, "warnings": []}
     -> exit 3
     ```

5. **Unauthenticated legacy release** (no installed-file fingerprint):
   - *Unit test invocation actually used*: `cli_main(["reconcile", "--to", "active", "--yes", "--json"])` in `tests/test_lifecycle_projections.py::test_legacy_route_refusal_before_mutation` (in-process manager mode against synthetic legacy release lacking fingerprint).
   - *Verbatim observed output*:
     ```text
     $ aether reconcile --to active --yes --json
     {"changed": false, "command": "reconcile", "data": {}, "errors": [{"code": "RECONCILE_REFUSED", "message": "active release 1.0.0rc3-20260910000000 cannot prove authentication; unsupported legacy route"}], "manager_version": "1.0.0rc5", "result": "error", "schema_version": 1, "warnings": []}
     -> exit 4
     ```

6. **No active manager** (uninitialized product):
   - *Unit test invocation actually used*: `cli_main(["reconcile", "--to", "active", "--json"])` in `tests/test_lifecycle_projections.py::test_reconcile_refuses_when_no_active_manager` (running from outside manager with `active_manager_dispatch_target` returning `None`).
   - *Verbatim observed output*:
     ```text
     $ aether reconcile --to active --json
     {"changed": false, "command": "reconcile", "data": {"remediation": ["aether doctor", "aether reconcile --to active", "aether rollback"]}, "errors": [{"code": "ACTIVE_MANAGER_AUTHORITY_REQUIRED", "message": "no active manager can authorize reconciliation; unsupported legacy route or uninitialized product"}], "manager_version": "1.0.0rc5", "result": "error", "schema_version": 1, "warnings": []}
     -> exit 4
     ```

### Verification after RC6-LIFE-2

| Check | Command | Observed result |
|---|---|---|
| Focused suite | `uv run --frozen python scripts/run_tests.py -- -q tests/test_lifecycle_projections.py tests/test_tui_projections.py tests/test_hermes_gateway_service.py tests/test_observation_lifecycle.py` | **157 passed** in 172.57 s |
| Decisive RED node (reproduced) | `uv run --frozen pytest tests/test_lifecycle_projections.py -k "test_reconcile_to_active_dispatches_to_active_manager_environment"` | FAILED on `e9595d2e` (`assert 4 == 0`), PASS on this revision |
| Code quality / Formatting / Types | `ruff check`, `ruff format --check`, `mypy src/aether_agents` | All clean: ruff clean, 175 files formatted, mypy clean (68 source files) |
| Public-artifact hygiene | `python scripts/check_public_artifacts.py` | PASS: tracked surface scan passed; no operator-local paths, secrets or session content |
| Documentation validation gate | `python scripts/check_documentation.py` | **EXITS 1 on this branch** (3 uncovered derived surfaces: `cli.option.aether.reconcile.--dry-run`, `--to`, `--yes`). Fails identically at base `e9595d2e` because `docs/capabilities.toml` on this lineage does not include the DOCS lineage's capability declarations. On the composed candidate revision (`3dbde1e4` or preview `5bf3dac7`), where `docs/capabilities.toml` declares `cli.reconcile` (status `partial`), `python scripts/check_documentation.py` exits 0 cleanly and `pytest tests/test_documentation.py tests/test_public_artifacts.py` passes (27 passed). |

### Residual limits

- **WSL2 Windows Terminal paths**: Handled within test fixtures with mock paths; live WSL qualification belongs to RC6-QUAL.
- **End-to-end multi-interpreter qualification**: The qualification harness exercises live cross-release transitions; this unit provides the verified CLI dispatch mechanics.
- **Live activation/cutover**: Owned by RC6-CLOSE.
