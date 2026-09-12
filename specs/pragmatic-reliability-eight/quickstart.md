# Verification quickstart

Resolve exact nodes from the implementation diff; commands below define minimum lanes, not invented test names. Record command, candidate revision, result and evidence producer. Scrub inherited `HERMES_KANBAN_*`, delegated-child and outer session selectors from isolated test processes.

## Focused Aether gates

```bash
uv sync --frozen
uv run --frozen pytest -q \
  tests/test_objective_contracts.py \
  tests/test_same_card_phase_predicates.py \
  tests/test_hermes_patch_reconciliation.py \
  tests/test_observation_qualification.py \
  tests/test_public_artifacts.py
uv run --frozen ruff check src/aether_agents tests scripts
uv run --frozen ruff format --check src/aether_agents tests scripts
uv run --frozen mypy src/aether_agents
uv run --frozen python scripts/check_documentation.py
uv run --frozen python scripts/check_public_artifacts.py
```

Add new focused nodes for #372/#385/#388/#393 and run them RED against the exact pre-fix source, then GREEN against the candidate. A test expected to exercise a maintained-fork patch must use an authenticated disposable fork/baseline candidate; do not import unpatched upstream and expect downstream behavior.

## Maintained-fork gates

Against a clean worktree of the exact reviewed maintained-fork revision:

```bash
python -m pytest -q <cron script-root tests> <cron origin/cwd tests>
python -m pytest -q <kanban review and worker-guidance tests>
python -m pytest -q <neighboring cron/session/kanban suites>
python -m ruff check <changed Python paths and tests>
```

Generate portable patches from reviewed commits, verify `git apply --check` against each declared base, compute digests through repository tooling and run the patch reconciliation suite. Inspect current upstream separately for every retirement conclusion.

## Full Aether gates

```bash
uv run --frozen pytest -q --cov=aether_agents --cov-report=term-missing
uv run --frozen python scripts/run_tests.py
uv build
```

Run the GitHub Python 3.11/3.12/3.13 policy and observation-qualification matrix. Required checks must be green without bypass. If a failure is inherited, prove it on the exact base; #403 is the only pre-authorized incidental blocker in this objective.

## Runtime canaries

- **#357:** the exact `test_real_plugin_context_captures_tool_and_api_then_unloads_every_hook` lane passes on Python 3.13 in the candidate and post-merge `main`; report other workflow failures separately.
- **#372:** create a disposable profile with a uniquely fingerprinted script in that profile's scripts root. Create/update, lifecycle scan and fire resolve the same inode/content; default-root decoy and traversal/symlink negatives are untouched/refused.
- **#385:** native transitions reject missing/self reviewer without row/event/run mutation and accept explicit Supervisor. After activation, one disposable worker card that has only a terminal integration child emits `review_requested` before any completion; Supervisor claims and decides it.
- **#388:** a disposable cron with explicit workdir produces a session row bound to that Git root. A missing/NULL/invalid binding makes every Objective Contract mutation action fail with the stable workspace error and leaves primary/drafts/finals unchanged.
- **#393:** one owner-originated one-shot cron creates a disposable no-op root. Its create receipt reports subscription, the exact origin subscription exists, terminal notification is consumed once by that origin, and another TUI/unattached cron receives nothing.
- **#396:** exact contract root plus child transitions appear in fresh observation for the provisioned board/project; unrelated board state is absent.
- **#397:** writer probe changes only disposable state; selected live-board hash and row counts remain stable.
- **#399:** all provisioned interpreters pass `python -I` origin/import checks without `PYTHONPATH`; source bytes/status are unchanged and a forced second-interpreter failure restores first-interpreter metadata.
- **#403:** tracked source, built wheel and sdist contain no operator path/destination; tombstone digest and historical locator validate.

## Closeout

Close an issue only with its exact criterion and revision. Update `HERMES_LOCAL_PATCHES.md` and structured patch evidence, then update project knowledge/work memory where available. Audit objective-owned branches, worktrees, stashes, temporary boards/jobs and test homes; preserve unrelated residue and the active Monitor flow.
