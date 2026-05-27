#!/usr/bin/env bash
# ==============================================================================
# Aether Agents v0.11.1 — Honcho Setup Script
# https://github.com/DarkArty07/Aether-Agents
#
# Sets up Honcho (memory provider) as a Docker Compose service.
# Pulls the submodule, generates .env from template with API keys from home/.env,
# and starts the services.
#
# Usage:  bash scripts/setup-honcho.sh
# ==============================================================================

set -euo pipefail

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

HONCHO_DIR="$PROJECT_ROOT/honcho-server"
ENV_TEMPLATE="$HONCHO_DIR/.env.template"
ENV_FILE="$HONCHO_DIR/.env"
HOME_ENV="$PROJECT_ROOT/home/.env"

echo ""
echo -e "${BOLD}═══ Honcho Setup — Aether Agents v0.11.1 ═══${NC}"
echo ""

# ── Step 1: Git Submodule ──────────────────────────────────────────────────
step "1/5" "Initializing git submodules"
if git submodule update --init --recursive; then
    ok "Submodules updated"
else
    fail "Submodule update failed"
    exit 1
fi

# ── Step 2: Copy template → .env ───────────────────────────────────────────
step "2/5" "Generating Honcho .env from template"
if [ ! -f "$ENV_TEMPLATE" ]; then
    fail ".env.template not found at $ENV_TEMPLATE"
    exit 1
fi

cp "$ENV_TEMPLATE" "$ENV_FILE"
ok "Copied .env.template → .env"

# ── Step 3: Read API keys from home/.env ───────────────────────────────────
step "3/5" "Reading API keys from home/.env"

OPENCODE_KEY=""
OPENROUTER_KEY=""

if [ -f "$HOME_ENV" ]; then
    # Read OPENCODE_GO_API_KEY
    OPENCODE_KEY=$(grep -E '^OPENCODE_GO_API_KEY=' "$HOME_ENV" | head -1 | cut -d'=' -f2-)
    if [ -n "$OPENCODE_KEY" ]; then
        ok "Found OPENCODE_GO_API_KEY"
    else
        warn "OPENCODE_GO_API_KEY not found in home/.env"
    fi

    # Read OPENROUTER_API_KEY
    OPENROUTER_KEY=$(grep -E '^OPENROUTER_API_KEY=' "$HOME_ENV" | head -1 | cut -d'=' -f2-)
    if [ -n "$OPENROUTER_KEY" ]; then
        ok "Found OPENROUTER_API_KEY"
    else
        warn "OPENROUTER_API_KEY not found in home/.env — embeddings will fail"
    fi
else
    fail "home/.env not found at $HOME_ENV"
    exit 1
fi

# ── Step 4: Substitute keys into honcho-server/.env ────────────────────────
step "4/5" "Substituting API keys into Honcho .env"

if [ -n "$OPENCODE_KEY" ]; then
    # Use | as delimiter to avoid issues with / in keys
    sed -i "s|\${OPENCODE_GO_API_KEY}|${OPENCODE_KEY}|g" "$ENV_FILE"
    ok "Substituted OPENCODE_GO_API_KEY"
fi

if [ -n "$OPENROUTER_KEY" ]; then
    sed -i "s|\${OPENROUTER_API_KEY}|${OPENROUTER_KEY}|g" "$ENV_FILE"
    ok "Substituted OPENROUTER_API_KEY"
else
    warn "OPENROUTER_API_KEY left as placeholder — configure it in home/.env and re-run"
fi

# ── Step 5: Start Docker Compose ───────────────────────────────────────────
step "5/5" "Starting Honcho services via Docker Compose"

if ! command -v docker &> /dev/null; then
    fail "Docker is not installed"
    exit 1
fi

cd "$PROJECT_ROOT"
if docker compose up -d; then
    ok "Honcho services started"
    echo ""
    info "Services running:"
    docker compose ps 2>/dev/null || true
else
    fail "Docker Compose failed to start"
    exit 1
fi

echo ""
echo -e "${BOLD}═══ Honcho Setup Complete ═══${NC}"
echo ""
echo -e "  ${GREEN}API:${NC}      http://localhost:8000"
echo -e "  ${GREEN}Health:${NC}   http://localhost:8000/health"
echo -e "  ${GREEN}Logs:${NC}    docker compose logs -f"
echo -e "  ${GREEN}Stop:${NC}    docker compose down"
echo ""
