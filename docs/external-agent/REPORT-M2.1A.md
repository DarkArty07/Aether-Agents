STATUS: IMPLEMENTED — PENDING ORCHESTRATOR EXACT-COMMIT AUDIT
COMMITS:
- 52de70cd354909fed068c28c88eda0b9dbdd7fb1 docs: fast-track default-off MCP bootstrap
- current report commit: feat: bootstrap default-off Aether MCP package; parent 52de70cd354909fed068c28c88eda0b9dbdd7fb1; Hermes must report its actual hash after commit
- implementation provenance: one external Codex coding-agent execution; Hermes performed read-only audit, reproduced the full gate outside the restricted agent sandbox, and took over the scoped commit because the sandbox could not write the linked-worktree Git index
FILES:
- pyproject.toml
- Makefile
- tests/test_post_olympus_residue_retirement.py
- src/aether_mcp/__init__.py
- src/aether_mcp/server.py
- src/aether_mcp/__main__.py
- tests/aether_mcp/test_bootstrap.py
- docs/external-agent/REPORT-M2.1A.md
RED:
- /home/darkarty/Desktop/agentes/aether/home/.venv-hermes/bin/python3 -m pytest --collect-only -q tests/aether_mcp/test_bootstrap.py tests/test_post_olympus_residue_retirement.py — expected collection succeeded with 17 tests
- /home/darkarty/Desktop/agentes/aether/home/.venv-hermes/bin/python3 -m pytest -q tests/aether_mcp/test_bootstrap.py tests/test_post_olympus_residue_retirement.py — expected missing product behavior: 6 failed, 11 passed; failures were missing `aether_mcp`, absent `src`, and absent distribution metadata
TESTS:
- /home/darkarty/Desktop/agentes/aether/home/.venv-hermes/bin/python3 -m pytest --collect-only -q tests/aether_mcp/test_bootstrap.py tests/test_post_olympus_residue_retirement.py — 17 tests collected
- final independent focused run: 17 passed in 2.83s
- external-agent sandbox full suite: 3 failed, 76 passed, 2 skipped in 19.02s; all three failures were M1.1 catalog qualification returning `ERR_CATALOG_NONZERO_EXIT` under the agent's restricted sandbox
- final independent Hermes full suite outside that sandbox: 80 passed, 1 skipped in 25.95s; the three catalog failures did not reproduce
- /home/darkarty/Desktop/agentes/aether/home/.venv-hermes/bin/python3 -m ruff check src/aether_mcp tests/aether_mcp/test_bootstrap.py tests/test_post_olympus_residue_retirement.py — All checks passed
- /home/darkarty/Desktop/agentes/aether/home/.venv-hermes/bin/python3 -m compileall -q src/aether_mcp tests/aether_mcp/test_bootstrap.py — exit 0
- /home/darkarty/Desktop/agentes/aether/home/.venv-hermes/bin/python3 -c "import tomllib; tomllib.load(open('pyproject.toml','rb'))" — exit 0
SMOKE:
- make mcp-smoke PYTHON=/home/darkarty/Desktop/agentes/aether/home/.venv-hermes/bin/python3 — exit 0 with empty MCP stdout/stderr
- PYTHONPATH=src /home/darkarty/Desktop/agentes/aether/home/.venv-hermes/bin/python3 -m aether_mcp </dev/null — exit 0 with empty stdout/stderr
- real MCP client initialize/list-tools — server `aether-mcp`, SDK server version `1.28.1`, negotiated protocol `2025-11-25`, 0 tools
- direct-child runtime inspection — exit 0 on EOF; empty stdout/stderr; no socket FD, child process, test-canary file, temporary directory, or process survivor
IDENTITY/EVIDENCE:
- preflight root: /home/darkarty/Desktop/agentes/aether/.aether/worktrees/feature-v0.22.0-orca-transition
- preflight branch/head/parent: feature/v0.22.0-orca-transition / 52de70cd354909fed068c28c88eda0b9dbdd7fb1 / 06ff5098542b18162a4f3f836516b1a4a2f7cb20
- handoff subject: docs: fast-track default-off MCP bootstrap
- Python: /home/darkarty/Desktop/agentes/aether/home/.venv-hermes/bin/python3 3.11.15
- dependencies already present, no install: mcp 1.28.1; setuptools 83.0.0; pytest 9.1.1; ruff 0.16.1
- package metadata: aether-mcp 0.22.0.dev0; Python >=3.11; only dependency mcp==1.28.1; only entry point aether-mcp = aether_mcp.__main__:main
- tracked home configuration/profile registration scan: absent
- src inventory: only src/aether_mcp; production Orca references: absent
- post-test inventory: no Aether MCP/Orca process, M1.1 test temporary, or M2.1a-owned cache survivor
DESIGN NOTE:
- the public `FastMCP.run_stdio_async()` transport was probed with the socket-free event loop and reproduced a >5 second hang after stdin EOF; the bounded reader therefore delegates protocol handling to FastMCP's low-level server while preserving clean EOF and zero socket FDs
DECISIONS:
- none
BLOCKERS:
- none in the candidate; the external agent's Git-index write restriction is bypassed only by Hermes creating the exact scoped commit after deterministic verification
- the agent-sandbox catalog failures are classified as environmental because the unchanged tests passed in the independent non-sandbox run
REMAINING RISKS:
- exact-commit acceptance remains pending until Hermes creates and audits the containing commit
- no registration, activation, Orca adapter, real task operation, or live-system claim is made by M2.1a
SCOPE CONFIRMATION:
- active task only
- next milestone not started
- M1.1b, provider adapter, M1.3, and M2.2+ not started
- protected paths not accessed or modified
- no push/merge/rebase/amend/tag/Release
