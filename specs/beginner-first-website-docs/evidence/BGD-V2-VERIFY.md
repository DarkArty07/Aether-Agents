# BGD-V2-VERIFY evidence

Status: Implementer self-review evidence for the v2 candidate-verification unit. This
record is not independent review, integrated terminal acceptance, a release decision,
proof of Pages deployment, or proof of a public installation.

## Unit and source basis

- Objective Contract: `oc_844dfc12880ee967@v2`, SHA-256
  `72a435bf75c73d26785f3ce00d90f151e8023a236b4f69ba7d159bb3fee90e4e`.
- Candidate source revision verified before this evidence commit:
  `8dfea7e44e9d7d0a43ee7ccbc84ec41309c6cb6a` (`docs(website): reconcile local Pages
  status guidance`). It contains the independently reviewed BGD-WEB implementation,
  the corrected website status/Pages guidance and its regression; this unit does not
  modify website or runtime behavior.
- Required continuation base: `6ddedab1dae701af51382822740050ccb0c29dc9`; it is an
  ancestor of the candidate. The integrated website merge is
  `860176e1db8c6c24d937f38d67b9a9c1f190f9b4`, consuming recovered reviewed website head
  `ad892a7539ecc619bf00b9d4be0a1b8a2602f1a7`.
- Current read-only `origin/main` after `git fetch --no-prune origin main`:
  `89c372fa6af09c6cbd5ce9a18dc7dd78ed70dfc4`.
- Project binding: `.aether/project.toml` project
  `12027989-a08f-41cd-a82c-54ff1bfb6b03`, repository `DarkArty07/Aether-Agents`.
- No `.aether/skills/` directory exists in the candidate. Project-knowledge status was
  unavailable (`available=false`), so current source and test inspection were used; the
  implementation-evidence, project-knowledge and work-memory procedures governed this
  run. Relevant work-memory lessons were revalidated: rebuild after each HEAD-changing
  commit and restore the normal `HOME` before Playwright checks.

This unit changes only this evidence path. It does not modify the Objective Contracts,
scanner, public-artifact tests, website/source/runtime files, workflows or documentation
implementation.

## Executed verification before the evidence commit

Generated website output and captures are ignored and are not durable evidence. Commands
were run against the candidate source revision above unless a different revision is named.

| Command or action | Observed result | Interpretation |
| --- | --- | --- |
| `git status --short --branch`, lineage checks | Clean; candidate `8dfea7e...`; required base is an ancestor | Starting state and prerequisites matched the v2 receipt. |
| `git fetch --no-prune origin main` | PASS; `origin/main` = `89c372fa...` | Differential verification used the current fetched default-branch ref. |
| `npm ci` from `website/` | PASS; 320 packages added/audited, 0 vulnerabilities | Existing lockfile/dependencies were sufficient; no dependency file changed. |
| `npm run build` | PASS; 22 static pages | Normal website build completed. |
| `npm run check` | PASS; 33 files, 0 errors, warnings or hints | Astro/type diagnostics were clean. |
| `npm test` | PASS; 15 passed, 0 failed/skipped/cancelled | Content, guidance, manifest, link, source-integrity and preservation tests passed, including the corrected README/Pages regression. |
| `npm run test:e2e` | PASS; 57 passed, 1 intentional skip across desktop/mobile Chromium | Browser UX, grouped docs, navigation, search, accessibility, responsive/no-JavaScript and history behavior passed; the desktop-only mobile-navigation guard skipped and ran in the mobile project. |
| `AETHER_PAGES=1 npm run build` | PASS; 22 pages | Project-site base-path artifact built. |
| `node scripts/verify-pages-build.mjs` | PASS; 22 HTML pages | Pages links/resources resolved locally; this is not deployment evidence. |
| Restored normal `npm run build` | PASS; 22 pages | Non-Pages output was restored before capture and inspection. |
| `node scripts/capture.mjs` | PASS at 360, 390, 768, 1024, 1440 and 1920 pixels, plus docs index/start/walkthrough/reference at 390 and 1440 | Every reported document width equaled its viewport and every overflow list was empty. Capture files remain ignored under `website/test-results/visual/`. |
| Representative browser DOM/geometry inspection | Mobile `/docs/start-here/` at 390px reported `lang=en`, group `Start here`, 390px document width and two contained focusable local scroll regions. Desktop `/docs/` and `/docs/reference/capabilities/` at 1440px reported matching document widths, `lang=es-MX` for the index, and the expected grouped/article context. | Text/geometry inspection corroborated the automated browser checks. Pixel-level PNG review is not claimed: the available image-analysis backend rejected local capture requests; this limitation does not alter the passing DOM, geometry or accessibility results. |
| `uv run --frozen python scripts/check_documentation.py` | PASS: `documentation validation passed` | Root documentation/registry coherence remained green. |
| `uv run --frozen pytest -q tests/test_beginner_documentation.py tests/test_documentation.py` | PASS; 20 passed | Focused root documentation checks passed. |
| Isolated temporary `HOME`, with `HERMES_HOME` unset: 27 documented parser/help paths | All 27 exited 0 | Provider-free parser/help surfaces were exercised without credential or provider setup. |
| Same isolated environment: `aether doctor --json` | Exit 4; `LIFECYCLE_INTEGRITY_FAILED` / `ACTIVE_RELEASE_INVALID` | Expected clean-environment diagnostic; not normalized into success. |
| Same isolated environment: `aether init --dry-run --json` | Exit 3; `AETHER-INIT-HERMES-PROJECTS-UNAVAILABLE` | Expected read-only prerequisite refusal; no native Project or credential action was attempted. |
| Same isolated environment: `aether observe --json` | Exit 0; JSON `{"state":"empty"}` | Expected empty provider-free observation result. |
| Same isolated environment: `aether knowledge doctor --json` | Exit 1; `COMPONENT_UNAVAILABLE` | Expected optional-component boundary; direct source inspection remained the fallback. |
| Same isolated environment: `aether version --json` | Exit 0; `MANAGER_DETAIL_UNAVAILABLE` warning | Version output remained usable while unqualified manager details stayed visible as unavailable. |
| `git diff --check` before adding this record | PASS | No whitespace errors in the inspected candidate changes. |

## Public-artifact differential verification

The scanner and public-artifact test were executed without modification. For
`origin/main`, a fresh read-only archive was materialized in a temporary Git repository
so the scanner's `git ls-files` enumeration covered the exact fetched tree. Temporary
paths and generated files are not evidence.

| Check | Candidate source revision | Current `origin/main` baseline |
| --- | --- | --- |
| `uv run --frozen python scripts/check_public_artifacts.py --root ...` | Exit 1; exactly two findings | Exit 1; exactly the same two findings |
| Complete normalized finding set | `.aether/objective-contracts/oc_0084270d940c98d9/v1.md: absolute-user-home`; `.aether/objective-contracts/oc_0084270d940c98d9/v1.md: operator-desktop-layout` | Identical set and paths/kinds |
| Historical v1 blob | `97b5e859a96a882cd607d58b0090551c6b582f3f` | `97b5e859a96a882cd607d58b0090551c6b582f3f` |
| Set/blob comparison | Complete finding sets equal; exact allowed inherited baseline; blob equal | Confirms no objective-introduced finding, removed/changed finding or historical-byte change. |
| `uv run --frozen pytest -q tests/test_public_artifacts.py` | Exit 1: 5 passed, 1 failed solely on the exact inherited findings | The same test run against the detached `origin/main` tree also exited 1 with 5 passed and 1 inherited-baseline failure. The scanner/test remain enabled and unmodified. |

The nonzero public-artifact result is recorded as an accepted inherited #364 baseline,
never as a passing test. No new path, finding kind, changed historical blob, exemption,
skip or weakened assertion was observed.

## Requirement mapping

| Contract obligation | Evidence from this run |
| --- | --- |
| AC 1–11; deliverables 1–6 | The integrated reviewed content/website candidate passed normal build/check/content tests, 57 browser tests plus the documented intentional skip, Pages-mode verification, capture generation, representative desktop/mobile geometry/DOM inspection, no-JavaScript and accessibility coverage. This unit made no implementation change. |
| AC 12 | Candidate and fetched `origin/main` scanner outputs are complete-set equal and contain only the two permitted inherited findings for immutable historical v1; blob IDs are identical. The public-artifact test remains red only for that baseline. The evidence record contains no credentials, private runtime state, contact/channel identifiers, machine paths, sessions, boards, logs or provider bindings. |
| AC 13; deliverable 8 | The corrected candidate guidance identifies the local v2 status, independently approved BGD-WEB integration, active Pages workflow, loopback/non-deployment boundary and deferred merge/deployment authority. The new content regression passed within the 15-test suite; root documentation validation and focused tests also passed. |
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
