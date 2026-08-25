#!/data/data/com.termux/files/usr/bin/bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

if [[ "${PREFIX:-}" != /data/data/com.termux/files/usr ]]; then
  echo "[!] Run this script from native Termux, not from a proot Linux distribution." >&2
  exit 1
fi

echo "[*] Updating Termux packages..."
pkg update

echo "[*] Installing OpenRoadCode development prerequisites..."
pkg install -y git python python-tkinter

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
VENV_DIR="${VENV_DIR:-$PROJECT_ROOT/venv-termux}"

echo "[*] Creating Termux Python virtual environment: $VENV_DIR"
python -m venv "$VENV_DIR"
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
python -m pip install --upgrade pip wheel setuptools

# Keep this intentionally small. Hardware/platform-specific dependencies belong
# to their own targets and features, not in the Termux development bootstrap.
python -m pip install requests tomli Pillow

deactivate

echo
bash "$SCRIPT_DIR/check_termux.sh"
echo
echo "[+] Termux development environment is ready."
echo "    Activate with: source \"$VENV_DIR/bin/activate\""
