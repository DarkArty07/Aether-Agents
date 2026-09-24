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
  4. Role scoping and absence: derives per-role skill inventories from the candidate's own role-aware distribution
     (`_CANDIDATE_ROLE_SKILLS` / `_role_skills`), confirming `morfeo` receives 10 skills (including `plan`) while
     `supervisor` and `implementer` receive 9 skills (`plan` absent). Materializes disposable profile homes and
     verifies that the managed root resource `skills/plan/SKILL.md` is strictly absent on disk in Supervisor and
     Implementer. In a minimal home containing only managed Aether skills, `/plan` is omitted (`has_plan=False`) for
     Supervisor and Implementer. In a realistic home containing the pinned fork's bundled Plan-Mode skill
     (`skills/software-development/plan/SKILL.md`), `/plan` in Supervisor and Implementer resolves to the bundled skill,
     while in Morfeo the canonical root resource `skills/plan/SKILL.md` wins over the bundled shadow.
  5. Planning-only semantics (Decision 5): validates through static specification checks against the candidate `plan`
     skill text that the procedure mandates project-local `.aether/plans/<objective-slug>.md`, single-file idempotence,
     project separation, refusal on absent/ambiguous project binding, and non-capping contract forecasts. Behavioral
     model turns are recorded as NOT PERFORMED under headless environment isolation.
- `specs/plan-skill-productization/evidence/PLAN-NATIVE.md` (this file): evidence record detailing static checks,
  native loader selection, role absence, collision check, lifecycle specification checks, and behavioural observation distinction.

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
tests/test_plan_skill_dispatch.py::test_decision_5_planning_only_semantics_static_specification_checks PASSED [100%]

============================== 6 passed in 4.34s ===============================
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
| AC (d) / PS-001 / US-PS-3 (3) Role absence | `test_plan_skill_absent_from_disposable_supervisor_and_implementer_homes` | Derived from candidate `_CANDIDATE_ROLE_SKILLS`: `morfeo` has 10 skills (incl. `plan`), `supervisor` has 9, `implementer` has 9. Managed root resource `skills/plan` is strictly absent on disk in Supervisor and Implementer. In minimal homes, `/plan` is absent (`has_plan=False`) for Supervisor and Implementer; in realistic homes with the pinned fork's bundled Plan-Mode skill, `/plan` resolves to the bundled skill in Supervisor and Implementer while Morfeo resolves to canonical root |
| AC (d) / PS-009 (4) Collision gate | `test_plan_slash_command_collision_gate` | `COMMANDS` has no `plan` or `/plan`; `resolve_command('plan')` is `None`; collision gate does not block auto-registration |
| AC (d) / US-PS-1 (5) Decision 5 Planning-only semantics | `test_decision_5_planning_only_semantics_static_specification_checks` | Static specification checks pass: candidate skill mandates project-local `.aether/plans/<slug>.md`, single-file idempotence, project separation, stop-and-surface on ambiguity, and non-capping forecast; live behavioral model turn recorded as NOT PERFORMED |
| US-PS-2 / Authoring standards | `test_candidate_plan_skill_text_authoring_and_invariants` | YAML frontmatter valid, description 49 chars (<= 60, ends in `.`, contains `Morfeo`), modern section order, no operator paths, no secrets |

## Detailed evidence by classification

### 1. Static file checks

The candidate `plan` resource bytes authored by `PLAN-CANDIDATE` (`3da14572232775aedbc23b38393227cd62ed5ebc`) were inspected:

- File path: `src/aether_agents/resources/skills/plan/SKILL.md`
- Digest: SHA-256 `b2a0f696cdfeb898058e5d744d47e8f52e2b0b595fa9a96bf0fd6f20158f4e3d`
- Line count: 75 lines, 3,765 characters
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

#### Lane note added by integration (Supervisor repair, disclosed)

The node above was originally written so that it demanded the literal directory leaf
`hermes-source` from whatever interpreter resolved, and then unconditionally asserted the
fork source-tree digest. That encoded a false identity for the repository's policy lane,
which provisions only the authenticated **public** baseline checkout
(`v2026.8.18` @ `e624e9fde561`, tree `69bde94fd581c8ef8118c30e1e8da1d09a72b7ac71e2a03fbece9c60e056062c`)
on `AETHER_EXACT_HERMES_CHECKOUT` (`hermes-exact`) and never provisions the selected fork.
Consequently `observation-qualification` failed on all three Pythons at
`Enforce integrated coverage floor` before the coverage report could run.

The integration repair keeps the fork obligation exactly as strong on the fork lane (release
lock commit, `maintained_fork` source mode, and the recomputed fork tree digest) and makes the
no-release-lock lane assert only what that lane can honestly prove: the imported
`agent.skill_commands` really is the authenticated baseline checkout named by
`AETHER_EXACT_HERMES_CHECKOUT`, verified with `verify_clean_checkout` plus digest agreement.
A checkout that is neither the pinned fork nor the authenticated baseline now **fails closed**
rather than silently passing. This is a bounded oracle correction, not a widening of the
objective and not evidence that the fork claim was weakened: the fork claim is still asserted
on the fork lane and was mutation-tested.

### 3. Disposable profile role scoping and absence

- Role inventory derivation from candidate release distribution:
  - Derived from candidate role scoping (`_CANDIDATE_ROLE_SKILLS` / `_role_skills`):
    - `morfeo`: 9 common canonical skills + `plan` (total 10)
    - `supervisor`: 9 common canonical skills (`plan` absent, total 9)
    - `implementer`: 9 common canonical skills (`plan` absent, total 9)
- Physical disk inspection:
  - `<morfeo>/skills/plan/SKILL.md`: present and matches candidate bytes
  - `<supervisor>/skills/plan`: does not exist (strictly absent)
  - `<implementer>/skills/plan`: does not exist (strictly absent)
- Native slash registration inspection across home configurations:
  - In minimal managed homes (containing only Aether managed skills):
    - `HERMES_HOME=<morfeo>`: `scan_skill_commands()` registers `/plan` pointing to `<morfeo>/skills/plan/SKILL.md`
    - `HERMES_HOME=<supervisor>`: `scan_skill_commands()` does not contain `/plan` (`has_plan=False`)
    - `HERMES_HOME=<implementer>`: `scan_skill_commands()` does not contain `/plan` (`has_plan=False`)
  - In realistic profile homes (including the pinned fork's bundled Plan-Mode skill `skills/software-development/plan/SKILL.md`):
    - `HERMES_HOME=<morfeo>`: canonical root `skills/plan/SKILL.md` wins over the bundled shadow; `/plan` resolves to `<morfeo>/skills/plan/SKILL.md`
    - `HERMES_HOME=<supervisor>`: managed root resource `skills/plan` remains absent; `/plan` resolves to `<supervisor>/skills/software-development/plan/SKILL.md` (description: `Write a markdown plan to .hermes/plans/; no execution.`)
    - `HERMES_HOME=<implementer>`: managed root resource `skills/plan` remains absent; `/plan` resolves to `<implementer>/skills/software-development/plan/SKILL.md` (description: `Write a markdown plan to .hermes/plans/; no execution.`)

### 4. Planning-only semantics static specification checks (Decision 5)

No shipped Python module in `aether_agents` writes `.aether/plans` directly (`grep -rn 'aether/plans' src/aether_agents --include='*.py'` returns 0 hits); rather, the planning procedure is executed by Morfeo under prompt guidance from `skills/plan/SKILL.md`. As behavioral model turns were not performed in this headless run, Decision 5 semantics are verified via static specification checks against the candidate `plan` skill artifact:

- 5a (Project-local creation): The skill procedure explicitly mandates keeping the plan at one stable `.aether/plans/<objective-slug>.md` inside the explicitly resolved project, and explicitly instructs to end after writing or updating the plan file without writing implementation code, dispatching workers, or creating task cards. Verification instructions require confirming no task cards, boards, or code edits were created during planning.
- 5b (Idempotent repeat): The procedure explicitly instructs: "Reuse and update the existing file across invocations for the same objective; never create duplicate files or global plans."
- 5c (Project separation): The procedure requires resolving the project root explicitly and warns in Pitfalls against writing plans to global, user home, or framework default locations instead of the project-local `.aether/plans/<objective-slug>.md` path.
- 5d (Absent/ambiguous project binding): The procedure explicitly instructs: "Stop and surface ambiguity if no single project or objective can be identified."
- 5e (Forecast not a cap): The procedure explicitly mandates: "Treat anticipated Objective Contracts as a revisable forecast (never a cap). Mark uncertainty honestly; new contracts are justified by remaining obligations, not forced by a predetermined quota." Pitfalls explicitly list: "Treating anticipated Objective Contracts as a numerical cap or mandatory quota."

### 5. Behavioural observation distinction

- Real model turn: **NOT PERFORMED**.
- Rationale: Under PD-71 and role authority boundaries, headless automated unit execution has no provisioned model API credentials and is strictly prohibited from acquiring credentials, invoking remote models, or triggering live gateway / agent sessions.
- In accordance with task instructions and review findings, static file checks, native loader selection, role absence, and specification checks were executed in full and independently verified; behavioural model turns are recorded as not performed due to headless environment isolation.

## Known red (composition-owned, not unit-owned)

`tests/test_public_artifacts.py::test_canonical_base_manifest_matches_tracked_non_specs_files` fails in this isolated worktree due to base manifest inheritance:
- At base commit `2e347ab3`, `.aether/objective-contracts/oc_c29c2b0ed38d5030/v1.md` was tracked but absent from the `.github/workflows/policy.yml` heredoc (base delta = 1; 448 tracked vs 447 in heredoc).
- In this isolated worktree, `tests/test_plan_skill_dispatch.py` is additionally tracked without editing `policy.yml`, producing a delta of 2 (449 tracked vs 447 in heredoc).
- `PLAN-CANDIDATE` (`t_e2c6f3bd`) added both lines to the `policy.yml` heredoc in commit `3da14572` (450 lines in heredoc vs 449 tracked in its branch, pre-registering this unit's test file).
- This oracle is composition-owned, requires no repair in this unit, and passes on the composed integration revision.

## Remaining risk and limits

- Qualification is confined to the pinned maintained Hermes fork `aed6591a69f453a1867b73628603e7b53ba40ffc`. Public newer Hermes documentation regarding built-in `/plan` was not treated as target runtime proof.
- No live profile, active release, gateway unit, credentials, or remote services were touched.
- All exercises used disposable roots and scrubbed environments.
- Publication, pull requests, releases, and integration remain Supervisor-owned.
