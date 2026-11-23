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
    echo "Carbonate executable not found: $CARBONATE_BIN" >&2
    exit 127
fi
exec "$CARBONATE_BIN" serve
