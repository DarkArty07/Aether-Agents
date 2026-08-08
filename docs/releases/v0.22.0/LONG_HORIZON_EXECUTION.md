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
- CI: 5/5 required checks passed on pushed head `07e7278`.

### M1.1b

- Status: LOCALLY COMPLETE
- RED: CLI identity overrides, Bash-semantics parser and readable mount-prefix bypass each failed as expected; the repaired FIFO test executed and passed without skip.
- GREEN: focused `29 passed`; full suite `60 passed, 0 skipped`; Ruff, compileall, M2.1a smoke, diff and secret scans passed.
- Commit: `eb7a23baaeb969ef388268786d187d6f4c8bef7d` (`feat: qualify canonical Orca candidate exactly`)
- Real probe: two fresh roots produced identical output matching `M1_ORCA_QUALIFICATION.json`; zero processes and temporary roots survived.
- Acceptance: `M1_1B_ACCEPTANCE.md`

### M2.2

- Status: COMPLETE — LOCAL AND CI
- RED: protocol module and snapshot absent; exact workflow contract then failed for missing `src/aether_mcp/protocol.py` in both workflows.
- GREEN: focused `22 passed`; full suite `81 passed, 0 skipped`; 24 schemas, 50 stable errors, zero callable tools, Ruff, compileall and smoke passed.
- Commit: `59989d63f01930485715499156000d9fedfff037` (`feat: add bounded Aether MCP protocol contract`)
- Schema drift: generated 94,139-byte bundle equals committed snapshot; SHA-256 `e7f39a76ac4795ade2ec0a15bf64b4cab2233b912cf2285b0ce76d2805a2e605`.
- Acceptance: `M2_2_ACCEPTANCE.md`
- CI: 5/5 required checks passed on pushed acceptance head `b092abf`.

## Final gate

- Exact committed-tree verification: PASS on detached `b092abf044cd79f51748a950c2f4bed934a69f40` in a fresh Python 3.11 venv; clean-install provenance was under that venv, full suite `81 passed, 0 skipped`, Ruff, compileall, smoke, source inventory, schema drift, status authority and delta secret scan passed.
- Pull request synchronization: Draft PR #163 reached the same head and all five required checks passed. A final documentation-only ledger commit follows this recorded gate.
- Continuity reconciliation: PASS; `AGENTS.md`, `ROADMAP.md`, `STATUS.yaml`, M1.1b acceptance and M2.2 acceptance agree that the authorized sequence is complete and no next implementation is authorized.
- Technical verification time: `2026-08-08T05:25:03-06:00` (epoch `1786188303`).
- Finish time and elapsed duration: captured after terminal documentation CI and cleanup in the final PR comment, avoiding a self-invalidating post-CI commit.
