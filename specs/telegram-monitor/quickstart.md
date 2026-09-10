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

## 4. Private live qualification — isolated laboratory

D13's [qualification-isolation.md](qualification-isolation.md) is normative for this
phase and supersedes the previous shared-installation synthetic-scope approach.

```bash
uv run --frozen python scripts/qualify_telegram_monitor.py --json
# PRIVATE_EVIDENCE is an approved private directory outside every Git worktree.
uv run --frozen python scripts/qualify_telegram_monitor.py --live \
  --wait-hourly-boundaries 2 --output "$PRIVATE_EVIDENCE/telegram-monitor-live.json" --json
```

Without `--live`, zero model/sender calls. Before live effects verify candidate/runtime
compatibility, isolated mutable paths, output privacy and the unchanged approved route
and destination. No CLI token/model/recipient overrides or persisted credential copies.
The supported native scheduler runs only the private lab profile; no receiver, dispatcher,
custom scheduler or permanent service. The production gateway and projects are untouched.

Perform one bounded initial smoke, then two actual hourly active cuts and a subsequent
native idle cut. Native synthetic source records cover the original identity/lifecycle,
D12 narrative corpus, blocked/unchanged, short-lived final and direct-work scenarios.
Keep projects registered after their work finishes; unreadable source state is not idle.
Manual triggering never substitutes for hourly evidence. Preserve existing pickup,
lateness, inference/fallback and timeout bounds. Do not retry live calls indefinitely.

Stop the lab scheduler/job cooperatively and retain private receipts/root as declared
objective evidence; do not attempt shared-registry restoration or automatic test deletion.
Use background completion and heartbeats for the wait, independently of the test TUI.
No lab result alone establishes production activation or final acceptance.

## 5. Review, integration and activation

Supervisor independently verifies code, AC/test mapping, real receipts and exact candidate
before integration. Use one normal PR with all repository checks green, preserve unit
commits and do not bypass/rewrite history. Before local activation, record prior monitor
configuration/job identity/package source and a reversible rollback path using supported
product lifecycle/native interfaces. Rollback disables only the feature and preserves
monitor receipts and all unrelated work; no destructive database cleanup.

After the independently accepted laboratory, verify the exact candidate on the existing
production gateway with the full D3 real scope and a first normal hourly report/ack.
Do not copy lab job IDs, cursors, source records or acceptance state into production; do
not hide real work to force idle. If there is no reportable real work, keep first-delivery
acceptance pending rather than fabricate an outcome. A cached incompatible gateway
requires an explicit safe-activation resolution, not interruption of active work.

On activation the user must see `aether monitor status` accurately report automatic/off,
next due, scope and last delivery, and observe actual intended Telegram output. Retire the
single temporary build-progress cron only after matching its exact objective identity
from native `cronjob list` and after permanent first delivery is verified, or at definitive
terminal stop. Preserve all unrelated jobs. Do not infer full closeout from the Supervisor
root's decomposition-done status. Reconcile issue #367 and audit objective-owned vs
pre-existing branches/worktrees/stashes. Release: minor additive impact expected; defer,
channel none; no tag/package publication for this objective.
