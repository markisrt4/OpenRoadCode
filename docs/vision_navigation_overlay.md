# Navigation over live video

The Vision screen can display navigation guidance over the existing camera feed.
The **NAV OVERLAY: ON/OFF** control changes only overlay visibility. Camera capture,
AI detection, route calculation and spoken guidance keep their existing lifecycle.
The chosen visibility survives leaving and returning to Vision during a session.

The compact panel occupies the upper-left corner of the video, inside its
letterboxed image bounds. It shows a typed maneuver arrow, distance to the turn,
instruction, road name, speed and GPS status. Display units follow the application's
Imperial/Metric setting; shared values remain in metres and metres per second.
An absent camera frame leaves the normal camera startup/error message visible.

## Direction and status

Directions come from Valhalla maneuver types, not from matching words in the
instruction. Street names come from the route response. Guidance messages now
carry optional `turn` and `road_name` fields. Updated readers also accept old
messages without these fields, showing a neutral direction indicator and the
existing instruction. Restart the navigation producer and calculate a fresh
route to obtain typed maneuver metadata. Older readers with a strict schema must
be updated alongside the producer.

The overlay distinguishes no GPS fix, live GPS, weak accuracy (over 25 metres),
cached position and stale position (over three seconds without a new fix).
Missing/cached/stale GPS suppresses actionable maneuver text and live speed.
Off-route and arrival states have explicit labels. Guidance older than five
seconds is suppressed; video older than 1.5 seconds displays a delayed-video
message instead of a maneuver or speed.

## Timestamp alignment and ownership

Camera frames carry local monotonic timestamps. Navigation ingress records local
monotonic receipt times and retains bounded histories. The controller selects
only observations received at or before the displayed frame's timestamp, so
delayed frames cannot borrow future guidance. Duplicate or out-of-order GPS and
motion source timestamps do not refresh the corresponding history.

This is approximate presentation alignment. The camera timestamp is recorded by
the existing capture adapter, and guidance has no source timestamp on its wire
contract. Sensor transport latency, exposure timing and clock calibration remain
future work. This panel is fixed on the image; it does not identify lanes, project
arrows onto the road, or change the position solution.

`NavigationOverlayController` owns matching, freshness, visibility and timer
generation checks, using the toolkit-independent contracts in
`ui/vision/navigation_overlay.py`. Composition owns one ordered subscriber and
observes Vision frame delivery through an adapter. The screen consumes immutable
state and emits semantic requests. Hiding Vision cancels the health timer and
invalidates old callbacks; shutdown closes ingress before the overlay and camera
controllers. No extra camera, AI model, or route planner is constructed.

## Device check

On the navigation-upgrades branch, close ORC and update the Python checkout.
For Termux with the existing runit setup:

```bash
git switch feature/navigation-upgrades
git pull --ff-only
sv restart openroadcode-navigation
```

Restart ORC normally. Connect the existing camera source (`/dev/video0` in the
current composition), calculate a route in Navigation, then open Vision. Confirm
the maneuver, distance, road name and speed match Navigation, and that the toggle
hides/reveals guidance without restarting the video. End the route, check arrival
and off-route states, switch units in Settings, and leave/re-enter Vision. A stopped
camera stream should change to the delayed-video message. Check GPS loss/cached
data without replacing it with fabricated values.

Focused validation (activate the project's Python environment first):

```bash
git switch feature/navigation-upgrades
python -m pytest -q controllers/computer_vision/unit_test/test_navigation_overlay_controller.py controllers/computer_vision/unit_test/test_vision_controller.py apps/orcUi/frontend/tk/unit_test/test_vision_navigation_overlay.py apps/orcUi/frontend/tk/unit_test/test_camera_vision_screen.py apps/orcUi/composition/unit_test/test_vision_navigation.py apps/orcUi/composition/unit_test/test_vision_optional.py apps/orcUi/composition/unit_test/test_application.py messaging/contracts/route_guidance/unit_test/test_route_guidance_state_contract.py controllers/route_planning/test/test_vision_maneuver_metadata.py services/navigation/unit_test/test_navigation_runtime.py common/logging/unit_test/test_navigation_logging.py
```

Full validation remains pending until the user runs `python scripts/quality_gate.py`
locally and confirms live rendering and camera latency on the device.
