#!/usr/bin/env bash
# ==============================================================================
# Aether Agents v0.17.0 — Gateway Service Manager
# https://github.com/DarkArty07/Aether-Agents
#
# Manage the Hermes Gateway systemd user service: start, stop, restart, status.
#
# Usage:
#   bash scripts/start-gateway.sh start                     # hermes-gateway
#   bash scripts/start-gateway.sh -p prometeo start         # hermes-gateway-prometeo
#   bash scripts/start-gateway.sh --profile myprof stop      # hermes-gateway-myprof
# ==============================================================================

set -euo pipefail

SCRIPT_VERSION="0.17.0"
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

# ── Defaults ──────────────────────────────────────────────────────────────────
PROFILE=""
COMMAND=""

# ── Parse arguments ────────────────────────────────────────────────────────────
usage() {
    echo ""
    echo -e "${BOLD}Aether Agents v${SCRIPT_VERSION} — Gateway Service Manager${NC}"
    echo ""
    echo "Usage:"
    echo "  bash scripts/start-gateway.sh [options] <command>"
    echo ""
    echo "Commands:"
    echo "  start     Enable and start the gateway service"
    echo "  stop      Stop the gateway service"
    echo "  restart   Restart the gateway service"
    echo "  status    Show gateway service logs (journalctl)"
    echo ""
    echo "Options:"
    echo "  -p, --profile PROFILE   Use service hermes-gateway-PROFILE"
    echo "                          (default: hermes-gateway)"
    echo ""
    echo "Examples:"
    echo "  bash scripts/start-gateway.sh start"
    echo "  bash scripts/start-gateway.sh -p prometeo start"
    echo "  bash scripts/start-gateway.sh --profile orchestrator restart"
    echo ""
    exit 1
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -p|--profile)
            PROFILE="$2"
            shift 2
            ;;
        -h|--help)
            usage
            ;;
        start|stop|restart|status)
            COMMAND="$1"
            shift
            ;;
        *)
            fail "Unknown argument: $1"
            usage
            ;;
    esac
done

if [ -z "$COMMAND" ]; then
    fail "No command specified"
    usage
fi

# ── Determine service name ────────────────────────────────────────────────────
if [ -n "$PROFILE" ]; then
    SERVICE_NAME="hermes-gateway-${PROFILE}"
else
    SERVICE_NAME="hermes-gateway"
fi

# ── Check systemd availability ─────────────────────────────────────────────────
check_systemd() {
    if ! command -v systemctl &>/dev/null; then
        fail "systemctl not found — systemd is not available"
        echo ""
        echo -e "${YELLOW}Manual start:${NC}"
        echo "  source ${HOME}/Aether-Agents/home/.venv-hermes/bin/activate"
        echo "  HERMES_HOME=${HOME}/Aether-Agents/home python -m hermes_cli.main"
        echo ""
        echo -e "${YELLOW}Manual stop:${NC}"
        echo "  Find PID: ps aux | grep hermes"
        echo "  Kill:      kill <PID>"
        echo ""
        exit 1
    fi

    # Verify systemd user session is running
    if ! systemctl --user status &>/dev/null; then
        warn "systemd user session not running — some commands may fail"
        info "Start it with: systemctl --user daemon-start"
    fi
}

# ── Service commands ───────────────────────────────────────────────────────────
do_start() {
    info "Enabling ${SERVICE_NAME}..."
    systemctl --user enable "${SERVICE_NAME}" 2>/dev/null || {
        warn "Could not enable ${SERVICE_NAME} — service unit may not exist yet"
    }

    info "Starting ${SERVICE_NAME}..."
    if systemctl --user start "${SERVICE_NAME}" 2>/dev/null; then
        ok "${SERVICE_NAME} started"
    else
        fail "Failed to start ${SERVICE_NAME}"
        info "Check logs: systemctl --user status ${SERVICE_NAME}"
        info "Or: journalctl --user -u ${SERVICE_NAME} -n 50"
        exit 1
    fi
}

do_stop() {
    info "Stopping ${SERVICE_NAME}..."
    if systemctl --user stop "${SERVICE_NAME}" 2>/dev/null; then
        ok "${SERVICE_NAME} stopped"
    else
        warn "Could not stop ${SERVICE_NAME} — may not be running"
    fi
}

do_restart() {
    info "Restarting ${SERVICE_NAME}..."
    if systemctl --user restart "${SERVICE_NAME}" 2>/dev/null; then
        ok "${SERVICE_NAME} restarted"
    else
        fail "Failed to restart ${SERVICE_NAME}"
        info "Check logs: systemctl --user status ${SERVICE_NAME}"
        exit 1
    fi
}

do_status() {
    echo ""
    info "Service: ${SERVICE_NAME}"
    systemctl --user status "${SERVICE_NAME}" 2>/dev/null || true
    echo ""
    echo -e "${BOLD}Recent logs (last 30 lines):${NC}"
    journalctl --user -u "${SERVICE_NAME}" -n 30 --no-pager 2>/dev/null || true
    echo ""
}

# ── Main ───────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}Aether Agents v${SCRIPT_VERSION} — Gateway Manager${NC} (${SCRIPT_DATE})"
echo -e "${BOLD}════════════════════════════════════════════════════════════════${NC}"
echo ""
echo "  Service:  ${SERVICE_NAME}"
echo ""

check_systemd

case "$COMMAND" in
    start)   do_start   ;;
    stop)    do_stop    ;;
    restart) do_restart ;;
    status)  do_status  ;;
esac