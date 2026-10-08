# Google Earth navigation experiment

The `navigation-google-earth` branch offers Google Earth Web as an alternative
navigation map. It runs in native Chromium on Termux/X11 and uses WebGL. It does
not use the Debian/proot VirGL bridge used by games. Successful page loading does
not establish that Chromium uses hardware acceleration: verify on the device.

## Updating and trying the branch

Close ORC and update the device checkout:

```bash
git fetch origin
git switch navigation-google-earth
git pull --ff-only origin navigation-google-earth
```

Start Termux/X11 and ORC using the usual launcher. No map-renderer rebuild or new
Python dependency is required. Native Chromium and the existing X11 embedding
tools must be installed. Keep `[apps.google_earth] enabled = true` in the selected
applications configuration. Earth requires internet access; MapLibre remains the
offline map.

In **NAVIGATION**, select **Google Earth**. Wait for the page to load and for ORC
position telemetry to arrive. ORC injects its position into the browser rather
than using Chromium's independent location provider. Cached receiver fixes are
accepted; missing coordinates stop position delivery.

The existing camera rail routes pan, zoom, tilt, north-up, follow, and recenter
requests to the selected platform. **Chase view** selects the branch's close
oblique Earth follow perspective. Earth input controls are relative gestures;
MapLibre zoom values are not exact Google Earth camera coordinates. Google can
change its location-control UI, so tracking activation needs device verification.

Route geometry, radar, and ORC POI markers remain on MapLibre. Earth provides the
alternate visual map and GPS/camera experiment. Navigation and routing services
continue running when Earth is selected.

## Device checks

1. Select Earth, verify tiles render, then try pan, zoom, tilt, north-up, and
   recenter. Test **Chase view** with a valid position.
2. Compare a stationary fix and changing ORC positions. Pan manually and verify
   following pauses; recenter should resume it.
3. Switch to MapLibre and back. Earth should reuse its browser rather than launch
   a second process. Resize the ORC window and verify the embedded viewport fits.
4. Navigate Home, return to Navigation, change theme, and close ORC. Verify that
   Earth never remains attached to a destroyed map host or appears as an orphan
   window. The application runtime owns the browser; leaving Navigation hides
   and detaches it, while application shutdown stops it.
5. Close the Earth browser externally and check that Navigation returns to
   MapLibre. With ORC offline, selecting Earth should leave MapLibre active.

For a synthetic route on an existing broker, stop live navigation position
publishers first to avoid mixing simulated and real positions, then run:

```bash
python -m messaging.component_test.earth_route_simulator_cli --no-broker
```

Stop the simulator with Ctrl+C and restart normal navigation services afterward.
The live browser diagnostic is available with:

```bash
python -m controllers.navigation.component_test.earth_cdp_probe_cli --trace-geolocation
```

Chromium's local DevTools endpoint uses port `9223`; do not run a second Earth
experiment with that port simultaneously. Use the existing graphics helper's
OpenGL/Vulkan probes and Chromium's `chrome://gpu` report to record the device
renderer. Do not enable a vendor-specific driver on an unvalidated GPU.

## Implementation and validation

`MapPlatformControlIf` exposes immutable selection state and semantic requests
to the frontend. The composition root owns `NavigationMapRuntime`, which serializes
browser launch, camera input, resizing, and detachment on one worker. The controller
consumes ORC position/motion messages in SI units and converts angles only at the
browser boundary. Chromium DevTools transport lives under `protocols/chromium`.

Tests cover browser reuse, failure fallback, stale startup cancellation,
hide/close behavior, camera request routing, and GPS conversion. A local headless
Chromium fixture verifies real DevTools discovery, WebSocket commands,
geolocation callback delivery, and keyboard/wheel input. These checks do not
validate Google Earth's current website, touch behavior, or Android GPU drivers.
