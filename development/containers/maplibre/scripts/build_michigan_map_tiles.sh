#!/usr/bin/env bash
set -euo pipefail

TILEMAKER_BIN="${TILEMAKER_BIN:-$HOME/src/tilemaker/build/tilemaker}"

OSM_PBF="${OSM_PBF:-/opt/valhalla/michigan-latest.osm.pbf}"

OUTPUT_DIR="${OUTPUT_DIR:-/srv/openroadcode/maps/vector}"
OUTPUT_MBtiles="${OUTPUT_MBtiles:-$OUTPUT_DIR/michigan.mbtiles}"

TILEMAKER_ROOT="${TILEMAKER_ROOT:-$HOME/src/tilemaker}"

CONFIG_FILE="$TILEMAKER_ROOT/resources/config-openmaptiles.json"
PROCESS_FILE="$TILEMAKER_ROOT/resources/process-openmaptiles.lua"

STORE_DIR="${STORE_DIR:-/tmp/tilemaker}"


if [[ ! -x "$TILEMAKER_BIN" ]]; then
    echo "tilemaker not found or not executable: $TILEMAKER_BIN" >&2
    exit 1
fi

if [[ ! -f "$OSM_PBF" ]]; then
    echo "OSM PBF not found: $OSM_PBF" >&2
    exit 1
fi

if [[ ! -f "$CONFIG_FILE" ]]; then
    echo "Tilemaker config not found: $CONFIG_FILE" >&2
    exit 1
fi

if [[ ! -f "$PROCESS_FILE" ]]; then
    echo "Tilemaker process script not found: $PROCESS_FILE" >&2
    exit 1
fi

mkdir -p "$OUTPUT_DIR"
mkdir -p "$STORE_DIR"

echo "Building Michigan vector tiles"
echo "--------------------------------"
echo "Input:      $OSM_PBF"
echo "Output:     $OUTPUT_MBtiles"
echo "Tilemaker:  $TILEMAKER_BIN"
echo

rm -f "$OUTPUT_MBtiles"

"$TILEMAKER_BIN" \
    "$OSM_PBF" \
    "$OUTPUT_MBtiles" \
    --config "$CONFIG_FILE" \
    --process "$PROCESS_FILE" \
    --store "$STORE_DIR"

echo
echo "Map tile build complete:"
ls -lh "$OUTPUT_MBtiles"

