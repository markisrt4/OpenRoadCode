# Embedded Waze gesture controls (Termux prototype)

With native Waze open through scrcpy, a **Waze Controls** button appears directly
below Views. Open it for Zoom +, Zoom − and four pan arrows. The arrows move the
view in screen directions, not compass directions; Waze can rotate its map.
The tray shares the same docked drawer as Views and Places, so only one is open.
It scrolls on short displays. Closing it restores the viewer's full width.

Pan sends a short drag in the opposite finger direction to the requested view
movement. Zoom sends scrcpy's Ctrl-drag pinch simulation through the center of
the displayed video. Gesture coordinates account for the current viewer size
and aspect-ratio margins. There are no hard-coded Waze button coordinates,
camera API calls, route changes or ORC map-camera commands.

This implementation is enabled only for the owned scrcpy viewer, currently the
native Termux integration. It does not add Waydroid gesture injection. The native
phone app, existing ADB/scrcpy connection and its virtual display are still
required. Controls are disabled until attachment completes and while launching,
closing or sending a gesture. Requests are serialized without a backlog.

Input goes to the specific embedded X11 window and its unique session title.
There is no default-display ADB input, pointer movement, global key injection,
or X11 keyboard-focus change. A small isolated sender supplies viewer-local
focus/key/mouse events so SDL can process a pinch while ORC owns real focus.
SDL's explicit automatic mouse capture is disabled only for this viewer; real
pointer input remains available. The sender releases button/Ctrl events on
completion, failure and cancellation. Leaving the Waze screen or closing its
session cancels pending work; a changed window identity or size aborts a gesture.
The retained route/session is not restarted by the controls.

Use the controls with **Waze's map visible**, not a menu, dialog or login screen.
Waze decides how to respond to input and may return to automatic following after
manual panning. There is no automatic recenter button in this prototype. Device
validation is needed for each Android/Waze/scrcpy combination; local input
delivery is not proof that Waze changed its camera.

## Phone check

With Termux:X11 running and the same phone connected to ADB, close ORC and run:

```bash
git switch feature/waze-live-map
git pull --ff-only
adb devices -l
ORC_SCRCPY_RENDERER=software ./runOrcUi
```

While stationary, open NAV → Views → Waze, wait for loading to finish, then open
Waze Controls. Test one tap of each arrow and Zoom +/−. Confirm the map responds
and ORC buttons and ordinary Waze dragging still work. Open Views/Places, leave
for Settings, then return through NAV and repeat. Check that an active route
survives. Try a compact window and resizing ORC; retry after layout settles if a
gesture is cancelled during a resize. Verify the phone's main display receives
no gestures and the real mouse pointer does not jump to the viewer.

If input fails, capture the relevant ORC terminal log excerpt and the installed
scrcpy version, without coordinates or app content. To copy the version:

```bash
git switch feature/waze-live-map
scrcpy --version 2>&1 | head -n 3 | termux-clipboard-set
```

## Focused validation

```bash
git switch feature/waze-live-map
python -m pytest -q controllers/navigation/unit_test/test_waze_gesture_controller.py apps/orcUi/composition/unit_test/test_scrcpy_waze_gestures.py frontends/x11/unit_test/test_scrcpy_gesture_sender.py frontends/tk/unit_test/test_navigation_experience_controls.py
```

The sender tests need an X11 display and SDL2 to exercise the actual SDL drag,
pinch and cancellation events and verify unchanged pointer/focus. They skip
those cases when unavailable. Phone rendering/behavior and the full quality gate
remain separate checks. The four existing Waydroid adapter dependency-boundary
violations are unchanged; this feature introduces no new boundary exceptions.
