# Native Waze investigation: Termux and Raspberry Pi 5

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

The existing Chromium GPS bridge does not provide Android location. Native Waze
on the phone should use its normal location permission. Waydroid needs a distinct,
verified Android provider or mock-location experiment; test whether Waze accepts
and follows that feed before designing a permanent ORC adapter. Do not treat a
fixed map pin as proof of navigation.

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
