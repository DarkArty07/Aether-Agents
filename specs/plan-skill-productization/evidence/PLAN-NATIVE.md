# PLAN-NATIVE — unit evidence

**Card:** `t_4b5cdf5f` (PLAN-NATIVE), Objective Contract
`oc_c29c2b0ed38d5030@v1` (SHA-256
`e8ab6fd7d21eb7b65b4887206bc0b2aaae5c02a60f411b970da2696963651af0`),
Issue `#504`.

**Base commit:** `2e347ab358e7daa850551a90cb24d12f35de0f59`

**Branch:** `aether-agents-2/t_4b5cdf5f-plan-native-qualify-selected-fork-plan-d`

**Consumer of:** `PLAN-CANDIDATE` (reviewed candidate commit `3da14572232775aedbc23b38393227cd62ed5ebc`,
plan resource SHA-256 `b2a0f696cdfeb898058e5d744d47e8f52e2b0b595fa9a96bf0fd6f20158f4e3d`).

## What changed

- `tests/test_plan_skill_dispatch.py` (new): automated qualification suite covering:
  1. Selected runtime verification: resolves interpreter via active release `runtime/current/venv/bin/python`,
     inspects `agent.skill_commands.__file__`, confirms resolution to `hermes-source`, binds to pinned fork commit
     `aed6591a69f453a1867b73628603e7b53ba40ffc`, and verifies tree digest `cc1ebf94ad167979951e7b956ef3a8c448e96fd3389c93cddf60f8f883bb5ce7`.
  2. Collision gate: verifies `hermes_cli.commands.COMMANDS` and `resolve_command` contain no `plan` or `/plan`
     command, confirming `/plan` remains unreserved by core Hermes and free for slash skill auto-registration.
  3. Native selection over nested learned shadow: in a disposable `HERMES_HOME` containing both canonical root
     `skills/plan/SKILL.md` (reviewed candidate bytes) and nested learned `skills/software-development/plan/SKILL.md`,
     `scan_skill_commands()` selects `/plan` mapped to the canonical root path, verifying the returned bytes match
     SHA-256 `b2a0f696cdfeb898058e5d744d47e8f52e2b0b595fa9a96bf0fd6f20158f4e3d`.
  4. Role absence: disposable Supervisor and Implementer profile homes materialized without `plan` confirm that
     `skills/plan` is strictly absent on disk and `/plan` is omitted from `scan_skill_commands()` registration.
  5. Planning-only semantics (Decision 5): exercises project-local plan lifecycle at `.aether/plans/<objective-slug>.md`,
     verifying single plan creation, zero implementation/contracts/boards created, idempotent repeat update, project
     isolation, refusal when project binding is absent or ambiguous, and non-capping contract forecasts.
- `specs/plan-skill-productization/evidence/PLAN-NATIVE.md` (this file): evidence record detailing static checks,
  native loader selection, role absence, collision check, lifecycle scenarios, and behavioural observation distinction.

## Verification actually run

Focused qualification suite:

```bash
uv run --frozen pytest -v tests/test_plan_skill_dispatch.py
```

Result:

```text
============================= test session starts ==============================
platform linux -- Python 3.13.15, pytest-9.1.1, pluggy-1.6.0
collecting ... collected 6 items

tests/test_plan_skill_dispatch.py::test_agent_skill_commands_imported_from_pinned_fork_tree PASSED [ 16%]
tests/test_plan_skill_dispatch.py::test_plan_slash_command_collision_gate PASSED [ 33%]
tests/test_plan_skill_dispatch.py::test_native_scan_skill_commands_selects_canonical_plan_over_nested_learned PASSED [ 50%]
tests/test_plan_skill_dispatch.py::test_plan_skill_absent_from_disposable_supervisor_and_implementer_homes PASSED [ 66%]
tests/test_plan_skill_dispatch.py::test_candidate_plan_skill_text_authoring_and_invariants PASSED [ 83%]
tests/test_plan_skill_dispatch.py::test_planning_only_semantics_lifecycle_scenarios PASSED [100%]

============================== 6 passed in 4.05s ===============================
```

Linter and formatting checks:

```bash
uv run --frozen ruff check tests/test_plan_skill_dispatch.py
uv run --frozen ruff format --check tests/test_plan_skill_dispatch.py
```

Result:

```text
All checks passed!
1 file already formatted
```

Public artifact and documentation checks:

```bash
uv run --frozen python scripts/check_public_artifacts.py --root .
uv run --frozen python scripts/check_documentation.py
```

Result:

```text
public artifact path scan passed: tracked surface + 0 artifact(s)
documentation validation passed
```

## Requirement coverage

| Requirement | Verification check | Observed result |
| --- | --- | --- |
| AC (d) / PS-009 (1) Selected runtime | `test_agent_skill_commands_imported_from_pinned_fork_tree` | `agent.skill_commands` imports from active release `hermes-source/agent/skill_commands.py`; `release-lock.json` binds commit `aed6591a69f453a1867b73628603e7b53ba40ffc`; tree digest equals `cc1ebf94ad167979951e7b956ef3a8c448e96fd3389c93cddf60f8f883bb5ce7` |
| AC (d) / PS-009 (2) Native selection | `test_native_scan_skill_commands_selects_canonical_plan_over_nested_learned` | `scan_skill_commands()` returns `/plan` pointing to `<home>/skills/plan/SKILL.md` (not the nested learned path); bytes SHA-256 is `b2a0f696cdfeb898058e5d744d47e8f52e2b0b595fa9a96bf0fd6f20158f4e3d` |
| AC (d) / PS-001 / US-PS-3 (3) Role absence | `test_plan_skill_absent_from_disposable_supervisor_and_implementer_homes` | Disposable Supervisor and Implementer homes lack `skills/plan` on disk; `scan_skill_commands()` registers `/plan` in Morfeo only, returning `has_plan=False` for Supervisor and Implementer |
| AC (d) / PS-009 (4) Collision gate | `test_plan_slash_command_collision_gate` | `COMMANDS` has no `plan` or `/plan`; `resolve_command('plan')` is `None`; collision gate does not block auto-registration |
| AC (d) / US-PS-1 (5) Decision 5 Planning-only semantics | `test_planning_only_semantics_lifecycle_scenarios` | Scenarios 5a–5e pass: single file at `.aether/plans/<slug>.md`, no contracts/code/boards created, idempotent file reuse, project separation, stop-and-surface on ambiguity, forecast non-capping |
| US-PS-2 / Authoring standards | `test_candidate_plan_skill_text_authoring_and_invariants` | YAML frontmatter valid, description 49 chars (<= 60, ends in `.`, contains `Morfeo`), modern section order, no operator paths, no secrets |

## Detailed evidence by classification

### 1. Static file checks

The candidate `plan` resource bytes authored by `PLAN-CANDIDATE` (`3da14572232775aedbc23b38393227cd62ed5ebc`) were inspected:

- File path: `src/aether_agents/resources/skills/plan/SKILL.md`
- Digest: SHA-256 `b2a0f696cdfeb898058e5d744d47e8f52e2b0b595fa9a96bf0fd6f20158f4e3d`
- Line count: 75 lines, 2,868 characters
- Frontmatter:
  - `name`: `plan`
  - `description`: `Author a project-local Objective Plan for Morfeo.` (49 chars <= 60, ends in `.`, contains `Morfeo`)
  - `version`: `0.1.0`
  - `author`: `Morfeo (Aether role), Hermes Agent`
  - `license`: `MIT`
  - `platforms`: `[linux, macos, windows]`
  - `metadata.hermes.tags`: `[planning, objective, morfeo]`
  - `metadata.hermes.related_skills`: `[]`
- Modern section headings present: `## When to Use`, `## Prerequisites`, `## Procedure`, `## Pitfalls`, `## Verification`
- Single planning trigger in `## When to Use`: explicit planning request (such as `/plan`) or cross-session route requested for an objective with Morfeo.
- Exclusions stated: does not execute code, does not create Kanban boards or cards, does not certify independent review, does not add mandatory planning ceremony to simple questions.

### 2. Native loader selection on selected maintained fork

- Module resolution: `agent.skill_commands` resolves to `<release-root>/hermes-source/agent/skill_commands.py`
- Selected fork tree: `<release-root>/hermes-source` matches release lock `commit` `aed6591a69f453a1867b73628603e7b53ba40ffc` and `source_tree_sha256` `cc1ebf94ad167979951e7b956ef3a8c448e96fd3389c93cddf60f8f883bb5ce7`.
- Core command registry check:
  - `"plan" in commands.COMMANDS`: `False`
  - `"/plan" in commands.COMMANDS`: `False`
  - `resolve_command("plan")`: `None`
  - `resolve_command("/plan")`: `None`
  - Observed result: collision gate passes; core commands register no `plan` command.
- Selection order test:
  - In a disposable root with both `skills/plan/SKILL.md` and `skills/software-development/plan/SKILL.md`,
    `iter_skill_index_files` yields sorted matching paths, evaluating `skills/plan/SKILL.md` first.
  - `scan_skill_commands()` registers `/plan` with `skill_md_path` resolving to `<home>/skills/plan/SKILL.md`.
  - The nested learned shadow at `<home>/skills/software-development/plan/SKILL.md` is evaluated second;
    `seen_names` deduping skips it without overwriting the canonical mapping.
  - The resolved file bytes confirm exact SHA-256 match `b2a0f696cdfeb898058e5d744d47e8f52e2b0b595fa9a96bf0fd6f20158f4e3d`.

### 3. Disposable profile role scoping and absence

- Disposable profile homes materialized from candidate definitions:
  - `morfeo`: 9 common canonical skills + `plan` (total 10)
  - `supervisor`: 9 common canonical skills (`plan` absent)
  - `implementer`: 9 common canonical skills (`plan` absent)
- Physical disk inspection:
  - `<morfeo>/skills/plan/SKILL.md`: present and matches candidate bytes
  - `<supervisor>/skills/plan`: does not exist
  - `<implementer>/skills/plan`: does not exist
- Native slash registration inspection:
  - `HERMES_HOME=<morfeo>`: `scan_skill_commands()` contains `/plan`
  - `HERMES_HOME=<supervisor>`: `scan_skill_commands()` does not contain `/plan` (`has_plan=False`)
  - `HERMES_HOME=<implementer>`: `scan_skill_commands()` does not contain `/plan` (`has_plan=False`)

### 4. Planning-only lifecycle semantics (Decision 5)

Deterministic scenario verification:

- Scenario 5a (Project-local creation): Given project root `project_a` with `.aether/project.toml`, planning
  for slug `bounded-feature-alpha` creates `.aether/plans/bounded-feature-alpha.md`. Exactly one plan file exists;
  no `.aether/objective-contracts/` directory exists; no `src/` directory or code edits exist; no `.hermes/` board
  or task cards exist.
- Scenario 5b (Idempotent repeat): Invoking planning again for the same slug updates the existing file in place.
  Total plan count remains 1; updated content is verified.
- Scenario 5c (Project separation): Planning in `project_a` and `project_b` writes exclusively to their respective
  `.aether/plans/` paths without cross-project leakage or global path creation.
- Scenario 5d (Absent/ambiguous project binding): If project root is absent (`None`) or ambiguous (conflicting candidates),
  the procedure stops and produces zero files.
- Scenario 5e (Forecast not a cap): Projections in the plan represent revisable forecasts and do not impose a numeric quota.

### 5. Behavioural observation distinction

- Real model turn: **NOT PERFORMED**.
- Rationale: Under PD-71 and role authority boundaries, headless automated unit execution has no provisioned model
  API credentials and is strictly prohibited from acquiring credentials, invoking remote models, or triggering live
  gateway / agent sessions.
- In accordance with task instructions, static file checks, native loader selection, role absence, and deterministic
  scenario tests were executed in full and independently verified; behavioural model turns are recorded as not performed
  due to headless environment isolation.

## Known red (composition-owned, not unit-owned)

`tests/test_public_artifacts.py::test_canonical_base_manifest_matches_tracked_non_specs_files` fails
in this isolated worktree because `tests/test_plan_skill_dispatch.py` is newly tracked while this worktree's
copy of `.github/workflows/policy.yml` reflects the base commit `2e347ab3` (which does not yet include that line).
`PLAN-CANDIDATE` (`t_e2c6f3bd`) added `tests/test_plan_skill_dispatch.py` to the heredoc in its branch. This oracle
is composition-owned and passes on the composed integration revision.

## Remaining risk and limits

- Qualification is confined to the pinned maintained Hermes fork `aed6591a69f453a1867b73628603e7b53ba40ffc`.
  Public newer Hermes documentation regarding built-in `/plan` was not treated as target runtime proof.
- No live profile, active release, gateway unit, credentials, or remote services were touched.
- All exercises used disposable roots and scrubbed environments.
- Publication, pull requests, releases, and integration remain Supervisor-owned.
