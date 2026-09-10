# Start here

This is the first page for a technically capable reader who knows Git and a terminal but
has no Aether-specific context. The canonical manual is written in English and describes
this repository's current build. Start with the model and route choice below; use the
reference pages when you need exact command or implementation detail.

> **Current-build status.** This repository is an operational-reliability **stabilization
> build**, not a public release or release-qualified installation. The safe exercise for
> a new reader is a provider-free source checkout: inspect the parser, help output and
> deterministic tests without configuring a provider or credentials. The broader product
> design is intended to support more than this build currently proves.

## What Aether is

Aether Agents is a software-engineering product and method layered on [Hermes
Agent](https://hermes-agent.nousresearch.com/docs/) and the [GitHub Spec Kit
method](https://github.com/github/spec-kit/). An owner states a software objective. Aether
turns that intent into explicit scope and acceptance, then uses the appropriate amount of
role-separated work to produce code, tests, review and evidence.

Aether is not a magic prompt, a second generic Hermes manual, or a claim that every
intended workflow is already qualified. It does not replace Git, project governance,
engineering judgement or the evidence needed to accept a change. The current
[capability registry](capabilities.toml) is the sole source for implementation status;
this manual explains how the current build is used and where its limits are.

## The mental model: one owner and three roles

The **owner** supplies product intent, constraints, priorities and final acceptance.
Aether has exactly three product roles:

- **Morfeo** turns the owner's intent into a coherent design, specifications and—when the
  objective needs the pipeline—one executable [Objective Contract](guides/objective-contracts.md).
  Morfeo also chooses the route for the complete objective and may handle a bounded direct
  action.
- **Supervisor** makes a substantial objective executable: it decomposes the accepted
  contract, coordinates work, independently reviews results, integrates them and owns
  pipeline closeout.
- **Implementer** executes one bounded work unit in an isolated Git worktree, runs the
  relevant checks, commits the intended change and reports evidence. Implementers do not
  redefine the objective or publish the pipeline.

The roles narrow the decision space as work moves from intent to implementation. Read
[Roles and authority](roles-and-authority.md) for the complete boundary and the
[glossary](reference/glossary.md) for these terms in one place.

## Choose the route for the complete objective

Route selection is a judgement about the **whole objective**, not about how many files a
technical mutation happens to touch.

| Choose the direct route when… | Choose the pipeline route when… |
| --- | --- |
| the objective is understood, bounded and easy to inspect; | the objective is substantial, multi-responsibility or architectural; |
| correction or reversal is reasonably simple; and | multiple independent units, integration or independent review add value; or |
| decomposition and independent review would add no proportionate assurance. | important scope or implementation facts are materially uncertain. |

On the **direct route**, Morfeo works in the managed project workspace, verifies the
actual diff and tests, and performs no ceremonial board handoff. If inspection reveals
substantial work, Morfeo stops expanding the direct change and uses the pipeline instead;
it does not split one substantial objective into small-looking direct actions.

On the **pipeline route**, Morfeo finalizes one project-bound contract and hands it to
Supervisor. Supervisor creates bounded units; Implementers work in isolated worktrees;
Supervisor independently reviews and integrates the results. The [illustrative first
objective](guides/first-objective.md) walks through both choices without turning an
example into a requirement.

## Safe first exercise: inspect the source checkout

### Prerequisites

Have these before following the commands:

- a checked-out copy of this repository;
- Git and `uv` available in the terminal; and
- Python compatible with the project declaration (`>=3.11,<3.14`).

No model provider, credential, hosted service or live agent session is needed for this
exercise. Generic Hermes installation, provider configuration and credential management
are deliberately not repeated here; use the [authoritative Hermes documentation](https://hermes-agent.nousresearch.com/docs/)
for that context.

### Run the provider-free checks

From the repository root, inspect the parser and deterministic observation surface:

```bash
uv sync --frozen
uv run --frozen aether --version
uv run --frozen aether --help
uv run --frozen aether observe --help
uv run --frozen aether doctor --help
```

Expected observations:

- `--version` reports the package version without importing the managed Hermes runtime.
- `--help` lists the parser surface, and `observe --help` lists the read-only observation
  arguments. These are parser checks, not proof of a live project launch.
- `doctor --help` is safe to inspect. A read-only `aether doctor --json` may return a
  non-zero integrity result when no active candidate release exists; that is an honest
  diagnostic, not an instruction to install, authenticate or activate anything.

For the exact `observe` behavior and its empty, ambiguous and read-only outcomes, see
[Observation](guides/observation.md). For the full set of current command surfaces, see
the [CLI reference](reference/cli.md).

## The project-initialization boundary

The current `aether init` command is intentionally narrower than the product's intended
greenfield scope. It requires an **existing Git repository root** and an exact-path,
non-archived native Hermes Project whose `primary_path` matches that root. It does not run
`git init`, create a native Hermes Project, create a remote, or guess among projects.

Greenfield and brownfield work are part of the intended product design, but greenfield
initialization is not current behavior in this build. Do not infer current capability from
that design statement. Read [Project initialization](guides/project-initialization.md)
before attempting `aether init`; it explains the prerequisites and refusal conditions.

## Reading current status honestly

Use these labels consistently:

- **Implemented** means source and focused verification support the documented current
  behavior.
- **Partial** means useful behavior exists but a stated functional boundary or
  qualification requirement remains incomplete.
- **Transitional** means a temporary mechanism remains while its qualification or
  retirement condition is open.
- **Unsupported** means an interface is visible but explicitly refuses the promised
  effect; it must not be presented as working.
- **Intended** describes accepted product design, not a capability this checkout has
  demonstrated.
- **Historical** describes preserved rationale or an earlier result, not current status.

The registry in `docs/capabilities.toml` owns those implementation-status values. The
[generated capability reference](reference/capabilities.md) is derived from it and must
not be edited as a substitute. Current documentation, capability status and local runtime
state answer different questions; [Authority and artifact ownership](authority.md)
explains the distinction.

## Next step

Continue with [Getting started](getting-started.md) for the sequenced provider-free path
and the project prerequisites. Then read [First objective](guides/first-objective.md) for
an illustrative pipeline walkthrough, or use the [glossary](reference/glossary.md) when a
term is unfamiliar.
