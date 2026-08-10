# Tk Automotive Frontend

This package contains reusable Tk automotive screens and panels. Widgets here
present values through toolkit-independent contracts from `ui`; they do not
construct, poll, calibrate, or stop controllers and hardware.

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
