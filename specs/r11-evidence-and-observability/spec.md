# R11 Specification: Evidence, Observability, and Evaluation

**Roadmap ID**: R11
**Stage status**: done — reconciled 2026-08-21 for PD-51, PD-56, PD-59, PD-64, PD-66, and A1 public-path qualification
**Accepted**: 2026-08-17 — Christopher accepted the R4–R13 Decision Review
**Amended**: 2026-08-18 — proportional direct-work evidence under PD-44
**Decision authority**: Christopher
**Autonomous design delegate for this stage**: Supervisor
**Future role owner**: Supervisor
**Depends on**: R2, R3, R7, R8, R9, R10, `DESIGN.md`
**May affect**: R12, R13
**Parent roadmap**: `../../ROADMAP.md`
**Selected Hermes baseline**: `NousResearch/hermes-agent` `v2026.8.18`, commit `e624e9fde561e1add9388384012b295fde669ade`, distribution version `0.20.4`

## 1. Purpose

R11 decides what counts as proof that work was done, how the owner sees it, and how a claim about the system itself is qualified.

The owner reviews by running the product, retrospectively, having approved nothing in advance (PD-14). That makes evidence the only thing standing between "an agent said it finished" and "it works". R11 is therefore not a reporting stage; it is the stage that makes acceptance possible.

R11 does not select models (R12) or authorize any run (R13).

## 2. The Deliverable Is the Running Product

- **FR-1101**: For product work delivered through the pipeline, the reviewable deliverable is the running product, not a diff, a log, or a summary (R1-FR-117). Direct operational work requires evidence proportional to the actual objective and testing standard.
- **FR-1102**: Every pipeline body of work MUST ship a runnable validation path with prerequisites, commands, and expected outcomes, carried by the contract's quickstart artifact (R2-FR-203). A direct action has no synthetic contract quickstart; it records the actual command, inspection, or diff used for proportional verification.
- **FR-1103**: Each converged user story MUST be independently runnable, so a failure in a later story leaves earlier ones inspectable and usable (R2-FR-228).
- **FR-1104**: The pipeline validation path MUST be executed by the system before work is reported as done. An unrun validation path is documentation, not evidence.
- **FR-1104a**: A direct PD-44 action MUST execute the testing standard the owner selected for that objective and report what was not tested. For DOC-09/P5-F13, Christopher selected mechanical configuration/syntax/diff checks only and deferred functional route validation to himself; the build therefore MUST NOT claim functional verification.

## 3. Per-Unit Evidence

In pipeline work, contract-level validation proves the whole; per-unit evidence proves each part and is what the next unit reads. Both are required and they are not substitutes. A direct action has no delegated unit, so its completion report answers the same material questions from actual tool output without inventing card metadata.

Every completion MUST answer four questions:

1. What changed?
2. How was it verified?
3. What would unblock or retry this if it failed?
4. What risk is deliberately left open?

- **FR-1105**: Every delegated unit MUST complete with a human-readable summary and structured metadata carrying, at minimum: the files changed, the verification actually run, and the residual risk knowingly accepted. A direct action reports those facts in Morfeo's response from observed state.
- **FR-1106**: Evidence MUST describe what was actually executed, not what was intended. A verification listed but not run is a false claim, not an omission.
- **FR-1107**: A unit with no files and no tests MUST say so explicitly and record whatever evidence does exist — sources consulted, decisions made, manual steps performed.
- **FR-1108**: Structured metadata MUST NOT carry secrets, raw logs, tokens, or unrelated transcripts. Pointers and summaries only (R9-FR-908).
- **FR-1109**: A decision card's evidence is the decision itself, stated as binding, with the reasoning that produced it (R7-FR-718).
- **FR-1110**: A denied protected effect MUST appear in the unit's evidence, including what was attempted and why it was refused (R10-FR-1014).
- **FR-1110a**: Repeated attempts at a denied effect MUST surface as a reportable condition in their own right, not as a series of unrelated single denials. R10-FR-1015 declares the pattern reportable; the pattern is only visible where denials are counted per unit, so evidence MUST distinguish one refusal from a worker routing around a gate.

## 4. Evidence Classes and Severity

Not all findings are equal, and treating them equally is how the important ones stop being read.

| Class | Severity | Disposition |
|---|---|---|
| Constitution conflict | Highest | Resolved by changing spec, plan, or tasks — never by diluting the principle (R3-FR-306, R2-FR-218) |
| Contract defect | High | Escalated to Morfeo; never worked around (R7 tier 2) |
| Requirement with no task, or task with no requirement | High | Repaired in the artifact that owns it before execution proceeds |
| Failed verification | High | The unit is not complete |
| Out-of-scope defect noticed | Reported | Raised as a question; never silently fixed or discarded (PD-16) |
| Residual risk accepted | Reported | Recorded in evidence and surfaced in the end-of-work report |
| Hotspot flag | Reported | Two on one path trigger decomposition (R7-FR-744) |

- **FR-1111**: A constitution conflict MUST outrank every other finding class.
- **FR-1112**: An out-of-scope defect MUST reach the end-of-work report as a question, neither applied nor dropped (R1-FR-122).
- **FR-1113**: Accepted residual risk MUST be visible to the owner. Risk recorded only in a card the owner never opens is not disclosed.

## 5. The End-of-Work Report

- **FR-1114**: Morfeo MUST assemble a pipeline end-of-work report from durable board state, never from its own recollection of the run (R1-FR-122). For direct work it MUST use actual tool output, current repository diff, and observed state.
- **FR-1115**: The report MUST list the increments delivered, each with its validation path.
- **FR-1116**: The report MUST list every unit that terminated as not converged, with its budget and its last state, presented as a legitimate outcome rather than a failure (R1-FR-121).
- **FR-1117**: The report MUST list external failures separately from contract defects. The owner may act on the first or authorize a separate direct operational objective; Morfeo already handled the second.
- **FR-1118**: The report MUST list out-of-scope defects and accepted residual risk as questions.
- **FR-1119**: A pipeline report MUST NOT claim an outcome the board does not record (R5-FR-538). A direct report MUST NOT claim an outcome the executed tools or current project state do not establish.

## 6. Observability During a Run

The runtime records board transitions, runs, worker logs, and health. Aether reuses those surfaces and adds only product-owned transition/release evidence needed to prove install, update, rollback, package, platform, privacy, and publication claims. It does not duplicate board execution state.

- **FR-1120**: Aether MUST NOT build a parallel pipeline-observability layer. Native events, runs, logs, and diagnostics remain authoritative for delegated execution; Aether's manager records only its own lifecycle and release evidence (FR-503).
- **FR-1120a**: Liveness, semantic progress, and termination MUST be reported separately. A status, process, stream chunk, or heartbeat proves activity/liveness only; none is a percentage or proof that the objective advanced.
- **FR-1120b**: Retry evidence MUST distinguish dispatcher failure retries, clean-exit protocol corrections, resumptions, redispatches, review cycles, and authorized lifecycle corrections. A zero technical failure counter MUST NOT be reported as “no retries” when other logical attempts occurred.
- **FR-1121**: Every pipeline repository change MUST be attributable to a unit, profile, and attempt (R5-FR-535). Every direct change MUST be attributable to Morfeo's profile and session with the actual diff or command result available.
- **FR-1122**: A unit that never gets picked up MUST be detectable. The runtime reports a unit whose assignee produces no claim, and the design MUST NOT depend on someone noticing its absence by eye.
- **FR-1123**: Watching a run MUST be possible without interrupting it. Reading the board is not participation.

Current issue state is part of the release-visible evidence boundary:

- Aether `#192`, **OPEN** at inspection on 2026-08-21, owns machine-readable retry/resumption/lifecycle accounting.
- Aether `#195`, **OPEN** at inspection on 2026-08-21, owns semantic-progress evidence beyond heartbeat.

The selected source reinforces rather than closes those issues. `tools/kanban_tools.py:277-286` describes a runtime-activity-to-board-heartbeat bridge explicitly as liveness and keeps manual heartbeat notes optional. `kanban_db.py:4952-4967` reclaims stale activity even for a live PID, but that still does not prove useful task progress. Neither issue closes until its own acceptance criteria are executed and recorded.

## 7. Qualifying Claims About Aether Itself

This project has already paid twice for treating documentation as evidence — once by researching the wrong source tree, and once by writing a stage against behaviour nobody had exercised. The discipline that follows is a requirement, not a lesson.

- **FR-1124**: Every claim about runtime behaviour MUST be labelled as **verified** or **assumed**, and a verified claim MUST cite the version, the revision, and the inspected path.
- **FR-1125**: A claim MUST be verified against the tree the runtime actually loads, resolved before reading (R4-SC-402).
- **FR-1125a**: A public product claim MUST instead be verified against the exact locked public source/artifact and installed release candidate. Evidence from a private editable runtime cannot qualify a public release path.
- **FR-1126**: An assumed claim MUST NOT be relied upon by a requirement that would be unsafe if it were false.
- **FR-1127**: Executing the behaviour outranks reading the code, which outranks reading the documentation. Where they disagree, the more direct evidence wins and the disagreement is recorded.
- **FR-1128**: An upstream upgrade MUST be reviewed against recorded claims before an accepted decision is treated as still valid (R4-FR-424).

## 8. Controlled Evaluation

- **FR-1129**: A model, a prompt, or a limit MUST NOT be selected by preference. Selection requires a controlled comparison on the same work (R12).
- **FR-1130**: An evaluation MUST hold the contract constant and vary one thing. A comparison across different contracts measures the contracts.
- **FR-1131**: Cost MUST NOT substitute for demonstrated quality. A cheaper configuration is adopted only when its evidence is comparable on the same criteria.
- **FR-1132**: The constitution is scored identically regardless of which model produced the work (R3 inherited requirement).

## 9. Public Release Qualification

- **FR-1133**: Deterministic qualification MUST build the exact source commit into wheel and sdist, inspect contents/metadata/license, install the built wheel through `uv` in a disposable environment outside the source tree, and execute the public CLI from that installation.
- **FR-1134**: Runtime evidence MUST verify release-lock coordinates, digest, provenance, package identity/version, Python compatibility, isolated install, executable resolution, profile-policy integrity, and active-release coherence before any runtime executes.
- **FR-1135**: Lifecycle evidence MUST cover clean install, guided/declarative setup parity, greenfield and brownfield init, two-project isolation, service start/readiness/stop, interrupted update, rollback, external-upgrade mismatch, reconcile, safe uninstall, and destructive-purge denial/confirmation.
- **FR-1136**: Security evidence MUST cover secret/private-content scans of source and built artifacts, path traversal, symlink/hardlink escape, unsafe archive entries, permissions, atomic writes, service-target isolation, log redaction, and every R10 guard positive/negative control.
- **FR-1137**: The official matrix is Ubuntu 24.04 native, Ubuntu 24.04 under WSL2 with `systemd` and Linux-filesystem state, and continued Garuda/Arch validation. A result outside a declared lane is additional evidence, not proof of an untested platform.
- **FR-1138**: Live RC qualification MUST install the public PyPI RC, consume the exact locked public `upstream` or `transitional_fork` artifact, use a public Hermes-supported provider selected during setup, and execute a preregistered realistic Git project through Morfeo → Supervisor → Implementer → independent review → integration. Credentials, spend, and live execution require their explicit gates.
- **FR-1139**: Guard qualification under PD-66 MUST reproduce the two known false-positive classes: read-only validation misclassified as gateway lifecycle and an exact active Morfeo task-bound contract worktree denied merely for not being the main worktree. Positive authorized cases and all negative identity/path/tool controls are equally mandatory.
- **FR-1140**: Machine-readable evidence MUST bind package version, release-lock schema/version, source/fork tag and commit, artifact digests, Aether commit, platform, setup input hash, scenario, budgets, commands, exit status, and retained redacted logs. A heartbeat is never recorded as semantic completion.
- **FR-1141**: Stable `v1.0.0` is eligible only from the accepted RC commit after every non-waived criterion passes and the owner explicitly authorizes publication. A waiver names the failed criterion, evidence, impact, alternative, and owner decision; it never rewrites failure as success.

## 10. Evidence

Historical board behavior was verified by direct execution against the loaded `0.20.1` runtime. Public release-critical source behavior was inspected at selected commit `e624e9f…`:

- Completion summary and structured metadata are delivered verbatim to dependent units, with the age of each handoff shown.
- Attempt records exist per attempt, carrying outcome, profile, elapsed time, and reason — observed for a unit blocked twice.
- Every transition appends a durable event; a unit's history was read back in full after the fact.
- A board health snapshot reports active conditions per unit with severity.

The prior EC1 worker run is evidence for that private installation only. Clean-package, public update/rollback, native/WSL platform, and public-provider RC claims remain unverified until A1 executes FR-1133 through FR-1141 against the exact release candidate.

## 11. Requirements Inherited by Later Stages

| Requirement | Owner |
|---|---|
| Model selection requires controlled comparison on identical work | R12 |
| Cost never substitutes for demonstrated quality | R12 |
| The first authorized run is the evidence source for every assumed claim | R13 |
| Exact public-package and live-RC qualification gates release eligibility | R13 |
| Issues #192 and #195 remain visible until their acceptance evidence exists | R13 |

## 12. Success Criteria

- **SC-1101**: The owner accepts or rejects a body of work by running one documented command.
- **SC-1102**: Every completed unit answers the four questions.
- **SC-1103**: No evidence claims a verification that was not executed.
- **SC-1104**: Every out-of-scope defect and accepted risk reaches the owner as a question.
- **SC-1105**: Every pipeline repository change is attributable to a unit, profile, and attempt; every direct change is attributable to Morfeo's profile/session and actual evidence.
- **SC-1106**: Every claim about runtime behaviour in this repository is labelled verified or assumed.
- **SC-1107**: No configuration is adopted on preference alone.
- **SC-1108**: No direct action is forced into a fake card or quickstart, and no deferred functional validation is reported as passed.
- **SC-1109**: Built wheel/sdist install and run outside the source tree with contents, metadata, identity, and provenance verified.
- **SC-1110**: Update fault injection, rollback, mismatch reconciliation, and uninstall prove coherent-state recovery without damage to unrelated Hermes/user state.
- **SC-1111**: Native Linux and WSL2 lanes execute the documented public path and retain machine-readable evidence.
- **SC-1112**: Guard positives, negatives, both known false-positive regressions, and a complete no-recovery pipeline all pass.
- **SC-1113**: Reports distinguish liveness, semantic progress, termination, failure retries, resumptions, redispatches, review cycles, and lifecycle corrections.
- **SC-1114**: Stable publication occurs only from the accepted RC commit after explicit owner authority.

## 13. Done When

- [x] The running product is confirmed as the deliverable, with an executed validation path.
- [x] Per-unit evidence is defined by the four questions it must answer.
- [x] Evidence classes are ranked, with the constitution conflict highest.
- [x] The end-of-work report's contents and its source are specified.
- [x] Observability is inherited rather than built.
- [x] The verified-or-assumed discipline is made a requirement.
- [x] Controlled evaluation rules are set for R12.
- [x] Clean-package, runtime integrity, lifecycle, security, platform, public-provider, and publication evidence are defined.
- [x] Open issues #192/#195 and the liveness-versus-progress boundary remain release-visible.
- [x] Christopher has reviewed the stage (R4–R13 Decision Review, 2026-08-17).
