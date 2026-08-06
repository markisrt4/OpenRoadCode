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
mock, stub, or unconfigured implementations when working on application logic
at a desk. Your laptop should not need to believe it is a Jeep.

## A quick architecture tour

The main dependency direction is:

```text
Applications and UI
        ↓
Controllers
        ↓
Hardware adapters and protocols
        ↓
Linux devices, services, and physical hardware
```

In practical terms:

- `apps/` owns user-facing applications and runtime assembly.
- `controllers/` exposes behavior applications can use.
- `hardware_io/` isolates device-specific access.
- `protocols/` handles communication formats and remote APIs.
- `config/` holds runtime and hardware configuration.

Keep hardware-specific imports out of application and UI code. When adding a
device, place its implementation behind an interface so the rest of the
project can run with a real adapter, a test fake, or no hardware at all.

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
  external applications, credentials, or services that CI cannot provide.

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
- Exercise relevant component CLIs when changing hardware integrations.
- Update configuration examples and documentation when behavior changes.
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
