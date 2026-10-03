#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

if [[ $EUID -ne 0 ]]; then
    echo "This script needs root privileges to install system services." >&2
    echo "Please run: sudo $0" >&2
    exit 1
fi

# Preserve the invoking non-root user for the child installers.
if [[ -z "${SUDO_USER:-}" || "$SUDO_USER" == "root" ]]; then
    echo "Unable to determine the non-root OpenRoadCode runtime user." >&2
    echo "Run this installer through sudo from the intended user account." >&2
    exit 1
fi

bash "$SCRIPT_DIR/install_message_broker_systemd.sh"
bash "$SCRIPT_DIR/install_navigation_service_systemd.sh"
bash "$SCRIPT_DIR/install_automotive_service_systemd.sh"

echo
echo "[+] OpenRoadCode telemetry services installed and enabled."
echo "    Broker:     openroadcode-message-broker.service"
echo "    Navigation: openroadcode-navigation.service"
echo "    Automotive: openroadcode-automotive.service"
