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
│   └── leddmx_bluetooth_controller.py
├── parsers/
│   └── leddmx_config_parser.py
└── component_test/
    └── test_dummy_lighting_controller.py

protocols/leddmx/
└── leddmx_protocol.py

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

### `LedDmxBluetoothController`

The hardware adapter for LEDDMX-compatible Bluetooth Low Energy controllers.
It owns a background asyncio event loop and exposes thread-friendly
`concurrent.futures.Future` objects to synchronous callers such as Tkinter.

## Python dependency

Install Bleak:

```bash
python3 -m pip install bleak
```

Bleak is the Bluetooth Low Energy GATT client used by the LEDDMX adapter.

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
from controllers.lighting.adapters import LedDmxBluetoothController

config = load_leddmx_config()

controller = LedDmxBluetoothController(
    address=None,
    config=config,
)
```

When `address` is omitted, the adapter scans nearby BLE devices and checks for
the configured write characteristic.

## Basic usage

```python
from controllers.lighting import RgbColor
from controllers.lighting.adapters import LedDmxBluetoothController

controller = LedDmxBluetoothController()

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

The protocol and configuration parser should also have independent tests as
the package grows.

## Structured logging

`lighting.bluetooth` records command execution, connection transitions, write
retry and recovery; `lighting.ui` retains request IDs through futures and UI
completion callbacks. `lighting.reactive` records enable changes and output
failures/recovery while routine music-driven commands stay DEBUG. An unconfigured
backend reports a fixed availability state. Records exclude discovery names, BLE
addresses/UUIDs, packets, RGB/brightness values and exception messages. Existing
BLE retry timing is preserved. See the
[device validation guide](../../common/logging/DEVICE_VALIDATION.md).
