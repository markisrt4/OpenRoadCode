#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="${SERVICE_NAME:-openroadcode}"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
SECRETS_DIR="${SECRETS_DIR:-/etc/openroadcode}"
SECRETS_FILE="${SECRETS_FILE:-${SECRETS_DIR}/secrets.env}"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
SERVICE_USER="${SERVICE_USER:-${SUDO_USER:-$USER}}"
PYTHON_BIN="${PYTHON_BIN:-/usr/bin/python3}"

if [[ $EUID -ne 0 ]]; then
    echo "This script needs root privileges to install a system service." >&2
    echo "Please run: sudo $0" >&2
    exit 1
fi

if ! command -v systemctl >/dev/null 2>&1; then
    echo "systemctl is not available on this system." >&2
    exit 1
fi

if ! id "$SERVICE_USER" >/dev/null 2>&1; then
    echo "Service user does not exist: $SERVICE_USER" >&2
    exit 1
fi

if [[ ! -x "$PYTHON_BIN" ]]; then
    echo "Python executable not found: $PYTHON_BIN" >&2
    exit 1
fi

if [[ ! -f "$PROJECT_ROOT/apps/carUi/main.py" ]]; then
    echo "Car UI entry point not found under: $PROJECT_ROOT" >&2
    exit 1
fi

install -d -m 0750 -o root -g "$SERVICE_USER" "$SECRETS_DIR"

if [[ ! -e "$SECRETS_FILE" ]]; then
    install -m 0640 -o root -g "$SERVICE_USER" /dev/null "$SECRETS_FILE"
    echo "Created empty secrets file: $SECRETS_FILE"
else
    echo "Keeping existing secrets file: $SECRETS_FILE"
fi

cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=OpenRoadCode Car UI
Wants=network-online.target
After=network-online.target

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$PROJECT_ROOT
EnvironmentFile=$SECRETS_FILE
ExecStart=$PYTHON_BIN -m apps.carUi.main
Restart=on-failure
RestartSec=3

[Install]
WantedBy=graphical.target
EOF

systemctl daemon-reload
systemctl enable "$SERVICE_NAME.service"

echo "Installed and enabled $SERVICE_FILE"
echo "Add KEY=value entries to $SECRETS_FILE, then start the service with:"
echo "  sudo systemctl restart $SERVICE_NAME.service"
echo "View its status with:"
echo "  sudo systemctl status $SERVICE_NAME.service"
