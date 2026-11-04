# Navigation views and places

NAV remains the single rail destination. The navigation bar now contains Home,
Work, Places and Views on both the ORC map and native Waze screen.

Views opens a docked drawer with schematic preview tiles for Road map, Waze and
3D terrain. The selected experience is highlighted; Waze shows a running/resume
label while its session is active. Unsupported experiences are disabled. Launch
and close operations disable duplicate selections until they finish. Selecting
a tile closes the drawer. Closing the drawer alone changes no active session.

The drawer occupies a separate column beside the native viewport. It does not
cover an embedded X11 surface. Its content scrolls on short displays. Closing
it restores the full content width without stopping or relaunching Waze.

Places contains Food, Fuel, Groceries and Transit categories, transit filters,
Clear Results, search status and selectable results. Selecting a result opens the
existing POI card with ORC navigation, Navigate with Waze and supported business
actions. Home and Work use ORC's saved destinations; on the Waze screen they
send those destinations to Waze. Opening Places from Waze returns to the ORC map
and keeps Waze running. ORC POI markers are not injected into Waze.

The existing expandable Controls tray continues to provide pan, zoom, follow,
North, recenter, tilt and 2D/3D actions. In terrain mode these use the existing
Cesium camera contract. Opening Views or Places collapses the camera tray;
opening the camera tray closes the navigation drawer. Existing Cesium layer
controls remain in the terrain viewer; this change does not replace that
branch's layer implementation. Radar/weather controls are in the map's Views
drawer rather than competing for space on the top bar.
The Controls handle is aligned at the top-right of the map, directly below
Views. It hides while Views or Places is open and returns when the drawer closes.
Nested native hosts explicitly settle their grid allocation when a drawer opens
or closes, including on the first click. Left-rail tile sizing is unchanged.
Returning to NAV restores the last selected Road/Terrain experience as well as
the remembered Map/Waze destination.

This change preserves the existing map and terrain runtime lifecycles. The
drawers themselves do not reset the camera, but it does not add persistence for
Cesium camera/layer settings across browser teardown or application restarts.
scrcpy retains the virtual display proportions chosen at session launch; opening
a drawer temporarily scales that display into the smaller viewport. Close and
reopen Waze after resizing ORC if a new display aspect ratio is needed.

## Device check

On Termux with ADB connected, close ORC, update, then launch:

```bash
git switch feature/waze-live-map
git pull --ff-only
ORC_SCRCPY_RENDERER=software ./runOrcUi
```

Verify Road map → Views → Waze, leave for another screen, and return through
NAV. Open/close Views while Waze is navigating: the route should remain active,
the viewer should stay inside the panel, and full width should return on close.
Open Places, search Food, select a business, and test its ORC/Waze navigation
actions. Verify saved Home/Work. Switch to terrain and test the Controls tray.
Repeat at a compact window size; scroll the drawers to reach remaining actions.

Focused checks (use an available X11 display for geometry tests):

```bash
git switch feature/waze-live-map
python -m pytest -q controllers/navigation/unit_test/test_navigation_experience_controller.py frontends/tk/unit_test/test_navigation_experience_controls.py frontends/tk/media/unit_test/test_android_app_screen.py apps/orcUi/frontend/tk/unit_test/test_navigation_panel.py apps/orcUi/composition/unit_test/test_android_app_view.py apps/orcUi/frontend/tk/unit_test/test_map_platform_bar.py
```

The full quality gate remains a local pre-merge check. The existing Waydroid
embedder's four dependency-boundary violations are unchanged by this work.
