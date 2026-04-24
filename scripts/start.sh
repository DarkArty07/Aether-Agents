#!/usr/bin/env bash
# start.sh — Start Aether Agents ecosystem
# Starts Olympus MCP server and verifies Daimon discovery
# Usage: ./scripts/start.sh [--install]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
AETHER_HOME="${AETHER_HOME:-$PROJECT_ROOT/home}"
PYTHON="${PYTHON:-}"
if [ -z "$PYTHON" ]; then
    # Try standard install path first, then from-source, then PATH
    if [ -f "$HOME/.hermes/sdk/venv/bin/python" ]; then
        PYTHON="$HOME/.hermes/sdk/venv/bin/python"
    elif [ -f "$HOME/.hermes/hermes-agent/venv/bin/python" ]; then
        PYTHON="$HOME/.hermes/hermes-agent/venv/bin/python"
    elif command -v hermes &>/dev/null; then
        # Try to resolve from hermes binary location
        PYTHON="$(dirname "$(command -v hermes)")/python" 2>/dev/null || true
        if [ ! -f "$PYTHON" ]; then
            PYTHON=""
        fi
    fi
    if [ -z "$PYTHON" ]; then
        echo "ERROR: Could not find hermes-agent Python interpreter."
        echo "  Set PYTHON=/path/to/python or install hermes-agent SDK:"
        echo "    curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash"
        exit 1
    fi
fi
HERMES_BIN="${HERMES_BIN:-$(which hermes 2>/dev/null || echo "$HOME/.local/bin/hermes")}"

export AETHER_HOME

echo "=== Aether Agents — Starting ==="
echo "Project root: $PROJECT_ROOT"
echo "AETHER_HOME:  $AETHER_HOME"
echo "Python:       $PYTHON"
echo "Hermes:       $HERMES_BIN"
echo ""

# ── Option: install package ──────────────────────────────────────
if [ "${1:-}" = "--install" ]; then
    echo "Installing olympus-mcp package..."
    "$PYTHON" -m pip install -e "$PROJECT_ROOT" 2>&1 | tail -3
    echo ""
fi

# ── Step 1: Setup .env files ─────────────────────────────────────
if [ ! -f "$AETHER_HOME/profiles/ariadna/.env" ]; then
    echo "Step 1: Setting up .env files from .env.example..."
    for profile_dir in "$AETHER_HOME/profiles"/*/; do
        profile_name="$(basename "$profile_dir")"
        if [ -f "$profile_dir/.env.example" ] && [ ! -f "$profile_dir/.env" ]; then
            cp "$profile_dir/.env.example" "$profile_dir/.env"
            echo "  Created $profile_name/.env from .env.example"
        fi
    done
    echo ""
    echo "  IMPORTANT: Edit the .env files in each profile directory"
    echo "  with your actual API keys before using the system."
    echo "  Profile directory: $AETHER_HOME/profiles/"
else
    echo "Step 1: .env files already exist (skipping)"
fi

# ── Step 2: Verify Olympus module ────────────────────────────────
echo "Step 2: Verifying Olympus module..."
PYTHONPATH="$PROJECT_ROOT/src" "$PYTHON" -c "
from olympus.config import get_config, reset_config
from olympus.discovery import discover_agents
reset_config()
config = get_config()
agents = discover_agents(config)
print(f'  Discovered {len(agents)} Daimon(s): {list(agents.keys())}')
if len(agents) < 2:
    print('  WARNING: Expected at least 2 Daimons (ariadna + others)')
" 2>&1
echo ""

# ── Step 3: Olympus config in Hermes ─────────────────────────────
echo "Step 3: Verifying Olympus MCP config in Hermes..."
HERMES_CONFIG="$HOME/.hermes/profiles/hermes/config.yaml"
if grep -q "olympus" "$HERMES_CONFIG" 2>/dev/null; then
    echo "  Olympus MCP server found in Hermes config ✓"
else
    echo "  WARNING: Olympus MCP server not found in $HERMES_CONFIG"
    echo "  Add the following to your Hermes config.yaml:"
    echo ""
    echo "  mcp_servers:"
    echo "    olympus:"
    echo "      command: $PYTHON"
    echo "      args:"
    echo "        - -m"
    echo "        - olympus.server"
    echo "      env:"
    echo "        AETHER_HOME: $AETHER_HOME"
    echo "        PYTHONPATH: $PROJECT_ROOT/src"
    echo "      enabled: true"
fi
echo ""

# ── Step 4: Verify Daimon profiles ──────────────────────────────
echo "Step 4: Verifying Daimon profiles..."
expected_daimons="ariadna hefesto etalides daedalus athena"
for daimon in $expected_daimons; do
    profile_dir="$AETHER_HOME/profiles/$daimon"
    if [ -f "$profile_dir/config.yaml" ]; then
        if grep -q "agent:" "$profile_dir/config.yaml"; then
            echo "  $daimon ✓ (config.yaml with agent field)"
        else
            echo "  $daimon ⚠ (config.yaml exists but missing agent field)"
        fi
    else
        echo "  $daimon ✗ (missing config.yaml)"
    fi
done
echo ""

# ── Step 5: Start Olympus MCP server ─────────────────────────────
echo "Step 5: Olympus MCP server is started automatically by Hermes"
echo "  When Hermes connects, it will spawn Olympus via MCP stdio."
echo "  Daimons are spawned lazily on first talk_to(action=\"open\")."
echo ""

echo "=== Aether Agents Ready ==="
echo "Start Hermes with: hermes"
echo "Then use Olympus tools: talk_to(agent=\"ariadna\", action=\"discover\")"