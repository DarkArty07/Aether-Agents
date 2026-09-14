# Collaboration authoring and handoff evidence

## Owner direction and route

The owner approved autonomous execution after reviewing the native-runtime scope and preliminary size estimate, explicitly requiring the plan before implementation. The approved objective includes the principal Aether and scoped maintained-fork delivery, installation in the already provisioned runtime and closure of #334/#317/#407 as a mitigation with long-term behavioral efficacy unverified.

This is pipeline work because it changes native coordination and multiple role/protocol/installation responsibilities. Independent review can catch delivery-vs-ack confusion, authority promotion, cross-session routing, controller/dependency regressions and unsafe installation. Morfeo authored the plan/shared design; Supervisor owns decomposition, review, integration and ordinary closeout. No implementation unit has been authored by Morfeo.

## Plan first

`b7914f73545b14389f92fcaeed05247cf86f5f7d` committed `spec.md`, `plan.md`, `quickstart.md` and `research.md` before product implementation or worker dispatch. The design preserves sectorized identities and existing native coordination; D1-D9 state shared behavior and bounded local freedom. A source-supported optional same-board collaboration record/metadata is used instead of another service or semantic judge.

## Canonical identity and validity

- Verified portable Aether Project: `12027989-a08f-41cd-a82c-54ff1bfb6b03` and its existing GitHub repository `DarkArty07/Aether-Agents`.
- One canonical finalized contract: `oc_a28ff9b7fa20d29d@v1`.
- Relative artifact: `.aether/objective-contracts/oc_a28ff9b7fa20d29d/v1.md`.
- Final artifact SHA-256: `7a51dc2b3d2d62788b1228f823f9def58652e48d48fcecaecb5293f34dde7de5`.
- Trace: `ctr_80c325f04f9cae67bb4fcce7a782889c`.
- Native incremental authoring: all required sections supplied independently; revision 12 validated with `valid=true` and no missing sections, then finalized by the native tool. Finalization is not Supervisor receipt or functional acceptance.

The authoring session initially had no resolved Git workspace. The existing native Project switch restored binding; an explicitly anchored temporary authoring Project points at this same-repository worktree. No SessionDB or registry was manually rewritten to fabricate authoring authority. Handoff must use the exact primary Project returned by `prepare_handoff`, not the temporary author's display name.

## Design sufficiency self-review

- CE-01..CE-12 cover exact identity, early questions, proactive evidence, durable consumption/disposition, peer authority, native surface parity, controller/independent-work preservation, stale/end-of-flow handling, role resources, merge/adoption and issue/residue closeout.
- D1-D9 settle the optional create/comment interface, DB responsibility, response semantics, actual transport consumers, coalescing, false user-identity prevention, contract changes, ownership and bootstrap on the pre-change runtime.
- `done` on the decomposition root is explicitly not terminal flow completion.
- Tests use actual native state/APIs with controlled external sinks; source/resource loading is observed without calling a model. Mechanical PASS is not long-term behavioral qualification. Required repository gates are preserved.
- Current instruction supersedes #317's open-ended tracking disposition, not evidence history or owner authority. The stopped monitor remains outside implementation/activation scope.
- No claim of independent receipt, unit coverage or runtime activation is made at authoring time.

## Checks performed by Morfeo

Using the already provisioned interpreter, from this worktree:

```text
python -B -m pytest -q tests/test_contract_quality_documents.py tests/test_contract_result_review.py
14 passed in 0.29s
```

This is unchanged-resource regression evidence at the plan-authoring base, not tests of the not-yet-implemented collaboration feature. `git diff --cached --check` passed before the plan commit. No model/Telegram canary, live board mutation or runtime installation was used to claim design validity.

Role work-memory is now available after binding; a concise source-inspection lesson was saved successfully. Initial availability limits remain disclosed in `research.md`. No graph or session memory replaces the canonical design.
