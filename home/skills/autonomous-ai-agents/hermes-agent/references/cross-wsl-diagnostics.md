# Cross-WSL Command Diagnostics

## The Problem

When running commands on another WSL distro via `wsl.exe -d <DISTRO> -- bash -c '...'`, variable assignment and `$` expansion silently fail — variables appear empty even though the shell is working correctly.

**Reproduction (2026-06-09, FedoraLinux-43):**

```bash
# ❌ BROKEN — X is empty
$ wsl.exe -d FedoraLinux-43 -- bash -c 'X=hello && echo "X=$X"'
X=

# ❌ BROKEN — even with --norc --noprofile
$ wsl.exe -d FedoraLinux-43 -- bash --norc --noprofile -c 'X=hello && echo "X=$X"'
X=

# ❌ BROKEN — even with sh (dash)
$ wsl.exe -d FedoraLinux-43 -- sh -c 'X=hello && echo "X=$X"'
X=

# ✅ WORKS — via stdin
$ echo 'X=hello; echo "X=$X"' | wsl.exe -d FedoraLinux-43 -- bash
X=hello

# ✅ WORKS — via stdin heredoc
$ cat <<'EOF' | wsl.exe -d FedoraLinux-43 -- bash
X=hello
echo "X=$X"
EOF
X=hello
```

## Root Cause

The `$` character interacts with the WSL interop layer's argument-passing mechanism. Even though single quotes in the local shell prevent expansion, the `wsl.exe` process uses a Windows→Linux translation layer that can mangle or strip `$` references in command arguments. The exact behavior varies by:
- WSL version (WSL1 vs WSL2)
- Windows build
- Local shell (bash, zsh, fish)
- Whether interop is working correctly

Passing via **stdin** avoids the argument chain entirely — the raw text arrives verbatim at the target shell.

## Diagnostic Matrix

| Test | Expected | If fails |
|------|----------|----------|
| `wsl.exe -d DISTRO -- bash -c 'echo hello'` | `hello` | WSL interop broken |
| `echo hello \| wsl.exe -d DISTRO -- bash` | `hello` | WSL stdio broken |
| `wsl.exe -d DISTRO -- bash -c 'X=hello && echo $X'` | `hello` | Variable expansion bug (use stdin) |
| `echo 'X=hello && echo $X' \| wsl.exe -d DISTRO -- bash` | `hello` | Both methods broken (rare) |

## The Fix: stdin Heredoc Pattern

**Always use this pattern for cross-WSL diagnostics that involve variables, sourcing profiles, or multi-line scripts:**

```bash
cat <<'EOF' | wsl.exe -d <DISTRO> -- bash
# All commands here run verbatim on the target distro
source ~/.bashrc
echo "HERMES_HOME=$HERMES_HOME"
hermes --version
systemctl --user status hermes-gateway-prometeo.service
EOF
```

**Rules:**
- Use `<<'EOF'` (quoted) — prevents ALL local expansion
- Use `<<'EOF'` not `<<"EOF"` — the quotes matter
- Everything between the heredoc markers is passed verbatim
- The `wsl: Failed to translate '\\wsl.localhost\...'` warning is cosmetic and ignorable

## When NOT to Use stdin

`bash -c` is fine for simple, single-line commands without variables:

```bash
# These are fine:
wsl.exe -d FedoraLinux-43 -- bash -c 'whoami'
wsl.exe -d FedoraLinux-43 -- bash -c 'ls -la /home'
wsl.exe -d FedoraLinux-43 -- bash -c 'uptime'
```

## False Diagnostic Traps This Bug Can Cause

1. **"HERMES_HOME is not set"** — Variable appears empty because `$HERMES_HOME` was mangled, not because .bashrc failed
2. **"Config file not found"** — `ls $HERMES_HOME/config.yaml` fails because the variable is empty
3. **"Gateway service not found"** — `systemctl --user status` output truncated by argument parsing
4. **"Python venv missing"** — `ls ~/.prometeo/venv/bin/python` works but `$HOME` expansion in a follow-up `-c` command fails

**Before concluding any diagnostic result, verify with stdin.** If the result changes, the original was a false negative.
