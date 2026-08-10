# OpenRoadCode Configuration

This directory contains shared OpenRoadCode runtime configuration, parsing,
and domain-specific configuration profiles.

## Files

- `runtime.toml` selects radio stacks, input devices, sensors, and
  auxiliary applications.
- `runtime_config.py` parses and validates that TOML file.
- `integration_test/test_runtime_config_parser.py` verifies parsing,
  defaults, path resolution, filtering, and validation behavior.
- `integration_test/test_input_device_config.py` verifies optional keyboard and
  standalone pushbutton parsing and action validation.

The parser lives at the root configuration boundary because multiple
applications and tools consume the same deployment choices. Each consumer
still owns its own dependency assembly and lifecycle.

## Configuration boundaries

The TOML file describes **which components are assembled**:

- enabled radio stacks
- backend selection
- launcher selection
- RigCTL connection settings
- remote display
- rotary encoder drivers/settings and the system-volume encoder assignment
- optional Linux input-event keyboard selection
- optional standalone GPIO pushbuttons and their semantic UI actions
- barometric sensor driver and I2C address
- decoded artwork cache capacity and optional persistent source directory
- target-aware audio output selection and optional device-name matching
- auxiliary applications such as ADS-B and the weather dashboard

Radio-domain data remains in the existing JSON files under:

```text
PROJECT_ROOT/config/radio
```

Those JSON files continue to describe:

- frequency ranges
- starting frequencies
- modes
- bandwidths
- tuning steps
- presets

This separation prevents the runtime composition file from becoming a large
combined application, hardware, and radio-domain configuration blob.

Radio profiles are loaded through `config.radio_config_manager`; applications
should use that parser rather than reading the JSON files directly.

## Example

```toml
[runtime]
remote_display = ":2"
# Display used by the Weather and ADS-B browser dashboards.
auxiliary_display = ":0"
# Optional display used specifically by Netflix and YouTube browser windows.
# media_display = ":0"

[audio]
# auto selects desktop default, Pi 4 onboard analog, or Pi 5 USB audio.
output = "auto"
# device_match = "C-Media USB Audio"

[image_cache]
directory = "var/cache/artwork"
max_entries = 24

[position_cache]
enabled = true
directory = "~/.cache/openroadcode/position"
max_age_seconds = 604800

[auxiliary.weather_dashboard]
enabled = true
# Warm Streamlit after CarUi is ready so the first browser launch is faster.
preload = true

[rigctl]
host = "127.0.0.1"
port = 4532

[environmental.barometric_sensor]
driver = "bmp388"
address = 0x77

[input.rotary_encoders]
volume_index = 0

[input.keyboard]
enabled = false
# device_path = "/dev/input/event3"

[[input.push_buttons]]
pin = 16
action = "home"
active_low = true
debounce_seconds = 0.05

[[input.rotary_encoders.devices]]
driver = "seesaw"
address = 0x36

[[input.rotary_encoders.devices]]
driver = "seesaw"
address = 0x37

[[input.rotary_encoders.devices]]
driver = "gpio"
pin_a = 11
pin_b = 13
button = 15

[[radios]]
key = "fm_radio"
config = "fm_radio.json"
backend = "rigctl"
launcher = "sdrpp"
enabled = true
```

Relative radio configuration paths are resolved from:

```text
PROJECT_ROOT/config/radio
```

The example above therefore resolves to:

```text
PROJECT_ROOT/config/radio/fm_radio.json
```

Absolute paths are also accepted.

## Loading the configuration

```python
from pathlib import Path

from config.runtime_config import (
    RuntimeConfigParser,
)

parser = RuntimeConfigParser(
    Path("config/runtime.toml")
)
config = parser.load()

print(config.runtime.remote_display)
print(config.rigctl.host)
print(config.environmental.barometric_sensor.driver)
print(config.environmental.barometric_sensor.address)
print(config.input.rotary_encoders.devices)
print(config.input.rotary_encoders.volume_index)
print(config.input.keyboard.enabled)
print(config.input.keyboard.device_path)
print(config.input.push_buttons)
print(config.radio("fm_radio").config_path)
```

Only enabled radio stacks should normally be assembled:

```python
for radio_stack in config.enabled_radios():
    print(radio_stack.key)
```

## Validation

The parser rejects:

- malformed TOML
- missing or empty radio keys
- missing radio configuration names
- duplicate radio keys
- empty or unsupported rotary encoder device definitions
- duplicate or invalid Seesaw I2C addresses
- unsupported barometric sensor drivers or invalid I2C addresses
- invalid or shared GPIO physical pins
- a volume encoder index outside the configured device list
- non-boolean keyboard enablement or a non-string keyboard device path
- unsupported pushbutton actions
- invalid, duplicate, or encoder-conflicting pushbutton pins
- negative pushbutton debounce intervals
- invalid RigCTL ports
- non-boolean `enabled` values
- missing radio JSON files

## Testing the configured volume encoder

The configured `volume_index`, encoder driver, and system audio integration can
be tested without launching the Car UI:

```bash
python3 -m apps.carUi.input.component_test.volume_encoder_cli
```

Rotating the selected encoder changes the actual default PipeWire sink volume
and prints the resulting level. The test starts only the device selected by
`volume_index`; disconnected contextual encoders do not affect this test.
The default reported range is 20 levels, matching the default 5% PipeWire
increment. This is independent of the Car UI's eight-bar visual indicator.
Pressing the selected encoder toggles system mute.

For tests that intentionally use nonexistent radio files, construct the parser
with `require_radio_files=False`.

## Running the parser test

From the project root:

```bash
python3 -m unittest discover \
  -s config/integration_test \
  -p 'test_*.py'
```

The test suite uses only the Python standard library.

# Runtime Configuration Validator

`runtime_config_test_app.py` is a command-line validator for shared runtime
TOML files. It uses the production parser and validates the
same schema used by application startup.

## Basic usage

From the project root:

```bash
python3 -m config.component_test.runtime_config_test_app \
    config/runtime.toml
```

A valid file prints the resolved runtime configuration and exits with status
code `0`.

An invalid file prints an `INVALID:` message to standard error and exits with
status code `1`.

## Explicit project root

Use `--project-root` when running against a configuration outside the normal
repository layout:

```bash
python3 -m config.component_test.runtime_config_test_app \
    /tmp/runtime.toml \
    --project-root /path/to/project
```

## Structure-only validation

To validate TOML structure without requiring referenced radio JSON files to
exist:

```bash
python3 -m config.component_test.runtime_config_test_app \
    config/runtime.toml \
    --skip-radio-file-check
```

## Quiet mode

For scripts and CI:

```bash
python3 -m config.component_test.runtime_config_test_app \
    config/runtime.toml \
    --quiet
```

Quiet mode prints only the final `VALID:` or `INVALID:` result.

## Validator tests

```bash
python3 -m unittest discover \
  -s config/integration_test \
  -p 'test_*.py'
```
