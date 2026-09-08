# OpenRoadCode runit services

These service definitions provide the Termux counterpart to the Linux service
installers under `scripts/systemd/`. Runit remains the process supervisor on
Android/Termux; higher-level clients such as the OpenRoadCode Android bridge may
control it through the localhost service-manager API.

## Services

- `openroadcode-service-manager` provides the lightweight localhost control
  plane on `127.0.0.1:8768`.
- `openroadcode-message-broker` runs the ZeroMQ message broker.
- `openroadcode-navigation` runs the navigation service using
  `config/runtime.termux.toml`.
- `openroadcode-automotive` publishes the automotive state. Navigation ground
  motion is its default road-speed source on Termux.
- `openroadcode-adsb` runs the optional ADS-B/tar1090 stack.

The normal **core stack** is broker + navigation + automotive. ADS-B is kept
optional so radio processing is not consuming resources when it is not needed.
The service manager is intentionally lightweight and can remain running while
the core stack is stopped.

## Install

Termux requires the `termux-services` package:

```bash
pkg install termux-services
```

After installing that package, restart the Termux shell once so its service
environment is initialized. Then, from the OpenRoadCode repository:

```bash
cd ~/src/OpenRoadCode
git switch automotive
./scripts/runit/install_termux_services.sh
```

The installer creates real service directories under `$PREFIX/var/service/`
and copies the version-controlled `run` definitions into them. Mutable
`supervise/` state therefore remains outside the source tree. The installer
also removes retired service names, stopping them first so a migration cannot
leave duplicate processes bound to the same ports.

The installer also verifies that `runsvdir` has adopted every service. A newly
added service normally appears automatically. If Termux's existing supervisor
does not notice it, the installer reports the affected services and asks you to
restart the supervisor:

```bash
pkill runsvdir
```

Then fully close/reopen Termux and verify the reported service with `sv status`.
This is the recovery for warnings such as:

```text
unable to open supervise/ok: file does not exist
```

## Direct control

```bash
sv status openroadcode-service-manager
sv status openroadcode-message-broker
sv status openroadcode-navigation
sv status openroadcode-automotive
sv status openroadcode-adsb

sv up openroadcode-message-broker
sv up openroadcode-navigation
sv up openroadcode-automotive

sv down openroadcode-automotive
sv down openroadcode-navigation
sv down openroadcode-message-broker
```

Start dependencies in the order broker -> navigation -> automotive. Stop them
in reverse order. `openroadcode-adsb` may be started and stopped independently.

## Local service-manager API

The Android bridge does not replace runit. It uses the service manager as a
small control plane while runit continues to own process lifetime and crash
restarts.

```bash
curl http://127.0.0.1:8768/services
curl -X POST http://127.0.0.1:8768/stack/core/start
curl -X POST http://127.0.0.1:8768/stack/core/stop
curl -X POST http://127.0.0.1:8768/services/openroadcode-navigation/restart
```

The API binds only to localhost and accepts only predefined OpenRoadCode
service operations. It deliberately does not expose arbitrary shell execution.

## Battery and idle operation

Stopping the core stack is the preferred phone idle state when OpenRoadCode is
not being used. The lightweight service manager can remain available so the
Android bridge can start the stack again. Android-side sensor, Bluetooth,
camera, and USB/radio services have separate lifecycles; a future full-stop
control can shut those down together with the Termux core for the lowest idle
power use.
