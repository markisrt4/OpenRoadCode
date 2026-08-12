#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

DISPLAY_NUM="${1:-2}"
GEOMETRY="${2:-1280x720}"
DEPTH="${3:-24}"
VNC_PORT=$((5900 + DISPLAY_NUM))

if command -v vncserver >/dev/null 2>&1; then
  VNC_CMD="vncserver"
elif command -v tigervncserver >/dev/null 2>&1; then
  VNC_CMD="tigervncserver"
elif command -v vncserver-virtual >/dev/null 2>&1; then
  VNC_CMD="vncserver-virtual"
else
  echo "[!] No compatible VNC server command found."
  exit 1
fi

echo "[*] Using VNC command: $VNC_CMD"

echo "[*] Stopping old VNC display :$DISPLAY_NUM if present..."
"$VNC_CMD" -kill ":$DISPLAY_NUM" 2>/dev/null || true

echo "[*] Cleaning stale locks..."
rm -f "/tmp/.X${DISPLAY_NUM}-lock"
rm -f "/tmp/.X11-unix/X${DISPLAY_NUM}"
rm -f "$HOME/.vnc/"*.pid 2>/dev/null || true

echo "[*] Starting VNC display :$DISPLAY_NUM..."

"$VNC_CMD" ":$DISPLAY_NUM" \
  -geometry "$GEOMETRY" \
  -depth "$DEPTH" \
  -localhost no

sleep 2

HOST_IP="$(hostname -I | awk '{print $1}')"

echo
if ss -tuln | grep -q ":${VNC_PORT} "; then
  echo "[+] VNC server started successfully."
else
  echo "[!] WARNING: VNC port ${VNC_PORT} not detected."
fi

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
