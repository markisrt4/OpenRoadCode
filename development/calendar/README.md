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

If the runit supervisor is not active, restart the Termux session.\nLogs are in ~/.local/state/openroadcode/current.
Carbonate is located on PATH, in ~/go/bin, or in ~/src/carbonate.\nOverride with CARBONATE_BIN for another installation.
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

These scripts manage Carbonate, **not** a standalone ORC calendar daemon.
The initial ORC sync worker (`CalendarSyncWorker.sync_once`) and SQLite
snapshot cache (`CalendarEventCache`) are available. They are not yet
scheduled or connected to the UI. Call sync from a background worker, not
the UI thread. Only successful, enabled calendar queries replace snapshots;
failed calendars retain their last saved events. The current cache stores
time-window snapshots and is a foundation for offline support, not yet a
complete incremental-sync or recurrence-expansion implementation.
