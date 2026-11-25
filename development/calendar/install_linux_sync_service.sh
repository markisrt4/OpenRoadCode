#!/usr/bin/env sh
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
set -eu
if [ "$#" -ne 1 ]; then
    echo "Usage: sh development/calendar/install_linux_sync_service.sh USERNAME" >&2
    exit 2
fi
case "$1" in
    ''|*[!a-zA-Z0-9@._+-]*) echo "Invalid username" >&2; exit 2 ;;
esac
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/../.." && pwd)
PYTHON_BIN="${OPENROADCODE_PYTHON:-$REPO_DIR/.venv/bin/python}"
if [ ! -x "$PYTHON_BIN" ]; then
    echo "Python environment missing. Run bash scripts/dev_setup.sh first." >&2
    exit 1
fi
"$PYTHON_BIN" -c 'import dateutil' || {
    echo "Install python-dateutil in the selected Python environment." >&2
    exit 1
}
# Escape systemd specifiers and reject paths requiring additional quoting.
case "$REPO_DIR$PYTHON_BIN" in
    *%*|*\\*|*\"*) echo "Unsupported service path characters" >&2; exit 2 ;;
esac
UNIT_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
mkdir -p "$UNIT_DIR"
umask 077
cat > "$UNIT_DIR/openroadcode-calendar-sync.service" <<EOF
[Unit]
Description=OpenRoadCode calendar synchronization
Wants=openroadcode-carbonate.service
After=openroadcode-carbonate.service

[Service]
Type=simple
Environment="OPENROADCODE_SECRETS_FILE=%h/.config/openroadcode/secrets.env"
WorkingDirectory=$REPO_DIR
ExecStart="$PYTHON_BIN" -m controllers.calendar.calendar_sync_daemon --username "$1"
Restart=on-failure
RestartSec=10

[Install]
WantedBy=default.target
EOF
systemctl --user daemon-reload
echo "Installed openroadcode-calendar-sync.service"
echo "Start: systemctl --user enable --now openroadcode-calendar-sync.service"
echo "Status: systemctl --user status openroadcode-calendar-sync.service"
echo "Logs: journalctl --user -u openroadcode-calendar-sync.service -f"
