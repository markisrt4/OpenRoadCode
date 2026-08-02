# Inertial Measurement Unit (IMU)

The `hardware_io.imu` package provides a small interface for reading linear
acceleration and angular velocity from an inertial measurement unit. The
included `Mpu6050Imu` implementation communicates with an MPU-6050 over I2C.

Measurements are returned as immutable `Vector3` values in SI units:

- Acceleration: meters per second squared (`m/s²`)
- Angular velocity: radians per second (`rad/s`)

The package reports raw sensor measurements. Calibration, filtering, attitude
estimation, and application behavior belong in higher-level components.

## Hardware Setup

Connect the MPU-6050 to the host's I2C bus:

| MPU-6050 | Raspberry Pi |
| --- | --- |
| VCC | 3.3 V |
| GND | Ground |
| SDA | I2C SDA |
| SCL | I2C SCL |

Check the voltage requirements of the specific breakout board before wiring
it. Enable I2C on Raspberry Pi OS:

```bash
sudo raspi-config
```

Choose **Interface Options**, enable **I2C**, and reboot if prompted. Verify
that the device is visible:

```bash
i2cdetect -y 1
```

The default MPU-6050 address is `0x68`. Boards that expose the AD0 pin can
typically use `0x69` when AD0 is high.

## Installation

From the project root, install the MPU-6050 feature bundle:

```bash
scripts/installers/host_setup.sh --feature mpu6050
```

This installs `i2c-tools`, Adafruit Blinka, and the Adafruit CircuitPython
MPU-6050 driver. To install only the Python dependencies in an existing
environment:

```bash
python3 -m pip install adafruit-blinka adafruit-circuitpython-mpu6050
```

## Usage

```python
from hardware_io.imu import Mpu6050Imu


imu = Mpu6050Imu()
imu.start()

try:
    acceleration = imu.get_acceleration_mps2()
    angular_velocity = imu.get_angular_velocity_rad_s()

    print(
        f"acceleration: x={acceleration.x:.3f}, "
        f"y={acceleration.y:.3f}, z={acceleration.z:.3f} m/s²"
    )
    print(
        f"angular velocity: x={angular_velocity.x:.4f}, "
        f"y={angular_velocity.y:.4f}, "
        f"z={angular_velocity.z:.4f} rad/s"
    )
finally:
    imu.stop()
```

Call `start()` before reading the sensor and `stop()` when finished. Repeated
calls to `start()` are safe. Reading before startup or after shutdown raises a
`RuntimeError`.

To use a non-default address:

```python
imu = Mpu6050Imu(address=0x69)
```

An existing CircuitPython-compatible I2C bus can also be shared:

```python
import board

from hardware_io.imu import Mpu6050Imu


i2c = board.I2C()
imu = Mpu6050Imu(i2c_bus=i2c)
```

When a bus is supplied by the caller, `stop()` leaves that bus open. When the
driver creates the default bus, `stop()` releases it.

## Interface

Hardware-independent consumers can depend on `ImuIf`:

```python
from hardware_io.imu import ImuIf


def read_motion(imu: ImuIf) -> None:
    acceleration = imu.get_acceleration_mps2()
    angular_velocity = imu.get_angular_velocity_rad_s()
```

`ImuIf` defines:

- `start()` — initialize the device
- `stop()` — release owned resources
- `is_connected()` — report whether initialization succeeded
- `get_acceleration_mps2()` — return an acceleration `Vector3`
- `get_angular_velocity_rad_s()` — return an angular-velocity `Vector3`

## Component Test

Run the live hardware test from the project root:

```bash
python3 -m hardware_io.imu.component_test.imu_cli
```

The CLI prints acceleration and angular velocity every 0.2 seconds. Press
`Ctrl+C` to stop it.

Read one sample and exit:

```bash
python3 -m hardware_io.imu.component_test.imu_cli --once
```

Use a different address or sampling interval:

```bash
python3 -m hardware_io.imu.component_test.imu_cli \
    --address 0x69 \
    --interval 0.5
```

Run the CLI with `--help` to see all options.

## Troubleshooting

- If `i2cdetect` does not show the sensor, check power, ground, SDA, SCL, the
  selected I2C bus, and whether I2C is enabled.
- If initialization fails at `0x68`, scan the bus and try `--address 0x69` if
  that is the address reported.
- If Python reports a missing MPU-6050 or `board` module, install the
  dependencies listed above in the same environment used to run the CLI.
- If access to the I2C device is denied, check the permissions and group
  ownership of `/dev/i2c-*` for the host system.
