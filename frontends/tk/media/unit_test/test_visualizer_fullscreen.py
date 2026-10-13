# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT
"""Fullscreen only retires its presentation, and closes it exactly once."""
from unittest.mock import Mock, patch

from frontends.tk.media.visualizer_fullscreen import VisualizerFullscreen


def test_fullscreen_close_retires_surface_and_restores_parent_once():
    window = object.__new__(VisualizerFullscreen)
    window._closed = False
    window._panel = Mock()
    window._on_close = Mock()
    with patch('tkinter.Toplevel.destroy') as destroy:
        window.close()
        window.close()
        window.destroy()
        window._panel.close.assert_called_once()
        window._on_close.assert_called_once()
        destroy.assert_called_once()
