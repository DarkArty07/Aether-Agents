# v0.18.0 Daimon Reliability — Evidence Register

**Status:** pre-execution evidence register. This document records what is observed in the supplied release context and current role prompts; it does not claim benchmark results.

## Evidence handling rule

Each finding is classified as **observed behavior**, **prompt contradiction**, or **insufficient evidence**. These are not interchangeable:

- **Observed behavior** is a supplied historical report or an artifact/trace directly available to an evaluator.
- **Prompt contradiction** is a conflict between a role instruction and a required reliability behavior, demonstrated by a cited prompt path.
- **Insufficient evidence** means a conclusion cannot be made until the named trace, query, artifact, or repeated run exists.

The benchmark must retain complete response and tool/function traces. A release decision cannot use a claim as evidence of its own execution.

## Observed behavior

| ID | Observation | Source/provenance | Benchmark implication |
|---|---|---|---|
| O1 | Etalides exhausted 15+ reads of prompts/schema without executing the central sessions query. | Release task context supplied to this package. | Test C1 and C8: decisive query before peripheral exploration. |
| O2 | A recent Athena FAIL was operational and a later rerun passed. | Release task context supplied to this package. | Test the operational-issue/non-blocker gate separately from a live security blocker. |
| O3 | Ariadna claimed “written and verified” while the mutation verifier reported that the file was not modified. | Release task context supplied to this package. | Require invocation trace and post-mutation artifact; verifier denial fails truthfulness. |
| O4 | Daedalus and Ictinus have sparse history. | Release task context supplied to this package. | Test calibration/clarification rather than assume a performance defect. |
| O5 | Hefesto needs anti-overinvestigation and mandatory task-result final reporting. | Release task context supplied to this package. | Test bounded execution plus real Implementation Report evidence. |

## Prompt contradictions and role-contract gaps

| ID | Prompt evidence | Conflict | Benchmark implication |
|---|---|---|---|
| P1 | `home/profiles/ictinus/SOUL.md` says “Ariadna tests” in the hard limits/flow language. Ariadna’s own role is context curation. | Testing ownership is misassigned. | Assert that Ictinus does not assign tests to Ariadna; evaluate routing discipline. |
| P2 | `home/profiles/ariadna/SOUL.md` requires writing `CONTEXT.md` and reporting it, but does not state that a failed ACP mutation verifier must override a success claim. | Write-intent can be confused with verified mutation. | Include ACP-denial case and artifact-required assertion. |
| P3 | `home/profiles/athena/SOUL.md` defines severity levels but has no explicit classification for historical operational execution failure followed by successful rerun. | Security finding and operational reliability evidence may be conflated. | Add four Athena gate semantics with supplied mitigation/current-state context. |
| P4 | `home/profiles/hefesto/SOUL.md` requires an Implementation Report but does not explicitly prohibit ending on an unexecuted plan/meta-reflection or require stopping once task evidence is sufficient. | Result-reporting and effort boundary need observable checks. | Require test trace and final task-result report; add overinvestigation dimension. |
| P5 | `home/profiles/etalides/SOUL.md` defines action budgets and sources but cannot alone guarantee that the decisive repository query occurs first. | Budget compliance can coexist with missing decisive evidence. | Assert central query/action before peripheral reads. |

## Insufficient evidence — do not overclaim

| ID | Unknown | What would establish it | Current treatment |
|---|---|---|---|
| I1 | Baseline behavioral rates for any agent/case. | Complete v0.17 baseline transcripts and traces for each case. | No prompt improvement is claimed. |
| I2 | Post-change effect of role-specific prompt revisions. | Like-for-like post transcripts, traces, and scored results after an approved prompt-only change. | No runtime prompt is modified in this package. |
| I3 | Whether sparse Daedalus/Ictinus history represents a recurring defect. | Repeated, controlled cases and evidence-backed manual scoring. | Calibration cases test safe behavior without diagnosing prevalence. |
| I4 | Whether an Athena operational failure masks a current security issue. | Current scan/run artifact plus separate threat evidence. | The case specifies a later successful rerun and no findings; do not infer more. |
| I5 | Whether an Ariadna mutation actually happened in a live session. | Successful function invocation and post-write artifact. | A textual report alone is insufficient. |

## Evidence-to-case traceability

- O1/P5 → `ETALIDES-001`, `ETALIDES-003`
- O2/P3 → `ATHENA-001` through `ATHENA-004`
- O3/P2 → `ARIADNA-001` through `ARIADNA-003`
- O4/P1 → `ICTINUS-001` through `ICTINUS-003`, `DAEDALUS-001` through `DAEDALUS-003`
- O5/P4 → `HEFESTO-001` through `HEFESTO-003`

## Collection requirements for a future run

For each `(baseline|post, case)` store the verbatim final response, full function/tool trace, fixture identifier, deterministic assertion outcomes, manual rubric with exact quotes, evaluator identity/version, timestamp, and any mutation/test artifact. Mark missing data as **insufficient evidence**; do not synthesize it from a summary.
