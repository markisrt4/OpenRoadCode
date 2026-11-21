#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Configure the independent SDRForge launchers to use this ORC radio region.
set -euo pipefail
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOCALE="${1:-romeo}"
if [[ ! "$LOCALE" =~ ^[a-zA-Z0-9_-]+$ ]]; then
    echo "Invalid radio locale: $LOCALE" >&2
    exit 2
fi
RADIO_ROOT="$PROJECT_ROOT/config/radio"
if [[ ! -d "$RADIO_ROOT/$LOCALE" ]]; then
    echo "Regional radio profiles not found: $RADIO_ROOT/$LOCALE" >&2
    exit 1
fi
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/sdrforge"
mkdir -p "$CONFIG_DIR"
CONFIG="$CONFIG_DIR/radio-region.conf"
# Values are read as literal data by SDRForge, never evaluated as shell code.
if [[ "$RADIO_ROOT" == *$'\n'* || "$RADIO_ROOT" == *$'\r'* ]]; then
    echo "Unsupported newline in radio configuration path" >&2
    exit 2
fi
printf 'SDRFORGE_RADIO_ROOT=%s\nSDRFORGE_RADIO_LOCALE=%s\n' \
    "$RADIO_ROOT" "$LOCALE" > "$CONFIG"
chmod 600 "$CONFIG"
echo "Configured SDRForge region: $LOCALE"
echo "Radio root: $RADIO_ROOT"
echo "Config: $CONFIG"
echo "Restart the SDRForge service or USB session to apply."
