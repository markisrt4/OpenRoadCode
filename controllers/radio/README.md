README.md


# Radio Controller

`controllers.radio` provides transport-independent radio control behavior. It coordinates tuning, modes, presets, frequency ranges, and input adapters without depending on a specific UI or radio protocol implementation.

## Package Layout

```text
controllers/radio/
├── __init__.py
├── radio_backend_if.py
├── radio_controller.py
├── radio_controller_if.py
├── radio_controller_stub.py
├── radio_input_adapter_if.py
├── radio_types.py
├── unconfigured_radio_controller.py
├── README.md
├── adapters/
│   ├── __init__.py
│   ├── keyboard_radio_adapter.py
│   └── rigctl_radio_backend.py
├── component_test/
│   ├── __init__.py
│   └── test_radio_component.py
└── integration_test/
    ├── __init__.py
    └── test_sdrpp_rigctl.py
```

## Responsibilities

The package owns:

- Current frequency and mode state
- Frequency stepping and range wrapping
- Preset selection and wraparound
- Controller-facing backend contracts
- Input-to-controller mappings
- Adaptation of a rigctl client to the radio backend contract

Protocol packages own command formatting, socket communication, and protocol response parsing. Higher-level code owns configuration loading, process lifecycle, UI behavior, and runtime assembly.

## Controller Implementations

Applications and input adapters should depend on `RadioControllerIf`.

- `RadioController` coordinates a configured receiver backend.
- `RadioControllerStub` provides deterministic in-memory tuning and telemetry
  for demos and UI development.
- `UnconfiguredRadioController` reports `is_available == False`, exposes a
  reason through `status_message`, and raises for radio operations rather than
  fabricating receiver state.

## System Dependencies

The core radio controller uses only the Python standard library.

The keyboard adapter requires `evdev`:

```bash
sudo apt install python3-evdev
```

The rigctl backend requires the local `protocols.rigctl` package and access to a running rigctl-compatible server.

The SDR++ integration test requires SDR++ with the Rigctl Server module available.

### Installing SDR++

SDR++ is not installed as a dependency of this Python package. Install it separately using a package or build provided by the SDR++ project.

Download the appropriate Linux build from the SDR++ project:

- https://www.sdrpp.org/
- Project Location: https://github.com/AlexandreRouma/SDRPlusPlus
- Nightly Build: https://github.com/AlexandreRouma/SDRPlusPlus/releases

On Debian- or Ubuntu-based systems, install a downloaded `.deb` package with:

```bash
sudo apt install ./sdrpp_<package>.deb
```

For distributions without a supported package, follow the SDR++ Linux build instructions in the upstream repository.

After installation, start SDR++ and configure the **Rigctl Server** module:

```text
Host: localhost
Port: 4532
```

Select the VFO to be controlled and start the Rigctl Server module before running the integration test.

Verify that SDR++ is listening on the expected port:

```bash
ss -ltn | grep 4532
```

The integration test defaults to `127.0.0.1:4532`.

## Basic Use

```python
from controllers.radio import RadioController, RadioMode, RadioPreset, RadioRange
from controllers.radio.adapters.rigctl_radio_backend import RigctlRadioBackend
from protocols.rigctl import RigctlClient

wide_fm = RadioMode(name="WFM", bandwidth=180_000, step_hz=100_000)

controller = RadioController(
    backend=RigctlRadioBackend(RigctlClient("127.0.0.1", 4532)),
    presets=[
        RadioPreset("88.7 FM", 88_700_000, wide_fm),
        RadioPreset("101.1 FM", 101_100_000, wide_fm),
    ],
    default_mode=wide_fm,
    radio_range=RadioRange(
        min_frequency_hz=87_500_000,
        max_frequency_hz=108_000_000,
        start_frequency_hz=88_100_000,
    ),
)

controller.start()
controller.frequency_up()
controller.next_preset()
controller.stop()
```

## Component Test

Run the deterministic component test from the repository root:

```bash
python3 -m controllers.radio.component_test
```

The test uses in-memory test doubles and prints the result of each validated operation. It covers:

- Startup and shutdown
- Default mode application
- Frequency stepping
- Range wrapping
- Preset navigation
- Backend synchronization
- Rigctl frequency conversion
- Signal strength, SNR, and RDS forwarding
- Optional response normalization
- Invalid response handling
- Radio model validation

The component test does not require SDR++, a keyboard device, a network connection, or third-party system packages.

## SDR++ Rigctl Integration Test

The integration test connects to a real rigctl server and exercises `RigctlRadioBackend`.

To test an already-running SDR++ instance:

```bash
python3 -m controllers.radio.integration_test.test_sdrpp_rigctl
```

To set and verify a test frequency:

```bash
python3 -m controllers.radio.integration_test.test_sdrpp_rigctl \
    --frequency 101100000
```

To set a mode and bandwidth during the test:

```bash
python3 -m controllers.radio.integration_test.test_sdrpp_rigctl \
    --frequency 101100000 \
    --mode WFM \
    --bandwidth 180000
```

To launch SDR++ as part of the test:

```bash
python3 -m controllers.radio.integration_test.test_sdrpp_rigctl \
    --launch-command "sdrpp" \
    --frequency 101100000
```

Note: Rigctl Server must be enabled within sdrpp.  Enable Rigctl Serrver -> Listen on startup

The test defaults to `127.0.0.1:4532`. Use `--host` and `--port` to select a different rigctl endpoint.

When a test frequency is supplied, the integration test records the original frequency and restores it before exiting. A process launched with `--launch-command` is stopped when the test completes.

## Import Boundaries

The root package exports only controller interfaces, controller types, and the controller implementation. Concrete adapters are imported explicitly:

```python
from controllers.radio.adapters.rigctl_radio_backend import RigctlRadioBackend
from controllers.radio.adapters.keyboard_radio_adapter import KeyboardRadioAdapter
```

This prevents optional adapter dependencies from being imported when only the core controller package is needed.
