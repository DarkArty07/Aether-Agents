# U3 evidence — current docs corpus, capability registry and documented limits

**Unit:** U3 of the #552 execution breakdown (`git show
6b989bf04613d935a32ffed2734c6a46b28ae088:specs/documentation-consistency/tasks.md`).
**Base revision:** `62ec14653baa8f84449f41a68d64cf64d50939d6`.
**Candidate revision:** `741c0fd1baaf9fc014a9224f453158386f12c03e` (one local commit).
**Scope audited:** the 20 tracked current `docs/` Markdown pages, `docs/capabilities.toml`
and its generated `docs/reference/capabilities.md`, verified against current source,
`VERSION`, the local tag set and the capability registry.

This note is a finding inventory for the aggregate record. It grants no authority and is
not an acceptance claim.

## Confirmed findings and corrections

| # | Finding | Cited source at base | Correction | Files changed |
| --- | --- | --- | --- | --- |
| U3-1 | The limits table called source `1.0.0rc16` / `1.0.0-rc.16` the current release candidate while `VERSION` reads `1.0.0rc17` and `main` carries RC17 plus later unreleased source. The same Markdown line also concatenated `|| State export \| ...`, so no separate current-limit row was formed (line had 9 pipe fields instead of 3 cells). | `docs/reference/limitations-and-troubleshooting.md:18`; `VERSION:1`; `README.md:5-24`; `docs/index.md:7-15` | Split into three valid rows: **Release-candidate scope** now states the development source tree, the still-`1.0.0rc17` `VERSION` string, the local `v1.0.0-rc.17` tag at an earlier revision and the unreleased Lab/Monitor retirement, with `aether doctor --json` as the only portable route to installed state; **Historical RC16 candidate** retains the RC16 facts as attributable history with the exact versioned locators (tag `v1.0.0-rc.16`, fork commit, tree, digest, HLP-428/433, schema-5 emission); **State export** now stands as its own current-limit row. | `docs/reference/limitations-and-troubleshooting.md` |
| U3-2 | The Morfeo MCP guide directed activation at "the managed rc9-then-rc10 update path" in the present tense. RC9 and RC10 are historical bridge candidates in the owning stage specification. | `docs/guides/morfeo-mcp.md:20`; `specs/008-morfeo-mcp/spec.md:31,35-37` | The guide now names the managed `aether update` preparation/activation boundary and labels the RC9/RC10 bridge as history in `specs/008-morfeo-mcp/spec.md` rather than as current source behaviour. | `docs/guides/morfeo-mcp.md` |
| U3-3 | Five current pages described the maintained-fork release lock as `schema_version` 4 only, while current preparation emits schema 5 and readers accept 4 and 5. | `docs/reference/limitations-and-troubleshooting.md:17`; `docs/reference/cli.md:59`; `docs/guides/policy-and-recovery.md:81`; `docs/getting-started.md:111`; `docs/product-boundary.md:45`; source: `scripts/release_bundle.py:43,917,948`, `src/aether_agents/lifecycle.py:486,504-517,5794-5796`, `specs/001-aether-v1-productization/contracts/release-lock.schema.json` | Each page now distinguishes the emitted schema (5, with the closed `hermes.extras` allowlist) from the accepted reader schemas (4 and 5, where schema 4 carries no extras) without claiming an installed release. | `docs/reference/limitations-and-troubleshooting.md`, `docs/reference/cli.md`, `docs/guides/policy-and-recovery.md`, `docs/getting-started.md`, `docs/product-boundary.md` |
| U3-4 | The documentation index stated the fork binding as "release-lock schema 4 or 5 `maintained_fork`" without distinguishing emission from read compatibility. | `docs/index.md:18` | Reworded to name the emitted schema 5 plus the closed `hermes.extras` allowlist and the schema-4/5 read range. | `docs/index.md` |
| U3-5 | The capability registry — the sole implementation-status owner — asserted the maintained-fork identity under `schema_version` 4 only. | `docs/capabilities.toml:136` (`lifecycle.immutable-release-and-update-boundary`) | Corrected in the owning registry first: current preparation emits `schema_version` 5 with the closed allowlist, readers accept 4 and 5, schema 4 carries no extras, and the rc3 activation evidence remains attributed history. | `docs/capabilities.toml` |
| U3-6 | The generated capability reference had to follow the registry owner. | `docs/reference/capabilities.md` (generated) | Regenerated exactly once with `uv run --frozen python scripts/check_documentation.py --write`; the generated diff is the single registry note line and nothing else. The no-write check then passed. | `docs/reference/capabilities.md` (generated) |

## Reasoned non-applicability (verified, not edited)

- `docs/guides/objective-plans.md:37` names "RC16 updater compatibility" and "RC17's bounded
  release evidence" as dated history with the storage-key rationale. Correctly labelled
  history, not a present-tense status claim.
- `docs/index.md:20,26` frames the rc3 qualification and the rc2 rollback explicitly as
  "the historical rc3 qualification". Not a current claim.
- `docs/product-boundary.md:41` describes the authorized `1.0.0rc1` milestone as a
  pre-stable candidate that is not stable `1.0.0`, a package-index publication or WSL2
  qualification. Truthful and boundary-preserving.
- `docs/capabilities.toml` lines 48, 70, 114, 136 and 169 attribute the rc3 activation,
  rollback and trace results as installation-local evidence with an explicit
  "not public release or cross-platform qualification" limit. Attributable history.
- `docs/guides/observation.md`, `docs/reference/plugins-and-tools.md`,
  `docs/guides/project-knowledge.md`, `docs/guides/morfeo-tool-configuration.md`,
  `docs/guides/execution.md`, `docs/guides/expected-behavior.md`, `docs/authority.md`,
  `docs/roles-and-authority.md`, `docs/guides/lifecycle.md`,
  `docs/guides/project-initialization.md`, `docs/guides/objective-contracts.md` and
  `docs/getting-started.md` contain no RC-label or active-release status claim. Spot
  verification of behavioural claims against source held: the 300-second semantic budget,
  `budget_tokens` 128–8,000, the 32,768-byte ceiling, the 50-reference cap, the lexical
  10,000-note search limit and the 14/5 knowledge action sets all match
  `src/aether_agents/knowledge/*`.
- Graphify's configured/optional boundary is preserved: every packaged role template
  ships `aether-project-knowledge` with `enabled: false`, matching the guide's opt-in
  wording.
- The Lab/Monitor retirement wording is already present and correct
  (`docs/index.md:75-78`, `docs/product-boundary.md:25-29`), including the preservation of
  native Hermes cron, ordinary Telegram interaction and native notifications. No edit.

## Needed changes reported rather than edited (outside U3's writable surface)

- `README.md:5-24` source-versus-release portal and the root `AGENTS.md` temporal
  paragraphs belong to U4; `DESIGN.md`/`ROADMAP.md` to U1; current stage specifications
  to U2.
- `.github/workflows/policy.yml` "Validate canonical base manifest" heredoc omits the
  tracked path `.aether/objective-contracts/oc_593cb1275b24ea19/v1.md` (397 entries versus
  398 tracked non-`specs/` paths). This is the base-state defect recorded in the
  decomposition handoff and assigned to U5:
  `tests/test_public_artifacts.py::test_canonical_base_manifest_matches_tracked_non_specs_files`
  fails identically at base and after this unit. U3 added no tracked non-`specs/` path and
  changed nothing in that workflow or oracle.
- `tests/test_public_artifacts.py` `INTEGRATIONS.md` byte-integrity constants belong to
  U4/U5 and were not touched.

## Test effect

- `tests/test_documentation.py` — 14 passed.
- `tests/test_observation_usage_guidance.py` — 9 passed.
- `tests/test_public_artifacts.py` — 8 passed, 1 pre-existing base-state failure (U5's
  manifest heredoc; unaffected by this unit).
- No assertion was weakened, skipped, deleted or re-scoped, and no oracle required
  correction: no existing assertion enforced the superseded wording. Assertions that touch
  the edited pages (the semantic-maintenance surface list, the `STATE_BUSY` /
  `CATCHUP_INCOMPLETE` / `STATE_UNREADABLE` presence checks) still hold unchanged.
- `scripts/check_documentation.py` and `scripts/check_public_artifacts.py` pass; `git diff
  --check` is clean; balanced code fences and resolvable relative links were verified over
  all 460 tracked Markdown files, mirroring the policy job.

## Open limits

- No verified installed release is claimed anywhere in this unit's artifacts; local
  runtime state stays private evidence and `aether doctor --json` remains the only
  portable route to live state.
- This is a documented, reviewable sweep of the tracked current corpus at the recorded
  base revision. It is not an unbounded proof that no sentence in any historical evidence
  file or future revision can conflict.
- Content edits inside existing tracked `docs/` pages change no docs path, so
  `website/src/lib/docs.ts` is unaffected by this unit.
