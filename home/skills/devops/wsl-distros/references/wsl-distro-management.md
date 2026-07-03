## WSL Distro Management from PowerShell

### List Distros (clean output from wsl.exe)

```powershell
wsl.exe --list --verbose | tr -d '\0' | grep -v '^$' | cat
```

The `tr -d '\0'` is essential — wsl.exe outputs UTF-16 with null bytes that make output unreadable without it.

### Map Distros to VHDX Locations (Registry)

WSL2 stores VHDX at `C:\Users\<user>\AppData\Local\wsl\{GUID}\ext4.vhdx` by default, but imported distros may use custom paths. The registry has the authoritative mapping:

```powershell
powershell.exe -Command "
Get-ChildItem 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Lxss' -EA SilentlyContinue |
  ForEach-Object {
    \$name = (Get-ItemProperty \$_.PSPath -EA SilentlyContinue).DistributionName
    \$guid = \$_.PSChildName
    \$path = (Get-ItemProperty \$_.PSPath -EA SilentlyContinue).BasePath
    Write-Host ('{0}: {1} ({2})' -f \$guid, \$name, \$path)
  }
"
```

### Unregister a Distro

```powershell
wsl.exe --unregister <distro-name>
```

This permanently deletes the distro and its VHDX. Verified working — the VHDX file and the distro folder are both removed.

### Post-Cleanup Folder Cleanup

Some distros (especially imported ones) leave behind a parent folder with scripts/tarballs:

```powershell
# Check C:\WSL for leftovers after unregistering
powershell.exe -Command "
Get-ChildItem 'C:\WSL' -Force -EA SilentlyContinue | ForEach-Object {
    \$size = 0
    if (\$_.PSIsContainer) {
        \$size = (Get-ChildItem \$_.FullName -Recurse -Force -EA SilentlyContinue |
                 Measure-Object -Property Length -Sum -EA SilentlyContinue).Sum
    } else { \$size = \$_.Length }
    Write-Host ('{0}: {1} MB ({2})' -f \$_.Name, [math]::Round(\$size/1MB,0), \$_.PSIsContainer)
}
"
```

If empty after unregistering, `Remove-Item 'C:\WSL' -Recurse -Force`.

### Typical VHDX Sizes (observed)

| Distro | Typical VHDX | Notes |
|--------|-------------|-------|
| Ubuntu (default, active) | 50-200 GB | Grows with usage, never shrinks automatically |
| Fedora (active) | 10-30 GB | Similar to Ubuntu |
| Clean test distro | 1-5 GB | Fresh install |
| Imported distro | 5-20 GB | Depends on what was imported |

VHDX files are sparse — `du` inside Linux shows used space, but the .vhdx file on Windows may be smaller due to sparse allocation.
