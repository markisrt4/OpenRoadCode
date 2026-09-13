#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

if ! command -v readsb >/dev/null 2>&1; then
    echo "[!] readsb is required before installing tar1090." >&2
    exit 1
fi
if ! command -v wget >/dev/null 2>&1; then
    echo "[!] wget is required before installing tar1090." >&2
    exit 1
fi

if ! command -v lighttpd >/dev/null 2>&1; then
    echo "[*] Installing lighttpd..."
    sudo apt update
    sudo apt install -y --no-install-recommends lighttpd
fi

dashboard_url="http://127.0.0.1/tar1090/"

dashboard_reachable() {
    command -v curl >/dev/null 2>&1 &&
        curl -fsI --max-time 3 "$dashboard_url" >/dev/null
}

if dashboard_reachable; then
    echo "[*] tar1090 dashboard is already reachable; leaving the existing installation in place."
else
    if [[ -d /usr/local/share/tar1090/html || -d /var/www/html/tar1090 ]]; then
        echo "[!] tar1090 files exist but the dashboard is unavailable; repairing the installation..."
    else
        echo "[*] Installing tar1090..."
    fi
    installer="$(mktemp)"
    trap 'rm -f "$installer"' EXIT
    wget -q -O "$installer" https://github.com/wiedehopf/tar1090/raw/master/install.sh
    sudo bash "$installer" /run/readsb
    rm -f "$installer"
    trap - EXIT
fi

tar1090_config="/usr/local/share/tar1090/html/config.js"
if [[ -f "$tar1090_config" ]]; then
    runtime_user="${SUDO_USER:-$(id -un)}"
    runtime_group="$(id -gn "$runtime_user")"
    echo "[*] Allowing $runtime_user to manage tar1090 UI preferences..."
    sudo chown "$runtime_user:$runtime_group" "$tar1090_config"
fi

if command -v systemctl >/dev/null 2>&1; then
    # readsb owns the RTL-SDR while running. OpenRoadCode starts it on demand
    # through ADSBLauncher so the receiver remains available to SDR++/radio.
    echo "[*] Configuring ADS-B services..."
    sudo systemctl disable --now readsb || true
    sudo systemctl enable --now lighttpd || true
fi

if command -v curl >/dev/null 2>&1; then
    for _ in {1..10}; do
        if dashboard_reachable; then
            echo "[+] tar1090 is reachable at $dashboard_url"
            exit 0
        fi
        sleep 1
    done
    echo "[!] tar1090 installation completed, but $dashboard_url is still unavailable." >&2
    echo "[!] Check: systemctl status lighttpd tar1090 --no-pager -l" >&2
    exit 1
fi
