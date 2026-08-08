# TASK-M1.1-CORRECTION-1 — Harden Qualification Boundaries

> **Status:** ACTIVE CORRECTION
> **Task owner:** Hermes
> **Implementation owner:** One repository-local external coding agent
> **Acceptance owner:** Hermes after independent reproduction

```text
PROJECT_ROOT: /home/darkarty/Desktop/agentes/aether/.aether/worktrees/feature-v0.22.0-orca-transition
BRANCH: feature/v0.22.0-orca-transition
IMPLEMENTATION_HEAD_UNDER_REVIEW: a683dd681d5924197c3b3add7f534ae83a795cae
HANDOFF_COMMIT_SUBJECT: docs: require M1.1 qualification hardening
REPORT: docs/external-agent/REPORT-M1.1-CORRECTION-1.md
EVIDENCE_JSON: docs/releases/v0.22.0/M1_ORCA_QUALIFICATION.json
EVIDENCE_REPORT: docs/releases/v0.22.0/M1_ORCA_QUALIFICATION.md
```

This correction task is immutable after handoff. Do not edit it.

## 1. Objective

Correct only the five independently reproduced fail-closed defects in the
provisional M1.1 qualifier, add honest executable coverage for the previously
overclaimed cases, regenerate provisional evidence from the real pinned Orca
artifact and stop for Hermes review.

Do not redesign the accepted happy path. Do not begin M1.2.

## 2. Governing sources

Read completely before writing:

- `AGENTS.md`
- `docs/external-agent/OPERATING-CONTRACT.md`
- `docs/external-agent/TASK-M1.1.md`
- `docs/releases/v0.22.0/M1_1_INDEPENDENT_REVIEW.md`
- `docs/releases/v0.22.0/M1_ORCA_QUALIFICATION.md`
- `scripts/aether_mcp/qualify_orca.py`
- `tests/aether_mcp/provider/test_qualification.py`

The independent review is the authority for the correction defects. The original
M1.1 task remains the authority for all unchanged acceptance boundaries.

## 3. Preflight — stop on mismatch

Before writing, verify:

1. `pwd` equals `PROJECT_ROOT` exactly.
2. The branch equals the declared branch.
3. `git status --porcelain` is empty.
4. `git rev-parse HEAD^` equals
   `IMPLEMENTATION_HEAD_UNDER_REVIEW`.
5. `git log -1 --format=%s` equals `HANDOFF_COMMIT_SUBJECT`.
6. Commits `a478e39f858c5658a98f5c9cb6435636b7af03dc` and
   `a683dd681d5924197c3b3add7f534ae83a795cae` are the two direct predecessors in
   the preserved M1.1 implementation chain.
7. The real launcher/AppImage still match the paths and digests frozen in the
   original task. Any drift is `BLOCKED`; do not update expected identity.
8. A read-only process inventory contains no Orca process. Do not kill an unknown
   process.

Do not reset, stash, switch, fetch, pull, amend or absorb changes to pass preflight.

## 4. Exact allowed files

Modify only:

1. `scripts/aether_mcp/qualify_orca.py`
2. `tests/aether_mcp/provider/test_qualification.py`
3. `docs/releases/v0.22.0/M1_ORCA_QUALIFICATION.json`
4. `docs/releases/v0.22.0/M1_ORCA_QUALIFICATION.md`

Create only:

5. `docs/external-agent/REPORT-M1.1-CORRECTION-1.md`

Do not edit the original task, original implementer report, independent review,
ROADMAP, STATUS, operating contract or any other file.

## 5. Required corrections

Use strict RED-GREEN-REFACTOR. Add the focused failing tests first and record the
exact RED command plus expected failures in the correction report.

### C1 — Exact static launcher binding

Replace whole-text substring detection with a non-executing parser that:

- reads wrapper text as data, never sources/evals/runs it for binding;
- recognizes exactly one active literal assignment of the form used by the pinned
  wrapper: `APPIMAGE='/absolute/path'`;
- ignores comments;
- rejects absent, duplicate, dynamic, interpolated, command-substitution,
  non-absolute or malformed assignments;
- compares the assignment's canonical path exactly with the explicit artifact;
- returns a stable generic error without echoing child-controlled wrapper text.

Required regressions include comment-only candidate reference, assignment to a
different artifact, duplicate assignments, dynamic assignment and the exact real
wrapper PASS.

### C2 — Recursive exact side-effect inventory

Replace the top-level name check with a recursive type-aware inventory.

After successful metadata extraction and both catalog calls, the only allowed
file is:

```text
squashfs-root/orca-ide.desktop
```

The only allowed directories are the explicitly created HOME/XDG/TMP directories
plus `squashfs-root`. Every HOME/XDG/TMP directory must remain empty. Reject:

- nested files under any allowlisted directory;
- additional files/directories under `squashfs-root`;
- symlinks, sockets, devices, FIFOs or unexpected entry types anywhere;
- files created by either metadata extraction or either catalog call.

Do not expose untrusted filenames in public errors. Add separate nested-file,
symlink and unexpected-entry regressions.

### C3 — Secret-safe stable failures

No child-controlled or environment-derived text may reach CLI stdout, stderr,
committed evidence or exception messages rendered by the CLI.

- Do not include metadata/catalog stderr or stdout in errors.
- Do not include extracted untrusted version text, command objects, filenames or
  malformed JSON content.
- Do not print `str(exc)` from the generic exception boundary.
- Preserve stable codes and bounded trusted messages; safe numeric exit/timeout
  facts are allowed only when they cannot contain child text.
- Keep stdout as the single canonical structured result channel and keep stderr
  empty.

Add synthetic canaries independently to metadata stderr, catalog stderr, malformed
JSON, malformed command objects, unexpected filenames, observed version and an
unexpected Python exception. Invoke the real CLI boundary and prove no canary
appears in stdout, stderr or evidence.

### C4 — Exact `/tmp` and ambient-root admission

Require the isolated root to be an existing real directory with a basename
starting `aether-m1-1-`, canonically located under `/tmp` and not equal to `/tmp`.
Reject:

- any root outside `/tmp`;
- the repository or a descendant;
- HOME or a descendant;
- equality/containment with ambient `XDG_CONFIG_HOME`, `XDG_DATA_HOME`,
  `XDG_CACHE_HOME`, `XDG_STATE_HOME` or `XDG_RUNTIME_DIR` when defined;
- a symlink at the leaf or any component between `/tmp` and the root;
- broad/global directories.

Do not reject a valid isolated child merely because ambient `TMPDIR` is `/tmp`.
Add one separate executable regression per distinction.

### C5 — Owned process-group lifecycle

Replace `subprocess.run(timeout=...)` and the global name-based `ps` scan with one
bounded subprocess helper that owns each metadata/catalog child session/process
group.

The helper must:

- launch with an isolated process session/group;
- capture stdout/stderr without forwarding them to public output;
- on normal exit, non-zero exit, exception or timeout, deterministically inspect,
  terminate and reap the entire owned group;
- use bounded TERM/KILL escalation where needed;
- fail closed when process-group inspection or cleanup cannot be proven;
- never scan/kill an unrelated global process by name.

Add real subprocess regressions where metadata and catalog launch descendants.
Cover success, non-zero exit and timeout. Assert the exact test-owned PIDs no
longer exist after the qualifier returns/raises and clean every test-owned process
in fixture teardown even on assertion failure.

## 6. Coverage corrections

Split or extend tests so they truly execute, rather than merely name/assert:

- missing, duplicate and mismatched `X-AppImage-Version` separately;
- catalog stderr with exit 0 separately from non-zero exit;
- declared count versus actual list-length mismatch;
- forbidden ambient variables observed by a fake child, not a hardcoded receipt;
- two complete qualifier/CLI outputs compared byte-for-byte;
- every C1–C5 reproducer from the independent review;
- synthetic environment changes through `monkeypatch` or guaranteed teardown.

Do not weaken/delete the original 22 tests. Correct an overbroad original assertion
only when the new test proves the sharper contract.

## 7. Preserved happy-path contract

The corrected real probe must still freeze exactly:

```text
launcher: /home/darkarty/.local/bin/orca
launcher SHA-256: 89efbb54323f6eb2372aa59f32d0e0d330486ae6764b7dd5896705c638a90208
AppImage: /home/darkarty/.local/opt/orca/orca-linux.AppImage
AppImage SHA-256: 813b11e99f7caa4bf8e4fc47200dd6c465f34a04d61e855adbd8822190592e33
product version: 1.4.167
catalog schema: 1
command count: 220
catalog bytes: 153496
catalog SHA-256: 068e1d66737f19835536e4a1573a2f931bffe9821af9c1bdff855f902898944b
```

Keep the canonical PASS JSON schema byte-compatible unless a field currently
makes a false claim. If a schema change is materially necessary, stop `BLOCKED`
for Hermes rather than silently changing evidence shape.

## 8. Evidence refresh

After all tests are green:

1. Run the real probe twice with two fresh roots named
   `/tmp/aether-m1-1-correction-*`.
2. Require byte-identical stdout and empty stderr.
3. Require exact equality with refreshed `EVIDENCE_JSON`.
4. Recursively inventory each root before cleanup and record only the expected
   metadata file.
5. Delete both roots and verify their absence.
6. Verify no process owned by either run survives.
7. Update `EVIDENCE_REPORT` without rewriting its historical provisional nature;
   append a clearly dated `Correction 1` section naming the correction commit by
   hash and its own evidence commit by subject/parent, not self-hash.
8. Create the correction report using the operating-contract schema and include a
   C1–C5 result matrix.

## 9. Required commits

Create exactly two new commits after the handoff, without amending history:

1. `fix: harden Orca qualification boundaries`
   - script and test file only;
   - focused/full tests, Ruff and compileall green.
2. `docs: refresh provisional M1.1 qualification evidence`
   - evidence JSON, evidence Markdown and correction report only;
   - reports name commit 1 by full hash and identify commit 2 by required
     subject/parent; return commit 2's hash after creating it.

If blocked before correction is green, do not fabricate these commits. Write a
truthful correction report only when doing so does not violate the exact file or
commit boundary, then stop for Hermes.

## 10. Forbidden scope

Do not:

- begin M1.2 or inspect/map the full provider seam matrix;
- create `src/`, an MCP server, adapter, dependency, package scaffold or future
  placeholder;
- run any Orca command except `agent-context --json` and AppImage metadata
  extraction;
- start Orca runtime, workers, models, Runs, Tasks, Dispatches, terminals or
  worktrees;
- access network/providers, credentials, protected `.aether`, global Orca state,
  live profiles, other repositories or unrelated user data;
- change frozen Orca identity to make a test pass;
- push, merge, rebase, amend, tag, Release, deploy or activate.

## 11. Mandatory validation

Run and record:

```text
python3 -m pytest -q tests/aether_mcp/provider/test_qualification.py
python3 -m pytest -q
python3 -m ruff check scripts/aether_mcp/qualify_orca.py tests/aether_mcp/provider/test_qualification.py
python3 -m compileall -q scripts/aether_mcp tests/aether_mcp
python3 scripts/aether_mcp/qualify_orca.py <all explicit pinned arguments>
git diff --check IMPLEMENTATION_HEAD_UNDER_REVIEW..HEAD
git status --porcelain
```

Additionally run each C1–C5 reproducer as a named pytest case, run the real probe
twice, compare bytes with the committed evidence and prove zero test-owned
survivors/temporary roots after the complete full suite.

## 12. Binary acceptance criteria

Hermes may accept the correction only if:

1. Git ancestry, scope and exact two new commits match this task.
2. Every C1–C5 independent reproducer is RED before the fix and GREEN after.
3. All overclaimed coverage distinctions in section 6 are executable tests.
4. Child-controlled canaries never reach any public output or evidence path.
5. Every owned process group is cleaned on success, non-zero, exception and
   timeout without touching unrelated processes.
6. Recursive inventory detects every unexpected nested entry/type.
7. Only valid non-ambient `/tmp/aether-m1-1-*` roots are admitted.
8. The exact real Orca identity and deterministic evidence remain unchanged.
9. Focused/full tests, Ruff, compileall and diff check pass.
10. No temporary path or test-owned process survives.
11. Original provisional reports remain historical; M1.2 remains unstarted.
12. Worktree is clean.

## 13. Return format and stop

After the final commit return only:

```text
M1.1 CORRECTION 1 IMPLEMENTER RESULT: PASS | FAIL | BLOCKED
HEAD: <full hash>
COMMITS: <hash subject; hash subject>
FOCUSED TESTS: <count/result>
FULL TESTS: <count/result>
C1-C5: <one result per correction boundary>
REAL PROBE: <two-run identity/determinism result>
REPORT: docs/external-agent/REPORT-M1.1-CORRECTION-1.md
EVIDENCE: docs/releases/v0.22.0/M1_ORCA_QUALIFICATION.json
WORKTREE: clean | dirty
BLOCKERS: none | exact blocker
STOPPED: yes — M1.2 not started
```

Then stop. Hermes will inspect the exact commits and independently rerun all
original and adversarial gates.
