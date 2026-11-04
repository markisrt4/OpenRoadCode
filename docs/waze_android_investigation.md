# Native Waze investigation: Termux and Raspberry Pi 5

## Current integration: native Waze only

The left rail has one full **NAV** tile. The navigation top bar provides a
**Map / Waze** switch; the NAV tile restores whichever view was last presented.
Failed Waze launches do not replace the remembered Map view. When Waze is
disabled, Navigation remains a normal Map destination. The native Waze toolbar
also has **Home** and **Work** buttons. They read
the same saved destinations as Navigation, refresh edits on each click, and send
the coordinates to Waze without changing an active ORC route. Missing locations
report that the shortcut must be configured in Navigation.

The ORC Waze entry and Home/Work/POI destination handoffs now use the Android app
exclusively. Missing integration or a failed launch reports **Native Waze
unavailable** rather than opening the website. ORC no longer constructs or
registers a Waze browser launcher, web screen or browser GPS worker. The older
web experiments below are historical, not a fallback available from the UI.
The existing `apps.waze.enabled` switch is retained; its legacy URL/profile
fields remain compatible but do not select or launch a browser.

On Linux, installed Waydroid is detected automatically. On native Termux,
installed `adb` and `scrcpy` select the virtual-display backend automatically.
The Android session/ADB connection must already be running. Explicit
`ORC_WAYDROID_PANEL=0` or `ORC_SCRCPY_WAZE=0` disables its respective integration;
this produces an unavailable message, not a web fallback. Existing commands with
either flag set to `1` remain valid.

### Command-line ADB authorization on the local VM

If setup reports `adb: device unauthorized`, the running Android image has not
trusted this desktop user's ADB key. Android UI access is not required: with
Waydroid running, explicitly append this VM's **public** key through its root
shell. The private key stays on the VM. Do not disable ADB authentication.

```bash
git switch feature/waze-live-map
sudo -v
adb start-server
{
    printf '\n'
    cat "$HOME/.android/adbkey.pub"
    printf '\n'
} | sudo waydroid shell -- tee -a /data/misc/adb/adb_keys >/dev/null
sudo waydroid shell -- chown system:shell /data/misc/adb/adb_keys
sudo waydroid shell -- chmod 0640 /data/misc/adb/adb_keys
sudo waydroid shell -- restorecon /data/misc/adb/adb_keys
sudo waydroid shell -- stop adbd
sleep 1
sudo waydroid shell -- start adbd
sleep 1
waydroid adb connect
adb -s 192.168.240.112:5555 get-state
```

Use the actual IP from `waydroid status` in place of the example address. The
target must report `device` before enabling the location provider. The CLI's
“Established ADB connection” log does not verify the transport's authorization.
The leading and trailing newlines above keep the public key on its own record
even when either existing file lacks a final newline; existing keys are retained.

If `getprop init.svc.adbd` remains `stopping`, recover only Android's ADB daemon
through the root shell (no Android UI or ADB connection is needed):

```bash
git switch feature/waze-live-map
sudo waydroid shell -- setprop service.adb.tcp.port 5555
sudo waydroid shell -- killall -9 adbd
sudo waydroid shell -- start adbd
sleep 1
sudo waydroid shell -- getprop init.svc.adbd
waydroid adb connect
adb -s 192.168.240.112:5555 get-state
```

Expect `running` and then `device`. If either is absent, diagnose before
continuing. Keep `ro.adb.secure=1`; disabling authentication is not required.
Once authorized:

```bash
git switch feature/waze-live-map
python3 -m scripts.setup_waydroid_location enable
python3 -m scripts.setup_waydroid_location status
```

This authorizes the VM for ADB access to its local Waydroid instance. Normal GPS
updates still run without sudo. Restart ORC after enabling the configuration.
If the status report shows Waze's location permissions denied, its declared
permissions can also be granted through the root shell:

```bash
git switch feature/waze-live-map
sudo waydroid shell -- pm grant com.waze android.permission.ACCESS_COARSE_LOCATION
sudo waydroid shell -- pm grant com.waze android.permission.ACCESS_FINE_LOCATION
```

### Native current location

On Waydroid, enable Android Location and grant Waze **Location → Allow while
using the app**, with **Use precise location** enabled if offered. To open
Waze's Android app-info page without launching the entire Android desktop:

```bash
git switch feature/waze-live-map
waydroid app intent android.settings.APPLICATION_DETAILS_SETTINGS package:com.waze
```

These Android permissions allow Waze to consume location; they do not create a
GPS source in a VM. Configure the host-to-Waydroid feed once, as the normal
desktop user, with Waydroid running:

```bash
git switch feature/waze-live-map
python3 -m scripts.setup_waydroid_location enable
./runOrcUi --follow-logs
```

In ORC Settings, share the host location, allow the browser permission and keep
that host-location page open. Confirm **Live location** before opening Waze;
cached/expired positions are not forwarded. The permission page is ORC's host
location source, not the Waze website. With Waze active, Settings should report
**Sharing live location with Android**. Resume Waze through the NAV entry
after changing Android app permissions. Mock-location acceptance and navigation
still need device verification.

On an X11 desktop with Chrome/Chromium installed, **Share host location** opens
a dedicated app-style window sized to 480×330, using its own persistent
`host-location` profile. The window retains normal move/close controls and can
be moved out of the way while sharing. Its **Close** button minimizes the helper
without closing its browser page, so GPS continues. **Stop sharing** ends the
feed; the operating system's title-bar X also ends it by actually closing the
browser. Repeated requests reuse the helper. Its timers are not throttled just because ORC is
in front. Browser permission must be allowed in this dedicated profile the
first time. The page uses compact ORC colors and controls. If no supported
Chrome/Chromium executable is available, the default-browser path remains for
Firefox and other hosts; that browser controls its window size. No browser
dependency is installed automatically.

The Settings **Share host location** button hides while fresh browser fixes are
arriving and returns if that feed expires. An already-running helper reconnects
to navigation when ORC restarts, without opening the popup or asking permission
again. The page retries transient HTTP failures and obtains a new fix after
reconnection; it does not replay cached coordinates as live GPS. This requires
the helper browser process to remain running. After an OS restart or actually
closing the browser, start sharing again. Consent remains in its persistent
profile subject to the browser's own permission policy.

The custom Close control uses a loopback window-control listener on port 8767.
Only POST requests from the local permission-page origin are accepted. It can
only hide this dedicated helper window; it cannot inject locations or change
Android permissions. The listener stops with ORC, while the helper page may
remain running to reconnect on the next launch.

When updating from an older helper version, close its old browser window once
using its title-bar X before restarting ORC, then share again to load the new
Close control and reconnection behavior.

If GPS does not reach Waze, collect the permission/connection status as your
normal desktop user while Waydroid is running:

```bash
git switch feature/waze-live-map
python3 -m scripts.setup_waydroid_location status
```

This is read-only: it does not connect ADB, grant permissions, inject a position,
or print coordinates. It checks whether configuration matches the current
Waydroid IP and ADB identity, Android Location is enabled, mock GPS is allowed,
and Waze has precise/coarse location permission. Include ORC Settings' location
status with the result so a missing live host fix can be distinguished from an
Android connection or permission failure. A matching configuration and granted
permissions do not by themselves prove that Waze accepts mock GPS.

On Termux, grant location to the native Waze app in the phone's Android settings
and enable the phone's Location service. Waze uses the phone's native GPS; it
does not use the Waydroid mock-location setup or Chrome website permissions.

Focused validation for native-only selection and session behavior:

```bash
git switch feature/waze-live-map
LOGGING_TMP_DIR=/tmp/orc-waze-validation venv/bin/python -m pytest -q apps/orcUi/composition/unit_test/test_waze.py apps/orcUi/composition/unit_test/test_native_waze_backend.py controllers/navigation/unit_test/test_waze_app_controller.py controllers/navigation/unit_test/test_waze_session.py
```

## Multitasking: return to Waze without resetting navigation

An enabled Waze integration provides a **Map / Waze** navigation switch.
Leaving Waze for Settings, Radio, the ORC map or another screen hides/detaches
its surface rather than closing the session. Choose **NAV** to restore the last
navigation view, or use the top-bar switch. The separate Waze panel does not share its presentation state with
Panera or other POI apps. Native Android brings the existing Waze activity back
to the foreground without resending a destination. The Termux viewer reuses its
owned scrcpy process and virtual display. An externally killed process may still require
recovery; this is session retention, not restoration after a device restart.

Fresh host locations continue to feed a retained Waydroid Waze session while
another ORC screen is visible. Cached, simulated and expired fixes are still
excluded. Background audio is not deliberately stopped or muted; actual voice
guidance and Android's behavior while Weston is unmapped need device validation.
The historical web Live Map experiment is no longer a UI fallback.
An already active native session can be restored even after ORC goes offline.

Use **Close Waze** in its toolbar to explicitly end the session. Native close
force-stops only `com.waze`, releases the retained surface, stops its background
location forwarding and returns to the ORC map. Waydroid close uses the verified
local Waydroid ADB target; it needs `adb`, now included by the Linux setup script.
A failed close reports the error and retains the session for retry. Other
Android apps, saved places and Waze sign-in data are not removed. Closing ORC
releases its owned browser/scrcpy resources and GPS feed; it does not force-stop
the externally owned Waydroid app. Use **Close Waze** first if navigation must end.

The native Waze entry does not launch Chrome or show the website's app-store
banner. Android's own Waze first-run screens and location permissions still
apply; ORC does not accept terms or authenticate users automatically.

Device check after updating: start native Waze, select a destination, switch to
Settings and Radio, then return through the sidebar. Confirm the same route,
fresh GPS and audio remain active. Finally choose **Close Waze**, confirm GPS
sharing pauses, and reopen Waze. Repeat on Termux to verify the virtual display
survives hiding. Core focused checks:

```bash
git switch feature/waze-live-map
LOGGING_TMP_DIR=/tmp/orc-waze-validation venv/bin/python -m pytest -q controllers/navigation/unit_test/test_waze_session.py controllers/navigation/unit_test/test_location_sharing_controller.py apps/orcUi/composition/unit_test/test_waze.py apps/orcUi/composition/unit_test/test_scrcpy_waze_player.py frontends/tk/media/unit_test/test_android_app_screen.py
```

The final file includes real Tk lifecycle checks, skipped without `DISPLAY`.

## Home, Work and POI destination handoff

Home and Work remain ORC saved destinations. Select either shortcut, or select a
POI, and choose **Navigate with Waze** in its details popup. The action converts
the stored SI coordinates into a `waze://?ll=LAT,LON&navigate=yes` VIEW intent,
then presents the existing full-width Waze panel with **Back to map**. It does
not change an active ORC route, copy favorites into Waze, or synchronize accounts.
The ordinary **Waze** toolbar button still opens Waze without a destination.
Destination handoff requires online mode and the native Android-panel opt-in;
browser-only configurations report that native Waze is required instead of
silently dropping the selected destination.

Waydroid uses its supported `app intent ACTION URI` session command, avoiding
per-request sudo or a separate ADB setup for destination delivery. Termux uses
`ORC_SCRCPY_WAZE=1`: it waits for the new scrcpy display ID and sends the VIEW
intent explicitly to that virtual display. Hiding the viewer cancels pending
delivery. Missing display acknowledgement or an Android command failure emits
`navigation.waze` / `destination.failed`; it never retries on the phone's default
display. Returning to ORC and selecting the destination again retries delivery.
Destination coordinates and place names are not included in these events.

### First device test: guest navigation

With the compositor and Android session running, close and update ORC:

```bash
git switch feature/waze-live-map
git pull --ff-only
ORC_WAYDROID_PANEL=1 ./runOrcUi --follow-logs
```

1. Open Waze and, if the installed version offers it, choose its guest/continue
   without an account flow. Complete any terms and Android location permissions.
   ORC does not automate or bypass these screens. Do not clear Android app data
   merely to run this test.
2. Return to ORC, select a configured Home or Work destination, and choose
   **Navigate with Waze**. If first-run screens consumed the intent, retry the
   action after completing those screens.
3. Confirm Waze receives the intended destination, offers a route while signed
   out, stays embedded, and returns through **Back to map**. Then try a POI.
4. Test live GPS and route following separately; delivery of a destination does
   not prove navigation or voice guidance works.

Guest availability and destination acceptance are still device-validation gates;
the focused tests cover intent arguments, coordinate units, cancellation and
popup actions, not Waze's account policy. No credentials or signed-in Android
data are included in an ORC build.

Focused developer validation (set `DISPLAY` to run the popup layout tests too):

```bash
git switch feature/waze-live-map
LOGGING_TMP_DIR=/tmp/orc-waze-validation venv/bin/python -m pytest -q controllers/navigation/unit_test/test_waze_app_controller.py apps/launchers/unit_test/test_installed_waydroid_app.py apps/launchers/unit_test/test_waydroid_launcher.py apps/orcUi/composition/unit_test/test_waze.py apps/orcUi/composition/unit_test/test_scrcpy_waze_player.py apps/orcUi/frontend/tk/unit_test/test_navigation_panel.py
```

## Host location sharing and Waydroid GPS

Settings → **Share host location** reuses the navigation service or starts an
ORC-owned user-session producer and loopback message broker when none is running.
The button does not require sudo or a preinstalled systemd unit. Allow location
in the browser and keep that permission page open. Fresh browser fixes become
the navigation producer's position; after ten seconds without a new fix, it
returns to its primary source. Explicit route playback temporarily suspends this
override. Settings distinguishes live, cached, expired and simulated positions.
Closing ORC stops only services that this UI session started.

An already-running navigation producer from an older checkout needs a one-time
restart after updating, so it understands the new location-sharing command.
The producer now preserves Android Bridge sample times in UTC; repeated delivery
of an old sample does not make it fresh. Termux continues using its Android
Bridge source, and native phone Waze keeps its own Android location permissions.

For the Linux Waydroid experiment, start Weston and Waydroid, close ORC, and run
this once as the normal desktop user (the setup script requests sudo for Android
permission changes):

```bash
git switch feature/waze-live-map
git pull --ff-only
sudo apt-get install -y adb
python3 -m scripts.setup_waydroid_location enable
ORC_WAYDROID_PANEL=1 ./runOrcUi --follow-logs
```

Setup verifies the local Waydroid IP, model and ADB identity, saves the previous
mock-location permission and Android location setting, and enables that identity
to supply test GPS. Runtime updates use the explicitly configured ADB device,
without sudo. Repeat setup if the Waydroid IP or ADB connection changes.

Share a live host location in Settings, then open Waze. Only noncached,
nonsimulated samples at most ten seconds old are forwarded, while the Android
app screen is active, or a retained Waze navigation session is active in the
background. Leaving another Android app pauses its visible-screen sharing;
explicitly closing Waze, losing fresh fixes or closing ORC removes the provider
when no other app view needs it. This is an Android-wide mock GPS feed: other Waydroid
apps with location permission can also see it while active. Grant Waze its normal
location permission. Whether Waze accepts and follows this feed still needs VM
validation; unit and loopback integration tests do not establish navigation
compatibility. A VM browser's location may also be approximate.

Close ORC before restoring the saved Android settings:

```bash
git switch feature/waze-live-map
python3 -m scripts.setup_waydroid_location disable
```

Normal shutdown removes the owned provider; forcibly killing ORC cannot guarantee
cleanup. This experiment is intended for the dedicated Waydroid instance.

Native renderer failures now leave a **Map unavailable** message and **Retry
map** control instead of a blank panel. Retry relaunches the renderer; it cannot
repair incompatible libraries. After a Termux package upgrade, a missing `fmt`
symbol still requires rebuilding the native renderer against current packages.

## Linux VM follow-up

The Ubuntu x86_64 VMware device test now successfully embeds Panera through
Waydroid Android 13, with split/expanded layout recovery. The confirmed background
subsurface setting is documented in [POI ordering](poi_ordering.md). That proves
the presentation path, not Waze installation or navigation compatibility.

Google Play previously marked Waze incompatible on this VM while allowing Google
Maps. Android 13 exceeds Waze's documented Android 10 minimum, so the OS version
alone does not explain the rejection. See [Waze requirements](https://support.google.com/waze/answer/6071125?hl=en).
CPU ABI, Play device filtering and other device capabilities remain separate
possibilities. [Waydroid's documentation](https://docs.waydro.id/usage/install-and-run-android-applications)
notes that ARM-only APKs do not run on x86_64. Do not infer the installed Waze
package's ABI from the Play rejection alone.

With Waydroid running, collect these read-only facts before choosing an install
or launch path:

```bash
git switch feature/waze-live-map
sudo waydroid shell -- getprop ro.product.cpu.abilist
sudo waydroid shell -- getprop ro.dalvik.vm.native.bridge
sudo waydroid shell -- pm path com.waze
```

These commands are read-only. The VM subsequently reported only x86/x86_64 with
native bridge `0`. After a VMware snapshot, the user installed the community
installer's Android 13 libndk translation, confirmed ARM ABIs and
`libndk_translation.so`, and successfully installed Waze through Play. Waze runs
but initially reported no GPS while ORC had only a cached position. The optional
host-location experiment above now provides a separate Android GPS adapter.

### Native Waze window integration

With `ORC_WAYDROID_PANEL=1`, Navigation's existing Waze button now tries the
installed `com.waze` package through Waydroid, then presents it in the same
Android panel used by Panera. Waze opens full width without a split toggle,
because a second map is redundant. Other apps retain their split and expanded
layouts. Existing Weston sizing and automatic chrome trimming are reused.
Back to map returns to Navigation. The breadcrumb uses the installed app name.
The browser fallback also has an explicit ORC-styled BACK TO MAP toolbar above
the hosted page, including after dark/light theme changes. Opening Waze records
`navigation.waze` / `app.open.requested` with `backend` set to `native` or
`browser`; use that event to distinguish a native panel issue from fallback UI.

The installed-app lookup and launch run off the UI thread. Repeated pending
requests coalesce; closing ORC or switching offline invalidates pending display
callbacks. A missing app or failed Waydroid launch falls back to the existing
embedded Waze web Live Map. Without the Android-panel opt-in, Waze retains the
browser behavior. Waze must remain enabled in ORC's application configuration.

Start the dedicated Weston and Waydroid session using the startup instructions
below, then from the normal desktop terminal run:

```bash
git switch feature/waze-live-map
git pull --ff-only
source venv/bin/activate
ORC_WAYDROID_PANEL=1 ./runOrcUi
```

Choose Navigation → Waze. Validate app embedding, full-width layout, input alignment,
Back to map and reopening. Window embedding alone does not supply Android GPS,
select a destination, or establish working turn-by-turn navigation. Configure
the separate host-location experiment above to test GPS forwarding. App
installation and window embedding were device-tested; GPS forwarding still
needs the VM test. Focused validation:

```bash
git switch feature/waze-live-map
LOGGING_TMP_DIR=/tmp/orc-waze-validation venv/bin/python -m pytest -q controllers/navigation/unit_test/test_waze_app_controller.py apps/launchers/unit_test/test_installed_waydroid_app.py apps/orcUi/composition/unit_test/test_waze.py apps/orcUi/composition/unit_test/test_android_app_view.py
```

## Earlier investigation baseline

### Termux native Waze experiment

Retaining the native viewer requires the X11 root window. When `xwininfo` is
absent, ORC reads it through the system X11 library already used by Tk. A missing
`xwininfo` command therefore does not abort the viewer after Android starts Waze.
Connection failures still appear as a launch error in ORC; check `DISPLAY` and
access to the running Termux X server.

On native Termux with Termux:X11, opt into the scrcpy backend instead of Waydroid:

```bash
git switch feature/waze-live-map
git pull --ff-only
adb get-state
ORC_SCRCPY_WAZE=1 ./runOrcUi
```

ADB must already be paired/connected to the same Android phone and report `device`.
The launcher does not pair devices, choose an arbitrary device when multiple are
connected, or disconnect ADB. If needed, set `ANDROID_SERIAL` to the intended
already-connected device; both adb and scrcpy inherit it. Run in native Termux,
where scrcpy/adb are installed, rather than only inside Debian proot.

Navigation → Waze checks package availability using ADB, then starts an owned
scrcpy viewer with a dedicated 1280×720/240 Android virtual display and launches
`com.waze`. This avoids mirroring ORC recursively. It uses an ORC-specific window
title, borderless X11 output, full-width presentation and Back to map. It applies
no Waydroid-specific crop or Android configuration overrides. On departure ORC
signals only its own scrcpy process and reaps it on a background worker, so the
viewer teardown wait does not block the Tk thread. Each viewer launch has a
unique window title to prevent a fast reopen from attaching the retiring viewer.
scrcpy's normal virtual-display teardown
applies, so this experiment does not promise an ongoing route survives closing
the panel. The installed Android app remains installed. Audio forwarding is
disabled; audio behavior on the phone still needs testing. Native Android owns
GPS permissions and theme; no ORC location is injected.

OpenGL is the default renderer. Earlier standalone phone tests had corruption
with OpenGL and GLES; this integration does not establish that driver issue is
fixed. To isolate it with the previously working software renderer:

```bash
git switch feature/waze-live-map
ORC_SCRCPY_WAZE=1 ORC_SCRCPY_RENDERER=software ./runOrcUi
```

`ORC_SCRCPY_RENDERER=opengles2` is also available. Validate Waze rendering, clicks,
text input, Back to map and reopening. The viewer writes diagnostics to Termux's
temporary directory. For a launch/render failure, share the tail:

```bash
git switch feature/waze-live-map
tail -n 60 "$TMPDIR/orc-scrcpy-waze.log" | termux-clipboard-set
```

If no log exists, check `adb get-state`: a failed installed-package check falls
back to the existing web Live Map before the viewer is started. Termux device
validation remains pending; cloud tests cover commands, owned-process teardown
and fullscreen-only UI behavior, not phone graphics or GPS reception.

If ORC's map lacks location independently of Waze, inspect Android Bridge
readiness without sharing coordinates:

```bash
git switch feature/waze-live-map
python scripts/probe_android_location.py | tee "$TMPDIR/orc-android-location-probe.json" | termux-clipboard-set
```

This reads `/health` and `/location` at the configured environment override
`OPENROADCODE_ANDROID_BRIDGE_URL`, or localhost port 8766 by default. It reports
readiness/provider/fix age and whether coordinate fields exist, without printing
the coordinates. It does not start the Bridge or navigation service, request
permissions, change location settings, or prove the running service's selected
configuration matches the probe. If the Bridge is ready with fresh fixes, inspect
the navigation producer configuration and bus delivery next. If it is unavailable
or waiting for a fix, check the Android Bridge foreground service and its Android
location permission first. The branch leaves AndroidPositionSource's `/location`
reader and the Termux GPS input profile unchanged; it adds a route-playback wrapper
around live sources, while desktop browser fallback is disabled on Termux.

If the bridge reports a fresh fix but Recenter does nothing, validate the complete
bus contract rather than only the presence of latitude/longitude fields:

```bash
git switch feature/waze-live-map
python -m scripts.probe_android_location --bus | tee "$TMPDIR/orc-android-location-probe.json" | termux-clipboard-set
```

The bounded bus check uses the same strict decoder as the map and omits position
coordinates. A running navigation service retains its imported code after a Git
update: restart the supervised service and ORC to load changes before comparing
their message formats. Do not start a second producer alongside the supervised
one. The UI logs `map_renderer.position` events for the first accepted live fix,
Recenter requests and dispatch failures; repeated identical errors are suppressed.
Optional position-observer failures are isolated so they cannot block the native
map's position and camera updates. These changes improve recovery and diagnosis;
they do not establish the cause of a particular phone's missing marker without
the device results.

### Original baseline

Status: repository/source investigation, not a device compatibility result.
No Android runtime, kernel, application, display configuration, or existing Waze
browser behavior was changed. This checkout is an x86_64 cloud environment with
no connected Android/Pi device, Waydroid, ADB, or scrcpy. Actual navigation,
rendering performance and audio on the two targets remain untested.

## What the POI work already provides

`apps/launchers/android_app_launcher.py` selects Android Bridge on the Android
host and tries Waydroid on Linux, with browser fallbacks. The concrete adapters
are `android_bridge_launcher.py`, `android_host_action_client.py`, and
`waydroid_launcher.py`. `docs/poi_ordering.md` documents this split.

This is app launch/handoff support. It does not prove that Waydroid is installed
or working on a specific Pi, and it provides no Android display capture,
app-window embedding, audio transport, or Android-side ORC GPS provider.

The existing Waydroid `is_available()` checks command presence and a successful
`waydroid status` exit code. That alone is not session readiness: status may exit
successfully with a stopped session. The diagnostic below reports Session and
Container separately and queries apps only when both are already running.

## Feasible paths to test

| Target | Android runtime | Presentation candidate | Location |
| --- | --- | --- | --- |
| Termux/X11 on Android | Existing host Android and its Waze app | Dedicated Android virtual display mirrored into an X11 scrcpy window | Waze's native Android GPS/permissions |
| Standalone Pi 5 | Existing Linux Waydroid installation, if working | Nested Weston X11 host, or an X11 scrcpy viewer connected to Waydroid ADB | A separately validated Android location provider fed from ORC/GNSS |

### Termux

Ordinary unrooted proot does not supply real container privileges, namespaces or
kernel-module support. Treat Waydroid-inside-proot as unsuitable for this path;
use the Android host which already runs on the phone. A rooted/custom system
would be a different target and is not assumed here.
Source: [PRoot-Distro limitations](https://github.com/termux/proot-distro#limitations).

The existing Bridge can hand off to an installed Android package. To keep an app
inside ORC's X11 panel, a display/control transport is still needed. scrcpy
supports starting an app on a dedicated virtual display. That is a candidate,
not a confirmed Waze solution. Mirroring the physical phone display back into
Termux:X11 risks a recursive view of ORC; the dedicated display avoids relying on
that layout. An authorized ADB connection is required, including for same-device
use; running under Termux does not itself grant ADB/shell privileges.
Sources: [scrcpy virtual display](https://github.com/Genymobile/scrcpy/blob/master/doc/virtual-display.md),
[connections](https://github.com/Genymobile/scrcpy/blob/master/doc/connection.md).

First verify that native Waze starts and offers actual navigation. Then separately
test whether it renders and accepts touch/text input on a virtual display, uses
native GPS, and remains usable alongside Termux:X11. Its secondary-display support
and background-location behavior have not been established by this investigation.
No mirroring or pairing commands are run by the diagnostic.

### Pi 5

Waydroid needs kernel binder plus ashmem or memfd support, and a Wayland compositor.
The repository launcher does not install these or validate the GPU/Android image.
Sources: [kernel prerequisites](https://docs.waydro.id/debugging/getting-essential-information),
[Waydroid installation and sessions](https://docs.waydro.id/usage/install-on-desktops).

The Pi 5 kernel commonly uses 16 KiB pages. Image and application compatibility
must be checked on the actual host; this is not a reason to change kernels
without evidence. Raspberry Pi documents both its 16 KiB BCM2712 kernel and a
4 KiB alternative: [kernel documentation](https://www.raspberrypi.com/documentation/computers/linux_kernel.html).

ORC currently embeds X11 clients. A native Wayland app surface cannot simply be
reparented with xdotool. Weston can run nested on X11; an experiment could host
Waydroid inside that compositor and embed the compositor's X11 window. This avoids
requiring a video encode/decode round trip, but GPU, input, resize and compositor
lifecycle still need testing. Source: [Weston backends](https://wayland.pages.freedesktop.org/weston/toc/running-weston.html).

Alternatively, Waydroid exposes an ADB connection, which may allow the same
scrcpy viewer approach as Termux. This needs a working Android video encoder;
software-encoding performance on the Pi must be measured. Neither smooth capture
nor hardware encoding is established by the existing POI launch code.
Source: [Waydroid ADB](https://docs.waydro.id/faq/using-adb-with-waydroid).

Before any ORC embedding, confirm Waze works in the existing Waydroid desktop and
image: installation, sign-in, route calculation, location and voice guidance.
Waze currently documents Android 10+; it does not certify this Waydroid/Pi
configuration. Check image Android version and required services, rather than
assuming every VANILLA or GAPPS image works. If a GAPPS image needs certification,
follow Waydroid's own procedure; the probe does not inspect or transmit IDs.
Sources: [Waze requirements](https://support.google.com/waze/answer/6071125?hl=en),
[Waydroid certification](https://docs.waydro.id/faq/google-play-certification).

## GPS, audio and lifecycle gates

The Chromium GPS bridge alone does not provide Android location. The opt-in
Waydroid adapter above supplies a separate mock-location experiment. Test whether
Waze accepts and follows that feed; a fixed map pin is not proof of navigation.
Native Waze on the phone uses its normal location permission.

scrcpy audio forwarding is documented for Android 11+, with Android-version
conditions; video success alone does not prove voice guidance works. For native
Termux, decide whether guidance plays on Android or is captured into ORC, avoiding
duplicate output. For the Pi, test the Waydroid audio path and interaction with
ORC media. Source: [scrcpy audio](https://github.com/Genymobile/scrcpy/blob/master/doc/audio.md).

Before implementation, agree whether leaving the Waze view hides its display or
stops navigation. Display ownership and app/navigation ownership are separate:
scrcpy's default virtual-display teardown can destroy the displayed activities.
Also validate keyboard placement on the secondary display, repeated open/close,
rotation, resize, offline behavior, app crash and reconnect. Existing X11 embedding
and text-input contracts may be reusable; app control belongs in controllers and
platform adapters, not Tk widgets.

## Read-only device evidence

### Ubuntu 24.04 Linux VM setup

The optional installer supports Ubuntu noble on amd64/arm64 only; it is not a
universal Linux or Pi OS installer. It loads the installed Binder module, installs
Weston/diagnostics, adds the official Waydroid APT repository when no package
candidate exists, and installs Waydroid. Repository setup executes the upstream
HTTPS installer as root. Review `development/debian/setup_waydroid.sh` before use.
It stops on errors and does not change the desktop login session or install Waze.
The optional GAPPS initialization downloads an Android image with Google services;
an existing configuration is preserved, not converted or reset.

```bash
git switch feature/waze-live-map
git pull --ff-only
bash development/debian/setup_waydroid.sh --init-gapps
```

In the existing X11 desktop, start nested Weston (skip if already running):

```bash
git switch feature/waze-live-map
bash development/debian/start_waydroid_display.sh
```

The launcher uses Weston's X11 backend, `kiosk-shell.so`, and `--idle-time=0`.
Kiosk mode gives the Android surface the complete output and reconfigures it when
the embedded output changes size; it does not depend on a desktop app's maximized
state. It has no desktop panel or nested lock screen. The Linux host desktop's
session/lock policy is unchanged. Start from the normal desktop, without sudo,
and leave the launcher terminal open.

For the first switch from desktop shell, close ORC, stop the Waydroid session and
container, then Ctrl+C the old Weston before running the launcher. It refuses an
occupied Wayland socket and does not kill an unrelated compositor. Its cleanup
owns only the Weston process it starts. A runtime marker lets ORC recognize the
live kiosk process and omit the desktop-panel crop automatically. If Weston
reports that `kiosk-shell.so` is missing, send that error; do not change kernels,
graphics drivers or Android images to address it.

Leave Weston running. In a second terminal, start the session as your normal user:

```bash
git switch feature/waze-live-map
WAYLAND_DISPLAY=wayland-0 waydroid session start
```

Leave the session running. In a third terminal:

```bash
git switch feature/waze-live-map
WAYLAND_DISPLAY=wayland-0 waydroid show-full-ui
```

First validate the Android desktop. Google Play may need Waydroid certification
(see the official link above). Availability of an x86_64-compatible Waze package,
Android GPU support, location and voice guidance remain separate device gates.
Do not install unofficial ARM translation layers or force software rendering as
part of this installer. VMware SVGA3D acceleration in Weston alone does not prove
Android acceleration works. No Android app embedding is wired by this script.

Run `scripts/probe_android_navigation.py` on each actual device. It uses Python's
standard library and existing tools only. It does not install/start Waydroid,
start an ADB server, pair a device, launch Waze, or change settings. It reports
kernel/page size, display environment presence, tool availability, selected scrcpy
capabilities and already-running Waydroid state. It omits GPS, serial numbers,
network addresses and installed-app inventories. Native Android package visibility
can be restricted: an unsuccessful Waze query is reported as unknown, not absent.
Binder path presence and display environment variables are observations, not
proof of runtime readiness.

Run from the repository in **native Termux**, rather than only inside Debian
proot, so Android host tools can be observed:

```bash
git switch feature/waze-live-map
git pull --ff-only
python scripts/probe_android_navigation.py | tee "$TMPDIR/orc-android-navigation-probe.json" | termux-clipboard-set
```

Run again on the **Pi desktop** where ORC/Waydroid would run:

```bash
git switch feature/waze-live-map
git pull --ff-only
python3 scripts/probe_android_navigation.py
```

Share the Termux clipboard report and the Pi report. Those determine whether the
next step is a native Waze display experiment, Pi runtime diagnosis, or testing an
already-working Waydroid Waze app. Review those device results before selecting
the first runtime/display experiment.

Portable probe validation:

```bash
git switch feature/waze-live-map
python -m pytest scripts/unit_test/test_probe_android_navigation.py -q
```

Four focused probe tests and a local run passed. The local run correctly reported
no Android/Waydroid tooling; it is not a device test. No broad test suite or full
quality gate was run for this investigation.
