# OpenRoadCode runit services

These service definitions provide the Termux counterpart to the Linux service
installers under `scripts/systemd/`. Runit remains the process supervisor on
Android/Termux; higher-level clients such as the OpenRoadCode Android bridge may
control it through the localhost service-manager API.

## Services

- `openroadcode-service-manager` provides the lightweight localhost control
  plane on `127.0.0.1:8769`.
- `openroadcode-message-broker` runs the ZeroMQ message broker.
- `openroadcode-valhalla` runs local routing with a prepared Termux configuration.
- `openroadcode-navigation` runs the navigation service using
  `config/runtime.termux.toml`.
- `openroadcode-automotive` publishes the automotive state. Navigation ground
  motion is its default road-speed source on Termux.
- `openroadcode-adsb` runs the optional ADS-B/tar1090 stack.

The normal **core stack** is broker + Valhalla + navigation + automotive. ADS-B is kept
optional so radio processing is not consuming resources when it is not needed.
The service manager is intentionally lightweight and can remain running while
the core stack is stopped.

Only the service manager starts automatically after installation. Core and
ADS-B definitions include runit's `down` marker so opening Termux does not
unexpectedly consume routing, radio, or sensor resources.

## Install

Termux requires the `termux-services` package:

```bash
pkg install termux-services
```

After installing that package, restart the Termux shell once so its service
environment is initialized. Then, from the OpenRoadCode repository:

```bash
cd ~/src/OpenRoadCode
./scripts/runit/install_termux_services.sh
```

If Valhalla is running in a foreground terminal, stop that instance before
installing its supervised service. New navigation builds register these services
automatically. Routing data must be installed before Valhalla can serve requests.

On Linux, `scripts/systemd/install_navigation_runtime_systemd.sh` installs and
enables the broker, Valhalla, and navigation units. Navigation requests
`valhalla.service` as a dependency. After upgrading service-manager integration,
rerun `scripts/systemd/install_service_manager_systemd.sh` to refresh its narrow
systemctl permissions, which now include Valhalla core start/stop/restart.

The installer creates real service directories under `$PREFIX/var/service/`
and copies the version-controlled `run` definitions into them. Mutable
`supervise/` state therefore remains outside the source tree. The installer
also removes retired service names, stopping them first so a migration cannot
leave duplicate processes bound to the same ports.

Every service writes rotating logs beneath
`~/.local/state/openroadcode/log/<service>/`. The installer also verifies that
`runsvdir` has adopted every service. A newly
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
sv status openroadcode-valhalla
sv status openroadcode-navigation
sv status openroadcode-automotive
sv status openroadcode-adsb

scripts/runit/manage_core.sh start
scripts/runit/manage_core.sh status
scripts/runit/manage_core.sh stop
```

Start dependencies in the order broker -> Valhalla -> navigation -> automotive. Stop them
in reverse order. `openroadcode-adsb` may be started and stopped independently.

## Local service-manager API

The Android bridge does not replace runit. It uses the service manager as a
small control plane while runit continues to own process lifetime and crash
restarts.

```bash
curl http://127.0.0.1:8769/services
curl -X POST http://127.0.0.1:8769/stack/core/start
curl -X POST http://127.0.0.1:8769/stack/core/stop
curl -X POST http://127.0.0.1:8769/services/openroadcode-navigation/restart
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
