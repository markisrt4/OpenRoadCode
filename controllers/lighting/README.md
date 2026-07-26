# Lighting Controllers

The `controllers.lighting` package provides application-agnostic interfaces,
state models, test doubles, and hardware adapters for lighting devices.

## Package layout

```text
controllers/lighting/
├── __init__.py
├── lighting_controller_if.py
├── lighting_types.py
├── lighting_controller_stub.py
├── dummy_lighting_controller.py
├── adapters/
│   └── leddmx_controller.py
├── parsers/
│   └── leddmx_config_parser.py
└── component_test/
    └── test_dummy_lighting_controller.py

protocols/leddmx/
└── leddmx_protocol.py

hardware_io/bluetooth/
├── ble_gatt_transport_if.py
└── bleak_gatt_transport.py

config/lighting/
└── leddmx.toml
```

## Controller choices

### `LightingControllerStub`

A silent deterministic implementation of `LightingControllerIf`.

Use it when a consumer requires a lighting controller but the test does not
care about lighting behavior. Commands immediately return successful completed
futures and do not mutate state.

### `DummyLightingController`

A stateful in-memory emulator.

Use it for UI development, component tests, and demonstrations where callers
need to inspect `LightingState` after commands are issued.

### `LedDmxController`

The protocol controller for LEDDMX-compatible lights. It owns a background
asyncio event loop and exposes thread-friendly
`concurrent.futures.Future` objects to synchronous callers such as Tkinter.
It receives a generic `BleGattTransportIf`; it does not import Bleak, perform
discovery, or manage GATT clients itself.

`LightingState.connection_status`, `device_address`, and
`last_connection_error` describe the real BLE transport. LEDDMX does not
provide authoritative output readback, so power, color, brightness, pattern,
and music fields are only the most recently requested settings.

The application owns the controller for its full lifetime. Individual panels
must not close it when navigating between screens.

## Python dependency

Install Bleak:

```bash
python3 -m pip install bleak
```

Bleak is used only by the `hardware_io.bluetooth` GATT transport.

## Linux system dependencies

Bleak's Linux backend communicates with BlueZ over D-Bus. Install BlueZ and
ensure the Bluetooth service is running.

Debian, Ubuntu, and Raspberry Pi OS:

```bash
sudo apt update
sudo apt install bluez
sudo systemctl enable --now bluetooth
```

Confirm the adapter is visible:

```bash
bluetoothctl list
```

The current Bleak documentation requires a Linux distribution with BlueZ
5.55 or newer.

## LEDDMX configuration

The BLE service UUID, write characteristic UUID, discovery exclusions, and
timing options are stored in:

```text
PROJECT_ROOT/config/lighting/leddmx.toml
```

Example:

```toml
[bluetooth]
# Optional, but recommended after identifying the controller:
# address = "AA:BB:CC:DD:EE:FF"
service_uuid = "0000ffe0-0000-1000-8000-00805f9b34fb"
characteristic_uuid = "0000ffe1-0000-1000-8000-00805f9b34fb"
excluded_service_uuids = [
    "00001101-0000-1000-8000-00805f9b34fb",
]
write_with_response = false
command_delay_seconds = 0.05
reconnect_delay_seconds = 0.25
scan_timeout_seconds = 15.0
candidate_connect_timeout_seconds = 8.0

[discovery]
excluded_name_fragments = ["konnwei"]
```

Load it explicitly:

```python
from controllers.lighting.parsers.leddmx_config_parser import load_leddmx_config
from controllers.lighting.adapters.leddmx_controller import LedDmxController
from hardware_io.bluetooth.bleak_gatt_transport import BleakGattTransport

config = load_leddmx_config()
transport = BleakGattTransport(
    address=config.address,
    characteristic_uuid=config.characteristic_uuid,
)
controller = LedDmxController(transport)
```

When `address` is omitted, the adapter scans nearby BLE devices and checks for
the configured write characteristic.

## Basic usage

```python
from controllers.lighting import RgbColor
from apps.carUi.runtime.lighting_runtime_factory import (
    create_lighting_controller,
)

controller = create_lighting_controller(project_root=PROJECT_ROOT)

try:
    controller.connect().result(timeout=20)
    controller.set_power(True).result(timeout=5)
    controller.set_color(
        RgbColor(255, 120, 0)
    ).result(timeout=5)
    controller.set_brightness(75).result(timeout=5)
finally:
    controller.close()
```


## Testing

```bash
python3 -m unittest     controllers.lighting.component_test.test_dummy_lighting_controller
```

Scan first, then directly probe a likely device:

```bash
python3 -m hardware_io.bluetooth.component_test.ble_scan_cli --timeout 15
python3 -m controllers.lighting.component_test.leddmx_cli \
    --address AA:BB:CC:DD:EE:FF
```

Once connection succeeds, safely verify a command:

```bash
python3 -m controllers.lighting.component_test.leddmx_cli \
    --address AA:BB:CC:DD:EE:FF \
    --power on
```

For testing several commands, keep one connection open. Some LEDDMX
controllers take longer than 15 seconds to advertise again after a disconnect:

```bash
python3 -m controllers.lighting.component_test.leddmx_cli --interactive
```

At the prompt, use `on`, `off`, `color FF0000`, `color 00FF00`, `state`, and
`quit`.

Put the confirmed address in `config/lighting/leddmx.toml` so Car UI connects
directly. If no address is configured, characteristic-based discovery remains
available as a fallback.
