# Google Earth destination exploration

The active ORC navigation view uses MapLibre. Select a POI on the map or from a
nearby search, then press the **globe icon inside that place’s popup** to explore
its destination in Earth. The icon sits beside the place name; the map has no
floating Earth control. The colour PNG globe has transparent corners that blend
into the popup; offline mode greys it out and disables launching.

Earth opens the selected destination in a separate ordinary native Chromium
window, with its normal browser and Earth controls. Internet access and native
Chromium are required. Close the browser window when finished to return to ORC,
which continues using MapLibre. A successful launch closes the selected POI card.

The handoff passes only the selected place through a URL. It does not embed Earth,
subscribe to GPS, inject location, expose DevTools, or automate the Earth camera.
Earth controls the initial transition and subsequent exploration. This link-out
design is an interpretation of ordinary viewing permitted by the
[Earth terms](https://www.google.com/help/terms_maps-earth/), not an explicit
Google approval of ORC. Google's
[permissions guidance](https://about.google/brand-resource-center/products-and-services/geo-guidelines/)
separately prohibits embedding Earth in apps. Keep the normal Google/provider
attribution visible.

Update the branch and restart ORC before trying it:

```bash
git switch navigation-google-earth
git pull --ff-only origin navigation-google-earth
```

The prior embedded/GPS experiment remains in the branch history and source for
reference, but is no longer wired into the default ORC navigation screen. The
following notes describe that historical experiment, not the active UI workflow.

---

# Historical Google Earth navigation experiment

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
3. Switch to MapLibre and back. Earth closes on switching away and opens a fresh
   embedded browser on return. Resize the ORC window and verify the embedded viewport fits.
4. Navigate Home, return to Navigation, change theme, and close ORC. Verify that
   Earth never remains attached to a destroyed map host or appears as an orphan
   window. The application runtime owns the browser; leaving Navigation closes
   it before the map host is destroyed.
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
renderer. The Earth launcher leaves Chromium's GPU backend selection at its
platform default and preserves explicit browser GPU arguments. The browser still
receives the existing Mesa graphics environment. Forcing ANGLE desktop OpenGL
(`--use-gl=angle --use-angle=gl`) caused a reported Termux Earth startup regression
and is no longer selected automatically. Driver detection alone does not validate
Chromium's available ANGLE backends or establish hardware acceleration.
Fully restart ORC and its Earth browser after updating; a warm browser retains its
old launch settings.

If location fails, first check that MapLibre has the correct ORC position. Earth's
status distinguishes missing ORC coordinates, bridge startup, and delivery without
an active Earth location subscription. The location tool retries every five seconds
until Earth subscribes, rather than treating a dispatched click as success.
Use recenter after manually panning. Enable `ORC_EARTH_TRACE=1` before launching
ORC to log delivered coordinates and active watchers.

Do not enable a vendor-specific driver on an unvalidated GPU.

## Implementation and validation

`MapPlatformControlIf` exposes immutable selection state and semantic requests
to the frontend. The composition root owns `NavigationMapRuntime`, which serializes
browser launch, camera input, resizing, and shutdown on one worker. The controller
consumes ORC position/motion messages in SI units and converts angles only at the
browser boundary. Chromium DevTools transport lives under `protocols/chromium`.

Tests cover fresh browser startup, failure fallback, stale startup cancellation,
hide/close behavior, camera request routing, and GPS conversion. A local headless
Chromium fixture verifies real DevTools discovery, WebSocket commands,
geolocation callback delivery, and keyboard/wheel input. These checks do not
validate Google Earth's current website, touch behavior, or Android GPU drivers.

## Diagnosing a black Earth viewport on Termux

`VK_ERROR_SURFACE_LOST_KHR`, `swapchain killed`, and Chromium GPU-process exits
indicate a failed rendering surface/GPU process. The accompanying missing X11
refresh-rate extensions alone do not establish the cause. ORC applies Earth
window resizing only when dimensions change; GPS ticks no longer issue redundant
X11 resize/move operations. This reduces surface reconfiguration but does not
prove that Zink survives embedding or window hide/reopen on the device.

Close ORC and its Earth browser, then run a visible standalone window without ORC
embedding:

```bash
python -m apps.launchers.component_test.google_earth_launcher_cli --display :1
```

Leave the terminal waiting while inspecting Earth; press Enter to stop the test.
If standalone Earth also goes black, inspect the browser log for GPU failures.
If standalone works but embedding fails, investigate X11 reparent/hide and surface
lifecycle rather than changing the GPU backend blindly. The standalone test uses
a temporary unique browser profile and process selector, with a default example
location, not ORC GPS. It does not reuse or stop an existing ORC Earth instance.
Its separate `earth-standalone.log` path is printed when the test starts.

### Standalone Earth with live ORC GPS

Keep the ORC broker and navigation service running with a valid Android position
(the same feed used by MapLibre). The ORC UI may remain on MapLibre; do not open
its embedded Earth window during this test.

```bash
python -m apps.launchers.component_test.google_earth_launcher_cli --display :1 --orc-gps
```

This uses port `9224` (separate from embedded Earth's `9223`), grants only the
Earth origin geolocation permission through Chromium DevTools, and feeds ORC GPS
into the page bridge. It does not ask Chromium to obtain Android location itself.
The terminal reports page/bridge readiness, missing ORC coordinates, and Earth
location subscription state. Wait for Earth to finish loading; Ctrl+C closes only
the test browser and its subscriber. Run only one GPS diagnostic on that port.
A synthetic position in the initial URL is just the starting view; it does not
represent a live receiver fix. Device tests must confirm actual coordinates and
follow behavior, not just a successful bridge delivery.

### Embedded surface startup

ORC prepares an `about:blank` Chromium shell, embeds and sizes it, and then
navigates to Earth using DevTools. Earth creates its WebGL surface after X11
reparenting. Switching away or leaving Navigation closes the browser while its
host still exists; it no longer reparents an active Earth surface for warm reuse.
Returning reloads Earth. Preload prepares only the blank shell; nonembedded
application launches still navigate to the configured Earth URL when shown.
Permission grants are refreshed when Chromium's browser session changes.

This removes operations associated with the reported surface loss, but the actual
Termux/Zink behavior still requires testing: select embedded Earth, verify GPS,
switch to MapLibre and back, leave and return to Navigation, resize, then close
ORC. A standalone success does not prove the embedded GPU path is stable.
