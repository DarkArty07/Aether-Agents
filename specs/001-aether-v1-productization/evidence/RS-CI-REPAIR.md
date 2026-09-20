# RS-CI-REPAIR — Cross-Device Test Fixture Portability on Python 3.11/3.12

**Authority.** Objective Contract `oc_f190ae9e878151e6@v2` (SHA-256
`9bd2828f6f13e086db394d3bb26afb289a23cb5f78293738594fb399c8567188`); discovered from
required CI on pull request #486.

**Parent candidate.** Commit `89283704e48a2284504dbe53db944411e300b797`
(`merge: integrate reviewed rc3 restoration and contaminated proof`), which integrates
reviewed units RS-RESTORE (`97539c038d0754de79746e44be8a7fbd4b142b92`) and RS-PROOF
(`d693387294558a147533d072116e425f7922071f`).

**Scope and Boundaries.** Test-only CI portability repair in `tests/test_source_restoration.py`.
Production source (`src/**`), restoration fixture (`restore_exact_hermes_source.py`),
`VERSION`, workflow policy, contracts, and live runtime/services are strictly preserved.
This unit evidence is separate and distinguished from terminal live restoration evidence
governed by RS-CLOSE.

**Unit compatibility.** `patch` (test fixture portability correction; no production interface,
schema, or behavior modified).

---

## 1. Problem and CI Reproduction

### Root Cause
In pull request #486 required CI run `35523342100`, the `observation-qualification` workflow
succeeded across the full suite until:
- Job `106111128643` (Python 3.11): failed at `tests/test_source_restoration.py::test_restore_refuse_cross_device`
- Job `106111128650` (Python 3.12): failed at `tests/test_source_restoration.py::test_restore_refuse_cross_device`
- The remaining 1,895 tests, 23 skips, and 587 subtests passed prior to this node.

In `tests/test_source_restoration.py:237–254`, the test monkeypatched `os.stat` to simulate a cross-device
mismatch by returning `res.st_dev + 1` for the quarantine parent. The monkeypatch handler `fake_stat`
evaluated:
```python
if Path(path).resolve() == quarantine.parent.resolve():
```
In Python 3.11 and 3.12, the standard library implementation of `Path.resolve()` invokes `p.stat()` / `os.stat`
to resolve symlinks on each path segment. Because `os.stat` was monkeypatched with `fake_stat`, invoking
`Path.resolve()` inside `fake_stat` triggered recursive re-entry into `fake_stat`, resulting in
`RecursionError: maximum recursion depth exceeded`. In Python 3.13, implementation differences in `pathlib`
did not re-enter `os.stat` in the same sequence, masking the recursion locally.

### Pre-Repair Reproduction
Executing the pre-repair test against candidate `89283704e48a2284504dbe53db944411e300b797` confirmed
the failure under both Python 3.11 and 3.12:
- Python 3.11 (`cpython-3.11.15`):
  `FAILED tests/test_source_restoration.py::test_restore_refuse_cross_device`
  `RecursionError: maximum recursion depth exceeded while calling a Python object`
- Python 3.12 (`cpython-3.12.13`):
  `FAILED tests/test_source_restoration.py::test_restore_refuse_cross_device`
  `RecursionError: maximum recursion depth exceeded`

---

## 2. Correction and Mechanics

### Fixture Repair
The cross-device test fixture in `tests/test_source_restoration.py` was updated to identify
the target quarantine parent without invoking path resolution routines that call `os.stat`:

1. **Precomputed Lexical and Resolved Targets:**
   Before applying the `os.stat` monkeypatch, the target quarantine parent path is resolved and
   precomputed into a set of normalized absolute paths:
   ```python
   quarantine_parent_resolved = quarantine.parent.resolve()
   target_parents = {
       os.path.abspath(os.fspath(quarantine.parent)),
       os.path.abspath(os.fspath(quarantine_parent_resolved)),
   }
   ```
2. **Stat-Free Matching inside `fake_stat`:**
   Inside `fake_stat`, matching is performed via lexical normalization:
   ```python
   if isinstance(path, (str, bytes, os.PathLike)):
       try:
           norm = os.path.abspath(os.fspath(path))
       except (TypeError, ValueError):
           norm = None
       if norm in target_parents:
           return os.stat_result(...)
   ```
   Because `os.path.abspath` operates purely on string/path manipulations without calling `os.stat`,
   no re-entry occurs.
3. **Oracle Preservation:**
   The test retains the exact cross-device refusal assertion (`RestorationError` matching
   `"cross-device operation refused"`), confirms `target.is_dir()` remains intact, and confirms
   `not quarantine.exists()`, proving that pre-swap filesystem validation refused the operation
   prior to any rename.

---

## 3. Verification Evidence

### Test Execution across Interpreters

| Interpreter | Command | Result |
| --- | --- | --- |
| Python 3.11 | `uv run --python <python3.11> --frozen pytest -q tests/test_source_restoration.py` | **12 passed** in 6.58s |
| Python 3.12 | `uv run --python <python3.12> --frozen pytest -q tests/test_source_restoration.py` | **12 passed** in 6.80s |
| Python 3.13 | `uv run --frozen pytest -q tests/test_source_restoration.py` | **12 passed** in 6.71s |

Focused execution of `test_restore_refuse_cross_device`:
- Python 3.11: 1 passed in 0.26s
- Python 3.12: 1 passed in 0.26s
- Python 3.13: 1 passed in 0.26s

### Linter, Formatting, and Tree Cleanliness
- `git diff --check`: clean (exit 0).
- `uv run --frozen ruff check tests/test_source_restoration.py`: clean (`All checks passed!`).
- `uv run --frozen ruff format --check tests/test_source_restoration.py`: clean (`1 file already formatted`).
- Zero `pytest.skip` or `skipif` annotations added; `grep -n "skip" tests/test_source_restoration.py` returned zero occurrences.

### Boundary and Integrity Summary
- `restore_exact_hermes_source.py` unchanged (`git diff` empty).
- Production source `src/**` unchanged (`git diff` empty).
- `VERSION` unchanged (`1.0.0rc4`).
- `.github/workflows/policy.yml` unchanged (`git diff` empty).
- No remote mutations, live services, or store directories modified.
