# KG19-INT — Terminal integration, acceptance and closeout of `oc_d96969bf913512f7@v1`

**Status:** terminal integration record for Objective Contract `oc_d96969bf913512f7@v1`
(Issue #505 — first-turn proactive Morfeo project orientation).

**Base commit:** `03797e9f8f4f0c68b8daa256d52d9e0a56800526`
**Breakdown:** `specs/005-project-knowledge-graphify/tasks-505.md` at `bbd3831e` (Supervisor-owned)

## 1. Integrated units (each preserved as its own commit, no rewrite)

| Unit | Reviewed commit | Merge into integration branch |
| --- | --- | --- |
| KG19-01 packaged first-turn trigger | `0b462384` | `b6655e65` |
| KG19-02 isolated E01 with controls | `4e5d35da` | `8f3ad14e` |
| KG19-03 explicit orient-before-exploration order | `97ea1bec` | `8c6806f3` |
| KG19-04 owner-authorized omission record | `82b9a248` | `3522629a` |
| Owner testing decision (tracked stage artifacts) | `c5b01c08` | `4c4c06d4` |

Every reviewed unit commit remains individually inspectable as its own commit; nothing was
squashed, amended, rebased or otherwise rewritten. The owner's decision commit was merged
with ancestry preserved.

## 2. Acceptance verification against the contract

**AC-1 — trigger present and proportional in the packaged resources.** Met at the delivered
bytes. The Morfeo SOUL carries the conditional first-turn clause with its explicit order
("before repository content searches and answer-bearing source reads"), the no-universal-savings
and no-ceremonial-call boundaries, the greetings/trivial/directly-supplied-source exemption,
and the honest-degradation clause. The packaged `project-knowledge` skill states the order in
"When to Use", "How to Run", Procedure step 2 and a Pitfalls entry. Distribution is verified by
the lifecycle materialization oracle over a fresh profile home (independently reviewed in
KG19-01 and reaffirmed in KG19-03). Delivered hashes equal the independently reviewed KG19-03
bytes:

- Morfeo SOUL `a1c997634ddface5d0f86744ff24cc23b964145a20d736d1ced4b3c23ef1d7f8`
- `project-knowledge` SKILL `41436ff6cd9f64cd3b82d2e7a160d22454b0c01bb604b67674a3c08471c38e27`

**AC-2 — executed, attributed E01 positive result: NOT VERIFIED BY OWNER DECISION.**
This is an accepted omission, not a PASS and not a failure. On the initial KG19-01 bytes E01 was
executed twice on valid trials and in both the graph was consulted only after substantive source
exploration (`evidence/KG19-02.md` §3.1, §4, §4.1; `evidence/E01-evidence.json`). KG19-03
corrected the wording in response. The planned single re-qualification turn (KG19-04) was
cancelled by direct owner instruction — "solo haz las modificaciones y hasta ahí no lo pruebes" —
and the omission is recorded in the owning stage artifacts (`spec.md`, `validation.md` at
`c5b01c08`) and in `evidence/KG19-04.md`. First-turn behavior on the corrected bytes remains
**unqualified** pending the owner's organic use. No success was simulated.

**AC-3 — controls and honest degradation.** Historical result retained: the exact-source control
made no ceremonial graph call, and the unborn-HEAD path is isolated by a deterministic no-spend
witness (`SCOPE_UNAVAILABLE`, no commit, no index, no installation). The live unborn control is
recorded with its real observed code (`PROJECT_UNRESOLVED`) rather than being relabelled.

**AC-4 — preservation.** Only packaged resources, their tests, the objective's `specs/` artifacts
and the CI base-manifest registration changed. Supervisor and Implementer SOULs, `work-memory`,
packaged `config.yaml` templates (opt-in stays `enabled: false`), the frozen lab scenario set,
lockfiles and the Objective Contract are untouched. The primary checkout's four pre-existing
local modifications were neither read nor written.

**AC-5 — gates, PR, checks, merge, issue.** Required CI gates and the merge are recorded in §5.

## 3. Integration repairs performed by Supervisor (distinct from reviewed unit work)

One bounded repair, mechanically implied and behavior-free: the merge of the owner's decision
commit conflicted with KG19-04 in `specs/005-project-knowledge-graphify/validation.md`, because
both added a paragraph at the same location. I resolved it by preserving **both** records in
sequence — the KG19-02/KG19-03/KG19-04 observed-result paragraph first, then the owner's
testing-decision paragraph — with no text dropped or reworded. `spec.md` auto-merged cleanly.

This repair was authored by me, not independently reviewed; it changes no product behavior and
introduces no new requirement. Its verification is read-only: zero conflict markers remain,
`git diff --check` is clean, and the tracked-Markdown fence/link sweep over 383 files reports no
violations.

## 4. Verification actually performed, and deliberate omissions

Owner direction cancelled further agent-run testing for this objective, including focused,
unit and packaging test runs; only the repository's automatic required checks remain as a merge
gate. Accordingly:

Performed (read-only, no test execution):

- delivered resource SHA-256 versus the independently reviewed KG19-03 hashes: equal;
- CI base manifest set-equality (448 expected / 448 actual) and presence of the contract path;
- integration history shape: five `--no-ff` merges, each unit commit an ancestor;
- `git diff --check` clean; no conflict markers anywhere in the tree;
- tracked-Markdown fence and relative-link sweep: 383 files, no violations;
- operator-path scan on the changed artifacts: none.

Deliberately **not** performed, with reason: the contract Testing Standard's executable battery
(`scripts/run_tests.py`, ruff, mypy, compileall, `check_documentation.py`,
`check_public_artifacts.py`, `uv build`) and the E01 re-qualification. Reason: the owner's current
instruction explicitly forbids new discretionary agent-run tests for this objective and directs
delivery of the modification without a live-behavior claim. The automatic required CI checks are
not discretionary agent tests and still gate the merge.

Disclosed honestly: unit KG19-04's log shows discretionary lint/documentation/public-artifact
checks executed after the owner changed direction. That is not presented as a test-free
execution; the disclosure and its history are preserved in `evidence/KG19-04.md`.
Fixture-only changes produced solely for the cancelled qualification are retained as
`specs/005-project-knowledge-graphify/fixtures/e01_morfeo_orientation_lane.py` with its history
and evidence, not silently absorbed or erased; the pinned hashes in that lane were updated to the
corrected KG19-03 bytes.

## 5. GitHub closeout

Recorded from durable Git and check state at completion (see the terminal handoff for the exact
observed values): objective branch pushed, pull request opened against `main` with its checks
and merge result, and Issue #505 reconciled against the real outcome. Required check contexts
for `main` are `pull-request-target`, `policy (3.11)`, `policy (3.12)` and `policy (3.13)`.

## 6. Release conclusions (recorded separately from their compatibility evidence)

- **`release_impact = patch`** — supporting evidence: the change is an additive, backward-compatible
  refinement of packaged role/skill guidance. No tool signature, argument schema, configuration
  default, CLI contract or dependency changed; the plugin stays opt-in (`enabled: false`); no
  existing oracle was weakened. Every unit reported `patch`, and the aggregate agrees. It is not
  `none`, because shipped packaged artifacts that reach a fresh profile home did change.
- **`release_action = defer`** — supporting evidence: the objective contract forbids tag, package
  publication, deployment, activation and cutover for this objective, and the standing RC8
  candidate remains a local-only, unpushed artifact. A merge does not imply a release.
- **`release_channel = none`** — supporting evidence: no release artifact is prepared or published
  by this objective, so no channel is engaged. Prerelease is a channel and is never a
  compatibility-impact class.

These three conclusions are independent of one another and of the compatibility evidence above.

## 7. Preservation and remaining risk

Preserved: live Morfeo profile resources, live board, other active worktrees and sessions, and the
primary checkout's pre-existing local edits. Not performed: runtime activation, profile
modification, service restart, tag, publication or deployment.

Remaining risk, stated plainly: **first-turn orientation behavior on the corrected bytes is
unverified.** The wording correction is supported by static, packaging and distribution evidence
and by the observed failure on the earlier bytes, but no agent-run measurement establishes that it
changes real first-turn behavior. The owner will assess it organically. Prior E01 trials remain
historical evidence about the earlier bytes only.
