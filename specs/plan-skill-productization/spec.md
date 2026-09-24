# Canonical project-local `/plan` for Morfeo (#504)

**Status:** owner-approved objective; implementation and independent review pending.
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

### US-PS-4 — Previous releases and operator state remain usable

The new manager accepts an authentic pre-`plan` profile bundle with its original exact inventory and a new profile bundle with `plan` only in Morfeo. It rejects missing, extra, forged, cross-role or mismatched resources; hashes/provenance are not weakened. Fresh install, old→new preparation, new→old rollback and failed-transition compensation are exercised in disposable roots. Managed `plan` bytes are removed on rollback only after ownership validation; unrelated learned skills (including an existing nested `plan`), operator-owned configuration, other profiles, sessions, and worktrees remain unchanged. If the selected installed predecessor cannot read the new wheel directly, its refusal is recorded and a separately qualified compatible transition is required **before any live update**; no shortcut through a manual profile edit or false release claim is permitted.

### US-PS-5 — Coherent public guidance and evidence

The Objective Plan guide, relevant canonical-skill/profiles documentation and capability status explain the actual shipped `/plan` behavior, project-local location, scope, role ownership and current native compatibility, while distinguishing source/packaging tests from live agent behavior and release activation. Root `AGENTS.md` is reconciled only if the authorized change makes an instruction inaccurate. Historical generic-Hermes wording is not silently represented as new Aether behavior before code/tests pass.

## Functional requirements

- **PS-001:** Morfeo's package-owned skill MUST be named `plan` and be offered as `/plan` only when the selected Hermes runtime supports skill slash dispatch without collision.
- **PS-002:** On explicit `/plan`, Morfeo MUST remain in planning-only mode and resolve the exact Aether Project/objective before writing; absence or conflict stops without selecting by recency/name/cwd alone.
- **PS-003:** The plan MUST live at one stable `.aether/plans/<objective-slug>.md` for that objective in its own project. Reinvocation MUST preserve prior decisions and failed approaches and refresh changeable evidence.
- **PS-004:** Plans MUST identify outcome, scope/exclusions, closure and stop/replan conditions, route and attributed continuity without acting as a contract or board. Anticipated contract handoffs MAY be revised and MUST NOT become a numerical cap.
- **PS-005:** The skill MUST refer to `objective-contract-design` for contract extraction and MUST NOT copy the generic Hermes microtask/TDD/commit/delegate recipe or prescribe another mandatory ceremony.
- **PS-006:** Aether's wheel, sdist, role bundle, release identity and native activation MUST deliver the new canonical skill **only to Morfeo**; existing role skill inventories and ownership boundaries remain sound.
- **PS-007:** Release validation and profile transitions MUST distinguish strict historical and new role inventories from the authenticated release evidence, rather than applying one current global list to all releases; malformed sets MUST still fail closed.
- **PS-008:** Fresh install, prospective old→new migration, rollback, compensation and uninstall MUST preserve operator/private state and handle a same-name learned skill without unverified overwrites or selection ambiguity.
- **PS-009:** The selected fork's native slash dispatch MUST select the canonical plan bytes for Morfeo; a built-in command collision MUST block qualification.
- **PS-010:** Applicable R2 guidance, current-build documentation, capability registry, packaging/role tests and runnable verification MUST be updated together; documentation MUST NOT claim release or activation from a merge.
- **PS-011:** Work happens in isolated worktrees/branches, retaining unrelated live profile/session/worktree/release state; PR/check/merge are normal reviewed source closeout, never a gateway restart or package publication.

## Acceptance and stopping

Trace US-PS-1–5 and PS-001–011 through [quickstart.md](quickstart.md). A passing static resource check or even a green PR alone does not prove model behavior; report the exact scenarios exercised and remaining limits. Stop if exact Project identity is unresolved, the selected runtime no longer offers dynamic `/plan`, old-release compatibility cannot be shown in isolation, a protected effect would be needed, or the design would have to grant a new role/authority or broaden the objective. Report the incomplete state instead of manufacturing another release or permission exception.
