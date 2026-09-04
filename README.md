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

Current integration work includes the `orcUi` shell, native offline MapLibre presentation, Valhalla route planning, live Android-backed positioning on Termux, and an integrated SDR++ RF-radio frontend. SDR++ can be launched and embedded directly inside `orcUi` on X11, with ORC-owned radio profiles, presets, telemetry, RDS presentation, and SDR++ display controls layered around the native SDR application.

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

* Touchscreen automotive user interface, including the evolving `orcUi` shell
* Offline Valhalla route planning and native MapLibre map presentation
* Route overlays, camera follow/recenter, manual map panning, and live vehicle position
* Provider-independent positioning and navigation telemetry
* Android bridge geographic positioning for the Termux navigation service
* Message-bus-driven native map-renderer commands
* Focused map POI presentation for selected categories
* Integrated SDR++ RF radio embedded in `orcUi` on X11
* FM broadcast, NOAA weather, AM airband, HAM, and scanner-oriented radio profiles and presets
* SDR++ application controls for waterfall, band plan, FFT hold, auto range, and theme synchronization
* Read-only SDR++ signal/SNR telemetry and FM RDS presentation
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

The Radio entry screen separates RF Radio from Streaming Radio. RF Radio launches the integrated SDR++ path; Streaming Radio currently presents a Coming Soon screen while its provider/controller plumbing remains under development.

Not every feature is supported on every target. In particular, Android/Termux is a development and portability target and does not provide hardware parity with the Raspberry Pi installation.

---

## SDR++ RF Radio Integration

OpenRoadCode treats SDR++ as the native RF engine and spectrum/waterfall UI rather than reimplementing SDR functionality in Tkinter. On X11, `orcUi` launches SDR++, discovers its window, reparents it into the radio host, and keeps the embedded window sized to the ORC panel. The same path is exercised on native Debian/Linux and through Debian proot under Termux:X11.

Three localhost interfaces deliberately separate responsibilities:

| Port | Interface | Responsibility |
| --- | --- | --- |
| 4532 | SDR++ RigCTL | RF tuning, mode/bandwidth, receiver operations, and radio-specific data such as FM RDS |
| 4533 | ORC `remote_control` module | SDR++ UI/application controls such as waterfall, band plan, FFT hold, auto range, and theme |
| 4534 | ORC `telemetry` module | Read-only SNR, signal/FFT metrics, VFO, frequency, bandwidth, and display ranges |

Application-facing SDR behavior lives under `controllers/sdr`; wire protocols remain under `protocols`; SDR++ process lifecycle remains in `apps/launchers/sdrpp_launcher.py`; X11 window ownership is handled by `frontends/x11`; and `apps/orcUi` owns presentation. Telemetry is best-effort and must not prevent normal tuning or radio operation if port 4534 is unavailable.

The Debian setup script builds the ORC SDR++ modules and installs the X11 integration tools required by the embedded UI:

```bash
./development/debian/setup_sdrpp.sh
```

Termux uses the corresponding proot build/setup path:

```bash
./development/termux/setup_sdrpp.sh
```

See [`development/sdrpp/README.md`](development/sdrpp/README.md) and [`controllers/sdr/README.md`](controllers/sdr/README.md) for module and controller boundaries.

---

## Planned and Experimental Features

Potential future work includes streaming-radio station discovery, dashcam and backup-camera integration, additional vehicle gauges, CAN/TPMS integration, steering-wheel controls, APRS, AIS, additional digital radio modes, trip recording, richer semantic POI discovery, and custom OpenRoadCode operating-system images. These are areas of interest rather than release commitments.

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
orcUi / carUi / carTui / webUi / demos
```

Producer services own physical devices or simulation sources, domain processing, and publication lifecycle. Applications consume public telemetry instead of constructing competing GPS, IMU, or OBD-II instances merely to display state.

Map presentation follows the same separation. Navigation owns normalized position and route information, application-side map logic owns camera policy, and `MapRendererClient` publishes renderer commands through the message bus. The native MapLibre renderer therefore does not need to know whether a position originated from USB GNSS, Android, browser-based development input, or simulation.

Commands requiring acknowledgement or error reporting use request/reply messaging where appropriate. Public telemetry remains SI-normalized on the wire; presentation code performs unit conversion.

`orcUi`, `carUi`, `carTui`, and `webUi` are application front ends at different stages of development. Browser-backed utilities such as Weather, ADS-B, YouTube, and Google Earth are auxiliary applications managed according to application policy.

Messaging and service documentation:

* [Messaging overview and subscriber quick start](messaging/README.md)
* [Message Bus Interface Design Description](docs/messaging/message_bus_idd.md)
* [Ethernet Interface Design Description and port registry](docs/ethernet_idd.md)
* [Navigation producer service](services/navigation/README.md)
* [Automotive producer service](services/automotive/README.md)
* [SDR controllers](controllers/sdr/README.md)
* [SDR++ integration](development/sdrpp/README.md)
* [Car TUI telemetry consumer](apps/carTui/README.md)
* [Termux development target](development/termux/README.md)
* [Contributor architecture and testing rules](CONTRIBUTING.md)

---

## Configuration and Application Lifecycle

Runtime service composition is selected through `config/runtime.toml`. Producer inputs can select physical, Android-backed, or simulation implementations without changing downstream telemetry consumers.

User-facing auxiliary applications are configured separately:

* `config/applications.toml` contains the Raspberry Pi/Linux application profile.
* `config/applications.termux.toml` contains Termux presentation routing and platform-specific application behavior.
* `config/runtime.termux.toml` is an explicit Android sensor/navigation service profile.

Application startup policy is explicit:

* `lazy` starts an application when requested.
* `preload` warms application resources in the background without leaving the presentation visible.
* `persistent` keeps the application/runtime available while visibility is managed separately.

Browser-backed applications use independent Chromium app windows and profiles. Presentation targets and exclusive groups control where windows appear and which auxiliary applications may remain visible together.

ADS-B also separates presentation from data ownership. The Raspberry Pi/Linux profile uses `source = "rtlsdr"`; the Termux profile currently uses `source = "simulation"`. With the RTL-SDR source, `readsb` is started on demand by the ADS-B launcher and stopped when ADS-B releases the receiver.

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

Features can be selected explicitly. Use `--all-features` to install all compatible software capabilities, `--show-plan` to inspect the resolved plan without modifying the machine, and `--with-vnc` or `--with-gpsd-service` only when those services should be configured.

For the integrated SDR++ RF path on Debian/Linux, run `./development/debian/setup_sdrpp.sh`. It installs the SDR++ build dependencies, ORC's SDR++ modules, and the X11 utilities used for embedding. An X11 session is required for the current embedded-window implementation.

Concrete devices and credentials remain separate from package installation. Run `./scripts/installers/host_setup.sh --help` for current options.

### Android / Termux

Termux is an active development target rather than a complete Raspberry Pi replacement. It is used to exercise native Python services, ZeroMQ, Valhalla, MapLibre, Chromium/Termux:X11 presentation, Android sensor integration, SDR++ integration, and simulated ADS-B presentation.

The current navigation profile consumes geographic position from the localhost Android sensor bridge while retaining simulation fallbacks for platform-dependent sensor inputs. SDR++ runs inside the Debian proot and is presented through Termux:X11. Follow the [Termux development guide](development/termux/README.md) for the current native build, runit services, sensor bridge, navigation data, Valhalla, SDR++, and UI workflow.

---

## Running the ORC UI

From the repository root:

```bash
python -m apps.orcUi
```

The RADIO navigation item opens a source chooser. RF RADIO starts the SDR++ integration and embeds SDR++ into the ORC radio panel; STREAMING RADIO currently opens its Coming Soon page.

On Linux, the embedded SDR++ path requires an X11 session and the tools installed by `development/debian/setup_sdrpp.sh`. On Termux, start or verify Termux:X11 first and export the appropriate `DISPLAY` value. The Termux guide contains the current launch sequence and native map prerequisites.

The older `carUi` application remains in the repository while the ORC UI shell is integrated and matured.

---

## Development Without Hardware

Mocks, stubs, simulation producers, and unconfigured implementations allow developers to test application logic, presentation, dependency assembly, and failure handling without the complete vehicle hardware stack.

Component-test CLIs provide direct subsystem verification for navigation inputs, route planning and map presentation, OBD-II, SDR applications, rotary encoders, environmental sensors, Spotify/media, audio, and Bluetooth devices. Component tests may require hardware, permissions, services, or environment variables and supplement rather than replace automated tests.

---

## Automated Checks and Doxygen

Public methods declared in `*_if.py` modules must document every argument with `@param` and every non-`None` return value with `@return` or `@retval`.

Run the interface-contract checker and generate documentation with:

```bash
python scripts/check_doxygen_contracts.py
doxygen Doxyfile
```

Generated HTML documentation is written to `build/doxygen/html/index.html`; warnings are written to `build/doxygen-warnings.log` and are treated as errors by the project Doxyfile.

Before a pull request, also run the relevant unit/component tests for the changed subsystems. Native integration changes should be exercised on their target platform where practical, because Python can verify a contract but remains stubbornly unable to impersonate an Android graphics stack convincingly.

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

Read [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, architecture, testing conventions, hardware guidance, and the pull-request checklist.

---

## License

OpenRoadCode is licensed under the MIT License. See [LICENSE](LICENSE).
