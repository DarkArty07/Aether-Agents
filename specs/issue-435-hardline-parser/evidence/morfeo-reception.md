# Morfeo reception — oc_13551b9a7a1eaf42@v1 (#435 hardline parser source phase)

Reception performed by Morfeo against the finalized contract (SHA-256
`1fefa317a11745af8968862ccd7bdc0e484de4268398ea3d2fa62d63f13a7e5f`) and issue #435.
Labels: **directly verified by Morfeo** (own execution), **reused pipeline evidence**
(independent workers' recorded results, not re-executed here), **unverified**.

Delivered identities bound before acceptance:

| Item | Value |
| --- | --- |
| Fork base | `938bc34fbc797402ccc61d352192e122a344d052` (tree `ae106dfbf45e6615b261674b7cb0dc9252ce14f1`) |
| Fork candidate | `f459cfa0ad27705e2b27ce91c5658648372f307c` (tree `cac4313200eb7a3359cb435622da17060494af8a`) |
| Fork PR | `DarkArty07/aether-hermes#19`, OPEN, unmerged, base `aether-main` |
| Aether integration | `a083f71520a4975412d0a2da96d21e469a6eba3e` (merge of `36fe18a1` + `1b055cb5`) |
| HLP-435 patch | `patches/hermes/HLP-435-hardline-quoted-grep.patch`, 8,666 bytes / 193 lines |

## Acceptance criteria

| Criterion | Artifact / location | Check and producer | Result / limit |
| --- | --- | --- | --- |
| AC1 false-positive correction | fork `tools/approval.py:576-595`, `:2199-2272`; fixtures literal in `tests/tools/test_hardline_blocklist.py` | **Directly verified by Morfeo**: fixture byte strings extracted from the candidate test module's AST (no diff/Markdown escaping), then classified at base and candidate with disposable `HOME`/`HERMES_HOME`/`XDG_*`/`TMPDIR`. No shell string executed. | **Supported.** Base: shapes A/B = 138 and 95 bytes, `shlex` balanced, limits not exceeded, raw grep parse `malformed=False`, normalized parse `malformed=True`, `detect_hardline_command` → `(True, _MALFORMED_EXEC_DESCRIPTION)`, `check_all_command_guards` blocks. Candidate: both → `(False, None)`, guard `approved=True`. Exactly the reported defect and its removal. |
| AC2 protection preservation | same source; `tests/tools/` guard modules | **Directly verified by Morfeo** at candidate (and base) with the same synthetic-only probe. | **Supported.** 24/24 protected destructive positives still hardline (root-delete ordinary/quoted/`$HOME`/`${HOME}`, `r\m`, `r''m`, `${IFS}`, `&&`, `;`, `$( )`, `{ }`, `sudo`, `mkfs`, `dd`→raw, `>`-redirect, `shutdown`, `reboot`, `systemctl`, `init 0`, `telinit 6`, `kill -9 -1`, fork bomb, executable-quoted `bash -c "shutdown -h now"`, `--no-preserve-root`). 10/10 genuinely malformed grep shapes still fail closed with `_MALFORMED_EXEC_DESCRIPTION`. Inert single-quoted PCRE / composite / prose stay non-hardline. Command substitution inside a grep operand and a real separator after grep still hardline — grep masking hides no executable construct. Identical matrix at base. |
| AC3 review and base | fork branch `fix/435-hardline-quoted-grep` | **Directly verified by Morfeo** for base traceability and one failure-attribution claim; **reused pipeline evidence** for the independent reviews and the full battery. | **Supported.** `f459cfa0^` = `938bc34f` exactly (traceable, no base change). Full `tests/tools/test_hardline_blocklist.py` at candidate: **199 passed** (own run). Independent reviews consumed: HF-435 approved; AE-435 approved after Return 1/2 + 2/2. The single battery failure `test_real_binaries_execute_leading_dash_program_payload[sort-args2-{bulk}-False]` reproduced **identically at base and candidate** (same `FileNotFoundError` on the `executed` marker) → baseline-shared, not introduced. Reused, not re-run here: the 4-module `run_tests.sh` totals (base 393/1/5, candidate 409/1/5), `compileall`, `ruff check`. Fork Actions **NOT RUN** (repository Actions disabled) — not green. |
| AC4 portable provenance | `patches/hermes/HLP-435-hardline-quoted-grep.patch`, `specs/issue-435-hardline-parser/evidence/HLP-435.md` | **Directly verified by Morfeo** in a disposable `--no-hardlinks` worktree at the exact base. | **Supported.** Patch SHA-256 `1836729e2b76ecc390e4467d17fb65ba67a5239ebb34492402b7629a7ac3a563`; `git apply --check` exit 0; `apply --index` → `git write-tree` = `cac4313200eb7a3359cb435622da17060494af8a` (byte-for-byte the reviewed candidate tree); reverse `--index` → `ae106dfbf45e6615b261674b7cb0dc9252ce14f1` (exact base tree). Rollback proven. Integration is a true two-parent merge (`36fe18a1` + `1b055cb5`), reviewed AE commit reachable, no squash/amend/rebase; branch delta over the authoring base is exactly the 3 objective files. |
| AC5 noninterference | repos, runtime lock, #494 board | **Directly verified by Morfeo**. | **Supported, with one concurrent fact.** Fork `aether-main` still `938bc34f` (PR #19 open, unmerged). Installed runtime pin unchanged: `5b2b6ba543680c6fe8a62de4b467d1107be3abf4`, `source_mode=maintained_fork`. Issue #435 OPEN. All four #494/RC16 worktrees and branches intact. Aether `main` *did* advance to `d9e3964`, but that is RC16's own authorized merge (PR #524 from `…t_21f26600-execute-oc_c770cea3db51d97e-v2-rc16-494`) and its delta is entirely RC16/#494-owned; the HLP-435 patch is **absent from `main`**. #435 changed no default branch. |

## Authorized omissions

- No Aether evidence PR: opening it would have published a knowingly red required check
  (`policy.yml` manifest drift). Left as an honest open gate, per the contract's explicit
  permission. **Authorized by the contract**, not by Morfeo convenience.
- `scripts/validate_hermes_patch_reconciliation.py --check --fork-checkout` is **NOT
  APPLICABLE** to HLP-435 in this phase (candidate ledger inputs deliberately not created
  during the RC16 collision) — explicitly not a PASS.
- Fork Actions **NOT RUN**; no live gateway/provider/model canary (not authorized in a
  source-only phase).

## Disposition

**Source phase accepted.** All five material criteria are supported; no unresolved
material mismatch. `release_impact=patch`, `release_action=defer`, `release_channel=none`
— consistent with the provisional conclusions; a merge is not a release.

**Issue #435 stays OPEN — this is not a bug closure.** Remaining gates, in order:

1. Reconcile HLP-435 into `HERMES_LOCAL_PATCHES.md`, the reconciliation aggregate and
   entries, and the `policy.yml` artifact manifest **onto the new `main`** (now that RC16
   merged its own ledger/manifest surfaces), then open the Aether evidence PR.
2. Merge fork PR #19 into `aether-main` when the RC16 collision is cleared.
3. Separately authorized managed adoption of the merged fork revision into the installed
   runtime, then live qualification of the two originally rejected inspections.

## Limits of this reception

- The 4-module fork battery totals, `compileall` and `ruff check` are **reused pipeline
  evidence**, not an independent Morfeo rerun; the decisive classifier matrix, the full
  hardline module, the patch reconstruction and the failure attribution are own runs.
- Independent security review of the parser boundary is HF-435's recorded verdict;
  Morfeo verified its outcomes, not its reasoning line by line.
- `ruff format --check` deviations exist identically at base and candidate and are not an
  enforced fork gate; recorded as an observed limit, not waived.
- No installed-behavior claim is made anywhere in this reception.
