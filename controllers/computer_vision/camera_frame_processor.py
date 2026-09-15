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
    """Apply lightweight preprocessing with hysteretic automatic mode selection."""

    def __init__(
        self,
        mode: CameraMode = CameraMode.AUTO,
        *,
        auto_enter_low_light: float = 65.0,
        auto_exit_low_light: float = 85.0,
    ) -> None:
        if not 0.0 <= auto_enter_low_light <= 255.0:
            raise ValueError("auto_enter_low_light must be between 0 and 255")
        if not 0.0 <= auto_exit_low_light <= 255.0:
            raise ValueError("auto_exit_low_light must be between 0 and 255")
        if auto_enter_low_light >= auto_exit_low_light:
            raise ValueError("auto_enter_low_light must be below auto_exit_low_light")

        self._mode = CameraMode(mode)
        self._auto_enter_low_light = float(auto_enter_low_light)
        self._auto_exit_low_light = float(auto_exit_low_light)
        self._auto_effective_mode = CameraMode.DAY
        self._last_effective_mode = CameraMode.DAY
        self._last_luminance = 0.0

    @property
    def mode(self) -> CameraMode:
        return self._mode

    @property
    def last_effective_mode(self) -> CameraMode:
        return self._last_effective_mode

    @property
    def last_luminance(self) -> float:
        return self._last_luminance

    def set_mode(self, mode: CameraMode) -> None:
        self._mode = CameraMode(mode)

    def effective_mode(self, image: Any) -> CameraMode:
        if self._mode is not CameraMode.AUTO:
            self._last_effective_mode = self._mode
            return self._mode

        try:
            import cv2
        except ModuleNotFoundError as exc:
            raise RuntimeError("OpenCV is required for camera preprocessing") from exc

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        luminance = float(gray.mean())
        self._last_luminance = luminance

        if self._auto_effective_mode is CameraMode.DAY:
            if luminance < self._auto_enter_low_light:
                self._auto_effective_mode = CameraMode.LOW_LIGHT
        elif luminance > self._auto_exit_low_light:
            self._auto_effective_mode = CameraMode.DAY

        self._last_effective_mode = self._auto_effective_mode
        return self._auto_effective_mode

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
