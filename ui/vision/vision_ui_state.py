# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Immutable, toolkit-independent camera and perception presentation state."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class VisionLifecycle(str, Enum):
    """Lifecycle phases visible to a vision frontend."""

    INACTIVE = "inactive"
    STARTING = "starting"
    RUNNING = "running"
    ERROR = "error"


class VisionCameraMode(str, Enum):
    """Semantic camera-processing modes selectable by a user."""

    AUTO = "auto"
    DAY = "day"
    LOW_LIGHT = "low_light"


class VisionPixelFormat(str, Enum):
    """Pixel layouts supported by the frontend image contract."""

    RGB888 = "rgb888"


@dataclass(frozen=True, slots=True)
class VisionImage:
    """One immutable image ready for frontend rendering."""

    width: int
    height: int
    stride_bytes: int
    pixel_format: VisionPixelFormat
    timestamp_s: float
    sequence: int
    data: bytes

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("image dimensions must be positive")
        minimum_stride = self.width * 3
        if self.stride_bytes < minimum_stride:
            raise ValueError("RGB888 stride must contain every pixel")
        if len(self.data) != self.stride_bytes * self.height:
            raise ValueError("image data length does not match stride and height")
        if self.timestamp_s < 0.0:
            raise ValueError("timestamp_s must be non-negative")
        if self.sequence < 0:
            raise ValueError("sequence must be non-negative")


@dataclass(frozen=True, slots=True)
class VisionObject:
    """One detected or tracked object in normalized image coordinates."""

    label: str
    confidence: float
    x: float
    y: float
    width: float
    height: float
    track_id: int | None = None
    track_age_s: float | None = None

    def __post_init__(self) -> None:
        if not self.label.strip():
            raise ValueError("label must not be empty")
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
        if self.x + self.width > 1.0 or self.y + self.height > 1.0:
            raise ValueError("object bounds must remain inside the image")
        if self.track_id is not None and self.track_id < 0:
            raise ValueError("track_id must be non-negative")
        if self.track_age_s is not None:
            if self.track_id is None:
                raise ValueError("track_age_s requires a track_id")
            if self.track_age_s < 0.0:
                raise ValueError("track_age_s must be non-negative")


@dataclass(frozen=True, slots=True)
class VisionUiState:
    """Complete snapshot presented atomically by a vision frontend."""

    lifecycle: VisionLifecycle = VisionLifecycle.INACTIVE
    requested_mode: VisionCameraMode = VisionCameraMode.AUTO
    effective_mode: VisionCameraMode = VisionCameraMode.DAY
    ai_enabled: bool = True
    camera_rate_hz: float = 0.0
    inference_rate_hz: float = 0.0
    inference_latency_s: float = 0.0
    luminance_ratio: float = 0.0
    source_label: str = ""
    status_message: str = ""
    image: VisionImage | None = None
    objects: tuple[VisionObject, ...] = ()

    def __post_init__(self) -> None:
        for name, value in (
            ("camera_rate_hz", self.camera_rate_hz),
            ("inference_rate_hz", self.inference_rate_hz),
            ("inference_latency_s", self.inference_latency_s),
        ):
            if value < 0.0:
                raise ValueError(f"{name} must be non-negative")
        if not 0.0 <= self.luminance_ratio <= 1.0:
            raise ValueError("luminance_ratio must be between 0 and 1")
