# Roles and authority

Aether has one human authority and three product roles. Role responsibility is semantic: contracts, review, attribution, worktree isolation, tests, and rollback carry ordinary local safety. The pre-tool policy is not an operating-system separation between roles.

| Participant | Primary responsibility | Local authority | Must not silently do |
| --- | --- | --- | --- |
| Owner | Product intent and final authority | Decide objectives, constraints, acceptance, and protected external effects | Delegate an unstated product decision by omission |
| Morfeo | Owner dialogue, contract architecture, memory/adaptation, and bounded direct operational work | Choose a proportional direct route for an understood bounded objective; create one finalized Objective Contract for pipeline work | Become the standing implementation role or invent owner intent |
| Supervisor | Executability analysis, decomposition, independent review, convergence, and integration | Decide contract-settled shared execution questions; make mechanical integration repairs that add no behavior | Change product intent or absorb feature implementation |
| Implementer | One bounded contract-derived implementation unit | Make reversible, testable technical choices that preserve scope, acceptance, interfaces, sibling independence, and authority | Fan out sibling product work, widen scope, or redefine the contract |

## Pipeline and direct work

Morfeo evaluates the complete owner objective. Bounded, inspectable work that does not gain proportionate value from decomposition and independent review may be completed directly and verified. A feature, architecture change, multi-responsibility objective, complex integration, or materially uncertain work crosses the role boundary through one Objective Contract and Supervisor card.

For pipeline work, Supervisor derives the record of breakdown, stamps shared decisions into dependent units, and uses the Hermes board lifecycle. Implementers receive isolated worktrees and fresh sessions. Supervisor independently reviews and integrates in dependency order. See [Lifecycle](guides/lifecycle.md) and [Execution](guides/execution.md).

## Escalation

- **Local implementation detail:** Implementer decides.
- **Material shared question settled by the contract:** Supervisor answers through the durable execution path.
- **Material product question absent from the contract:** return it through Morfeo to the owner.

A genuine protected-edge denial is authoritative and must not be bypassed. An unexpected denial of ordinary local reversible work is evidence of an Aether regression and follows the recovery boundary in [Policy and recovery](guides/policy-and-recovery.md).

## Portable resources

The package contains resources for `morfeo`, `supervisor`, and `implementer`; only Morfeo enables the Objective Contract plugin. These are versioned portable candidate resources, not a claim that a particular machine's live profiles are activated or qualified. See [Plugins and tools](reference/plugins-and-tools.md) and the registry's [role record](reference/capabilities.md#rolesportable-profile-bundle).
