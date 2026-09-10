# BGD-V2-VERIFY evidence

Status: Implementer self-review evidence for the v2 candidate-verification unit. This
record is not independent review, integrated terminal acceptance, a release decision,
proof of Pages deployment, or proof of a public installation.

## Unit and source basis

- Objective Contract: `oc_844dfc12880ee967@v2`, SHA-256
  `72a435bf75c73d26785f3ce00d90f151e8023a236b4f69ba7d159bb3fee90e4e`.
- Candidate revision verified before writing this record:
  `3d1fe9a1659d7e132011446b5feb8e4b1dcc8485` (`docs(plan): decompose contract v2 closeout`).
- Required continuation base: `6ddedab1dae701af51382822740050ccb0c29dc9`; it is an
  ancestor of the candidate. The integrated website merge is
  `860176e1db8c6c24d937f38d67b9a9c1f190f9b4`, consuming the independently approved
  recovered website head `ad892a7539ecc619bf00b9d4be0a1b8a2602f1a7`.
- Current read-only `origin/main` after `git fetch --no-prune origin main`:
  `89c372fa6af09c6cbd5ce9a18dc7dd78ed70dfc4`.
- Project binding: `.aether/project.toml` project
  `12027989-a08f-41cd-a82c-54ff1bfb6b03`, repository `DarkArty07/Aether-Agents`.
- No `.aether/skills/` directory exists in the candidate. Project-knowledge status was
  unavailable, so current source and test inspection were used; the applicable
  implementation-evidence, project-knowledge and work-memory procedures governed this
  run. A prior work-memory note about rebuilding Astro output after HEAD changes was
  revalidated by the current website source and applied below.

This unit changed only this evidence path. It did not modify the Objective Contracts,
scanner, public-artifact tests, website/source/runtime files, workflows or documentation
implementation.

## Executed verification

All commands below were run against the candidate unless a different root/revision is
named. Generated website output and captures are ignored and are not durable evidence.

| Command or action | Observed result | Interpretation |
| --- | --- | --- |
| `git status --short --branch`, branch/base/revision checks | Clean at start; candidate was `3d1fe9a1659d7e132011446b5feb8e4b1dcc8485`; required base was an ancestor | Starting state and prerequisite lineage matched the v2 receipt. |
| `git fetch --no-prune origin main` | PASS; `origin/main` resolved to `89c372fa6af09c6cbd5ce9a18dc7dd78ed70dfc4` | Differential verification used the current fetched default-branch ref, not prior prose. |
| `npm ci` from `website/` | PASS; 320 packages added/audited, 0 vulnerabilities | Existing locked website dependencies were sufficient; no package or lockfile change was made. |
| `npm run build` | PASS; Astro built 22 pages | Normal website build completed from the candidate. |
| `npm run check` | PASS; 33 files, 0 errors, 0 warnings, 0 hints | Astro/type diagnostics were clean. |
| `npm test` | PASS; 14 passed, 0 failed/skipped/cancelled | Website content, manifest, link, source-integrity and preservation tests passed. |
| `npm run test:e2e` | PASS; 57 passed, 1 intentionally skipped across desktop/mobile Chromium | Browser behavior, docs UX, responsive/no-JavaScript behavior and accessibility checks passed; the sole skip is the desktop-only guard for the mobile-navigation case, which ran in the mobile project. |
| `AETHER_PAGES=1 npm run build` | PASS; 22 pages | Project-site base-path build completed. |
| `node scripts/verify-pages-build.mjs` | PASS; Pages base-path verification passed for 22 HTML pages | Local Pages artifact links/resources resolved; this is not deployment evidence. |
| Restored normal `npm run build` | PASS; 22 pages | Normal non-Pages output was restored before capture/inspection. |
| First `node scripts/capture.mjs` attempt | Exit 1: local preview was not listening (`ERR_CONNECTION_REFUSED`) | Environment-only precondition failure; no behavior change or second speculative retry was made. |
| `npm run preview`, HTTP readiness probe, then one rerun of `node scripts/capture.mjs` | Preview became ready with HTTP 200; capture PASS | The bounded environment retry completed the required capture generation. |
| Capture layout output at 360, 390, 768, 1024, 1440 and 1920 pixels, plus docs index/start/walkthrough/reference at 390 and 1440 | Every reported document width equaled the viewport; every `overflow` list was empty | Representative desktop/mobile geometry had no detected page overflow. Capture files remain ignored under `website/test-results/visual/`. |
| Representative DOM inspection at mobile `/docs/start-here/` and desktop `/docs/` plus `/docs/reference/capabilities/` | Main landmarks, navigation, headings, language metadata, grouped navigation, search/context and local scroll-region observations were present; widths equaled viewports | Text/geometry inspection corroborated the browser checks. Pixel-level visual inspection is not claimed: the available image-analysis backend rejected the three local capture requests with `opencode rejected the request`. |
| `uv run --frozen python scripts/check_documentation.py` | PASS: `documentation validation passed` | Root documentation/registry coherence remained green. |
| `uv run --frozen pytest -q tests/test_beginner_documentation.py tests/test_documentation.py` | PASS: 20 passed | Focused root documentation checks passed. |
| Isolated temporary `HOME`, with `HERMES_HOME` unset: 27 parser/help commands (`aether --version`, top-level `--help`, all documented top-level command help paths, and all 11 `knowledge` subcommand help paths) | All 27 exited 0 | Beginner-facing parser/help surfaces were exercised without provider or credential setup. |
| Same isolated environment: `aether doctor --json` | Exit 4; `LIFECYCLE_INTEGRITY_FAILED` / `ACTIVE_RELEASE_INVALID` | Expected clean-environment diagnostic; not normalized into success. |
| Same isolated environment: `aether init --dry-run --json` | Exit 3; `AETHER-INIT-HERMES-PROJECTS-UNAVAILABLE` | Expected read-only prerequisite refusal; no native Project or credential action was attempted. |
| Same isolated environment: `aether observe --json` | Exit 0; `{"state":"empty"}` | Expected empty provider-free observation result. |
| Same isolated environment: `aether knowledge doctor --json` | Exit 1; `COMPONENT_UNAVAILABLE` | Expected optional-component boundary; direct source inspection remained the fallback. |
| Same isolated environment: `aether version --json` | Exit 0; `MANAGER_DETAIL_UNAVAILABLE` warning | Version remains usable while unqualified manager details stay visible as unavailable. |
| `git diff --check` before adding this record | PASS | No whitespace errors in the candidate changes inspected before the evidence addition. |

## Public-artifact differential verification

The scanner and test were executed without modification. For `origin/main`, a fresh
read-only archive was materialized into a temporary Git index solely so the scanner's
`git ls-files` enumeration operated on the exact fetched tree; no generated or temporary
file is evidence.

| Check | Candidate HEAD | Current `origin/main` baseline |
| --- | --- | --- |
| `uv run --frozen python scripts/check_public_artifacts.py --root <candidate>` | Exit 1; exactly two findings | Exit 1; exactly the same two findings |
| Complete normalized finding set | `.aether/objective-contracts/oc_0084270d940c98d9/v1.md: absolute-user-home`; `.aether/objective-contracts/oc_0084270d940c98d9/v1.md: operator-desktop-layout` | Identical set and paths/kinds |
| Historical v1 blob | `97b5e859a96a882cd607d58b0090551c6b582f3f` | `97b5e859a96a882cd607d58b0090551c6b582f3f` |
| Set/blob comparison | Finding sets equal; exact allowed inherited baseline; blob equal | Confirms no objective-introduced finding, removed/changed finding, or historical-byte change. |
| `uv run --frozen pytest -q tests/test_public_artifacts.py` | Exit 1: 5 passed, 1 failed | The one failure is the unchanged inherited #364 tracked-surface finding above; the scanner/test remains enabled and unmodified. |

The nonzero public-artifact result is recorded as an accepted inherited baseline, never as
a passing test. No new path, finding kind, changed historical blob, exemption, skip or
weakened assertion was observed.

## Requirement mapping

| Contract obligation | Evidence from this run |
| --- | --- |
| AC 1–11; deliverables 1–6 | The integrated reviewed content/website candidate was exercised through normal build/check/content tests, 57 browser passes plus the documented intentional skip, Pages-mode verification, capture generation, representative desktop/mobile geometry/DOM inspection, no-JavaScript and accessibility coverage. No implementation change was made by this unit. |
| AC 12 | Candidate and fetched `origin/main` scanner outputs are complete-set equal and contain only the two permitted inherited findings for immutable historical v1; blob IDs are identical. The public-artifact test remains red only for that baseline. The new evidence record contains no credentials, private runtime state, contact/channel identifiers, machine paths, sessions, boards, logs or provider bindings. |
| AC 13; deliverable 8 | Root documentation validation and focused documentation tests passed; website guidance and implementation were consumed as present in the integrated candidate. |
| AC 14; deliverables 7 and 9 | This record supplies unit verification and explicit limitations. Independent Supervisor review remains required; this self-review is not approval. No PR, push, merge, issue mutation, deployment, release or package publication was performed. |
| Preservation, authority and stop conditions | Only `specs/beginner-first-website-docs/evidence/BGD-V2-VERIFY.md` is writable under this unit. Contract bytes, scanner/test, workflows, docs/website/runtime source and unrelated paths were preserved. |

## Compatibility and remaining risk

Unit compatibility impact: `none`. This unit adds evidence only and does not change public
interfaces, runtime behavior, website behavior, scanner behavior or release metadata. This
is unit-level compatibility evidence; Supervisor owns aggregate release conclusions.

Remaining limitations and risks:

- The exact inherited #364 public-artifact baseline remains a local nonzero and must not
  be represented as a green test. Terminal integration must keep the differential and
  historical-blob proof, and required PR checks remain independently required.
- Pixel-level inspection of generated PNG captures could not be completed because the
  available image-analysis backend rejected the requests. Automated browser assertions,
  capture geometry and text/DOM inspection passed; independent reviewer visual inspection
  remains outstanding.
- The candidate is a local stabilization build. Passing local checks does not imply a
  public installation, provider-backed execution, merge, Pages deployment or release.
- Same-card Supervisor review remains outstanding; this record is not independent review.
