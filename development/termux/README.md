# OpenRoadCode Termux Target

This directory contains the experimental native Termux build workflow used to
exercise OpenRoadCode directly on Android hardware.

The current target combines:

- the OpenRoadCode Android sensor bridge on localhost port 8766;
- Python hardware/controller code running natively in Termux;
- the OpenRoadCode ZeroMQ broker and services;
- native Valhalla and MapLibre builds;
- Termux:X11 for native graphical execution;
- an offline navigation dataset stored under
  `~/.local/share/openroadcode`.

## Build the native navigation stack

```bash
cd ~/src/OpenRoadCode
./development/termux/build_navigation_stack.sh
```

The script installs/builds native dependencies and prints the resulting paths.
Termux:X11 defaults to display `:1`; override it with `X11_DISPLAY` when needed.

## Test the Android sensor bridge

With the OpenRoadCode Android bridge application running:

```bash
curl http://127.0.0.1:8766/health
curl http://127.0.0.1:8766/imu
python -m hardware_io.android.component_test.magnetometer_cli
python -m controllers.navigation.component_test.android_navigation_sensor_cli
```

## Test Android sensors through ZeroMQ

Use three Termux sessions.

Session 1, broker:

```bash
cd ~/src/OpenRoadCode
python -m messaging.zeromq.broker_cli
```

Session 2, Android sensor service:

```bash
cd ~/src/OpenRoadCode
python -m services.android.android_sensor_service_cli
```

Session 3, subscriber:

```bash
cd ~/src/OpenRoadCode
python -m services.android.android_sensor_subscriber_cli
```

Move and rotate the phone. The subscriber should continuously print
`navigation.imu_state` messages whose source is the Android bridge.

## Navigation data

The runtime target should pull validated map/routing data from a map-build
machine. The map-build machine publishes a validated `/srv/openroadcode`
dataset; the target decides when to update itself. This avoids granting the
build machine privileged write access to runtime targets and keeps update
timing under runtime control.

Linux vehicle targets use `scripts/runtime/pull_navigation_data.sh`. A
Termux-native pull helper is the preferred next step for the Android target,
using `~/.local/share/openroadcode` instead of `/srv/openroadcode` and no sudo.

Server-push deployment is development convenience only, not the production
update model.
