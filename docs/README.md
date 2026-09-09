# OpenRoadCode Documentation

This directory is the central entry point for OpenRoadCode documentation. Implementation-specific README files stay beside the code they describe; this page provides the curated map across the repository rather than copying or symlinking them.

The [project README](../README.md) remains the repository landing page. [Doxygen](../Doxyfile) builds the API/reference documentation, while the public website imports repository README files into its documentation tree.

## Architecture and design

- [System architecture](architecture.md)
- [Applications architecture audit](apps_architecture_audit.md)
- [ORC UI architecture](../apps/orcUi/ARCHITECTURE.md)
- [ORC media integration](../apps/orcUi/MEDIA.md)
- [Ethernet interface design](ethernet_idd.md)
- [Android sensor pipeline](android_sensor_pipeline.md)
- [Navigation runtime](navigation_runtime.md)
- [Navigation deployment](navigation_deployment.md)
- [Message bus interface design](messaging/message_bus_idd.md)
- [Automotive vehicle-state interface](idd/automotive_vehicle_state.md)
- [Environmental barometric-state interface](idd/environmental_barometric_state.md)
- [Navigation command-service interface](idd/navigation_command_service.md)
- [Navigation IMU-state interface](idd/navigation_imu_state.md)
- [Navigation magnetic-field interface](idd/navigation_magnetic_field_state.md)
- [Navigation position-state interface](idd/navigation_position_state.md)
- [Route-guidance interface](idd/route_guidance_state.md)

## Applications

Application documentation covers the graphical, terminal, browser, rendering, launcher, demo, and dashboard surfaces. The ORC UI architecture and media guides above document the current runtime composition and ownership model introduced by the runtime-integration cleanup.

- [Car UI](../apps/carUi/README.md)
- [Car UI input](../apps/carUi/input/README.md)
- [Car UI runtime](../apps/carUi/runtime/README.md)
- [Car TUI](../apps/carTui/README.md)
- [Web UI](../apps/webUi/README.md)
- [Weather dashboard](../apps/weatherDash/README.md)
- [Map renderer](../apps/map_renderer/README.md)
- [Application launchers](../apps/launchers/README.md)
- [Automotive dashboard](../apps/automotive_dashboard/README.md)
- [Automotive demos](../apps/demos/automotive/README.md)

## Core subsystems

These directories contain the bulk of the component-level documentation. Their README files are kept with their implementations and are recursively published by the documentation website.

- [Controllers](../controllers/) — audio, automotive/OBD-II, input, radio, SDR, navigation, rendering, application runtime, games, media, and related control layers
- [Hardware I/O](../hardware_io/) — GPS, IMU, GPIO, Bluetooth, and other hardware adapters
- [Protocols](../protocols/) — CAN, OBD-II, OAuth, map rendering, rig control, Spotify, and related protocol models
- [Services](../services/) — [automotive](../services/automotive/README.md) and [navigation](../services/navigation/README.md)
- [Messaging](../messaging/README.md) — transport-independent messaging contracts, dispatch, and ZeroMQ transport
- [Configuration](../config/README.md) — shared runtime configuration and profiles
- [UI contracts](../ui/README.md) — toolkit-independent presentation contracts
- [UI component-test guide](../ui/component_test/README.md) — component-test documentation
- [Input events](../input_events/README.md) — normalized physical-input contracts
- [Frontends](../frontends/README.md) — concrete presentation implementations, including [terminal frontends](../frontends/tui/README.md) and [Tk automotive frontend](../frontends/tk/automotive/README.md)

## Development, deployment, and tooling

Development documentation is also kept beside the tools and platform targets it describes.

- [Termux development target](../development/termux/README.md)
- [SDR++ development](../development/sdrpp/README.md)
- [SDR++ remote control](../development/sdrpp/remote_control/README.md)
- [SDR++ telemetry](../development/sdrpp/telemetry/README.md)
- [MapLibre development container](../development/containers/maplibre/README.md)
- [MapLibre container scripts](../development/containers/maplibre/scripts/README.md)
- [runit services](../scripts/runit/README.md)
- [Termux scripts](../scripts/termux/README.md)
- [Map builder](../tools/map_builder/README.md)
- [XDG paths](xdg_paths.md)
- [Contributing](../CONTRIBUTING.md)

## Features and reference

- [Roadmap](roadmap.md)
- [Vehicle one-wire reference](vehicle-one-wire.pdf)
- [Security policy](../SECURITY.md)
- [Doxygen configuration](../Doxyfile)

Streaming Radio is currently represented in the application as a Coming Soon surface while its provider/controller plumbing is under development. The former implementation guide was removed during runtime cleanup, so it is intentionally not linked here as active architecture documentation.

## Documentation coverage

The public website recursively imports component README files, while this page provides a curated human entry point. Counts are deliberately not hard-coded here because the repository is changing quickly; the generated documentation tree is the authoritative exhaustive inventory.

Top-level areas without their own README are still represented where appropriate by API/reference generation or by cross-cutting documentation under `docs/`.

## Documentation conventions

Keep implementation-specific instructions in the owning component's README. Put cross-cutting architecture, interface, deployment, and user guides under `docs/`. Link to canonical files instead of duplicating them. When adding a new component README or standalone architecture guide, ensure the public documentation importer and Doxygen inputs still cover it, and add it here when it represents a new documentation area or important entry point.
