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

The importer adds or updates named food, fuel/charging, grocery, and transit
POIs. OSM ways/relations use their reported bounding-box centers as approximate
marker positions. Availability and brand tags depend on OSM coverage. It
preserves other regions and existing address/street/place data; it does not
remove previously indexed businesses that are now absent from OSM. It is a
local POI refresh, not a full address, map-tile, or routing update. A later full
navigation-dataset pull replaces this index; rerun the downloader afterward if
needed.

The installed database is replaced only after a staged import passes SQLite
validation. Stop ORC before importing so it reopens the replacement cleanly.

Data: © OpenStreetMap contributors, licensed under the Open Database License
(ODbL). See https://www.openstreetmap.org/copyright.
