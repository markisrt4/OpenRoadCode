#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

INSTALL_ROOT="${OPENROADCODE_NAVIGATION_ROOT:-/opt/openroadcode/navigation}"
CONFIG_ROOT="${OPENROADCODE_CONFIG_ROOT:-/etc/openroadcode}"
DATA_ROOT="${OPENROADCODE_DATA_ROOT:-/srv/openroadcode}"
CACHE_ROOT="${OPENROADCODE_CACHE_ROOT:-$HOME/.cache/openroadcode}"
RENDERER="$INSTALL_ROOT/bin/openroadcode-map-renderer"
CONFIG="${OPENROADCODE_NAVIGATION_CONFIG:-$CONFIG_ROOT/navigation.toml}"
STYLE="$DATA_ROOT/maps/styles/openroadcode.json"
BROKER_SUBSCRIBER_ENDPOINT="${OPENROADCODE_BROKER_SUBSCRIBER_ENDPOINT:-tcp://127.0.0.1:5557}"

if [[ ! -x "$RENDERER" ]]; then
  echo "OpenRoadCode map renderer is not installed: $RENDERER" >&2
  echo "Install the native navigation stack or set OPENROADCODE_NAVIGATION_ROOT." >&2
  exit 1
fi
if [[ ! -f "$CONFIG" ]]; then
  echo "Navigation config is missing: $CONFIG" >&2
  exit 1
fi
if [[ ! -f "$STYLE" ]]; then
  echo "Offline map style is missing: $STYLE" >&2
  exit 1
fi

mkdir -p "$CACHE_ROOT"
export OPENROADCODE_NAVIGATION_CONFIG="$CONFIG"
export OPENROADCODE_DATA_ROOT="$DATA_ROOT"
export OPENROADCODE_CACHE_ROOT="$CACHE_ROOT"
export OPENROADCODE_BROKER_SUBSCRIBER_ENDPOINT="$BROKER_SUBSCRIBER_ENDPOINT"

echo "OpenRoadCode map renderer: $RENDERER"
echo "OpenRoadCode map config: $CONFIG"
echo "OpenRoadCode map data root: $DATA_ROOT"
echo "OpenRoadCode map command bus: $BROKER_SUBSCRIBER_ENDPOINT topic=map.command"
exec "$RENDERER"
