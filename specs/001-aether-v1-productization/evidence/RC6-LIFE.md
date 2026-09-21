# RC6-LIFE — Target-Compatible Active Record, Target-Owned Projections and Bounded Reconcile Evidence

**Unit**: RC6-LIFE (`t_60de3ef6`), role Implementer, worktree branch `aether-agents-2/t_60de3ef6-rc6-life-target-compatible-active-record`.
**Authority**: Objective Contract `oc_b5926701207812e8@v1` (SHA-256 `e7164c83862b747c7868706799c08ea63151ca388aa2dc2b1b89a40be33b01fc`), base `d2874c2f3fc839a82fbaa96ece6edebab3856298`, material design `specs/001-aether-v1-productization/plan-rc6.md` §L1/§L2, Supervisor breakdown `specs/001-aether-v1-productization/tasks-rc6.md`. Never edited or staged the canonical contract.
**Delivered scope**: Contract L1, L2; D1; Acceptance AC-1, AC-2; breakdown unit RC6-LIFE.
**Unit compatibility impact**: `patch` (internal bug fixes and completing reserved `--to active` reconcile surface without changing public schemas or breaking frozen interfaces).

---

## 1. Summary of behavior and test coverage

This unit delivers the six required outcomes of the RC6-LIFE specification:

1. **Target-compatible active record**:
   - The immutable target `record.json` owns the persisted field set and values.
   - `ReleaseStore._target_active_payload(record)` reads the immutable `record.json` and updates only `previous_release_id` to the actual predecessor.
   - Optional-field absence versus explicit null is strictly preserved: absent fields are not serialized with source dataclass defaults (such as `tui_sha256: null`), and explicit nulls remain explicit nulls.
   - Unknown keys from the target record are preserved rather than dropped.
   - Concrete defect reproduced and verified: frozen rc3's authentic reader rejects `tui_sha256` (even when null) with `IntegrityError: malformed active release record`. With target-compatible active record serialization, the frozen rc3 reader parses the active pointer cleanly.
   - Tested in `tests/test_lifecycle_projections.py::test_target_compatible_active_record_preserves_target_field_shape_and_reader_semantics`.

2. **Pre-mutation validation in target manager subprocess**:
   - Before any pointer or projection mutation, the proposed active record runs through the exact target manager's reader in an isolated subprocess (`_validate_target_record_subprocess`).
   - Confirms target release identity and installed-record coherence (version, wheel_sha256, hermes_commit, authority_context, aether_identity, prebuild_identity, installed_file_fingerprint, observation_compatibility, observer).
   - Pure target-reader preparation in `activate_existing` runs before acquiring the cross-process lifecycle mutation lock and does not mutate live state.
   - A target that cannot prove its record semantics or identity fails before cutover.
   - Tested in `tests/test_lifecycle_projections.py::test_incompatible_or_malformed_target_refuses_with_zero_byte_change`.

3. **Byte-exact compensation**:
   - Before cutover, `_transition_release` captures the exact active-record bytes from `self.store.active_pointer`.
   - On transition error, compensation restores the exact previously captured active-record bytes via `_atomic_bytes(self.store.active_pointer, prior_active_bytes)` rather than reserializing through a failing class.
   - Record and selector recovery stay strictly paired; selector symlink and opaque projection files are restored.
   - No success receipt precedes target-side validation: transition journal is marked `failed` with `TRANSITION_VALIDATION_FAILED` on any cutover failure.
   - Tested in `tests/test_lifecycle_projections.py::test_transition_compensation_restores_byte_exact_previous_record_bytes`.

4. **Target-owned projections and brand-agnostic generalization**:
   - The authenticated target's Aether code determines launcher, Desktop, and WSL projection bytes via `_prepare_target_projections_subprocess`.
   - Parent validates bounds and destination ownership against strict allowlists (`roots.launcher_dir / aether`, `roots.desktop_dir / {aether.desktop, hermes.desktop}`, `roots.service_dir / hermes-gateway-morfeo.service`, `roots.wsl_shortcuts_dir / {Aether.cmd, Continue-Aether.cmd}`).
   - Parent validates SHA-256 digests of all opaque projection bytes before applying.
   - Replaced source branding equality (`record.version == "1.0.0rc4"`) with brand-agnostic `_is_branded_version(record.version)` for service TUI lines.
   - Service install/refresh runs through Hermes CLI only when the operation requires it (`hermes_owned` and `restart_service`); target projection preparation never calls service operations.
   - After applying projections, parent validates from the selected target (`_validate_target_projections_subprocess`).
   - Tested in `tests/test_lifecycle_projections.py::test_reconcile_repairs_rc4_wrong_projection` and `tests/test_hermes_gateway_service.py`.

5. **Bounded reconcile surface (`aether reconcile --to active`)**:
   - Completed the reserved `aether reconcile --to active [--dry-run] [--yes] [--json]` CLI surface reusing the existing `recover()` / `_reconcile_release_projections_locked` path.
   - Preview (`--dry-run` or without `--yes`) is non-mutating: every managed byte on disk is identical before and after.
   - Authorized execution (`--yes`) reconciles only the already-active, authenticated release: does not select another release, does not install packages, does not restart services when read-only reconciliation suffices.
   - Unsupported modes (`--to installed` or omitting `--to active`) refuse explicitly with code 3 (`UNSUPPORTED_RECONCILE_MODE`).
   - Existing CLI messages pointing operators at `aether reconcile --to active` are now fully functional.
   - Tested in `tests/test_lifecycle_projections.py::test_reconcile_to_active_surface`.

6. **Safe refusal of unsupported legacy routes**:
   - An active release that cannot authenticate itself (e.g. legacy rc3 lacking `installed_file_fingerprint` or build identity) is refused before mutation under `aether reconcile --to active`.
   - Refusal is reported as `RECONCILE_REFUSED` / unsupported legacy route with zero byte change to record, selector, projections, or unit files.
   - Tested in `tests/test_lifecycle_projections.py::test_legacy_route_refusal_before_mutation`.

---

## 2. Requirement → Check → Observed Result → Evidence Path

| Obligation | Source Ref | Check Executed | Observed Result | Evidence Location |
|---|---|---|---|---|
| Target-compatible active record | AC-1, L1 | `test_target_compatible_active_record_preserves_target_field_shape_and_reader_semantics` | PASS: `tui_sha256` absent from active.json; absence vs null preserved; frozen rc3 `ReleaseRecord.from_json` parses successfully; RED/GREEN proven | `tests/test_lifecycle_projections.py:1217` |
| Pre-mutation target validation | AC-1, L1 | `test_incompatible_or_malformed_target_refuses_with_zero_byte_change` | PASS: Unknown target keys/malformed reader refuse before cutover; hashes of active.json, selector, launcher, desktop, service 100% unchanged | `tests/test_lifecycle_projections.py:1347` |
| Byte-exact compensation | AC-1, L1 | `test_transition_compensation_restores_byte_exact_previous_record_bytes` | PASS: Exact previously captured active-record bytes restored (SHA-256 match); selector symlink paired; no reserialization through failing class | `tests/test_lifecycle_projections.py:1299` |
| Target-owned projections | AC-2, L2 | `test_reconcile_repairs_rc4_wrong_projection`, `tests/test_hermes_gateway_service.py` | PASS: Target determines projection bytes; parent validates allowlisted destinations & digests; brand-agnostic version checking; service restart avoided when read-only suffices | `tests/test_lifecycle_projections.py:1468`, `src/aether_agents/lifecycle.py:3842` |
| Bounded reconcile surface | AC-2, L2 | `test_reconcile_to_active_surface` | PASS: `--dry-run` leaves every byte unchanged; `--yes` repairs active projections; idempotent on second run (`no_change`); `--to installed` exits 3 | `tests/test_lifecycle_projections.py:1406`, `src/aether_agents/cli.py:800` |
| Safe legacy route refusal | AC-2, L2 | `test_legacy_route_refusal_before_mutation` | PASS: rc3 active release refuses before mutation with `RECONCILE_REFUSED`; all 3 witnessed hashes byte-identical before/after | `tests/test_lifecycle_projections.py:1530` |
| Regression / Focused suite | AC-1, AC-2 | `uv run --frozen pytest -q tests/test_lifecycle_projections.py tests/test_tui_projections.py tests/test_hermes_gateway_service.py tests/test_observation_lifecycle.py` | PASS: 150/150 tests passed in 156s | Terminal log |
| Code quality / Formatting | AC-1, AC-2 | `uv run --frozen ruff check src/aether_agents tests scripts` && `uv run --frozen ruff format --check src/aether_agents tests scripts` && `uv run --frozen mypy src/aether_agents` | PASS: Ruff clean (0 errors), Format clean (175 files formatted), Mypy clean (0 issues in 68 source files) | Terminal log |

---

## 3. Direct versus Reused Attribution

- **Direct implementation (this card)**:
  - Target-compatible active record serialization in `ReleaseStore._target_active_payload` and `ReleaseStore._commit_active`.
  - Target manager isolated subprocess runner `_TARGET_RUNNER_SCRIPT` supporting `validate_record`, `prepare_projections`, and `validate_projections`.
  - Parent allowlist and bound validation in `LifecycleManager._prepare_target_projections_subprocess`.
  - Target projection application and target-side post-switch validation in `LifecycleManager.project_release`.
  - Byte-exact active record compensation via `self.store._restoring_prior_bytes` and `_atomic_bytes`.
  - Bounded CLI surface `aether reconcile --to active [--dry-run] [--yes] [--json]` in `src/aether_agents/cli.py`.
  - 6 focused verification tests in `tests/test_lifecycle_projections.py`.
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
- `tests/test_hermes_gateway_service.py`

No additions or modifications to `.github/workflows/policy.yml` are required for this unit.

---

## 5. Residual Risk and Environment Limits

- **WSL Terminal Shortcuts**: Tested in disposable/mock directories in unit tests; end-to-end qualification on real WSL Windows Terminal paths is owned by RC6-QUAL.
- **Candidate Activation**: Actual live runtime cutover and service restart are owned by RC6-CLOSE; this unit performed zero live mutations or systemctl interactions.
- **Confinement**: All tests were confined to `tmp_path` with isolated `HOME`, `XDG_DATA_HOME`, `XDG_STATE_HOME`, `XDG_CONFIG_HOME`, and disposable projection roots. Live installation and operator configuration remained 100% untouched.
