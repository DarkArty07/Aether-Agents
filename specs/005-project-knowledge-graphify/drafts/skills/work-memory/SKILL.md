---
name: work-memory
description: Save and reuse role-scoped project work experiences.
version: 0.1.0
author: Christopher, Aether Agents
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [experience, retrieval, learning, correction, privacy]
    related_skills: [project-knowledge, canonical-skill-governance]
---

# Work Memory Skill

> DRAFT FOR IMPLEMENTATION. This file is not installed or authoritative today.
> Its examples describe the proposed Aether contract, not currently available tools.

Retain nontrivial technical experiences and recover their original details in later
sessions. Work memory belongs to the current project and role. It is not owner-facing
personalization, canonical project truth, a complete session transcript or model training.

## When to Use

- Recall prior attempts, corrections or techniques relevant to the current task.
- Save a non-obvious failure, a reusable verified solution or a meaningful correction.
- Correct a recorded lesson when new evidence changes its meaning or applicability.
- Request an updated reflection when a summary of recorded signals is useful.
- Do not write a note for every command, manufacture a lesson to satisfy ceremony,
  or consult all memories before a simple task.

## Prerequisites

- The managed `work_memory` tool is available with a verified project and role binding.
- Know the task's current scope and the evidence you actually have. Do not invent
  successful tests, dates, commits or prior decisions.
- All roles receive the same operations. Temporary Implementers contribute to their
  project's Implementer-role store; they do not share Hermes profile homes.
- Credentials, private owner data and unrelated project content are not note material.

## How to Run

Use `work_memory` rather than raw Graphify CLI commands. The plugin selects storage,
records runtime provenance and isolates reflection. You do not choose `memory_dir`,
`graph_path`, another role or a global store. Read source documents with normal file
tools when a note's applicability depends on current code or policy.

## Quick Reference

Examples target the proposed contract; confirm the registered schema when deployed:

```text
work_memory(action="search", query="contract handoff validation", limit=3)
work_memory(action="read", note_id="<id returned by search>")
work_memory(action="save",
  situation="A targeted test passed but the integration scenario failed",
  lesson="The fixture omitted a required configuration value",
  applicability="Use when this fixture is reused with the same configuration contract",
  outcome="useful",
  evidence=[{"path":"tests/test_example.py","locator":"<actual test name>","result":"<observed result>"}])
work_memory(action="correct", note_id="<existing note id>",
  reason="The former lesson applied only to an older interface",
  replacement={"lesson":"<corrected lesson>","applicability":"<verified conditions>"},
  evidence=[])
work_memory(action="reflect")
```

The fixture names and observations above are illustrative. Supply actual references,
not these placeholders. Empty evidence stays explicitly unverified; never mark an
example as a successful execution. `reflect` does not replace `search` or `read`.

## Procedure

1. Search briefly when past technical experience could avoid rediscovery. Use the
   subsystem, symbols and problem; limit the result set rather than loading a role's
   full history. No match is a normal outcome, not a reason to search other roles.
2. Open the original note if details affect the decision. Check its conditions, source
   revision, evidence, corrections and freshness. If output is paginated, follow the
   returned cursor before assuming you read the full note. A useful result is not
   proof; a stale result may still orient a search but cannot certify current behavior.
3. Apply only what is compatible with current instructions and the project sources.
   Keep ordinary technical judgment local. Do not revive an obsolete decision because
   it was remembered, or copy preferences into project rules.
4. When work produces a nontrivial lesson, capture the situation, concrete result,
   conditions and evidence while you still have context. Use `useful`, `dead_end` or
   `corrected` as the outcome signal. Do not generalize one failure into a universal
   prohibition or call an untested idea verified.
5. Read the save receipt and note ID. If the write fails, preserve only a scoped
   finding in the existing permitted work record; do not copy secrets or start a
   parallel memory store. Do not report a note as saved without a successful receipt.
6. If a prior note is wrong or narrower than stated, use `correct`. Preserve its history
   and evidence; normal retrieval must select the replacement rather than accumulating
   both as independent corroboration. A conflict is not permission to overwrite another
   current revision silently.
7. Use `reflect` when enough new outcomes make the summary useful, not at every turn.
   It summarizes signals and references, not every technical answer. Retrieve the original
   notes for the actual solution. A report's generation tells you which notes it covered.
8. Share a verified project fact through the owning document or procedure when authorized
   by the task. A learned procedure becomes canonical only through the normal sanitization,
   verification and review path. Do not dump this role's history into the shared graph.

## Pitfalls

- Different role names do not isolate Graphify by themselves; the plugin owns binding.
- Omitting `--graph` from the native CLI does not guarantee private reflection: it may
  autodetect the shared graph. Do not bypass the managed reflection path.
- Do not write `.graphify_learning.json` beside a shared graph, even when notes and
  LESSONS.md have private paths. Do not personalize shared query results with private data.
- `useful` is an outcome signal, not a certificate of correctness. Repeated notes and
  retry duplicates are not independent evidence.
- A note from another revision or a changed dependency may be obsolete even when the
  named file is unchanged. Verify the relevant conditions before reusing it.
- A new session or a different model does not require a new role memory namespace.
- Keep owner preferences in the existing private personalization memory. Supervisor and
  Implementer work memory is for technical experience, not profiling the owner.

## Verification

- Ensure receipts identify the current project and role; a note ID is never a path.
- Confirm a saved solution is retrievable in full, not only counted by reflection.
- Confirm corrections point to replacements and do not silently retain wrong advice as current.
- After reflection, treat the report as an auxiliary summary and inspect pending generations.
- If memory is unavailable, continue the objective using current sources; do not widen
  permissions, install packages, create mandatory notes or repair unrelated infrastructure.
- For permanent removal requested by the owner, use the administrative workflow covering
  originals and derived results. Do not promise universal deletion from unknown backups.
