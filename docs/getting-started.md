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

Top-level `aether [--project PATH] --json` emits a non-mutating launch plan from packaged manager code without importing Hermes or changing state; without `--json`, `aether` launches project-bound Morfeo into the active release-owned TUI.

## Initialize an existing repository

`aether init` currently requires an **existing Git repository root**. It does not initialize Git in an empty directory, create a remote repository, create a native Hermes Project, or select a Project by name or approximate path.

Before running it, create or identify one non-archived native Hermes Project whose primary path is exactly the repository root. If multiple matching Projects exist, pass the matching native identifier with `--hermes-project`.

```bash
cd /path/to/existing-git-repository
uv run --frozen aether init --dry-run
uv run --frozen aether init
```

The command validates or writes `.aether/project.toml`, maps its portable UUID to the exact-path native Hermes Project, and makes the marker and finalized Objective Contracts trackable while keeping drafts ignored. It refuses missing, ambiguous, mismatched, invalid, or conflicting identity rather than guessing. See [Project initialization](guides/project-initialization.md) for the full boundary.

## Launch Aether in an initialized project

Aether never infers a project from a display name, a session history, a board default, or checkout recency. It resolves exactly one initialized project through this precedence:

1. an explicit `--project PATH`;
2. `AETHER_PROJECT_ROOT` in the environment, which also takes precedence over the current directory;
3. a verified `AETHER_PROJECT_ID` whose project-registry entry and portable marker agree;
4. the current directory, or its nearest initialized parent directory;
5. only when none of the above applies: the single registered project.

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

**Project default (`AETHER_PROJECT_ROOT`).** Setting `AETHER_PROJECT_ROOT` to an absolute project path selects that project from any directory: it takes precedence over the current directory (and over the single registered project), while an explicit `--project PATH` still wins over it. A relative or empty value is refused, so use an absolute path of your own.

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

## What not to infer

The package has local lifecycle candidate commands (`setup`, `update`, `rollback`, and `uninstall`), but these are not a complete public installation path. Do not run a state-changing lifecycle command merely to explore the documentation. The current supported discovery commands are `--help`, `--version`, `observe --help`, and read-only `doctor`; see [CLI reference](reference/cli.md) and [limitations](reference/limitations-and-troubleshooting.md).

`aether update` is nonetheless the only supported promotion and activation boundary, and its
local-candidate route has a non-mutating preview: `aether update --local --aether-checkout
PATH --aether-commit SHA --fork-checkout PATH --fork-commit SHA` reports the exact Aether and
maintained-fork revisions, target version and release ID, active HLP coverage, artifacts and
hashes, expected service interruption, preserved state and any blockers without staging or
activating anything. Activation happens only with an explicit `--yes`, may interrupt
Aether-owned instances immediately, and `aether rollback` restores product code without
rolling user state backward. The managed Hermes source is the release-lock `maintained_fork`
identity (`schema_version` 4, repository `https://github.com/DarkArty07/aether-hermes`); the
retired `transitional_fork` mode is refused for new preparation.

## Inspect the Telegram Monitor without changing anything

`aether monitor status --json` and `aether monitor history --json` read durable monitor state and are safe to run before deciding anything; `aether monitor on` and `aether monitor off` change the installation and require the provisioned runtime. The deterministic qualification lane performs no model call and no Telegram send:

```bash
uv run --frozen python scripts/qualify_telegram_monitor.py --json
```

Read [Telegram Monitor](guides/telegram-monitor.md) before enabling the feature, and treat live hourly/Telegram qualification as pending until the terminal integration reports it.

For the intended operational model after an initialized project exists, read [Lifecycle](guides/lifecycle.md), [Objective Contracts](guides/objective-contracts.md), and [Execution](guides/execution.md).
