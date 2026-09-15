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

## Deliverables

| Path | Change |
| --- | --- |
| `VERSION` | reconciled to `1.0.0rc1` |
| `CHANGELOG.md` | new `1.0.0rc1` entry stating the pre-stable RC scope, no PyPI/index publication and unverified WSL2 |
| `scripts/release_bundle.py` | new tool: `build`, `verify`, `members` and `verify-published-assets` subcommands |
| `tests/test_release_bundle.py` | new focused module, 31 tests |
| `.github/workflows/release.yml` | reconciled: tag/identity validation preserved, the tagged commit is built and qualified, the create path attaches the tool's verified eight-member set, and a reconcile re-verifies the published assets instead of attaching nothing |

Qualified commit: `4688b6d9c197b5531a80e1389f958fd0e9b88304` (clean checkout, remote
`https://github.com/DarkArty07/Aether-Agents`). Maintained-fork input:
`https://github.com/DarkArty07/aether-hermes` commit
`54eeb56dabefc98821d696656ed58c55dd777346`, clean checkout, proven reachable from
`refs/heads/aether-main` (local branch tip; remote-tracking tip
`bb5e9a422f3135371557e75bcd1db01c5f8fc3ba` — the candidate is three commits ahead because
it is not published yet).

## Produced bundle members (byte sizes and SHA-256)

| Member | Bytes | SHA-256 |
| --- | --- | --- |
| `aether_agents-1.0.0rc1-py3-none-any.whl` | 658758 | `6fada306450bfed68fb0b8ce2cade9ea2a6fac73b02088a573aee6dca2ede254` |
| `aether_agents-1.0.0rc1.tar.gz` | 1008615 | `b06a4f7ccf1c879a1136a3b226833df42cbaf3f6c9ca16e3972bb96041f1f248` |
| `aether-hermes-source-54eeb56dabefc98821d696656ed58c55dd777346.tar.gz` | 65892746 | `cf766ef8665c810b85d93e990e621192110e78a27ecb692170008c217dd42542` |
| `aether-agents-1.0.0rc1-release-lock.json` | 2327 | `df04fff0ae12965e54a844be20c7a96d025f77422c72a2bc8aece0b71935ee82` |
| `aether-agents-1.0.0rc1-provenance.json` | 2914 | `574bec6a4b9b55a6d91b352870760641666454058f38f4eb1cb4765fc886aac0` |
| `aether-agents-1.0.0rc1-package-members.json` | 2453288 | `5b89f1de0675126d8650c480ea9c83c31c9c0a84f3e9ffb29dd31788c2413f7c` |
| `aether-agents-1.0.0rc1-clean-install.json` | 14358 | `b665a02df5891bdf5eb915d9f98a0fb62dd494924fc718d729b38adfb540f7b1` |
| `SHA256SUMS` | 767 | `08b9f2db5165e298ed01dac0b8d2d40470fb081abc2a328b29e265c9a84c28eb` |

Candidate bundle directory for this qualification: `/tmp/lc-reltool-bundle-r3`.

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
           "git_tag": "v1.0.0-rc.1", "git_commit": "4688b6d9…", "python_requires": ">=3.11,<3.14",
           "observer_requirements_sha256": "798d9f1f…", "wheel_sha256": "6fada306…"},
"hermes": {"source_mode": "maintained_fork", "repository": "https://github.com/DarkArty07/aether-hermes",
           "version": "0.20.1", "commit": "54eeb56d…", "source_tree_sha256": "4f0c6fab…",
           "python_requires": ">=3.11,<3.14", "artifacts": [one source archive with URL+digest]},
"profile_bundle": {"version": "2", "sha256": "31915524…", "roles": ["morfeo","supervisor","implementer"]}
```

`hermes.source_tree_sha256` is the product's own deterministic materialization digest of
the exact commit (`lifecycle._materialize_git_archive` + `lifecycle._tree_sha256`), and
the bundle's archive is proven to materialize that same tree, so the lock, the archive and
the doctor/activation comparison use one identity.

## Verification actually run (raw results)

Command form: `uv run --frozen python scripts/release_bundle.py …`.

| Check | Result |
| --- | --- |
| `build --aether-checkout <checkout> --aether-commit 4688b6d… --fork-checkout <fork> --fork-commit 54eeb56… --work <scratch> --out <bundle> --pre-integration` | exit 0 in 57.3 s; 8 members written; `finished_bundle: {members_rehashed: 7, plain_text_scan: clean}` (the counter is the seven members `SHA256SUMS` covers; the checksum file is the eighth, and `members` reports all eight) |
| Byte reproducibility from the same commit (tool builds twice and compares) | `{"wheel": true, "sdist": true}` with `SOURCE_DATE_EPOCH` pinned to the commit timestamp (`1789450620`) |
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
| `verify --bundle <bundle> --expect-aether-commit 4688b6d… --expect-fork-commit 54eeb56… --pre-integration --clean-install` | exit 0 in 37.7 s: every member re-hashed against `SHA256SUMS`, wheel/archive re-matched against the lock, scans re-run, fresh artifact-installed handshake repeated |
| `members --bundle <bundle>` | exit 0; prints the eight absolute member paths in sorted order, `SHA256SUMS` first |
| `verify-published-assets --bundle <bundle> --tag v1.0.0-rc.1 --assets -` (the workflow's stdin form) against the qualified digests | exit 0: `published release carries the qualified bytes: v1.0.0-rc.1` and the eight names |
| The shipped release step executed for real (extracted step script + real `scripts/release_bundle.py` + stub `gh` that logs argv) | create path: `release view` then `release create` with exactly the eight qualified paths (`--verify-tag --generate-notes --prerelease`); reconcile path: `release view` then `release edit` with **no file arguments** and the verification in between; drift cases: non-zero exit, diagnostic on stderr, **no** create/edit invocation logged. Tests: `test_release_step_attaches_exactly_the_qualified_member_set`, `test_release_step_reconcile_verifies_the_release_and_passes_no_files`, `test_release_step_reconcile_fails_closed_before_editing_anything`, `test_release_step_refuses_a_bundle_that_drifted_before_attaching` |
| Real `gh` interface check (read-only, against a public release) | `gh release view --json assets --jq '.assets[] | "\(.name)\t\(.digest // "")"'` emits `name<TAB>sha256:<hex>` lines — the shape the tool parses; `gh release edit --help` shows `USAGE: gh release edit <tag>`, with no `[<filename>...]` (unlike `gh release create`, whose help documents asset files), and `gh release edit <tag> --prerelease f1 f2` is rejected locally with `accepts 1 arg(s), received 3` |

### Refusals proven (negative evidence)

| Case | Observed | Exit |
| --- | --- | --- |
| strict mode at this revision (no `--pre-integration`) | `lock-schema-drift: the repository schema declares schema_version 3; the maintained-fork schema is supplied by the release-runtime unit and only exists after integration` | 1 |
| wrong Aether revision | `revision-mismatch: aether checkout HEAD 4688b6d… is not the requested commit 410c172…` | 1 |
| wrong revision form | `unknown-revision: aether commit '2e9bf8a' is not a full 40-hex id` | 1 |
| foreign maintained-fork repository | `repository-identity: maintained-fork source must be https://github.com/DarkArty07/aether-hermes, observed https://github.com/NousResearch/hermes-agent.git` | 1 |
| dirty checkout (modified file at report time) | `dirty-checkout: aether checkout has uncommitted changes: M CHANGELOG.md` | 1 |
| divergent fork commit | `branch-divergence: commit … is not reachable from aether-main (observed …)` (test) | — |
| tampered member byte | `digest-mismatch: aether_agents-1.0.0rc1-py3-none-any.whl hashes to e52af9aa…, not the recorded 6fada306…` | 1 |
| removed member | `member-drift: bundle members do not match SHA256SUMS: extra [], missing ['aether-agents-1.0.0rc1-provenance.json']` | 1 |
| rewritten checksum entry | `digest-mismatch: aether-agents-1.0.0rc1-clean-install.json hashes to b665a02d…, not the recorded 00000000…` | 1 |
| unlisted file in the bundle directory (attach set) | `member-drift: bundle members do not match SHA256SUMS: extra ['stray.bin'], missing []` — `members` refuses, so the create path attaches nothing | 1 |
| published release, one asset digest differs | `published-asset-mismatch: release v1.0.0-rc.1 bytes do not match the qualified bundle: aether_agents-1.0.0rc1.tar.gz is sha256:0000…, not the qualified sha256:b06a4f7c…` | 1 |
| published release missing the checksum file | `published-asset-drift: release v1.0.0-rc.1 does not carry the qualified bundle: missing ['SHA256SUMS'], unexpected []` | 1 |
| published release carrying an extra asset | `published-asset-drift: … does not carry the qualified bundle: missing [], unexpected ['aether-agents-1.0.0rc1-unexpected.json']` | 1 |
| published asset without a digest (older upload) | `published-asset-unverifiable: release v1.0.0-rc.1 assets carry no digest, so the qualified bytes cannot be verified: ['aether_agents-1.0.0rc1-py3-none-any.whl']` | 1 |
| asset listing line without the `name<TAB>digest` separator | `published-assets-malformed: expected '<name>\t<digest>' per published asset, observed 'SHA256SUMS'` | 1 |
| operator path in Aether-authored bytes | `private-path-scan: Aether-authored public bytes contain operator paths: …` (test; also caught a real leak in an earlier revision of the report during this unit's own runs) | 1 |
| credential material | `secret-scan` refusal (test) | 1 |

Every reconcile refusal above happens before any `gh release edit` invocation; the
behavioural test asserts that no create/edit call is logged for the drifting, incomplete
and digest-less releases.

## Repository gates (raw results)

| Gate | Result |
| --- | --- |
| `uv build` | exit 0; `dist/aether_agents-1.0.0rc1.tar.gz`, `dist/aether_agents-1.0.0rc1-py3-none-any.whl` |
| `uv run --frozen python scripts/run_tests.py` (full bootstrap, exact-Hermes, at the repair commit) | **6 failed, 1716 passed, 70 skipped** in 487.58 s — failures analysed below; my new module's 31 tests pass |
| `uv run --frozen ruff check src/aether_agents tests scripts` | exit 0 |
| `uv run --frozen ruff format --check src/aether_agents tests scripts` | exit 0 (166 files already formatted) |
| `uv run --frozen mypy src/aether_agents` | exit 0 (renders `Success: no issues found in 67 source files`) |
| `uv run --frozen python scripts/check_documentation.py` | exit 0 (`documentation validation passed`) |
| `uv run --frozen python scripts/check_public_artifacts.py --root .` | exit 0 (`public artifact path scan passed: tracked surface + 0 artifact(s)`) |
| `git diff --check` / `git diff --cached --check` | exit 0 (no whitespace damage; nothing staged at report time) |
| `.github/workflows/release.yml` YAML parse | parses; one job; the tag step still emits exactly `version` and `prerelease` |
| `uv run --frozen pytest -q tests/test_a1_contracts.py -k ReleaseWorkflow` (the existing release-workflow suite, not edited by this unit) | 10 passed, 8 subtests passed — the reconciled workflow still keeps that behaviour, including the no-bundle identity reconcile |
| `uv run --frozen pytest -q tests/test_release_bundle.py` | 31 passed |

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

## Integration dependencies recorded for LC-INT

- `policy.yml`: the two exact manifest lines above (recorded, not edited, per the card).
- Release identity constant: set `FORK_COMMIT` in `.github/workflows/release.yml` to the
  accepted `aether-main` revision; the workflow otherwise refuses.
- The workflow runs the tool in **strict** mode: once the released tree carries the
  schema-4 maintained-fork release lock and the pinned
  `aether update --local --aether-checkout --aether-commit --fork-checkout --fork-commit`
  option surface, the two conditions this unit recorded as `unavailable`/
  `not_applicable` under `--pre-integration` become enforced. If the integrated v4 schema
  or the pinned CLI vocabulary differs from the shapes assumed here, the tool fails
  closed with `lock-schema-invalid` / `unavailable` and the delta must come back to this
  unit rather than being worked around.
- Reconcile is verification-only by construction: a re-run or `workflow_dispatch` for a tag
  whose release already exists succeeds only when that release carries these exact bytes.
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
any machine or live state. No aggregate release conclusion, channel or impact is asserted
here; `release_impact=major`, `release_action=publish`, `release_channel=prerelease`
remain the contract's decision for the integration and closeout cards.

## Residual risk

- The v4 lock shape and the pinned `--local` CLI vocabulary are supplied by parallel
  units; the strict-mode coupling above is the one place this unit's output meets their
  bytes, and the tool refuses rather than guessing if they disagree.
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
