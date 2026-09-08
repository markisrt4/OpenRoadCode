# OpenRoadCode Computer Vision

The computer-vision layer consumes `CameraFrame` objects and publishes
presentation-neutral object detections. Camera ownership remains in
`hardware_io.camera`; perception does not open video devices directly.

## VM perception preview

Install the camera and YOLO development dependencies in the active Python
environment:

```bash
sudo apt install python3-opencv
python -m pip install ultralytics
```

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
