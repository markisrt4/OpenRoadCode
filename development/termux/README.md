# OpenRoadCode Termux Target

This directory contains the native Termux build workflow used to exercise OpenRoadCode directly on Android hardware.

The current target combines:

- the OpenRoadCode Android sensor bridge on localhost port `8766`;
- native Python controllers and services running in Termux;
- the OpenRoadCode ZeroMQ broker, navigation service, and simulated ADS-B web presentation under runit supervision;
- Android-backed geographic position through the sensor bridge;
- simulated IMU input in the current Termux navigation profile;
- native Valhalla and MapLibre builds;
- Termux:X11 for graphical execution;
- optional hardware-accelerated graphics when a compatible Mesa backend is available; and
- offline navigation data stored under `~/.local/share/openroadcode`.

CarUi keeps the shared runtime composition in `config/runtime.toml` and selects `config/applications.termux.toml` for Termux-specific application behavior. `config/runtime.termux.toml` is the explicit Android/Termux navigation and sensor-service profile through `OPENROAD_RUNTIME_CONFIG`.

## Graphics acceleration

Android devices do not share one GPU architecture, so OpenRoadCode does not assume a particular video driver. `development/termux/configure_graphics.sh` inspects the device and selects only a graphics backend that the installed Termux repositories can support.

Run detection without changing packages:

```bash
./development/termux/configure_graphics.sh
```

Install the packages selected for the detected device:

```bash
./development/termux/configure_graphics.sh --install
```

The first validated hardware path is Qualcomm/Adreno. On a device exposing the KGSL interface, when the Termux repository supplies `mesa-vulkan-icd-freedreno`, the selected stack is:

```text
Adreno -> KGSL -> Turnip/Freedreno -> Vulkan -> Zink -> OpenGL -> Termux:X11
```

For that backend, OpenGL applications should be launched with:

```bash
export MESA_LOADER_DRIVER_OVERRIDE=zink
```

Validate each layer independently when bringing up a new device. When the corresponding diagnostic packages are installed, useful probes are:

```bash
vulkaninfo --summary
MESA_LOADER_DRIVER_OVERRIDE=zink glxinfo -B
MESA_LOADER_DRIVER_OVERRIDE=zink glxgears
```

Do not install every Mesa Vulkan ICD indiscriminately and do not assume Freedreno on Mali, PowerVR, or other GPU families. Unknown devices retain the basic/software graphics path until a hardware backend has been validated. Application launchers should consume the selected graphics environment rather than hard-coding a GPU vendor.

Chromium launched under Termux:X11 should use `--password-store=basic` so it does not depend on a desktop password-keyring service. GPU-specific Chromium flags should remain platform/runtime configuration rather than UI code.

## Navigation contracts

Navigation data is intentionally separated by responsibility:

- **Position** contains geographic fix information such as latitude, longitude, altitude, fix mode, satellite counts, and accuracy.
- **Ground motion** contains speed over ground, course over ground, vertical speed, and turn rate.
- **Attitude** contains heading, pitch, and roll.
- **IMU** contains acceleration and angular-velocity measurements.
- **Route guidance** contains progress and maneuver state for an active route.

Position does not conceptually own speed or course. A physical provider may deliver those values with a location sample, but normalized OpenRoadCode consumers remain insulated from the provider-specific transport.

The current Termux navigation profile uses the Android bridge as its physical position source and keeps IMU simulation available so navigation remains usable when Android motion integration is unavailable. The map consumes the normalized navigation position contract rather than talking directly to Android.

## Automotive transport on Termux

PySerial is intentionally **not** a Termux dependency. Android/Termux automotive hardware uses the Android bridge and TCP transport rather than opening a serial device directly from Termux.

The ELM327 stack keeps transport selection behind the common stream-transport interface. Physical Linux targets may select the serial backend when PySerial is installed, while Android/Termux injects the TCP transport exposed by the bridge. Importing the OBD-II controller stack or running transport-injected/simulated tests must not require PySerial merely to collect or import the modules.

For the validated KONNWEI/ELM327 Android path, the bridge exposes the Bluetooth SPP connection through localhost TCP. This keeps Bluetooth ownership in Android while OpenRoadCode consumes the same ELM327 protocol through a platform-neutral byte stream.

## Build the native navigation stack

```bash
cd ~/src/OpenRoadCode
./development/termux/build_navigation_stack.sh
```

The script installs/builds native dependencies and prints the resulting paths. Termux:X11 normally uses display `:1`; override it with `X11_DISPLAY` when needed.

## Test the Android sensor bridge

With the `openroadcode-android-bridge` application running:

```bash
curl http://127.0.0.1:8766/health
curl http://127.0.0.1:8766/location
curl http://127.0.0.1:8766/imu
```

A healthy `/location` response is consumed by `AndroidPositionSource` and published by the normal navigation service. This keeps map-follow and other consumers independent of the Android bridge API.

## Run supervised Termux services

Install Termux service supervision once:

```bash
pkg install termux-services
```

Restart the Termux shell after first installing `termux-services`, then from the repository root run:

```bash
chmod +x scripts/runit/install_termux_services.sh
./scripts/runit/install_termux_services.sh
```

Start and inspect the supervised services with:

```bash
sv up openroadcode-broker
sv up openroadcode-navigation
sv up openroadcode-adsb

sv status openroadcode-broker
sv status openroadcode-navigation
sv status openroadcode-adsb
```

Stop them with:

```bash
sv down openroadcode-adsb
sv down openroadcode-navigation
sv down openroadcode-broker
```

The runit definitions call the same runtime wrappers used by the Linux service installation where applicable. Termux-specific service definitions live under `scripts/runit/`. Runtime-generated `supervise/` directories are state, not source, and must never be committed to the repository.

Valhalla is currently launched separately from the supervised broker/navigation services. The Termux build installs it under `$PREFIX/opt/openroadcode/navigation/valhalla/bin/valhalla_service`, while deployed routing data and the Termux-specific configuration live under `~/.local/share/openroadcode/valhalla`.

A development launch is:

```bash
VALHALLA_CONFIG="$HOME/.local/share/openroadcode/valhalla/valhalla.termux.json" \
VALHALLA_BIN="$PREFIX/opt/openroadcode/navigation/valhalla/bin/valhalla_service" \
VALHALLA_WORKERS=1 \
./scripts/runtime/start_valhalla.sh
```

Verify the service with:

```bash
curl http://127.0.0.1:8002/status
```

## ADS-B / tar1090 simulation

The Termux application profile uses the ADS-B producer source `simulation`. This keeps presentation testing independent of RTL-SDR hardware and Linux `readsb`/systemd service management.

Install the tar1090 presentation files once:

```bash
cd ~/src/OpenRoadCode
./development/termux/setup_tar1090.sh
```

After `scripts/runit/install_termux_services.sh` has installed the service, `openroadcode-adsb` owns the local tar1090 web server on port `8081`.

## Native map and route presentation

The native MapLibre renderer uses offline vector tiles under `~/.local/share/openroadcode/maps/vector/openroadcode.mbtiles`. Map commands are published on the OpenRoadCode message bus using the `map.command` topic. Position telemetry and camera control remain separate so a manual pan does not move the vehicle marker.

The active navigation/map path is:

```text
Android location
        |
        v
Android sensor bridge :8766
        |
        v
AndroidPositionSource
        |
        v
navigation service -> normalized position telemetry
        |
        v
OpenRoadCode ZeroMQ broker
        |
        +--------------------> ORC UI map-follow camera
        |
        v
MapRendererClient -> map.command
        |
        v
native MapLibre renderer -> offline map + vehicle marker / route
```

Route planning uses the local Valhalla HTTP service on port `8002`. The route-to-map component test can use the real Valhalla service while recording renderer commands:

```bash
python -m services.navigation.component_test.route_to_map_e2e_cli \
  --external-valhalla
```

To publish the resulting route to a running renderer through the normal broker path, add `--external-renderer`.

## Run ORC UI

Start Termux:X11/XFCE first. When X11 is managed by runit, do not start a duplicate server on the same display.

Then launch the ORC UI from a Termux/X11 shell with the broker and navigation service already running:

```bash
cd ~/src/OpenRoadCode
export DISPLAY=:1
export CARUI_FULLSCREEN=0
export CARUI_GEOMETRY=1024x600
python -m apps.orcUi
```

The current ORC UI navigation map supports shared camera state between Home and Navigation views, follow/recenter behavior, screen-relative panning, route overlays, live vehicle position, and focused POI categories. Browser-backed launchers use the selected X11 display and Chromium is started with `--password-store=basic`.

## Navigation data

The runtime target pulls validated map/routing data from a map-build machine. The map-build machine publishes a validated dataset; the target decides when to update itself. The Termux-native target stores deployed navigation data under `~/.local/share/openroadcode`. Use `development/termux/pull_navigation_data.sh` for the Android/Termux path where applicable.

Vector-map content and routing data are generated from source datasets and should not be assumed to contain every real-world business. UI POI highlighting operates on features present in the deployed vector tiles.

## Test notes

The broad Python suite runs under Termux with platform-specific hardware tests skipped when their Linux-only dependencies are unavailable. Component tests supplement automated tests where real hardware, native services, X11, or Android integration is required.
