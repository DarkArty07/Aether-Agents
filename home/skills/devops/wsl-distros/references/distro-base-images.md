# WSL Distro Base Image Comparison

Quick reference for the four distro families Chris uses. Last verified 2026-06-05.

## Ubuntu (Microsoft Canonical image)

| Attribute | Value |
|-----------|-------|
| Package manager | `apt` (Debian family) |
| Base image type | "User-friendly" — preinstalled tooling |
| Default user | Created on first launch via OOBE |
| Default shell | bash |
| Preinstalled | `awk`, `gawk`, `python3`, `python3-pip`, `python3-venv`, `curl`, `wget`, `git`, `ca-certificates`, `build-essential` (gcc, make, libc-dev) |
| NOT preinstalled | Some dev tools (`docker`, `docker-compose`, `node`, `poetry`); use `apt install` |
| Boot time (cold) | ~2-4s |
| Disk footprint | ~1.5 GB |
| Common use | Aether-Agents, AetherTest, dev environments |

**Pitfall:** `python3-pip` may be excluded in newer Ubuntu minimal variants. Use `sudo apt install python3-pip` if missing.

## Fedora (Fedora WSL official image, available since 2025-05)

| Attribute | Value |
|-----------|-------|
| Package manager | `dnf` (RHEL family) |
| Base image type | Minimal/server — almost nothing preinstalled |
| Default user | Created on first launch via OOBE |
| Default shell | bash |
| Preinstalled | `dnf`, basic `coreutils`, `bash`, `glibc-minimal-langpack` |
| NOT preinstalled | `awk` (in `gawk`), `gcc`, `make`, `python3-devel`, `ca-certificates`, `python3-pip` (in newer images), `git`, `curl` |
| Boot time (cold) | ~2-3s |
| Disk footprint | ~600 MB |
| Common use | RHEL-compatible testing, prometheus/grafana, services that need `dnf` |

**Pitfall:** ANY third-party installer that uses `awk` (hermes-agent, pyenv, nvm) will fail with "checksum mismatch" or similar. Pre-flight is mandatory.

**Pitfall:** `python3-pip` is not bundled in newer Fedora WSL images. Install with `sudo dnf install python3-pip` and pair with `python3-devel` for any wheel compilation.

## AlmaLinux (RHEL binary-compatible, available since 2024)

| Attribute | Value |
|-----------|-------|
| Package manager | `dnf` (RHEL family, near-identical to Fedora) |
| Base image type | Minimal/server — same as Fedora |
| Preinstalled | Same as Fedora minimal |
| NOT preinstalled | Same as Fedora |
| Variants | `AlmaLinux-8` (LTS), `AlmaLinux-9` (current), `AlmaLinux-10` (latest), `AlmaLinux-Kitten-10` (rolling) |
| Common use | RHEL production-mirroring, CentOS replacement |

**Pitfall:** Same as Fedora. The `dnf` ecosystem is identical.

## Arch (rolling release)

| Attribute | Value |
|-----------|-------|
| Package manager | `pacman` |
| Base image type | EXTREMELY minimal — basically just the bootstrap |
| Preinstalled | `pacman`, `bash`, `glibc`, that's about it |
| NOT preinstalled | Everything. You build up from zero. |
| Common use | Minimal custom environments, learning Linux internals |
| Risk | Rolling release = things break. Not for production agents. |

**Pitfall:** Everything Fedora is missing, Arch is missing MORE. The "build everything from scratch" workflow is the Arch way. Pre-flight is at least 3x longer.

## Pre-flight: Universal vs. Per-Distro

| Tool/Binary | Ubuntu | Fedora 43 | Alma 10 | Arch |
|-------------|--------|-----------|---------|------|
| `awk` / `gawk` | ✓ | `dnf install gawk` | `dnf install gawk` | `pacman -S gawk` |
| `gcc` | ✓ (build-essential) | `dnf install gcc` | `dnf install gcc` | `pacman -S gcc` (base-devel) |
| `make` | ✓ | `dnf install make` | `dnf install make` | `pacman -S make` (base-devel) |
| `python3` | ✓ | ✓ | ✓ | `pacman -S python` |
| `python3-pip` | ✓ | `dnf install python3-pip` | `dnf install python3-pip` | `pacman -S python-pip` |
| `python3-venv` | ✓ | `dnf install python3-devel` | `dnf install python3-devel` | (bundled with python) |
| `ca-certificates` | ✓ | `dnf install ca-certificates` | `dnf install ca-certificates` | `pacman -S ca-certificates` |
| `curl` | ✓ | `dnf install curl` | `dnf install curl` | `pacman -S curl` |
| `git` | ✓ | `dnf install git` | `dnf install git` | `pacman -S git` |

## The "Just install everything you might need" command

When in doubt, this is the safe pre-flight for ANY RHEL-family distro (Fedora/Alma):

```bash
sudo dnf install -y gawk curl ca-certificates python3 python3-pip python3-devel gcc make git
```

For Arch:
```bash
sudo pacman -S --noconfirm gawk curl ca-certificates python python-pip base-devel git
```

For Ubuntu (rarely needed):
```bash
sudo apt install -y gawk curl ca-certificates python3 python3-pip python3-venv build-essential git
```

These commands install ~150 MB but guarantee any third-party installer will work. Cost: 30 seconds. Savings: hours of misleading-error debugging.
