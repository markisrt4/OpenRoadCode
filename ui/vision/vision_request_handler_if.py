# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Semantic requests emitted by camera and perception frontends."""

from abc import ABC, abstractmethod

from ui.vision.vision_ui_state import VisionCameraMode


class VisionRequestHandlerIf(ABC):
    """Handle user intent without exposing camera or inference adapters."""

    @abstractmethod
    def request_activate(self) -> None:
        """Request camera and perception startup."""
        ...

    @abstractmethod
    def request_deactivate(self) -> None:
        """Request shutdown and release of transient resources."""
        ...

    @abstractmethod
    def request_camera_mode(self, mode: VisionCameraMode) -> None:
        """Request a semantic camera-processing mode.

        @param mode Desired camera-processing mode.
        """
        ...

    @abstractmethod
    def request_ai_enabled(self, enabled: bool) -> None:
        """Request the desired object-inference state.

        @param enabled True to enable inference; False to disable it.
        """
        ...
