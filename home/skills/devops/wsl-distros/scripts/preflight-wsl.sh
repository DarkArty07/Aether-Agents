#!/bin/bash
# preflight-wsl.sh — Verify standard Unix tools before running a third-party installer
# Usage: bash preflight-wsl.sh [distro-family]
#   distro-family: ubuntu | fedora | alma | arch | auto (default: auto-detect)

set -e

DISTRO_FAMILY="${1:-auto}"

# Auto-detect
if [ "$DISTRO_FAMILY" = "auto" ]; then
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        case "$ID" in
            ubuntu|debian) DISTRO_FAMILY="ubuntu" ;;
            fedora) DISTRO_FAMILY="fedora" ;;
            almalinux|rocky|centos|rhel) DISTRO_FAMILY="alma" ;;
            arch|manjaro) DISTRO_FAMILY="arch" ;;
            *) DISTRO_FAMILY="unknown" ;;
        esac
    fi
fi

echo "=== WSL Pre-flight Check ==="
echo "Detected family: $DISTRO_FAMILY"
echo ""

MISSING_TOOLS=()
MISSING_PKGS=()

# Check core tools
for tool in awk sed grep cut tr sort uniq; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        MISSING_TOOLS+=("$tool")
    fi
done

# Check installer-relevant tools
for tool in curl wget gpg; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        MISSING_TOOLS+=("$tool")
    fi
done

# Check Python toolchain
if ! command -v python3 >/dev/null 2>&1; then
    MISSING_TOOLS+=("python3")
fi

# Check build toolchain
for tool in gcc make; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        MISSING_TOOLS+=("$tool")
    fi
done

# Report
if [ ${#MISSING_TOOLS[@]} -eq 0 ]; then
    echo "✓ All standard tools present."
    exit 0
fi

echo "✗ Missing tools: ${MISSING_TOOLS[*]}"
echo ""
echo "Install with the appropriate package manager:"

case "$DISTRO_FAMILY" in
    ubuntu)
        echo "  sudo apt update && sudo apt install -y gawk coreutils grep sed curl ca-certificates python3 python3-pip python3-venv build-essential"
        ;;
    fedora|alma)
        echo "  sudo dnf install -y gawk curl ca-certificates python3 python3-pip python3-devel gcc make"
        ;;
    arch)
        echo "  sudo pacman -S --noconfirm gawk curl ca-certificates python python-pip base-devel"
        ;;
    *)
        echo "  (Unknown distro — install the missing tools using your package manager)"
        ;;
esac

exit 1
