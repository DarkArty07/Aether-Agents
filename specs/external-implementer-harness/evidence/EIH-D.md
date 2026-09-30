# EIH-D — OD-1 guidance and documentation for the opt-in harness

## Scope and source

- **Objective Contract:** `oc_f1ea2c4a2e0662da@v1` (#563).
- **Unit:** EIH-D (Deliverable D2, EIH-11, AC9).
- **Supervisor breakdown:** `specs/external-implementer-harness/tasks.md` section "EIH-D", plan §3.13.
- **Base commit:** `2221302f1c93fb4ffd166df9b5482aa2fecaef7a` (working tree clean at start).
- **Role:** Implementer (`t_53f0d535`).

## Obligations and delivered changes

| Obligation | Location | Change and observed evidence |
| --- | --- | --- |
| OD-1 in Morfeo SOUL | `src/aether_agents/resources/profiles/morfeo/SOUL.md` | Stated OD-1 under `### Contract extraction and finalization`: the owner requests another Implementer harness when a contract is started; without that explicit request every role runs on Hermes and Morfeo neither proposes, asks about nor selects another harness. Nine `## 0X.` headings and role structure preserved. |
| OD-1 in canonical contract skill | `src/aether_agents/resources/skills/objective-contract-design/SKILL.md` | Stated OD-1 under `### Contract boundary and scope fidelity`, step 9 of `### Extraction and handoff` (setting optional `implementer_harness` on `begin`/`supersede` only on explicit owner request), and `## Pitfalls`. |
| Expected behavior catalogue | `docs/guides/expected-behavior.md` | Added entry `## Select an external Implementer harness only on explicit owner request` detailing trigger (when/who), expected conduct (OD-1), explicit limits, canonical sources, and observable signs. |
| Applicable user documentation | `docs/guides/execution.md` | Added section `## Opt-in Implementer harness (Claude Code)` covering minimum requirements (installed and logged in by user, unattended execution, unmanaged configuration, plan/quota consumption, stateless fallback on missing binary/disabled bypass/auth/quota failure) and limits (Hermes by default, role restrictions to Implementer work attempts, goal-mode and review attempts stay on Hermes, no credential access/storage, implementation only). |
| Capability registry and reference | `docs/capabilities.toml`, `docs/reference/capabilities.md` | Registered `lifecycle.external-implementer-harness` with status `partial`, surfaces `lifecycle.external-implementer-harness`, documented sources, specs, implementation, verification, and limits notes. Regenerated `docs/reference/capabilities.md` using `scripts/check_documentation.py --write`. |
| Changelog Unreleased section | `CHANGELOG.md` | Added Unreleased entries for #563 describing opt-in Claude Code harness under amended PD-40, OD-1 owner selection rule, user minimum requirements, and explicit limits. |
| Focused guidance test | `tests/test_contract_quality_documents.py` | Added `test_external_implementer_harness_guidance_states_od1_and_minimum_requirements` asserting OD-1 phrasing in Morfeo SOUL and `objective-contract-design` SKILL, presence in `expected-behavior.md` and `execution.md`, and minimum requirements coverage. |

## Applicability check of listed boundary artifacts

All listed writable artifacts in the unit assignment were applicable and updated:
- `src/aether_agents/resources/profiles/morfeo/SOUL.md`: Applicable (stated OD-1).
- `src/aether_agents/resources/skills/objective-contract-design/SKILL.md`: Applicable (stated OD-1 and contract parameter guidance).
- `docs/guides/expected-behavior.md`: Applicable (added expected behavior entry).
- `docs/guides/execution.md`: Applicable (home for execution, worktree, and review lifecycle).
- `docs/capabilities.toml` and `docs/reference/capabilities.md`: Applicable (registered capability and refreshed reference).
- `CHANGELOG.md`: Applicable (Unreleased section updated).
- `tests/test_contract_quality_documents.py`: Applicable (added focused guidance test).

No listed artifact was skipped; no non-applicability exception needed.

## Executed verification commands and results

All verification commands executed from the unit worktree:

1. `uv run --frozen python scripts/check_documentation.py`
   - Exit code: `0`
   - Output: `documentation validation passed`
2. `git diff --check`
   - Exit code: `0`
   - Output: clean (no whitespace or conflict errors)
3. `uv run --frozen pytest tests/test_contract_quality_documents.py tests/test_documentation.py`
   - Exit code: `0`
   - Output: `31 passed, 1 skipped in 0.87s`
4. `uv run --frozen ruff check tests/test_contract_quality_documents.py`
   - Exit code: `0`
   - Output: `All checks passed!`
5. `uv run --frozen ruff format --check tests/test_contract_quality_documents.py`
   - Exit code: `0`
   - Output: `1 file already formatted`
6. `uv run --frozen python scripts/check_public_artifacts.py`
   - Exit code: `0`
   - Output: `public artifact path scan passed: tracked surface + 0 artifact(s)`

## Compatibility and limits

- **Unit compatibility impact:** `minor` (additive guidance, documentation, capability registration, and test coverage for the opt-in external Implementer harness).
- **Prohibitions observed:**
  - Never invoked `claude` or Claude Code.
  - Never modified live boards or live Hermes homes.
  - Never modified `src/aether_agents/*.py`, `pyproject.toml`, `policy/`, or the canonical Objective Contract.
  - No secrets, credentials, or operator home paths included.
  - Local commit only; no branch push, pull request, merge, or issue closure.
