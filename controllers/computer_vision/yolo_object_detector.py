# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Ultralytics YOLO object detector implementation."""

from __future__ import annotations

import time
from typing import Any, Iterable

from controllers.computer_vision.object_detector_if import (
    Detection,
    DetectionFrame,
    ObjectDetectorIf,
)
from hardware_io.camera.camera_if import CameraFrame


DEFAULT_ROAD_CLASSES = frozenset({"person", "bicycle", "motorcycle", "car", "bus", "truck"})


class YoloObjectDetector(ObjectDetectorIf):
    """Run a pretrained Ultralytics YOLO model on camera frames."""

    def __init__(
        self,
        model_name: str = "yolo11n.pt",
        *,
        confidence: float = 0.35,
        image_size: int = 640,
        labels: Iterable[str] = DEFAULT_ROAD_CLASSES,
    ) -> None:
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        if image_size <= 0:
            raise ValueError("image_size must be positive")

        try:
            from ultralytics import YOLO
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "Ultralytics is required for YOLO detection; install it with "
                "'python -m pip install ultralytics'"
            ) from exc

        self._model: Any = YOLO(model_name)
        self._confidence = confidence
        self._image_size = image_size
        self._labels = frozenset(labels)

    def detect(self, frame: CameraFrame) -> DetectionFrame:
        start = time.perf_counter()
        results = self._model.predict(
            source=frame.image,
            conf=self._confidence,
            imgsz=self._image_size,
            verbose=False,
        )
        inference_time_ms = (time.perf_counter() - start) * 1000.0

        detections: list[Detection] = []
        if results:
            result = results[0]
            image_height, image_width = frame.image.shape[:2]
            names = result.names

            for box in result.boxes:
                class_id = int(box.cls[0].item())
                label = str(names[class_id])
                if self._labels and label not in self._labels:
                    continue

                confidence = float(box.conf[0].item())
                x1, y1, x2, y2 = (float(value) for value in box.xyxy[0].tolist())
                x1 = max(0.0, min(x1, float(image_width)))
                y1 = max(0.0, min(y1, float(image_height)))
                x2 = max(x1, min(x2, float(image_width)))
                y2 = max(y1, min(y2, float(image_height)))

                detections.append(
                    Detection(
                        label=label,
                        confidence=confidence,
                        x=x1 / image_width,
                        y=y1 / image_height,
                        width=(x2 - x1) / image_width,
                        height=(y2 - y1) / image_height,
                    )
                )

        return DetectionFrame(
            timestamp_s=frame.timestamp_s,
            sequence=frame.sequence,
            inference_time_ms=inference_time_ms,
            detections=tuple(detections),
        )
