#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="gpsd-start"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
WRAPPER_SCRIPT="$PROJECT_ROOT/scripts/runtime/start_gpsd.sh"
GPS_DEVICE="${1:-/dev/ttyACM0}"

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
    echo "Please run: sudo $0 $GPS_DEVICE" >&2
    exit 1
fi

chmod +x "$WRAPPER_SCRIPT"

cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=Start gpsd for Drive_ubiquitOS
After=network.target

[Service]
Type=simple
WorkingDirectory=$PROJECT_ROOT
Environment=GPS_DEVICE=$GPS_DEVICE
ExecStart=$WRAPPER_SCRIPT
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "$SERVICE_NAME.service"
systemctl restart "$SERVICE_NAME.service"

echo "Installed and enabled $SERVICE_FILE"
echo "Use: sudo systemctl status $SERVICE_NAME.service"
