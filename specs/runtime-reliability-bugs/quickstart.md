# Verification — approved runtime reliability bugs

This is the runnable verification path for the [specification](spec.md) and [plan](plan.md). Commands below are prescribed verification, not claims that implementation tests have already passed. Morfeo's intake evidence consists only of source inspection and isolated synthetic-structure probes; implementation evidence is produced by the pipeline.

## Inputs and isolation

Use two clean managed source checkouts: Aether at the contract base (including these design artifacts), and `DarkArty07/aether-hermes` at `c185ee3bb5b6d609241432fd123c16143f065987`. The second is an explicitly authorized secondary repository, not the legacy editable runtime. Resolve `AETHER_CHECKOUT`, `FORK_CHECKOUT` and `HERMES_PYTHON` from actual provisioned paths at execution time and record them privately; no operator paths belong in public artifacts. The selected interpreter must already provide Hermes test dependencies. Use the fork's documented `.venv`/`venv` discovery; if necessary a reversible workspace-local symlink may point to the existing environment, with no environment/package modification. Verify imports resolve to the candidate source, not its installed editable checkout, before testing.

Do not run native Kanban tools, canaries or imports under the worker's inherited live-board environment. From an outer stdlib-only launcher, use the existing `isolated_hermes_env()` boundary for Aether probes before child imports and explicitly seed only synthetic configuration/credentials. The launcher must itself not import native Kanban before isolation. Use test-side injection of a poisoned mapping to exercise the baseline without touching actual inherited DBs. All SQLite witness boards are generated laboratory fixtures. No real messaging target, native root subscription, remote dispatch or production `state.db` is a fixture.

For comparison, create an unchanged fork baseline worktree and a candidate worktree. The same new regression tests must run against both with identical dependencies/configuration. The test harness may block a real loopback HTTP request using Events/Barriers, but must never sleep and infer ordering from elapsed time alone. No live LLM traffic or provider auto-discovery. Label deterministic HTTP replies and credentials as fixtures.

## Sterile outer launcher for every test command

The command groups below must run in a child with a clean test environment, not directly with inherited worker identity. Resolve `AETHER_EXACT_HERMES_CHECKOUT` to the already authenticated legacy release checkout (not the maintained candidate), then use this shell function in the managed test session:

```bash
: "${AETHER_EXACT_HERMES_CHECKOUT:?resolve the exact release checkout first}"
LAB_ROOT=$(mktemp -d)
mkdir -p "$LAB_ROOT/user" "$LAB_ROOT/hermes" "$LAB_ROOT/workspaces"
lab_run() {
  env -i PATH="$PATH" HOME="$LAB_ROOT/user" \
    LANG=C.UTF-8 TZ=UTC PYTHONDONTWRITEBYTECODE=1 \
    HERMES_HOME="$LAB_ROOT/hermes" \
    HERMES_KANBAN_DB="$LAB_ROOT/kanban.db" \
    HERMES_KANBAN_WORKSPACES_ROOT="$LAB_ROOT/workspaces" \
    XDG_STATE_HOME="$LAB_ROOT/xdg-state" XDG_DATA_HOME="$LAB_ROOT/xdg-data" \
    AETHER_EXACT_HERMES_CHECKOUT="$AETHER_EXACT_HERMES_CHECKOUT" \
    HERMES_TEST_FILE_RETRIES=0 "$@"
}
```

Prefix each test/static command below with `lab_run` (for example `lab_run uv run --frozen python scripts/check_documentation.py`). For the fork runner use `lab_run scripts/run_tests.sh ...`; the function already sets its retry policy. This sterile outer launcher protects the baseline run too; poisoned-marker tests then add synthetic values inside their own child fixtures. No secret/config variables are inherited. Use already provisioned dependencies; do not weaken isolation or import live credentials when a dependency is absent. Keep the sandbox and failed output until evidence is captured, then clean only owned test artifacts. This is test setup, not a new production environment policy.

## Aether gates

From the Aether candidate, use its canonical wrapper and existing locked dev environment:

```bash
uv run --frozen python scripts/check_hermes_baseline_drift.py --json
uv run --frozen python scripts/check_documentation.py
uv run --frozen python scripts/run_tests.py -- -q --tb=short tests/test_e2e_harness.py tests/test_observation_qualification.py
uv run --frozen python scripts/run_tests.py -- -q --tb=short
uv run --frozen ruff check src/aether_agents/lab/runner.py tests/test_e2e_harness.py
uv run --frozen ruff format --check src/aether_agents/lab/runner.py tests/test_e2e_harness.py
git diff --check
```

Add any actually changed neighboring file to lint/format and affected test selection. The canonical Aether wrapper authenticates the existing release-locked Hermes baseline; do not point `--checkout` at a non-matching maintained fork or weaken that verifier. Aether's existing exact-baseline suite is a preservation gate. Separately, B267/native integrated probes must use the exact maintained-fork candidate under the isolated launcher and record that revision; the two kinds of evidence are not interchangeable.

The existing GitHub policy, observation qualification, integrated coverage floor, static checks and build checks remain required. Graphify tests already in those checks may execute as preservation coverage; no Graphify implementation or gate changes are authorized. Replay documentation/link gates in a clean checkout/archive, not the provisioned root containing ignored runtime dependencies (#323). Do not patch #323 as part of this objective. Known #329/#349/#352 failures must be distinguished through unchanged-baseline evidence, not hidden by retries or altered timeouts.

## Maintained-fork gates

Always use the fork's `scripts/run_tests.sh`; do not call pytest directly. It supplies per-file process isolation and credential-free CI parity. Use the already provisioned Python selected by the runner and disable file retries for unambiguous RED/GREEN. Confirm candidate source path before each baseline/candidate run.

From the fork baseline, then candidate:

```bash
HERMES_TEST_FILE_RETRIES=0 scripts/run_tests.sh tests/agent/test_kanban_stop.py
HERMES_TEST_FILE_RETRIES=0 scripts/run_tests.sh tests/agent/test_error_classifier.py
HERMES_TEST_FILE_RETRIES=0 scripts/run_tests.sh tests/agent/test_auxiliary_client.py tests/agent/test_auxiliary_client_resolve_dedup.py
HERMES_TEST_FILE_RETRIES=0 scripts/run_tests.sh tests/run_agent/test_background_review.py tests/run_agent/test_background_review_cache_parity.py tests/run_agent/test_background_review_cost_controls.py tests/test_background_review_session_isolation.py
HERMES_TEST_FILE_RETRIES=0 scripts/run_tests.sh tests/agent/ tests/run_agent/
git diff --check
```

Add new regression files and native DB/tool tests affected by B304; the exact existing native names are discovered from the checked-out test tree, not invented. New tests for each Bxxx are mandatory when not already covered. The broad affected directories must include the new tests, with zero deselected-by-mistake coverage. Capture first failure and first successful candidate runs; do not call pass-on-retry a deterministic fix. Preserve platform-specific tests/markers rather than pretending Linux proves Windows/macOS behavior.

Inherited fork Actions are disabled under `AETHER_FORK.md`; report this as NOT RUN, not green CI. Do not enable workflows or modify settings to solve it. Independent review and the documented local runner are the authorized fork merge evidence; any actual protected required-check refusal is a real blocker, not permission to bypass.

## Per-behavior integrated matrix

| Requirement | Positive exercise | Required negative/preservation controls |
| --- | --- | --- |
| B267 | Real isolated subprocess/native create/claim/complete, deliberately poisoned env, explicit sandbox DB | Separate witness DB unchanged; all ambient worker/session/project/tenant/delegation markers cleared; unrelated config preserved; symlink/escaped destination rejected before writes; parent env untouched |
| B304 | Native task/run completes once, then validator receives missing transcript and reads same-run durable proof | Wrong board/task/run/event; unreadable DB; conflicting transcript; reopened/new execution; repeated read has no writes/events/notifications; existing review/block transitions retain behavior |
| B295 | Local HTTP exhausted primary then explicitly configured healthy secondary, capture real requests and response | Generic 503 overload unchanged; overflow unchanged; no fallback/all fail bounded; undeclared candidate never contacted; completed local tool sentinel not repeated |
| B301 | Actual SDK Responses adapter HTTP with per-request metadata, primary retry and configured secondary | Sync/async, streaming/non-streaming supported routes; mapping/defaults immutable; subsequent request clean; distinct destination auth; no primary auth/cookie/key copied across destinations |
| B292 | Both named-provider spellings, bare model, temporary key_env/api_mode, direct and real configured-fallback requests | No unrelated global key; anonymous/built-in compatibility; missing named config is not silently treated as another provider; unchanged baseline may already pass |
| B294 | Real local request with event-controlled review start/in-flight/finish; intentional new-turn and stop boundaries; foreground response | Assert agent/client/request ownership, no review-to-parent abort, pre-admission cancellation means no request, identity-qualified cleanup, stable cache/session behavior and intentional stop propagation |

For B292, unchanged-baseline success in the integrated matrix permits tests/evidence-only closure as already working. For B294, unchanged-baseline success permits an explicit not-reproduced disposition with the issue retained open, not a speculative implementation or a claim that history is repaired. A different discovered cause returns to Morfeo's design boundary.

## Evidence format and review

Record integrated evidence under `specs/runtime-reliability-bugs/evidence/` and keep raw large logs as native task attachments or ignored private execution artifacts. Use one concise Markdown evidence report with a row per Bxxx and the exact commands, source commits, baseline result, candidate result, disposition, review and omissions. If machine-readable evidence is useful, a JSON object with `source_revisions`, `commands`, `results_by_issue`, `review`, `github`, `release` and `residue` is sufficient; examples here are not a requirement for a new result framework. No secrets, raw operator paths, private model responses or invented receipts.

Reviewer must independently inspect the final candidate and exercise the fragile controls (read-only same-run proof, poisoned environment, cross-destination authentication, and review cancellation ownership). Unit self-report does not substitute for receipt review. Supervisor owns `tasks.md` coverage and integration review, not Morfeo.

## Closeout and rollback

1. Preserve each accepted implementation commit. Open routine branch PRs against maintained fork `aether-main` and Aether `main`; link existing selected issues and evidence.
2. Verify the fork PR merge through the normal allowed path using local evidence and independent review; do not claim disabled Actions passed. If actual required protections cannot be satisfied, stop that merge visibly without bypass.
3. Include the exact fork merge SHA, downstream ledger and test/rollback/retirement evidence in the Aether PR. Pass Aether's existing required checks, then verify its merged commit and post-merge status.
4. Reconcile issue dispositions precisely: fixed, qualified already-working, or #294 retained open/not reproduced. Do not close an unresolved historical incident as fixed.
5. Audit local/remote branches, worktrees and stashes; remove only this objective's proven merged resources through normal reversible-safe cleanup, preserving all pre-existing/unknown/concurrent state. Never infer remote existence from a stale tracking ref.
6. Report `release_impact=patch` only with compatibility evidence, `release_action=defer`, `release_channel=none`. No runtime installation/reload, live data changes or package/tag release. A later activation objective requires its own canary and authority. Before activation, rollback is an ordinary revert of this objective's isolated source commits, not an old database restore.
