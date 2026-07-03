# Windows Cleanup Commands (from WSL)

All commands below are run from within a WSL terminal.

## Check Windows Disk Usage

```bash
df -h /mnt/c/
```

## List Hidden System Files on C:\

```bash
cmd.exe /c 'dir /a:h C:\'
```

## PowerShell: System .sys Files

```bash
powershell.exe -Command "
Get-ChildItem C:\ -Force -ErrorAction SilentlyContinue |
  Where-Object { \$_.Name -match '\.sys' } |
  Select-Object Name, @{N='SizeGB';E={[math]::Round(\$_.Length/1GB,1)}} |
  Format-Table -AutoSize
"
```

## Check Hibernation Status

```bash
cmd.exe /c "powercfg /a"
```

## Disable Hibernation from WSL (Admin elevation works!)

```powershell
# Verified working from WSL — Start-Process -Verb RunAs triggers UAC elevation
# Deletes hiberfil.sys immediately (typically 20-32 GB)
powershell.exe -Command "
Start-Process 'powercfg.exe' -ArgumentList '/h','off' -Verb RunAs -Wait -ErrorAction Stop
"
```

Check result: `powershell.exe -Command "Test-Path C:\hiberfil.sys"` should return `False`.

Alternative (if UAC is disabled or running as SYSTEM):
```cmd
powercfg /h off
```

## Windows Temp Size

```bash
powershell.exe -Command "
\$tempSize = (Get-ChildItem C:\Windows\Temp -Recurse -EA SilentlyContinue |
  Measure-Object Length -Sum).Sum
Write-Host ('Windows\Temp: {0} GB' -f [math]::Round(\$tempSize/1GB,1))
"
```

## Recycle Bin Check

```bash
powershell.exe -Command "
\$shell = New-Object -ComObject Shell.Application
\$rb = \$shell.NameSpace(0xa)
Write-Host ('Recycle Bin items: {0}' -f \$rb.Items().Count)
"
```

## WSL VHDX Files

```bash
powershell.exe -Command "
Get-ChildItem 'C:\Users\*\AppData\Local\Packages\' -Directory -EA SilentlyContinue |
  Where-Object { \$_.Name -match 'Canonical|Ubuntu|WSL|Fedora' } |
  ForEach-Object {
    Get-ChildItem \$_.FullName -Recurse -Filter '*.vhdx' -EA SilentlyContinue |
    ForEach-Object {
      Write-Host ('{0}: {1} GB' -f \$_.FullName, [math]::Round(\$_.Length/1GB,1))
    }
  }
"
```

## Disk Cleanup Utility (silent)

```bash
cmd.exe /c "cleanmgr /sagerun:1"
```

## Venv and Node_modules Scanning (Windows)

Developer environments accumulate massive dependency trees. Python venvs (200MB-5GB each) and node_modules (100MB-1GB each) are often the biggest space hogs on Windows dev machines. Scanning from WSL is slow, so provide an explicit list to PowerShell.

### Step 1: Discover all venv/node_modules locations

```powershell
# Find all venv and node_modules dirs under Desktop (fast — just names, no sizes)
powershell.exe -Command "
Get-ChildItem 'C:\Users\chris\Desktop' -Recurse -Directory -Force -EA SilentlyContinue |
  Where-Object { $_.Name -match '^(node_modules|\.venv|venv|env)$' } |
  ForEach-Object { $_.FullName.Replace('C:\Users\chris\Desktop\','') }
"
```

### Step 2: Measure sizes (explicit list, one at a time)

Since `du`-style recursive measurement is slow, build an explicit `$paths` array from Step 1 and measure each:

```powershell
powershell.exe -Command "
$venvs = @(
    'C:\Users\chris\Desktop\path\to\.venv',
    'C:\Users\chris\Desktop\path\to\node_modules'
    # ... paste all paths from Step 1
)
$total = 0
$venvs | ForEach-Object {
    if (Test-Path $_) {
        $size = (Get-ChildItem $_ -Recurse -Force -EA SilentlyContinue |
                 Measure-Object -Property Length -Sum -EA SilentlyContinue).Sum
        $sizeMB = [math]::Round($size/1MB,0)
        $total += $sizeMB
        Write-Host ('  {0} MB - {1}' -f $sizeMB, $_.Replace('C:\Users\chris\Desktop\',''))
    }
}
Write-Host ('  TOTAL: {0} GB' -f [math]::Round($total/1024,1))
"
```

### Step 3: Classify into safe-to-delete vs keep

| Category | Safe to Delete? | Example |
|----------|----------------|---------|
| `archivados/DEPRECATED/*/.venv` | YES — project is archived | 500MB-800MB each |
| Duplicate `.openclaw` copies | YES — check if 3 copies exist | 200MB each |
| Backup `_recursos/*/sdk/venv` | YES — backup of old SDK | 500MB+ |
| `activos/*/.venv` | NO — active projects | Ask user |
| `activos/*/node_modules` | NO — active projects | Ask user |

### Typical Findings (from real scans)

- **Python venvs**: 8-15 GB total, with deprecated projects accounting for 40-60%
- **node_modules**: 3-6 GB total, with SillyTavern, Gemini CLI, and mindcraft being large deprecated offenders
- **.openclaw workspace**: Often duplicated 3x (`.openclaw/`, `DevTools/.openclaw/`, `DevTools/VERSIONES PROMETEO/`) — each copy has identical `.venv` + `node_modules`

## Notes

- `du -sh /mnt/c/Users/` from Linux is extremely slow — prefer PowerShell for Windows analysis
- `hiberfil.sys` size ≈ 40-100% of installed RAM
- `pagefile.sys` is Windows swap — NEVER delete
- WSL VHDX files are sparse (on-disk < virtual size)

## Iterative Scanning Pattern (Timeout-Safe)

Recursive `-Recurse` on large Windows dirs (Users, Windows, Desktop) times out at 120s from WSL. Scan one level at a time:

```powershell
# Top-level C:\ scan
Get-ChildItem 'C:\' -Directory -Force -EA SilentlyContinue | ForEach-Object {
    $size = 0
    try {
        Get-ChildItem $_.FullName -Force -EA SilentlyContinue | ForEach-Object {
            if ($_.PSIsContainer) {
                $size += (Get-ChildItem $_.FullName -Recurse -Force -EA SilentlyContinue |
                         Measure-Object Length -Sum -EA SilentlyContinue).Sum
            } else { $size += $_.Length }
        }
    } catch {}
    [PSCustomObject]@{Folder=$_.Name; SizeGB=[math]::Round($size/1GB,1)}
} | Sort-Object SizeGB -Descending | Select -First 15 | Format-Table -AutoSize
```

Then drill ONE folder per call:
```powershell
Get-ChildItem 'C:\Program Files' -Directory -Force -EA SilentlyContinue | ForEach-Object {
    $size = (Get-ChildItem $_.FullName -Recurse -Force -EA SilentlyContinue |
             Measure-Object Length -Sum -EA SilentlyContinue).Sum
    [PSCustomObject]@{Folder=$_.Name; SizeGB=[math]::Round($size/1GB,1)}
} | Sort-Object SizeGB -Descending | Select -First 10 | Format-Table -AutoSize
```

## AppData\Local\Temp Cleanup

Often 5-15 GB. Scan from WSL:
```powershell
powershell.exe -Command "
\$size = (Get-ChildItem 'C:\Users\chris\AppData\Local\Temp' -Recurse -Force -EA SilentlyContinue |
  Measure-Object Length -Sum -EA SilentlyContinue).Sum
Write-Host ('AppData\Local\Temp: {0} GB' -f [math]::Round(\$size/1GB,1))
"
```

Clean from WSL via PowerShell (handles locked files better than bash `rm -rf`):
```powershell
powershell.exe -Command "
Get-ChildItem 'C:\Users\chris\AppData\Local\Temp' -Force -EA SilentlyContinue | ForEach-Object {
    try { Remove-Item $_.FullName -Recurse -Force -EA Stop } catch {}
}
"
```

Alternative (may skip locked files):
```bash
rm -rf /mnt/c/Users/chris/AppData/Local/Temp/*
```

## Game Recording Cleanup (Overwolf, NVIDIA, Radeon ReLive)

Auto-saved recordings accumulate fast:
- Overwolf: `C:\Users\<user>\Videos\Overwolf\`
- NVIDIA ShadowPlay: `C:\Users\<user>\Videos\NVIDIA\`
- Radeon ReLive: `C:\Users\<user>\Videos\Radeon ReLive\`

```powershell
# Check Overwolf recordings
Get-ChildItem 'C:\Users\*\Videos\Overwolf' -Recurse -Force -EA SilentlyContinue |
    Measure-Object Length -Sum | ForEach-Object {
    Write-Host ('Overwolf: {0} GB' -f [math]::Round($_.Sum/1GB,1))
}
```
