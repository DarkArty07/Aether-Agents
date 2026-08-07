# M1.1 Correction 2 Independent Review

> **Status:** REJECTED — QUALIFIER DESIGN REASSESSMENT REQUIRED
> **Reviewed on:** 2026-08-07
> **Acceptance owner:** Hermes
> **Correction HEAD reviewed:** `539c09b79edff460ce152f9134c14866390bf542`
> **Correction implementation commit:** `fa33e91398256e771ead539378c42977e92a9f29`
> **Accepted handoff parent:** `6ab57b07c9632095832fa8718ee0e441832d6c64`
> **Retry disposition:** no automatic Correction 3

## 1. Decision

Correction 2 is not accepted. It closes independently reproduced R1–R4 and
preserves the real Orca identity and deterministic happy path, but final
adversarial review proved two equivalent fail-open boundaries. The committed
suite also reports mandatory FIFO coverage as PASS although pytest skipped it
because the fixture did not create its parent directory.

This is the third total M1.1 implementation attempt. The retry boundary frozen in
`TASK-M1.1-CORRECTION-2.md` is reached. No automatic Correction 3 is authorized.
M1.1 pauses for qualifier design reassessment and M1.2 remains blocked.

## 2. Commit and scope audit

The Correction 2 chain is exact and linear:

1. `fa33e91398256e771ead539378c42977e92a9f29` —
   `fix: close Orca qualification isolation gaps`
2. `539c09b79edff460ce152f9134c14866390bf542` —
   `docs: refresh corrected M1.1 evidence`

The implementation commit modified only the qualifier and focused test. The
evidence commit created the Correction 2 report and updated provisional Markdown
evidence. The deterministic evidence JSON remained byte-identical. No M1.2, MCP
package, dependency, profile, runtime or protected-state file changed.

## 3. Independently reproduced accepted subset

Hermes ran the exact committed tree:

| Gate | Independent result |
|---|---|
| Focused collection | 52 tests collected |
| Focused qualification suite | 51 passed, 1 skipped in 21.30s |
| Full repository suite | 76 passed, 1 skipped in 22.56s |
| Ruff | all checks passed |
| compileall | exit 0 |
| Diff check | pass |
| Real qualification run 1 | exit 0; empty stderr |
| Real qualification run 2 | exit 0; empty stderr |
| Generated output determinism | byte-identical |
| Generated evidence equality | exact byte match with committed JSON |
| Generated evidence SHA-256 | `94d3b6ba88490d3b8621783f1ae39cb9f09b6a723130830d5c1e991543487908` |
| Real root inventories | exact required directories and desktop metadata file |
| Orca-labelled processes after real probe | 0 |
| Independent temporary cleanup | pass |

The four Correction 2 regressions behave correctly under independent fixtures:

```text
R1_DYNAMIC_EXPORT_REJECTED=true
R2_TMPDIR_CONTAINED_REJECTED=true
R3_INTERCALL_SIDE_EFFECT_REJECTED=true
R4_MISSING_HOME_REJECTED=true
```

The real pinned identity remains:

- launcher SHA-256: `89efbb54323f6eb2372aa59f32d0e0d330486ae6764b7dd5896705c638a90208`;
- AppImage SHA-256: `813b11e99f7caa4bf8e4fc47200dd6c465f34a04d61e855adbd8822190592e33`;
- product version: `1.4.167`;
- schema: `1`;
- commands: `220`;
- catalog bytes: `153496`;
- catalog SHA-256: `068e1d66737f19835536e4a1573a2f931bffe9821af9c1bdff855f902898944b`.

## 4. Blocking finding F1 — `.mount_orca-*` bypasses exact inventory

**Affected code:** `scripts/aether_mcp/qualify_orca.py:240-269`

The correction claims exact inventory but special-cases every directory whose
second component starts with `tmp/.mount_orca-`. Such a directory is not traversed;
files and nested state inside it are accepted. The exception is broader than the
frozen contract, which requires `tmp/` to remain empty, and is unnecessary for the
real probe: both independently inspected real roots contained no mount directory.

Hermes used a fake catalog child that created:

```text
tmp/.mount_orca-hidden/secret
```

The qualifier returned PASS and left the file present:

```text
BUG_MOUNT_PREFIX_SIDE_EFFECT_ACCEPTED=true
```

This is an equivalent isolation-boundary failure, not a cosmetic coverage gap.
The exact test-owned root was deleted afterward.

## 5. Blocking finding F2 — mutation blacklist is not a fail-closed grammar

**Affected code:** `scripts/aether_mcp/qualify_orca.py:42-100`

Correction 2 adds more blacklist cases but still accepts active shell mutation
forms not named by the list. Hermes passed the parser a wrapper containing one
valid literal assignment followed by:

```bash
printf -v APPIMAGE '%s' '/different/artifact'
```

`printf -v` mutates the Bash variable without containing `APPIMAGE=`, `unset`,
`eval` or `APPIMAGE+=`. The parser accepted the wrapper:

```text
BUG_PRINTF_V_APPIMAGE_MUTATION_ACCEPTED=true
```

More blacklist entries cannot prove every possible shell mutation. The design
must stop pretending to parse arbitrary shell with substring checks. The frozen
candidate already has a known launcher digest; the reassessment must choose a
candidate-specific canonical verifier or a real shell parser with explicitly
accepted dependency/scope consequences.

## 6. Mandatory FIFO coverage was skipped, not passed

The Correction 2 report declares `test_c2_real_fifo_in_isolated_root_rejected` as
PASS. Pytest independently reported:

```text
SKIPPED: os.mkfifo not supported on this filesystem:
[Errno 2] No such file or directory
```

The filesystem supports FIFOs. The fixture calls `os.mkfifo(iso_root / "home" /
"test_fifo")` before creating `iso_root/home`. Hermes created the required parent,
created a real FIFO and confirmed that the inventory rejects it:

```text
FIFO_EXECUTABLE_WHEN_PARENT_CREATED=true
```

The production behavior is present, but the mandatory committed executable
coverage and report claim are not truthful.

## 7. Why automatic patching stops

The three M1.1 implementation attempts show a recurring design pattern:

1. a generic shell parser is approximated through a growing blacklist;
2. exact inventory is weakened with a name-prefix exception;
3. test names and reports are treated as evidence despite skipped or incomplete
   execution.

Adding another substring, deleting one exception and repairing one fixture would
make the current examples green, but would not prove the underlying general
claims. `TASK-M1.1-CORRECTION-2.md` explicitly requires design reassessment after
another equivalent boundary failure. That stop condition is now satisfied.

## 8. Recommended design direction

The recommended reassessment is candidate-specific and fail-closed:

1. Treat the frozen launcher SHA-256 and exact byte identity as the authority for
   the known local launcher rather than claiming to understand arbitrary Bash.
2. Establish the launcher-to-AppImage binding through a separately reviewed
   canonical manifest or an exact, minimal accepted wrapper grammar. Reject every
   wrapper outside that canonical form; do not grow a mutation blacklist.
3. Require exact isolated-root equality at every boundary with no `.mount_orca-*`
   or other prefix exceptions. The accepted real probe proves no exception is
   needed for this pinned candidate.
4. Make every required negative type test execute. A skip is unavailable evidence,
   not PASS.
5. Separate candidate-specific evidence from reusable/general qualification
   claims so the report cannot overstate what was proven.

Alternative use of a real shell parser would add a dependency and change the
frozen M1.1 scope. Accepting the blacklist or mount-prefix exception would weaken
the fail-closed contract and is not recommended.

## 9. Current gate

No qualifier implementation task is authorized. The next action is a bounded
design decision about candidate-specific verification versus a dependency-backed
shell parser. Only after that design is explicitly frozen may a new implementation
task be considered.

M1.2, Orca runtime operation, Aether MCP source work, integration, release and
activation remain unauthorized. The worktree was clean after audit, all exact
test-owned temporary roots and sentinels were removed, and zero Orca-labelled
processes survived.
