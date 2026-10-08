# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for immutable vision presentation values."""

import pytest

from ui.vision.vision_ui_state import VisionImage, VisionObject, VisionPixelFormat, VisionUiState


def test_rgb_image_requires_exact_buffer_length() -> None:
    """Reject a pixel buffer inconsistent with its declared geometry."""
    with pytest.raises(ValueError, match="data length"):
        VisionImage(2, 2, 6, VisionPixelFormat.RGB888, 1.0, 0, b"short")


def test_object_bounds_must_remain_inside_image() -> None:
    """Reject normalized boxes extending beyond the source image."""
    with pytest.raises(ValueError, match="inside"):
        VisionObject("car", 0.9, 0.8, 0.1, 0.3, 0.2)


def test_tracking_age_requires_identity() -> None:
    """Reject tracking age when no persistent identity is available."""
    with pytest.raises(ValueError, match="track_id"):
        VisionObject("car", 0.9, 0.1, 0.1, 0.3, 0.2, track_age_s=1.0)


def test_ui_state_uses_normalized_luminance() -> None:
    """Reject luminance outside the frontend-neutral normalized range."""
    with pytest.raises(ValueError, match="luminance_ratio"):
        VisionUiState(luminance_ratio=1.1)
