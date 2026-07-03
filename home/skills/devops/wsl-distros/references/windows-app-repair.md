# Windows App Repair & Reinstall (from WSL)

When aggressive cleanup deletes program files (not just caches), Windows apps may crash on launch. Common symptoms:
- Chrome: exits immediately with code `-2147483645` (0x80000003 = EXCEPTION_BREAKPOINT) — missing DLLs
- Apps that "won't open" after cleanup

## Chrome Reinstall Pattern (from WSL)

Chrome's silent installer (`/silent /install`) often **fails silently** when repairing a corrupted installation — it skips files it thinks are present but are actually broken. The reliable pattern:

```powershell
# 1. Kill any zombie Chrome processes
powershell.exe -Command "Get-Process chrome -ErrorAction SilentlyContinue | Stop-Process -Force"

# 2. Remove ALL Chrome directories (force clean slate)
powershell.exe -Command "
Remove-Item -Recurse -Force 'C:\Program Files\Google\Chrome' -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force 'C:\Program Files (x86)\Google\Chrome' -ErrorAction SilentlyContinue
"

# 3. Download fresh installer
powershell.exe -Command "
$Path = 'C:\Temp\chrome_installer.exe'
Invoke-WebRequest -Uri 'https://dl.google.com/chrome/install/latest/chrome_installer.exe' -OutFile $Path
"

# 4. INTERACTIVE install (NOT /silent /install — that skips broken files)
powershell.exe -Command "Start-Process 'C:\Temp\chrome_installer.exe' -Wait"

# 5. Verify Chrome is running
powershell.exe -Command "
Start-Process 'C:\Program Files\Google\Chrome\Application\chrome.exe'
Start-Sleep -Seconds 5
Get-Process chrome -ErrorAction SilentlyContinue | Select-Object Id, ProcessName | Format-Table
"
```

**Key lesson:** Always use interactive install when repairing. Silent install is for fresh installs on clean systems only.

## Generic Windows App Reinstall Pattern (from WSL)

```powershell
# 1. Find the uninstaller via registry
powershell.exe -Command "
Get-ChildItem 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\' -EA SilentlyContinue |
  Get-ItemProperty | Where-Object { $_.DisplayName -like '*AppName*' } |
  Select-Object DisplayName, UninstallString | Format-List
"

# 2. If uninstaller exists, run it cleanly first
powershell.exe -Command "Start-Process 'uninstaller_path' -Wait"

# 3. If uninstaller is missing (files already deleted), force-remove directories
powershell.exe -Command "Remove-Item -Recurse -Force 'C:\Program Files\AppName' -EA SilentlyContinue"

# 4. Reinstall (download installer + run interactively)
# 5. Verify with Get-Process
```

## Common Windows Cleanup Targets (from Session Data)

| Location | Typical Size | What It Is |
|----------|-------------|------------|
| AppData\Local\Temp | 5-15 GB | User temp files — safe to clear |
| AppData\Roaming\Cursor | 2-5 GB | Cursor IDE data |
| AppData\Roaming\npm | 1-2 GB | npm cache (Windows side) |
| ProgramData\Package Cache | 1-3 GB | Visual Studio/MSI installers |
| ProgramData\NVIDIA Corporation\NVIDIA App | 5-10 GB | NVIDIA driver packages, shader cache |
| Videos\Overwolf | 5-15 GB | Auto-saved game recordings (LoL, etc.) |
| Desktop\DEVELOPERSPROJECTS\archivados | 10-20 GB | Archived projects |
| WinSxS | 10-15 GB | Windows component store (use DISM, not manual delete) |

## Developer Dependency Trees (venv + node_modules)

Often 10-20 GB on dev machines. Scan for `.venv`, `venv`, `node_modules` dirs under `Desktop\DEVELOPERSPROJECTS\` and `DevTools\`. Deprecated projects with abandoned venvs are the biggest offenders.

```powershell
# Find all venv and node_modules dirs (fast — just names, no sizes)
powershell.exe -Command "
Get-ChildItem 'C:\Users\chris\Desktop' -Recurse -Directory -Force -EA SilentlyContinue |
  Where-Object { $_.Name -match '^(node_modules|\.venv|venv|env)$' } |
  ForEach-Object { $_.FullName.Replace('C:\Users\chris\Desktop\','') }
"
```
