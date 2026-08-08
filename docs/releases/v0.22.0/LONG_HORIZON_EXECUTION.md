# v0.22.0 Long-Horizon Execution Log

> **Authorized by:** Christopher (DarkArty07)
> **Execution owner:** Hermes
> **Started:** 2026-08-08T04:44:21-06:00
> **Start epoch:** 1786185861
> **Branch:** `feature/v0.22.0-orca-transition`
> **Starting HEAD:** `a446c707ee893fcbd84d085d2b631e9aa93842f8`
> **Worktree:** `.aether/worktrees/feature-v0.22.0-orca-transition`
> **Status:** IN PROGRESS

## Frozen scope

Execute exactly three milestones in this order:

1. **M2.1a-R1:** repair the stale Release source-boundary assertion, cover both CI workflows, and reconcile versioned closeout authority.
2. **M1.1b:** replace heuristic Orca qualification with the already frozen canonical-candidate verifier, execute the mandatory FIFO regression, and close reusable isolation qualification without lifecycle operations.
3. **M2.2:** implement provider-independent canonical protocol models, stable errors, canonical request encoding, deterministic schema export, and bounded validation. No storage, trusted-principal derivation, provider adapter, Orca operation, or runtime activation.

## Protected boundaries

- Preserve the dirty primary checkout exactly.
- Use only the isolated feature worktree.
- Do not merge, tag, create a GitHub Release, deploy, register or activate MCP.
- Do not start Orca Runs, Tasks, Dispatches, workers, terminals, messages or lifecycle operations.
- Do not read credentials, private Orca state or unrelated repositories.
- Keep MCP local stdio and default-off.
- Use TDD for behavior changes and atomic commits per milestone.
- If one milestone is genuinely blocked, record the blocker and continue only with independent safe work.

## Milestone ledger

### M2.1a-R1

- Status: LOCALLY COMPLETE
- RED: `test_product_asset_workflows_accept_exact_bounded_mcp_source` failed on the stale `release.yml` assertion.
- GREEN: focused regression passed; full suite `82 passed, 1 skipped`; workflow YAML, Ruff, compileall, release-assets simulation and diff checks passed.
- Commit: `f31c6b610f9cbd0de38a617187d5497c194f9105` (`fix: reconcile M2.1a release source boundary`)
- CI: pending push

### M1.1b

- Status: PENDING
- RED: pending
- GREEN: pending
- Commit: pending
- Real probe: pending

### M2.2

- Status: PENDING
- RED: pending
- GREEN: pending
- Commit: pending
- Schema drift: pending

## Final gate

- Exact committed-tree verification: pending
- Pull request synchronization: pending
- Continuity reconciliation: pending
- Finish time and elapsed duration: pending
