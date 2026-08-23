# Car UI Runtime Factory

The runtime factory converts validated TOML into application configuration,
controllers, and launchers before the Tk UI is created. Frontend-adjacent
services such as `CarUiInputRuntime` are constructed later by
`CarUiComposition`, after a frontend dispatcher exists.

Car UI startup also prepares an MPU-6050 navigation controller for the
embedded off-road destination. The controller connects and polls only while
that screen is visible. `CARUI_IMU_ADDRESS` selects the I2C address and
`CARUI_IMU_FILTER_TIME_CONSTANT` selects the orientation-filter time constant.
The existing Car UI position source forwards GPS/browser reports into this
controller, so the destination does not create a second position provider.

## Files

```text
apps/carUi/runtime/
├── car_ui_runtime.py
├── car_ui_runtime_factory.py
├── car_ui_input_runtime.py
├── input_device_runtime.py
├── lighting_runtime_factory.py
├── music_visualizer_runtime_factory.py
├── position_source_factory.py
├── radio_runtime_registry.py
├── rotary_encoder_runtime.py
└── spotify_runtime_factory.py
```

The corresponding component test belongs at:

```text
apps/carUi/runtime/unit_test/test_car_ui_runtime_factory.py
```

## Runtime flow

```text
runtime.toml
        |
        v
RuntimeConfigParser
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
        +-- KeyboardConfig -> KeyboardReaderIf (Linux KeyboardReader when enabled)
        +-- PushButtonConfig -> RpiGpioPushButton (on Raspberry Pi)
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

from apps.carUi.runtime.car_ui_runtime_factory import create_car_ui_runtime

runtime = create_car_ui_runtime(
    Path("config/runtime.toml")
)

fm_runtime = runtime.radios.get("fm_radio")

print(runtime.remote_display)
print(runtime.auxiliary_display)
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

## Music visualizer runtime

`music_visualizer_runtime_factory.py` assembles one selectable PipeWire analysis
source, ACRCloud recognition controller, metadata cache, Spotify metadata
enricher, and music-lighting output adapter. The default capture device is
PipeWire/PulseAudio's `@DEFAULT_MONITOR@`, so visualization and recognition use
system playback rather than a microphone. The external-input choice defaults
to `@DEFAULT_SOURCE@`; both devices can be overridden independently:

The capture adapter honors an explicit `PULSE_SERVER`. When it is unset, it
automatically uses the native socket under `$XDG_RUNTIME_DIR/pulse/native` (or
`/run/user/<uid>/pulse/native`) when that socket exists.

```bash
CARUI_VISUALIZER_EXTERNAL_DEVICE=alsa_input.usb-C-Media_USB_Audio_Device-00.mono-fallback \
CARUI_VISUALIZER_INPUT=external_input \
venv/bin/python -m apps.carUi.main
```

The source retains twelve seconds of fresh PCM and exposes recognition only
after ten seconds have accumulated. Overlapping FFT samples are excluded from
the recognition buffer.

## Browser position source

Car UI can receive location from the browser on the same computer instead of
gpsd. `BrowserPositionSource` starts a small HTTP server, serves a page that
uses `navigator.geolocation.watchPosition()`, and normalizes each report into
the same `PositionState` used by other providers.

From the repository root, start Car UI with:

```bash
CARUI_POSITION_SOURCE=browser venv/bin/python -m apps.carUi.main
```

At startup it prints the local page address. Open
`http://localhost:8765/`, select **Share location**, and grant the browser's
location permission. The optional settings are:

```bash
CARUI_BROWSER_POSITION_HOST=127.0.0.1
CARUI_BROWSER_POSITION_PORT=8765
```

The relay provides:

- `GET /` — browser geolocation page
- `POST /position` — JSON position reports

To test the complete relay-to-UI path without relying on browser geolocation,
leave Car UI running and submit a simulated position from another terminal:

```bash
curl --fail-with-body \
  -H 'Content-Type: application/json' \
  -d '{"latitude":42.3314,"longitude":-83.0458,"accuracy":8.0,"speed":0}' \
  http://localhost:8765/position
```

The response should be HTTP 204 with no body, and the Car UI location display
should update. Invalid or out-of-range coordinates return HTTP 400.

Browsers treat `localhost` as a secure context. Access from a phone or another
computer generally requires HTTPS; binding the development relay to
`0.0.0.0` alone does not bypass that browser security requirement. The current
relay does not configure TLS, so same-machine browser use is the supported
development path.

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

`rotary_encoder_runtime.py` is the rotary hardware composition boundary. It converts
these driver-specific records into an ordered tuple of `RotaryEncoderIf`
objects. `input_device_runtime.py` constructs enabled keyboard and standalone
pushbutton devices. `CarUiInputRuntime` owns their adapters, polls rotary
devices, drains the common frontend event queue, and isolates individual
device failures. Startup transfers device ownership to `CarUiDependencies`,
which releases keyboards, pushbuttons, and encoders during shutdown.

Keyboard support uses Linux `/dev/input/event*` devices. Standalone GPIO
pushbuttons are constructed only on Raspberry Pi hosts; non-Pi development
hosts safely omit them.

## Test

```bash
python3 -m unittest apps.carUi.runtime.unit_test.test_car_ui_runtime_factory
python3 -m unittest apps.carUi.runtime.unit_test.test_rotary_encoder_runtime
python3 -m unittest config.integration_test.test_input_device_config
python3 -m unittest controllers.input.unit_test.test_input_adapters
python3 -m unittest frontends.common.input.unit_test.test_ui_input_event_dispatcher
python3 -m unittest controllers.navigation.unit_test.test_browser_position_source
python3 -m unittest apps.carUi.unit_test.test_position_source_factory
python3 -m unittest apps.carUi.unit_test.test_position_status_presenter
```
