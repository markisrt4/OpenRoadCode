# OpenRoadCode Termux Target

This directory contains the native Termux build workflow used to exercise
OpenRoadCode directly on Android hardware.

The current target combines:

- the OpenRoadCode Android sensor bridge on localhost port `8766`;
- native Python controllers and services running in Termux;
- the OpenRoadCode ZeroMQ broker and navigation service under runit supervision;
- Android-backed IMU input through the sensor bridge;
- simulated geographic position and ground motion in the normal Termux runtime
  profile until Android location/motion endpoints are integrated;
- an independently tested browser-geolocation position path for native map
  checkout;
- native Valhalla and MapLibre builds;
- Termux:X11 for graphical execution;
- optional hardware-accelerated graphics when a compatible Mesa backend is
  available; and
- offline navigation data stored under `~/.local/share/openroadcode`.

The Termux runtime profile is `config/runtime.termux.toml`.

## Graphics acceleration

Android devices do not share one GPU architecture, so OpenRoadCode does not
assume a particular video driver. `development/termux/configure_graphics.sh`
inspects the device and selects only a graphics backend that the installed
Termux repositories can support.

Run detection without changing packages:

```bash
./development/termux/configure_graphics.sh
```

Install the packages selected for the detected device:

```bash
./development/termux/configure_graphics.sh --install
```

The first validated hardware path is Qualcomm/Adreno. On a device exposing the
KGSL interface, when the Termux repository supplies
`mesa-vulkan-icd-freedreno`, the selected stack is:

```text
Adreno -> KGSL -> Turnip/Freedreno -> Vulkan -> Zink -> OpenGL -> Termux:X11
```

For that backend, OpenGL applications should be launched with:

```bash
export MESA_LOADER_DRIVER_OVERRIDE=zink
```

Validate each layer independently when bringing up a new device. When the
corresponding diagnostic packages are installed, useful probes are:

```bash
vulkaninfo --summary
MESA_LOADER_DRIVER_OVERRIDE=zink glxinfo -B
MESA_LOADER_DRIVER_OVERRIDE=zink glxgears
```

Do not install every Mesa Vulkan ICD indiscriminately and do not assume
Freedreno on Mali, PowerVR, or other GPU families. Unknown devices retain the
basic/software graphics path until a hardware backend has been validated.
Application launchers should consume the selected graphics environment rather
than hard-coding a GPU vendor.

Chromium launched under Termux:X11 should use `--password-store=basic` so it
does not depend on a desktop password-keyring service. GPU-specific Chromium
flags should remain platform/runtime configuration rather than UI code.

## Navigation contracts

Navigation data is intentionally separated by responsibility:

- **Position** contains geographic fix information such as latitude, longitude,
  altitude, fix mode, satellite counts, and accuracy.
- **Ground motion** contains speed over ground, course over ground, vertical
  speed, and turn rate.
- **Attitude** contains heading, pitch, and roll.
- **IMU** contains acceleration and angular-velocity measurements.
- **Route guidance** contains progress and maneuver state for an active route.

Position does not own speed or course. Providers may originate several of these
values from the same physical device, but the normalized OpenRoadCode contracts
remain independent.

The navigation controller likewise accepts position and ground-motion sources
independently. The Termux simulation profile supplies separate simulated
position and ground-motion sources, while the Android sensor bridge currently
supplies the physical IMU input.

## Build the native navigation stack

```bash
cd ~/src/OpenRoadCode
./development/termux/build_navigation_stack.sh
```

The script installs/builds native dependencies and prints the resulting paths.
Termux:X11 normally uses display `:1`; override it with `X11_DISPLAY` when
needed.

## Test the Android sensor bridge

With the `openroadcode-android-bridge` application running:

```bash
curl http://127.0.0.1:8766/health
curl http://127.0.0.1:8766/imu
python -m hardware_io.android.component_test.magnetometer_cli
python -m controllers.navigation.component_test.android_navigation_sensor_cli
```

The current navigation service consumes Android IMU data through this bridge.
Android geographic position and ground-motion endpoints are follow-on bridge
integrations. Until then, `runtime.termux.toml` supplies those two inputs from
independent simulation sources.

## Run broker and navigation as services

Install Termux service supervision once:

```bash
pkg install termux-services
```

Restart the Termux shell after first installing `termux-services`, then from the
repository root run:

```bash
chmod +x scripts/runit/install_termux_services.sh
./scripts/runit/install_termux_services.sh
```

Start and inspect the production broker and navigation services with:

```bash
sv up openroadcode-broker
sv up openroadcode-navigation

sv status openroadcode-broker
sv status openroadcode-navigation
```

Stop them with:

```bash
sv down openroadcode-navigation
sv down openroadcode-broker
```

The runit definitions call the same runtime wrappers used by the Linux service
installation. Termux-specific supervision lives under `scripts/runit/`; the
application/service code remains platform independent.

If navigation remains `down`, run the service definition directly to expose the
startup error:

```bash
scripts/runit/openroadcode-navigation/run
```

Common development-time causes are an older manually launched navigation
process already owning command endpoint `tcp://127.0.0.1:5560`, or the Android
sensor bridge not running while the Termux profile is configured for Android
IMU input.

## Native map checkout with browser geolocation

A native MapLibre blue-dot checkout has been verified on Android using browser
geolocation as a temporary physical position source. The browser path publishes
the same public `openroad.navigation.position` contract used by normal
navigation consumers, so the renderer and map-follow runtime remain independent
of the physical position provider.

The verified data path is:

```text
Android browser navigator.geolocation
        |
        v
BrowserPositionSource HTTP :8765
        |
        v
PositionStatePublisher -> ZeroMQ ingress :5556
        |
        v
OpenRoadCode broker -> subscriber egress :5557
        |
        v
NavigationMapFollowRuntime
        |
        v
MapRendererClient -> renderer command endpoint :5562
        |
        v
native MapLibre renderer -> offline map + blue dot
```

For this isolated checkout, stop the normal navigation service so its simulated
position does not compete with browser position:

```bash
sv down openroadcode-navigation
sv status openroadcode-broker
```

Keep the following processes running in separate Termux terminals.

### Terminal 1: broker

The broker is normally already supervised by runit:

```bash
sv up openroadcode-broker
sv status openroadcode-broker
```

### Terminal 2: native map renderer

```bash
cd ~/src/OpenRoadCode
export DISPLAY=:1
./development/termux/start_map_renderer.sh
```

The Termux launcher creates target-local renderer configuration and rewrites the
deployed style paths for `~/.local/share/openroadcode`. The Termux renderer
command endpoint is TCP `tcp://127.0.0.1:5562`; this avoids Android restrictions
encountered with `/tmp` IPC sockets.

Mesa may report DRI3/Zink warnings under Termux:X11. A verified software-rendered
configuration falls back to LLVMpipe and still renders the offline map.

### Terminal 3: navigation-to-map follower

```bash
cd ~/src/OpenRoadCode
source venv-termux/bin/activate
python -m apps.common.navigation_map_follow_cli \
    --config config/runtime.termux.toml \
    --renderer-endpoint tcp://127.0.0.1:5562
```

### Terminal 4: browser position publisher

```bash
cd ~/src/OpenRoadCode
source venv-termux/bin/activate
python development/termux/browser_position_publisher_cli.py
```

Open `http://localhost:8765/` in the normal Android browser, select **Share
location**, and grant location permission. The terminal should print normalized
latitude, longitude, and accuracy reports. The map follower consumes those
reports from the normal ZeroMQ subscriber endpoint and updates the native blue
dot at the physical location.

This browser path is a development checkout, not the intended production GPS
architecture. The next production integration is an Android-backed
`PositionSourceIf` composed into the navigation service. Downstream consumers
should require no changes because they already consume the normalized position
contract.

## Run CarUi

Start Termux:X11/XFCE first, for example:

```bash
termux-x11 :1 -xstartup "xfce4-session"
```

Then launch CarUi from a Termux/X11 shell with the broker and navigation service
already running. The runtime uses the Termux profile and normal OpenRoadCode
messaging contracts.

The turn-by-turn panel has been exercised on Termux against the ZeroMQ guidance
path. Map following consumes position and ground motion independently, allowing
position fixes to remain authoritative while ground motion is used for bearing
and short-term map prediction.

## Navigation data

The runtime target pulls validated map/routing data from a map-build machine.
The map-build machine publishes a validated `/srv/openroadcode` dataset; the
target decides when to update itself. This avoids granting the build machine
privileged write access to runtime targets and keeps update timing under runtime
control.

The Termux-native target stores deployed navigation data under
`~/.local/share/openroadcode`. Use `development/termux/pull_navigation_data.sh`
for the Android/Termux path where applicable.

Server-push deployment is a development convenience only, not the production
update model.

## Test notes

The broad Python suite runs under Termux with platform-specific hardware tests
skipped when their Linux-only dependencies are unavailable. In particular,
gpsd Python bindings and evdev are not Termux runtime requirements simply
because Linux hardware adapters exist in the repository.

The final Termux branch regression run completed with 509 tests passing, 2
platform-specific tests skipped, and 45 subtests passing.
