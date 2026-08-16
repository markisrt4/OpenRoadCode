# Native Map Renderer

`apps/map_renderer` is the C++ MapLibre Native display process used by
OpenRoadCode navigation. It opens a GLFW window, loads the configured local
map style, accepts commands over a Unix-domain socket, and renders camera or
route updates without coupling Python controllers to MapLibre.

## Runtime contract

The renderer listens at:

```text
/tmp/openroadcode-map-renderer.sock
```

Clients normally use
`protocols.map_renderer.map_renderer_client.MapRendererClient`. The JSON
protocol supports:

- `set_center` with `latitude` and `longitude`
- `set_camera` with `latitude`, `longitude`, `zoom`, `bearing`, and `pitch`
- `fit_bounds` with `south`, `west`, `north`, `east`, and optional `padding`
- `set_route` with a GeoJSON object
- `set_position` with `latitude` and `longitude`

`set_route` updates the GeoJSON source named `route`, while `set_position`
updates the point source named `vehicle`. The MapLibre style must define those
sources and the layers that display them. The current executable loads
`/srv/openroadcode/maps/styles/michigan-test.json` and caches resources in
`/tmp/openroadcode-map-cache.db`.

## Build

MapLibre Native must first be built with its Linux OpenGL preset. The
[MapLibre build-container guide](../../development/containers/maplibre/README.md)
provides the recommended isolated workflow. It pins the tested MapLibre
commit, mounts the host source directory into the container, and includes
scripts for building both MapLibre and this executable.

The container workflow is source-repeatable but not yet bit-for-bit hermetic:
its Debian base image and APT packages still float. The guide records this
limitation and the remaining work needed for a fully reproducible build.

Inside the build container, the expected source and build trees are:

```text
/src/maplibre-native
/src/maplibre-native/build-linux-opengl
```

Override those paths when configuring if needed:

```bash
cmake -S apps/map_renderer -B apps/map_renderer/build \
  -DMAPLIBRE_ROOT=/path/to/maplibre-native \
  -DMAPLIBRE_BUILD=/path/to/maplibre-native/build-linux-opengl
cmake --build apps/map_renderer/build
```

For a host build, always supply those two CMake options because the defaults
are container paths.

Run a host-built renderer from the repository root:

```bash
apps/map_renderer/build/openroadcode-map-renderer
```

The container workflow instead writes the executable to
`apps/map_renderer/build-container/openroadcode-map-renderer` by default.

With the renderer running, send a sample camera command:

```bash
python3 -m protocols.map_renderer.component_test.map_renderer_client_cli
```

The window also supports mouse dragging, scroll-wheel zoom, and double-click
zoom.

## Follow a live GPS receiver

With the renderer and gpsd running, send live 2D/3D fixes to the vehicle
marker and follow camera:

```bash
python3 -m controllers.navigation.component_test.gpsd_map_follow_cli
```

The adapter renders at 30 frames per second. Between GPS fixes it predicts a
short distance from GPS speed and course, then smoothly corrects toward each
new fix. Prediction stops after 1.5 seconds without a report, and a correction
of 75 meters or more snaps immediately rather than sliding across the map.
GPS course rotates the map only above 1 m/s, which prevents an unreliable
stationary course from making the map spin. Use `--no-follow` to update only
the vehicle marker, or run with `--help` for GPSD endpoint, smoothing, camera,
and socket options.

### Parked checkout

Do this outside with the vehicle parked before beginning a road test:

1. Connect the USB receiver and identify its device:

   ```bash
   ls -l /dev/ttyACM* /dev/ttyUSB*
   ```

2. If the deployed system gpsd service is already configured, verify it with
   `systemctl status gpsd gpsd.socket`. Otherwise, start the repository's
   foreground test instance in its own terminal:

   ```bash
   hardware_io/gps/start_gpsd.sh /dev/ttyACM0
   ```

3. Confirm that gpsd reaches a 2D or 3D fix:

   ```bash
   gpspipe -w
   python3 -m hardware_io.gps.component_test.gps_cli
   ```

4. Start `openroadcode-map-renderer` using the normal host or container build
   described above. Confirm that its socket exists:

   ```bash
   ls -l /tmp/openroadcode-map-renderer.sock
   ```

5. Start live map following from the repository root:

   ```bash
   python3 -m controllers.navigation.component_test.gpsd_map_follow_cli
   ```

The vehicle marker should appear at the live fix. At walking or driving speed,
the camera should follow it and rotate to the GPS course. A stationary receiver
will retain the last reliable bearing.

### In-car test

Secure the computer, display, receiver, and cables; begin logging while parked;
and have a passenger observe the display and terminal output. The driver should
not operate the test UI. Start with a short, familiar, low-speed loop and check:

- time from startup to the first fix;
- marker lag and camera smoothness during acceleration and turns;
- unwanted camera rotation while stopped;
- recovery after tunnels, parking structures, or receiver obstruction;
- GPSD and renderer behavior after unplugging and reconnecting the receiver.

If the camera feels too busy, reduce its update rate, for example:

```bash
python3 -m controllers.navigation.component_test.gpsd_map_follow_cli \
  --correction-time 0.8 \
  --camera-interval 0.1 \
  --course-speed 2.0
```

Use `--no-follow` to isolate marker accuracy from camera behavior. Press
`Ctrl+C` to stop the bridge; stop the foreground gpsd helper separately if it
was used. A production vehicle install should use the operating system's gpsd
service rather than the foreground helper.

## Offline map assets

The executable currently expects the style at
`/srv/openroadcode/maps/styles/michigan-test.json`. That style is deployment
data and is not created by the C++ build. It must reference the locally
generated MBTiles archive and define `route` and `vehicle` GeoJSON sources.
See the [offline tile guide](../../development/containers/maplibre/scripts/README.md)
for the separate tilemaker workflow.
