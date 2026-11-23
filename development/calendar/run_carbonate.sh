#!/usr/bin/env sh
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
# Run the locally installed Carbonate CalDAV bridge.
set -eu
CARBONATE_BIN="${CARBONATE_BIN:-carbonate}"
if ! command -v "$CARBONATE_BIN" >/dev/null 2>&1; then
    if [ -x "$HOME/go/bin/carbonate" ] && [ "$CARBONATE_BIN" = carbonate ]; then
        CARBONATE_BIN="$HOME/go/bin/carbonate"
    fi
fi
if ! command -v "$CARBONATE_BIN" >/dev/null 2>&1; then
    if [ "$CARBONATE_BIN" = carbonate ] && [ -x "$HOME/src/carbonate/carbonate" ]; then
        CARBONATE_BIN="$HOME/src/carbonate/carbonate"
    fi
fi
if ! command -v "$CARBONATE_BIN" >/dev/null 2>&1; then
    echo "Carbonate executable not found: $CARBONATE_BIN" >&2
    exit 127
fi
# Load the existing bridge password without printing it or placing it in argv.
# The file must contain exactly the password, optionally followed by a newline.
PASSWORD_FILE="${CARBONATE_BRIDGE_PASSWORD_FILE:-$HOME/.config/openroadcode/carbonate-bridge-password}"
if [ -z "${CARBONATE_BRIDGE_PASSWORD:-}" ] && [ -f "$PASSWORD_FILE" ]; then
    if [ ! -r "$PASSWORD_FILE" ]; then
        echo "Carbonate password file is not readable" >&2
        exit 1
    fi
    CARBONATE_BRIDGE_PASSWORD=$(cat "$PASSWORD_FILE")
    export CARBONATE_BRIDGE_PASSWORD
fi
if [ -z "${CARBONATE_BRIDGE_PASSWORD:-}" ]; then
    echo "Carbonate bridge password unavailable; configure $PASSWORD_FILE" >&2
    exit 1
fi
exec "$CARBONATE_BIN" serve
