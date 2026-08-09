# Car TUI

`apps/carTui` is the statically composed terminal counterpart to Car UI. It
provides a curses home menu and navigable automotive destinations while using
the reusable views under `frontends/tui`.

Included destinations:

- Off-road navigation: heading, pitch, roll, acceleration, angular velocity,
  calibration, and relative-heading reset.
- Vehicle telemetry: RPM, speed, boost, temperatures, pedal/load values,
  pressures, airflow, fuel, and module voltage.
- Radio: FM broadcast, scanner, AM aviation, and FM weather-band receivers
  with tuning, presets, and receiver telemetry.

Run from the repository root:

```bash
venv/bin/python -m apps.carTui.main
```

Both the graphical and terminal automotive applications load
`config/runtime.toml`. Car TUI builds its FM, scanner, airband, and
weather receivers from the radio stacks and JSON profiles selected there. Use
`--config PATH` to select another runtime file.

## Run without physical hardware

Use the built-in changing software simulation on a Linux VM or development
workstation:

```bash
venv/bin/python -m apps.carTui.main --demo
```

`--simulate` is an equivalent spelling. Simulation supplies changing vehicle
telemetry, IMU attitude and acceleration, and a valid moving GPS fix. It does
not access I2C, Bluetooth, serial ports, gpsd, SDR hardware, or physical input
devices. The four radio categories use in-memory receiver controllers.

Hardware options:

```bash
venv/bin/python -m apps.carTui.main \
  --imu-address 0x68 \
  --gps \
  --obd-port /dev/rfcomm0 \
  --obd-baud 38400
```

Home controls are arrow keys or `j`/`k`, Enter to open, and `q` to quit. Inside
a destination, `b` or Escape returns home and `q` exits the application.

Radio controls are `1`–`4` to select FM, scanner, airband, or weather band;
`p` toggles the selected receiver; Left/Right tunes by one mode-specific step;
and `[`/`]` selects the previous or next preset. Only one simulated receiver
is active at a time.

The standalone commands remain available through
`apps.automotive_dashboard.navigation_tui` and `vehicle_tui`; they compose the
same reusable terminal views but retain their focused command-line options and
lifecycle.
