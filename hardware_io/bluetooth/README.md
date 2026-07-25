# Bluetooth

The `bluetooth` component provides low-level Bluetooth communication and discovery utilities.

## BLE Scanner

The `BleScanner` scans for nearby Bluetooth Low Energy devices.

It returns discovered devices as `BleDeviceInfo` objects.

Each device may contain:

- Bluetooth address
- Device name
- Advertised local name
- Signal strength
- Advertised service UUIDs
- Manufacturer data

The scanner returns all discovered BLE devices and does not filter them by protocol or device type.

## Dependencies

There are two independent requirements:

- Python needs a compatible version of [`bleak`](https://pypi.org/project/bleak/).
- Linux needs BlueZ and a Bluetooth Low Energy adapter.

The Raspberry Pi model does not determine which Python package to install. It
only determines whether Bluetooth hardware is built in. Raspberry Pi 3 and
newer boards, plus the Zero W and Zero 2 W, have built-in Bluetooth. Other
boards require a USB Bluetooth adapter with BLE support. In practice, the
Raspberry Pi OS release and its Python and BlueZ versions matter more than the
board model.

### Python

This component requires Python 3.10 or newer. The current `bleak` release also
requires Python 3.10 or newer. Check the interpreter before installing:

```bash
python3 --version
```

On Raspberry Pi OS Bookworm and newer, install Python packages in a virtual
environment:

```bash
sudo apt update
sudo apt install python3-venv
python3 -m venv .venv
source .venv/bin/activate
python -m pip install bleak
```

On an older OS that does not enforce externally managed Python environments, a
virtual environment is still recommended. Do not use
`--break-system-packages` to modify Raspberry Pi OS's system Python.

Python 3.8 and 3.9 can install the older `bleak==0.22.3`, but they cannot run
this component because the component itself uses Python 3.10 language and
standard-library features. Upgrade Python or the OS instead of pinning an old
`bleak` release.

### Linux and Raspberry Pi OS

Current `bleak` releases require BlueZ 5.55 or newer. On Debian, Ubuntu, or
Raspberry Pi OS, install the Bluetooth service and command-line tools with:

```bash
sudo apt update
sudo apt install bluez bluetooth
```

Check both BlueZ and the adapter before scanning:

```bash
bluetoothctl --version
bluetoothctl show
```

If `bluetoothctl show` reports no controller, confirm that the board has
built-in Bluetooth or attach a BLE-capable USB adapter. Also check that the
controller is not blocked:

```bash
rfkill list bluetooth
sudo rfkill unblock bluetooth
sudo systemctl enable --now bluetooth
```

Very old Raspberry Pi OS images may ship BlueZ older than 5.55 and Python older
than 3.10. For those systems, upgrading Raspberry Pi OS is the supported path;
changing only the `bleak` version does not update the system Bluetooth stack.

## Component Test

A BLE scanner CLI component test is provided in the `component_test` directory.

```text
bluetooth/
├── __init__.py
├── ble_scanner.py
├── README.md
└── component_test/
    ├── __init__.py
    └── ble_scan_cli.py
```

Run the component test from the project root:

```bash
python3 -m hardware_io.bluetooth.component_test.ble_scan_cli
```

The default scan duration is 10 seconds.

A different scan duration can be specified using `--timeout`:

```bash
python3 -m hardware_io.bluetooth.component_test.ble_scan_cli \
    --timeout 15
```

Example output:

```text
Scanning for Bluetooth Low Energy devices for 10.0 seconds...

============================================================
0A:FE:EF:0C:57:3C
Name: None
Local name: None
RSSI: -56
Service UUIDs: []
Manufacturer data: {}
============================================================
12:34:5A:05:9C:54
Name: KONNWEI
Local name: KONNWEI
RSSI: -68
Service UUIDs: ['00001101-0000-1000-8000-00805f9b34fb']
Manufacturer data: {}
============================================================
Found 2 BLE device(s).
```

## Design

The Bluetooth component provides generic Bluetooth discovery and communication functionality.

It does not identify devices for a specific protocol or assign meaning to discovered devices.
