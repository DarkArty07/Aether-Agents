# RC6-DOCS — rc6 identity, launch/observer guidance, capability and policy-manifest reconciliation

**Unit**: RC6-DOCS (`t_0470a8e1`), role Implementer, worktree branch
`aether-agents-2/t_0470a8e1-rc6-docs-rc6-identity-launch-observer-gu`.
**Authority**: Objective Contract `oc_b5926701207812e8@v1` (SHA-256
`e7164c83862b747c7868706799c08ea63151ca388aa2dc2b1b89a40be33b01fc`), base
`d2874c2f3fc839a82fbaa96ece6edebab3856298`, material design
`specs/001-aether-v1-productization/plan-rc6.md`, Supervisor breakdown
`specs/001-aether-v1-productization/tasks-rc6.md` (`adc57c2b`) with shared decisions 1–10.
Never edited, staged or exact-copied the canonical contract.
**Delivered scope**: contract in-scope 7/11, D3; acceptance obligation AC-6 (guidance half) and
the reporting preconditions of AC-8; breakdown unit RC6-DOCS.
**Unit compatibility conclusion**: `patch`.

---

## 1. Consumed reviewed inputs

The three reviewed behavior-unit branches were merged into this worktree before the
documentation work, so that every documented surface and every manifest literal describes the
revision actually present (the rc5 DOCS lane used the same composition):

| Unit | Reviewed candidate | Merge commit in this worktree |
| --- | --- | --- |
| RC6-LIFE | `e9595d2e97aa85f2e0d7e4a501215865c0ab06ca` | `67f07678` |
| RC6-OBS | `00be3b17630e108c53994e15afb380f31dffada3` | `4fc9085d` |
| RC6-LAUNCH | `c79f5b14…` (launcher byte-identical to reviewed `c372b403`) | `69bc8717` |

Their evidence files (`RC6-LIFE.md`, `RC6-OBS.md`, `RC6-LAUNCH.md`) were read before writing
any claim, and the claims were re-verified against the merged source rather than copied from
prose. This unit's own authored commit stays inside its writable surface; the merges carry the
reviewed unit commits, which are not re-authored here.

---

## 2. Requirement → check → observed result → evidence

| Obligation | Source ref | Check actually run | Observed result | Evidence |
| --- | --- | --- | --- | --- |
| Identity is one coupled move: `VERSION` = `1.0.0rc6` | card item 1 | `uv run --frozen pytest -q tests/test_release_bundle.py::test_version_file_carries_the_objective_release_identity` | **PASS**: `VERSION` → package `1.0.0rc6`, semver `1.0.0-rc.6`, tag `v1.0.0-rc.6`, `prerelease=True` | `VERSION`; `tests/test_release_bundle.py` |
| README states the identity and the local-only/pre-stable status | card item 1; oracle (c) | `pytest -q tests/test_public_artifacts.py::test_readme_is_a_current_beta_portal_and_package_metadata_is_stable` | **PASS**: exactly one status paragraph carries package `1.0.0rc6`, display `1.0.0-rc.6`, annotated tag `v1.0.0-rc.6`, local-only/not pushed/not published, `release_impact = patch` / `release_action = prepare` / `release_channel = prerelease`, rc.2–rc.5 immutable and non-accepting, rc.1 published-but-rejected and not activatable, **not** stable `1.0.0`, **not** PyPI, **not** WSL2-qualified, #261 open; no published `rc.5`/`rc.6` link | `README.md`; `tests/test_public_artifacts.py` |
| `docs/index.md` carries the current candidate and navigates to the new guidance | card item 1 | review of the diff plus the documentation checker | **PASS**: current local-only `1.0.0rc6` statement; one added navigation entry for launch and recovery | `docs/index.md` |
| A new `CHANGELOG.md` section records the rc6 delta | card item 1 | review of the diff | **PASS**: `## 1.0.0rc6` section precedes rc5 and records identity, conclusions, predecessors, the lifecycle/observer/launch deltas, the guidance, the reconciled canonical surfaces, the manifest registration and the maintained-fork pin | `CHANGELOG.md` |
| Capability registry and generated reference are reconciled and up to date | card items 1 and 3; oracle (d) | `uv run --frozen python scripts/check_documentation.py` and `… --write` | **PASS** (`documentation validation passed`, exit 0) after the registry was corrected: `cli.reconcile` moved from `unsupported` to `partial` and now declares `--to`, `--dry-run`, `--yes` (the checker refused the revision with three `uncovered derived surface` errors before the fix), `cli.aether-launch` records the exact selection precedence, `cli.observe` and `observation.contract-observer` record the transient codes and the new module/regression paths | `docs/capabilities.toml`; `docs/reference/capabilities.md` |
| The repository's own `VERSION` satisfies the policy guard and unsupported identities are still refused | oracle (a) | `pytest -q tests/test_public_artifacts.py::test_canonical_base_manifest_guard_accepts_only_supported_package_identities`; direct read of the guard ERE | **PASS**: `1.0.0rc6` was added to the accepted-identity list, the guard accepts the repository's own `VERSION`, and the refused set (`1.0.0-rc.1`, `1.0.0rc`, `1.0`, `v1.0.0`, `01.0.0`, `1.0.0rc0`, `1.0.0.post1`, …) is still refused. The guard ERE itself needed no edit — verified, not assumed | `tests/test_public_artifacts.py`; `.github/workflows/policy.yml` |
| Golden observation summary replayed at the rc6 identity | oracle (f) | regeneration through the existing path (`tests/observation_helpers.complete_trace().summary()` at the installed rc6 product version, canonical JSON, `summary_id` recomputed by `aether_agents.observation.identity.summary_id`), then `pytest -q tests/test_observation_reducer.py::test_complete_pipeline_matches_the_reviewed_golden_summary_byte_for_byte tests/test_observation_brief_tool.py` | **PASS**: exactly three version-derived lines moved (`collector_version`, `reducer_version`, `summary_id`), the regenerated bytes equal the build's own pipeline output byte-for-byte, 40 passed / 1 skipped | `tests/fixtures/observation/complete-summary.json` (sha256 `30696a24d6c9a0aab95c74915397148faa618168fbd363236d972f245fde7aad`) |
| AC-6 guidance: in-project launch, `--project PATH`, fresh/Continue, `--resume latest`, visible ambiguity, `AETHER_PROJECT_ROOT` precedence, optional Bash/Zsh and Fish defaults with removal, no silent personal preference | card item 2; oracle (d) | `pytest -q tests/test_observation_usage_guidance.py` (three new nodes that exercise the real resolver and parser and assert the documented statements) | **PASS**: 8 passed; **decisive RED at base `d2874c2f`** (disposable worktree, same file): 3 failed — `aether reconcile --to active --dry-run` was `unrecognized arguments`, and the documented guidance and codes did not exist (5 pre-existing nodes passed there) | `docs/getting-started.md`; `tests/test_observation_usage_guidance.py` |
| Recovery surfaces documented exactly as implemented | card item 2 | documentation review plus the parser oracle in the same test file | **PASS**: `aether doctor [--project PATH] [--json]`, `aether reconcile --to active [--dry-run] [--yes] [--json]` (what it reconciles, its non-mutating preview, its idempotence, `UNSUPPORTED_RECONCILE_MODE` for `--to installed`/missing `--to`, `RECONCILE_REFUSED` before mutation for an unauthenticated legacy route) and `aether rollback [VERSION]` are recorded; every documented form parses | `docs/guides/lifecycle.md`; `docs/reference/cli.md`; `docs/reference/limitations-and-troubleshooting.md` |
| Bounded observer codes documented as retryable, settled state still succeeding | card item 2 | documentation review plus the source-literal tie in the guidance test | **PASS**: `STATE_BUSY`/`AETHER-OBSERVE-BUSY` and `CATCHUP_INCOMPLETE`/`AETHER-OBSERVE-CATCHUP-INCOMPLETE` are recorded as retryable contention that is never a successful, fresh or empty summary, `STATE_UNREADABLE`/`AETHER-OBSERVE-STATE-UNREADABLE` as fail-closed, and the same literals exist in `src/aether_agents/commands/observe.py` and `src/aether_agents/observation/brief.py` | `docs/guides/observation.md`; `.aether/skills/aether-observe/SKILL.md` |
| Canonical surfaces reconciled without weakening a requirement | card item 3 | review of every normative diff against the frozen units and the merged source | **PASS**: `specs/001-…/spec.md` (rc6 amendment note plus A1-FR-043 selection, A1-FR-063 bounded reconciliation, A1-FR-067b transient codes), `specs/001-…/contracts/cli.md` (`aether` synopsis + selection, `reconcile` build-level scope, `observe` code bullet), `specs/002-…/spec.md` (OBS-FR-026 and §13.1). No requirement was lowered and no requirement intent was re-decided | `specs/001-aether-v1-productization/spec.md`; `specs/001-aether-v1-productization/contracts/cli.md`; `specs/002-aether-contract-observation/spec.md` |
| Policy manifest carries this contract and every added path present at this revision | card item 4; oracle (b) | `pytest -q tests/test_public_artifacts.py::test_canonical_base_manifest_matches_tracked_non_specs_files` | **PASS**: four literal lines added (see §4). The RC6-LIFE handoff's note about `website/tsconfig.json` was checked and corrected: that path is already in the heredoc at base; the only base mismatch was the missing rc6 contract line | `.github/workflows/policy.yml` |
| No operator-local path, secret, or banned legacy name in a tracked artifact | oracle (e) | `uv run --frozen python scripts/check_public_artifacts.py`; `git grep` for the policy workflow's banned-name set | **PASS**: `public artifact path scan passed: tracked surface + 0 artifact(s)`; no banned name; the new guidance uses `/path/to/…` placeholders only | `scripts/check_public_artifacts.py` |
| Static gates | card verification | `ruff check src/aether_agents tests scripts`, `ruff format --check src/aether_agents tests scripts`, `mypy src/aether_agents` | **PASS**: All checks passed; 178 files already formatted; no issues in 69 source files | terminal log, this revision |
| Focused lane | card verification | `pytest -q tests/test_documentation.py tests/test_public_artifacts.py tests/test_release_bundle.py tests/test_observation_usage_guidance.py` and the observation modules touched by the golden fixture | **PASS**: 69 passed (identity lane), 251 passed / 1 skipped (with the reducer, brief-tool, query-parity and passive-startup modules), 201 passed on the final re-run of the identity+reducer lane | terminal log, this revision |

### Oracle discipline (which checks are decisive)

- Decisive RED: the three new guidance nodes fail at base `d2874c2f` for the documented
  reasons above. They are new guidance/parser oracles, not defect reproductions.
- The documentation checker is a real gate, not prose: it refused this revision before the
  capability reconciliation with `uncovered derived surface: cli.option.aether.reconcile.--to
  / --dry-run / --yes`.
- Preservation oracles: the manifest equality test, the release-bundle identity test, the
  pre-existing usage-guidance nodes and the public-artifact scan already existed and were kept
  meaningful rather than relaxed.

---

## 3. rc5-era evidence reuse ledger

`tasks-rc6.md` shared decision 7 allows an rc5-era item to be cited only where its artifact
identity and criterion applicability still match after the rc6 delta. Applied to this unit's
delta (identity/capabilities/manifest/tests and the documentation of target-owned projections,
the launcher scrub, the passive observer and the bounded codes):

| rc5-era evidence | Current after the rc6 delta? | Reason |
| --- | --- | --- |
| `DOCS.md` | **Superseded by this unit** (retained as rc5 history) | It is the direct predecessor record of exactly the surfaces this unit moved: rc5 identity, README/index/CHANGELOG wording, capability registry statements, the rc5 manifest registration and the coupled test oracles. Every one of those statements is restated at rc6 here. Its rc5-specific identity values must not be cited as current. |
| `GW-SERVICE.md` | **Partially current; mechanism statements superseded** | The boundary it established (Hermes owns and materializes `hermes-gateway-morfeo.service`; Aether neither writes nor byte-compares it; semantic doctor; no drop-in or wrapper unit) still holds and is restated in `docs/guides/lifecycle.md`. Its statements about *where the executing source decides unit bytes* were overtaken by RC6-LIFE: the exact-version equality discriminator is gone, projection bytes are target-generated and parent-validated, and `src/aether_agents/lifecycle.py` changed twice since that evidence. For the service-boundary criterion it is reusable as history and corroboration; for mechanism or revision-identity claims it is not. |
| `TUI-PRESERVE.md` | **Conclusions current; launcher-internal evidence superseded** | The preserved conclusions it certifies — Desktop/WSL actions target the stable `runtime/current/venv/bin/aether` entry with the exact project root and `--resume latest`, launch performs no npm/build, and the locked `hermes-source` tree is not mutated — still hold and are re-verified at rc6 by RC6-LIFE (`test_desktop_and_wsl_projections_point_to_stable_aether_entry_point`) and RC6-LAUNCH. Its internal receipts for `src/aether_agents/launcher.py` are invalidated by the rc6 scrub/target-binding change and are replaced by `RC6-LAUNCH.md`. |
| `LG-CLI.md` | **Source facts current; receipts replaced by direct evidence** | It is the origin of the exact project-selection rules this unit now documents. The rules were not changed by any rc6 unit, and this unit re-verified them at the rc6 revision with its own resolver tests rather than citing the rc5 receipts; `src/aether_agents/launcher.py` is no longer the same artifact, so the old receipts cannot be claimed as unchanged-identity evidence. |
| `LG-KNOW.md` | **Current** | No rc6 unit changed the knowledge/Graphify surface, its implementation paths or its verification set; its criterion applicability is untouched by this objective, so it may be cited as unchanged-identity evidence. |
| `RS-PROOF.md` | **Superseded as decision evidence; retained as history** | It certifies the rc3/rc4 contamination two-hop restoration of `src/aether_agents/lifecycle.py`, which RC6-LIFE changed materially (target-reader validation, target-owned projections, byte-exact compensation). Its criterion is also not this objective's criterion: rc6 requires the frozen mixed-version cycle rc5 → candidate → rc5 → candidate owned by RC6-QUAL. |

Not in the ledger list and deliberately not re-cited by this unit: the rc2/rc3 identity records,
the rc5 quarantine and activation receipts, and private recovery/diagnostic receipts.

---

## 4. Manifest lines

Added literally to the `.github/workflows/policy.yml` heredoc in this commit (four lines):

```text
.aether/objective-contracts/oc_b5926701207812e8/v1.md
src/aether_agents/observation/capture/retained_index.py
tests/test_observation_passive_startup.py
tests/test_observation_query_parity.py
```

Left pending for `RC6-INT` to apply mechanically after `RC6-QUAL` runs (the files do not exist
at this revision, so adding them now would make the equality oracle fail):

```text
scripts/qualify_mixed_version_lifecycle.py
tests/test_mixed_version_lifecycle_qualification.py
# plus any fixture path RC6-QUAL records in its handoff
```

No tracked non-`specs/` file was removed or renamed by this unit, and no other unit recorded a
manifest literal for a file added at or before this revision. The four behavior-unit/observation
literals above are the complete set the reviewed units recorded for files that exist here.

---

## 5. Direct versus reused attribution

**Direct work in this unit (implemented and verified here)**

- The coupled rc6 identity move: `VERSION`, `README.md`, `docs/index.md`, `CHANGELOG.md`,
  `docs/capabilities.toml`, the regenerated `docs/reference/capabilities.md`,
  `tests/test_public_artifacts.py`, `tests/test_release_bundle.py` and the regenerated golden
  observation summary.
- The AC-6 public guidance (launch, default selection, `AETHER_PROJECT_ROOT` precedence,
  ambiguity, fresh/Continue, `--resume latest`, optional Bash/Zsh and Fish defaults with their
  removal commands, the no-silent-personal-preference statement) and the three new guidance
  oracles that exercise the real resolver and parser.
- The recovery-surface documentation (`doctor`, the bounded `reconcile --to active`, `rollback`)
  and the bounded observer transient codes in the guides, the CLI reference, the limitations
  page, the project observation skill and the capability registry.
- The canonical reconciliation of `specs/001-…/spec.md`, `specs/001-…/contracts/cli.md` and
  `specs/002-…/spec.md` at the surfaces the finalized design already decides.
- The policy-manifest completion for this revision.

**Consumed, not re-authored**

- The reviewed behavior of RC6-LIFE, RC6-OBS and RC6-LAUNCH, merged read-only as composition.
  Every documented claim about those surfaces was re-read from the merged source; nothing was
  invented and no behavior code was edited by this unit.
- The golden-summary regeneration path from the reducer fixture (`tests/observation_helpers.py`),
  the identity helper (`aether_agents.observation.identity.summary_id`) and the existing
  documentation generator (`scripts/check_documentation.py --write`).
- rc5-era evidence only as recorded in the §3 ledger.

**Not claimed**

- No live installation, service, activation, tag, release, issue or remote effect was performed
  by this unit; the only board access was a read-only SQLite inspection of card titles/status.
- No aggregate release decision: an independent Supervisor review of this unit and the
  downstream integrated verification remain outstanding.

---

## 6. Residual risk and environment limits

- **Observation follow-up is open.** Card `t_6020b35d` (RC6-OBS-2) is running and reworks hook
  binding claims and absence-based emission serialization. This unit's observer statements are
  deliberately held at the durable contract level (passive registration/hooks, asynchronous
  retained-binding restore, one validated index per catch-up snapshot, no attribution to a
  guessed trace, the fixed retryable/unreadable codes) and do not pin the internal coverage
  window, so an OBS-2 mechanism change should not invalidate them. If OBS-2 nevertheless
  changes an *observable* public surface (codes, schemas, tool actions), the affected
  documentation and capability statements must be re-reconciled before close; the observation
  post-review discrepancy is **not** claimed retired here.
- **Plan advancement.** Morfeo advanced `plan-rc6.md` with the owner-confirmed unattended
  operating disposition (`0b462158473c66d20a743aa09c689d4d262a798c`); `RC6-INT` owns
  incorporating it. This unit pins no plan revision in its artifacts, so the documentation does
  not conflict with that commit, but the integration unit should confirm the disposition does
  not add a documented public surface.
- **Manifest is intentionally one revision short.** The three RC6-QUAL paths are recorded but not
  applied here; the equality oracle passes at this revision only because those files are not yet
  tracked. RC6-INT must apply them (and any RC6-QUAL fixture line) before running the oracle.
- **Identity is not acceptance.** The rc.1–rc.5 tags and activation history remain immutable and
  are not acceptance; the published rc.1 stays rejected and non-activatable.
- **Not qualified here.** Live candidate readiness, the mixed-version cycle, WSL2, PyPI/OIDC and
  the local annotated tag belong to RC6-QUAL/RC6-INT/RC6-CLOSE. Documentation guidance is
  verified against fixtures and the real parser, not against a live installed candidate.
- **Environment**: all checks ran in the isolated worktree environment (`uv run --frozen …`) on
  the merged candidate revision. The disposable RED worktree used for the base comparison was
  created outside the repository and removed after use. No operator-local absolute path appears
  in any tracked artifact.

---

## 7. RC6-DOCS-2 — correction of the shell-default, recovery-preamble and identity-value claims

**Unit**: RC6-DOCS-2 (`t_e90863a1`), role Implementer, branch
`aether-agents-2/t_e90863a1-rc6-docs-2-correct-u1-shell-default-exam`, based on this unit's
accepted tip `80ce317809d4413a718b3fec412c543b17e2c3ab`. Authority unchanged: Objective Contract
`oc_b5926701207812e8@v1`, material design `plan-rc6.md` §U1 (line 80). Docs-only fix forward: no
behavior code, no contract text, no card-state reopen, no release, remote or board effect.

### 7.1 Requirement → check → observed result → evidence

| # | Requirement | Check actually run | Observed result | Evidence |
| --- | --- | --- | --- | --- |
| D1 | §U1: teach optional `AETHER_PROJECT_ROOT` selection and its precedence over cwd, with Bash/Zsh **and** Fish examples and removal commands, generic paths | `uv run --frozen pytest -q tests/test_observation_usage_guidance.py`, shell-default assertions scoped to the section | RED at `80ce3178`: `AssertionError: takes precedence over the current directory`. GREEN on this candidate: 9 passed. | `docs/getting-started.md` §"Optional personal shell defaults"; `tests/test_observation_usage_guidance.py` |
| D2 | The recovery preamble must not deny the rollback surface's own release selection, and must keep the refusals that are true of all three | same lane, recovery assertions: negative pin on the retired sentence plus the four retained claims | RED at `80ce3178`: `'None of them selects a different release' is contained here`. GREEN on this candidate. | `docs/guides/lifecycle.md` §"Recovery surfaces"; `tests/test_observation_usage_guidance.py` |
| D3 | State precisely which identity value fails and which is resolved, in all three named surfaces, with the registry regenerated | same lane, identity-split oracle over `docs/getting-started.md`, `docs/reference/cli.md`, `docs/capabilities.toml` and the generated `docs/reference/capabilities.md`, plus the resolver exercise | RED at `80ce3178`: `('docs/getting-started.md', 'an empty --project value is refused')`. GREEN on this candidate. | the four surfaces listed; `tests/test_observation_usage_guidance.py` |

RED method: `git stash push -- docs/` kept the candidate test module while restoring the base
documents at `80ce3178`, the lane then exited 1 with exactly the three failures above, and
`git stash pop` restored the candidate. Exactly the three corrected functions fail at base; the
other six pass. Recorded as observed, not inferred.

### 7.2 Direct measurement behind the corrected identity wording

A disposable probe outside the repository imported the packaged launcher from this worktree with
isolated `HOME`/`XDG_*`/`TMPDIR`/`HERMES_HOME` and every `AETHER_*`/`HERMES_*` selector cleared, then
called `_resolve_project` against a fixture project. Observed: relative `--project alpha` and
`projects_root/alpha` resolved to the fixture root and returned its portable project id; empty
`--project` was refused with `project path must not be empty`; `AETHER_PROJECT_ROOT=relative/project`
was refused with `AETHER_PROJECT_ROOT must be an absolute path`; empty `AETHER_PROJECT_ROOT` was
refused with `AETHER_PROJECT_ROOT must not be empty`; `AETHER_PROJECT_ID=not-a-uuid` was refused with
`is not a valid canonical UUID`. The durable oracle for the same split is
`test_documented_identity_value_split_matches_the_implemented_resolver`, together with the extended
assertion inside `test_documented_project_selection_precedence_matches_the_implemented_resolver`.

### 7.3 Same-claim-class sweep (`docs/**`, `README.md`)

- Fixed: `docs/guides/lifecycle.md` §"Recovery surfaces" was the only surface claiming that no
  recovery surface selects a different release.
- Reviewed and left unchanged as accurate: the reconcile-scoped "never selects another release"
  statements (`docs/reference/cli.md`, `docs/reference/capabilities.md`, `docs/capabilities.toml` and
  the canonical `specs/001-…/contracts/cli.md`), which bind `reconcile --to active` only; and the
  update-scoped "no other surface stages or activates a release", which describes staging or
  activating a *new* release, while rollback re-points product-owned pointers to a release already
  recorded as coherent.
- `README.md` needed no correction: its single rollback sentence ("rollback restores product code
  without rolling user state backward") is accurate and does not deny the release switch.

### 7.4 Gates

| Gate | Command | Result |
| --- | --- | --- |
| Documentation registry | `uv run --frozen python scripts/check_documentation.py` (with `--write` to regenerate the reference) | `documentation validation passed`; the regenerated diff is confined to the one notes paragraph |
| Guidance/documentation/artifact lane | `uv run --frozen pytest -q tests/test_observation_usage_guidance.py tests/test_documentation.py tests/test_public_artifacts.py` | 36 passed (9 + 18 + 9) |
| Manifest equality | `… pytest -q tests/test_public_artifacts.py::test_canonical_base_manifest_matches_tracked_non_specs_files` | 1 passed; no tracked path added, so `manifest_lines: none` |
| Public artifact scan | `uv run --frozen python scripts/check_public_artifacts.py` | `public artifact path scan passed: tracked surface + 0 artifact(s)` |
| Lint / format / types | `ruff check src/aether_agents tests scripts`; `ruff format --check src/aether_agents tests scripts`; `mypy src/aether_agents` | all clean; 178 files already formatted; 69 source files type-clean |

Isolation: every check ran with disposable `HOME`, `XDG_STATE_HOME`, `XDG_DATA_HOME`,
`XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, `TMPDIR` and `HERMES_HOME`, and with every `HERMES_*`/`AETHER_*`
routing variable unset. No live installation, gateway, TUI, service, board, contract or observation
store was touched; no push, PR, merge, tag, release, activation, service restart or issue mutation
occurred.

### 7.5 Direct versus reused attribution

**Direct work in this unit**: all three document corrections and the registry regeneration; the new
and extended oracle assertions and the resolver exercise; the claim-class sweep; every gate above.
**Reused, re-verified rather than trusted**: the design steward's defect report (consumed as a defect
list — each defect was re-measured from source and behavior before editing), the existing
documentation generator `scripts/check_documentation.py --write`, the existing guidance oracles
(extended, not replaced), and the accepted RC6-LAUNCH/RC6-LIFE behavior read from the merged source
rather than re-authored.
**Not claimed**: no independent review of this correction, no terminal integration, no release or
aggregate compatibility conclusion (the unit-level impact stays `patch`), and no live-candidate
qualification.

### 7.6 Residual limits

- **Contract wording stays broader than the implementation.** `specs/001-…/spec.md` (A1-FR-043) and
  `specs/001-…/contracts/cli.md` still state that "an empty or relative identity MUST fail visibly",
  while the accepted launcher refuses only an empty `--project` value and resolves a relative
  `--project PATH`. Those files are outside this unit's writable surface, so the discrepancy is
  reported on the card for an owner-side decision instead of being softened in the docs or changed in
  code. The canonical sentence is unchanged; the documents now describe implemented behavior.
- **One oracle is not RED at base.** The relative-`--project` resolver pin passes at `80ce3178` as
  well as on this candidate, because the behavior is unchanged and only the prose was wrong. It is
  recorded as a grounding pin for the corrected wording, not as a RED assertion; the three prose
  assertions carry the RED evidence.
- **Bounded scope.** Only the three reported discrepancies and their same-claim-class neighbours were
  reviewed; this is not a general documentation audit, and no other guide's wording was changed.
- **Environment**: isolated worktree at the accepted base; the RED comparison used `git stash` on
  tracked `docs/` paths plus a probe script outside the repository. No operator-local absolute path
  appears in any tracked artifact.
