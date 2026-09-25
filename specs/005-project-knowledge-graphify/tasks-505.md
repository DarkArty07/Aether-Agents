# First-turn project-knowledge orientation (#505) — Supervisor task breakdown

**Status:** active execution breakdown for Objective Contract `oc_d96969bf913512f7@v1`.

**Derived by:** Supervisor, decomposition root card `t_fbcc54ab`.

**Source contract:** `.aether/objective-contracts/oc_d96969bf913512f7/v1.md`
(SHA-256 `00c92805d49a19fecf82b896dfeb69cd1bf115ea8c1fd6ac8b76360384e6195c`)
on Aether base `03797e9f8f4f0c68b8daa256d52d9e0a56800526`.

**Objective board:** `oc-12027989a08f41cda82c54ff1bfb6b03-d96969bf913512f7-v1`
(its `worktree_base_ref` is the base above; unit worktrees start at that base and do
not inherit this file — read it read-only with
`git show <breakdown-sha>:specs/005-project-knowledge-graphify/tasks-505.md`).

This file is Supervisor-owned execution decomposition. It does not widen the Objective
Contract, and card bodies remain the executable unit deliveries. The prior
`tasks.md` SK-01–SK-INT breakdown belongs to `oc_f2acfb5effb21f6d@v1` and is historical
context, not an input to this objective.

**Owning requirements:** `specs/005-project-knowledge-graphify/spec.md` KG-19;
`specs/005-project-knowledge-graphify/validation.md` E01;
`specs/005-project-knowledge-graphify/research.md` §6; Issue #505.
**Continuity note:** the local, untracked Objective Plan
`.aether/plans/graphify-first-turn-adoption.md` in the isolated authoring worktree is
context only; it never substitutes these obligations.

## Receipt

| Check | Observed |
| --- | --- |
| Portable project | `.aether/project.toml` `project_id` equals the handoff `12027989-a08f-41cd-a82c-54ff1bfb6b03` |
| Contract bytes | SHA-256 `00c92805d49a19fecf82b896dfeb69cd1bf115ea8c1fd6ac8b76360384e6195c` matches the envelope |
| Base / HEAD | `03797e9f8f4f0c68b8daa256d52d9e0a56800526` (`docs(contracts): finalize first-turn knowledge orientation`), parent `e7011eea` |
| Design inputs present at base | `e7011eea` carries the KG-19 requirement, the E01 clarification and the #505 research entry; `specs/005-project-knowledge-graphify/contracts/soul-and-skills.md` owns the resource insertion points |
| Execution board | native board bound to `oc_d96969bf913512f7@v1`; no default-board fallback |
| Design sufficiency | trigger ownership (Morfeo SOUL), procedure and visible skill description (`project-knowledge` SKILL), positive and negative E01 controls, preservation boundary, authority and stop conditions are settled; no material product decision is missing |
| Profiles | `implementer`, `supervisor`, `morfeo` exist; no extra roles are created |
| Provisioned inputs | managed Graphify 0.9.54 component configured in the operator state root; the provisioned model route is reachable; structural mode needs no model call |
| Known base debt (required fix) | the CI `Validate canonical base manifest` step fails on this base: exactly one tracked non-`specs/` path is missing from `.github/workflows/policy.yml`, namely `.aether/objective-contracts/oc_d96969bf913512f7/v1.md`. Registering it is a mechanically implied obligation of this objective, not a widened scope |
| Primary checkout | the primary checkout holds pre-existing local modifications that this objective must not read, reset, stash, checkout or commit; only the isolated objective worktrees are written |

## Cross-artifact executability

| Concern | Settled conclusion | Execution consequence |
| --- | --- | --- |
| Behavior owner | The Morfeo SOUL owns the first-turn trigger; the packaged `project-knowledge` SKILL owns the procedure and the description Hermes shows in its skill index (KG-19; `contracts/soul-and-skills.md`). | Only these two versioned resources change behavior. The Supervisor and Implementer SOULs keep their existing shared knowledge paragraph. |
| Activation vs. behavior | Shipping improved guidance is not a profile opt-in change. The portable templates keep `aether-project-knowledge` `enabled: false`; KG-01/02/05/10/11 stay untouched. | No template or opt-in edit. A disposable test profile may enable the plugin explicitly as test configuration only. |
| Static vs. behavioral evidence | Packaging, format and discovery tests can prove distribution and text presence; they cannot prove adoption. E01 with a real isolated Morfeo is the behavioral oracle (KG-19; `validation.md` §4). | `KG19-01` produces deterministic evidence; `KG19-02` produces attributed real-call evidence. Neither is reported as the other, and a text-only test is never PASS for E01. |
| Test ownership | `tests/test_knowledge_resources.py` already asserts the skill frontmatter (`description` ≤ 60 chars ending in `.`, `platforms: [linux]`), the required headings, that every JSON example validates through `validate_arguments`, absence of `/home/` text, and the three-role tool-parity strings in each SOUL. `scripts/qualify_knowledge_expansion.py` owns the 14 + 5 example catalog. | Extend these oracles; never weaken, skip or delete an existing assertion to obtain green. The skill description must keep fitting the packaging budget while leading with the orientation trigger. |
| Index rendering budget | Hermes renders a skill to the model as `<name>: <description>` and truncates a long description, so the visible trigger has to lead the string; the existing ≤ 60-char oracle keeps the whole description inside that rendered window. | Lead the description with the proactive orientation trigger, not with maintenance wording. |
| E01 lane shape | The E01 fixture (disposable project with two subsystems, a documented decision, a commit and a structural index) does not match the 16 frozen `lab/scenarios/e2e-*.json` scenarios, and `tests/test_e2e_harness.py` asserts exactly those 16 contiguous scenario ids. | Build a dedicated disposable qualification lane (precedent: `scripts/qualify_knowledge_expansion.py`; portable fixture precedent: `specs/006-tools-memory-stability/fixtures/`). Do not edit the frozen scenario set or its oracle for this objective. |
| Isolation boundary | `aether_agents/lab/isolation.py::isolated_hermes_env` scrubs `HERMES_KANBAN_*`, `HERMES_SESSION_*` and task/run/project/tenant/cwd identity and pins disposable home, board, workspaces and XDG roots; `aether_agents/lab/runner.py::prepare_profiles` copies candidate config and tracked SOUL into isolated profiles without touching the source. | Reuse these reviewed primitives. Add disposable skill materialization and explicit test-only plugin enablement; never mutate live homes, the live board or other sessions. |
| Component reuse | `aether knowledge configure --python <interpreter>` binds an already-provisioned isolated Graphify interpreter inside the active state root without installing anything, and `--mode structural` builds a local structural index that never calls a model. | Point the disposable state root at the provisioned component interpreter; install nothing and enable no semantic extraction. |
| Model spend | The contract authorizes E01 with the already provisioned model connection. Graph queries and status calls never call a model; only the agent turns themselves are spend. | Bounded, minimum-sufficient live sessions, each attributed with provider usage. The committed lane refuses to spend unless explicitly acknowledged and never runs under CI. |
| Publication | Implementer commits locally and never pushes, opens the PR, merges, closes #505 or mutates live profiles. | Terminal Supervisor owns acceptance, PR, checks, merge, issue reconciliation, cleanup and the aggregated release conclusions. |

## Requirement coverage

| Source | Unit | Notes |
| --- | --- | --- |
| AC-1 (trigger) | KG19-01 | Morfeo SOUL trigger, skill description and body, packaging/materialization/discovery oracles |
| AC-2 (E01 positive, real calls) | KG19-02 | Disposable two-subsystem project, real isolated Morfeo turn with no Graphify hint, attributed call and response evidence |
| AC-3 (controls, honest degradation) | KG19-02 | Trivial and exact-source control; missing index/binding/component and unborn-HEAD control; no ceremonial call, no install, no commit, no rebuild, no invented project |
| AC-4 (preservation) | independent review, then KG19-INT | Only packaged resources and their tests, docs and evidence change; live profile, services, other worktrees and sessions, and the primary checkout's pre-existing local edits stay untouched |
| AC-5 (closeout) | KG19-INT | Focused tests, the `CONTRIBUTING.md` gates, PR checks and review, merge, #505 reconciliation, residue cleanup, exact final receipt |
| Deliverable: preservation record and separate release conclusions | KG19-INT | `release_impact` / `release_action` / `release_channel` recorded separately, with no release effect |
| Base debt: CI base manifest | KG19-01 | Register `.aether/objective-contracts/oc_d96969bf913512f7/v1.md` in `.github/workflows/policy.yml` |

## Shared decisions (stamp into every unit)

1. The changed behavior surface is exactly two versioned resources: `src/aether_agents/resources/profiles/morfeo/SOUL.md` and `src/aether_agents/resources/skills/project-knowledge/SKILL.md`. Do not edit the Supervisor or Implementer SOULs, `work-memory`, the packaged `config.yaml` templates, `home/` profiles or installed copies.
2. Executable text stays in English, consistent with the existing durable prompts and packaged skills.
3. The trigger is: on the first substantive request to understand a bound project's architecture, dependencies, implementation or documented decisions, discover the canonical `project-knowledge` skill and consult an available graph of that exact project and revision without waiting for the owner to name Graphify, using the result to narrow current-source inspection. It is not a global order to query before every file read, it promises no universal savings or obedience, and it does not require a graph call for greetings, trivial questions, or a directly supplied source.
4. The skill body teaches bounded, useful consultation: `query` → `explain` → snapshot-local `community`; refinement with names or symbols actually observed, or a fallback to source search; reading current sources before designing or concluding; and honest reading of revision, coverage and warnings. Natural-language questions are noisy because the worker passes the text through Graphify, and the procedure says so instead of implying semantic answering.
5. Preserve every existing oracle: the `tests/test_knowledge_resources.py` frontmatter, heading, example and tool-parity assertions; the three-role parity strings; the `scripts/qualify_knowledge_expansion.py` 14 + 5 catalog validation; `scripts/check_documentation.py` registry coherence; and the policy workflow gates. Add focused fail-first tests; never weaken, skip or delete an assertion.
6. No new dependencies, installs, credentials, credential widening or semantic/auxiliary spend. Queries and status calls never invoke a model.
7. No hook, daemon, watcher, autoload or `skills.auto_load` behavior is added, and no Graphify global install or raw path command is introduced.
8. Evidence stays sanitized: project-relative paths, revisions and bounded call/usage records only; no private transcripts, machine paths, credentials, personal memories or full graph payloads. Markdown evidence under `specs/005-project-knowledge-graphify/evidence/` keeps balanced code fences and only resolvable relative links, because the repository policy gate checks every tracked Markdown file.
9. Tracked Python outside `specs/` must be registered in `.github/workflows/policy.yml`; portable diagnostics and fixtures under a stage's `fixtures/` directory are admitted by the existing policy rule without registration. Keep the lane inside `specs/005-project-knowledge-graphify/fixtures/` unless a non-`specs/` path is genuinely required.
10. Units commit locally on their own branch and never push, open the PR, merge, close the issue or activate anything. Same-card review is the unit review lane; KG19-INT consumes reviewed units and does not replace unit review.
11. Unit compatibility evidence is reported per unit; the aggregate `release_impact` / `release_action` / `release_channel` conclusions belong to KG19-INT. No tag, package publication, deployment or cutover.
12. E01 is reproducible and attributed: it records the exact resource bytes, the fixture revision, the index status and revision observed before the model call, the order of skill discovery and knowledge calls, the references used, the subsequent source reads, the answer, and the provider usage per call.

## Execution graph

```text
t_fbcc54ab (Supervisor decomposition root)
    -> KG19-01 package the first-turn orientation trigger (Implementer, isolated worktree)
    -> KG19-02 E01 isolated real-Morfeo qualification with controls
         (Implementer; after independently reviewed KG19-01)
    -> same-card Supervisor review on each implementation unit
    -> KG19-INT terminal integration, acceptance, publication and closeout
         (Supervisor, same flow, terminal = true)
```

KG19-02 is serialized on reviewed KG19-01 because E01 exercises the packaged candidate
resources: running a real Morfeo session against bytes that are about to change would
invalidate the evidence and spend live model calls twice. No unit edits a file the other
owns. KG19-01 owns the two resources, their focused tests, the CI manifest registration
and its packaging evidence; KG19-02 owns the disposable E01 fixture, lane and evidence,
and touches `validation.md` only where the observed E01 result makes the accepted stage
artifact honest.

## KG19-01 — package the first-turn orientation trigger

- Source: AC-1; KG-19; `specs/005-project-knowledge-graphify/contracts/soul-and-skills.md`; this unit.
- Outcome: `src/aether_agents/resources/profiles/morfeo/SOUL.md` owns an explicit first-turn project-understanding trigger that consults available project knowledge without the owner naming Graphify, keeps direct-source and trivial questions proportional, and preserves the existing knowledge and memory boundaries. `src/aether_agents/resources/skills/project-knowledge/SKILL.md` carries that trigger in its visible description and teaches the bounded `query`/`explain`/`community`, refinement, honest revision and coverage reading, and current-source verification flow. Focused tests extend the existing oracles with packaging, discovery and fresh-profile materialization evidence. Excludes: any behavioral claim about a real agent, live profiles, the E01 lane, semantic extraction, opt-in changes and KG-01/02/05/10/11 text.
- Inputs: base `03797e9f8f4f0c68b8daa256d52d9e0a56800526`. No prerequisite unit. Shared decisions 1–9 and 12 apply.
- Boundaries: writable `src/aether_agents/resources/profiles/morfeo/SOUL.md`, `src/aether_agents/resources/skills/project-knowledge/SKILL.md`, `tests/test_knowledge_resources.py`, `.github/workflows/policy.yml`, `specs/005-project-knowledge-graphify/evidence/KG19-01.md`, and — only if the changed documented behavior requires it — `docs/guides/project-knowledge.md`, `docs/reference/plugins-and-tools.md`, `docs/capabilities.toml` with its generated `docs/reference/capabilities.md`. Preserve `tests/test_documentation.py`, `scripts/check_documentation.py`, `scripts/qualify_knowledge_expansion.py`, the other role resources, the substance of `spec.md` / `validation.md` / `research.md`, lockfiles and the Objective Contract.
- Judgement: exact wording in the Morfeo SOUL and the skill, the description string inside its existing length budget, which focused tests are added, and whether documented user-facing behavior changed. Escalate if the trigger cannot be made visible without weakening an existing assertion or widening a KG-01/02/05 boundary.
- Verification: fail-first focused tests, then `uv run --frozen pytest -q tests/test_knowledge_resources.py tests/test_documentation.py`, the lifecycle packaging and materialization modules, and `tests/test_public_artifacts.py`; `uv run --frozen python scripts/check_documentation.py`, using its `--write` mode only if the registry changed, followed by inspecting the resulting diff; the CI base-manifest step reproduced verbatim so the expected list equals `git ls-files | grep -v '^specs/'` sorted with exit 0; `uv run --frozen ruff check`, `ruff format --check` and `mypy` on affected Python; `git diff --check`. Evidence records the exact resource hashes before and after and the fresh-profile materialization result.
- Dependencies: decomposition root only.
- Completion: local commit; same-card review; report the unit compatibility impact and the resource hashes for KG19-02 to consume; no push.

## KG19-02 — E01 isolated real-Morfeo first-turn qualification with controls

- Source: AC-2 and AC-3; `specs/005-project-knowledge-graphify/validation.md` E01 and the contract Testing Standard; KG-19; this unit.
- Outcome: an executed, attributed E01 on the reviewed KG19-01 resource bytes. A disposable project with two subsystems and a documented decision, committed, registered under a disposable identity, and indexed structurally through the provisioned component; then a real Morfeo in a new isolated disposable profile and session receives a technical request that never mentions Graphify and discovers and loads `project-knowledge`, consults the graph early with the correct project, revision and coverage, then reads the current sources and distinguishes a documented specification from implemented behavior. Separate controls record honest proportionality and degradation: a trivial question or a directly supplied exact source produces no ceremonial call; a missing index, binding or component and an unborn repository produce no invented project, no installation, no commit, no rebuild and no spend, and communicate the limit plainly. Excludes: product behavior changes, live-profile mutation, editing KG19-01 resources, semantic extraction, new package installs, and CI execution of the lane.
- Inputs: the independently reviewed KG19-01 commit and its resource hashes; base `03797e9f8f4f0c68b8daa256d52d9e0a56800526`. Merge the reviewed KG19-01 commit into this worktree with a merge commit; do not rewrite or re-edit its files. If the run exposes a defect in the resources or the procedure, report it as rework for KG19-01 instead of editing it here. Shared decisions 3–12 apply.
- Boundaries: writable `specs/005-project-knowledge-graphify/fixtures/` (the new portable lane and fixture), `specs/005-project-knowledge-graphify/evidence/` (new records), `specs/005-project-knowledge-graphify/validation.md` only for the E01 status or pointer text the observed result supports, and — only if a non-`specs/` tracked file is genuinely required — the matching `.github/workflows/policy.yml` registration line, appended after KG19-01's own edit. Preserve the two packaged resources, the other roles' resources, the frozen `lab/scenarios/e2e-*.json` set and its oracle, KG-01/02/05/10/11, live homes, other worktrees and sessions, and the primary checkout's pre-existing local edits.
- Judgement: the lane entry point and fixture layout, how the disposable profile materializes the candidate skills and enables the plugin as test configuration, which isolation primitive to reuse, and how many bounded live sessions the positive case and controls need — minimum sufficient, never a rerun for reassurance.
- Verification: `uv run --frozen python scripts/run_tests.py -- <focused lane>` for the committed deterministic parts; the disposable structural index built with `aether knowledge update --project-id <uuid> --role morfeo --workspace <root> --mode structural --json` inside the isolated XDG roots, with `status` and revision confirmed before any model call, and `aether knowledge configure --python <provisioned component interpreter>` used instead of any install; the real Morfeo turn run through the existing isolated invocation shape (`hermes --accept-hooks -p morfeo --usage-file … --in <repo> chat -q <query> -Q`) against the disposable home, board and session; sanitized evidence attributing producer, revision, call order, coverage, references, source reads, answer and per-call usage for the positive case and for each control; before-and-after witnesses that the live home, the live board and the primary checkout are unchanged. The committed lane refuses to spend unless explicitly acknowledged and does not run under CI. `ruff`, `ruff format --check` and `mypy` on affected Python; `git diff --check`.
- Dependencies: independently reviewed KG19-01. Reason: the E01 oracle is the packaged candidate behavior, and the evidence is invalid if those bytes change afterwards.
- Completion: local commit; same-card review; report the observed result honestly — a failed or partial E01 is reported, never written as complete, and acceptance stops rather than substituting static tests; no push.

## KG19-INT — terminal integration, acceptance, publication and closeout

- Source: AC-4 and AC-5, the contract deliverables, its authority section; `DESIGN.md` §10.1; this unit.
- Outcome: the reviewed unit commits preserved as their own commits on one objective branch, with this breakdown committed if it is not already there; acceptance verification against the contract; a PR to `main` whose required checks are green without bypass; a verified merge at exactly that commit; #505 reconciled against the real result; residue limited to branches and worktrees created by this objective and cleaned only after durable evidence; a preservation record for the primary checkout's pre-existing local edits and for other active sessions; and the separate conclusions `release_impact` / `release_action` / `release_channel` with no release, tag, publication, deployment or activation. If the E01 lane cannot be isolated with the provisioned access, or fails without a justified local correction, the objective stops and reports instead of relaxing E01.
- Inputs: this decomposition root, reviewed KG19-01 and reviewed KG19-02. Preserve each as its own commit; no squash, amend, rebase or history rewrite.
- Boundaries: integration-owned conflict, import, wiring, path and `.github/workflows/policy.yml` repairs that introduce no new behavior. A behavior gap returns as implementation rework. Do not touch the live Morfeo profile, other worktrees or sessions, or the primary checkout's local modifications.
- Verification: the contract Testing Standard in full — focused resource, skill, packaging and knowledge lanes; `uv run --frozen python scripts/run_tests.py`; the repository quality checks; `git diff --check`; `scripts/check_documentation.py`; `scripts/check_public_artifacts.py`; `uv build`; the required PR checks (`pull-request-target`, `policy (3.11)`, `policy (3.12)`, `policy (3.13)`); then the GitHub closeout procedure. Confirm the merged resource bytes hash-equal the bytes E01 ran against, because a mismatch invalidates that E01 evidence for the changed resource. Evidence: `specs/005-project-knowledge-graphify/evidence/KG19-INT.md`.
- Dependencies: the decomposition root and both reviewed implementation units; this card is `terminal = true`.
- Completion: terminal Supervisor closeout only when the merged result and the durable board, Git, check, issue and cleanup state support it; local integration alone is not success.

## Authority and stop conditions

The owner's current instruction authorizes this bounded behavior change, autonomous
execution and normal closeout with a pull request, review, green checks and merge to
`main` in the already provisioned repository, without new credentials and without
bypass. Stop and escalate through the existing path, preserving the candidate and the
evidence, if the project or Hermes Project identity becomes ambiguous; if the work would
require redefining KG-01/02/05 or activating profiles by default; if progress would
require touching the primary checkout's pre-existing local edits (notify the owner
before, and never reconcile them on your own); if a test would need to write to an
installed Morfeo profile or another active session; if the real E01 cannot be isolated
with the provisioned access or fails without a justified local correction; or on a
genuine protected-edge denial, an attempted bypass, red checks without an in-scope
correction, or an impossible normal green merge. Do not open a runtime repair chain and
do not lower E01 or acceptance to reach `done`. The inability to build a first index in
a repository without `HEAD` is the expected fallback, not permission to commit
automatically.
