# Execution: boards, sessions, worktrees, and review

A finalized Objective Contract version receives an Aether-specific handoff boundary before Supervisor work begins.

## Per-contract execution board

`prepare_handoff` derives one deterministic execution-board identity from `(project_id, contract_id, version)`. It resolves exactly one live native Hermes Project whose primary path equals the verified Aether project root, creates or validates the board metadata and database, and reads them back before returning success.

The returned board and native Project identifiers are local root-card routing data. They are not portable contract content and must not be copied to envelopes or child bodies. Retries of the same ready version converge on the same board; a different project, contract, or finalized version receives another board. There is no fallback to the default/current board.

This isolates execution-board task graphs, claims, logs, and workspaces. It does not solve source-level merge collisions; worktree isolation and review still matter.

## Session affinity

A ready handoff derives an opaque flow identity. Supervisor phases for that flow use the runtime's session-affinity boundary and one canonical Supervisor workspace. Internal milestones do not return to the owner-facing session; only the lifecycle's explicit input, revision, or terminal-flow conditions should do so.

Implementer cards are deliberately different: each receives a fresh session and an isolated worktree. This preserves a bounded execution context and keeps a worker from inheriting a Supervisor's ongoing conversation.

## Worktrees and review

Implementation cards use the Hermes worktree lifecycle so parallel workers do not share a checkout. A completion includes actual verification and remaining risk. Supervisor reviews work it did not author, returns correctable rework through the review path, and performs the final integration verification.

A worker must flag repeated collision pressure on the same file as a hotspot rather than silently expanding its scope. Hermes provides the generic board, worktree, review, retry, and reclaim mechanisms; consult the [Hermes documentation](https://hermes-agent.nousresearch.com/docs/) for their general operation.

## Qualification limit

The handoff source and focused tests cover deterministic IDs, isolation checks, idempotent provisioning, and profile instructions. The complete installed runtime/session-affinity path remains a separately qualified boundary; see [Capability coverage](../reference/capabilities.md) and [limitations](../reference/limitations-and-troubleshooting.md).
