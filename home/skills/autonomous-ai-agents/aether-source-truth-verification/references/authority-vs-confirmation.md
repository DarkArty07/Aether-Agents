# Authority Is Not Interactive Reauthorization

This reference captures a reusable Aether MCP interpretation rule exposed by a user correction. Treat paths and line numbers as examples from the observed tree; revalidate the active prompt, project decisions, release status, and live MCP responses before applying them.

## The distinction

A contract requiring **explicit** or **separate** worker/provider/model/effect/budget authority does not by itself require Hermes to ask the user for permission again.

Authority can already be established by:

- the user's current task instruction;
- approved project policy or participant policy;
- an admitted provider/model/budget configuration;
- the current Task contract and authorized-effect plan;
- a prior scope-specific gate that still applies.

Interactive confirmation is needed only when the required authority is genuinely absent or ambiguous and the gap is product-material, protected, irreversible, credential-bearing, spend-bearing, publication-related, or returned as a typed `UNKNOWN`/blocker that cannot be resolved from authoritative state.

## Observed source pattern

The active Aether prompt combined three rules:

1. Aether MCP + Orca is the only multi-agent path when an admitted specialist worker is materially selected.
2. Dispatch requires explicit provider, model, effect, and budget authority.
3. Hermes must not burden the user with routine mechanics; otherwise it chooses the safest reasonable interpretation and proceeds.

The MCP contract made `swarm_validate` read-only and assigned `swarm_dispatch` responsibility for revalidating contract generation, dependencies, participant policy, profile/environment, one-writer scope, attempt budget, provider schema, and operation identity.

The correct synthesis is therefore:

> Inspect and validate existing authority first. Do not turn contract explicitness into a pre-emptive permission question.

## Correct workflow

1. Resolve the exact project and active authority sources.
2. Classify the requested effect: read-only, local append-only, local reversible, external, protected, or unknown.
3. Derive the Task contract from current user intent plus approved project/runtime policy.
4. Use `project_inspect` or `project_admit` as appropriate.
5. Build the complete manifest and call `swarm_validate` without asking about routine mechanics.
6. If the manifest is admitted and the selected worker/provider/model/effect/budget are already authorized, proceed through start/dispatch.
7. If validation or dispatch returns a typed denial, missing authority, or `UNKNOWN`, inspect authoritative state and reconcile where supported.
8. Ask the user only for the unresolved material decision—not for permission merely to use Aether MCP or Orca.

## Release gate versus per-Task authority

Do not automatically convert a release milestone such as “model-backed qualification pending a separate gate” into a permanent per-Task confirmation ritual. Determine whether it is:

- a current release-level activation boundary;
- historical evidence;
- already superseded by a newer accepted runtime state;
- or an actual missing authority for this Task.

If the release-level gate still blocks worker execution, report that exact gate. Do not phrase the blocker as though MCP usage itself requires permission.

## Bad and corrected wording

Bad:

> I would only use Hefesto if you explicitly authorize Aether MCP + Orca.

Correct when authority has not yet been inspected:

> I will inspect and validate the existing Task authority through Aether MCP. I will ask only if validation exposes an uncovered protected effect, spend boundary, credential requirement, or material decision.

Correct when a real gate is evidenced:

> The MCP is available, but the current release policy blocks this model-backed dispatch at gate X. That uncovered gate—not use of the MCP itself—requires a decision.

## Verification checklist

- [ ] “Explicit authority” was not silently translated into “ask the user again.”
- [ ] Existing user, project, Task, participant, provider, model, effect, budget, and attempt authority was inspected first.
- [ ] Read-only validation was used before escalating uncertainty.
- [ ] Release-level and per-Task gates were separated.
- [ ] The user was asked only for the smallest unresolved material decision.
- [ ] Aether MCP/Orca machinery was not treated as a protected effect merely because it enforces protected effects.
