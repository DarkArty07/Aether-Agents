# M1.1 Independent Qualification Review

> **Status:** REJECTED — CORRECTION REQUIRED
> **Reviewed on:** 2026-08-06
> **Acceptance owner:** Hermes
> **Implementation HEAD reviewed:** `a683dd681d5924197c3b3add7f534ae83a795cae`
> **Accepted handoff parent:** `48a83ea51563ca1ac7db34ac431efc71c424e3b7`
> **Correction task:** `../../external-agent/TASK-M1.1-CORRECTION-1.md`

## 1. Decision

M1.1 is not accepted. The implementation preserves the authorized Git/file scope
and correctly qualifies the currently installed Orca artifact on its happy path,
but five independently reproduced fail-closed violations conflict with the frozen
M1.1 contract. M1.2 remains blocked.

The implementer's `PASS PROVISIONAL` report remains preserved as truthful
implementer evidence. It is not rewritten into independent acceptance.

## 2. Commit and scope audit

The implementation chain is exact and linear:

1. `a478e39f858c5658a98f5c9cb6435636b7af03dc` —
   `test: add deterministic Orca qualification contract`
2. `a683dd681d5924197c3b3add7f534ae83a795cae` —
   `docs: record provisional M1.1 qualification evidence`

The commits changed exactly the five M1.1-authorized paths:

- `scripts/aether_mcp/qualify_orca.py`
- `tests/aether_mcp/provider/test_qualification.py`
- `docs/releases/v0.22.0/M1_ORCA_QUALIFICATION.json`
- `docs/releases/v0.22.0/M1_ORCA_QUALIFICATION.md`
- `docs/external-agent/REPORT-M1.1.md`

No M1.2 file, MCP package, dependency, profile, runtime configuration or protected
state change was present. The worktree was clean before independent probing.

## 3. Independently reproduced green evidence

Hermes reran the exact candidate rather than relying on the implementer output:

| Gate | Independent result |
|---|---|
| Focused collection | 22 tests collected |
| Focused qualification suite | 22 passed in 20.65s |
| Full repository suite | 47 passed in 21.69s |
| Ruff | all checks passed |
| compileall | exit 0 |
| Diff check | pass |
| Real qualification run 1 | exit 0; no stderr |
| Real qualification run 2 | exit 0; no stderr |
| Generated output determinism | byte-identical |
| Generated evidence equality | exact byte match with committed JSON |
| Catalog identity | schema 1; 220/220 commands; 153496 bytes; frozen digest |
| Installed product identity | Orca 1.4.167; launcher and AppImage digests match |
| Independent temporary cleanup | pass |
| Orca-labelled processes after happy path | 0 |

The committed evidence JSON is therefore valid for the exact current happy-path
artifact. The rejection concerns insufficient and incorrect fail-closed behavior,
not the observed Orca identity.

## 4. Blocking findings

### B1 — Static launcher binding accepts a comment-only reference

**Affected code:** `scripts/aether_mcp/qualify_orca.py:99-111`

The probe searches the entire wrapper text for the candidate artifact path. A
wrapper whose real `APPIMAGE` assignment points elsewhere is accepted when the
candidate path appears only in a comment.

**Independent result:**

```text
COMMENT_ONLY_BINDING_ACCEPTED=true
```

**Required invariant:** parse exactly one literal static `APPIMAGE` assignment,
reject comments, duplicate/dynamic/interpolated assignments, and compare its
canonical value exactly with the qualified artifact. Never source or execute the
wrapper to establish binding.

### B2 — Nested side-effect files are accepted

**Affected code:** `scripts/aether_mcp/qualify_orca.py:298-303`

The probe checks only immediate child names of the isolated root. Arbitrary files
under allowlisted `home`, `config`, `data`, `cache`, `state`, `runtime` or `tmp`
directories are invisible to the check.

**Independent result:**

```text
NESTED_SIDE_EFFECT_ACCEPTED=true
```

**Required invariant:** recursively validate the exact allowed tree. The only
allowed file after qualification is
`squashfs-root/orca-ide.desktop`; environment directories must remain empty and
all entries must have expected regular-file/directory types.

### B3 — Child-controlled text leaks through structured errors

**Affected code:** `scripts/aether_mcp/qualify_orca.py:176-203`, `219-239`,
`247-250`, `294-303`, and `389-395`

Child stderr, extracted values, malformed objects, filenames and unexpected
exception strings are copied into error payloads. A synthetic secret emitted by a
failing metadata child was reproduced in `QualificationError.message`, which the
CLI prints as JSON.

**Independent result:**

```text
SYNTHETIC_SECRET_LEAKED_IN_ERROR=true
```

**Required invariant:** child-controlled text and environment-derived values never
appear in stdout/stderr/evidence. Emit stable error codes and bounded trusted
messages only. The generic exception path must also fail closed without `str(exc)`.

### B4 — Unauthorized and ambient isolation roots are accepted

**Affected code:** `scripts/aether_mcp/qualify_orca.py:113-144`

The probe rejects several broad directories but does not require an
`/tmp/aether-m1-1-*` root and does not compare against ambient XDG paths.

**Independent results:**

```text
OUTSIDE_TMP_ROOT_ACCEPTED=true
AMBIENT_XDG_ROOT_ACCEPTED=true
```

**Required invariant:** require a real, non-symlinked path under
`/tmp/aether-m1-1-*`; reject symlinks in every path component; reject equality or
containment with ambient HOME and XDG config/data/cache/state/runtime roots; reject
repository containment.

### B5 — Timeout leaves a descendant process alive

**Affected code:** `scripts/aether_mcp/qualify_orca.py:163-180` and `206-239`

`subprocess.run(..., timeout=...)` owns only the direct child. A launcher that
spawns `sleep` and waits is timed out correctly, but the descendant survives.
The later global `ps` scan is not reached on timeout and is neither child-scoped
nor fail-closed.

**Independent results:**

```text
TIMEOUT_ERROR_CODE_CORRECT=true
TIMEOUT_DESCENDANT_SURVIVED=true
```

Hermes killed the test-owned descendant and verified zero survivors afterward.

**Required invariant:** start each child in its own process session/group; on
success, error or timeout, deterministically terminate and reap the entire owned
group. Failure to inspect or clean the owned group must fail closed. Do not use a
global name-based `ps` scan as proof of child cleanup.

## 5. Coverage integrity findings

The green numerator overstates several named cases:

- `test_absent_duplicate_or_mismatched_appimage_version` exercises only mismatch,
  not missing and duplicate metadata.
- `test_child_environment_does_not_receive_forbidden_ambient_variables` asserts a
  result field but does not let the child observe or reject leaked variables.
- `test_no_surviving_child_process` exercises only the current happy path and does
  not create a descendant or test timeout cleanup.
- `test_qualification_pass_deterministic` calls the qualifier once and does not
  compare two complete canonical CLI outputs.
- stderr/non-zero behavior is consolidated so that either error code passes rather
  than proving each boundary separately.
- synthetic environment variables are assigned directly and not restored through
  `monkeypatch`, allowing test-order leakage.

The correction must add executable regressions for these distinctions rather than
rename tests or relax the task.

## 6. Preserved accepted subset

The correction must not redesign or discard these verified parts:

- exact launcher and AppImage paths/digests;
- version extraction from `X-AppImage-Version=1.4.167`;
- `agent-context --json` as the only catalog command;
- schema 1, 220/220 commands and frozen raw catalog digest;
- canonical deterministic evidence shape;
- standard-library-only implementation;
- no runtime, worker, model, network or protected-state effect on the real happy
  path;
- two-commit and five-file M1.1 authority boundary.

## 7. Next authorized action

Only `TASK-M1.1-CORRECTION-1.md` is authorized. It may modify the existing script,
test and provisional evidence files and create one correction report. It may not
rewrite this review, the original implementer report or the original immutable
task. M1.2 remains unauthorized until Hermes independently reproduces every
original gate and every correction reproducer and creates a separate acceptance
marker.
