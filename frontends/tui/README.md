# Terminal Frontends

`frontends/tui` contains reusable curses presentation components. Views accept
structural snapshot contracts and primitive status/control values; they do not
construct controllers, open hardware, own application routes, or run their own
curses wrapper.

`curses_helpers.py` owns clipped text drawing and primitive numeric formatting
shared across TUI domains, preventing radio and automotive views from importing
one another for presentation utilities.

`automotive/NavigationDashboardView` and `VehicleDashboardView` are shared by
the standalone automotive dashboard commands and the multi-screen `carTui`
application.

`radio/RadioDashboardView` presents receiver selection, frequency, mode,
signal telemetry, RDS text, and presets. Controller ownership and tuning
commands remain in the consuming application.
