# Application Architecture Audit

This audit tracks application-layer code against the OpenRoadCode split between command behavior and shared message-bus telemetry.

## Audit rule

Application code should generally use controller/request interfaces for commands and public messaging contracts for continuously changing shared telemetry. Direct hardware construction is appropriate in runtime composition, producer services, and deliberately named diagnostics, but not in ordinary telemetry displays once a public topic exists.

## Current status

### `apps/carTui`

**Migrated.** Vehicle and navigation screens consume the shared bus. CarTUI does not own OBD or navigation sensor telemetry hardware.

### `apps/webUi`

**Substantially bus-oriented.** WebUI uses shared vehicle/navigation contracts. Producer helpers such as the periodic position publisher are not consumer-side hardware ownership.

### `apps/carUi`

**Telemetry migration complete for vehicle gauges and off-road display.**

`CarUiComposition` subscribes to vehicle, attitude, IMU, position, and motion contracts and dispatches them onto the Tk thread. `VehicleGaugesScreen` and `OffroadDashboardScreen` are passive consumers. Car UI startup no longer constructs the MPU-6050 merely to feed the off-road display.

Calibration and heading reset remain modeled separately through `NavigationRequestHandlerIf`. They are intentionally not encoded as telemetry. The current Car UI factory leaves that handler unbound until the navigation producer/service has an explicit command endpoint; this is preferable to silently opening a second local IMU/controller that would mutate the wrong estimator.

Car UI still owns a position provider for shell location/status and other application behavior. That is a separate responsibility from dashboard navigation telemetry and should be reviewed independently if position ownership later moves entirely into a service.

### `apps/automotive_dashboard/main.py`

**Migrated.** The graphical vehicle dashboard consumes the vehicle-state bus.

### `apps/automotive_dashboard/vehicle_tui.py`

**Classified as a legacy direct-hardware diagnostic until migrated or retired.** It constructs ELM327 hardware and polls directly. It should not be used as the reference architecture for a normal UI consumer. The preferred user-facing terminal consumer is `apps/carTui`.

### `apps/automotive_dashboard/navigation_tui.py`

**Classified as a command-capable hardware diagnostic.** It intentionally owns MPU/GPS/controller state and exposes calibration/reset. Its displayed telemetry should eventually be migrated if the tool remains a first-class application; otherwise it should move under a diagnostic/component-test namespace.

### `apps/automotive_dashboard/navigation_visualizer.py`

**Classified as a command-capable hardware diagnostic pending migration.** Same rule as `navigation_tui`: direct ownership is acceptable only while the tool is explicitly treated as a diagnostic.

### `apps/automotive_dashboard/offroad_dashboard.py`

**Classified as a legacy standalone diagnostic pending migration/retirement.** The reusable panel itself remains valid; the standalone composition is not the reference architecture now that Car UI consumes navigation state from the bus.

## Command boundary

Telemetry answers "what is the system state?" Commands answer "please change system behavior." Calibration and relative-heading reset therefore stay behind `NavigationRequestHandlerIf`. A future navigation-service command client can implement that interface without changing the Tk panel or turning commands into state topics.

## Repeatable direct-import audit

Run:

```bash
venv/bin/python scripts/audit_app_hardware_imports.py
```

The script reports every direct `hardware_io` import under `apps/`. Each result must be justified as composition/producer/diagnostic code or removed from a telemetry consumer. This makes the audit repeatable instead of relying on somebody remembering which grep incantation was used six months ago.

## Remaining work

1. Add a real navigation-service command endpoint/client and bind it to `NavigationRequestHandlerIf` in Car UI.
2. Decide whether the three legacy standalone navigation/vehicle tools deserve migration or should physically move into component-test/diagnostic locations.
3. Run unit/integration tests after pulling this branch and fix stale tests that still assume Car UI constructs its own IMU navigation controller.
4. Run the hardware-import audit and review every surviving result.

## Important distinction

The target is not "no hardware imports under apps at any cost." Hardware must be constructed somewhere. The target is one clear owner for shared telemetry and many loosely coupled consumers, because letting every dashboard seize the same serial port or I2C device is less an architecture than a small territorial dispute.
