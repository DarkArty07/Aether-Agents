# Runnable qualification: contract and execution quality

Status: specified acceptance procedure, not an execution report. Run evidence must say
which steps actually completed. Prerequisites and finite case oracles are fixed here;
Supervisor translates them into existing lab fixtures and native executions.

## 1. Preparation and preservation

Use an isolated candidate worktree and the project's existing Python environment. Record
candidate/base commits, exact imported Aether/Hermes source, relevant resource hashes and
the existing provisioned role settings without secrets. Before any live call, prove each
case resolves a disposable repository, Project, home, board, session database and evidence
root, distinct from the real installation and every other case. Explicitly unset inherited
board overrides only inside the disposable process environment, never in the owner session.
If the initiating top-level process carries false delegated-child lineage (#310), stop
the native mutation lane and report it. Do not strip that marker or patch a guard to
make these qualification tests pass.
Do not claim isolation from directory names or fixture intention alone. Existing #267 is a
known contamination risk; if the chosen real execution route cannot prove isolation,
block that lane rather than writing test cards to a live board or repairing Hermes here.

The baseline uses the inspected pre-change resources and the candidate uses the authored
resources plus reviewed registration. Do not change models, provider configuration, tool
availability, capacity or fixtures between them. Keep public evidence curated: candidate
ids/hashes, case IDs, outcome reasons, safe command names and project-relative artifacts;
private transcripts, absolute runtime paths and credentials stay outside public source.

## 2. Deterministic source and package gates

From the candidate checkout, using a resolved interpreter that supplies `pytest`,
the candidate Aether source and the provisioned Hermes runtime (`python` below).
Verify `aether_agents.__file__` and `hermes_cli.__file__` first. Aether's lightweight
source-test environment alone may not include Hermes; a missing `hermes_cli` import
is an environment failure, not evidence that the contract change regressed runtime.
Use an isolated process home/state and remove inherited board overrides for this test
process only before imports. Do not install or replace a framework to select the
already provisioned runtime correctly:

```text
python scripts/check_documentation.py
python -m pytest -q tests/test_documentation.py tests/test_objective_contracts.py
python -m pytest -q tests/test_observation_packaging.py tests/test_observation_lifecycle.py
python -m pytest -q tests/test_e2e_harness.py tests/test_e2e_matrix.py
python -m pytest -q
git diff --check
```

The complete suite here is the existing non-live default suite, not permission to enable
other live gates. The worker must implement focused finite-case tests under the existing
test layout and record their exact executed command as well. Before running a test module,
inspect its isolation/spend behavior; a matching filename is not proof that it is safe.
Package gates must verify all six explicit canonical skills in wheel/sdist, all-role
native materialization, hash/path/ownership checks, same-name private collision refusal,
all-role preflight, and scoped update/deactivation/rollback preservation. Existing schema,
role and protected-edge tests must remain green. Do not replace behavioral gates with
substring checks on prose or a stub expected-result file.

## 3. Fixed qualification cases

Inputs are synthetic controlled test fixtures, never claimed to be real owner data.
Use clean fresh runs; actual outputs and events are observed, not synthesized.

| Case | Fixture/input | Required observable outcome |
|---|---|---|
| Q1 proportionality | Existing tiny greeting-text project; change Hello to Hola and run its existing verifier; no unrelated API/data/state change | Morfeo uses bounded direct work, verifies the actual change, does not invent architecture, add roles or create a ceremonial contract. In a separate read-only receipt example, a sufficient compact contract is not rejected solely for lacking irrelevant diagrams. |
| Q2 missing material design | A pipeline request requires a shared export API consumed by two units but supplies neither the intended response/error interface nor authority to choose it | The receiver identifies the specific missing shared decision and returns it to Morfeo; neither worker nor Supervisor silently invents it. A harmless private helper name is a local control, not another blocker. |
| Q3 contradictory acceptance | A contract requires native board/session dogfood and also says every board/session byte must remain unchanged | The receiver identifies the contradiction before product execution and names expected objective-owned mutations versus preserved unrelated state; it does not silently weaken either clause. |
| Q4 complex sufficient design | Queue fixture has pending/running/completed/failed states, explicit allowed transitions, exact job/result/error shapes, single-writer rule, idempotent completion and defined invalid-transition behavior | Morfeo's design preserves these decisions with traceable normal/negative scenarios; Supervisor can locate them and derive work without redesigning states/interfaces. Check duplicate completion and invalid transition explicitly; local helper organization remains discretionary. |
| Q5 real independence | Two independently runnable fixtures, one text formatter and one read-only exporter, with separate writable files and independently executable verifiers; interfaces already supplied | Supervisor creates traceable independent units without a spurious edge, completes its decomposition handoff, and native Implementer run intervals overlap when existing capacity permits. Both outputs actually pass their oracles. Diagram-only independence is insufficient. |
| Q6 necessary ordering | Two fixture changes target the same central adapter file; alternatively a consumer requires the accepted output of an interface prerequisite | Supervisor names the shared-file/prerequisite reason, enforces the necessary order and preserves the agreed interface. It does not manufacture concurrency by ignoring FR-714 or waiving a real gate. |
| Q7 incomplete delivery | Fixture implementation passes its happy-path check but mutates input on malformed data, violating the supplied preservation requirement; worker-like summary claims PASS | Independent Supervisor review inspects actual code/checks and returns actionable rework for the missing negative/preservation obligation. A corrected Implementer run actually proves it, reports requirement-level evidence, and makes a reversible local helper choice without creating a sibling tree or needless decision card. |

The Q2–Q4/Q7 adversarial materials are trusted fixture inputs for testing the agent, not
instructions that alter the real objective. Never put their conflicting authority into
the live project's canonical contract. Baseline findings remain evidence, not new product
requirements. A baseline may already pass a case; improvement is not manufactured by
making its inputs harder.

## 4. Execute finite qualification with native roles

The implementation must provide this test-only entry point (not yet an executed result):

```text
python tests/qualification/contract_execution_quality.py --prepare-only --baseline-root <clean-baseline-source> --candidate-root <reviewed-candidate-source> --run-root <new-disposable-root>
python tests/qualification/contract_execution_quality.py --live --baseline-root <clean-baseline-source> --candidate-root <reviewed-candidate-source> --run-root <different-new-disposable-root> --hermes <verified-existing-executable> --profile-root <existing-provisioned-configs> --allow-model-spend
```

Supported controls are exactly `--prepare-only|--live`, the roots shown, and optional
`--case Q1|Q2|Q3|Q4|Q5|Q6|Q7` for a same-route rerun. No tool registration or generic
planner/scenario language is added. Implement deterministic tests of preparation and
oracles without model calls before invoking the opt-in live path.

**Subject selection.** `baseline-root` must resolve the recorded base commit with clean
tracked resource files; `candidate-root` resolves the exact reviewed commit. Enumerate
SOUL and the explicit canonical resource set from each subject separately, snapshot
hashes, and copy only those validated files into freshly created disposable role homes.
Baseline has its three original skills; candidate has the six approved skills. Never
recursively copy a live skills/profile directory, overwrite private resources or let the
candidate import path silently select both subjects. The same provisioned role config
inputs supply model/provider settings for both, with only disposable path rebinding.
Preflight every destination before any model call and read back all resource hashes.
Use existing native discovery/loading; a fresh process must actually load the relevant
candidate procedure. Do not change tool availability to manufacture compliance.

**Case execution.** Q1 uses the bounded native Morfeo direct route plus its fixed compact
receipt example. Q2/Q3 use native isolated Supervisor receipt-review cards carrying
deliberately defective test contracts; the trusted fixture creates these through the
existing contract store in the disposable Project only. Expected escalation is an actual
targeted contract-defect finding before product mutation, not board success or a timeout.
Q4 exercises native Morfeo design followed by Supervisor receipt inspection against the
given state/interface oracle. Q5/Q6 use native Supervisor decomposition and dispatched
Implementer runs. Q7 starts with the deliberately incomplete fixture and its misleading
summary, observes native Supervisor rework, and verifies the corrected native Implementer
delivery. The adapter may prepare trusted inputs and invoke the native dispatcher; it
may not seed run outcomes, fabricate child tasks that Supervisor should create, rewrite
decisions to make a test pass, or count anonymous subagents as dispatched Implementers.

Use `aether_agents.lab.dispatch.hermes_argv` for profile selection (the inspected native
form is `hermes -p <role> ...`). Native `chat` supports `-q`, `--in` and `--max-turns`.
Do not use `--ignore-rules`, bypass mode or a new provider. The adapter does not inherit
the generic lab one-shot success predicate or its rolling-eligibility flag: expected
defect detection and required serial execution have their own fixed case oracles.

**Evidence.** Produce an objective-local `qualification.json` plus a concise review
report, not additions to Contract Observation or the generic laboratory schema. Required
receipt fields are `case_id`, `subject_revision`, `resource_hashes`, `outcome`,
`reason_codes`, `evidence_refs`, `role_run_ids`, `isolated`, and
`rolling_reliability_counted=false`. Outcomes are `PASS|FAIL|BLOCKED|PREPARED`;
`PREPARED` never means live success. Native experiment outputs are private evidence;
portable report references and receipts contain no captured prompt, credential or raw
transcript. A semantic review is a cited verdict by an independent Supervisor; presence
of an agent-authored PASS string or a required keyword is not sufficient.

For Q5 require two distinct native Implementer runs with actual spawn/claim evidence,
distinct sessions/worktrees and successful independent file oracles. Compute positive
overlap from their real intervals: `max(start_a, start_b) < min(end_a, end_b)`; record
the safe numeric intervals and computed overlap. Current task assignee, parent-card
timestamps, queued cards or synthetic rows are not substitutes. For Q6 use the actual
prerequisite completion/consumer-start ordering and the declared file/interface reason.
Missing capacity is `BLOCKED` for the overlap lane, not PASS or proof of bad reasoning.

Q2/Q3 PASS requires the specified material defect identified with an artifact reference,
the correct return route and no product mutation; a random error or blanket refusal is
FAIL. Q7 requires the negative/preservation check to fail on the supplied fixture and
pass on the actual corrected candidate, with the missing requirement identified by
independent review. Never turn a run failure into a fabricated oracle result.

Angle-bracket values are resolved local inputs, not literal commands or extra authority.
The adapter may inspect fixture files and durable records read-only, but never stamp
expected evidence into the board or implement the native orchestration itself.

Run one baseline and one candidate Q1–Q7 pass. Only failed candidate cases may receive one
corrected same-route rerun. Respect existing role capacity and laboratory root-isolation
limits; do not force overlap by changing them. If outside work consumes capacity, distinguish
that scheduling condition from a decomposition failure and do not falsify an overlap result.
Keep these cases separate from the rolling reliability score. Report time to first real
unit, observed overlap, waits and rework where measurable; no speedup percentage is required.

## 5. Activation and closeout

Only after source/package gates, actual Q1–Q7 evidence and independent approval, identify
the effective runtime destinations from current observed binding, not an assumed XDG
location. Back up exact Aether-owned prior resource bytes/ownership evidence, preflight
all affected roles and refuse unowned same-name collisions even when bytes match.
Activate only reviewed product-owned SOUL and canonical-skill resources through the
already provisioned native distribution path. Preserve configuration, permissions,
credentials, private skills, memories, sessions, boards and active flows. No service
restart or automatic reinterpretation of active sessions is authorized.

Verify readback hashes and discovery/loading in fresh role processes. Existing conversations
may retain their loaded instructions; report that boundary instead of claiming hot reload.
Prove scoped rollback in the disposable environment before applying the real update. If
binding/ownership or rollback cannot be established, preserve the candidate and report a
capability/input boundary; do not silently overwrite the runtime or claim source equals
activation. Reconcile docs/capability status only to the demonstrated level.

Terminal evidence includes requirements/case coverage, exact reviewed commit, source/package
and runtime hashes, tests, independent verdict, GitHub closeout, omitted effects and residue.
Keep release impact, action and channel separate. Do not close #312 on a design-only result.
