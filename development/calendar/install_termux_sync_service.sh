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
REPO_DIR=$(pwd -P)
if [ ! -f "$REPO_DIR/controllers/calendar/calendar_sync_daemon.py" ]; then
    echo "Run installer from the OpenRoadCode repository root" >&2
    exit 1
fi
SERVICE_DIR="$PREFIX/var/service/openroadcode-calendar-sync"
mkdir -p "$SERVICE_DIR/log" "$HOME/.local/state/openroadcode-calendar-sync"
# Quote the supplied username as a shell literal to prevent command injection.
QUOTED_USERNAME=$(printf "%s" "$1" | sed "s/'/'\\\\''/g")
cat > "$SERVICE_DIR/run" <<EOF
#!/data/data/com.termux/files/usr/bin/sh
cd '$REPO_DIR'
exec python -m controllers.calendar.calendar_sync_daemon --username '$QUOTED_USERNAME' 2>&1
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
