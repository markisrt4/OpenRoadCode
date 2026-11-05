# Waydroid on the Linux development VM

Use the normal desktop user in an Ubuntu 24.04 X11 VM, with sudo access. This
workflow owns a dedicated nested Weston kiosk and Waydroid session. It is not
the Termux workflow and does not change the Linux desktop's lock policy.

## Install once

```bash
git switch feature/waze-live-map
git pull --ff-only
bash development/debian/waydroid_vm.sh install --init-gapps
```

The existing installer checks kernel Binder support, installs the official
Waydroid package, Weston, ADB and diagnostics, and initializes a GAPPS Android
image **only when no Waydroid configuration exists**. Existing images, apps,
accounts, ARM translation and data are preserved. Without `--init-gapps`, install
only installs/upgrades the packages. No Android image is forcibly reinitialized.

Waze installation, Play Store/account setup and ARM translation are separate
one-time Android/image tasks. This workflow does not download APKs, install
third-party translation layers, accept terms or log into accounts. Fresh x86 VMs
may still need a compatible image/ARM translation before Waze can be installed.
GPU/image compatibility must also be validated on the particular VM; the script
does not silently switch Android's graphics drivers.

## Everyday startup

```bash
git switch feature/waze-live-map
bash development/debian/waydroid_vm.sh run
```

This checks/starts the runtime, configures it and verifies readiness. It never
launches ORC. Launch ORC separately when ready:

```bash
git switch feature/waze-live-map
./runOrcUi
```

The Waydroid script performs the following stages:

1. Reuse or start exactly one dedicated Weston X11 kiosk with `kiosk-shell.so`
   and `--idle-time=0`. Verify its live marker process and socket, and require one
   Weston window. Weston 13 does not publish `_NET_WM_PID`; an absent window PID
   is accepted, but a contradictory advertised PID or multiple windows is not.
2. Start `waydroid-container` and the user's Android session, then wait for boot.
3. Discover the current bridge subnet, guest IP and veth peer. Reject conflicting
   host routes. With NetworkManager running, mark only `waydroid0` and its exact
   current peer unmanaged; never apply a `veth*` wildcard.
4. Enable IPv4 forwarding and ensure bridge/subnet-scoped forward rules. Check
   both installed iptables backends because Docker and Waydroid may use different
   ones. Reuse existing subnet masquerading; add scoped NAT only if absent.
   No firewall table is flushed, no policy is changed, and Docker rules are kept.
   Restore Android's connected/default routes in its `eth0` policy table.
5. Check host-to-Android reachability. Start the user's ADB server with local
   emulator discovery bounded below ORC's broker port 5557. An existing ADB server
   is preserved; commands pin the discovered Waydroid serial, so other devices
   and a pre-existing phantom emulator cannot be selected accidentally.
6. Import the user's public ADB key with proper newline separators, preserving
   existing keys; restore ownership, mode and SELinux context. Enable TCP 5555,
   restart local Android adbd when needed, and recover its known `stopping` state.
   Keep ADB authentication enabled. Require `get-state` to report **device** and
   verify the target identifies as Waydroid; a “connected” message is insufficient.
   The location capability probe accepts Android's documented help text even when
   the image returns a usage exit status; actual failed mutations still stop setup.
7. Disable Android's non-secure lock, keep the virtual Android screen awake,
   configure the existing location provider and grant installed Waze location
   permissions. It does not remove a PIN/password; a secure-lock failure stops
   setup with an explanation.
   Location setup checks the manager's pinned serial against live container eth0
   instead of requiring the CLI status summary to repeat the IP. Its standalone
   command also falls back to eth0 when status omits the address; it still requires
   an authorized ADB device identified as Waydroid before changing permissions.
   It reads back the location switch and mock-location permission through the
   runtime ADB identity before marking location setup enabled.
8. Return to the terminal with the configured runtime ready. Start ORC afterward
   so it loads the updated location-provider settings.

Run is repeatable: unchanged keys/rules aren't duplicated, ready processes are
reused, and guest IP changes update ORC's location configuration. Existing ADB
connections are not globally disconnected and its server is not killed.

Browser location consent or an actual GNSS source is still required for a fresh
host position. Mock-location setup provides a transport, not a GPS measurement.
If Android restarts or ADB drops during provider cleanup, ORC revalidates the
configured device and recreates its GPS test provider on the next fresh fix after
connectivity returns. It does not replay stale fixes or reconnect other devices.
Reachability/ADB checks do not establish Internet/DNS or Play Store availability.
The network repair runs before each startup; it is not a new system-wide firewall
or boot service. Bridge ARP/filtering failures that persist stop startup instead
of reporting success or repeatedly rebooting Android behind the user's back.

Closing ORC leaves the managed Android session and Weston warm for the next run.
Starting/configuring while ORC is already running requires restarting ORC to load
changed location configuration.

## Start, configure, diagnose and stop separately

```bash
git switch feature/waze-live-map
bash development/debian/waydroid_vm.sh start
```

`run`, `start` and `configure` perform the same idempotent runtime/configuration
checks without launching ORC. Use `configure` after app installation, an Android
restart or a guest-IP change. If a stage fails, it prints the failed operation;
successfully started owned processes remain available for diagnosis or stop.

```bash
git switch feature/waze-live-map
sudo -v
bash development/debian/waydroid_vm.sh status
```

Status is read-only. It reports kiosk ownership, Android/bridge addresses,
neighbors, ADB state, lock state, location configuration and logs. It does not
start ADB to inspect it. Without cached sudo credentials, Android inspection can
be unavailable; status does not prompt for credentials or repair anything.
Stage logs are under `${XDG_STATE_HOME:-$HOME/.local/state}/openroadcode/waydroid-vm/`.
The process record and startup lock are in `$XDG_RUNTIME_DIR`.

```bash
git switch feature/waze-live-map
bash development/debian/waydroid_vm.sh stop
```

Stop ends only the session/display processes started by this workflow, checking
PID start times to avoid killing a reused PID. It preserves the system container
service, apps/data, host ADB server, scoped runtime network rules and unrelated
desktop processes. Externally started kiosks/sessions may be reused, but are not
stopped by this command. Location setup can be reversed separately with the
existing `python3 -m scripts.setup_waydroid_location disable` command.

## Recovering a network failure

For an intermittent bridge/ADB failure after a successful managed startup, close
ORC and explicitly rebuild the Android session/network while keeping its kiosk:

```bash
git switch feature/waze-live-map
bash development/debian/waydroid_vm.sh restart
bash development/debian/waydroid_vm.sh run
```

Restart closes Android apps and restarts the container, then reruns configuration
and readiness checks. It does not reset Android data, restart the host ADB server,
or run repeatedly in the background. Use status/logs if the failure recurs.

## Migrating the old manual display

A live legacy compositor is deliberately not killed or adopted. If startup
reports that the socket belongs to an unverified/legacy compositor, close ORC,
stop the Waydroid session, then stop that Weston's terminal with Ctrl+C:

```bash
git switch feature/waze-live-map
waydroid session stop
pgrep -a -x weston
```

Stop only the PID/terminal corresponding to the old dedicated Waydroid display.
Then use `waydroid_vm.sh run`. A dead socket is reclaimed only after verifying
that it belongs to this user, has no listener and its Wayland lock is free. A live
or ambiguous socket/marker is left untouched with an actionable error.

## Validation

```bash
git switch feature/waze-live-map
python3 -m pytest -q scripts/unit_test/test_waydroid_vm.py scripts/unit_test/test_setup_waydroid_location.py scripts/unit_test/test_waydroid_display_launcher.py
```

On the VM, run `configure` twice and confirm ADB reports `device`, location is
configured and the kiosk stays unlocked. Launch Waze, test mouse input in both
Android and ORC, close/reopen ORC, then test stop/start. After a VM reboot, repeat
run/status. Confirm Maps/browser Internet access inside Android separately.
Command-fake tests validate orchestration and ownership decisions; they cannot
prove Binder, graphics, networking or input behavior on the VM. The full quality
gate and VM end-to-end validation remain required before declaring this ready
for production use.
