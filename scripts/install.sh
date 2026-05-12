#!/bin/bash
set -euo pipefail

# Gather Desktop Linux Port - Install Script
# ================================================================
# Copies the built Electron runtime to /opt/applications/gather
# and installs a .desktop entry for your user.
# ================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="${BUILD_DIR:-$REPO_ROOT/build}"
ELECTRON_DIR="$BUILD_DIR/electron"

INSTALL_DIR="${INSTALL_DIR:-/opt/applications/gather}"

if [ ! -d "$ELECTRON_DIR" ]; then
    echo "ERROR: Build not found at $ELECTRON_DIR"
    echo "Run ./scripts/build.sh first"
    exit 1
fi

echo "Installing Gather Desktop to $INSTALL_DIR..."

# Create target directory
mkdir -p "$INSTALL_DIR"

# Copy Electron runtime and app
cp -a "$ELECTRON_DIR"/* "$INSTALL_DIR/"

# Install wrapper script
cp "$REPO_ROOT/bin/gather-wrapper.sh" "$INSTALL_DIR/gather"
chmod +x "$INSTALL_DIR/gather"

# Install icon to FreeDesktop icon hierarchy
ICON_DIR="$HOME/.local/share/icons/hicolor/1024x1024/apps"
mkdir -p "$ICON_DIR"
cp "$INSTALL_DIR/icon.png" "$ICON_DIR/gather.png"

# Install user desktop entry
DESKTOP_DIR="$HOME/.local/share/applications"
mkdir -p "$DESKTOP_DIR"
cp "$REPO_ROOT/assets/gather.desktop" "$DESKTOP_DIR/gather.desktop"

# Update desktop entry executable path (icon is referenced by name)
sed -i "s|Exec=.*|Exec=$INSTALL_DIR/gather %U|g" "$DESKTOP_DIR/gather.desktop"

# Refresh desktop database if available
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$DESKTOP_DIR"
fi

echo ""
echo "Installation complete!"
echo ""
echo "Run from terminal:  $INSTALL_DIR/gather"
echo "Or open from your desktop environment's application menu."
echo ""
echo "Note: If icons don't appear immediately, log out and back in."
