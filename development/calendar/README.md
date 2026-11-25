# Carbonate bridge service and calendar selection

Carbonate is an unofficial, separately installed Proton CalDAV bridge.
Authenticate it manually with `carbonate auth` before installing a service.
Never put Proton credentials or the bridge password in a service file.
The bridge should remain bound to loopback.

## Unattended authentication

The launcher uses ORC's existing `EnvironmentVariableSecretManager` to load
`CARBONATE_BRIDGE_PASSWORD`. On Termux, the default secrets file is
`~/.config/openroadcode/secrets.env`; on Linux it is
`/etc/openroadcode/secrets.env`. Set `OPENROADCODE_SECRETS_FILE` to
override the location. Use ORC's secret manager to set the secret, rather
than putting it in a service unit or a second password file:

```sh
python - <<'PY'
from getpass import getpass
from security.environment_variable_secret_manager import EnvironmentVariableSecretManager
EnvironmentVariableSecretManager().set_secret(
    "CARBONATE_BRIDGE_PASSWORD", getpass("Existing Carbonate bridge password: ")
)
PY
```

Run this from the OpenRoadCode repository root, with the Python environment
used by ORC. Keep the secrets directory private (mode 700) and secrets file
private (mode 600). The bridge password is not the Proton login password.
The launcher uses `python3` by default; override with
`OPENROADCODE_PYTHON` if the service requires a different interpreter.
Carbonate itself must be authenticated separately first.

## Termux

Install `termux-services` using `pkg install termux-services`, then:

```sh
sh development/calendar/install_termux_service.sh
sv up openroadcode-carbonate
sv status openroadcode-carbonate
```

If the runit supervisor is not active, restart the Termux session.
Logs are in ~/.local/state/openroadcode/current.
Carbonate is located on PATH, in ~/go/bin, or in ~/src/carbonate.
Override with CARBONATE_BIN for another installation.
Use `sv down openroadcode-carbonate` to stop it.

## Linux with systemd user services

```sh
sh development/calendar/install_linux_systemd.sh
systemctl --user enable --now openroadcode-carbonate.service
systemctl --user status openroadcode-carbonate.service
```

This is a user service, not a system service. It normally runs while the
user session is active. For boot-time operation without a login session,
the system administrator may configure user lingering separately.

## Calendar selection

Run the live diagnostic using your full CalDAV username and a bridge
password entered interactively:

```sh
python -m controllers.calendar.component_test.caldav_provider_cli \
  --username 'YOUR_USERNAME@proton.me' --prompt-password --disable-index 7
```

The selection is stored in `~/.config/openroadcode/calendar-selection.json`.
Indexes are discovery-order shortcuts only; the stored identifier is the
calendar's collection URL. Use `--enable-index 7` to reverse the change.

Run the same command without `--disable-index` to retrieve read-only
events. `--timeout` and `--days` control each query and date window.
Unsupported recurrence resources are counted as skipped, not silently
treated as successful event expansion.

## Offline cache and synchronization

The separate ORC calendar daemon synchronizes immediately and every 15 minutes
by default (7 days past, 30 days future). Successful enabled calendars replace
their SQLite snapshots atomically; failed or disabled calendars retain their
last successful snapshot. This is a rolling cache, not an archive.
Recurring events are expanded within the query window; unsupported resources
are counted as skipped.

## Calendar sync daemon (manual validation)

Before installing an unattended calendar service, validate the daemon manually.
The CalDAV bridge must already be running, and the secret manager must contain
`CALDAV_BRIDGE_PASSWORD` (separate from `CARBONATE_BRIDGE_PASSWORD` used to
launch Carbonate). Use the full CalDAV account username. Never put passwords
on the command line.

```sh
python -m controllers.calendar.calendar_sync_daemon \
  --username 'YOUR_USERNAME@proton.me'
```

The default SQLite cache is
`~/.local/share/openroadcode/calendar/events.sqlite3`. The daemon starts
synchronizing immediately, then repeats every 900 seconds. Stop it with
Ctrl+C. It does not print event contents. Calendar selection is reloaded during synchronization.

Install the optional service using the platform instructions below.

## Monitored Termux calendar synchronization

After confirming that the manual sync works and the required
`CALDAV_BRIDGE_PASSWORD` secret is available, install the sync worker from
the OpenRoadCode checkout:

```sh
sh development/calendar/install_termux_sync_service.sh 'YOUR_USERNAME@proton.me'
sv up openroadcode-calendar-sync
sv status openroadcode-calendar-sync
tail -f "$HOME/.local/state/openroadcode-calendar-sync/current"
```

The runit service is separate from `openroadcode-carbonate`. Both names are
included in the Termux service manager's allowlist for System Performance
monitoring. The calendar daemon also appears in ORC process workload metrics.
A service marked running indicates process supervision, not necessarily that
CalDAV synchronization succeeded; inspect logs for cycle results.

Stop with `sv down openroadcode-calendar-sync`. If the supervisor is not
active, restart the Termux session. Keep the secrets file private. Selection changes take effect on subsequent synchronization cycles.


## Linux calendar synchronization

Use a private user-owned secrets file for the user services:

```sh
export OPENROADCODE_SECRETS_FILE="$HOME/.config/openroadcode/secrets.env"
sh development/calendar/install_linux_sync_service.sh 'YOUR_USERNAME@proton.me'
systemctl --user status openroadcode-calendar-sync.service
journalctl --user -u openroadcode-calendar-sync.service -n 50
```

Both bridge and sync passwords must be available in the configured secrets file.
Install Python dependencies with the ORC development setup before starting
the sync daemon.

## Dashboard

The Calendar destination displays cached events and calendar selection settings.
Home's Personal context displays the next timed appointment. A passive dot
appears on the Personal tab for an appointment within 60 minutes when cache
freshness is known and not stale. The Home monitor reads asynchronously every
30 seconds while Home is mounted. System diagnostics report synchronization
health separately from service process status.

Calendar services are optional. Appointment geocoding, routing and departure
estimates are not included in this release.

## Presentation architecture

The toolkit-independent contracts in `ui/calendar/` expose immutable agenda,
appointment, selection, and synchronization health state. The adapters in
`controllers/calendar/calendar_presentation.py` own agenda workers and selection
persistence. Agenda reads are single-flight; superseded results are discarded.
Selection changes are saved as a batch, preserving unknown calendar IDs.

Application composition constructs the adapters and injects them into the Tk
frontend. The dashboard screen owns its mounted agenda session; application
composition owns the shared Home appointment monitor and closes it on shutdown.
Closing a session cancels queued work and retires running results without waiting
for database I/O. Widgets own rendering and toolkit timers, not worker threads.
Calendar selection currently uses synchronous local configuration operations
through its injected adapter. Calendar-driven navigation remains separate.

Calendar domain consumers use `CalendarQueryIf` in `controllers/calendar/`.
The calendar subsystem owns synchronization health; System diagnostics retains
a compatibility adapter. Application composition centralizes cache, account,
selection and timezone defaults. The existing Detroit timezone default is
preserved; callers can supply a different timezone explicitly.
