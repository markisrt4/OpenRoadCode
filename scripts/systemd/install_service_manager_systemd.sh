#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

SERVICE_NAME="openroadcode-service-manager"
SERVICE_USER="openroadcode-service-manager"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
ENV_DIR="/etc/openroadcode"
ENV_FILE="$ENV_DIR/service-manager.env"
SUDOERS_FILE="/etc/sudoers.d/${SERVICE_NAME}"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
PYTHON_BIN="${OPENROADCODE_PYTHON:-python3}"
HOST="${OPENROADCODE_SERVICE_MANAGER_HOST:-0.0.0.0}"
PORT="${OPENROADCODE_SERVICE_MANAGER_PORT:-8769}"
TOKEN="${OPENROADCODE_SERVICE_MANAGER_TOKEN:-}"
SYSTEMCTL_BIN="$(command -v systemctl || true)"

if [[ $EUID -ne 0 ]]; then
    echo "This script needs root privileges to install the service manager." >&2
    echo "Please run: sudo $0" >&2
    exit 1
fi
if [[ -z "$SYSTEMCTL_BIN" ]]; then
    echo "systemctl is not available on this system." >&2
    exit 1
fi
if ! command -v sudo >/dev/null 2>&1; then
    echo "sudo is required for restricted service control." >&2
    exit 1
fi
if ! command -v visudo >/dev/null 2>&1; then
    echo "visudo is required to validate the restricted sudo policy." >&2
    exit 1
fi
if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 is required to generate the service-manager token." >&2
    exit 1
fi

if ! id -u "$SERVICE_USER" >/dev/null 2>&1; then
    useradd --system --no-create-home --shell /usr/sbin/nologin "$SERVICE_USER"
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
OPENROADCODE_SYSTEMCTL=$SYSTEMCTL_BIN
EOF
chmod 600 "$ENV_FILE"

{
    echo "# Managed by OpenRoadCode. Restrict the service manager to approved unit actions."
    for action in start stop restart; do
        for unit in \
            openroadcode-message-broker.service \
            openroadcode-navigation.service \
            openroadcode-automotive.service \
            readsb.service; do
            echo "$SERVICE_USER ALL=(root) NOPASSWD: $SYSTEMCTL_BIN $action $unit"
        done
    done
} > "$SUDOERS_FILE"
chmod 440 "$SUDOERS_FILE"
visudo -cf "$SUDOERS_FILE" >/dev/null

cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=OpenRoadCode Restricted Service Manager
After=network.target
Wants=network.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$PROJECT_ROOT
Environment=PYTHONUNBUFFERED=1
EnvironmentFile=$ENV_FILE
ExecStart=$PYTHON_BIN -m services.linux.systemd_service_manager_http --host $HOST --port $PORT
Restart=on-failure
RestartSec=2
PrivateTmp=true
PrivateDevices=true
ProtectHome=read-only
ProtectSystem=strict
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
LockPersonality=true

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "$SERVICE_NAME.service"
systemctl restart "$SERVICE_NAME.service"

echo "Installed and enabled $SERVICE_FILE"
echo "Service user: $SERVICE_USER"
echo "Restricted sudo policy: $SUDOERS_FILE"
echo "Service API: http://$HOST:$PORT/services"
echo "Bearer token stored in: $ENV_FILE"
echo "Use: sudo systemctl status $SERVICE_NAME.service"
