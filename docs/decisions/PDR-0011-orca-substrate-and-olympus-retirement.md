# PDR-0011: Orca execution substrate and progressive Olympus retirement

- **Status:** APPROVED
- **Date:** 2026-08-03
- **Owner:** Christopher (DarkArty07)
- **Supersedes:** The assumption that Olympus, ACPManager, Harmonia, or the v0.19.x kernel must remain Aether's future execution substrate
- **Superseded by:** None

## Context

Aether's product identity is not its current orchestration implementation. Aether owns product intent, Hermes, Daimon roles and personalities, product authority, requirements, policies, continuity, acceptance, and governance. Olympus currently bundles those concerns with generic process spawning, ACP session lifecycle, terminal observation, coordination ledgers, leases, dispatch, messaging, and cleanup.

The v0.19.x work proved a bounded deterministic lifecycle, not a general coordination runtime. The later maintenance candidate correctly removed unconsumed experiments, but the maintained Olympus package on canonical `main@2b326f05a36cbb77a9bf9475ef914be6f49d886d` still contains 45 Python modules and 19,589 source lines. Its largest remaining responsibilities duplicate lifecycle and orchestration capabilities now available through Orca.

Orca provides Runs, Tasks, Dispatches, supervised workers, durable messages, worktrees, terminals, recovery, and a user interface. It does not own Aether's product meaning, participant policy, semantic acceptance, continuity, protected-effect authority, or Ariadna curation. It is therefore a candidate execution substrate, not a replacement product and not an acceptance authority.

The owner approved `v0.22.0` as the architectural cleanup increment that progressively removes unnecessary code, beginning with Olympus, while incorporating Orca. The migration remains inside the existing Aether repository. Version-order reconciliation for any unreleased `v0.21.0` candidate work is a separate release-governance gate; it does not change the approved `v0.22.0` capability boundary.

## Decision

### 1. v0.22.0 is the cleanup and execution-substrate transition

`v0.22.0` owns the progressive retirement of Olympus and the introduction of an Orca-backed execution path.

This is not permission to delete the package in one cut. Each removal must follow:

```text
characterize current behavior
-> establish the Aether-owned replacement contract
-> implement or bind the replacement
-> prove affected-path parity
-> switch the active consumer
-> prove rollback and cleanup
-> retire the now-unreachable legacy slice
```

A passing Orca command is not parity evidence by itself. The replacement must preserve the applicable Aether authority, isolation, continuity, evidence, and cleanup contract.

### 2. Aether remains the product and decision plane

Aether retains ownership of:

- user intent and product requirements;
- Hermes task contracting and routing decisions;
- Daimon identity, role, profile, model, provider, and participation policy;
- canonical `PROJECT_ROOT` and profile isolation;
- protected-effect authorization;
- budgets and material compromise decisions;
- evidence requirements and semantic acceptance;
- project continuity, `.aether`, and Ariadna;
- release, activation, deployment, and rollback authority.

Orca must not infer or redefine these values.

### 3. Orca is a replaceable execution substrate behind an Aether adapter

Orca may own:

- Run, Task, and Dispatch persistence;
- worker, terminal, and worktree lifecycle;
- supervised messages, questions, escalation, and completion delivery;
- local and approved remote runtime placement;
- terminal and browser presentation;
- operational recovery and runtime UI.

Aether must integrate these capabilities through a stable adapter. Product code and profiles must not depend on every Orca internal field or undocumented implementation detail.

The initial adapter must be local, pinned, fail-closed, JSON-based, and reversible. It must bind every operation to an exact project root, Aether execution contract, Run, Task, Dispatch attempt, and cleanup receipt.

### 4. Olympus becomes frozen legacy

No new product capability should be implemented inside Olympus unless it is strictly required to preserve behavior during migration or to fix a defect blocking a safe cutover.

The remaining code is classified as one of:

- **PRESERVE:** product meaning or evidence retained without behavioral change;
- **REWRITE:** Aether-owned behavior moved behind a non-Olympus package boundary;
- **REPLACE:** generic runtime behavior supplied by Orca through the adapter;
- **RETIRE:** behavior with no approved future consumer;
- **BLOCKED:** code that cannot be removed until dependent replacement gates pass.

The versioned inventory at `docs/releases/v0.22.0/OLYMPUS_RETIREMENT_INVENTORY.md` governs those classifications.

### 5. Ariadna and continuity are extracted, not deleted

Ariadna remains Aether's continuity, context, memory, and curation capability. The following must survive Olympus retirement:

- `.aether/aether.db` and its current continuity meaning;
- `CONTEXT.md` curation and validation;
- hot-state, session, decision, issue, and file-change continuity;
- project-scoped hooks and fail-closed project identity;
- the `aether_status`, `aether_update`, and `aether_curate` product capabilities;
- Ariadna's profile, role, and curation criteria.

Their ACP/Olympus invocation and import paths are implementation details to be replaced.

### 6. Historical evidence and legacy stores are preserved read-only

The v0.19.0, v0.19.x, and v0.20.0 release evidence remains historical truth. References to retired Olympus paths inside versioned historical reports must not be rewritten as if those files never existed.

Before deleting readers or schema code, v0.22.0 must inventory and classify:

- `.aether/aether.db` — preserve in place;
- `.aether/self_improvement.db` — preserve and move its implementation boundary;
- `.aether/.consulting/consulting.db` — inspect, export or archive if present, then retire;
- `$AETHER_HOME/.olympus/olympus_v3.db` — freeze and archive read-only after Orca parity;
- `$AETHER_HOME/.olympus/projects/*/coordination-v0.19.1.sqlite` — freeze as historical coordination evidence;
- PID-scoped `.olympus_session.*`, `.olympus_db_path.*`, and `.aether_home.*` files — remove only after no active process can consume them.

No destructive data migration is implicit in this decision.

### 7. Removal is performed as independently reversible cuts

The final `src/olympus_v3` package deletion is the last source cut, not the first. Earlier cuts extract Aether-owned behavior and replace generic lifecycle consumers.

A cut is admissible only when:

1. its current consumer set is known;
2. its behavior or irrelevance is characterized by tests;
3. replacement behavior is independently exercised;
4. active configuration no longer points at the legacy path;
5. no live legacy process or write authority survives;
6. rollback restores the prior path without data loss;
7. residual imports and executable references are zero outside preserved historical evidence.

## Rationale

A direct deletion would remove useful Aether behavior together with generic runtime machinery. A progressive transition allows Aether to keep product authority and continuity while replacing the high-maintenance process, session, dispatch, terminal, messaging, and worktree code that Orca already supplies.

Keeping Orca behind a narrow adapter reduces upstream coupling and leaves open a future substrate replacement if Orca fails security, stability, or maintenance gates. Extracting Ariadna and continuity first prevents the execution-runtime migration from becoming a product-identity rewrite.

## Alternatives considered

### Delete `src/olympus_v3` immediately and repair failures afterward

- **Benefits:** Maximum visible code reduction.
- **Costs:** Breaks continuity, setup, profiles, MCP tools, tests, and rollback at once; cannot distinguish intentional retirement from accidental product loss.
- **Decision:** Rejected.

### Refactor Olympus incrementally into the future runtime

- **Benefits:** Preserves existing imports and tests.
- **Costs:** Continues investing in the runtime that v0.22.0 is intended to replace and keeps Aether coupled to ACPManager and the kernel.
- **Decision:** Rejected as the target architecture. Compatibility shims may exist temporarily but must have deletion gates.

### Fork Orca before proving the adapter

- **Benefits:** Full implementation control.
- **Costs:** Large maintenance and security burden before value is demonstrated.
- **Decision:** Rejected for the first transition. Use official seams and a pinned build first.

### Create a separate Aether successor repository

- **Benefits:** Clean source tree.
- **Costs:** Splits product identity, history, decisions, profiles, continuity, and release authority.
- **Decision:** Rejected while the Aether product vision remains unchanged.

### Let Orca become the product authority

- **Benefits:** Fewer Aether-specific contracts.
- **Costs:** Loses user-intent authority, product acceptance, continuity, participant policy, and protected-effect boundaries.
- **Decision:** Rejected.

## Consequences

### Positive

- Aether's differentiated product logic becomes explicit and independently testable.
- Generic runtime code can be removed instead of maintained twice.
- Orca adoption remains reversible and replaceable.
- Ariadna and `.aether` survive the lifecycle migration.
- Code retirement becomes evidence-backed rather than file-count driven.

### Negative

- The repository temporarily carries both paths and compatibility adapters.
- Some tests must be converted from Olympus implementation tests into substrate-neutral contract tests.
- Legacy stores require read-only archival policy.
- Orca must be pinned, hardened, and operationally exercised before it can replace active lifecycle code.

### Risks

- Accidental transfer of product authority to Orca.
- Cross-project or cross-profile access from a desktop runtime.
- Treating `worker_done` as semantic acceptance.
- Assuming worker stop also cleans terminals, setup processes, and worktrees.
- Losing evidence-per-attempt or digest-verified handoff guarantees.
- Preserving compatibility shims indefinitely.
- Removing historical evidence or live state during cleanup.

## Validation or review gate

v0.22.0 cannot claim Olympus retirement until it demonstrates:

1. an exact canonical baseline and rollback point;
2. an Aether-native package boundary independent of `olympus_v3`;
3. schema-compatible continuity and self-improvement state;
4. a pinned, hardened, project-isolated Orca runtime;
5. one synthetic vertical slice and one bounded Aether two-worker slice;
6. exact Run/Task/Dispatch and attempt correlation;
7. product-authorized participant and protected-effect enforcement;
8. deterministic evidence and semantic acceptance outside Orca terminal status;
9. restart and recovery without duplicate editors or concurrent authority;
10. explicit cleanup of workers, terminals, setup processes, worktrees, messages, and temporary state;
11. rollback without mutating `.aether` or historical stores;
12. zero active `olympus_v3` imports, entry points, plugins, or configuration references after the final cut;
13. preservation of versioned historical references;
14. full affected and repository regression evidence on the exact candidate tree.

## Implementation authorization

The owner approved the `v0.22.0` capability boundary and progressive local source cleanup on 2026-08-03. This authorizes:

- the current analysis and roadmap;
- local Aether-native extraction work;
- a minimal Orca adapter;
- a hardened, isolated, non-production Orca pilot;
- reversible local retirement cuts after their documented gates pass.

This approval does not authorize destructive data migration, mutation of historical stores, force-push, deployment, production activation, credential creation, spending, external publication, or bypass of the release gates. Merge, tag, GitHub Release, and source publication remain subject to the repository's standing gated workflow and exact-candidate evidence. Runtime activation remains a separate operational gate.

## References

- Product authority: `docs/knowledge/AUTHORITY.md`
- Product completion: `docs/product/COMPLETION.md`
- Multi-agent decision: `docs/decisions/PDR-0005-multi-agent-participation-and-coordination.md`
- Self-improvement decision: `docs/decisions/PDR-0009-semver-self-improvement-cycle.md`
- Olympus maintenance baseline: `docs/architecture/EXPERIMENTAL_COORDINATION.md`
- v0.19.x closeout: `docs/releases/v0.19.x-kernel-migration/ROADMAP_CLOSEOUT.md`
- v0.22.0 manifest: `docs/releases/v0.22.0/STATUS.yaml`
- Retirement inventory: `docs/releases/v0.22.0/OLYMPUS_RETIREMENT_INVENTORY.md`
- Orca equivalence matrix: `docs/releases/v0.22.0/ORCA_EQUIVALENCE_MATRIX.md`
- Migration roadmap: `docs/releases/v0.22.0/ROADMAP.md`
