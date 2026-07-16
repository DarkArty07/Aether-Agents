#!/usr/bin/env bash
# ==============================================================================
# Aether Agents v0.17.0 — Honcho Setup Script
# https://github.com/DarkArty07/Aether-Agents
#
# Sets up Honcho (memory provider) with Docker Compose or Podman Compose.
# Pulls the submodule, generates .env from template with API keys from home/.env,
# and starts the services.
#
# Usage:  bash scripts/setup-honcho.sh
#         bash scripts/setup-honcho.sh --detect-compose
# ==============================================================================

set -euo pipefail
umask 077

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

DETECT_COMPOSE_ONLY=false
case "${1:-}" in
    "") ;;
    --detect-compose) DETECT_COMPOSE_ONLY=true ;;
    --help|-h)
        echo "Usage: bash scripts/setup-honcho.sh [--detect-compose]"
        exit 0
        ;;
    *)
        fail "Unknown option: $1"
        echo "Usage: bash scripts/setup-honcho.sh [--detect-compose]" >&2
        exit 2
        ;;
esac

if [ "$DETECT_COMPOSE_ONLY" = false ]; then
    echo ""
    echo -e "${BOLD}═══ Honcho Setup — Aether Agents v0.17.0 ═══${NC}"
    echo ""
fi

# ── Pre-check: Compose runtime ────────────────────────────────────────────────
if [ "$DETECT_COMPOSE_ONLY" = false ]; then
    info "Detecting Compose runtime..."
fi
COMPOSE=()
COMPOSE_LABEL=""

if command -v docker &>/dev/null && docker compose version &>/dev/null; then
    COMPOSE=(docker compose)
    COMPOSE_LABEL="Docker Compose"
elif command -v docker-compose &>/dev/null && docker-compose --version &>/dev/null; then
    COMPOSE=(docker-compose)
    COMPOSE_LABEL="Docker Compose (legacy)"
elif command -v podman &>/dev/null && podman compose version &>/dev/null; then
    COMPOSE=(podman compose)
    COMPOSE_LABEL="Podman Compose"
else
    echo ""
    fail "No supported Compose runtime found."
    echo ""
    echo "  Install Docker Compose or Podman Compose, then re-run this script."
    echo "  Docker: https://docs.docker.com/compose/install/"
    echo "  Podman: https://podman.io/docs/installation"
    echo ""
    exit 1
fi

if [ "$DETECT_COMPOSE_ONLY" = false ]; then
    ok "$COMPOSE_LABEL detected: ${COMPOSE[*]}"
fi

if [ "$DETECT_COMPOSE_ONLY" = true ]; then
    printf '%s\n' "${COMPOSE[*]}"
    exit 0
fi

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
chmod 600 "$ENV_FILE"
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

OPENCODE_GO_API_KEY="$OPENCODE_KEY" OPENROUTER_API_KEY="$OPENROUTER_KEY" python3 - "$ENV_FILE" <<'PY'
import os
import sys

path = sys.argv[1]
with open(path, encoding="utf-8") as env_file:
    content = env_file.read()

for placeholder, variable in (
    ("${OPENCODE_GO_API_KEY}", "OPENCODE_GO_API_KEY"),
    ("${OPENROUTER_API_KEY}", "OPENROUTER_API_KEY"),
):
    value = os.environ.get(variable, "")
    if value:
        content = content.replace(placeholder, value)

with open(path, "w", encoding="utf-8") as env_file:
    env_file.write(content)
PY

if [ -n "$OPENCODE_KEY" ]; then
    ok "Substituted OPENCODE_GO_API_KEY"
fi

if [ -n "$OPENROUTER_KEY" ]; then
    ok "Substituted OPENROUTER_API_KEY"
else
    warn "OPENROUTER_API_KEY left as placeholder — configure it in home/.env and re-run"
fi

# ── Step 5: Start services ─────────────────────────────────────────────────
step "5/5" "Starting Honcho services via $COMPOSE_LABEL"

cd "$PROJECT_ROOT"
if "${COMPOSE[@]}" up -d; then
    ok "Honcho services started"
    echo ""
    info "Services running:"
    "${COMPOSE[@]}" ps 2>/dev/null || true
else
    fail "$COMPOSE_LABEL failed to start"
    exit 1
fi

echo ""
echo -e "${BOLD}═══ Honcho Setup Complete ═══${NC}"
echo ""
echo -e "  ${GREEN}API:${NC}      http://localhost:8010"
echo -e "  ${GREEN}Health:${NC}   http://localhost:8010/health"
echo -e "  ${GREEN}Logs:${NC}     ${COMPOSE[*]} logs -f"
echo -e "  ${GREEN}Stop:${NC}     ${COMPOSE[*]} down"
echo ""
