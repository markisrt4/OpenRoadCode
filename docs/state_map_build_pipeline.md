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

## Experimental Rochester staged-file trial

`rochester-static-trial` in **Build regional map data** is isolated from the
normal export-based builders. It queries the NAIP index for Rochester, selects
one dated acquisition year, and downloads the referenced public USGS staged
image files. TNMAccess locates a staged 1/3-arc-second 3DEP GeoTIFF covering the
same bounds. No image-export or point-elevation requests are made.

GDAL runs only on the Actions build host. It clips/reprojects RGB imagery to
4096×4096 pixels and bilinearly samples a 129×129 terrain grid. Terrain samples
are aligned to the existing pack's endpoint-based grid convention. The vertical
datum is explicitly unresolved in this trial; do not treat relative rendered
heights as ellipsoid altitudes. Catalog records and source raster metadata are
retained. Incomplete imagery coverage or invalid elevations fail the trial.

The trial permits at most 12 imagery files and one DEM, with 512 MiB per-file
and 1 GiB combined local source/crop-payload limits. Downloads have three attempts and a
40-minute job deadline; retries can transfer additional bytes. Completed files
are cached with URL/size/hash receipts. Partial-file transfers restart, and
`force_rebuild=true` skips old source caches when a new acquisition is intended.
This is not a statewide bulk-download implementation.

Successful output is two ZIPs in the existing phone-installable pack formats,
each with its descriptor, plus `source-plan.json` and `trial-report.json`. Trial
build identities differ from the production builder so its caches cannot reuse
experimental output. Outputs are Actions artifacts retained for seven days;
this job neither publishes a Release nor installs or activates data on a phone.
Inspect quality and compare timing, transfer sizes, source years and relief
against the current Rochester pack before changing production or publishing.

```bash
git switch navigation-cesium
gh workflow run build-metro-detroit-imagery.yml --ref navigation-cesium \
  -f build_target=rochester-static-trial -f force_rebuild=false
```

Source references:
[USGS NAIP archive](https://www.usgs.gov/centers/eros/science/usgs-eros-archive-aerial-photography-national-agriculture-imagery-program-naip),
[TNMAccess API](https://tnmaccess.nationalmap.gov/api/v1/docs), and
[3DEP products](https://www.usgs.gov/3d-elevation-program/about-3dep-products-services).
The separate AWS NAIP mirror uses requester-pays access and is not used here.

### Rochester source-access findings

The first live trial (Actions run 42127306036) found that the current NAIP index
returns EarthExplorer landing pages rather than direct files. Follow-up directory
checks (run 42128007673) found no objects at the expected Michigan 2022 staged
prefix. This is an observed access/layout limitation, not evidence that the
imagery does not exist. These runs produced diagnostic artifacts, not map packs.

The optional `trial_imagery_source=planetary-computer` selects Microsoft's public
NAIP COG mirror for a separate trial. It validates the NAIP collection and USDA
licensor identity, selects a dated year and retains the collection/item metadata.
The build host requests a short-lived anonymous read URL from the documented
signing API; signed URLs/tokens are not written to receipts or packs. Files are
cached by their unsigned source URL and content hash. No account/subscription key
is configured and the phone does not contact Microsoft. The 3DEP source stays the
USGS staged GeoTIFF. Public access can still be throttled; this is not a guarantee
of service availability or permission to substitute other imagery collections.

```bash
git switch navigation-cesium
gh workflow run build-metro-detroit-imagery.yml --ref navigation-cesium \
  -f build_target=rochester-static-trial \
  -f trial_imagery_source=planetary-computer -f force_rebuild=false
```

References: [Microsoft's anonymous data-access documentation](https://planetarycomputer.microsoft.com/docs/concepts/sas/)
and [NAIP collection metadata](https://planetarycomputer.microsoft.com/api/stac/v1/collections/naip).

The mirror trial found four July 2022 NAIP COGs, but full-resolution whole-file
transfers exceeded the small trial's payload cap. It now reads geographic crops
from static COG files using HTTP range requests and caches self-contained local
GeoTIFFs. No custom image-export service is invoked. Range-transfer byte counts
are not yet instrumented; `cached_source_bytes` measures local crop/DEM storage,
not total network traffic. Original acquisition dates, asset URLs and spatial
metadata remain in the source plan. Temporary signed access URLs are redacted
from GDAL diagnostics and never included in the published pack metadata.

### First successful Rochester COG trial (2026-11-08)

[Actions run 42496879182](https://github.com/markisrt4/OpenRoadCode/actions/runs/42496879182)
completed successfully on `eacdeaa8`. The script reported 40.95 seconds excluding
runner setup, four 60-cm source NAIP tiles acquired on 2022-07-30, a complete
4096×4096 RGB image (6,517,068 bytes), and 16,641 valid ground samples ranging
from 210.91 to 282.46 metres. Those are source elevations; runtime still displays
relative relief and does not resolve/convert the original vertical datum.

Imagery and terrain archives are 6,538,261 and 128,693 bytes respectively. The
combined Actions artifact is 6,682,920 bytes, ID `13623777678`, retained until
2026-11-15. The agent downloaded it, verified the outer artifact and both inner
archive checksums, validated packs with existing readers, and visually inspected
a reduced-resolution image preview for obvious gaps. This does not establish
better performance than an equivalent export build, street-level image quality
in ORC, or Termux GPU stability. Range network bytes are unmeasured; the report's
483,668,404 cached-source bytes are local crop/DEM storage.

For device review, download the artifact with authenticated GitHub CLI; it
extracts the two pack ZIPs and their adjacent descriptors. No USGS processing
runs on the phone:

```bash
git switch navigation-cesium
git pull --ff-only
source venv-termux/bin/activate
gh run download 42496879182 --repo markisrt4/OpenRoadCode \
  --name rochester-static-trial-42496879182 \
  --dir build-output/rochester-static-trial
python -m development.maps.install_region --coverage rochester --update \
  --pack-file build-output/rochester-static-trial/rochester-imagery.zip
python -m development.maps.install_terrain --coverage rochester \
  --pack-file build-output/rochester-static-trial/rochester-terrain.zip
./runOrcUi
```

Reopen Terrain and zoom into Rochester. The streaming catalog includes the
installer-owned Rochester/Southfield local terrain directories at close zoom,
above regional focus grids; broad state/metro terrain remains the distant
fallback. Source samples remain loaded only when requested through the existing
loopback terrain transport. No production builder or published release changed.

Archive installation also migrates an older real terrain directory into a
retained `.previous-terrain-*` backup before activating the new revision. If
activation fails, it restores the original directory. Stop ORC before installing
this update. This migration does not delete previous source packs.


### Southfield staged-source trial

The same bounded trial builder accepts `--coverage southfield`; Rochester remains
the default. In Actions, select `build_target=rochester-static-trial`,
`trial_coverage=southfield`, and `trial_imagery_source=planetary-computer`. The
legacy target name is retained for compatibility. Outputs use Southfield preset
bounds, metadata and filenames (`southfield-imagery.zip`, `southfield-terrain.zip`),
with the same 4096×4096 imagery and 129×129 terrain quality settings. Source
selection, rights checks, complete-image coverage checks and pack validation are
shared with Rochester. Cropped source cache keys include bounds.

Download the successful `southfield-static-trial-<run-id>` Actions artifact, then
use the existing imagery and terrain installers with `--coverage southfield`
and their corresponding `--pack-file`. Viewing and device acceptance remain
separate from build validation. This does not install building footprints.


### Michigan staged-source regional test

`build_target=michigan-staged` tests all eight existing Michigan detail regions
using the static-file approach qualified in Rochester/Southfield. The old
`michigan-all` export/sampling workflow remains available separately. This initial
regional test creates Actions artifacts, not a published Release.

- NAIP: paginated public mirror catalog, USDA licensor check, newest dated source
  per named quarter-quad (or exact footprint when no tile name is available).
  Older dates may remain in other footprints; provenance records actual dates.
- NAIP workers share a provider-issued container access token in memory only;
  tokens never enter source plans, caches or packs.
- Each source is cropped through GDAL HTTP range reads onto the final grid.
  Regional imagery is 4096×4096, with transparent source gaps/water. This is
  regional coverage, not street-level imagery. Existing local packs stay finer.
- 3DEP: paginated staged-file discovery, multiple intersecting rasters, a common
  endpoint-aligned 1025×1025 grid, split into at most 64 129×129 terrain tiles.
  Invalid/missing terrain samples cause whole affected tiles to be omitted and
  listed in `build-report.json`. No elevations are invented to hide gaps.
- Complete image coverage of Michigan land has not yet been qualified. The
  usable-image fraction includes water and neighboring envelopes and must not
  be presented as a land-completeness percentage. Missing terrain tiles remain
  visible limitations of the test, even when the pack validates.
- Two regions run concurrently, each with two source crop workers. Completed
  source crops use bounds/dimensions/source-based cache keys plus checksums.
  Failed reruns restore completed crops and the discovery snapshot; force rebuild
  starts a fresh source review. Source reads have bounded retries; failures are
  not converted into approved gaps. Neither crop sizes nor cache bytes measure
  actual network transfer. The build time and size must be observed, not assumed.
- Runtime formats, installers, layer priorities and source-rights references are
  unchanged. Vertical datum remains unresolved; viewing uses relative relief.

Start the test:

```bash
git switch navigation-cesium
gh workflow run build-metro-detroit-imagery.yml --ref navigation-cesium \
  -f build_target=michigan-staged -f force_rebuild=false
```

Each successful region uploads `michigan-staged-<coverage>-<run-id>` containing
imagery/terrain ZIPs, adjacent checksum descriptors, source plan and coverage
report, retained for 14 days. Failed regions upload whatever evidence completed;
inspect reports and job status before installation. Existing finished packs are
not deleted or overwritten by failed builds. Device installs use the existing
`--pack-file` interfaces with each region's coverage name.


### Metro Detroit building stage

The `michigan-staged` pipeline also builds an optional Metro Detroit building
archive. Run `build_target=metro-detroit-buildings` to test only this stage.
This stage uses the existing Geofabrik Michigan PBF download/cache and osmium
extraction, not Overpass. It does not rebuild navigation, search or routing.

Existing simple closed-way normalization and height classification are reused:
`osm-height` is an OSM height tag (not a verified survey); `levels-estimate` uses
3 metres per recorded floor; `placeholder` uses an explicit 9-metre fallback.
Placeholder geometry remains hidden by existing viewer policy; floor estimates
appear at close zoom. Complex polygons/courtyards and outlines crossing the
outer coverage boundary are omitted and counted. Height counts, source PBF
SHA-256, ODbL attribution, and license reference accompany the pack.

The Metro envelope matches existing imagery bounds (-83.75, 42.0, -82.55, 42.9).
A bounded 32×32 tile catalog replaces the city demo's 4×2 grid for this coverage
only. Existing per-tile limits remain 10,000 outlines / 10 MiB; the renderer still
keeps at most four nearby tiles and two loads active. Build fails rather than
silently truncating overfull tiles. Archive cap is 64 MiB; extraction cap is
512 MiB. Footprints and heights are not photorealistic building meshes.

A successful stage uploads `metro-detroit-buildings-<run-id>` with the ZIP,
adjacent checksum descriptor and `buildings-report.json`, retained for 14 days.
No Release is published automatically. The existing ZIP verification and safe
unpack routine are reused; a new validated device revision is activated with an
atomic symlink change. Old revisions are retained and invalid archives cannot
replace active data. The regional pack is selected ahead of city-sized building
packs inside Metro Detroit, allowing continuous panning between cities; local
imagery and terrain priorities remain unchanged.

After downloading a successful stage artifact, install on Termux or Linux:

```bash
git switch navigation-cesium
python -m development.maps.install_buildings \
  --pack-file build-output/metro-buildings/metro-detroit-buildings.zip
./runOrcUi
```

The phone processes finished tiles, not the source PBF. Source coverage, height
completeness, startup and pan performance still require device acceptance before
extending building extraction statewide.
