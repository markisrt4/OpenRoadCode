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
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PYTHON_BIN="${OPENROADCODE_PYTHON:-python3}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    echo "Python executable not found: $PYTHON_BIN" >&2
    exit 127
fi
exec "$PYTHON_BIN" "$SCRIPT_DIR/carbonate_exec.py" "$CARBONATE_BIN"
