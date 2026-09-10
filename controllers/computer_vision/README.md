# OpenRoadCode Computer Vision

The computer-vision layer consumes `CameraFrame` objects and publishes
presentation-neutral object detections. Camera ownership remains in
`hardware_io.camera`; perception does not open video devices directly.

## Debian/Ubuntu setup

Use the project setup script rather than installing dependencies by hand:

```bash
./development/debian/setup_camera_perception.sh
```

The script installs the Linux camera tooling (`v4l-utils`, OpenCV, Python venv
support), finds the active OpenRoadCode virtual environment or the repository
`venv`, creates `venv` if needed, and installs Ultralytics there. It finishes
with import checks and reports whether `/dev/video0` is present.

Activate the environment when needed:

```bash
source venv/bin/activate
```

## VM perception preview

Run the live preview with the default USB camera:

```bash
python -m controllers.computer_vision.component_test.perception_preview
```

The default configuration uses `/dev/video0`, 1920x1080 MJPEG capture at 30
FPS, the small `yolo11n.pt` model, 640-pixel inference input, and a confidence
threshold of 0.35. Ultralytics may download the model weights on the first run.

The preview displays detections for road-relevant COCO classes: person,
bicycle, motorcycle, car, bus, and truck. It also displays camera FPS, AI FPS,
inference latency, and the current object count. Press `q` or Escape to exit.

Useful overrides:

```bash
python -m controllers.computer_vision.component_test.perception_preview \
  --device /dev/video0 \
  --model yolo11n.pt \
  --confidence 0.40 \
  --imgsz 640
```

## Concurrency model

`PerceptionWorker` runs inference on a background thread. Camera capture and
preview remain on the caller's thread. Submitting a newer frame replaces any
older pending frame that inference has not started processing, so the detector
prefers fresh road-scene data over building latency in a frame queue.

Bounding boxes are normalized to `[0, 1]`, allowing inference resolution and
preview resolution to differ without coupling the UI to model input geometry.


## orcUi VISION evaluation screen

The integrated orcUi shell now exposes an isolated `VISION` navigation
destination for camera/perception evaluation. It intentionally does not feed
HOME, NAVIGATION, VEHICLE, or other screens while the feature is being
developed.

Start orcUi normally:

```bash
python -m apps.orcUi
```

Select `VISION` from the side navigation. Entering the screen opens
`/dev/video0`, starts YOLO inference, and shows the live camera image with
normalized detection overlays. Leaving the screen stops inference and releases
the camera.

The screen provides three processing profiles:

- `AUTO`: select low-light enhancement when mean scene luminance is low.
- `DAY`: show and analyze the unmodified camera frame.
- `LOW LIGHT`: apply CLAHE to the LAB lightness channel before preview and
  inference.

The initial low-light mode is software preprocessing only. Camera exposure,
gain, gamma, and other V4L2 hardware controls remain separate so the software
effect can be evaluated before hardware tuning is added.
