# Michigan detail and national map delivery plan

Status: Michigan building delivery is implemented on `navigation-cesium`; the
higher-resolution and national stages below are proposals, not completed builds.
The existing OSM building extractor, state catalog, staged-raster discovery,
MBTiles imagery reader, terrain mosaics, artifact checksums, and atomic installers
remain the foundation. Navigation/search/routing remain separate products.

## 1. Michigan buildings: current implementation

Use the eight existing Michigan regional definitions, extending the two southern
building envelopes from 41.7 to 41.69 to include the checked-in state boundary
near 41.696089. Existing terrain/imagery bounds remain unchanged. Each region reuses the
Michigan Geofabrik PBF and emits a checked building ZIP, descriptor, and report.
Relations, courtyards, parts and base offsets use the same schema-3 geometry as
Metro Detroit. A component belongs to the first matching region by centroid;
this assigns overlapping Upper/Lower Peninsula envelopes consistently. Complete
footprints may extend over the owning region's edge. Parts are associated before
ownership filtering so a neighboring region's part can suppress the parent roof.
The source extract is Michigan, not a strict political-boundary clip; envelopes
include neighboring areas/water and unrecorded OSM buildings cannot be invented.

Each pack retains the 1,024 tile / 10,000 outlines / 10 MiB-per-tile ceilings.
Regional delivery budgets are 256 MiB ZIP / 1 GiB extracted per region; Metro's
128 MiB / 512 MiB limits remain unchanged. These are limits, not predicted sizes.
The viewer mounts the installed regional catalogs together, namespaces tile IDs,
and keeps four active tiles, two pending loads, and at most 512 building entities
per active tile. Southeast supersedes the overlapping Metro building pack in the
viewer; Metro's installed revision is retained. Partial regional installs work.

GitHub target `michigan-buildings` builds all eight with two concurrent workers;
`michigan-staged` includes this stage. Download finished artifacts to the device;
no device PBF build or USGS export is needed. `--michigan-directory` preflights all
eight archives before installation; each region activates independently and
retains its previous revision. A later failure can leave earlier regions updated;
rerun to finish. This is not a single atomic eight-region transaction.

Acceptance: all eight reports validated; common source snapshot reviewed; cross-
region navigation and pans; Chrysler parts; residential estimates; Grand Rapids,
Lansing, Traverse City, Marquette, and a region-boundary view; VM and Termux memory,
startup, shutdown and stability. Building heights remain tagged, floor-derived,
or approximate 9 m blocks; these categories must stay visible in metadata.

## 2. Higher-resolution Michigan imagery and terrain

Do not enlarge an overview JPEG and call it detail. Keep statewide overviews and
add independently downloadable detail packs with on-demand tile rendering.

| Product | Proposed target | Existing component to extend |
| --- | --- | --- |
| State overview | Keep current small offline pack | Current regional/overview imagery and terrain |
| Regional imagery | Roughly 2 m ground pixels | Existing NAIP MBTiles builder, z16 near Detroit |
| City/corridor imagery | Roughly 0.9 m, z17 near Detroit | Existing 256 px Web Mercator imagery pyramid |
| Optional close detail | Roughly 0.44 m, z18, only when source warrants it | Same pyramid; smaller geographic packs |
| Regional terrain | 10–30 m sample spacing | Staged 3DEP rasters and existing terrain tile reader |
| Selected terrain detail | 1–3 m where available and useful | Same source discovery; additional terrain LOD/profile |

These are output sampling targets, not promises of native source resolution or
survey accuracy. Record native resolution, acquisition date, resampling method,
source gaps, and rights per source. A 60 cm source cannot become genuine 30 cm
imagery by upsampling. Satellite/aerial image pixels and terrain sample spacing
are different quantities. Buildings remain a separate geometry layer.

Source order: dated public USDA NAIP GeoTIFF/COG files for imagery; downloadable
USGS 3DEP DEMs for terrain. Reuse staged-file discovery and resumable crop caches,
avoiding custom whole-region image-export services. The existing Downtown and
Auburn Hills pilots are a delivery proof, not statewide high-resolution coverage.
The Michigan MiSAIL program lists 12-inch imagery: evaluate actual downloadable
coverage and redistribution rights before adding it as an optional source.
Public viewing access alone does not establish bulk redistribution permission.

First detail expansion: Metro Detroit at z17, then Rochester/Auburn Hills and a
hilly comparison area with 10 m terrain. Compare source imagery, tile image,
source DEM, sampled elevations, and rendered relief. Test z18 only where it
adds source-supported information. Keep current device rendering budgets and
terrain exaggeration distinct from source elevations. Resolve source vertical
datum/geoid conversion before describing globe elevations as accurate ellipsoid
heights; the current relative-relief convention remains explicit meanwhile.

Use approximately 10–20 km imagery delivery cells, subdividing to stay under the
existing 512 MiB detail ZIP / 2 GiB database ceilings. Check the existing 100,000
tile limit rather than raising it blindly. Terrain retains bounded child grids
and requires hierarchical catalog/LOD work before statewide fine grids: do not
attach every high-resolution terrain tile to the scene or preload every sample.
Select requested detail cells, installed-only cells, and coarse fallback through
one catalog. Prefer the best installed compatible resolution, with an explicit
profile/date in download UI. No automatic large network download while driving.

### Storage planning, not a download quotation

For a planning example of **150,000 km² of land** (not the full Michigan rectangle):
`pixels = area_m² / spacing_m²`. Full RGB is three bytes per pixel. With a trial
compression range of 0.15–1 byte per pixel and about 4/3 pyramid overhead:

| Imagery spacing | Approximate compressed pyramid planning range |
| --- | --- |
| 2 m | 7.5–50 GB |
| 1 m | 30–200 GB |
| 0.5 m | 120–800 GB |

Measure real representative urban, forest, farm and shoreline packs before a
statewide commitment. Compression, alpha masks, source gaps, rectangular padding,
and tiling overhead change these numbers. At 10 m, float32 elevations for this
example are about 6 GB before compression, pyramid levels and metadata; at 1 m,
about 600 GB. Current JSON height grids can cost more than float32. Whole-state
native-resolution everything is not a small phone download. Offer selected
cities/corridors and storage budgets; count old revisions and scratch space.

## 3. Extend to all 50 states

Reuse `state_map_catalog.py` and the checked-in 50-state boundaries, including
existing antimeridian handling. Extend building coverage/source selection beyond
Michigan, using Geofabrik's ISO/state metadata and the existing source catalog.
Do not create 50 hand-maintained scripts. Generate per-state/per-cell build jobs
from a versioned product plan and keep geographic ownership stable across state
and cell seams. Explicitly test border-crossing footprints and parts.

A product record should identify state/cell, layer, profile, source snapshot and
acquisition dates, source rights, bounds, valid-data mask, build revision,
checksum, compressed and installed bytes, prerequisites, superseded revision,
and coverage gaps. Unchanged input hashes/profile reuse existing output. Publish
immutable packs plus a small versioned catalog. Updates download changed cells,
retain a recoverable previous revision, and never label a failed state complete.

GitHub Actions remains the build coordinator; short-lived Actions artifacts are
for testing. Existing release tooling can publish accepted packs durably, with
reviewed release promotion instead of treating expiring artifacts or draft assets
as the production catalog. Split larger outputs into independently resumable
packs; verify current hosting asset limits and storage/egress costs before choosing
GitHub Releases versus an object store. No hosting purchase or new account is
part of this implementation. Track build minutes, transfer bytes, cache use and
artifact retention per state, with limited worker concurrency and failure retries.

Rollout gates:

1. Michigan: buildings + measured city imagery/terrain profiles and device tests.
2. Ohio and Indiana: prove neighboring-state sources, ownership seams and reuse.
3. Colorado (terrain) and California (density/size): exercise mountains, mixed
   source dates, large source files and adaptive delivery cells.
4. Hawaii and Alaska: validate imagery sources/rights separately, water/nodata,
   vertical datums, Alaska IfSAR DEMs and antimeridian cells. Do not assume the
   CONUS NAIP source path has equivalent coverage or redistribution rights there.
5. Remaining states: small queued batches with per-state acceptance reports,
   explicit missing layers, and a rollback/promotion gate. Offline navigation
   remains usable when an optional imagery/terrain/building pack is absent.

Before national detail delivery, build a paged spatial catalog for all layers so startup reads
metadata and fetches only needed geometry/height tiles and respect the current imagery stack layer limit. Profile the present full
pack checksum scan on Termux; extend verification caching/lazy verification with
integrity checks if measured startup cost warrants it. Do not silently remove
verification to make it faster. Higher resolution should increase disk/network
use, not the number of simultaneously resident GPU resources.

## Source references reviewed for this plan

- [USDA NAIP dataset](https://catalog.data.gov/dataset/national-agriculture-imagery-program-naip-imagery):
  source pixel sizes vary by acquisition; standard program coverage is CONUS.
- [USGS elevation product formats/resolutions](https://www.usgs.gov/faqs/what-types-elevation-datasets-are-available-what-formats-do-they-come-and-where-can-i-download):
  downloadable DEM products at multiple resolutions.
- [USGS 1 m DEM collection](https://data.usgs.gov/datacatalog/data/USGS%3A77ae0551-c61e-4979-aedd-d797abdcde0e):
  lidar-derived bare-earth terrain; public-domain metadata.
- [USGS Michigan lidar summary](https://www.usgs.gov/ngp-user-engagement-office/news/new-3d-elevation-program-fact-sheet-michigan):
  statewide QL2 lidar acquisition; coverage does not imply this app has built or installed it.
- [Michigan MiSAIL](https://www.michigan.gov/dtmb/services/maps/misail):
  potential higher-resolution imagery source requiring product-specific review.
- [USGS Alaska 5 m DEM collection](https://catalog.data.gov/dataset/5-meter-alaska-digital-elevation-models-dems-usgs-national-map-3dep-downloadable-data-coll):
  distinct Alaska terrain product.
