#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

SERVICE_NAME="openroadcode-service-manager"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
PYTHON_BIN="${OPENROADCODE_PYTHON:-python3}"
HOST="${OPENROADCODE_SERVICE_MANAGER_HOST:-127.0.0.1}"
PORT="${OPENROADCODE_SERVICE_MANAGER_PORT:-8769}"

if [[ $EUID -ne 0 ]]; then
    echo "This script needs root privileges to install the service manager." >&2
    echo "Please run: sudo $0" >&2
    exit 1
fi
if ! command -v systemctl >/dev/null 2>&1; then
    echo "systemctl is not available on this system." >&2
    exit 1
fi
if [[ "$HOST" != "127.0.0.1" && "$HOST" != "localhost" && "$HOST" != "::1" ]]; then
    echo "The first-stage service manager must remain localhost-only." >&2
    exit 1
fi

cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=OpenRoadCode Restricted Service Manager
After=network.target
Wants=network.target

[Service]
Type=simple
WorkingDirectory=$PROJECT_ROOT
Environment=PYTHONUNBUFFERED=1
ExecStart=$PYTHON_BIN -m services.linux.systemd_service_manager_http --host $HOST --port $PORT
Restart=on-failure
RestartSec=2

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "$SERVICE_NAME.service"
systemctl restart "$SERVICE_NAME.service"

echo "Installed and enabled $SERVICE_FILE"
echo "Local API: http://$HOST:$PORT/services"
echo "Use: sudo systemctl status $SERVICE_NAME.service"
