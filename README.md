# OpenRoadCode

> An open-source automotive computing, software-defined radio, vehicle telemetry, and embedded experimentation platform.

OpenRoadCode is a modular in-vehicle computing platform designed primarily for Raspberry Pi and Linux-based embedded systems. Android/Termux is also used as an active portability and development target.

It combines software-defined radio, offline navigation, positioning, vehicle telemetry, media controls, environmental sensors, physical controls, and touchscreen interfaces into one extensible platform.

The project is intended for developers, makers, radio enthusiasts, and embedded Linux engineers who want a vehicle computing system they can inspect, modify, extend, and fully control.

OpenRoadCode does not replace factory safety or vehicle-control systems. It complements them with an independent platform for experimentation, visualization, communications, entertainment, and custom applications.

Explore the project at [openroadcode.org](https://www.openroadcode.org/) or visit the [OpenRoadCode repository](https://github.com/markisrt4/OpenRoadCode).

---

## Project Status

OpenRoadCode is under active development and currently operates as an advanced experimental platform rather than a finished commercial infotainment system.

Some components are functional and actively used in the reference vehicle. Others are experimental, hardware-dependent, or still being integrated. Interfaces, configuration formats, and directory structures may continue to evolve before the first stable release.

---

## Project Goals

OpenRoadCode is designed to:

* Provide an open and customizable automotive computing platform
* Support multiple hardware implementations through reusable interfaces
* Keep hardware-specific code isolated from application logic
* Allow applications and controllers to be tested without physical hardware
* Support Raspberry Pi and Linux development systems while exercising portability through Android/Termux
* Encourage experimentation with radio, navigation, vehicle telemetry, sensors, and embedded Linux
* Provide educational examples of modular Python and embedded-system architecture
* Avoid unnecessary dependence on cloud services

---

## Current Capabilities

Current and partially integrated capabilities include:

* Touchscreen automotive user interface
* Offline Valhalla route planning and MapLibre map presentation
* Provider-independent positioning and navigation telemetry
* FM broadcast radio, AM airband, NOAA weather radio, and multi-band scanning
* RTL-SDR integration with shared receiver ownership
* ADS-B aircraft tracking through readsb and tar1090
* Bluetooth OBD-II communication and vehicle telemetry
* Bluetooth cabin-lighting control
* Spotify integration, artwork, lyrics, and music-video lookup/playback
* YouTube and Netflix media launchers
* PipeWire audio control
* Rotary encoder, keyboard, and GPIO pushbutton input
* Environmental, barometric, IMU, and vehicle-orientation sensing
* Configurable browser application lifecycle and presentation targets
* Configurable startup and splash-screen behavior
* Mock, stub, and simulation implementations for development without hardware

Not every feature is supported on every target. In particular, Android/Termux is a development and portability target and does not provide hardware parity with the Raspberry Pi installation.

---

## Planned and Experimental Features

Potential future work includes dashcam and backup-camera integration, additional vehicle gauges, CAN/TPMS integration, steering-wheel controls, APRS, AIS, additional digital radio modes, trip recording, and custom OpenRoadCode operating-system images. These are areas of interest rather than release commitments.

---

## Reference Hardware

The current reference system is based primarily on:

| Component                    | Purpose                              |
| ---------------------------- | ------------------------------------ |
| Raspberry Pi 5               | Primary embedded computer            |
| Raspberry Pi 4               | Secondary and development target     |
| Raspberry Pi Touch Display 2 | Primary touchscreen                  |
| RTL-SDR receivers            | Radio and ADS-B reception            |
| USB GNSS receiver            | Position and time data               |
| Bluetooth OBD-II adapter     | Vehicle telemetry                    |
| Bluetooth LED controller     | Cabin-lighting control               |
| Rotary encoders              | Physical user input                  |
| GPIO pushbuttons             | Physical controls and shutdown input |
| Environmental / IMU sensors  | Environmental and motion data        |
| USB audio hardware           | Audio input and output               |
| Ethernet travel router       | Local in-vehicle network             |
| Linux workstation or VM      | Development environment              |
| Android / Termux device      | Portability and integration testing  |

Hardware compatibility varies by platform, Linux distribution, kernel, device permissions, and available drivers.

---

## Software Architecture

OpenRoadCode separates applications, application-facing controllers, domain services, messaging, protocols, and hardware-specific implementations.

```text
OpenRoadCode/
├── apps/                 main applications and application launchers
├── services/             long-lived domain producers such as navigation
├── messaging/            public contracts and ZeroMQ transport
├── controllers/          application-facing behavior
├── hardware_io/          physical and platform-specific adapters
├── protocols/            device and external-service protocols
├── common/               shared telemetry and units
├── frontends/ and ui/    presentation implementations
├── input_events/         cross-layer physical input contracts
├── config/               runtime and application policy
└── scripts/              installation and service integration
```

Continuously changing public telemetry is distributed through producer services and the ZeroMQ message bus:

```text
Hardware / simulation
        │
        ▼
Domain producer service
        │
        ▼
SI-normalized public contracts
        │
        ▼
ZeroMQ XSUB/XPUB broker
        │
        ▼
Shared application telemetry state
        │
        ▼
carUi / carTui / webUi / demos
```

Producer services own physical devices or simulation sources, domain processing, and publication lifecycle. Applications consume public telemetry instead of constructing competing GPS, IMU, or OBD-II instances merely to display state.

Commands requiring acknowledgement or error reporting use request/reply messaging where appropriate. Public telemetry remains SI-normalized on the wire; presentation code performs unit conversion.

`carUi`, `carTui`, and `webUi` are peer applications. Browser-backed utilities such as Weather, ADS-B, YouTube, and Google Earth are auxiliary applications managed by CarUi according to application policy. A top-level application is not preloaded merely because it happens to use a browser.

Messaging and service documentation:

* [Messaging overview and subscriber quick start](https://github.com/markisrt4/OpenRoadCode/blob/master/messaging/README.md)
* [Message Bus Interface Design Description](https://github.com/markisrt4/OpenRoadCode/blob/master/docs/messaging/message_bus_idd.md)
* [Navigation producer service](https://github.com/markisrt4/OpenRoadCode/blob/master/services/navigation/README.md)
* [Automotive producer service](https://github.com/markisrt4/OpenRoadCode/blob/master/services/automotive/README.md)
* [Car TUI telemetry consumer](https://github.com/markisrt4/OpenRoadCode/blob/master/apps/carTui/README.md)
* [Termux development target](https://github.com/markisrt4/OpenRoadCode/blob/master/development/termux/README.md)
* [Contributor architecture and testing rules](https://github.com/markisrt4/OpenRoadCode/blob/master/CONTRIBUTING.md)

---

## Configuration and Application Lifecycle

Runtime service composition is selected through `config/runtime.toml`. Producer inputs can select physical, browser-backed, Android-backed, or simulation implementations without changing downstream telemetry consumers.

User-facing auxiliary applications are configured separately:

* `config/applications.toml` contains the Raspberry Pi/Linux application profile.
* `config/applications.termux.toml` contains Termux presentation routing and platform-specific application behavior.
* `config/runtime.termux.toml` is an explicit Android sensor/navigation service profile. CarUi does not select it automatically.

Application startup policy is explicit:

* `lazy` starts an application when requested.
* `preload` warms application resources in the background without leaving the presentation visible.
* `persistent` keeps the application/runtime available while visibility is managed separately.

Browser-backed applications use independent Chromium app windows and profiles. Presentation targets and exclusive groups control where windows appear and which auxiliary applications may remain visible together.

ADS-B also separates presentation from data ownership. The Raspberry Pi/Linux profile uses `source = "rtlsdr"`; the Termux profile currently uses `source = "simulation"`. With the RTL-SDR source, `readsb` is started on demand by the ADS-B launcher and stopped when ADS-B releases the receiver. It is deliberately not a permanently enabled system service because the receiver is shared with other SDR applications.

Do not commit credentials, API keys, OAuth tokens, browser state, or runtime service state such as runit `supervise/` directories.

---

## Installation

Raspberry Pi OS and Debian/Ubuntu hosts use the target-aware installer. Review it before running it on an existing system because it may install packages, configure services, and create a Python environment.

```bash
git clone https://github.com/markisrt4/OpenRoadCode.git
cd OpenRoadCode

./scripts/installers/host_setup.sh --target rpi4
./scripts/installers/host_setup.sh --target rpi5
./scripts/installers/host_setup.sh --target linux-dev
```

Features can be selected explicitly, for example:

```bash
./scripts/installers/host_setup.sh --target rpi5 \
  --feature desktop-ui \
  --feature input \
  --feature gps \
  --feature bluetooth \
  --feature automotive \
  --feature adsb
```

Use `--all-features` to install all compatible software capabilities, `--show-plan` to inspect the resolved plan without modifying the machine, and `--with-vnc` or `--with-gpsd-service` only when those services should be configured.

Concrete devices and credentials remain separate from package installation. Run `./scripts/installers/host_setup.sh --help` for current options.

### Android / Termux

Termux is an active development target rather than a complete Raspberry Pi replacement. It is used to exercise native Python services, ZeroMQ, Valhalla, MapLibre, Chromium/Termux:X11 presentation, Android sensor integration, and simulated ADS-B presentation.

Follow the [Termux development guide](https://github.com/markisrt4/OpenRoadCode/blob/master/development/termux/README.md) for the current native build, runit services, sensor bridge, navigation data, tar1090, and CarUi launch workflow.

---

## Running CarUi

From the repository root on a normal Linux/Raspberry Pi installation:

```bash
CARUI_GEOMETRY=1024x600 \
CARUI_FULLSCREEN=0 \
venv/bin/python -m apps.carUi.main
```

Termux normally uses X11 display `:1` and disables the splash by default because of Android/Termux Tcl/Tk interpreter teardown behavior. The Termux guide contains the complete launch sequence.

Useful overrides include `CARUI_GEOMETRY`, `CARUI_FULLSCREEN`, `CARUI_SPLASH`, `CARUI_MEDIA_DISPLAY`, `OPENROAD_RUNTIME_CONFIG`, `OPENROAD_APPLICATIONS_CONFIG`, and `OPENROAD_RUNTIME_TARGET`.

---

## Development Without Hardware

Mocks, stubs, simulation producers, and unconfigured implementations allow developers to test application logic, presentation, dependency assembly, and failure handling without the complete vehicle hardware stack.

Component-test CLIs provide direct subsystem verification for navigation inputs, OBD-II, SDR applications, rotary encoders, environmental sensors, Spotify/media, audio, and Bluetooth devices. Component tests may require hardware, permissions, services, or environment variables and supplement rather than replace automated tests.

---

## Automated Checks and Doxygen

Public methods declared in `*_if.py` modules must document every argument with `@param` and every non-`None` return value with `@return` or `@retval`.

Run the interface-contract checker and generate documentation with:

```bash
python scripts/check_doxygen_contracts.py
doxygen Doxyfile
```

Generated HTML documentation is written to:

```text
build/doxygen/html/index.html
```

Doxygen warnings are written to:

```text
build/doxygen-warnings.log
```

Unit tests use Python's `unittest` framework. Focused subsystem tests live alongside their implementation packages; component tests are used where real hardware or platform services are required.

---

## Coding Guidelines

General project conventions include:

* Use `snake_case` for Python modules, methods, functions, and variables.
* Use clear interface names ending in `If`.
* Prefer dependency injection over global state.
* Keep hardware-specific behavior in `hardware_io`.
* Keep protocol parsing in `protocols`.
* Keep application-facing behavior in `controllers`.
* Keep long-lived producer ownership in `services`.
* Avoid importing application modules from lower-level packages.
* Provide type annotations and Doxygen contracts for public interfaces.
* Keep configuration outside application logic.
* Handle unavailable hardware as a normal runtime condition.
* Add mocks/stubs where they create a useful test seam.
* Avoid abstractions that do not provide a real boundary or interchangeable implementation.

---

## Supported Platforms

Primary targets are:

* Raspberry Pi OS on Raspberry Pi 4 and Raspberry Pi 5
* Debian-based ARM64 systems
* Debian/Ubuntu AMD64 development systems
* Android/Termux as an active development and portability target

Termux support is intentionally partial. Hardware-specific Linux integrations such as GPIO, some audio paths, and direct RTL-SDR ownership may differ or be unavailable. Termux:X11 provides the graphical environment used by the current Android workflow.

---

## Safety

OpenRoadCode is an experimental hobbyist and educational platform. It must not be relied upon for steering, braking, throttle, airbags, stability control, or other safety-critical vehicle functions.

Do not interact with the system while driving unless the interaction is legal, safe, and designed to minimize distraction. Radio operation must comply with applicable laws and regulations. Vehicle wiring, power integration, CAN access, GPIO connections, and external hardware modifications should be performed carefully.

---

## Contributing

Contributions are welcome, particularly in automated tests, documentation, hardware adapters, configuration validation, installation, accessibility, radio applications, vehicle telemetry, embedded Linux support, failure handling, and platform portability.

Before a major architectural change, describe the problem, proposed design, affected layers, platform dependencies, and testing implications. Changes should preserve the separation between applications, controllers, services, messaging, protocols, and hardware-specific code.

Read [CONTRIBUTING.md](https://github.com/markisrt4/OpenRoadCode/blob/master/CONTRIBUTING.md) for development setup, architecture, testing conventions, hardware guidance, and the pull-request checklist.

---

## License

OpenRoadCode is licensed under the MIT License. See [LICENSE](https://github.com/markisrt4/OpenRoadCode/blob/master/LICENSE).
