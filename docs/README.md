# OpenRoadCode Documentation

This is the central entry point for OpenRoadCode documentation. Implementation-specific README files stay beside the code they describe. The complete catalog below is generated from those canonical files and the standalone guides, so it works directly in GitHub, local Markdown previews, and the documentation website.

The [project README](../README.md) remains the repository landing page. [Doxygen](../Doxyfile) builds the API reference.

## Architecture and design

- [System architecture](architecture.md)
- [Applications architecture audit](apps_architecture_audit.md)
- [ORC UI architecture](../apps/orcUi/ARCHITECTURE.md)
- [ORC media integration](../frontends/tk/media/README.md)
- [Ethernet interface design](ethernet_idd.md)
- [Android sensor pipeline](android_sensor_pipeline.md)
- [Navigation runtime](navigation_runtime.md)
- [Navigation deployment](navigation_deployment.md)
- [XDG path policy](xdg_paths.md)
- [Message bus interface design](messaging/message_bus_idd.md)
- [Automotive vehicle-state interface](idd/automotive_vehicle_state.md)
- [Environmental barometric-state interface](idd/environmental_barometric_state.md)
- [Navigation command-service interface](idd/navigation_command_service.md)
- [Navigation IMU-state interface](idd/navigation_imu_state.md)
- [Navigation magnetic-field interface](idd/navigation_magnetic_field_state.md)
- [Navigation position-state interface](idd/navigation_position_state.md)
- [Route-guidance interface](idd/route_guidance_state.md)

## Features and reference

- [Streaming Radio](streaming_radio.md)
- [Roadmap](roadmap.md)
- [Vehicle one-wire reference](vehicle-one-wire.pdf)
- [Security policy](../SECURITY.md)
- [Doxygen configuration](../Doxyfile)

<!-- BEGIN GENERATED DOCS INDEX -->

## Complete documentation catalog

Generated from the canonical documentation files. Every component README and standalone guide is listed here. Run `python scripts/docs_inventory.py --write` after adding or moving documentation.

### Apps

- [Automotive Dashboard (`apps/automotive_dashboard`)](../apps/automotive_dashboard/README.md)
- [Cartui (`apps/carTui`)](../apps/carTui/README.md)
- [Input (`apps/carUi/input`)](../apps/carUi/input/README.md)
- [Carui (`apps/carUi`)](../apps/carUi/README.md)
- [Runtime (`apps/carUi/runtime`)](../apps/carUi/runtime/README.md)
- [Automotive (`apps/demos/automotive`)](../apps/demos/automotive/README.md)
- [Launchers (`apps/launchers`)](../apps/launchers/README.md)
- [Map Renderer (`apps/map_renderer`)](../apps/map_renderer/README.md)
- [Architecture (`apps/orcUi`)](../apps/orcUi/ARCHITECTURE.md)
- [Weatherdash (`apps/weatherDash`)](../apps/weatherDash/README.md)
- [Webui (`apps/webUi`)](../apps/webUi/README.md)

### Config

- [Config](../config/README.md)

### Controllers

- [Audio (`controllers/audio`)](../controllers/audio/README.md)
- [Obd2 (`controllers/automotive/obd2`)](../controllers/automotive/obd2/README.md)
- [Automotive (`controllers/automotive`)](../controllers/automotive/README.md)
- [Cache (`controllers/cache`)](../controllers/cache/README.md)
- [Environmental (`controllers/environmental`)](../controllers/environmental/README.md)
- [Image (`controllers/image`)](../controllers/image/README.md)
- [Input (`controllers/input`)](../controllers/input/README.md)
- [Lighting (`controllers/lighting`)](../controllers/lighting/README.md)
- [Navigation (`controllers/navigation`)](../controllers/navigation/README.md)
- [Radio (`controllers/radio`)](../controllers/radio/README.md)
- [Route Planning (`controllers/route_planning`)](../controllers/route_planning/README.md)
- [Sdr (`controllers/sdr`)](../controllers/sdr/README.md)
- [Spotify (`controllers/spotify`)](../controllers/spotify/README.md)
- [Streaming Radio (`controllers/streaming_radio`)](../controllers/streaming_radio/README.md)
- [Video (`controllers/video`)](../controllers/video/README.md)
- [Weather (`controllers/weather`)](../controllers/weather/README.md)

### Development

- [Maplibre (`development/containers/maplibre`)](../development/containers/maplibre/README.md)
- [Scripts (`development/containers/maplibre/scripts`)](../development/containers/maplibre/scripts/README.md)
- [Sdrpp (`development/sdrpp`)](../development/sdrpp/README.md)
- [Remote Control (`development/sdrpp/remote_control`)](../development/sdrpp/remote_control/README.md)
- [Telemetry (`development/sdrpp/telemetry`)](../development/sdrpp/telemetry/README.md)
- [Termux (`development/termux`)](../development/termux/README.md)

### Docs

- [Android Sensor Pipeline](android_sensor_pipeline.md)
- [Apps Architecture Audit](apps_architecture_audit.md)
- [Architecture](architecture.md)
- [Ethernet Idd](ethernet_idd.md)
- [Automotive Vehicle State (`docs/idd`)](idd/automotive_vehicle_state.md)
- [Environmental Barometric State (`docs/idd`)](idd/environmental_barometric_state.md)
- [Navigation Command Service (`docs/idd`)](idd/navigation_command_service.md)
- [Navigation Imu State (`docs/idd`)](idd/navigation_imu_state.md)
- [Navigation Magnetic Field State (`docs/idd`)](idd/navigation_magnetic_field_state.md)
- [Navigation Position State (`docs/idd`)](idd/navigation_position_state.md)
- [Route Guidance State (`docs/idd`)](idd/route_guidance_state.md)
- [Message Bus Idd (`docs/messaging`)](messaging/message_bus_idd.md)
- [Navigation Deployment](navigation_deployment.md)
- [Navigation Runtime](navigation_runtime.md)
- [Roadmap](roadmap.md)
- [Streaming Radio](streaming_radio.md)
- [Xdg Paths](xdg_paths.md)

### Frontends

- [Frontends](../frontends/README.md)
- [Automotive (`frontends/tk/automotive`)](../frontends/tk/automotive/README.md)
- [Media (`frontends/tk/media`)](../frontends/tk/media/README.md)
- [Tui (`frontends/tui`)](../frontends/tui/README.md)

### Hardware Io

- [Android (`hardware_io/android`)](../hardware_io/android/README.md)
- [Elm327 (`hardware_io/automotive/elm327`)](../hardware_io/automotive/elm327/README.md)
- [Automotive (`hardware_io/automotive`)](../hardware_io/automotive/README.md)
- [Bluetooth (`hardware_io/bluetooth`)](../hardware_io/bluetooth/README.md)
- [Environmental (`hardware_io/environmental`)](../hardware_io/environmental/README.md)
- [Gpio (`hardware_io/gpio`)](../hardware_io/gpio/README.md)
- [Gps (`hardware_io/gps`)](../hardware_io/gps/README.md)
- [Imu (`hardware_io/imu`)](../hardware_io/imu/README.md)
- [Keyboard (`hardware_io/keyboard`)](../hardware_io/keyboard/README.md)
- [Potentiometer (`hardware_io/potentiometer`)](../hardware_io/potentiometer/README.md)
- [Rotary Encoder (`hardware_io/rotary_encoder`)](../hardware_io/rotary_encoder/README.md)

### Input Events

- [Input Events](../input_events/README.md)

### Messaging

- [Messaging](../messaging/README.md)

### Project

- [Contributing](../CONTRIBUTING.md)
- [Project](../README.md)

### Protocols

- [Can (`protocols/can`)](../protocols/can/README.md)
- [Map Renderer (`protocols/map_renderer`)](../protocols/map_renderer/README.md)
- [Oauth (`protocols/oauth`)](../protocols/oauth/README.md)
- [Obd2 (`protocols/obd2`)](../protocols/obd2/README.md)
- [Rigctl (`protocols/rigctl`)](../protocols/rigctl/README.md)
- [Sdrpp Telemetry (`protocols/sdrpp_telemetry`)](../protocols/sdrpp_telemetry/README.md)
- [Spotify (`protocols/spotify`)](../protocols/spotify/README.md)

### Scripts

- [Runit (`scripts/runit`)](../scripts/runit/README.md)
- [Termux (`scripts/termux`)](../scripts/termux/README.md)

### Services

- [Automotive (`services/automotive`)](../services/automotive/README.md)
- [Navigation (`services/navigation`)](../services/navigation/README.md)

### Tools

- [Map Builder (`tools/map_builder`)](../tools/map_builder/README.md)

### Ui

- [Component Test (`ui/component_test`)](../ui/component_test/README.md)
- [Ui](../ui/README.md)

<!-- END GENERATED DOCS INDEX -->

## Documentation conventions

Keep implementation-specific instructions in the owning component's README. Put cross-cutting architecture, interface, deployment, and user guides under `docs/`. Link to canonical files instead of duplicating them. After adding, moving, or removing documentation, run `python scripts/docs_inventory.py --write` and commit the updated index. CI checks that the catalog is current. The website uses the same discovery inventory, while retaining ownership of its layout, navigation, and deployment.
