# Navigation Service

The navigation service is the single owner of the active navigation sensor pipeline. It publishes normalized navigation telemetry and accepts acknowledged navigation commands without requiring applications to know which IMU, GPS, or route-planning implementation is installed.

## Runtime ownership

```text
configured IMU + GPS sources
          |
NavigationController
          |
          +--> NavigationStatePublisher --> ZeroMQ telemetry bus
          |
          +--> NavigationCommandService <-- ZeroMQ REQ/REP clients
                                      |
                                      +--> RoutePlanningControllerIf
```

Applications should subscribe to public navigation topics for state and use command/request interfaces for acknowledged operations. They should not construct navigation hardware merely to display telemetry, request calibration, or calculate a route.

Route following is composed separately from raw sensor ownership:

```text
openroad.navigation.position
          |
RouteGuidanceRuntime
          |
RouteGuidanceController
          |
route_guidance.state
          |
NavigationSessionController
          |
ReroutePolicy
          |
NavigationCommandClient --> navigation.route.calculate
```

`NavigationSessionController` owns the active destination, travel mode, and route lifecycle. `RouteGuidanceController` owns route-relative geometry/state only. `ReroutePolicy` decides when a sustained off-route condition warrants recalculation; it does not call a route planner itself.

## Configuration

Navigation composition is selected through runtime TOML. There is no separate simulation code path in the service CLI.

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

Both configurations run the same controller and publication path. Only the concrete input sources change.

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

The telemetry publisher endpoint comes from `[messaging].publisher_endpoint`. The navigation command endpoint defaults to `tcp://127.0.0.1:5560` unless overridden in runtime configuration.

## Public telemetry

The service publishes one controller snapshot across the normalized navigation contracts:

- `openroad.navigation.position`
- `openroad.navigation.motion`
- `openroad.navigation.attitude`
- `openroad.navigation.imu`

Route following additionally publishes derived guidance state on:

- `route_guidance.state`

See `messaging/README.md`, `docs/messaging/message_bus_idd.md`, and `docs/idd/` for subscriber examples and wire-contract details.

## Commands

Commands use ZeroMQ REQ/REP rather than the PUB/SUB telemetry bus because callers need acknowledgement, result data, and error reporting.

Supported operations include:

- `navigation.calibrate_stationary`
- `navigation.reset_heading`
- `navigation.route.calculate`

`navigation.route.calculate` accepts an origin, destination, and travel mode and returns a `RouteResult` representation. `NavigationCommandClient.calculate_route()` is the normal programmatic client used by navigation-session rerouting.

Application code for calibration/heading operations should normally depend on the toolkit-independent `NavigationRequestHandlerIf`. Route/session orchestration should depend on a route-calculation callable or client rather than constructing the route planner directly.

The service executes commands against the same controller/service composition used for navigation ownership. This prevents UI processes from creating competing hardware or route-planning instances.

## Route guidance and rerouting

`RouteGuidanceController` projects geographic positions onto the active route and reports progress, remaining distance, maneuver state, arrival, and route deviation. It uses separate off-route and on-route thresholds to provide hysteresis and avoid state flapping from ordinary GPS noise.

`ReroutePolicy` adds time-domain policy above that state. By default, an off-route condition must persist before a reroute is requested, and a cooldown prevents repeated recalculation attempts.

When recalculation succeeds, `NavigationSessionController` installs the replacement `RouteResult` into `RouteGuidanceController` and can notify map/presentation composition through its route-changed callback.

## Shared consumer state

Applications that need a latest-value cache can use:

```python
from common.telemetry.navigation_bus_state import NavigationBusState
```

Register its setters with `MessageDispatcher`, then read `snapshot()` from the UI thread. `common.telemetry.vehicle_bus_state.VehicleBusState` provides the equivalent pattern for vehicle telemetry.

## Testing

Portable unit and component coverage includes route planning, route/map presentation, navigation messaging, route guidance, off-route hysteresis/recovery, navigation-session lifecycle, and simulated rerouting through the real ZeroMQ command boundary.

Some integration tests are intentionally platform/environment dependent. Tests involving the Python `gps` binding, real gpsd/GNSS input, a live Valhalla service, or the graphical MapLibre renderer belong on the Raspberry Pi or another host with those dependencies installed.
