#!/data/data/com.termux/files/usr/bin/bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

if [[ "${PREFIX:-}" != /data/data/com.termux/files/usr ]]; then
  echo "[!] Run this script from native Termux, not from a proot Linux distribution." >&2
  exit 1
fi

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
VENV_DIR="${VENV_DIR:-$PROJECT_ROOT/venv-termux}"

echo "[*] Updating Termux packages..."
pkg update

echo "[*] Upgrading installed Termux packages..."
pkg upgrade -y

echo "[*] Enabling the Termux X11 repository..."
pkg install -y x11-repo

echo "[*] Installing OpenRoadCode Termux host prerequisites..."
pkg install -y \
  git \
  less \
  python \
  python-numpy \
  python-tkinter \
  termux-api \
  termux-x11-nightly \
  xfce4 \
  dbus \
  xorg-xrandr \
  chromium

echo "[*] Creating Termux Python virtual environment: $VENV_DIR"
python -m venv --system-site-packages "$VENV_DIR"
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
python -m pip install --upgrade pip wheel setuptools

# Portable OpenRoadCode runtime dependencies needed by the current browser/car UI paths.
python -m pip install Flask requests tomli Pillow pyzmq pyserial

deactivate

echo
bash "$SCRIPT_DIR/check_termux.sh"
echo
echo "[+] Termux development environment is ready."
echo "    X11 desktop command: termux-x11 :1 -xstartup \"xfce4-session\""
echo "    Activate with:        source \"$VENV_DIR/bin/activate\""
