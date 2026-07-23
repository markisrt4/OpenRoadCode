# Automotive Dashboard

The automotive dashboard displays live vehicle state decoded through an
ELM327-compatible OBD-II adapter. Both interfaces use the same
`Elm327ObdAdapter` and `Obd2Manager` controller path.

## Terminal Dashboard

The terminal dashboard uses Python's built-in curses support and requires no
graphical desktop:

```bash
python3 -m apps.automotive_dashboard.tui \
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
python3 -m apps.automotive_dashboard.tui \
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

## Graphical Dashboard

The Tk dashboard remains available with:

```bash
python3 -m apps.automotive_dashboard.main \
    --port /dev/rfcomm0
```
