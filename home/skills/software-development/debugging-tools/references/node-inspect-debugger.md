# Node.js Inspect Debugger — Full Reference

## Overview

Two tools, pick one:

- **`node inspect`** — built-in, zero install, CLI REPL. Best for quick poking.
- **CDP via `chrome-remote-interface`** — scriptable from Node/Python. Best for automation.

## Quick Reference: `node inspect` REPL

Launch paused on first line: `node inspect path/to/script.js`

| Command | Action |
|---|---|
| `c` / `cont` | continue |
| `n` / `next` | step over |
| `s` / `step` | step into |
| `o` / `out` | step out |
| `pause` | pause running code |
| `sb('file.js', 42)` | set breakpoint at file.js line 42 |
| `sb(42)` | set breakpoint at line 42 of current file |
| `sb('functionName')` | break when function is called |
| `cb('file.js', 42)` | clear breakpoint |
| `breakpoints` | list all breakpoints |
| `bt` | backtrace (call stack) |
| `list(5)` | show 5 lines of source |
| `watch('expr')` | evaluate expr on every pause |
| `watchers` | show watched expressions |
| `repl` | drop into REPL in current scope |
| `exec expr` | evaluate expression once |
| `restart` | restart script |
| `kill` | kill script |
| `.exit` | quit debugger |

## Attaching to a Running Process

```bash
kill -SIGUSR1 <pid>
node inspect -p <pid>
```

Start with inspector:
```bash
node --inspect script.js
node --inspect-brk script.js
node --inspect=0.0.0.0:9230 script.js
```

For TypeScript via tsx:
```bash
node --inspect-brk --import tsx script.ts
```

## Programmatic CDP

```bash
npm i -g chrome-remote-interface
node --inspect-brk=9229 target.js &
```

## Debugging Hermes ui-tui

### Single Ink component under dev
```bash
cd ui-tui
npm run build
node --inspect-brk dist/entry.js
```

### Running `hermes --tui`
```bash
hermes --tui &
TUI_PID=$(pgrep -f 'ui-tui/dist/entry' | head -1)
kill -SIGUSR1 "$TUI_PID"
node inspect -p "$TUI_PID"
```

### Vitest under debugger
```bash
node --inspect-brk ./node_modules/vitest/vitest.mjs run --no-file-parallelism src/app/foo.test.tsx
```

## Heap Snapshots & CPU Profiles
```javascript
await client.Profiler.enable();
await client.Profiler.start();
await new Promise(r => setTimeout(r, 5000));
const { profile } = await client.Profiler.stop();
require('fs').writeFileSync('/tmp/cpu.cpuprofile', JSON.stringify(profile));
```

## Common Pitfalls
1. Wrong line numbers in TS source. Breakpoints hit emitted JS, not `.ts`.
2. `--inspect` vs `--inspect-brk`. Use `--inspect-brk` to pause before code runs.
3. Port collisions. Default 9229. `--inspect=0` for random port.
4. Child processes. Use `NODE_OPTIONS='--inspect-brk'` to propagate.
5. Background kills. Ctrl+C from `node inspect` leaves target paused.
6. Running via agent terminal. Launch with `pty=true` or `background=true`.
7. Security. Never bind inspector to `0.0.0.0` outside isolated networks.

## Verification Checklist
- [ ] `curl -s http://127.0.0.1:9229/json/list` returns the expected target
- [ ] First breakpoint actually hits
- [ ] Source listing at pause shows the right file
- [ ] `exec process.pid` in `repl` returns the expected PID