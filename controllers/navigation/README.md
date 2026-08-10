# Navigation Controller

The `controllers.navigation` package converts motion-sensor measurements into
a higher-level vehicle motion state. `NavigationController` provides:

- Relative heading in degrees
- Filtered pitch and roll in degrees
- Raw acceleration in meters per second squared
- Gravity-compensated linear acceleration in meters per second squared
- Raw angular velocity in radians per second
- A timestamp for each sample

The controller owns sampling, timing, lifecycle, and state creation. Orientation
math is delegated to an `OrientationEstimatorIf`, allowing different sensor
combinations and estimation algorithms without changing the controller.

## Controller Implementations

Applications should depend on `NavigationControllerIf`.

- `NavigationController` processes live motion and an optional position source.
- `NavigationControllerStub` provides deterministic in-memory state for demos
  and UI development.
- `SimulatedNavigationController` provides changing attitude, acceleration,
  angular velocity, and GPS data for interactive development without hardware.
- `UnconfiguredNavigationController` reports `is_available == False`, exposes
  a reason through `status_message`, and raises for navigation operations
  rather than fabricating position or motion.

All implementations expose the same lifecycle, heading reset, stationary
calibration, position update, and state-reading contract.

The multi-screen terminal frontend selects the simulator with no sensor,
gpsd, or serial dependencies:

```bash
venv/bin/python -m apps.carTui.main --demo
```

## Adapters

`NavigationController` depends on navigation-facing interfaces rather than
hardware drivers:

```text
Mpu6050Imu -> Mpu6050NavigationAdapter -> NavigationSensorIf
GpsReader  -> GpsdPositionSource       -> PositionSourceIf
```

`Mpu6050NavigationAdapter` converts the MPU-6050 acceleration and angular
velocity readings into a normalized `MotionSample`. Future motion sensors can
provide their own `NavigationSensorIf` adapters.

`GpsdPositionSource` converts asynchronous `GpsData` reports into normalized
`PositionState` updates. `BrowserPositionSource` receives the browser
Geolocation API through a local HTTP relay and produces the same state type.
Position input is optional.

CarUi decorates either provider with `PersistentPositionSource`. It publishes
a recent last-known fix immediately at startup, then replaces it with live
updates. Only valid live 2D/3D fixes are stored through `PositionSnapshotCache`
and the generic `controllers.cache` storage layer. Restored states have
`is_cached == True`; speed, course, and satellite counts are not restored.

The default snapshot path and maximum age are:

```text
~/.cache/openroadcode/position
604800 seconds (7 days)
```

Override them with `CARUI_POSITION_CACHE_DIRECTORY` and
`CARUI_POSITION_CACHE_MAX_AGE_SECONDS`, or disable persistence with
`CARUI_POSITION_CACHE=0`.

## Orientation Estimators

`ComplementaryOrientationEstimator` is the current default. It supports
six-axis sensors such as the MPU-6050 by combining accelerometer tilt with
integrated gyroscope motion.

Because that estimator has no absolute reference, its heading starts at zero
and drifts over time. This is a limitation of the default estimator, not of
`NavigationController`.

Future estimators can implement `OrientationEstimatorIf` and incorporate
additional inputs such as:

- A magnetometer
- GNSS course while moving
- Vehicle heading data
- A sensor with onboard orientation fusion

Pass a different estimator with `orientation_estimator=`. An estimator may own
and manage any additional sensor dependencies it needs through its `start()`
and `stop()` methods.

## Coordinate Convention

The orientation math assumes the IMU is mounted with:

- Positive X pointing forward
- Positive Y pointing to the right
- Positive Z pointing up

With this mounting, positive pitch raises the front, positive roll lowers the
right side, and positive heading rotation is around the Z axis. A differently
mounted sensor should be transformed into this coordinate system before its
measurements reach the controller.

## Usage

```python
from controllers.navigation import (
    Mpu6050NavigationAdapter,
    NavigationController,
)
from hardware_io.imu import Mpu6050Imu


sensor = Mpu6050NavigationAdapter(Mpu6050Imu())
navigation = NavigationController(sensor=sensor)
navigation.start()

try:
    state = navigation.read_state()

    print(
        f"heading={state.heading_deg:.1f}° "
        f"pitch={state.pitch_deg:.1f}° "
        f"roll={state.roll_deg:.1f}°"
    )
    print(f"acceleration={state.acceleration_mps2}")
finally:
    navigation.stop()
```

To include the existing gpsd source:

```python
from controllers.navigation import (
    GpsdPositionSource,
    Mpu6050NavigationAdapter,
    NavigationController,
)
from hardware_io.gps import GpsReader
from hardware_io.imu import Mpu6050Imu


navigation = NavigationController(
    sensor=Mpu6050NavigationAdapter(Mpu6050Imu()),
    gps_source=GpsdPositionSource(GpsReader()),
)
```

When GPS has published a report, it is included in the navigation state:

```python
state = navigation.read_state()

if state.gps is not None and state.gps.has_fix:
    print(state.gps.latitude_deg, state.gps.longitude_deg)
    print(state.gps.speed_mps, state.gps.course_deg)
```

`GpsState.received_at` identifies when the navigation adapter received the
report, allowing consumers to reject stale GPS data.

`PositionState` is the provider-neutral name. `GpsState` remains available as
a compatibility alias for existing consumers.

Call `read_state()` at a steady interval. The filter accounts for elapsed
time, but consistent sampling produces better results.

Use `reset_heading()` to establish a new relative heading:

```python
navigation.reset_heading()
```

`acceleration_mps2` is the raw sensor acceleration and includes gravity.
`linear_acceleration_mps2` subtracts the gravity vector estimated from the
current pitch and roll. The compensated value is only as accurate as the
orientation estimate, sensor calibration, and mounting alignment.

## Stationary Calibration

After starting the controller, keep the sensor and vehicle still and collect a
stationary calibration:

```python
navigation.start()
calibration = navigation.calibrate_stationary()
```

The default calibration averages 100 samples. It estimates gyroscope zero-rate
bias and normalizes the stationary accelerometer magnitude to standard gravity.
The raw acceleration remains available for diagnostics; calibration is applied
to orientation, angular velocity, and linear acceleration calculations.

Calibration cannot distinguish every accelerometer-axis bias from an unknown
mounting angle. For best results, mount the sensor rigidly, avoid vibration
during calibration, and perform a more complete multi-position calibration if
higher accuracy is eventually required.

## Component Test

The navigation component test runs the full path from the MPU-6050 hardware
driver through `NavigationController` and the default complementary estimator.
Run it from the project root:

```bash
python3 -m controllers.navigation.component_test.navigation_cli
```

The CLI displays heading, pitch, roll, acceleration, and angular velocity every
0.1 seconds. Press `Ctrl+C` to stop it.

Read one state and exit:

```bash
python3 -m controllers.navigation.component_test.navigation_cli --once
```

Use a different I2C address or sample interval:

```bash
python3 -m controllers.navigation.component_test.navigation_cli \
    --address 0x69 \
    --interval 0.2
```

The default estimator can also be tuned with
`--filter-time-constant SECONDS`. A larger value trusts short-term gyroscope
motion longer; a smaller value corrects pitch and roll toward accelerometer
tilt more quickly:

```bash
python3 -m controllers.navigation.component_test.navigation_cli \
    --filter-time-constant 1.0
```

Run the CLI with `--help` for all options. The heading shown by this test is
relative because the default estimator does not yet use an absolute heading
source.

If gpsd is already running, include its latest state in the output:

```bash
python3 -m controllers.navigation.component_test.navigation_cli --gps
```

Use `--gps-host` and `--gps-port` for a non-default gpsd endpoint.

## Position Integration

Applications and controllers consume `PositionSourceIf`, independently of how
the position was obtained. The `gpsd` connection remains in `hardware_io.gps`,
while `GpsdPositionSource` adapts its reports. `BrowserPositionSource` provides
the same contract from browser geolocation.

GPS can contribute:

- Position and altitude
- Ground speed
- Course over ground while the vehicle is moving
- A low-frequency correction for drifting relative heading

Course over ground is not the same as the direction the vehicle is facing. It
is unreliable while stopped or moving very slowly, and it can differ from
vehicle heading during reversing or sideways motion. For that reason, GPS
course should be treated as a conditional fusion input rather than replacing
the orientation estimator.

`GpsdPositionSource` adds normalized position/course state to
`NavigationState`. A later GPS-aware `OrientationEstimatorIf` can use valid,
sufficiently fast course updates for drift correction; the current default
estimator intentionally does not fuse GPS course into heading yet.
