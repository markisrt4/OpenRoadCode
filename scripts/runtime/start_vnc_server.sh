#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

DISPLAY_NUM="${1:-2}"
GEOMETRY="${2:-1280x720}"
DEPTH="${3:-24}"
VNC_PORT=$((5900 + DISPLAY_NUM))

if command -v tigervncserver >/dev/null 2>&1; then
  VNC_CMD="tigervncserver"
elif command -v vncserver-virtual >/dev/null 2>&1; then
  VNC_CMD="vncserver-virtual"
else
  echo "[!] No virtual VNC server found. Install tigervnc-standalone-server." >&2
  exit 1
fi

echo "[*] Using VNC command: $VNC_CMD"

auth_args=()
if [[ "$VNC_CMD" == tigervncserver ]]; then
  password_file="${XDG_CONFIG_HOME:-$HOME/.config}/tigervnc/passwd"
  if [[ ! -s "$password_file" ]]; then password_file="$HOME/.vnc/passwd"; fi
  if [[ ! -s "$password_file" ]]; then
    echo "[!] No TigerVNC password file. Run scripts/installers/setup_vnc.sh interactively as the service user." >&2
    exit 1
  fi
  auth_args=(-PasswordFile "$password_file")
fi

echo "[*] Stopping old VNC display :$DISPLAY_NUM if present..."
"$VNC_CMD" -kill ":$DISPLAY_NUM" 2>/dev/null || true

echo "[*] Starting VNC display :$DISPLAY_NUM..."

"$VNC_CMD" ":$DISPLAY_NUM" \
  -geometry "$GEOMETRY" \
  -depth "$DEPTH" \
  -localhost no "${auth_args[@]}"

listener=""
for (( attempt = 0; attempt < 10; attempt++ )); do
  listener="$(ss -Hltn "sport = :$VNC_PORT")"
  if [[ -n "$listener" ]]; then break; fi
  sleep 1
done
if [[ -z "$listener" ]]; then
  echo "[!] $VNC_CMD did not open TCP port $VNC_PORT for display :$DISPLAY_NUM." >&2
  exit 1
fi

HOST_IP="$(hostname -I | awk '{print $1}')"

echo
echo "[+] VNC server is listening."
echo "    Command: $VNC_CMD"
echo "    Display: :$DISPLAY_NUM"
echo "    Port:    $VNC_PORT"
echo "    Connect: ${HOST_IP}:${VNC_PORT}"

echo
echo "[*] Listening ports:"
ss -tulnp | grep "$VNC_PORT" || true

echo
echo "[*] Logs:"
ls -1 "$HOME/.vnc/"*.log 2>/dev/null || true
