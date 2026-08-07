# M1.1 Orca Qualification Evidence Report

> **Status:** PASS PROVISIONAL
> **Task:** TASK-M1.1 — Freeze Orca Source and Executable Identity
> **Implementation commit:** `a478e39f858c5658a98f5c9cb6435636b7af03dc` (`test: add deterministic Orca qualification contract`)
> **Target evidence commit subject:** `docs: record provisional M1.1 qualification evidence`
> **Target evidence commit parent:** `a478e39f858c5658a98f5c9cb6435636b7af03dc`

## 1. Frozen Executable and Catalog Identity

The deterministic qualification probe has verified and frozen the exact machine identity of the installed Orca launcher, bound AppImage artifact, product version, catalog schema, and command registry:

- **Launcher Path:** `/home/darkarty/.local/bin/orca`
- **Launcher Type:** Bash wrapper
- **Launcher Size:** `1015` bytes
- **Launcher SHA-256:** `89efbb54323f6eb2372aa59f32d0e0d330486ae6764b7dd5896705c638a90208`
- **Bound AppImage Path:** `/home/darkarty/.local/opt/orca/orca-linux.AppImage`
- **AppImage Size:** `203385690` bytes
- **AppImage SHA-256:** `813b11e99f7caa4bf8e4fc47200dd6c465f34a04d61e855adbd8822190592e33`
- **Product Version Source:** `orca-ide.desktop / X-AppImage-Version`
- **Product Version:** `1.4.167`
- **Catalog Command Registry:** `orca agent-context --json`
- **Catalog Schema Version:** `1`
- **Catalog Declared Command Count:** `220`
- **Catalog Actual Command Length:** `220`
- **Catalog Bytes:** `153496`
- **Catalog SHA-256:** `068e1d66737f19835536e4a1573a2f931bffe9821af9c1bdff855f902898944b`

## 2. Version Extraction Rationale

`orca --version` and `orca --help` both exit with code 0 but emit human-formatted CLI help text rather than machine-readable version information. `orca agent-context --json` provides the complete structured command schema without declaring a version command.

Product version `1.4.167` is deterministically extracted via AppImage metadata extraction mode:

```bash
/home/darkarty/.local/opt/orca/orca-linux.AppImage --appimage-extract orca-ide.desktop
```

This mode extracts only `squashfs-root/orca-ide.desktop` into the explicitly isolated working root without executing application code or starting an Orca runtime.

## 3. Verification Commands and Results

### Focused Unit and Deterministic Contract Tests
- **Command:** `python3 -m pytest -q tests/aether_mcp/provider/test_qualification.py`
- **Result:** `22 passed in 22.12s` (100% pass)

### Full Repository Test Suite
- **Command:** `python3 -m pytest -q`
- **Result:** `47 passed in 20.98s` (100% pass)

### Linter Check
- **Command:** `python3 -m ruff check scripts/aether_mcp/qualify_orca.py tests/aether_mcp/provider/test_qualification.py`
- **Result:** `All checks passed!`

### Bytecode Compilation Check
- **Command:** `python3 -m compileall -q scripts/aether_mcp tests/aether_mcp`
- **Result:** Exit 0 (clean compilation)

### Two-Run Real Qualification Probe
- **Command:** `python3 scripts/aether_mcp/qualify_orca.py --isolated-root /tmp/aether-m1-1-qual-run1` and `--isolated-root /tmp/aether-m1-1-qual-run2`
- **Result:** Both runs succeeded with exit code 0 and produced byte-identical canonical JSON evidence (`153496` catalog bytes, SHA-256 `068e1d66737f19835536e4a1573a2f931bffe9821af9c1bdff855f902898944b`).

## 4. Temporary Path Inventory and Teardown

Every isolated working root created during qualification testing and qualification probe execution was checked and cleaned up:

- `/tmp/aether-m1-1-qual-run1`: removed (cleaned)
- `/tmp/aether-m1-1-qual-run2`: removed (cleaned)
- `/tmp/aether-m1-1-test-probe`: removed (cleaned)

Read-only process inventory confirmed zero surviving Orca processes after execution.

## 5. Non-Authorization Confirmation

- **No Orca Runtime Started:** `orca open`, `serve`, `status`, or app runtime were not executed.
- **No Workers / Models / Network:** Zero worker processes, model calls, API calls, or network calls were performed.
- **No Protected State Read/Modified:** Protected `.aether` stores, credentials, and profile configs were untouched.
- **No External Dependencies Installed:** Qualification uses standard library Python 3.11 only.
- **M1.2 Not Started:** Scope remains bounded strictly to M1.1 identity freezing. Acceptance remains provisional until Hermes independent verification.

## 6. Correction 1 — Boundary Hardening (2026-08-07)

- **Correction Task:** `TASK-M1.1-CORRECTION-1.md`
- **Correction Implementation Commit:** `d17de965fb2bbd679bedb8087750c41945141f9f` (`fix: harden Orca qualification boundaries`)
- **Target Evidence Commit Subject:** `docs: refresh provisional M1.1 qualification evidence`
- **Target Evidence Commit Parent:** `d17de965fb2bbd679bedb8087750c41945141f9f`
- **Defects Corrected:**
  - **C1 (Exact launcher binding):** Implemented non-executing parser `parse_static_appimage_binding` requiring single static `APPIMAGE='/abs/path'` assignment ignoring comments and rejecting dynamic/duplicate assignments.
  - **C2 (Recursive inventory):** Implemented `check_isolated_root_inventory` recursively checking every entry under `isolated_root`. Allowed file is strictly `squashfs-root/orca-ide.desktop` and env directories remain empty.
  - **C3 (Secret-safe failures):** Standardized all error messages to static bounded strings without echoing child stderr, stdout, version strings, or `str(exc)`.
  - **C4 (Exact /tmp admission):** Required `isolated_root` to be a non-symlinked directory directly under `/tmp` with basename starting `aether-m1-1-` and rejected ambient XDG/HOME overlaps.
  - **C5 (Owned process group):** Implemented `run_owned_process_group` with `start_new_session=True` and bounded SIGTERM -> SIGKILL process group teardown.
- **Verification Commands and Results:**
  - **Focused qualification suite:** `39 passed in 27.28s` (100% pass)
  - **Full test suite:** `64 passed in 26.96s` (100% pass)
  - **Ruff check:** `All checks passed!`
  - **Compileall:** Exit 0
  - **Two-run real probe:** `/tmp/aether-m1-1-correction-run1` and `/tmp/aether-m1-1-correction-run2` — byte-identical canonical JSON, exit code 0, 0 stderr, exact match with `docs/releases/v0.22.0/M1_ORCA_QUALIFICATION.json`.
