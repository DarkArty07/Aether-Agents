# Expanding the Team's Reach — Cross-Box Control Patterns

Companion to **Pitfall #13** in SKILL.md. This reference documents the working patterns and gotchas surfaced by the first real L2 deployment: driving the AetherTest WSL distro from the main Ubuntu WSL over SSH+tmux. The patterns generalize to any cross-box scenario (WSL↔WSL, host↔VM, container↔host, pod↔cluster).

## The 3-Level Ladder (Recap)

| Level | Mechanism | Persistence | When to use |
|-------|-----------|-------------|-------------|
| L1 — Passthrough | `wsl.exe -d X -- cmd` / `ssh` / `docker exec` | None | One-shot, < 2 uses/week |
| L2 — Channel | SSH server + `~/.ssh/config` alias | Yes | Daily use, stateful calls, scp, scripts |
| L3 — Full agent | hermes-agent install on the other side | Yes (daemon) | Other side takes work autonomously |

The decision tree is in SKILL.md §Pitfall 13. This reference documents **the L2 recipe and the L1↔L2 verification patterns** that surfaced during the AetherTest deployment.

## Cross-Source Inventory Checklist ("Is X actually here?")

When the user says "is Y installed on the other box?", never trust a single source. Cross at minimum three:

1. **WMI/registry/system path** — `Get-AppxPackage`, `Get-ChildItem $env:LOCALAPPDATA\Packages`, registry at `HKCU:\Software\Microsoft\Windows\CurrentVersion\Lxss`
2. **Filesystem artifact** — the binary itself, the config dir, the data dir
3. **Process list** — `Get-Process`, `ps -ef` — the thing might be running but not installed at the standard path

**The trap:** stopping at the first "not found" and reporting it as final. Example: `which opencode` returned empty inside AetherTest, the conclusion was going to be "not installed", but `type -a opencode` (which honors login-shell `~/.bashrc` PATH exports) revealed the binary at `~/.opencode/bin/opencode`. **Login shell vs non-interactive shell matters for environment loading.** See Pitfall 14 in SKILL.md for the full pattern.

## L2 Recipe — 5-Minute SSH Channel (Idempotent)

```bash
# === From THIS box (the one that has ssh client) ===

# 1. Generate a dedicated key (one per remote, never reuse)
test -f ~/.ssh/<remote>_ed25519 || \
  ssh-keygen -t ed25519 -N '' -f ~/.ssh/<remote>_ed25519 -C '<remote>-control'

# 2. Install SSH server + tmux on the remote (assumes passwordless sudo)
wsl -d <remote> -- sudo apt-get update
wsl -d <remote> -- sudo apt-get install -y openssh-server tmux
# Or for ssh: ssh -t <remote> 'sudo apt-get install -y openssh-server tmux'

# 3. sshd_config: hardens + pins port
wsl -d <remote> -- sudo tee /etc/ssh/sshd_config >/dev/null <<'EOF'
Port 2222
PasswordAuthentication no
ChallengeResponseAuthentication no
PermitRootLogin no
PubkeyAuthentication yes
UsePAM yes
AllowUsers <remoteuser>
EOF
# Remove deprecated options that produce warnings
wsl -d <remote> -- sudo sed -i '/^UsePrivilegeSeparation/d;/^KeyRegenerationInterval/d;/^ServerKeyBits/d' /etc/ssh/sshd_config

# 4. Host keys + runtime dir
wsl -d <remote> -- sudo ssh-keygen -A
wsl -d <remote> -- sudo mkdir -p /var/run/sshd

# 5. Authorize our key
wsl -d <remote> -- sudo -u <remoteuser> mkdir -p /home/<remoteuser>/.ssh
wsl -d <remote> -- sudo -u <remoteuser> bash -lc 'cat >> ~/.ssh/authorized_keys' < ~/.ssh/<remote>_ed25519.pub
wsl -d <remote> -- sudo chmod 700 /home/<remoteuser>/.ssh
wsl -d <remote> -- sudo chmod 600 /home/<remoteuser>/.ssh/authorized_keys

# 6. Auto-start sshd (best-effort — see "boot caveat" below)
wsl -d <remote> -- sudo tee /etc/wsl.conf >/dev/null <<'EOF'
[boot]
command="service ssh start"
EOF

# 7. First boot of sshd (since the VM is already up)
wsl -d <remote> -- sudo /usr/sbin/sshd

# 8. SSH config alias on this box
cat >> ~/.ssh/config <<EOF

Host <alias>
  HostName 127.0.0.1
  Port 2222
  User <remoteuser>
  IdentityFile ~/.ssh/<remote>_ed25519
  IdentitiesOnly yes
  StrictHostKeyChecking accept-new
  ServerAliveInterval 30
  ServerAliveCountMax 3
EOF

# 9. Verify (this MUST work end-to-end before declaring success)
ssh <alias> 'echo ok; tmux -V; uname -a; whoami'

# 10. Create a default tmux session that survives disconnects
ssh <alias> 'tmux new-session -d -s main -c /home/<remoteuser> || \
              tmux kill-session -t main 2>/dev/null; \
              tmux new-session -d -s main -c /home/<remoteuser>'

# 11. Helper function (interactive entry — opens tmux directly)
cat >> ~/.bashrc <<'EOF'
<alias>() { ssh -t <alias> 'tmux new-session -A -s main -c /home/<remoteuser>'; }
EOF
```

## Boot Caveat — `/etc/wsl.conf [boot] command=` is Unreliable

WSL2's `[boot] command=` directive only fires on a **cold boot** of the distro's VM. It does NOT fire when `wsl -d X` reattaches to an already-running VM. And `service` in WSL2 depends on a working init system that may not be present in minimal distros.

**Symptoms:**
- `wsl -d X` opens a shell fine
- `ssh <alias>` returns "Connection refused"
- `ps` inside the distro shows no sshd

**Fix (3 options, in order of preference):**
1. **One-shot kick** — `wsl -d <remote> -- sudo /usr/sbin/sshd` before each use. Idempotent (fails harmlessly if sshd is already running).
2. **Wrap in the helper function** — add a preflight check:
   ```bash
   <alias>() {
     ssh -o ConnectTimeout=3 <alias> 'true' 2>/dev/null || \
       wsl.exe -d <remote> -- sudo /usr/sbin/sshd
     ssh -t <alias> 'tmux new-session -A -s main -c /home/<remoteuser>'
   }
   ```
3. **systemd path** — only if the distro has systemd enabled (`[boot] systemd=true` in wsl.conf). Then `systemctl enable ssh` actually persists. But: most Ubuntu 24.04+ WSL2 installs do NOT enable systemd by default; enabling it is a project decision, not a 5-min recipe.

The cleanest practice for 2026: keep the `wsl.conf [boot] command=` line as a **best-effort hint**, and rely on the helper-function preflight to guarantee sshd is up.

## tmux as a State Bridge Across Tool Calls

The killer feature of L2 over L1 is that tmux survives between Hermes tool calls. Use it as a state bridge:

**Send input to a remote TUI:**
```bash
ssh <alias> 'tmux send-keys -t main:0 C-c'             # Ctrl+C — clear/abort
sleep 0.3
ssh <alias> 'tmux send-keys -t main:0 "<command>" C-m' # type + Enter
```

**Capture what the TUI is currently displaying:**
```bash
ssh <alias> 'tmux capture-pane -t main:0 -p -S -200'
# -S -200 = last 200 lines of scrollback
# -p = print to stdout (otherwise goes to buffer)
```

**Pattern: launching a TUI agent (opencode, claude code, codex) on the remote**
1. Pre-flight: ensure sshd is up (see Boot Caveat).
2. Ensure a `main` session exists (create if missing).
3. `tmux send-keys` to send the launch command.
4. Wait 5-10 seconds (TUIs have startup latency).
5. `tmux capture-pane` to read the first screen.
6. User now connects with `<alias>` and interacts directly. The TUI stays alive in `main` even if the user disconnects.

**Why this matters:** L1 (`wsl.exe -d X -- opencode`) starts a fresh process each call, kills it on exit, has no state. L2 + tmux gives you a persistent session that's **yours to drive** and **Hermes' to read**.

## L1 vs L2 Verification Anti-Pattern

When you verify "is opencode installed on the other box" via L1:
```bash
wsl -d <remote> -- bash -lc 'which opencode'   # returns nothing
# Conclusion: not installed.
# WRONG — `which` returns nothing because:
#  1. The user's PATH export in ~/.bashrc only loads in INTERACTIVE login shell.
#  2. `bash -lc 'cmd'` is non-interactive; some bash configs skip .bashrc.
#  3. `wsl -d X --` spawns a non-interactive wrapper that may not source .bashrc.
```

Correct:
```bash
# Match the user's actual session: login + interactive
wsl -d <remote> -- sudo -u <user> bash -l    # then in there: type -a opencode
# OR simulate the same PATH the user sees
wsl -d <remote> -- sudo -u <user> bash -lic 'echo $PATH; which opencode; type -a opencode'
```

**Rule:** When verifying "is X installed?" on the other box, replicate the user's shell mode (login + interactive), not the agent's preferred non-interactive form. If the two disagree, the user's view is the source of truth for "installed".

## What to Log for Future Sessions

- The exact distro name, the SSH alias, the user, the port, the key path
- Where the helper function lives (which `~/.bashrc`)
- Whether the user wants the boot preflight (yes for "just works" UX)
- The `wsl.conf` content (so you can grep it during diagnostics)

Future session asking "is AetherTest still configured for SSH?" should be answered by `grep -A 8 'Host aethertest' ~/.ssh/config` and `ssh aethertest 'echo ok'` in 3 commands, no investigation needed.
