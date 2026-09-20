# RS-RESTORE — Exact inventory and atomic rc3 source restorer

**Authority.** Objective Contract `oc_f190ae9e878151e6@v2` (SHA-256
`9bd2828f6f13e086db394d3bb26afb289a23cb5f78293738594fb399c8567188`), in-scope
items 1 and 2; AC-1 and AC-2; breakdown unit RS-RESTORE from
`specs/001-aether-v1-productization/tasks-rc4-restore.md`.

**Base.** Commit `3e814325d6108d8d9b61534c8c6c0093a5a68c0e` plus breakdown commit
`9ab00bcbe36e26f3f5a6d9d20be84909b0269582`.

**New tracked non-`specs/` paths:** `tests/test_source_restoration.py`.
Tracked paths `.aether/objective-contracts/oc_f190ae9e878151e6/{v1,v2}.md` and
`tests/test_source_restoration.py` registered in `.github/workflows/policy.yml`.

**Unit compatibility.** `patch` (internal restoration fixture, test suite, and policy
manifest registration; no public interface or schema changed).

---

## 1. Independent Live Inventory Classification (AC-1)

### Execution
The independent inventory was executed via:
```bash
python specs/001-aether-v1-productization/fixtures/restore_exact_hermes_source.py \
  --release-dir "$XDG_DATA_HOME/aether/releases/1.0.0rc3-8987f650c027ad09" \
  --fork-checkout . \
  --inventory-only --json
```

### Observed Results

| Metric | Clean Materialized Archive | Active Live `hermes-source` | Classification Result |
| --- | --- | --- | --- |
| Fork commit | `aed6591a69f453a1867b73628603e7b53ba40ffc` | N/A (untracked worktree) | Exact commit |
| Tree SHA-256 digest | `cc1ebf94ad167979951e7b956ef3a8c448e96fd3389c93cddf60f8f883bb5ce7` | Failed integrity (symlinks/extras) | Matches release lock exactly |
| Expected tracked files | 9,377 | 9,377 | Zero missing, zero changed |
| Missing expected files | 0 | 0 | **PASS** (0 missing) |
| Changed expected files | 0 | 0 | **PASS** (0 changed) |
| Target total entries | 9,377 | 18,261 | Files + symlink directories |
| Total extra entries | 0 | 8,884 | Confined to closed allowlist |
| `node_modules/**` extras | 0 | 8,653 | Allowed extra prefix (8,650 files + 3 symlink dirs) |
| `ui-tui/node_modules/**` | 0 | 230 | Allowed extra prefix |
| `ui-tui/dist/entry.js` | 0 | 1 | Allowed extra exact |
| Symlinks total | 0 | 19 | 16 file symlinks + 3 symlink dirs |
| Disallowed extras | 0 | 0 | **PASS** (0 disallowed) |
| Restorable verdict | N/A | `true` | **PASS** |

*Note on `__pycache__` and Directory Classification:*
1. Python import bytecode execution created regular `.pyc` files in `__pycache__`
   directories across the live tree. Consistent with canonical `_tree_sha256` rules
   (`names[:] = sorted(name for name in names if name != "__pycache__")`), `__pycache__`
   directories are excluded from comparison.
2. Following Round 1 review, `scan_tree_entries` was updated to inspect `dirnames` via `lstat`:
   - The 3 extra symlink directories present in live rc3 (`node_modules/hermes-tui`,
     `node_modules/@hermes/shared`, `node_modules/@hermes/ink`) are now classified and
     accounted for as allowlisted symlinks under `node_modules/`.
   - Regular directory extras outside the clean tree and allowlist (e.g. unexpected empty dirs)
     and symlink directories outside the allowlist are classified into `disallowed_extras`
     and strictly trigger refusal.

---

## 2. Restorer Architecture and Mechanics (AC-2)

### Component
- `specs/001-aether-v1-productization/fixtures/restore_exact_hermes_source.py`

### Mechanism and Invariants
1. **Materialization and Verification:** Materializes `git archive` of exact fork commit
   `aed6591a69f453a1867b73628603e7b53ba40ffc` into sibling `.hermes-source.clean.<uuid>`
   on the same filesystem as target `hermes-source`. Asserts `_tree_sha256(clean) == cc1ebf94…`.
2. **Hardening:** Executes `_harden_private_tree` on the clean staging tree (`0o700` dirs,
   `0o600`/`0o700` files) and verifies digest preservation.
3. **Inventory Gate:** Performs full classification of target `hermes-source` against
   the clean tree. Refuses if any expected file is missing, changed, type-mismatched, or
   if any extra falls outside `node_modules/**`, `ui-tui/node_modules/**`, or `ui-tui/dist/entry.js`.
4. **Filesystem Confinement:** Checks `st_dev` between `target_source`, `release_dir`,
   and `quarantine_path.parent`. Refuses cross-device operations before any rename.
5. **Durable Quarantine Outside Release:**
   - Default quarantine directory naming uses `.quarantine-<release-id>-<timestamp>` located in
     `release_dir.parent` (sibling of the release directory).
   - Dot-prefix naming prevents matching `_RELEASE_ID_RE`, ensuring `ReleaseStore.recover()`
     never removes the quarantine directory, and `ReleaseStore.records()` ignores it.
   - Any explicit quarantine path located in `release_dir.parent` matching `_RELEASE_ID_RE`
     is refused before swap to prevent accidental deletion during store cleanup.
6. **Atomic Swap:** Atomically renames `target_source` to `quarantine_path` outside the
   release (never inside `hermes-source`, never deleted), then renames clean staging to
   `target_source`. Fsyncs parent directories.
7. **Rollback Safety:**
   - On pre-swap refusal: cleans up staging tree; target `hermes-source` is completely untouched.
   - On swap rename failure: moves quarantine back to `target_source`, cleans up staging;
     leaves exactly one `hermes-source` (original contaminated tree, no ambiguous pair).
   - On post-swap validation failure: removes failed target, moves quarantine back to
     `target_source`; leaves exactly one `hermes-source` (original contaminated tree, no ambiguous pair).
8. **Scope Preservation:** Only `hermes-source` is swapped. `record.json`, `release.json`,
   `release-lock.json`, `profile-bundle.json`, `artifacts/`, `manager/`, and `runtime/`
   are preserved byte-identically.

---

## 3. Automated Verification Evidence

### Test Suite: `tests/test_source_restoration.py`

Hermetic test suite using disposable git checkout fixture (`_clean_tagged_checkout`)
decoupled from unreachable Git objects in shallow clones and independent of live operator state.
Zero `pytest.skip` calls.

| Test Node | Purpose | Observed |
| --- | --- | --- |
| `test_classify_hermes_source_expected_hash_equality` | Verifies altered expected file bytes trigger `changed_files` and refuse restoration | **PASS** (0.01s) |
| `test_classify_hermes_source_missing_file_refusal` | Verifies missing expected file triggers `missing_files` and refuses restoration | **PASS** (0.01s) |
| `test_classify_hermes_source_extra_file_prefix_refusal` | Verifies extra files outside closed allowlist trigger `disallowed_extras` and refuse restoration | **PASS** (0.01s) |
| `test_classify_hermes_source_disallowed_symlink_dir_refusal` | Verifies symlink directories outside closed allowlist trigger `disallowed_extras` and refuse restoration | **PASS** (0.01s) |
| `test_classify_hermes_source_disallowed_dir_extra_refusal` | Verifies regular directories outside clean dirs and allowlist trigger `disallowed_extras` and refuse restoration | **PASS** (0.01s) |
| `test_classify_hermes_source_allowlisted_symlink_and_regular_extras` | Verifies regular files, symlink files, and symlink directories inside allowlisted prefixes are accepted | **PASS** (0.01s) |
| `test_restore_refuse_cross_device` | Verifies cross-device operation (`st_dev` mismatch) refuses with `RestorationError` before any swap | **PASS** (0.01s) |
| `test_restore_rollback_on_injected_pre_swap_refusal` | Verifies pre-swap refusal leaves target tree completely untouched with zero mutation | **PASS** (0.02s) |
| `test_restore_rollback_on_injected_swap_failure` | Verifies swap rename failure rolls back quarantine to `hermes-source` and leaves no ambiguous pair | **PASS** (0.02s) |
| `test_restore_rollback_on_injected_post_swap_failure` | Verifies post-swap validation failure rolls back quarantine to `hermes-source` and leaves no ambiguous pair | **PASS** (0.02s) |
| `test_quarantine_durability_against_release_store_recover` | Verifies default dot-prefixed quarantine is untouched by `ReleaseStore.recover()` and `ReleaseStore.records()` | **PASS** (0.01s) |
| `test_restore_disposable_release_validate_and_doctor_ready` | Full end-to-end AC-2 proof: contaminated release fails validation and doctor flags `ACTIVE_RELEASE_REVALIDATION_FAILED`; restorer swaps clean tree, preserves quarantine, makes `validate_release` succeed, clears `ACTIVE_RELEASE_REVALIDATION_FAILED`, achieves `doctor().ready is True`, and leaves metadata byte-identical | **PASS** (6.25s) |

### Fail-First Verification Summary

| Probe Condition | Expected Behavior | Observed Result |
| --- | --- | --- |
| Expected file corrupted (`pyproject.toml` modified) | `RestorationError` raised, `is_restorable == False` | `RestorationError: target source has 1 changed expected files` |
| Expected file deleted (`uv.lock` unlinked) | `RestorationError` raised, `is_restorable == False` | `RestorationError: target source missing 1 expected files` |
| Disallowed extra file (`unexpected_root.py`) | `RestorationError` raised, `is_restorable == False` | `RestorationError: target source contains 2 extras outside closed allowlist` |
| Disallowed symlink directory (`bad_symlink_dir`) | `RestorationError` raised, `is_restorable == False` | `RestorationError: target source contains 1 extras outside closed allowlist` |
| Disallowed regular directory (`unexpected_empty_dir`) | `RestorationError` raised, `is_restorable == False` | `RestorationError: target source contains 1 extras outside closed allowlist` |
| Injected cross-device target/quarantine | `RestorationError` raised before any rename | `RestorationError: cross-device operation refused` |
| Pre-swap refusal injected | Staging cleaned up, target unchanged | Target mtime/inodes preserved, 0 staging leftovers |
| Swap rename failure injected | Quarantine rolled back to target source | Original contaminated tree restored at `hermes-source`, 0 quarantine leftovers |
| Post-swap validation failure injected | Quarantine rolled back to target source | Original contaminated tree restored at `hermes-source`, 0 quarantine leftovers |
| Store recovery against quarantine sibling | Quarantine preserved, not deleted | `incomplete_releases_removed == 0`, quarantine files intact |
| Pre-restoration disposable release validation | `validate_release` fails, doctor flags revalidation error | `IntegrityError: release source tree contains a non-regular file`, `ACTIVE_RELEASE_REVALIDATION_FAILED` in doctor |
| Post-restoration disposable release validation | `validate_release` succeeds, doctor ready | `ReleaseRecord` returned, `ACTIVE_RELEASE_REVALIDATION_FAILED` absent, `doctor.ready is True` |

---

## 4. Static Checks and Policy Compliance

1. **Ruff Linter & Formatter:**
   ```bash
   uv run --frozen ruff check specs/001-aether-v1-productization/fixtures/restore_exact_hermes_source.py tests/test_source_restoration.py
   uv run --frozen ruff format --check specs/001-aether-v1-productization/fixtures/restore_exact_hermes_source.py tests/test_source_restoration.py
   ```
   Result: All checks passed. Both files fully formatted.

2. **Git Diff Check:**
   ```bash
   git diff --check
   ```
   Result: Clean (0 whitespace errors or formatting issues).

3. **Policy Manifest Registration:**
   ```bash
   expected=$(mktemp); actual=$(mktemp)
   sed -n "35,463p" .github/workflows/policy.yml > "$expected"
   sed -i "s/^          //" "$expected"
   sort -o "$expected" "$expected"
   git ls-files | grep -v "^specs/" | sort > "$actual"
   diff -u "$expected" "$actual"
   ```
   Result: Exact match (429/429 tracked non-`specs/` paths match expected manifest).

4. **Mypy Check:**
   Skipped with canonical reason: No Python source files under `src/` were modified by
   this unit. `src/` is a preserved boundary.

5. **Exclusions Honored:**
   - No live source mutation executed.
   - No process quiesced or stopped.
   - No hop executed.
   - No git push, PR, merge, remote tag, or issue mutation.
   - Live `hermes-source` remained strictly read-only.
