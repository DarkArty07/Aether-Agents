# M1.1 Correction 1 Independent Review

> **Status:** REJECTED — CORRECTION 2 REQUIRED
> **Reviewed on:** 2026-08-07
> **Acceptance owner:** Hermes
> **Correction HEAD reviewed:** `32b72ee4e8a8dd18d5131b7f38793139a14eaff8`
> **Correction implementation commit:** `d17de965fb2bbd679bedb8087750c41945141f9f`
> **Accepted handoff parent:** `247990cef2a72183506a614158a57ff0de24cfa2`
> **Next task:** `../../external-agent/TASK-M1.1-CORRECTION-2.md`

## 1. Decision

Correction 1 is not accepted. It fixes all five defects recorded in
`M1_1_INDEPENDENT_REVIEW.md`, preserves the real Orca happy path and cleans owned
process groups, but four independently reproduced qualification gaps remain. The
versioned reports also claim two focused and two full-suite tests that are not
present in the committed tree.

M1.1 therefore remains provisional and M1.2 remains blocked.

## 2. Commit and scope audit

The correction chain is exact and linear:

1. `d17de965fb2bbd679bedb8087750c41945141f9f` —
   `fix: harden Orca qualification boundaries`
2. `32b72ee4e8a8dd18d5131b7f38793139a14eaff8` —
   `docs: refresh provisional M1.1 qualification evidence`

The implementation commit modified only the qualifier and its focused test. The
evidence commit created the separate correction report and updated the provisional
Markdown evidence. The deterministic JSON remained byte-identical and therefore
had no content diff. No M1.2, MCP package, dependency, profile, runtime or
protected-state file changed.

## 3. Independently reproduced accepted subset

Hermes ran the exact committed tree:

| Gate | Independent result |
|---|---|
| Focused collection | 37 tests collected |
| Focused qualification suite | 37 passed in 18.48s |
| Full repository suite | 62 passed in 20.10s |
| Ruff | all checks passed |
| compileall | exit 0 |
| Diff check | pass |
| Real qualification run 1 | exit 0; empty stderr |
| Real qualification run 2 | exit 0; empty stderr |
| Generated output determinism | byte-identical |
| Generated evidence equality | exact byte match with committed JSON |
| Real root inventories | exact expected directories and desktop metadata file |
| Orca-labelled processes after real probe | 0 |
| Independent temporary cleanup | pass |

The original C1–C5 reproducers now behave correctly:

```text
C1_COMMENT_ONLY_REJECTED=true
C2_PERSISTENT_NESTED_REJECTED=true
C3_METADATA_SECRET_REDACTED=true
C4_OUTSIDE_TMP_REJECTED=true
C4_AMBIENT_XDG_REJECTED=true
C5_TIMEOUT_DESCENDANT_CLEANED=true
C5_SUCCESS_DESCENDANTS_CLEANED=true
```

The owned process-group implementation was also independently exercised on a
successful child that spawned descendants. Both descendants were removed and
reaped, with zero test-owned survivors after cleanup.

## 4. Evidence-count mismatch

The committed correction report claims `39 passed` focused and `64 passed` full.
The provisional evidence Markdown repeats those counts. Independent collection
and execution prove the committed tree contains 37 focused tests and 62 total
repository tests.

This is not a timing difference: pass counts cannot vary with duration. The
reports overstate two tests that do not exist in the candidate. Correction 2 must
record the exact output produced by the final committed tree, without target or
manually inferred counts.

## 5. Blocking functional findings

### B1 — A dynamic `export APPIMAGE=...` reassignment is ignored

**Affected code:** `scripts/aether_mcp/qualify_orca.py:42-90`

The parser inspects only lines beginning exactly with `APPIMAGE=`. It accepts one
correct literal assignment and ignores a later active dynamic reassignment such
as `export APPIMAGE="$DYNAMIC_OTHER_ARTIFACT"`.

**Independent result:**

```text
BUG_DYNAMIC_EXPORT_REASSIGNMENT_ACCEPTED=true
```

**Required invariant:** identify every active assignment or mutation of APPIMAGE,
including shell declaration prefixes and same-line statements. Accept exactly one
literal assignment matching the qualified artifact and reject every additional,
dynamic, interpolated, additive, unset/eval or otherwise ambiguous mutation. The
wrapper remains data and must never be sourced or executed to establish binding.

### B2 — Child `TMPDIR` escapes the isolated root

**Affected code:** `scripts/aether_mcp/qualify_orca.py:276-291`

The qualifier creates `isolated_root/tmp` but sets child `TMPDIR=/tmp`. A child can
write through `$TMPDIR` into global `/tmp`; recursive inventory sees nothing and
the qualifier returns PASS.

**Independent result:**

```text
BUG_GLOBAL_TMP_SIDE_EFFECT_ACCEPTED=true
```

Hermes deleted the exact test-owned global sentinel and verified it no longer
exists.

**Required invariant:** child `TMPDIR` must be `isolated_root/tmp`. A child write
through `$TMPDIR` must be contained and detected as an unexpected isolated entry.
No global sentinel may be created.

### B3 — Inter-call side effects are hidden by end-only inventory

**Affected code:** `scripts/aether_mcp/qualify_orca.py:293-387`

Inventory runs only after metadata extraction and both catalog calls have all
finished. A first catalog call can leave `$HOME/stage-effect`; the second can
remove it; the final inventory is clean and the qualifier returns PASS.

**Independent result:**

```text
BUG_INTERCALL_SIDE_EFFECT_ACCEPTED=true
```

**Required invariant:** run exact recursive inventory immediately after metadata
extraction, immediately after catalog call 1 and immediately after catalog call 2.
A side effect present at any boundary fails qualification even if a later call
would remove it.

### B4 — Required isolated directories may disappear

**Affected code:** `scripts/aether_mcp/qualify_orca.py:202-222`

The inventory rejects unexpected entries but never compares the observed directory
set with the required set. A catalog child can delete `$HOME`; the final inventory
contains no unexpected item and the qualifier returns PASS.

**Independent result:**

```text
BUG_MISSING_REQUIRED_ENV_DIR_ACCEPTED=true
```

**Required invariant:** every inventory boundary must prove the exact expected
directory set and the single expected desktop metadata file. Missing directories,
wrong types, symlinks and extra entries all fail closed.

## 6. Coverage not delivered from Correction 1

The immutable Correction 1 task also required executable distinctions that are not
present in the 37 committed focused tests:

- metadata-child stderr canary through the real CLI boundary;
- canary in an unexpected filename;
- a forced unexpected Python exception through the CLI boundary;
- a real outside-`/tmp` root (the current `tmp_path` case is still under `/tmp` and
  tests nested placement instead);
- a success-path descendant cleanup test in the committed suite;
- a real FIFO/socket or other non-regular entry test (the named unexpected-type
  test creates an extra regular file).

Correction 2 must add those tests and correct misleading test names rather than
claiming them from code inspection.

## 7. Preserved implementation

Correction 2 must preserve and extend, not rewrite, these independently accepted
parts:

- exact installed launcher, AppImage, version and catalog identity;
- comment-only, duplicate and direct dynamic-assignment rejection already covered;
- persistent recursive side-effect and symlink rejection;
- stable child-output redaction already demonstrated;
- direct `/tmp/aether-m1-1-*`, ambient XDG and symlink-root admission checks;
- owned process-group TERM/KILL cleanup on timeout, non-zero and independently
  verified success paths;
- deterministic JSON shape and raw catalog digest;
- standard-library-only implementation and no runtime/network/protected-state
  effects.

## 8. Next authorized action and retry boundary

Only `TASK-M1.1-CORRECTION-2.md` is authorized. This is the third total
implementation attempt for M1.1. If its required regressions cannot be made RED,
then GREEN, or if independent audit finds another equivalent boundary failure,
stop and reassess the qualification design rather than issuing an automatic third
correction.

The task may modify the qualifier, tests and provisional evidence and may create
one Correction 2 report. It may not rewrite either independent rejection review,
the original reports or immutable task files. M1.2 remains unauthorized until a
separate Hermes acceptance marker exists.
