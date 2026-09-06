#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

if [[ $EUID -ne 0 ]]; then
    echo "This script needs root privileges." >&2
    echo "Please run: sudo $0 [valhalla-config] [valhalla-workers]" >&2
    exit 1
fi

# Keep the systemd installer aligned with the runtime/deployment layout.
# Navigation data is deployed under /srv/openroadcode, while binaries live
# under /opt/openroadcode/navigation.
VALHALLA_CONFIG="${1:-/srv/openroadcode/valhalla/valhalla.json}"
VALHALLA_WORKERS="${2:-1}"

"$SCRIPT_DIR/install_zeromq_systemd.sh"
"$SCRIPT_DIR/install_valhalla_systemd.sh" "$VALHALLA_CONFIG" "$VALHALLA_WORKERS"
"$SCRIPT_DIR/install_navigation_service_systemd.sh"

systemctl daemon-reload

echo
echo "OpenRoadCode navigation runtime installed and enabled."
echo "Services:"
echo "  openroadcode-zmq.service"
echo "  valhalla.service"
echo "  openroadcode-navigation.service"
echo
echo "Check with:"
echo "  systemctl --no-pager --full status openroadcode-zmq valhalla openroadcode-navigation"
