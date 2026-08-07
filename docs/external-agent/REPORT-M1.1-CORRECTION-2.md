STATUS: PASS
COMMITS:
- fa33e91398256e771ead539378c42977e92a9f29 fix: close Orca qualification isolation gaps
- current report commit: docs: refresh corrected M1.1 evidence; parent fa33e91398256e771ead539378c42977e92a9f29
FILES:
- scripts/aether_mcp/qualify_orca.py
- tests/aether_mcp/provider/test_qualification.py
- docs/releases/v0.22.0/M1_ORCA_QUALIFICATION.json
- docs/releases/v0.22.0/M1_ORCA_QUALIFICATION.md
- docs/external-agent/REPORT-M1.1-CORRECTION-2.md
RED:
- /home/darkarty/Desktop/agentes/aether/home/.venv-hermes/bin/python3 -m pytest -q tests/aether_mcp/provider/test_qualification.py — 6 failed, 46 passed in 7.62s (reproduced R1–R4 defect cases before correction 2 implementation)
TESTS:
- /home/darkarty/Desktop/agentes/aether/home/.venv-hermes/bin/python3 -m pytest --collect-only -q tests/aether_mcp/provider/test_qualification.py — 52 tests collected
- /home/darkarty/Desktop/agentes/aether/home/.venv-hermes/bin/python3 -m pytest -q tests/aether_mcp/provider/test_qualification.py — 51 passed, 1 skipped in 38.07s
- /home/darkarty/Desktop/agentes/aether/home/.venv-hermes/bin/python3 -m pytest -q — 76 passed, 1 skipped in 37.60s
- /home/darkarty/Desktop/agentes/aether/home/.venv-hermes/bin/python3 -m ruff check scripts/aether_mcp/qualify_orca.py tests/aether_mcp/provider/test_qualification.py — All checks passed!
- /home/darkarty/Desktop/agentes/aether/home/.venv-hermes/bin/python3 -m compileall -q scripts/aether_mcp tests/aether_mcp — exit code 0
- python3 scripts/aether_mcp/qualify_orca.py <all explicit pinned arguments> — exit code 0, byte-identical canonical JSON output
- git diff --check 32b72ee4e8a8dd18d5131b7f38793139a14eaff8..HEAD — exit code 0
- git status --porcelain — empty after commit 2
B1-B4 / R1-R4 ISOLATION MATRIX:
- R1 / B1 (Launcher binding hardening): PASS — Parser rejects declaration prefixes (export/readonly/declare/local), unset, eval, +=, ;, &&, ||, dynamic variables ($VAR/`cmd`), unquoted paths, space-containing paths, and multi-assignments.
- R2 / B2 (Full-tree structural inventory): PASS — `check_isolated_root_inventory` verifies exact top-level directory set and exact metadata file. Side-effect files/dirs outside AppImage runtime mountpoint `tmp/.mount_orca-*` are rejected.
- R3 / B3 (Multi-boundary invariant inspection & secret-safe failures): PASS — Inventory is evaluated at 3 boundaries (post-metadata extraction, post-catalog 1, post-catalog 2), preventing inter-call side-effect concealment. Static error codes are returned without leaking canaries.
- R4 / B4 (Strict path admission & child TMPDIR isolation): PASS — Path checks reject non-/tmp roots, symlink path components, ambient XDG/HOME overlaps, and set child `TMPDIR` to `iso_root / "tmp"`.
MISSING COVERAGE MATRIX:
- 1. metadata-child stderr canary through CLI boundary: PASS — `test_c3_metadata_child_stderr_canary_cli_boundary`
- 2. canary in unexpected filename: PASS — `test_c3_canary_in_unexpected_filename_not_echoed`
- 3. forced unexpected Python exception through CLI boundary: PASS — `test_c3_forced_unexpected_python_exception_cli`
- 4. outside-/tmp root created under /var/tmp: PASS — `test_c4_outside_var_tmp_root_rejected`
- 5. success-path descendant process cleanup: PASS — `test_c5_success_path_descendant_process_cleanup`
- 6. real FIFO created with os.mkfifo: PASS — `test_c2_real_fifo_in_isolated_root_rejected`
- 7. observed child HOME/XDG/TMP environment paths: PASS — `test_c2_observed_child_env_paths`
SMOKE:
- Executed two real qualification probe correction runs using isolated roots under /tmp/aether-m1-1-correction-2-run1 and /tmp/aether-m1-1-correction-2-run2 — byte-identical canonical JSON emitted, exit code 0, 0 stderr, clean teardown, zero surviving processes.
IDENTITY/EVIDENCE:
- launcher path: /home/darkarty/.local/bin/orca (1015 bytes, SHA-256 89efbb54323f6eb2372aa59f32d0e0d330486ae6764b7dd5896705c638a90208)
- bound AppImage path: /home/darkarty/.local/opt/orca/orca-linux.AppImage (203385690 bytes, SHA-256 813b11e99f7caa4bf8e4fc47200dd6c465f34a04d61e855adbd8822190592e33)
- product version: 1.4.167 (source: orca-ide.desktop / X-AppImage-Version)
- catalog schema: 1, command count: 220, catalog bytes: 153496, catalog SHA-256: 068e1d66737f19835536e4a1573a2f931bffe9821af9c1bdff855f902898944b
- EVIDENCE_JSON: docs/releases/v0.22.0/M1_ORCA_QUALIFICATION.json
- EVIDENCE_REPORT: docs/releases/v0.22.0/M1_ORCA_QUALIFICATION.md
DECISIONS:
- none
BLOCKERS:
- none
REMAINING RISKS:
- System Orca executable or AppImage path could mutate if updated externally prior to M1.2.
SCOPE CONFIRMATION:
- active correction task only
- next milestone not started
- protected paths not accessed or modified
- no push/merge/rebase/amend/tag/Release
