# TASK-M2.1A — Bootstrap the Default-Off Aether MCP Process

> **Status:** ACTIVE FAST-TRACK IMPLEMENTATION HANDOFF
> **Task owner:** Hermes
> **Implementation owner:** One repository-local external coding agent
> **Acceptance owner:** Hermes after independent exact-commit reproduction

```text
PROJECT_ROOT: /home/darkarty/Desktop/agentes/aether/.aether/worktrees/feature-v0.22.0-orca-transition
BRANCH: feature/v0.22.0-orca-transition
HANDOFF_PARENT: 06ff5098542b18162a4f3f836516b1a4a2f7cb20
HANDOFF_COMMIT_SUBJECT: docs: fast-track default-off MCP bootstrap
PYTHON: /home/darkarty/Desktop/agentes/aether/home/.venv-hermes/bin/python3
MCP_SDK: mcp==1.28.1
BUILD_BACKEND: setuptools==83.0.0
REPORT: docs/external-agent/REPORT-M2.1A.md
```

This task is immutable after handoff. M1.1b is deliberately deferred, not the
active task. This slice advances only the provider-independent M2.1 bootstrap and
must not create an Orca adapter or call Orca.

## 1. Objective

Create the smallest real `aether_mcp` Python package and stdio MCP process that:

1. imports only from the new `aether_mcp` namespace;
2. uses the official MCP SDK already used by Hermes (`mcp==1.28.1`);
3. completes a real MCP initialize/list-tools handshake;
4. exposes exact server/protocol metadata and zero tools;
5. opens no network listener;
6. exits cleanly when stdin reaches EOF;
7. performs no provider, storage, profile, credential or runtime effect;
8. remains default-off and unregistered in every Hermes profile/config.

This is M2.1a only. It does not grant D1 and does not implement M2.2–M2.7.

## 2. Governing sources

Read completely before writing:

- `AGENTS.md`
- `docs/external-agent/OPERATING-CONTRACT.md`
- `docs/external-agent/TASK-M2.1A.md`
- `docs/releases/v0.22.0/M0_PROVIDER_SEAM_AMENDMENT.md`
- `docs/releases/v0.22.0/M1_2_INDEPENDENT_REVIEW.md`
- `docs/releases/v0.22.0/ROADMAP.md` sections M2 and 10.7
- `docs/architecture/AETHER_MCP.md`
- `docs/reference/AETHER_MCP_CONTRACT.md`
- `pyproject.toml`
- `Makefile`
- `tests/test_post_olympus_residue_retirement.py`

For compatibility evidence, inspect but do not modify the installed Hermes source
patterns in:

```text
/home/darkarty/.hermes/hermes-agent/agent/transports/hermes_tools_mcp_server.py
/home/darkarty/.hermes/hermes-agent/tests/tui_gateway/test_slash_worker_mcp_discovery.py
```

Do not read Hermes credentials/config/state. Only the named source files are in
scope outside the repository.

## 3. Preflight — stop on mismatch

Before writing, verify:

1. `pwd` equals `PROJECT_ROOT` exactly.
2. Branch equals `BRANCH`.
3. `git status --porcelain` is empty.
4. `git rev-parse HEAD^` equals `HANDOFF_PARENT`.
5. `git log -1 --format=%s` equals `HANDOFF_COMMIT_SUBJECT`.
6. `src/` is absent.
7. The declared Python resolves exactly to the `PYTHON` path.
8. That interpreter reports Python `3.11+`, `mcp 1.28.1`, `setuptools 83.0.0`,
   `pytest 9.1.1` and `ruff 0.16.1`.
9. No dependency installation is required.
10. Read-only process inventory contains no Aether MCP or Orca process. Do not kill
    unknown processes.

Do not reset, stash, switch, fetch, pull, install, amend, rebase or absorb changes
to pass preflight. Return `BLOCKED` without edits on mismatch.

## 4. Exact allowed paths

Modify only:

1. `pyproject.toml`
2. `Makefile`
3. `tests/test_post_olympus_residue_retirement.py`

Create only:

4. `src/aether_mcp/__init__.py`
5. `src/aether_mcp/server.py`
6. `src/aether_mcp/__main__.py`
7. `tests/aether_mcp/test_bootstrap.py`
8. `docs/external-agent/REPORT-M2.1A.md`

Do not create `src/aether_agents`, `src/olympus_v3`, schemas, storage, adapters,
plugins, config, profiles, entry points other than the one explicitly admitted
below, or any other path.

## 5. Strict TDD

Use RED -> GREEN -> REFACTOR. Add the test changes before production/package
files and run the focused RED tests. Record exact failing test names and expected
failure reasons. Import errors because `aether_mcp` does not yet exist are valid
RED only after the test itself imports/collects correctly and the failure is the
expected missing product behavior.

### RED-A — Distribution boundary

Update the retirement contract so it permits exactly one new distribution and
namespace while preserving all retired boundaries. GREEN must prove:

- `[build-system]` is exactly `setuptools==83.0.0` with
  `setuptools.build_meta`;
- project name is `aether-mcp`;
- project version is `0.22.0.dev0` and does not claim a Release;
- `requires-python` is `>=3.11`;
- the only runtime dependency is `mcp==1.28.1`;
- the only console entry point is
  `aether-mcp = aether_mcp.__main__:main`;
- setuptools discovers packages only under `src`;
- `src/aether_mcp` is present;
- `src/aether_agents`, `src/olympus_v3`, old distributions/entry points,
  `aiosqlite`, `cryptography` and retired runtime dependencies remain absent.

Do not weaken unrelated retirement tests. Replace only assertions invalidated by
this explicitly approved M2.1a package.

### RED-B — Import and metadata

Prove:

```text
import aether_mcp

aether_mcp.__version__ == "0.22.0.dev0"
aether_mcp.PROTOCOL_ID == "aether.mcp/v1alpha1"
aether_mcp.SERVER_NAME == "aether-mcp"
```

The package import must not read environment/config/state, create files, spawn a
process, import Orca code or open a socket.

### RED-C — Real MCP handshake

Using `mcp.StdioServerParameters`, `mcp.client.stdio.stdio_client` and
`mcp.ClientSession` against:

```text
<PYTHON> -m aether_mcp
```

with a candidate-first `PYTHONPATH=<PROJECT_ROOT>/src`, prove:

- initialize succeeds under a bounded timeout;
- `serverInfo.name == "aether-mcp"`;
- `serverInfo.version == "1.28.1"` (the pinned SDK-reported server version);
- protocol version is non-empty and equals the version negotiated by this pinned
  SDK/client pair;
- server instructions identify `aether.mcp/v1alpha1`, version `0.22.0.dev0`,
  `default-off`, and `no tools registered`;
- `list_tools()` returns exactly zero tools;
- closing the client session leaves no child process.

Do not mock this handshake.

### RED-D — EOF and stdout integrity

Start the real module as a direct child with pipes, close stdin without sending a
protocol request, and require:

- exit code `0` within a bounded timeout;
- stdout empty (no banner/log/prose corrupts MCP wire);
- stderr empty at normal log level;
- no descendant process survives.

### RED-E — No network/provider effects

While the direct child is alive waiting on stdio:

- inspect its Linux `/proc/<pid>/fd` entries and require no `socket:[...]` file
  descriptor;
- require no new Orca/Aether-MCP descendant other than the one test-owned MCP
  process;
- use test-owned canaries/temporary directories to prove no file is created;
- close stdin and prove complete cleanup.

Do not inspect unrelated process FDs or protected state.

### RED-F — Make target

Add one bounded target:

```text
mcp-smoke
```

It must use the selected `PYTHON`, set candidate-first `PYTHONPATH=src`, invoke
`python -m aether_mcp` with stdin from `/dev/null`, and terminate successfully.
It must not install, register, configure or launch a persistent service.

## 6. Production implementation

### 6.1 Package metadata

Add only the exact metadata from RED-A to `pyproject.toml`. Preserve current pytest
and Ruff configuration. Do not add optional dependencies, build tools, network
transports or cryptography.

### 6.2 Package API

`src/aether_mcp/__init__.py` exposes only static metadata constants required by
RED-B. It has no side effects.

### 6.3 Server

Implement a minimal factory in `src/aether_mcp/server.py` using:

```python
from mcp.server.fastmcp import FastMCP
```

Create `FastMCP` with exact server name, static instructions and error-only normal
logging. Register no tools, resources, prompts, lifespan, auth, HTTP/SSE mount,
state or background task.

`src/aether_mcp/__main__.py` provides `main() -> int`, runs only stdio transport,
returns `0` on normal EOF/KeyboardInterrupt and emits no normal stdout/stderr
content. Errors go only to static, secret-safe stderr and return nonzero. Never
print exception-controlled content.

No network transport option or CLI argument exists in M2.1a.

### 6.4 Default-off boundary

Do not modify any profile/config/template, setup/update script, gateway, plugin,
Hermes home, MCP registration or runtime service. The package can run only when
explicitly invoked by the smoke test/operator.

## 7. Validation

Run and record actual outputs:

```text
python3 -m pytest --collect-only -q tests/aether_mcp/test_bootstrap.py tests/test_post_olympus_residue_retirement.py
python3 -m pytest -q tests/aether_mcp/test_bootstrap.py tests/test_post_olympus_residue_retirement.py
python3 -m pytest -q
python3 -m ruff check src/aether_mcp tests/aether_mcp/test_bootstrap.py tests/test_post_olympus_residue_retirement.py
python3 -m compileall -q src/aether_mcp tests/aether_mcp/test_bootstrap.py
make mcp-smoke
PYTHONPATH=src python3 -m aether_mcp </dev/null
python3 -c "import tomllib; tomllib.load(open('pyproject.toml','rb'))"
git diff --check HANDOFF_PARENT..HEAD
git status --porcelain
```

Also prove:

- real initialize/list-tools handshake passes;
- no socket, process, temp file or cache outside normal ignored Python bytecode
  survives;
- no active config/profile contains `aether_mcp` registration;
- `src` contains only `src/aether_mcp`;
- no `orca` subprocess invocation/import/string is introduced in production
  package files;
- no dependency was installed.

Tests may create ignored `__pycache__` locally but must remove M2.1a-owned caches
before final worktree verification. Do not touch protected `.aether`.

## 8. Report and commit

Create `docs/external-agent/REPORT-M2.1A.md` containing:

- preflight identity;
- RED failures and GREEN results;
- exact package/dependency metadata;
- handshake server info/protocol/tool count;
- EOF/stdout/stderr evidence;
- socket/process/file cleanup evidence;
- focused/full/Ruff/compileall/Make results;
- exact changed-path inventory;
- confirmation that M1.1b, provider adapter, M1.3 and later M2 packages remain
  unstarted.

Create exactly one commit:

```text
feat: bootstrap default-off Aether MCP package
```

The commit may contain only the eight allowed paths. Do not amend.

## 9. Forbidden scope

Do not:

- execute or modify M1.1b;
- invoke Orca, AppImage metadata extraction or `agent-context`;
- implement provider manifest verification, catalog calls or adapter logic;
- register any MCP tool, resource or prompt;
- implement protocol envelopes, project admission, SQLite, trace, learning,
  cryptography, schemas or provider projections from M2.2–M2.7;
- create network transports/listeners;
- create Runs, Tasks, Dispatches, workers, messages, terminals or worktrees;
- access credentials, profile config/state, protected `.aether`, global Orca state,
  network providers, models, other repositories or unrelated user data;
- install dependencies;
- modify setup/update scripts, profiles, config templates, gateway or CI;
- push, merge, rebase, amend, tag, Release, deploy or activate.

## 10. Binary acceptance

Hermes may accept M2.1a only if:

1. ancestry, exact one commit and eight-path allowlist match;
2. RED/GREEN evidence is real and test-first;
3. package metadata and only dependency match exactly;
4. all retired namespaces/entry points remain absent;
5. real MCP handshake returns expected metadata and zero tools;
6. direct EOF exits 0 with empty stdout/stderr;
7. runtime inspection proves no socket/provider/file effect;
8. Make smoke, focused/full tests, Ruff and compileall pass;
9. no dependency/config/profile/runtime mutation occurred;
10. no process/temp/cache survivor remains;
11. worktree is clean;
12. M1.1b, D1, adapter, M1.3 and M2.2–M2.7 remain blocked.

## 11. Return format and stop

Return only:

```text
M2.1A IMPLEMENTER RESULT: PASS | FAIL | BLOCKED
HEAD: <full hash>
COMMIT: <full hash> feat: bootstrap default-off Aether MCP package
PYTHON: <exact executable/version>
DEPENDENCIES: mcp 1.28.1 / setuptools 83.0.0 / no install
FOCUSED COLLECTION: <exact count>
FOCUSED TESTS: <exact result>
FULL TESTS: <exact result>
HANDSHAKE: <server name/version/protocol/tool count>
EOF: <exit/stdout/stderr>
ISOLATION: <socket/process/file survivors>
REPORT: docs/external-agent/REPORT-M2.1A.md
WORKTREE: clean | dirty
BLOCKERS: none | exact blocker
STOPPED: yes — M1.1b, adapter, M1.3 and M2.2+ not started
```

Then stop. Hermes will independently inspect and reproduce the exact committed
candidate before authorizing any later package.
