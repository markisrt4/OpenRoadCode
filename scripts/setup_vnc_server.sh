#!/usr/bin/env bash
set -euo pipefail

DISPLAY_NUM="${1:-2}"
GEOMETRY="${2:-1280x720}"
DEPTH="${3:-24}"
VNC_PORT=$((5900 + DISPLAY_NUM))

echo "[*] Creating ~/.vnc..."
mkdir -p "$HOME/.vnc"

if [[ ! -f "$HOME/.vnc/passwd" ]]; then
  echo "[*] Setting VNC password..."
  vncpasswd
else
  echo "[*] Existing VNC password found."
fi

echo "[*] Writing ~/.vnc/xstartup..."

cat > ~/.vnc/xstartup <<'EOF'
#!/bin/sh

unset SESSION_MANAGER
unset DBUS_SESSION_BUS_ADDRESS
unset WAYLAND_DISPLAY

export XDG_SESSION_TYPE=x11
export GDK_BACKEND=x11

xsetroot -solid "#1e1e1e" 2>/dev/null || true
xterm -geometry 100x30+20+20 &

exec /usr/bin/openbox
EOF

chmod +x "$HOME/.vnc/xstartup"

echo "[*] Stopping old VNC display :$DISPLAY_NUM if present..."
vncserver -kill ":$DISPLAY_NUM" 2>/dev/null || true

echo "[*] Cleaning stale locks..."
rm -f "/tmp/.X${DISPLAY_NUM}-lock"
rm -f "/tmp/.X11-unix/X${DISPLAY_NUM}"
rm -f "$HOME/.vnc/"*.pid

echo "[*] Starting VNC display :$DISPLAY_NUM..."
vncserver ":$DISPLAY_NUM" -geometry "$GEOMETRY" -depth "$DEPTH" -localhost no

VM_IP="$(hostname -I | awk '{print $1}')"

echo
echo "[+] VNC server started."
echo "    Display: :$DISPLAY_NUM"
echo "    Port:    $VNC_PORT"
echo "    Connect: ${VM_IP}:${VNC_PORT}"
echo
echo "[*] Logs:"
echo "    $HOME/.vnc/$(hostname):${VNC_PORT}.log"
