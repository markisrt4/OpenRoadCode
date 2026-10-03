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
