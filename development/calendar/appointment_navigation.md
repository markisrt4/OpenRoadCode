# Appointment-driven navigation

The Home Personal context displays the next timed appointment from the local
calendar cache. All-day appointments are excluded from departure estimates.
The Calendar screen remains usable without connectivity; incomplete coverage
and stale or never-synchronized data are identified separately.

## Journey estimation

The monitor reads the cached event and current vehicle position. Local SQLite
address search must return a single address candidate. Local Valhalla calculates
travel duration without starting guidance. The recommended departure is the
appointment start minus travel duration and the arrival buffer.

The Calendar settings dialog allows an arrival buffer from 0 to 120 minutes,
in five-minute increments, defaulting to 10 minutes. It is persisted in the
navigation section of the shared settings TOML file.

The navigation estimate cache reuses results for up to 120 seconds, or 30
seconds for unsuccessful estimates. Event, buffer or significant position
changes invalidate reuse. The movement threshold is approximately 255 meters.

## Starting guidance

The driver must confirm the resolved destination. Confirmation may replace
active guidance. Changed or expired appointments are rejected after confirmation.
Route initiation runs in a worker; map presentation and observer notification
run on the UI thread. Duplicate requests are rejected while initiation is pending.
Shutdown discards late UI completion but cannot revoke an already-issued service
command.

Appointment location text is not sent to an external geocoding provider.
Local map search data, a working local routing service and a current position
are required for journey estimates. A single address candidate is not proof
of an exact match; verify the displayed destination before confirming.

## Validation

Run the repository quality gates and unit tests on the Ubuntu CI runner.
Verify the Calendar and Home screens on both 1280×720 and 800×480 touchscreens,
including offline operation, missing map data, changed appointments, arrival
buffer persistence, and confirmation cancellation.
