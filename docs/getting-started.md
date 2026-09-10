# Getting started

This page is the second step after [Start here](start-here.md). It explains what a new
reader can safely inspect, what must exist before project initialization, and where to go
next. It is not a general Git, Python or Hermes installation tutorial.

> **Current status.** The checkout is an operational-reliability **stabilization build**,
> not a public release or release-qualified installation. The guaranteed beginner exercise
> is a provider-free source checkout: parser/help output and deterministic checks that do
> not call a model provider or require credentials.

## Prerequisites

Before running any Aether command in this guide, confirm:

- you are inside a checked-out Aether Agents repository;
- Git is available and the repository is readable;
- `uv` is available for the locked development environment; and
- the Python version satisfies the project declaration (`>=3.11,<3.14`).

The provider-free inspection below needs no provider account, credential, configured live
profile or hosted service. Generic Hermes installation, provider setup and credential
management are outside this manual; use the [authoritative Hermes Agent
documentation](https://hermes-agent.nousresearch.com/docs/) when that context is needed.

## Step 1 — inspect the local source checkout

From the repository root, prepare the locked development environment and inspect the
Hermes-free parser surfaces:

```bash
uv sync --frozen
uv run --frozen aether --version
uv run --frozen aether --help
uv run --frozen aether observe --help
uv run --frozen aether doctor --help
```

These commands are safe orientation checks:

- `aether --version` reports the package version without importing the managed Hermes
  runtime.
- `aether --help` lists the top-level parser surface. It does not prove that the complete
  installed project-aware launch path is qualified.
- `aether observe --help` shows the read-only observation syntax. It does not call a
  provider.
- `aether doctor --help` only constructs help output. The read-only `aether doctor --json`
  diagnostic may return a non-zero integrity result when no active candidate release
  exists; that is an expected diagnostic boundary in a clean checkout, not a request to
  install or authenticate.

For exact commands, options and output categories, see the [CLI reference](reference/cli.md).
For the observation empty, ambiguous and read-only states, see [Observation](guides/observation.md).

## Step 2 — understand the observed boundary

A passing parser check means the command surface can be read. It does not mean that a
provider-backed agent run, a managed service, a public installer or a release candidate is
available. Read [Limitations and troubleshooting](reference/limitations-and-troubleshooting.md)
and the generated [capability coverage](reference/capabilities.md) before interpreting a
candidate interface as current product behavior.

The status words have precise meanings: `implemented`, `partial`, `transitional`,
`unsupported`, and `deprecated` belong to `docs/capabilities.toml`. Accepted future
behavior is **intended**, and preserved prior rationale is **historical**; neither changes
current capability status. The [glossary](reference/glossary.md) provides the short
version of these terms.

## Step 3 — initialize only an eligible project

Do not treat “greenfield” in the product design as current `aether init` behavior. The
current command requires an **existing Git repository root** and one exact-path,
non-archived native Hermes Project whose `primary_path` matches that root. It does not run
`git init`, create a native Hermes Project, create a remote, or choose a project by name or
approximate path.

When those prerequisites are already satisfied, [Project initialization](guides/project-initialization.md)
explains the read-only discovery and marker-writing boundary, including `--dry-run` and
`--hermes-project ID`. If the repository or native Project is missing, ambiguous or
mismatched, stop at the documented refusal instead of guessing or creating external state.

## Step 4 — choose what to learn next

After the provider-free checks, choose based on your goal:

1. To understand the complete product story, read [First objective](guides/first-objective.md).
   It is a non-normative illustrative pipeline walkthrough and includes a contrasting
   bounded direct example.
2. To work on a substantial authorized objective, read [Objective Contracts and handoff](guides/objective-contracts.md),
   then [Execution](guides/execution.md) and [Lifecycle](guides/lifecycle.md).
3. To understand the safety and diagnostic boundary, read [Policy and recovery](guides/policy-and-recovery.md)
   and [Limitations and troubleshooting](reference/limitations-and-troubleshooting.md).
4. To look up a term or exact command, use the [glossary](reference/glossary.md) or
   [CLI reference](reference/cli.md).

A complete pipeline is not required for every objective. Morfeo selects direct work when
the complete objective is understood, bounded, inspectable and practically reversible;
substantial or materially uncertain objectives go through the pipeline. Read [Start here](start-here.md)
again if that distinction is unclear.

## What not to infer

The parser exposes local lifecycle candidate commands such as `setup`, `update`,
`rollback` and `uninstall`, but their presence is not a complete public installation path.
The service and reconciliation placeholders explicitly refuse their effects. Do not run a
state-changing lifecycle command merely to explore the documentation. Use the provider-free
checks above and the read-only diagnostic guidance in [Limitations and troubleshooting](reference/limitations-and-troubleshooting.md).

## Next step

Open [Project initialization](guides/project-initialization.md) only if you already have
an existing Git root and an exact native Hermes Project. Otherwise continue to the
[illustrative first objective](guides/first-objective.md) and [glossary](reference/glossary.md)
without activating a provider or changing project state.
