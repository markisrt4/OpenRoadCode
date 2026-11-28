#!/usr/bin/env sh
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
set -eu
if [ "$#" -ne 1 ]; then
    echo "Usage: sh development/calendar/install_linux_sync_service.sh USERNAME|--accounts" >&2
    exit 2
fi
case "$1" in
    --accounts) ;;
    ''|*[!a-zA-Z0-9@._+-]*) echo "Invalid username" >&2; exit 2 ;;
esac
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/../.." && pwd)
PYTHON_BIN="${OPENROADCODE_PYTHON:-$REPO_DIR/.venv/bin/python}"
if [ ! -x "$PYTHON_BIN" ]; then
    echo "Python environment missing. Run bash development/calendar/dev_setup.sh first." >&2
    exit 1
fi
"$PYTHON_BIN" -c 'import dateutil' || {
    echo "Install python-dateutil in the selected Python environment." >&2
    exit 1
}
cd "$REPO_DIR"
ACCOUNTS_FILE="$HOME/.config/openroadcode/calendar-accounts.json"
SECRETS_FILE="${OPENROADCODE_SECRETS_FILE:-$HOME/.config/openroadcode/secrets.env}"
DEPENDENCIES="Wants=openroadcode-carbonate.service
After=openroadcode-carbonate.service"
if [ "$1" = "--accounts" ]; then
    [ -f "$ACCOUNTS_FILE" ] || { echo "Configure calendar accounts first." >&2; exit 1; }
    ARGS="--accounts-file \"$ACCOUNTS_FILE\""
    DEPENDENCIES=""
    if "$PYTHON_BIN" -c 'import sys; from pathlib import Path; from controllers.calendar.calendar_accounts import load_accounts; sys.exit(not any(a.enabled and a.provider == "proton" for a in load_accounts(Path(sys.argv[1]))))' "$ACCOUNTS_FILE"; then
        DEPENDENCIES="Wants=openroadcode-carbonate.service
After=openroadcode-carbonate.service"
    fi
else
    ARGS="--username \"$1\""
fi
# Escape systemd specifiers and reject paths requiring additional quoting.
case "$REPO_DIR$PYTHON_BIN$ACCOUNTS_FILE$SECRETS_FILE" in
    *%*|*\\*|*\"*) echo "Unsupported service path characters" >&2; exit 2 ;;
esac
UNIT_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
mkdir -p "$UNIT_DIR"
umask 077
STAGING_DIR=$(mktemp -d "$UNIT_DIR/.calendar-sync.XXXXXX")
trap 'rm -rf "$STAGING_DIR"' EXIT
cat > "$STAGING_DIR/openroadcode-calendar-sync.service" <<EOF
[Unit]
Description=OpenRoadCode calendar synchronization
$DEPENDENCIES

[Service]
Type=simple
Environment="OPENROADCODE_SECRETS_FILE=$SECRETS_FILE"
WorkingDirectory=$REPO_DIR
ExecStart="$PYTHON_BIN" -m controllers.calendar.calendar_sync_daemon $ARGS
Restart=on-failure
RestartSec=10

[Install]
WantedBy=default.target
EOF
systemd-analyze --user verify "$STAGING_DIR/openroadcode-calendar-sync.service"
mv "$STAGING_DIR/openroadcode-calendar-sync.service" "$UNIT_DIR/openroadcode-calendar-sync.service"
systemctl --user daemon-reload
echo "Installed openroadcode-calendar-sync.service"

