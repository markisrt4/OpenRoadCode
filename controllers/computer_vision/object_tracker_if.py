# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Presentation-neutral multi-object tracking contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from controllers.computer_vision.object_detector_if import DetectionFrame


@dataclass(frozen=True)
class ObjectTrack:
    """One persistent object identity in normalized camera coordinates."""

    track_id: int
    label: str
    confidence: float
    x: float
    y: float
    width: float
    height: float
    age_s: float

    def __post_init__(self) -> None:
        if self.track_id < 0:
            raise ValueError("track_id must be non-negative")
        if self.age_s < 0.0:
            raise ValueError("age_s must be non-negative")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        for name, value in (
            ("x", self.x), ("y", self.y),
            ("width", self.width), ("height", self.height),
        ):
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be normalized between 0 and 1")


@dataclass(frozen=True)
class TrackFrame:
    """Tracked objects associated with one detector result."""

    timestamp_s: float
    sequence: int
    tracks: tuple[ObjectTrack, ...]


class ObjectTrackerIf(ABC):
    """Associate frame-local detections into persistent object identities."""

    @abstractmethod
    def update(self, detections: DetectionFrame) -> TrackFrame:
        """Update tracking state from one chronological detection frame."""

    def reset(self) -> None:
        """Forget all active tracks."""
