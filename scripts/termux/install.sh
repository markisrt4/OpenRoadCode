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
FEATURES_FILE="$PROJECT_ROOT/scripts/installers/installer_features.sh"

config_home="${XDG_CONFIG_HOME:-$HOME/.config}"
mkdir -p "$config_home/openroadcode"
printf 'target = "termux"\n' > "$config_home/openroadcode/host.toml"
echo "[*] Persisted OpenRoadCode host target: termux"

if [[ ! -f "$FEATURES_FILE" ]]; then
  echo "[!] Feature definitions not found: $FEATURES_FILE" >&2
  exit 1
fi
# shellcheck disable=SC1091
source "$FEATURES_FILE"

if (( $# > 0 )); then
  FEATURES=("$@")
else
  FEATURES=(base desktop-ui web-ui browser streamlit spotify navigation)
fi

echo "[*] Termux features: ${FEATURES[*]}"
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
  python-tkinter \
  termux-api \
  termux-x11-nightly \
  xfce4 \
  dbus \
  xorg-xrandr \
  chromium

echo "[*] Creating Termux Python virtual environment: $VENV_DIR"
python -m venv "$VENV_DIR"
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
python -m pip install --upgrade pip wheel setuptools

python_packages=()
for feature in "${FEATURES[@]}"; do
  if ! is_known_feature "$feature"; then
    echo "[!] Unknown Termux feature: $feature" >&2
    exit 1
  fi
  while read -r package; do
    [[ -z "$package" ]] && continue
    if [[ " ${python_packages[*]} " != *" $package "* ]]; then
      python_packages+=("$package")
    fi
  done < <(get_feature_python_packages "$feature")
done

if (( ${#python_packages[@]} > 0 )); then
  echo "[*] Installing feature-selected Python packages..."
  python -m pip install "${python_packages[@]}"
fi

deactivate

echo
bash "$SCRIPT_DIR/check_termux.sh" "$VENV_DIR" "${FEATURES[@]}"
echo
echo "[+] Termux development environment is ready."
echo "    X11 desktop command: termux-x11 :1 -xstartup \"xfce4-session\""
echo "    Activate with:        source \"$VENV_DIR/bin/activate\""
