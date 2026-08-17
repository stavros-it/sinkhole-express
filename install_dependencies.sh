#!/bin/bash
# ============================================================================
# Sinkhole Express - Linux Dependency Installer
# Installs system + Python packages required by the app:
#   - python3-tk          (Tkinter, ships separately on most distros)
#   - customtkinter       (modern dark UI)
#   - keyring             (secret service access for password storage)
# Run from the folder that contains sinkhole_express.pyw
# ============================================================================

set -e

echo ""
echo "============================================"
echo "  Sinkhole Express - Dependency Installer"
echo "============================================"
echo ""

# --- Detect package manager and install python3-tk ---
if command -v apt-get >/dev/null 2>&1; then
    echo "Detected Debian/Ubuntu. Installing python3-tk..."
    sudo apt-get update -qq
    sudo apt-get install -y python3-tk python3-dbus
elif command -v dnf >/dev/null 2>&1; then
    echo "Detected Fedora/RHEL. Installing python3-tkinter..."
    sudo dnf install -y python3-tkinter python3-dbus
elif command -v pacman >/dev/null 2>&1; then
    echo "Detected Arch. Installing tk..."
    sudo pacman -S --noconfirm tk
elif command -v zypper >/dev/null 2>&1; then
    echo "Detected openSUSE. Installing python3-tk..."
    sudo zypper install -y python3-tk python3-dbus-python
else
    echo "[WARNING] Could not detect package manager."
    echo "          Please install python3-tk / tkinter manually."
    echo ""
fi

echo ""

# --- Check that Python 3 is available ---
if ! command -v python3 >/dev/null 2>&1; then
    echo "[ERROR] python3 was not found on your PATH."
    echo "        Install Python 3 from https://www.python.org/downloads/"
    echo ""
    exit 1
fi

echo "Using Python:"
python3 --version
echo ""

# --- Upgrade pip first ---
echo "Upgrading pip..."
python3 -m pip install --upgrade pip --user
echo ""

# --- Install required Python packages ---
echo "Installing required packages: customtkinter, keyring ..."
python3 -m pip install --upgrade customtkinter keyring --user

echo ""
echo "============================================"
echo "  All dependencies installed successfully."
echo "============================================"
echo ""
echo "You can now launch the app with:"
echo "  python3 sinkhole_express.pyw"
echo ""
echo "Note: keyring needs a Secret Service provider (gnome-keyring or kwallet)"
echo "to store the Pi-hole password securely. Most desktop environments"
echo "include one by default."
echo ""
