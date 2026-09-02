# Tk Automotive Frontend

This package contains reusable Tk automotive screens and panels. Widgets here
present values through toolkit-independent contracts from `ui`; they do not
construct, poll, calibrate, or stop controllers and hardware.

## Theme architecture

Automotive presentation uses the shared OpenRoadCode theme pipeline rather than
application-local color rewriting:

```text
orc-dark.css / orc-light.css
        |
        v
    StyleSheet
        |
        +--> VehicleGaugeTheme
        +--> ShifterTheme
        +--> OffroadTheme
        |
        v
     Tk widgets
```

`ThemeController` owns the selected `ThemeMode` and active `ThemeBundle` without
knowing how a frontend renders them. Tk-specific code resolves the stylesheet
into typed frontend themes. Controllers, telemetry producers, and hardware
therefore remain independent of Tk and CSS.

The automotive stylesheet selectors are `.automotive-gauge`,
`.automotive-shifter`, and `.automotive-offroad`. Widgets should consume the
active stylesheet through `set_style_sheet()` or a typed `set_theme()` method
instead of embedding ORC palette constants in application screens.

Page surfaces and instrument surfaces are intentionally separate. Light mode
can use a light dashboard background while retaining a dark round gauge face or
shifter cluster. Linear telemetry cards have dedicated surface, text, and muted
text properties so their values remain readable in either mode.

## Off-road dashboard

`OffroadDashboardPanel` renders vehicle attitude, linear acceleration,
position-derived altitude, ground speed, course over ground, satellite usage,
and application status. It implements only the contracts its display needs:

- `OrientationUiIf`
- `TranslationUiIf`
- `PositionUiIf`
- `GroundTrackUiIf`
- `StatusUiIf`

The panel emits calibration and relative-heading reset requests through
`NavigationRequestHandlerIf`. The standalone composition in
`apps/automotive_dashboard/offroad_dashboard.py` owns the navigation
controller, polling schedule, unit conversion, request handling, and lifecycle.

Heading and course over ground are deliberately separate. Heading describes
where the vehicle points; ground track describes its actual movement relative
to true north. The current navigation controller publishes a relative heading,
so the panel identifies it with `HeadingReference.RELATIVE` rather than
mislabeling it as a true-north bearing.

`PositionUiIf.set_satellites()` requires a real satellite snapshot. A source
that exposes only an aggregate satellite count cannot populate it without
inventing satellite identities, so the standalone app leaves that display
unavailable until its navigation source provides detailed records.

## Vehicle gauges

`VehicleGaugePanel` provides the reusable performance instrument cluster.
It accepts the narrow `VehicleGaugeSnapshot` presentation shape but does not
import, construct, or poll an OBD-II adapter. `VehicleState` and synthetic
demo values both satisfy that shape. Gauge visibility and ordering persist in
`~/.config/openroadcode/vehicle_gauges.json`.

For independently presented values it implements `VehicleUiIf`,
`VehicleConnectionUiIf`, `VehicleTripUiIf`, `VehicleTireUiIf`, and
`VehicleDiagnosticsUiIf`. Contract measurements remain SI; conversions to the
panel's current imperial display units happen only inside the Tk frontend.
Complete snapshots remain a convenience adapter for the existing OBD-II source
and standalone example.

The same panel is hosted by Car UI's `vehicle_gauges` destination and the
standalone synthetic example:

```bash
python3 -m apps.automotive_dashboard.vehicle_gauge_demo
```

See `README_vehicle_gauges.md` for the available instruments, theme values,
and layout API.
