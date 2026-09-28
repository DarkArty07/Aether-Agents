# Morfeo result reception — Lab/Monitor source retirement

**Contract:** `oc_736139ca259b79d8@v1`, SHA-256
`3be6f0ef6e84864f3431618f8eb38aa9b2a122bc8f50aee993a5d1917a171c58`.
**Project:** `.aether/project.toml` UUID `12027989-a08f-41cd-a82c-54ff1bfb6b03`.
**Final source revision inspected:** `d5bed9a8f30c5d5e2289630c4eac1c6585b42c48`
(`origin/main`, PR #547 merge `52bdd53d34ca5bd2643e0ec9009bf4fe09e17d66`
plus PR #548 Pages correction). This is a **post-merge reception**, not evidence
contained in either retirement PR. Source outcome and objective-owned worktree cleanup
are supported at this revision. Supervisor task `t_35254b55` completed the scoped
post-terminal root-worktree removal, independently rechecked below.

## Criterion-by-criterion result

| Criterion | Actual location and evidence | Result and limit |
| --- | --- | --- |
| RET-01: formal Lab removed | **Direct** `git ls-tree -r origin/main`: no `src/aether_agents/lab/`, `lab/`, `scripts/e2e/`, or mapped Lab resources. **Reused** independently reviewed U1 `evidence/u1.md`: dedicated Lab tests removed, while retained knowledge E01 fixture migrated off both Lab imports. | Supported at final revision. The old formal API/qualification matrix is intentionally gone; this is not PD-74 PASS. |
| RET-02: Monitor and periodic reports removed | **Direct** final `src/aether_agents/cli.py` has no `monitor` parser/dispatch; `pyproject.toml` lists exactly three current plugin entry points; Morfeo's shipped `config.yaml` has no Monitor opt-in; `git ls-tree` has no Monitor source, reporting resources or dedicated scripts. **Reused** U2 `evidence/u2.md` and integrated packaging/CLI/absence checks. | Supported in source and new packages. Historical plugin-name literals remain solely in closed legacy identity validation; historical installed runtime/paused job/state were not purged or reactivated. No new reporting mechanism was introduced. |
| RET-03/04: preserve remaining function and test isolation | **Direct** diff base→final: no Hermes fork/pin, cron/gateway implementation, SOUL or canonical skill changes; only Morfeo's default config loses Monitor opt-in. **Direct** `tests/runtime_isolation.py` keeps identity scrubbing/contained disposable destinations and the KG-19 fixture now uses it. **Reused** `evidence/u1.md` (eight deterministic KG tests, 35 passed/one optional native skip in isolated U1) and `evidence/integration.md` plus green exact-head CI for retained source tests. | Supported for source/product tests; no claim of a live runtime or agent-behavior qualification. Owner-cancelled live E01 remains UNVERIFIED. |
| RET-05: exact packaging and historical integrity | **Direct** final `src/aether_agents/lifecycle.py:133-146,6730-6755,7071-7078` has current three-plugin map and a separate exact historical four-plugin map; parsed authenticated map feeds fingerprints, with no open-ended plugin allowance. **Reused** `evidence/u3.md` and integrated disposable wheel/sdist, malformed-map, manager/runtime and release identity tests. | Supported for current artifacts and deterministic legacy-read logic. The historical map test uses a constructed wheel, not a live old-release cutover; frozen-old-reader forward adoption is deferred. |
| RET-06: current docs and history | **Direct** final `docs/capabilities.toml`, `docs/reference/capabilities.md` and root docs omit both current capabilities; `specs/telegram-monitor/spec.md:3-9` explicitly supersedes the historical intent. `git diff` of the post-retirement Pages repair shows only removal of the obsolete guide description in `website/src/lib/docs.ts`. **Reused** U4 and integrated `evidence/integration.md`, literal inventory `397=397`, documentary checks, and successful exact-head Pages run `36404606317`. | Supported. Earlier #407, KG-19 and contract evidence remain historical; no retroactive PASS. |
| RET-07: verified closeout | **Direct** `gh pr view`: #547 and #548 MERGED at the two stated SHAs, eight required checks successful on each; `gh run view` confirms Repository Policy and Website Pages SUCCESS on final `d5bed9a8`; #546 CLOSED completed, no milestone. Inspected PR #547 CI log: 1713 passed/6 skipped plus 36 native Graphify tests, integrated 80% coverage with unchanged 78% floor. **Reused** Supervisor root `t_634761f7` and SHA-256-verified attachment 1 `final.md` (digest `8b3005a4bc8b2a460111288ee636d85ccb7a3d267759300bbde8c060a28bf91b`), four independently reviewed units, full local exact-Hermes 1655 passed/64 skipped/658 subtests and uninstrumented performance 4 passed. **Direct cleanup readback:** dependent Supervisor task `t_35254b55` done; `.worktrees/t_9bfdfc93` absent from filesystem and `git worktree list` following ordinary non-force removal. | Supported at exact final source revision; no runtime adoption claim. A non-ancestor, content-equivalent local design branch remains intentionally rather than force-deleted. |

## Verification attribution and limitations

I directly inspected exact current source, contract/attachment hashes, tracked-path
absence, the PR/issue/main run states and selected PR #547 CI log entries. I **did not**
re-run the full suite, build artifacts, Graphify append, browser tests or behavior
campaign. The executable test/build counts outside selected CI log rows above are
attributed to Implementer/Supervisor evidence at their specified revisions. PR #548
touched only the website guide map, so the reviewed Python/package evidence and #547
CI remain applicable to final `d5bed9a8`; the final main push additionally passed
Repository Policy (`36404606178`) and Pages (`36404606317`). Two local combined
`pytest-cov` attempts failed with mixed coverage shards; local partial 74% was not
called PASS. The existing CI split measured 80% at #547; no threshold or check was
weakened. The compact native observer repeatedly returned
`AETHER-OBSERVE-CATCHUP-INCOMPLETE`; exact native task, attachment, source and GitHub
states were used instead. Graph index unavailable; I did not refresh it or claim a
project graph update. No release, live cutover, model/Telegram report, historical state
purge or PD-74 reliability qualification was performed.

**Release conclusions:** `release_impact=major` (removed public Lab API and Monitor
CLI/tool/plugin), `release_action=defer`, `release_channel=none`.

## Cleanup follow-up

The previous terminal worker retained `.worktrees/t_9bfdfc93` because its process CWD
used it. Supervisor's dependent cleanup task `t_35254b55` completed after checking
clean status, no process/file-descriptor users and the exact final revision, removing
that worktree with ordinary non-force `git worktree remove`. Morfeo independently
confirmed path absence and no Git worktree registration. The primary design branch has
different commit ancestry but equivalent content to final `main` for the owning plan/
quickstart (the sole textual difference is a corrected CI line locator). Its branch
ref is preserved rather than force-deleted. Tracking this post-merge reception in a
later documentation update does not make it part of the earlier retirement PRs.
