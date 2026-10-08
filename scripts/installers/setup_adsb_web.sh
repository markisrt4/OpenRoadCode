#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/toolchain.lock"
TAR1090_REF="${TAR1090_REF:-$TAR1090_COMMIT}"

if ! command -v readsb >/dev/null 2>&1; then
    echo "[!] readsb is required before installing tar1090." >&2
    exit 1
fi
if ! command -v wget >/dev/null 2>&1; then
    echo "[!] wget is required before installing tar1090." >&2
    exit 1
fi
if ! command -v git >/dev/null 2>&1; then
    echo "[!] git is required before installing pinned tar1090 sources." >&2
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
    source_checkout="$(mktemp -d)"
    trap 'rm -rf "$source_checkout"' EXIT
    git -C "$source_checkout" init --quiet
    git -C "$source_checkout" remote add origin https://github.com/wiedehopf/tar1090.git
    git -C "$source_checkout" fetch --quiet --depth 1 origin "$TAR1090_REF"
    git -C "$source_checkout" checkout --quiet --detach FETCH_HEAD
    sudo bash "$source_checkout/install.sh" /run/readsb "" "" "$source_checkout"
    rm -rf "$source_checkout"
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
