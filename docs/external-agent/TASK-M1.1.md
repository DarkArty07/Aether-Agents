# TASK-M1.1 — Freeze Orca Source and Executable Identity

> **Status:** ACTIVE
> **Task owner:** Hermes
> **Implementation owner:** One repository-local external coding agent
> **Acceptance owner:** Hermes after independent reproduction

```text
PROJECT_ROOT: /home/darkarty/Desktop/agentes/aether/.aether/worktrees/feature-v0.22.0-orca-transition
BRANCH: feature/v0.22.0-orca-transition
ACCEPTED_BASELINE: 24ccce63cbf58dbc233e934b026dc372d167b00f
HANDOFF_COMMIT_SUBJECT: docs: prepare M1.1 external agent handoff
REPORT: docs/external-agent/REPORT-M1.1.md
EVIDENCE_JSON: docs/releases/v0.22.0/M1_ORCA_QUALIFICATION.json
EVIDENCE_REPORT: docs/releases/v0.22.0/M1_ORCA_QUALIFICATION.md
```

This task file is immutable after handoff. Do not edit it.

## 1. Objective

Implement the deterministic, credential-free M1.1 qualification probe that
freezes the exact installed Orca launcher, AppImage artifact, product version,
build digest and machine-readable command-catalog identity without starting an
Orca runtime or calling a worker/model.

One successful result must be reproducible twice with byte-identical canonical
JSON. Every mismatch or unavailable required identity must fail closed with a
stable structured error; never infer, fabricate or silently normalize a value.

This is provider qualification before an adapter. It does **not** implement
`src/aether_mcp`, an MCP server, an Orca adapter or any later M1/M2 behavior.

## 2. Governing sources to read before writing

- `AGENTS.md`
- `docs/external-agent/OPERATING-CONTRACT.md`
- `docs/releases/v0.22.0/M0_DESIGN_ACCEPTANCE.md`
- `docs/releases/v0.22.0/ROADMAP.md`, especially M1.1 at lines 748–761
- `docs/decisions/ADR-0001-aether-mcp-control-and-trace-plane.md`
- `docs/architecture/AETHER_MCP.md`
- `pyproject.toml`
- `tests/test_post_olympus_residue_retirement.py`

Do not reinterpret historical retirement roadmaps as active implementation
instructions.

## 3. Verified starting facts

Hermes verified these facts on the accepted baseline before writing this task:

### Repository

- The accepted M0 commit is
  `24ccce63cbf58dbc233e934b026dc372d167b00f`.
- `src/aether_mcp`, `src/aether_agents` and `src/olympus_v3` are absent.
- `pyproject.toml` contains pytest and Ruff configuration only; there is no Python
  project distribution or runtime dependency set.
- Python is 3.11.15, pytest is 9.1.1 and Ruff is 0.16.1 in the current environment.
- The inherited retirement suite contains 13 tests and passes.

### Installed launcher and artifact

```text
launcher path: /home/darkarty/.local/bin/orca
launcher type: Bash wrapper
launcher size: 1015 bytes
launcher SHA-256: 89efbb54323f6eb2372aa59f32d0e0d330486ae6764b7dd5896705c638a90208
bound AppImage path: /home/darkarty/.local/opt/orca/orca-linux.AppImage
AppImage size: 203385690 bytes
AppImage SHA-256: 813b11e99f7caa4bf8e4fc47200dd6c465f34a04d61e855adbd8822190592e33
AppImage product version source: orca-ide.desktop / X-AppImage-Version
AppImage product version: 1.4.167
update metadata: owner=stablyai, repo=orca, provider=github, releaseType=release
```

The wrapper declares a static `APPIMAGE` path and runs the unpacked CLI through
`ELECTRON_RUN_AS_NODE=1`. Qualification must prove the launcher remains bound to
the exact artifact; hashing only the 1,015-byte wrapper is insufficient.

### Catalog behavior

- `orca --version` and `orca --help` both exit 0 but emit the same human help text;
  neither is an accepted version source.
- `orca agent-context --json` is the official machine-readable command registry.
- Its own schema notes say it is a pure local read that works without a running
  Orca app.
- Two isolated executions produced byte-identical JSON:

```text
catalog bytes: 153496
catalog SHA-256: 068e1d66737f19835536e4a1573a2f931bffe9821af9c1bdff855f902898944b
schemaVersion: 1
commandCount: 220
actual commands length: 220
```

- Every sampled command object exposes these keys:
  `aliases`, `argumentMode`, `command`, `examples`, `flags`, `notes`, `path`,
  `positionalArgs`, `summary`, `usage`.
- There is no version-named command in the catalog.
- In isolated HOME/XDG roots, `--help`, `--version` and two
  `agent-context --json` calls left zero side-effect files and zero Orca-labelled
  survivor processes.
- The AppImage's own metadata extraction mode can read the version without
  starting the application:

```text
orca-linux.AppImage --appimage-extract orca-ide.desktop
```

It writes only `squashfs-root/orca-ide.desktop` under the chosen temporary working
root. Do not require or install `7z`, `unsquashfs`, an ASAR package or network tool.

These are verified starting facts, not permission to hardcode a PASS. Tests must
prove the probe rejects altered fixtures and changed real identity.

## 4. Preflight — stop on any mismatch

Run these checks before writing:

1. `pwd` equals `PROJECT_ROOT` exactly.
2. `git branch --show-current` equals the declared branch.
3. `git status --porcelain` is empty.
4. `git rev-parse HEAD^` equals `ACCEPTED_BASELINE`.
5. `git log -1 --format=%s` equals `HANDOFF_COMMIT_SUBJECT`.
6. The governing files listed above exist and were read.
7. The launcher and AppImage exist as regular executable files at the verified
   paths. A symlink, path change or digest change is a truthful `BLOCKED`, not a
   reason to update expected values.
8. A read-only process inventory shows no Orca process. Do not kill anything if
   one exists; report `BLOCKED` with PID/executable/argv metadata but no environment.

Do not reset, stash, amend or switch anything to make preflight pass.

## 5. Exact deliverables

Create only:

1. `scripts/aether_mcp/qualify_orca.py`
2. `tests/aether_mcp/provider/test_qualification.py`
3. `docs/releases/v0.22.0/M1_ORCA_QUALIFICATION.json`
4. `docs/releases/v0.22.0/M1_ORCA_QUALIFICATION.md`
5. `docs/external-agent/REPORT-M1.1.md`

No `__init__.py`, package scaffold, schema directory, fixture repository, Makefile
change, dependency or unrelated documentation update is authorized.

### 5.1 Qualification CLI

Implement a Python 3.11 standard-library-only executable script with a documented
CLI accepting explicit values for:

- launcher path;
- AppImage artifact path;
- isolated root;
- expected launcher SHA-256;
- expected artifact SHA-256;
- expected product version;
- expected catalog schema version;
- expected command count.

The probe must:

1. canonicalize paths without following an untrusted path outside the explicit
   files;
2. reject missing, non-regular, non-executable, symlinked or digest-mismatched
   launcher/artifact inputs;
3. validate that the launcher is statically bound to the exact artifact without
   sourcing or executing the wrapper as shell input;
4. reject an isolated root that is missing, symlinked, inside the repository,
   inside the current HOME/XDG roots, or otherwise ambient/global;
5. build an allowlisted child environment rooted entirely under the explicit
   isolated root; do not forward credentials, provider variables, pairing codes,
   `NODE_OPTIONS`, `PYTHONPATH` or the ambient HOME/XDG state;
6. extract `orca-ide.desktop` through the AppImage metadata mode inside the
   isolated root and parse exactly one `X-AppImage-Version` value;
7. invoke only `agent-context --json` through the verified launcher, twice, with a
   bounded timeout and no runtime/start command;
8. parse JSON, require top-level `schemaVersion`, `commandCount`, and `commands`,
   require declared count equals actual list length, require unique command names,
   and validate the documented command-object shape;
9. prove the two raw catalog payloads are byte-identical and record their SHA-256;
10. reject stderr, non-zero exit, timeout, malformed/unstructured response,
    version/schema/count mismatch, unexpected files outside the explicit metadata
    extraction subtree, or a surviving child process;
11. emit exactly one canonical UTF-8 JSON object plus newline to stdout, with
    sorted keys and no timestamp, random ID, temporary path, secret, environment
    dump or free-form success prose;
12. return zero only for a complete PASS and non-zero with a stable structured
    error code for every rejection.

The canonical PASS document must distinguish:

- launcher identity;
- bound AppImage/build identity;
- product version and its exact metadata source;
- catalog identity and schema/count facts;
- isolation/effect facts;
- explicit booleans confirming no runtime, worker, model, network or protected
  state operation was requested.

Do not include private host data beyond the two explicitly accepted executable
paths and their public file metadata.

### 5.2 Deterministic tests — strict TDD

Write tests before production code and record the observed RED command/failure in
the report. Use real temporary files and subprocesses; do not mock the function
under test into returning desired identity.

At minimum cover:

- complete deterministic PASS with two byte-identical outputs;
- absent launcher;
- launcher symlink;
- launcher digest mismatch;
- launcher bound to a different artifact;
- absent/non-executable artifact;
- artifact digest mismatch;
- absent, duplicate or mismatched `X-AppImage-Version`;
- non-zero metadata extraction;
- ambient/repository/symlinked isolated root;
- child environment does not receive forbidden ambient variables;
- malformed JSON and human prose instead of JSON;
- catalog stderr or non-zero exit;
- timeout;
- schema-version mismatch;
- declared/actual command-count mismatch;
- duplicate command names;
- missing required command fields;
- differing catalog bytes between the two calls;
- synthetic secret canary never appears in stdout/stderr/evidence;
- no files outside the isolated extraction/output allowlist;
- no surviving child process after success or timeout cleanup.

A fake executable fixture may emulate AppImage metadata extraction and
`agent-context --json`, but the acceptance evidence must also run the real pinned
launcher/artifact. Fixture success is not real qualification.

### 5.3 Evidence JSON

Run the completed probe twice against the real pinned launcher and AppImage using
a newly created `/tmp` isolated root for each run. Require byte-identical stdout
and store one canonical result at `EVIDENCE_JSON`.

The evidence JSON is generated output, not a hand-edited claim. It must contain no
secrets, timestamp, random path or fabricated version/build field.

### 5.4 Provisional evidence report

`EVIDENCE_REPORT` must state `PASS PROVISIONAL`, name the first implementation
commit by hash and identify its own containing commit by the required subject and
parent rather than an impossible self-hash. It must include exact probe/test
commands and actual results, reproduce the frozen
identity, explain why `--version` is not used, list every created temporary path
and its cleanup result, and state all non-authorizations. Do not mark M1.1 accepted.

The separate external-agent `REPORT` must follow the operating-contract schema.

## 6. Allowed scope

- The five deliverable paths in section 5.
- Read-only inspection of the governing tracked files.
- Read-only file metadata/content inspection of the exact launcher and AppImage.
- Temporary roots under `/tmp/aether-m1-1-*` created for tests/probes and deleted
  before final report.
- Read-only process inventory before/after the probe.
- Local atomic Git commits named in section 8.

## 7. Forbidden scope

Do not:

- edit this task, the operating contract, `AGENTS.md`, ROADMAP, STATUS, ADRs,
  architecture, product docs, pyproject, Makefile, workflows or existing tests;
- create `src/`, an MCP server, adapter, package metadata or future placeholders;
- run `orca open`, `serve`, `status`, orchestration, terminal, worktree, account,
  environment, browser, computer, automation or any command except
  `agent-context --json` and AppImage metadata extraction;
- start/stop/restart/signal Orca, create runtime state, workers, models, terminals,
  Runs, Tasks, Dispatches or worktrees;
- install dependencies or use network/provider/model calls;
- inspect global Orca state, accounts, credentials, `.aether`, live profile config,
  other repositories or unrelated user data;
- begin M1.2;
- push, merge, rebase, amend, tag, Release, deploy or activate.

## 8. Required atomic commits

Create exactly these commits in order:

1. `test: add deterministic Orca qualification contract`
   - qualification script and test file only;
   - all focused and inherited tests green before commit.
2. `docs: record provisional M1.1 qualification evidence`
   - generated evidence JSON, provisional evidence report and external-agent
     report only.
   - both reports name commit 1 by full hash and declare this commit's exact
     subject/parent; the post-commit return message supplies commit 2's hash.

Do not amend either commit. If blocked before a green implementation, do not
fabricate these commits; write a truthful `BLOCKED` report and stop for Hermes.

## 9. Mandatory validation

Run and record exact outputs/counts for:

```text
python3 -m pytest -q tests/aether_mcp/provider/test_qualification.py
python3 -m pytest -q
python3 -m ruff check scripts/aether_mcp/qualify_orca.py tests/aether_mcp/provider/test_qualification.py
python3 -m compileall -q scripts/aether_mcp tests/aether_mcp
python3 scripts/aether_mcp/qualify_orca.py <all explicit pinned arguments>
git diff --check ACCEPTED_BASELINE..HEAD
git status --porcelain
```

Also:

- execute the real probe twice with separate isolated roots and compare stdout
  byte-for-byte;
- verify both temporary roots are removed;
- verify no Orca-labelled process survives;
- verify `git status --porcelain` is empty after the final report commit;
- verify the final commit subjects and changed paths match sections 5 and 8.

Do not run `make clean`, setup/update/gateway targets or package installers.

## 10. Binary acceptance criteria

Hermes may accept M1.1 only if all are true:

1. Preflight matched the exact branch, clean handoff and accepted M0 parent.
2. Tests were demonstrably RED before production implementation and GREEN after.
3. The probe is standard-library-only and fail-closed.
4. The launcher, bound AppImage, version `1.4.167`, both SHA-256 digests, catalog
   schema 1, command count 220 and raw catalog digest are independently proven.
5. Two real runs produce byte-identical canonical evidence.
6. Every required negative case has an executable test.
7. No runtime/start command, worker/model/network/provider call or protected-state
   read occurred.
8. No temporary file or process survives.
9. Focused tests, full suite, Ruff, compileall and diff check pass.
10. Exactly the authorized files and two local commits exist.
11. Both reports remain provisional and M1.2 was not started.
12. The worktree is clean.

## 11. Return format and stop

After the final commit, return only:

```text
M1.1 IMPLEMENTER RESULT: PASS | FAIL | BLOCKED
HEAD: <full hash>
COMMITS: <hash subject; hash subject>
FOCUSED TESTS: <count/result>
FULL TESTS: <count/result>
REAL PROBE: <two-run identity/determinism result>
REPORT: docs/external-agent/REPORT-M1.1.md
EVIDENCE: docs/releases/v0.22.0/M1_ORCA_QUALIFICATION.json
WORKTREE: clean | dirty
BLOCKERS: none | exact blocker
STOPPED: yes — M1.2 not started
```

Then stop. Hermes will inspect the exact commits and independently rerun the gates.
