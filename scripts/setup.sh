#!/usr/bin/env bash
# ==============================================================================
# Aether Agents v0.15.0 — Setup Script
# https://github.com/DarkArty07/Aether-Agents
#
# Automated installation: Python venv, pip packages, config generation, wrappers.
# Idempotent — safe to re-run. Preserves existing config and .env files.
#
# Usage:  bash scripts/setup.sh
# ==============================================================================

set -euo pipefail

SCRIPT_VERSION="0.15.0"
SCRIPT_DATE="$(date +%Y-%m-%d)"

# ── Colors ─────────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

ok()   { echo -e "  ${GREEN}✓${NC} $*"; }
warn() { echo -e "  ${YELLOW}⚠${NC} $*"; }
fail() { echo -e "  ${RED}✗${NC} $*" >&2; }
info() { echo -e "  ${BLUE}→${NC} $*"; }
step() { echo -e "\n${BOLD}[$1]${NC} $2"; }

# ── Paths ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$(dirname "$SCRIPT_DIR")" && pwd)"
VENV_DIR="$PROJECT_ROOT/home/.venv-hermes"
HERMES_PYTHON="$VENV_DIR/bin/python"
HERMES_BIN="$VENV_DIR/bin/hermes"

# ── Portable sed (BSD/macOS vs GNU) ───────────────────────────────────────────
# Uses | as delimiter — safe for file paths which contain / but not |
sed_inplace() {
    local pattern="$1"
    local replacement="$2"
    local file="$3"
    if sed --version 2>/dev/null | grep -q GNU; then
        sed -i "s|${pattern}|${replacement}|g" "$file"
    else
        sed -i '' "s|${pattern}|${replacement}|g" "$file"
    fi
}

# ── Verify repo structure ─────────────────────────────────────────────────────
verify_repo() {
    if [ ! -f "$PROJECT_ROOT/pyproject.toml" ]; then
        fail "pyproject.toml not found at $PROJECT_ROOT"
        fail "Run this script from the Aether-Agents repo root: bash scripts/setup.sh"
        exit 1
    fi
    if [ ! -d "$PROJECT_ROOT/src/olympus_v3" ]; then
        fail "src/olympus_v3/ not found — is this the Aether-Agents repository?"
        exit 1
    fi
    if [ ! -d "$PROJECT_ROOT/home/profiles" ]; then
        fail "home/profiles/ not found — is this the Aether-Agents repository?"
        exit 1
    fi
    ok "Repository structure verified"
}

# ── Detect WSL ────────────────────────────────────────────────────────────────
detect_wsl() {
    if grep -qi microsoft /proc/version 2>/dev/null; then
        IS_WSL=true
        info "WSL environment detected"
    else
        IS_WSL=false
    fi
}

# ── Init submodules (for users who cloned without --recurse-submodules) ───────
init_submodules() {
    if [ -f ".gitmodules" ]; then
        info "Initializing git submodules..."
        git submodule update --init --recursive 2>/dev/null && ok "Submodules initialized" || warn "Submodule init skipped (no network or not a git repo)"
    fi
}

# ── Step 1: Detect Python 3.11+ ───────────────────────────────────────────────
detect_python() {
    step 1 "Detecting Python 3.11+"

    local python_cmd=""

    # Prefer explicit version pinchots (3.11, then 3.12, then 3.13+)
    for cmd in python3.11 python3.12 python3.13; do
        if command -v "$cmd" &>/dev/null; then
            python_cmd="$cmd"
            break
        fi
    done

    # Fall back to python3 and check version
    if [ -z "$python_cmd" ]; then
        if command -v python3 &>/dev/null; then
            local py_version
            py_version=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || echo "0.0")
            local major minor
            IFS='.' read -r major minor <<< "$py_version"
            if [ "$major" -eq 3 ] && [ "$minor" -ge 11 ]; then
                python_cmd="python3"
            fi
        fi
    fi

    if [ -z "$python_cmd" ]; then
        fail "Python 3.11+ not found!"
        echo ""
        echo "  Install Python 3.11+ and re-run this script:"
        echo ""
        echo "    Ubuntu/Debian:  sudo apt install python3.11 python3.11-venv python3.11-dev"
        echo "    Fedora:         sudo dnf install python3.11 python3.11-devel"
        echo "    macOS:           brew install python@3.11"
        if [ "${IS_WSL:-false}" = true ]; then
            echo "    WSL:            sudo apt install python3.11 python3.11-venv python3.11-dev"
        fi
        echo ""
        exit 1
    fi

    local version_str
    version_str=$("$python_cmd" --version 2>&1)
    ok "Found $version_str (${python_cmd})"
    PYTHON_CMD="$python_cmd"
}

# ── Step 2: Create venv ───────────────────────────────────────────────────────
create_venv() {
    step 2 "Setting up virtual environment"

    if [ -d "$VENV_DIR" ] && [ -x "$VENV_DIR/bin/python" ]; then
        local venv_version
        venv_version=$("$VENV_DIR/bin/python" -c \
            'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' \
            2>/dev/null || echo "0.0")
        local major minor
        IFS='.' read -r major minor <<< "$venv_version"

        if [ "$major" -eq 3 ] && [ "$minor" -ge 11 ]; then
            ok "venv exists at ${VENV_DIR} (Python ${venv_version}) — reusing"
            info "Upgrading pip..."
            "$VENV_DIR/bin/pip" install --upgrade pip --quiet 2>/dev/null || true
            return 0
        else
            warn "venv uses Python ${venv_version} (expected 3.11+) — recreating"
            rm -rf "$VENV_DIR"
        fi
    fi

    "$PYTHON_CMD" -m venv "$VENV_DIR"
    ok "Created venv at ${VENV_DIR}"

    "$VENV_DIR/bin/pip" install --upgrade pip --quiet 2>/dev/null || true
    ok "Upgraded pip"
}

# ── Step 3: Install hermes-agent ───────────────────────────────────────────────
install_hermes_agent() {
    step 3 "Installing hermes-agent from PyPI"

    info "Installing hermes-agent (this may take a moment)..."
    "$VENV_DIR/bin/pip" install hermes-agent

    if [ -x "$HERMES_BIN" ]; then
        local hermes_version
        hermes_version=$("$HERMES_BIN" --version 2>&1 || echo "unknown")
        ok "hermes-agent ${hermes_version}"
        ok "Binary: ${HERMES_BIN}"
    else
        fail "hermes binary not found at ${HERMES_BIN} after installation"
        exit 1
    fi
}

# ── Step 4: Install olympus-mcp ───────────────────────────────────────────────
install_olympus_mcp() {
    step 4 "Installing olympus-mcp (editable mode)"

    info "Installing olympus-mcp from ${PROJECT_ROOT}..."
    "$VENV_DIR/bin/pip" install -e "$PROJECT_ROOT"

    ok "olympus-mcp installed in editable mode"

    # Verify the MCP server is importable
    if "$HERMES_PYTHON" -c "import olympus_v3.server" 2>/dev/null; then
        ok "olympus_v3.server import verified"
    else
        warn "olympus_v3.server import check failed — may need PYTHONPATH set"
        info "The MCP server path will be set in config.yaml"
    fi
}

# ── Step 5: Install CUDA extras (optional) ────────────────────────────────────
install_cuda_extras() {
    step 5 "Installing CUDA extras (optional)"

    if ! command -v nvidia-smi &>/dev/null; then
        warn "No NVIDIA GPU detected — skipping faster-whisper"
        info "STT will use CPU fallback. Install later with: pip install faster-whisper"
        return 0
    fi

    local gpu_name
    gpu_name=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1 || echo "unknown")
    info "GPU detected: ${gpu_name}"
    info "Installing faster-whisper with CUDA support..."

    if "$VENV_DIR/bin/pip" install faster-whisper 2>&1; then
        ok "faster-whisper installed — CUDA STT support available"
    else
        warn "faster-whisper installation failed — STT will use CPU fallback"
        info "Retry later: source ${VENV_DIR}/bin/activate && pip install faster-whisper"
    fi
}

# ── Step 6: Setup .env files ──────────────────────────────────────────────────
setup_env_files() {
    step 6 "Setting up .env files from templates"

    local created=0
    local existing=0

    for profile_dir in "$PROJECT_ROOT/home/profiles"/*/; do
        [ -d "$profile_dir" ] || continue
        local profile_name
        profile_name="$(basename "$profile_dir")"

        if [ -f "$profile_dir/.env.example" ]; then
            if [ -f "$profile_dir/.env" ]; then
                ok "${profile_name}/.env already exists — skipping"
                existing=$((existing + 1))
            else
                cp "$profile_dir/.env.example" "$profile_dir/.env"
                ok "${profile_name}/.env created from .env.example"
                created=$((created + 1))
            fi
        elif [ "$profile_name" = "ictinus" ]; then
            info "→ ${profile_name}: no .env.example (Level 1 Consultant — config-only)"
        else
            warn "→ ${profile_name}: no .env.example found"
        fi
    done

    if [ "$created" -eq 0 ] && [ "$existing" -eq 0 ]; then
        info "No .env.example files found in profiles"
    fi

    # Create orchestrator-level home/.env from template
    if [ -f "$PROJECT_ROOT/home/.env.example" ] && [ ! -f "$PROJECT_ROOT/home/.env" ]; then
        cp "$PROJECT_ROOT/home/.env.example" "$PROJECT_ROOT/home/.env"
        ok "Created home/.env from template"
    elif [ -f "$PROJECT_ROOT/home/.env" ]; then
        ok "home/.env already exists — skipping"
    else
        info "No home/.env.example template found — skipping"
    fi
}

# ── Step 7: Generate config.yaml from templates ──────────────────────────────
generate_configs() {
    step 7 "Generating config.yaml from templates"

    local generated=0
    local skipped=0

    for profile_dir in "$PROJECT_ROOT/home/profiles"/*/; do
        [ -d "$profile_dir" ] || continue
        local profile_name
        profile_name="$(basename "$profile_dir")"
        local template="${profile_dir}config.yaml.template"
        local config="${profile_dir}config.yaml"

        # Skip profiles without templates
        [ -f "$template" ] || continue

        if [ -f "$config" ]; then
            # Config already exists — only regenerate if it has unresolved placeholders
            if grep -q "__AETHER_ROOT__\|__HERMES_PYTHON__" "$config" 2>/dev/null; then
                warn "${profile_name}/config.yaml has unresolved placeholders — regenerating"
                cp "$template" "$config"
                sed_inplace "__AETHER_ROOT__" "$PROJECT_ROOT" "$config"
                sed_inplace "__HERMES_PYTHON__" "$HERMES_PYTHON" "$config"
                ok "${profile_name}/config.yaml regenerated"
                generated=$((generated + 1))
            else
                ok "${profile_name}/config.yaml already configured — skipping"
                skipped=$((skipped + 1))
            fi
        else
            cp "$template" "$config"
            sed_inplace "__AETHER_ROOT__" "$PROJECT_ROOT" "$config"
            sed_inplace "__HERMES_PYTHON__" "$HERMES_PYTHON" "$config"
            ok "${profile_name}/config.yaml generated from template"
            generated=$((generated + 1))
        fi
    done

    if [ "$generated" -eq 0 ] && [ "$skipped" -eq 0 ]; then
        info "No config.yaml.template files found in profiles"
    fi
}

# ── Step 8: Create wrapper scripts ─────────────────────────────────────────────
create_wrappers() {
    step 8 "Creating wrapper scripts"

    mkdir -p "$HOME/.local/bin"

    # Wrapper content — both aether and hermes are identical
    local wrapper_content
    wrapper_content="#!/bin/bash
# Aether Agents wrapper — auto-generated by setup.sh v${SCRIPT_VERSION}
# Points to .venv-hermes/bin/hermes (default profile)

export HERMES_HOME=\"${PROJECT_ROOT}/home\"
exec \"${HERMES_BIN}\" \"\$@\"
"

    for name in aether hermes; do
        local wrapper_path="$HOME/.local/bin/${name}"

        if [ -f "$wrapper_path" ]; then
            local current_content
            current_content=$(cat "$wrapper_path" 2>/dev/null || echo "")
            if [ "$current_content" = "$wrapper_content" ]; then
                ok "${name} wrapper already up-to-date — skipping"
                continue
            fi
        fi

        echo "$wrapper_content" > "$wrapper_path"
        chmod +x "$wrapper_path"
        ok "${name} → ${wrapper_path}"
    done

    # ── aether-setup wrapper (auto-generated by python wrappers.py) ──────────
    local setup_wrapper_path="$HOME/.local/bin/aether-setup"
    if [ -f "$setup_wrapper_path" ]; then
        local current_setup
        current_setup=$(cat "$setup_wrapper_path" 2>/dev/null || echo "")
        if [ "$current_setup" = "$wrapper_content" ]; then
            ok "aether-setup wrapper already up-to-date — skipping"
        else
            echo "$wrapper_content" > "$setup_wrapper_path"
            chmod +x "$setup_wrapper_path"
            ok "aether-setup → ${setup_wrapper_path}"
        fi
    else
        echo "$wrapper_content" > "$setup_wrapper_path"
        chmod +x "$setup_wrapper_path"
        ok "aether-setup → ${setup_wrapper_path}"
    fi
}

# ── Step 9: Add HERMES_HOME to .bashrc ────────────────────────────────────────
setup_bashrc() {
    step 9 "Configuring shell environment"

    local export_line="export HERMES_HOME=\"${PROJECT_ROOT}/home\""
    local bashrc="$HOME/.bashrc"

    # Create .bashrc if it doesn't exist
    [ -f "$bashrc" ] || touch "$bashrc"

    # Add or update HERMES_HOME export (handles re-install at different paths)
    if grep -qF "HERMES_HOME" "$bashrc" 2>/dev/null; then
        # Replace the existing line — handles re-install at a different PROJECT_ROOT
        sed -i.bak "s|^export HERMES_HOME=.*|export HERMES_HOME=\"${PROJECT_ROOT}/home\"|" "$bashrc"
        rm -f "$bashrc.bak"
        ok "Updated HERMES_HOME in ~/.bashrc to ${PROJECT_ROOT}/home"
    else
        {
            echo ""
            echo "# Aether Agents — added by setup.sh v${SCRIPT_VERSION}"
            echo "$export_line"
        } >> "$bashrc"
        ok "Added HERMES_HOME to ~/.bashrc"
    fi

    # Verify exactly one HERMES_HOME export line exists
    local hermes_count
    hermes_count=$(grep -c "^export HERMES_HOME=" "$bashrc" 2>/dev/null || echo 0)
    if [ "$hermes_count" -ne 1 ]; then
        warn "Expected 1 HERMES_HOME export in ~/.bashrc, found ${hermes_count}"
    fi

    # Add ~/.local/bin to PATH if not already there
    if ! echo ":${PATH}:" | grep -qF ":$HOME/.local/bin:" 2>/dev/null; then
        if ! grep -qF '.local/bin' "$bashrc" 2>/dev/null; then
            {
                echo ""
                echo "# Added by setup.sh — wrapper scripts live here"
                echo 'export PATH="$HOME/.local/bin:$PATH"'
            } >> "$bashrc"
            ok "Added ~/.local/bin to PATH in ~/.bashrc"
        else
            ok "~/.local/bin already in ~/.bashrc PATH"
        fi
    else
        ok "~/.local/bin already in PATH"
    fi
}

# ── Step 10: Update .gitignore ────────────────────────────────────────────────
update_gitignore() {
    step 10 "Updating .gitignore"

    local gitignore="$PROJECT_ROOT/.gitignore"

    if [ ! -f "$gitignore" ]; then
        echo "home/.venv-hermes/" > "$gitignore"
        ok "Created .gitignore with home/.venv-hermes/"
        return 0
    fi

    if grep -qF '.venv-hermes' "$gitignore" 2>/dev/null; then
        ok ".venv-hermes already in .gitignore — skipping"
    else
        {
            echo ""
            echo "# Hermes venv (pip install target)"
            echo "home/.venv-hermes/"
        } >> "$gitignore"
        ok "Added home/.venv-hermes/ to .gitignore"
    fi
}

# ── Final summary ─────────────────────────────────────────────────────────────
print_summary() {
    echo ""
    echo -e "${BOLD}╔══════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}║   Aether Agents v${SCRIPT_VERSION} — Setup Complete                  ║${NC}"
    echo -e "${BOLD}╚══════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${YELLOW}Next steps:${NC}"
    echo ""
    echo "  1. ${BOLD}Edit API keys${NC} in profile .env files:"
    echo "     ${DIM}${PROJECT_ROOT}/home/profiles/*/ .env${NC}"
    echo ""
    echo "  2. ${BOLD}Restart your terminal${NC} (or run: source ~/.bashrc)"
    echo ""
    echo "  3. ${BOLD}Start Aether Agents:${NC}"
    echo "     aether"
    echo ""
    echo -e "${BLUE}Installation details:${NC}"
    echo "     Project root:   ${PROJECT_ROOT}"
    echo "     Hermes home:     ${PROJECT_ROOT}/home"
    echo "     Venv:            ${VENV_DIR}"
    echo "     Python:          ${HERMES_PYTHON}"
    echo "     Hermes binary:   ${HERMES_BIN}"
    echo "     Profiles:       ${PROJECT_ROOT}/home/profiles/"
    echo ""

    if [ "${IS_WSL:-false}" = true ]; then
        echo -e "${YELLOW}WSL notes:${NC}"
        echo "  • If using Windows terminals, update any .desktop shortcuts"
        echo "    to point to: ${HERMES_PYTHON}"
        echo "  • GPU access requires NVIDIA driver for WSL (2GB+)"
        echo ""
    fi

    echo -e "${DIM}Re-run this script anytime — it's idempotent and safe.${NC}"
}

# ── Main ───────────────────────────────────────────────────────────────────────
main() {
    echo ""
    echo -e "${BOLD}Aether Agents v${SCRIPT_VERSION} — Setup${NC} (${SCRIPT_DATE})"
    echo -e "${BOLD}════════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "  Project root:  ${PROJECT_ROOT}"
    echo "  Venv target:   ${VENV_DIR}"
    echo "  Profile dir:   ${PROJECT_ROOT}/home/profiles/"
    echo ""

    verify_repo
    detect_wsl
    init_submodules
    detect_python
    create_venv
    install_hermes_agent
    install_olympus_mcp
    install_cuda_extras
    setup_env_files
    generate_configs
    create_wrappers
    setup_bashrc
    update_gitignore
    print_summary
}

main "$@"