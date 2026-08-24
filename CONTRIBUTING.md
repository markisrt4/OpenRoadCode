# Contributing to OpenRoadCode

Thanks for helping build OpenRoadCode!

This project lives at the intersection of cars, radios, embedded Linux,
hardware hacking, and software experimentation. You do not need to be an
expert in all—or even most—of those things to contribute. Curiosity, care,
and a willingness to test your work will get you a long way.

Whether you are fixing a typo, adding support for a sensor, improving the
touchscreen UI, or arriving with an alarming collection of SDR equipment,
you are welcome here.

Visit [openroadcode.org](https://openroadcode.org) for the project page, and
use the GitHub repository for code, issues, and pull requests.

## First things first

OpenRoadCode interacts with vehicles, electrical systems, radios, Linux
services, and physical hardware. Please experiment thoughtfully.

- Never rely on OpenRoadCode for steering, braking, throttle, airbags, or
  other safety-critical vehicle functions.
- Do not test an interface while driving unless the interaction is legal,
  safe, and designed to avoid distraction.
- Avoid transmitting with radio hardware unless you understand the equipment
  and the applicable regulations.
- Do not commit credentials, OAuth tokens, API keys, device identifiers, or
  private vehicle data.
- Report sensitive vulnerabilities privately by following
  [SECURITY.md](SECURITY.md), rather than opening a public issue.
- Describe any hardware, permissions, or system services needed to reproduce
  your work.

Safety notes are not meant to drain the fun out of the project. They help
make sure everyone gets to keep having fun afterward.

## Finding something to work on

Contributions of all sizes are useful. Good places to start include:

- Documentation and examples
- Automated tests
- Hardware mocks and stubs
- Clearer error messages
- Configuration validation
- UI accessibility and usability
- Hardware adapters
- Radio and vehicle-telemetry features
- Installer and platform support

For a substantial feature or architectural change, open an issue before
investing heavily in an implementation. Explain the problem, the proposed
direction, affected hardware or services, and how the result could be tested.
That gives everyone a chance to compare maps before the convoy sets off.

## Setting up a development environment

Copy the clone URL from the GitHub repository, then enter the project
directory:

```bash
git clone https://github.com/markisrt4/OpenRoadCode.git
cd OpenRoadCode
```

The installer supports Raspberry Pi 4, Raspberry Pi 5, and Debian/Ubuntu
development hosts. Preview the development setup before changing your system:

```bash
./scripts/installers/host_setup.sh --target linux-dev --show-plan
```

Remove `--show-plan` when you are ready to install. Read the plan first:
installers may add system packages, configure services, or create a Python
environment.

Installation targets describe platforms, features describe optional
capabilities, and concrete devices are configured separately. Avoid adding a
specific sensor, adapter, radio, or service to every target merely because it
is present in one reference vehicle.

Use `--all-features` when a development or reference system needs every
capability compatible with its selected target. Optional services and concrete
device configuration remain separate by design.

When an installer has created the project environment, activate it with:

```bash
source venv/bin/activate
```

Many parts of the project can be developed without vehicle hardware. Prefer
mock, stub, simulation, or unconfigured implementations when working on
application logic at a desk. Your laptop should not need to believe it is a
Jeep.

## A quick architecture tour

OpenRoadCode separates reusable domain behavior, process ownership, messaging,
and presentation.

Commands and requested behavior use controller or request-handler interfaces:

```text
Application / UI
      ↓
Controller or request interface
      ↓
Concrete implementation / service command endpoint
      ↓
Hardware adapter / protocol / remote service
```

Continuously changing public telemetry is distributed through producer services and the message bus:

```text
Hardware / simulator
      ↓
Domain producer service
      ↓
SI domain state
      ↓
Contract publisher
      ↓
ZeroMQ message bus
      ↓
Shared application telemetry state
      ↓
Frontend / UI
```

In practical terms:

- `apps/` owns user-facing applications, runtime assembly, and app-specific state.
- `services/` owns long-running domain producers, process lifecycle, runtime composition, and acknowledged command endpoints.
- `controllers/` exposes reusable domain behavior, policies, and hardware-independent processing.
- `messaging/` owns public message contracts, encoding/decoding, dispatch, and transports.
- `frontends/` owns toolkit-specific reusable presentation.
- `ui/` owns toolkit-independent presentation contracts.
- `common/` owns neutral cross-cutting helpers such as shared telemetry state and unit conversion.
- `hardware_io/` isolates device-specific access.
- `protocols/` handles communication formats, device protocols, and remote APIs.
- `config/` holds runtime and hardware configuration.

A producer service owns its physical device or simulation source, domain processing, and publication lifecycle. Applications should subscribe to public telemetry instead of creating their own competing GPS, IMU, or OBD-II hardware instances just to display state.

Do not confuse `services/` with `messaging/`. A service owns and runs a domain capability. Messaging transports and defines public messages. A ZeroMQ socket does not become a service merely because it has ambitions.

For new public telemetry, use SI units and perform imperial/metric conversion only at the presentation boundary. Shared conversions live in `common.units`; do not duplicate conversion constants in each frontend. Existing internal APIs with explicitly named non-SI units must be converted at a documented boundary rather than silently reinterpreted.

Use PUB/SUB for continuously changing state that may have multiple consumers.
Use request/reply when an operation needs acknowledgement or an error response;
navigation calibration, heading reset, and route calculation are examples. Do
not turn a command into telemetry merely because ZeroMQ happens to be nearby.

Simulation belongs at the producer-service input so simulated and physical
sources exercise the same downstream contract and consumers. Runtime service
composition belongs in runtime configuration, not in individual UI applications.

A useful rule when choosing a boundary is:

- "Do this" normally belongs behind a controller/request interface or acknowledged service command endpoint.
- "This is the current state" is a candidate for a public telemetry contract.

For navigation specifically, keep these responsibilities separate:

- route planning calculates a `RouteResult`;
- route guidance derives maneuver progress, arrival, and off-route state;
- navigation-session orchestration owns destination/travel mode, reroute policy, and route replacement;
- map presentation displays route/position state without deciding when to reroute.

Architecture references:

- [Architecture overview](docs/architecture.md)
- [Messaging overview and subscriber quick start](messaging/README.md)
- [Message Bus Interface Design Description (IDD)](docs/messaging/message_bus_idd.md)
- [Domain IDDs](docs/idd/)
- [Navigation producer service](services/navigation/README.md)
- [Automotive producer service](services/automotive/README.md)

Avoid abstractions that do not provide a useful boundary, test seam, or
interchangeable implementation. Software already has enough ceremonial
ribbon-cutting.

## Where tests belong

Tests live beside the code they exercise. OpenRoadCode does not use one giant
test attic where everything gets tossed and forgotten.

Each package may contain one or more of these directories:

- `unit_test/` contains fast, isolated, automated tests. Replace hardware,
  processes, clocks, and remote services with fakes or mocks.
- `integration_test/` contains automated tests connecting real software
  components. These tests must run unattended and clean up their resources.
- `component_test/` contains manual tools for hardware, interactive input,
  external applications, credentials, services, or end-to-end environment
  checks that CI cannot reliably provide.

Use snake_case filenames:

```text
controllers/radio/
├── unit_test/test_radio_controller.py
├── integration_test/test_rigctl_backend.py
└── component_test/sdrpp_rigctl_cli.py
```

Files discovered by the automated runner must start with `test_`. Manual
component programs should normally end with `_cli.py` so they cannot be
mistaken for unattended tests.

A component test should state its environment assumptions. If it requires
Raspberry Pi hardware, gpsd, Valhalla, MapLibre, a display server, credentials,
or another external dependency, document that rather than allowing an import
failure to serve as the setup guide.

Run the same commands used by continuous integration:

```bash
python scripts/run_tests.py unit
python scripts/run_tests.py integration
```

Run both categories, in that order, with:

```bash
python scripts/run_tests.py all
```

Component tests are run individually because their requirements vary. In a
pull request, document the command, connected hardware or service, expected
behavior, and result.

## Public interfaces and documentation

Public methods declared in `*_if.py` modules must document:

- Every argument with `@param`
- Every non-`None` result with `@return` or `@retval`

Run the contract check with:

```bash
python scripts/check_doxygen_contracts.py
```

Docstrings and comments should explain intent, constraints, or surprising
behavior. They do not need to narrate obvious Python one line at a time.

When adding or changing a public message contract:

1. define a stable topic or command name and schema version where applicable;
2. document units, nullability, ranges, producer semantics, and consumer semantics;
3. add or update the applicable IDD under `docs/idd/` or `docs/messaging/`;
4. add encoder/decoder and validation tests;
5. update `messaging/README.md` and the owning service README when discovery or runtime behavior changes.

New normalized public telemetry contracts use SI units unless the IDD explicitly documents a justified exception. Do not expose a presentation preference such as miles versus kilometers as two competing wire contracts.

Public request/reply commands are interfaces too. Document request fields, response fields, failure behavior, units, and ownership in an IDD when they cross a process boundary.

## Code style

- Use `snake_case` for modules, functions, methods, and variables.
- Add type annotations to public APIs.
- Prefer dependency injection over global state.
- Keep functions and modules focused.
- Treat unavailable hardware as a normal runtime condition where practical.
- Preserve existing interfaces unless a deliberate migration is part of the
  change.
- Do not mix unrelated cleanup into a focused pull request.

Match the surrounding code where the project does not yet enforce a rule
automatically. Consistency beats introducing a second excellent convention.

### License headers and attribution

Repository-owned source files use SPDX headers to record their license and
copyright holders. New Python and shell files should begin with:

```text
# SPDX-FileCopyrightText: YEAR Your Name
# SPDX-License-Identifier: MIT
```

Use the comment syntax appropriate for other languages. Keep a shebang first,
and keep a Python encoding declaration on its required first or second line.

When making a copyrightable contribution to an existing file, add your own
`SPDX-FileCopyrightText` line without removing the existing notices. Trivial
changes such as typo fixes or formatting do not normally require an additional
copyright line. Preserve notices in third-party or adapted code, and identify
its license accurately rather than applying the project's header automatically.

## Hardware contributions

A useful hardware contribution usually includes:

1. An interface or an existing interface it implements.
2. A concrete adapter isolated under `hardware_io/`.
3. A mock, stub, or graceful unavailable state where practical.
4. Unit tests that do not require the device.
5. A component CLI for direct hardware verification.
6. Configuration and documentation for selecting the implementation.

Include relevant device models, addresses, pins, connection types, Linux
permissions, and service requirements. Never assume another contributor has
your exact Raspberry Pi, adapter revision, wiring harness, or especially
cooperative Bluetooth dongle.

## Legacy and deprecated code

Some areas are experimental or awaiting migration. Do not build new features
on a legacy module merely because it happens to have the most adventurous
filename.

When touching deprecated code, make the intended direction clear. A change
may port it to current interfaces, isolate it under a clearly named legacy or
deprecated area, or remove it when there is no remaining use. Call out that
decision in the pull request.

## Preparing a pull request

Before opening a pull request:

- Keep the change focused and reviewable.
- Run `python scripts/run_tests.py unit`.
- Run `python scripts/run_tests.py integration` when the environment permits.
- Run `python scripts/check_doxygen_contracts.py` after changing interfaces.
- Exercise relevant component CLIs when changing hardware or service integrations.
- Update configuration examples and documentation when behavior changes.
- Update the applicable IDD, messaging documentation, and service README when adding or changing a public cross-process interface.
- Remove secrets, generated files, debug output, and machine-specific paths.

In the pull request description, tell us:

- What problem the change solves
- Why this approach was chosen
- How it was tested
- What hardware or services were involved
- Any limitations or follow-up work

Screenshots are welcome for visual changes. Logs and command output are useful
for hardware and protocol changes, provided secrets and private data have been
removed.

## Be good to one another

Assume good intent, explain unfamiliar concepts, and leave room for people to
learn. Helpful reviews discuss the code and its tradeoffs rather than the
person who wrote it.

OpenRoadCode is an ambitious experiment assembled from many disciplines. No
one arrives knowing all of them. Share what you know, ask when you do not, and
help make the next contributor's first drive a little smoother.
