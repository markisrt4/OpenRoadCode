# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT
from unittest.mock import Mock

from frontends.tk.media.music_visualizer_screen import MusicVisualizerScreen
from ui.music_visualizer import MusicVisualizerSource


def test_hiding_screen_cancels_rendering_and_requests_capture_stop():
    host, controller, panel = Mock(), Mock(), Mock()
    screen = MusicVisualizerScreen(host, on_back=Mock(), theme_bundle=Mock(),
                                   controller=controller, initial_source=MusicVisualizerSource.SIMULATED)
    screen._poll_job = 'poll'
    screen._panel = panel
    screen.hide()
    host.cancel_ui_callback.assert_called_once_with('poll')
    controller.stop.assert_called_once_with()
    panel.close.assert_called_once_with()
    assert screen._panel is None
    # The composition owns controller shutdown; closing presentation only requests stop.
    screen.close()
    controller.close.assert_not_called()
