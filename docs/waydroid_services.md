# Waydroid services on Ubuntu/X11

These services separate the Android runtime from the ORC UI. They currently
target the same initialized Ubuntu 24.04 X11 installation as the
[VM workflow](waydroid_vm.md). They are not the Termux/scrcpy workflow. A packaged
production image can use this lifecycle, but hardware graphics/input and real GPS
delivery still need validation on the target.

## Install or upgrade

Close ORC and stop the old manually managed session/display first. The installer
needs sudo once; normal service startup uses a scoped noninteractive helper.

```bash
git switch feature/waze-live-map
git pull --ff-only
bash development/debian/waydroid_vm.sh stop
bash development/debian/waydroid_services.sh install
bash development/debian/start_waydroid_services.sh
```

Installation writes user units, an XDG desktop-login entry, a root-owned helper
at `/usr/local/libexec/openroadcode-waydroid-prepare`, and a per-user sudo rule.
It enables the existing `waydroid-container.service` at boot. It preserves Android
images, apps, accounts, ARM translation and data. It does not launch ORC or the
user runtime during installation. The final command above explicitly starts the
runtime from the current desktop. A legacy/unowned Weston must be stopped from
its original terminal; the service will not adopt or kill it.

The helper accepts only four fixed operations: start the container, prepare its
network/ADB/kiosk, and configure location for Android's root or shell identity.
It imports only Python's standard library in isolated mode and executes no code
from the checkout as root. Network rules are scoped to the discovered Waydroid
subnet/bridge; existing firewall rules and other ADB devices are preserved. The
public key is validated and added without replacing other authorized keys.
ADB authentication remains enabled. The grant allows this desktop account to
perform these operations on the local Waydroid container without a password;
it does not grant arbitrary shell or systemctl access.

The user units reference this checkout and its current Python interpreter.
Keep that location/venv available. Rerun install after moving the checkout,
changing interpreters, or pulling helper/unit changes, then restart the runtime
explicitly. The root-owned helper is a copy; a Git pull alone cannot upgrade it.
Existing ORC autostart preferences are preserved on upgrade.
Before upgrading an already installed service, stop its target and runtime with
`systemctl --user stop openroadcode-session.target openroadcode-waydroid.service`
instead of the manual VM stop command above. The installer refuses to replace
the helper while the user runtime is active.

## Start ORC separately or opt in to autostart

```bash
git switch feature/waze-live-map
systemctl --user start openroadcode-ui.service
```

You can instead use `./runOrcUi` manually; do not run a second UI while its service
is active. To opt in to starting ORC at desktop login:

```bash
git switch feature/waze-live-map
systemctl --user enable openroadcode-ui.service
```

The installer also accepts `install --autostart-orc` for image provisioning.
Disabling that unit removes ORC autostart without disabling Waydroid.

At login the XDG entry imports the actual `DISPLAY`/`XAUTHORITY` into the user
manager and starts `openroadcode-session.target`. This also supports X11 desktops
that do not automatically activate systemd's `graphical-session.target`.
No linger, graphical root process, hard-coded `:0`, or manual sudo refresh is
required. The dedicated Wayland socket is `wayland-0`; a conflicting compositor
causes a visible service failure rather than being replaced.

## Lifecycle and readiness

- The existing system service owns the Android container.
- `openroadcode-waydroid.service` owns the Weston kiosk, user Android session and
  readiness supervisor. It verifies Android boot, current networking, authorized
  ADB, the Waydroid device identity and retained location permissions before
  sending systemd `READY=1`, including installed Waze's fine/coarse permissions.
  It discovers the address directly inside the
  container, even when `waydroid status` omits it.
- `openroadcode-ui.service` starts after that readiness check. It can still show
  ORC's own map if Waydroid fails. Restarting or stopping ORC leaves Waze/Android
  running. Android location forwarding currently belongs to ORC, so it resumes
  when ORC restarts and receives a fresh host fix.

The runtime checks its owned processes and ADB every ten seconds, attempts a
reconnect to only the selected device, and fails if it cannot recover. Systemd
permits three startup attempts within five minutes. A runtime restart closes the
Android session and its apps; it does not erase data or restart the host ADB
server. UI restarts have their own bounded retry policy.

Readiness means the runtime/location **transport** is ready. Browser consent or
a real live GNSS source is still needed; this does not fabricate a position or
declare Waze has acquired GPS. The service never stores coordinates in its
readiness configuration or journal messages.

## Status, recovery and shutdown

```bash
git switch feature/waze-live-map
systemctl --user status openroadcode-waydroid.service openroadcode-ui.service --no-pager
journalctl --user -u openroadcode-waydroid.service -n 60 --no-pager
```

Weston/session stage output also remains in
`~/.local/state/openroadcode/waydroid-vm/`. After fixing a startup failure:

```bash
git switch feature/waze-live-map
systemctl --user reset-failed openroadcode-waydroid.service
systemctl --user restart openroadcode-waydroid.service
```

To restart only ORC, preserving Waze:

```bash
git switch feature/waze-live-map
systemctl --user restart openroadcode-ui.service
```

To stop the user runtime and UI together:

```bash
git switch feature/waze-live-map
systemctl --user stop openroadcode-session.target
```

The system container remains warm. For a full Android shutdown, stop the user
target first, then `sudo systemctl stop waydroid-container.service`. Do not run
the manual VM start/stop commands concurrently with the service; both use the
same runtime lock. Stopping/restarting the service cleans only its owned session
and display. A failed manual-runtime ownership check leaves that runtime alone.

To uninstall:

```bash
git switch feature/waze-live-map
bash development/debian/waydroid_services.sh uninstall
```

This stops/removes this user's units, login entry and sudo grant. It preserves
the shared root helper, system container service and Android data for other
users/workflows. Existing location configuration can be reversed separately
with `python3 -m scripts.setup_waydroid_location disable` while Android is running.

## Validation

Focused checks:

```bash
git switch feature/waze-live-map
python3 -m pytest -q scripts/unit_test/test_waydroid_service.py scripts/unit_test/test_waydroid_vm.py scripts/unit_test/test_setup_waydroid_location.py
```

On the VM, validate installation and startup without cached sudo credentials,
restart ORC while Waze is navigating, stop/start the user target, then log out/in
and reboot. Confirm no duplicate Weston, the kiosk remains unlocked, ADB reports
`device`, and Waze receives a fresh host location. Command-fake tests and unit
syntax checks do not establish those device results. Full quality-gate and
target-device validation remain pending before production rollout.
