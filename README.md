# OpenRoadCode

> An open-source automotive computing, software-defined radio, vehicle telemetry, and embedded experimentation platform.

OpenRoadCode is a modular in-vehicle computing platform designed for Raspberry Pi and Linux-based embedded systems.

It combines software-defined radio, GPS, vehicle telemetry, media controls, environmental sensors, physical controls, and a touchscreen interface into one extensible platform.

The project is intended for developers, makers, radio enthusiasts, and embedded Linux engineers who want a vehicle computing system they can inspect, modify, extend, and fully control.

OpenRoadCode does not replace factory safety or vehicle-control systems. It complements them with an independent platform for experimentation, visualization, communications, entertainment, and custom applications.

---

## Project Status

OpenRoadCode is under active development.

The project currently operates as an advanced experimental platform rather than a finished commercial infotainment system.

Some components are functional and actively used in the reference vehicle. Others are experimental, hardware-dependent, or still being integrated.

Interfaces, configuration formats, and directory structures may continue to evolve before the first stable release.

---

## Project Goals

OpenRoadCode is designed around several core goals:

* Provide an open and customizable automotive computing platform
* Support multiple hardware implementations through reusable interfaces
* Keep hardware-specific code isolated from application logic
* Allow applications and controllers to be tested without physical hardware
* Support Raspberry Pi and other Linux-based embedded computers
* Encourage experimentation with radio, vehicle telemetry, sensors, and embedded Linux
* Provide educational examples of modular Python and embedded-system architecture
* Avoid unnecessary dependence on cloud services

---

## Current Capabilities

Current and partially integrated capabilities include:

* Touchscreen automotive user interface
* FM broadcast radio
* AM airband reception
* NOAA weather radio
* Multi-band radio scanning
* RTL-SDR integration
* ADS-B aircraft tracking
* GPS positioning through GPSD
* Bluetooth OBD-II communication
* Vehicle telemetry and gauge support
* Bluetooth cabin-lighting control
* Spotify integration
* Music-video lookup and playback
* PipeWire audio control
* Rotary encoder input
* Keyboard input
* GPIO pushbuttons
* Environmental sensing
* Barometric pressure sensing
* IMU and vehicle-orientation experiments
* Remote display through VNC
* Configurable startup and splash-screen behavior
* Mock and stub controllers for development without hardware

Not every feature is supported on every hardware configuration.

---

## Planned and Experimental Features

Potential future work includes:

* Offline navigation
* Downloadable maps
* Dashcam support
* Backup-camera integration
* Additional vehicle gauges
* CAN bus monitoring
* TPMS integration
* Steering-wheel control integration
* APRS
* AIS reception
* Digital radio modes
* Additional SDR applications
* Trip recording and telemetry history
* Plugin-style application discovery
* Additional embedded Linux targets
* Custom OpenRoadCode operating-system images

These items represent areas of interest rather than release commitments.

---

## Reference Hardware

The current reference system is based primarily on:

| Component                    | Purpose                              |
| ---------------------------- | ------------------------------------ |
| Raspberry Pi 5               | Primary embedded computer            |
| Raspberry Pi 4               | Secondary and development target     |
| Raspberry Pi Touch Display 2 | Primary touchscreen                  |
| RTL-SDR receivers            | Radio reception                      |
| USB GPS receiver             | Position and time data               |
| Bluetooth OBD-II adapter     | Vehicle telemetry                    |
| Bluetooth LED controller     | Cabin-lighting control               |
| Rotary encoders              | Physical user input                  |
| GPIO pushbuttons             | Physical controls and shutdown input |
| Environmental sensors        | Temperature and barometric data      |
| IMU sensors                  | Pitch, roll, and motion data         |
| USB audio hardware           | Audio input and output               |
| Ethernet travel router       | Local in-vehicle network             |
| Linux workstation or VM      | Development environment              |

OpenRoadCode is designed to support additional hardware through adapter and controller interfaces.

Hardware compatibility varies by Linux distribution, kernel, device permissions, and available drivers.

---

## Software Architecture

OpenRoadCode separates application logic from hardware-specific implementations.

The primary repository areas are:

```text
OpenRoadCode/
├── apps/
│   ├── carUi/
│   └── other applications
│
├── controllers/
│   ├── audio/
│   ├── environmental/
│   ├── image/
│   ├── lighting/
│   ├── navigation/
│   ├── radio/
│   ├── spotify/
│   └── other application-facing controllers
│
├── hardware_io/
│   ├── automotive/
│   ├── bluetooth/
│   ├── environmental/
│   ├── gpio/
│   ├── gps/
│   ├── imu/
│   ├── keyboard/
│   ├── pushbutton/
│   ├── rotary_encoder/
│   └── other hardware adapters
│
├── protocols/
│   ├── oauth/
│   ├── obd2/
│   ├── rigctl/
│   ├── spotify/
│   └── other protocol implementations
│
├── config/
├── scripts/
└── tests and component-test utilities
```

The intended dependency direction is:

```text
Applications and UI
        │
        ▼
Controller interfaces
        │
        ▼
Concrete controllers
        │
        ▼
Hardware adapters and protocols
        │
        ▼
Linux devices, services, and external hardware
```

Higher-level application modules should not depend directly on hardware-specific implementations.

---

## Controllers

Controllers expose application-facing behavior.

Examples include:

* Radio control
* Audio control
* Spotify playback
* Navigation
* Lighting
* Environmental data
* Vehicle information

A controller may have several implementations:

```text
AudioControllerIf
├── PipeWireAudioController
├── AudioControllerStub
└── UnconfiguredAudioController
```

This pattern allows the application to run with:

* Real hardware
* Mock data
* Stub implementations
* Unsupported or unconfigured features

Controllers should avoid exposing unnecessary implementation details to the user interface.

---

## Hardware Adapters

Hardware adapters isolate device-specific behavior.

Examples include:

* USB GPS receivers
* Bluetooth OBD-II devices
* Raspberry Pi GPIO
* I2C rotary encoders
* Environmental sensors
* IMUs
* Pushbuttons
* Linux keyboard input

Application code should interact with interfaces and domain objects rather than directly accessing device files, GPIO libraries, serial ports, or Bluetooth libraries.

This makes it easier to support additional implementations without rewriting higher-level code.

---

## Protocol Modules

Protocol modules implement communication formats independently of the user interface.

Examples include:

* OBD-II and ELM327 commands
* Spotify Web API requests
* OAuth authorization
* `rigctl` radio control
* Bluetooth lighting protocols

Protocol code should not contain user-interface behavior.

---

## Configuration

OpenRoadCode uses configuration files for hardware selection, radio profiles, device settings, runtime behavior, and application options.

Configuration files are stored primarily under:

```text
config/
```

The goal is to avoid hard-coding:

* Device addresses
* Bluetooth UUIDs
* Serial-device paths
* Radio frequencies
* Scanner ranges
* Runtime implementations
* Application-specific hardware selections

Example configurations should be copied and customized rather than edited in place when possible.

Do not commit credentials, API keys, OAuth tokens, or other secrets to the repository.

---

## Installation

Installation support is still evolving.

The repository contains installer and setup utilities under:

```text
scripts/
scripts/installers/
```

Platform-specific scripts are available for supported ARM64 and AMD64 development environments.

Review an installer before running it, particularly on an existing workstation. The scripts may install system packages, configure services, create Python environments, and modify user-level Linux configuration.

A typical development setup begins with:

```bash
git clone https://github.com/markisrt4/OpenRoadCode.git
cd OpenRoadCode
```

Then use the appropriate installer from `scripts/installers/` for the target platform.

After installation, activate the Python environment if the installer created one:

```bash
source venv/bin/activate
```

The exact installation flow may change while the installer scripts are consolidated.

---

## Running the Car UI

From the repository root:

```bash
CARUI_GEOMETRY=1024x600 \
CARUI_FULLSCREEN=0 \
venv/bin/python -m apps.carUi.main
```

For fullscreen operation:

```bash
CARUI_FULLSCREEN=1 \
venv/bin/python -m apps.carUi.main
```

Environment variables currently used by the application include:

| Variable                  | Purpose                               |
| ------------------------- | ------------------------------------- |
| `CARUI_GEOMETRY`          | Window size in `WIDTHxHEIGHT` format  |
| `CARUI_FULLSCREEN`        | Enable or disable fullscreen mode     |
| `CARUI_SPLASH`            | Enable or disable the startup splash  |
| `CARUI_SPLASH_FADE_MS`    | Splash fade duration                  |
| `CARUI_SPLASH_HOLD_MS`    | Time the splash remains fully visible |
| `CARUI_SPLASH_FULLSCREEN` | Override splash fullscreen behavior   |
| `CARUI_DISPLAY`           | Explicit X11 display override         |

Example without the startup splash:

```bash
CARUI_SPLASH=0 \
CARUI_GEOMETRY=1024x600 \
CARUI_FULLSCREEN=0 \
venv/bin/python -m apps.carUi.main
```

---

## Remote X11 Development

OpenRoadCode can be launched through X11 forwarding for development.

Connect to the target system with:

```bash
ssh -X username@openroad-host
```

Then run:

```bash
echo "$DISPLAY"

CARUI_GEOMETRY=1024x600 \
CARUI_FULLSCREEN=0 \
venv/bin/python -m apps.carUi.main
```

Trusted X11 forwarding may be used where appropriate:

```bash
ssh -Y username@openroad-host
```

The application normally preserves the `DISPLAY` value assigned by SSH.

---

## Development Without Hardware

Many OpenRoadCode components provide mocks, stubs, or unconfigured implementations.

These allow developers to:

* Test application logic on a workstation
* Develop panels without connecting physical devices
* Simulate controller state
* Verify dependency assembly
* Test failure and unconfigured states
* Build new hardware adapters independently

New controllers should provide a mock or stub implementation when practical.

---

## Component Tests

Many hardware and controller modules include command-line component tests.

These are intended to verify one subsystem at a time without launching the complete application.

Examples may include tests for:

* GPS input
* OBD-II communication
* Rotary encoders
* Environmental sensors
* Spotify
* Music-video lookup
* Audio control
* Bluetooth devices

Component tests may require hardware, Linux permissions, system services, or environment variables.

They supplement automated tests but should not be treated as a replacement for them.

---

## Automated Checks

Public methods declared in `*_if.py` modules must document:

* Every argument with `@param`
* Every non-`None` return value with `@return` or `@retval`

Run the interface-contract check with:

```bash
python3 scripts/check_doxygen_contracts.py
```

The command exits with a nonzero status when a public interface contract is incomplete.

GitHub Actions may run this and other checks for pull requests and changes to the default branch.

Additional automated behavioral tests are being added as the project matures.

---

## Coding Guidelines

General project conventions include:

* Use `snake_case` for Python modules, methods, functions, and variables
* Use clear interface names ending in `If`
* Prefer dependency injection over global state
* Keep hardware-specific behavior in `hardware_io`
* Keep protocol parsing in `protocols`
* Keep application-facing behavior in `controllers`
* Avoid importing application modules from lower-level packages
* Provide type annotations for public APIs
* Document public interfaces
* Keep configuration outside application logic
* Provide mocks or stubs for hardware-dependent components when practical
* Handle unavailable hardware as a normal runtime condition
* Prefer small, focused modules over large multipurpose classes

---

## Adding New Hardware

A typical hardware integration should follow this pattern:

1. Define or reuse a hardware interface.
2. Create a concrete adapter for the device.
3. Add a component test for direct hardware verification.
4. Create or update the corresponding controller.
5. Add configuration for selecting the implementation.
6. Inject the implementation during runtime assembly.
7. Keep device-specific imports out of the UI.

Example:

```text
EnvironmentalSensorIf
        │
        ├── Bmp390Adapter
        ├── MockEnvironmentalSensor
        └── FutureSensorAdapter
```

The rest of the application should not need to know which physical sensor is active.

---

## Adding a New Application Feature

A new user-facing feature will typically include:

```text
apps/
    User-interface panel or application

controllers/
    Application-facing behavior

hardware_io/
    Optional device implementation

protocols/
    Optional communication protocol

config/
    Runtime and device settings
```

Not every feature requires every layer.

Avoid creating abstractions unless they provide a real boundary, test seam, or interchangeable implementation. Software has enough ceremonial architecture already.

---

## Supported Platforms

Primary development targets include:

* Raspberry Pi OS
* Debian-based ARM64 systems
* Debian-based AMD64 development systems

Other Linux distributions may work but are not currently guaranteed.

The user interface currently relies on Linux desktop and display technologies including Tkinter, X11, VNC, and related services.

Some integrations also rely on:

* GPSD
* BlueZ
* PipeWire
* RTL-SDR
* SDR++
* Chromium
* Streamlit
* Linux GPIO and I2C support

---

## Safety

OpenRoadCode is an experimental hobbyist and educational platform.

It must not be relied upon for:

* Steering
* Braking
* Throttle control
* Airbag control
* Stability control
* Other safety-critical vehicle functions

Do not interact with the system while driving unless the interaction is legal, safe, and designed to minimize distraction.

Radio operation must comply with applicable laws and regulations.

Vehicle wiring, power integration, CAN bus access, GPIO connections, and external hardware modifications should be performed carefully.

The project maintainers and contributors are not responsible for vehicle damage, data loss, distraction, regulatory violations, or injury resulting from use of the software or associated hardware.

---

## Contributing

Contributions are welcome, particularly in the following areas:

* Automated tests
* Documentation
* Hardware adapters
* Configuration validation
* Installation improvements
* User-interface accessibility
* Radio applications
* Vehicle telemetry
* Embedded Linux support
* Failure handling
* Platform portability

Before submitting a major architectural change, open an issue describing:

* The problem being solved
* The proposed design
* The affected layers
* Hardware or platform dependencies
* Testing considerations

Changes should preserve separation between applications, controllers, protocols, and hardware-specific code.

A dedicated `CONTRIBUTING.md` will provide more detailed contribution guidance.

---

## Reporting Problems

When reporting a problem, include:

* Linux distribution and version
* CPU architecture
* Raspberry Pi or computer model
* Python version
* Relevant hardware
* Configuration files with secrets removed
* Steps to reproduce
* Expected behavior
* Actual behavior
* Relevant logs or terminal output

For hardware-related issues, also include:

* Device model
* Connection type
* Device path
* USB or I2C detection output
* Required Linux services
* Whether the component test succeeds

---

## License

OpenRoadCode is released under the MIT License.

See:

```text
LICENSE
```

for the complete license text.

---

## Acknowledgments

OpenRoadCode builds upon the work of many open-source projects and communities, including Linux, Python, Raspberry Pi, RTL-SDR, GPSD, BlueZ, PipeWire, SDR++, Spotify integration libraries, and numerous hardware-driver projects.

The project would not be possible without the maintainers who document obscure hardware behavior so the rest of us can eventually discover that one missing `udev` rule.
