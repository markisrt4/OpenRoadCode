#!/data/data/com.termux/files/usr/bin/sh
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
# Install ORC calendar sync as a supervised Termux service.
set -eu
if [ "$#" -ne 1 ] || [ -z "$1" ]; then
    echo "Usage: sh development/calendar/install_termux_sync_service.sh USERNAME" >&2
    exit 2
fi
if ! command -v sv >/dev/null 2>&1; then
    echo "Install termux-services first: pkg install termux-services" >&2
    exit 1
fi
case "$1" in
    *[!a-zA-Z0-9@._+-]*)
        echo "Username contains unsupported characters" >&2
        exit 2
        ;;
esac
REPO_DIR=$(pwd -P)
if [ ! -f "$REPO_DIR/controllers/calendar/calendar_sync_daemon.py" ]; then
    echo "Run installer from the OpenRoadCode repository root" >&2
    exit 1
fi
PYTHON_BIN="$PREFIX/bin/python"
"$PYTHON_BIN" -c 'import dateutil' || {
    echo "Install calendar dependencies with bash scripts/dev_setup.sh" >&2
    exit 1
}
SERVICE_DIR="$PREFIX/var/service/openroadcode-calendar-sync"
mkdir -p "$SERVICE_DIR/log" "$HOME/.local/state/openroadcode-calendar-sync"
cat > "$SERVICE_DIR/run" <<EOF
#!/data/data/com.termux/files/usr/bin/sh
cd '$REPO_DIR'
exec '$PYTHON_BIN' -m controllers.calendar.calendar_sync_daemon --username '$1' 2>&1
EOF
chmod 700 "$SERVICE_DIR/run"
cat > "$SERVICE_DIR/log/run" <<'EOF'
#!/data/data/com.termux/files/usr/bin/sh
exec svlogd -tt "$HOME/.local/state/openroadcode-calendar-sync"
EOF
chmod 700 "$SERVICE_DIR/log/run"
echo "Installed openroadcode-calendar-sync"
echo "Start: sv up openroadcode-calendar-sync"
echo "Status: sv status openroadcode-calendar-sync"
echo "Logs: tail -f $HOME/.local/state/openroadcode-calendar-sync/current"
