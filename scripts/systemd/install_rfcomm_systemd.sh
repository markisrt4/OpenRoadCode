#!/usr/bin/env bash
set -euo pipefail

ADDRESS="${1:-}"
CHANNEL="${2:-}"
RFCOMM_ID="${3:-0}"
SERVICE_NAME="openroadcode-rfcomm${RFCOMM_ID}"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

if [[ $EUID -ne 0 ]]; then
  echo "This installer must run with root privileges." >&2
  exit 1
fi

if [[ ! "$ADDRESS" =~ ^([[:xdigit:]]{2}:){5}[[:xdigit:]]{2}$ ]]; then
  echo "Invalid Bluetooth MAC address: $ADDRESS" >&2
  exit 1
fi
if [[ ! "$CHANNEL" =~ ^[1-9][0-9]*$ ]]; then
  echo "Invalid RFCOMM channel: $CHANNEL" >&2
  exit 1
fi
if [[ ! "$RFCOMM_ID" =~ ^[0-9]+$ ]]; then
  echo "Invalid RFCOMM device number: $RFCOMM_ID" >&2
  exit 1
fi

cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=OpenRoadCode RFCOMM device /dev/rfcomm${RFCOMM_ID}
Wants=bluetooth.service
After=bluetooth.service

[Service]
Type=simple
ExecStart=/usr/bin/rfcomm connect ${RFCOMM_ID} ${ADDRESS} ${CHANNEL}
ExecStop=-/usr/bin/rfcomm release ${RFCOMM_ID}
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
EOF

rfcomm release "$RFCOMM_ID" >/dev/null 2>&1 || true
systemctl daemon-reload
systemctl enable "$SERVICE_NAME.service"
systemctl restart "$SERVICE_NAME.service"

echo "[+] Installed and enabled $SERVICE_FILE"
echo "    Status: systemctl status $SERVICE_NAME.service"
