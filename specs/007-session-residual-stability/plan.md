# Technical plan: residual session stabilization

## Execution shape

Supervisor creates three independently reviewed units plus one terminal integration lane. #396 may proceed independently. #397 first consumes the accepted Telegram Monitor v4 result and implements only a demonstrated residual gap. #399 is isolated from Monitor source while that flow is active; terminal integration waits for the Monitor result before touching shared lifecycle, CLI, policy or documentation files.

All candidates start from the finalized contract base. Terminal integration merges the latest `origin/main` normally and returns semantic conflicts to the owning unit; it does not rebase, squash or rewrite accepted commits.

## D396 — exact board and project reconciliation

The observer must resolve the execution board from canonical contract identity and verified board metadata, never ambient current/default board state. `_read_native_board` receives an explicit board slug and calls `kanban_db_path(board_slug)`. A private binding maps `trace_id -> (project UUID, contract, version, board slug)` from the verified `prepare_handoff` result; restart/bootstrap may reconstruct it only from exact canonical board metadata.

Reconciliation validates the board tuple, opens only that DB, binds the root from the opaque idempotency token, and follows native parent links. Unresolvable bindings emit a coverage gap and do not read `default`. Native terminal outcomes `review_requested`/`changes_requested` are preserved in `run_outcome`, while event `status` is normalized to the existing terminal envelope vocabulary.

The capture plugin uses a verified collector per Aether project (or an equivalent verified temporary collector), selected from the exact project hint before objective/kanban hooks. A cross-project hook never falls back to the collector already active for another project. No change belongs in journal ingestion or the reducer.

Required negatives: wrong project/version/DB, malformed metadata, absent or ambiguous root token, unrelated current board, and missing registry/marker. Required Green: exact board root plus descendants/runs, idempotent repeat, valid terminal outcomes, and a Router contract projected only under its own project UUID.

## D397 — reusable subprocess isolation and pre-write gate

Do not change native Kanban precedence; production workers require explicit DB pinning. Write-capable probes must use one of two reviewed constructors and a fresh subprocess:

- single-board probes use `aether_agents.lab.isolated_hermes_env`, which scrubs inherited Kanban/session/project/cwd identity and explicitly pins a disposable DB/workspaces root;
- canonical multi-board Monitor probes use the accepted D15R child environment, remove all raw Kanban selectors, resolve canonical `board=` paths inside the private laboratory, and must not set `HERMES_KANBAN_DB`.

Before the first writer, child-side code resolves effective home, board root, DB, projects DB and workspaces and compares them to private, non-symlink, contained roots. No write-capable helper may fall back to `os.environ.copy()` without this gate. Tests reproduce the vulnerable home-only environment on a disposable copy, then prove both safe variants leave a canary byte/row stable. Reviewer procedure prohibits direct SQL cleanup and requires preserving and escalating accidental mutation evidence.

## D399 — controlled editable reconciliation

Add one package-owned reconciliation operation shared with the existing lifecycle installer, without weakening clean release checks. Internal names are local freedom; observable behavior is fixed:

- explicit verified Hermes source and explicit one-or-more interpreter paths;
- inspect distribution/direct-url identity and generated editable files;
- capture private backups and source/status/tree fingerprints;
- execute forced editable reinstall with local source, `--no-deps`, and offline mode when selected;
- update all interpreters as one logical transaction, restoring metadata already changed if a later interpreter fails;
- execute `env -i`/`python -I` canaries and verify intended module origins;
- return a structured receipt with source and metadata fingerprints.

Do not inject `PYTHONPATH`, reset or clean the source, infer health from `pyproject.toml`, update dependencies, or restart a service for metadata-only repair. Add maintained-fork packaging coverage that fails if an intentional top-level module is absent from the built/editable mapping.

## Integration and runtime acceptance

Run focused RED/GREEN and neighboring suites, full exact-Hermes Aether tests, Ruff, format, mypy, coverage, documentation, build and public-artifact scan with inherited findings disclosed. Required GitHub checks must pass without bypass.

After merge, update the dedicated clean Aether runtime checkout. Refresh Hermes editable metadata only through the reviewed #399 operation. Restart the gateway only if changed loaded modules require it and only at a verified worker-safe boundary. Execute the three issue-specific canaries, close #396/#397/#399, update evidence/work-memory, then remove objective-owned merged branches/worktrees and archive temporary Projects. Preserve active Monitor residue and pre-existing stashes.
