# LC-FORK — maintained-fork candidate for the RC

**Unit:** LC-FORK (implementer), card `t_926a1913`.
**Authority:** Objective Contract `oc_3397f9f05d780f8e@v1`
(SHA-256 `4d4c7650bf8ea93fc7cffe3d87f7f974e172d66cefcf6a74a2d83051568a4879`) on
Aether base `410c172ae69ffa87f6e32960ae4aef3b8d6598f0`, plus the Supervisor
breakdown at `specs/001-aether-v1-productization/tasks.md` (commit
`61124bc1dea787fbc5408fcc7f7b4f654f342e78`) and its shared decisions 4, 10, 11,
14 and 15. No canonical artifact was edited.

**Result:** one reviewable maintained-fork branch carrying every recorded active
HLP behavior as source, with fork documentation and the Hermes distribution
identity reconciled. HLP-420 is the single entry whose source does not exist on
the fork; the flow controller confirmed the measurement and moved that coverage
to unit **LC-PORT420** (see §7). Everything below is measured at the revision it
names; no publication, merge, tag, service action or live-state change was made.

## 1. Starting point and receipt

| Check | Observed |
| --- | --- |
| Fork resolved by remote URL | `origin` = `https://github.com/DarkArty07/aether-hermes` (branch `aether-main`), provisioned checkout clean before and after this unit |
| Provisioned revision | `54eeb56dabefc98821d696656ed58c55dd777346`, three commits ahead of `origin/aether-main` `bb5e9a422f3135371557e75bcd1db01c5f8fc3ba`; no push and no PR existing |
| Isolation | nested worktree `<fork-root>/.worktrees/lc-fork` on new branch `fix/425-review-flow-continuity`, created from that checkout at `54eeb56dab` |
| `aether-main` preserved | the checkout whose branch is `aether-main` was never checked out, staged or committed: `rev-parse aether-main` = `54eeb56dab…` and `status --porcelain` empty at the end of the unit |
| Aether side | this unit's Aether worktree at `410c172…`; the only Aether file written is this record |
| Live runtime / editable state | read-only inspection only; no file copied, edited or pointed at the candidate, and no service action |

## 2. Candidate organization (local judgement)

The provisioned checkout carried three commits over the remote base:

| Commit | Subject |
| --- | --- |
| `10a307bb22cf07dab5025120eee2eacb1424f8ca` | `fix(kanban): preserve supervisor review session continuity` |
| `c007cea73f3cfc7106dbdffa95598e0324934a32` | `fix(review): fail closed on damaged Aether flow identity` |
| `54eeb56dabefc98821d696656ed58c55dd777346` | `merge(review): adopt supervisor review-flow continuity` |

Measured: `git diff c007cea73f 54eeb56dab` is empty and both trees are
`8d50484dccba2c075091fec3e0d84087537d2d87`, so the third commit is a content
no-op that only records the adoption of the branch into the local
`aether-main`.

Decision: keep both reviewed content commits byte-for-byte, keep the no-op merge
(it is the current local `aether-main` tip, and dropping it would make the
branch non-fast-forwardable into that tip), and add exactly one documentation
commit. Nothing was amended, reordered, squashed or force-pushed, and no commit
was authored on top of a rewritten parent.

| Identity | Value |
| --- | --- |
| Branch | `fix/425-review-flow-continuity` |
| Candidate tip (new commit) | `387705ea1dd76f43585fca220b11859173cc4a6b` — `docs(fork): record HLP-425 review-flow continuity for the RC` |
| Branch base | `bb5e9a422f3135371557e75bcd1db01c5f8fc3ba` |
| Branch delta | 11 files, +2157 / -104 (ten source/test files from the two behavior commits, plus `AETHER_FORK.md`) |
| Pinned-revision relation | `54eeb56dab` (the revision shared decision 4 names) remains an unmodified ancestor; `git diff --stat 54eeb56dab..387705ea1` is `AETHER_FORK.md` only, so every source file is byte-identical to the pinned revision |

The distribution identity decision required by the contract is a *no-correction*
result: `hermes-agent` `0.20.1` is declared identically by `pyproject.toml`
(`[project].name` / `[project].version`, line 4–5), `hermes_cli/__init__.py:17`
(`__version__`) and the editable package entry in `uv.lock:1571–1573`, and both
`pyproject.toml` and `uv.lock` are byte-identical to the fork base. No packaging
metadata was changed, so there is nothing to reverse and no lock/version surface
is affected.

Documentation added by the tip commit (`AETHER_FORK.md`, +65 lines):

- a `## Supervisor same-card review-flow continuity for the RC (Aether #425/#426)`
  section naming the two behavior commits, their functions, the behavior, the
  local evidence, rollback and the upstream retirement gate;
- a `## Distribution identity and release binding` section recording the
  `hermes-agent` `0.20.1` surfaces and the fact that the repository carries
  inherited upstream `v2026.*` tags as objects but that none of them is an
  ancestor of `aether-main` (37 tags in the object store, `git tag --merged
  aether-main` = 0), so a candidate's identity is its commit, tree and file-byte
  projection rather than a tag.

## 3. No `.patch` replay

| Check | Command | Result |
| --- | --- | --- |
| Tracked patch files in the candidate tree | `git ls-files \| grep -cE '\.(patch\|diff)$'` | `0` |
| `patches/` tree present | `git ls-files \| grep -E '^patches/'` | no match |
| What the branch actually changes | `git diff --name-status bb5e9a42..387705ea1` | six Python source files, four Python test files, one Markdown file |
| `patches/hermes/**` usage | — | no file read as an apply source, none applied, copied or referenced by the candidate |

## 4. Verification (raw results)

Environment: the worktree's own `uv` environment
(`uv sync --locked --python 3.11 --extra all --extra dev`, 28 s), so the editable
pointer, `python -m pytest` subprocesses and the console scripts all resolve to
the candidate tree. Resolved-import check from outside the worktree:
`hermes_cli.__file__` → `<worktree>/hermes_cli/__init__.py`,
`agent.runtime_cwd.__file__` → `<worktree>/agent/runtime_cwd.py`. Tests ran with
a disposable empty `HOME` (empty `~/.hermes`); the canonical runner launches a
hermetic `env -i` and does not forward `HERMES_HOME`, so profile paths resolve
under that sterile `HOME`. `HERMES_TEST_FILE_RETRIES=0`.

| Check | Command | Observed |
| --- | --- | --- |
| Affected-surface suite (canonical runner) | `scripts/run_tests.sh` over 19 review/session/collaboration/review-lifecycle/Runtime test files | **399 passed, 0 failed, 1 skipped**, 100 % complete, 15.9 s runner wall (24 workers), `EXIT=0`; the skip is the Windows-only case the runner reports as running on the `tests-os` lane |
| Complete suite (canonical runner) | `scripts/run_tests.sh` (full discovery) | see §4.1 |
| Blocking lint (fork gate) | `ruff check .` | candidate `exit 0` — `All checks passed!`; the same command at base `bb5e9a42` also `exit 0`, so no diagnostic is introduced or removed |
| Advisory ruff diff | `ruff check --output-format=json .` at head and base | head `0` diagnostics, base `0` diagnostics — no new diagnostics |
| Format check | `ruff format --check` | `9 files would be reformatted, 1 file already formatted` for the ten changed files **both** at the candidate and at its base; repository-wide `4124 files would be reformatted, 1703 files already formatted`. Pre-existing drift; no file changes format-check status |
| Format delta inside candidate-written regions | `ruff format --diff` original-side lines ∩ added lines of `git diff -U0 bb5e9a42..54eeb56dab` | 93 lines, concentrated in `hermes_cli/kanban_db.py` (29) and `tests/hermes_cli/test_kanban_session_affinity.py` (60). Recorded as residual (§9); the fork's recorded practice is to preserve existing drift instead of reformatting files that carry thousands of drifted lines, and the blocking gate is `ruff check .` per `.github/workflows/lint.yml` |
| Whitespace/diff hygiene | `git diff --check bb5e9a42..387705ea1`; `git diff --check` (working tree) | both clean, `exit 0` |
| Frontend/JS surfaces | `git diff --name-only bb5e9a42..54eeb56dab` filtered for `*.js/jsx/ts/tsx/mjs/json/css/scss/html` | no match — no runtime asset or JS/TS surface changed, so no npm build or JS test run is required by the card |
| Tree state | `git status --porcelain=v1` | empty (clean); the runner's `test_durations.json` is gitignored (`.gitignore:39`) |

### 4.1 Complete canonical suite

| Run | Command | Observed |
| --- | --- | --- |
| Candidate `387705ea1`, run 1 | `scripts/run_tests.sh` (full discovery, sterile `HOME`, `HERMES_TEST_FILE_RETRIES=0`) | **3007 files, 33365 tests passed, 97 failed, 296 skipped**, 100 % complete, 639.6 s runner wall (24 workers), `EXIT=1`; 24 files carry the failures plus one file with a collection/import error (`tests/agent/test_model_metadata.py`, 300 s per-file timeout) |
| Candidate `387705ea1`, run 2 (identical revision) | same command | **3007 files, 33352 tests passed, 94 failed, 296 skipped**, 100 % complete, 845.6 s runner wall (24 workers), `EXIT=1`; same collection-error file |
| Base `bb5e9a42`, unchanged tree | same command in a detached worktree of the same checkout | **3007 files, 33322 tests passed, 91 failed, 296 skipped**, 100 % complete, 555.2 s runner wall (24 workers), `EXIT=1`; 22 failing files plus the same collection-error file |

Attribution of the 97/94/91 spread: two runs of the byte-identical candidate
revision differ by 3 failures and by 206 s of wall time, and the candidate-versus-base
delta is 6 failures (run 1) and 3 (run 2) — the same order as the run-to-run
variance. The six tests that failed only in run 1 (five in
`tests/agent/test_bedrock_adapter.py`, one in `tests/gateway/test_turn_lease.py`)
passed **78 passed, 0 failed** when those two modules were re-run alone at the
candidate, and neither module is in the changed set. The failing class is
optional-provider/plugin and installer code whose failures are environment-driven
under the parallel runner (`ImportError: Feature 'search.parallel' unavailable:
lazy installs disabled`, missing Daytona/Modal/Fal/Hindsight extras, gateway
lifecycle probes); no file this candidate changes, and none of the four test
modules it touches, appears in any failing set.

Attachments for this section, so the numbers above are re-fetchable rather than
quoted: `LC-FORK-complete-suite-candidate-387705ea1.txt` (run 1; 14 093 bytes, sha256
`85f1a8b544cd608a7f2477617ccf04e3925dcebcd07e311d3c14ed36ee8ec202`),
`LC-FORK-complete-suite-base-control-bb5e9a422f.txt` (base control; 13 279 bytes,
sha256 `9683b19adb673607da8d106e7cf479eba96226011d2611bc7952efb52c88c559`; it also
carries a two-line identification header) and
`LC-FORK-complete-suite-candidate-387705ea1-run2-summary.txt.gz` (run 2; 3 027 bytes
gzipped, sha256 `9468fa8e0d768dfb16cf1a959c16b02262268b7dd800c2d20a3f38b5990d1cae`;
uncompressed 13 849 bytes, sha256
`03b7a027eb3130bd92047ad8973aa0350caae7a9c8a21a2bafc3aaaa7fcd850e`). Each attachment
is the runner's preamble, its `=== Summary:` block, its deduplicated `FAILED` line list
and its file-level failure sections, with the per-test traceback detail elided; the raw
runner output (~1.0–1.1 MB per run) is not attached, because the session scratch copy is
not durable — re-running the command in this section re-creates it. The run-2 digest is
reproducible by the rule recorded in §12, which was validated by reproducing the run-1
digest byte-exactly (the derived file's sha256 equals the run-1 attachment's).

## 5. Per-HLP attribution at the candidate revision

Method (all mechanical, re-runnable): for each of the 29 detailed reconciliation
records in
`specs/001-aether-v1-productization/evidence/hermes-patch-reconciliation/entries/*.json`
(the set the Aether validator derives from the ledger's level-two sections),

1. every recorded component path was materialized from the candidate tree
   (presence, byte size and SHA-256);
2. every 40-hex revision the ledger records for that entry was tested for
   ancestry with `git merge-base --is-ancestor <rev> 387705ea1…`, and for the
   entries that name fork commits the files those commits touch were listed;
3. one behaviour anchor per entry was verified by literal search in the named
   file and its line number recorded.

Result: **28 of 29 records fully attributed** — every component present and every
behaviour anchor found at the candidate revision. `HLP-420` is the single
exception and is owned by LC-PORT420 (§7). Revisions that are not ancestors are
external references (upstream `NousResearch/hermes-agent` inspection revisions
and Aether commits); no fork revision recorded in the ledger is missing from the
candidate's ancestry.

| HLP | Recorded status | Components present | Recorded fork revisions that are ancestors | Behaviour anchor |
| --- | --- | --- | --- | --- |
| HLP-188 | ACTIVE_LOCAL / UPSTREAM_OPEN | 2/2 | — (pre-fork baseline) | `hermes_cli/kanban_db.py:6463` `def _has_sticky_block`; `tests/hermes_cli/test_kanban_blocked_sticky.py` |
| HLP-189 | ACTIVE_LOCAL / UPSTREAM_OPEN | 2/2 | — | `tools/kanban_tools.py:1626` `max_retries` |
| HLP-191 | ACTIVE_LOCAL / UPSTREAM_OPEN | 7/7 | — | `hermes_cli/kanban.py:665` `--recover-escalated`; `hermes_cli/kanban_db.py:6299` `triage_escalation_recovered` |
| HLP-194 | ACTIVE_LOCAL / UPSTREAM_OPEN | 8/8 | — | `hermes_cli/kanban_exit_codes.py:12` `KANBAN_PROTOCOL_EXIT_CODE`; `agent/kanban_stop.py:391` `def evaluate_kanban_stop` |
| HLP-198 | ACTIVE_LOCAL / UPSTREAM_OPEN | 2/2 | — | `hermes_cli/kanban_db.py:13231` `env["HERMES_KANBAN_BRANCH"]` |
| HLP-204 | ACTIVE_LOCAL / UPSTREAM_OPEN | 8/8 | — | `hermes_cli/config_defaults.py:2490` `max_in_progress_per_profile` |
| HLP-209 | ACTIVE_LOCAL / UPSTREAM_VERIFIED | 2/2 | — | `cron/lifecycle_guard.py:448` `stat.S_ISDIR(metadata.st_mode)` |
| HLP-211 | ACTIVE_LOCAL_E2E_QUALIFIED | ledger files | — | `hermes_cli/kanban_affinity.py:39` `def normalize_session_affinity`; `hermes_cli/kanban_db.py:6779` `def _wake_terminal_flow_controller`; `VALID_ORIGIN_SIGNALS` |
| HLP-226 | ACTIVE_LOCAL + 226b; 226c fork-only | ledger files | 6 fork commits | `tools/kanban_tools.py:1618` `project_source_task_id`; `hermes_cli/kanban_db.py:3949` `def _project_from_board_binding` |
| HLP-246 | ACTIVE_LOCAL | ledger files | — | `tools/kanban_tools.py:1326` `expected_sha256` |
| HLP-247 | ACTIVE_LOCAL | ledger files | — | `hermes_cli/kanban_db.py:6530` `def recompute_ready` |
| HLP-262 | ACTIVE_LOCAL / UPSTREAM_MISSING | 2/2 | — | `hermes_cli/kanban_db.py:6463` `_has_sticky_block` treats `origin_signal` as sticky |
| HLP-275 | ACTIVE_LOCAL / UPSTREAM_PARTIAL | 2/2 | 1 | `tools/vision_tools.py:637` `_EMBED_TARGET_BYTES` (proactive cap) |
| HLP-280 | ACTIVE_LOCAL_E2E_QUALIFIED | 1/1 | — | `hermes_cli/kanban_db.py:6689` bounded unresolved-attention recovery |
| HLP-305 | fork holder + live FTS | 3/3 | 11 | `run_agent.py:8650` `classify_persistence_error`; FTS holder files |
| HLP-310 | ACTIVE_LOCAL / UPSTREAM_MISSING | 3/3 | 3 | `tools/environments/base.py:576` unsets `${!HERMES_KANBAN_*}` / `HERMES_DELEGATED_CHILD_CONTEXT` |
| HLP-334 | ACTIVE_LOCAL / UPSTREAM_MISSING | 8/8 | 4 | `hermes_cli/kanban_db.py:2199` `CREATE TABLE … kanban_collaboration` |
| HLP-335 | ACTIVE_LOCAL | 1/1 | — | `hermes_cli/kanban_db.py:11873` `["gh", "pr", "view", pr_url, "--json", "state"]` behind `_RESPAWN_GUARD_PR_WINDOW` |
| HLP-354 | ACTIVE_LOCAL / UPSTREAM_MISSING | 2/2 | 2 | `hermes_cli/kanban_db.py:10114` `def _resolve_worktree_base_ref` |
| HLP-362 | ACTIVE_LOCAL / UPSTREAM_MISSING | 3/3 | 3 | `hermes_cli/kanban_db.py:8956` “an initial review requires an explicit independent reviewer” |
| HLP-369 | ACTIVE_LOCAL / UPSTREAM_MISSING | 8/8 | 9 | `hermes_cli/goals.py:1108` `phase == "review_readiness"` |
| HLP-372 | ACTIVE_LOCAL / UPSTREAM_MISSING | 6/6 | 3 | `cron/script_root.py:45` `def resolve_cron_script_path` |
| HLP-382 | ACTIVE_LOCAL / UPSTREAM_MISSING | 2/2 | 1 | `hermes_state.py:84` `from hermes_state_compaction import`; `hermes_state_compaction.py:211` `def _publication_marker_key` |
| HLP-385 | ACTIVE_LOCAL / UPSTREAM_MISSING | 2/2 | 2 | `agent/prompt_builder.py:263` “distinct review/QA phase child” guidance |
| HLP-388 | ACTIVE_LOCAL / UPSTREAM_MISSING | 1/1 | 2 | `run_agent.py:69` `def _launch_cwd_for_session` |
| HLP-389 | ACTIVE_LOCAL / UPSTREAM_MISSING | 2/2 | 1 | `cron/lifecycle_guard.py:46` `from tools.shell_heredoc import strip_inert_heredoc_bodies` |
| HLP-393 | ACTIVE_LOCAL / UPSTREAM_MISSING | 6/6 | 3 | `cron/jobs.py:1651` `def _normalize_notification_origin` |
| HLP-420 | ACTIVE_LOCAL / UPSTREAM_MISSING | **1/2** | 1 | **not present at any fork revision — owned by LC-PORT420 (§7)** |
| HLP-425 | ACTIVE_LOCAL / UPSTREAM_MISSING | 9/9 | 2 | `hermes_cli/kanban_db.py:1323` `def _review_flow_session_context`; `agent/runtime_cwd.py:76` `def resolve_session_identity_cwd` |

Ledger records that the reconciliation set carries at level three rather than as
detailed sections were checked the same way (recorded fork revision is an
ancestor, every named file exists): `HLP-313`, `HLP-353`, `B292`, `B294`,
`B295`, `B301`, `B304`, `ABR-315`, `ABR-META`, `ABR-AUX`, `HLP-334` fork
commits, the HLP-305 maintained-fork holder files and the HLP-226b files — 13 of
13 verified, 0 requiring attention.

The machine-readable attribution — per-entry component presence, byte size and
SHA-256, recorded-commit ancestry results and anchor line numbers — is attached as
`LC-FORK-attribution-387705ea1.json.gz` (7 886 bytes, sha256
`11d9006830c11287ea350ad85e33ee80d856203a67294a3d75eedf579817ede1`, produced with
`gzip -9 -n` so the archive itself is reproducible; uncompressed 50 982 bytes, sha256
`51913566efd655b454898074efd0076123b23281f3e253d4be1c553caa8107d9`). It names
`candidate_revision = 387705ea1dd76f43585fca220b11859173cc4a6b` and
`candidate_tree_object = ead7e6c3c4a55ce2cc997fd705f1c0fe17c4455d`, so the report is
run against the exact candidate revision rather than against the pinned source
revision. Its `entries` map is byte-identical to the same report computed at the
contract-named source revision `54eeb56dab` (the tip's parent, §6) — verified by
comparing the two JSON documents, whose only differences are `candidate_revision` and
the candidate tree object — so no component, ancestry or anchor result depends on
which of those two revisions the report is run against.

## 6. Tree-digest inputs for the Aether release lock

`hermes.source_mode=maintained_fork` binds this fork by repository and exact
commit. Inputs measured at the candidate tip:

| Input | Value |
| --- | --- |
| `hermes.repository` | `https://github.com/DarkArty07/aether-hermes` (branch `aether-main`) |
| `hermes.commit` | `387705ea1dd76f43585fca220b11859173cc4a6b` |
| Git tree object | `ead7e6c3c4a55ce2cc997fd705f1c0fe17c4455d` |
| Deterministic path-and-file-byte projection | `1350dacfff5e6b4da68d1d593da7356a855f84a30c428570ac88ca38a237a46e` over 9375 regular files, encoding `sha256(json.dumps(sorted[(path, sha256(blob bytes))], separators=(",", ":"), ensure_ascii=True))`; no symlink or submodule entry exists in the tree |
| Source revision named by the contract | `54eeb56dabefc98821d696656ed58c55dd777346`; tree `8d50484dccba2c075091fec3e0d84087537d2d87`; projection `fb9284a9ce0ee4430a33951d3fe3a7cbffa77027346ade738d1399a9e1fb1bee`; identical sources to the tip apart from `AETHER_FORK.md` |
| `hermes.version` | `0.20.1` (three consistent surfaces, §2) |
| `hermes.python_requires` | `>=3.11,<3.14` |
| Fork base for comparison | `bb5e9a422f3135371557e75bcd1db01c5f8fc3ba`; tree `a2b2f3e9713c039bdc093241d8020f851ff093f4`; projection `d2233c45e4c91b232f19a5c1ee8b23fe75a26c1c5cc92d017a94155b554e46c8` |
| `hermes.tag` | **no tag exists on the fork at the candidate revision** — 37 inherited upstream tags are present as objects and none is an ancestor of `aether-main`. The lock field needs an explicit decision by LC-RUNTIME/LC-INT (for example binding the fork's distribution version without a tag, or an annotated tag created at publication). Recorded as residual risk, not decided here |

The projection is reported as an input, computed with the documented
path-and-file-byte encoding; the authoritative value remains LC-RUNTIME's, and
the encoding is reproducible from the commit alone (no working tree, no
platform-bound metadata).

Every projection value in the table is a **blob-based** projection of the fork tree
(rows are `(path, sha256(blob bytes))` in global path order). These values are fork
evidence, and they are **not** the release lock's `hermes.source_tree_sha256`: that field
is re-derived by the shipping validator, so its canonical encoding is
`src/aether_agents/lifecycle.py::_tree_sha256` over the *materialized* (git-archive
extracted) source — `sha256(json.dumps(rows, separators=(",", ":"), ensure_ascii=True))`
with rows in `os.walk` DFS order and per-level sorted names. Measured here so the two
encodings are not read as contradicting figures: at `387705ea1d` the materialized digest
is `fb3e5336a0106ad96ccac88345f23880a9f2597235f023aab246add4a2498337`, produced by
calling that validator function on the `git archive` extraction of the candidate (9 375
regular files, zero symlinks), which reproduces the vector recorded in shared decision 19
of `specs/001-aether-v1-productization/tasks.md` (commit `4cb3235`). The cause is
mechanical and re-measured here: `.gitattributes` gives the nine `*.ps1` files
`text: set` / `eol: crlf`, and exactly those nine files differ between blob bytes (LF)
and materialized bytes (CRLF) — the other 9 366 files are byte-identical. Row order
matters as well: the same materialized tree under a global path sort digests to
`c6088578…` rather than to the DFS value. LC-RUNTIME/LC-INT own the lock value; nothing
in this table is it.

## 7. HLP-420 (collaboration request 2 / peer response 3) — owned by LC-PORT420

Measured at `54eeb56dab` before any change: `agent/auxiliary_client.py` contains
0 occurrences of `AuxiliaryResponsesTerminalError` and 0 of
`incomplete_details`; `tests/agent/test_auxiliary_client_responses_terminal_420.py`
does not exist; `git log --all -S 'AuxiliaryResponsesTerminalError'` finds no
fork commit or branch. The behavior exists only as
`patches/hermes/HLP-420-responses-terminal-fidelity.patch` and in the Aether-side
live editable/runtime source (read-only inspection: 2 occurrences of the symbol).

Material question raised through the card's collaboration path
(`recipient: controller`, request id 2). The flow controller independently
re-measured the same absence, sized it as a single entry (28 of 29 present) and
responded (message 3) that coverage moves to a dedicated root-gated unit
**LC-PORT420**, which exclusively owns the port and both files. My boundary was
updated accordingly: no HLP-420 coverage is claimed here, no
`patches/hermes/**` file is applied, and neither `agent/auxiliary_client.py` nor
the 420 test module was touched. This record marks the entry as owned by
LC-PORT420 instead of as coverage this unit holds; the disposition is recorded
as `applied` on request 2.

## 8. Merge expectation

| Check | Observed |
| --- | --- |
| Fast-forwardable from local `aether-main` | `git merge-base --is-ancestor aether-main fix/425-review-flow-continuity` → true |
| Fast-forwardable from the remote base | `git merge-base --is-ancestor origin/aether-main fix/425-review-flow-continuity` → true; `git rev-list --count origin/aether-main..fix/425-review-flow-continuity` = 4 |
| Real merge rehearsal | in a throwaway local clone of the fork, `git merge --ff-only origin/fix/425-review-flow-continuity` reported `Fast-forward` with exit 0 and moved `aether-main` to `387705ea1`, after which the working tree was discarded |
| History rewrite | none: the two behavior commits and the adoption merge are unchanged; only one new commit was added on top. This unit performed no push, PR, tag or merge in the maintained fork (the ff-only rehearsal above ran in a throwaway clone, not in the provisioned repository), and the candidate branch is unpublished |
| Expectation for LC-INT | normal PR from `fix/425-review-flow-continuity` into `aether-main`, green required checks, no bypass; this branch is the fork half that LC-INT integrates together with LC-PORT420's branch |

## 9. Preservation, non-effects and residual risk

Preserved (verified, not assumed): the `aether-main` checkout (branch, tip and
clean status unchanged), the live runtime and installed editable state (read-only
inspection only; no copy, edit, re-point or restart), the owner's primary Aether
checkout, unrelated worktrees/branches/stashes and unrelated services. No
credential, provider, model or router configuration was read, written or
referenced. No machine path, operator identity or live-state value appears in the
fork commit messages, the fork documentation or this record.

Residual risk and limits:

1. **HLP-420 is not carried by this branch** — a separate unit owns it (§7).
   Until it lands, the fork candidate does not by itself satisfy D6's "every
   accepted active HLP behavior".
2. **`hermes.tag` has no value at the candidate revision** (§6). This is a lock
   input, not something this unit may create (tagging is publication).
3. **Format drift**: 93 lines inside candidate-written regions would be rewritten
   by `ruff format`, in files whose pre-existing drift is far larger, and the
   format check fails identically at the base. No file's format-check status
   changes, and the fork's blocking lint gate (`ruff check .`) passes. Not
   corrected, to avoid a drive-by reformat.
4. **Complete-suite failures** (§4.1) are environmental in character; the fork's
   recorded baseline has the same class. They are reported as measured and not
   attributed to the candidate unless they fall in changed files.
5. **CI is NOT RUN**: the fork's inherited GitHub Actions remain disabled, so
   these are local qualification results, not a claimed remote CI pass. No
   compatibility or release conclusion is drawn here beyond this unit.
6. Attribution is source-level (files, anchors, ancestry) plus the affected-suite
   run; it is not an independent behavioural re-verification of every HLP entry,
   which remains the reviewer's and the reconciliation generator's lane.

## 10. Requirement coverage

| Obligation | Where satisfied |
| --- | --- |
| In-scope 8 / AC-01 (fork half): clean exact fork input, normal branch/PR path without history rewrite, fork identity `DarkArty07/aether-hermes:aether-main` | §1, §2, §8 |
| AC-02 (fork half) / D6: every detailed active HLP record attributable at the selected fork revision; fork docs/tests updated; no `.patch` replayed | §3, §5 (28/29 fully attributed; HLP-420 owned by LC-PORT420), §2 documentation |
| Shared decision 4 (maintained-fork identity; `hermes-agent` 0.20.1) | §2, §6 |
| Shared decision 10 (one evidence record; larger logs as task attachments) | this file plus the card's attachments: the focused-suite log and the three complete-suite digests (§4.1) and the machine-readable attribution (§5) |
| Shared decision 11 (fork test standard; no skip added or weakened) | §4 (focused first, then the complete suite; the single skip is the runner's Windows-only case) |
| Shared decision 14 (policy manifest) | the only Aether file added is under `specs/`, so no `.github/workflows/policy.yml` line is required |
| Shared decision 15 (stop expanding a defective unit; report instead) | §7 — reported with measured evidence instead of widening scope |
| Compatibility (unit level) | this unit changes one maintained fork only, keeping `hermes-agent` 0.20.1 identity and adding no dependency; fork source identity stays `DarkArty07/aether-hermes:aether-main`. No aggregate release conclusion is made here |

## 11. HLP-310 / AC-03 recurrence — classification requested during implementation

A peer message received during this unit asked LC-FORK to classify an observed
recurrence: in the live Morfeo TUI a parent terminal inherited
`HERMES_DELEGATED_CHILD_CONTEXT=1` after a real five-child delegated batch, which
would contradict the HLP-310 promise if it came from this candidate's source.

Measured at the points that decide the question:

| Question | Measurement |
| --- | --- |
| Candidate carries HLP-310 | yes: `tools/environments/base.py:533` (snapshot exclusion regex), `:576` (`unset ${!HERMES_SESSION_*} ${!HERMES_CRON_AUTO_DELIVER_*} ${!HERMES_KANBAN_*}`), `:585` (`AI_AGENT HERMES_AGENT HERMES_DELEGATED_CHILD_CONTEXT …` evaluated before `export -p`); the marker itself is wired by `agent/delegation_context.py:35,129,138` |
| Candidate focused regressions | `scripts/run_tests.sh tests/tools/test_snapshot_session_id_leak.py tests/tools/test_delegate_kanban_isolation.py` → **12 passed, 0 failed** (exit 0), including `test_snapshot_dump_excludes_delegated_and_kanban_vars` (real bash dump through `_export_dump_excluding_session_vars`) and `test_delegated_child_terminal_snapshot_does_not_leak_to_parent` |
| Effective runtime carries HLP-310 | no: in both the active release source (`runtime/current/src/hermes-agent/tools/environments/base.py`, read-only) and the live editable tree, `HERMES_DELEGATED_CHILD_CONTEXT` has **0 occurrences** and the snapshot prelude is the pre-HLP-310 `"AI_AGENT HERMES_AGENT "` at `:582` — no marker exclusion and no `${!HERMES_KANBAN_*}` unset |

Classification: the observed recurrence is consistent with the effective runtime
carrying no HLP-310 exclusion at all — the ledger's own HLP-310 record states
"Activation: not part of this delivery. Live runtime remains unmodified" — and it
does not by itself evidence a gap in the maintained-fork source. This unit
therefore adds and changes no HLP-310 source and did not touch the live runtime,
whose adoption belongs to the RC activation lane.

Still outstanding, and outside this unit's writable surface: a real
parent→child→parent fresh-process canary on the effective runtime after RC
activation (LC-CLOSE's real lane), and optionally the same canary against the
candidate revision inside a disposable harness (a bounded test-only unit). Both
were offered to the flow controller together with these measurements; creating that
unit is decomposition, not a local implementation choice, so LC-FORK did not create
it on its own authority.

## 12. Review return disposition and the run-digest rule

The Supervisor review of this record (review run 19; comment 36) independently
reproduced the candidate revision and its fast-forwardability, the absence of patch
replay, the distribution identity, the four HLP-425 behaviour anchors, the 19-file
focused suite (`399 passed / 0 failed / 1 skipped`), the lint and format status, the tree
object and the deterministic projection, and returned one bounded correction: two
sentences claimed attachments that had not been delivered — the machine-readable
attribution (§5) and the run-2 summary (§4.1). Disposition of that return:

1. §5 now names `LC-FORK-attribution-387705ea1.json.gz` with both hashes, and the report
   was recomputed at the exact candidate revision instead of the pinned source revision;
   the two reports' `entries` maps are byte-identical (§5).
2. §4.1 now names all three run digests, says which is rule-derived and states what is
   not attached.
3. The run-2 digest was derived from the raw run-2 log by this rule:
   1. the runner's first three lines, verbatim;
   2. the `=== Summary:` block, verbatim, from the blank line before it up to (excluding)
      the `=== Per-file subprocess time distribution ===` header;
   3. a generated `FAILED lines: <count>` line, where the count is the number of raw
      `^FAILED ` lines;
   4. the raw `^FAILED ` lines themselves, in raw order, verbatim;
   5. the trailing region, verbatim and including its leading blank line, from the
      `=== N files with test failures … ===` header to the final `EXIT=` line.

   The rule is validated rather than asserted: applied to the run-1 raw log it reproduces
   the run-1 attachment byte-exactly — sha256
   `85f1a8b544cd608a7f2477617ccf04e3925dcebcd07e311d3c14ed36ee8ec202`, the same value the
   card records for that attachment. Applied to the base-control raw log it reproduces
   that digest as well, except for the attachment's own two-line header and the
   `Durations cached to test_durations.json …` line it omits (measured diff: 3 lines), so
   the base-control digest is described by its content and is not claimed as rule-derived.
4. §6 gained the blob-versus-materialized clarification requested by the flow controller
   while this record was being edited (peer note citing shared decision 19): the
   projection values in §6 are blob-based fork evidence, while the lock's
   `hermes.source_tree_sha256` is the materialized-tree digest of
   `src/aether_agents/lifecycle.py::_tree_sha256`, measured here at the candidate as
   `fb3e5336…`.

No fork-side change, no history rewrite and no new scope came out of the review return:
the candidate revision `387705ea1dd76f43585fca220b11859173cc4a6b`, the branch, the tree and
the behavior commits are unchanged, and the attachment set is the only delta. The run-2
raw log (1 082 245 bytes, sha256
`87ffeb0788728e3535d9d22bcd4a26ad84805d1381ea19781052ca4aa42c79a5`) remained in the
session scratch area only, which is why it is not itself an attachment.
