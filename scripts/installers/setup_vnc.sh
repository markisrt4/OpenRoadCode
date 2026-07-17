#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-$PWD}"
DISPLAY_NUM="${DISPLAY_NUM:-2}"
GEOMETRY="${GEOMETRY:-1280x720}"
DEPTH="${DEPTH:-24}"
RUNTIME_SCRIPT="$PROJECT_DIR/scripts/runtime/start_vnc_server.sh"

echo "[*] Setting up VNC..."

mkdir -p "$HOME/.vnc"
mkdir -p "$PROJECT_DIR/scripts"

if [[ ! -f "$HOME/.vnc/passwd" ]]; then
  echo "[*] Setting VNC password..."
  if command -v vncpasswd >/dev/null 2>&1; then
    printf 'changeme\nchangeme\n' | vncpasswd -user >/dev/null 2>&1 || \
      echo "[!] VNC password setup failed; continuing."
  else
    echo "[!] vncpasswd not found; skipping VNC password setup."
  fi
else
  echo "[*] Existing VNC password found."
fi

echo "[*] Writing ~/.vnc/xstartup..."

cat > "$HOME/.vnc/xstartup" <<'EOF'
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

echo "[*] Installing VNC runtime script..."
chmod +x "$RUNTIME_SCRIPT"

echo "[*] Installing VNC systemd service..."
bash "$PROJECT_DIR/scripts/systemd/install_vnc_systemd.sh"

echo
echo "[*] VNC is configured."
echo "    Display: :$DISPLAY_NUM"
echo "    Port:    $((5900 + DISPLAY_NUM))"
echo
echo "[*] VNC service commands:"
echo "    systemctl --user status carui-vnc.service"
echo "    systemctl --user restart carui-vnc.service"
echo "    journalctl --user -u carui-vnc.service -f"
