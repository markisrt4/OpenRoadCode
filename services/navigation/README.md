# Navigation Service

The navigation service is the single owner of the active navigation controller. It publishes navigation telemetry and accepts acknowledged navigation commands without requiring applications to know which IMU or GPS hardware is installed.

## Runtime ownership

```text
IMU / GPS / simulator
        |
NavigationControllerIf
        |
        +--> NavigationStatePublisher --> ZeroMQ telemetry bus
        |
        +--> NavigationCommandService <-- ZeroMQ REQ/REP client
```

Applications should subscribe to public navigation topics for state and use `NavigationRequestHandlerIf` for commands. They should not construct navigation hardware merely to display telemetry or request calibration.

## Start locally

Start the message broker first:

```bash
python3 -m messaging.zeromq.broker_cli
```

Then start the navigation service with simulated hardware:

```bash
python3 -m services.navigation.navigation_service_cli --simulate
```

For physical MPU-6050 navigation:

```bash
python3 -m services.navigation.navigation_service_cli
```

Enable GPS owned by the same service with:

```bash
python3 -m services.navigation.navigation_service_cli --gps
```

The default telemetry publisher endpoint is supplied by `messaging.zeromq.endpoints`. The navigation command endpoint defaults to `tcp://127.0.0.1:5560`.

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

The service executes both operations against the same `NavigationControllerIf` instance used for telemetry publication. This prevents UI processes from creating competing hardware/controller instances.

## Shared consumer state

Applications that need a latest-value cache can use:

```python
from common.telemetry.navigation_bus_state import NavigationBusState
```

Register its setters with `MessageDispatcher`, then read `snapshot()` from the UI thread. `common.telemetry.vehicle_bus_state.VehicleBusState` provides the equivalent pattern for vehicle telemetry.

## Testing

Navigation service unit tests cover command semantics, REQ/REP transport, and shared controller ownership. Messaging integration tests cover navigation telemetry through the broker.
