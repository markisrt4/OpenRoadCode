#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="valhalla"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"

WRAPPER_SCRIPT="$PROJECT_ROOT/scripts/runtime/start_valhalla.sh"

VALHALLA_CONFIG="${1:-/opt/valhalla/valhalla.json}"
VALHALLA_WORKERS="${2:-1}"

if [[ ! -f "$WRAPPER_SCRIPT" ]]; then
    echo "Wrapper script not found: $WRAPPER_SCRIPT" >&2
    exit 1
fi

if [[ ! -f "$VALHALLA_CONFIG" ]]; then
    echo "Valhalla configuration not found: $VALHALLA_CONFIG" >&2
    exit 1
fi

if ! command -v valhalla_service >/dev/null 2>&1; then
    echo "valhalla_service is not available in PATH." >&2
    exit 1
fi

if ! command -v systemctl >/dev/null 2>&1; then
    echo "systemctl is not available on this system." >&2
    exit 1
fi

if [[ $EUID -ne 0 ]]; then
    echo "This script needs root privileges to install a system service." >&2
    echo "Please run: sudo $0 $VALHALLA_CONFIG $VALHALLA_WORKERS" >&2
    exit 1
fi

chmod +x "$WRAPPER_SCRIPT"

cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=Valhalla routing service for OpenRoadCode
After=network.target

[Service]
Type=simple
WorkingDirectory=$PROJECT_ROOT

Environment=VALHALLA_CONFIG=$VALHALLA_CONFIG
Environment=VALHALLA_WORKERS=$VALHALLA_WORKERS

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

