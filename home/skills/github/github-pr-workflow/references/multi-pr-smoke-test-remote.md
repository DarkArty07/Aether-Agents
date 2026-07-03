# Multi-PR Remote Smoke Test (SSH Target Machine)

When multiple open PRs modify setup scripts in parallel, run a consolidated smoke test on a remote machine. Each PR branch is cloned fresh, its setup script executed, and PR-specific check assertions verified — all from a single script delivered over SSH.

## When to Use This Pattern

- 2+ PRs that modify `scripts/setup.sh`, `setup-honcho.sh`, `.env` generation, wrapper creation, or SOUL.md files
- Changes that alter system state (`.bashrc`, `~/.local/bin/`, venv creation) — cannot test locally without contaminating the dev environment
- CI alone is insufficient because installation scripts mutate state

## Architecture

```
┌─────────────────┐     SCP script      ┌──────────────────┐
│  Dev Machine     │ ──────────────────> │  AetherTest /     │
│  (Hermes/Agent)  │                     │  Remote Host      │
│                  │  SSH execute        │                   │
│  Writes test     │ ──────────────────> │  - Clones PRs     │
│  script, reads   │                     │  - Runs setup.sh  │
│  log + output    │ <────────────────── │  - Asserts checks │
└─────────────────┘     Log file /       │  - Cleans up      │
                        results table    └──────────────────┘
```

## Essential Shell Constructs

### The `check()` Function (robust assertion runner)

```bash
PASS=0; FAIL=0
declare -A PR_PASS PR_FAIL

ok()    { local pr="$1"; shift; echo "  ✓ $*"; PASS=$((PASS+1)); PR_PASS[$pr]=$((${PR_PASS[$pr]:-0}+1)); }
fail()  { local pr="$1"; shift; echo "  ✗ $*"; FAIL=$((FAIL+1)); PR_FAIL[$pr]=$((${PR_FAIL[$pr]:-0}+1)); }
check() { local pr="$1" msg="$2" rc; shift 2; set +e; eval "$@"; rc=$?; set -e; \
          if [ "$rc" -eq 0 ]; then ok "$pr" "$msg"; else fail "$pr" "$msg"; fi; }
```

Key design choices:
- `set +e` / `set -e` guard: prevents a single failed check from aborting the entire script via `set -e`
- `eval "$@"`: accepts the command as a single string argument, supporting pipes, subshells, and compound commands
- Associative arrays `PR_PASS[$n]` / `PR_FAIL[$n]`: tracks per-PR pass/fail counts for the final table

### Pitfall: `eval` + `cd` leaves CWD permanently changed

```bash
# BAD — after this check, CWD is in honcho-server/
check "45" "valid git history" "cd honcho-server && git log --oneline -1"

# GOOD — subshell keeps CWD unchanged
check "45" "valid git history" "(cd honcho-server && git log --oneline -1)"
```

When `eval` runs a command containing `cd`, it mutates the shell's working directory permanently. Any check that runs after it and uses relative paths will break. Always wrap `cd` operations in a subshell `(...)`.

### Pitfall: `exec > >(tee ...)` over SSH buffers output

```bash
# BAD — process substitution doesn't stream via SSH stdout
exec > >(tee -a "$LOG_FILE") 2>&1
# Output only appears in LOG_FILE, never returns via SSH

# GOOD — tee directly, or skip tee and read LOG_FILE via separate SSH
bash /tmp/smoke-script.sh
ssh remote 'tail -20 /tmp/smoke-log.txt'
```

The `> >(...)` syntax spawns a background process. When the parent process runs over SSH, the background process's output is consumed locally on the remote machine by `tee` and never makes it back through the SSH channel. The SSH session sees no output until the process exits, and even then it's incomplete. **Workaround**: log to a file and read it via a second SSH command, or skip the `tee` and let raw stdout flow.

### Pitfall: `grep -qi 'hermes'` matches `HERMES_HOME`

When asserting that the `aether-setup` wrapper does NOT reference the `hermes` binary:

```bash
# BAD — too broad: matches env vars and paths
if grep -qi 'hermes' wrapper; then fail "..."; fi
# Matches HERMES_HOME, .venv-hermes/, etc. — false positive

# GOOD — specific: only match exec targets
if grep -q 'exec.*hermes\b' wrapper; then fail "..."; fi
# Only matches exec hermes_binary, exec $hermes, etc.
```

Wrapper scripts legitimately contain `HERMES_HOME` and `HERMES_PYTHON` environment variables, plus `.venv-hermes/` in the Python path. Grep for `exec.*hermes` or `hermes.*\$@` instead of the bare word.

## Cloning Strategy

### Submodule Pitfall: pinned broken commits

When a PR does NOT fix the submodule (the submodule is still pinned to a non-existent commit):

```bash
# FAILS — git clone --recurse-submodules exits non-zero
git clone --recurse-submodules -b feature/install-fixes-env \
    https://github.com/OWNER/REPO.git /tmp/smoke-pr-46

# WORKS — clone without submodules, init the path
git clone -b feature/install-fixes-env \
    https://github.com/OWNER/REPO.git /tmp/smoke-pr-46
cd /tmp/smoke-pr-46 && git submodule init 2>/dev/null || true
```

**Rule:** Only use `--recurse-submodules` for PRs that explicitly fix the submodule. For all others, clone bare and initialise the submodule path only (this creates the directory without fetching the broken commit). PRs that don't touch the submodule don't need to verify it.

### Per-PR cloning with conditional submodules

```bash
clone_pr() {
    local pr_num="$1"
    local branch="$2"
    local recurse="${3:-yes}"
    local dest="/tmp/smoke-pr-$pr_num"
    rm -rf "$dest"
    if [ "$recurse" = "yes" ]; then
        git clone --recurse-submodules -b "$branch" \
            https://github.com/OWNER/REPO.git "$dest" 2>&1 | tail -3
    else
        git clone -b "$branch" \
            https://github.com/OWNER/REPO.git "$dest" 2>&1 | tail -3
        (cd "$dest" && git submodule init 2>/dev/null || true)
    fi
}
```

## Running Over SSH

### Delivery pattern

```bash
# 1. Write the smoke test script locally
write_file /tmp/smoke-test.sh "..."
scp -P 2222 /tmp/smoke-test.sh tester@remote:/tmp/smoke-test.sh

# 2. Execute with background + notify
ssh remote -o RequestTTY=no 'bash /tmp/smoke-test.sh' 2>&1
# (Use notify_on_complete=true to get notified)

# 3. Read the log file directly from remote
ssh remote 'tail -30 /tmp/smoke-test.log'
```

### Necessary SSH flags

- `-o RequestTTY=no`: prevents SSH from allocating a TTY (which would break non-interactive scripts)
- `-P 2222` or define `Host` entry in `~/.ssh/config` with a non-standard port
- Background the SSH command so you can work on other tasks while it runs

## Results Table Format

After all checks run, output a markdown table suitable for pasting into PR comments or issues:

```markdown
| PR | Branch | Checks | PASS | FAIL | Result |
|----|--------|--------|------|------|--------|
| #45 | feature/install-fixes-honcho | Submodule, README | 5 | 0 | ✅ PASS |
| #46 | feature/install-fixes-env | Banner, .env, ictinus | 10 | 0 | ✅ PASS |
| #47 | feature/install-fixes-ux | Wrapper, Docker, SOUL | 12 | 1 | ⚠️ PARTIAL |

**Note:** 1 failure is a test false-positive — see `grep -qi 'hermes'` pitfall above.
```

## Cleanup

The script should register a `trap` handler to remove clone directories:

```bash
trap 'rm -rf /tmp/smoke-pr-45 /tmp/smoke-pr-46 /tmp/smoke-pr-47' EXIT
```

This ensures cleanup happens even if the script aborts mid-way.

## See Also

- `references/smoke-testing-setup-scripts.md` — single-PR local smoke test (the simpler variant)
