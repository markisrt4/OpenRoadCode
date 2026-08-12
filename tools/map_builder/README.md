# OpenRoadCode Map Builder

Reproducible Debian-container workflow for generating the offline map and routing data consumed by OpenRoadCode.

It automates the previously manual chain: discover Geofabrik regions, download and validate OSM PBF extracts, merge selected regions when necessary, build MapLibre-compatible MBTiles with tilemaker, install the OpenRoadCode map style and offline glyphs, build Valhalla routing data, validate all generated artifacts, write a build manifest, and deploy the result to `/srv/openroadcode`.

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

Controls: Up/Down and PageUp/PageDown navigate, Space selects, `/` searches, `c` clears the search, Enter accepts the selected regions, and `q` quits. Parent/child region combinations are rejected to prevent duplicate map data.

## Non-interactive build

```bash
./scripts/run-builder.sh build --regions north-america/us/michigan
```

Multiple regions are comma separated:

```bash
./scripts/run-builder.sh build --regions north-america/us/michigan,north-america/us/ohio
```

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
│   ├── styles/openroadcode.json
│   └── routes/
└── valhalla/
    ├── valhalla.json
    ├── admins.sqlite
    ├── timezones.sqlite
    ├── tiles/
    └── tiles.tar
```

`maps/routes/` is runtime/debug space. Routes are sent dynamically to the native map renderer rather than generated as part of the base dataset.

## Validation

Validation runs automatically after a build. It checks source PBFs with osmium, MBTiles SQLite integrity and required vector layers, style JSON and runtime sources, glyph presence, Valhalla databases/tiles/extract, an optional `valhalla_service /status` smoke test, and SHA-256 checksums for key artifacts.

Run validation again with:

```bash
./scripts/validate-host.sh
```

## Deploy to `/srv`

```bash
./scripts/deploy-to-srv.sh
```

The deployment script refuses to install an output tree without a validated `build-manifest.json`. It synchronizes generated data into `/srv/openroadcode` while preserving `maps/routes/` as runtime/debug space.

## Cache and scratch data

`.cache/` stores downloaded Geofabrik data, `.scratch/` stores intermediate build data, and `build-output/` contains only the deployable result. These directories are intentionally ignored by Git.

## Tests

```bash
make test
```

The included tests cover Geofabrik region parsing/selection rules and MapLibre style installation/validation.

## Attribution

Generated datasets are based on OpenStreetMap/Geofabrik data and use open-source tilemaker, Valhalla, and glyph assets. Downstream applications must preserve the applicable licenses and attribution requirements.
