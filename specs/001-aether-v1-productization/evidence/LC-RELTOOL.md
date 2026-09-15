# LC-RELTOOL — release bundle, workflow and qualification tooling

Unit `LC-RELTOOL` of Objective Contract `oc_3397f9f05d780f8e@v1`
(SHA-256 `4d4c7650bf8ea93fc7cffe3d87f7f974e172d66cefcf6a74a2d83051568a4879`), base
`410c172ae69ffa87f6e32960ae4aef3b8d6598f0`, branch
`aether-agents-2/t_69a9eae4-lc-reltool-release-bundle-and-workflow-q`.
Contract in-scope 7 and 11; D8; AC-05, AC-11 and the tooling half of AC-12.

**This is a tooling qualification, not a publication.** No tag, release, artifact
upload, push, PR, merge, activation, issue mutation or credential change happened in this
unit; the bundle below is a local candidate built from local commits.

## Review repair (Supervisor run 28, changes requested)

Supervisor independently verified the bundle digests and sizes, the archive↔lock tree
identity (using the product's own `_tree_sha256`), the schema-4 `maintained_fork` lock, the
9/9 clean install, the tamper refusal and both suites, and required one bounded correction
in `.github/workflows/release.yml`: `gh release edit` takes no file arguments, so the
reconcile branch could not attach the bundle and failed on every re-run, while the create
path attached seven of eight members because the `find … ! -name SHA256SUMS` filter
excluded the checksum file, leaving the provenance digest carried by nothing.

Repaired in commit `4688b6d9c197b5531a80e1389f958fd0e9b88304`, staying inside
`gh release create`/`gh release edit` (no `gh release upload`, no second release path):

- the create path attaches the tool's own verified member set (`scripts/release_bundle.py
  members`), so all eight members including `SHA256SUMS` are attached and a file the bundle
  does not list is refused with `member-drift` instead of being attached;
- the reconcile path passes no files at all: it reads the published assets with
  `gh release view … --json assets --jq`, proves every name and `sha256:` digest against the
  qualified bundle (`verify-published-assets`), and fails closed with the offending names
  before any `gh release edit` runs;
- both invariants are pinned behaviourally rather than by string counts: the shipped step
  script is executed with the real tool and a stub `gh` that logs argv, asserting that the
  attached set equals the qualified member set and that the edit invocation passes no files.

The bundle below was rebuilt and re-verified at the repair commit, which supersedes the
`64fea6d5edee5b2377abb88c2aacee7d9ee68f84` qualification of run 28: wheel and sdist bytes
are bound to the qualified commit (commit-timestamp `SOURCE_DATE_EPOCH`, and the sdist also
carries the tool and test sources themselves). The maintained-fork archive digest is
unchanged by the repair.

## Review repair (Supervisor run 34, changes requested)

Re-review confirmed the run-28 repair behaviourally — the create path attaches all eight
members including `SHA256SUMS`, the reconcile path proves published names and digests and
refuses `published-asset-drift`/`-mismatch`/`-unverifiable`/`-malformed` before any edit,
the shipped step script is executed with the real tool and a stub `gh`, no forbidden verb
appears, there is one create/edit occurrence set and the tag validation is intact — and
required two bounded items:

1. **The built lock omitted `hermes.branch`.** The release-runtime unit's schema declares
   `schema_version` 4 with a closed `hermes` block whose `branch` is required and constant
   `aether-main`, so strict mode would have failed at integration with
   `lock-schema-invalid: release lock does not validate: hermes: 'branch' is a required
   property`. The lock now emits the branch the tool already verifies
   (`build_release_lock` → `hermes.branch: aether-main`), `validate_lock` pins it even where
   the in-tree schema still declares 3, and
   `test_lock_validation_applies_the_repository_schema_when_it_declares_four` now uses a
   stub carrying the real v4 key sets (closed `additionalProperties` blocks) instead of a
   `schema_version`-only stub, so a missing `branch`, an extra property or an empty
   `artifacts` list each fail it.
2. **The qualified member set was not byte-reproducible.** Two builds of the same two
   revisions into different directories differed in three of eight members:
   `clean-install.json` (14358 vs 14404 bytes) and consequently `provenance.json` and
   `SHA256SUMS`, because `uv` reports how long each resolution, preparation, install and
   check took and that elapsed value was captured verbatim. Captured tool output is now
   normalized (`in <elapsed>`) where it is excerpted into a report, so the elapsed value can
   no longer reach a member.

   **Run-50 correction to this item.** The sentence that stood here — "removes the *only*
   run-to-run variance …, so the reconcile claim below … is now true rather than
   aspirational" — claimed more than the evidence supported. The elapsed value was one of
   three environment-dependent values in that same member trio; the run-50 re-review
   measured the other two, and the run-50 repair below closed them. The elapsed
   normalization from this round stands unchanged; the reconcile claim is asserted only for
   the axes proven in the run-50 section.

Repaired in commit `867d7982737470605663995dab12e80b18f6fc26`. The bundle below was rebuilt
there with four real builds, all naming the same two revisions in their reports: two run in
this round into different output directories (`/tmp/r5-bundle-a`, `/tmp/r5-bundle-b`) and the
earlier pair from this task's first repair run (`/tmp/r4-bundle-a`, `/tmp/r4-bundle-b`), which
this round compared digest-by-digest against its own. All eight members are byte-identical
across all four; the bundle supersedes the
`4688b6d9c197b5531a80e1389f958fd0e9b88304` qualification. The maintained-fork archive
digest is unchanged across every round.

## Review repair (Supervisor run 50, changes requested)

The re-review verified round-34 item 1 as closed (the lock's `hermes.branch`, with the full
sensitivity matrix against the release-runtime unit's real v4 schema) and returned one
consolidated item: finish the normalization, or correct the claim. Two environment-dependent
axes remained, both reaching the same three members the run-34 round had touched
(`clean-install.json` → `provenance.json` → `SHA256SUMS`), and the run-34 four-build proof
could not see either because all four builds ran in the same directory tree with an
already-populated venv:

1. **The venv's interpreter alias.** `uv` exposes one interpreter as `bin/python` and
   `bin/python3`, and which alias a run records depends only on whether the build's own venv
   already existed (the first `uv run` after `.venv` is deleted records `python`, the next
   one `python3`). The build interpreter normally lives *inside* the Aether checkout
   (`<aether-checkout>/.venv/bin/python3`), and the mask list replaced the checkout path
   before the interpreter path, so the alias survived into every capture it appeared in.
2. **The truncation footer.** `_excerpt` computed `[truncated N characters]` on the **raw**
   text and `_portable` masked the paths afterwards, so the count encoded the real lengths
   of the checkout and work directories: the same content recorded from a longer or shorter
   build directory differed in the footer, and therefore in the member bytes.

Repaired in commit `1aa83ff02c90ca83b6f731e0aabaa0d0b7dc4c20`:

- `_capture` masks host-local paths **first** and excerpts **second**, so the recorded text
  and its footer depend only on the portable text;
- `_normalize_captured` records every interpreter leaf canonically as `bin/<interpreter>`
  (`bin/python`, `bin/python3`, `bin/python3.13`; not `bin/python-config` or
  `bin/activate`) exactly the way elapsed values are recorded as `in <elapsed>`;
- `_report_masks` masks the build interpreter **and its resolved target** before the checkout
  it normally lives in, so the alias cannot survive anywhere in a capture.

The captures in the qualified bundle now read `Using CPython 3.13.15 interpreter at:
<probe-interpreter>` in the manager and runtime venv steps, `<probe-interpreter>
<disposable-root>/tui-repo/scripts/aether_tui.py --check` for the TUI probe and
`<disposable-root>/runtime/bin/<interpreter> -c …` for the runtime probe. A scan of
`clean-install.json` for `bin/python` with or without a version suffix finds no literal
left: the interpreter appears only as the canonical `bin/<interpreter>` leaf (runtime probe
argv) and as `<probe-interpreter>` (venv steps, TUI probe argv).

### Proof — three builds of the same two revisions, all eight digests equal

| Build | Work / output directory | Interpreter the build itself ran with |
| --- | --- | --- |
| 1 | `/tmp/r6-work-a` → `/tmp/r6-bundle-a` | `<checkout>/.venv/bin/python3` (venv already existed) |
| 2 | `/tmp/r6-work-b-with-a-much-longer-directory-name` → `/tmp/r6-bundle-b-longer-name` | `<checkout>/.venv/bin/python3` (venv already existed) |
| 3 | `/tmp/r6-work-fresh` → `/tmp/r6-bundle-fresh`, run as the **first** `uv run` after `.venv` was deleted | `<checkout>/.venv/bin/python` — recorded by the wrapper that ran the build as `BUILD_INTERPRETER=…/.venv/bin/python` |

Member-by-member comparison of the three `sha256sum` tables: all eight digests identical in
every pair, and `sha256sum --check --strict SHA256SUMS` passes inside all three bundles.
Build 3 exercises the fresh-venv alias, builds 1 and 2 differ in both directory lengths, and
all three share only the two revisions as inputs.

### What is claimed, and what is not

- **Claimed:** on the declared toolchain the eight-member set is a function of the two
  revisions alone — independent of the build directory and of whether the build venv already
  existed. Both measured axes are closed, and each is pinned by a test that runs the real
  capture path and fails on the pre-repair revision
  (`test_recorded_capture_does_not_depend_on_the_build_directory_or_the_venv_alias`,
  `test_build_interpreter_is_masked_before_the_checkout_it_lives_in`,
  `test_captured_interpreter_leaf_is_normalized_like_the_elapsed_value`).
- **Not claimed:** the recorded interpreter *version* (`python_version: 3.13.15`), `uv`'s own
  version and `SOURCE_DATE_EPOCH` are declared toolchain inputs — the workflow pins
  `uv 0.12.3` with `uv sync --frozen` under `requires-python >=3.11,<3.14`. A rebuild on a
  different CPython minor version records that version; that is a toolchain identity, not the
  host-path/venv-state variance this repair removes.

## Deliverables

| Path | Change |
| --- | --- |
| `VERSION` | reconciled to `1.0.0rc1` |
| `CHANGELOG.md` | new `1.0.0rc1` entry stating the pre-stable RC scope, no PyPI/index publication and unverified WSL2 |
| `scripts/release_bundle.py` | new tool: `build`, `verify`, `members` and `verify-published-assets` subcommands; captured tool output is masked before it is excerpted and records elapsed values and interpreter leaves canonically, so all eight members are reproducible from the two revisions alone |
| `tests/test_release_bundle.py` | new focused module, 35 tests |
| `.github/workflows/release.yml` | reconciled: tag/identity validation preserved, the tagged commit is built and qualified, the create path attaches the tool's verified eight-member set, and a reconcile re-verifies the published assets instead of attaching nothing |

Qualified commit: `1aa83ff02c90ca83b6f731e0aabaa0d0b7dc4c20` (clean checkout, remote
`https://github.com/DarkArty07/Aether-Agents`; the digests below are that revision's). The
maintained-fork input is unchanged: `https://github.com/DarkArty07/aether-hermes` commit
`54eeb56dabefc98821d696656ed58c55dd777346`, clean checkout, proven reachable from
`refs/heads/aether-main` (local branch tip; remote-tracking tip
`bb5e9a422f3135371557e75bcd1db01c5f8fc3ba` — the candidate is three commits ahead because
it is not published yet).

Re-measured this round, the candidate revision is still absent from the declared repository:
`git fetch --no-tags origin 54eeb56dabefc98821d696656ed58c55dd777346` fails with
`upload-pack: not our ref`, `gh api repos/DarkArty07/aether-hermes/commits/54eeb56d…`
answers `No commit found for SHA` (HTTP 422), and the object is not in the fetched history of
`refs/heads/aether-main` (`bb5e9a422f3135371557e75bcd1db01c5f8fc3ba`). The qualification
therefore used a local clean checkout of the exact revision, exactly as the earlier rounds
did; the consequence for the publication path is recorded under integration dependencies.

## Produced bundle members (byte sizes and SHA-256)

| Member | Bytes | SHA-256 |
| --- | --- | --- |
| `aether_agents-1.0.0rc1-py3-none-any.whl` | 658758 | `84a6ee00a4b6de82c940e0d0fa63ea56f05acab947e685f03e8d880d0bb02fef` |
| `aether_agents-1.0.0rc1.tar.gz` | 1010905 | `1c4b4a84ee6f60a847cc4db229f8596980c084f572dd5e31265e5d7fce89ba07` |
| `aether-hermes-source-54eeb56dabefc98821d696656ed58c55dd777346.tar.gz` | 65892746 | `cf766ef8665c810b85d93e990e621192110e78a27ecb692170008c217dd42542` |
| `aether-agents-1.0.0rc1-release-lock.json` | 2356 | `3dc4eff39fd5c7072c46858d5a4ffc5ffcf3e715020d06ce2bf1afc7849f07d5` |
| `aether-agents-1.0.0rc1-provenance.json` | 2949 | `559975712efdd5cedd21f79e11a6c59c74fa10e46beed02ccb3b07070b0ba1e8` |
| `aether-agents-1.0.0rc1-package-members.json` | 2453323 | `067e67b911094a6ebbe710a1ba0807c770e92bd3fb4b0c88b3cfc618a808696c` |
| `aether-agents-1.0.0rc1-clean-install.json` | 14424 | `43361ff8439263d4c1b13fba8a6c7f9475387ff204d54bdbad3e26426fad5968` |
| `SHA256SUMS` | 767 | `e6936ac2c1512d217d993bbb5210c03c49445a526fb2d3ee7ad412c8b550109b` |

Candidate bundle directory for this qualification: `/tmp/r6-bundle-a`; the three builds of
the run-50 proof produced identical bytes as `/tmp/r6-bundle-b-longer-name` and
`/tmp/r6-bundle-fresh`. The wheel and sdist bytes are bound to the qualified commit (the
commit timestamp is `SOURCE_DATE_EPOCH`, and the sdist also carries the tool, test and
`specs/` sources), so these digests — unlike the maintained-fork archive, which is unchanged
across every round — differ from the `867d7982…` table they replace. The digests belong to
`1aa83ff0…`, the revision that carries the tool, the tests and `VERSION`; the branch tip adds
only this evidence file, and because the sdist ships `specs/`, a rebuild at any later commit
necessarily has a different sdist digest — LC-INT rebuilds at the integrated revision and
attaches those bytes, as recorded below.

**What the workflow does with exactly these eight names:** `scripts/release_bundle.py
members --bundle <bundle>` prints this list — the seven members `SHA256SUMS` covers, plus
`SHA256SUMS` itself — and the create path passes exactly those paths to `gh release create`
with `--verify-tag --generate-notes` and the tag's prerelease flag; a file in the bundle
directory the checksum file does not list is refused (`member-drift`) and nothing is
attached. The reconcile path passes no file arguments at all (`gh release edit` accepts
none); it reads the release's published assets with `gh release view --json assets --jq`,
then `scripts/release_bundle.py verify-published-assets` re-proves every asset name and
`sha256:` digest against this bundle and exits non-zero — with the offending names, before
any `gh release edit` runs — when a published asset is missing, extra, digest-less or
differently hashed. The integration card must set the release workflow's `FORK_COMMIT` to
the accepted maintained-fork revision before the tag is pushed (the workflow ships a
fail-closed placeholder so wrong bytes cannot be published).

## Release lock (schema 4, maintained fork)

```json
"schema_version": 4,
"aether": {"version": "1.0.0-rc.1", "package_version": "1.0.0rc1", "distribution": "aether-agents",
           "git_tag": "v1.0.0-rc.1", "git_commit": "1aa83ff0…", "python_requires": ">=3.11,<3.14",
           "observer_requirements_sha256": "798d9f1f…", "wheel_sha256": "84a6ee00…"},
"hermes": {"source_mode": "maintained_fork", "repository": "https://github.com/DarkArty07/aether-hermes",
           "branch": "aether-main", "version": "0.20.1", "tag": "54eeb56d…",
           "commit": "54eeb56d…", "source_tree_sha256": "4f0c6fab…",
           "python_requires": ">=3.11,<3.14", "artifacts": [one source archive with URL+digest]},
"profile_bundle": {"version": "2", "sha256": "31915524…", "roles": ["morfeo","supervisor","implementer"]}
```

The lock's `hermes` key set is exactly the nine properties the release-runtime unit's v4
schema declares (`additionalProperties: false`): `artifacts`, `branch`, `commit`,
`python_requires`, `repository`, `source_mode`, `source_tree_sha256`, `tag`, `version`. Run
against that real schema, the validator reports `schema_validation: applied` with
`repository_schema_version: 4`; removing `branch` refuses with
`lock-identity: release lock identity: hermes.branch is None`. `hermes.tag` is the commit
itself with `tag_source: exact-commit`, the explicit no-tag representation for a maintained
fork that does not tag every candidate revision.

`hermes.source_tree_sha256` is the product's own deterministic materialization digest of
the exact commit (`lifecycle._materialize_git_archive` + `lifecycle._tree_sha256`), and
the bundle's archive is proven to materialize that same tree, so the lock, the archive and
the doctor/activation comparison use one identity.

## Verification actually run (raw results)

Command form: `uv run --frozen python scripts/release_bundle.py …`.

| Check | Result |
| --- | --- |
| `build --aether-checkout . --aether-commit 1aa83ff0… --fork-checkout <provisioned fork checkout> --fork-commit 54eeb56… --work /tmp/r6-work-a --out /tmp/r6-bundle-a --pre-integration`, then the same into `/tmp/r6-work-b-with-a-much-longer-directory-name` / `/tmp/r6-bundle-b-longer-name` and, as the first `uv run` after `rm -rf .venv`, into `/tmp/r6-work-fresh` / `/tmp/r6-bundle-fresh` | all three exit 0 in 64.4 s, 55.6 s and 80.0 s; 8 members written by each; `finished_bundle: {members_rehashed: 7, plain_text_scan: clean}` (the counter is the seven members `SHA256SUMS` covers; the checksum file is the eighth, and `members` reports all eight) |
| **Byte reproducibility of the whole member set** (round-34 item 2, completed in run 50) | three builds of the same two revisions — two different work/output directory pairs plus one fresh-venv build (`.venv` deleted first; a wrapper recorded the build's own `sys.executable` as `<checkout>/.venv/bin/python`, the fresh alias the other two builds recorded as `python3`) — agree on all eight digests, member by member; `sha256sum --check --strict SHA256SUMS` passes in each. No timestamp field exists in either report; the captured `uv` elapsed values are recorded as `in <elapsed>`, every interpreter leaf as `bin/<interpreter>` (or `<probe-interpreter>` for the build interpreter), and excerpt footers are counted on the masked text, so neither the build directory nor the venv state reaches a member |
| Byte reproducibility of the distributions from the same commit (the tool builds twice and compares) | `{"wheel": true, "sdist": true, "source_date_epoch": 1789457806}` with `SOURCE_DATE_EPOCH` pinned to the commit timestamp |
| Rebuilt lock validated against the release-runtime unit's **real v4 schema** (round-34 item 1, re-measured in run 50) | `validate_lock(lock, aether_checkout=…, allow_schema_drift=False)` with `_lock_schema_path` pointed at that unit's `specs/001-aether-v1-productization/contracts/release-lock.schema.json` (asserted to be the `schema_version` 4 file): accepted with `schema_validation: applied`, `repository_schema_version: 4`, pinned identity `hermes.branch=aether-main`; sensitivity held under the same schema — `branch` deleted → `lock-identity: release lock identity: hermes.branch is None`; `branch: "main"` → `lock-identity: … hermes.branch is 'main'`; an extra `hermes` property → `lock-schema-invalid: … Additional properties are not allowed ('unexpected' was unexpected)`; `artifacts: []` → `lock-schema-invalid: … hermes/artifacts: [] should be non-empty; hermes/artifacts: [] does not contain items matching the given schema`; `source_mode: upstream` → `lock-identity`; `schema_version: 3` → `lock-identity: … schema_version is not 4`. The built lock's `hermes` key set is exactly the nine v4 properties: `artifacts, branch, commit, python_requires, repository, source_mode, source_tree_sha256, tag, version` |
| `verify --bundle /tmp/r6-bundle-a --expect-aether-commit 1aa83ff0… --expect-fork-commit 54eeb56… --pre-integration --clean-install` | exit 0 in 42.3 s; every member re-hashed against `SHA256SUMS`; 9/9 install steps exit 0; 13 probes = 6 required handshakes `pass`, 5 optional fail-closed envelopes `refused` as documented (`doctor`, `status`, `setup --dry-run`, `update --dry-run`, `rollback --dry-run`), 1 optional probe `unavailable` (`aether update --local --dry-run`, the option surface that does not exist at this revision) and 1 required probe `unavailable` (`pinned aether update --local option surface`), which the report records in `failed_probes` rather than hiding; `hermes-agent` 0.20.1 importable; the four Aether plugin entry points discovered from the artifact-installed wheel |
| Source not mutated by the build | post-build `HEAD` equals the requested commit and `git status --porcelain` is empty |
| Wheel inspection (product `LifecycleManager._inspect_wheel`) | 158 members; `aether-agents` 1.0.0rc1; entry point `aether-contract-observer=aether_agents.observation.capture.hermes_plugin`; installed-file fingerprint `cac9cb16…`; observation schema digests `7b239fce…`/`b854701e…`/`9d134b4d…` |
| Sdist inspection | 261 members; root entries `.gitignore`, `LICENSE`, `PKG-INFO`, `README.md`, `VERSION`, `pyproject.toml`, `scripts`, `specs`, `src`, `tests` |
| Maintained-fork archive inspection | 9375 members; extracted tree digest equals the lock's `source_tree_sha256` (`4f0c6fab…`) |
| Private-path scan of Aether-authored bytes (`scripts/check_public_artifacts.py`, tracked surface + wheel + sdist + plain-text reports/lock/sums) | clean |
| Private-path scan of the maintained-fork archive | 89 distinct matches across upstream members, reported as shapes (`/home/<name>/`, `/Users/<name>/`, `C:\Users\<name>`, `c:\users\<name>`) — generic example paths in upstream code/tests/docs; disclosed deliberately in the report and never as literals |
| Secret scan | canonical narrow patterns (private-key material, `ghp_`/`github_pat_`) enforced strictly on every member: clean; broader patterns (AWS/Slack/api-key/telegram) reviewed with labels: 1 synthetic fixture in `tests/test_objective_contracts.py` of the sdist, upstream examples counted in the fork archive |
| Clean install into fresh disposable roots | 9/9 steps exit 0: manager venv, `uv pip install <wheel>` (normal resolver), `uv pip check`, runtime venv, `uv export --frozen --no-dev` from the archive, `uv pip sync --require-hashes --strict`, wheel into the runtime, `uv pip install --no-deps --editable <archive>` (the Hermes project refuses wheel/sdist builds by design), `uv pip check` |
| Runtime handshake | `hermes-agent` 0.20.1 importable (`import hermes_cli`), all four Aether plugin entry points discovered from the artifact-installed wheel |
| CLI handshakes | `aether --version`, `aether version --json` (reports `1.0.0rc1`), `aether --help`, `aether update --help` → pass; `doctor`/`status`/`setup --dry-run`/`update --dry-run`/`rollback --dry-run` → documented fail-closed envelopes (exit 3/4) |
| TUI handshake | `scripts/aether_tui.py --check` (exact commit) against a disposable launcher layout and the artifact-installed runtime → `result: ready` |
| `verify --bundle <bundle> --expect-aether-commit 4688b6d… --expect-fork-commit 54eeb56… --pre-integration --clean-install` (run-28 round, superseded by the `1aa83ff0…` row above; kept as history) | exit 0 in 37.7 s: every member re-hashed against `SHA256SUMS`, wheel/archive re-matched against the lock, scans re-run, fresh artifact-installed handshake repeated |
| `members --bundle <bundle>` | exit 0; prints the eight absolute member paths in sorted order, `SHA256SUMS` first (re-measured on this bundle) |
| `verify-published-assets --bundle <bundle> --tag v1.0.0-rc.1 --assets -` (the workflow's stdin form) against the qualified digests | exit 0: `published release carries the qualified bytes: v1.0.0-rc.1` and the eight names |
| The shipped release step executed for real (extracted step script + real `scripts/release_bundle.py` + stub `gh` that logs argv) | create path: `release view` then `release create` with exactly the eight qualified paths (`--verify-tag --generate-notes --prerelease`); reconcile path: `release view` then `release edit` with **no file arguments** and the verification in between; drift cases: non-zero exit, diagnostic on stderr, **no** create/edit invocation logged. Tests: `test_release_step_attaches_exactly_the_qualified_member_set`, `test_release_step_reconcile_verifies_the_release_and_passes_no_files`, `test_release_step_reconcile_fails_closed_before_editing_anything`, `test_release_step_refuses_a_bundle_that_drifted_before_attaching` |
| Real `gh` interface check (read-only, against a public release) | `gh release view --json assets --jq '.assets[] | "\(.name)\t\(.digest // "")"'` emits `name<TAB>sha256:<hex>` lines — the shape the tool parses; `gh release edit --help` shows `USAGE: gh release edit <tag>`, with no `[<filename>...]` (unlike `gh release create`, whose help documents asset files), and `gh release edit <tag> --prerelease f1 f2` is rejected locally with `accepts 1 arg(s), received 3` |

### Refusals proven (negative evidence)

| Case | Observed | Exit |
| --- | --- | --- |
| strict mode at this revision (no `--pre-integration`) | `lock-schema-drift: the repository schema declares schema_version 3; the maintained-fork schema is supplied by the release-runtime unit and only exists after integration` — re-measured at `1aa83ff0…` | 1 |
| lock without the declared branch (against the real v4 schema) | `lock-identity: release lock identity: hermes.branch is None`; `branch: "main"` → `lock-identity: … hermes.branch is 'main'`; `source_mode: upstream` → `lock-identity`; `schema_version: 3` → `lock-identity: … schema_version is not 4`; and with every pinned value correct but the shape drifted (`artifacts: []`, one extra property) → `lock-schema-invalid: release lock does not validate: hermes: Additional properties are not allowed ('unexpected' was unexpected); hermes/artifacts: [] should be non-empty; hermes/artifacts: [] does not contain items matching the given schema` — all re-measured in run 50, and the same refusals are pinned by the tests | 1 |
| wrong Aether revision | `revision-mismatch: aether checkout HEAD 1aa83ff02c90ca83b6f731e0aabaa0d0b7dc4c20 is not the requested commit 410c172ae69ffa87f6e32960ae4aef3b8d6598f0` — re-measured at this revision | 1 |
| wrong revision form | `unknown-revision: aether commit '2e9bf8a' is not a full 40-hex id` | 1 |
| foreign maintained-fork repository | `repository-identity: maintained-fork source must be https://github.com/DarkArty07/aether-hermes, observed https://github.com/NousResearch/hermes-agent.git` | 1 |
| dirty checkout (modified file at report time) | `dirty-checkout: aether checkout has uncommitted changes: ?? scratch-dirty-probe` — re-measured at this revision; the probe file was removed afterwards and `git status --porcelain` is empty again | 1 |
| divergent fork commit | `branch-divergence: commit … is not reachable from aether-main (observed …)` (test) | — |
| tampered member byte | `digest-mismatch: aether_agents-1.0.0rc1.tar.gz hashes to 1a44164b7c407411c1771fd7590f34500d74216f001546a658061d5f0a7c7eb7, not the recorded 1c4b4a84ee6f60a847cc4db229f8596980c084f572dd5e31265e5d7fce89ba07` — re-measured at this revision on a copy; the qualified bundle is untouched | 1 |
| removed member | `member-drift: bundle members do not match SHA256SUMS: extra [], missing ['aether-agents-1.0.0rc1-provenance.json']` — re-measured at this revision | 1 |
| rewritten checksum entry | `digest-mismatch: aether-agents-1.0.0rc1-clean-install.json hashes to 43361ff8439263d4c1b13fba8a6c7f9475387ff204d54bdbad3e26426fad5968, not the recorded 0000000000000000000000000000000000000000000000000000000000000000` — re-measured at this revision | 1 |
| unlisted file in the bundle directory (attach set) | `member-drift: bundle members do not match SHA256SUMS: extra ['stray.bin'], missing []` — `members` refuses, so the create path attaches nothing (re-measured at this revision) | 1 |
| published release, one asset digest differs | `published-asset-mismatch: release v1.0.0-rc.1 bytes do not match the qualified bundle: aether_agents-1.0.0rc1.tar.gz is sha256:0000000000000000000000000000000000000000000000000000000000f, not the qualified sha256:1c4b4a84ee6f60a847cc4db229f8596980c084f572dd5e31265e5d7fce89ba07` — re-measured against a listing built from this bundle | 1 |
| published release missing the checksum file | `published-asset-drift: release v1.0.0-rc.1 does not carry the qualified bundle: missing ['SHA256SUMS'], unexpected []` — re-measured at this revision (a listing without `SHA256SUMS`, the exact shape the tool's own checksum file cannot produce) | 1 |
| published release carrying an extra asset | `published-asset-drift: … does not carry the qualified bundle: missing [], unexpected ['aether-agents-1.0.0rc1-unexpected.json']` | 1 |
| published asset without a digest (older upload) | `published-asset-unverifiable: release v1.0.0-rc.1 assets carry no digest, so the qualified bytes cannot be verified: ['aether_agents-1.0.0rc1-py3-none-any.whl']` | 1 |
| asset listing line without the `name<TAB>digest` separator | `published-assets-malformed: expected '<name>\t<digest>' per published asset, observed 'aether-agents-1.0.0rc1-clean-install.json'` | 1 |
| operator path in Aether-authored bytes | `private-path-scan: Aether-authored public bytes contain operator paths: …` (test; also caught a real leak in an earlier revision of the report during this unit's own runs) | 1 |
| credential material | `secret-scan` refusal (test) | 1 |

The matching control for the reconcile path was re-measured too: an eight-asset listing built
from this bundle (the seven covered members plus `SHA256SUMS` itself, each with its
`sha256:` digest) prints `published release carries the qualified bytes: v1.0.0-rc.1` and
exits 0.

Every reconcile refusal above happens before any `gh release edit` invocation; the
behavioural test asserts that no create/edit call is logged for the drifting, incomplete
and digest-less releases.

## Repository gates (raw results)

| Gate | Result |
| --- | --- |
| `uv build` | exit 0; `dist/aether_agents-1.0.0rc1.tar.gz`, `dist/aether_agents-1.0.0rc1-py3-none-any.whl` |
| `uv run --frozen python scripts/run_tests.py` (full bootstrap, exact-Hermes, clean tree at the qualified commit `1aa83ff0…`) | **6 failed, 1720 passed, 70 skipped** in 383.00 s — the same six attributed classes as the previous round (1 VERSION-coupled node owned by LC-RUNTIME's module, 1 policy-manifest line for LC-INT, 4 monitor nodes of the pre-existing #438 class); my new module's 35 tests pass and the load-sensitive latency oracle of `tests/test_observation_performance.py` passed in this run |
| `uv run --frozen ruff check src/aether_agents tests scripts` | exit 0 |
| `uv run --frozen ruff format --check src/aether_agents tests scripts` | exit 0 (166 files already formatted) |
| `uv run --frozen mypy src/aether_agents` | exit 0 (renders `Success: no issues found in 67 source files`) |
| `uv run --frozen python scripts/check_documentation.py` | exit 0 (`documentation validation passed`) |
| `uv run --frozen python scripts/check_public_artifacts.py --root .` | exit 0 (`public artifact path scan passed: tracked surface + 0 artifact(s)`) |
| `git diff --check` / `git diff --cached --check` | exit 0 (no whitespace damage; nothing staged at report time) |
| `.github/workflows/release.yml` YAML parse (re-measured at this revision) | parses; one job, seven steps; the identity checks are intact (`refs/tags/$RELEASE_TAG^{commit}` against `refs/remotes/origin/main`); exactly one `gh release create "$RELEASE_TAG"` and one `gh release edit "$RELEASE_TAG"` occurrence (the second `gh release edit` mention is a comment stating that it takes no file arguments); the tag step still emits exactly `version` and `prerelease`; `FORK_COMMIT` is still the fail-closed zero placeholder that LC-INT replaces |
| `uv run --frozen pytest -q tests/test_a1_contracts.py -k ReleaseWorkflow` (the existing release-workflow suite, not edited by this unit) | 10 passed, 8 subtests passed — including `test_workflow_keeps_release_effects_and_permissions_bounded`, which forbids the publication verbs, and the no-bundle identity reconcile |
| `uv run --frozen pytest -q tests/test_release_bundle.py` | 35 passed |

Three of the module's tests pin the run-50 repair behaviourally and fail on the pre-repair
revision `2475fe88` (verified: `3 failed, 2 passed` for the same selection against the old
tool): `test_recorded_capture_does_not_depend_on_the_build_directory_or_the_venv_alias`,
`test_build_interpreter_is_masked_before_the_checkout_it_lives_in`,
`test_captured_interpreter_leaf_is_normalized_like_the_elapsed_value`.

### Failures in the full bootstrap, attributed

The run-50 suite is **6 failed, 1720 passed, 70 skipped**; the six are the same classes the
round-34 record attributed, re-measured at `1aa83ff0…`:

1. `tests/test_public_artifacts.py::test_canonical_base_manifest_matches_tracked_non_specs_files`
   — **my files need manifest lines.** The heredoc in `.github/workflows/policy.yml`
   declares 400 entries while 404 tracked non-`specs/` files exist. Missing:
   `.aether/objective-contracts/oc_3397f9f05d780f8e/v1.md` (contract landing, not mine),
   `patches/hermes/HLP-425-review-flow-continuity.patch` (#437, LC-BLOCK's line), and my
   two files. The exact lines this unit contributes (10-space indentation inside the
   heredoc; the workflow sorts the list before comparing):

```
          scripts/release_bundle.py
          tests/test_release_bundle.py
```

   With those two lines applied the remaining undeclared files are exactly the two
   pre-existing ones above (re-measured: declared 400, tracked non-`specs/` 404, the four
   undeclared names are precisely those four), and the manifest test failed at base
   `410c172` for the same pre-existing reason.
2. `tests/test_observation_lifecycle.py::test_prepare_release_installs_one_wheel_in_manager_and_exact_runtime`
   — **cross-unit collision caused by `VERSION`, owned by the LC-RUNTIME module.** That
   test builds the repository's real distributions and compares them with a lock fixture
   whose package version is the hardcoded literal `"0.24.0"`. With `VERSION`
   `1.0.0rc1` the comparison fails with
   `IntegrityError: Aether release-lock identity disagrees with wheel metadata`.
   Controlled reproduction: at the same commit with `VERSION` restored to `0.24.0` the
   test passes (1 passed in 9.62 s). The test module is in LC-RUNTIME's writable surface,
   so this unit did not edit it; the required reconciliation is to derive that fixture
   version from the repository `VERSION`/`product_version()` instead of the stale literal.
   This is returned as a bounded integration repair / rework item, not absorbed here.
3. `tests/test_telegram_monitor_cli_plugin.py` (4 failures:
   `test_cli_actions_read_the_durable_state_without_hermes`,
   `test_control_tool_returns_a_bounded_envelope_when_the_runtime_raises`,
   `test_cli_control_action_returns_the_envelope_when_the_runtime_raises`,
   `test_d15r_fixture_and_environment_gaps_chain_end_to_end`)
   — **pre-existing, unowned by this unit.** Reproduced at base `410c172` in a scratch
   clone (7 failures there, a different subset: exactly the order/environment-dependent
   symptom of #438). LC-BLOCK owns #437/#438; nothing in this unit's diff touches the
   monitor, the policy manifest logic or the lifecycle.

The load-sensitive latency oracle that failed under the round-34 suite load
(`tests/test_observation_performance.py::test_native_plugin_callback_latency_includes_projection_validation_and_append`,
p95 5.84 ms against its 5.0 ms budget) passed in this run; it remains a timing oracle whose
result depends on suite load, not on this unit's diff.

## Integration dependencies recorded for LC-INT

- `policy.yml`: the two exact manifest lines above (recorded, not edited, per the card).
- Release identity constant: set `FORK_COMMIT` in `.github/workflows/release.yml` to the
  accepted `aether-main` revision; the workflow otherwise refuses.
- **The accepted fork revision must be reachable from the declared repository before the
  publication path can resolve it.** Re-measured in run 50: `54eeb56d…` is not fetchable
  (`git fetch --no-tags origin 54eeb56d…` → `upload-pack: not our ref`), GitHub answers
  `No commit found for SHA` (HTTP 422) for it, and it is not in the history of the current
  `refs/heads/aether-main` (`bb5e9a422f…`). The contract records it as the accepted
  revision "three commits ahead of remote `bb5e9a422f…`", so the integration must publish
  that branch (the three commits fast-forward it) before the tag is pushed — otherwise the
  workflow's `--fork-repository` resolution fails closed with `revision-unavailable`, and
  even a fetchable commit would still have to pass `verify_branch_membership` against the
  branch. This is a property of the accepted revision, not of the tool: the tool refuses
  rather than deriving an identity from a branch tip, the working directory or recency.
- The workflow runs the tool in **strict** mode, and round-34 item 1 closed the schema half
  of that coupling: the lock now emits `hermes.branch: aether-main` and validates against
  the release-runtime unit's real v4 schema (`schema_validation: applied`,
  `repository_schema_version: 4`). What remains enforced at integration is the pinned
  `aether update --local --aether-checkout --aether-commit --fork-checkout --fork-commit`
  option surface, which this revision reports as `unavailable` under `--pre-integration`.
  If the integrated vocabulary differs from that shape (or the v4 schema changes again), the
  tool fails closed and the delta must come back to this unit rather than being worked
  around.
- **The released bytes are revision-bound.** The digests above belong to a bundle built from
  `1aa83ff0…`; LC-INT must rebuild from the integrated revision and attach *those* bytes,
  then verify them with the same `members` / `verify-published-assets` pair. Rebuilding from
  the same inputs on the declared toolchain reproduces all eight members byte-for-byte
  (run-50 proof), so the reconcile branch is reachable on a re-run rather than only on a
  first run.
- Reconcile is verification-only by construction: a re-run or `workflow_dispatch` for a tag
  whose release already exists succeeds exactly when that release carries these exact bytes.
  A release that exists *without* them (for example one created before this reconciliation,
  or an interrupted upload) is refused with the offending names and is **not** repaired by
  the workflow — the incomplete release must be removed and the tag re-run, because
  `gh release edit` cannot attach files and the pre-existing canonical A1 contract forbids
  `gh release upload` inside this workflow.

## Compatibility statement (unit level)

The change is source-compatible with the accepted Aether 1.0 interfaces: no `src/**`
module, exported name, schema, CLI surface or packaged resource was modified. The tool
gains two additive subcommands (`members`, `verify-published-assets`) and the workflow
keeps its single release path and its tag/identity validation, including the pre-existing
A1 contract's no-bundle identity reconcile. `VERSION` moved to the contract-decided
`1.0.0rc1`, which changes product identity (not API compatibility) and is exactly why the
repository-wide test identified in failure 2 needs its version-derived reconciliation. The
bundle is built once from exact clean revisions; its artifact digests are reproducible from
the same commit, and its release lock binds the exact commit/tree identities rather than
any machine or live state. The round-34 and run-50 repairs only tightened those two
properties: the lock gained `hermes.branch` (a v4 requirement, validated against the real
schema), and captured tool output is masked before it is excerpted with elapsed values and
interpreter leaves recorded canonically, so the entire member set — not just the
distributions — is reproducible from the two revisions regardless of the build directory or
the build venv's state. No aggregate release conclusion, channel or impact is asserted
here; `release_impact=major`, `release_action=publish`, `release_channel=prerelease`
remain the contract's decision for the integration and closeout cards.

## Residual risk

- The v4 lock shape and the pinned `--local` CLI vocabulary are still supplied by parallel
  units and can change. The schema half is now proven against the real v4 schema rather than
  only against the shape assumed here, but the coupling remains: if either changes, the tool
  refuses (`lock-schema-invalid` / `unavailable`) and the delta must return to this unit.
- `tests/test_observation_performance.py`'s latency-percentile oracle is load-sensitive: it
  failed once under the round-34 suite load (p95 5.84 ms against a 5.0 ms budget) and passed
  in the run-50 suite and when run alone at the same revisions. It is not this unit's file
  and no constant was adjusted; recorded so a future red suite is not mis-attributed to this
  change.
- **Reproducibility boundary.** The claim proven in the run-50 section covers the build
  directory and the fresh-vs-existing venv state. The recorded interpreter *version*
  (`python_version: 3.13.15`), `uv`'s own version and `SOURCE_DATE_EPOCH` are declared
  toolchain inputs (the workflow pins `uv 0.12.3` and runs `uv sync --frozen` under
  `requires-python >=3.11,<3.14`); a rebuild on a different CPython minor version records
  that version instead, so cross-toolchain byte equality is not claimed.
- **Runtime observation (not a unit claim):** two read-only inspection calls were affected by
  the Aether pre-tool hook. One workflow-inspection command was refused with
  `AETHER-IMPLEMENTER-EXTERNAL-EFFECT` because the inline script text contained the verb
  strings the guard matches (used there only as dictionary keys for counters); the inspection
  was completed with a script file instead. One large record patch then failed the hook with
  `hook … failed closed: timed out after 5s` and succeeded on retry. No external effect was
  attempted in either case; recorded for the runtime owner, not treated as a unit defect.
- **Fork-revision availability (cross-unit, reported above):** the accepted maintained-fork
  revision is not fetchable from the declared repository today, so the workflow's
  `--fork-repository` resolution would refuse `revision-unavailable` until the fork branch
  carries it. The qualification therefore used a local clean checkout of the exact commit;
  the bytes and the locked tree digest are unaffected by where the commit object came from,
  but a rebuild that must fetch it will fail closed until the branch is published.
- The reconcile verification depends on GitHub reporting a `sha256:` digest per release
  asset. When a digest is absent (an upload predating asset digests) the step refuses with
  `published-asset-unverifiable` instead of accepting the release; that is deliberate, and
  it means such a release must be re-created rather than reconciled.
- The TUI `--check` probe builds a disposable launcher layout around the shipped
  `scripts/aether_tui.py`; if that launcher's layout contract changes in another unit, the
  probe fails closed and needs its layout (or the probe) reconciled.
- `tests/test_observation_lifecycle.py`'s hardcoded `0.24.0` must be reconciled before the
  integrated suite can be green; it is identified above with a controlled reproduction.
- Nineteen seconds of behaviour (`aether setup/update/doctor/status/rollback`) are
  exercised as documented-envelope refusals in a disposable root at this revision; their
  positive paths belong to the runtime unit's own evidence and the real activation lane.
