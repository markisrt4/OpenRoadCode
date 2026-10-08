#!/data/data/com.termux/files/usr/bin/bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

fail=0
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
VENV_DIR="${1:-$PROJECT_ROOT/venv-termux}"
shift || true
FEATURES=("$@")

check_command() {
  local command_name="$1"
  if command -v "$command_name" >/dev/null 2>&1; then
    printf '[+] %-14s %s\n' "$command_name" "$(command -v "$command_name")"
  else
    printf '[!] %-14s missing\n' "$command_name" >&2
    fail=1
  fi
}

if [[ "${PREFIX:-}" != /data/data/com.termux/files/usr ]]; then
  echo "[!] This does not appear to be a native Termux environment." >&2
  fail=1
else
  echo "[+] Termux prefix: $PREFIX"
fi

check_command python
check_command git
check_command termux-x11
check_command xfce4-session
check_command dbus-launch
check_command xrandr

if [[ " ${FEATURES[*]} " == *" browser "* ]]; then
  check_command chromium
fi

if python - <<'PY' >/dev/null 2>&1
import tkinter
PY
then
  echo "[+] tkinter        import succeeded"
else
  echo "[!] tkinter        import failed" >&2
  fail=1
fi

if [[ -x "$VENV_DIR/bin/python" ]]; then
  if [[ " ${FEATURES[*]} " == *" web-ui "* ]] && ! "$VENV_DIR/bin/python" -m pip show Flask >/dev/null 2>&1; then
    echo "[!] Flask           missing from $VENV_DIR" >&2
    fail=1
  fi
  if [[ " ${FEATURES[*]} " == *" streamlit "* ]] && ! "$VENV_DIR/bin/python" -m pip show streamlit >/dev/null 2>&1; then
    echo "[!] streamlit       missing from $VENV_DIR" >&2
    fail=1
  fi
else
  echo "[!] Termux venv missing: $VENV_DIR" >&2
  fail=1
fi

DISPLAY_VALUE="${DISPLAY:-:1}"
echo "[*] DISPLAY:        $DISPLAY_VALUE"

if DISPLAY="$DISPLAY_VALUE" xrandr --query >/dev/null 2>&1; then
  echo "[+] X11 display     reachable"
else
  echo "[*] X11 display     not currently reachable"
  echo "    Start it with: termux-x11 :1 -xstartup \"xfce4-session\""
fi

if (( fail )); then
  echo "[!] Termux environment check failed." >&2
  exit 1
fi

echo "[+] Termux environment looks ready for OpenRoadCode GUI development."
