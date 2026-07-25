# Car UI Runtime Configuration

This directory contains application-specific configuration and parsing for the
Car UI runtime.

## Files

- `car_ui_runtime.toml` selects the radio stacks and auxiliary applications
  assembled for the Car UI.
- `car_ui_runtime_config_parser.py` parses and validates that TOML file.
- `component_test/test_car_ui_runtime_config_parser.py` verifies parsing,
  defaults, path resolution, filtering, and validation behavior.

The parser is application-specific and therefore belongs under
`apps/carUi/config`. It does not belong in `apps/common`, because the schema
describes Car UI runtime composition rather than a reusable lower-level
configuration format.

## Configuration boundaries

The TOML file describes **which components are assembled**:

- enabled radio stacks
- backend selection
- launcher selection
- RigCTL connection settings
- remote display
- rotary encoder drivers/settings and the system-volume encoder assignment
- barometric sensor driver and I2C address
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

## Example

```toml
[runtime]
remote_display = ":2"

[rigctl]
host = "127.0.0.1"
port = 4532

[environmental.barometric_sensor]
driver = "bmp388"
address = 0x77

[input.rotary_encoders]
volume_index = 0

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

from apps.carUi.config.car_ui_runtime_config_parser import (
    CarUiRuntimeConfigParser,
)

parser = CarUiRuntimeConfigParser(
    Path("apps/carUi/config/car_ui_runtime.toml")
)
config = parser.load()

print(config.runtime.remote_display)
print(config.rigctl.host)
print(config.environmental.barometric_sensor.driver)
print(config.environmental.barometric_sensor.address)
print(config.input.rotary_encoders.devices)
print(config.input.rotary_encoders.volume_index)
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
python3 -m unittest     apps.carUi.config.component_test.test_car_ui_runtime_config_parser
```

The test suite uses only the Python standard library.

## Migration from the JSON manifest

The following files are superseded by the TOML runtime configuration:

```text
apps/carUi/config/radio_manifest.json
apps/carUi/config/radio_manifest_parser.py
```

Do not delete them until `main.py` and runtime assembly no longer import
`RadioManifestParser`.

After the runtime factory is migrated to `CarUiRuntimeConfigParser`, verify:

```bash
grep -R "RadioManifestParser\|radio_manifest.json" apps
```

When that command returns no active references, the legacy JSON manifest and
parser can be removed. Git remains available for historical archaeology, as it
usually is when humans resist deleting obsolete code for entirely reasonable
reasons.


# Runtime Configuration Validator

`car_ui_runtime_config_test_app.py` is a command-line validator for Car UI
runtime TOML files. It uses the production parser and therefore validates the
same schema used by application startup.

## Basic usage

From the project root:

```bash
python3 -m apps.carUi.config.component_test.car_ui_runtime_config_test_app \
    apps/carUi/config/car_ui_runtime.toml
```

A valid file prints the resolved runtime configuration and exits with status
code `0`.

An invalid file prints an `INVALID:` message to standard error and exits with
status code `1`.

## Explicit project root

Use `--project-root` when running against a configuration outside the normal
repository layout:

```bash
python3 -m apps.carUi.config.component_test.car_ui_runtime_config_test_app \
    /tmp/runtime.toml \
    --project-root /path/to/project
```

## Structure-only validation

To validate TOML structure without requiring referenced radio JSON files to
exist:

```bash
python3 -m apps.carUi.config.component_test.car_ui_runtime_config_test_app \
    apps/carUi/config/car_ui_runtime.toml \
    --skip-radio-file-check
```

## Quiet mode

For scripts and CI:

```bash
python3 -m apps.carUi.config.component_test.car_ui_runtime_config_test_app \
    apps/carUi/config/car_ui_runtime.toml \
    --quiet
```

Quiet mode prints only the final `VALID:` or `INVALID:` result.

## Validator tests

```bash
python3 -m unittest \
    apps.carUi.config.component_test.test_car_ui_runtime_config_test_app
```
