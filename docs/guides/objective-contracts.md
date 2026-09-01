# Objective Contracts and handoff

An Objective Contract is Morfeo's durable, project-bound statement of one owner-approved pipeline objective. It records the objective, scope, authority, deliverables, acceptance, testing standard, stop conditions, and canonical references. It is not a replacement for the relevant Spec Kit artifacts: Supervisor owns decomposition and `tasks.md`.

## Availability and scope

The `objective_contract` tool is registered only in a configured Morfeo profile. Supervisor and Implementer may inspect a finalized contract as evidence but do not author or modify it. Bounded direct Morfeo work does not need an Objective Contract or a ceremonial card.

The tool accepts these actions:

- `begin`, `set_section`, `show`, `list`, and `validate` for incremental drafts and explicit validation;
- `finalize` to produce an immutable, readable version with a verified digest;
- `supersede` to create a later version while preserving earlier final bytes; and
- `prepare_handoff` to prove the exact final bytes are in Git `HEAD` and prepare local routing data.

`validate` is a real current action. It validates the requested draft/contract state; it does not finalize, dispatch work, or change owner intent.

## Storage and immutability

```text
.aether/
  project.toml
  drafts/                         # local and ignored
  objective-contracts/<id>/v<N>.md # final, tracked versions
```

Finalization validates required sections, retains provenance metadata and a digest, and reads its committed bytes back. A correction is a new superseding version with a change reason, never an in-place edit of final bytes.

## Contract Handoff Envelope

The small Kanban root-card body carries the contract identity/version, portable project binding, project-relative path, digest, base commit, and verification instruction. It does not carry the full contract. `prepare_handoff` also returns opaque local values such as the execution-board slug, native Hermes Project ID, idempotency key, and flow ID. Those values are root-card side data only: pass them unchanged to the root-card integration fields; do not copy them into the portable contract, envelope, or child card bodies.

A handoff refuses on project marker/registry disagreement, missing or ambiguous exact-path native Project, uncommitted/missing final bytes, raw board-database override, unsafe filesystem redirection, or conflicting board identity. See [Execution](execution.md) for the resulting board boundary and [plugins and tools](../reference/plugins-and-tools.md) for the registered tool.
