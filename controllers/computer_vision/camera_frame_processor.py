# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Camera-frame preprocessing for human preview and perception."""

from __future__ import annotations

from enum import Enum
from typing import Any


class CameraMode(str, Enum):
    """Selectable camera processing profiles."""

    AUTO = "auto"
    DAY = "day"
    LOW_LIGHT = "low_light"


class CameraFrameProcessor:
    """Apply lightweight camera preprocessing without owning camera hardware."""

    def __init__(self, mode: CameraMode = CameraMode.AUTO, *, auto_threshold: float = 70.0) -> None:
        if not 0.0 <= auto_threshold <= 255.0:
            raise ValueError("auto_threshold must be between 0 and 255")
        self._mode = mode
        self._auto_threshold = float(auto_threshold)

    @property
    def mode(self) -> CameraMode:
        return self._mode

    def set_mode(self, mode: CameraMode) -> None:
        self._mode = CameraMode(mode)

    def effective_mode(self, image: Any) -> CameraMode:
        if self._mode is not CameraMode.AUTO:
            return self._mode

        try:
            import cv2
        except ModuleNotFoundError as exc:
            raise RuntimeError("OpenCV is required for camera preprocessing") from exc

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        return CameraMode.LOW_LIGHT if float(gray.mean()) < self._auto_threshold else CameraMode.DAY

    def process(self, image: Any) -> Any:
        """Return a processed BGR image suitable for preview or inference."""
        mode = self.effective_mode(image)
        if mode is CameraMode.DAY:
            return image

        try:
            import cv2
        except ModuleNotFoundError as exc:
            raise RuntimeError("OpenCV is required for camera preprocessing") from exc

        # CLAHE improves local contrast without globally blowing out headlights
        # and bright road signs. Work in LAB so chroma is left undisturbed.
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        lightness, channel_a, channel_b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(lightness)
        return cv2.cvtColor(cv2.merge((enhanced, channel_a, channel_b)), cv2.COLOR_LAB2BGR)
