# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from frontends.tk.audio_analysis.music_visualizer_panel import _fit_image_size


def test_image_fit_never_returns_zero_dimensions() -> None:
    assert _fit_image_size(1,1,960,720) == (1,1)


def test_image_fit_preserves_aspect_ratio_inside_canvas() -> None:
    width,height=_fit_image_size(500,200,960,720)
    assert width <= 460
    assert height <= 188
    assert abs(width/height-960/720) < .02
