# PDR-0012: Hermes-led Orca swarm boundary

- **Status:** APPROVED
- **Date:** 2026-08-05
- **Owner:** Christopher (DarkArty07)
- **Supersedes:** PDR-0011's requirement to retain a pre-emptive Python decision-plane implementation under `src/aether_agents`; v0.22.0 M1 native-core retention
- **Preserves:** PDR-0011's Olympus source retirement, capability-gap honesty, historical evidence, local-store non-destruction, and runtime-activation gates

## Context

Aether previously depended on ACP and A2A-style coordination. Olympus and its surrounding lifecycle made Hermes the mandatory transport hub for specialist work: process/session ownership, task progression, messages, evidence, cleanup, and result delivery converged through Aether-specific runtime code.

The product target is different. Hermes should open one feature effort, decompose it, and dispatch independent work to several agents through Orca. Workers should execute in parallel, exchange durable Orca messages when useful, ask and reply through the Run, and report completion through their Dispatch. Hermes remains the initiator, product-intent interpreter, active implementer, supervisor, and semantic acceptance owner; it is not the mandatory broker for every worker-to-worker interaction.

Orca's installed public orchestration surface already owns Runs, Tasks and dependency DAGs, Dispatch attempts, supervised worker startup, direct and group messages, ask/reply, `worker_done`, terminals, worktrees, recovery, and cleanup inspection. It explicitly allows all independent Tasks to be created and all independent workers to be started before the coordinator waits.

The v0.22.0 candidate retired the Olympus executable namespace but first moved 3,743 lines of extracted authority, continuity, evidence, review, and inert self-improvement implementation into `src/aether_agents`. That package has no production consumer beyond its own tests, six profile plugin wrappers, setup/update installation, and doctor checks. Retaining it creates a second, disconnected coordination/authority implementation in anticipation of needs that Orca may already satisfy.

## Decision

### 1. Aether is the product layer, not a parallel runtime

Aether owns its product through versioned artifacts and Hermes judgment:

- product vision, requirements, scope, principles, and decisions;
- Hermes behavior, task decomposition, routing, supervision, synthesis, and semantic acceptance;
- Daimon names, roles, profiles, participation policy, and model/provider configuration;
- skills, operational guidance, verification expectations, and protected-effect policy;
- release, activation, deployment, and rollback authority.

These responsibilities do not require a standing Aether Python package merely because their earlier implementation lived in Olympus.

### 2. Orca owns swarm mechanics

The target execution topology is:

```text
user intent
-> Hermes creates or binds one Orca Run for the feature effort
-> Hermes creates independent Tasks and dependency edges
-> Hermes starts all ready independent workers before waiting
-> workers execute in parallel through Orca Dispatches
-> workers communicate through Orca messages, ask/reply, and intentional groups
-> workers report worker_done or escalation
-> Hermes continues its own bounded work, resolves product decisions, and synthesizes
-> exact task results are reconciled into the feature branch
-> Hermes verifies the product outcome and requires explicit cleanup
```

No Aether implementation may duplicate Orca Run, Task, Dispatch, worker, terminal, worktree, message, recovery, or cleanup state.

### 3. One feature branch is the integration line, not necessarily one writable checkout

A feature effort has one integration branch. Parallel writers use conflict-aware placement:

- agents with disjoint, explicitly owned files may run in the current Orca worktree;
- agents that may touch overlapping files use Orca child worktrees derived from the feature effort;
- each Task owns an exact write scope;
- Orca does not infer merge conflicts or file ownership, so Hermes must prevent overlapping writers and reconcile commits deterministically;
- no worker force-pushes, rewrites shared history, or merges/releases independently.

This preserves one product branch while avoiding unsafe concurrent writes to one filesystem checkout.

### 4. Retire the disconnected native core

The v0.22.0 candidate must remove:

- `src/aether_agents`;
- the `aether-agents` Python distribution and `aiosqlite` runtime dependency;
- editable Aether installation from setup/update;
- Aether import checks from doctor;
- all six profile `plugins/aether` wrappers and their activation blocks;
- tests that exist only to preserve identity, contracts, budget, continuity, evidence, effects, review, closure, or inert self-improvement implementation;
- CI/build/release steps that package the removed runtime;
- current-facing documentation and website claims that the native core remains active.

This retirement must not add an Orca adapter, compatibility shim, renamed kernel, or hidden fallback in the same cut.

### 5. Preserve product assets and non-destructive history

The cut retains:

- `home/SOUL.md`, `home/config.yaml.template`, profile SOULs/config templates, skills, skins, and images;
- setup, update, gateway, doctor, and release-governance tooling after removing package-only behavior;
- website and user/contributor documentation after architectural correction;
- PDRs, historical releases, benchmarks, closeouts, and retirement evidence as historical truth;
- `.aether/aether.db`, `.aether/self_improvement.db`, and legacy stores in place and unmodified.

Source-reader retirement does not authorize database deletion, migration, mutation, or automatic import into Orca.

### 6. Future integration code is demand-driven

A future Orca adapter is permitted only after an observed public Orca seam requires product-specific translation that cannot live truthfully in Hermes instructions, configuration, or an existing Orca skill. Any adapter must be:

- minimal and based on the version-matched installed Orca CLI contract;
- free of ACP, A2A, Olympus, Harmonia, and hidden fallback behavior;
- incapable of becoming a second task/message/lifecycle store;
- tested first against the real boundary it translates;
- removable if Orca later exposes the needed behavior natively.

No deleted `aether_agents` module is presumed to be the starting point.

## Consequences

### Positive

- The architecture matches the product intent: Aether defines the team and judgment; Orca runs the swarm.
- Hermes is a semantic coordinator and participant without becoming a mandatory message broker.
- Unused extracted code and its maintenance/test burden disappear.
- Future code is justified by a real Orca integration need rather than inherited Olympus abstractions.

### Negative

- The candidate has no Aether-native continuity writer or self-improvement ledger implementation.
- Existing `.aether` databases become preserved historical/local state until a separately approved consumer exists.
- Profiles launched independently no longer write Aether continuity through a profile plugin.
- A concrete Orca workflow still needs live isolated validation before multi-agent capability can be claimed.

## Rejected alternatives

### Keep `aether_agents` as a future policy kernel

Rejected because it has no active consumer and duplicates concepts already represented by Hermes policy or Orca runtime state.

### Let every worker edit one shared checkout concurrently

Rejected as the default because Orca explicitly does not infer write conflicts. Shared checkout execution is allowed only for disjoint, explicitly owned scopes.

### Delete all scripts, skills, and website code

Rejected because these are active product delivery assets, not the retired ACP/Olympus coordination runtime.

### Implement the Orca adapter during the deletion cut

Rejected because it would hide whether retained abstractions are actually necessary and would conflate source retirement with replacement implementation.

## Validation gates

The correction is complete when:

1. no native Aether runtime package, dependency, profile plugin, editable install, import check, or package build remains;
2. setup still generates the Hermes root config and six profile configs idempotently;
3. current docs describe Hermes + Orca swarm ownership without claiming live activation;
4. historical evidence and local stores remain untouched;
5. repository tests, lint, shell syntax, YAML, release policy, links, and disposable setup/doctor pass;
6. the exact committed candidate is clean and synchronized;
7. Orca integration, live pilot, PR, merge, tag, release, and activation remain separate gates.

## Implementation authorization

On 2026-08-05 the owner clarified the Hermes-led Orca swarm target and directed removal of code that no longer serves it. This authorizes the bounded repository retirement described above, its tests, documentation, commits, feature-branch push, and issue reconciliation. It does not authorize Orca activation, a live multi-agent pilot, destructive data changes, merge, tag, release, deployment, credentials, or spending.

## References

- GitHub issue: #160
- Prior retirement decision: `PDR-0011-orca-substrate-and-olympus-retirement.md`
- v0.22.0 roadmap: `docs/releases/v0.22.0/ROADMAP.md`
- Installed Orca guides: `orca-ide skills get orchestration` and `orca-ide skills get orca-cli`
