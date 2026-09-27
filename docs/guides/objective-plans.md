# Objective Plans and continuity

An Objective Plan helps Morfeo conduct one owner's objective across sessions and,
when needed, multiple [Objective Contracts](objective-contracts.md). It is a
working record, not another contract, task board or authority. The governing
requirements are [R1](../../specs/r1-authority-and-interaction/spec.md) FR-116a/FR-121a
and [R2 §3.1](../../specs/r2-contract-and-handoff/spec.md#31-objective-plans-route-and-continuity-not-contract-authority).

## Location and identity

Use `.aether/plans/<objective-slug>.md` in the explicitly resolved project. Keep
one stable file for the objective rather than creating a replacement each session.
Operational plans are **local and ignored** by default: check the project's accepted
privacy/versioning policy before writing, and do not force-add a plan or silently
change ignore rules. The procedure is public; private continuity is not.

Do not choose the globally newest plan or infer identity from a display name.
Resolve ambiguity before writing. A worktree is not a new objective: retain the
explicitly selected plan location and identify the current candidate separately.
Do not initialize, register or migrate a project merely to create a plan. Existing
plans elsewhere remain usable historical context, not a migration backlog.

## When a plan helps

Use it when the work needs a meaningful route, spans contracts or must continue in
another session. Do not require it for a simple question or routine bounded change.
Morfeo recognizes the need; the user need not remember to invoke a planning command.
An explicit planning-only request still ends at the proposal, not implementation.

Aether's canonical explicit planning skill is **`aether-plan`**, delivered only to
Morfeo through the role-scoped release bundle. Its intended native invocation is
`/aether-plan`, planning-only, writing one stable `.aether/plans/<objective-slug>.md`
inside the explicitly resolved project. A skill is package-wide procedure; its
**outputs live inside each selected project**. The #541 rename is source maintenance;
it does not claim that a running installation already exposes the new command.

The stable package/profile directory is `skills/plan/`, preserving RC16 updater
compatibility; frontmatter exposes `aether-plan` and native name-based loading selects
it. Storage identity is not a command alias. RC17's bounded release evidence is separate
from the source-only #541 maintenance and historical #504 qualification.

The generic Hermes `/plan` is not an alias for this behavior and is not replaced.
Historical Aether `plan` qualification on fork commit
`aed6591a69f453a1867b73628603e7b53ba40ffc` remains evidence for that old name only.
The renamed resource avoids relying on precedence over a homonymous learned skill;
source/reference changes alone do not qualify native dispatch or agent behavior.

Supervisor and Implementer do not receive `aether-plan`; their role boundaries do not
include objective-level planning. Older release inventories remain historical inputs,
not reasons to rewrite installed profiles during documentation work. A source change
or merge is not active-profile installation, release cutover or a behavioral guarantee.

## Exploration before a plan

Reuse relevant `.aether/observations/<topic>.md` notes when they exist, without requiring
an observation or loading every note. Separate accepted decisions from hypotheses and
unresolved questions; references do not turn a proposal into approved scope. A topic may
end with an answer rather than a plan. Research within an accepted specification remains
in its `research.md`, and product specifications/technical plans stay outside `.aether`.
See [project adoption](project-initialization.md#methodology-after-initialization) and
the [expected planning behavior](expected-behavior.md#plan-explicitly-without-silently-starting-execution).

`aether-plan` is the focused explicit entry; `objective-contract-design` owns the shared
adoption/planning method and authorized continuity without a command. Both use the same
project-local plan convention. Explicit planning still stops without implementation or
dispatch, even when its route forecasts future execution.

## A compact outline

The following headings are an example, not a schema or mandatory empty template:

```markdown
# <Objective>
Project/plan identity: <verified project and exact plan path>
Disposition / last material update: <current state and date>

## Stable destination
Requested observable result; scope/exclusions; preservation; closure evidence.
References to the canonical owners of accepted requirements and authority.

## Current route
Independently useful milestones, real dependencies and related contract references.
Current approach and the material assumptions that could invalidate it.

## Operational continuity
Verified results: artifact/revision, producer and limits.
Failed attempts: what failed and why; what would need to change before retrying.
Untried ideas: explicitly unverified, not automatically authorized work.
Remaining obligation; justified next step and stop/replan condition, or blocker.
```

Do not copy every task or log. The technical `plan.md` still owns its existing
execution approach; specifications/contracts own obligations; native boards own
execution status. A broader planning scope does not grant higher authority. A
pipeline handoff must be executable without access to private continuity notes.

## Continue, close, or stop

Update after meaningful decisions, results, failures and session handoff, not every
command. Reread before targeted edits when another session may have changed the file.
On resumption, read the exact plan and check changeable facts against current
sources. Preserve settled decisions and failed approaches without assuming stale
notes are current proof. `todo` is for the current segment; its history-backed state
is **not automatically carried into an independent new session**.

Before a successor contract, material prerequisite, repeated same-cause failure or
change of approach, identify the unmet obligation, the evidence for the next action,
and the condition to stop or replan. Distinguish a product failure, a faulty test
instrument and a coordination failure. A new contract/session does not reset
applicable bounds or make accumulated failure irrelevant.

- Close when the agreed material outcome is supported; optional improvements stay out.
- Continue a justified bounded correction under existing authority and review rules.
- Preserve and report an incomplete stop when the premise is invalid or continuation
  is unjustified. This is not acceptance and does not require pretending a board is done.

The canonical `objective-contract-design` skill owns planning/continuation method;
`contract-result-review` owns reception. Missing material owner decisions still go
to the owner through existing mechanisms. Authorized routine work gains no new
confirmation gate. No new tool, scheduler, agent, schema or fixed retry count is added.

## Verification boundary

Resource tests can check that instructions are present and native loaders read the
intended bytes. They cannot demonstrate that a model will converge faster. Observe
ordinary future sessions for faithful scope, useful continuation and honest closure;
record actual examples without a synthetic campaign or invented behavioral PASS.
Source changes, local activation and observed behavior remain separate claims.
