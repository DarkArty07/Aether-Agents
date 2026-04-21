#!/usr/bin/env bash
# configure.sh — Configure Aether Agents for this machine
# Run once after cloning, before start.sh
#
# What it does:
#   1. Substitutes __AETHER_ROOT__ with the actual project root path
#   2. Substitutes __HERMES_PYTHON__ with the hermes-agent venv Python
#   3. Generates home/profiles/hermes/config.yaml from template
#
# Usage:
#   bash scripts/configure.sh
#   HERMES_PYTHON=/custom/path/python bash scripts/configure.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Auto-detect hermes-agent Python (override with HERMES_PYTHON env var)
HERMES_PYTHON="${HERMES_PYTHON:-$HOME/.hermes/hermes-agent/venv/bin/python}"

echo "=== Aether Agents — Configure ==="
echo "  Project root:  $PROJECT_ROOT"
echo "  Hermes Python: $HERMES_PYTHON"
echo ""

# ── Validate hermes Python exists ────────────────────────────────────
if [ ! -f "$HERMES_PYTHON" ]; then
    echo "  WARNING: Hermes Python not found at $HERMES_PYTHON"
    echo "  Install the hermes-agent SDK first:"
    echo "    curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash"
    echo ""
    echo "  Then re-run this script, or set HERMES_PYTHON=/path/to/python"
    exit 1
fi

# ── Portable sed (BSD/macOS vs GNU Linux) ────────────────────────────
sed_inplace() {
    if sed --version 2>/dev/null | grep -q GNU; then
        sed -i "s|$1|$2|g" "$3"
    else
        sed -i '' "s|$1|$2|g" "$3"
    fi
}

# ── Step 1: Configure home/config.yaml ───────────────────────────────
CONFIG="$PROJECT_ROOT/home/config.yaml"
if grep -q "__AETHER_ROOT__\|__HERMES_PYTHON__" "$CONFIG" 2>/dev/null; then
    sed_inplace "__AETHER_ROOT__" "$PROJECT_ROOT" "$CONFIG"
    sed_inplace "__HERMES_PYTHON__" "$HERMES_PYTHON" "$CONFIG"
    echo "  ✓ home/config.yaml configured"
else
    echo "  ✓ home/config.yaml already configured (skipping)"
fi

# ── Step 2: Generate hermes profile config from template ─────────────
TEMPLATE="$PROJECT_ROOT/home/profiles/hermes/config.yaml.template"
HERMES_CONFIG="$PROJECT_ROOT/home/profiles/hermes/config.yaml"

if [ ! -f "$TEMPLATE" ]; then
    echo "  ERROR: Template not found: $TEMPLATE"
    exit 1
fi

# Only generate if it doesn't exist OR still has placeholders
if [ ! -f "$HERMES_CONFIG" ] || grep -q "__AETHER_ROOT__\|__HERMES_PYTHON__" "$HERMES_CONFIG" 2>/dev/null; then
    cp "$TEMPLATE" "$HERMES_CONFIG"
    sed_inplace "__AETHER_ROOT__" "$PROJECT_ROOT" "$HERMES_CONFIG"
    sed_inplace "__HERMES_PYTHON__" "$HERMES_PYTHON" "$HERMES_CONFIG"
    echo "  ✓ home/profiles/hermes/config.yaml generated"
else
    echo "  ✓ home/profiles/hermes/config.yaml already exists (skipping)"
fi

echo ""
echo "=== Configuration complete ==="
echo ""
echo "Next steps:"
echo "  1. Edit home/profiles/hermes/.env with your API keys"
echo "  2. Run: bash scripts/start.sh"
echo "  3. Run: hermes"
