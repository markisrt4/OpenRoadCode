# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Presentation-neutral object-detection contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from hardware_io.camera.camera_if import CameraFrame


@dataclass(frozen=True)
class Detection:
    """One normalized object detection within a camera frame."""

    label: str
    confidence: float
    x: float
    y: float
    width: float
    height: float

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        for name, value in (
            ("x", self.x),
            ("y", self.y),
            ("width", self.width),
            ("height", self.height),
        ):
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be normalized between 0 and 1")


@dataclass(frozen=True)
class DetectionFrame:
    """Detections associated with one source camera frame."""

    timestamp_s: float
    sequence: int
    detections: tuple[Detection, ...]


class ObjectDetectorIf(ABC):
    """Interface implemented by YOLO or other perception engines."""

    @abstractmethod
    def detect(self, frame: CameraFrame) -> DetectionFrame:
        """Run inference for one camera frame."""
