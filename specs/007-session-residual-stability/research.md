# Research ledger: residual session stabilization

## Shared baseline

- Aether project UUID: `12027989-a08f-41cd-a82c-54ff1bfb6b03`.
- Contract-design base: `600c08182fc16cee3bc0f6d639029972ee97f03d`.
- #354 was closed separately after the restored active resolver passed seven focused tests and later contract roots/children received exact bases.
- #227, #396, #397 and #399 are existing nonduplicate issues; #227 was reopened from this session's exact recurrence.
- Telegram Monitor `oc_f8c9fc9320587cf3@v4` is active and owns overlapping lifecycle/lab/CLI/docs files.

## #227 recurrence evidence

The v1 root `t_e963488b` persisted a 236-character body ending literally in `...[truncated]`. The worktree, finalized contract artifact and base were correct, and no children existed at detection. A complete recovery envelope was posted as a root comment and Supervisor was told to stop before decomposition. This proves the loss happened before Kanban persistence and that the current Aether pre-tool policy does not reject the sentinel. Issue #227 was reopened with the exact body hash; v2 includes prevention.

## #396 causal evidence

The affected v2 board contains the exact root token, four active tasks, five parent links and fourteen runs. The current reconciler calls `kanban_db_path()` without a board argument, reads `default`, finds no matching root and therefore emits no `native_reconciliation` events. The reducer's single unit is missing input, not a hidden descendant.

A second RED is required after selecting the exact board: native outcomes `review_requested` and `changes_requested` are passed as event `status` values outside the allowed envelope vocabulary. They must become terminal event status `completed` while remaining exact in `run_outcome`.

The Router contract proved wrong project routing: its trace events were projected under the Aether Agents collector and absent under the Router project. The observer currently owns one collector; it must select a verified project collector from the exact hook project hint and refuse cross-project fallback. A read-only/temp-output canary against the v2 board produced the expected Green: four units, root `t_69c40036`, five edges, fourteen runs and native reconciliation events.

## #397 causal evidence

Hermes destination precedence is explicit DB, explicit Kanban home, board/current/default. Changing only `HERMES_HOME`, cwd or a ContextVar cannot isolate an inherited `HERMES_KANBAN_DB`. A disposable reproduction added a task only to the foreign-target copy; the read-only live-board snapshot remained byte-identical with all table digests/counts unchanged.

Two safe variants were demonstrated: integrated `isolated_hermes_env` for a single explicitly pinned disposable DB, and accepted Monitor D15R child environment for canonical multi-board work with no raw DB override. Both passed child-side effective-root gates before the writer. #397 therefore consumes D15R after Monitor v4 acceptance and adds only the general probe-entry/procedure gap. Native production precedence is preserved. Accidental mutation must stop, preserve DB/WAL/logs and escalate; direct SQL cleanup is prohibited.

## #399 reproduced evidence

A disposable maintained-fork source and venv reproduced:

1. install editable without `hermes_state_compaction` in the top-level module inventory;
2. add the source file and update `pyproject.toml` without reinstalling;
3. `python -I` still reports `find_spec` as absent;
4. forced offline/no-dependency editable reinstall regenerates the finder and the same canary passes.

Current outer/runtime interpreters were already operationally recovered and have identical regenerated finder hashes. The source bytes remained unchanged. Upstream auto-discovers modules at install time but has the same snapshot property: adding a module later still requires reinstall.

Aether's clean release lifecycle installs editable source into new environments and is coherent. The gap is the existing dirty maintained-fork adoption/reconciliation path, which is not yet one authoritative, transactional product operation across both provisioned interpreters.

## Limits

- `project_knowledge` has no snapshot at this revision; source inspection is used instead.
- No live board was mutated by this research.
- No provider/model call, credential access, service restart, package publication or release was used.
- Exact #396/#397 reports are appended before contract finalization; this ledger does not claim their algorithms are qualified merely from issue prose.
