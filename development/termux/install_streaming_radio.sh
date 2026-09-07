#!/data/data/com.termux/files/usr/bin/bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

fail() {
    echo "Error: $*" >&2
    exit 1
}

case "${PREFIX:-}" in
    */com.termux/files/usr) ;;
    *) fail "this installer is intended for Termux; PREFIX=${PREFIX:-<unset>}" ;;
esac

if ! command -v pkg >/dev/null 2>&1; then
    fail "Termux package manager 'pkg' was not found"
fi

echo "OpenRoadCode streaming radio setup (Termux)"
echo "=========================================="
echo "PREFIX: ${PREFIX}"
echo

if command -v mpv >/dev/null 2>&1; then
    echo "mpv is already installed: $(command -v mpv)"
else
    echo "Refreshing package metadata..."
    pkg update -y

    echo "Installing streaming-radio runtime dependencies..."
    pkg install -y \
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
echo "Termux mpv is configured for Android audio output by the Termux package."
echo "Run OpenRoadCode streaming-radio tests from the repository root with:"
echo "  python -m unittest -v controllers.radio.unit_test.test_streaming_radio_controller hardware_io.audio.unit_test.test_mpv_streaming_audio_player"
