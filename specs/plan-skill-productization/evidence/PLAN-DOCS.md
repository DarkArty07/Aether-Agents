# PLAN-DOCS — unit evidence

**Card:** `t_38b4e82f` (PLAN-DOCS), Objective Contract `oc_c29c2b0ed38d5030@v1` (SHA-256 `e8ab6fd7d21eb7b65b4887206bc0b2aaae5c02a60f411b970da2696963651af0`), Issue `#504`.

**Branch:** `aether-agents-2/t_38b4e82f-plan-docs-reconcile-public-guidance-regi`

**Shipped source revision documented:** candidate commit `3da14572232775aedbc23b38393227cd62ed5ebc` (reviewed and approved in `t_e2c6f3bd` PLAN-CANDIDATE; base `2e347ab358e7daa850551a90cb24d12f35de0f59`).

## Outcome summary

Reconciled public guidance, capability registry, generated documentation reference, authority reader notes, tool configuration, and asserting quality suites with the shipped Morfeo-scoped `plan` canonical skill surface. Coherence updates were applied to the objective's specification and validation artifacts. Verified all documentation and contract quality tests pass with deterministic reference generation.

## Before and after wording for reconciled statements

### 1. `docs/guides/objective-plans.md` (lines 30–33)

**Before:**
> The generic `/plan` skill has a different default save location. Aether's project-local convention governs Aether Objective Plans without rewriting that skill for every Hermes user. This adds no global plan picker or automatic hook.

**After:**
> Aether packages an Aether-owned canonical skill named `plan`, delivered **only to Morfeo** through the role-scoped release bundle. It resolves as literal `/plan` on the selected maintained fork `aed6591a69f453a1867b73628603e7b53ba40ffc`, planning-only, writing one stable `.aether/plans/<objective-slug>.md` inside the explicitly resolved project. A skill is package-wide procedure; its **outputs live inside each selected project**.
>
> The generic Hermes `/plan` is not this behaviour. Generic Hermes planning carries different defaults and unbounded execution recipes, whereas Aether's project-local procedure governs Objective Plans without rewriting skills for every Hermes user or adding global plan pickers.
>
> Supervisor and Implementer retain their previous inventories and do not receive `plan`; their role boundaries do not include objective-level planning. A future Hermes version with a built-in `/plan` requires a separate compatibility decision rather than an assumed alias; compatibility is qualified for the pinned fork commit only. A source change or merge does not constitute an active-profile installation, release cutover, or universal model behavioral guarantee.

### 2. `docs/capabilities.toml` (`skills.aether-canonical-resources`)

**Before:**
> summary = "Eight Aether Canonical Skills are explicitly registered for packaging and native profile materialization, including contract execution, project knowledge and role work memory."
> documents = ["docs/authority.md", "docs/guides/project-initialization.md"]
> specifications = ["specs/r5-topology-and-isolation/spec.md", "specs/r13-synthesis-and-release/spec.md"]
> implementation = ["src/aether_agents/lifecycle.py", ... 8 skill paths ...]
> notes = "The resource mechanism and explicit eight-skill inventory are covered by wheel, sdist, profile-bundle, native-directory, byte-identity and privacy checks. The three contract/execution procedures had their open-ended observation requirement in issue #317 closed at owner direction without claiming organic PASS; knowledge-skill packaging does not establish live-agent adoption. Private live-profile activation is separate runtime evidence, and the public installed lifecycle remains unqualified."

**After:**
> summary = "Ten Aether Canonical Skills are explicitly registered for packaging and native profile materialization, including contract execution, project knowledge, role work memory and Morfeo objective planning."
> documents = ["docs/authority.md", "docs/guides/project-initialization.md", "docs/guides/objective-plans.md"]
> specifications = ["specs/r5-topology-and-isolation/spec.md", "specs/r13-synthesis-and-release/spec.md", "specs/plan-skill-productization/spec.md"]
> implementation = ["src/aether_agents/lifecycle.py", ... 8 skill paths ..., "src/aether_agents/resources/skills/contract-result-review/SKILL.md", "src/aether_agents/resources/skills/plan/SKILL.md"]
> notes = "The resource mechanism and explicit ten-skill inventory (with plan delivered only to Morfeo) are covered by wheel, sdist, profile-bundle, native-directory, byte-identity and privacy checks. The three contract/execution procedures had their open-ended observation requirement in issue #317 closed at owner direction without claiming organic PASS; knowledge-skill and plan-skill packaging does not establish live-agent adoption. Private live-profile activation is separate runtime evidence, and the public installed lifecycle remains unqualified."

### 3. `docs/reference/capabilities.md`

Regenerated via `uv run --frozen python scripts/check_documentation.py --write` reflecting the reconciled 10-skill summary, updated documents, specifications, implementation list (including all 10 canonical skill links), and limits notes.

### 4. `docs/authority.md` (§ Objective Plans and cross-session continuity)

**Extended:** added explicit reader pointer:
> Morfeo's user-invoked planning entry is the canonical `plan` skill (scoped to Morfeo only); `objective-contract-design` retains the substantive contract method.

### 5. `docs/guides/morfeo-tool-configuration.md` (§ Morfeo tool configuration)

**Reconciled:** clarified that `/plan` is Morfeo's role-scoped canonical planning skill writing project-local plans:
> `todo` helps retain the current thread, but does not decide when the whole objective is complete. Likewise, `/plan` is a planning skill delivered only to Morfeo through the role-scoped release bundle (writing project-local plans to `.aether/plans/`), not an execution lock. Neither is a proven cure for scope expansion or a reason to turn every request into a planning exercise.

### 6. `specs/plan-skill-productization/spec.md` (line 3)

**Before:**
> `**Status:** owner-approved objective; implementation and independent review pending.`

**After:**
> `**Status:** owner-approved objective; candidate implementation reviewed; documentation and verification in progress.`

### 7. `specs/plan-skill-productization/quickstart.md` (line 3)

**Before:**
> `This is the **proposed acceptance path**, not a report of tests already passing.`

**After:**
> `This is the acceptance path for candidate verification.`

### 8. `tests/test_contract_quality_documents.py`

Updated assertion from old phrase `generic `/plan`` to new shipped phrases `delivered **only to Morfeo**` and `generic Hermes `/plan` is not this behaviour`.

### 9. `tests/test_documentation.py`

Updated `test_canonical_skill_capabilities_are_statused_and_traceable` to assert `Ten Aether Canonical Skills` in the summary and verify exact set equality between the on-disk packaged skills under `src/aether_agents/resources/skills/*/SKILL.md` (10 skills) and the registry's registered skill implementation paths, ensuring the test fails if any packaged canonical skill is omitted in the future.

## Deliberately unchanged surfaces and non-applicability reasons

- **`AGENTS.md`**: Left unchanged. The current instruction states:
  `For objective planning and cross-session continuation, see docs/guides/objective-plans.md and the objective-contract-design canonical procedure's planning entry. Keep one local .aether/plans/<objective-slug>.md when a meaningful route or continuity is needed; do not select by recency, duplicate canonical obligations, or add plan ceremony to simple bounded work. Plans remain local/ignored unless publication is explicitly decided. A session or contract boundary does not reset failed approaches or the reasoning needed to justify continuation. Source instructions do not prove live adoption.`
  This instruction remains entirely accurate: it points readers to the authoritative guide (`docs/guides/objective-plans.md`) and canonical procedure, specifies the exact project-local path, and enforces anti-ceremony/continuation principles. No statement in it was invalidated by the addition of the Morfeo-scoped `/plan` skill.
- **`specs/r2-contract-and-handoff/spec.md`**: Left unchanged. The normative requirements in §3.1 (FR-204b–f) and the historical note at lines 66–72 are Morfeo-owned normative intent. They accurately anticipate the project-local `/plan` addition without contradiction.
- **`specs/plan-skill-productization/{plan,research}.md`**: Left unchanged. Content accurately reflects the technical plan and research decisions.
- **`src/**`, `scripts/**`, `.github/workflows/policy.yml`**: Untouched by this unit, as specified by the writable boundary.

## Verification actually run

Commands executed in this worktree:

1. `uv run --frozen python scripts/check_documentation.py`
   - Exit code: 0
   - Output: `documentation validation passed`
2. `uv run --frozen python scripts/check_public_artifacts.py --root .`
   - Exit code: 0
   - Output: `public artifact path scan passed: tracked surface + 0 artifact(s)`
3. Card verification commands:
   - Command: `uv run --frozen pytest -q tests/test_documentation.py tests/test_contract_quality_documents.py tests/test_public_artifacts.py`
   - Exit code: 1
   - Output: `1 failed, 40 passed, 1 skipped in 2.88s`
   - Attribution: Failure is solely `tests/test_public_artifacts.py::test_canonical_base_manifest_matches_tracked_non_specs_files` due to the composition-owned manifest delta (`tests/test_plan_skill_dispatch.py` in `PLAN-NATIVE`), as described in Known red below.
   - Docs-focused subset: `uv run --frozen pytest -q tests/test_documentation.py tests/test_contract_quality_documents.py` passes completely with `32 passed, 1 skipped in 1.10s` (exit code: 0).
4. Tracked Markdown fence balance and link resolution check (simulating policy workflow R0 lane verbatim):
   - Command: Bash/Python script extracted verbatim from `.github/workflows/policy.yml` (`Validate accepted R0 design baseline`) checking balanced code fences and resolving relative Markdown links on all 385 tracked `.md` files.
   - Result: `R0 check passed on 385 markdown files` (exit code: 0).
5. ROADMAP status marker check:
   - Command: assertion that no `BORRADOR` or `PENDIENTE` markers exist in `ROADMAP.md`.
   - Result: `ROADMAP markers check passed`

## Known red (composition-owned, not candidate-owned)

`tests/test_public_artifacts.py::test_canonical_base_manifest_matches_tracked_non_specs_files` fails because the policy workflow manifest heredoc literally names `tests/test_plan_skill_dispatch.py` (authored by parallel unit `PLAN-NATIVE`, `t_4b5cdf5f`). That file does not exist in this isolated worktree; the oracle passes once `PLAN-INT` integrates all reviewed units. No test in this unit was skipped or weakened.

## What remains unqualified

- **Installed release & activation:** Source documentation and capability registry updates do not constitute an installed package, local release activation, or live profile cutover.
- **Model behavioral convergence:** Static documentation tests confirm instructional coverage and traceability; they do not guarantee that every model will adhere to planning instructions without failure in live sessions.
- **Upstream core compatibility:** The `/plan` slash dispatch is qualified solely on the pinned maintained fork commit `aed6591a69f453a1867b73628603e7b53ba40ffc`. Future Hermes releases with a built-in `/plan` require separate qualification.
