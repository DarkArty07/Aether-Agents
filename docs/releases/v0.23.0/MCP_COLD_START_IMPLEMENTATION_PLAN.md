# v0.23.x Aether MCP Cold-Start Implementation Plan

> **Status:** READY FOR AUTHORIZATION — NO IMPLEMENTATION OR ACTIVATION AUTHORIZED
> **Recorded:** 2026-08-11 UTC
> **Design authority:** `MCP_COLD_START_GUIDANCE_DESIGN.md`
> **Parent program:** `MCP_TOOL_SURFACE_LEARNING_PLAN.md`
> **Resume record:** `MCP_COLD_START_HANDOFF.md`
> **Target branch:** `v0.23.0-orca-production-cutover`
> **Required worktree:** `/home/darkarty/Desktop/agentes/aether/.aether/worktrees/v0.23.0-orca-production-cutover`

## 1. Purpose

Implement and prove the approved cold-start guidance architecture without
conflating documentation, prompt experimentation, MCP protocol changes,
installation, model use, promotion, integration or release.

This is an implementation plan, not implementation authority. The session that
created it changed documentation only.

## 2. Outcome contract

A successful implementation candidate provides:

1. an isolated Hermes Prompt `3.0.0-coldstart.1` candidate carrying the mandatory
   Aether MCP boot contract;
2. intent-oriented descriptions for exactly the current 15 tools;
3. property descriptions that identify exact input provenance;
4. typed, secret-safe result/error guidance that cannot grant authority;
5. frozen cold-session baseline and candidate evaluation under equivalent initial
   conditions;
6. source, wheel, installed MCP, Tool Search and prompt identity convergence;
7. no dependence on an Aether skill;
8. no hidden fallback, unauthorized worker/model effect or cleanup survivor;
9. an explicit product-owner disposition before prompt promotion or active
   runtime installation.

## 3. Non-goals

Do not during this plan:

- remove, hide, rename, combine or deprecate any current tool;
- redesign the Orca lifecycle or create another coordinator/store;
- use the rejected Prompt 3.0.0 candidate as the active prompt;
- modify Hermes Agent core unless a separately documented framework defect makes
  the approved design impossible;
- activate v0.24.0;
- spend, select credentials, alter account policy, or execute a model-backed
  worker without a separate gate;
- push, merge, tag, publish or activate merely because local tests pass.

## 4. Roles and write ownership

One accountable implementation owner should make the tightly coupled source and
test changes. Do not split `protocol.py`, `guidance.py`, `runtime.py` and their
contract tests among parallel writers.

| Deliverable | Accountable owner | Forbidden overlap |
|---|---|---|
| Frozen design/plan/cases/evaluator | Hermes | Candidate implementation may not rewrite after freeze |
| MCP source and tests | One implementation owner | No second source writer/worktree |
| Prompt candidate text | Hermes/product prompt owner | MCP implementation may not promote active SOUL |
| Independent evaluation | Frozen evaluator/harness | Candidate cannot change expected outcomes or thresholds |
| Product disposition | Christopher | Implementer cannot self-accept or activate |

The existing Aether MCP + Orca path remains the subject under test. Do not invoke
Olympus, ACP, Harmonia, `talk_to`, aliases or another coordinator as fallback.

## 5. Gate sequence

```text
P0 owner implementation authorization
  -> P1 preregister cold benchmark and freeze artifacts
  -> P2 preserve baseline evidence
  -> P3 MCP metadata/result candidate through RED/GREEN
  -> P4 isolated prompt candidate through RED/GREEN
  -> P5 deterministic fixture and package/runtime convergence
  -> P6 repeated cold-session A/B
  -> P7 bounded model-backed case under separate authority
  -> P8 independent acceptance and owner disposition
  -> P9 separately authorized installation/promotion/integration/release
```

A later gate never becomes authorized automatically.

## 6. P0 — Obtain exact implementation authority

### Required owner decision

Record one explicit decision authorizing the compatible candidate implementation
and identifying:

- approved branch/worktree;
- allowed source, test, schema, prompt-candidate and documentation paths;
- whether local commits are expected;
- confirmation that active `home/SOUL.md`, active MCP registration and runtime
  processes remain unchanged;
- whether a new isolated Hermes home/process may be created for tests;
- confirmation that model/provider execution remains separately gated.

### Stop condition

Without this decision, perform no step after P0.

## 7. P1 — Preregister the cold-session evaluation

Create new immutable experiment artifacts under:

```text
docs/releases/v0.23.0/prompt/coldstart/
  MCP_COLD_START_EXPERIMENT.yaml
  cases.json
  evaluator.py or evaluator contract document
  README.md
```

Exact naming may follow repository convention, but the old Prompt 3.0.0
experiment files must remain byte-for-byte unchanged.

### Freeze before candidate edits

The experiment must record:

- baseline prompt version/path/SHA-256;
- candidate identifier `3.0.0-coldstart.1` and initially absent digest;
- Aether product commit and dirty-state requirement;
- Hermes Agent version and source commit if available;
- Aether MCP package version, wheel digest, catalog names/descriptions and schema
  bundle digest;
- model, provider/account class, API mode and fixed generation settings;
- Tool Search configuration and listing tier;
- cold-session definition;
- fixture state reset procedure;
- exact case prompts and expected semantic outcomes;
- repetition count per case;
- order/randomization policy;
- timeouts and maximum tool/model calls;
- token, latency and cost collection method;
- cleanup and survivor checks;
- evaluator identity and digest;
- acceptance thresholds and no-regression cases;
- rollback disposition.

### Evaluation semantics

Avoid the rejected experiment's exact-serialization failure. Score separately:

1. semantic route/outcome;
2. hard safety/authority invariants;
3. tool sequence and identity provenance;
4. machine-readable output validity;
5. efficiency metrics.

Policy denials must define whether verification is already satisfied, whether the
case may close, and whether `must_verify` is an observed fact or future
obligation.

### RED proof

Before candidate edits, run the frozen cases against active Prompt 2.0.0 plus the
current generic tool descriptions. Preserve the baseline distribution. Do not
infer candidate thresholds from one run.

### Gate

The product owner or previously authorized evaluator contract accepts the frozen
experiment. Candidate code cannot modify these artifacts afterward.

## 8. P2 — Preserve exact baseline and rollback

Before source changes, record:

```text
git rev-parse HEAD
git status --short
sha256sum home/SOUL.md
sha256sum schemas/aether-mcp/v1alpha2/bundle.json
```

Build or identify the current rollback wheel without installing it. Preserve:

- source commit;
- wheel path and SHA-256;
- schema bundle SHA-256;
- 15 tool names and current generic descriptions;
- active MCP registration backup and file mode if runtime testing is later
  authorized;
- active SOUL SHA-256;
- active Hermes process/session identity;
- attempt-owned cleanup baseline.

Do not inspect or copy secrets into evidence. Use `[REDACTED]` for any accidental
credential-bearing value and remove the raw artifact from versioned scope.

### Gate

A deterministic rollback artifact exists and the worktree remains attributable.

## 9. P3 — Implement MCP guidance through TDD

### 9.1 RED: catalog descriptions

Modify `tests/aether_mcp/test_operational_server.py` first to require:

- exact 15-tool set, no additions/removals;
- no description matching the generic baseline;
- first-sentence intent semantics from the approved design;
- first-sentence and full-description length ceilings;
- explicit worker/model warning on `swarm_dispatch`;
- explicit no-worker statement on `swarm_start`;
- explicit plan-only statement on `orca_call`;
- explicit start-only restriction on `swarm_reconcile`;
- no secret-like values or prompt-injection patterns;
- descriptions survive a real MCP `tools/list` readback.

Run the focused test and preserve the expected failure.

### 9.2 RED: property provenance

Modify `tests/aether_mcp/test_protocol.py` first to require JSON Schema
`description` annotations for:

- common operation metadata;
- all logical identity fields;
- cursor, catalog and schema digests;
- sender/recipient participant semantics;
- reconcile/cancel target identity semantics;
- JSON-encoded message payload.

Require descriptions to remain bounded and require the strict input validation
shape to remain unchanged except for non-validating annotations. Preserve the RED
result.

### 9.3 RED: response guidance

Add focused tests, preferably in a new file:

```text
tests/aether_mcp/test_guidance.py
```

Test:

- exact `aether.guidance/v1alpha1` schema;
- all enum values and invalid combinations;
- no mutating recommendation when `decision_required=true`;
- unknown effect always reconciles or stops and is never directly retried;
- deterministic `DELIVERY_UNKNOWN`/`RECONCILIATION_REQUIRED` guidance;
- protected dispatch authority yields null `next_tool` until authority exists;
- successful dispatch/cancel can suggest status without executing it;
- `orca_search -> orca_describe -> orca_call` remains read-only planning;
- every known public error has one explicit disposition;
- every non-public internal literal error has an explicit mapping/admit/collapse
  disposition;
- raw exception/provider text cannot enter guidance;
- existing envelope consumers tolerate the additive `guidance` field.

Preserve the RED result.

### 9.4 GREEN: central guidance ownership

Recommended source ownership:

```text
src/aether_mcp/guidance.py       # new: immutable tool metadata and deterministic guidance policy
src/aether_mcp/protocol.py       # schema annotations, guidance validation/envelope field
src/aether_mcp/runtime.py        # attach guidance from public code + trusted state
src/aether_mcp/server.py         # register exact versioned descriptions
```

Constraints:

- `guidance.py` may import stable protocol constants; `protocol.py` must not
  import runtime/provider behavior and create a cycle;
- only one canonical mapping owns each tool description;
- server registration must not duplicate independent prose;
- guidance is calculated after validation from public code and trusted state;
- no guidance function may execute a tool;
- no guidance function may grant authority or synthesize IDs;
- current tool names and required request fields remain unchanged;
- string payload preservation regression remains green.

Implement only enough to pass the frozen tests.

### 9.5 Error taxonomy correction

Classify every emitted code identified by the design audit. Add an explicit test
that recomputes the audit and fails on an unclassified literal.

For each code choose one and document it:

- map to existing stable public code;
- add a new public code with contract/reference tests;
- intentionally collapse to `INTERNAL_ERROR` with `STOP`, null `next_tool`,
  `safe_to_retry=false`, and diagnostic trace reference where safe.

Do not expose internal exception messages merely to make an error “actionable.”

### 9.6 Schema snapshot and compatibility

Regenerate `schemas/aether-mcp/v1alpha2/bundle.json` deterministically after the
new annotation tests pass. Preserve the historical v1alpha1 snapshot unchanged.
Record old/new v1alpha2 digest.

Prove known consumers accept the additive envelope field. If a consumer enforces
a closed response shape, stop and create a product/protocol decision; do not bump
to v1alpha3 silently.

### Focused verification

```bash
.venv/bin/python -m pytest -p no:cacheprovider \
  tests/aether_mcp/test_operational_server.py \
  tests/aether_mcp/test_protocol.py \
  tests/aether_mcp/test_guidance.py -q
```

### Gate

Focused tests pass, the exact 15 tools remain, request validation is not weakened,
and compatibility is proven or honestly blocked.

## 10. P4 — Build the isolated prompt candidate

### 10.1 Candidate construction

Create a new immutable candidate file, for example:

```text
docs/releases/v0.23.0/prompt/coldstart/HERMES_CANDIDATE_3_0_0_COLDSTART_1.md
```

Start from the byte-exact active Prompt 2.0.0 baseline. Apply only the minimum
changes needed to:

- replace the obsolete v0.22 execution boundary;
- add the approved cold-start boot contract;
- preserve direct single-owner execution;
- preserve protected-effect and user-authority gates;
- prohibit legacy fallback;
- avoid broader personality or policy rewrites from the rejected 3.0.0 candidate.

Record the final SHA-256 into the already frozen experiment manifest without
changing cases, expected outcomes, evaluator or thresholds. If the manifest
requires the candidate digest before freeze, use a two-stage freeze with an
immutable baseline/case/evaluator digest and a separately signed candidate
identity record.

### 10.2 Candidate loading

Do not copy the candidate into active
`/home/darkarty/Desktop/agentes/aether/home/SOUL.md`.

Run it only from an isolated test HERMES_HOME or an equivalent harness that:

- contains no production credentials;
- uses an isolated MCP state root;
- cannot overwrite active profile/config/memory;
- records which SOUL digest the fresh agent loaded;
- starts a new process/session for every repetition.

### RED/GREEN claim

The active 2.0.0 baseline should fail at least the obsolete-boundary/cold-routing
cases preserved by the baseline. The candidate must pass because of the changed
prompt plus MCP metadata under equivalent conditions, not because the candidate
receives extra case-specific context.

### Gate

The prompt candidate remains isolated, has a deterministic digest, and passes all
o-tool policy cases before any real MCP effects are allowed.

## 11. P5 — Deterministic package and fixture qualification

### 11.1 Full source verification

Run from the exact worktree:

```bash
.venv/bin/python -m pytest -p no:cacheprovider tests/aether_mcp -q
.venv/bin/ruff check src/aether_mcp tests/aether_mcp
.venv/bin/python -m compileall -q src/aether_mcp tests/aether_mcp
git diff --check
.venv/bin/python scripts/check_release_governance.py policy
```

Run the repository-wide suite when shared protocol behavior changes or repository
policy requires it.

### 11.2 Wheel and isolated install

Build a wheel from the exact committed candidate. Install only into an authorized
isolated environment. Verify:

- wheel import and version;
- exact source/wheel bundle digest;
- exactly 15 tools from a fresh MCP process;
- exact first sentences and loaded schemas;
- string JSON payloads remain strings;
- no Run/Task/worker is created by registration or discovery;
- Tool Search can discover each tool by user intent;
- `tool_describe` returns the intended full contract;
- response guidance survives MCP serialization.

A successful setup command or `hermes mcp test` exit code is insufficient by
itself. Capture real handshake/catalog readback from a new process.

### 11.3 Deterministic lifecycle cases

Use isolated fixture state for read-only and no-model cases. Exercise admission,
inspection, validation, start-without-dispatch, status, supported reconciliation,
cancel, close and trace. Do not claim dispatch/message/retry qualification if the
fixture binding does not provide a durable successful Dispatch.

### Gate

The candidate is deterministic, package/runtime identities converge, no model was
called, and every created fixture Run closes with zero survivors.

## 12. P6 — Repeated cold-session A/B

Run the frozen baseline and candidate from independent cold sessions under the
same:

- provider/model/account class;
- case prompts and order policy;
- Tool Search configuration;
- MCP catalog and fixture state;
- evaluator;
- timeout and call budget;
- memory/project-context absence;
- usage collection.

Record every tool search, describe and call. A case fails skill independence if it
calls `skill_view` for an Aether workflow even if the final outcome is correct.

### Required report

Create:

```text
docs/releases/v0.23.0/prompt/coldstart/MCP_COLD_START_RESULT.md
```

Report:

- per-case/per-repetition semantic and hard-invariant outcomes;
- first-tool selection and full sequence;
- identity provenance violations;
- invalid/precondition calls;
- skill calls;
- tokens, latency, calls and reported monetary cost (`UNKNOWN` when unavailable);
- cleanup and survivor evidence;
- baseline/candidate deltas;
- regressions and user corrections;
- exact artifact digests.

Do not rescore a frozen run after observing a benchmark defect. Preserve it,
classify the evaluator/case defect, freeze a new version prospectively, and count
correction rounds. Stop after the third failed approach.

### Gate

Every hard threshold passes in every repetition. Improvement in average calls or
tokens cannot compensate for one authority, identity, fallback or cleanup
failure.

## 13. P7 — Separately authorized model-backed case

This gate is not authorized by documentation or by P0 unless the owner explicitly
includes:

- exact Orca build;
- provider/account class;
- model and CLI identity;
- credential source without disclosure;
- PAYG policy and cost ceiling;
- one worker/Dispatch limit;
- retry policy;
- timeout;
- artifact acceptance;
- cancellation, close and survivor checks.

Use the same cold-start prompt/metadata candidate. Prove the real path:

```text
cold session
-> discover/admit/validate
-> start without automatic worker
-> dispatch one admitted Task
-> status/message
-> retry only if pre-registered and evidenced
-> verify artifact
-> cancel or semantic close
-> close and zero survivors
-> trace review
```

A fixture cannot substitute for this evidence. A model-backed pass cannot repair
a failed deterministic safety case.

## 14. P8 — Independent acceptance and product disposition

Required review questions:

- Did the candidate pass without skills?
- Did the prompt and descriptions each contribute their intended layer rather
  than duplicate a manual?
- Are descriptions discoverable under actual Tool Search budget behavior?
- Did field descriptions eliminate identity-class confusion?
- Are result/error recommendations deterministic and authority-neutral?
- Were all internal/public errors classified honestly?
- Did any hidden provider/model/cost effect occur?
- Are source, wheel, installed process, catalog, schema and prompt identities
  exact?
- Did every Run close with zero attempt-owned survivors?
- Is direct single-owner behavior no worse than baseline?

The product owner selects separately:

### MCP metadata disposition

- `ACCEPT_15_TOOL_COLD_START_METADATA`;
- `CORRECT_AND_RERUN`;
- `INSUFFICIENT_CONTINUE_V0_23`;
- `REJECT_AND_ROLL_BACK`.

### Prompt disposition

- `PROMOTE_EXACT_CANDIDATE_AS_HERMES_PROMPT_3_0_0`;
- `CORRECT_AND_RERUN`;
- `KEEP_ACTIVE_2_0_0`;
- `REJECT_CANDIDATE`.

Accepting one does not automatically accept the other.

## 15. P9 — Later installation, promotion and release gates

Only after P8 and explicit authority:

1. back up active MCP registration/config and active SOUL with hashes/modes;
2. install the exact accepted wheel into the named Aether runtime;
3. copy/promote only the exact accepted SOUL candidate;
4. start a fresh Hermes/MCP process so cached prompt/catalog state cannot survive;
5. read back prompt digest, package identity, 15 tools, descriptions and schema;
6. run the frozen smoke/cold case;
7. roll back immediately on identity drift or hard-invariant failure;
8. record installed activation separately from source integration/release;
9. commit/push/PR/merge/tag/Release only under their own repository gates.

Do not call an on-disk edit active until a fresh session proves the loaded digest.

## 16. Rollback plan

Rollback restores both independent surfaces:

### MCP

- reinstall the preserved baseline wheel;
- restore exact registration/config backup and mode;
- terminate only attempt-owned candidate MCP processes;
- start a fresh baseline process;
- verify baseline package, schema digest and 15-tool catalog;
- preserve incident evidence.

### Prompt

- restore active Prompt 2.0.0 byte-for-byte;
- verify SHA-256 against the frozen baseline;
- start a fresh Hermes session;
- verify no candidate prompt cache remains.

Rollback does not restore Olympus/ACP/Harmonia or permit silent fallback.

## 17. Completion and stop condition

Implementation is complete only when:

- all authorized gates through the selected horizon have passed;
- the exact candidate and evaluation evidence are committed;
- active/runtime effects match explicit authority;
- every started Run is closed with zero survivors;
- remaining model, prompt promotion, integration, release and v0.24 actions are
  reported as later gates.

Stop after the accepted current horizon. Do not proceed automatically from a
green local candidate to installation, prompt promotion, model execution,
integration, release or v0.24.0.
