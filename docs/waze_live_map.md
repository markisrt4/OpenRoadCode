# Experimental Waze Live Map

The `WAZE` destination opens the official Waze Live Map embed in an ORC-owned
browser panel. It uses the existing X11 browser hosting, with a separate browser
profile and a Back action to Home. Leaving the screen, entering offline mode,
or closing ORC stops the browser and cancels pending launches.

This requires an online connection, an existing supported Chromium/Chrome setup,
X11 and `xdotool`, as used by ORC's browser media panels. Raspberry Pi 5 rendering
and touchscreen behavior still need device validation. Native Wayland embedding
is not provided; use the existing ORC X11 session.

Configure `[apps.waze]` in `config/applications.toml` (Linux/Pi) or
`config/applications.termux.toml` (Termux). The default location is Detroit;
change the URL's `lat`, `lon`, and `zoom` parameters to choose the initial view.
Set `enabled = false` to remove the destination. Existing custom application
configs without a Waze entry continue to work without a Waze screen.

The page is a separate Waze view: it does not receive ORC GPS, routes or POIs,
and Waze data is not extracted into MapLibre. This is an online traffic/map
experiment, not the mobile Waze app or voice-guided turn-by-turn navigation.
The embed's available controls may differ from the full Live Map website.

Use the documented [Waze embed](https://developers.google.com/waze/iframe/)
and preserve Waze's presentation. Its guidelines restrict associating Waze with
non-Waze maps and applying Waze branding to them. The documentation describes
website embedding, not an explicit desktop-application license; this experiment
does not settle that distinction or grant permission beyond Waze's terms.

## Try on the Pi

From the repository checkout:

```bash
git switch feature/waze-live-map
./runOrcUi
```

Select **WAZE** while online. Check that the map loads, pan/zoom work by touch,
resizing stays inside ORC, and Back returns Home. Reopen the screen repeatedly,
switch to Navigation, then toggle offline while Waze is open: its browser should
close, and normal ORC navigation should continue. Re-enable online and reopen
Waze, then close ORC and check that the Waze browser exits.

Focused portable validation:

```bash
git switch feature/waze-live-map
python -m pytest apps/orcUi/composition/unit_test/test_waze.py apps/orcUi/composition/unit_test/test_application.py apps/orcUi/composition/unit_test/test_startup_cleanup.py -q
python scripts/check_ui_boundaries.py
```

Full validation remains pending the user-run quality gate before merge.
