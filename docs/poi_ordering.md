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
Do not use a Weston instance containing unrelated desktop work: the whole nested
compositor window is borrowed and resized, including its desktop chrome.

Launch ORC from the normal X11 desktop:

```bash
git switch feature/waze-live-map
git pull --ff-only
source venv/bin/activate
ORC_WAYDROID_PANEL=1 ./runOrcUi
```

Select a Panera POI and ORDER. A successful Android launch queues presentation
on the UI thread and opens an Android app screen with Back to Navigation. The
external-window root lookup uses `xwininfo` from `x11-utils` (included by the
desktop and Waydroid setup scripts).
The
screen fills the landscape content area. ORC does not stretch individual Android
app contents or force their orientation; portrait-only app compatibility layout
and any side margins remain Android-controlled and need device validation.
Termux's native Bridge behavior and desktop browser fallbacks remain unchanged.
Missing/multiple Weston windows produce a panel launch error rather than choosing
an arbitrary compositor. Turn off the flag to return to external handoff behavior.

Back hides/detaches Weston without stopping Android, its apps, or navigation.
Reopening ORDER remaps it inside ORC. Closing ORC detaches borrowed windows to the
X11 root before destroying its own host. A theme change repaints ORC chrome without
restarting Android. ORC owns only its `show-full-ui` command client, not the session
or compositor. Use Waydroid's normal controls to stop navigation or Android.

VM validation: open Panera, Back, reopen, resize ORC, switch theme, then close
ORC. Confirm the app remains available using `waydroid app list` and Android can
still be shown. Test portrait margins explicitly; the current patch does not add
an Android orientation override. Graphical Waydroid testing is pending on the VM;
focused automated checks cover launch/fallback, queued shutdown and borrowed-window
cleanup. The full quality gate remains a user-run check before merge.

Focused local validation:

```bash
git switch feature/waze-live-map
python -m pytest apps/orcUi/composition/unit_test/test_android_app_view.py apps/launchers/unit_test/test_android_app_launcher.py apps/orcUi/composition/unit_test/test_application.py apps/orcUi/composition/unit_test/test_waze.py frontends/x11/unit_test/test_x11_window_embedder.py -q
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
