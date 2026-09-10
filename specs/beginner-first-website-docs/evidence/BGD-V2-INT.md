# BGD-V2 terminal integration evidence

Status: terminal closeout evidence for Objective Contract `oc_844dfc12880ee967@v2`.
This record distinguishes local acceptance, inherited nonzero scanner evidence, GitHub
required checks and publication boundaries. It is not evidence of merge, Pages deployment,
package publication, provider-backed execution or a public installation.

## Authority and candidate

- Final contract: `.aether/objective-contracts/oc_844dfc12880ee967/v2.md`, SHA-256
  `72a435bf75c73d26785f3ce00d90f151e8023a236b4f69ba7d159bb3fee90e4e`.
- Required continuation base: `6ddedab1dae701af51382822740050ccb0c29dc9`.
- Locally verified candidate before this evidence commit:
  `49f8219e709b76b084d3f9690cdcbec7ca62e145`.
- Fetched default-branch baseline:
  `89c372fa6af09c6cbd5ce9a18dc7dd78ed70dfc4`; it is an ancestor of the candidate.
- Portable Project: `12027989-a08f-41cd-a82c-54ff1bfb6b03`, repository
  `DarkArty07/Aether-Agents`.
- GitHub issue #368 is the owning issue. It was open with no milestone before publication.
- The accepted content, website, website-guidance correction and v2 verification commits
  remain discrete in history. No squash, amend, rebase, force operation or history rewrite
  was used.

The canonical Objective Contracts, public-artifact scanner and its test are unchanged from
the v2 continuation base. During GitHub closeout, the existing policy workflow's exact
non-spec manifest required one bounded integration correction for the five objective-owned
reader/test paths; that workflow-only repair is recorded below and changes no executable
reader behavior or acceptance oracle. The independently reviewed local progress reporter
remains private operational state; no destination, job, board, session or routing identifier
is recorded here.

## Independent review consumed

The terminal candidate consumes completed native same-card Supervisor review of both active
v2 units:

- Candidate verification was approved after an execution-first rerun of the full
  website/root/parser/Pages/browser sequence and the exact current-default-branch scanner
  differential.
- The progress reporter was approved after four review rounds, including correction of its
  provider-free mode, failure-path privacy, exact terminal binding and repeated-failure
  suppression. The accepted reporter is one reused no-agent job with change-driven output;
  earlier agent-backed records remain historical and are not reclassified.
- A truthfulness defect in `website/README.md` was returned to an Implementer and corrected
  in its own commit. The independently reviewed verification unit then re-ran and approved
  the corrected candidate, so terminal integration does not self-approve that repair.

## Integrated local verification

Website checks began from a fresh detached clone of the exact candidate. Generated output,
browser reports and captures in that clone were untracked and were not treated as durable
repository evidence.

| Command or action | Observed result | Interpretation |
| --- | --- | --- |
| `npm ci` | PASS; 320 packages installed/audited, 0 vulnerabilities | The committed lockfile was sufficient. |
| `npm run build` | PASS; 22 static pages | Normal local-path build completed from fresh output. |
| `npm run check` | PASS; 33 files, 0 errors, warnings or hints | Astro/type diagnostics are clean. |
| `npm test` | PASS; 15 tests | Manifest, corpus, routes, links, source integrity, guidance and preservation checks pass. |
| First isolated browser attempt | Environment-only refusal because another loopback preview already owned port 4321 | No process was stopped and this attempt is not counted as qualification. An alternate-port probe passed 55 cases; its two expected failures were the unchanged test's explicit 4321 locality assertion. |
| Exact `npm run test:e2e` | PASS; 57 passed, 1 intentional desktop skip across 58 desktop/mobile Chromium cases | The existing preview was first proven to serve source links pinned to exact candidate `49f8219e...`; the unchanged command/test suite then passed. The skipped desktop mobile-menu guard runs and passes in the mobile project. |
| `AETHER_PAGES=1 npm run build` | PASS; 22 pages | Project-site base-path artifact built locally. |
| `node scripts/verify-pages-build.mjs` | PASS; 22 HTML pages | Base-path links/resources resolve. This does not deploy Pages. |
| Restored `npm run build` | PASS; 22 pages | Normal non-Pages output was restored. |
| `node scripts/capture.mjs` | PASS at 360, 390, 768, 1024, 1440 and 1920 pixels, plus four representative docs routes at mobile and desktop widths | Every reported document width equaled its viewport and every overflow list was empty. |
| Capture image-analysis attempts | Unavailable: the image-analysis backend returned connection/rejection errors for all eight representative docs captures | No pixel-level visual pass is claimed. Real Chromium interaction, DOM/geometry, overflow and Axe evidence passed. |
| `uv run --frozen python scripts/check_documentation.py` | PASS: `documentation validation passed` | Registry and generated capability reference remain coherent. |
| `uv run --frozen pytest -q tests/test_beginner_documentation.py tests/test_documentation.py` | PASS; 20 passed | Beginner journey, links, status and documentation invariants pass. |
| Isolated temporary `HOME`, `HERMES_HOME` unset: 27 parser/help paths | PASS; 27 of 27 exited 0 | Top-level version/help, every top-level command help path and every knowledge-child help path remain provider-free. |
| Same isolated environment: `doctor --json` | Expected exit 4, `LIFECYCLE_INTEGRITY_FAILED` | No active qualified release exists. |
| Same isolated environment: `init --dry-run --json` | Expected exit 3, `AETHER-INIT-HERMES-PROJECTS-UNAVAILABLE` | Initialization refuses without an exact native Project; no state was created. |
| Same isolated environment: `observe --json` | Exit 0, state `empty` | Read-only provider-free observation remains usable. |
| Same isolated environment: `knowledge doctor --json` | Expected exit 1, `COMPONENT_UNAVAILABLE` | Optional knowledge remains unavailable; direct source inspection was used. |
| Same isolated environment: `version --json` | Exit 0 with `MANAGER_DETAIL_UNAVAILABLE` | Product version remains available while unqualified manager detail stays visible. |
| `git diff --check origin/main...HEAD` | PASS | No whitespace errors in the objective diff. |
| Root and website `AGENTS.md` audit | PASS | Guidance remains coherent with direct tracked-doc rendering, stabilization status, required website commands and no merge/deploy/release inference. |

The exact browser command passed without killing or replacing the pre-existing same-candidate
preview. The alternate-port diagnostic changed only disposable verification configuration
inside the fresh clone and is not represented as an unchanged-suite pass.

## Exact inherited public-artifact baseline

The unchanged scanner and unchanged public-artifact test were run against both the candidate
and a freshly materialized exact `origin/main` tree.

| Check | Candidate | `origin/main` |
| --- | --- | --- |
| Scanner exit | 1 | 1 |
| Complete findings | `.aether/objective-contracts/oc_0084270d940c98d9/v1.md: absolute-user-home`; `.aether/objective-contracts/oc_0084270d940c98d9/v1.md: operator-desktop-layout` | Identical complete set |
| Historical blob | `97b5e859a96a882cd607d58b0090551c6b582f3f` | `97b5e859a96a882cd607d58b0090551c6b582f3f` |
| `pytest -q tests/test_public_artifacts.py` | Exit 1; 1 failed, 5 passed | Exit 1; 1 failed, 5 passed |

The result is accepted only as the exact inherited #364 baseline fixed for future contracts
by merged PR #370. It is not called a passing test. No finding was added, removed or changed;
the historical blob is byte-identical; the scanner/test remain enabled and unmodified.
GitHub required checks remain a separate green requirement.

## GitHub closeout checkpoint

The authorized target is one normal pull request to `main`, linked to #368, with all branch-
protection-required checks green. The PR must remain open and unmerged because a qualifying
`main` push triggers `.github/workflows/pages.yml`, including `actions/deploy-pages@v4`.

The branch was normally pushed and pull request #375 was opened against `main`, linked to
#368 without auto-closing it. Its first required policy matrix failed immediately because
the workflow's exact non-spec manifest did not yet list the five objective-owned additions:
`docs/start-here.md`, `docs/guides/first-objective.md`,
`docs/reference/glossary.md`, `tests/test_beginner_documentation.py` and
`website/tests/browser/docs.spec.ts`. The three Python jobs reported the same deterministic
manifest defect. Terminal integration added exactly those five entries to the existing
manifest as mechanically implied build/config glue; local manifest equality, workflow YAML,
documentation checks, focused tests, whitespace and the exact scanner baseline were then
re-verified before a normal follow-up push. No check was bypassed or weakened.

The final required-check state and open/unmerged boundary are recorded after the corrected
PR revision completes. Merge, issue closure and Pages deployment remain outside current
authority.

## Compatibility and release conclusions

- `release_impact = patch` — backward-compatible documentation and reading-surface
  correction/expansion; no Aether runtime/API contract changed.
- `release_action = defer` — neither merge nor release preparation/publication is authorized.
- `release_channel = none` — no prerelease or stable channel is selected.

`VERSION` remains `0.24.0`; no version, changelog release heading, tag, GitHub Release,
package or deployment mutation is part of this objective.

## Deferred or non-applicable closeout steps

- Merge: deferred because merging this docs/website diff to `main` would trigger Pages
  deployment, which this contract does not authorize.
- Issue closure: deferred with merge; #368 remains open and linked rather than falsely
  completed as a live deployment.
- Milestone reconciliation: non-applicable because #368 has no milestone.
- Pages deployment: forbidden under current authority; local Pages-mode build is not a
  deployment claim.
- Release/tag/package publication: non-applicable and forbidden; release action/channel are
  `defer`/`none`.
- Remote/local objective branch and worktree cleanup: deferred because the authorized
  terminal artifact is an active, unmerged pull request. Active/unmerged and unrelated work
  must be preserved.
- Project-knowledge update: unavailable because the bound component reports no snapshot;
  direct source and executable verification are the accepted fallback.
