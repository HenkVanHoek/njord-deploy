#!/bin/bash

# ==============================================================================
#  Installation Script for PiSelfhosting Configurator
# ==============================================================================

# Step 1: Check if the script is run as root (with sudo)
if [ "$(id -u)" -ne 0 ]; then
  echo "Please run this script with sudo: sudo ./install.sh" >&2
  exit 1
fi

echo "Installing PiSelfhosting Configurator..."

# Step 2: Define source and destination paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -f "$SCRIPT_DIR/../dist/PiSelfhostingInstaller" ]; then
  BINARY_PATH="$SCRIPT_DIR/../dist/PiSelfhostingInstaller"
elif [ -f "./PiSelfhosting-Linux" ]; then
  BINARY_PATH="./PiSelfhosting-Linux"
elif [ -f "$SCRIPT_DIR/../PiSelfhosting-Linux" ]; then
  BINARY_PATH="$SCRIPT_DIR/../PiSelfhosting-Linux"
else
  BINARY_PATH="PiSelfhosting-Linux"
fi

if [ -f "$SCRIPT_DIR/../images/piselfhosting-icon192x192.png" ]; then
  ICON_PATH="$SCRIPT_DIR/../images/piselfhosting-icon192x192.png"
else
  ICON_PATH="images/piselfhosting-icon192x192.png"
fi

if [ -f "$SCRIPT_DIR/piselfhosting-Configurator.desktop" ]; then
  DESKTOP_PATH="$SCRIPT_DIR/piselfhosting-Configurator.desktop"
else
  DESKTOP_PATH="piselfhosting-Configurator.desktop"
fi

DEST_BIN="/usr/local/bin"
DEST_ICON="/usr/share/icons/hicolor/256x256/apps"
DEST_DESKTOP="/usr/share/applications"

# Step 3: Create destination directories if they do not exist
mkdir -p "$DEST_BIN"
mkdir -p "$DEST_ICON"
mkdir -p "$DEST_DESKTOP"

# Step 4: Copy files to their final locations
echo "Copying application..."
cp "$BINARY_PATH" "$DEST_BIN/PiSelfhosting-Configurator"

echo "Copying icon..."
cp "$ICON_PATH" "$DEST_ICON/piselfhosting-icon192x192.png"

echo "Creating application shortcut..."
# Copy the desktop file to a temporary location to modify it without changing the repository file
TEMP_DESKTOP="/tmp/piselfhosting-Configurator.desktop"
cp "$DESKTOP_PATH" "$TEMP_DESKTOP"
sed -i "s|Exec=.*|Exec=$DEST_BIN/PiSelfhosting-Configurator|" "$TEMP_DESKTOP"
sed -i "s|Icon=.*|Icon=piselfhosting-icon192x192|" "$TEMP_DESKTOP"
cp "$TEMP_DESKTOP" "$DEST_DESKTOP/"
rm "$TEMP_DESKTOP"

# Step 5: Make the application executable for all users
chmod +x "$DEST_BIN/PiSelfhosting-Configurator"

echo ""
echo "✅ Installation complete!"
echo "You can now find PiSelfhosting Configurator in your applications menu."

exit 0
