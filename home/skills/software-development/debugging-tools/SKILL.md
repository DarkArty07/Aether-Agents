---
name: debugging-tools
description: Debug Python (pdb, debugpy), Node.js (node inspect, CDP), and Hermes TUI slash commands — breakpoints, remote debugging, and registry troubleshooting across runtimes.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [debugging, python, nodejs, pdb, debugpy, breakpoints, node-inspect, hermes-tui, cdp]
    related_skills: [systematic-debugging]
---

# Debugging Tools

## Overview

Three debugging contexts, each with its own toolset. Pick the one that matches your runtime:

| Runtime | Primary tool | When to use |
|---------|-------------|-------------|
| **Python** | `breakpoint()` + pdb | Local scripts, tests, any Python process |
| **Python (remote)** | debugpy or remote-pdb | Long-lived processes, daemons, PTY children |
| **Node.js** | `node inspect` | Hermes TUI (Ink/TypeScript), Node test runners |
| **Node.js (remote)** | CDP via chrome-remote-interface | Automated breakpoints, heap snapshots |
| **Hermes TUI** | Hybrid (Python registry + TypeScript frontend) | Slash commands, autocomplete, gateway dispatch |

**Start with the simplest tool that could work.** `breakpoint()` is cheaper than debugpy. `node inspect` is cheaper than CDP scripting. Console.log / print() is cheaper than breakpoints — use breakpoints when the traceback doesn't reveal the bug.

## Python Debugging

### breakpoint() + pdb (local)

Add `breakpoint()` in the source, run normally:

```python
def compute(x, y):
    result = some_helper(x)
    breakpoint()  # drops into pdb here
    return result + y
```

Remove before committing: `rg -n 'breakpoint\\(\\)' --type py`.

### pdb quick reference

| Command | Action |
|---------|--------|
| `n` | next line (step over) |
| `s` | step into |
| `r` | return from current function |
| `c` | continue |
| `l` / `ll` | list source / full function |
| `w` | where (stack trace) |
| `p expr` / `pp expr` | print / pretty-print |
| `display expr` | auto-print expr on every stop |
| `b file:line` | set breakpoint |
| `interact` | full Python REPL in current scope |
| `!stmt` | execute arbitrary Python |
| `q` | quit |

### Launch a script under pdb (no source edits)

```bash
python -m pdb path/to/script.py arg1 arg2
python -m pdb -c continue script.py  # post-mortem on crash
```

### Debug a pytest test

```bash
scripts/run_tests.sh tests/file.py::test_name --pdb -p no:xdist
python -m pytest tests/file.py::test_name --pdb
```

Note: xdist breaks pdb. Add `-p no:xdist` or `-n 0`.

### Remote debug with debugpy

```bash
pip install debugpy
# Process waits for debugger:
python -m debugpy --listen 127.0.0.1:5678 --wait-for-client your_script.py
```

Then attach from VS Code (launch.json with `"request": "attach"`) or use `remote-pdb` for terminal-friendly debugging:

```bash
pip install remote-pdb
# In code:
from remote_pdb import set_trace
set_trace(host="127.0.0.1", port=4444)
# Connect:
nc 127.0.0.1 4444
```

### Python common pitfalls

1. **pdb under xdist silently does nothing.** Use `-p no:xdist`.
2. **`breakpoint()` in CI hangs the process.** Never commit it.
3. **`PYTHONBREAKPOINT=0`** disables all `breakpoint()` calls.
4. **Threads.** pdb only debugs the current thread. Use debugpy for multithreaded.
5. **asyncio.** pdb works in coroutines but `await` inside pdb requires 3.13+.
6. **Forking.** Each child needs its own breakpoint.

See `references/python-debugpy.md` for the complete guide.

## Node.js Debugging

### node inspect (built-in, zero install)

```bash
# Launch paused on first line
node inspect path/to/script.js
node --inspect-brk $(which tsx) path/to/script.ts
```

| Command | Action |
|---------|--------|
| `c` / `cont` | continue |
| `n` / `next` | step over |
| `s` / `step` | step into |
| `o` / `out` | step out |
| `sb('file.js', 42)` | set breakpoint |
| `cb('file.js', 42)` | clear breakpoint |
| `bt` | backtrace |
| `list(5)` | show source |
| `repl` | REPL in current scope |
| `exec expr` | evaluate once |

### Attaching to a running process

```bash
kill -SIGUSR1 <pid>        # enable inspector
node inspect -p <pid>      # attach
```

Start with inspector: `node --inspect-brk script.js`

### Programmatic CDP

```bash
npm i -g chrome-remote-interface
# Start target:
node --inspect-brk=9229 target.js &
# Driver script: see references/node-inspect-debugger.md
```

### Node.js pitfalls

1. **Wrong line numbers in TS source** — `node inspect` hits emitted JS, not `.ts`.
2. **`--inspect` vs `--inspect-brk`** — use `--inspect-brk` to pause before code runs.
3. **Port collisions** — default 9229, use `--inspect=0` for random port.
4. **Child processes** — use `NODE_OPTIONS='--inspect-brk'` to propagate.
5. **Security** — never bind inspector to `0.0.0.0` outside isolated networks.

See `references/node-inspect-debugger.md` for the complete guide, vitest debugging, and heap snapshots.

## Hermes TUI Slash Command Debugging

### Architecture

```
Python backend (hermes_cli/commands.py)     ── canonical COMMAND_REGISTRY
       │
       ▼
TUI gateway (tui_gateway/server.py)         ── slash.exec / command.dispatch
       │
       ▼
TUI frontend (ui-tui/src/app/slash/)        ── local handlers + fallthrough
```

### Investigation steps

1. **Check TUI frontend:** `rg "/commandname" --type ts[x] --path ui-tui/`
2. **Check Python backend:** `rg "CommandDef" --type py --path hermes_cli/`
3. **Check gateway:** `rg "complete.slash|slash.exec" --path tui_gateway/`

### Fix: Missing command autocomplete

Add a `CommandDef` to `COMMAND_REGISTRY` in `hermes_cli/commands.py`:

```python
CommandDef("commandname", "Description", "Session",
    cli_only=True, aliases=("alias",),
    args_hint="[arg1|arg2|arg3]",
    subcommands=("arg1", "arg2", "arg3")),
```

### Common issues

1. **Command in TUI but not autocomplete:** Missing from `COMMAND_REGISTRY`.
2. **Command in autocomplete but doesn't work:** Handler missing in TUI or gateway.
3. **Behavior differs CLI vs TUI:** Different implementations. Check both `cli.py` and TUI local handler.
4. **Command persists config but doesn't apply live:** Need to patch nanostore state, not just `config.set`.
5. **Gateway dispatch silently ignores:** Not in `GATEWAY_KNOWN_COMMANDS`.

### Debugging tactics

- **Python side:** use `python-debugpy` (see references) to break in `_SlashWorker.exec`.
- **Ink side:** use `node-inspect-debugger` (see references) to break in `app.tsx` dispatch.
- **Always rebuild TUI:** `npm --prefix ui-tui run build` before testing.

See `references/debugging-hermes-tui-commands.md` for the complete guide.