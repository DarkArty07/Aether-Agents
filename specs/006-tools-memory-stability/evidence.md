# Evidence — tools, memory and runtime stability

## Authoring receipt (Morfeo; not independent review)

Source baseline: cc93451799ded171c38fea98188e02fd75b0fe74. Earlier inspected baseline
b1baad948bc21e956d291c8d40abb2add6033b3c differs in the current Supervisor review-convergence
procedure, which is preserved and referenced. No product fix has been implemented by
this authoring run.

Executed in the managed authoring worktree:

- Portable fixtures/binding_privacy_probe.py, using source/test helper imports:
  **5 failed, 9 passed in 0.85s**. The failures are the intended baseline RED for
  non-Git native-cwd explicit binding and tool_calls/error privacy/storage. This is
  not a green implementation result. The compound shell command continued to the
  independent document/diff checks; its final exit status is not the probe status.
- `python3 scripts/check_documentation.py`: documentation validation passed.
- `git diff --check`: no whitespace errors at that authoring checkpoint.
- Final contract capability validation returned valid=true at draft revision 12;
  finalized v1 digest is 69765e73e657b7c0854454a4257a43e5f113ed9c4deb9c6559c536b374a5c040.
  On-disk bytes match. The literal policy manifest matches the staged tracked non-spec
  paths exactly (no missing/extra entries).
- `python3 scripts/check_public_artifacts.py` FAILED on the same two inherited findings
  in `.aether/objective-contracts/oc_0084270d940c98d9/v1.md`: absolute-user-home and
  operator-desktop-layout. That artifact is unchanged by this objective. No added-stage
  path was reported. This is an inherited verification limitation, not a passing scan
  or a newly granted exception; terminal acceptance must reconcile the actual gate.
- The existing focused code baseline was previously exercised: 259 passed/1 native
  Graphify prerequisite skip. No full exact-public-baseline rerun or behavioral
  qualification is claimed for this design-only change.
- The real native knowledge/memory session recovery and published per-issue evidence
  are linked in research.md. Session recovery is not source-level correction.

## Author cold-read check

| Concern | Owning location | Author result / limit |
|---|---|---|
| Complete owner scope | spec.md TS-373/390/389/382/275/P/C | All five remain required; no silent omission. |
| Buildable material design | plan.md TS-373/390/389 | Identity, typed privacy and script-discovery boundaries are selected; equivalent private choices delegated. |
| Unresolved feasibility | spec.md research gates; plan.md TS-275/382 | Explicit bounded research acceptance, then autonomous Morfeo design checkpoint; not mislabeled ready to build. |
| Preservation versus real tests | spec.md authority; quickstart.md isolation | Objective-owned test/board/canary writes allowed; unrelated state protected. |
| Runnable verification | quickstart.md; diagnostic fixture | Baseline RED exercised; future production/full/native qualification belongs to implementation/integration. |
| Root/child lifecycle | Objective Contract and canonical Supervisor procedure | Supervisor owns tasks.md and verified fan-out; root must release children, not wait for implementation. |
| Release and external authority | spec.md decisions/authority | Expected compatibility patch is unverified until diff review; action defer/channel none; no deployment or publication. |
| Intake/guidance | spec.md intent | Reuse five canonical issues; existing AGENTS.md/constitution preserved. |

Structural contract validation/finalization, independent receipt review and eventual
unit/criterion coverage are distinct facts. This is an author self-check only; no
Supervisor-produced tasks or independent review existed at this checkpoint.

## Execution evidence owner

Supervisor and Implementer append attributed research/implementation/review/integration
receipts here: requirement, artifact location, producer, exact source/candidate/integrated
revision, command/tool, result, limits and authorized omissions. Do not commit runtime
paths, session/board routing identifiers, private model/endpoint choices or raw content.
Morfeo records final contract-result-review after inspecting the actual integrated result.

## Supervisor integration receipt (terminal card; not independent unit review)

Terminal card `t_e4ba4b4e` consumed the seven reviewed units and the two recorded design
checkpoints. It re-verified each unit's approval and commit before integration; unit-level
claims below are attributed to their producer, and the integration checks marked
"Supervisor-observed" were run by this card.

**Aether integration (no history rewrite).** All seven unit branches were merged with
explicit merge commits onto the objective branch; every unit tip remains an ancestor and
each unit's files are byte-identical to its reviewed branch tip. Integration HEAD
`1b06eb1100c60ce017a72aab6c3423f0f335b0e3` (merge commits `666d17d`, `509a5a4`, `2816a38`,
`0b7d77c`, `acda9f4`, `dd3725d`, `1b06eb1`). Worktree clean; contract v1 digest unchanged.

**Maintained-fork integration.** Fork base `266e412fb83ad32af92ed391db942f88993d76a2`;
reviewed tips `6c96428f640d1405a8f34d8619ac6d6378cb53c0` (U389), `72890d48304fb61b88dc00ed6ab4749a505ed20a`
(U382F), `780a6f6c7550cb6202069a1f8821fe4d4d785633` (U275F) merged without conflict into
`6da4a79773d98cfd43b8e9e108aeb9eec860c0cd`. The three portable patches were generated from
those tips, recorded in `HERMES_LOCAL_PATCHES.md` (HLP-275/382/389), and each verified with
`git apply --check` against an archived base tree.

| Requirement | Integrated source | Supervisor-observed evidence | Limit / disposition |
|---|---|---|---|
| TS-373 | `src/aether_agents/knowledge/bindings.py` (unit commit `61a8c6d`) | Probe fixture on the integrated tree: **14 passed** (baseline `5 failed/9 passed`); focused lane 443 passed/6 skipped | Real native operator canary belongs to runtime adoption; see the adoption section below |
| TS-390 | `src/aether_agents/observation/{contracts,privacy}.py` (unit commit `0a519e3`) | Same probe run: all four histogram cases pass; `mypy` 53 files clean; docs check clean | Native post-adoption canary not run in this card (see limits) |
| TS-389 | fork `cron/lifecycle_guard.py` at `6c96428f64` | Guard suite 296 passed/0 failed; runtime canary on the adopted tree: harmless heredoc log read **accepted**, direct restart and referenced real script **blocked**; the same canary on an archived base tree blocks the harmless path | Adopted; see adoption section |
| TS-382 | fork `hermes_state.py`, `hermes_state_common.py`, `hermes_state_compaction.py`, `hermes_state_search.py`, `agent/conversation_compression.py` at `72890d4830` | Unchanged oracle: base `266e412f` RED `2 failed/8 passed` twice (longest hold 1.917 s vs 1.0 s budget); integrated tree GREEN `10 passed` on two consecutive runs | One earlier integrated run showed the legacy concurrent-append case exceeding its 1.0 s fixture budget under host contention (1 of 5 runs); recorded, not hidden |
| TS-275 | fork `tools/vision_tools.py` at `780a6f6c75` | Canary on the adopted runtime: the outgoing auxiliary request carries the image byte-identically (640x360 → data URL 10290, decoded sha256 `e87e8160…` = source) and the oversized image is prepared to exactly `100x5000` with an 18,654-character data URL and scale disclosure | **End-to-end image interpretation is NOT reproducible right now**; see the routing boundary below |
| TS-P | scope above | Fork suites (state 250/0, guard 296/0, vision 101/0, callers 204/0) on the integrated tree; Aether probe/focused/format/mypy/docs/build checks | Live database, unrelated services and unrelated worktrees untouched; private fixtures outside Git |
| TS-C | this receipt | Required closeout state recorded in the terminal card completion | Issue dispositions below |

**TS-275 routing boundary (exact evidence, no oracle weakening).** After adoption, six
bounded real calls through the provisioned vision operation returned `success: true` but did
not interpret the image. The model answered "you forgot to attach or upload the image" or
described unrelated content for: the oversized acceptance fixture, both within-policy
controls (including one sent byte-identically), and a trivially simple 600x300 test image
that never touches this repair. The routing product's own record shows the operation
(`operation_label: vision`, model `gemini-3.8-flash-low`, provider `antigravity`) completing
with text-scale token counts, so the image is lost between the Hermes client and the
upstream model. That surface is a separate product outside this objective's authority.
Consequently TS-275 acceptance is **not claimed**: issue #275 stays open, and the recorded
research acceptance (that the route could interpret image-only content earlier the same day)
is preserved as attributed prior evidence rather than overwritten.

**Scoped runtime adoption (Supervisor-observed).** The reviewed fork fixes were adopted into
the live editable runtime by copying only the seven changed files plus the new
`hermes_state_compaction.py`; every one of those files was byte-identical to the fork base
before adoption, so no unrelated dirty file was overwritten. Pre-adoption copies, a SHA-256
manifest and a `RESTORE.sh` rollback script are retained outside Git under the private
rollback directory. Post-adoption hashes match the reviewed candidate blobs. Byte-identical
in-caps images, the guard canary and the state oracle all pass against the adopted tree.

**Explicit limits of this card.** (1) A full exact-public-baseline `scripts/run_tests.py`
qualification was not run; the reconciled local evidence is the full local suite plus the
declared lanes. (2) The native `aether_observe` canary for TS-390 and the tool-level
knowledge canary for TS-373 require the Aether package to load the integrated sources in the
operator runtime; the runtime currently resolves `aether_agents` from the primary checkout,
so those canaries become effective after this branch merges and the primary checkout is
refreshed — recorded as pending rather than claimed. (3) `scripts/check_public_artifacts.py`
still reports only the two pre-existing findings in the unchanged
`oc_0084270d940c98d9/v1.md`; no new finding was introduced by this objective.
