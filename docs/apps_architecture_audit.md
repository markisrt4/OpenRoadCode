# Application Architecture Audit

This audit tracks application-layer code against the current OpenRoadCode split between controller-driven commands and message-bus telemetry.

## Audit rule

Application code should generally use:

- controller interfaces for commands and behavior;
- public messaging contracts for continuously changing shared telemetry;
- frontend-specific presentation only above those boundaries.

Direct hardware construction in an application is acceptable for a deliberately standalone hardware diagnostic or producer, but it should not be the normal telemetry path for a user-facing consumer once a public topic exists.

## Current status

### `apps/carTui`

**Status: migrated.**

Vehicle and navigation screens consume the shared bus through `VehicleBusState` and `NavigationBusState`. Navigation consumes position, motion, attitude, and IMU contracts. CarTUI no longer owns the OBD or navigation sensor/controller telemetry stack.

### `apps/webUi`

**Status: substantially bus-oriented.**

WebUI contains dedicated `web_vehicle_ui_state.py` and `web_navigation_ui_state.py` state models and uses shared navigation/vehicle contracts. `periodic_position_publisher.py` is a producer-side helper rather than a consumer-side hardware dependency.

Continue to keep new vehicle/navigation UI state sourced from public contracts rather than adding controller polling back into request handlers.

### `apps/automotive_dashboard/main.py`

**Status: migrated.**

The graphical vehicle dashboard consumes `openroad.vehicle.state` through `MessageDispatcher` and correctly marshals worker-thread callbacks onto the Tk event loop.

### `apps/automotive_dashboard/vehicle_tui.py`

**Status: legacy direct telemetry consumer.**

This standalone TUI constructs `Elm327Device`, `Elm327ObdAdapter`, and `Obd2Manager`, then polls vehicle state directly. That duplicates producer ownership now represented by the vehicle-state bus.

Recommended direction: convert it to a bus subscriber or retire it in favor of `apps/carTui`. If retained as a direct ELM327 diagnostic, move/reframe it as a component-test tool rather than a normal application consumer.

### `apps/automotive_dashboard/navigation_tui.py`

**Status: mixed command and telemetry ownership.**

This standalone TUI directly constructs `Mpu6050Imu`, navigation adapters, GPS input, and `NavigationController`. Its telemetry display should eventually consume position/motion/attitude/IMU from the bus.

It also exposes calibration and heading-reset commands. Those are behavior requests, not telemetry, and should not be removed merely to force a bus-only design. Recommended direction:

1. migrate displayed state to bus contracts;
2. preserve calibration/reset behind an explicit command/controller boundary;
3. if no remote command mechanism exists yet, treat this tool as a hardware diagnostic rather than the reference application architecture.

### `apps/automotive_dashboard/navigation_visualizer.py`

**Status: requires migration review.**

The visualizer historically owns navigation-controller lifecycle and calibration/reset behavior. Displayed attitude should move toward the shared navigation contracts. Command controls require the same explicit command-path decision as `navigation_tui.py`.

### `apps/automotive_dashboard/offroad_dashboard.py`

**Status: requires migration review.**

The standalone off-road dashboard historically owns navigation telemetry while also issuing calibration/heading commands. Separate those concerns before migration: bus for state, command/controller path for behavior.

### `apps/carUi`

**Status: partially migrated; documentation is stale in places.**

The vehicle gauge screen now accepts `VehicleStateMessage` updates and is bus-driven. Existing CarUI README text still describes an optional `VehicleStateSourceIf` with screen-owned polling and should be updated.

The off-road/navigation path still deserves a focused review because its historical implementation starts navigation hardware while visible. It should converge on the same public position/motion/attitude/IMU contracts used by CarTUI, while calibration and heading-reset remain explicit commands.

## Priority order

1. **CarUI vehicle documentation cleanup** - code is already migrated; make the README truthful.
2. **CarUI off-road telemetry migration** - highest-value remaining user-facing direct navigation consumer.
3. **Standalone automotive dashboard classification** - either migrate legacy TUIs/visualizers to bus state or clearly move them into diagnostic/component-test roles.
4. **Command contracts** - define an explicit pattern for actions such as navigation calibration and heading reset before removing the final direct controller references from command-capable tools.
5. **Repeat import audit** - search `apps/` for direct `hardware_io` imports after migration and justify each surviving occurrence.

## Important distinction

A direct hardware import is not automatically wrong. Runtime composition, hardware producers, and diagnostics must construct concrete devices somewhere. The smell is a **telemetry display** owning the same hardware/controller pipeline that another application also wants to consume.

The target is not "no hardware imports under apps at any cost." The target is one clear owner for shared telemetry and many loosely coupled consumers.
