# Native Map Renderer

`apps/map_renderer` is the C++ MapLibre Native display process used by OpenRoadCode navigation. It opens a GLFW window, loads the configured local map style, accepts commands over ZeroMQ, and renders camera, route, and vehicle-position updates without coupling Python controllers to MapLibre.

## Runtime contract

The renderer command server uses the OpenRoadCode ZeroMQ map-renderer endpoint. Clients normally use `protocols.map_renderer.map_renderer_client.MapRendererClient` rather than constructing transport messages directly.

The command protocol supports:

- `set_center` with `latitude` and `longitude`
- `set_camera` with `latitude`, `longitude`, `zoom`, `bearing`, and `pitch`
- `fit_bounds` with `south`, `west`, `north`, `east`, and optional `padding`
- `set_route` with a GeoJSON object
- `set_position` with `latitude` and `longitude`

`set_route` updates the GeoJSON source named `route`, while `set_position` updates the point source named `vehicle`. The MapLibre style must define those sources and their presentation layers.

## Runtime configuration

Production installs read renderer settings from:

```text
/etc/openroadcode/navigation.toml
```

The repository default is `config/navigation.toml`:

```toml
[map_renderer]
style = "/srv/openroadcode/maps/styles/openroadcode.json"
cache = "/var/cache/openroadcode/maplibre.db"

[vehicle_marker]
mode = "vehicle"
scale = 1.0
```

The navigation-stack installer creates `/etc/openroadcode/navigation.toml` only when it does not already exist. Re-running the installer preserves local vehicle configuration.

The filesystem ownership model is intentional:

```text
/opt/openroadcode/navigation/
    installed navigation software

/etc/openroadcode/navigation.toml
    vehicle/runtime configuration

/srv/openroadcode/
    deployable map and routing data
```

Map-data updates must not overwrite `/etc/openroadcode/navigation.toml`.

## Vehicle marker modes

The current runtime configuration supports:

- `blue_dot` — classic blue location marker
- `heading` — heading-oriented marker mode
- `vehicle` — vehicle-specific marker mode; this is the default

`scale` controls marker size relative to the style-defined base size.

The renderer includes `marker_mode` and `marker_scale` properties on the `vehicle` GeoJSON feature. The deployed MapLibre style uses those properties to select the corresponding presentation layer. Position transport remains independent of marker choice.

The `vehicle` mode currently uses a red placeholder presentation in the style. The intended production asset is a top-down red Hyundai Veloster graphic. That artwork should live in the deployable map/style asset package rather than being compiled into the C++ executable.

## Map/style data

The canonical deployed style is:

```text
/srv/openroadcode/maps/styles/openroadcode.json
```

It is produced by `tools/map_builder` and travels with the map dataset. It references the deployed MBTiles archive and glyphs and defines the `route` and `vehicle` GeoJSON sources.

Do not hard-code a region-specific style filename such as `michigan-test.json` in runtime code. Region selection belongs to the map-builder dataset; renderer configuration points at the stable `openroadcode.json` deployment path.

## Build

MapLibre Native must first be built with its Linux OpenGL preset. The [MapLibre build-container guide](../../development/containers/maplibre/README.md) provides the recommended isolated workflow. It pins the tested MapLibre commit, mounts the host source directory into the container, and includes scripts for building both MapLibre and this executable.

For a complete vehicle software build/install, prefer:

```bash
./scripts/installers/install_navigation_stack.sh --target rpi5
```

The navigation-stack installer builds MapLibre Native and the OpenRoadCode renderer in the container and installs the executable beneath:

```text
/opt/openroadcode/navigation/bin/
```

Map and Valhalla data are intentionally built and deployed separately; see [Navigation deployment](../../docs/navigation_deployment.md).

The container workflow is source-repeatable but not yet bit-for-bit hermetic. Its Debian base image and APT packages still float. The guide records this limitation and the remaining work needed for a stricter reproducibility guarantee.

For a direct developer build, expected container paths are:

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

Run a host-built renderer from the repository root:

```bash
apps/map_renderer/build/openroadcode-map-renderer
```

The container workflow writes the development executable to `apps/map_renderer/build-container/openroadcode-map-renderer` before the installer copies it into `/opt/openroadcode/navigation/bin/`.

With the renderer running, send sample commands with:

```bash
python3 -m protocols.map_renderer.component_test.map_renderer_client_cli
```

The window also supports mouse dragging, scroll-wheel zoom, and double-click zoom.

## Follow a live GPS receiver

With the renderer and gpsd running, send live 2D/3D fixes to the vehicle marker and follow camera:

```bash
python3 -m controllers.navigation.component_test.gpsd_map_follow_cli
```

The adapter renders at 30 frames per second. Between GPS fixes it predicts a short distance from GPS speed and course, then smoothly corrects toward each new fix. Prediction stops after 1.5 seconds without a report, and a correction of 75 meters or more snaps immediately rather than sliding across the map. GPS course rotates the map only above 1 m/s, which prevents an unreliable stationary course from making the map spin. Use `--no-follow` to update only the vehicle marker, or run with `--help` for GPSD endpoint, smoothing, and camera options.

### Parked checkout

Do this outside with the vehicle parked before beginning a road test:

1. Connect the USB receiver and identify its device:

   ```bash
   ls -l /dev/ttyACM* /dev/ttyUSB*
   ```

2. Verify the deployed gpsd service with `systemctl status gpsd gpsd.socket`, or use the repository foreground helper for development.

3. Confirm that gpsd reaches a 2D or 3D fix:

   ```bash
   gpspipe -w
   python3 -m hardware_io.gps.component_test.gps_cli
   ```

4. Start the installed renderer:

   ```bash
   /opt/openroadcode/navigation/bin/openroadcode-map-renderer
   ```

5. Start live map following from the repository root:

   ```bash
   python3 -m controllers.navigation.component_test.gpsd_map_follow_cli
   ```

The vehicle marker should appear at the live fix. At walking or driving speed, the camera should follow it and rotate to the GPS course. A stationary receiver retains the last reliable bearing.

### In-car test

Secure the computer, display, receiver, and cables; begin logging while parked; and have a passenger observe the display and terminal output. The driver should not operate the test UI. Start with a short, familiar, low-speed loop and check:

- time from startup to the first fix;
- marker lag and camera smoothness during acceleration and turns;
- unwanted camera rotation while stopped;
- recovery after tunnels, parking structures, or receiver obstruction;
- GPSD and renderer behavior after unplugging and reconnecting the receiver.

Use `--no-follow` to isolate marker accuracy from camera behavior. A production vehicle install should use the operating system's gpsd service rather than the foreground helper.
