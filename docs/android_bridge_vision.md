# Vision from the Android Bridge camera

The Android Bridge already exposes rear-camera H.264 video over MPEG-TS on port
8767. ORC Vision now consumes that stream behind the existing `CameraIf` contract,
so video, perception and the navigation overlay share the normal Vision pipeline.
This change uses the existing bridge camera API and does not require a new APK API.

## Source selection

On native Termux (`PREFIX=/data/data/com.termux/files/usr`), Vision defaults to
`android_bridge` at `http://127.0.0.1:8767`. Desktop/Linux defaults to V4L2 at
`/dev/video0`. Composition owns platform detection and source selection.

Optional environment overrides, supplied when starting ORC:

| Variable | Values / purpose |
| --- | --- |
| `OPENROADCODE_VISION_CAMERA_SOURCE` | `android_bridge` or `v4l2` |
| `OPENROADCODE_VISION_BRIDGE_URL` | Camera service base URL, e.g. `http://phone-address:8767` |
| `OPENROADCODE_VISION_CAMERA_DEVICE` | V4L2 device path, default `/dev/video0` |

For a paired Linux runtime, select `android_bridge` and supply the camera address
shown in Bridge. The video URL is independent of the sensor service on 8766 and
the service-manager API on 8769. No new listener or fixed port is introduced by
the Python adapter. The legacy browser-motion development source also defaults to
8767; use an explicitly different development port when testing it alongside
Android video. Ordinary Termux navigation uses Android GPS and simulated IMU,
so it does not start that browser-motion listener.

## Decoder and lifecycle

OpenCV must include the FFmpeg video backend and support open/read timeout
properties (OpenCV 4.5.2 or later). OpenCV and Pillow are required for live video;
AI detection/tracking libraries are optional. Missing tracking dependencies or a
failed model load starts live video with **AI unavailable** and the AI button
disabled. Navigation overlays and camera controls keep working. Restart ORC after
installing AI dependencies to retry initialization. The adapter imports OpenCV
lazily and reports missing backend
support on the Vision error screen rather than using an unbounded decoder.

Before opening video, `/status` must report `state=streaming`, `codec=h264`, and
`container=mpegts`. This checks the actual listener; a saved enabled preference
is not evidence that the camera stream is ready. Open is bounded at 1.5 seconds
and reads at 0.5 seconds, with a separate 0.5-second status timeout. Closing signals
cancellation before waiting for the current operation, discards late frames, and
releases the native decoder once without racing `read()`. Stream loss reports an
error; leave Vision and reopen it after restarting the camera to reconnect.

Frames use the same BGR layout as V4L2. Their timestamps mark delivery by the local
decoder; Android capture timing and MPEG-TS PTS are not yet mapped into navigation's
clock. Overlay alignment therefore remains approximate and does not measure full
camera-to-display latency. Android Camera2 owns exposure. ORC DAY/AUTO/LOW_LIGHT
controls select the existing software image processing without issuing V4L2 or
Android exposure commands.

## Termux device check

1. In Bridge, enable the Camera stream, allow camera access, select **localhost**,
   and confirm streaming status. The current bridge stream is 1280x720 at a target
   of 30 FPS. Keep the bridge's camera service running when returning to Termux.
2. Close ORC and other stream players such as ffplay. Bridge supports one HTTP
   video client; a second player replaces the existing viewer. Bridge's built-in
   camera preview uses a separate camera surface and does not take this HTTP slot.
   Do not run the CLI `--frames` check while Vision is open. Read-only `/status`
   checks and `--check-only` do not consume the video stream.
3. Activate the Python environment normally used to run ORC. Update and check the
   bridge/backend without taking the video slot:

```bash
git switch feature/navigation-upgrades
git pull --ff-only
python -m hardware_io.camera.component_test.android_bridge_camera_cli --check-only
```

Decode five frames with ORC/other viewers still closed:

```bash
git switch feature/navigation-upgrades
python -m hardware_io.camera.component_test.android_bridge_camera_cli --frames 5
```

Restart ORC normally and open Vision. Confirm **Android Bridge camera** in SRC,
live video, and the existing AI and NAV OVERLAY controls. Calculate a route in
Navigation and return to Vision to check the maneuver overlay. Leaving Vision
should release the HTTP video slot; returning should reconnect. Stop/start Camera
in Bridge and check recovery by leaving and reopening Vision.

Camera workers enqueue the latest snapshot through the thread-safe UI dispatcher;
only the frontend thread renders it. A **VIDEO STALE** banner means the displayed
frame has aged beyond the overlay threshold; it does not by itself establish
whether the camera, decoder, UI delivery, or another HTTP viewer caused the delay.

If diagnosis is needed, copy only the read-only listener/backend check:

```bash
git switch feature/navigation-upgrades
python -m hardware_io.camera.component_test.android_bridge_camera_cli --check-only 2>&1 | termux-clipboard-set
```

Paste the clipboard contents in the conversation. The command does not collect
frames, GPS coordinates or credential values.

## Focused validation

If importing `cv2` fails with `dlopen failed` and a Protobuf symbol referenced by
`libopencv_dnn.so`, the native OpenCV/Protobuf libraries are incompatible. Update
the Termux package set, then reinstall its matching `libprotobuf`, `opencv`,
`opencv-python` and `python-opencv-python` packages. This is a native package
failure before any video decoding, not a failure of the Bridge camera endpoint.
If it persists after package repair, collect installed package versions and the
short import error before changing Python packages or rebuilding from source.

```bash
git switch feature/navigation-upgrades
python -m pytest -q hardware_io/camera/unit_test/test_android_bridge_camera.py apps/orcUi/composition/unit_test/test_vision_camera.py apps/orcUi/composition/unit_test/test_vision_optional.py controllers/computer_vision/unit_test/test_vision_controller.py apps/orcUi/composition/unit_test/test_vision_navigation.py
python -m pytest -q hardware_io/camera/integration_test/test_android_bridge_stream.py
```

The integration test generates synthetic H.264 video with FFmpeg and serves it
through an ephemeral localhost HTTP fixture. It skips when the required decoder
or fixture encoder is unavailable. Device capture/latency testing and the user's
local `python scripts/quality_gate.py` remain pending.
