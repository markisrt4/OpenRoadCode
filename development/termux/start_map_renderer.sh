#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

INSTALL_ROOT="${OPENROADCODE_NAVIGATION_ROOT:-${PREFIX:-/data/data/com.termux/files/usr}/opt/openroadcode/navigation}"
DATA_ROOT="${OPENROADCODE_DATA_ROOT:-$HOME/.local/share/openroadcode}"
RUNTIME_ROOT="${OPENROADCODE_RUNTIME_ROOT:-$HOME/.local/state/openroadcode/navigation}"
DISPLAY_VALUE="${DISPLAY:-:1}"
RENDERER="$INSTALL_ROOT/bin/openroadcode-map-renderer"
SOURCE_STYLE="$DATA_ROOT/maps/styles/openroadcode.json"
RUNTIME_STYLE="$RUNTIME_ROOT/openroadcode.termux.json"
RUNTIME_CONFIG="$RUNTIME_ROOT/navigation.termux.toml"
CACHE_PATH="$HOME/.cache/openroadcode/maplibre.db"

[[ -x "$RENDERER" ]] || {
  echo "OpenRoadCode map renderer is not installed: $RENDERER" >&2
  echo "Run ./development/termux/build_navigation_stack.sh first." >&2
  exit 1
}
[[ -f "$SOURCE_STYLE" ]] || {
  echo "Offline map style is missing: $SOURCE_STYLE" >&2
  echo "Pull the navigation dataset before starting the renderer." >&2
  exit 1
}

mkdir -p "$RUNTIME_ROOT" "$(dirname "$CACHE_PATH")"

# The deployable dataset intentionally uses the Linux deployment root. Create a
# target-local runtime style rather than mutating the canonical dataset.
sed "s#/srv/openroadcode#$DATA_ROOT#g" "$SOURCE_STYLE" > "$RUNTIME_STYLE"

cat > "$RUNTIME_CONFIG" <<EOF
[map_renderer]
style = "$RUNTIME_STYLE"
cache = "$CACHE_PATH"

[vehicle_marker]
mode = "blue_dot"
scale = 1.0
EOF

export DISPLAY="$DISPLAY_VALUE"
export OPENROADCODE_NAVIGATION_CONFIG="$RUNTIME_CONFIG"
exec "$RENDERER"
