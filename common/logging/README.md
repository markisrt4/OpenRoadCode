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

## Quality gates

The GitHub Actions **Logging quality gate** job tests schema types, escaping,
rotation budgets, concurrent writers, repeated error suppression, native output
collection, viewer rotation/filtering, and navigation operation ID propagation.
It also compiles the C++ command receiver and a small logger executable, then
validates actual native output using the same schema validator as Python.
These checks need neither MapLibre nor a graphical display.

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
