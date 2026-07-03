# WSL Cross-Distro Delegation Pitfalls

## The Interop Breakage Loop

When orchestrating across WSL distros via `wsl.exe -d <distro>`, the WSL interop layer
(binfmt_misc) can break silently. This is the most common cross-distro failure mode.

### Detection (pre-delegation check)

Before delegating ANY cross-distro command, verify interop is alive:

```bash
cat /proc/sys/fs/binfmt_misc/WSLInterop 2>/dev/null
# Expected: "enabled" or at least the file exists
# Failure: "No such file or directory" → interop is DOWN
```

Or quick smoke test:
```bash
wsl.exe -d FedoraLinux-43 -- echo "INTEROP_OK" 2>&1
# Expected: INTEROP_OK
# Failure: "cannot execute binary file: Exec format error"
```

### Root Cause

After `wsl --shutdown` (or WSL restart), the binfmt_misc registration for
`WSLInterop` can fail to re-register. The `/proc/sys/fs/binfmt_misc/` mount
may be present but missing the `WSLInterop` entry.

### Fix (user must execute)

The agent CANNOT fix this autonomously (requires sudo, and sudo piping is blocked
by security hooks). The user must run from **Windows PowerShell**:

```powershell
wsl --shutdown
```

Then reopen the WSL terminal. Interop should be restored.

### Why Not sudo Fix In-Place?

The command to register interop:
```bash
sudo sh -c 'echo ":WSLInterop:M::MZ::/init:PF" > /proc/sys/fs/binfmt_misc/register'
```
...often fails with "I/O error" even when binfmt_misc is mounted, because the
kernel module state is corrupted. Only a full `wsl --shutdown` reliably resets it.

### Orchestrator Workflow

When orchestrating cross-distro:

1. **Check interop first** — one quick `wsl.exe -d <distro> -- echo OK`
2. **Interop UP** → proceed with delegation
3. **Interop DOWN** → escalate to user immediately with the `wsl --shutdown` command
4. **Do NOT let Daimons investigate** — Hefesto/Etalides will burn 50+ seconds
   and 9+ tool calls probing /etc/wsl.conf, mounts, and binfmt_misc before
   reaching the same conclusion. The orchestrator (Hermes) should catch this
   at the pre-delegation gate.

### Memory Reference

The memory system also tracks this: "Cross-distro delegation: WSL interop
binfmt_misc: if register write fails with I/O error even when mounted,
fallback is wsl --shutdown from Windows + reopen terminal."
