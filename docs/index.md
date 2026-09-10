# Aether Agents documentation

This is the canonical English manual for the current Aether Agents build. It is a
navigation page, not a second authority: current behavior is explained in `docs/`,
implementation status belongs to [`docs/capabilities.toml`](capabilities.toml), and
accepted product intent belongs to `DESIGN.md` and the applicable specifications.

> **Before you begin:** this repository is an operational-reliability stabilization build,
> not a public release or release-qualified installation. The guaranteed exercise is a
> provider-free source checkout. Read [Start here](start-here.md) before attempting any
> project command.

The manual follows five groups so a reader can learn the model before opening deep
reference material. Every group is ordered for learning, not by filesystem order.

## Start here

1. **[Start here](start-here.md)** — A zero-context mental model, role boundaries and the
   direct-versus-pipeline route choice.
2. **[Getting started](getting-started.md)** — Prerequisites, safe parser inspection,
   expected observations and the boundary before project initialization.

## Core concepts

1. **[Product boundary](product-boundary.md)** — What Aether adds to Hermes and what it
   deliberately does not own.
2. **[Roles and authority](roles-and-authority.md)** — Owner, Morfeo, Supervisor and
   Implementer responsibilities and decision limits.
3. **[Authority and artifact ownership](authority.md)** — Where design intent, current
   behavior, status, runtime state and evidence belong.
4. **[Glossary](reference/glossary.md)** — Concise definitions for Aether-specific terms.

## Working with Aether

1. **[Project initialization](guides/project-initialization.md)** — The current
   existing-Git-root and exact native Hermes Project prerequisites.
2. **[Objective Contracts and handoff](guides/objective-contracts.md)** — How a substantial
   pipeline objective is recorded and handed to Supervisor.
3. **[First objective](guides/first-objective.md)** — A clearly illustrative, non-normative
   pipeline walkthrough and a contrasting bounded direct example.
4. **[Execution](guides/execution.md)** — Boards, sessions, isolated worktrees, review and
   unit evidence.
5. **[Lifecycle](guides/lifecycle.md)** — Direct and pipeline routes, recovery and the
   GitHub-backed terminal sequence.
6. **[Project knowledge and role work memory](guides/project-knowledge.md)** — Optional
   technical graph context and separate role experiences.

## Operations and safety

1. **[Observation](guides/observation.md)** — Provider-free, read-only contract observation
   and its bounded outcomes.
2. **[Policy and recovery](guides/policy-and-recovery.md)** — Protected edges,
   reversibility-first local work and rollback-first recovery.
3. **[Limitations and troubleshooting](reference/limitations-and-troubleshooting.md)** —
   Current boundaries, safe diagnostics and explicit non-success conditions.

## Reference

1. **[CLI reference](reference/cli.md)** — Parser commands, options, output and exit
   behavior in this build.
2. **[Plugins and tools](reference/plugins-and-tools.md)** — Aether's registered Hermes
   plugin surfaces and action boundaries.
3. **[Capability coverage](reference/capabilities.md)** — Generated current-status and
   traceability reference; do not edit it directly.

## How to use this manual

Use the first two groups when learning the system. Use the working guides when an
objective is authorized and the operations/reference pages when you need a diagnostic or
exact interface detail. If a statement about what exists conflicts with a future design
statement, consult the capability registry and [Authority and artifact ownership](authority.md)
for the owning source instead of inferring readiness from a page, example or historical
record.

The website renders this tracked corpus directly. Its Spanish landing and orientation
copy are a guide into this English manual, not a duplicate translation. Generic Hermes
installation, provider setup and credential management belong to the [official Hermes
Agent documentation](https://hermes-agent.nousresearch.com/docs/).
