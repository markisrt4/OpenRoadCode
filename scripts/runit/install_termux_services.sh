#!/data/data/com.termux/files/usr/bin/bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_ROOT="${PREFIX:-/data/data/com.termux/files/usr}/var/service"

if ! command -v sv >/dev/null 2>&1; then
    echo "Termux runit services are not installed." >&2
    echo "Install them with: pkg install termux-services" >&2
    exit 1
fi

mkdir -p "$SERVICE_ROOT"

for service in openroadcode-broker openroadcode-navigation; do
    source_dir="$SCRIPT_DIR/$service"
    target="$SERVICE_ROOT/$service"

    if [[ ! -f "$source_dir/run" ]]; then
        echo "Missing runit service definition: $source_dir/run" >&2
        exit 1
    fi

    chmod +x "$source_dir/run"
    ln -sfn "$source_dir" "$target"
    echo "Installed $service -> $source_dir"
done

echo
echo "OpenRoadCode Termux services installed."
echo "Start them with:"
echo "  sv up openroadcode-broker"
echo "  sv up openroadcode-navigation"
echo
echo "Check status with:"
echo "  sv status openroadcode-broker"
echo "  sv status openroadcode-navigation"
