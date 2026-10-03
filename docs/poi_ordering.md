# Ordering and websites from a POI

Select a food marker in Navigation, then choose ORDER or WEBSITE. ORDER appears
for businesses with a configured ordering integration (currently Panera and
McDonald's). WEBSITE appears whenever the POI has a valid OSM website link.
An independent restaurant's website may offer ordering, but ORC does not assume
that every website is an ordering service. Cached POI data remains searchable
offline; Order and Website require ORC's online mode.

| Platform | ORDER | WEBSITE |
| --- | --- | --- |
| Termux / Android | Android Bridge opens the configured package if installed, otherwise the configured web destination | Android Bridge opens the website |
| Linux | An installed Waydroid package is tried first; missing package, missing Waydroid, or failed launch falls back to the default desktop browser | Default desktop browser |

Linux uses `gio open` when available, otherwise `xdg-open` from xdg-utils.
Configure a default browser in the desktop environment. It opens a normal browser
window with that browser's existing profile. Waydroid and desktop handoffs have
bounded command waits and run outside the Tk thread. ORC reports launch failures
and leaves the POI card open for retry. An opener timeout can occur after a window
has opened; check before retrying. No Waydroid installation is needed for the web
path. Termux requires the Android Bridge app with its `orcbridge://launch` handler
and `termux-open-url`. This update does not require a new Bridge APK.

An accepted launch is a handoff, not confirmation of an order. ORC does not submit
purchases or select a restaurant location automatically: select/confirm the store,
items, and payment in the restaurant app or site. Some providers require their
mobile app for ordering; a fallback website cannot add ordering capabilities that
the provider does not offer.

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
