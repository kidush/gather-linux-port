#!/bin/bash
# Gather Desktop wrapper for Linux
# Forces X11 Ozone backend for proper window decorations on Wayland desktops.

INSTALL_DIR="${INSTALL_DIR:-/opt/applications/gather}"
cd "$INSTALL_DIR" || exit 1

exec ./electron resources/app.asar --ozone-platform=x11 "$@"
