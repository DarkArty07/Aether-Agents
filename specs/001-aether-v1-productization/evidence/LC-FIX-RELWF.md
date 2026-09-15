# LC-FIX-RELWF Evidence — release workflow context placement repaired (#445)

**Unit:** LC-FIX-RELWF (task `t_5cd52e79`, Implementer; same-card review pending)
**Objective Contract:** `oc_3397f9f05d780f8e@v1`
**Canonical breakdown:** `specs/001-aether-v1-productization/tasks.md` (read-only for this unit)
**Branch:** `aether-agents-2/t_5cd52e79-lc-fix-relwf-release-workflow-must-be-va`
**Base / pre-change tip:** `748aa24` (= `origin/main`, = the commit the published tag
`v1.0.0-rc.1` points to)
**Delivered change:** `.github/workflows/release.yml` (3 lines: 1 removal, 2 additions) and
this record
**Status of this record:** unit-local implementation evidence. It is not an aggregate release
conclusion, not a publication claim, and not independent review. See §7 for the one piece of
required evidence this unit cannot produce by itself.

---

## 1. The defect, measured from the run list

Workflow id `322473622` (`.github/workflows/release.yml`), read from the repository at the start
of this unit (and re-read after the edit below; the list is unaffected by a local working-tree
change):

| run | branch | event | result | created |
| --- | --- | --- | --- | --- |
| `34976208051` | `aether-agents-2/lc-int-evidence-completion` | push | failure | 13:37:36Z |
| `34973974807` | `main` | push | failure | 13:16:45Z |
| `34973199966` | `dependabot/…/setup-python-7.0.0` | push | failure | 13:09:21Z |
| `34973191917` | `dependabot/…/setup-node-7` | push | failure | 13:09:16Z |
| `34972973946` | `main` | push | failure | 13:07:09Z |
| `34970491076` | `aether-agents-2/lc-int-integration` | push | failure | 12:42:59Z |
| `34969050801` | `aether-agents-2/lc-int-integration` | push | failure | 12:28:26Z |
| `34962565337` | `aether-agents-2/lc-int-integration` | push | failure | 11:18:19Z |
| `34962035859` | `aether-agents-2/lc-int-integration` | push | failure | 11:12:29Z |
| `34959233501` | `aether-agents-2/lc-int-integration` | push | failure | 10:40:49Z |
| `34958903673` | `aether-agents-2/lc-int-integration` | push | failure | 10:37:05Z |
| `34958456645` | `aether-agents-2/lc-int-integration` | push | failure | 10:32:10Z |
| `34957990444` | `aether-agents-2/lc-int-integration` | push | failure | 10:27:10Z |
| `32001505643` | `v0.24.0` | push | **success** | 2026-08-17 |
| `31991018645` | `v0.23.0` | push | **success** | 2026-08-17 |
| `31353381390` | `v0.22.0` | push | **success** | 2026-08-10 |
| `30395467442` | `v0.20.0` | push | **success** | 2026-07-28 |

13 failure / 4 success. Every failure is a **zero-job** run, which is GitHub's shape for a
workflow file it refuses to schedule:

```
$ gh api repos/…/actions/runs/<id>/jobs --jq '.total_count'
34973974807 -> 0      # tag push v1.0.0-rc.1, head 748aa24
34972973946 -> 0      # main push, head 748aa24
34969050801 -> 0      # aether-agents-2/lc-int-integration push
34973199966 -> 0      # dependabot push
32001505643 -> 1      # v0.24.0 tag push, success (the pre-defect reference)
```

and `gh run view 34973974807` reports verbatim:

```
X This run likely failed because of a workflow file issue.
```

The defect is live, not historical: run `34976208051` was created by a branch push at 13:37:36Z
during this unit, and it is a zero-job failure like the rest. Every push to any branch reproduces
it, so the repository currently has no working automated release path.

## 2. Root cause, re-measured with GitHub's own context rules

Local YAML parsing (and the repository's own workflow-reading tests) never failed, which is why
the file entered `main`. The decisive rule is **context availability**, and the independent
implementation of it is `actionlint` (the community linter that encodes the documented
per-position context matrix, including GitHub's own error wording).

```
$ uvx --from actionlint-py actionlint --version
1.7.12

$ uvx --from actionlint-py actionlint -oneline <pre-change blob 748aa24>
release.yml:37:31: context "runner" is not allowed here. available contexts are "github",
"inputs", "matrix", "needs", "secrets", "strategy", "vars". see
https://docs.github.com/en/actions/learn-github-actions/contexts#context-availability for more
details [expression]
rc=1

$ uvx --from actionlint-py actionlint -oneline <fixed working tree>
rc=0
```

Two controls, run with the same tool and version:

| control | expectation | result |
| --- | --- | --- |
| A — the fix reverted (the same key placed back in the job-level `env:` of an otherwise fixed file) | the error returns, at the same position | `…:37:31: context "runner" is not allowed here …` `rc=1` |
| B — `.github/workflows/policy.yml` at the same commit (a workflow GitHub demonstrably accepts and executes) | clean, i.e. the tool has no false-positive bias here | `rc=0` |

So the single reported error is the placement of one key, and moving it removes the only
GitHub-rule violation in the file.

## 3. The change

Job level (`jobs.release.env`) — one key removed:

```yaml
    env:
      RELEASE_TAG: ${{ github.event_name == 'workflow_dispatch' && inputs.tag || github.ref_name }}
      GH_TOKEN: ${{ github.token }}
    steps:
```

Step level — the same key added to exactly the two steps whose `run:` bodies read it, and to no
other step:

| step | env keys before | env keys after |
| --- | --- | --- |
| `Build and qualify the release bundle` | `RELEASE_VERSION` | `RELEASE_BUNDLE_DIR`, `RELEASE_VERSION` |
| `Create or reconcile GitHub Release` | `RELEASE_PRERELEASE`, `RELEASE_VERSION` | `RELEASE_BUNDLE_DIR`, `RELEASE_PRERELEASE`, `RELEASE_VERSION` |

`RELEASE_BUNDLE_DIR` is read at `.github/workflows/release.yml` line 88 (`--out "$RELEASE_BUNDLE_DIR"`)
after the change and line 114 (`bundle_dir="${RELEASE_BUNDLE_DIR:-}"`) after the change; both
steps now declare it.

### Structural delta (per job / per step / per key, not a text diff)

| element | before | after | verdict |
| --- | --- | --- | --- |
| workflow `name` / top-level keys / `permissions` / workflow `env` (`FORK_REPOSITORY`, `FORK_COMMIT`) | — | — | identical |
| `on:` block | — | — | identical (`sha256[:12]` of the parsed trigger `373c4f0c32e5` both sides) |
| job set | `['release']` | `['release']` | identical |
| `runs-on` | `ubuntu-latest` | `ubuntu-latest` | identical |
| job env keys | `GH_TOKEN`, `RELEASE_BUNDLE_DIR`, `RELEASE_TAG` | `GH_TOKEN`, `RELEASE_TAG` | the key moved |
| step count / step sequence (`name` or `uses`, in order) | 7 | 7 | identical |
| step 0–3, 5 (`actions/checkout@3d3c42e5…`, `Validate release tag`, `astral-sh/setup-uv@94527f2e…`, `Install locked release toolchain`, `Retain the qualified bundle`) | — | — | `IDENTICAL` on `name`, `uses`, `with`, `env`, `shell` and the SHA-256 of every `run:` body |
| step 4 `Build and qualify the release bundle` | env `RELEASE_VERSION` | env `RELEASE_BUNDLE_DIR`, `RELEASE_VERSION`; `run:` body digest unchanged | the key moved |
| step 6 `Create or reconcile GitHub Release` | env `RELEASE_PRERELEASE`, `RELEASE_VERSION` | env `RELEASE_BUNDLE_DIR`, `RELEASE_PRERELEASE`, `RELEASE_VERSION`; `run:` body digest unchanged | the key moved |

Summary: 5 structural deltas, **all five** of them the relocated `RELEASE_BUNDLE_DIR` key; deltas
of any other kind: **0**. `Retain the qualified bundle` keeps `${{ runner.temp }}/release-bundle`
in its `with:` and is untouched — after the change the only `runner.` references in the file are
at step-level positions (lines 73, 94, 100), which is the placement `policy.yml` already uses.

File digests: before `f988ec0d758de339c5e489c94d4dc3fe7bacd8c3df4aa83fa419aeb121671a7b`
(6388 bytes, 141 lines); after `c27e3e44881dd3f2275b815d9fdd522957e8ab3075a02cf9b979d8e7b89e8b03`
(6456 bytes, 142 lines). `git diff --stat`: `1 file changed, 2 insertions(+), 1 deletion(-)`.

## 4. The step's validation logic, executed locally

The `Validate release tag` body was extracted from the **fixed** workflow with the shipped
extraction convention (`tests/test_a1_contracts.py::_workflow_step_script`) and executed outside
pytest in a disposable clone checked out at the tagged commit, with `origin` pointed at the real
repository and `refs/remotes/origin/main` fetched from it:

```
checkout: detached at 748aa24ce5684185f65aa88b0e85919627ff6538   VERSION=1.0.0rc1
origin/main = 748aa24ce5684185f65aa88b0e85919627ff6538          (the tag's commit)

positive  RELEASE_TAG=v1.0.0-rc.1  rc=0  GITHUB_OUTPUT: version=1.0.0rc1, prerelease=true
negative  RELEASE_TAG=v1.0.0       rc=1  (version identity assertion refuses it)
negative  RELEASE_TAG=nonsense     rc=1  stderr: Unsupported release tag: nonsense
```

The positive leg exercises the tag-shape mapping, the annotated-tag check, the `VERSION` identity
check and the `refs/tags/X^{commit} == refs/remotes/origin/main` equality check, so the repaired
file's gate logic still accepts the published RC identity. The local run replaces only `gh`-free
execution: it is not a live dispatch (see §7).

## 5. Repository gates

| Gate | Result |
| --- | --- |
| `uv sync --frozen --group dev` | `SYNC_RC=0` |
| `uv run --frozen pytest tests/test_a1_contracts.py tests/test_release_bundle.py -q` (the two suites that read `release.yml` and execute its step bodies) | `64 passed, 11 subtests passed in 6.78s`, exit 0 |
| `uv run --frozen pytest tests/test_a1_contracts.py tests/test_release_bundle.py tests/test_public_artifacts.py -q` (re-run at the delivered, staged state, adding the tracked-surface scan node) | `73 passed, 11 subtests passed in 8.07s`, exit 0 |
| `uv run --frozen python scripts/check_public_artifacts.py --root .` | `public artifact path scan passed: tracked surface + 0 artifact(s)`, exit 0 |
| `uv run --frozen python scripts/check_documentation.py` | `documentation validation passed`, exit 0 |
| `uv run --frozen mypy src/aether_agents` | `Success: no issues found in 67 source files` |
| CI-scoped `ruff check` (exact `policy.yml:697` scope) | `All checks passed!` |
| CI-scoped `ruff format --check` (exact `policy.yml:698` scope) | `160 files already formatted` |
| `git diff --check` | clean |

Two repo-wide static conditions are pre-existing, outside CI's scope and untouched by this change
(it adds no Python): `ruff check .` reports 3 `I001` findings in `lab/fixtures/sandbox/brownfield/verify.py`
and `specs/006-tools-memory-stability/fixtures/binding_privacy_probe.py`, and `ruff format --check .`
reports 5 files outside the CI scope (`lab/README.md`, `specs/001-aether-v1-productization/fixtures/hlp310_snapshot_canary.py`,
`specs/007-session-residual-stability/evidence/SR-399.md`, `specs/autonomous-bug-remediation/evidence/ABR-323.md`,
`specs/fix-310-341-345-354/evidence/HF-354.md`). None is in this unit's diff; they are named here so
nobody mistakes them for this change's effect.

The canonical full bootstrap (`scripts/run_tests.py`) was **not** run: the machine was under the
load/residue pressure the integration lane already documented (load average ~8.8, ~1 GB RAM
available, `/tmp` at 73%), and this change cannot affect any Python node. That omission is stated
rather than implied.

## 6. Audited but not changed

- **`.github/workflows/policy.yml`** — read as the reference for correct placement: its `runner.*`
  references (lines 620, 660, 684) are step-level, and GitHub accepts and executes it (e.g. run
  `34972975507` on `main`, push, `success`; `34973197119` on a dependabot branch, `success`), which
  is why the same workflow shape was chosen for the fix. Not modified.
- **`Retain the qualified bundle`** — already used `${{ runner.temp }}` directly in `with:`; left
  exactly as it was, per the card.
- **`RELEASE_TAG` / `GH_TOKEN` at job level** — both use contexts that are valid in
  `jobs.<job_id>.env` (`github`, `inputs`); left in place.
- **`VERSION`, `CHANGELOG.md`, `DESIGN.md`, `scripts/release_bundle.py`, `src/**`, all tests, other
  workflows, other units' evidence** — untouched. The tag `v1.0.0-rc.1`, the published release and
  its assets were not read-modified, re-uploaded, re-created or deleted; no `gh release` mutation
  of any kind was performed by this unit.
- **The empty job-level `env:` block** — kept rather than collapsed to a flat form, so the diff
  stays a key move. `RELEASE_TAG` and `GH_TOKEN` still need it.
- **`git fetch`/`git worktree` residue** — the disposable clone used in §4 lives outside the
  repository tree and is not tracked; no worktree, branch or tag was created in the project.

## 7. The empirical proof required by the card, and the boundary this unit cannot cross

The card requires GitHub acceptance to be shown empirically: push the fix on its own branch and
show the push does **not** produce a zero-job `release.yml` run, with the run list quoted before
and after. **That push has not been performed by this unit, and this record does not claim it.**

Reason, with sources: the Implementer publication boundary is canonical product policy —
`src/aether_agents/resources/profiles/implementer/SOUL.md` §02 ("Implementer must never publish,
never push, never open or merge pull requests …"), asserted by
`tests/test_objective_contracts.py::test_role_souls_assign_onboarding_issue_and_publication_boundaries`
(line 1495) — and the governing stabilisation breakdown repeats it for implementation units:
`specs/007-session-residual-stability/tasks.md:73` ("Implementation units make no remote mutation:
no push, no PR, no issue mutation …"). The Objective Contract itself keeps the same split
(`.aether/objective-contracts/oc_3397f9f05d780f8e/v1.md:44`: "Implementers may commit scoped work
in assigned branches/worktrees but do not publish"). A card cannot grant that authority, so the
push is handed to the lane that owns pipeline publication and terminal evidence.

**Ready-to-run handoff for that lane** (branch commit is on the unit branch; any branch carrying
the commit will do, e.g. the integration lane's own):

```
git push --set-upstream origin aether-agents-2/t_5cd52e79-lc-fix-relwf-release-workflow-must-be-va
gh run list --repo <owner>/<repo> --workflow=322473622 --limit 5 \
  --json databaseId,headBranch,headSha,event,conclusion,createdAt
```

Expected after-state: **no new `release.yml` run at all** for that push. The workflow only
triggers on `v*` tag pushes and `workflow_dispatch`, so a valid file produces no run for a branch
push, while the invalid one produced a zero-job failure for every branch push (13 of them in §1).
The before/after pair is therefore "zero-job failure for a branch push, then no run for a branch
push" — with the `13:37:36Z` run `34976208051` as the immediately preceding datum. Any new
zero-job run would falsify this unit's fix; none has been claimed here.

Until that capture exists, the repair is **proven locally** (GitHub's own context rules, §2;
structural delta, §3; gate logic, §4; repository gates, §5) but **not yet proven accepted by
GitHub**. The reviewing lane can settle it with the two commands above.

## 8. Interaction the owner needs to know (card item 5)

The workflow's tag validation asserts
`refs/tags/$RELEASE_TAG^{commit} == refs/remotes/origin/main`. Measured today, that equality holds
exactly (`748aa24` both sides, §4), which is why a `workflow_dispatch` reconcile of
`v1.0.0-rc.1` would still pass. **Once this correction is merged to `main`, `main` advances past
`748aa24` and that assertion can no longer hold**, so the already-published tag cannot be
reconciled through this workflow any more.

That is acceptable and is recorded rather than worked around: the prerelease is published and
independently verified, and the contract's AC-12 requires that the tag not be rewritten. Fixing
this interaction would mean changing the workflow's identity assertion — a redesign, explicitly
outside this unit's mandate ("This is a context-placement repair, not a workflow redesign").

## 9. Not claimed by this record

- No push, no workflow run, no CI result, no tag, no release, no publication (see §7).
- No aggregate `release_impact` / `release_action` / `release_channel` conclusion (Supervisor-owned).
- No claim that a future tag push publishes successfully end to end: the fix removes the only
  workflow-file rejection measured here; the build/upload legs still depend on the fork revision
  pinned in `FORK_COMMIT` being servable by the remote, which is the integration lane's obligation.
- No claim about `main`'s state after the merge, about stable `1.0.0`, PyPI or WSL2.
- No full-suite bootstrap result (§5), and no independent review: this is the unit's own evidence.

## 10. Review addendum — the empirical proof in §7, completed by the publication lane

*Added by the Supervisor review run (run 101) that reviewed this unit. §1–§9 above are the
implementing lane's record and are unaltered; this section reports the verification that lane
could not perform under its publication boundary.*

### 10.1 The push, and its observation

The reviewed commit was pushed on its own branch and the run list read back before and after.

| | Value |
| --- | --- |
| Branch | `aether-agents-2/t_5cd52e79-lc-fix-relwf-release-workflow-must-be-va` |
| Commit | `304c469387752b426088d7244d317dbed78b865f` |
| Workflow observed | `322473622` (`.github/workflows/release.yml`) |
| Before | `total_count = 19`; 15 failures, **all zero-job**; newest datum `34979146475` (`push`, `main`, `f8e88467`, 14:04:14Z) |
| Immediately preceding branch push | `34976915020` (`push`, `aether-agents-2/lc-int-evidence-completion`, 13:44:01Z) — **created a zero-job run** |
| After | `total_count = 19` — **unchanged**; runs for commit `304c469…`: **0**; no new run of any kind |

Re-read after a further 150 s: still `total_count = 19`, still 0 runs for the commit, newest run
still `34979146475`. Scheduling lag is therefore excluded rather than assumed away.

A second push on the same branch (`ae7e2a5c6…`, this addendum's own commit) replicated the result
independently: `total_count` remained 19, and runs for that commit were 0. Two separate pushes
carrying the fixed file therefore produced no `release.yml` run at all, which also shows the first
reading was not a one-off timing artifact.

The pair is discriminating because both sides are the **same event type on the same workflow**: a
push to a non-default branch carrying the invalid file produced a zero-job run (two independent
observations, `34976208051` at 13:37:36Z and `34976915020` at 13:44:01Z), while the same push
carrying the fixed file produced no run at all — which is what a valid file with a
tag-only trigger must do.

### 10.2 Why "no run" is not merely "nothing happened"

`policy.yml` triggers only on `push` to `main` and `pull_request` targeting `main` (verified from
the file: `on: push: branches: [main]` / `on: pull_request: branches: [main]`), so a feature-branch
push is *expected* to start nothing. That removes an easy misreading in both directions: the
absence of a `policy.yml` run here is not evidence either way, and the absence of a `release.yml`
run is the whole test. Confirmation that the push was processed, on the same event, follows from
the merge state in §10.4.

Byte-level and rule-level checks by the reviewing lane, independent of the implementing lane's
tooling choices: `actionlint` **1.7.7** (a different build than the 1.7.12 used in §2) reports the
identical single finding on the pre-change file — `release.yml:37:31: context "runner" is not
allowed here. available contexts are "github", "inputs", "matrix", "needs", "secrets", "strategy",
"vars"` — and `rc=0` on the fixed file; `policy.yml` is `rc=0` under the same binary; and reverting
the fixed file to job level reproduces the pre-change bytes exactly and the same error at the same
position. Per-step/per-key comparison from the reviewer's own model: triggers, permissions,
workflow-level `env`, `runs-on`, job set and step count all identical; job env keys
`['GH_TOKEN','RELEASE_BUNDLE_DIR','RELEASE_TAG'] → ['GH_TOKEN','RELEASE_TAG']`; exactly two
step-level deltas, both the relocated key; all seven steps identical in name, `uses`, `with`,
`shell` and `run`-body digest. The two readers of the variable (`--out "$RELEASE_BUNDLE_DIR"`,
`bundle_dir="${RELEASE_BUNDLE_DIR:-}"`) are exactly the two steps that now declare it.

### 10.3 The validation logic, re-executed

The shipped `Validate release tag` body was extracted from the fixed workflow and executed against
a controlled origin. With `origin/main` equal to the tag commit: `rc=0`,
`GITHUB_OUTPUT: version=1.0.0rc1` / `prerelease=true`. Negative controls: `RELEASE_TAG=v1.0.0` →
`rc=1` (version mismatch); `RELEASE_TAG=nonsense` → `rc=1` (`Unsupported release tag: nonsense`).

### 10.4 The interaction in §8, demonstrated

Re-running the same body with `origin/main` advanced to the post-merge commit
`f8e88467c0441280e3ab49b247c6cfd7039db12a` fails (`rc=1`) on the
`refs/tags/X^{commit} == refs/remotes/origin/main` assertion. The §8 consequence is therefore
measured, not predicted: once this correction lands, `workflow_dispatch` can no longer reconcile
`v1.0.0-rc.1`, and the already-published release must not be deleted, moved or rewritten to restore
that path.

### 10.5 What this addendum does not claim

It does not re-open §9's non-claims. Specifically: the fix is proven accepted by GitHub's workflow
parser for the branch that carries it, and the merge-push observation on `main` is recorded
alongside this unit (issue #445 and the task ledger) rather than in this file, because it could only
be made after the merge. No release, tag, asset, `VERSION` or other workflow was touched, and the
published `v1.0.0-rc.1` artifacts remain exactly as verified by the integration lane.
