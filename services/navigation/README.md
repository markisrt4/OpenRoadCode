# Navigation Service

The navigation service is the single owner of the active navigation pipeline. It publishes navigation telemetry and accepts acknowledged navigation commands without requiring applications to know which IMU or GPS hardware is installed.

## Runtime ownership

```text
configured IMU + GPS sources
          |
NavigationController
          |
          +--> NavigationStatePublisher --> ZeroMQ telemetry bus
          |
          +--> NavigationCommandService <-- ZeroMQ REQ/REP client
```

Applications should subscribe to public navigation topics for state and use `NavigationRequestHandlerIf` for commands. They should not construct navigation hardware merely to display telemetry or request calibration.

## Configuration

Navigation composition is selected entirely through runtime TOML. There is no separate simulation code path in the service CLI.

Physical example:

```toml
[services.navigation]
enabled = true
rate_hz = 10.0
command_endpoint = "tcp://127.0.0.1:5560"

[services.navigation.inputs.imu]
source = "device"
device = "mpu6050"
address = 0x68

[services.navigation.inputs.gps]
source = "device"
device = "gpsd"
host = "127.0.0.1"
port = "2947"
```

Simulation example:

```toml
[services.navigation.inputs.imu]
source = "simulation"

[services.navigation.inputs.imu.simulation]
profile = "driving"

[services.navigation.inputs.gps]
source = "simulation"

[services.navigation.inputs.gps.simulation]
profile = "driving"
latitude_deg = 42.8028
longitude_deg = -83.0127
speed_mps = 13.4
course_deg = 180.0
```

Both configurations run the same `NavigationController` and publication path. Only the concrete input sources change.

## Start locally

Start the ZeroMQ broker first:

```bash
python3 -m messaging.zeromq.broker_cli
```

Then start the navigation service with the desired runtime file:

```bash
python3 -m services.navigation.navigation_service_cli \
  --config config/runtime.toml
```

For a simulation runtime:

```bash
python3 -m services.navigation.navigation_service_cli \
  --config config/runtime_simulation.toml
```

The telemetry publisher endpoint comes from `[messaging].publisher_endpoint`. The navigation command endpoint defaults to `tcp://127.0.0.1:5560` unless overridden in the runtime TOML.

## Public telemetry

The service publishes one controller snapshot across the navigation contracts:

- `openroad.navigation.position`
- `openroad.navigation.motion`
- `openroad.navigation.attitude`
- `openroad.navigation.imu`

See `messaging/README.md` and `docs/messaging/message_bus_idd.md` for subscriber examples and wire-contract details.

## Commands

Commands use ZeroMQ REQ/REP rather than the PUB/SUB telemetry bus because callers need acknowledgement and error reporting.

The initial operations are:

- `navigation.calibrate_stationary`
- `navigation.reset_heading`

Application code should normally depend on the toolkit-independent request interface:

```python
from ui.navigation.navigation_request_handler_if import NavigationRequestHandlerIf


def calibrate(handler: NavigationRequestHandlerIf) -> None:
    handler.request_stationary_calibration()


def zero_heading(handler: NavigationRequestHandlerIf) -> None:
    handler.request_heading_reset()
```

A standalone process can use the ZeroMQ implementation:

```python
from services.navigation.zeromq_navigation_request_handler import (
    ZeroMqNavigationRequestHandler,
)

handler = ZeroMqNavigationRequestHandler()
try:
    handler.request_stationary_calibration()
    handler.request_heading_reset()
finally:
    handler.close()
```

The service executes both operations against the same navigation controller instance used for telemetry publication. This prevents UI processes from creating competing hardware/controller instances.

## Shared consumer state

Applications that need a latest-value cache can use:

```python
from common.telemetry.navigation_bus_state import NavigationBusState
```

Register its setters with `MessageDispatcher`, then read `snapshot()` from the UI thread. `common.telemetry.vehicle_bus_state.VehicleBusState` provides the equivalent pattern for vehicle telemetry.

## Testing

Navigation service unit tests cover command semantics, REQ/REP transport, shared controller ownership, runtime composition, and configuration parsing. Messaging integration tests cover navigation telemetry through the broker.
