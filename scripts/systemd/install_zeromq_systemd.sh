#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

SERVICE_NAME="openroadcode-zmq"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
WRAPPER_SCRIPT="$PROJECT_ROOT/scripts/runtime/start_zeromq_broker.sh"
RUN_USER="${SUDO_USER:-${USER:-}}"
PYTHON_BIN="${OPENROADCODE_PYTHON:-python3}"

if [[ $EUID -ne 0 ]]; then
    echo "This script needs root privileges." >&2
    echo "Please run: sudo $0" >&2
    exit 1
fi
if [[ -z "$RUN_USER" || "$RUN_USER" == "root" ]]; then
    echo "Run this installer through sudo from the intended OpenRoadCode user." >&2
    exit 1
fi
if [[ ! -x "$WRAPPER_SCRIPT" ]]; then
    chmod +x "$WRAPPER_SCRIPT"
fi
if ! sudo -u "$RUN_USER" "$PYTHON_BIN" -c 'import zmq' >/dev/null 2>&1; then
    echo "pyzmq is not available to $RUN_USER through $PYTHON_BIN" >&2
    exit 1
fi

cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=OpenRoadCode ZeroMQ Message Broker
After=network.target
Wants=network.target

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
