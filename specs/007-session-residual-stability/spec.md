# Specification: residual session stabilization

Status: design in progress for Objective Contract `oc_291b2fb34b413d92`.
Owning issues: Aether-Agents #396, #397 and #399. Issue #354 is already closed by prior evidence and is not reimplemented.

## Objective

Close the three demonstrated residual defects without interfering with the active Telegram Monitor v4 flow. Integrate intended artifacts to `main`, activate only reviewed changes, close the issues on exact canaries, clean objective-owned residue and preserve unrelated branches, worktrees, stashes, sessions and credentials.

## SR-396 — contract observation follows the exact execution board

An Objective Contract trace must observe its own provisioned board, root and descendants rather than remain at authoring-time state or follow the current/default board. The binding must derive from verified project UUID, contract ID/version, exact execution-board metadata and opaque root correlation. It must work for non-Aether repositories and preserve correct project attribution.

Acceptance requires a disposable RED/GREEN fixture and one real provider-free contract canary. After root creation and a child lifecycle transition, compact status must have a fresh `as_of`, include the root/child with correct relations and state, and retain explicit coverage gaps. It must not scan unrelated boards, infer acceptance, expose raw content or mutate Kanban authority.

## SR-397 — write-capable probes cannot reach a live board

Any Aether-owned harness or canonical review probe that may invoke native Kanban writers must construct one disposable context before importing or calling writers. It must scrub all inherited `HERMES_KANBAN_*`, `HERMES_SESSION_*`, task/run/project/cwd identity, set explicit disposable DB/home/board/workspaces roots, and verify the paths resolved by the loaded writer before the first mutation.

A mismatch refuses before writing. A live-board fingerprint and row-count canary must remain byte/row stable. Accidental mutation is escalated through supported lifecycle evidence; direct SQL deletion of tasks, comments, events or runs is never cleanup. First consume the accepted Telegram Monitor v4 isolation result and reuse it when it satisfies this requirement; do not duplicate or overwrite its active work.

## SR-399 — editable mappings are reconciled transactionally

Adding or removing a top-level Hermes module must trigger regeneration of editable metadata for every provisioned interpreter. The product-owned operation must accept one verified source and explicit interpreter set, back up generated editable metadata, perform forced local no-dependency reinstalls, and roll back already-updated interpreters if a later update fails.

The operation preserves dirty source bytes and status, runs without `PYTHONPATH`, supports offline/no-network recovery, and verifies each interpreter with `python -I`: distribution identity, `find_spec`, module origins and imports must resolve from the exact source. A maintained-fork packaging test keeps intentional top-level modules and setuptools discovery/allow-list coherent. Clean release installation remains strict and separate from an explicitly authorized dirty-runtime reconciliation.

## Preservation and authority

Owner authority covers local source changes, isolated tests, ordinary push/PR/check/merge, reviewed runtime activation and worker-safe restart when necessary. It does not authorize credential/provider/model changes, check bypass, history rewrite, data deletion, package publication, release creation, direct live-board mutation or interruption of the Monitor flow.

No issue closes on source presence, retry success, a board terminal flag or a test using injected `PYTHONPATH`. Release conclusions: `release_impact=patch`, `release_action=defer`, `release_channel=none`.
