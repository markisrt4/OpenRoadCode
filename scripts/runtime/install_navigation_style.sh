#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
DATA_ROOT="${DATA_ROOT:-/srv/openroadcode}"
STYLE_TEMPLATE="${NAVIGATION_STYLE_TEMPLATE:-$PROJECT_ROOT/tools/map_builder/templates/openroadcode-style.json}"
STYLE_DESTINATION="${NAVIGATION_STYLE_DESTINATION:-$DATA_ROOT/maps/styles/openroadcode.json}"

[[ -s "$STYLE_TEMPLATE" ]] || {
  echo "Navigation style template not found: $STYLE_TEMPLATE" >&2
  exit 1
}

# The style is software-version-owned even though it references map data under
# DATA_ROOT. This lets style-only improvements deploy without rebuilding the
# potentially multi-gigabyte MBTiles dataset.
if [[ ! -d "$DATA_ROOT/maps" ]]; then
  echo "[!] Navigation style deployment deferred; map data are not present under $DATA_ROOT/maps" >&2
  exit 0
fi

sudo install -d -m 0755 "$(dirname -- "$STYLE_DESTINATION")"
sudo install -m 0644 "$STYLE_TEMPLATE" "$STYLE_DESTINATION"

echo "[+] Navigation map style installed"
echo "    source:      $STYLE_TEMPLATE"
echo "    destination: $STYLE_DESTINATION"
