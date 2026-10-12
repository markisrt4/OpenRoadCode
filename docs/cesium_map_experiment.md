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

### Offline Detroit buildings

On `navigation-cesium`, download once, then launch as usual:

```sh
python -m development.maps.download_detroit_buildings
python -m apps.launchers.component_test.cesium_viewer_cli --display :1
```

The installed pack is auto-detected. `--no-buildings` hides it;
`--buildings PATH` selects another pack with the same validated format.
No network requests are made by the building renderer. The source download uses
four smaller Overpass queries, with up to three attempts per tile for transient
errors. Completed tiles are cached beside the pack in a `.download` directory, so
rerunning resumes after a timeout. No partial pack is installed. The public
service can still be unavailable; retry later if all attempts fail.
The downloader never silently installs an incomplete server response.

Coverage matches the Detroit imagery and terrain rectangle. This prototype uses
simple closed OSM building ways wholly inside that rectangle. Multipolygon
relations, courtyards, building parts, and boundary-crossing outlines are omitted;
this is not a complete city model. Flat roofs and bases are a visual approximation.
Bases use the coarse terrain's relative relief at each outline's centroid.

Blue buildings use OSM `height` tags (unverified), gold uses `building:levels × 3 m`
(an estimate), and brown uses a **9 m placeholder**, not a measured height. Unsupported
height units fall back to floor estimates or placeholders. The status line reports
counts for each category. No facade textures or photogrammetry are included.

OSM data is licensed under ODbL 1.0, independently of CesiumJS. Visible contributor
attribution links to https://www.openstreetmap.org/copyright. The external pack
retains the source response and a manifest containing the download time, bounds,
checksum, source, and license link. Keep those records with the data. Redistributing
this derived database requires an ODbL review and compliance; it is not covered by
the imagery's public-domain rights. Packs remain outside the code repository.

### Layer comparison controls

The viewer now opens 1,500 m from the destination, with buildings visible and the
synthetic reference grid hidden. Buildings and Grid buttons independently toggle
their layers without rebuilding geometry or downloading anything. Highlighted
buttons indicate visible layers. Buildings is disabled when no building pack is
installed. The attribution remains visible when buildings are hidden. Reset view
restores the camera, preserving layer choices; `--distance-m` overrides the initial
viewing distance. The control rail scrolls on short screens.

### Launch from an ORC POI

The selected-place popup now includes a separate **3D Map** icon beside Navigate
and Earth. It centers the local viewer on that POI, labeled with its name. The
cyan destination point and its white-on-dark label bypass depth testing so
buildings cannot hide them in a tilted view. Their position remains anchored to
the selected POI at local ground height; this is a destination overlay, not a
claim that the POI sits on a rooftop. The
Google Earth button retains its ordinary online browser behavior. 3D Map works
in offline mode, uses only installed SDK/data, and never downloads new coverage.
If the selected place is outside installed imagery coverage, the viewer footer
says so; missing data leaves the reference globe usable. Detailed coverage depends on the installed packs: the original downtown
rectangle or the optional Downtown–Midtown tile pack. An absent SDK or invalid pack reports
a launch failure in ORC; run the documented installers before using this action.

**Return to ORC** or the viewer window's close button closes the local viewer. ORC
owns the isolated profile, browser and loopback server and cleans them up when the
application exits. Only one local 3D viewer may run at a time. Close it before
selecting another place. This stage is destination exploration, without live
vehicle following, route overlays, or replacement of the normal MapLibre map.

Device validation: open a downtown Detroit POI in NAV, choose 3D Map, toggle
Buildings/Grid and return. Repeat in offline mode, then select a POI outside the
Detroit pack to confirm the coverage warning. Close ORC while a viewer is open
and confirm its window also closes.

### Downtown–Midtown tiled pack

Review the download plan first, then explicitly install:

```sh
git switch navigation-cesium
python -m development.maps.download_detroit_map_tiles
python -m development.maps.download_detroit_map_tiles --download
python -m apps.launchers.component_test.cesium_viewer_cli --display :1
```

The new pack covers approximately 5 × 6.7 km, from downtown north through Midtown
(bounds: −83.085, 42.315, −83.025, 42.375). Eight geographic tiles each contain a
2048 × 1536 NAIP export and OSM building geometry. Export pixel count does not
prove native source resolution, and the newest identifiable NAIP year can differ
between tiles. NAIP remains public domain; OSM retains its separate ODbL license.
Source responses and license references remain in the external pack.

Actual size is unknown before export. Hard payload caps are 160 MiB imagery,
160 MiB OSM source records, and 80 MiB prepared buildings, plus metadata. Most
responses should be smaller; the installer prints the final size. Installation
copies the completed download cache into the final pack, temporarily requiring
roughly twice its storage. The `.download` directory remains for resume and can
be removed manually after successful validation to reclaim duplicate storage.
An incomplete download never replaces the original downtown packs or becomes an
installed tile pack. Run the same command again to resume completed imagery and
OSM requests. Transient OSM failures retry; imagery failures resume on rerun.

The viewer and POI action automatically prefer a validated installed tiled pack.
The original packs remain usable with `--no-tiles`; explicitly choosing the old
imagery/building options also bypasses automatic tiled-pack selection. No tile
requests go to the internet during viewing: the loopback server serves only
manifested image/geometry files. Source records are not exposed to the browser.

At most four nearby tiles are attached, with at most two tile loads in flight.
The camera's visible rectangle selects intersecting tiles, prioritized by distance
to its center. Camera movement unloads unwanted imagery and building entities.
Late requests cannot attach to a closed viewer or an abandoned tile. At wide zoom
levels this prototype deliberately limits detail to four nearby tiles; zoom in
for full local detail. The footer reports active/installed tile counts and cyan
outlines mark installed coverage. Buildings toggle independently; estimates and
placeholders retain their colors. Boundary-crossing simple outlines belong to
one tile by their mean vertex location; complex OSM relations remain omitted.

The shared builder now offers a separate Downtown–Midtown terrain pack, described
below. Without it, the earlier downtown terrain prototype still fades to flat
ground outside its rectangle. Embedding, live tracking, and routing overlays
remain later stages.

Phone acceptance: pan from downtown north toward Midtown, watch active tile counts
stay at four or fewer, and inspect newly loaded buildings/imagery. Toggle Buildings,
zoom out, return to ORC, and repeat offline. Verify smoothness and memory use on the
phone before considering broader coverage or embedding.

### Shared builder and terminal install menu

Terrain can also be installed **directly on Termux**, without Docker or a map
build host. It uses the same USGS downloader and stores device-owned data outside
the certified navigation dataset:

```bash
git switch navigation-cesium
git pull --ff-only
bash development/termux/install_terrain.sh
```

Choose **2 — Downtown–Midtown** and confirm. A complete pack is installed
atomically; an existing validated pack is reused. Close and reopen the 3D viewer.
Its footer reports the installed sample grid. If the image service returns a
token-required error, the installer uses public USGS EPQS with a coarser 33×33
grid (about 200-metre spacing across Midtown). Two point queries run at a time;
1,089 queries can take several minutes. EPQS source responses are preserved,
and an unspecified source datum is explicitly marked rather than assumed.
No account/token is added or obtained. Device-installed Midtown terrain is
preferred over the old downtown prototype; a deployed Midtown terrain pack
takes precedence when both exist. This command downloads terrain only, reusing
installed imagery/buildings. No navigation dataset publication or pull is needed.

The optional building stage now belongs to the existing map builder. It reuses
navigation source PBFs rather than querying Overpass. See
[the map-builder workflow](../tools/map_builder/README.md#optional-3d-buildings-and-interactive-installation)
for coverage selection, publication, and `--interactive` vehicle installation.
The `3d --layer terrain` stage downloads a 65×65 USGS 3DEP elevation grid through
the same validated publish/install workflow. Terrain installs independently of
buildings, preserving sample responses and source datum metadata. It supplies
relative relief, with roughly 100-metre sampling across Downtown–Midtown, not
converted absolute ellipsoid elevations. Its payload is capped at 2 MiB; source
provenance adds installation bytes shown in the pull menu. Empty/missing samples
and mixed datums fail before installation; transient HTTP errors get bounded
retries. Installed prototype aerial tiles with matching coverage are reused;
the shared imagery build stage remains pending.

Acceptance: install the terrain pack using the map-builder instructions, reopen
the 3D viewer, and check that its footer says relative relief. Inspect sloping
ground with buildings on, toggle 2D/3D, and confirm the destination remains
visible. Repeat offline. Detroit is fairly flat, so large mountains would
indicate bad samples rather than successful terrain rendering.

### Pine Knob relief comparison (Termux)

Pine Knob in Clarkston is coverage 3 in the optional terrain menu. Its separate
pack preserves installed Detroit terrain. The viewer chooses a terrain pack
containing the selected destination, preferring shared Midtown coverage where it
matches. This experiment displays source elevations relative to the pack centre;
it does not exaggerate heights or convert the source datum to ellipsoid heights.

```bash
git switch navigation-cesium
git pull --ff-only
bash development/termux/install_terrain.sh --coverage pine-knob
bash development/termux/test_pine_knob.sh
```

The test opens near the ski hill without Detroit imagery or buildings. Terrain
ON/OFF switches between sampled ground and a flat ellipsoid without resetting the
camera. With no imagery, 10 m contour lines help show the relief. The footer shows
the sampled elevation range. Source sampling is coarse, so this is a terrain
comparison rather than a detailed ski-trail map. Grid graphics, the destination marker and building bases follow the selected
relief scale and flatten with terrain disabled; building heights remain unchanged. Rendering and live USGS downloads require device
validation. After downloading, this view works offline.

USGS HTTP 500, 502, 503, 504 and rate-limit failures receive up to three
attempts per request. If the image service remains unavailable, the terrain
installer switches to public EPQS; EPQS requests use the same bounded retries.
A failure of both services leaves no incomplete pack installed. Rerun the terrain
installer before opening the hill comparison; the local viewer URL alone does
not indicate a successful terrain installation.

### Pine Knob aerial imagery

Install the optional NAIP image directly on Termux, without Docker. This uses the
same bounds as Pine Knob terrain and a separate device-owned pack. The downloader
locks the newest identifiable NAIP acquisition returned for that coverage and
retains source records, public-domain evidence, attribution and a checksum.
The image is capped at 20 MiB; the exported 2048×1536 pixels do not imply native
source resolution. Temporary HTTP failures get three attempts, with no partial
pack installed on failure.

```bash
git switch navigation-cesium
git pull --ff-only
bash development/termux/install_pine_knob_imagery.sh
bash development/termux/test_pine_knob.sh
```

Close an existing viewer first. The Pine Knob launcher now loads its installed
imagery over local terrain; imagery remains visible when Terrain is switched OFF.
Contour lines are shown only when no imagery is loaded. Compare ON/OFF from the
same camera angle, inspect coverage for no-data gaps, and reopen without internet
to verify offline viewing. ORC's selected-POI adapter also selects this local image
for destinations inside its bounds. No Pine Knob building pack is included.

Focused checks use mocked provider replies. Actual USGS download availability,
Termux rendering and the full quality gate require user validation.

Imagery progress reports separate service metadata, source catalog, bounded
export and JPEG download stages. On a network failure, the error identifies the
stage and endpoint after bounded retries. This helps distinguish a service outage
from an export request failure; retries cannot guarantee provider availability.

### Touch-friendly camera pitch

More tilt and Less tilt orbit the ground at the current screen centre in 10-degree steps,
preserving camera heading and distance. Tilt is limited to 0–80 degrees from
top-down to keep the camera above ground. The footer reports the current tilt;
Reset view restores the initial 45-degree view. These controls also work with
terrain switched off, allowing a comparison from the same viewing angle.

Mouse panning changes the tilt anchor: tilt controls pick the visible terrain at
the screen centre, falling back to the ellipsoid. If the centre points at sky,
tilt changes orientation in place. Only Reset view returns to the selected POI.
Pine Knob's test intentionally disables building layers; “buildings not installed”
does not indicate a terrain failure. Ground relief is not vertically exaggerated.

### Relief scale and pan arrows

The arrow pad pans across ground relative to the camera heading, retaining tilt
and viewing distance. Each step is 15% of the current distance to the visible
centre, bounded to 25 m–100 km. If the centre points at sky and no ground can be
picked, pan waits until ground is visible. Mouse pan and touch tilt still work.

Relief cycles 1× / 2× / 3×; the default 1× uses actual relative elevations. The
footer explicitly labels 2× and 3× as exaggerated. Source samples and the displayed
sampled elevation range remain unchanged. Imagery drapes over the new terrain;
markers, local grid graphics and loaded building bases are refreshed, while
building heights stay real. Terrain OFF disables the relief control and returns
these overlays to flat ground. Reset view restores destination, initial tilt,
and 1× relief. Contour spacing refers to displayed height, so exaggeration makes
additional contour lines visible.

```bash
git switch navigation-cesium
git pull --ff-only
bash development/termux/test_pine_knob.sh
```

Pan away from the destination with the arrows, change tilt, then cycle relief.
Check that panning and scaling retain the viewed area, imagery remains aligned,
and the marker follows the ground. Reset should restore the destination and 1×.
No pack downloads are required. Device rendering and the user-run quality gate
remain pending.

### Embedded ORC prototype (X11)

Navigation offers a Map / Terrain toggle on its existing toolbar. MapLibre remains the default;
Google Earth is not an embedded platform in this selector. Selecting Terrain opens
static exploration at the last selected POI, or the current known host/bridge
position on first use (Detroit if unknown). Selecting a POI's existing local 3D
action opens that place inside the map area rather than a separate browser window.
Local packs and the installed Cesium SDK are reused; no map downloads are required.

The browser is still Chromium: this is an X11 surface-hosting experiment rather
than a new embedded browser engine or dependency. Its blank app window is attached
before navigating to the local Cesium page, avoiding reparenting a live WebGL
canvas. Each session owns an isolated temporary profile, loopback origin and
random loopback DevTools port. Startup and geometry updates run on a serialized
worker. Generation checks cancel obsolete startup, and owned resources close
before the transient map host is destroyed. Viewer failure restores MapLibre and
shows a status. The browser and profile are recreated each time.

ORC's header and navigation sidebar remain visible. While Cesium is active, the
native camera rail hides and Cesium's pan, pitch, zoom and relief controls are
shown in the map area. The Map / Terrain toggle closes the browser and restores the native map. Leaving Navigation closes the session;
re-entering Navigation starts on MapLibre. Route, radar and live vehicle-follow
overlays still belong to MapLibre; the prototype is destination exploration.

```bash
git switch navigation-cesium
git pull --ff-only
python -m apps.orcUi
```

On Termux/X11, open Navigation and toggle Map to Terrain, or search for Pine Knob and use
its 3D action. Verify it stays inside the map area; pan, pitch and relief controls
should respond while ORC sidebar navigation remains usable. Resize ORC, switch
back using both return controls, then leave Navigation for Home and reopen it.
Repeat a few times to check cleanup and resize behavior. Verify offline use after
pack installation. If startup fails, copy the selector status and
`${LOGGING_TMP_DIR:-${TMPDIR:-${XDG_CACHE_HOME:-$HOME/.cache}/openroadcode/tmp}}/cesium-embedded.log`.

This uses existing Chromium, xdotool and xprop support. If the selector reports
missing xdotool on Termux, install only these X11 tools:

```bash
git switch navigation-cesium
pkg install xdotool xorg-xprop
```

Focused mocked lifecycle, stale completion, return-to-native, cleanup and contract
checks pass. Native X11 focus/touch, Termux GPU stability and device resizing are
pending validation; this environment has no X11 test display. The full quality
gate remains user-run:

```bash
git switch navigation-cesium
python scripts/quality_gate.py
```

Embedded Chromium launches with `--no-first-run` and `--no-default-browser-check`
to avoid first-use dialogs for its temporary profile. Blank-window attachment
and local-page loading have separate bounded startup deadlines; a page-load
timeout reports the last DevTools startup stage or error. Actual Termux startup
still requires device validation.

Embedded startup uses a script-free local HTTP loading page, not `--app=about:blank`.
Some Chromium builds open a regular New Tab window for the latter. The local page
creates a real app window without loading Cesium or creating a WebGL canvas;
DevTools locates that exact page and navigates to Cesium only after attachment.

### Compact embedded presentation

The Map / Terrain control shares the Home / Work / Places toolbar; there is no
separate renderer-selection row or user-facing MapLibre label. It shows the
current view and disables clicks while opening. Normal loading and failure
messages use ORC's existing status area.

The embedded browser hides its duplicate header and starts with camera controls
collapsed. Controls opens a compact four-column overlay for pan, zoom, pitch and
relief; press Controls again to clear the map. A short relief/tilt readout replaces
the multi-line data diagnostics. Renderer errors remain visible, and source
attribution stays available in Cesium's credit area. Standalone viewing retains
the fuller controls and diagnostics. Validate this layout on Termux by switching
Map / Terrain and opening/closing Controls at the usual ORC window size.

### Regional imagery installer

The device-side menu now starts with **Metro Detroit overview** and optional
**Detroit Downtown–Midtown detail**, rather than the Pine Knob demo. Existing
Pine Knob packs remain usable. This first regional step installs imagery only;
base navigation/search/routing and OSM buildings still use the existing builder.

```bash
git switch navigation-cesium
python -m development.maps.install_region
```

The overview envelope is longitude −83.75 to −82.55, latitude 42.0 to 42.9:
a rectangular planning area around Wayne, Oakland and Macomb, not certified
county boundaries. A 2048×1536 image provides coarse context, not detailed imagery
throughout the region. USGS catalog/export failures or source gaps remain possible.
The menu prints the 20 MiB image cap before confirming; metadata adds disk usage.
Viewing requires no network. The viewer chooses the smallest installed imagery
coverage containing the selected destination. Reopen Terrain after installing.

```bash
git switch navigation-cesium
python -m development.maps.install_region --coverage metro-detroit --update
```

Updates fetch and validate a fresh revision before atomically switching a managed
active link. Earlier revisions remain on disk for recovery. A failed update keeps
the previous active pack. Metro Detroit overview downloads resume completed, checksum-checked pieces after
interruption. Detail downloads remain available through `download_detroit_map_tiles`.
This is an initial regional imagery workflow, not yet a regional terrain/building
installer or an automatic imagery freshness check.

Large imagery catalog responses are fetched using the complete ArcGIS object-ID
index, then checked batches of at most 20 records (subdivided if the service
still truncates them or times out). Missing records stop installation before image export;
source IDs and the assembled catalog remain in pack provenance.

During imagery transfer, the terminal displays downloaded MiB, total MiB and
percentage when USGS provides a Content-Length header. Without that header it
shows downloaded MiB and “total size unknown”; it does not guess a percentage.
Catalog batches show records fetched and percentage separately. These indicators
measure download progress, not final validation or installation completion.

Catalog record batches use a 30-second network timeout and two complete-response
attempts before splitting into smaller requests. Retries include reading the
response body, not only opening the connection. Single-record requests keep retrying temporary failures until successful or
cancelled. Installed imagery stays active throughout.

The Metro Detroit overview uses 16 smaller 512×384 exports, combined locally
into one north-first 2048×1536 JPEG using the already installed Pillow library.
Each export queries only its own geographic footprint. Transfer is capped at
1.25 MiB per piece (20 MiB total), with up to another 20 MiB for the final image
during assembly, plus source metadata. Individual pieces may use different NAIP
acquisition years; per-piece catalog/export evidence is retained. Completed
pieces remain in the `.download` cache if another export fails. A successful
assembly removes that cache so later updates fetch fresh acquisitions.

### Build once, distribute a checked imagery artifact

For regular device installation, prefer a prebuilt archive over on-demand USGS
exports. This path exists now, but **no Metro Detroit artifact or public hosting
URL is bundled**. A build machine must first finish and inspect the imagery;
packaging does not repair USGS outages or certify that exported imagery has no
gaps. The existing navigation dataset still uses its SSH/rsync deployment.

On the build machine (repository environment with Pillow, already supplied by
ORC installers), build without activating the result on that machine:

```bash
git switch navigation-cesium
python -m development.maps.install_region --coverage metro-detroit --build-only build-output/metro-detroit-imagery
python -m tools.map_builder.builder.imagery_artifact --coverage metro-detroit --pack build-output/metro-detroit-imagery --output build-output/artifacts/metro-detroit-imagery.zip
```

Inspect the imagery before distributing it. Upload both
`metro-detroit-imagery.zip` and `metro-detroit-imagery.zip.json` beside each other
on an HTTPS server or as release assets. Packaging preserves the source records
and evidence files. The descriptor includes the exact archive size and SHA256.
These commands do not upload or publish anything automatically.

On Termux, substitute the actual published descriptor URL below:

```bash
git switch navigation-cesium
python -m development.maps.install_region --coverage metro-detroit --pack-manifest https://YOUR-HOST/metro-detroit-imagery.zip.json
./runOrcUi
```

The installer shows size before confirmation, saves partial transfers for HTTP
Range resume, and restarts safely if the server ignores Range. It caps archives
and extraction at 64 MiB, checks SHA256, rejects unsafe archive entries, validates
imagery checksum and regional bounds, then switches the active revision. Existing
imagery stays usable if transfer or validation fails. Add `--update` to replace
an existing installation with a newly published artifact. Completed archives are
retained in the device's `.artifacts` cache for reuse; this consumes extra space.
The pack descriptor and archive must come from a trusted publisher: checksums
verify transfer consistency, not publisher authenticity.

USGS source downloads now retry temporary network failures, timeouts, incomplete
response reads, HTTP 429 and HTTP 500/502/503/504 until success or Ctrl+C. Backoff
is 10, 20, 40, 80, then 120 seconds; a longer server Retry-After takes precedence.
A visible one-second countdown remains interruptible. Catalog batches still split
after two failed attempts; the smallest requests keep retrying. Fatal HTTP errors,
invalid source rights and failed data validation still stop. Completed overview
tiles remain cached on cancellation; the current unfinished JPEG restarts.

Regional envelopes can include areas with no approved US NAIP sources (for
example, across the border or over water). If a complete catalog contains no
NAIP/USDA source for an overview piece, the builder leaves that piece transparent
and records its bounds and source evidence in `missing_coverage`. Such overviews
use PNG, with a coverage-gap count in the title. It does not substitute partner
imagery or invent ground detail. Undated identifiable NAIP, invalid rights,
incomplete catalogs and network failures are not treated as coverage gaps. A
region with no supported imagery at all still fails. Re-running reuses completed
pieces, including checked gap records, until the pack is successfully assembled.

### Inspect a locally built archive without hosting

Keep the archive and its adjacent `.zip.json` descriptor together. Install it
without contacting USGS or any other network service:

```bash
git switch navigation-cesium
python -m development.maps.install_region --coverage metro-detroit --pack-file build-output/artifacts/metro-detroit-imagery.zip --update
./runOrcUi
```

The installer shows size and asks for confirmation, checks the descriptor's
region, filename, size and SHA256, then extracts and validates the imagery before
activation. `--update` allows replacing an existing managed imagery revision;
the previous revision remains available. Reopen Terrain if ORC is already running.
`--pack-file`, `--pack-manifest` and `--build-only` are mutually exclusive.

### Shared ORC camera rail and detail imagery

The existing ORC camera rail now operates Terrain through semantic exploration
camera actions: pan, relative zoom, north, recenter and tilt/2D–3D. Recenter goes
to the selected exploration place. The vehicle-follow button is disabled in
Terrain; live following and route guidance remain a later integration step.
Changing tilt/2D–3D keeps the current panned ground centre. The native zoom number
is replaced by a dash in Terrain, since its camera uses viewing distance instead.
Standalone browser exploration retains its own camera buttons; the embedded
Controls menu keeps dataset/layer controls rather than duplicating the ORC rail.

The rail stays in place across map switching, preserving embedded surface size.
Startup waits for the initialized viewer's first rendered frame (up to 45 seconds)
before reporting ready. This targets startup/layout flashing; it does not prove
that every Termux/X11 GPU issue is fixed. Camera work runs on the existing runtime
worker, ignores stale generations, and owns no browser transport in widgets.

Downtown–Midtown detail imagery is now a **4096×4096** composite built from 16
1024×1024 exports. It uses the same image payload cap and resumable tiles, with
more decoding/GPU memory than the coarse Metro Detroit overview. Build into a
new directory so older lower-resolution data is not mistaken for this revision:

```bash
git switch navigation-cesium
python -m development.maps.install_region --coverage detroit-midtown --build-only build-output/detroit-midtown-detail-v2
python -m tools.map_builder.builder.imagery_artifact --coverage detroit-midtown --pack build-output/detroit-midtown-detail-v2 --output build-output/artifacts/detroit-midtown-detail-v2.zip
python -m development.maps.install_region --coverage detroit-midtown --pack-file build-output/artifacts/detroit-midtown-detail-v2.zip --update
./runOrcUi
```

Open a place within Downtown–Midtown to inspect detail. The smallest installed
imagery coverage containing that place is selected; outside it the metro overview
remains available. Existing still-smaller legacy downtown coverage takes priority
if installed. Source acquisitions and gaps determine actual visual quality; more
output pixels do not create detail absent from NAIP itself.
