# Experimental Waze Live Map

The **Waze** button at the right of Navigation’s top row opens the official
full Waze Live Map (`https://www.waze.com/live-map`) in an ORC-owned browser
panel. It uses the existing X11 browser hosting, with a separate browser
profile and a Back action to Navigation. It does not add a left-sidebar entry.
Leaving the screen, entering offline mode,
or closing ORC stops the browser and cancels pending launches.

This requires an online connection, an existing supported Chromium/Chrome setup,
X11 and `xdotool`, as used by ORC's browser media panels. Raspberry Pi 5 rendering
and touchscreen behavior still need device validation. Native Wayland embedding
is not provided; use the existing ORC X11 session.

Configure `[apps.waze]` in `config/applications.toml` (Linux/Pi) or
`config/applications.termux.toml` (Termux). The default opens the full Live Map
so its **Driving directions** controls are available. Existing custom URLs remain
respected; the old compact embed URL can still be configured explicitly.
Set `enabled = false` to remove the button. Existing custom application
configs without a Waze entry continue to work without a Waze screen.

Waze receives ORC's live GPS position while its screen is open. A local-only
Chromium control connection on port 9224 supplies the browser geolocation API
and grants location access to the Waze page. This avoids depending on Linux
Chromium's location provider to obtain Android GPS in Termux. It shares your
position with Waze; it does not send ORC routes or POIs or extract Waze data into
MapLibre. Location forwarding stops when the screen is hidden or closed.

Only future live, noncached fixes from ORC's navigation stream are used. Invalid
or unavailable fixes clear browser location, and fixes expire after ten seconds
without an update. A map center or cached startup position is never used as a GPS fix.
The bridge uses a conservative 50 m accuracy estimate because this stream carries
position without measured accuracy. Waze can still show unavailable location if
ORC has no live fix; verify the Android sensor bridge/navigation service first.

The local browser integration has been exercised in headless Chromium with a
local test page, including moving fixes, invalidation and connection teardown.
The actual Waze page and Android/Termux integration still need device validation.

This is an online traffic/map experiment, not the mobile Waze app or voice-guided turn-by-turn navigation.
Enter an origin and destination under **Driving directions** to preview routes.
Starting navigation on a phone is a separate Waze mobile-app action.

This experimental browser host preserves Waze's presentation. The full website
is distinct from the [documented iframe](https://developers.google.com/waze/iframe/):
iframe documentation does not establish permission to host the full website in
a desktop application. Waze's terms still apply; this experiment does not settle
that licensing question.

## Try on Termux or the Pi

From the repository checkout:

```bash
git switch feature/waze-live-map
./runOrcUi
```

Open **Navigation**, then select **Waze** at the top right while online. Check that the map loads, pan/zoom work by touch,
resizing stays inside ORC, and Back returns Navigation. Confirm **Driving
directions** is visible, enter a starting point and destination, and select a
route preview. If the page is cramped, check its responsive layout at the device
resolution. Reopen the screen repeatedly,
switch to Navigation, then toggle offline while Waze is open: its browser should
close, and normal ORC navigation should continue. Re-enable online and reopen
Waze, tap its location control and confirm it uses your live position. Move with
an active GPS fix and confirm updates. Then close ORC and check that the Waze
browser exits. If location still fails, distinguish an absent ORC GPS fix from
Waze refusing browser geolocation; browser consent alone does not establish that
Android GPS is reaching Linux Chromium.

Focused portable validation:

```bash
git switch feature/waze-live-map
python -m pytest apps/orcUi/composition/unit_test/test_waze.py apps/orcUi/frontend/tk/unit_test/test_waze_toolbar.py controllers/navigation/unit_test/test_waze_location_player.py protocols/chromium/unit_test/test_chromium_devtools_session.py -q
python scripts/check_ui_boundaries.py
```

Full validation remains pending the user-run quality gate before merge.

## Routing controls and browser startup

The compact embed searches for an address and places a pin. Waze documents a
link in the lower-left corner leading to search/routing options. The full
[Live Map](https://www.waze.com/live-map) exposes **Driving directions** for
origin/destination route previews; starting navigation uses the mobile app.
A destination pin in the embed alone does not mean that driving navigation has
started. The default now opens the full Live Map directly in the managed ORC
panel, avoiding the compact embed's extra routing link.
See [Waze embed documentation](https://developers.google.com/waze/iframe/) and
[Waze desktop drive planning](https://support.google.com/waze/answer/6378906?co=GENIE.Platform%3DDesktop&hl=en-GB).
Device validation should confirm Driving directions is accessible at the actual
Termux/Pi screen size and that selecting a route stays usable inside the panel.

Configured browser applications now identify surviving browser processes by the
literal, bounded `--user-data-dir` argument, rather than the initial URL. Waze's
query-string punctuation must not be interpreted as process-search regex syntax,
and navigation to another URL must not make the managed browser disappear from
ORC's lifecycle tracking. Cleanup waits up to one second for the dedicated profile
processes to exit before allowing another launch. If they remain, ORC reports the
failure instead of racing the existing profile. Failed window embedding also
stops the spawned browser instead of leaving a loose window holding the profile.

A real headless Chromium check exercised surviving-profile discovery after losing
the launch handle and changing the recorded URL, then fallback shutdown. This
fixes a reproducible ownership problem; it does not prove the specific cause of
a device's exit status 3. That exit remains an error and is not silently treated
as a successful launch. If it recurs, the referenced browser log is needed to
distinguish profile contention from another browser startup failure.

Focused lifecycle validation:

```bash
git switch feature/waze-live-map
python -m pytest apps/launchers/unit_test/test_browser_launcher.py apps/launchers/unit_test/test_browser_app_factory.py apps/orcUi/composition/unit_test/test_waze.py -q
```
