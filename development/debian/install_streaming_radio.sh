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
    fail "this installer currently supports Debian/Ubuntu apt-based systems"
fi

if ! command -v sudo >/dev/null 2>&1; then
    fail "sudo is required to install system packages"
fi

arch="$(dpkg --print-architecture 2>/dev/null || uname -m)"

echo "OpenRoadCode streaming radio setup (Debian/Linux)"
echo "================================================="
echo "Architecture: ${arch}"
echo

if command -v mpv >/dev/null 2>&1; then
    echo "mpv is already installed: $(command -v mpv)"
else
    echo "Installing streaming-radio runtime dependencies..."
    sudo apt-get update
    sudo apt-get install -y \
        ca-certificates \
        mpv
fi

echo
if ! command -v mpv >/dev/null 2>&1; then
    fail "mpv installation completed but the mpv executable was not found"
fi

mpv_path="$(command -v mpv)"
mpv_version="$(mpv --version | head -n 1)"

echo "mpv: ${mpv_path}"
echo "Version: ${mpv_version}"
echo
echo "Streaming radio runtime dependencies are ready."
echo "Run OpenRoadCode streaming-radio tests from the repository root with:"
echo "  python -m unittest -v controllers.radio.unit_test.test_streaming_radio_controller hardware_io.audio.unit_test.test_mpv_streaming_audio_player"
