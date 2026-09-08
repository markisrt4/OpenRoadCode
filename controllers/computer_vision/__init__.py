# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Computer-vision contracts and implementations."""

from controllers.computer_vision.object_detector_if import (
    Detection,
    DetectionFrame,
    ObjectDetectorIf,
)

__all__ = ["Detection", "DetectionFrame", "ObjectDetectorIf"]
