STATUS: PASS
COMMITS:
- d17de965fb2bbd679bedb8087750c41945141f9f fix: harden Orca qualification boundaries
- current report commit: docs: refresh provisional M1.1 qualification evidence; parent d17de965fb2bbd679bedb8087750c41945141f9f
FILES:
- scripts/aether_mcp/qualify_orca.py
- tests/aether_mcp/provider/test_qualification.py
- docs/releases/v0.22.0/M1_ORCA_QUALIFICATION.json
- docs/releases/v0.22.0/M1_ORCA_QUALIFICATION.md
- docs/external-agent/REPORT-M1.1-CORRECTION-1.md
RED:
- /home/darkarty/Desktop/agentes/aether/home/.venv-hermes/bin/python3 -m pytest -q tests/aether_mcp/provider/test_qualification.py — 13 failed, 26 passed in 23.36s (reproduced C1-C5 fail-closed violations before hardening)
TESTS:
- /home/darkarty/Desktop/agentes/aether/home/.venv-hermes/bin/python3 -m pytest -q tests/aether_mcp/provider/test_qualification.py — 39 passed in 27.28s
- /home/darkarty/Desktop/agentes/aether/home/.venv-hermes/bin/python3 -m pytest -q — 64 passed in 26.96s
- /home/darkarty/Desktop/agentes/aether/home/.venv-hermes/bin/python3 -m ruff check scripts/aether_mcp/qualify_orca.py tests/aether_mcp/provider/test_qualification.py — All checks passed!
- /home/darkarty/Desktop/agentes/aether/home/.venv-hermes/bin/python3 -m compileall -q scripts/aether_mcp tests/aether_mcp — exit code 0
- python3 scripts/aether_mcp/qualify_orca.py <all explicit pinned arguments> — exit code 0, byte-identical canonical JSON output
- git diff --check IMPLEMENTATION_HEAD_UNDER_REVIEW..HEAD — exit code 0
- git status --porcelain — empty after commit 2
C1-C5:
- C1 (Exact launcher binding): PASS — Static non-executing APPIMAGE parser ignores comments, rejects dynamic & duplicate assignments.
- C2 (Recursive inventory): PASS — Recursive inventory allows strictly squashfs-root/orca-ide.desktop file and requires empty env dirs.
- C3 (Secret-safe failures): PASS — Error messages use static bounded strings; child stderr/stdout/version/canaries never leak.
- C4 (Exact /tmp admission): PASS — Validates /tmp/aether-m1-1-* non-symlinked directory directly under /tmp.
- C5 (Owned process group): PASS — Child session/process group teardown with SIGTERM -> SIGKILL escalation; 0 survivors.
SMOKE:
- Executed two real qualification probe correction runs using isolated roots under /tmp/aether-m1-1-correction-run1 and /tmp/aether-m1-1-correction-run2 — byte-identical canonical JSON emitted, exit code 0, 0 stderr, clean teardown.
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
