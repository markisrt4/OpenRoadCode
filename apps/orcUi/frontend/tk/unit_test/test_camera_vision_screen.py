# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for camera VISION fallback presentation."""

from apps.orcUi.frontend.tk.camera_vision_screen import CameraVisionScreen
import pytest

from ui.vision.vision_ui_state import VisionCameraMode, VisionLifecycle, VisionUiState


def test_camera_error_detail_is_used_as_empty_canvas_message() -> None:
    """Show the controller's actionable camera error when no frame exists."""
    state = VisionUiState(
        lifecycle=VisionLifecycle.ERROR,
        status_message="Camera unavailable: Unable to open /dev/video0",
    )

    assert CameraVisionScreen._empty_image_message(state) == state.status_message


def test_running_without_a_frame_reports_that_capture_is_pending() -> None:
    """Distinguish a pending first frame from an unavailable camera."""
    state = VisionUiState(lifecycle=VisionLifecycle.RUNNING)

    assert CameraVisionScreen._empty_image_message(state) == "Waiting for camera frames…"


def test_auto_is_the_only_mode_available_before_hardware_probe() -> None:
    assert VisionUiState().available_modes == (VisionCameraMode.AUTO,)


def test_auto_cannot_be_removed_from_available_modes() -> None:
    with pytest.raises(ValueError, match="AUTO"):
        VisionUiState(available_modes=(VisionCameraMode.DAY,))
