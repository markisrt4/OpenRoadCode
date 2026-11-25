# OpenRoadCode camera input

This package owns presentation-neutral camera capture. Linux USB cameras are
currently supported through `V4L2Camera`, which uses OpenCV's V4L2 backend.

## VM / Raspberry Pi setup

On Pi 5, select **Linux USB cameras and V4L2 controls** in the host installer
TUI, or use the equivalent command:

```bash
git switch feature/rpi5-integration
git fetch origin
git pull --ff-only
./scripts/installers/host_setup.sh --target rpi5 --feature video-v4l2
```

Select **YOLO object detection and tracking** only if you want inference.
If the installer adds the `video` group, log out and back in before opening
Vision. The desktop capture backend supports USB V4L2 cameras.

Confirm the camera is visible and inspect its modes:

```bash
v4l2-ctl --list-devices
v4l2-ctl -d /dev/video0 --list-formats-ext
```

Launch `./runOrcUi`, open **Vision**, and confirm the preview appears. Leave
and reopen Vision to verify the camera is released and can be opened again.
If the capture node differs from `/dev/video0`, select it at launch, preferably
using a stable link from `/dev/v4l/by-id`:

```bash
ORC_CAMERA_DEVICE=/dev/video2 ./runOrcUi
```

Run the live OpenRoadCode preview from the repository root:

```bash
python -m hardware_io.camera.component_test.camera_preview
```

The defaults match the first OpenRoadCode road camera tested in development:
`/dev/video0`, MJPEG, 1920x1080, 30 fps. Override them when needed:

```bash
python -m hardware_io.camera.component_test.camera_preview \
  --device /dev/video0 --width 1280 --height 720 --fps 30 --format MJPG
```

Press `q` or Escape to close the preview.

## Architecture

`CameraIf` owns capture only. It returns `CameraFrame` objects and knows
nothing about UI, recording, or computer vision. Perception consumes those
frames through `controllers.computer_vision.ObjectDetectorIf`, allowing the
preview, recorder, and future YOLO implementation to evolve independently.
`CameraControlsIf` similarly exposes hardware-neutral `DAY` and `LOW_LIGHT`
profiles. Linux-specific V4L2 commands remain in its platform adapter.


## Hardware control profiles

The validated USB road camera also exposes V4L2 controls for exposure, gain,
gamma, backlight compensation, white balance, sharpness, and power-line
frequency. OpenRoadCode currently applies two conservative hardware profiles
through `V4L2CameraProfileController`:

- `DAY`: camera auto exposure, gain 1, gamma 200, backlight compensation 0.
- `LOW_LIGHT`: camera auto exposure, gain 10, gamma 220, backlight
  compensation 1. The device advertises absolute exposure but reports it
  inactive and rejects writes while streaming, so ORC does not force it.

Both profiles select 60 Hz power-line compensation for the current U.S. test
environment. The low-light profile deliberately leaves exposure under the camera's supported
auto mode and increases only bounded gain/gamma/backlight controls, avoiding an
unsupported shutter override and excessive motion blur.

The profile controller shells out to `v4l2-ctl`, which is installed by
`development/debian/setup_camera_perception.sh`.

## Structured logging

`vision.camera` records open/close and capture failure/recovery;
`vision.camera.controls` records profile transitions and control failures/recovery.
Normal capture and already-applied profiles remain DEBUG. Records include only
fixed stages, state and exception type, never frames, device paths or control
command output. Parent vision operation IDs are retained. See the
[device validation guide](../../common/logging/DEVICE_VALIDATION.md).
