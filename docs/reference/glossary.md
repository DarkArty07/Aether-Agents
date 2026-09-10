# Aether glossary

These short definitions orient a new reader. The linked pages remain authoritative for
current behavior, command details and policy; a glossary entry does not create a new
requirement.

## Aether

A software-engineering product and method built on Hermes Agent and GitHub Spec Kit. It
turns owner intent into scoped, testable work while keeping role responsibilities and
evidence visible. See [Start here](../start-here.md).

## Owner

The person who supplies product intent, constraints, priorities and final acceptance. The
owner is the final product and technology authority; the roles do not invent an unstated
objective.

## Morfeo

The named design and operational-steward role. Morfeo works with the owner's intent,
maintains coherent specifications, chooses direct work or the pipeline for the complete
objective, and authors an Objective Contract when the pipeline requires one.

## Supervisor

The unnamed execution and convergence role. Supervisor checks executability, decomposes a
contract into bounded units, coordinates dependencies, independently reviews results,
integrates accepted work and owns pipeline terminal closeout.

## Implementer

The unnamed, replicable implementation role. An Implementer executes one contract-derived
unit in an isolated worktree, runs relevant checks, commits the intended change and
reports evidence. It does not redefine intent or publish.

## Objective

The complete outcome requested by the owner. Route selection applies to this whole outcome,
not to individual edits or the number of files touched.

## Objective Contract

A finalized, project-bound statement of one pipeline objective. It records the outcome,
scope, delegated authority, deliverables, acceptance, testing standard, stop conditions and
canonical references. A finalized version is immutable; a material correction supersedes it
with a later version. Read [Objective Contracts and handoff](../guides/objective-contracts.md).

## Direct route

A bounded path in which Morfeo works and verifies the objective directly. It fits work that
is understood, inspectable and practically reversible when decomposition and independent
review would add no proportionate value. It does not mean unchecked work and creates no
ceremonial pipeline card.

## Pipeline route

The multi-role path for substantial, multi-responsibility, architectural or materially
uncertain work: Morfeo designs and contracts it, Supervisor decomposes and coordinates it,
Implementers execute isolated units, and Supervisor reviews and integrates the results.

## Board

Hermes durable coordination state for a pipeline: cards, dependencies, handoffs, retries,
review and execution status. A board is not the product specification, a capability-status
registry or a replacement for evidence.

## Worktree

An isolated Git working directory and branch used by an implementation unit. Isolation
reduces interference between concurrent changes; Supervisor still has to resolve source
collisions during integration.

## Review

Inspection of a result against its task and contract. **Independent review** is performed by
someone who did not author the unit. Self-review and a passing build are useful but are not
independent approval.

## Evidence

The inspectable record of what changed, what commands or checks actually ran, what results
were observed, what was omitted and what risk remains. Evidence supports a claim; it does
not replace product intent or redefine a specification.

## Capability registry

The structured `docs/capabilities.toml` file, which is the sole authority for current
implementation-status values: `implemented`, `partial`, `transitional`, `unsupported`
and `deprecated`. The generated [capability reference](capabilities.md) is derived from
that registry.

## Current behavior

What this checked-out build can safely document and demonstrate now, based on source,
parser behavior, tests and the capability registry. Current documentation must not borrow
an intended future behavior as if it were implemented.

## Intended design

Accepted product behavior or scope that describes where Aether is meant to go. Intended
design is not proof of implementation, public installation, provider-backed execution or
release qualification.

## Historical evidence

Preserved rationale, research, test output or an earlier decision. Historical material
explains how the current state arose but does not override current owner intent, current
specifications or the capability registry.

## Provider-free

An exercise that does not call a model provider or require provider credentials. The
provider-free source-checkout path—parser help, version reporting and deterministic
checks—is the guaranteed beginner exercise in this stabilization build.

## Stabilization build

The repository's current development state while reliability and release gates remain
open. It is not a public release or a release-qualified installation. Local source and
deterministic test results are valuable evidence but do not establish live qualification.

## Git repository root

The top directory of an existing Git repository. The current `aether init` command requires
this prerequisite; it does not run `git init` in an empty directory.

## Native Hermes Project

An existing non-archived Hermes Project whose `primary_path` exactly matches the Git
repository root. The current initialization command reads this mapping and refuses missing,
ambiguous or mismatched matches; it does not create or modify the native Project.

## Next step

Start with [Getting started](../getting-started.md) for prerequisites and provider-free
commands. Then use [First objective](../guides/first-objective.md) to see how a substantial
objective and a bounded direct correction differ.
