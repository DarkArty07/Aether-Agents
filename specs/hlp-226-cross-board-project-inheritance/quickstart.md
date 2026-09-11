# Verification quickstart — HLP-226 cross-board Project inheritance

All commands run in clean isolated worktrees/checkouts at the exact candidate revision. Do
not run them against or activate them in the loaded editable runtime. Set retries to zero so
a first-attempt failure remains visible.

## 1. Exact RED/GREEN regression

Construct a disposable Git repository, board, and two profile homes:

- creator profile registers Project P;
- the current board metadata binds P to repository R;
- the current Supervisor source task carries P, nonterminal affinity F, and
  `workspace_kind="dir"` with `R/.worktrees/<prior-board-id>`;
- `<prior-board-id>` is deliberately absent from the current board;
- the Supervisor profile Projects registry contains zero Projects.

Call native `kanban_create` for a same-profile, same-flow terminal Supervisor without a
literal workspace override. On the exact fork baseline, assert the observed RED error:

```text
kanban_create: session-affinity tasks require a canonical project_id
```

On the candidate, assert H226C-FR-002 exactly: same Project, same workspace, `dir`, same flow,
`terminal=true`, and correct parent gating/provenance.

## 2. Two-step disposable E2E

From the created terminal Supervisor, call native `kanban_create` for an Implementer with a
fresh worktree request. Run the native dispatcher/workspace resolver. Assert:

- Project P is persisted;
- path is `R/.worktrees/<child-id>` and differs from the shared Supervisor path;
- branch follows the existing deterministic Project convention;
- the worktree exists, its checked-out branch matches the persisted branch, and a read-only
  Git command succeeds; and
- no Project row was added to the Supervisor or Implementer profile registry.

This is the canonical end-to-end acceptance path. A unit test that only constructs a task row
does not replace it.

## 3. Security and preservation matrix

Run focused tests that cover every H226C-FR-004 negative and the existing positive controls:

```bash
HERMES_TEST_FILE_RETRIES=0 pytest -q \
  tests/tools/test_kanban_tools.py \
  tests/hermes_cli/test_kanban_db.py \
  tests/hermes_cli/test_kanban_session_affinity.py
```

If maintained-fork file names differ at implementation time, Supervisor may select the
current equivalent suites but must record the mapping. The matrix must include direct
HLP-226, same-board HLP-226b, the cross-board recurrence, outside/mismatched board repository,
Project conflict, flow/assignee conflict, ordinary scratch, and non-affinity controls.

## 4. Fork static and broader checks

Run the maintained fork's documented complete test path and at least:

```bash
python -m compileall -q hermes_cli tools tests
ruff check hermes_cli/kanban_db.py tools/kanban_tools.py tests
ruff format --check hermes_cli/kanban_db.py tools/kanban_tools.py tests
git diff --check
```

Record exact commands, versions, pass/fail totals, skips, retries, and limits. A failure in a
known baseline is not hidden; show that the objective neither caused nor fixed it.

## 5. Aether reconciliation and full gates

After the reviewed fork commit exists, update the existing portable patch/registry/evidence
surfaces and run the current repository-defined checks, including:

```bash
uv run --frozen python scripts/validate_hermes_patch_reconciliation.py
uv run --frozen python scripts/check_hermes_baseline_drift.py --json
uv run --frozen python scripts/check_documentation.py
uv run --frozen python scripts/check_public_artifacts.py
uv run --frozen ruff check src/aether_agents tests scripts
uv run --frozen ruff format --check src/aether_agents tests scripts
uv run --frozen mypy src/aether_agents
uv run --frozen python -m compileall -q src tests scripts
HERMES_TEST_FILE_RETRIES=0 uv run --frozen python scripts/run_tests.py
uv build
```

The historical full-run baselines identified by the immediately preceding accepted objective
remain separately attributed; they are not a waiver for new failures. Required GitHub checks
must pass. Non-required failures must be inspected and shown equivalent to an unchanged
baseline before a normal merge.

## 6. Final artifact and closeout

At the exact integrated fork and Aether revisions:

1. rerun the canonical two-step E2E;
2. verify the portable patch reconstructs the integrated fork bytes;
3. verify the patch registry and evidence cite exact commits and no private paths/state;
4. verify issue #226 reflects the real merged result rather than only a local patch;
5. verify no live runtime reload/activation, release, deployment, setting, profile, model,
   provider, credential, or unrelated board mutation occurred;
6. classify `release_impact=patch`, `release_action=defer`, `release_channel=none`; and
7. audit objective-owned branches/worktrees after durable merges while preserving unrelated
   active or pre-existing residue.
