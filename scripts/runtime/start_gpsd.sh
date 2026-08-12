#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
TARGET_SCRIPT="$PROJECT_ROOT/hardware_io/gps/start_gpsd.sh"

if [[ ! -f "$TARGET_SCRIPT" ]]; then
    echo "Target script not found: $TARGET_SCRIPT" >&2
    exit 1
fi

if [[ ! -x "$TARGET_SCRIPT" ]]; then
    chmod +x "$TARGET_SCRIPT"
fi

exec "$TARGET_SCRIPT" "$@"
