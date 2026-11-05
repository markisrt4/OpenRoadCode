# Offline state map build pipeline

This guide describes how OpenRoadCode builds, publishes, installs, and renders
offline imagery and terrain. Michigan is the qualified reference state. The same
catalog and reusable workflow provide a repeatable path for all 50 states.

## Data products and sources

Each coverage produces two independently checked archives:

- `<coverage>-imagery.zip`: a bounded natural-color image assembled from public
  USGS/USDA NAIP exports. Transparent pixels record water or approved source
  gaps; unsupported partner or commercial imagery is not substituted.
- `<coverage>-terrain.zip`: 64 USGS 3DEP grids. Each grid contains 129 by 129
  elevations in metres with its original vertical-datum metadata and compressed
  source-response provenance.

The U.S. Census Bureau 2024 generalized state boundary file defines the 50-state
catalog. Rectangular build envelopes are planning regions rather than political
clipping. They intentionally include surrounding water and neighboring land.

Visible attribution and retained provenance remain mandatory. NAIP and 3DEP data
rights are independent of CesiumJS and OpenStreetMap licensing.

## Michigan coverage model

`michigan-overview` is the always-available fallback. Its 8 by 8 terrain layout
samples approximately every 650–720 metres and its imagery is an 8192 by 8192
statewide composite. Eight independently resumable detail regions provide about
130–200 metre sampling in the Lower Peninsula and 260–304 metre sampling in the
Upper Peninsula:

- `mi-lower-southwest`
- `mi-lower-southeast`
- `mi-lower-central-west`
- `mi-lower-central-east`
- `mi-lower-northwest`
- `mi-lower-northeast`
- `mi-upper-west`
- `mi-upper-east`

Metro Detroit remains a separate highest-detail tier. Runtime priority is Metro
Detroit, state detail, state overview, then the flat reference globe.

## GitHub Actions build

The registered **Build regional map data** workflow exposes `michigan-all`. It
runs the eight detail coverages sequentially so no more than one coverage's
bounded row matrix pressures the public USGS services at once. Inside a coverage,
eight row jobs retain the existing two-row and two-request concurrency limits.

Dispatch from a checkout authenticated with GitHub CLI:

```bash
git switch navigation-cesium
gh workflow run build-metro-detroit-imagery.yml \
  --ref navigation-cesium \
  -f build_target=michigan-all \
  -f force_rebuild=false
```

Monitor the newest run:

```bash
git switch navigation-cesium
gh run watch "$(gh run list --workflow build-metro-detroit-imagery.yml \
  --branch navigation-cesium --limit 1 --json databaseId --jq '.[0].databaseId')"
```

Each coverage performs these stages:

1. Calculate stable imagery and terrain build fingerprints.
2. Restore a complete checked package when its fingerprint matches.
3. Otherwise restore validated imagery exports and terrain-row caches.
4. Build missing NAIP exports and missing 3DEP grids with bounded retries.
5. Validate checksums, bounds, dimensions, rights metadata, and source records.
6. Assemble imagery and terrain archives plus adjacent `.zip.json` descriptors.
7. Upload temporary checked coverage artifacts.
8. After all eight coverages pass, create one draft Michigan detail release.

A failed rerun restores completed rows and exports. `force_rebuild=true` bypasses
reusable package caches and should be reserved for changed source/build inputs.
The final draft is not published automatically; inspect its assets and rendering.

## Download and install a draft

Draft assets require authenticated `gh release download`. Keep each archive next
to its descriptor, then install every desired coverage:

```bash
git switch navigation-cesium
mkdir -p build-output/michigan-detail
gh release download TAG --dir build-output/michigan-detail

for coverage in \
  mi-lower-southwest mi-lower-southeast \
  mi-lower-central-west mi-lower-central-east \
  mi-lower-northwest mi-lower-northeast \
  mi-upper-west mi-upper-east; do
  python -m development.maps.install_region --coverage "$coverage" \
    --pack-file "build-output/michigan-detail/${coverage}-imagery.zip" --update --yes
  python -m development.maps.install_terrain --coverage "$coverage" \
    --pack-file "build-output/michigan-detail/${coverage}-terrain.zip" --yes
done
```

Installation validates the archive and activates a revision symlink atomically.
Earlier revisions remain available for recovery. Restart `./runOrcUi` after an
installation batch.

## Runtime terrain delivery

The launcher validates installed pack manifests and payload checksums, but sends
only immutable terrain metadata in `/config.json`. Every catalog entry receives
a loopback-only `/data/terrain/<index>` URL. Cesium requests sample payloads only
when a visible heightmap intersects them. Detail grids become eligible at level
7; the overview remains available at coarse levels. This avoids serializing all
installed state samples at startup and permits camera movement across shards.

Terrain height controls display 1× actual relative relief or 2×, 3×, and 4×
exaggeration. Exaggeration never changes the installed source elevations.

## Repeating the build for another state

`development.maps.state_map_catalog` derives all state envelopes from the checked
Census asset and creates detail regions targeting approximately 300-metre or
better sampling. Inspect a plan locally:

```bash
git switch navigation-cesium
python -m development.maps.state_map_catalog --state WI --scope all
python -m development.maps.state_map_catalog --state CA --scope detail --matrix
```

Before `build-state-map-data.yml` reaches the repository's default branch, use
the registered **Build regional map data** workflow as a validation bridge from
the feature branch:

```bash
git switch navigation-cesium
gh workflow run build-metro-detroit-imagery.yml \
  --ref navigation-cesium \
  -f build_target=generic-state \
  -f state=OH \
  -f scope=all \
  -f force_rebuild=false
```

The bridge validates the state input, builds its coverage matrix sequentially,
and creates the same kind of per-state draft release. Once
`build-state-map-data.yml` reaches the repository's default branch, dispatch the
dedicated **Build state map data** workflow instead:

To exercise the automatic catalog across representative state shapes and sizes,
the registered workflow also provides one GitHub-hosted sequential validation
batch. It builds Ohio, Hawaii, California, and Alaska in that order, stopping on
the first failed state:

```bash
git switch navigation-cesium
gh workflow run build-metro-detroit-imagery.yml \
  --ref navigation-cesium \
  -f build_target=validation-states \
  -f force_rebuild=false
```

```bash
git switch navigation-cesium
gh workflow run build-state-map-data.yml \
  --ref navigation-cesium \
  -f state=WI \
  -f scope=all \
  -f force_rebuild=false
```

The state input accepts a postal abbreviation, state name, or two-digit FIPS
code. Releases remain per-state so devices install only wanted coverage. Large
states create more detail regions; Alaska crosses the antimeridian and has many
regions, so its detail matrix should be dispatched in reviewed batches rather
than alongside other states. Do not launch all 50 states simultaneously: stagger
state runs to respect public USGS capacity and GitHub Actions limits.

## Validation and troubleshooting

- A cache hit is accepted only when its descriptor fingerprint matches current
  build inputs.
- Missing or corrupt terrain children fail assembly; partial packs never activate.
- Approved imagery coverage gaps are transparent and recorded in the manifest.
- HTTP 429 and transient 5xx responses use bounded retry/backoff. Rerun to reuse
  completed work rather than forcing a rebuild.
- A successful workflow produces a draft release. Publish only after installing
  and checking water transparency, regional seams, terrain LOD, attribution,
  roads, and state/country boundaries.

During branch development run focused tests. Before merge, the user runs:

```bash
git switch navigation-cesium
python scripts/quality_gate.py
```
