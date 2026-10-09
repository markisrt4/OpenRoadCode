# Standalone Cesium map experiment

Branch: `navigation-cesium`. Tracking: [MAR-22](https://linear.app/mark-russell/issue/MAR-22).

Stage one checks the renderer without changing ORC navigation. It renders a local
ellipsoid globe, procedural geographic grid, and a static Detroit marker. Around
the marker, a synthetic 250-metre checkerboard grid, 250/500/1,000-metre distance
rings, and labelled compass directions make camera movement visible. A yellow
ground arrow points north; the footer reports camera height, tilt, and heading.
These reference graphics are not real streets or buildings. Without an installed imagery pack it has no aerial imagery. An optional coarse terrain pack adds relative relief. Building datasets, routing,
and GPS follow are not implemented yet. Zoom, rotation/pan gestures, north-up, tilt, and reset are available. The
viewer is an owned, isolated Chromium app window; Return to ORC, window close, or
Ctrl+C stops only this experiment and its local server.

## Architecture

- `ui/navigation/cesium_viewer_state.py`: immutable destination and initial camera
  state in SI units. Independent of Cesium, Chromium, HTTP, and controllers.
- `frontends/web/cesium/`: presentation. Maps the snapshot into Cesium camera and
  entity calls; emits an explicit close request. No dataset downloads or vehicle
  subscriptions. No runtime CDN, ion token, geocoder, or default hosted basemap.
- `apps/launchers/cesium_viewer_server.py`: loopback HTTP adapter with separate web
  and SDK mounts. Owns serving and the close-request event, not browser lifetime.
- `apps/launchers/component_test/cesium_viewer_cli.py`: composition and lifetime.
  Binds state, local server, native browser, unique temporary profile, and cleanup.
  Reuses ORC's existing GPU environment selection without forcing ANGLE flags.
- `apps/launchers/cesium_sdk.py`: pinned SDK identity and local installation path.
  The optional SDK is installed explicitly outside the repository, not during
  ORC startup. Installer verifies npm archive SHA-512 and retains license files.

The prototype uses CesiumJS 1.124.0's prebuilt distribution (Apache-2.0). This is
an explicit compatibility pin, not a claim to the latest release. Node/npm and a
new Python dependency are not required on the phone. Upgrades require changing
both the version and integrity pin, followed by device validation. Cesium data
rights remain separate from its engine license.

## Install and run on Termux/X11

From the repository root, with Termux/X11 and native Chromium available:

```bash
git fetch origin
git switch navigation-cesium
git pull --ff-only
python -m development.maps.install_cesium
python -m apps.launchers.component_test.cesium_viewer_cli --display :1
```

Installation requires internet once and stores the SDK under
`$XDG_DATA_HOME/openroadcode/cesium/1.124.0` (default `~/.local/share`). It downloads
roughly a few tens of MB; the SDK takes additional space unpacked. The base
viewer then runs without internet. No Detroit data has been installed or
claimed as available offline. `--sdk` selects another preinstalled SDK location.

Optional destination:

```bash
python -m apps.launchers.component_test.cesium_viewer_cli \
  --latitude 42.3314 --longitude -83.0458 --label Detroit --distance-m 2500
```

The launcher prints its log path (`cesium-viewer.log`) and temporary local URL.
It requests a maximized app window with a title-bar close button. Return to ORC
closes the experiment; it does not start ORC if ORC was not running. If rendering
fails, the return button remains available once configuration has loaded.

## Device acceptance and next stages

Verify the globe renders, the Detroit marker is visible, gestures/buttons work,
reset restores the initial view (Detroit centred, north facing, tilted), and closing/relaunching leaves no orphan browser
or server. Try a second run without internet. Inspect smoothness while rotating
and zooming; a blank local globe is only the rendering baseline, not a benchmark
for an imagery/terrain/building scene.

The user runs the full quality gate: `python scripts/quality_gate.py`. Focused
state/HTTP/lifecycle tests cover invalid destinations, asset isolation, authorized
close requests, and cleanup on browser startup failure. A cloud Chromium software-rendering probe initialized Cesium and its controls,
exercised reset, and confirmed the Return to ORC request reached the launcher.
The user has confirmed the baseline quality gate passes and scrolling is smooth
on Termux/X11. Reference-grid rendering and control behavior still need device
verification. Use zoom to change ring size and camera height, tilt to switch
between overhead and angled squares, and reset after panning to restore Detroit.

Next, qualify and prepare a bounded Detroit imagery layer, then terrain and
buildings independently using [the dataset review](detroit_map_data_review.md).
Keep data providers and coverage/license metadata outside the viewer's camera
controls. Compare the same datasets in MapLibre before adding a permanent ORC
launch control or replacing its navigation map.

## First real imagery pack (bounded downtown Detroit)

The viewer can now load a separately installed local imagery pack. The pack's
storage/checksum adapter is independent of the immutable SI layer snapshot and
Cesium presentation. It serves only the selected image through the local origin;
the browser never contacts the source service. Attribution stays in Cesium's
credit display. Missing imagery leaves the reference globe usable.

From the repository root, download explicitly while online:

```bash
python -m development.maps.download_detroit_imagery
python -m apps.launchers.component_test.cesium_viewer_cli --display :1
```

The downloader queries the USGS NAIP Plus catalog for primary Michigan records,
selects the newest identifiable NAIP/USDA acquisition year, locks the export to
those raster IDs, and saves a natural-colour WGS84 JPEG plus provenance. It does
not substitute commercial imagery if no qualifying record is found. Source
metadata is retained and the service must still describe public-domain imagery.
USGS reference: https://imagery.nationalmap.gov/arcgis/rest/services/USGSNAIPPlus/ImageServer

Coverage is west/south/east/north `-83.065, 42.315, -83.025, 42.345`, approximately
3.3 km across around downtown Detroit. The export is 2,048 × 1,536 pixels; these
are resampled output pixels, not a native acquisition-resolution claim. The
actual year, records, downloaded byte count, and SHA-256 are recorded in
`manifest.json`. The JPEG is capped at 20 MB; exact size and completeness need a
successful device download. Inspect for no-data gaps near coverage edges/river.
A bounded image is a first data-quality test, not a citywide tiled map.

Default installation:
`$XDG_DATA_HOME/openroadcode/map-packs/detroit-imagery-v1` (or `~/.local/share`).
The viewer automatically uses this pack if installed. Use `--no-imagery` to
return to the reference globe, or `--imagery /path/to/pack` for an explicit pack.
After installation the image works offline. Outside its rectangle the reference
globe remains visible; the image is not stretched to cover the world. Terrain
and buildings are still absent, so tilting the photo will not create 3D buildings.

The cloud network policy blocked the catalog and image-download endpoints. This
change therefore does not claim a downloaded/visually verified Detroit image,
confirmed acquisition year, exact file size, or measured device performance.
Device download and visual inspection remain pending. Run the full quality gate
locally after updating: `python scripts/quality_gate.py`.

## Coarse Detroit terrain / relative relief

```bash
python -m development.maps.download_detroit_terrain
python -m apps.launchers.component_test.cesium_viewer_cli --display :1
```

The explicit downloader requests a 33 × 33 regular ground grid from USGS 3DEP's
raw elevation service, with bilinear sampling and no hillshade rendering. Samples
are roughly 100 metres apart over the same bounded Detroit rectangle. All 1,089
samples must be finite and present before the pack is installed. Raw responses,
source metadata, source datum labels when returned, checksum, and coverage are
retained outside the repository. No GDAL, raster-codec dependency, terrain service
subscription, or runtime network request is introduced. Source:
https://elevation.nationalmap.gov/arcgis/rest/services/3DEPElevation/ImageServer
3DEP data is public domain; rights reference is recorded in the manifest.

The viewer automatically loads an installed pack. `--no-terrain` compares with
the flat ellipsoid; `--terrain /path/to/pack` selects explicit local data. Terrain
and imagery remain independently installed layers. A Cesium adapter interpolates
the local grid into bounded-detail heightmap tiles and stops refining at level 13.
Reference graphics follow the sampled ground. Outside the pack it remains flat;
the outer one-sample band fades to flat to avoid a hard vertical seam.

This is **relative relief**, not precise globe elevation. USGS ground elevation
is not automatically Cesium ellipsoid height. Original source heights are retained,
but the scene subtracts the central sample as its baseline; no silent NAVD88-to-
ellipsoid conversion or arbitrary geoid offset is applied. Camera readout says
"Scene height". Do not use these displayed values as navigation/altimetry readings.
Datum conversion and production terrain tiling remain future work. The coarse
sampling cannot reproduce buildings or fine roadside features, and Detroit's
relief may look subtle. No exaggerated vertical scaling is applied.

After updating, download while online, inspect the printed source elevation range,
then compare a tilted view with and without terrain. Check reset, zoom, reference
graphics, imagery draping, and Return to ORC. Run the full gate locally:
`python scripts/quality_gate.py`. Live USGS sampling and Termux rendering remain
pending device validation; mocked tests do not verify real service coverage. A
cloud software-rendering probe loaded synthetic terrain and imagery together,
exercised zoom/tilt/reset, and confirmed close-request delivery. The optional
Node test verifies north-to-south interpolation, coverage edges, and the detail
limit; it skips in the quality gate when Node is not installed.
