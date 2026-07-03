# WSL Migration Recipes

Worked examples of additive, non-destructive migrations between WSL distros.

---

## Recipe 1: Prometeo Ubuntu → Fedora 43 (2026-06-05)

**Context:** Chris's Prometeo personal assistant lived in Ubuntu WSL alongside Aether-Agents. Two services on the same distro caused systemd unit collisions, OAuth re-prompt loops (zombie gateway PIDs), and `.env` confusion. Goal: move Prometeo to a dedicated Fedora 43 WSL.

**Architecture:**
- Ubuntu: Aether-Agents (Hermes) — unchanged
- Fedora 43: Prometeo — fresh, isolated

**Steps:**

**Scripts produced during this migration:**
- `scripts/stop-prometeo-ubuntu.sh` — idempotent service stop/disable + orphan process cleanup
- `scripts/quarantine-prometeo-ubuntu.sh` — cold backup of `~/.prometeo/` to `/mnt/c/`

The stop script evolved through three fix cycles to handle the `activating` auto-restart state. See Pitfall #9 in the main SKILL.md for why `systemctl --user is-active` was replaced with `show -p ActiveState --value`.

### 1. Stop Prometeo services on Ubuntu (using the idempotent script)

In Ubuntu WSL terminal, run the stop script created during migration:

```bash
# From the Aether-Agents repo root
bash scripts/stop-prometeo-ubuntu.sh
```

This script is idempotent — running it twice is a no-op the second time. It:
- Checks the actual active state of each service (handles `active`, `activating`, and `auto-restart`)
- Stops and disables them
- Kills orphaned Prometeo hermes_cli.main processes that match `--profile prometeo`
- Does NOT touch the Aether gateway (`hermes-gateway.service`)
- Reports before/after state so the user can verify

**Manual equivalent (if the script is not available):**
```bash
# Stop
systemctl --user stop hermes-gateway-prometeo.service
systemctl --user stop prometeo-cognee-cortex-monitor.service
# Disable
systemctl --user disable hermes-gateway-prometeo.service
systemctl --user disable prometeo-cognee-cortex-monitor.service
# Kill orphan processes
pgrep -af 'hermes_cli.main.*--profile prometeo' | awk '{print $1}' | xargs -r kill
```

### 3. Install Fedora 43 WSL
From PowerShell admin:
```powershell
wsl --list --online          # confirm FedoraLinux-43 is listed
wsl --install -d FedoraLinux-43
wsl -l -v                    # verify
```

### 4. Pre-flight Fedora (avoid the awk/checksum mismatch trap)
In Fedora WSL terminal:
```bash
sudo dnf install -y gawk curl ca-certificates python3 python3-pip python3-devel gcc make
which awk && awk --version    # /usr/bin/awk and "GNU Awk"
```

### 5. Snapshot Prometeo from Ubuntu
In Ubuntu WSL terminal (NOT destructive — additive):
```bash
# Stop the service briefly (10s) for consistent snapshot
systemctl --user stop hermes-gateway-prometeo.service

mkdir -p /mnt/c/prometeo-migration
tar --exclude='cache' --exclude='*.pyc' \
    -czf /mnt/c/prometeo-migration/prometeo-home.tar.gz \
    -C /home/prometeo .prometeo

# Back up systemd unit files
cp ~/.config/systemd/user/hermes-gateway-prometeo.service /mnt/c/prometeo-migration/
cp -r ~/.config/systemd/user/hermes-gateway-prometeo.service.d /mnt/c/prometeo-migration/ 2>/dev/null || true

# Restart the service in Ubuntu (back to normal)
systemctl --user start hermes-gateway-prometeo.service

ls -lh /mnt/c/prometeo-migration/
```

### 6. Restore on Fedora
In Fedora WSL terminal:
```bash
# Create the destination path matching Ubuntu's structure
mkdir -p ~/.prometeo/profiles/prometeo

# Install hermes-agent in a fresh venv
python3 -m venv ~/.prometeo/venv
source ~/.prometeo/venv/bin/activate
pip install --upgrade pip
pip install hermes-agent

# Restore the snapshot
cp /mnt/c/prometeo-migration/prometeo-home.tar.gz /tmp/
tar -xzf /tmp/prometeo-home.tar.gz -C ~
ls ~/.prometeo/profiles/prometeo/

# Restore systemd unit files
mkdir -p ~/.config/systemd/user
cp /mnt/c/prometeo-migration/hermes-gateway-prometeo.service ~/.config/systemd/user/
cp -r /mnt/c/prometeo-migration/hermes-gateway-prometeo.service.d ~/.config/systemd/user/ 2>/dev/null || true

# REWRITE the unit file paths to Fedora's venv (sed)
sed -i 's|/home/prometeo/Aether-Agents/home/.venv-hermes/bin/python|/home/prometeo/.prometeo/venv/bin/python|' \
    ~/.config/systemd/user/hermes-gateway-prometeo.service
sed -i 's|/home/prometeo/Aether-Agents/home/|/home/prometeo/.prometeo/|' \
    ~/.config/systemd/user/hermes-gateway-prometeo.service
sed -i 's|/home/prometeo/Aether-Agents/|/home/prometeo/.prometeo/|' \
    ~/.config/systemd/user/hermes-gateway-prometeo.service

# Verify
cat ~/.config/systemd/user/hermes-gateway-prometeo.service
```

### 7. Enable linger (so service starts without open session)
```bash
sudo loginctl enable-linger $(whoami)
```

### 8. Start the service in Fedora
```bash
systemctl --user daemon-reload
systemctl --user enable --now hermes-gateway-prometeo.service
systemctl --user status hermes-gateway-prometeo.service
```

### 9. Smoke test
Send a real message to the Telegram bot. If it responds, the migration succeeded.

### 10. Post-Migration MCP Validation

**CRITICAL:** The Telegram bot responding does NOT mean MCP servers work. MCP failures are silent — the bot responds fine but tools like Magnific, Playwright, or file search fail when invoked. After smoke test, run the 6-point diagnostic checklist from `references/mcp-post-migration-diagnostics.md`:

```bash
# Run the one-shot health check (copy from mcp-post-migration-diagnostics.md)
bash ~/.local/bin/mcp-health-check

# Or manually check the most common failures:
which node && node --version                              # #1 Node.js
systemctl --user show hermes-gateway-prometeo.service | grep Environment  # #2 PATH
grep -n '/home/' ~/.prometeo/config.yaml | head -10       # #3 config paths
ls ~/.prometeo/mcp-tokens/                                # #4 OAuth tokens
```

**If any check fails:** fix it BEFORE declaring the migration complete. MCP failures discovered days later are much harder to debug than ones caught during migration.

### 9. Cold backup Ubuntu (USER-DRIVEN, NOT agent-driven)
This step is the user's decision, not the agent's. The agent SHOULD NOT execute `systemctl --user disable` or `wsl --unregister` without explicit user confirmation. The user may want Ubuntu Prometeo as a fallback for days/weeks.

---

## Recipe 2: General Service Migration Between Distros

**Applies to:** any service that lives in `~/.config/systemd/user/<service>.service` and has data in `~/.<app>/`.

### Phase 1: Snapshot source (additive)
```bash
# Source distro
systemctl --user stop <service>
tar -czf /mnt/c/<migration>/<app>-home.tar.gz -C ~ .<app>
cp ~/.config/systemd/user/<service>.service /mnt/c/<migration>/
cp -r ~/.config/systemd/user/<service>.service.d /mnt/c/<migration>/ 2>/dev/null || true
systemctl --user start <service>   # source is back to normal
```

### Phase 2: Bootstrap target
```bash
# Target distro
sudo dnf/apt install -y <runtime-deps>
# Install the app's venv / container / binary
```

### Phase 3: Restore target
```bash
# Target distro
cp /mnt/c/<migration>/<app>-home.tar.gz /tmp/
tar -xzf /tmp/<app>-home.tar.gz -C ~
mkdir -p ~/.config/systemd/user
cp /mnt/c/<migration>/<service>.service ~/.config/systemd/user/
cp -r /mnt/c/<migration>/<service>.service.d ~/.config/systemd/user/ 2>/dev/null || true

# Rewrite paths (REVIEW each substitution manually, not blind sed)
# e.g., for hermes-agent: Aether-Agents paths → target distro paths
```

### Phase 4: Verify
```bash
systemctl --user daemon-reload
systemctl --user enable --now <service>
systemctl --user status <service>
# Send a real-world request to the service (Telegram bot, HTTP, etc.)
```

### Phase 5: Cold backup source (USER DECISION)
Don't touch source. User decides when to disable.

---

## Recipe 3: Cross-Distro File Sharing via /mnt/c/

When you need to share a file between two distros (e.g., a config snippet, a binary, a snapshot), the cleanest path is `/mnt/c/` (the Windows C: drive, mounted in every WSL distro).

```bash
# Source distro: write to /mnt/c/
cp ~/myfile.txt /mnt/c/shared/myfile.txt

# Target distro: read from /mnt/c/
cp /mnt/c/shared/myfile.txt ~/

# Cleanup (optional, not destructive)
rm /mnt/c/shared/myfile.txt
```

**Caveat:** `/mnt/c/` is the Windows filesystem. Operations from Linux (chmod, symlinks) don't translate. For pure data (configs, snapshots, JSON, tar.gz) it's perfect. For executable scripts, copy to Linux first and `chmod +x`.

**Caveat 2:** Don't write thousands of small files to `/mnt/c/` — it's slow. For migrations, tar first, then copy the tar.

---

## Recipe 4: WSL Distro Export/Import (for size compaction or relocation)

```powershell
# Export a distro to a tar file
wsl --export <DistroName> D:\\WSL-Backups\\<DistroName>.tar

# Import a distro from a tar file
wsl --import <NewName> D:\\WSL\\<NewName> D:\\WSL-Backups\\<DistroName>.tar

# Verify
wsl -l -v
```

**Use cases:**
- Compacting a bloated distro (the imported version is smaller)
- Moving a distro from C: to D: (or vice versa)
- Cloning a distro to use as a template

**Note:** `--import` creates a default user (root), not the original user. You'll need to set up the user manually:
```bash
# In the new distro
useradd -m -G wheel -s /bin/bash <username>
passwd <username>
# Edit /etc/wsl.conf to set the default user
echo "[user]
default = <username>" | sudo tee -a /etc/wsl.conf
# Restart WSL
wsl --shutdown
```

---

## Recipe 6: Cross-Distro Data Pipe Without `/mnt/c/` (Venv-Preserving)

**Context:** The target distro already has the application installed with its own venv. You want to copy the application's data (configuration, profiles, sessions, skills) from one WSL distro to another WITHOUT overwriting the target's venv. The `/mnt/c/` bridge is available but you want a one-shot pipe with no intermediate files.

**Architecture:** Data streams directly from source distro → tar → stdout pipe through Windows → target distro's stdin → tar extraction, without writing to `/mnt/c/`.

**Key constraint:**
- The target distro's venv (`~/.prometeo/venv/`) must be preserved
- Only the non-venv data should be overwritten with the source distro's data

**Three-step venv preservation:**

```bash
# STEP 1 — Backup target venv to safe location
echo 'mv ~/.prometeo/venv ~/.prometeo_venv_backup && echo "VENV_BACKUP"' | wsl.exe -d FedoraLinux-43 -- bash

# STEP 2 — Copy all non-venv data via tar pipe
tar czf - -C /home/source_user/.prometeo . --exclude=venv 2>/dev/null | wsl.exe -d FedoraLinux-43 -- bash -c 'tar xzf - -C /home/target_user/.prometeo/ && echo "COPY_OK"'

# STEP 3 — Restore target venv from backup
echo 'mv ~/.prometeo_venv_backup ~/.prometeo/venv && echo "VENV_RESTORE"' | wsl.exe -d FedoraLinux-43 -- bash
```

**Execution pattern reference:**

| Pattern | Syntax | When to use |
|---------|--------|-------------|
| **Pipe-to-stdin** | `echo 'cmd && echo "OK"' \| wsl.exe -d Distro -- bash` | Primary pattern for most commands. Avoids bash -c quoting hell. Each command chain is a string passed via stdin. |
| **bash -c** | `wsl.exe -d Distro -- bash -c 'cmd'` | Only when stdin is consumed by data (tar pipe, here-docs). The command must be INLINE with `bash -c` because stdin carries the data stream. |
| **--cd /tmp** | `echo 'cmd' \| wsl.exe -d Distro --cd /tmp -- bash` | Suppresses the "Failed to translate" warning (see Pitfall 11 in SKILL.md). Place `--cd /tmp` BEFORE `--`. |

**Pipe-to-stdin rules:**
- Chain multiple commands with `&&` so a failure stops the chain and the final `echo "OK"` never runs
- Always end the chain with `echo "UNIQUE_MARKER"` so the caller can verify the entire chain succeeded
- Output on success: non-fatal `wsl: Failed to translate` warning (if no `--cd`), followed by `UNIQUE_MARKER`
- The path translation warning appears on EVERY cross-distro `wsl.exe -d` call from inside a WSL session — it is harmless (exit code 0)

**Why this beats `/mnt/c/` for small-to-medium data:**
- No intermediate file to write, manage, or clean up
- The `--exclude=venv` filter is applied mid-stream, not after the fact
- Either the entire pipe completes successfully or extraction never starts (tar checksum)
- Works when `/mnt/c/` is unmounted or unwritable

**When NOT to use this pattern (use Recipe 1 instead):**
- Large datasets (>500 MB compressed): the pipe crosses the Windows kernel boundary on every chunk, which is slower than a file copy via `/mnt/c/`
- When you need to verify the archive before extracting: `tar -tzf /mnt/c/snapshot.tar.gz` to inspect, then extract
- When both distros are on the same Windows machine but you need resumability: `/mnt/c/` file survives interruptions, a pipe doesn't

**Complete worked example — Prometeo data Ubuntu→Fedora (2026-06-08):**

All steps ran via `echo 'commands' | wsl.exe -d FedoraLinux-43 -- bash`:

1. **Backup venv** — `mv ~/.prometeo/venv ~/.prometeo_venv_backup`
2. **Copy data** — `tar czf - --exclude=venv | wsl.exe -d FedoraLinux-43 -- bash -c 'tar xzf -'`
3. **Restore venv** — `mv ~/.prometeo_venv_backup ~/.prometeo/venv`
4. **Symlink** — `rm -f ~/.local/bin/hermes && ln -s ~/.prometeo/venv/bin/hermes ~/.local/bin/hermes`
5. **Env var** — `grep -q "HERMES_HOME" ~/.bashrc || echo 'export HERMES_HOME="$HOME/.prometeo"' >> ~/.bashrc`
6. **Default profile** — attempt `cp profiles/prometeo/config.yaml ~/.prometeo/config.yaml` → skipped: file does not exist in Hermes v0.15.x profile structure (config is generated by `hermes setup`)
7. **Verify** — `source ~/.bashrc && hermes config show` → confirmed HERMES_HOME, symlink, and Hermes v0.15.2 running

**Key lesson from step 6:** Hermes v0.15.x stores config at `$HERMES_HOME/config.yaml` (generated by setup wizard or using defaults). The old pattern of `profiles/<name>/config.yaml` as a separate file does not exist in v0.15.x — profile config is now embedded in the profile directory's own structure. If migrating from Hermes v0.14.x or earlier, `config.yaml` must be re-generated with `hermes setup` — it cannot be copied from the old profile.

---

## Recipe 7: Cold Backup of Agent Data to `/mnt/c/`

**Context:** After an agent has been migrated to a new distro and verified, the source data can be cold-backed up to `/mnt/c/` for safe keeping in case the user needs to revert. This is step 6 from the migration pattern: "Cold backup source to `/mnt/c/<cold-backup>/` (move, don't delete, in case of regression)."

**Pattern:** `quarantine-prometeo-ubuntu.sh` at `/home/prometeo/Aether-Agents/scripts/` is the concrete implementation for Prometeo data. The generic pattern for any agent follows the same structure:

```bash
#!/usr/bin/env bash
set -euo pipefail

SRC="${HOME}/.${AGENT_NAME}"
DEST_BASE="/mnt/c/${BACKUP_PREFIX}"
TS="$(date +%Y%m%d-%H%M%S)"
DEST="${DEST_BASE}/${BACKUP_PREFIX}-${TS}"
SENTINEL="${HOME}/.${AGENT_NAME^^}_QUARANTINED"
DRY_RUN="${QUARANTINE_DRY_RUN:-0}"

run() {
  if [[ "$DRY_RUN" == "1" ]]; then
    echo "  [DRY-RUN] would run: $*"
  else
    eval "$@"
  fi
}

# 1. Size estimate
echo "  size: $(du -sh "$SRC" | awk '{print $1}')"

# 2. Safety — verify agent processes are stopped
# (adapt pgrep pattern to your agent)

# 3. Writable check — mkdir -p + rmdir (NOT mktemp — see Pitfall #9 in SKILL.md)
if ! mkdir -p "$DEST_BASE" 2>/dev/null; then
  echo "  ERROR: $DEST_BASE not writable."
  exit 1
fi
rmdir "$DEST_BASE"

# 4. Execute
run "mkdir -p '$DEST_BASE'"
run "mv '$SRC' '$DEST'"

# 5. Sentinel
if [[ "$DRY_RUN" != "1" ]]; then
  echo "$DEST" > "$SENTINEL"
fi

echo "  Data moved to $DEST"
echo "  To restore: mv '$DEST' '$SRC'"
echo "  To delete later: rm -rf '$DEST'"
```

**Key invariants:**
- **Never `rm` / `rm -rf` the source.** Always `mv` to cold storage. The user can delete later.
- **Idempotent:** if source is already gone, exit 0.
- **Sentinel file** (`~/.<NAME>_QUARANTINED`) records where the data was moved to, so the user can always find it.
- **Dry-run mode** via env var (`QUARANTINE_DRY_RUN=1`) for safe preview.
- **Writable test** uses `mkdir -p + rmdir` (not `mktemp`) — see Pitfall #9.
- **Final report** shows `du -sh` of the destination so the user knows what moved.
