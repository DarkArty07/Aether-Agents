# v0.23.x Aether MCP Cold-Start Design Handoff

> **Status:** DESIGN AND PLAN COMPLETE — IMPLEMENTATION NOT AUTHORIZED
> **Recorded:** 2026-08-11 UTC
> **Project:** Aether Agents
> **Branch:** `v0.23.0-orca-production-cutover`
> **Required worktree:** `/home/darkarty/Desktop/agentes/aether/.aether/worktrees/v0.23.0-orca-production-cutover`
> **Next gate:** explicit P0 implementation authorization

## 1. Resume objective

Make Hermes use Aether MCP correctly from a cold session without depending on
history, memory, project-local rules, or the agent choosing to load an optional
skill.

The product owner approved the design direction that each kind of guidance lives
in its proper guaranteed surface. This session was documentation-only and leaves
implementation, prompt experimentation, installation and runtime effects gated.

## 2. Canonical artifacts

Read in this order:

1. `MCP_COLD_START_GUIDANCE_DESIGN.md` — approved architecture and normative
   contracts;
2. `MCP_COLD_START_IMPLEMENTATION_PLAN.md` — gated TDD and evaluation sequence;
3. `MCP_TOOL_SURFACE_LEARNING_PLAN.md` — parent O0–O8 optimization program;
4. `M1_3_TOOL_QUALIFICATION_CHECKPOINT.md` — observed baseline and limitations;
5. `ROADMAP.md` and `STATUS.yaml` — active release state;
6. `prompt/PROMPT_3_0_0_RESULT.md` — prior rejected prompt experiment that must
   remain immutable;
7. `../../decisions/PDR-0014-versioned-orca-production-adoption.md` — authority
   and version boundary.

## 3. Frozen design decisions

- Skills are not an acceptance dependency because loading is agent-selected.
- Aether-specific mandatory guidance belongs in the Aether `SOUL.md` candidate,
  which Hermes injects into the stable system-prompt tier.
- Hermes Agent core system-prompt code is not modified for Aether-specific policy.
- MCP server-level `instructions` are not an accepted teaching surface because
  Hermes 0.19.1 does not expose them to the model.
- Exactly 15 tools remain callable and distinct.
- `SOUL.md` teaches the state machine and authority invariants, not all schemas.
- Tool first sentences support Tool Search discovery.
- Full descriptions teach when/requires/effect/returns/next/do-not-use/recovery.
- JSON Schema descriptions teach identifier and control-field provenance.
- Typed result/error guidance provides only mechanically justified next actions.
- The server never chooses product meaning, participants, protected authority,
  provider/account/model/spend, or cross-project effects.
- Unknown mutation effects reconcile before retry.
- `swarm_start` creates Run/Tasks without dispatching a worker.
- `swarm_dispatch` may start fixture/model workers and must expose provider/model
  implications.
- `swarm_message` requires coordinator or participants admitted by successful
  Dispatches.
- `swarm_reconcile` currently supports prior uncertain `swarm_start` operations,
  not generic Task/Dispatch reconciliation.
- `orca_call` validates/plans read-only argv and does not execute it.
- v0.24.0 remains inactive.

## 4. Prompt state

Active Hermes Prompt remains 2.0.0. The prior Prompt 3.0.0 candidate was not
promoted after three experiment rounds and is immutable evidence.

The future cold-start prompt candidate identifier is:

```text
3.0.0-coldstart.1
```

It must:

- derive from the byte-exact active 2.0.0 baseline;
- make the smallest v0.23.x routing/cold-start correction;
- remain in an isolated file/HERMES_HOME during evaluation;
- never overwrite active `home/SOUL.md` before a frozen A/B pass and explicit
  product-owner promotion decision;
- not import the whole rejected 3.0.0 candidate silently.

## 5. MCP contract state

Current protocol identity:

```text
aether.mcp/v1alpha2
```

Current callable catalog:

```text
project_admit
project_inspect
swarm_validate
swarm_start
swarm_status
swarm_dispatch
swarm_message
swarm_reconcile
swarm_retry
swarm_cancel
swarm_close
swarm_trace
orca_search
orca_describe
orca_call
```

Current descriptions remain generic in source. The design keeps the protocol
identity by default, adds non-validating schema descriptions, and defines an
additive response extension:

```text
aether.guidance/v1alpha1
```

Known-consumer tolerance for the additive field must be proven. If an admitted
consumer requires a closed response shape, stop for a protocol-version decision;
do not silently bump to v1alpha3.

Adding schema descriptions will change deterministic v1alpha2 bundle bytes and
digest. Preserve the pre-change wheel/bundle/digest and verify exact
source-wheel-installed-session convergence.

## 6. Error-contract finding

The public protocol contains 50 stable error codes. A static source audit found
27 additional literal emitted codes that are not public and may collapse to
`INTERNAL_ERROR`:

```text
ERR_CAPABILITY_UNQUALIFIED
ERR_COORDINATOR_BINDING_REQUIRED
ERR_COORDINATOR_BINDING_STALE
ERR_COORDINATOR_BINDING_UNQUALIFIED
ERR_COORDINATOR_PRINCIPAL_MISMATCH
ERR_COORDINATOR_SCOPE_MISMATCH
ERR_INVALID_ARGUMENT
ERR_JOURNAL_RECORD
ERR_JOURNAL_SCOPE
ERR_JOURNAL_TAMPERED
ERR_OPERATION_CONFLICT
ERR_OPERATION_NOT_FOUND
ERR_OPERATION_REQUIRED
ERR_PROVIDER_BUILD_MISMATCH
ERR_PROVIDER_RECEIPT_SCOPE
ERR_PROVIDER_RECEIPT_SHAPE
ERR_RECONCILIATION_SCOPE
ERR_RECONCILIATION_SHAPE
EVIDENCE_REQUIRED
MESSAGE_CORRELATION_INVALID
PROVIDER_EFFECT_FAILED
RETRY_BUDGET_EXHAUSTED
RETRY_FORBIDDEN
RUN_NOT_CLOSED
STALE_ATTEMPT
TRACE_SCHEMA_UNSUPPORTED
WRITE_SCOPE_VIOLATION
```

Before guidance implementation, classify each as:

- map to existing public code;
- admit a new public code with tests/reference; or
- intentionally collapse to `INTERNAL_ERROR` with `STOP`, no fabricated next
  tool and no unsafe retry.

Do not expose raw exception/provider text.

## 7. Cold-session acceptance essentials

A valid cold repetition has:

- fresh process/session and empty conversation;
- frozen baseline or candidate SOUL loaded before session creation;
- no Aether workflow memory or project-specific MCP instructions;
- zero Aether skill calls;
- normal Tool Search and exact 15-tool catalog;
- frozen model/provider/account/tool/prompt/schema identity;
- isolated state and no model/spend unless separately authorized.

Hard thresholds are 100% per authorized repetition for:

- route and authority invariants;
- identifier provenance;
- no hidden/legacy fallback;
- no unauthorized worker/model effects;
- reconcile-before-retry;
- zero skill dependency;
- zero attempt-owned survivors after started Runs.

Average efficiency cannot compensate for one hard failure.

## 8. Exact next action

### NOW

Obtain an explicit P0 implementation authorization covering the bounded source,
test, schema, prompt-candidate and isolated-test paths. Confirm active SOUL,
active MCP registration/runtime and model/provider execution remain untouched.

### AFTER P0

1. preregister and freeze repeated cold-session cases/evaluator/thresholds;
2. run and preserve the active 2.0.0 + generic-description baseline;
3. add RED tests for catalog descriptions, property provenance and guidance;
4. implement the smallest 15-tool compatible candidate;
5. build an isolated `3.0.0-coldstart.1` prompt candidate;
6. qualify package/handshake/Tool Search in isolated no-model state;
7. run the frozen repeated A/B;
8. request separate model-backed and promotion/activation decisions.

### STOP CONDITION

Stop after documentation until P0 is explicit. A green design is not source,
prompt, installation, model, integration or release authority.

## 9. Paths expected in future implementation

Existing files likely modified after authorization:

```text
src/aether_mcp/server.py
src/aether_mcp/protocol.py
src/aether_mcp/runtime.py
tests/aether_mcp/test_operational_server.py
tests/aether_mcp/test_protocol.py
schemas/aether-mcp/v1alpha2/bundle.json
docs/reference/AETHER_MCP_CONTRACT.md
```

Expected new candidate files:

```text
src/aether_mcp/guidance.py
tests/aether_mcp/test_guidance.py
docs/releases/v0.23.0/prompt/coldstart/MCP_COLD_START_EXPERIMENT.yaml
docs/releases/v0.23.0/prompt/coldstart/cases.json
docs/releases/v0.23.0/prompt/coldstart/HERMES_CANDIDATE_3_0_0_COLDSTART_1.md
docs/releases/v0.23.0/prompt/coldstart/MCP_COLD_START_RESULT.md
```

These are planned paths, not files created by the design session.

## 10. Resume checks

Run before relying on this handoff:

```bash
cd /home/darkarty/Desktop/agentes/aether/.aether/worktrees/v0.23.0-orca-production-cutover
git status --short
git branch --show-current
git log -5 --oneline
sha256sum home/SOUL.md
```

Then verify the active runtime independently before any operational claim. Do not
infer active SOUL/package/catalog identity solely from repository files or a prior
session.

## 11. Effects not performed by this design session

- no Python/source/test/schema behavior change;
- no `home/SOUL.md` change;
- no Hermes Agent core change;
- no config/profile/registration change;
- no package build/install;
- no MCP restart or prompt-cache invalidation;
- no Run, Task, Dispatch, worker or model call;
- no credentials, account or spending effect;
- no push, merge, tag, Release, deployment or v0.24.0 activation.
