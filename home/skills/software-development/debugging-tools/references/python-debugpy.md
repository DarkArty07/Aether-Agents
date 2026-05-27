# Python Debugger (pdb + debugpy) — Full Reference

## Overview

Three tools, picked by situation:

| Tool | When |
|---|---|
| `breakpoint()` + pdb | Local, interactive, simplest |
| `python -m pdb` | Launch under pdb with no source edits |
| `debugpy` | Remote / headless / attach to running process |
| `remote-pdb` | Terminal-friendly remote debugging via netcat |

## pdb Quick Reference

| Command | Action |
|---|---|
| `h` / `h cmd` | help |
| `n` | next line (step over) |
| `s` | step into |
| `r` | return from current function |
| `c` | continue |
| `unt N` | continue until line N |
| `j N` | jump to line N |
| `l` / `ll` | list source / full function |
| `w` | where (stack trace) |
| `u` / `d` | move up / down in stack |
| `a` | print args of current function |
| `p expr` / `pp expr` | print / pretty-print |
| `display expr` | auto-print expr on every stop |
| `b file:line` | set breakpoint |
| `b func` | break on function entry |
| `b file:line, cond` | conditional breakpoint |
| `cl N` | clear breakpoint N |
| `tbreak file:line` | one-shot breakpoint |
| `!stmt` | execute arbitrary Python |
| `interact` | full Python REPL in scope |
| `q` | quit |

## Recipe 1: Local breakpoint

```python
def compute(x, y):
    result = some_helper(x)
    breakpoint()
    return result + y
```

Remove before committing: `rg -n 'breakpoint\\(\\)' --type py`

## Recipe 2: Launch under pdb

```bash
python -m pdb path/to/script.py arg1 arg2
(Pdb) b path/to/script.py:42
(Pdb) c
```

## Recipe 3: Debug a pytest test

```bash
scripts/run_tests.sh tests/path/to/test_file.py::test_name --pdb -p no:xdist
source .venv/bin/activate
python -m pytest tests/foo_test.py::test_bar --pdb
```

## Recipe 4: Post-mortem

```python
import pdb, sys
try:
    run_the_thing()
except Exception:
    pdb.post_mortem(sys.exc_info()[2])
```

Wrap whole script: `python -m pdb -c continue script.py`

## Recipe 5: Remote debug with debugpy

### Setup
```bash
pip install debugpy
```

### Pattern A: Source-edit — process waits for debugger at launch
```python
import debugpy
debugpy.listen(("127.0.0.1", 5678))
print("debugpy listening on 5678, waiting for client...", flush=True)
debugpy.wait_for_client()
debugpy.breakpoint()
```

### Pattern B: Launch with -m debugpy
```bash
python -m debugpy --listen 127.0.0.1:5678 --wait-for-client your_script.py arg1
python -m debugpy --listen 127.0.0.1:5678 --wait-for-client -m your.module
```

### Pattern C: Attach to running process
```bash
python -m debugpy --listen 127.0.0.1:5678 --pid <pid>
```

Fix ptrace: `echo 0 | sudo tee /proc/sys/kernel/yama/ptrace_scope`

### Connecting from terminal (Option 3: remote-pdb)
```bash
pip install remote-pdb
# In code:
from remote_pdb import set_trace
set_trace(host="127.0.0.1", port=4444)
# From terminal:
nc 127.0.0.1 4444
```

## Debugging Hermes-specific Processes

### Tests
See Recipe 3. Always add `-p no:xdist`.

### tui_gateway subprocess
Add remote-pdb at the handler:
```python
from remote_pdb import set_trace
set_trace(host="127.0.0.1", port=4444)
```
Trigger slash command, then `nc 127.0.0.1 4444`.

### _SlashWorker subprocess
Same pattern — remote-pdb with set_trace inside worker's exec path.

### Gateway (gateway/run.py)
Use remote-pdb at a handler, or debugpy with --wait-for-client.

## Common Pitfalls

1. **pdb under pytest-xdist silently does nothing.** Use `-p no:xdist` or `-n 0`.
2. **`breakpoint()` in CI / non-TTY hangs the process.** Never commit it.
3. **`PYTHONBREAKPOINT=0`** disables all `breakpoint()` calls.
4. **`debugpy.listen` blocks only if you also call `wait_for_client()`.**
5. **Attach to PID fails on hardened kernels.** Fix ptrace_scope.
6. **Threads.** pdb only debugs current thread. Use debugpy.
7. **asyncio.** pdb works in coroutines but `await` inside pdb requires 3.13+.
8. **`scripts/run_tests.sh` strips credentials.** Debug with raw pytest first.
9. **Forking / multiprocessing.** Each child needs its own breakpoint.

## Verification Checklist

- [ ] After `pip install debugpy`: `python -c "import debugpy; print(debugpy.__version__)"`
- [ ] Remote debug port listening: `ss -tlnp | grep 5678`
- [ ] First breakpoint actually hits
- [ ] No stray `breakpoint()` / `set_trace()` / `debugpy.listen` in committed code

## One-Shot Recipes

**"Why is this dict missing a key?"**
```python
breakpoint()
# (Pdb) pp d
# (Pdb) pp list(d.keys())
# (Pdb) w
```

**"This test passes in isolation but fails in the suite."**
```bash
source .venv/bin/activate
python -m pytest tests/ -x --pdb -p no:xdist
```

**"My async handler deadlocks."**
```python
import remote_pdb; remote_pdb.set_trace(host="127.0.0.1", port=4444)
# nc 127.0.0.1 4444, then w, then !import asyncio; asyncio.all_tasks()
```