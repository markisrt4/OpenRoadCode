# Ordering and websites from a POI

Select a food marker in Navigation, then choose ORDER or WEBSITE. ORDER appears
for businesses with a configured ordering integration (currently Panera and
McDonald's). WEBSITE appears whenever the POI has a valid OSM website link.
An independent restaurant's website may offer ordering, but ORC does not assume
that every website is an ordering service. Cached POI data remains searchable
offline; Order and Website require ORC's online mode.

| Platform | ORDER | WEBSITE |
| --- | --- | --- |
| Termux / Android | Android Bridge opens the configured package if installed, otherwise the configured web destination | `termux-open-url` opens the website directly |
| Linux | An installed Waydroid package is tried first; missing package, missing Waydroid, or failed launch falls back to the default desktop browser | Default desktop browser |

Linux uses `gio open` when available, otherwise `xdg-open` from xdg-utils.
Configure a default browser in the desktop environment. It opens a normal browser
window with that browser's existing profile. Waydroid and desktop handoffs have
bounded command waits and run outside the Tk thread. ORC reports launch failures
and leaves the POI card open for retry. An opener timeout can occur after a window
has opened; check before retrying. No Waydroid installation is needed for the web
path. Termux requires the Android Bridge app with its `orcbridge://launch` handler
and `termux-open-url` for ORDER. WEBSITE uses `termux-open-url` directly and
does not depend on Bridge. Ordering requires Bridge commit `ca82b7b` or newer;
the fast network-state monitoring described in [Online/offline mode](online_offline_mode.md)
requires `92c11b4` or newer.

An accepted launch is a handoff, not confirmation of an order. ORC does not submit
purchases or select a restaurant location automatically: select/confirm the store,
items, and payment in the restaurant app or site. Some providers require their
mobile app for ordering; a fallback website cannot add ordering capabilities that
the provider does not offer.

### Experimental Linux Android panel

On `feature/waze-live-map`, Linux can opt into presenting successful Waydroid
ORDER launches inside ORC. Start exactly one **dedicated nested Weston**, using
the standard `Weston Compositor` X11 class, and start Android there before ORC.
Use `wayland-0`; a custom socket previously left Android's hardware compositor
looking at the wrong display. See [VM setup](waze_android_investigation.md).
For this dedicated nested desktop, use Weston's `--idle-time=0` startup option
to prevent its idle lock screen from appearing inside ORC. Host desktop locking
is unchanged.
Do not use a Weston instance containing unrelated desktop work: the whole nested
compositor window is borrowed and resized, including its desktop chrome.
Use the dedicated [kiosk launcher](waze_android_investigation.md) for the resize
experiment. Desktop-shell maximization previously left Android at 567x505 when
ORC expanded; resizing the outer X11 frame alone did not resolve it.

Launch ORC from the normal X11 desktop:

```bash
git switch feature/waze-live-map
git pull --ff-only
source venv/bin/activate
ORC_WAYDROID_PANEL=1 ./runOrcUi
```

Select a Panera POI and ORDER. A successful Android launch queues presentation
on the UI thread and opens an Android app screen with Back to Navigation.
The breadcrumb is NAV followed by the installed app's display name. The default
view has equal map-left/app-right panes. Expand app fills the content area; Split
view restores both panes without restarting Android or its current activity.
The map uses the existing renderer lifecycle and stops when expanded or hidden.
After each split mount, ORC replays the retained Navigation camera (including
zoom, center, pitch and bearing), markers and vehicle position. Startup replays
are bounded and canceled when the map is hidden; it no longer starts in the
renderer dataset overview by omission.
This is a map presentation, not a second copy of Navigation's POI/route controls.
The
external-window root lookup uses `xwininfo` from `x11-utils` (included by the
desktop and Waydroid setup scripts).
The screen fills the landscape content area. ORC does not stretch individual Android
app contents or force their orientation; portrait-only app compatibility layout
and any side margins remain Android-controlled and need device validation.
Termux's native Bridge behavior and desktop browser fallbacks remain unchanged.
Missing/multiple Weston windows produce a panel launch error rather than choosing
an arbitrary compositor. Turn off the flag to return to external handoff behavior.

Back hides/detaches Weston without stopping Android, its apps, or navigation.
Reopening ORDER remaps it inside ORC. Closing ORC detaches borrowed windows to the
X11 root before destroying its own host. A theme change repaints ORC chrome without
restarting Android. ORC borrows the compositor, without owning the Android session.
The POI launcher already selected the app, so the view no longer calls
`waydroid show-full-ui`: Waydroid 1.6.2 uses that command to select the whole
Android desktop and write `policy_control=null*`, resetting the app launch policy.
Use Waydroid's normal controls to stop navigation or Android.

VM validation: open Panera, expand, restore split, Back, reopen, resize ORC, switch theme, then close
ORC. Confirm the app remains available using `waydroid app list` and Android can
still be shown. Test portrait margins explicitly; the current patch does not add
an Android orientation override. Graphical Waydroid testing is pending on the VM;
focused automated checks cover launch/fallback, queued shutdown and borrowed-window
cleanup. The full quality gate remains a user-run check before merge.

#### Narrow portrait layouts on the VM

The outer pane can grow, but a portrait-only Android activity may remain
letterboxed. Shrinking the desktop can leave that compatibility viewport below
the app's usable logical width. ORC does not stretch the bitmap to hide this.
On the dedicated experimental VM, record Android's existing density, then try a
lower density to provide more logical space within the portrait viewport:

```bash
git switch feature/waze-live-map
sudo waydroid shell -- wm density | tee /tmp/orc-waydroid-density-before.txt
sudo waydroid shell -- wm density 120
```

This is an optional diagnostic affecting all Android apps in this VM, not a
per-app ORC default. Text becomes smaller. If it helps, test readability and touch
targets; if not, revert. If the recorded output listed an Override density,
restore that exact value using `wm density VALUE`. If it listed only Physical
density, remove the diagnostic override:

```bash
git switch feature/waze-live-map
sudo waydroid shell -- wm density reset
```

Expanding ORC alone does not change a portrait-only Android activity. The
following **optional, VM-wide landscape experiment** uses commands verified in
LineageOS 20 / Android 13's WindowManager shell source. It saves user rotation,
fixed-to-user-rotation, ignore-orientation-request and force-resizable settings
before changing them. It does not assume that rotation 1 always means landscape:
the nested Waydroid display can have natural landscape at rotation 0.

With Waydroid running, select Expand app first, then run from the normal desktop:

```bash
git switch feature/waze-live-map
python3 scripts/waydroid_landscape.py apply
```

This uses sudo for Android shell access and affects every app on Android display
0 in this VM. It is not ORC's default or a per-app guarantee. Close Panera from
Android Recents and reopen it via ORDER if the current activity keeps its old
layout. Portrait-only applications may render badly even when forced resizable;
app compatibility still requires a device test. To undo:

```bash
git switch feature/waze-live-map
python3 scripts/waydroid_landscape.py restore
```

The backup is kept under the desktop user's state directory until restore
succeeds. Partial failures retain it. Do not repeatedly apply without restoring.

#### Hide Android status/navigation bars (optional VM setup)

Frame trimming is automatic, with no trim toggle in the ordinary toolbar.
ORC's Back/Expand controls remain outside the clipped viewport.
This does not hide Android system bars globally or change app permissions. The
initial desktop-shell trim is 32 pixels at the top and 48 at the bottom, sized for
the nested Weston panel and navigation area on this VM. With the kiosk launcher,
the live process marker selects zero top crop because there is no desktop panel.
Waydroid's app-first launch requests
immersive status mode; ORC does not reset it by opening full desktop mode again.
Different density/chrome sizes can require adjustment. Expand/Split does not
relaunch the app. Toolbar buttons use ORC control colors in dark and light mode.

The earlier helper used `policy_control`. Upstream LineageOS removed that hook,
but Waydroid's Android 13 vendor patches reimplement it. The earlier inference
from upstream source alone was incomplete: our own `show-full-ui` call also
reset the setting on presentation. The helper did not reliably hide bars in the
tested integration; do not keep reapplying it. If it was applied, restore it:

```bash
git switch feature/waze-live-map
bash development/debian/waydroid_system_bars.sh restore
```

For older images only, the helper's one-time admin action requires sudo and a running Waydroid. It saves the
previous setting under the desktop user's state directory, refuses to overwrite
an existing immersive policy, and does not add privileges to the ORC UI. A literal
`null*` placeholder is accepted and saved exactly for restoration. The
setting persists until restored, including outside ORC. To undo:

```bash
git switch feature/waze-live-map
bash development/debian/waydroid_system_bars.sh restore
```

If another tool changed the policy afterward, restore refuses to overwrite it.
The helper is tested against a fake settings store; actual Android bar behavior
remains a VM validation step.

#### Diagnose a POI popup that does not reopen

The VM trace showed that a click after Back to map reached ORC with Panera's
correct marker ID/index, followed by selection mismatch/missed events. The
session wrapper still called search.clear() during close, emptying the shared
metadata despite the retained markers. Close now only releases transient source
resources; explicit Clear/Search actions retain their metadata-clearing behavior.
A regression test exercises the factory and real session wrapper across close
and remount, reproduces the failure with the old close behavior, and passes with
the fix. Actual popup behavior still needs a VM retry.

POI polling also rearms after recoverable errors. Stream lifetime, named selection
and popup handoff diagnostics distinguish transport/selection failures from
presentation failures if another symptom occurs.

```bash
git switch feature/waze-live-map
ORC_LOG_COMPONENT_LEVELS='navigation.poi=DEBUG,map_renderer=DEBUG' ORC_WAYDROID_PANEL=1 ./runOrcUi --follow-logs --log-level DEBUG 2>&1 | tee /tmp/orc-poi-reopen.log
```

`--log-level DEBUG` is necessary for the live viewer as well as collection; the
old command enabled component debug records but left the viewer at INFO.
Open Panera's popup, leave Navigation, press Back to map to return to full
Navigation, and click the same marker several
times. Close ORC and collect the focused excerpt (debug clicks can include
coordinates; redact them if desired):

```bash
git switch feature/waze-live-map
grep -E -A8 -B2 'navigation.poi|map.clicked|showing POI|Traceback' /tmp/orc-poi-reopen.log | tail -n 160
```

#### Expand sizing

ORC now flushes Tk's pending grid geometry before resizing the borrowed window
and reapplies the current dimensions after a short compositor settle interval.
Obsolete callbacks are rejected on hide/reopen. This prevents the immediate resize
from using the old split-pane allocation. The VM previously reported Android's
physical display as 567x505 even while ORC was expanded, with no persistent size
override. After updating, verify both the visible app width and `wm size`; the
Tk geometry test alone does not prove Waydroid adopted the new output mode.

The kiosk launcher is the next resize experiment. Its output-resize handler
explicitly reconfigures fullscreen Wayland clients, avoiding dependence on
whether Android's desktop-mode surface remained maximized. This has source-level
support in Weston 13; actual Waydroid split/expand behavior needs VM validation.

POI result metadata is now scoped to the factory alongside retained renderer
markers. Returning to Navigation creates fresh event transports and action
sessions but preserves the marker-to-business lookup, so an existing Panera
marker remains selectable without running a new search. Explicitly clearing or
replacing search results also clears or replaces this metadata.

Focused validation for the remount, consent recovery and system-bar helper:

```bash
git switch feature/waze-live-map
python -m pytest controllers/poi/unit_test/test_poi_search_controller.py apps/orcUi/composition/unit_test/test_navigation_places.py apps/launchers/unit_test/test_host_location_permission.py controllers/navigation/unit_test/test_host_location_settings_controller.py scripts/unit_test/test_waydroid_system_bars.py -q
```

Focused local validation:

```bash
git switch feature/waze-live-map
python -m pytest apps/orcUi/composition/unit_test/test_android_app_view.py apps/launchers/unit_test/test_android_app_launcher.py apps/orcUi/composition/unit_test/test_application.py apps/orcUi/composition/unit_test/test_waze.py frontends/x11/unit_test/test_x11_window_embedder.py frontends/tk/media/unit_test/test_android_app_screen.py -q
```

If ORC has closed and the borrowed Weston window remains hidden, remap it from
the normal X11 terminal (after confirming only the dedicated compositor exists):

```bash
git switch feature/waze-live-map
xdotool search --class '^Weston Compositor$' windowmap
```

## Login sessions

ORC hands off to the restaurant app or the desktop's configured browser and does
not store restaurant passwords, payment details, or login tokens. The destination
keeps its own login session: Android app storage on Termux, app storage inside
Waydroid, or cookies in the desktop/Android browser profile. Those sessions are
separate across devices and between the app and website; providers may expire
sessions or request verification. To sign out or clear a session, use the app or
browser's controls. Test retention by signing in, reopening from the same POI,
and restarting ORC before reopening again. No purchase is needed for this test.

## Updating and testing

Update either platform:

```bash
cd ~/src/OpenRoadCode
git switch android-linux-food-apps
git pull --ff-only origin android-linux-food-apps
./runOrcUi
```

For a known Panera POI, choose ORDER on Termux and confirm the installed app comes
forward; on a phone without that app, confirm the website opens. On Linux, try
ORDER with and without the package installed in Waydroid. Without Waydroid it
should open the web destination. Select a POI with an OSM website and confirm
WEBSITE opens on both platforms. During a slow launch the map should remain
responsive and repeated clicks should not start additional launches. Switch
OFFLINE and confirm neither online action can launch, while Navigate still works.
