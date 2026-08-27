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
│   ├── leddmx_controller.py
│   └── leddmx_bluetooth_controller.py  # legacy compatibility only
├── parsers/
│   └── leddmx_config_parser.py
└── component_test/
    └── leddmx_smoke_cli.py

hardware_io/bluetooth/
├── ble_gatt_transport_if.py
└── bleak_gatt_transport.py

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

### `LedDmxController`

The transport-neutral LEDDMX controller. It translates lighting operations
into LEDDMX packets and sends them through an injected `BleGattTransportIf`.
The production runtime composes it with `BleakGattTransport`. This separation
keeps device protocol logic independent of Bleak and makes it testable without
Bluetooth hardware.

`LedDmxBluetoothController` is the older combined implementation. Its module
remains for source compatibility, but new code should use `LedDmxController`
and a generic BLE GATT transport.

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
from pathlib import Path
from apps.common.lighting_runtime_factory import create_lighting_controller

controller = create_lighting_controller(
    project_root=Path.cwd(),
    address=None,
)
```

When `address` is omitted, the adapter scans nearby BLE devices and checks for
the configured write characteristic.

## Basic usage

```python
from pathlib import Path
from apps.common.lighting_runtime_factory import create_lighting_controller
from controllers.lighting import RgbColor

controller = create_lighting_controller(project_root=Path.cwd())

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

Run automated lighting and transport tests without hardware:

```bash
python3 -m pytest -q controllers/lighting hardware_io/bluetooth/component_test
```

Run the guarded physical smoke test at low brightness. Omit `--address` to
discover a controller exposing the configured characteristic:

```bash
python3 -m controllers.lighting.component_test.leddmx_smoke_cli \
  --confirm-hardware \
  --address AA:BB:CC:DD:EE:FF
```

The test turns the light off in cleanup, including when a command fails.
