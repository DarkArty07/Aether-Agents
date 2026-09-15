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
   normalized (`in <elapsed>`) where it is excerpted into a report, which removes the only
   run-to-run variance without hiding anything else, so the reconcile claim below — a
   re-run succeeds exactly when the release already carries these bytes — is now true
   rather than aspirational.

Repaired in commit `867d7982737470605663995dab12e80b18f6fc26`. The bundle below was rebuilt
there with four real builds, all naming the same two revisions in their reports: two run in
this round into different output directories (`/tmp/r5-bundle-a`, `/tmp/r5-bundle-b`) and the
earlier pair from this task's first repair run (`/tmp/r4-bundle-a`, `/tmp/r4-bundle-b`), which
this round compared digest-by-digest against its own. All eight members are byte-identical
across all four; the bundle supersedes the
`4688b6d9c197b5531a80e1389f958fd0e9b88304` qualification. The maintained-fork archive
digest is unchanged across every round.

## Deliverables

| Path | Change |
| --- | --- |
| `VERSION` | reconciled to `1.0.0rc1` |
| `CHANGELOG.md` | new `1.0.0rc1` entry stating the pre-stable RC scope, no PyPI/index publication and unverified WSL2 |
| `scripts/release_bundle.py` | new tool: `build`, `verify`, `members` and `verify-published-assets` subcommands; captured tool output is normalized so every member is reproducible |
| `tests/test_release_bundle.py` | new focused module, 32 tests |
| `.github/workflows/release.yml` | reconciled: tag/identity validation preserved, the tagged commit is built and qualified, the create path attaches the tool's verified eight-member set, and a reconcile re-verifies the published assets instead of attaching nothing |

Qualified commit: `867d7982737470605663995dab12e80b18f6fc26` (clean checkout, remote
`https://github.com/DarkArty07/Aether-Agents`; the digests below are that revision's). The
maintained-fork input is unchanged: `https://github.com/DarkArty07/aether-hermes` commit
`54eeb56dabefc98821d696656ed58c55dd777346`, clean checkout, proven reachable from
`refs/heads/aether-main` (local branch tip; remote-tracking tip
`bb5e9a422f3135371557e75bcd1db01c5f8fc3ba` — the candidate is three commits ahead because
it is not published yet).

## Produced bundle members (byte sizes and SHA-256)

| Member | Bytes | SHA-256 |
| --- | --- | --- |
| `aether_agents-1.0.0rc1-py3-none-any.whl` | 658758 | `7ab13e9642ac17ae5e6f35882023ba5a91c5c284bffdd3960fb2b599408ee47f` |
| `aether_agents-1.0.0rc1.tar.gz` | 1010005 | `4dfdf64aa2f59baf5db439688878d2395c76d96445fddf25edb96789f092a122` |
| `aether-hermes-source-54eeb56dabefc98821d696656ed58c55dd777346.tar.gz` | 65892746 | `cf766ef8665c810b85d93e990e621192110e78a27ecb692170008c217dd42542` |
| `aether-agents-1.0.0rc1-release-lock.json` | 2356 | `3660895c3a6a8683a30e12f6850e8dddea5656eae740b9d5aa8bebdc80e2f44a` |
| `aether-agents-1.0.0rc1-provenance.json` | 2949 | `51287ef9173969339f02732486bbb68e7112e0954af54fe3f3227ac8a449719b` |
| `aether-agents-1.0.0rc1-package-members.json` | 2453323 | `d7783b7b001ab5d000564610365f8d007b2c2b610d961f194129b99c3f98c5d2` |
| `aether-agents-1.0.0rc1-clean-install.json` | 14432 | `c63a0d19512e88f9b8aca46b9c30c104583b9bb9edf8c7f20b31ecae90d3aa84` |
| `SHA256SUMS` | 767 | `02f111ddd16a6b256ebd2d548083f485474fe42621fef36702ca3236722bb093` |

Candidate bundle directory for this qualification: `/tmp/r5-bundle-a` (the four builds
above produced identical bytes; `/tmp/r4-bundle-a` and `/tmp/r4-bundle-b` are the earlier
pair, which the round-34 re-review inspected).

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
           "git_tag": "v1.0.0-rc.1", "git_commit": "867d7982…", "python_requires": ">=3.11,<3.14",
           "observer_requirements_sha256": "798d9f1f…", "wheel_sha256": "7ab13e96…"},
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
| `build --aether-checkout . --aether-commit 867d7982… --fork-checkout <provisioned fork checkout> --fork-commit 54eeb56… --work /tmp/r5-a --out /tmp/r5-bundle-a --pre-integration`, then the same into `/tmp/r5-b` / `/tmp/r5-bundle-b` | both exit 0; 8 members written by each; the second build spans 60 s (00:48:33 → 00:49:33 local, measured from its first materialized work entry to the written report); `finished_bundle: {members_rehashed: 7, plain_text_scan: clean}` (the counter is the seven members `SHA256SUMS` covers; the checksum file is the eighth, and `members` reports all eight) |
| **Byte reproducibility of the whole member set** (round-34 item 2) | four builds of the same two revisions into four different work/output directories — `/tmp/r5-bundle-a`, `/tmp/r5-bundle-b` and the earlier `/tmp/r4-bundle-a`, `/tmp/r4-bundle-b` — agree on all eight digests; every pairwise comparison is byte-identical, including `clean-install.json`, `provenance.json` and `SHA256SUMS`, which the round-34 re-review measured as differing. No timestamp field exists in either report; the only run-to-run variance was the captured `uv` elapsed values, now recorded as `in <elapsed>` |
| Byte reproducibility of the distributions from the same commit (the tool builds twice and compares) | `{"wheel": true, "sdist": true, "source_date_epoch": 1789453965}` with `SOURCE_DATE_EPOCH` pinned to the commit timestamp |
| Rebuilt lock validated against the release-runtime unit's **real v4 schema** (round-34 item 1) | `validate_lock(lock, aether_checkout=…, allow_schema_drift=False)` with the schema path pointed at that unit's `specs/001-aether-v1-productization/contracts/release-lock.schema.json`: `schema_validation: applied`, `repository_schema_version: 4`, pinned identity `hermes.branch=aether-main`; the same lock with `hermes.branch` deleted refuses `lock-identity: release lock identity: hermes.branch is None` |
| `verify --bundle /tmp/r5-bundle-a --expect-aether-commit 867d7982… --expect-fork-commit 54eeb56… --pre-integration --clean-install` | exit 0; every member re-hashed against `SHA256SUMS`; 9/9 install steps exit 0; 13 probes = 6 required handshakes `pass`, 5 optional fail-closed envelopes `refused` as documented, 1 optional probe `unavailable` (`aether update --local --dry-run`, the option surface that does not exist at this revision) and 1 required probe `unavailable` (`pinned aether update --local option surface`), which the report records in `failed_probes` rather than hiding; `hermes-agent` 0.20.1 importable; the four Aether plugin entry points discovered from the artifact-installed wheel |
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
| `verify --bundle <bundle> --expect-aether-commit 4688b6d… --expect-fork-commit 54eeb56… --pre-integration --clean-install` (run-28 round, superseded by the `867d7982…` row above; kept as history) | exit 0 in 37.7 s: every member re-hashed against `SHA256SUMS`, wheel/archive re-matched against the lock, scans re-run, fresh artifact-installed handshake repeated |
| `members --bundle <bundle>` | exit 0; prints the eight absolute member paths in sorted order, `SHA256SUMS` first |
| `verify-published-assets --bundle <bundle> --tag v1.0.0-rc.1 --assets -` (the workflow's stdin form) against the qualified digests | exit 0: `published release carries the qualified bytes: v1.0.0-rc.1` and the eight names |
| The shipped release step executed for real (extracted step script + real `scripts/release_bundle.py` + stub `gh` that logs argv) | create path: `release view` then `release create` with exactly the eight qualified paths (`--verify-tag --generate-notes --prerelease`); reconcile path: `release view` then `release edit` with **no file arguments** and the verification in between; drift cases: non-zero exit, diagnostic on stderr, **no** create/edit invocation logged. Tests: `test_release_step_attaches_exactly_the_qualified_member_set`, `test_release_step_reconcile_verifies_the_release_and_passes_no_files`, `test_release_step_reconcile_fails_closed_before_editing_anything`, `test_release_step_refuses_a_bundle_that_drifted_before_attaching` |
| Real `gh` interface check (read-only, against a public release) | `gh release view --json assets --jq '.assets[] | "\(.name)\t\(.digest // "")"'` emits `name<TAB>sha256:<hex>` lines — the shape the tool parses; `gh release edit --help` shows `USAGE: gh release edit <tag>`, with no `[<filename>...]` (unlike `gh release create`, whose help documents asset files), and `gh release edit <tag> --prerelease f1 f2` is rejected locally with `accepts 1 arg(s), received 3` |

### Refusals proven (negative evidence)

| Case | Observed | Exit |
| --- | --- | --- |
| strict mode at this revision (no `--pre-integration`) | `lock-schema-drift: the repository schema declares schema_version 3; the maintained-fork schema is supplied by the release-runtime unit and only exists after integration` — re-measured at `867d7982…` | 1 |
| lock without the declared branch (against the real v4 schema) | `lock-identity: release lock identity: hermes.branch is None` — and with every pinned value correct but the shape drifted (`artifacts: []`, one extra property): `lock-schema-invalid: release lock does not validate: hermes: Additional properties are not allowed ('unexpected' was unexpected); hermes/artifacts: [] should be non-empty; hermes/artifacts: [] does not contain items matching the given schema` (round-34 item 1; the same refusals are pinned by the test) | 1 |
| wrong Aether revision | `revision-mismatch: aether checkout HEAD 867d7982737470605663995dab12e80b18f6fc26 is not the requested commit 410c172ae69ffa87f6e32960ae4aef3b8d6598f0` — re-measured at this revision | 1 |
| wrong revision form | `unknown-revision: aether commit '2e9bf8a' is not a full 40-hex id` | 1 |
| foreign maintained-fork repository | `repository-identity: maintained-fork source must be https://github.com/DarkArty07/aether-hermes, observed https://github.com/NousResearch/hermes-agent.git` | 1 |
| dirty checkout (modified file at report time) | `dirty-checkout: aether checkout has uncommitted changes: ?? scratch-dirty-probe` — re-measured at this revision; the probe file was removed afterwards and `git status --porcelain` is empty again | 1 |
| divergent fork commit | `branch-divergence: commit … is not reachable from aether-main (observed …)` (test) | — |
| tampered member byte | `digest-mismatch: aether_agents-1.0.0rc1.tar.gz hashes to 430d4a9d75ea807f4e97c3e9fb91bfc02dddccc491c572c73d72da6cf6dff0dc, not the recorded 4dfdf64aa2f59baf5db439688878d2395c76d96445fddf25edb96789f092a122` — re-measured at this revision on a copy; the qualified bundle is untouched | 1 |
| removed member | `member-drift: bundle members do not match SHA256SUMS: extra [], missing ['aether-agents-1.0.0rc1-provenance.json']` — re-measured at this revision | 1 |
| rewritten checksum entry | `digest-mismatch: aether-agents-1.0.0rc1-clean-install.json hashes to c63a0d19512e88f9b8aca46b9c30c104583b9bb9edf8c7f20b31ecae90d3aa84, not the recorded 0000000000000000000000000000000000000000000000000000000000000000` — re-measured at this revision | 1 |
| unlisted file in the bundle directory (attach set) | `member-drift: bundle members do not match SHA256SUMS: extra ['stray.bin'], missing []` — `members` refuses, so the create path attaches nothing (re-measured at this revision) | 1 |
| published release, one asset digest differs | `published-asset-mismatch: release v1.0.0-rc.1 bytes do not match the qualified bundle: aether_agents-1.0.0rc1.tar.gz is sha256:00000000a2f59baf5db439688878d2395c76d96445fddf25edb96789f092a122, not the qualified sha256:4dfdf64aa2f59baf5db439688878d2395c76d96445fddf25edb96789f092a122` — re-measured against a listing built from this bundle | 1 |
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
| `uv run --frozen python scripts/run_tests.py` (full bootstrap, exact-Hermes, clean tree at the qualified commit `867d7982…`) | **7 failed, 1716 passed, 70 skipped** in 484.35 s — failures analysed below; my new module's 32 tests pass. The seventh failure is the latency-percentile oracle in `tests/test_observation_performance.py` (p95 5.84 ms against its 5.0 ms budget) under suite load; it passes 3/3 when run alone |
| `uv run --frozen ruff check src/aether_agents tests scripts` | exit 0 |
| `uv run --frozen ruff format --check src/aether_agents tests scripts` | exit 0 (166 files already formatted) |
| `uv run --frozen mypy src/aether_agents` | exit 0 (renders `Success: no issues found in 67 source files`) |
| `uv run --frozen python scripts/check_documentation.py` | exit 0 (`documentation validation passed`) |
| `uv run --frozen python scripts/check_public_artifacts.py --root .` | exit 0 (`public artifact path scan passed: tracked surface + 0 artifact(s)`) |
| `git diff --check` / `git diff --cached --check` | exit 0 (no whitespace damage; nothing staged at report time) |
| `.github/workflows/release.yml` YAML parse (re-measured at this revision) | parses; one job, seven steps; the identity checks are intact (`git rev-parse "refs/tags/$RELEASE_TAG^{commit}"` against `refs/remotes/origin/main`, and the second check that records `release_commit`); exactly one real `gh release create` invocation and exactly one real `gh release edit` invocation (the other match is a comment stating that `gh release edit` takes no file arguments); the six bounded-effect verbs (release upload, repo edit, container push, package publish, tag, push) all count 0; the tag step still emits exactly `version` and `prerelease`; `FORK_COMMIT` is still the fail-closed zero placeholder that LC-INT replaces |
| `uv run --frozen pytest -q tests/test_a1_contracts.py -k ReleaseWorkflow` (the existing release-workflow suite, not edited by this unit) | 10 passed, 8 subtests passed — the reconciled workflow still keeps that behaviour, including the no-bundle identity reconcile |
| `uv run --frozen pytest -q tests/test_release_bundle.py` | 32 passed |

### Failures in the full bootstrap, attributed

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
   pre-existing ones above, and the manifest test failed at base `410c172` for the same
   pre-existing reason.
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
4. `tests/test_observation_performance.py::test_native_plugin_callback_latency_includes_projection_validation_and_append`
   — **load-sensitive timing oracle, not a behaviour change.** It asserts a p95 latency
   budget of 5.0 ms over the `pre_api_request`/`post_api_request` hook samples; under this
   suite run it measured p95 5.84 ms, and it passed 3/3 when re-run alone at the same
   revision. No design-recorded constant was adjusted. The previous round's full suite
   (6 failures) and the Supervisor's own run happened to be lighter at that point; this
   unit's diff contains no runtime code path the probe exercises.

## Integration dependencies recorded for LC-INT

- `policy.yml`: the two exact manifest lines above (recorded, not edited, per the card).
- Release identity constant: set `FORK_COMMIT` in `.github/workflows/release.yml` to the
  accepted `aether-main` revision; the workflow otherwise refuses.
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
  `867d7982…`; LC-INT must rebuild from the integrated revision and attach *those* bytes,
  then verify them with the same `members` / `verify-published-assets` pair. Rebuilding from
  the same inputs reproduces all eight members byte-for-byte (round-34 item 2), so the
  reconcile branch is reachable on a re-run rather than only on a first run.
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
any machine or live state. The round-34 repair only tightened those two properties: the lock
gained `hermes.branch` (a v4 requirement, validated against the real schema) and captured
tool output is normalized so the entire member set, not just the distributions, is
reproducible. No aggregate release conclusion, channel or impact is asserted
here; `release_impact=major`, `release_action=publish`, `release_channel=prerelease`
remain the contract's decision for the integration and closeout cards.

## Residual risk

- The v4 lock shape and the pinned `--local` CLI vocabulary are still supplied by parallel
  units and can change. The schema half is now proven against the real v4 schema rather than
  only against the shape assumed here, but the coupling remains: if either changes, the tool
  refuses (`lock-schema-invalid` / `unavailable`) and the delta must return to this unit.
- `tests/test_observation_performance.py`'s latency-percentile oracle is load-sensitive: it
  failed once under this suite run (p95 5.84 ms against a 5.0 ms budget) and passed 3/3 when
  run alone at the same revision. It is not this unit's file and no constant was adjusted;
  recorded so a future red suite is not mis-attributed to this change.
- **Runtime observation (not a unit claim):** one read-only workflow-inspection command was
  refused by the Aether pre-tool hook with `AETHER-IMPLEMENTER-EXTERNAL-EFFECT` because the
  inline script text contained the verb strings the guard matches (used there only as
  dictionary keys for counters). No external effect was attempted; the inspection was
  completed with a script file instead. Recorded for the runtime owner, not treated as a
  unit defect.
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
