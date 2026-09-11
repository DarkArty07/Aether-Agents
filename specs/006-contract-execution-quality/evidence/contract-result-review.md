# Morfeo contract-result reception — #379

## Authority, scope and provenance

The owner approved direct Morfeo implementation of the proposed SOUL instruction and
canonical reception skill, with issue closeout and no Supervisor/Implementer agents.
This is a bounded prompt/resource correction, not a new runtime acceptance engine.
The owning clarification is in `DESIGN.md` section 10.1; root guidance points to it.

Inspected baseline: `ad9c5c8e549986923f8b220c76eaac3cb83ba736`.
The design research in [#379](https://github.com/DarkArty07/Aether-Agents/issues/379)
compared the existing Morfeo and Supervisor SOULs and canonical skills with Hermes'
existing skill loader and Spec Kit `analyze` / `checklist` at
`03a79d14ec785626db1dc300444f5b9154606e82`. Existing loading and document analysis are
reused; neither upstream checklist nor board completion is semantic result acceptance.

All checks below were run directly by Morfeo. This is **self-review**, not an independent
Supervisor receipt, a new multi-agent run or evidence of universal agent compliance.

## Request-to-result self-review

| Requested outcome | Actual artifact | Direct check and result |
| --- | --- | --- |
| Explicit Morfeo reception before claiming completion | `resources/profiles/morfeo/SOUL.md`, Completing pipeline work | Read final instruction: owner intent and contract, exact final revision, every material criterion, evidence attribution and limits are explicit. |
| A reusable method, not a new gate | `resources/skills/contract-result-review/SKILL.md` | Read all six steps; no new role, hook, board state, schema or mandatory full-suite rerun. |
| Inspect content, not only status | Skill steps 1–4 | Requires the actual artifact/location for each material criterion and decisive checks; hashes and green unrelated tests cannot replace semantic inspection. |
| Honest evidence provenance | Skill steps 2, 4–6 | Distinguishes directly verified, reused and unverified evidence; stale revisions require impact justification or rerun. |
| Preserve authority and roles | SOUL, DESIGN and skill decision/pitfalls | Supervisor retains pipeline closeout; material mismatches use supported rework; no owner-acceptance waiver, product takeover or completed-board rewrite. |
| No ceremonial work after a correct result | Skill step 6 | A supported result ends reception without another card or repeated review. |
| Canonical distribution | `lifecycle.py::_CANONICAL_SKILLS`, packaging/lifecycle tests | Existing bundle mechanism includes exact skill bytes and preserves collision/ownership/rollback checks. No second loader/registry. |
| Available to this Morfeo | Native profile SOUL and skill | Exact source-byte equality, collision preflight, rollback copy, successful native `skill_view` in this session. No other live profile was changed. |
| Direct execution and bounded closeout | Git diff, issue/PR and native calls | No agent delegation or Kanban card creation; no website/docs edits, deployment, provider/configuration change or release. GitHub closeout evidence is recorded in the issue/PR after merge. |

Resource paths above are relative to `src/aether_agents/`.

## Executed verification

- RED: the bundle allowlist test failed because `contract-result-review` was missing;
  all three new reception-resource tests also failed before the instruction/skill existed.
- GREEN focused: `uv run --frozen pytest -q tests/test_contract_result_review.py
  tests/test_contract_quality_documents.py tests/test_observation_packaging.py
  tests/test_observation_lifecycle.py` — **111 passed, 1 skipped**. This includes real
  wheel/sdist bytes, profile bundle/activation/collision/rollback behavior in disposable
  state. The skip was the optional native loader in the ordinary dev interpreter.
- Native loader: the already provisioned Hermes interpreter ran
  `tests/test_contract_quality_documents.py::test_native_loader_reads_exact_documents_in_disposable_home`
  — **1 passed**. The loader consumed the four procedure documents, including the new
  skill, from isolated native-home files with exact hash equality; no model invocation.
- `scripts/check_documentation.py` passed. The existing literal public manifest and
  tracked Markdown link/fence checks passed with both new paths explicitly listed.
- Ruff on all changed Python paths passed; format check on new/edited receipt-document
  tests passed. `mypy src/aether_agents` passed (53 source files).
- Full bootstrap: `uv run --frozen python scripts/run_tests.py -- -q` — **1133 passed,
  64 skipped, 445 subtests passed, 2 failed** in 396.92 seconds. The exact failing nodes
  are `tests/test_public_artifacts.py::test_tracked_public_surface_contains_no_operator_paths`
  and `tests/test_same_card_phase_predicates.py::test_initial_review_requires_an_independent_reviewer`.
  Both were reproduced unchanged in an isolated worktree at baseline
  `ad9c5c8e549986923f8b220c76eaac3cb83ba736` using the same interpreter and exact-Hermes
  bootstrap: **2 failed in 0.89 seconds**. The relevant tests, scanner and Hermes baseline
  are unchanged. This is baseline attribution, not a green full-suite claim.
  All production/resource bytes tested match source commit
  `893666c208c2a8713f3bf9f9716a16006c346590`; the subsequent amendment only records evidence.

### Pre-existing limitations

Repository-wide Ruff reports seven findings in three untouched knowledge/contract-test
files. `git diff HEAD` on those paths is empty. They are recorded separately in
[#380](https://github.com/DarkArty07/Aether-Agents/issues/380), not silently repaired,
ignored in changed-file checks or represented as a green whole-repository lint run.
The known immutable-contract scanner baseline from #364 is not modified or exempted.

## Local resource adoption and rollback

Preflight: the live Morfeo SOUL equaled the baseline resource, neither target was a
symlink, the new skill name did not collide, and the operator-managed profile had no
ReleaseStore ownership marker. No marker was fabricated. Only Morfeo's SOUL and new
skill were copied through the normal guarded file surface, with exact readback:

- SOUL SHA-256: `e298c2a14eb73b4c5f5f4aba51755c2bb4a92b3b3a467991e67595d1ad4ac924`.
- Skill SHA-256: `75883a60482207994706e55193f2a71192a2ad422560c441aa6eaf58ef6f9cf6`.

The previous SOUL and a private adoption manifest were saved outside the disposable
worktree. Rollback can restore those bytes and remove only the new same-hash skill;
first compare current hashes and preserve any subsequent user edits. No rollback drill,
profile restart or full release activation was performed. Existing sessions can retain
loaded instructions; this session explicitly loaded the new skill and applied its
bounded direct-self-review procedure. New ordinary sessions read the updated SOUL.

## Limits and release conclusions

This verifies authored instructions, distribution/loading and one direct self-review.
It does **not** qualify all future Supervisor-result receptions or every negative case.
Organic behavior (missing criterion, stale evidence, inaccessible material checks,
justified reuse and clean completion without redundant testing) remains under
[#317](https://github.com/DarkArty07/Aether-Agents/issues/317), with actual outcomes only.

`release_impact=minor`: additive portable canonical procedure, no removed public API.
`release_action=defer`; `release_channel=none`: no version bump, tag, package, deployment
or release. End-user CLI, tool schemas and capability status are unchanged; no current
web/manual page needs modification for this instruction-only method clarification.
The lifecycle source change is one addition to the existing resource allowlist.
