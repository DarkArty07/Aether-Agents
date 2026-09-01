# Lifecycle

Aether uses two routes. Neither route is selected by a classifier, score, fixed workflow state, or tool availability.

## Bounded direct route

Morfeo may complete an understood, bounded operational objective directly when its consequences are inspectable and the objective does not gain proportionate value from decomposition or independent review. Direct work is verified from actual commands, state, and diffs; it does not manufacture a board card or Objective Contract merely for ceremony.

## Pipeline route

Substantial or uncertain work moves through these durable boundaries:

1. Morfeo creates and finalizes one project-bound [Objective Contract](objective-contracts.md).
2. `prepare_handoff` verifies the final contract is reachable from Git `HEAD` and returns opaque root-card routing data only after provisioning the contract-version execution board.
3. Morfeo creates one Supervisor root card on that returned board and project binding.
4. Supervisor performs executability analysis and makes the contract's `tasks.md` the breakdown of record.
5. Supervisor creates independently testable Implementer units with parent links and every shared decision they need.
6. Each Implementer works in an isolated Git worktree, verifies its bounded result, and records completion evidence.
7. Supervisor reviews work it did not author, integrates in dependency order, and performs the integrated verification.

Hermes owns generic card status, retry, reclaim, review, worktree, and dispatcher behavior. Read the [Hermes documentation](https://hermes-agent.nousresearch.com/docs/) for those generic interfaces; this guide documents the Aether-specific role and handoff rules only.

## Failure evidence and recovery boundaries

The durable unit is the card, not a worker process. A retry/reclaim preserves the unit but does not prove that an interrupted external effect did not occur. A crash can consume an attempt/failure budget; stale-claim reclaim and application failure are not interchangeable. Completion reports must state what changed, actual verification, and the remaining material risk.

The current source includes a disposable qualification laboratory, but deterministic preparation is not live reliability or release evidence. The model/provider-backed path remains separately gated. See [Observation](observation.md) and [limitations](../reference/limitations-and-troubleshooting.md).
