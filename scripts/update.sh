#!/usr/bin/env bash
# ==============================================================================
# Aether Agents v0.8.0 — Update Script
# https://github.com/DarkArty07/Aether-Agents
#
# Updates the repo and dependencies: git pull, pip upgrades, config regeneration.
# Idempotent — safe to re-run. Preserves local config changes and .env files.
#
# Usage:  bash scripts/update.sh
# ==============================================================================

set -euo pipefail

SCRIPT_VERSION="0.8.0"
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

# ── Pre-flight checks ─────────────────────────────────────────────────────────
preflight() {
    if [ ! -f "$PROJECT_ROOT/pyproject.toml" ]; then
        fail "pyproject.toml not found at $PROJECT_ROOT"
        fail "Run this script from the Aether-Agents repo root: bash scripts/update.sh"
        exit 1
    fi

    if [ ! -d "$VENV_DIR" ] || [ ! -x "$HERMES_BIN" ]; then
        fail "Virtual environment not found at $VENV_DIR"
        fail "Run setup first: bash scripts/setup.sh"
        exit 1
    fi

    ok "Pre-flight checks passed"
}

# ── Step 1: Git pull ──────────────────────────────────────────────────────────
git_pull() {
    step 1 "Pulling latest changes"

    # Check if there are local changes
    local has_changes=false
    if ! git -C "$PROJECT_ROOT" diff --quiet 2>/dev/null || \
       ! git -C "$PROJECT_ROOT" diff --cached --quiet 2>/dev/null; then
        has_changes=true
    fi

    # Also check untracked files
    if git -C "$PROJECT_ROOT" ls-files --others --exclude-standard \
        --directory 2>/dev/null | grep -q .; then
        has_changes=true
    fi

    if [ "$has_changes" = true ]; then
        warn "Local changes detected — showing diff before stashing"
        echo ""
        git -C "$PROJECT_ROOT" diff --stat 2>/dev/null || true
        echo ""
        info "Stashing local changes..."
        git -C "$PROJECT_ROOT" stash push -m "auto-stash before update $(date +%Y%m%d-%H%M%S)" 2>/dev/null
        ok "Changes stashed"
    fi

    info "Pulling from remote..."
    git -C "$PROJECT_ROOT" pull 2>/dev/null
    ok "Repository updated"

    # Restore stashed changes if any
    if [ "$has_changes" = true ]; then
        info "Restoring stashed changes..."
        if git -C "$PROJECT_ROOT" stash pop 2>/dev/null; then
            ok "Stashed changes restored"
        else
            warn "Conflict while restoring stash — manually resolve with: git stash pop"
            info "View stash: git stash list"
        fi
    fi
}

# ── Step 2: Upgrade hermes-agent ──────────────────────────────────────────────
upgrade_hermes_agent() {
    step 2 "Upgrading hermes-agent"

    local old_version
    old_version=$("$HERMES_BIN" --version 2>&1 || echo "unknown")

    info "Upgrading hermes-agent (was: ${old_version})..."
    "$VENV_DIR/bin/pip" install --upgrade hermes-agent --quiet 2>/dev/null

    local new_version
    new_version=$("$HERMES_BIN" --version 2>&1 || echo "unknown")
    ok "hermes-agent ${new_version}"
}

# ── Step 3: Reinstall olympus-mcp ────────────────────────────────────────────
reinstall_olympus_mcp() {
    step 3 "Reinstalling olympus-mcp (editable mode)"

    info "Installing olympus-mcp from ${PROJECT_ROOT}..."
    "$VENV_DIR/bin/pip" install -e "$PROJECT_ROOT" --quiet 2>/dev/null
    ok "olympus-mcp reinstalled"

    if "$HERMES_PYTHON" -c "import olympus_v3.server" 2>/dev/null; then
        ok "olympus_v3.server import verified"
    else
        warn "olympus_v3.server import check failed"
    fi
}

# ── Step 4: Regenerate config.yaml if needed ──────────────────────────────────
regenerate_configs() {
    step 4 "Checking config.yaml files"

    local regenerated=0
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
            # Only regenerate if config has unresolved placeholders
            if grep -q "__AETHER_ROOT__\|__HERMES_PYTHON__" "$config" 2>/dev/null; then
                warn "${profile_name}/config.yaml has unresolved placeholders — regenerating"
                cp "$template" "$config"
                sed_inplace "__AETHER_ROOT__" "$PROJECT_ROOT" "$config"
                sed_inplace "__HERMES_PYTHON__" "$HERMES_PYTHON" "$config"
                ok "${profile_name}/config.yaml regenerated"
                regenerated=$((regenerated + 1))
            else
                ok "${profile_name}/config.yaml already configured — skipping"
                skipped=$((skipped + 1))
            fi
        else
            # Config doesn't exist — generate from template
            cp "$template" "$config"
            sed_inplace "__AETHER_ROOT__" "$PROJECT_ROOT" "$config"
            sed_inplace "__HERMES_PYTHON__" "$HERMES_PYTHON" "$config"
            ok "${profile_name}/config.yaml generated from template"
            regenerated=$((regenerated + 1))
        fi
    done

    if [ "$regenerated" -eq 0 ] && [ "$skipped" -eq 0 ]; then
        info "No config.yaml.template files found in profiles"
    fi
}

# ── Final summary ──────────────────────────────────────────────────────────────
print_summary() {
    echo ""
    echo -e "${BOLD}╔══════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}║   Aether Agents v${SCRIPT_VERSION} — Update Complete                  ║${NC}"
    echo -e "${BOLD}╚══════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "  ${GREEN}Run \`aether\` to start.${NC}"
    echo ""
}

# ── Main ───────────────────────────────────────────────────────────────────────
main() {
    echo ""
    echo -e "${BOLD}Aether Agents v${SCRIPT_VERSION} — Update${NC} (${SCRIPT_DATE})"
    echo -e "${BOLD}════════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "  Project root:  ${PROJECT_ROOT}"
    echo "  Venv:          ${VENV_DIR}"
    echo ""

    preflight
    git_pull
    upgrade_hermes_agent
    reinstall_olympus_mcp
    regenerate_configs
    print_summary
}

main "$@"