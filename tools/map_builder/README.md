# OpenRoadCode Map Builder

Reproducible Debian-container workflow for generating the offline map and routing data consumed by OpenRoadCode.

It automates the previously manual chain: discover Geofabrik regions, download and validate OSM PBF extracts, merge selected regions when necessary, build MapLibre-compatible MBTiles with tilemaker, install the OpenRoadCode map style and offline glyphs, build Valhalla routing data, validate all generated artifacts, write a build manifest, and publish/deploy the result as a `/srv/openroadcode` dataset.

The recommended production model uses a dedicated map-build machine. The vehicle does not compile its own map data; it pulls validated datasets from the build machine with `scripts/runtime/pull_navigation_data.sh`. See [Navigation Build and Deployment](../../docs/navigation_deployment.md).

## Toolchain

The toolchain is pinned in `toolchain.lock` to specific tilemaker, Valhalla, glyph, and Debian versions. A container engine is used only as a build/data-compilation environment; the OpenRoadCode runtime does not require one. The scripts use Docker by default. To use Podman, set `CONTAINER_ENGINE=podman`:

```bash
CONTAINER_ENGINE=podman ./scripts/build-image.sh
CONTAINER_ENGINE=podman ./scripts/run-builder.sh tui
```

## Build image

```bash
cd tools/map_builder
./scripts/build-image.sh
```

## Interactive region selector

```bash
./scripts/run-builder.sh tui
```

The runner bind-mounts the local `builder/` and `templates/` directories into the container, so Python, TUI, and style-template edits are available immediately. Rebuild the image only after changing the Dockerfile, toolchain versions, or container-installed dependencies.

Controls: Up/Down and PageUp/PageDown navigate, Right expands or collapses a region group, Left collapses or moves to its parent, Space selects, `/` searches, `c` clears the search, Enter accepts the selected regions, and `q` quits. `b` also accepts the selection. Parent/child region combinations are rejected to prevent duplicate map data.

The last accepted selection is stored in `.cache/selected-regions.json`. On the next run, regions that still exist in the current Geofabrik index are selected with `[x]`, and their parent groups are expanded so they are visible. Quitting with `q` leaves the previous accepted selection unchanged.

Before starting an expensive build, the builder checks `build-output/build-manifest.json`. If the manifest contains the same selected Geofabrik regions and the existing generated output passes validation, the existing build is reused instead of rerunning tilemaker and Valhalla. Region order does not matter. Use `--force` when a fresh rebuild is intentional, for example to pick up newer OpenStreetMap source data.

```bash
./scripts/run-builder.sh tui --force
```

## Non-interactive build

```bash
./scripts/run-builder.sh build --regions north-america/us/michigan
```

Multiple regions are comma separated:

```bash
./scripts/run-builder.sh build --regions north-america/us/michigan,north-america/us/ohio
```

Normal non-interactive builds also reuse matching validated output. Force a rebuild with:

```bash
./scripts/run-builder.sh build --regions north-america/us/michigan --force
```

After a successful interactive or non-interactive build, the builder reports the selected region names, their combined source PBF size, total deployable output size, elapsed build time, and output path. When an existing build is reused, it reports that result and prints the validation summary instead.

List known Geofabrik IDs with:

```bash
./scripts/run-builder.sh list
```

## Generated output

The host `build-output/` directory is mounted in the container as `/srv/openroadcode`, so generated file URLs and Valhalla paths are identical during validation and after deployment.

```text
build-output/
├── build-manifest.json
├── maps/
│   ├── source/
│   ├── vector/openroadcode.mbtiles
│   ├── glyphs/
│   ├── search/openroadcode-search.sqlite
│   ├── styles/openroadcode.json
│   └── routes/
└── valhalla/
    ├── valhalla.json
    ├── admins.sqlite
    ├── timezones.sqlite
    ├── tiles/
    └── tiles.tar
```

`maps/routes/` is runtime/debug space. Routes are sent dynamically to the native map renderer rather than generated as part of the base dataset. Vehicle-side deployment preserves this directory across dataset updates.

The canonical style name is `openroadcode.json`; runtime code should not depend on a region-specific filename.

Buildings use offline vector footprints and available height attributes, with a
3.66-metre fallback. Map-anchored directional lighting, vertical shading, and
subtle height-based colors improve depth in the tilted 3D view. ORC applies
light/dark building palettes when generating its runtime style. These effects
require no textures, extra datasets, or network access; restart ORC after pulling
style changes to regenerate the installed style.

## Validation

Validation runs automatically after a build. It checks source PBFs with osmium, MBTiles SQLite integrity and required vector layers, style JSON and runtime sources, glyph presence, Valhalla databases/tiles/extract, an optional `valhalla_service /status` smoke test, and SHA-256 checksums for key artifacts.

Run validation again with:

```bash
./scripts/validate-host.sh
```

A dataset is not considered deployable without a validated `build-manifest.json`.

## Publish on the map-build machine

The recommended vehicle-pull model publishes the latest validated dataset at `/srv/openroadcode` on the map-build machine:

```bash
./scripts/deploy-to-srv.sh
```

The deployment script refuses to install an output tree without a validated `build-manifest.json`. It synchronizes generated data into `/srv/openroadcode` while preserving `maps/routes/` as runtime/debug space. The POI search index is deployed at the canonical runtime path `maps/search/openroadcode-search.sqlite`; legacy `maps/poi/openroadcode-poi.sqlite` outputs are migrated during deployment.

The vehicle can then preview and pull that dataset over SSH:

```bash
./scripts/runtime/pull_navigation_data.sh \
  --source mapbuilder@MAP_HOST:/srv/openroadcode \
  --dry-run

./scripts/runtime/pull_navigation_data.sh \
  --source mapbuilder@MAP_HOST:/srv/openroadcode
```

These commands are run from the OpenRoadCode repository on the **vehicle**, not from `tools/map_builder` on the build host.

SSH key authentication is recommended. For the pull model, the vehicle only requires read access to the published build-machine dataset; the build machine does not need privileged SSH access to the vehicle.

## Optional push deployment

`deploy-to-srv.sh --remote` remains available for development or manually managed targets:

```bash
./scripts/deploy-to-srv.sh --remote openroad@192.168.1.50
make deploy REMOTE=openroad@192.168.1.50
```

For production vehicle updates, prefer the Pi-initiated pull workflow because it controls update timing, stages and validates the incoming dataset, retains the previous dataset, and can roll back after a failed Valhalla restart.

## Cache and scratch data

`.cache/` stores downloaded Geofabrik data, `.scratch/` stores intermediate build data, and `build-output/` contains only the deployable result. These directories are intentionally ignored by Git.

## Tests

```bash
make test
```

The included tests cover Geofabrik region parsing/selection rules, MapLibre style installation/validation, and reuse detection for matching validated build output.

## Attribution

Generated datasets are based on OpenStreetMap/Geofabrik data and use open-source tilemaker, Valhalla, and glyph assets. Downstream applications must preserve the applicable licenses and attribution requirements.

## Optional 3D buildings and interactive installation

Terrain is also available as a separate optional pack through this workflow.
For a direct **Termux download without Docker**, use
`bash development/termux/install_terrain.sh` after switching to
`navigation-cesium`; see [the device install steps](../../docs/cesium_map_experiment.md#shared-builder-and-terminal-install-menu).
On the **map build host**, use:

```bash
git switch navigation-cesium
git pull --ff-only
bash tools/map_builder/scripts/run-builder.sh 3d --layer terrain
```

Choose **2** for Detroit Downtown–Midtown and confirm. The stage downloads a
65×65 USGS 3DEP grid, preserves raw source responses and datum metadata, and
certifies the new `detroit-midtown-terrain` pack. It does not rebuild buildings,
map tiles or routing. A failed download leaves no partial installed pack and
restores the original build certificate when the dataset is unchanged.
The source elevations are in metres; rendering uses relative relief rather
than claiming a conversion to ellipsoid heights. This is coarse ground relief,
not a survey or topo-contour layer.
If the image service returns token errors 498/499, the stage falls back to public
USGS EPQS with a 33×33 grid and two concurrent point queries. The installed
manifest records the actual source, sample grid and datum availability. The
fallback is slower; it does not require credentials.

Publish with the existing command:

```bash
git switch navigation-cesium
bash tools/map_builder/scripts/deploy-to-srv.sh
```

The existing interactive pull menu lists terrain separately from buildings;
select both to install both. The viewer prefers the deployed Downtown–Midtown
terrain pack, falling back to the earlier downtown prototype when absent.


After building the normal navigation dataset, reuse its installed OSM PBFs to
create optional Cesium-compatible building packs. This does not contact Overpass
or rebuild vector tiles/routing. The first stage offers downtown Detroit and the
Downtown–Midtown corridor, using eight bounded building tiles per pack. Imagery and
terrain generation are future builder stages; this command does not download them.

From the repository root, on the map-build host:

```bash
git switch navigation-cesium
git pull --ff-only
bash tools/map_builder/scripts/run-builder.sh 3d
```

The menu selects coverage, describes the available layer and output limits, then
asks for confirmation. Geometry size is known after extraction. For automation:

```bash
git switch navigation-cesium
bash tools/map_builder/scripts/run-builder.sh 3d --coverage detroit-midtown --yes
```

The existing `osmium` toolchain extracts building ways from `maps/source/*.osm.pbf`.
Simple closed polygons use tagged heights, floor-count estimates, or marked 9 m
placeholders. Courtyards and multipolygons are omitted and counted. Packs retain
source filenames/SHA-256 values and ODbL attribution. They live under
`maps/3d/packs/<coverage>/`, with tile geometry and checksums in each pack manifest.
The dataset's `build-manifest.json` certifies optional packs and reports payload
size. Failed builds cannot retain a valid certificate for changed artifacts.
An existing certified pack is reused. A clean base-data rebuild removes generated
3D packs; run the optional stage again before publishing.

Publish using the existing tool, then select optional packs while pulling to Termux
(replace `USER@MAP_HOST` with your actual SSH map-build host):

```bash
git switch navigation-cesium
bash tools/map_builder/scripts/deploy-to-srv.sh
```

On the phone, from its checkout:

```bash
git switch navigation-cesium
git pull --ff-only
bash development/termux/pull_navigation_data.sh --interactive USER@MAP_HOST
```

The install menu shows the remote regions, optional pack layers, coverage and
exact pack size. New manifests also report base dataset size. Map/search/routing
remain one base dataset; optional 3D packs can be included or omitted independently.
Cancellation leaves installed data unchanged. Only chosen pack directories are
transferred. Staging retains partial transfers for retries, reuses unchanged base files from
the installed dataset with rsync `--copy-dest`, and all chosen pack
files are checked against the build certificate before activation. The remote
manifest remains the catalog of available packs; `installed-3d-selection.json`
records the installed subset. Device-owned `cesium/` and `map-packs/` folders are
preserved during updates.

Linux deployment supports the same menu:

```bash
git switch navigation-cesium
bash scripts/runtime/pull_navigation_data.sh --interactive --source USER@MAP_HOST:/srv/openroadcode
```

The viewer prefers a deployed Midtown pack, then another installed builder pack,
then the prototype XDG pack. Matching previously downloaded prototype imagery
can be paired with builder-owned geometry without copying it into the dataset.
Otherwise the original downtown image is retained if installed, and the viewer
reports missing imagery coverage. The SDK still requires its separate one-time
installation. Building data is usable offline without imagery or terrain.

If an earlier failed optional build removed the navigation manifest, recover it
without compiling maps or routing again. This validates the existing dataset and
recovers region IDs from its source PBF filenames:

```bash
git switch navigation-cesium
bash tools/map_builder/scripts/run-builder.sh validate --write-manifest --installed-regions
```

New optional-build failures restore the prior certificate only when revalidation
proves the original dataset remains unchanged. Single-part Osmium MultiPolygons
are supported as ordinary outlines; holes and multi-part geometry remain omitted.
