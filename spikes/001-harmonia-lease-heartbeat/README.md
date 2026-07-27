# Spike 001 — Harmonia lease heartbeat and terminal cleanup

## Question

Given a Harmonia dispatch protected by a ten-second SQLite lease, when the ACP task remains active beyond the original deadline and later terminates naturally, can the same fenced authority be renewed safely and can a matching terminal observation make `stop` idempotent without manufacturing cancellation?

## Scope

This is a throwaway experiment for [GitHub #107](https://github.com/DarkArty07/Aether-Agents/issues/107). It does not modify production coordination code, activate Harmonia, open ACP, close the issue or claim Gate B/Gate C.

The spike uses:

- the production `SQLiteLedger` lease implementation;
- a deterministic fake nanosecond clock;
- the production `Lease` and `LeaseResult` types;
- disposable SQLite tables for the proposed terminal/cleanup projection.

## Run

```bash
PYTHONPATH=src python spikes/001-harmonia-lease-heartbeat/main.py
```

Optional preserved SQLite artifact:

```bash
PYTHONPATH=src python spikes/001-harmonia-lease-heartbeat/main.py --db /tmp/harmonia-heartbeat-spike.sqlite
```

## Scenarios

| Scenario | Given / When / Then | Result |
|---|---|---|
| Renewable fence | Given an active lease, when heartbeat runs at second 8, then execution remains authorized after the original second-10 deadline with the same epoch and token | PASS |
| Terminal cleanup | Given trusted matching terminal evidence, when the renewed lease later expires and `stop` is called twice, then one cleanup row and zero cancel effects exist | PASS |
| Active stop | Given an active non-terminal session, when `stop` is called twice, then intent is durable before one external cancel effect and neither duplicates | PASS |
| Missing evidence | Given an expired lease without terminal evidence, when `stop` runs, then it returns `reconciliation_required` and performs no effect | PASS |
| Adversarial fencing | Given a foreign token, replaced epoch or mismatched session, when renewal/finalization is attempted, then it remains rejected/fail-closed | PASS |
| SQLite integrity | Given all scenarios, when `PRAGMA integrity_check` runs, then the result is `ok` | PASS |

Exact machine-readable output is preserved in [`result.json`](result.json).

## Verdict: VALIDATED

The selected mechanics are feasible:

- `renew_lease()` can extend the same authority without changing epoch or token;
- an authority object carrying the original expiry remains safely checkable because the ledger validates and returns the current persisted lease row by scope/resource/epoch/token;
- trusted terminal evidence can authorize idempotent cleanup after the dispatch lease expires;
- active cancellation can retain durable-intent-before-effect ordering;
- expired authority without evidence remains fail-closed;
- foreign tokens, replaced epochs and mismatched sessions remain rejected.

### What worked

- All five behavioral scenarios passed in one executable run.
- Two terminal `stop` calls produced one cleanup row and no cancel effect.
- Two active `stop` calls produced one intent and one external cancel effect.
- The same epoch/token crossed the original deadline after renewal.
- SQLite integrity remained valid.

### What did not prove

- No asynchronous heartbeat loop was implemented.
- Terminal rows are experimental SQLite projection rows, not authenticated production kernel events.
- No ACP manager, restart recovery or live session was exercised.
- No contract revocation race was executed concurrently; replacement and foreign-authority checks were deterministic sequential scenarios.
- The spike does not choose the final event names or public state vocabulary.
- The spike is not production code and does not resolve #107.

### Surprise

A dispatch envelope does not need mutation after renewal: production `check_lease()` uses its stable epoch/token to fetch and validate the newer persisted expiry. This lets a heartbeat preserve the immutable authority identity while extending only the lease row.

### Recommendation for the real build

Proceed with the provisional design in [`DECISION.md`](DECISION.md), then implement it test-first in production code. Keep the spike disposable after the production regression suite covers the same invariants.
