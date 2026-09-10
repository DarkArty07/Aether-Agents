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
