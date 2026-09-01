# Getting started

This repository is a development and stabilization build, not a released installation guide. The safe first steps are provider-free: inspect the installed source checkout, parser help, and deterministic tests. Generic Hermes installation, provider setup, and credential management belong to the [authoritative Hermes documentation](https://hermes-agent.nousresearch.com/docs/), not this guide.

## Inspect the local build

From a source checkout with the locked development environment available:

```bash
uv sync --frozen
uv run --frozen aether --version
uv run --frozen aether --help
uv run --frozen aether observe --help
```

`aether --version` and parser help do not import the managed Hermes runtime. `aether doctor --json` is also read-only, but it may report a non-zero integrity result when no active candidate release exists. That result is diagnostic evidence, not an instruction to install, authenticate, or activate anything.

## Initialize an existing repository

`aether init` currently requires an **existing Git repository root**. It does not initialize Git in an empty directory, create a remote repository, create a native Hermes Project, or select a Project by name or approximate path.

Before running it, create or identify one non-archived native Hermes Project whose primary path is exactly the repository root. If multiple matching Projects exist, pass the matching native identifier with `--hermes-project`.

```bash
cd /path/to/existing-git-repository
uv run --frozen aether init --dry-run
uv run --frozen aether init
```

The command validates or writes `.aether/project.toml`, maps its portable UUID to the exact-path native Hermes Project, and makes the marker and finalized Objective Contracts trackable while keeping drafts ignored. It refuses missing, ambiguous, mismatched, invalid, or conflicting identity rather than guessing. See [Project initialization](guides/project-initialization.md) for the full boundary.

## What not to infer

The package has local lifecycle candidate commands (`setup`, `update`, `rollback`, and `uninstall`), but these are not a complete public installation path. Do not run a state-changing lifecycle command merely to explore the documentation. The current supported discovery commands are `--help`, `--version`, `observe --help`, and read-only `doctor`; see [CLI reference](reference/cli.md) and [limitations](reference/limitations-and-troubleshooting.md).

For the intended operational model after an initialized project exists, read [Lifecycle](guides/lifecycle.md), [Objective Contracts](guides/objective-contracts.md), and [Execution](guides/execution.md).
