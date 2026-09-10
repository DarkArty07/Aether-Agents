# First objective: an illustrative pipeline walkthrough

> **Non-normative example.** This page is a teaching walkthrough, not a new
> requirement, run record or promise that the provider-backed execution has been
> completed. It shows how an owner-authorized substantial objective can move through
> Aether's intended responsibilities. The current repository remains a stabilization
> build; use the provider-free source-checkout exercise in [Getting started](../getting-started.md)
> for a runnable orientation.

## Read the example correctly

The example keeps three things separate:

1. **Intent** is what the owner wants changed.
2. **The contract and task cards** make that intent executable without changing it.
3. **Evidence** records what was actually inspected and tested.

The walkthrough uses an illustrative change to a fictional existing application. It does
not require a particular language, framework, provider or model. Terms used below refer to
the Aether/Hermes surfaces described in the linked current manual pages.

## Example objective

An owner says:

> “Add a read-only command that summarizes the application's recent build results,
> document the output, and keep the existing commands compatible.”

This is more than a one-line edit. It affects implementation, tests, documentation and
acceptance, and it needs the result to fit the existing application. The example therefore
uses the pipeline route. The route decision concerns the complete objective, not just one
file that might eventually change.

## 1. Owner intake

At **owner intake**, the owner supplies the desired outcome, constraints, priority and
acceptance expectation. The owner does not need to prescribe the internal task split. A
useful intake makes the observable result clear—for example, what “read-only” means,
which existing behavior must remain, and how a successful summary will be checked.

Aether first distinguishes the requested product outcome from implementation guesses. A
repository with existing code is a brownfield project; a planned new project is a
greenfield objective. Those labels describe context, not permission to claim that the
current `aether init` command can create a repository. Its actual prerequisite is covered
by [Project initialization](project-initialization.md).

## 2. Morfeo confirms scope and chooses a route

**Morfeo** inspects the project, its guidance and relevant source evidence. It clarifies
only material ambiguity and turns the owner's intent into a coherent design. It then
chooses the route for the complete objective:

- The **direct route** would fit a small, clear, inspectable and practically reversible
  correction where decomposition and independent review add no proportionate value.
- The **pipeline route** fits this example because multiple responsibilities, acceptance
  checks and integration matter.

Morfeo does not fragment a substantial objective into small direct actions merely to avoid
review. If inspection changes the estimated scope, it stops expanding the direct change
and returns to the pipeline boundary.

## 3. Objective Contract when the pipeline requires one

For a substantial pipeline objective, Morfeo finalizes one project-bound **Objective
Contract**. The contract records the outcome, scope, authority, deliverables, acceptance
criteria, testing standard, stop conditions and canonical references. It is immutable once
finalized; a material correction becomes a superseding version rather than an unrecorded
edit.

The contract for this example would state the read-only command, compatibility boundary,
documentation expectation and checks that prove the summary is correct. It would not invent
an implementation language, a provider setup or a new product capability. Read [Objective
Contracts and handoff](objective-contracts.md) for the current authoring boundary.

## 4. Supervisor prepares the board

**Supervisor** receives the finalized contract through the handoff and checks that the
objective is executable. The Supervisor may settle contract-supported shared details and
decompose the work into independently testable units, for example:

- implement the read-only summary behavior;
- add focused success, error and compatibility tests; and
- update the user-facing command documentation.

The durable **board** carries the task graph and handoffs. It is coordination state, not a
replacement for the contract or the implementation-status registry. Supervisor assigns
only bounded units with explicit acceptance and keeps dependencies visible. See
[Execution](execution.md) for the board boundary.

## 5. Implementers work in isolated worktrees

Each **Implementer** takes one assigned unit in an isolated Git **worktree**. The worker
reads the task, current source and relevant tests, makes local reversible changes, runs the
checks, and commits only its intended paths. It reports the changed files, commands,
observed results, compatibility impact and any remaining risk.

An Implementer may choose a private helper name or an equivalent local algorithm when that
choice preserves the contract. It must not silently change acceptance, widen the objective,
publish a result or absorb another unit's responsibility. A source checkout and local
checks are evidence about this unit; they are not proof of a public release or a live
provider-backed run.

## 6. Independent review and evidence

After an Implementer reports completion, a reviewer who did not author that unit checks the
actual diff and evidence against the task and contract. **Independent review** can return
an otherwise plausible change for correction; it is not the same as the Implementer's
self-review or a passing build.

The evidence should answer, for this example:

- Does the command remain read-only on both the normal and error paths?
- Do focused tests cover the summary and compatibility expectations?
- Does the documentation describe the current behavior rather than the intended future
  behavior?
- Are the changed paths, commit and test output inspectable without private runtime state?

Supervisor reviews the result it did not author, resolves actionable findings within scope,
and integrates accepted units in dependency order. Local integration is a checkpoint, not
by itself terminal closure.

## 7. GitHub-backed closeout and terminal reporting

For a project whose policy uses GitHub, the reviewed pipeline can continue through the
normal closeout sequence: verify acceptance, classify compatibility separately from release
action, push the normal branch, open a pull request, run required checks, correct
objective-caused failures without bypass, reconcile applicable tracking records, preserve
durable evidence and report the terminal outcome.

A merge, release or deployment is not implied by a green check. In particular, this current
repository keeps merge and Pages deployment behind their separate authority boundary. A
terminal report must say when a step is deferred or not applicable rather than implying it
happened. It must also preserve active, concurrent, review and unrelated work.

The **terminal report** distinguishes observed facts from inference and records what was
changed, what passed, what was omitted and why, and what material risk remains. It does not
copy credentials, private profile state, board/session identifiers, machine paths, logs or
provider/model bindings into public artifacts. Read [Lifecycle](lifecycle.md) and
[Policy and recovery](policy-and-recovery.md) for the current evidence and safety rules.

## A contrasting bounded direct example

Suppose the owner asks to correct one unambiguous spelling error in a documentation page.
If the change is understood, easy to inspect, practically reversible and does not benefit
from decomposition or independent review, Morfeo may use the **direct route**:

1. inspect the page and repository guidance;
2. make the smallest edit in the managed project workspace;
3. run the relevant documentation check;
4. inspect the diff and preserve evidence; and
5. report the verified direct result.

This example creates no ceremonial pipeline card. If the “small correction” reveals a
broader terminology problem, a code change, uncertain acceptance or an integration need,
Morfeo stops expanding it and selects the pipeline for the complete objective. Direct does
not mean unchecked, and pipeline does not mean that every objective needs maximum ceremony.

## Current behavior versus intended design

| Label | How to read it here |
| --- | --- |
| **Implemented** | The source and focused verification support the documented current behavior. |
| **Partial** | Some behavior exists, but a functional or qualification boundary remains open. |
| **Transitional** | A temporary mechanism is present while its qualification or retirement condition remains open. |
| **Unsupported** | An interface may be visible but explicitly refuses the promised effect. |
| **Intended** | Accepted product design; not proof that this checkout can perform it now. |
| **Historical** | Preserved rationale or an earlier result; not current implementation status. |

The [capability registry](../capabilities.toml) is the sole authority for implementation
status. For this repository, the documented safe beginner exercise is provider-free source
inspection. Public installation, interactive launch, complete provider-backed reliability
and release qualification remain incomplete or separately gated. Do not turn this example,
a local test result or a website page into evidence that those boundaries have changed.

## Next step

For the actual current command surface, read [CLI reference](../reference/cli.md). To
understand the vocabulary used in this walkthrough, open the [Aether glossary](../reference/glossary.md).
