# Environmental Hardware I/O

The `hardware_io.environmental` package provides hardware interfaces and concrete implementations for environmental sensors such as barometric pressure sensors.

The goal of this package is to expose **raw environmental measurements** from physical devices while remaining independent of any application, user interface, or higher-level processing. Environmental calculations such as weather prediction, altitude estimation, sensor fusion, or trend analysis belong in higher-level controllers.

## Design Goals

- Hardware abstraction through common interfaces
- Application-independent design
- Consistent units across all implementations
- Support multiple sensor vendors and communication methods
- Simple, primitive getter-based API
- Suitable for embedded and Raspberry Pi platforms

## Current Sensors

| Device | Interface | Measurements |
|---------|-----------|--------------|
| BMP388 | I²C | Atmospheric pressure, temperature |
| BMP390 | I²C | Atmospheric pressure, temperature |

Future implementations may include:

- BMP280
- BME280
- BME680
- SHT31
- Other environmental sensors

## Directory Layout

```text
environmental/
├── __init__.py
├── barometric_sensor_if.py
├── bmp388.py
├── bmp390.py
├── component_test/
└── README.md
```

## Responsibilities

This module is responsible for:

- Initializing environmental sensors
- Reading pressure measurements
- Reading temperature measurements
- Managing hardware resources
- Reporting sensor status

This module is **not** responsible for:

- Altitude calculations
- Weather forecasting
- Pressure trend analysis
- Sensor fusion
- Navigation
- Data logging
- User interface

Those responsibilities belong to higher-level controllers.

## Units

The hardware interfaces expose measurements using SI units.

| Measurement | Unit |
|-------------|------|
| Pressure | Pascals (Pa) |
| Temperature | Degrees Celsius (°C) |

Returning consistent units allows higher-level software to perform calculations without needing device-specific conversions.

## Example

```python
from hardware_io.environmental import Bmp388

sensor = Bmp388()

try:
    sensor.start()

    pressure = sensor.get_pressure_pa()
    temperature = sensor.get_temperature_c()

    print(f"Pressure: {pressure:.1f} Pa")
    print(f"Temperature: {temperature:.1f} °C")

finally:
    sensor.stop()
```

## Raspberry Pi Dependencies

The BMP388 and BMP390 implementations use Adafruit's CircuitPython driver.

```bash
python3 -m pip install \
    adafruit-blinka \
    adafruit-circuitpython-bmp3xx
```

The project installer can install the same system and Python dependencies.
Choose exactly one driver:

```bash
scripts/installers/host_setup.sh --feature bmp388
```

or:

```bash
scripts/installers/host_setup.sh --feature bmp390
```

The interactive `host_setup_tui.sh` installer provides the same choice under
**Environmental sensors**.

## Hardware Setup

Connect the BMP388 or BMP390 breakout to the Raspberry Pi I²C bus:

| Sensor | Raspberry Pi |
|--------|--------------|
| VIN/VCC | 3.3 V |
| GND | Ground |
| SCL | I²C SCL |
| SDA | I²C SDA |

Check the voltage requirements of the specific breakout board before wiring
it. Enable I²C through `sudo raspi-config`, then verify that the sensor is
visible:

```bash
i2cdetect -y 1
```

The default address is `0x77`. A board configured with SDO low commonly
appears at `0x76`.

## Component Testing

Run the live BMP388 hardware test from the project root:

```bash
python3 -m hardware_io.environmental.component_test.barometric_cli
```

The CLI reports pressure in pascals and temperature in degrees Celsius once
per second. Press `Ctrl+C` to stop it.

Read one sample and exit:

```bash
python3 -m hardware_io.environmental.component_test.barometric_cli --once
```

Use address `0x76` or change the sampling interval:

```bash
python3 -m hardware_io.environmental.component_test.barometric_cli \
    --address 0x76 \
    --interval 0.5
```

The same component test can exercise a BMP390:

```bash
python3 -m hardware_io.environmental.component_test.barometric_cli \
    --sensor bmp390
```

Run the CLI with `--help` to see all options.

## Troubleshooting

- If `i2cdetect` does not show `76` or `77`, check power, ground, SDA, SCL,
  and whether I²C is enabled.
- If initialization fails at `0x77`, scan the bus and pass `--address 0x76`
  when that is the reported address.
- If Python reports a missing `board` or `adafruit_bmp3xx` module, install the
  dependencies above in the same Python environment used to run the test.
- If access to `/dev/i2c-*` is denied, check the device permissions and the
  current user's group membership.

## Future Expansion

This package is intended to grow as additional environmental sensors are supported.

Potential future capabilities include:

- Humidity sensors
- Ambient light sensors
- Air quality sensors
- Carbon dioxide sensors
- Volatile organic compound (VOC) sensors
- Multiple sensor implementations sharing common interfaces

The public interfaces should remain stable while allowing additional hardware implementations to be added without affecting client applications.
