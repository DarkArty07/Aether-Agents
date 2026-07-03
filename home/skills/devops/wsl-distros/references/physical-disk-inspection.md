# Physical Disk Inspection from WSL

When a user asks about "disk partitions" or "where Fedora is installed," the agent's FIRST action must be to **clarify scope**: WSL virtual disks vs. physical host disk. Never assume — ask or probe both.

From inside WSL, standard Linux tools (`lsblk`, `fdisk -l`) only show WSL's virtual disks (VHDX). To inspect the **physical host disk** (the actual NVMe/SSD where Windows and potentially Fedora are dual-booted), use `powershell.exe` from the WSL terminal.

## Quick Diagnostic: Is This Physical or Virtual?

```bash
# Linux tools only show virtual WSL disks
lsblk -o NAME,SIZE,TYPE,MOUNTPOINT,FSTYPE
# If you only see sda/sdb/sdc (small, VHDX-style) → you're seeing WSL virtual disks
# The physical NVMe won't appear here

# PowerShell shows the real hardware
powershell.exe -Command "Get-Disk | Format-Table Number, FriendlyName, @{N='SizeGB';E={[math]::Round(`$_.Size/1GB,1)}}, BusType, PartitionStyle"
# NVMe/SATA/RAID → this is the physical host disk
```

## Step 1: List Physical Disks

```bash
powershell.exe -Command "Get-Disk | Select-Object Number, FriendlyName, @{N='SizeGB';E={[math]::Round(`$_.Size/1GB,1)}}, BusType, PartitionStyle | Format-Table -AutoSize"
```

Output example:
```
Number FriendlyName       SizeGB BusType PartitionStyle
------ ------------       ------ ------- ---------------
     0 XPG SPECTRIX S40G    953.8 NVMe    GPT
```

`BusType: NVMe` = physical NVMe SSD. `PartitionStyle: GPT` = modern partition table.

## Step 2: List Partitions with GPT Type GUIDs

```bash
powershell.exe -Command "Get-Partition -DiskNumber 0 | Select-Object PartitionNumber, @{N='SizeGB';E={[math]::Round(`$_.Size/1GB,1)}}, Type, GptType | Format-Table -AutoSize"
```

The `GptType` GUID tells you exactly what each partition contains, even when Windows can't read the filesystem.

## Step 3: Get Filesystem Info per Partition

```bash
powershell.exe -Command "Get-Disk -Number 0 | Get-Partition | ForEach-Object { `$p = `$_ ; `$vol = Get-Volume -Partition `$p -ErrorAction SilentlyContinue ; [PSCustomObject]@{ Partition=`$p.PartitionNumber; Drive=`$p.DriveLetter; 'Size(GB)'=[math]::Round(`$p.Size/1GB,1); Type=`$p.Type; FS=`$vol.FileSystem; Label=`$vol.FileSystemLabel; 'Free(GB)'=if(`$vol){[math]::Round(`$vol.SizeRemaining/1GB,1)}else{'N/A'} } } | Format-Table -AutoSize"
```

Linux partitions show `FS=` as empty and `Free(GB)=N/A` because Windows can't read ext4/btrfs/xfs. The `GptType` GUID from Step 2 is the key identifier.

## GPT Type GUID Reference (Partition Identification)

| GUID | Type | What It Contains |
|------|------|-----------------|
| `c12a7328-f81f-11d2-ba4b-00a0c93ec93b` | EFI System Partition (ESP) | UEFI bootloader (FAT32, usually 100-512 MB) |
| `e3c9e316-0b5c-4db8-817d-f92df00215ae` | Microsoft Reserved (MSR) | Reserved space for Windows (16-128 MB, raw) |
| `ebd0a0a2-b9e5-4433-87c0-68b6b72699c7` | Windows Basic Data | Windows C: drive (NTFS) |
| `0fc63daf-8483-4772-8e79-3d69d8477de4` | Linux Filesystem Data | Linux root, /boot, /home (ext4/btrfs/xfs/LVM) |
| `de94bba4-06d1-4d40-a16a-bfd50179d6ac` | Windows Recovery | Windows Recovery Environment (WinRE, NTFS) |
| `e6d6d379-f507-44c2-a23c-238f2a3df928` | Linux LVM | LVM physical volume |
| `933ac7e1-2eb4-4f13-b844-0e14e2aef915` | Linux /home | Separate /home partition |
| `bc13c2ff-59e6-4262-a352-b275fd6f7172` | Linux /boot | Separate /boot partition |
| `0657fd6d-a4ab-43c4-84e5-0933c84b4f4f` | Linux Swap | Swap partition |

**Common dual-boot layout (single NVMe, shared ESP):**

```
#  Size     Type              Purpose
1  100 MB   EFI System        Shared ESP (Windows + Fedora boot)
2   16 MB   MSR               Windows reserved
3  697 GB   Windows Data      Windows C: (NTFS)
5    2 GB   Linux Filesystem  Fedora /boot (ext4)
6  254 GB   Linux Filesystem  Fedora / (ext4/btrfs/xfs, possibly LVM)
4  0.7 GB   Windows Recovery  WinRE
```

Key observations for dual-boot:
- **Shared ESP** (partition 1): Both Windows and Fedora boot from the same EFI partition. No separate ESP for Linux.
- **Linux partitions show as "Unknown"** in Windows — the GptType GUID is the only identifier.
- **No separate swap partition** — Fedora usually uses ZRAM or a swap file instead.

## PowerShell Escaping from WSL (Critical)

When calling `powershell.exe` from a WSL `bash -c` command, `$` signs in PowerShell variable references MUST be escaped with backtick: `` `$_.Size `` not `$_.Size`. Otherwise bash interprets them as shell variables and the PowerShell command fails.

The commands above include the correct escaping for copy-paste use. When building new PowerShell commands dynamically, remember to escape `$` as `` `$ ``.

## Mounting Physical Linux Partitions from WSL (READ BEFORE ATTEMPTING)

After identifying Linux partitions, the natural next step is to mount them to read their contents. This section documents what works, what fails, and why.

### The `wsl --mount` Command

```powershell
# Mount a specific partition from the physical disk (run from admin PowerShell)
wsl --mount \\.\PHYSICALDRIVE0 --partition 6 --type ext4
```

After successful mount, the partition appears as a new device inside WSL (e.g., `/dev/sdf`). Mount it normally:

```bash
sudo mkdir -p /mnt/fedora
sudo mount /dev/sdf /mnt/fedora
ls /mnt/fedora/home/<user>/Desktop/
```

### FATAL: `ERROR_SHARING_VIOLATION` — Disk Locked by Windows

**Symptom:**
```
No se pudo conectar el disco "\\.\PHYSICALDRIVE0" a WSL2:
El proceso no tiene acceso al archivo porque está siendo utilizado por otro proceso.
Código de error: Wsl/Service/AttachDisk/MountDisk/ERROR_SHARING_VIOLATION
```

**Root cause:** `wsl --mount` requires **exclusive access to the entire physical disk**, not just the target partition. When Windows boots from a partition on that same disk (C:), Windows holds a permanent lock on the disk. `wsl --mount` cannot obtain the exclusive handle it needs, even for non-Windows partitions.

**This is NOT fixable** from software — it's a fundamental limitation of how WSL2 attaches physical disks. The disk is shared between the host OS and WSL2, but WSL2 needs exclusive access for the mount operation.

### Attempts That FAIL

| Attempt | Command | Result |
|---------|---------|--------|
| Read-only mount | `wsl --mount ... --type ext4 -o ro` | Same `ERROR_SHARING_VIOLATION` |
| Bare mode (no mount, just expose) | `wsl --mount \\.\PHYSICALDRIVE0 --bare` | Same `ERROR_SHARING_VIOLATION` |
| Different partition | `wsl --mount ... --partition 5` | Same error — the lock is on the disk, not the partition |

### UAC Elevation From Background Processes

`Start-Process -Verb RunAs` from a non-interactive WSL session **cannot display the UAC dialog**. The process exits with code `-1` or the user sees "The user has cancelled the operation" because the dialog never appeared.

**Workaround:** The user must manually open an **admin PowerShell window** (Win+X → Terminal (Admin)) and run the `wsl --mount` command there. The agent cannot automate elevation for `wsl --mount`.

### SOLUTION: WinBtrfs Driver (Windows ↔ WSL dual-boot access)

For dual-boot systems where Fedora/Nobara uses **btrfs** (default since Fedora 33), the reliable no-reboot solution is the **WinBtrfs driver**:

1. **Download WinBtrfs** from https://github.com/maharmstone/btrfs/releases
2. **Install driver** (admin PowerShell): `pnputil /add-driver "<path>\amd64\btrfs.inf" /install`
3. **Result:** Windows auto-detects the btrfs partition and assigns a drive letter (e.g., D:)
4. **Access from WSL:** `sudo mount -t drvfs D: /mnt/d` → files at `/mnt/d/@home/<user>/`

**btrfs subvolumes (Fedora/Nobara layout):**
```
D:
├── @/         → root filesystem (/)
└── @home/     → /home partition
     └── <user>/ → user's home directory
```

**Alternative for ext4:** Install ext2fsd (ext2fsd.com) for ext4 filesystems. Same pattern: install → Windows assigns drive letter → WSL mounts via drvfs.

**Why this beats rebooting:** The session persists. No interruption. Bidirectional read/write between Windows and Fedora without leaving the current environment.

### Fallback Options (if WinBtrfs fails)

| Option | What to do | Reliability |
|--------|-----------|-------------|
| **Linux Reader** | DiskInternals Linux Reader — read-only, no driver install | 90% |
| **wsl --mount on secondary disk** | Only works if Fedora is on a disk WITHOUT Windows C: | N/A for single-disk dual-boot |
| **Live USB** | Boot a Linux live USB, mount the NVMe partition | 100% (requires reboot) |

**Note:** Do NOT suggest rebooting/booting Fedora natively as a solution — it kills the current session and the user is asking for access FROM the current environment.

### When `wsl --mount` DOES Work

`wsl --mount` works perfectly for:
- **External USB drives** with Linux partitions (not in use by Windows)
- **Secondary internal disks** dedicated entirely to Linux (no Windows partitions on them)
- **VHDX files** (use `wsl --mount --vhd` instead)

The failure only occurs when the disk contains the **active Windows system partition (C:)**.

## PowerShell Escaping from WSL (Critical)

When calling `powershell.exe` from a WSL `bash -c` command, `$` signs in PowerShell variable references MUST be escaped with backtick: `` `$_.Size `` not `$_.Size`. Otherwise bash interprets them as shell variables and the PowerShell command fails.
The commands above include the correct escaping for copy-paste use. When building new PowerShell commands dynamically, remember to escape `$` as `` `$ ``.

## Limitations

- Cannot read Linux filesystem contents (ext4/btrfs/xfs) from PowerShell — the partitions are visible but their data is opaque to Windows.
- To read the actual Linux partition data via WSL, `wsl --mount` only works when the physical disk does NOT contain the active Windows C: partition. See "Mounting Physical Linux Partitions" above for the full error chain and fallbacks.
- `Get-Volume` returns `N/A` for Linux partitions — use `GptType` GUIDs for identification instead.
