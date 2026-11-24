#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Select a packaged SDRForge region or an explicit external override.
set -euo pipefail
LOCALE="${1:-romeo}"
RADIO_ROOT="${2:-}"
if [[ ! "$LOCALE" =~ ^[a-zA-Z0-9_-]+$ ]]; then
    echo "Invalid radio locale: $LOCALE" >&2
    exit 2
fi
if [[ -n "$RADIO_ROOT" ]]; then
    RADIO_ROOT="$(cd "$RADIO_ROOT" && pwd)"
    if [[ ! -d "$RADIO_ROOT/$LOCALE" ]]; then
        echo "Regional radio profiles not found: $RADIO_ROOT/$LOCALE" >&2
        exit 1
    fi
fi
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/sdrforge"
mkdir -p "$CONFIG_DIR"
CONFIG="$CONFIG_DIR/radio-region.conf"
if [[ "$RADIO_ROOT" == *$'\n'* || "$RADIO_ROOT" == *$'\r'* ]]; then
    echo "Unsupported newline in radio configuration path" >&2
    exit 2
fi
# Values are literal data, never evaluated as shell code.
(
    umask 077
    printf 'SDRFORGE_RADIO_ROOT=%s\nSDRFORGE_RADIO_LOCALE=%s\n' \
        "$RADIO_ROOT" "$LOCALE" > "$CONFIG"
)
chmod 600 "$CONFIG"
echo "Configured SDRForge region: $LOCALE"
echo "Radio root: ${RADIO_ROOT:-packaged catalog}"
echo "Config: $CONFIG"
echo "Restart the SDRForge service or USB session to apply."
