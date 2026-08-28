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

if [[ -d /usr/local/share/tar1090/html || -d /var/www/html/tar1090 ]]; then
    echo "[*] tar1090 appears to be installed already; leaving the existing installation in place."
else
    echo "[*] Installing tar1090..."
    sudo bash -c "$(wget -q -O - https://github.com/wiedehopf/tar1090/raw/master/install.sh)"
fi

if command -v systemctl >/dev/null 2>&1; then
    echo "[*] Enabling ADS-B web services..."
    sudo systemctl enable --now readsb || true
    sudo systemctl enable --now lighttpd || true
fi

if command -v curl >/dev/null 2>&1; then
    if curl -fsI --max-time 3 http://127.0.0.1/tar1090/ >/dev/null; then
        echo "[+] tar1090 is reachable at http://127.0.0.1/tar1090/"
    else
        echo "[*] tar1090 is installed but is not reachable yet; readsb/lighttpd may still be starting."
    fi
fi
