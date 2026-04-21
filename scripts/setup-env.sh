#!/usr/bin/env bash
# setup-env.sh — Generate .env per profile from shared/env.base
# Usage: ./scripts/setup-env.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AETHER_HOME="${AETHER_HOME:-$(dirname "$SCRIPT_DIR")/home}"
ENV_BASE="$AETHER_HOME/../shared/env.base"

echo "=== Aether Agents — Environment Setup ==="
echo "AETHER_HOME: $AETHER_HOME"
echo ""

# Check env.base exists
if [ ! -f "$ENV_BASE" ]; then
    echo "ERROR: shared/env.base not found at $ENV_BASE"
    exit 1
fi

# Copy env.base to each profile's .env
for profile_dir in "$AETHER_HOME"/profiles/*/; do
    profile_name=$(basename "$profile_dir")
    
    # Skip hermes orchestrator profile — uses main ~/.hermes/.env
    if [ "$profile_name" = "hermes" ]; then
        echo "SKIP: hermes (uses main ~/.hermes/.env)"
        continue
    fi
    
    target="$profile_dir.env"
    
    if [ -f "$target" ]; then
        echo "EXISTS: $profile_name/.env (skipping — edit manually)"
    else
        cp "$ENV_BASE" "$target"
        echo "CREATED: $profile_name/.env (fill in API keys)"
    fi
done

echo ""
echo "=== Done ==="
echo "Remember to fill in API keys in each profile's .env file"
echo "  Profiles: $AETHER_HOME/profiles/*/"