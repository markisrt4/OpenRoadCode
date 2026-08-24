# Offline Map Tile Generation

OpenRoadCode uses OpenStreetMap data for both route planning and offline
map rendering.

The same regional `.osm.pbf` source can be used by:

- Valhalla to generate routing graph tiles
- tilemaker to generate MapLibre-compatible vector tiles

## Data flow

OSM PBF
  |
  +--> Valhalla --> routing graph
  |
  +--> tilemaker --> MBTiles --> MapLibre Native

## Current source data

Michigan:

    /opt/valhalla/michigan-latest.osm.pbf

## Generated vector tiles

    /srv/openroadcode/maps/vector/michigan.mbtiles

## Build dependency

tilemaker is built separately and currently expected at:

    ~/src/tilemaker/build/tilemaker

Verify runtime dependencies with:

    ldd ~/src/tilemaker/build/tilemaker | grep "not found"

There should be no output.

## Generate vector tiles

Run:

    scripts/maps/build_map_tiles.sh

The script uses tilemaker's OpenMapTiles-compatible configuration:

    resources/config-openmaptiles.json
    resources/process-openmaptiles.lua

## MapLibre test

The generated MBTiles archive can be referenced from a MapLibre style using:

    mbtiles:///srv/openroadcode/maps/vector/michigan.mbtiles

Use `mbgl-render` to verify the map before integrating it into OpenRoadCode.
