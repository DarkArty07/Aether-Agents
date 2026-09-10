# Telegram Monitor — executable verification path

This is the required path for the future implementation, not a record of tests already
passed. Run from the assigned project worktree. Commands below that target proposed
files/surfaces become runnable when implemented; their absence is an unmet deliverable,
not permission to replace evidence with samples. `spec.md` owns acceptance.

## Clarification for MON-03 semantic verification

`spec.md` D12 owns verification allocation, correcting the repeated synonym-loop
interpretation of plan §5. Unit tests reject mismatched typed status, cross-item/unknown
refs, provenance promotion, invalid shape/size and unsafe source data. They accept
legitimate partial-success/pending-review prose without semantic word heuristics. Keep
prior adversarial prose examples as the quality-case corpus, not an impossible pure
regex truth oracle. Existing live Morfeo qualification includes contradictory worker
completion, forecasts, word-based time and malicious instructions; compare actual output
with authoritative state/evidence and report case outcomes. No new classifier/provider,
extra normal hourly inference or unlimited retries. A failed live case remains a failure.

## 1. Baseline and safety

1. Record `git status --short --branch`, candidate/base SHAs, root `AGENTS.md`, and the
   exact resolved Hermes source/version. Preserve concurrent dirty work and native jobs.
2. Use the provisioned locked development environment (`uv sync --frozen` if required),
   not global package installation. Read CONTRIBUTING.md and `.github/workflows/policy.yml`.
3. Native-boundary tests use disposable Hermes homes, boards and explicit scope/session
   fixtures with complete isolation of inherited `HERMES_KANBAN_*` values through the
   existing documented test isolation helper. Never exercise fixtures against live boards.
4. Existing Aether public locked-Hermes tests remain authoritative for their matrix.
   The installed maintained fork is separately qualified for monitor-specific hooks;
   do not claim an installed fork probe proves the public release baseline or change
   the locked baseline as an incidental convenience.

## 2. Focused executable tests (TDD)

Implement these stable feature test paths; internal test names are local freedom:

```bash
uv run --frozen pytest -q tests/test_telegram_monitor_state.py
uv run --frozen pytest -q tests/test_telegram_monitor_sources.py
uv run --frozen pytest -q tests/test_telegram_monitor_runtime.py
uv run --frozen pytest -q tests/test_telegram_monitor_delivery.py
uv run --frozen pytest -q tests/test_telegram_monitor_cli_plugin.py
```

| Evidence | Required behaviors | Acceptance |
| --- | --- | --- |
| state | enrollment, immutable ids, replay, direct short-lived final, origin grouping, manual-off race, no runtime-state rewrite | AC-1,2,3,4,7 |
| sources | two projects with colliding display names, two sessions per project, one multi-worker contract, direct no-contract, no activity, blocked/triage/review, stale and unsafe bindings | AC-3,4,5,6 |
| runtime | one idempotent cron, pre-gate before inference, cron model route unchanged, hour boundaries/DST/restarts, cron self-exclusion, enable/disable/now/status/history/scope | AC-1,2,3,7,8 |
| delivery | known failure, bounded retry, accepted and uncertain acknowledgments, multipart partial failure, no double send path, source-id header is not LLM authored, fallback labeling | AC-5,6,7 |
| CLI/plugin | parser/tool schemas, malformed inputs, portable state paths, installer resources and plugin surface, unavailable capability diagnostics, docs registry | AC-1,8 |

Secret/private-transcript canaries in fixtures must not appear in the generated snapshot,
model prompt, message or public artifacts. Report rows and evidence links must correspond
to the correct project/objective; no last-session global fallback is acceptable.

## 3. Repository verification

```bash
uv run --frozen python scripts/run_tests.py
uv run --frozen python scripts/check_documentation.py
uv run --frozen python scripts/check_hermes_baseline_drift.py --json
uv run --frozen mypy src/aether_agents
uv run --frozen ruff check src tests scripts/check_documentation.py scripts/qualify_telegram_monitor.py
uv run --frozen ruff format --check src tests scripts/check_documentation.py scripts/qualify_telegram_monitor.py
uv run --frozen python -m compileall -q src tests scripts/qualify_telegram_monitor.py
uv build
uv run --frozen python scripts/check_public_artifacts.py --root .
git diff --check
```

Use the repository's exact full static file list and package-artifact arguments from the
current policy workflow at integration; the focused command above does not replace those
checks. Run the unchanged integrated coverage gate/environment declared in policy.yml
(including isolated optional components); do not lower the 78% configured coverage floor.
Add every new non-spec tracked path to the existing literal manifest rather than changing
its policy or duplicating a registry. Candidate-caused regressions must be fixed; record
pre-existing failures with baseline comparison instead of silently skipping them.

## 4. Private live qualification

Implement `scripts/qualify_telegram_monitor.py` with explicit `--live`, `--json`,
`--output <private-path>` and `--wait-hourly-boundaries 2` options. Without `--live` it
must not send messages or invoke an LLM. It resolves only the already provisioned runtime,
Morfeo route and existing configured Telegram conversation, never accepting a token or
creating credentials. Native environment choices remain private invocation context, not
version-controlled defaults. Preserve the exact scenario/receipt correlations privately.

Before the long qualification, run the deterministic suite and one owner-authorized
initial native model+transport smoke. Then:

```bash
# $PRIVATE_EVIDENCE is an operator-selected protected directory outside the repository.
uv run --frozen python scripts/qualify_telegram_monitor.py --live \
  --wait-hourly-boundaries 2 --output "$PRIVATE_EVIDENCE/telegram-monitor-live.json" --json
```

The harness is bounded and never introduces a second recurring scheduler. It verifies:

1. Native job is idempotently installed under Morfeo with `0 * * * *`; manual off persists.
2. One synthetic monitored scope, with honest synthetic labels, is sourced from native
   isolated artifacts. Cover two project identities and originating sessions, a pipeline
   root/child boundary, direct no-contract work, and a short-lived completion. No arbitrary
   live projects are enrolled by the test. It must exercise the shipped source adapter,
   not feed handcrafted successful provider/Telegram responses into the main path.
3. Actual native scheduler crosses two wall-clock hourly boundaries with recorded due,
   capture, narration and acknowledgment times; close the originating test TUI and retain
   the existing gateway. A manually triggered run is not a replacement for this evidence.
4. Each active cut invokes at most one narrative; actual configured Morfeo route and native
   Telegram acknowledgment/message identity are recorded privately. Header remains correct.
5. After a confirmed final delivery, a subsequent native/direct precheck with genuinely
   empty monitored scope returns the silent wake gate and starts no model call. Fault cases
   use deterministic adapters, never induced failures in the owner's real network/service.
6. Restore the previous scope and other jobs; retain the accepted production monitor only
   after review. Do not kill active user agents or restart unrelated runtime services.
7. Publish only a sanitized evidence summary containing source revisions, timings/counts,
   case results and qualified scope; private chat/message/session handles stay in the
   protected local receipt. Telegram acceptance is not proof of human reading.

For long waiting, use native background/process completion and board heartbeat evidence;
do not discard progressing workers due to duration. If model/network/gateway is unhealthy,
report exact failed prerequisites and preserve the candidate without fabricating success.

## 5. Review, integration and activation

Supervisor independently verifies code, AC/test mapping, real receipts and exact candidate
before integration. Use one normal PR with all repository checks green, preserve unit
commits and do not bypass/rewrite history. Before local activation, record prior monitor
configuration/job identity/package source and a reversible rollback path using supported
product lifecycle/native interfaces. Rollback disables only the feature and preserves
monitor receipts and all unrelated work; no destructive database cleanup.

On activation the user must see `aether monitor status` accurately report automatic/off,
next due, scope and last delivery, and observe actual intended Telegram output. Retire the
single temporary build-progress cron only after matching its exact objective identity
from native `cronjob list` and after permanent first delivery is verified, or at definitive
terminal stop. Preserve all unrelated jobs. Do not infer full closeout from the Supervisor
root's decomposition-done status. Reconcile issue #367 and audit objective-owned vs
pre-existing branches/worktrees/stashes. Release: minor additive impact expected; defer,
channel none; no tag/package publication for this objective.
