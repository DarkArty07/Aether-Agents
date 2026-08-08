# TASK-M1.1-CORRECTION-2 — Close Remaining Isolation Gaps

> **Status:** ACTIVE FINAL CORRECTION
> **Task owner:** Hermes
> **Implementation owner:** One repository-local external coding agent
> **Acceptance owner:** Hermes after independent reproduction

```text
PROJECT_ROOT: /home/darkarty/Desktop/agentes/aether/.aether/worktrees/feature-v0.22.0-orca-transition
BRANCH: feature/v0.22.0-orca-transition
CORRECTION_1_HEAD_UNDER_REVIEW: 32b72ee4e8a8dd18d5131b7f38793139a14eaff8
HANDOFF_COMMIT_SUBJECT: docs: require M1.1 qualification correction 2
REPORT: docs/external-agent/REPORT-M1.1-CORRECTION-2.md
EVIDENCE_JSON: docs/releases/v0.22.0/M1_ORCA_QUALIFICATION.json
EVIDENCE_REPORT: docs/releases/v0.22.0/M1_ORCA_QUALIFICATION.md
```

This task is immutable after handoff. Do not edit it. This is the third total M1.1
implementation attempt; do not add an unplanned repair loop.

## 1. Objective

Close only the four functional gaps and evidence-count mismatch proven in
`M1_1_CORRECTION_1_REVIEW.md`, add the explicitly missing executable coverage from
Correction 1, regenerate provisional evidence from the real pinned Orca artifact
and stop for Hermes.

Do not redesign accepted process-group cleanup or the real happy path. Do not begin
M1.2.

## 2. Governing sources

Read completely before writing:

- `AGENTS.md`
- `docs/external-agent/OPERATING-CONTRACT.md`
- `docs/external-agent/TASK-M1.1.md`
- `docs/external-agent/TASK-M1.1-CORRECTION-1.md`
- `docs/external-agent/TASK-M1.1-CORRECTION-2.md`
- `docs/releases/v0.22.0/M1_1_INDEPENDENT_REVIEW.md`
- `docs/releases/v0.22.0/M1_1_CORRECTION_1_REVIEW.md`
- `scripts/aether_mcp/qualify_orca.py`
- `tests/aether_mcp/provider/test_qualification.py`

Correction 1's independent review is authoritative for the remaining defects. The
original tasks remain authoritative for unchanged boundaries.

## 3. Preflight — stop on mismatch

Before writing, verify:

1. `pwd` equals `PROJECT_ROOT` exactly.
2. The branch equals the declared branch.
3. `git status --porcelain` is empty.
4. `git rev-parse HEAD^` equals `CORRECTION_1_HEAD_UNDER_REVIEW`.
5. `git log -1 --format=%s` equals `HANDOFF_COMMIT_SUBJECT`.
6. The direct predecessor chain is:
   - `32b72ee4e8a8dd18d5131b7f38793139a14eaff8`
   - `d17de965fb2bbd679bedb8087750c41945141f9f`
   - `247990cef2a72183506a614158a57ff0de24cfa2`
7. The real launcher/AppImage paths and digests still match the frozen task. Drift
   is `BLOCKED`; do not change expected identity.
8. Read-only process inventory contains no Orca process. Do not kill unknown
   processes.

Do not reset, stash, switch, fetch, pull, amend, rebase or absorb changes to pass
preflight.

## 4. Exact allowed files

Modify only:

1. `scripts/aether_mcp/qualify_orca.py`
2. `tests/aether_mcp/provider/test_qualification.py`
3. `docs/releases/v0.22.0/M1_ORCA_QUALIFICATION.json`
4. `docs/releases/v0.22.0/M1_ORCA_QUALIFICATION.md`

Create only:

5. `docs/external-agent/REPORT-M1.1-CORRECTION-2.md`

An unchanged deterministic evidence JSON may remain byte-identical and therefore
need no Git content change. Do not touch either independent review, any prior
report/task, ROADMAP, STATUS, operating contract or another file.

## 5. RED phase

Before production edits, add focused regressions that reproduce every item below.
Run the exact focused suite and record the real RED count/output in the Correction
2 report. A new test that passes before the fix is not valid RED evidence unless
it solely covers behavior already implemented but previously untested; identify
those coverage-only cases separately.

### R1 — Hidden dynamic APPIMAGE reassignment

Use a launcher containing one valid literal assignment followed by an active
`export APPIMAGE="$DYNAMIC_OTHER_ARTIFACT"`. The current qualifier must incorrectly
accept it before the parser fix. The corrected qualifier must reject it with the
stable launcher-binding code.

Also cover same-line/semicolon assignment, an additive assignment, `unset
APPIMAGE`, and an eval/interpolated mutation as separate parameter cases or tests.
The exact frozen real wrapper must continue to pass.

### R2 — Global TMPDIR escape

Use a fake child that writes a uniquely named sentinel through `$TMPDIR`. Before
the fix, qualification returns PASS and creates the sentinel in global `/tmp`.
After the fix:

- child `TMPDIR` equals `isolated_root/tmp`;
- no global sentinel is created;
- the contained unexpected file is detected;
- fixture cleanup removes the contained test file even when assertions fail.

Never write or remove a path that is not uniquely owned by the test.

### R3 — Inter-call side-effect concealment

Call 1 leaves `home/stage-effect`; call 2 removes it while emitting identical
catalog bytes. Before the fix the final inventory is clean and qualification
passes. After the fix, inventory immediately after call 1 rejects the side effect,
so call 2 cannot conceal it.

### R4 — Missing required directory

A fake child removes `$HOME` and returns a valid deterministic catalog. Before the
fix qualification passes. After the fix the exact inventory rejects the missing
required directory.

## 6. Production corrections

### C1 — Fail-closed APPIMAGE mutation scan

Extend the non-executing wrapper parser so it sees every active APPIMAGE assignment
or mutation, not only lines starting exactly `APPIMAGE=`.

- Accept exactly one full literal assignment matching the qualified artifact.
- Reject declaration-prefixed assignments (`export`, `readonly`, `declare`, etc.),
  interpolation, command substitution, additive assignment, `unset`, `eval`,
  multiple statements or ambiguous mutation syntax.
- Ignore comments without treating commented assignments as active.
- Permit ordinary read-only `$APPIMAGE` references required by the frozen wrapper.
- Never source/eval/run the wrapper for binding.
- Never echo wrapper-controlled text in errors.

Prefer a small explicit fail-closed grammar for the frozen wrapper over an
incomplete general shell parser.

### C2 — Keep TMPDIR inside the isolated tree

Set child `TMPDIR` to `str(isolated_root / "tmp")`, not global `/tmp`. Preserve the
small explicit child environment allowlist. Add a fake-child observation proving
the exact HOME/XDG/TMP paths received.

### C3 — Exact inventory at every child boundary

Make inventory prove equality, not only absence of unknown entries:

```text
required directories:
  home
  config
  data
  cache
  state
  runtime
  tmp
  squashfs-root
required files:
  squashfs-root/orca-ide.desktop
```

At each applicable boundary reject missing entries, extra entries, wrong types,
symlinks and nested content. Run inventory:

1. immediately after successful metadata extraction;
2. immediately after successful catalog call 1;
3. immediately after successful catalog call 2.

The metadata boundary must already contain the exact expected tree because the
environment directories are created before extraction. Do not wait until a later
child can erase evidence.

Do not expose untrusted filenames or content in public errors.

### C4 — Honest evidence counts

Do not hardcode, infer or copy target pass counts. Run pytest against the final
committed candidate and record exactly what its output reports. Focused collection,
focused execution and full execution must agree with the committed test tree.
Durations may vary; collected/pass counts may not.

## 7. Missing executable coverage from Correction 1

Add or correct executable tests for:

1. metadata-child stderr canary through the real CLI boundary, proving empty CLI
   stderr and no canary in structured stdout;
2. a canary embedded in an unexpected filename, proving it is not echoed;
3. a forced unexpected Python exception through the CLI boundary, proving the
   generic static error and no exception text;
4. a genuinely outside-`/tmp` root created under `/var/tmp` (skip only with an
   explicit pytest reason if the directory is unavailable or unwritable);
5. success-path descendant process cleanup with exact test-owned PIDs;
6. a real FIFO created with `os.mkfifo` or an equivalent non-regular entry,
   proving type-aware rejection;
7. observed child HOME/XDG/TMP environment paths, including isolated TMPDIR.

Rename any existing test whose name claims a type/boundary it does not execute.
Use `monkeypatch` and `try/finally` so failures cannot leave environment variables,
processes, FIFOs, `/var/tmp` roots or sentinels.

Do not delete or weaken currently passing regressions.

## 8. Preserved happy path

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

Keep the PASS JSON byte-compatible. If a schema change becomes necessary, stop
`BLOCKED` rather than changing it silently.

## 9. Evidence refresh

After GREEN:

1. Run focused collection and record the exact collected count.
2. Run focused and full suites and record exact pass counts from command output.
3. Run the real probe twice with fresh direct children named
   `/tmp/aether-m1-1-correction-2-*`.
4. Require byte-identical stdout, empty stderr and exact evidence JSON equality.
5. Inventory each root exactly before cleanup.
6. Delete both roots and verify absence.
7. Verify zero test-owned/global sentinel files and zero test-owned processes.
8. Append a dated `Correction 2` section to provisional evidence, preserving prior
   history and identifying the implementation commit by hash and evidence commit
   by subject/parent.
9. Create the separate Correction 2 report with an R1–R4 and missing-coverage
   matrix.

## 10. Required commits

Create exactly two commits after the handoff without amending history:

1. `fix: close Orca qualification isolation gaps`
   - qualifier and focused tests only;
   - focused/full tests, Ruff and compileall green.
2. `docs: refresh corrected M1.1 evidence`
   - provisional evidence files and Correction 2 report only;
   - report names commit 1 by full hash and identifies commit 2 by required
     subject/parent, not self-hash.

If any required RED cannot be reproduced or GREEN cannot be proven, do not create
a fabricated PASS chain. Return `BLOCKED` with exact evidence and stop.

## 11. Forbidden scope

Do not:

- begin M1.2 or map the provider seam matrix;
- create `src/`, MCP server/adapter/package scaffolding or dependencies;
- run any Orca command except `agent-context --json` and AppImage metadata
  extraction;
- start Orca runtime, workers, models, Runs, Tasks, Dispatches, terminals or
  worktrees;
- access network/providers, credentials, protected `.aether`, global Orca state,
  live profiles, other repositories or unrelated user data;
- modify frozen Orca identity;
- push, merge, rebase, amend, tag, Release, deploy or activate.

## 12. Mandatory validation

Run and record:

```text
python3 -m pytest --collect-only -q tests/aether_mcp/provider/test_qualification.py
python3 -m pytest -q tests/aether_mcp/provider/test_qualification.py
python3 -m pytest -q
python3 -m ruff check scripts/aether_mcp/qualify_orca.py tests/aether_mcp/provider/test_qualification.py
python3 -m compileall -q scripts/aether_mcp tests/aether_mcp
python3 scripts/aether_mcp/qualify_orca.py <all explicit pinned arguments>
git diff --check CORRECTION_1_HEAD_UNDER_REVIEW..HEAD
git status --porcelain
```

Also run R1–R4, all original C1–C5 regressions, the seven missing-coverage tests,
the two-run real probe, exact evidence comparison and survivor/sentinel/temp-root
checks.

## 13. Binary acceptance criteria

Hermes may accept M1.1 only if:

1. Git ancestry, scope and exact two new commits match this task.
2. R1–R4 are demonstrably RED before production correction and GREEN afterward.
3. Every active APPIMAGE mutation outside one exact literal assignment rejects.
4. Child TMPDIR is isolated and no global sentinel is created.
5. Exact inventory runs after metadata and each catalog call and rejects missing,
   extra or wrong-type entries.
6. All seven missing coverage cases execute honestly.
7. Collected/focused/full counts in reports equal independent command output.
8. All prior C1–C5 and process cleanup regressions remain green.
9. Real Orca identity and deterministic JSON remain exact.
10. Ruff, compileall, diff check and full suite pass.
11. No test-owned process, global sentinel or temporary root survives.
12. M1.2 remains unstarted and worktree is clean.

If this third total attempt fails an equivalent independent boundary, Hermes stops
automatic patching and revisits qualification design.

## 14. Return format and stop

After the final commit return only:

```text
M1.1 CORRECTION 2 IMPLEMENTER RESULT: PASS | FAIL | BLOCKED
HEAD: <full hash>
COMMITS: <hash subject; hash subject>
FOCUSED COLLECTION: <count>
FOCUSED TESTS: <count/result>
FULL TESTS: <count/result>
R1-R4: <one result per remaining defect>
MISSING COVERAGE: <seven-case result>
REAL PROBE: <two-run identity/determinism result>
REPORT: docs/external-agent/REPORT-M1.1-CORRECTION-2.md
EVIDENCE: docs/releases/v0.22.0/M1_ORCA_QUALIFICATION.json
WORKTREE: clean | dirty
BLOCKERS: none | exact blocker
STOPPED: yes — M1.2 not started
```

Then stop. Hermes will independently inspect and reproduce the exact committed
candidate.
