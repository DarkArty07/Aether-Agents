# Getting started

This page takes you from an installed release to a running Morfeo session in your own
project. If Aether is not installed yet, start with [Installation](installation.md).
Generic Hermes provider setup and credential management belong to the
[authoritative Hermes documentation](https://hermes-agent.nousresearch.com/docs/).

## Check the installation

```bash
aether --version
aether doctor
aether --help
```

`aether --version` and parser help do not import the managed Hermes runtime. `aether doctor` is read-only: it reports `ready` when the active release is coherent, and a non-zero integrity result otherwise. That result is diagnostic evidence, not an instruction to install, authenticate, or activate anything.

Top-level `aether [--project PATH] --json` emits a non-mutating launch plan from packaged manager code without importing Hermes or changing state; without `--json`, `aether` launches project-bound Morfeo into the active release-owned TUI.

Make sure each role has a model configured (see [Installation, step 5](installation.md#5-configure-a-model-for-each-role)) before you start working with Morfeo.

## Initialize an existing repository

`aether init` requires an **existing Git repository root** (such as after `git init` in a new or existing directory). It does not run `git init` in an empty directory, create a remote repository, or select a Project by name or approximate path.

`aether init` reuses one exact-path native Hermes Project or creates and verifies one through the selected runtime CLI when absent. If multiple matching Projects exist, pass the matching native identifier with `--hermes-project`.

```bash
cd /path/to/existing-git-repository
aether init --dry-run
aether init
```

The command validates or writes `.aether/project.toml`, maps its portable UUID to the exact-path native Hermes Project, and makes the marker and finalized Objective Contracts trackable while keeping drafts ignored. It refuses missing, ambiguous, mismatched, invalid, or conflicting identity rather than guessing. See [Project initialization](guides/project-initialization.md) for the full boundary.

## Launch Aether in an initialized project

Aether never infers a project from a display name, a session history, a board default, or checkout recency. It resolves exactly one initialized project through this precedence:

1. an explicit `--project PATH`;
2. `AETHER_PROJECT_ROOT` in the environment, which also takes precedence over the current directory;
3. a verified `AETHER_PROJECT_ID` whose project-registry entry and portable marker agree;
4. the current directory, or its nearest initialized parent directory.

An uninitialized current working directory never silently opens an unrelated registered project: when a single project is registered, Aether refuses with actionable `git init` and `aether init` guidance; with several registered projects and no explicit selection the launch stops with a bounded `ambiguous project identity` error rather than presenting a picker, name match, or most-recent guess.

Identity values fail visibly instead of falling back to the current directory, and each one fails differently: an empty `--project` value is refused, while a relative `--project PATH` is resolved against the current working directory; `AETHER_PROJECT_ROOT` must be an absolute path, so an empty or relative value is refused (`must not be empty` / `must be an absolute path`); and `AETHER_PROJECT_ID` must be a canonical UUID whose registry entry and portable marker agree. A directory that is not an initialized project root, a registry/marker disagreement, and a conflict between an explicit identity and the registry are all reported as errors. With several registered projects and no explicit selection the launch stops with a bounded `ambiguous project identity` error rather than presenting a picker, name match, or most-recent guess.

```bash
cd /path/to/an/initialized/project
aether                                            # fresh Morfeo session in this project
aether --project /path/to/project                 # explicit project, from anywhere
aether --project /path/to/project --resume latest # continue that project's latest session
aether --project /path/to/project --json          # non-mutating launch plan
```

Top-level launch binds the active release's own interpreter, source root, TUI directory, Morfeo profile, and the exact project. In an activated installation the same two actions are installed as branded desktop entries — `Aether` (fresh) and `Continue Aether` (`--resume latest`) — and, on WSL hosts, as Windows Terminal fragments; both point at the stable `runtime/current/venv/bin/aether` entry with the exact project root.

### Optional personal shell defaults

Aether never writes a personal shell preference: a default or shortcut in your own shell configuration is optional, stays yours, and is added and removed by you.

**Project default (`AETHER_PROJECT_ROOT`).** Setting `AETHER_PROJECT_ROOT` to an absolute project path selects that project from any directory: it takes precedence over the current directory, while an explicit `--project PATH` still wins over it. A relative or empty value is refused, so use an absolute path of your own.

Bash and Zsh (`~/.bashrc`, `~/.zshrc`):

```bash
export AETHER_PROJECT_ROOT='/path/to/an/initialized/project'
```

Remove it with `unset AETHER_PROJECT_ROOT` and by deleting the line.

Fish (`~/.config/fish/config.fish`):

```fish
set -gx AETHER_PROJECT_ROOT /path/to/an/initialized/project
```

Remove it with `set -e AETHER_PROJECT_ROOT` and by deleting the line.

**Executable shortcut (optional convenience).** A shortcut is unrelated to project selection and only saves typing. Use the stable `runtime/current` entry so the shortcut follows an activated release.

Bash and Zsh (`~/.bashrc`, `~/.zshrc`):

```bash
alias aether='/path/to/aether/runtime/current/venv/bin/aether'
```

Remove it with `unalias aether` and by deleting the alias line.

Fish (`~/.config/fish/config.fish`):

```fish
function aether
    /path/to/aether/runtime/current/venv/bin/aether $argv
end
```

Remove it with `functions -e aether` and by deleting the function block.

## Work with Morfeo

Morfeo is the only role you talk to. Describe the outcome you want in plain language,
including constraints and what "done" means. Morfeo inspects the project and then either:

- completes a small, reversible objective **directly**, verifies it and reports; or
- writes an **Objective Contract**, commits it and hands it to the Supervisor, who
  decomposes it into Implementer units, reviews them and closes out through a pull request.

Use `/aether-plan` when you want a plan before any implementation. Morfeo plans and stops;
it creates no contract, card or worker. The generic `/plan` is not an Aether alias.

The [first objective tutorial](tutorials/first-objective.md) walks through both routes,
and [Lifecycle](guides/lifecycle.md) explains how Morfeo chooses between them.

## Inspect without changing anything

These commands are safe at any time and make no provider call:

```bash
aether --help
aether doctor --json
aether --project /path/to/project --json    # launch plan only
aether observe                              # brief of the open contract, if any
aether reconcile --to active --json         # preview of projection repairs
```

State-changing lifecycle commands (`setup`, `update`, `rollback`, `uninstall`) preview
their plan unless you pass `--yes`. `aether update` is the only supported promotion and
activation boundary; see [Installation](installation.md#update-to-a-later-release) and
[Policy and recovery](guides/policy-and-recovery.md). For the parser surface, read the
[CLI reference](reference/cli.md); for current limits, read
[limitations and troubleshooting](reference/limitations-and-troubleshooting.md).

## Next steps

- [Tutorial: your first objective](tutorials/first-objective.md)
- [Tutorial: use Morfeo from Claude Code](tutorials/claude-code.md)
- [Tutorial: project knowledge](tutorials/project-knowledge.md)
