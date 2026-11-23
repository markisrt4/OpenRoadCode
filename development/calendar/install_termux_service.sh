#!/data/data/com.termux/files/usr/bin/sh
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
# Register Carbonate under termux-services (runit).
set -eu
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if ! command -v sv >/dev/null 2>&1; then
    echo "Install termux-services first: pkg install termux-services" >&2
    exit 1
fi
SERVICE_DIR="$PREFIX/var/service/openroadcode-carbonate"
mkdir -p "$SERVICE_DIR"
cat > "$SERVICE_DIR/run" <<EOF
#!/data/data/com.termux/files/usr/bin/sh
exec /data/data/com.termux/files/usr/bin/sh "$SCRIPT_DIR/run_carbonate.sh" 2>&1
EOF
chmod 700 "$SERVICE_DIR/run"
echo "Installed $SERVICE_DIR"
echo "Start: sv up openroadcode-carbonate"
echo "Stop: sv down openroadcode-carbonate"
echo "Status: sv status openroadcode-carbonate"
echo "If the service supervisor is not running, restart Termux after installing termux-services."
echo "Carbonate must be installed and authenticated separately."
