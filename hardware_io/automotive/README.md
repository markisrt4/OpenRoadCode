# Automotive Hardware I/O

The `hardware_io.automotive` package contains low-level interfaces for
automotive hardware. Code in this package owns device connections and raw
device communication; it does not interpret vehicle data or implement
application behavior.

## Components

### ELM327

[`elm327`](elm327/) communicates with ELM327-compatible diagnostic devices over
a serial connection such as a Bluetooth RFCOMM device at `/dev/rfcomm0`.

```python
from hardware_io.automotive.elm327 import Elm327Device
```

## Layer Boundaries

- `hardware_io.automotive` owns physical-device access and transport details.
- `protocols.obd2` owns OBD-II requests, normalized responses, and PID decoding.
- `controllers.automotive.obd2` coordinates devices and protocol models into
  vehicle state for applications.

Keeping these layers separate allows another OBD-II transport to reuse the
protocol and controller code without depending on ELM327 command syntax.

## Installation

Automotive and Bluetooth support are optional host features. On a Raspberry
Pi 5, install both and configure the ELM327 RFCOMM binding with:

```bash
scripts/installers/host_setup.sh \
    --target rpi5 \
    --feature automotive \
    --feature bluetooth \
    --bluetooth-spp-address 12:34:5A:05:9C:54
```

The automotive feature installs `pyserial`. The Bluetooth feature installs the
BlueZ utilities used to establish and persist the RFCOMM connection.

## Decoded OBD-II Component Test

After the raw ELM327 component test succeeds, run the automotive controller
test to request and decode live vehicle values:

```bash
python3 -m controllers.automotive.obd2.component_test.obd2_cli \
    --port /dev/rfcomm0
```

The controller test uses `Elm327ObdAdapter` to translate raw, header-enabled
ELM327 output through `protocols.can.CanFrame` and into
`protocols.obd2.Obd2Response` objects. It then uses `Obd2Manager` to decode
supported PIDs and display values such as RPM, speed, temperatures, throttle
position, and control-module voltage. Stop it with `Ctrl+C`.
