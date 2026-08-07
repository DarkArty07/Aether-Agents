# TASK-M1.2 — Freeze the Structured Orca Provider Seam Matrix

> **Status:** ACTIVE FAST-TRACK TASK
> **Task owner:** Hermes
> **Implementation owner:** One repository-local external coding agent
> **Acceptance owner:** Hermes after independent catalog reproduction

```text
PROJECT_ROOT: /home/darkarty/Desktop/agentes/aether/.aether/worktrees/feature-v0.22.0-orca-transition
BRANCH: feature/v0.22.0-orca-transition
HANDOFF_PARENT: 5422d0d5a41a6beae9228487f70d9c18716f1284
HANDOFF_COMMIT_SUBJECT: docs: fast-track Orca seam qualification
ACCEPTANCE: docs/releases/v0.22.0/M1_1A_IDENTITY_CATALOG_ACCEPTANCE.md
MATRIX_JSON: docs/releases/v0.22.0/M1_ORCA_PROVIDER_SEAM_MATRIX.json
MATRIX_REPORT: docs/releases/v0.22.0/M1_ORCA_PROVIDER_SEAM_MATRIX.md
IMPLEMENTER_REPORT: docs/external-agent/REPORT-M1.2.md
```

This task is immutable after handoff. Do not edit it.

## 1. Objective

Using only the pinned, read-only `orca agent-context --json` catalog, map every
low-level Orca capability needed by the 24 frozen Aether MCP tools to an official
structured public command. Record exact argument metadata, result-schema evidence,
effect class, timeout semantics and recovery semantics. Classify each required
capability as `SUPPORTED`, `PARTIAL`, `MISSING` or `UNKNOWN`.

This is a documentation/evidence task. Do not implement an adapter, MCP package or
provider code and do not execute any mapped operation. Do not start Orca runtime
or begin M1.3.

## 2. Governing sources

Read completely before collection or writing:

- `AGENTS.md`
- `docs/external-agent/OPERATING-CONTRACT.md`
- `docs/external-agent/TASK-M1.2.md`
- `docs/releases/v0.22.0/M1_1A_IDENTITY_CATALOG_ACCEPTANCE.md`
- `docs/releases/v0.22.0/M1_1_CORRECTION_2_REVIEW.md`
- `docs/releases/v0.22.0/ROADMAP.md`, especially sections 9, 10.4 and 10.6
- `docs/architecture/AETHER_MCP.md`, especially provider adapter and control flows
- `docs/architecture/ORCHESTRATION.md`
- `docs/reference/AETHER_MCP_CONTRACT.md`
- `docs/reference/AETHER_TRACE_SCHEMA.md`
- `docs/reference/AETHER_LEARNING_EPISODE_SCHEMA.md`

The frozen contract defines required Aether behavior. The live public catalog is
the only authority for what Orca currently exposes. Do not infer public support
from private files, old docs or human prose.

## 3. Preflight — stop on mismatch

Before writing:

1. Verify exact project root and branch.
2. Require `git status --porcelain` empty.
3. Require `git rev-parse HEAD^ == HANDOFF_PARENT`.
4. Require the HEAD subject equals `HANDOFF_COMMIT_SUBJECT`.
5. Read-only verify exact launcher/AppImage paths, sizes and SHA-256 values from
   the M1.1a acceptance. Any drift is `BLOCKED`.
6. Require no Orca-labelled process in read-only process inventory. Do not kill
   unknown processes.
7. Confirm the three output paths do not already exist.

Do not reset, stash, switch, fetch, pull, rebase, amend or absorb changes to pass
preflight.

## 4. Exact allowed repository files

Create only:

1. `docs/releases/v0.22.0/M1_ORCA_PROVIDER_SEAM_MATRIX.json`
2. `docs/releases/v0.22.0/M1_ORCA_PROVIDER_SEAM_MATRIX.md`
3. `docs/external-agent/REPORT-M1.2.md`

Do not modify source, tests, prior evidence, acceptance/review files, roadmap,
status, architecture, contracts, dependencies, configuration or any other path.

Temporary roots/files are allowed only as direct `/tmp/aether-m1-2-*` children and
must be removed before the final commit. Inline standard-library Python may parse
and validate data; do not create a repository script.

## 5. Authorized catalog collection

Create two fresh isolated roots with HOME, all XDG roots and TMPDIR below their
own root. Use a small explicit environment allowlist. Invoke exactly twice:

```text
/home/darkarty/.local/bin/orca agent-context --json
```

Requirements:

- cwd is the isolated root;
- exit 0 and empty stderr;
- outputs are byte-identical;
- schema `1`;
- declared and actual command count `220`;
- raw bytes `153496`;
- SHA-256 `068e1d66737f19835536e4a1573a2f931bffe9821af9c1bdff855f902898944b`;
- no unexpected file under either isolated root;
- zero test-owned processes and zero Orca-labelled survivors afterward.

Keep raw catalog data only in owned temporary files or memory. Do not commit the
153 KB catalog or print environment values/secrets. Delete all temporary roots and
files in `finally`-equivalent cleanup.

## 6. Frozen Aether tool inventory

The JSON must enumerate these 24 tools exactly once:

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
swarm_record_decision
swarm_record_evidence
swarm_close
swarm_trace
orca_search
orca_describe
orca_call
orca_batch
orca_events
learning_capture
learning_label
learning_dataset
learning_export
project_forget
```

For each tool record:

- implementation milestone;
- Aether-local, Orca-provider or hybrid ownership;
- required low-level provider capability IDs, or an explicit empty list with
  reason when no Orca seam is required;
- effect class from the frozen Aether contract;
- whether M1.2 evaluates it now (`M2`–`M5`) or records it as later/local scope.

## 7. Required provider capability domains

Derive exhaustive M2–M5 capability rows from the governing control flows. At
minimum cover:

1. catalog search and exact command description;
2. Run create/bind/start/inspect/list/status/cancel/close;
3. Task create/bind/dependency/status/cancel/retry lineage;
4. Dispatch submit/accept/status/cancel/retry/reconcile/fence;
5. worker launch/identity/profile/environment/status/stop;
6. message send/list/read, question/reply and handoff;
7. terminal create/execute/status/output/close;
8. worktree create/bind/inspect/remove/cleanup;
9. event/list/cursor or equivalent observation;
10. recovery/restart/reconciliation after ambiguous or partial effects;
11. aggregate resource inventory and idempotent cleanup;
12. version/catalog/build identity reads needed for drift detection.

Do not assume that one broad command satisfies every distinct semantic row. Split
rows whenever arguments, results, effect, timeout or recovery differ.

## 8. Matrix JSON contract

Use deterministic sorted/indented JSON with:

```text
schema_version: 1
status: PROVISIONAL
source_identity:
  launcher/appimage/version/catalog facts from M1.1a
classification_legend:
  SUPPORTED/PARTIAL/MISSING/UNKNOWN definitions
aether_tools: exactly 24 entries
provider_capabilities: exhaustive sorted rows
summary:
  counts by classification and domain
  required_M2_to_M5_total
  blocking_missing_or_unknown_ids
  provisional_gate: SUFFICIENT | INSUFFICIENT | UNRESOLVED
```

Each provider capability row must include:

```text
capability_id
domain
required_by_tools
required_by_milestones
required_operation
provider_command or null
provider_command_path or null
argument_evidence:
  argumentMode, positionalArgs, flags and aliases from catalog
result_evidence:
  whether structured JSON is explicitly proven and exact evidence
provider_effect_class: READ_ONLY | LOCAL_APPEND_ONLY | LOCAL_REVERSIBLE |
  EXTERNAL_EFFECT | UNKNOWN
timeout_semantics: exact catalog evidence or UNKNOWN
recovery_semantics: exact catalog evidence or UNKNOWN
classification: SUPPORTED | PARTIAL | MISSING | UNKNOWN
evidence: catalog field/value references
gap: null or exact missing fact
fallback: NONE
```

Definitions:

- `SUPPORTED`: exact public command plus sufficient structured arguments, result,
  effect, timeout and recovery semantics for the required capability.
- `PARTIAL`: exact public command exists but one or more required semantics are not
  publicly structured.
- `MISSING`: no public structured command satisfies the required capability.
- `UNKNOWN`: catalog evidence cannot decide without executing an operation or
  consulting non-authoritative/private material.

Never upgrade a row based only on summary, usage, examples, notes or human prose
when the required structured result/effect/recovery contract is absent.

## 9. Markdown synthesis

The Markdown report must:

1. state exact source identity and collection method;
2. summarize classification counts without duplicating all raw JSON;
3. provide one concise table by capability/domain;
4. list every `PARTIAL`, `MISSING` and `UNKNOWN` row with exact gap;
5. distinguish Aether-local tools from Orca-owned operations;
6. answer whether every required M2–M5 operation has a public structured seam;
7. state that M1.1b remains open and M1.3 remains blocked;
8. recommend `PROCEED_TO_M1.3_PREPARATION`, `RETURN_TO_M0_DESIGN`, or
   `RESEARCH_REQUIRED`, but never authorize or start that action.

If any required operation is available only through private Orca storage, GUI
automation, free-form shell or unstable prose parsing, classify it `MISSING` and
recommend return to M0. Do not design a fallback.

## 10. Validation

Before commit run one fail-fast bundle that proves:

- JSON parses and is deterministic across two serializations;
- source catalog identity matches M1.1a exactly;
- exactly 24 unique Aether tools with the frozen names;
- every M2–M5 tool references defined capabilities;
- every capability has exactly one valid classification;
- every `SUPPORTED` row has a non-null exact provider command and structured
  result/effect/timeout/recovery evidence;
- every referenced provider command exists exactly once in the 220-command
  catalog;
- no duplicate capability IDs;
- all unresolved IDs equal the summary list;
- Markdown counts equal JSON counts;
- no private path, GUI, free-form shell or fallback mapping is accepted;
- links, fences, `git diff --check` and secret scan pass;
- all `/tmp/aether-m1-2-*` roots/files are gone;
- zero test-owned/Orca-labelled process survivors;
- `git status --porcelain` contains only the three declared uncommitted files
  before commit.

## 11. Commit and stop

Create exactly one commit:

```text
docs: map Orca structured provider seams
```

The commit contains exactly the three declared artifacts. Do not update status or
accept M1.2 yourself. Do not push, merge, rebase, amend, tag or Release.

Return only:

```text
M1.2 IMPLEMENTER RESULT: PASS | FAIL | BLOCKED
HEAD: <full hash>
COMMIT: <full hash> docs: map Orca structured provider seams
CATALOG: <schema/count/bytes/SHA-256/two-run result>
TOOLS: <24 unique result>
CAPABILITIES: <total and SUPPORTED/PARTIAL/MISSING/UNKNOWN counts>
PROVISIONAL GATE: SUFFICIENT | INSUFFICIENT | UNRESOLVED
REPORT: docs/external-agent/REPORT-M1.2.md
MATRIX: docs/releases/v0.22.0/M1_ORCA_PROVIDER_SEAM_MATRIX.json
SUMMARY: docs/releases/v0.22.0/M1_ORCA_PROVIDER_SEAM_MATRIX.md
CLEANUP: <roots/processes result>
WORKTREE: clean | dirty
BLOCKERS: none | exact blocker
STOPPED: yes — no operations executed; M1.3 not started
```

Then stop completely.
