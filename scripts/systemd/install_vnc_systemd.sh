#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="carui-vnc"
SERVICE_FILE="$HOME/.config/systemd/user/${SERVICE_NAME}.service"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
RUNTIME_SCRIPT="$PROJECT_ROOT/scripts/runtime/start_vnc_server.sh"
DISPLAY_NUM="${DISPLAY_NUM:-2}"
GEOMETRY="${GEOMETRY:-1280x720}"
DEPTH="${DEPTH:-24}"

if [[ ! -f "$RUNTIME_SCRIPT" ]]; then
    echo "Runtime script not found: $RUNTIME_SCRIPT" >&2
    exit 1
fi

if ! command -v systemctl >/dev/null 2>&1; then
    echo "systemctl is not available on this system." >&2
    exit 1
fi

mkdir -p "$HOME/.config/systemd/user"
chmod +x "$RUNTIME_SCRIPT"

if command -v loginctl >/dev/null 2>&1; then
    if [[ $EUID -eq 0 ]]; then
        loginctl enable-linger "$USER"
    elif command -v sudo >/dev/null 2>&1; then
        sudo loginctl enable-linger "$USER"
    else
        loginctl enable-linger "$USER"
    fi
fi

cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=CarUI VNC Server
After=network-online.target

[Service]
Type=forking
ExecStart=$RUNTIME_SCRIPT $DISPLAY_NUM $GEOMETRY $DEPTH
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable "$SERVICE_NAME.service"
systemctl --user restart "$SERVICE_NAME.service"

echo "Installed and enabled $SERVICE_FILE"
echo "Use: systemctl --user status $SERVICE_NAME.service"
