#!/usr/bin/env sh
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
# Install a user-level systemd service (no root required).
set -eu
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
RUNNER="$SCRIPT_DIR/run_carbonate.sh"
PYTHON_BIN="${OPENROADCODE_PYTHON:-$(command -v python3)}"
CARBONATE_BIN="${CARBONATE_BIN:-carbonate}"
if ! command -v "$CARBONATE_BIN" >/dev/null 2>&1; then
    if [ "$CARBONATE_BIN" = carbonate ] && [ -x "$HOME/go/bin/carbonate" ]; then
        CARBONATE_BIN="$HOME/go/bin/carbonate"
    elif [ "$CARBONATE_BIN" = carbonate ] && [ -x "$HOME/src/carbonate/carbonate" ]; then
        CARBONATE_BIN="$HOME/src/carbonate/carbonate"
    else
        echo "Carbonate executable not found. Build or install Carbonate first." >&2
        exit 1
    fi
fi
CARBONATE_BIN=$(command -v "$CARBONATE_BIN")
case "$CARBONATE_BIN" in
    /*) ;;
    *) echo "Carbonate executable must resolve to an absolute path" >&2; exit 1 ;;
esac
case "$CARBONATE_BIN$PYTHON_BIN$RUNNER" in
    *%*|*\\*|*\"*) echo "Unsupported executable path characters" >&2; exit 1 ;;
esac
UNIT_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
mkdir -p "$UNIT_DIR"
cat > "$UNIT_DIR/openroadcode-carbonate.service" <<EOF
[Unit]
Description=OpenRoadCode Carbonate CalDAV bridge
After=network-online.target

[Service]
Type=simple
Environment="OPENROADCODE_SECRETS_FILE=%h/.config/openroadcode/secrets.env"
Environment="CARBONATE_BIN=$CARBONATE_BIN"
Environment="OPENROADCODE_PYTHON=$PYTHON_BIN"
ExecStart=/bin/sh "$RUNNER"
Restart=on-failure
RestartPreventExitStatus=127
RestartSec=10

[Install]
WantedBy=default.target
EOF
systemctl --user daemon-reload
echo "Installed user service. Start with:"
echo "  systemctl --user enable --now openroadcode-carbonate.service"
echo "Status: systemctl --user status openroadcode-carbonate.service"
echo "Logs: journalctl --user -u openroadcode-carbonate.service -f"
