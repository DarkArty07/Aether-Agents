# BGD-CONTENT unit evidence

Status: Implementer self-review evidence for the canonical documentation/content unit.
This record is not independent review, integrated acceptance, a release decision or
proof of website deployment.

## Unit and source basis

- Objective Contract: `oc_844dfc12880ee967@v1` (contract digest recorded by the
  Supervisor), on required base `9bce0d222fdf0bfc581a26e282b81b08a1418d7c`.
- Unit: BGD-CONTENT, covering the beginner journey, current/intended status language,
  route choice, first-objective example, glossary, canonical cross-links and Spanish/
  English landing copy.
- Source checks used: `DESIGN.md` sections on product model, roles, route selection,
  Hermes boundary and autonomous stewardship; `docs/capabilities.toml`; the parser and
  initialization implementation in `src/aether_agents/cli.py` and
  `src/aether_agents/commands/init.py`; existing `docs/` references; and the contract
  handoff supplied on the board.
- Project Canonical Skills: no `.aether/skills/` directory exists at the required base;
  the loaded Aether Canonical `implementation-evidence`, `project-knowledge` and
  `work-memory` procedures governed this unit. The project-knowledge component reported
  `available=false`, so direct source inspection was used as the accepted fallback.

## Delivered paths

- Added `docs/start-here.md` with a zero-context mental model, role boundaries, direct /
  pipeline selection, prerequisites, provider-free exercise, initialization boundary,
  status vocabulary and next steps.
- Added `docs/guides/first-objective.md` with an explicitly non-normative illustrative
  substantial objective, the owner-intake → Morfeo → route → Objective Contract →
  Supervisor/board → Implementer/worktree → independent review/evidence → GitHub /
  terminal sequence, and a contrasting bounded direct example.
- Added `docs/reference/glossary.md` with concise Aether terms and links to detail.
- Reworked `docs/index.md` into the five ordered groups: Start here, Core concepts,
  Working with Aether, Operations and safety, and Reference.
- Reworked `docs/getting-started.md` into a prerequisite-first provider-free sequence.
- Added focused beginner cross-links and concrete next steps to the relevant existing
  non-generated canonical pages. `docs/reference/capabilities.md` was preserved because
  it is generated and must not be edited directly.
- Corrected the Spanish and English `website/src/data/content.ts` copy so greenfield is
  identified as intended scope, current `aether init` is identified as requiring an
  existing Git repository and exact-path native Hermes Project, and the pipeline / long-
  horizon presentation is not a claim of provider-backed or release-qualified execution.
- Added `tests/test_beginner_documentation.py` for required slugs, group/order coverage,
  prerequisites, route/walkthrough vocabulary, status and safety boundaries, relative
  source links and landing-copy safeguards.

## Executed verification

| Command or action | Observed result | Evidence / interpretation |
| --- | --- | --- |
| `uv run --frozen python scripts/check_documentation.py` | PASS: `documentation validation passed` | Registry and generated capability reference remained coherent; no generated file was edited. |
| `uv run --frozen pytest -q tests/test_beginner_documentation.py` | PASS: 9 passed after final test adjustment | Focused beginner corpus, order, link, orientation and landing-copy assertions. |
| `uv run --frozen pytest -q tests/test_documentation.py` | PASS: 11 passed | Existing registry/checker behavior preserved. |
| `uv run --frozen pytest -q tests/test_beginner_documentation.py tests/test_documentation.py` | PASS: 20 passed | Combined owned/new documentation checks. |
| `uv run --frozen pytest -q tests/test_beginner_documentation.py tests/test_documentation.py tests/test_public_artifacts.py` | 24 passed, 1 failed | The single failure is the known unchanged-base #364 public-artifact defect: `test_tracked_public_surface_contains_no_operator_paths` reports only the pre-existing tracked `.aether/objective-contracts/oc_0084270d940c98d9/v1.md` `absolute-user-home` and `operator-desktop-layout` findings. No `.aether` path is owned or changed here; the defect was not absorbed or weakened. |
| `uv run --frozen python scripts/check_public_artifacts.py --root <worktree>` | FAIL with the same two findings | Exact standalone reproduction of the baseline #364 scanner result; no new path finding was introduced by this unit. |
| `git diff --check` | PASS | No whitespace errors in the intended local diff. |
| `uv run --frozen ruff check tests/test_beginner_documentation.py` | PASS: `All checks passed!` | Focused test style is clean. |
| Isolated temporary `HOME`, `HERMES_HOME` unset: `uv run --frozen aether --version` | PASS, exit 0; `aether 0.24.0` | Hermes-free provider-free version surface. |
| Same isolated environment: `aether --help`, `aether observe --help`, `aether doctor --help`, `aether init --help`, `aether version --help`, `aether knowledge --help` | PASS, exit 0 for each | Parser/help paths are available without provider calls. |
| Same isolated environment: all top-level command help paths and all `aether knowledge <subcommand> --help` paths | PASS, exit 0 for each | Additional parser-facing help surfaces were exercised; no provider or credential setup was used. |
| Same isolated environment: `aether doctor --json` | Expected diagnostic, exit 4; JSON reported `LIFECYCLE_INTEGRITY_FAILED` / `ACTIVE_RELEASE_INVALID` | Clean environment has no active candidate release. This is diagnostic evidence, not a failed beginner parser/help path and not an instruction to install or authenticate. |
| Same isolated environment: `aether init --dry-run --json`, `aether observe --json`, `aether knowledge doctor --json`, `aether version --json` | Exit 3 with `AETHER-INIT-HERMES-PROJECTS-UNAVAILABLE`; exit 0 with `{"state":"empty"}`; exit 1 with `COMPONENT_UNAVAILABLE`; exit 0 with `MANAGER_DETAIL_UNAVAILABLE` warning | Provider-free/read-only boundaries were exercised. Initialization correctly stops when the native Hermes Projects database prerequisite is absent; observation reports an empty state; optional knowledge is unavailable without activation; version remains usable while manager detail is unavailable. |
| `npm run check` from `website/` | Not runnable, exit 127: `astro: command not found` | Website dependencies are not installed in this worktree. Website build/check/e2e qualification belongs to BGD-WEB; no dependency was added or fetched in this content unit. |
| Project knowledge status | `available=false`, source revision reported by component; no snapshot | Direct source and test inspection used; no graph claim is made. |

The isolated command runner used a temporary HOME and removed `HERMES_HOME`; temporary
locations and runtime state are intentionally omitted from this public record.

## Requirement and acceptance mapping

| Contract obligation | Delivered / observed evidence |
| --- | --- |
| AC-1: unmistakable start point, mental model, roles and route choice | `docs/index.md` begins with the Start here route; `docs/start-here.md` explains Aether/not-Aether, owner, Morfeo, Supervisor, Implementer, direct route and pipeline route. Focused tests assert the required pages and ordered groups. |
| AC-2: prerequisites before commands, first-use terminology, interpretation and next steps | `docs/getting-started.md` places `## Prerequisites` before command blocks, explains expected version/help/doctor observations, links the glossary and ends with `## Next step`. The major canonical pages have concrete next-step links. |
| AC-3: complete illustrative pipeline plus bounded direct contrast | `docs/guides/first-objective.md` labels itself non-normative and illustrative, follows the complete requested sequence, distinguishes independent review from self-review, and contrasts a reversible direct documentation correction. It explicitly does not claim provider-backed execution. |
| AC-4: current/partial/transitional/unsupported/intended/historical and stabilization truth | `docs/start-here.md`, `docs/getting-started.md`, the walkthrough and landing copy distinguish status labels and state stabilization-build, public-installation and release-qualification limits. The capability registry remains the status authority. |
| AC-5: commands and expected conditions grounded in parser/source, generic Hermes setup linked | Current CLI and init source were inspected; the documented parser/help commands and the clean-environment doctor diagnostic were executed. Hermes installation/provider/credential setup is linked to the authoritative Hermes documentation rather than restated. |
| AC-12: no private or opaque operational data in public artifacts | Focused assertions reject home paths and API-key wording in the new public pages; the public-artifact scanner introduced no new finding. No credentials, channels, sessions, board IDs, provider bindings, machine paths or runtime state were added. |
| AC-13: documentation metadata/terminology/status coherence and historical preservation | Existing canonical pages receive only beginner-navigation/status/prerequisite corrections; generated capability reference and historical website proposals are preserved. Website copy uses intended/current qualifiers. |
| Deliverables 1–2 | New canonical pages, reworked index/getting-started path, glossary, walkthrough and corrected bilingual landing copy are present in the delivered paths above. |

## Compatibility and remaining risk

Unit compatibility impact: `patch`. The change expands and clarifies reader-facing
Markdown and landing copy without changing Python/runtime APIs, CLI semantics, capability
status values or product architecture. This is unit-level compatibility evidence only;
Supervisor owns aggregate release conclusions.

Remaining risks are bounded to the known baseline public-artifact defect and the website
renderer still needing the independently reviewed content commit before its manifest,
routes and existing website test expectations can be updated by BGD-WEB. The unavailable
local `astro` command prevented a website check in this unit; it does not establish a
website build failure. No provider-backed execution, live profile activation, public
installation, deployment or release claim is made.
