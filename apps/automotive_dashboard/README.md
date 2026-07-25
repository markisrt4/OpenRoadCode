# Automotive Dashboard

The automotive dashboard displays live vehicle state decoded through an
ELM327-compatible OBD-II adapter. Both interfaces use the same
`Elm327ObdAdapter` and `Obd2Manager` controller path.

## Terminal Dashboard

The terminal dashboard uses Python's built-in curses support and requires no
graphical desktop:

```bash
python3 -m apps.automotive_dashboard.vehicle_tui \
    --port /dev/rfcomm0
```

It displays connection status, RPM, speed, boost, temperatures, throttle,
engine load, pressures, airflow, fuel level, and module voltage. Unsupported or
unavailable values appear as `--`.

Controls:

- `q` exits and closes the ELM327 connection.
- `r` retries after a connection failure.

Use `--baud` for a device with a non-default serial rate and `--refresh` to
control the delay between complete vehicle-state polls:

```bash
python3 -m apps.automotive_dashboard.vehicle_tui \
    --port /dev/rfcomm0 \
    --baud 38400 \
    --refresh 0.1 \
    --slow-refresh 5
```

RPM, speed, throttle, engine load, accelerator position, and manifold pressure
are requested every fast poll. Temperatures, fuel, airflow, barometric
pressure, and module voltage are cached and refreshed on the slower interval.
The manager also discovers supported PIDs when it connects and does not request
values the vehicle reports as unsupported.

The actual fast update rate is limited by the time needed for the supported
sequential OBD-II requests; `--refresh` is an additional delay after each poll.

## Navigation Terminal Dashboard

The navigation TUI displays live heading, pitch, roll, acceleration, and
angular velocity from the navigation controller:

```bash
python3 -m apps.automotive_dashboard.navigation_tui
```

It uses the full navigation path:

```text
Mpu6050Imu -> Mpu6050NavigationAdapter -> NavigationController
```

Controls:

- `q` exits and closes all configured navigation sources.
- `h` resets the relative heading to zero.
- `c` performs a stationary sensor calibration.
- `a` cycles the acceleration display through raw, linear, and both.
- `r` retries after a connection failure.

Use a different MPU-6050 address, display refresh rate, or complementary-filter
time constant with:

```bash
python3 -m apps.automotive_dashboard.navigation_tui \
    --address 0x69 \
    --refresh 0.1 \
    --filter-time-constant 0.5 \
    --acceleration-mode both
```

Raw acceleration includes gravity and is useful for sensor diagnostics. Linear
acceleration subtracts the gravity vector estimated from pitch and roll, so a
stationary, calibrated sensor should report approximately zero on all axes.
The linear result is sensitive to mounting alignment, sensor bias, vibration,
and orientation-estimation error.

Before pressing `c`, park the vehicle on a stable surface and keep it completely
still. Calibration averages accelerometer and gyroscope readings, removes the
measured gyroscope zero-rate bias, and normalizes the stationary gravity
magnitude. It also resets the orientation estimate and relative heading.

Run calibration automatically after connecting with:

```bash
python3 -m apps.automotive_dashboard.navigation_tui --calibrate
```

The defaults use 100 samples spaced 0.01 seconds apart. They can be adjusted:

```bash
python3 -m apps.automotive_dashboard.navigation_tui \
    --calibrate \
    --calibration-samples 200 \
    --calibration-interval 0.01
```

To include position, altitude, speed, course over ground, and GPS fix
information from the existing gpsd service:

```bash
python3 -m apps.automotive_dashboard.navigation_tui --gps
```

The default gpsd endpoint is `127.0.0.1:2947`. Override it when needed:

```bash
python3 -m apps.automotive_dashboard.navigation_tui \
    --gps \
    --gps-host 127.0.0.1 \
    --gps-port 2947
```

GPS course is displayed but is not yet fused into the default relative-heading
estimate.

## Graphical Dashboard

The Tk dashboard remains available with:

```bash
python3 -m apps.automotive_dashboard.main \
    --port /dev/rfcomm0
```

## Navigation Wireframe Visualizer

The navigation visualizer draws a lightweight 3D wireframe Jeep and rotates it
using live heading, pitch, and roll:

```bash
python3 -m apps.automotive_dashboard.navigation_visualizer
```

Use the **Calibrate** button or press `c` while the vehicle is stationary.
Use **Reset Heading** or press `h` to zero relative heading. Press `q` or
`Escape` to exit.

Run stationary calibration automatically after connecting:

```bash
python3 -m apps.automotive_dashboard.navigation_visualizer --calibrate
```

Additional options control the MPU-6050 address, display update rate,
complementary-filter time constant, and calibration sampling:

```bash
python3 -m apps.automotive_dashboard.navigation_visualizer \
    --address 0x68 \
    --update-ms 50 \
    --filter-time-constant 0.5 \
    --calibration-samples 100
```

## Off-Road Dashboard

The off-road dashboard presents navigation data as a trail-oriented display
with a large inclinometer, compass ribbon, pitch and roll cards, tilt warnings,
linear acceleration, and optional GPS trail data:

```bash
python3 -m apps.automotive_dashboard.offroad_dashboard --calibrate
```

Include position-derived altitude, speed, course, and satellite status from
gpsd:

```bash
python3 -m apps.automotive_dashboard.offroad_dashboard \
    --calibrate \
    --gps
```

Default caution and warning colors approach 30 degrees of pitch and 25 degrees
of roll. These are display thresholds, not a guarantee of rollover safety.
They can be configured for experimentation:

```bash
python3 -m apps.automotive_dashboard.offroad_dashboard \
    --pitch-warning 28 \
    --roll-warning 22
```

Use **Calibrate** or `c` while stationary, **Zero Heading** or `h` to reset
relative heading, and `q` or `Escape` to exit.

The heading card uses a top-view Jeep for IMU-relative heading. When GPS course
is available, an amber arrow shows true course over ground with a cardinal
label. Relative heading and GPS course use different references until an
absolute-heading estimator is added.

If the estimated attitude indicates that the vehicle is substantially
inverted, the dashboard displays a suitably dramatic **CAPSIZED** warning and
suggests calling the winch crew. It does not contact emergency services or
anyone else automatically.
