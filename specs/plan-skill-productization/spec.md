# Canonical project-local `/plan` for Morfeo (#504)

**Status:** owner-approved objective; implementation and independent review pending. Scope corrected by owner: source merge, not historical release qualification.
**Decision owner:** project owner. **Route:** Morfeo design → Supervisor → Implementer(s).
**Owning higher requirements:** R2-FR-204b–f, R1-FR-116a/121a, R5 role isolation, R7 convergence, `DESIGN.md` §10.
**Technical design:** [plan.md](plan.md). **Validation:** [quickstart.md](quickstart.md).

## Owner outcome and boundaries

A user who explicitly invokes `/plan` with Morfeo in an Aether Project receives a planning-only, durable Objective Plan in **that project's** `.aether/plans/`, not in a global Aether repository or Hermes's generic plan folder. The plan bounds the whole requested objective with an observable beginning, closure, exclusions, useful route and operational history. It anticipates Objective Contracts when knowable without imposing a numerical cap: a contract delegates one justified portion of work; it does not replace or enlarge the plan's owner intent. Morfeo also plans autonomously when continuity is useful without requiring the user to type `/plan`.

This objective makes the explicit `/plan` interface portable to fresh Aether installations by packaging an Aether Canonical Skill named `plan` **only in Morfeo's native profile**. `objective-contract-design` retains the substantive planning/contract method; the new skill is a focused, non-overlapping entry. Existing Project Canonical Skills and the precedence/authority model remain intact.

Scope is the reviewed source, documentation, tests and integration to `main` through the normal green PR path. It does **not** authorize modifying active profile bytes, restarting sessions/gateway, installing/updating or rolling back the live runtime, creating/publishing an Aether release, changing the Hermes fork, or manually deploying. A merge is not an activation or a behavioral qualification of every future model turn.

## Scenarios and observable requirements

### US-PS-1 — Explicit plan, no execution

With an exact Aether Project and a requested feature, `/plan` creates one `.aether/plans/<objective-slug>.md` under that project, containing a bounded destination, preservation/exclusions, route, anticipated delegations if supportable, continuity and stop/replan condition. It neither creates an Objective Contract nor a board, nor edits implementation code merely because the user asked for a plan. A later invocation for the **same objective** updates that same file after checking current sources and previous failures rather than multiplying plans. Different objectives in one project have distinct files; the same feature in different projects has separately bound plans. An ambiguous or missing Project binding causes no plan write or inferred selection.

### US-PS-2 — Useful contract forecast without a quota

The plan may describe the purpose of expected Objective Contracts, marking uncertainty; new contracts are justified by remaining obligations and evidence rather than constrained by a predetermined count. Every actual pipeline handoff remains one finalized Objective Contract with its own delegated authority and convergence/attempt bounds. A supported objective closes; repeated same-cause failure or invalidated premises trigger stop/replan instead of a new card/contract to keep working. Simple questions and bounded direct work do not acquire a mandatory `/plan` ceremony.

### US-PS-3 — Reproducible, role-limited distribution

A fresh candidate wheel/sdist contains public sanitized `skills/plan/SKILL.md`; its authenticated role bundle and native Morfeo home contain identical bytes. Supervisor and Implementer retain the previous canonical skill inventory and must not load a new `plan`. The selected maintained Hermes fork resolves literal `/plan` to the Aether-owned Morfeo skill, including when the private learned skill with the same frontmatter name exists under a different local path. A future fork with built-in `/plan` must be detected and treated as incompatibility, not silently presented as qualified.

### US-PS-4 — Package isolation and operator state

The candidate's package/bundle contains `plan` only in Morfeo and rejects missing, extra, forged, cross-role or mismatched candidate resources without weakening existing guards. Disposable fresh-profile tests preserve unrelated learned skills (including a nested `plan`) and operator-owned config. The existing installed manager may reject a candidate wheel whose resource set changed; disclose that limit instead of claiming an update works. Historical release transitions, bridge qualification, compensation and rollback are **not** acceptance gates for this source-only merge: no installation or activation was requested. Do not touch currently installed profiles, other sessions or worktrees.

### US-PS-5 — Coherent public guidance and evidence

The Objective Plan guide, relevant canonical-skill/profiles documentation and capability status explain the actual shipped `/plan` behavior, project-local location, scope, role ownership and current native compatibility, while distinguishing source/packaging tests from live agent behavior and release activation. Root `AGENTS.md` is reconciled only if the authorized change makes an instruction inaccurate. Historical generic-Hermes wording is not silently represented as new Aether behavior before code/tests pass.

## Functional requirements

- **PS-001:** Morfeo's package-owned skill MUST be named `plan` and be offered as `/plan` only when the selected Hermes runtime supports skill slash dispatch without collision.
- **PS-002:** On explicit `/plan`, Morfeo MUST remain in planning-only mode and resolve the exact Aether Project/objective before writing; absence or conflict stops without selecting by recency/name/cwd alone.
- **PS-003:** The plan MUST live at one stable `.aether/plans/<objective-slug>.md` for that objective in its own project. Reinvocation MUST preserve prior decisions and failed approaches and refresh changeable evidence.
- **PS-004:** Plans MUST identify outcome, scope/exclusions, closure and stop/replan conditions, route and attributed continuity without acting as a contract or board. Anticipated contract handoffs MAY be revised and MUST NOT become a numerical cap.
- **PS-005:** The skill MUST refer to `objective-contract-design` for contract extraction and MUST NOT copy the generic Hermes microtask/TDD/commit/delegate recipe or prescribe another mandatory ceremony.
- **PS-006:** Aether's candidate wheel, sdist, role bundle and disposable native profile materialization MUST deliver the new canonical skill **only to Morfeo**; existing role skill inventories and ownership boundaries remain sound. No live activation is authorized.
- **PS-007:** Candidate package/bundle validation MUST enforce Morfeo's exact inventory and the unchanged exact inventories of Supervisor and Implementer. Malformed, duplicate, missing and cross-role candidate resources MUST fail closed; do not weaken existing integrity checks. Do not represent historical upgrades as qualified by candidate-only tests.
- **PS-008:** Disposable fresh-profile loading and same-name learned-skill selection MUST preserve unrelated/operator state; no live profile overwrite or release transition is permitted. A later release/update/rollback objective owns historical transition qualification.
- **PS-009:** The selected fork's native slash dispatch MUST select the canonical plan bytes for Morfeo; a built-in command collision MUST block qualification.
- **PS-010:** Applicable R2 guidance, current-build documentation, capability registry, packaging/role tests and runnable verification MUST be updated together; documentation MUST NOT claim release or activation from a merge.
- **PS-011:** Work happens in isolated worktrees/branches, retaining unrelated live profile/session/worktree/release state; PR/check/merge are normal reviewed source closeout, never a gateway restart or package publication.

## Acceptance and stopping

Trace US-PS-1–5 and PS-001–011 through [quickstart.md](quickstart.md). A passing static resource check or even a green PR alone does not prove model behavior or an upgrade path; report the exact scenarios exercised and remaining limits. Stop if exact Project identity is unresolved, the selected runtime no longer offers dynamic `/plan`, a protected effect would be needed, or the design would grant a new role/authority or broaden the objective. If the source merge is otherwise green, do not extend it into historical release qualification; report that separately as unqualified, without manufacturing another release or permission exception.
