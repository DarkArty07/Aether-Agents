# 005: Shared project knowledge and role work memory

**Status:** owner-authorized main-integration candidate, 2026-09-05. This source is not
an activated runtime or release qualification. The owner's explicit requests to implement
the plan and integrate the completed candidate into `main` are a bounded exception to
PD-74 for this capability only. They do not unfreeze unrelated features or authorize a
release, deployment, live-profile activation or provider/model spending.

## Outcome

Reduce repeated repository discovery between sessions while preserving current-source
verification. All three roles have the same tools and may maintain the project graph.
Experiences belong to the project and role, not to a shared owner-personalization store.

## Requirements

- **KG-01 Identity:** use the existing portable project marker and local ProjectRegistry.
  Resolve each model call from an exact native session or explicit operator-created
  session binding. A verified session workspace may identify its exact Git root; process
  cwd, last-used graph, a project name and a model-supplied filesystem path may not.
  Contradictory bindings return a typed error with no substitute project data.
- **KG-02 Versions:** every published snapshot identifies project, worktree/view, Git
  commit, scope version, input hashes and engine version. Worktree snapshots are not
  union-merged. Initial support indexes committed regular source blobs; uncommitted
  changes remain explicitly uncovered and require direct inspection.
- **KG-03 Collaboration:** Morfeo, Supervisor and Implementer receive the same query and
  update actions. Publication is serialized under a stable per-view lock. Its inode is
  not deleted after release. Equivalent updates reuse a complete snapshot. Readers
  never consume a partially published candidate or another revision by silent fallback.
- **KG-04 Sources:** capture bounded, selected regular Git blobs without executing
  repository code, filters or hooks. Exclude links, submodules, LFS pointers, binary
  content, private profile/state directories, obvious secret files and high-confidence
  credential patterns. These checks are defense in depth, not a universal secret scanner
  or hostile-code sandbox.
- **KG-05 Runtime boundary:** reuse original Graphify 0.9.54 in an isolated subprocess
  environment. Do not vendor or alter Hermes/Graphify core. Installation is explicit;
  importing Aether, listing tools and asking a question do not install dependencies.
- **KG-06 Tools:** expose `project_knowledge` and `work_memory` through one native Hermes
  plugin, identical across the three roles. Schemas reject caller-selected role, project,
  graph path, note directory, executable and environment. Operator CLI operations are
  separately explicit. Return revision, coverage and bounded output with honest token
  estimates; a successful transport alone is not functional success.
- **KG-07 Experiences:** store complete situation, lesson, applicability, outcome and
  evidence under `(project_id, role_id)`. Every save carries one opaque idempotency key:
  an exact retry returns the existing note, reuse with changed content conflicts, and
  independent contributions use distinct keys even when their text matches. Only the key
  digest is persisted. All temporary implementers share the Implementer role namespace
  but retain individual session/task/run attribution. This does not share Hermes homes or
  owner-facing personal memory.
- **KG-08 Integrity:** note versions are immutable and have one effective revision.
  Corrections require the expected revision. Original content remains searchable and
  readable with explicit continuation. Reflection consumes only effective complete notes.
  Administrative deletion invalidates derived summaries and removes retained local note
  revisions; exported copies and independent backups remain outside that operation.
- **KG-09 Reflection:** invoke native Python `reflect(..., graph_path=None)` explicitly
  inside the isolated component. Never rely on CLI omission of `--graph`. Private notes
  and reflections are excluded from the shared corpus, and no personal learning sidecar
  is written beside the shared graph. Native reflection is signal aggregation, not
  training, semantic synthesis of full answers or independent verification.
- **KG-10 Guidance:** deliver `project-knowledge` and `work-memory` as package-owned
  canonical skills, discoverable through existing mechanisms. Add availability-guarded
  guidance to all three SOUL resources, preserve their responsibilities and avoid
  compulsory calls for irrelevant work. Skills do not redefine authority.
- **KG-11 Degradation:** unavailable, stale, corrupt or unbound knowledge cannot prevent
  normal authorized file-based work. Do not claim that failed updates will finish later
  unless a real operation has been scheduled. No automatic provider use or tool-schema
  mutation inside a conversation.
- **KG-12 Qualification:** verify native component execution, role/project isolation,
  simultaneous updates, correction and recovery across sessions, packaging and native
  plugin dispatch. Separate deterministic/component results from model-driven E2E,
  semantic extraction and measured cost/quality improvement.

## Initial implementation boundary

Structural extraction and document navigation are local. Rich semantic document
extraction is not implemented or enabled in this candidate. It requires a separately
qualified backend, corpus policy and explicit spending/data-egress authority. Outputs
must show structural-only coverage rather than claim semantic understanding.

The component is opt-in and profile activation remains explicit. MCP transport,
provider-backed learning, automatic skill promotion, global/cross-project graph merging,
permanent watchers, dashboards and new graph/vector databases are outside this delivery.

## Authority and traceability

Current code owns demonstrated behavior; this specification owns intended behavior.
The implementation registry records partial or implemented surfaces and their remaining
qualification limits. Research preserves the audit, including tests that reproduced
faults. The plan, tool/data contract and SOUL/skills contract are derived execution aids.
This candidate must not be counted as passing the existing PD-74 rolling reliability gate.
