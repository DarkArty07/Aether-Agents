# Smoke-Testing Setup Script Changes

When a PR modifies `setup.sh` (or any installation script that mutates system state like `.bashrc`, vens, wrapper directories), CI alone is insufficient. You must smoke-test the actual script execution in an isolated clone.

## Pattern: Fresh-Clone Smoke Test

After committing all changes but before opening the PR (or after, before merging):

```bash
# 1. Clone the branch fresh
cd /tmp
rm -rf smoke-test
git clone --depth 1 --branch "$(git branch --show-current)" \
  https://github.com/OWNER/REPO.git /tmp/smoke-test

# 2. Capture pre-test state of mutable files
grep "^export HERMES_HOME=" ~/.bashrc 2>/dev/null || echo "NO_HERMES_HOME_AT_START"

# 3. Run the full setup script
cd /tmp/smoke-test
bash scripts/setup.sh 2>&1 | tee /tmp/smoke-output.txt
```

### Verification Checklist

For each condition the fix addresses, verify from the captured output and post-state:

| What to check | How |
|---------------|-----|
| **Banner version** | `grep "Aether Agents.*Setup" /tmp/smoke-output.txt` |
| **Step-specific messages** | `grep "ictinus:" /tmp/smoke-output.txt` — exact message from the fix |
| **Files created** | `ls -la home/.env` (or whatever file the fix creates) |
| **System state mutated** | `grep "^export HERMES_HOME=" ~/.bashrc` — verify it points to the **new** clone path |
| **Wrapper scripts** | `grep "^export HERMES_HOME=" ~/.local/bin/aether` — must match clone path |

### Restoring System State

The smoke test modifies `~/.bashrc` and `~/.local/bin/` on the host machine. Always restore:

```bash
# Restore the original .bashrc line
sed -i.bak "s|^export HERMES_HOME=.*|export HERMES_HOME=/original/path/home|" ~/.bashrc
rm -f ~/.bashrc.bak

# Verify restoration
grep "^export HERMES_HOME=" ~/.bashrc

# Clean up the temp clone
rm -rf /tmp/smoke-test /tmp/smoke-output.txt
```

If the smoke test created wrapper scripts at new paths, remove them too:
```bash
rm -f ~/.local/bin/aether ~/.local/bin/hermes ~/.local/bin/aether-setup
```

### Pitfalls

- **Backup `.bashrc` first** if you have a complex one — the `sed -i.bak` + `rm -f` pattern is fast but irreversible after removal.
- **Don't rely on `source ~/.bashrc` during the test** — the test shell already captured `HERMES_HOME` at login. The test proves the file was mutated correctly; the user will source when they open a new terminal.
- **Multiple test runs**: The setup script is idempotent. Running it twice should produce the same results (second run says "already exists — skipping" etc.).
- **Environment-dependent failures** (missing Python, pip, GPU) are NOT bugs in the script — those are prerequisites. The smoke test validates the script's logic, not the environment's completeness.
- **Always clean up**: `/tmp` is not automatically wiped on WSL. Leaving stale clones can confuse future tests.
- **Multiple PRs in parallel**: For consolidated smoke tests across 3+ PR branches on a remote machine, see `references/multi-pr-smoke-test-remote.md`.
