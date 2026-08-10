# OpenRoadCode Vehicle Gauges

This package adds reusable analog and compact linear Tkinter gauges with an
early-2000s performance-cluster visual style.

## Files

- `vehicle_gauge_widgets.py` — scalable `Canvas` analog and linear gauges.
- `vehicle_gauge_panel.py` — maps `VehicleState` fields into gauges and
  provides the layout editor.
- `apps/automotive_dashboard/vehicle_gauge_demo.py` — animated standalone
  example that does not require a vehicle or ELM327 adapter.

## Test the widgets

```bash
python3 -m apps.automotive_dashboard.vehicle_gauge_demo
```

The demo uses synthetic values. Select **Arrange gauges** to show or hide gauges and change their order. The demo stores its layout in:

```text
~/.config/openroadcode/vehicle_gauges.json
```

The demo handles `Ctrl-C`, `SIGTERM`, and the window close button through the
same graceful shutdown path, cancelling scheduled animation callbacks before
destroying the Tk window.

## Add the panel to a vehicle screen

```python
from frontends.tk.automotive import VehicleGaugePanel

self.vehicle_gauges = VehicleGaugePanel(
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

The panel intentionally knows nothing about `Elm327Device`, `Obd2Manager`,
threads, or polling. The automotive manager/controller remains responsible for
acquiring data; the UI only displays snapshots.

The panel also implements the applicable contracts from `ui/automotive`.
Contract setters accept SI values and perform display-unit conversion at the
frontend boundary.

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

Shared colors and redline geometry belong to
`apps/common/uiTheme/vehicle_gauges.py`. Frontend renderers consume
`VEHICLE_GAUGE_THEME` and `VEHICLE_GAUGE_REDLINE_THEME`; application code can
provide immutable `VehicleGaugeTheme` and `VehicleGaugeRedlineTheme` variants
without embedding visual constants in screens or controllers.

RPM, boost, and speed enable `intense_redline`, layering a wide dark-red base,
saturated danger band, bright inner highlight, heavier danger ticks, and red
danger numerals. Other round gauges keep the restrained standard treatment
unless explicitly opted in.

Thresholds remain part of each `GaugeDefinition` through `caution_high` and
`danger_high`. The intense appearance is independently configurable with an
immutable `VehicleGaugeRedlineTheme` from `apps/common/uiTheme`:

```python
from dataclasses import replace
from apps.common.uiTheme import VehicleGaugeRedlineTheme
from frontends.tk.automotive.vehicle_gauge_panel import DEFAULT_GAUGES

hot_redline = VehicleGaugeRedlineTheme(
    shadow_color="#500000",
    danger_color="#ff1010",
    highlight_color="#ff9090",
    numeral_color="#d00000",
    shadow_width_scale=0.12,
    danger_width_scale=0.08,
    highlight_width_scale=0.025,
    major_tick_width_scale=0.05,
    minor_tick_width_scale=0.022,
)

custom_gauges = tuple(
    replace(
        gauge,
        caution_high=5.8,
        danger_high=6.2,
        redline_style=hot_redline,
    )
    if gauge.gauge_id == "rpm"
    else gauge
    for gauge in DEFAULT_GAUGES
)
```

Pass `custom_gauges` as the panel's `definitions` argument. Radius and width
scales must be positive; larger width scales produce heavier bands and ticks.

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
