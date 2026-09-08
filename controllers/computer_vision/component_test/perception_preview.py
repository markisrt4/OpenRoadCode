# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Live camera preview with background YOLO object detection."""

from __future__ import annotations

import argparse
import time

from controllers.computer_vision.perception_worker import PerceptionWorker
from controllers.computer_vision.yolo_object_detector import YoloObjectDetector
from hardware_io.camera.v4l2_camera import V4L2Camera


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", default="/dev/video0")
    parser.add_argument("--model", default="yolo11n.pt")
    parser.add_argument("--confidence", type=float, default=0.35)
    parser.add_argument("--imgsz", type=int, default=640)
    return parser.parse_args()


def _draw_detections(cv2, image, result) -> None:
    height, width = image.shape[:2]
    for detection in result.detections:
        x1 = int(detection.x * width)
        y1 = int(detection.y * height)
        x2 = int((detection.x + detection.width) * width)
        y2 = int((detection.y + detection.height) * height)
        cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2)
        label = f"{detection.label} {detection.confidence:.0%}"
        cv2.putText(
            image,
            label,
            (x1, max(24, y1 - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (0, 255, 0),
            2,
            cv2.LINE_AA,
        )


def main() -> None:
    args = _parse_args()

    try:
        import cv2
    except ModuleNotFoundError as exc:
        raise SystemExit("OpenCV is required. Install python3-opencv.") from exc

    detector = YoloObjectDetector(
        model_name=args.model,
        confidence=args.confidence,
        image_size=args.imgsz,
    )
    worker = PerceptionWorker(detector)
    camera = V4L2Camera(args.device, width=1920, height=1080, fps=30.0, pixel_format="MJPG")

    camera_frames = 0
    last_camera_frames = 0
    last_ai_frames = 0
    sample_started = time.monotonic()
    camera_fps = 0.0
    ai_fps = 0.0

    worker.start()
    try:
        with camera:
            while True:
                frame = camera.read()
                camera_frames += 1
                worker.submit(frame)

                image = frame.image.copy()
                result = worker.latest_result
                if result is not None:
                    _draw_detections(cv2, image, result)

                now = time.monotonic()
                elapsed = now - sample_started
                if elapsed >= 1.0:
                    camera_fps = (camera_frames - last_camera_frames) / elapsed
                    ai_count = worker.processed_frames
                    ai_fps = (ai_count - last_ai_frames) / elapsed
                    last_camera_frames = camera_frames
                    last_ai_frames = ai_count
                    sample_started = now

                latency = result.inference_time_ms if result is not None else 0.0
                objects = len(result.detections) if result is not None else 0
                status = (
                    f"CAM {camera_fps:4.1f} fps   AI {ai_fps:4.1f} fps   "
                    f"{latency:5.0f} ms   objects {objects}"
                )
                cv2.putText(
                    image,
                    status,
                    (24, 42),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 255, 255),
                    2,
                    cv2.LINE_AA,
                )

                cv2.imshow("OpenRoadCode Perception Preview", image)
                key = cv2.waitKey(1) & 0xFF
                if key in (ord("q"), 27):
                    break
    finally:
        worker.stop()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
