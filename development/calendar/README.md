# Carbonate bridge service and calendar selection

Carbonate is an unofficial, separately installed Proton CalDAV bridge.
Authenticate it manually with `carbonate auth` before installing a service.
Never put Proton credentials or the bridge password in a service file.
The bridge should remain bound to loopback.

## Termux

Install `termux-services` using `pkg install termux-services`, then:

```sh
sh development/calendar/install_termux_service.sh
sv up openroadcode-carbonate
sv status openroadcode-carbonate
```

If the runit supervisor is not active, restart the Termux session.
Carbonate must already be installed and discoverable on PATH.
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
A recurring ORC sync worker and persistent cache will be added separately.
