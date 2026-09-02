#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
INSTALL_ROOT="${OPENROADCODE_NAVIGATION_ROOT:-${PREFIX:-/data/data/com.termux/files/usr}/opt/openroadcode/navigation}"
CONFIG_ROOT="${OPENROADCODE_CONFIG_ROOT:-${PREFIX:-/data/data/com.termux/files/usr}/etc/openroadcode}"
DATA_ROOT="${OPENROADCODE_DATA_ROOT:-$HOME/.local/share/openroadcode}"
CACHE_ROOT="${OPENROADCODE_CACHE_ROOT:-$HOME/.cache/openroadcode}"
DISPLAY_VALUE="${DISPLAY:-:1}"
BROKER_SUBSCRIBER_ENDPOINT="${OPENROADCODE_BROKER_SUBSCRIBER_ENDPOINT:-tcp://127.0.0.1:5557}"
RENDERER="$INSTALL_ROOT/bin/openroadcode-map-renderer"
RUNTIME_CONFIG="$HOME/.local/state/openroadcode/navigation/navigation.termux.toml"
CONFIG="${OPENROADCODE_NAVIGATION_CONFIG:-$RUNTIME_CONFIG}"
STYLE="$DATA_ROOT/maps/styles/openroadcode.json"

if [[ ! -f "$CONFIG" && -z "${OPENROADCODE_NAVIGATION_CONFIG:-}" ]]; then
  CONFIG="$CONFIG_ROOT/navigation.toml"
fi

[[ -x "$RENDERER" ]] || {
  echo "OpenRoadCode map renderer is not installed: $RENDERER" >&2
  echo "Run ./development/termux/build_navigation_stack.sh first." >&2
  exit 1
}
[[ -f "$CONFIG" ]] || {
  echo "Navigation config is missing: $CONFIG" >&2
  echo "Run ./development/termux/build_navigation_stack.sh first." >&2
  exit 1
}
[[ -f "$STYLE" ]] || {
  echo "Offline map style is missing: $STYLE" >&2
  echo "Pull the navigation dataset before starting the renderer." >&2
  exit 1
}

mkdir -p "$CACHE_ROOT"

GRAPHICS_ENV="$({
  PYTHONPATH="$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}" python3 - <<'PY'
from apps.launchers.graphics_environment import detect_graphics_runtime

runtime = detect_graphics_runtime()
print(f"OPENROADCODE_GRAPHICS_BACKEND={runtime.backend}")
for key, value in runtime.environment.items():
    print(f"{key}={value}")
PY
})"

while IFS='=' read -r key value; do
  [[ -n "$key" ]] && export "$key=$value"
done <<< "$GRAPHICS_ENV"

export DISPLAY="$DISPLAY_VALUE"
export OPENROADCODE_NAVIGATION_CONFIG="$CONFIG"
export OPENROADCODE_DATA_ROOT="$DATA_ROOT"
export OPENROADCODE_CACHE_ROOT="$CACHE_ROOT"
export OPENROADCODE_BROKER_SUBSCRIBER_ENDPOINT="$BROKER_SUBSCRIBER_ENDPOINT"

echo "OpenRoadCode map graphics backend: ${OPENROADCODE_GRAPHICS_BACKEND:-system}"
echo "OpenRoadCode map config: $CONFIG"
echo "OpenRoadCode map data root: $DATA_ROOT"
echo "OpenRoadCode map command bus: $BROKER_SUBSCRIBER_ENDPOINT topic=map.command"
exec "$RENDERER"
