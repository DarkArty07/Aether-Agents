# Cross-FS rsync Pattern (WSL ext4 → DrvFS)

Worked example based on the Prometeo Ubuntu→Fedora quarantine (2026-06-05):
4.2 GB, WSL ext4 → /mnt/c/ DrvFS, `mv` timed out at 10 min, replaced with `rsync -aHAX --remove-source-files`.

## Problem

Moving large directories from the WSL ext4 filesystem to the Windows DrvFS mount
(`/mnt/c/`) with `mv` is **not safe**:

- `mv` on **different filesystems** performs a copy + delete (not a metadata rename).
- It is **not resumable**. If the process is killed or times out, the destination
  has a partial set of files and the source is partially consumed.
- In WSL, DrvFS is slow for many small files. A 4.2 GB directory with ~113k files
  takes well over 10 minutes. If the shell or session has a timeout (some TUI
  configurations, background job limits), the transfer is abandoned mid-way.

**Concrete result (2026-06-05):** After 10 minutes, `mv` was killed. Destination
had ~11,000 files (10%), source was missing those files and couldn't be resumed.
Had to abort and plan a recovery.

## Solution: `rsync` with `--remove-source-files`

`rsync` replicates the "move" semantics file-by-file with built-in resumability:

```bash
rsync -aHAX --info=progress2 --remove-source-files --log-file=/tmp/prometeo-quarantine.log "$SRC/" "$DEST/"
find "$SRC" -type d -empty -delete
```

### Flag breakdown

| Flag | Purpose |
|------|---------|
| `-a` | Archive mode: recursive, preserve symlinks, perms, timestamps, owner, group |
| `-H` | Preserve hard links. Safe to include even if DrvFS doesn't support them — silently skipped. |
| `-A` | Preserve ACLs. Same safety note. |
| `-X` | Preserve extended attributes. Same safety note. |
| `--info=progress2` | Show aggregated progress (current file + overall % + speed + ETA) |
| `--remove-source-files` | Delete each file from source AFTER it's fully transferred to dest |
| `--log-file=...` | Log every file transferred (for debugging / monitoring) |
| `$SRC/` (trailing slash) | Copy *contents* of `$SRC/` into `$DEST/`, not `$SRC` as a subdirectory |
| `find ... -empty -delete` | Remove empty source subdirectories left by `--remove-source-files` |

### Why `-HAX` when DrvFS doesn't fully support them?

rsync gracefully degrades: unsupported features produce warnings but don't fail.
Including `-HAX` is harmless and forward-compatible (if DrvFS or a future target
supports them, they're preserved). The flags are also the same as a typical
system-backup `rsync`, so the command can be reused verbatim for other targets.

## Full Script Template

The `quarantine-prometeo-ubuntu.sh` script at
`~/Aether-Agents/scripts/quarantine-prometeo-ubuntu.sh` is the canonical example.
Key structure:

```bash
#!/usr/bin/env bash
set -euo pipefail

DRY_RUN="${QUARANTINE_DRY_RUN:-0}"
FORCE="${QUARANTINE_FORCE:-0}"
SRC="${HOME}/.prometeo"
DEST_BASE="/mnt/c/prometeo-cold-backups"
TS="$(date +%Y%m%d-%H%M%S)"
DEST="${DEST_BASE}/prometeo-${TS}"
SENTINEL="${HOME}/.PROMETEO_QUARANTINED"
LOGFILE="/tmp/prometeo-quarantine.log"

run() {
  if [[ "$DRY_RUN" == "1" ]]; then echo "  [DRY-RUN] would run: $*"
  else eval "$@"; fi
}

# === Source state ===
[[ -e "$SRC" ]] || { echo "Source missing — idempotent exit"; exit 0; }
[[ -d "$SRC" ]] || { echo "Source not a directory"; exit 1; }
SIZE=$(du -sh "$SRC" | awk '{print $1}')

# === Safety checks (skipped if FORCE=1) ===
[[ "$FORCE" == "1" ]] || {
  # Check no rival processes alive
  orphans=$(pgrep -af 'pattern-to-exclude' || true)
  # Check /mnt/c/ writable (mkdir + rmdir, NOT mktemp — DrvFS quirk)
  mkdir -p "$DEST_BASE" && rmdir "$DEST_BASE"
}

# === Plan ===
echo "source: $SRC ($SIZE)  dest: $DEST  command: rsync -aHAX ..."

# === Executing ===
run "mkdir -p '$DEST_BASE'"
run "rsync -aHAX --info=progress2 --remove-source-files --log-file=$LOGFILE '$SRC/' '$DEST/'"
run "find '$SRC' -type d -empty -delete"

# === After ===
if [[ -d "$DEST" ]]; then
  echo "$DEST" > "$SENTINEL"
  echo "Transferred: $(du -sh "$DEST")"
fi
```

## Monitor Script Pattern

Companion script (`quarantine-prometeo-ubuntu-monitor.sh`) — read-only, re-runnable:

```bash
#!/usr/bin/env bash
# No set -e — this script MUST complete even if files are missing
rsync_pids=$(pgrep -af 'rsync.*quarantine-prometeo-ubuntu' || true)
[[ -n "$rsync_pids" ]] && echo "RUNNING" || echo "NOT running"
echo "Source: $(find "$SRC" -type f 2>/dev/null | wc -l) files"
echo "Size:   $(du -sh "$SRC" 2>/dev/null | awk '{print $1}')"
for d in /mnt/c/prometeo-cold-backups/prometeo-*; do
  [[ -d "$d" ]] && echo "$(basename $d): $(find "$d" -type f | wc -l) files"
done
[[ -f /tmp/prometeo-quarantine.log ]] && tail -10 /tmp/prometeo-quarantine.log
```

## Idempotent Behavior

- **Source doesn't exist** → exit 0 (nothing to do, already cleaned up or never created)
- **rsync interrupted** → re-run; it picks up where it left off (rsync compares file
  sizes/modtimes and skips matching files)
- **Already complete** → rsync finishes near-instantly (no files to transfer), `find`
  finds no non-empty dirs, sentinel written again (harmless overwrite)
- **FORCE=1** → skip safety checks (use when you've already verified the environment
  manually, e.g., in an interactive recovery session)

## When to Use `mv` Instead

- **Same filesystem (ext4 → ext4):** `mv` is instant (metadata-only rename).
- **Small datasets (< 100 MB, < 1000 files):** `mv` completes quickly enough.
- **You need atomic cutover:** `mv` on same FS is atomic. For cross-FS, do
  `rsync` to a temp dir, then `mv` the temp dir (which IS on the same FS).
