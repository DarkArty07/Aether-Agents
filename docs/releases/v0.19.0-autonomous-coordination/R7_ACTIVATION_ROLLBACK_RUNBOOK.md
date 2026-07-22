# R7 Future Activation and Rollback Runbook

## Status and authority

This runbook is **prepared but unexecuted**. R7 is code-complete, default-off, and observational. It does not authorize a pilot, gateway restart, production database migration, real effects, R8, merge, tag, or release. Chris must explicitly approve a separate activation plan while present or while an independently verified recovery channel exists.

Olympus remains the sole ACP process/session lifecycle owner. Harmonia may provide admission, dependency, budget, and evidence decisions in a future hybrid pilot, but it must never spawn, close, cancel, or replace Olympus sessions. `talk_to` remains supported throughout.

## Preconditions for a future pilot

All items must be satisfied in one user-present session:

1. Define one bounded E0/E1-only pilot contract: project, participants, paths, budget, duration, expected evidence, stop conditions, and rollback owner.
2. Replace test/process-local key custody with approved production identity and key custody.
3. Provide shared durable replay and correlation semantics across relevant processes/hosts, with independent security review.
4. Derive authority from trusted live contract, fence, revocation, ledger, and closure state; do not accept caller assertions.
5. Capture a verified backup of every configuration/database that the pilot would modify and test restore in an isolated copy.
6. Record gateway service state, PID, restart count, recent errors, and Telegram connectivity without mutating them.
7. Run the complete disabled compatibility matrix and prove the rollback path performs zero coordination observer/session/store operations.
8. Confirm the old `talk_to` path works before activation.
9. Obtain explicit user approval for the exact config migration and any gateway restart. Approval to test R7 code is not activation approval.

If any prerequisite is absent, stop. Do not improvise a live workaround.

## Planned activation sequence

The future implementation plan must provide the exact commands after the production seam is designed. The safe order is:

1. Stop new admission while leaving Olympus and `talk_to` available.
2. Back up approved config/state paths to a timestamped private location and verify checksums and restore readability.
3. Apply only the reviewed feature-flag/config migration; preserve `enabled: false` initially.
4. Parse configuration and run startup/import checks without restarting the live gateway when possible.
5. If a restart is explicitly approved, perform one bounded restart and immediately verify service health and Telegram connectivity.
6. Enable only the bounded pilot contract, not a global autonomous mode.
7. Observe read-only shadow agreement first; require zero unexpected mismatch before any E0/E1 execution.
8. Execute the smallest reversible pilot unit through Olympus lifecycle ownership.
9. Reconcile effects, session evidence, continuity, latency, errors, and operator burden before another unit.
10. Stop at the first stop condition. Do not widen scope automatically.

No E2–E4 effect is permitted in the initial pilot. No unknown effect may be retried automatically.

## Health checks during a future pilot

After every unit verify:

- Olympus is the only lifecycle owner and every session has one project identity;
- gateway service is active, restart count stable, and Telegram connected;
- `talk_to` open/message/poll/close plus steer/cancel/delegate semantics remain usable;
- ledger/correlation integrity and replay checks pass;
- assignment, participant, session correlation, and technical status match expected evidence;
- `semantic_complete` is never inferred from shadow or transport acknowledgement;
- no unauthorized path, credential, config, or external effect changed;
- latency, storage growth, model/tool usage, mismatches, and manual interventions are recorded;
- no Cotal, NATS, or JetStream dependency appears.

## Stop conditions

Immediately disable new coordination admission and begin rollback if any occurs:

- gateway or Telegram health degrades;
- Olympus lifecycle is bypassed, duplicated, or ambiguous;
- cross-project/session correlation, replay, stale fence, revocation race, or integrity failure;
- unknown or unreconciled effect;
- unexpected config/auth/runtime-state mutation;
- task/session evidence is partial, ambiguous, or cannot be verified;
- clean-run false positive or injected-failure miss exceeds the approved pilot threshold;
- budget, time, or scope limit is reached;
- rollback artifact or recovery channel becomes unavailable;
- the user requests stop.

## Rollback sequence

1. Disable new coordination admission first.
2. Keep Olympus and `talk_to` available for observation and bounded cleanup.
3. Revoke pilot capabilities and reconcile any known/unknown E0/E1 effects before retrying or closing.
4. Close or cancel only the exact pilot sessions through Olympus using their confirmed session IDs.
5. Restore the verified pre-pilot config/state artifacts. Never restore credentials from an unverified copy.
6. Parse restored configuration and verify the coordination flag is absent or `false`.
7. Restart the gateway only if the original activation changed/restarted it and the user has authorized rollback restart.
8. Verify service/Telegram health, five MCP tools, seven `talk_to` actions, project isolation, steering, curation, and cleanup.
9. Verify the disabled path performs zero observer reads, session derivations, and store writes.
10. Preserve the failed pilot ledger/evidence read-only for diagnosis; do not delete history.
11. Record the incident and resulting decision in versioned documentation and `.aether`, then curate context through Ariadna.

## Successful rollback definition

Rollback is complete only when:

- coordination is confirmed disabled;
- the old `talk_to`/Olympus path passes its compatibility matrix;
- gateway and Telegram health match the pre-pilot baseline;
- no second lifecycle owner or autonomous effect path remains;
- all pilot effects are reconciled or explicitly marked unknown for human resolution;
- no production credential or user data was lost;
- evidence and continuity identify the exact stop reason and remaining risk.

## Current evidence versus unproven claims

R7 currently proves isolated compatibility, typed failure detection, disposable restart-safe correlation, and a local ten-scenario benchmark with zero lifecycle/effect calls. It does **not** prove live provider cost savings, production throughput, cross-host identity, distributed key custody, long-duration stability, or safe gateway activation. Those remain decision inputs for a later pilot, not assumptions.