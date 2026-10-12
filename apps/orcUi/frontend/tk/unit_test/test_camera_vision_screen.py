# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for camera VISION fallback presentation."""

from apps.orcUi.frontend.tk.camera_vision_screen import CameraVisionScreen
from ui.vision.vision_ui_state import VisionLifecycle, VisionUiState
from ui.vision.navigation_overlay import NavigationOverlayState
from unittest.mock import Mock


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


def test_hiding_camera_stops_overlay_and_late_state_cannot_touch_canvas():
    screen = object.__new__(CameraVisionScreen)
    screen._navigation_handler = Mock()
    screen._request_handler = Mock()
    canvas = Mock()
    screen._canvas = canvas
    screen.hide()
    screen._navigation_handler.request_deactivate.assert_called_once()
    screen._request_handler.request_deactivate.assert_called_once()
    screen.set_navigation_overlay(NavigationOverlayState())
    assert canvas.mock_calls == []


def test_overlay_button_emits_semantic_visibility_request():
    screen = object.__new__(CameraVisionScreen)
    screen._navigation = NavigationOverlayState(enabled=True)
    screen._navigation_handler = Mock()
    screen._request_navigation_change()
    screen._navigation_handler.request_enabled.assert_called_once_with(False)
