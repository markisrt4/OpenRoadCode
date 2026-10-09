# Standalone Cesium map experiment

Branch: `navigation-cesium`. Tracking: [MAR-22](https://linear.app/mark-russell/issue/MAR-22).

Stage one checks the renderer without changing ORC navigation. It renders a local
ellipsoid globe, procedural geographic grid, and a static Detroit marker. There
is no aerial imagery, elevation terrain, building dataset, routing, or GPS follow
yet. Zoom, rotation/pan gestures, north-up, tilt, and reset are available. The
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
reset restores the initial view, and closing/relaunching leaves no orphan browser
or server. Try a second run without internet. Inspect smoothness while rotating
and zooming; a blank local globe is only the rendering baseline, not a benchmark
for an imagery/terrain/building scene.

The user runs the full quality gate: `python scripts/quality_gate.py`. Focused
state/HTTP/lifecycle tests cover invalid destinations, asset isolation, authorized
close requests, and cleanup on browser startup failure. A cloud Chromium software-rendering probe initialized Cesium and its controls,
exercised reset, and confirmed the Return to ORC request reached the launcher.
Termux hardware rendering and responsiveness remain unverified until reported by
the user.

Next, qualify and prepare a bounded Detroit imagery layer, then terrain and
buildings independently using [the dataset review](detroit_map_data_review.md).
Keep data providers and coverage/license metadata outside the viewer's camera
controls. Compare the same datasets in MapLibre before adding a permanent ORC
launch control or replacing its navigation map.
