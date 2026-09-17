# RC2-V3-MATERIALIZE — contract materialization and fork-pin reconciliation

**Authority.** Objective Contract `oc_742f9f4797494bf9@v3` (SHA-256
`2d7b4ff21cca41db14cc09623728a858d851542e54c687a2ff03d55d79009cbc`), in-scope items 1–2
and 6 (source half), AC-01 pin half. Direct Morfeo stewardship in an isolated worktree;
not publication, not activation, not independent review.

**Callers / purpose.** Evidence-only record under the A1 evidence directory; consumed by
human/agent review of the rc.2 objective. No runtime API. No data schema beyond Markdown.

**Base.** Aether `e1af59c0d0f2684cc149fd362d6933dadb964c2c` (`VERSION` `1.0.0rc2`). Maintained-fork
remote `origin/aether-main` resolves to `aed6591a69f453a1867b73628603e7b53ba40ffc`
(tree `2258311f9aa52c58fda9bdbd03183ba50ac85df0`).

**Effects.** Local and reversible only inside the stewardship worktree. No push, PR,
merge, tag, release, live activation, issue mutation, or deletion of pre-existing
worktrees/branches/stashes. The owner's dirty primary `main` checkout was not modified.

**User instruction (verbatim excerpt).** "finish Morfeo's convergence work from CURRENT
STATE: identify material unfinished rc2/convergence work versus historical/rejected
residue; execute only the material work that is authorized and safe in this isolated
worktree"

## What changed

| Path | Change |
| --- | --- |
| `.aether/objective-contracts/oc_742f9f4797494bf9/v2.md` | Materialized finalized `@v2` (historical supersession evidence) |
| `.aether/objective-contracts/oc_742f9f4797494bf9/v3.md` | Materialized finalized `@v3` (current authority) |
| `.github/workflows/policy.yml` | Manifest lines for `v2.md` and `v3.md` |
| `.github/workflows/release.yml` | `FORK_COMMIT` `7a4fdcd…` → `aed6591…` with comment reconciliation |
| `CHANGELOG.md` | Rc.2 pin and contract-registration bullets reconciled to `@v3` truth |
| `AGENTS.md` | Current objective pointer `@v1` → `@v3` with fork pin and recovery gate |

## Measured prerequisites

- Remote tags: only `v1.0.0-rc.1` is present; `v1.0.0-rc.2` is absent (publication still open).
- `aether update --local` requires the Aether candidate commit to carry exactly one annotated
  release tag matching `VERSION` (`lifecycle.LifecycleManager.local_candidate` /
  `_release_tag_at`). Therefore the v3 recovery promotion cannot run against `e1af59c0…`
  until that tag exists or the supported surface changes — recorded as a remaining gate,
  not bypassed.
- GitHub API auth via `gh` returns HTTP 401 (`token invalid`); remote issue/PR/release
  mutation and API reads remain blocked. Git `ls-remote` still works for refs.

## Focused verification

- `pytest tests/test_public_artifacts.py tests/test_hermes_patch_reconciliation.py`:
  **32 passed** at tip `38237a5402db0c85b5b83af8ced45b2e7bf9bb96`.
- Pre-integration release-bundle builds from two clean roots at that tip + fork
  `aed6591…` produced **byte-identical** `SHA256SUMS` (schema-4 lock pins
  `hermes.commit=aed6591a69f453a1867b73628603e7b53ba40ffc`,
  `source_mode=maintained_fork`). Artifacts remain local scratch evidence only; they are
  not a published release.

## Non-claims

This record does not accept REGATE run 173, activate a runtime, publish rc.2, close #261,
or mutate #460. Historical evidence under `RC2-VERIFY-PRE` / `RC2-IDENTITY` that pinned
`7a4fdcd…` remains historical; the release tip must use `aed6591…`.
