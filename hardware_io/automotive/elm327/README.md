# ELM327 Device

The `Elm327Device` provides low-level serial communication with an
ELM327-compatible automotive diagnostic device. It sends raw ELM327 commands
and returns `Elm327Response` objects.

OBD-II request modeling and PID decoding belong in `protocols.obd2`. An adapter
that translates between those protocol models and this device belongs in
`controllers.automotive`.

## Connection

The default connection is `/dev/rfcomm0` at 38400 baud. Both values can be
configured when creating the device:

```python
from hardware_io.automotive.elm327 import Elm327Device


device = Elm327Device(port="/dev/rfcomm0", baud=38400)

try:
    device.connect()
    response = device.send_command("ATI")
    print(response.raw)
finally:
    device.disconnect()
```

## Initialization

On connection, the device sends `ATZ`, `ATE0`, `ATL0`, `ATS0`, `ATH1`, and
`ATSP0` to reset and configure the ELM327.

Initialization commands use a settling delay. Normal commands do not use a
fixed delay; the device starts reading immediately and completes the command
when it receives the ELM327 `>` prompt.

## Dependency

The device requires `pyserial`:

```bash
python3 -m pip install pyserial
```

## Bluetooth RFCOMM

A Bluetooth Classic ELM327 uses the Serial Port Profile (SPP). BlueZ exposes
that connection as an RFCOMM serial device such as `/dev/rfcomm0`, which
`Elm327Device` opens through `pyserial`.

Use the setup helper with the address reported by the Bluetooth scanner:

```bash
scripts/installers/setup_rfcomm0.sh \
    --address 12:34:5A:05:9C:54
```

The helper:

1. Checks whether the device is already paired and pairs it when needed.
2. Marks the device as trusted.
3. Disconnects any connection held by `bluetoothctl`.
4. Uses SDP to discover the Serial Port Profile channel.
5. Installs and starts a systemd service that actively maintains
   `/dev/rfcomm0` now and on future boots, restarting the RFCOMM connection if
   it drops.
6. Warns if the current user does not belong to `dialout`.

Specify the channel only when SDP discovery fails:

```bash
scripts/installers/setup_rfcomm0.sh \
    --address 12:34:5A:05:9C:54 \
    --channel 1
```

The host installer can install the feature and configure RFCOMM together:

```bash
scripts/install_arm64.sh \
    --feature elm327 \
    --elm327-address 12:34:5A:05:9C:54
```

Pairing and RFCOMM configuration are host responsibilities. `Elm327Device`
intentionally begins at the serial-device boundary and does not invoke
`bluetoothctl`, `sdptool`, or `rfcomm` itself.

## Component Test

The component test opens a real serial connection, initializes the ELM327, and
lets you send raw adapter or OBD-II commands. It does not emulate an adapter and
does not decode OBD-II PID values.

Use this raw test first to separate serial, RFCOMM, and ELM327 problems from
OBD-II parsing problems. Once commands such as `ATI` and `0100` work, use the
[decoded automotive component test](../README.md#decoded-obd-ii-component-test)
to exercise `Elm327ObdAdapter` and the PID decoders.

### Prerequisites

Before running the test:

1. Power the ELM327 and, for a Bluetooth model, pair it with the host.
2. Establish its RFCOMM serial device, such as `/dev/rfcomm0`.
3. Confirm that the device exists and that your user can access it:

```bash
ls -l /dev/rfcomm0
```

Serial devices are commonly assigned to the `dialout` group. If necessary, add
your user to that group, then log out and back in:

```bash
sudo usermod -aG dialout "$USER"
```

Activate the project virtual environment so that `pyserial` and the project
packages are available:

```bash
source venv/bin/activate
```

### Interactive Mode

From the project root, run:

```bash
python3 -m hardware_io.automotive.elm327.component_test.elm327_cli
```

The test connects to `/dev/rfcomm0` at 38400 baud by default. After the ELM327
initialization commands succeed, enter commands at the prompt:

```text
Connecting to ELM327 on /dev/rfcomm0 at 38400 baud...
Connected. Enter an ELM327 command, or 'quit' to stop.

elm327> ATI

Command: ATI
Response:
  ELM327 v1.5

Raw response:
'ELM327 v1.5\r>'
elm327> quit
```

Useful initial commands include:

- `ATI` — report the adapter identification string.
- `ATDP` — report the selected vehicle protocol.
- `0100` — request the vehicle's supported Mode 01 PIDs.

Enter `quit` or `exit`, press `Ctrl+D`, or press `Ctrl+C` to disconnect and
stop the test.

### Single-Command Mode

Use `--command` to connect, send one command, print its response, and exit:

```bash
python3 -m hardware_io.automotive.elm327.component_test.elm327_cli \
    --command ATI
```

Use `--port` and `--baud` for an adapter with different serial settings:

```bash
python3 -m hardware_io.automotive.elm327.component_test.elm327_cli \
    --port /dev/ttyUSB0 \
    --baud 9600 \
    --command ATI
```

Display all command-line options with:

```bash
python3 -m hardware_io.automotive.elm327.component_test.elm327_cli --help
```

### Troubleshooting

- `Unable to connect` usually means the serial path is wrong, RFCOMM is not
  connected, the user lacks device permission, or another process owns the
  port.
- An empty response means the serial connection opened but the adapter did not
  return data before the configured timeout.
- `NO DATA` is an ELM327 response, not a connection failure. It can mean the
  vehicle is off, no ECU answered, or the requested PID is unsupported.
- Some inexpensive adapters advertise an inaccurate ELM327 version string, so
  `ATI` identifies what the adapter claims rather than verifying its firmware.
