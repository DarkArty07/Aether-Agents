# Installation

## Requirements

- Linux with Python 3.11 or newer;
- Bash and Git;
- Hermes Agent installed by `scripts/setup.sh` or available on `PATH`;
- for Aether MCP provider operation, the exact supported provider AppImage/profile and an existing coordinator handle.

## Hermes and product assets

```bash
git clone https://github.com/DarkArty07/Aether-Agents.git
cd Aether-Agents
bash scripts/setup.sh
```

The setup script creates `home/.venv-hermes`, root/profile live configs and launch wrappers. It does not overwrite configured files and does not activate Aether MCP.

## Aether MCP installation

First inspect any existing installation with `make runtime-status`. A new installation is an explicit local operation and requires real absolute values:

```bash
python scripts/aether_mcp/setup.py \
  --project-root /absolute/path/to/aether \
  --hermes-home /absolute/path/to/aether/home \
  --appimage /absolute/path/to/orca-linux.AppImage \
  --profile-root /absolute/path/to/provider-profile \
  --repo-selector path:/absolute/path/to/aether \
  --base-ref main \
  --coordinator-handle EXISTING_HANDLE \
  --profile-id default
```

The installer creates an isolated package environment under `home/.aether-mcp`, extracts/pins the provider build, writes secret-safe installation metadata, creates a wrapper and prepares Hermes registration with rollback material.

Enable or disable the prepared registration explicitly:

```bash
python scripts/aether_mcp/activate.py --hermes-home /absolute/path/to/aether/home
python scripts/aether_mcp/activate.py --hermes-home /absolute/path/to/aether/home --disable
```

Rollback restores the prior installation/config boundary:

```bash
python scripts/aether_mcp/rollback.py --hermes-home /absolute/path/to/aether/home
```

Do not hand-edit generated wrapper environment or installation metadata to bypass a failed doctor. Fix the exact configuration/provider defect or rollback.
