# OpenRoadCode camera input

This package owns presentation-neutral camera capture. Linux USB cameras are
currently supported through `V4L2Camera`, which uses OpenCV's V4L2 backend.

## VM / Raspberry Pi setup

Install the runtime dependency:

```bash
sudo apt install python3-opencv
```

Confirm the camera is visible and inspect its modes:

```bash
v4l2-ctl --list-devices
v4l2-ctl -d /dev/video0 --list-formats-ext
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
