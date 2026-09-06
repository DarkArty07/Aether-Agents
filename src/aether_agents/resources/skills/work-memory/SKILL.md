---
name: work-memory
description: Reuse verified context from project-role experiences.
version: 0.1.0
author: Aether contributors
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [graphify, memory, experiences, correction]
    related_skills: [project-knowledge, canonical-skill-governance]
---

# Work Memory Skill

Record and recover useful work experiences in the current project's role namespace.
Original notes preserve full solutions; reflection is only a deterministic summary of
signals. Neither notes nor reflection define product intent, certify tests or change
model weights.

## When to Use

Use when a useful technical experience can avoid repeated work. Preserve
project-relative evidence; this procedure cannot grant authority or certify a result.

- Recover a relevant prior solution, non-obvious failure, correction or limitation.
- Preserve a useful lesson while the task context and evidence are still available.
- Correct an earlier note when current evidence contradicts it.
- Do not record every command, transcript, successful read or temporary status update.

## Prerequisites

- The native `work_memory` tool is available and the session has a verified project.
- Morfeo, Supervisor and Implementer have the same actions. The plugin chooses the
  namespace from project and role; temporary implementers share their role's experience
  store with attributed task/session records, not a shared Hermes profile home.
- Existing source inspection remains the fallback if memory is unavailable. Do not
  create another store or install a provider to circumvent that failure.

## How to Run

Use `work_memory` to save, search, read, correct and reflect. Never supply an identity,
project path, note directory, executable or environment override. Every `save` requires
an opaque `idempotency_key`: reuse it unchanged only when retrying that exact save, and
create a new key for every independent note. A key is hashed before persistence. Do not
invoke raw `graphify reflect` from the project: omitting `--graph` still allows graph
autodetection. The integration explicitly calls the Python function with
`graph_path=None` in isolation.

## Quick Reference

```json
{"action":"search","query":"contract validation failed input","limit":5,"budget_tokens":2000}
```

```json
{"action":"save","idempotency_key":"wm-save-contract-empty-input-01","situation":"A validation failure was caused by an unchecked empty input","lesson":"Check the empty-input boundary before dispatching this operation","applicability":"The contract-validation path inspected in this task; revalidate after interface changes","outcome":"useful","evidence":[{"path":"src/contracts.py","locator":"validate_contract","result":"Observed the explicit empty-input check in source"}],"source_nodes":["validate_contract"]}
```

```json
{"action":"read","note_id":"wn_11111111111111111111111111111111"}
```

```json
{"action":"correct","note_id":"wn_11111111111111111111111111111111","expected_revision":1,"reason":"The old lesson omitted an applicable boundary","replacement":{"lesson":"Validate both absence and empty input","applicability":"Only this interface revision until revalidated"},"evidence":[]}
```

```json
{"action":"reflect"}
```

Example identifiers above are illustrative. Use the real note ID and current revision
returned by the tool. Follow `next_cursor` to read the remainder of an original note.

## Procedure

1. Search when previous experience could reduce work. Prefer a component, failure or
   symbol-specific query over loading the whole memory namespace.
2. Read promising original notes, following continuation when relevant content remains.
   A search excerpt or `LESSONS.md` may omit the actual solution.
3. Check applicability, source revision and evidence against current reality. A stored
   test result is historical, not a current PASS; source existence is not verification
   of a claimed result. The tool records claims as reported unless independently checked.
4. Apply the lesson only within the task and governing artifacts. Current instructions,
   specifications, code and applicable canonical procedures outrank recollection.
5. Save a concise, complete experience when it can prevent meaningful repetition:
   situation, lesson, conditions, outcome and actual evidence. Generate one opaque
   `idempotency_key` for that intended note and preserve it if the same tool call must be
   retried; do not reuse it for another contribution. Evidence may be empty; never invent
   a source or successful test to make a note appear verified.
6. Use `useful`, `dead_end` or `corrected` to describe the observed outcome, not universal
   quality of the cited component. A failed search in one task does not make a module
   irrelevant for every future task.
7. Correct an obsolete note with its latest `expected_revision`. A conflict means someone
   updated it: read again rather than force-overwriting. Corrections preserve history
   and only the effective revision contributes to ordinary retrieval and reflection.
8. Reflect when reviewing a meaningful set of experiences, not on every message. The
   result summarizes signals; it does not synthesize all original answers. Continue to
   use `search` and `read` for detailed solutions.
9. Promote a genuinely general project fact into its appropriate documentation or
   procedure using the existing review and canonical-skill governance path. Do not copy
   the private note collection into a shared graph or automatically create new rules.

## Pitfalls

- Never store credentials, private keys, owner-facing personal preferences, complete
  session transcripts or unrelated project information in work memory.
- Do not choose a different role to retrieve another role's private experiences.
- Do not write `.graphify_learning.json` beside the shared graph. Personal source-value
  judgments must not change the technical map or ranking for every agent.
- Separate memory by role is not a security sandbox against another process running as
  the same trusted OS user; do not claim stronger isolation than is implemented.
- A successful save receipt means the note was stored, not that its lesson is true.
- Reusing an `idempotency_key` with changed content is a conflict. Retrying unchanged
  content returns the original note with `idempotent_replay=true`; equal independent
  contributions require different keys.
- Deletion/export belongs to the explicit operator surface; exported copies and external
  backups cannot be erased merely by deleting the local note.

## Verification

Check the returned project, role, note ID, revision, generation and
`idempotent_replay` status. Recover a saved lesson through a later search/read and verify
relevant sources before reuse. Reflection should
not expose another role's notes or alter the shared graph. For closure, report actual task
and test evidence through the ordinary lifecycle; a memory record never replaces it.
