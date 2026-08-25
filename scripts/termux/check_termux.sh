#!/data/data/com.termux/files/usr/bin/bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

fail=0

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

if python - <<'PY' >/dev/null 2>&1
import tkinter
PY
then
  echo "[+] tkinter        import succeeded"
else
  echo "[!] tkinter        import failed" >&2
  fail=1
fi

DISPLAY_VALUE="${DISPLAY:-:1}"
echo "[*] DISPLAY:        $DISPLAY_VALUE"

if [[ -S "/tmp/.X11-unix/X${DISPLAY_VALUE#:}" ]]; then
  echo "[+] X11 socket      available"
else
  echo "[*] X11 socket      not visible at /tmp/.X11-unix/X${DISPLAY_VALUE#:}"
  echo "    This can be normal with Termux:X11; verify that your X server is running."
fi

if (( fail )); then
  echo "[!] Termux environment check failed." >&2
  exit 1
fi

echo "[+] Termux environment looks ready for OpenRoadCode GUI development."
