# Download POIs directly in Termux

The phone can download local OpenStreetMap POIs through Overpass and merge them
into its offline SQLite search index. No build VM, Docker, osmium, vector-tile
rebuild, or routing-data rebuild is required. Python's standard library handles
the download and import.

The existing map renderer reports viewport bounds; ORC queries this index and
sends selectable result markers back to the renderer. The markers use the same
provider enrichment and Order action as map-builder POIs.

## Download around the last navigation fix

If ORC has not cached a fix, read location directly from Android Bridge instead.
Open Bridge, select Android Sensors under Navigation, enable the sensor service,
and grant precise location permission. Keep Bridge running while ORC is stopped:

```bash
cd ~/src/OpenRoadCode
git switch android-linux-food-apps
git pull --ff-only origin android-linux-food-apps
python -m tools.poi_download --bridge-position --radius-km 10
```

This reads port 8766 and rejects simulated fixes or fixes older than two minutes.
It does not require ORC to have run previously.

Run ORC long enough to obtain a navigation fix, then stop ORC and the renderer.
Use your usual Termux Python environment:

```bash
cd ~/src/OpenRoadCode
git switch android-linux-food-apps
git pull --ff-only origin android-linux-food-apps
python -m tools.poi_download --radius-km 10
```

The command reports its center before downloading. Check that it is the intended
area: a cached fix can be old or come from a simulated drive. If no cached fix
exists, or you want another area, specify decimal-degree coordinates instead:

```bash
cd ~/src/OpenRoadCode
git switch android-linux-food-apps
python -m tools.poi_download --lat LATITUDE --lon LONGITUDE --radius-km 10
```

Replace `LATITUDE` and `LONGITUDE` with numbers. West longitude is negative.
The default radius is 10 km; the maximum is 25 km to keep public Overpass queries
manageable. Query timeouts or rate limits leave the installed index unchanged;
retry later or reduce the radius. Internet is needed for downloads, not searches.

On Termux, the default database is:

```text
~/.local/share/openroadcode/maps/search/openroadcode-search.sqlite
```

`OPENROADCODE_DATA_ROOT` overrides the data root. `--database PATH` overrides
the exact database file. Use the same data root as your ORC runtime.

Restart ORC and the map renderer after importing. View the downloaded area and
use the Food search, then select a Panera marker and tap Order.

## Data scope

The importer refreshes named food, fuel/charging, grocery, and transit
POIs inside the requested circle. Old OSM POIs inside that circle are removed
and current results are inserted, so deleted, unnamed, or reclassified places
no longer remain as stale search results. OSM ways/relations use their reported bounding-box centers as approximate
marker positions. Availability and brand tags depend on OSM coverage. It
preserves POIs outside that circle, custom POIs, and existing
address/street/place data. It is a
local POI refresh, not a full address, map-tile, or routing update. A later full
navigation-dataset pull replaces this index; rerun the downloader afterward if
needed.

The installed database is replaced only after a staged import passes SQLite
validation. Stop ORC before importing so it reopens the replacement cleanly.

Data: © OpenStreetMap contributors, licensed under the Open Database License
(ODbL). See https://www.openstreetmap.org/copyright.

## Importing saved responses

A plain `--input-json FILE` import merges records without deleting any POIs,
because the response does not identify its query area. To refresh an area from
a saved response, also supply `--lat`, `--lon`, and `--radius-km` matching the
original query. Only use a complete response from the downloader's full set of
category queries; a restaurant-only response would omit other supported POIs.
Area replacement requires Overpass snapshot metadata and rejects server remarks,
missing geometry, and invalid records. A complete empty snapshot clears supported
OSM POIs within the circle. All changes are staged and validated before activation.
