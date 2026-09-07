#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

SERVICE_NAME="openroadcode-service-manager"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
ENV_DIR="/etc/openroadcode"
ENV_FILE="$ENV_DIR/service-manager.env"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
PYTHON_BIN="${OPENROADCODE_PYTHON:-python3}"
HOST="${OPENROADCODE_SERVICE_MANAGER_HOST:-0.0.0.0}"
PORT="${OPENROADCODE_SERVICE_MANAGER_PORT:-8769}"
TOKEN="${OPENROADCODE_SERVICE_MANAGER_TOKEN:-}"

if [[ $EUID -ne 0 ]]; then
    echo "This script needs root privileges to install the service manager." >&2
    echo "Please run: sudo $0" >&2
    exit 1
fi
if ! command -v systemctl >/dev/null 2>&1; then
    echo "systemctl is not available on this system." >&2
    exit 1
fi
if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 is required to generate the service-manager token." >&2
    exit 1
fi

mkdir -p "$ENV_DIR"
chmod 700 "$ENV_DIR"

if [[ -z "$TOKEN" && -f "$ENV_FILE" ]]; then
    TOKEN="$(sed -n 's/^OPENROADCODE_SERVICE_MANAGER_TOKEN=//p' "$ENV_FILE" | head -n 1)"
fi
if [[ -z "$TOKEN" ]]; then
    TOKEN="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
fi
if [[ -z "$TOKEN" ]]; then
    echo "Unable to configure a service-manager token." >&2
    exit 1
fi

umask 077
cat > "$ENV_FILE" <<EOF
OPENROADCODE_SERVICE_MANAGER_TOKEN=$TOKEN
EOF
chmod 600 "$ENV_FILE"

cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=OpenRoadCode Restricted Service Manager
After=network.target
Wants=network.target

[Service]
Type=simple
WorkingDirectory=$PROJECT_ROOT
Environment=PYTHONUNBUFFERED=1
EnvironmentFile=$ENV_FILE
ExecStart=$PYTHON_BIN -m services.linux.systemd_service_manager_http --host $HOST --port $PORT
Restart=on-failure
RestartSec=2
NoNewPrivileges=true
PrivateTmp=true
ProtectHome=true
ProtectSystem=strict
ReadOnlyPaths=$PROJECT_ROOT

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "$SERVICE_NAME.service"
systemctl restart "$SERVICE_NAME.service"

echo "Installed and enabled $SERVICE_FILE"
echo "Service API: http://$HOST:$PORT/services"
echo "Bearer token stored in: $ENV_FILE"
echo "Use: sudo systemctl status $SERVICE_NAME.service"
