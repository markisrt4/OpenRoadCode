#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

fail() {
    echo "Error: $*" >&2
    exit 1
}

if [[ "${EUID}" -eq 0 ]]; then
    fail "run this script as a normal user with sudo access, not as root"
fi

if ! command -v apt-get >/dev/null 2>&1; then
    fail "this setup script currently supports Debian/Ubuntu apt-based systems"
fi

arch="$(dpkg --print-architecture)"

echo "OpenRoadCode media setup (Debian/Linux)"
echo "======================================="
echo "Architecture: ${arch}"
echo

sudo apt-get update
sudo apt-get install -y \
    ca-certificates \
    wget \
    xdotool

if [[ "${arch}" == "amd64" ]]; then
    if command -v google-chrome-stable >/dev/null 2>&1; then
        echo "Google Chrome stable is already installed."
    else
        package="$(mktemp --suffix=.deb)"
        cleanup() {
            rm -f -- "$package"
        }
        trap cleanup EXIT

        echo "Installing Google Chrome stable for Spotify Web Playback SDK support..."
        wget -qO "$package" \
            https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
        sudo apt-get install -y "$package"

        trap - EXIT
        rm -f -- "$package"
    fi
else
    echo
    echo "NOTE: Google Chrome stable is not installed automatically on ${arch}."
    echo "Spotify REMOTE mode remains usable, but PLAYER mode requires a browser"
    echo "with Spotify Web Playback SDK/EME support."
fi

echo
if command -v google-chrome-stable >/dev/null 2>&1; then
    echo "Chrome: $(command -v google-chrome-stable)"
else
    echo "Chrome: not available"
fi

echo "xdotool: $(command -v xdotool)"
echo
echo "Media runtime setup complete."
echo "Configure Spotify credentials separately with:"
echo "  ./development/debian/install_secrets.sh"
