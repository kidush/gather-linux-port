#!/bin/bash
set -euo pipefail

# Gather Desktop Linux Port - Build Script
# ================================================================
# This script extracts the macOS Gather.app, applies Linux compatibility
# patches, and prepares a runnable Linux build with the matching Electron
# runtime.
#
# Prerequisites:
#   - Node.js + npm
#   - Python 3
#   - curl, unzip
#   - Pillow (Python) for icon conversion
#   - The macOS Gather.app bundle (obtain from official releases)
#
# Usage:
#   GATHER_APP=/path/to/Gather.app ./scripts/build.sh
# ================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

# Configuration
GATHER_APP="${GATHER_APP:-$HOME/Downloads/Gather.app}"
ELECTRON_VERSION="${ELECTRON_VERSION:-37.6.0}"
ELECTRON_ZIP="electron-v${ELECTRON_VERSION}-linux-x64.zip"
ELECTRON_URL="https://github.com/electron/electron/releases/download/v${ELECTRON_VERSION}/${ELECTRON_ZIP}"
BUILD_DIR="${BUILD_DIR:-$REPO_ROOT/build}"
WORK_DIR="$BUILD_DIR/work"
ELECTRON_DIR="$BUILD_DIR/electron"

echo "=== Gather Desktop Linux Port Build ==="
echo "Gather app:      $GATHER_APP"
echo "Electron version: $ELECTRON_VERSION"
echo "Build directory:  $BUILD_DIR"
echo ""

# --- Dependency checks ---
command -v node >/dev/null 2>&1 || { echo "ERROR: Node.js is required"; exit 1; }
command -v npm >/dev/null 2>&1 || { echo "ERROR: npm is required"; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "ERROR: Python 3 is required"; exit 1; }
command -v curl >/dev/null 2>&1 || { echo "ERROR: curl is required"; exit 1; }
command -v unzip >/dev/null 2>&1 || { echo "ERROR: unzip is required"; exit 1; }

python3 -c "from PIL import Image" 2>/dev/null || {
    echo "ERROR: Python Pillow is required (pip install Pillow)"
    exit 1
}

# --- Auto-download macOS app if not present ---
if [ ! -d "$GATHER_APP" ]; then
    echo "Gather.app not found at $GATHER_APP"
    echo "Attempting to download latest macOS release from GitHub..."
    echo ""
    DOWNLOADED_APP=$(python3 "$SCRIPT_DIR/download-macos-app.py" ~/Downloads 2>&1)
    if [ $? -eq 0 ]; then
        GATHER_APP="$DOWNLOADED_APP"
        echo "Using downloaded app: $GATHER_APP"
        echo ""
    else
        echo "$DOWNLOADED_APP"
        echo ""
        echo "Please download the macOS Gather Desktop app manually from:"
        echo "  https://github.com/gathertown/gather-town-desktop-releases"
        echo ""
        echo "Then set the path:"
        echo "  GATHER_APP=/path/to/Gather.app ./scripts/build.sh"
        exit 1
    fi
fi

# --- Step 1: Extract app.asar from macOS bundle ---
echo "[1/9] Extracting app.asar from Gather.app..."
mkdir -p "$WORK_DIR"
cp "$GATHER_APP/Contents/Resources/app.asar" "$WORK_DIR/app.asar"

# --- Step 2: Install @electron/asar locally ---
echo "[2/9] Installing @electron/asar tool..."
cd "$WORK_DIR"
if [ ! -d "node_modules/@electron/asar" ]; then
    npm install @electron/asar
fi

# --- Step 3: Extract app.asar contents ---
echo "[3/9] Extracting app.asar contents..."
rm -rf "$WORK_DIR/extracted"
node -e "require('@electron/asar').extractAll('$WORK_DIR/app.asar', '$WORK_DIR/extracted')"

# --- Step 4: Remove macOS-only binaries ---
echo "[4/9] Removing macOS-only native binaries..."
rm -rf "$WORK_DIR/extracted/node_modules/gather-native-desktop-utils"
rm -rf "$WORK_DIR/extracted/resources/bin/*"

# --- Step 5: Apply Linux stub patches ---
echo "[5/9] Applying Linux compatibility stubs..."
python3 "$SCRIPT_DIR/apply-linux-stubs.py" "$WORK_DIR/extracted/build/js/entry.js"

# --- Step 6: Apply v2 URL patches ---
echo "[6/9] Applying v2 URL migration patches..."
python3 "$SCRIPT_DIR/apply-v2-patches.py" "$WORK_DIR/extracted/build/js/entry.js"

# --- Step 7: Apply window decoration fixes ---
echo "[7/9] Applying Linux window decoration fixes..."
python3 "$SCRIPT_DIR/apply-window-fixes.py" "$WORK_DIR/extracted/build/js/entry.js"

# --- Step 8: Create gather-native-desktop-utils stub ---
echo "[8/9] Creating gather-native-desktop-utils stub..."
mkdir -p "$WORK_DIR/extracted/node_modules/gather-native-desktop-utils"
cp "$REPO_ROOT/stubs/gather-native-desktop-utils.js" \
   "$WORK_DIR/extracted/node_modules/gather-native-desktop-utils/index.js"

# --- Step 9: Repack app.asar ---
echo "[9/9] Repacking patched app.asar..."
rm -f "$WORK_DIR/app.asar.patched"
node -e "require('@electron/asar').createPackage('$WORK_DIR/extracted', '$WORK_DIR/app.asar.patched')"

# --- Download Electron Linux runtime ---
echo ""
echo "Downloading Electron ${ELECTRON_VERSION} for Linux..."
mkdir -p "$ELECTRON_DIR"
cd "$ELECTRON_DIR"
if [ ! -f "$ELECTRON_ZIP" ]; then
    curl -L -o "$ELECTRON_ZIP" "$ELECTRON_URL"
fi
unzip -o "$ELECTRON_ZIP"

# --- Install patched app.asar into Electron ---
echo "Installing patched app.asar into Electron runtime..."
cp "$WORK_DIR/app.asar.patched" "$ELECTRON_DIR/resources/app.asar"

# --- Convert icon ---
echo "Converting icon..."
python3 -c "
from PIL import Image
img = Image.open('$GATHER_APP/Contents/Resources/icon.icns')
img.save('$ELECTRON_DIR/icon.png')
print('Icon saved:', img.size)
"

# --- Summary ---
echo ""
echo "=========================================================="
echo "  Build complete!"
echo "=========================================================="
echo ""
echo "Electron runtime:  $ELECTRON_DIR"
echo "Patched app.asar:  $ELECTRON_DIR/resources/app.asar"
echo "Icon:              $ELECTRON_DIR/icon.png"
echo ""
echo "Run directly:"
echo "  $ELECTRON_DIR/electron $ELECTRON_DIR/resources/app.asar --ozone-platform=x11"
echo ""
echo "Install system-wide:"
echo "  sudo $SCRIPT_DIR/install.sh"
echo ""
