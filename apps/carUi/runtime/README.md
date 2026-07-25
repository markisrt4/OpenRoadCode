# Car UI Runtime Factory

The runtime factory converts the validated TOML configuration into application
runtime objects before the Tk UI is created.

## Files

```text
apps/carUi/runtime/
├── __init__.py
├── radio_runtime.py
├── radio_runtime_registry.py
├── radio_runtime_factory.py
└── rotary_encoder_runtime.py
```

The corresponding component test belongs at:

```text
apps/carUi/runtime/component_test/test_radio_runtime_factory.py
```

## Runtime flow

```text
car_ui_runtime.toml
        |
        v
CarUiRuntimeConfigParser
        |
        v
CarUiRuntimeFactory
        |
        v
CarUiRuntime
        |
        +-- RotaryEncoderConfig
        |       |
        |       v
        |   RotaryEncoderRuntime
        |       +-- tuple[RotaryEncoderIf, ...]
        |       +-- volume_index
        |
        +-- RadioRuntimeRegistry
        |       +-- fm_radio
        |       +-- airband
        |       +-- scanner bands
        |
        +-- ADSBLauncher
        +-- WeatherDashLauncher
        +-- SDRResourceManager
```

## Usage

```python
from pathlib import Path

from apps.carUi.runtime.radio_runtime_factory import create_car_ui_runtime

runtime = create_car_ui_runtime(
    Path("apps/carUi/config/car_ui_runtime.toml")
)

fm_runtime = runtime.radios.get("fm_radio")

print(runtime.remote_display)
print(fm_runtime.config)
print(fm_runtime.controller)
print(fm_runtime.launcher)
```

## Configuration names

TOML uses stable symbolic names:

```toml
backend = "rigctl"
launcher = "sdrpp"
```

The factory maps those names to known constructors. The TOML file does not
contain Python class paths and cannot instantiate arbitrary application
objects.

Rotary encoder devices use a separate tagged configuration:

```toml
[[input.rotary_encoders.devices]]
driver = "seesaw"
address = 0x36

[[input.rotary_encoders.devices]]
driver = "gpio"
pin_a = 11
pin_b = 13
button = 15
```

`rotary_encoder_runtime.py` is the hardware composition boundary. It converts
these driver-specific records into an ordered tuple of `RotaryEncoderIf`
objects. The event router and panels receive only that generic interface and
logical indexes.

## Migration

Once `main.py` uses `create_car_ui_runtime()`, the following legacy files are
no longer required:

```text
apps/carUi/radio_runtime_assembly.py
apps/carUi/config/radio_manifest.json
apps/carUi/config/radio_manifest_parser.py
```

Panel managers should retrieve runtimes through:

```python
runtime = self.app.runtime.radios.get("fm_radio")
```

rather than application attributes such as:

```python
self.app.fm_radio_controller
self.app.fm_radio_launcher
self.app.fm_radio_config
```

## Test

```bash
python3 -m unittest apps.carUi.runtime.component_test.test_radio_runtime_factory
python3 -m unittest apps.carUi.runtime.component_test.test_rotary_encoder_runtime
```
