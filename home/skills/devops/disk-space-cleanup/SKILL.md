---
name: disk-space-cleanup
description: Disk space analysis, cleanup proposals, and safe deletion on Linux VMs (including WSL). Structured level-based approach with dependency verification. For Windows-side cleanup from WSL (VHDX, hibernation, AppData), see the `wsl-distros` skill.
triggers:
  - disk space low or full
  - VM grown too large
  - clean up disk / free space
  - df -h shows high usage
  - user asks to reclaim storage
---

# Disk Space Cleanup

Structured approach to analyze and reclaim disk space on Linux/WSL VMs.

## When to Use

- User reports disk space issues or asks to clean up
- VM has grown unexpectedly large
- Periodic maintenance requests

## Workflow

### Phase 1 — Scan and Map

```bash
# Top-level view
df -h /

# User home breakdown (visible dirs)
du -sh /home/$USER/* 2>/dev/null | sort -rh | head -15

# Hidden dirs (where caches live)
du -sh /home/$USER/.* 2>/dev/null | sort -rh | head -20

# Drill into .cache/ subdirs
du -sh /home/$USER/.cache/*/ 2>/dev/null | sort -rh | head -10

# Drill into .local/ (often overlooked — uv, claude, cursor-agent, pnpm)
du -sh ~/.local/share/*/ 2>/dev/null | sort -rh | head -10
du -sh ~/.local/bin/ ~/.local/lib/ 2>/dev/null
```

If `du` times out on large dirs, use `timeout 30` or skip and estimate from partial results.

### Phase 2 — Categorize into Levels

Present a structured proposal with these levels:

| Level | Category | Risk | Example |
|-------|----------|------|---------|
| 1 | Caches (download/pkg managers) | Zero — regenerate on use | pip, uv, npm, huggingface, whisper |
| 2 | User-confirmed deletions | Zero — user explicitly said delete | old projects, training data |
| 3 | Installed tools/runtimes | Low — only if user confirms they don't use them | go, bun, rustup, conda, .gemini, IDE servers |
| 4 | Selective cache cleanup | Low — requires selection | huggingface-cli delete-cache |
| 5 | System-level | Medium — needs sudo | apt autoremove, journalctl vacuum |

**Always present the proposal BEFORE executing.** Let user approve/reject per level.

### Phase 3 — Dependency Verification (CRITICAL)

Before deleting any tool/runtime (conda, nvm, go, bun, etc.):

1. **Check .bashrc/.zshrc for PATH entries:**
   ```bash
   grep -n "conda\|miniconda\|nvm\|\.bun\|\.cargo" ~/.bashrc ~/.zshrc 2>/dev/null
   ```

2. **Check if active projects depend on it:**
   - Where is the active Python? `which python3` vs conda's python
   - Where is hermes/your agent? `which hermes` → check if it's in a venv or in the tool being deleted
   - For conda: `ls ~/miniconda3/envs/` — are any of those in use?

3. **Verify the critical binary is NOT in the tool being deleted:**
   ```bash
   # Example: verify hermes is in its own venv, not in conda
   /path/to/venv/bin/python3 -c "import hermes_cli; print(hermes_cli.__file__)"
   ```

### Phase 4 — Execute by Level

Run each approved level as a batch. For each:
- Show the command before running
- Capture bytes/files removed from tool output
- If any command fails, report and continue with the rest

### Phase 5 — Verify

```bash
# Post-cleanup disk usage
df -h /

# Health check critical binaries
hermes --version  # or whatever was at risk
python3 --version
```

## Common Caches and Commands

| Cache | Command | Typical Size |
|-------|---------|-------------|
| pip | `pip cache purge` | 5-20 GB |
| uv | `uv cache clean` | 10-30 GB |
| npm | `npm cache clean --force` | 5-10 GB |
| whisper | `rm -rf ~/.cache/whisper/` | 1-2 GB |
| Homebrew | `rm -rf ~/.cache/Homebrew/` | 1-2 GB |
| HuggingFace | `huggingface-cli delete-cache` or `rm -rf ~/.cache/huggingface/` | 5-50 GB |
| Playwright | `rm -rf ~/.cache/ms-playwright/` + `ms-playwright-go/` | 500MB-1GB |
| camoufox | `rm -rf ~/.cache/camoufox/` | 1-2 GB |
| go-build | `rm -rf ~/.cache/go-build/` | 50-200 MB |
| node-gyp | `rm -rf ~/.cache/node-gyp/` | 50-100 MB |
| cloud-code | `rm -rf ~/.cache/cloud-code/` | 100-200 MB |
| typescript | `rm -rf ~/.cache/typescript/` | 20-50 MB |
| puccinialin | `rm -rf ~/.cache/puccinialin/` | 50-100 MB |

## Cross-Platform: Windows Cleanup from WSL

For Windows-side cleanup (hiberfil.sys, VHDX management, disk analysis, Temp files, AppData scanning, game recordings, Chrome reinstall, Windows app repair, and WSL distro management), see the **`wsl-distros`** skill and its references:

- `references/windows-cleanup-from-wsl.md` — PowerShell commands for hibernation disable, disk analysis, VHDX scanning, iterative directory scanning, temp/game cleanup
- `references/windows-app-repair.md` — Chrome reinstall, Windows app repair, cleanup targets table, developer dependency tree scanning
- `references/wsl-distro-management.md` — WSL distro list, VHDX mapping via registry, distro unregister workflow

## Pitfalls

1. **NEVER delete a tool without verifying dependencies first.** Conda/nvm/go might be the Python/Node runtime for active projects. Check `which`, PATH, and venv locations.

2. **pip/uv cache purge is SAFE** — it only removes downloaded packages, not installed ones. Virtual environments are untouched.

3. **conda envs are NOT in the pip cache.** Deleting miniconda3 removes all conda environments. Verify none are active.

4. **HuggingFace cache is tricky** — models are large but some may be actively used. Use `huggingface-cli delete-cache` for interactive selection rather than `rm -rf`.

5. **npm cache clean --force** prints a warning about "recommended protections disabled" — this is normal, ignore it.

6. **uv cache can be much larger than expected** — `du` estimated 12GB but actual removal was 27GB. Trust `uv cache clean` output over `du` estimates.

7. **Two-pass npm cleanup** — `npm cache clean --force` clears `_cacache/` but `_npx/` may remain (~1GB+). Always re-check `du -sh ~/.npm/` after first clean; do `rm -rf ~/.npm/_npx/` if still large.

8. **Backup tarballs** — check for `.tar.gz` backups in home dir. User may have forgotten about them. Ask before deleting.

9. **miniconda.sh installer** — the installer script (~155MB) stays in home after installation. Safe to delete once conda is installed (or if removing conda entirely).

10. **STRICT SCOPE COMPLIANCE**: Chris will specify exactly what to clean ("solo los caches", "nada mas"). When he does, clean ONLY that — do not sneak in extra deletions even if they seem safe. If he wants a broader cleanup, he'll ask for a proposal first ("hazme una propuesta"). The proposal-approve-execute pattern is the default for multi-level cleanups; single-scope ("just caches") means execute directly without additional suggestions.

For Windows or WSL-specific pitfalls (hibernation, VHDX, wsl.exe UTF-16 output, /mnt/ exclusion from du, admin elevation), see the **`wsl-distros`** skill.
