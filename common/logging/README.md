# ORC logging

ORC uses Python's `logging` and C++ `spdlog` with a shared JSON Lines contract.
Navigation route planning and map rendering are the first instrumented flow.
Logs are diagnostic records; they are independent of the ORC message broker.

## Run and view

Start the UI with readable live output:

```bash
./runOrcUi --follow-logs
./runOrcUi --follow-logs --log-level DEBUG --log-component navigation
```

Attach to an already running instance from the repository root:

```bash
venv/bin/python -m common.logging.viewer
venv/bin/python -m common.logging.viewer --component map_renderer --level DEBUG --from-end
```

The standalone viewer initially reads the active log file. `--from-end` displays
new events only. It follows file replacement during rotation. Terminal output
escapes control characters and displays context fields alongside readable messages.
The viewer's level filters already collected events; it cannot enable DEBUG in an
existing process. Set logging levels before starting that process.

## Android bridge live viewer

The Android bridge's **Diagnostics → Logs** screen reads recent history and polls
for new events from the selected Termux or paired remote Linux runtime. Pause
retains displayed history and stops network activity. Leaving the screen or
backgrounding the app also cancels polling. Severity and dotted component-prefix
filters apply to collected events; they cannot enable DEBUG in a running process.
Copy and share export only the bounded displayed history, including context.

The service manager exposes a read-only `GET /logs` endpoint on its existing API
port, normally `8769`. It uses the same access policy as `/services`: existing
same-phone access for Termux, or administrator/paired bearer credentials for
remote access. No new listener, permission, runtime dependency, or pairing flow
is needed. Responses disable caching and accept no filesystem paths.

Supported query parameters are `level` (default `INFO`), `component` (optional
dotted prefix), and `cursor` (opaque value returned by the previous page). Omit
the cursor when changing filters. The response contains `events`, `cursor`,
`has_more`, `reset`, and a human-readable `scope`. Each request scans at most
256 KiB and returns at most 200 validated events within a 256 KiB event budget.
Initial history comes from the retained log tail. Live cursors follow retained
rotations; expired cursors set `reset` and return recent history. Partial records
are retried; malformed and oversized records are skipped. This is a diagnostic
viewer, not a guaranteed event-delivery channel.

Termux normally provides the shared ORC store. The restricted Linux manager
provides its private service-manager store; navigation/media logs in another
account's store are outside that scope. The response and screen identify the
store rather than silently implying host-wide coverage. Log aggregation across
accounts is a separate follow-up. Device bridge logs are also outside this feed.

Update/restart the Termux manager, or rerun the Linux service-manager installer,
before using an updated Android APK. Older managers return an update instruction
in the viewer. Linux's minimal deployment already copies the new logger and
service helper modules through its existing package manifest.

## Collection and storage

Default storage is `$XDG_STATE_HOME/openroadcode/logs/orc.jsonl`, falling back to
`~/.local/state/openroadcode/logs/orc.jsonl`. `ORC_LOG_DIR` overrides the directory.
Python processes write through a shared advisory lock. The UI launcher drains the
renderer's stdout and stderr, preserving structured native events and wrapping
plain third-party output as `map_renderer.output` events. Renderer output previously
written to `~/.cache/openroadcode/map-renderer.log` now goes to this shared store.
An explicitly supplied launcher `log_file` selects a separate rotating JSON store.

All participating processes and the viewer must run as the same user, or have
write access to the same `ORC_LOG_DIR`. This is a local filesystem collector;
remote navigation processes retain logs on their own hosts. Shared network storage
and collecting logs between hosts are outside this initial implementation.

The store retains the active file and four backups, each at most 10 MiB: a total
budget of 50 MiB for JSON logs, plus a small lock file. Oldest events expire on
rotation. Individual events exceeding 64 KiB are replaced with a bounded summary.
This budget applies to the ORC store; service supervisor journals have their own
retention settings.

Python's navigation service also emits JSON to stderr for its supervisor. The UI
collects logs silently unless `--follow-logs` is enabled. A renderer started
manually emits JSON to stderr; automatic file collection requires the UI launcher.

## Format and levels

Each physical line is one JSON object, including exceptions with escaped newlines.
Required fields are `timestamp`, `level`, `component`, `event`, `message`, and `pid`.
Timestamps use UTC with millisecond precision. Components have stable dotted names,
events use stable names, and additional context uses `snake_case` with native JSON
types. The native process's PID is preserved during collection.

```json
{"timestamp":"2026-10-03T15:04:12.123Z","level":"INFO","component":"navigation.routing","event":"route.calculated","message":"Route calculated","pid":2418,"operation_id":"a92d7f","point_count":326}
```

| Level | Meaning |
| --- | --- |
| DEBUG | Individual commands, sensor updates, and detailed diagnostics |
| INFO | Lifecycle, route requests/results, and meaningful state changes |
| WARNING | Unexpected condition with continued or reduced operation |
| ERROR | Failed operation; process can continue |
| CRITICAL | Component cannot continue operating |

`ORC_LOG_LEVEL` defaults to `INFO`. `ORC_LOG_COMPONENT_LEVELS` supplies comma-separated
component overrides, including dotted prefixes:

```bash
export ORC_LOG_COMPONENT_LEVELS='navigation.routing=DEBUG,map_renderer=WARNING'
./runOrcUi --follow-logs
```

More specific component overrides take precedence. Environment settings apply
independently to each process; restarting only the UI does not change an already
running navigation service's settings.

Routine GPS/camera events stay at DEBUG. Repeated warnings/errors with the same
component, event, level, and operation ID are limited to one event per five seconds
per collector. The next matching event reports `suppressed_count`. Distinct route
operations and CRITICAL events are retained. A process ending before the next
matching event can leave the final suppression count unreported.

Route calculations create an `operation_id`, retained in the navigation reply,
Python route presentation, map commands, and C++ route handling. It is optional
for unrelated events and older route responses. A published ZeroMQ command does
not prove that the renderer received or applied it; those are separate events.

Do not include credentials, destination addresses, coordinates, or complete route
payloads in routine records. The navigation flow records counts and summaries.
Existing map click/POI diagnostics, including coordinates, are emitted only at
DEBUG. Third-party native output is retained as text and can include details
outside ORC's own instrumentation.

Route failures record the exception type without potentially sensitive backend
response text. Python exception records support type, message, and stack trace;
use that facility only where error details are appropriate to retain.

## Add instrumentation

Configure logging once at the process entry point, then use named loggers:

```python
import logging
from common.logging.structured import configure_logging, event, operation

configure_logging()
logger = logging.getLogger("navigation.routing")
with operation() as operation_id:
    event(logger, logging.INFO, "route.requested", "Route requested")
```

C++ uses `orc_logging.hpp` to encode JSON safely and emit through `spdlog`. Its
build dependencies include `libspdlog-dev` on Debian/Ubuntu and `libspdlog` on Termux.
The MapLibre build container and host setup include the dependency.

## Runtime and service management

Runtime records use `runtime.*` components. Start ORC with
`./runOrcUi --follow-logs --log-component runtime`, or attach independently:

```bash
venv/bin/python -m common.logging.viewer --component runtime --from-end
```

| Component | Coverage |
| --- | --- |
| `runtime.apps` | Managed app show/hide/close/stop/restart, background preload, running-state changes, exclusive-peer and cleanup failures |
| `runtime.browser` | Browser spawn, startup failure, observed owned-process exit, launch/stop failures |
| `runtime.processes` | Child-group termination, forced kill, observed exit, display-cleanup signal dispatch |
| `runtime.host` | Deferred UI restart/poweroff request, clear, dispatch failure, unsupported action |
| `runtime.services.systemd` / `runtime.services.runit` | Service/core-stack actions, profile/bridge configuration, supervisor commands, observed status changes and query recovery |
| `runtime.services.http` | Service-manager HTTP startup, binding rejection, shutdown, and failures |

Each lifecycle operation has a local operation ID shared with nested work.
Background preload carries its request ID into its worker. Browser exit events
retain the launch ID and numeric child PID/exit code where ORC owns the process.
Exit detection occurs when existing status checks poll the process; no new watcher
or automatic restart policy is introduced. Service status polling logs only an
initial observation, changes, and query failure/recovery transitions at INFO or
higher; underlying read commands stay at DEBUG.

Action completion means the method returned. App close can hide or retain a
process according to its configured policy. Cleanup and preload passes retain
their existing continue-after-failure behavior and report failure counts.
Supervisor command completion does not prove telemetry readiness; observed state
is separate. Runit input health uses existing checks, and systemd's `failed` state
is visible even though the public status remains `stopped`. Host dispatch records
do not assert that the host powered off or a replacement UI became ready.

Records exclude command lines/arguments, URLs, display addresses, native stdout/
stderr, status detail strings, file paths, pairing identifiers/PINs/tokens,
authentication headers, and exception messages. Only approved service names and
normalized status/profile values are recorded. Native diagnostic files and UI/
HTTP error responses retain their existing behavior.

Termux uses the calling user's shared store. The restricted Linux service manager
runs under its own account, so its installer includes the logger modules and sets
`ORC_LOG_DIR=/var/lib/openroadcode/service-manager/logs`, inside its existing writable
private state directory. Reinstall the service manager to deploy this packaging
change. Read that separate bounded store using the service account:

```bash
sudo -u openroadcode-service-manager env PYTHONPATH=/opt/openroadcode \
  ORC_LOG_DIR=/var/lib/openroadcode/service-manager/logs \
  python3 -m common.logging.viewer --component runtime.services --from-end
```

Use the configured install root if it differs from `/opt/openroadcode`. No new
external dependencies are required. Tests exercise failures and correlation with
fake launchers/supervisors/host actions; live systemd/runit, X11 browser, and
installed-service behavior still need platform smoke testing.

## Quality gates

Weather instrumentation uses the `weather` prefix for forecasts, city/model/route
overlays, radar replay and tile caching. Weather logging tests exercise private
provider failures, recovery, request IDs across workers/callbacks, quiet cache
behavior, and stale result rejection. See the
[weather logging guide](../../controllers/weather/README.md#structured-logging).

The service-manager performance sampler uses `runtime.performance` for start,
stop, sampling failure, and recovery events. Host, process, and service sampling
failures are reported separately; repeated failures of the same type and routine
samples stay quiet. Each start has an operation ID shared with worker events and
shutdown. Records retain exception types only, excluding telemetry values,
process details, socket addresses, and exception messages.

The GitHub Actions **Logging quality gate** job tests schema types, escaping,
rotation budgets, concurrent writers, repeated error suppression, native output
collection, viewer rotation/filtering, and navigation operation ID propagation.
It also compiles the C++ command receiver and a small logger executable, then
validates actual native output using the same schema validator as Python.
These checks need neither MapLibre nor a graphical display.

Automotive coverage checks service and OBD/ELM327 lifecycle, reconnect transitions,
profile and trip operation IDs, quiet polling, failure cleanup, and exclusion of
raw vehicle data. See the [automotive logging guide](../../services/automotive/README.md#structured-logging)
for events and the live viewer filter.

Media coverage checks queued playback operation IDs across worker threads,
library loads/caches, observed state transitions, Spotify SDK callbacks,
browser/video/audio failures, cleanup, and privacy exclusions. See the
[media logging guide](../../controllers/spotify/README.md#structured-media-logging).

Run the checks locally:

```bash
venv/bin/python -m pytest -q common/logging/unit_test
cmake -S apps/map_renderer/component_test -B build/logging
cmake --build build/logging --parallel 2
ctest --test-dir build/logging --output-on-failure
```

Native checks require CMake, pkg-config, spdlog, RapidJSON, libzmq, and cppzmq headers.
Python tests also run through the existing `scripts/run_tests.py all` gate.
Repository administrators must add **Logging quality gate** to required branch
checks if merge blocking is desired; editing a workflow does not change branch
protection settings.
