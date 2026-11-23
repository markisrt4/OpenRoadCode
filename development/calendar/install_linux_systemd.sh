#!/usr/bin/env sh
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
# Install a user-level systemd service (no root required).
set -eu
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
RUNNER="$SCRIPT_DIR/run_carbonate.sh"
UNIT_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
mkdir -p "$UNIT_DIR"
cat > "$UNIT_DIR/openroadcode-carbonate.service" <<EOF
[Unit]
Description=OpenRoadCode Carbonate CalDAV bridge
After=network-online.target

[Service]
Type=simple
ExecStart=/bin/sh $RUNNER
Restart=on-failure
RestartSec=10

[Install]
WantedBy=default.target
EOF
systemctl --user daemon-reload
echo "Installed user service. Start with:"
echo "  systemctl --user enable --now openroadcode-carbonate.service"
echo "Status: systemctl --user status openroadcode-carbonate.service"
echo "Logs: journalctl --user -u openroadcode-carbonate.service -f"
echo "Carbonate must be installed and authenticated separately."
