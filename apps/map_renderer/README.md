## Map/style data

The canonical deployed style is:

```text
/srv/openroadcode/maps/styles/openroadcode.json
```

It is produced by `tools/map_builder` and travels with the map dataset. It references the deployed MBTiles archive and glyphs and defines the `route` and `vehicle` GeoJSON sources.

Do not hard-code a region-specific style filename such as `michigan-test.json` in runtime code. Region selection belongs to the map-builder dataset; renderer configuration points at the stable `openroadcode.json` deployment path.

## Build

MapLibre Native must first be built with its Linux OpenGL preset. The [MapLibre build-container guide](https://github.com/markisrt4/OpenRoadCode/blob/master/development/containers/maplibre/README.md) provides the recommended isolated workflow. It pins the tested MapLibre commit, mounts the host source directory into the container, and includes scripts for building both MapLibre and this executable.

For a complete vehicle software build/install, prefer:

```bash
./scripts/installers/install_navigation_stack.sh --target rpi5
```

The navigation-stack installer builds MapLibre Native and the OpenRoadCode renderer in the container and installs the executable beneath:

```text
/opt/openroadcode/navigation/bin/
```

Map and Valhalla data are intentionally built and deployed separately; see [Navigation deployment](https://github.com/markisrt4/OpenRoadCode/blob/master/docs/navigation_deployment.md).

The container workflow is source-repeatable but not yet bit-for-bit hermetic. Its Debian base image and APT packages still float. The guide records this limitation and the remaining work needed for a stricter reproducibility guarantee.

## Radar position markers

Weather radar visibility also controls three concentric locator rings around
`vehicle`, the real live or cached navigation position. The rings sit above the
precipitation overlay and below the vehicle marker. Their radii are fixed at
36, 72, and 108 screen pixels so the position remains easy to spot at any zoom;
they are location indicators, not distance scales. Panning the map does not
move the rings to the camera center. Without a known position, no rings appear.

Repeated commands for the same radar tile URL update opacity/visibility while
retaining the source and tile cache. This lets Home and Navigation replay radar
state after a renderer restart without continuously rebuilding the overlay.

After pulling changes to the renderer, rebuild/install the native executable
as well as restarting the Python UI. On Termux, run
`./development/termux/build_navigation_stack.sh`; it rebuilds ORC's renderer
incrementally while retaining already built Valhalla dependencies. MapLibre is
rebuilt when its pinned revision or libpng headers/version change, or when an
older build has no dependency stamp. This prevents startup crashes after a
Termux libpng upgrade (for example, `libpng version mismatch`). Stop the UI
before rebuilding and restart it after installation completes.

On X11, the renderer first requests an EGL OpenGL ES 3.0 context. If EGL cannot
create the window, it retries using X11's native GLX context API with the same
OpenGL ES and framebuffer requirements. Termux always selects GLFW's X11
platform, including standalone launches. The renderer logs the fallback and
reports failure if neither context API works.


### City weather labels

The renderer adds a `city-weather` GeoJSON source and large value/smaller city
name symbols to the configured style at startup. `set_city_weather` updates
these points independently of `route-weather`, radar and temperature/wind
rasters. `search_weather_cities` reads loaded offline `place` vector features,
checks their screen positions (including tilt and bearing), prioritizes cities
and towns, deduplicates tile copies, and spaces a maximum of twelve labels.
Replies use `map.weather.cities` with the request id and named coordinates.
The Python city-weather controller owns the data, time window and units.

City-weather feature hits use `weather_city_hit.hpp` to select the opaque city
identity before publishing the existing map-click event. A small native check
covers absent, invalid-type, POI, and valid city identities:

```bash
g++ -std=c++20 -Wall -Wextra -Werror apps/map_renderer/component_test/weather_city_hit_cli.cpp -o /tmp/weather-city-hit-test
/tmp/weather-city-hit-test
```
