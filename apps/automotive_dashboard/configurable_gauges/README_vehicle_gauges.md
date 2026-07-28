# OpenRoadCode Vehicle Gauges

This package adds reusable analog and compact linear Tkinter gauges with an
early-2000s performance-cluster visual style.

## Files

- `round_gauge.py` — scalable `Canvas`-based analog and linear gauges.
- `vehicle_gauge_subpanel.py` — maps `VehicleState` fields into gauges and provides the layout editor.
- `vehicle_gauge_demo.py` — animated test app that does not require the car or ELM327 adapter.

## Test the widgets

Place the three Python files together and run:

```bash
python3 vehicle_gauge_demo.py
```

The demo uses synthetic values. Select **Arrange gauges** to show or hide gauges and change their order. The demo stores its layout in:

```text
~/.config/openroadcode/vehicle_gauges.json
```

The demo handles `Ctrl-C`, `SIGTERM`, and the window close button through the
same graceful shutdown path, cancelling scheduled animation callbacks before
destroying the Tk window.

## Add the subpanel to the vehicle UI

```python
from vehicle_gauge_subpanel import VehicleGaugeSubpanel

self.vehicle_gauges = VehicleGaugeSubpanel(
    parent,
    config_path="~/.config/openroadcode/vehicle_gauges.json",
    columns=4,
)
self.vehicle_gauges.pack(fill="both", expand=True)
```

Whenever the automotive controller publishes a new `VehicleState`:

```python
self.vehicle_gauges.update_state(vehicle_state, connected=True)
```

When the OBD-II connection drops:

```python
self.vehicle_gauges.update_state(last_vehicle_state, connected=False)
```

The subpanel intentionally knows nothing about `Elm327Device`, `Obd2Manager`, threads, or polling. The automotive manager/controller remains responsible for acquiring data; the UI only displays snapshots.

## Default gauges

The included definitions cover RPM, boost, speed, throttle, coolant temperature,
intake-air temperature, engine load, and module voltage. Primary driving metrics
use white-face analog dials; secondary telemetry uses compact horizontal gauges.
Set a definition's `shape` to `"round"` or `"linear"` when adding another
`VehicleState` attribute. Circular dial geometry can be tuned with `start_angle`
and `sweep_angle`. Operating ranges use `caution_low`, `danger_low`,
`caution_high`, and `danger_high`; linear readouts change from white to yellow
to red as those thresholds are crossed. `value_scale` supports display-unit
conversion such as raw RPM to thousands, and `icon` supports the built-in
`"coolant"` and `"voltage"` dashboard symbols.

The gear indicator accepts `R`, `N`, and `1` through `6` from a `gear` state
attribute. Generic OBD-II does not normally report the selected gear on a
manual transmission; provide it from a shifter sensor or a gear-ratio inference
layer. The diagnostics panel accepts `diagnostic_trouble_codes` and `mil_on`.
Those values should be populated from OBD-II Mode 03 and Mode 01 PID 01.

Additional optional state fields drive the information tiles:
`odometer_miles`, `trip_miles`, `fuel_economy_mpg`,
`estimated_range_miles`, and `ambient_temp_f`. The TPMS panel accepts
`tire_pressures_psi` as a dictionary with `front_left`, `front_right`,
`rear_left`, and `rear_right` keys. Fuel level uses the existing
`fuel_level_pct` field.
