# TASK-M1.1B — Replace Heuristic Qualification with a Canonical Candidate Verifier

> **Status:** DEFERRED BY PRODUCT OWNER — DO NOT EXECUTE
> **Task owner:** Hermes
> **Implementation owner:** One repository-local external coding agent
> **Acceptance owner:** Hermes after independent exact-commit reproduction
> **Superseding active task:** `docs/external-agent/TASK-M2.1A.md`

```text
PROJECT_ROOT: /home/darkarty/Desktop/agentes/aether/.aether/worktrees/feature-v0.22.0-orca-transition
BRANCH: feature/v0.22.0-orca-transition
HANDOFF_PARENT: d3dcd014341b97a35c35751bc73a7da8439ca741
HANDOFF_COMMIT_SUBJECT: docs: authorize candidate-specific Orca qualifier
CANONICAL_MANIFEST: docs/releases/v0.22.0/ORCA_PROVIDER_MANIFEST.json
CANONICAL_MANIFEST_SHA256: 186e7409a9d942319a802d2a6ac1b4cec95f0ab2c48c97907ec7729a3faa8cfe
REPORT: docs/external-agent/REPORT-M1.1B.md
EVIDENCE_JSON: docs/releases/v0.22.0/M1_ORCA_QUALIFICATION.json
EVIDENCE_REPORT: docs/releases/v0.22.0/M1_ORCA_QUALIFICATION.md
```

The product owner deferred this handoff before implementation. Its historical
contract is preserved below, but no agent is authorized to execute it. Do not
edit the canonical manifest.
This is a qualifier redesign, not Correction 3 and not another Bash blacklist.

## 1. Objective

Replace the generic Bash mutation parser and generic `.mount_orca-*` inventory
exception with a candidate-specific verifier that:

1. trusts only the committed canonical manifest and exact file bytes;
2. never tries to prove arbitrary Bash semantics;
3. allows only a bounded, positively identified disconnected FUSE cleanup residue;
4. requires that residue to disappear before final exact inventory;
5. makes the FIFO regression execute honestly;
6. reproduces the exact accepted Orca identity/catalog twice;
7. stops before M1.3 or any provider lifecycle operation.

## 2. Governing sources

Read completely before writing:

- `AGENTS.md`
- `docs/external-agent/OPERATING-CONTRACT.md`
- `docs/external-agent/TASK-M1.1B.md`
- `docs/releases/v0.22.0/M0_PROVIDER_SEAM_AMENDMENT.md`
- `docs/releases/v0.22.0/M1_1A_IDENTITY_CATALOG_ACCEPTANCE.md`
- `docs/releases/v0.22.0/M1_1_CORRECTION_2_REVIEW.md`
- `docs/releases/v0.22.0/M1_2_INDEPENDENT_REVIEW.md`
- `docs/releases/v0.22.0/ORCA_PROVIDER_MANIFEST.json`
- `scripts/aether_mcp/qualify_orca.py`
- `tests/aether_mcp/provider/test_qualification.py`

This task supersedes only the rejected heuristic launcher parser and broad mount
exception. Preserve all other fail-closed boundaries unless this task explicitly
replaces them.

## 3. Preflight — stop on mismatch

Before writing, verify:

1. `pwd` equals `PROJECT_ROOT` exactly.
2. Branch equals `BRANCH`.
3. `git status --porcelain` is empty.
4. `git rev-parse HEAD^` equals `HANDOFF_PARENT`.
5. `git log -1 --format=%s` equals `HANDOFF_COMMIT_SUBJECT`.
6. Canonical manifest SHA-256 equals `CANONICAL_MANIFEST_SHA256`.
7. Manifest launcher/AppImage paths, sizes and hashes match the real installed files.
8. Manifest catalog identity equals schema `1`, count `220`, bytes `153496`, SHA-256
   `068e1d66737f19835536e4a1573a2f931bffe9821af9c1bdff855f902898944b`.
9. Read-only process inventory contains no Orca process. Do not kill unknown
   processes.

Do not reset, stash, switch, fetch, pull, amend, rebase or absorb changes to pass
preflight. Return `BLOCKED` without edits on any mismatch.

## 4. Exact allowed paths

Modify only:

1. `scripts/aether_mcp/qualify_orca.py`
2. `tests/aether_mcp/provider/test_qualification.py`
3. `docs/releases/v0.22.0/M1_ORCA_QUALIFICATION.json`
4. `docs/releases/v0.22.0/M1_ORCA_QUALIFICATION.md`

Create only:

5. `docs/external-agent/REPORT-M1.1B.md`

Read but never modify:

- `docs/releases/v0.22.0/ORCA_PROVIDER_MANIFEST.json`
- this task and every governing/acceptance document.

Do not touch ROADMAP, STATUS, AGENTS, architecture, contracts, dependencies or any
other file.

## 5. Strict TDD

Follow RED -> GREEN -> REFACTOR. Add focused behavioral tests first and run them
against the unchanged qualifier. Record exact RED test names and expected failures
in the report. A syntax/import error is not valid RED.

### RED-A — Canonical manifest is the authority

Prove that the current CLI permits caller-supplied launcher/artifact/hash/version
values and that the replacement must not. GREEN requires:

- production CLI accepts only `--isolated-root`;
- manifest path and expected manifest digest are repository constants;
- no CLI option can replace launcher, artifact, hashes, version, catalog or timeout;
- manifest SHA-256 mismatch fails before any child process;
- missing, extra, malformed or wrongly typed manifest fields fail closed;
- a one-byte launcher/AppImage change from the manifest fails before metadata or
  catalog execution.

The internal Python API may accept a test-only explicit manifest path and expected
manifest digest so fake candidates remain testable. Production `main()` must always
use the canonical constants.

### RED-B — Bash syntax is no longer a qualification language

Remove `parse_static_appimage_binding` and every production heuristic that scans
Bash assignments/mutations. The exact launcher hash plus the manifest's accepted
static binding review is the authority.

Replace obsolete parser-syntax tests with exact-byte tests:

- canonical launcher bytes pass;
- any altered byte fails unless a separate test manifest explicitly admits that
  exact fake fixture;
- result evidence states the binding was accepted by manifest review and pins the
  launcher plus expected AppImage paths/hashes.

A test manifest is only a fixture; it must never change production manifest
selection.

### RED-C — Positive transient FUSE identification

Replace the broad `startswith(".mount_orca-")` exemption. At each post-child
boundary inspect `isolated_root/tmp` directly.

The only transient entry eligible for bounded waiting must satisfy all conditions:

1. direct child of `isolated_root/tmp`;
2. basename fully matches manifest regex
   `^\.mount_orca-[A-Za-z0-9]+$`;
3. `lstat` says real directory and not symlink;
4. attempting `os.scandir` fails specifically with `errno.ENOTCONN`;
5. it disappears within manifest `cleanup_timeout_ms` under the manifest poll
   interval.

A readable normal directory, even empty and correctly named, rejects immediately.
A hidden file/subtree, symlink, FIFO, another errno, wrong name or nested artifact
rejects. An eligible disconnected endpoint that does not disappear by the deadline
fails with a stable timeout code. After waiting, the ordinary exact inventory has
**zero exceptions**.

Use deterministic dependency injection/monkeypatch only where kernel ENOTCONN is
not safely constructible. The final real probe must exercise the actual AppImage
cleanup behavior.

### RED-D — FIFO executes, never falsely skips

Create `isolated_root/home` before `os.mkfifo`. On this required Linux environment,
`mkfifo` failure is a test failure, not `pytest.skip`. Prove the real FIFO exists,
then qualification rejects it as a non-regular entry. Cleanup must run in
`finally`.

### RED-E — Preserved isolation and cleanup class

Retain and run regressions for:

- isolated HOME/XDG/TMPDIR allowlist;
- root must be a direct non-symlink child of `/tmp` with the new
  `aether-m1-1b-` prefix;
- metadata and catalog stderr/canary redaction;
- malformed/non-deterministic catalog rejection;
- exact required directories/file and inter-call inventories;
- nested files, missing directories, symlinks and non-regular entries;
- timeout/nonzero/success descendant process-group cleanup;
- no test-owned processes, roots or sentinels surviving.

Delete or rewrite tests whose only contract is rejected Bash parsing. Do not delete
valid isolation, determinism, redaction, process or inventory coverage.

## 6. Production design

### 6.1 Manifest loading

Implement a strict loader for schema `1`:

- verify canonical manifest bytes against the hardcoded expected digest before
  reading values;
- reject unknown/missing keys and wrong scalar/list/object types at every level;
- require absolute paths and exact declared policy/candidate identifiers;
- verify binding-review launcher hash/path agrees with launcher/AppImage sections;
- use no ambient config, environment override or user profile;
- expose only static error codes/messages, never manifest-controlled values.

### 6.2 Exact candidate identity

For launcher and AppImage:

- reject missing, symlink, non-regular or non-executable paths;
- compare exact size and streaming SHA-256 before child execution;
- recheck exact size/hash before returning PASS;
- never parse, source, eval or echo launcher contents.

The AppImage metadata version and catalog remain independently verified against the
manifest.

### 6.3 Child operations and environment

Execute exactly the two operation shapes admitted by the manifest:

```text
<AppImage> --appimage-extract orca-ide.desktop      exactly once
<launcher> agent-context --json                    exactly twice
```

Use argv arrays, exact process-group ownership and the small isolated environment.
Production CLI timeout comes from the manifest. No shell execution.

### 6.4 Inventory and transient cleanup

Maintain exact inventory after metadata extraction and after each catalog call.
Before each post-catalog inventory, run the positive transient-FUSE cleanup check
from RED-C. Do not hide or remove unexpected content. The qualifier may wait for
a verified disconnected endpoint to self-remove; it must not `rm`, unmount or kill
an unrelated path/process to manufacture PASS.

### 6.5 Deterministic evidence schema

Preserve existing evidence fields and add deterministic manifest authority:

```text
manifest_identity:
  candidate_id
  qualification_policy
  manifest_path
  manifest_sha256
binding_review:
  method
  launcher_sha256
  expected_appimage_path
bounded_cleanup:
  timeout_ms
  poll_interval_ms
  transient_fuse_condition
  final_inventory_exceptions: 0
  verified: true
```

Do not emit measured milliseconds, temporary root names, PIDs, timestamps or other
run-variable values. Two fresh real probes must remain byte-identical.

## 7. Real accepted identity

Final evidence must preserve exactly:

```text
manifest SHA-256: 186e7409a9d942319a802d2a6ac1b4cec95f0ab2c48c97907ec7729a3faa8cfe
launcher: /home/darkarty/.local/bin/orca
launcher size: 1015
launcher SHA-256: 89efbb54323f6eb2372aa59f32d0e0d330486ae6764b7dd5896705c638a90208
AppImage: /home/darkarty/.local/opt/orca/orca-linux.AppImage
AppImage size: 203385690
AppImage SHA-256: 813b11e99f7caa4bf8e4fc47200dd6c465f34a04d61e855adbd8822190592e33
product version: 1.4.167
catalog schema: 1
command count: 220
catalog bytes: 153496
catalog SHA-256: 068e1d66737f19835536e4a1573a2f931bffe9821af9c1bdff855f902898944b
```

## 8. Evidence and validation

After GREEN:

1. Run focused collection and focused tests; record exact counts.
2. Run full suite, Ruff and compileall.
3. Run production CLI twice with fresh direct roots named
   `/tmp/aether-m1-1b-real-*`.
4. Require both stdout payloads byte-identical, stderr empty and JSON equal to the
   updated evidence JSON.
5. Require final exact inventory before deleting each owned root.
6. Delete both owned roots and prove absence.
7. Prove zero test-owned process/sentinel/root survivors.
8. Update the evidence report with an `M1.1b` section that supersedes only the
   rejected parser/mount claims and records actual test counts.
9. Create `REPORT-M1.1B.md` with RED/GREEN, manifest, FUSE, FIFO, identity, cleanup,
   scope and commit evidence.
10. Run:

```text
python3 -m pytest --collect-only -q tests/aether_mcp/provider/test_qualification.py
python3 -m pytest -q tests/aether_mcp/provider/test_qualification.py
python3 -m pytest -q
python3 -m ruff check scripts/aether_mcp/qualify_orca.py tests/aether_mcp/provider/test_qualification.py
python3 -m compileall -q scripts/aether_mcp tests/aether_mcp
python3 scripts/aether_mcp/qualify_orca.py --isolated-root /tmp/aether-m1-1b-real-<unique>
python3 -m json.tool docs/releases/v0.22.0/M1_ORCA_QUALIFICATION.json
python3 -m json.tool docs/releases/v0.22.0/ORCA_PROVIDER_MANIFEST.json
git diff --check HANDOFF_PARENT..HEAD
git status --porcelain
```

## 9. Commit contract

Create exactly one atomic commit after the handoff:

```text
fix: pin Orca qualification candidate
```

It may contain only the five allowed implementation/evidence paths. Do not amend.
If RED cannot be reproduced, the real probe differs, cleanup cannot be proven or a
required test skips, return `BLOCKED` without a PASS commit.

## 10. Forbidden scope

Do not:

- modify the canonical manifest or this task;
- add another Bash parser rule or generic mount-prefix exception;
- execute any Orca operation except the exact metadata extraction and two
  `agent-context --json` calls;
- run/create/cancel/close Runs, Tasks, Dispatches, workers, messages, terminals or
  worktrees;
- start Orca runtime, worker/model/provider/network activity;
- access credentials, profiles, protected `.aether`, global Orca state, other
  repositories or unrelated user data;
- implement schema fixtures, compositions, adapter, MCP package, M1.3 or M2;
- install dependencies;
- push, merge, rebase, amend, tag, Release, deploy or activate.

## 11. Binary acceptance

Hermes may accept M1.1b only if:

1. ancestry, exact one commit and five-path allowlist match;
2. canonical manifest remains byte-identical at the expected digest;
3. production CLI has no identity/catalog/timeout override;
4. no Bash semantics parser remains;
5. byte drift fails before child execution;
6. only positively identified ENOTCONN residue receives bounded wait;
7. normal `.mount_orca-*` directories/subtrees fail and final inventory has no
   exceptions;
8. FIFO test executes and passes without skip;
9. all preserved isolation/process/redaction/determinism tests pass;
10. two real probes are byte-identical and match exact accepted identity/evidence;
11. focused/full counts are honest and every required gate passes;
12. no process, sentinel or temporary root survives;
13. worktree is clean and M1.3/M2 remain unstarted.

## 12. Return format and stop

Return only:

```text
M1.1B IMPLEMENTER RESULT: PASS | FAIL | BLOCKED
HEAD: <full hash>
COMMIT: <full hash> fix: pin Orca qualification candidate
MANIFEST: 186e7409a9d942319a802d2a6ac1b4cec95f0ab2c48c97907ec7729a3faa8cfe
FOCUSED COLLECTION: <exact count>
FOCUSED TESTS: <exact result>
FULL TESTS: <exact result>
RED/GREEN: <manifest / parser removal / FUSE / FIFO / preserved isolation>
REAL PROBE: <two-run identity and determinism result>
CLEANUP: <roots / processes / sentinels>
REPORT: docs/external-agent/REPORT-M1.1B.md
EVIDENCE: docs/releases/v0.22.0/M1_ORCA_QUALIFICATION.json
WORKTREE: clean | dirty
BLOCKERS: none | exact blocker
STOPPED: yes — M1.3 and M2 not started
```

Then stop. Hermes will audit the exact commit and rerun the real probe before any
M1.3 authorization.
