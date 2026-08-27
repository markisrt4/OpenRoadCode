#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

SERVICE_NAME="openroadcode-navigation"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
WRAPPER_SCRIPT="$PROJECT_ROOT/scripts/runtime/start_navigation_service.sh"
RUN_USER="${SUDO_USER:-${USER:-}}"
PYTHON_BIN="${OPENROADCODE_PYTHON:-python3}"

if [[ ! -f "$WRAPPER_SCRIPT" ]]; then
    echo "Wrapper script not found: $WRAPPER_SCRIPT" >&2
    exit 1
fi
if ! command -v systemctl >/dev/null 2>&1; then
    echo "systemctl is not available on this system." >&2
    exit 1
fi
if [[ $EUID -ne 0 ]]; then
    echo "This script needs root privileges to install a system service." >&2
    echo "Please run: sudo $0" >&2
    exit 1
fi
if [[ -z "$RUN_USER" || "$RUN_USER" == "root" ]]; then
    echo "Unable to determine the non-root OpenRoadCode runtime user." >&2
    echo "Run this installer through sudo from the intended user account." >&2
    exit 1
fi

chmod +x "$WRAPPER_SCRIPT"

cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=OpenRoadCode Navigation Service
After=network.target gpsd.service openroadcode-zmq.service valhalla.service
Wants=network.target openroadcode-zmq.service

[Service]
Type=simple
User=$RUN_USER
WorkingDirectory=$PROJECT_ROOT
Environment=PYTHONUNBUFFERED=1
Environment=OPENROADCODE_PYTHON=$PYTHON_BIN
ExecStart=$WRAPPER_SCRIPT
Restart=on-failure
RestartSec=2

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "$SERVICE_NAME.service"
systemctl restart "$SERVICE_NAME.service"

echo "Installed and enabled $SERVICE_FILE"
echo "Use: sudo systemctl status $SERVICE_NAME.service"
