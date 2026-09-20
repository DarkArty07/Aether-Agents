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
| Total extra entries | 0 | 8,881 | Confined to allowlist |
| `node_modules/**` extras | 0 | 8,650 | Allowed extra prefix |
| `ui-tui/node_modules/**` | 0 | 230 | Allowed extra prefix |
| `ui-tui/dist/entry.js` | 0 | 1 | Allowed extra exact |
| Symlinks | 0 | 16 (in `node_modules/.bin/`) | Allowed extra symlinks |
| Disallowed extras | 0 | 0 | **PASS** (0 disallowed) |
| Restorable verdict | N/A | `true` | **PASS** |

*Note on `__pycache__`:* Python import bytecode execution created 621 regular `.pyc`
files in `__pycache__` directories across the live tree. Consistent with canonical
`_tree_sha256` rules (`names[:] = sorted(name for name in names if name != "__pycache__")`),
`__pycache__` directories are excluded from tree comparison. When the clean archive is
swapped into `hermes-source`, no `__pycache__` files or directories remain.

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
5. **Atomic Swap:** Atomically renames `target_source` to `quarantine_path` outside the
   release (sibling of `release_dir`, never inside `hermes-source`, never deleted), then
   renames clean staging to `target_source`. Fsyncs parent directories.
6. **Rollback Safety:**
   - On pre-swap refusal: cleans up staging tree; target `hermes-source` is completely untouched.
   - On swap rename failure: moves quarantine back to `target_source`, cleans up staging;
     leaves exactly one `hermes-source` (original contaminated tree, no ambiguous pair).
   - On post-swap validation failure: removes failed target, moves quarantine back to
     `target_source`; leaves exactly one `hermes-source` (original contaminated tree, no ambiguous pair).
7. **Scope Preservation:** Only `hermes-source` is swapped. `record.json`, `release.json`,
   `release-lock.json`, `profile-bundle.json`, `artifacts/`, `manager/`, and `runtime/`
   are preserved byte-identically.

---

## 3. Automated Verification Evidence

### Test Suite: `tests/test_source_restoration.py`

| Test Node | Purpose | Observed |
| --- | --- | --- |
| `test_classify_hermes_source_expected_hash_equality` | Verifies altered expected file bytes trigger `changed_files` and refuse restoration | **PASS** (0.01s) |
| `test_classify_hermes_source_missing_file_refusal` | Verifies missing expected file triggers `missing_files` and refuses restoration | **PASS** (0.01s) |
| `test_classify_hermes_source_extra_prefix_refusal` | Verifies extras outside closed allowlist trigger `disallowed_extras` and refuse restoration with zero mutation | **PASS** (0.01s) |
| `test_classify_hermes_source_allowlisted_symlink_and_regular_extras` | Verifies regular files and symlinks inside the three allowlisted prefixes are accepted as restorable | **PASS** (0.01s) |
| `test_classify_live_rc3_source_matches_exact_inventory` | Proves AC-1 against actual read-only live rc3 `hermes-source`: 9377 expected, 0 missing, 0 changed, 8881 extras all allowlisted | **PASS** (0.42s) |
| `test_restore_refuse_cross_device` | Verifies cross-device operation (`st_dev` mismatch) refuses with `RestorationError` before any swap | **PASS** (0.01s) |
| `test_restore_rollback_on_injected_pre_swap_refusal` | Verifies pre-swap refusal leaves target tree completely untouched with zero mutation | **PASS** (2.35s) |
| `test_restore_rollback_on_injected_swap_failure` | Verifies swap rename failure rolls back quarantine to `hermes-source` and leaves no ambiguous pair | **PASS** (2.36s) |
| `test_restore_rollback_on_injected_post_swap_failure` | Verifies post-swap validation failure rolls back quarantine to `hermes-source` and leaves no ambiguous pair | **PASS** (2.34s) |
| `test_restore_disposable_contaminated_rc3_release` | Full end-to-end AC-2 proof: contaminated rc3 release fails validation pre-swap, restorer materializes clean archive, hardens, atomically swaps, preserves quarantine, makes `validate_release` succeed, and leaves metadata files byte-identical | **PASS** (38.12s) |

### Fail-First Verification Summary

| Probe Condition | Expected Behavior | Observed Result |
| --- | --- | --- |
| Expected file corrupted (`README.md` modified) | `RestorationError` raised, `is_restorable == False` | `RestorationError: target source has 1 changed expected files` |
| Expected file deleted (`LICENSE` unlinked) | `RestorationError` raised, `is_restorable == False` | `RestorationError: target source missing 1 expected files` |
| Disallowed extra added (`unexpected_root.py`) | `RestorationError` raised, `is_restorable == False` | `RestorationError: target source contains 2 extras outside closed allowlist` |
| Injected cross-device target/quarantine | `RestorationError` raised before any rename | `RestorationError: cross-device operation refused` |
| Pre-swap refusal injected | Staging cleaned up, target unchanged | Target mtime/inodes preserved, 0 staging leftovers |
| Swap rename failure injected | Quarantine rolled back to target source | Original contaminated tree restored at `hermes-source`, 0 quarantine leftovers |
| Post-swap validation failure injected | Quarantine rolled back to target source | Original contaminated tree restored at `hermes-source`, 0 quarantine leftovers |
| Pre-restoration disposable rc3 validation | `validate_release` fails due to contamination | `IntegrityError: release source tree contains a non-regular file` |
| Post-restoration disposable rc3 validation | `validate_release` succeeds with exact record | `ReleaseRecord(version='1.0.0rc3')` returned successfully |

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
   Result: Exact match (0 diff).
   Registered paths:
   - `.aether/objective-contracts/oc_f190ae9e878151e6/v1.md`
   - `.aether/objective-contracts/oc_f190ae9e878151e6/v2.md`
   - `tests/test_source_restoration.py`

4. **Mypy Check:**
   Skipped with canonical reason: No Python source files under `src/` were modified by
   this unit. `src/` is a preserved boundary.

5. **Exclusions Honored:**
   - No live source mutation executed.
   - No process quiesced or stopped.
   - No hop executed.
   - No git push, PR, merge, remote tag, or issue mutation.
   - Live `hermes-source` remained strictly read-only.
