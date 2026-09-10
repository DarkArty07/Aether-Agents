---
name: aether-observe
description: Use when checking contract progress with aether observe.
version: 0.1.0
author: Aether contributors
license: MIT
platforms: [linux]
---

# Contract observation in this project

## Purpose and authority

This Project Canonical Skill is discovered through root `AGENTS.md`. It provides a
procedure, not acceptance authority, a new controller, or a substitute for the owner,
Objective Contract, required independent review, or canonical work state.

Use the compact native `aether_observe` tool first for contract-wide status, change,
blockage and remaining-work questions. Read individual cards, artifacts, code or logs
only to answer a specific detail or to replace missing/unusable observation evidence.
The curated tool is a Morfeo surface. Other roles do not impersonate Morfeo to invoke it.

## Prerequisites

1. Resolve the exact Aether project and contract from the current objective and its
   canonical artifacts. A display name, current/default board, latest session, or cwd
   alone must not select a different project. Use the verified project root explicitly.
2. Resolve one contract ID or trace reference. If multiple versions/traces are possible,
   use the exact bound trace rather than guessing. Do not create a new contract or board
   to make an observation query work.
3. Confirm the native tool is available. If it is deferred, use native tool discovery
   and description. The read-only CLI alternative is documented below; neither route
   needs a model/provider request to summarize the stored facts.

## Procedure

### 1. Status first

Call `aether_observe` with `action="status"`, `project` set to the verified project
root and `ref` set to the exact contract ID or trace. These are runtime values, not
identities hard-coded into this skill.

Check returned project/contract/trace identity, `summary_id`, `as_of`, completion and
runtime states, required/done/open/blocked/review unit counts, and acceptance coverage.
Do not equate a decomposition root being done with completion of its descendants.

### 2. Changes when a valid comparison exists

For a follow-up, retain the last successful `summary_id` in the conversation or existing
objective context. Call `action="changes"` with `since_summary_id` and the same exact
project/ref. Check comparability, identity, timestamps and coverage. Never fabricate a
prior summary ID or infer a compatible comparison from unrelated sessions/contracts.
Fetch current status if the compact change response does not contain a needed fact.

### 3. Diagnose an actual anomaly

Use `action="diagnose"` for a blockage, unexpected lack of progress, incomplete
acceptance or coverage anomaly. Inspect verdict/reason codes, unfinished units/criteria,
next gate, coverage gaps and bottleneck/defect classes. Heartbeats prove liveness only.
They do not prove that implementation or review made progress.

### 4. Expand only the relevant evidence

For a specific requested correction, inspect that card's latest review handoff/comment.
For a failed test, inspect its recorded test output and the relevant code. For uncertain
worker activity, inspect its current run and actual recent tool/results evidence.
Use exact board/task binding from the contract handoff; never use the default board as
an alternative identity. Avoid reconstructing the entire board and every transcript
when the compact observation and one targeted source can answer the question.

### 5. Failure and incomplete coverage

- An explicit empty result means no matching observed open work, not proof that no work
  exists in the authoritative board. Ambiguous identity requires resolution, not recency.
- Partial, unknown or stale coverage remains labeled. Do not manufacture a progress
  percentage or completion claim from absent counters. If the owner requests a card-count
  percentage, disclose the denominator and distinguish it from effort/time completion.
- On an unreadable/schema/privacy error, report the exact sanitized code. Do not call
  the same failing reduction repeatedly or describe it as database corruption without
  evidence. The tool can wrap a summary-validation failure as state unreadable.
- Record a reproducible product defect according to repository policy and fall back to
  the minimum exact Kanban/artifact evidence. Do not disable privacy guards, drop keys,
  rewrite stored summaries, rebuild state, or switch projects merely to get a result.
- Observation may ingest/reduce and persist its own derived projection. It does not
  alter authoritative Kanban, SessionDB or contract artifacts. Do not claim that it has
  zero filesystem writes or use it inside a stricter no-derived-write audit.

### 6. Report and close honestly

Base the answer on the returned state and requested evidence, naming coverage limits.
Observation is a navigation/read model, not an independent approval. Final owner-objective
acceptance still requires the applicable contract-result-review procedure and actual
artifact/evidence checks; neither a green summary nor a terminal board flag replaces them.

## CLI alternative

After resolving the values in the local shell (placeholders below are examples):

```bash
aether observe "$CONTRACT_REF" --project "$PROJECT_ROOT" --json
aether observe "$CONTRACT_REF" --project "$PROJECT_ROOT" --since "$SUMMARY_ID" --json
```

`status`, `changes` and `diagnose` are native tool actions, not invented CLI subcommands.
Use the installed CLI help before using additional flags. Do not combine `--watch` and
`--json`. A compact tool call is normally preferable to a permanent watch process.

## Verification

- Confirm the returned identity against the owning contract and selected project.
- Distinguish a successful current summary, partial coverage, empty result and error.
- On changes, confirm the exact prior summary and comparability.
- Ground a detailed correction in the actual review evidence, not a generic reason code.
- Keep quoted/raw sensitive content out of public reports and artifacts.
- No corrective mutation or extra autonomous process is implied by this procedure.
