# Objective Contracts

**Status:** owner-approved bootstrap implementation
**Source defect:** [#227](https://github.com/DarkArty07/Aether-Agents/issues/227)

## Purpose and vocabulary

An **Objective Contract** is Morfeo's durable, executable statement of one owner-approved objective handed to Supervisor. It defines the required outcome, scope, delegated authority, deliverables, acceptance, testing standard and stop conditions. Supervisor owns the execution plan and work-unit decomposition.

A **Contract Handoff Envelope** is the short Kanban body carrying only contract identity, portable project UUID, project-relative path, SHA-256, base commit and a verify-before-decomposition instruction. Kanban is routing/lifecycle, never the contract body.

This requirement applies only to Morfeo → Supervisor pipeline handoffs. Morfeo's bounded direct work remains unaffected.

## Reconciliation with R2

R2-D01 previously prohibited a second artifact that duplicates Spec Kit obligations. Issue #227 demonstrated that a durable handoff identity is nevertheless required because a complete inline tool-call body can be abbreviated before Kanban.

Owner decision: Objective Contracts are now the canonical handoff artifact. They may reference existing Spec Kit files and must not contradict them. When an obligation already has one canonical owning artifact, the Objective Contract references it and states only the objective-level binding needed by Supervisor. This amendment is motivated by observed transport loss, not by a new document phase.

## Project isolation

Version 1 assumes exactly one repository root per Aether Project. Every operation requires the portable UUID from `.aether/project.toml`. The tool resolves it through `ProjectRegistry` and verifies registry/marker agreement before every read or write.

The tool must never infer identity from cwd, last-used repository, profile, repository name, timestamp or an unverified environment value. A contract ID remains permanently bound to one project. Conflict produces zero writes and zero dispatch.

## Storage and lifecycle

```text
.aether/
  project.toml                 # portable, tracked
  drafts/                      # persistent local drafts, ignored
  objective-contracts/         # finalized versions, tracked
    <contract-id>/v<N>.md
```

Actions are `begin`, `set_section`, `show`, `list`, `validate`, `finalize`, `supersede` and `prepare_handoff`. `validate` reports required-section completeness for the current draft without finalizing or mutating it. Accepted content is persisted one section at a time with optimistic `expected_revision`; a complete contract is never transported in one tool argument.

Objective Contract prose is UTF-8 and may be multiline or longer than observation metadata. The authoring boundary rejects truncation sentinels and recognized credential value shapes, but it does not apply observation-only ASCII, length, URI, email or machine-path restrictions to contract prose.

Required sections are owner intent, objective, decisions/assumptions, in/out scope, authority, deliverables, acceptance criteria, testing standard, stop conditions and canonical references.

Drafts are editable. Finalization validates completeness, rejects truncation sentinels, records provenance, writes and reads back the final bytes, and returns SHA-256. Finalized identity is immutable: corrections create `vN+1` with `supersedes` and a change reason; prior bytes remain unchanged.

## System provenance

The capability—not the model—records RFC 3339 UTC and local-offset creation/finalization timestamps, `author_profile=morfeo`, and exact creation/finalization Hermes session IDs. No transcript or prompt content is stored.

## Responsibility boundary

The separate authoring plugin owns project resolution, incremental persistence, validation, finalization, versioning, provenance, digest generation, listing, envelope preparation and local execution-board provisioning. It is enabled only for Morfeo.

It does not infer owner decisions, auto-commit, dispatch Kanban, widen authority, modify finalized versions or join the observer plugin. Supervisor and Implementers receive read-only contract access.

`prepare_handoff` succeeds only when both `.aether/project.toml` and the exact final contract bytes are reachable from Git `HEAD`. A ready handoff provisions or reuses one isolated board for the complete executable identity `(project_id, contract_id, version)` and resolves the exact-path native Hermes Project. It returns the board and Hermes Project only as local root-card routing side data; neither belongs in portable contract bytes or the short envelope. Morfeo separately creates the Kanban card. Supervisor independently verifies project, path, digest and base commit before creating children.

## Execution-board isolation

A ready `prepare_handoff` provisions exactly one local Hermes board for the complete executable identity `(project_id, contract_id, version)`. The deterministic slug encodes every identity byte and the local `board.json` repeats the exact Aether tuple for fail-closed readback; retries and concurrent Morfeo sessions converge on the same board, while another project, contract or version resolves to a different board and SQLite database.

Provisioning occurs only after Git/base verification succeeds. It resolves exactly one non-archived Hermes Project whose primary repository equals the same verified Aether project root passed directly by the store, scopes the board to that runtime Project and reads the metadata/database back before returning. Missing, ambiguous, archived, path-conflicting, raw-DB-override, symlinked or identity-conflicting state stops handoff before board mutation and never falls back to the current/default board.

`execution_board` and `hermes_project_id` are local root-card side data. They never enter the portable Objective Contract, Contract Handoff Envelope, child bodies or opaque flow/idempotency identities. Morfeo passes them unchanged as the Supervisor root card's `board` and `project`; the plugin provisions no card and performs no dispatch. Hermes pins every spawned worker to that board, so unrelated contract flows cannot read or mutate each other's task graph, claims, logs or workspaces. Project-linked worktrees still isolate repository writes; source-level overlap remains an integration concern rather than a Kanban concern.

## Pragmatic version-1 exclusions

No dashboard, semantic search, outcome artifact, multi-repository project, automatic commit/dispatch, historical migration, central mutable index or context-compressor redesign. Direct Morfeo work creates no ceremonial contract.

## Acceptance

1. Interleaved drafts for two registered repositories never cross roots.
2. Marker/registry conflict, stale revision and truncation sentinel cause zero writes.
3. Timestamps and session IDs come from runtime/system inputs, not model arguments.
4. Finalization produces deterministic readable Markdown and verified SHA-256.
5. Superseding creates `v2` while preserving `v1` byte-for-byte.
6. Handoff is refused until marker and contract are present unchanged in Git `HEAD`.
7. The plugin exposes exactly one transactional tool only when configured for Morfeo.
8. A real fresh Supervisor worktree reads and verifies the same contract bytes before decomposition.
9. The blocked telemetry qualification is recreated from a short envelope and proceeds to the next real bug.
10. Unicode, multiline and long contract prose round-trips unchanged except for documented outer whitespace normalization, while recognized credential value shapes remain denied.
11. A ready handoff provisions one deterministic project-scoped board; a retry, including a concurrent retry, reuses it.
12. Different projects, contracts and finalized versions resolve to distinct board databases whose tasks are invisible to each other.
13. No board is created before Git/base verification succeeds, and existing archived/path/project identity conflicts fail closed without using `default`.
14. The execution board and runtime Hermes Project are returned only as root-card side data and remain absent from contract bytes and the short envelope.

## Bootstrap

Because the pipeline is blocked by the missing capability, the owner authorized Morfeo to implement it directly. The first contract may be materialized once through verified incremental writes; that bootstrap is retired as soon as the tool is active.
